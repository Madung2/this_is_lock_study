import asyncio
import time
from ..models import TransferRequest, TransferResponse
from ..database import get_optimistic_connection

class OptimisticLockTransferService:
    def __init__(self):
        self.initial_balances = {
            "account_a": 100000,
            "account_b": 100000
        }
        self.max_retries = 5  # 재시도 최대 횟수
    
    async def transfer(self, request: TransferRequest) -> TransferResponse:
        """낙관적락을 사용한 계좌 이체 (재시도 로직 포함)"""
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                result = await self._attempt_transfer(request, start_time, attempt + 1)
                if result.success or result.message == "잔액이 부족합니다.":
                    return result
                # 충돌 시 재시도
                # 재시도 간격을 점점 늘려가면서 대기
                # attempt=1 이면 0.02초, attempt=2 이면 0.04초, attempt=3 이면 0.08초...
                # 이렇게 하면 동시 요청이 몰릴 때 충돌 가능성을 줄일 수 있음
                await asyncio.sleep(0.01 * (2 ** attempt))  # 지수 백오프
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return TransferResponse(
                        success=False,
                        message=f"이체 중 오류가 발생했습니다: {str(e)}",
                        execution_time=time.time() - start_time
                    )
        
        return TransferResponse(
            success=False,
            message=f"최대 재시도 횟수({self.max_retries})를 초과했습니다. 동시성 충돌이 지속되고 있습니다.",
            execution_time=time.time() - start_time
        )
    
    async def _attempt_transfer(self, request: TransferRequest, start_time: float, attempt: int) -> TransferResponse:
        """단일 이체 시도"""
        async with get_optimistic_connection() as conn:
            # 트랜잭션 시작
            async with conn.transaction():
                ############################읽는부분 (락 없음)############################
                # 낙관적락: SELECT FOR UPDATE 사용하지 않음
                # 대신 version 컬럼을 함께 조회
                from_account_data = await conn.fetchrow(
                    "SELECT id, balance, version FROM accounts WHERE id = $1",
                    request.from_account
                )
                
                to_account_data = await conn.fetchrow(
                    "SELECT id, balance, version FROM accounts WHERE id = $1",
                    request.to_account
                )
                
                if not from_account_data or not to_account_data:
                    return TransferResponse(
                        success=False,
                        message="계좌를 찾을 수 없습니다.",
                        execution_time=time.time() - start_time
                    )
                
                # 잔액 확인
                if from_account_data['balance'] < request.amount:
                    return TransferResponse(
                        success=False,
                        message="잔액이 부족합니다.",
                        from_balance=from_account_data['balance'],
                        to_balance=to_account_data['balance'],
                        from_version=from_account_data['version'],
                        to_version=to_account_data['version'],
                        execution_time=time.time() - start_time
                    )
                
                ############################업데이트 부분 ############################
                new_from_balance = from_account_data['balance'] - request.amount
                new_to_balance = to_account_data['balance'] + request.amount
                
                # 낙관적락: UPDATE 시 version을 확인하여 충돌 감지
                # from_account 업데이트 (version 확인)
                # from_account의 버전 값이 우리 가 조회한 값과 같으면 버전업 하고 밸런스도 업데이트 해줘...
                from_update_result = await conn.execute(
                    "UPDATE accounts SET balance = $1, version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 AND version = $3",
                    new_from_balance, request.from_account, from_account_data['version']
                )
                
                # 업데이트된 행이 없으면 충돌 발생
                if from_update_result == "UPDATE 0":
                    return TransferResponse(
                        success=False,
                        message=f"동시성 충돌 감지 (출금 계좌) - 재시도 {attempt}회차",
                        from_balance=from_account_data['balance'],
                        to_balance=to_account_data['balance'],
                        from_version=from_account_data['version'],
                        to_version=to_account_data['version'],
                        execution_time=time.time() - start_time
                    )
                
                # to_account 업데이트 (version 확인)
                to_update_result = await conn.execute(
                    "UPDATE accounts SET balance = $1, version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 AND version = $3",
                    new_to_balance, request.to_account, to_account_data['version']
                )
                
                # 업데이트된 행이 없으면 충돌 발생
                if to_update_result == "UPDATE 0":
                    return TransferResponse(
                        success=False,
                        message=f"동시성 충돌 감지 (입금 계좌) - 재시도 {attempt}회차",
                        from_balance=from_account_data['balance'],
                        to_balance=to_account_data['balance'],
                        from_version=from_account_data['version'],
                        to_version=to_account_data['version'],
                        execution_time=time.time() - start_time
                    )
                
                # 성공 시 업데이트된 version 정보 포함
                return TransferResponse(
                    success=True,
                    message=f"이체가 성공했습니다. (재시도 {attempt}회차)",
                    from_balance=new_from_balance,
                    to_balance=new_to_balance,
                    from_version=from_account_data['version'] + 1,  # 업데이트된 version
                    to_version=to_account_data['version'] + 1,     # 업데이트된 version
                    execution_time=time.time() - start_time
                )
    
    async def initialize_accounts(self):
        """테스트를 위한 계좌 초기화 함수
        1. 기존 계좌값 전체 삭제
        2. 새로운 계좌 생성 & 초기화 값 입력
        account_a: 100000, account_b: 100000
        version: 0 (초기값)
        """
        async with get_optimistic_connection() as conn:
            # 기존 계좌 삭제
            await conn.execute("DELETE FROM accounts")
            
            # 새 계좌 생성 (version 0으로 초기화)
            await conn.execute(
                "INSERT INTO accounts (id, balance, version) VALUES ($1, $2, 0), ($3, $4, 0)",
                "account_a", self.initial_balances["account_a"],
                "account_b", self.initial_balances["account_b"]
            )
            
            return self.initial_balances
    
    async def get_balances(self):
        """현재 잔액 조회 (version 정보 포함)"""
        async with get_optimistic_connection() as conn:
            rows = await conn.fetch(
                "SELECT id, balance, version FROM accounts WHERE id IN ('account_a', 'account_b')"
            )
            
            balances = {}
            for row in rows:
                balances[row['id']] = {
                    "balance": row['balance'],
                    "version": row['version']
                }
            
            return balances 