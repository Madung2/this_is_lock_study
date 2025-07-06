import asyncio
import time
from ..models import TransferRequest, TransferResponse
from ..database import get_pessimistic_connection

class PessimisticLockTransferService:
    def __init__(self):
        self.initial_balances = {
            "account_a": 100000,
            "account_b": 100000
        }
    
    @staticmethod
    async def transfer(request: TransferRequest) -> TransferResponse:
        start_time = time.time()
        
        async with get_pessimistic_connection() as conn:
            try:
                # 트랜잭션 시작
                async with conn.transaction(): # 트랜젝션 : 커밋하고 롤백 자동화
                    # 비관적락을 위한 SELECT FOR UPDATE 사용
                    # 계좌 순서를 정렬하여 데드락 방지 : 정렬안해두면 2개 요청이 동시에 accound_a와 account_b에 락을 걸었을때 데드락 발생
                    accounts = sorted([request.from_account, request.to_account])

                    ############################읽는부분############################        
                    # 첫 번째 계좌 잠금 # 업데이트를 할 수 있음을 가정하고 쿼리..
                    row1 = await conn.fetchrow(
                        "SELECT id, balance FROM accounts WHERE id = $1 FOR UPDATE",
                        accounts[0]
                    )
                    
                    # 두 번째 계좌 잠금
                    row2 = await conn.fetchrow(
                        "SELECT id, balance FROM accounts WHERE id = $1 FOR UPDATE",
                        accounts[1]
                    )
                    
                    if not row1 or not row2:
                        return TransferResponse(
                            success=False,
                            message="계좌를 찾을 수 없습니다.",
                            execution_time=time.time() - start_time
                        )
                    
                    # 실제 계좌 정보 구분
                    from_account_data = row1 if row1['id'] == request.from_account else row2
                    to_account_data = row1 if row1['id'] == request.to_account else row2
                    
                    # 잔액 확인
                    if from_account_data['balance'] < request.amount:
                        return TransferResponse(
                            success=False,
                            message="잔액이 부족합니다.",
                            from_balance=from_account_data['balance'],
                            to_balance=to_account_data['balance'],
                            execution_time=time.time() - start_time
                        )
                    
                    
                    ############################업데이트 부분############################
                    new_from_balance = from_account_data['balance'] - request.amount
                    new_to_balance = to_account_data['balance'] + request.amount
                    
                    await conn.execute(
                        "UPDATE accounts SET balance = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                        new_from_balance, request.from_account
                    )
                    
                    await conn.execute(
                        "UPDATE accounts SET balance = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                        new_to_balance, request.to_account
                    )
                    
                    return TransferResponse(
                        success=True,
                        message="이체가 성공했습니다.",
                        from_balance=new_from_balance,
                        to_balance=new_to_balance,
                        execution_time=time.time() - start_time
                    )
                    
            except Exception as e:
                return TransferResponse(
                    success=False,
                    message=f"이체 중 오류가 발생했습니다: {str(e)}",
                    execution_time=time.time() - start_time
                )



    async def initialize_accounts(self):
        """테스트를 위한 계좌 초기화 함수 반드시 아래 값이 나와야 함..
        1. 기존 계좌값 전체 삭제
        2. 새로운 계좌 생성 & 초기화 값 입력
        account_a: 100000, account_b: 100000
        """
        async with get_pessimistic_connection() as conn:
            # 기존 계좌 삭제
            await conn.execute("DELETE FROM accounts")
            
            # 새 계좌 생성
            await conn.execute(
                "INSERT INTO accounts (id, balance) VALUES ($1, $2), ($3, $4)",
                "account_a", self.initial_balances["account_a"],
                "account_b", self.initial_balances["account_b"]
            )
            
            return self.initial_balances
    
    async def get_balances(self):
        """현재 잔액 조회"""
        async with get_pessimistic_connection() as conn:
            rows = await conn.fetch(
                "SELECT id, balance FROM accounts WHERE id IN ('account_a', 'account_b')"
            )
            
            balances = {}
            for row in rows:
                balances[row['id']] = row['balance']
            
            return balances