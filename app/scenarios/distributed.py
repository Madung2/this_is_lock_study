import asyncio
import time
import uuid
from ..models import TransferRequest, TransferResponse
from ..database import get_redis_client, get_distributed_connection

class DistributedLockTransferService:
    def __init__(self):
        self.initial_balances = {
            "account_a": 100000,
            "account_b": 100000
        }
        self.lock_timeout = 10  # 락 타임아웃 (초)
        self.max_retries = 50   # 락 획득 재시도 횟수
        self.retry_delay = 0.1  # 재시도 간격 (초)
    
    async def transfer(self, request: TransferRequest) -> TransferResponse:
        """Redis 분산락을 사용한 계좌 이체"""
        start_time = time.time()
        
        # 락 키 생성 (계좌 순서 정렬로 데드락 방지)
        accounts = sorted([request.from_account, request.to_account])
        lock_key = f"transfer_lock:{accounts[0]}" # 출금계좌 기준으로 락 생성. 
        lock_value = str(uuid.uuid4())  # 고유한 락 값
        
        # 락 획득 시도
        lock_acquired = await self._acquire_lock(lock_key, lock_value)
        if not lock_acquired:
            return TransferResponse(
                success=False,
                message=f"락 획득 실패: 다른 이체 작업이 진행 중입니다. (최대 {self.max_retries}회 재시도)",
                execution_time=time.time() - start_time
            )
        
        try:
            # 락 획득 성공 후 이체 로직 수행
            return await self._perform_transfer(request, start_time)
        finally:
            # 락 해제
            await self._release_lock(lock_key, lock_value)
    
    async def _acquire_lock(self, lock_key: str, lock_value: str) -> bool:
        """Redis 분산락 획득"""
        redis = await get_redis_client()
        
        for attempt in range(self.max_retries):
            # SET key value NX EX seconds: 키가 존재하지 않으면 설정하고 만료시간 설정
            result = await redis.set(
                lock_key, 
                lock_value, 
                nx=True,  # not Exist = True => 레디스에 이 키가 없을때만 set
                ex=self.lock_timeout  # Expire = 10초
                
            )
            
            if result:  # 락 획득 성공
                return True
            
            # 락 획득 실패 시 잠시 대기 후 재시도
            await asyncio.sleep(self.retry_delay)
        
        return False  # 최대 재시도 횟수 초과
    
    async def _release_lock(self, lock_key: str, lock_value: str):
        """ 락 해제"""
        redis = await get_redis_client()
        
        try:
            # 1. 현재 값 확인
            current_value = await redis.get(lock_key)
            
            # 2. 자신이 설정한 락인지 확인
            if current_value == lock_value:
                # 3. 락 삭제
                await redis.delete(lock_key)
                print(f"락 해제 성공: {lock_key}")
            else:
                print(f"다른 락 값, 해제하지 않음: {lock_key}")
                
        except Exception as e:
            print(f"락 해제 실패: {e}")
    
    async def _perform_transfer(self, request: TransferRequest, start_time: float) -> TransferResponse:
        """실제 이체 로직 수행 (락 보호 하에서 실행)"""
        async with get_distributed_connection() as conn:
            try:
                # 트랜잭션 시작
                async with conn.transaction():
                    ############################읽는부분############################
                    # 분산락으로 보호되므로 일반 SELECT 사용
                    from_account_data = await conn.fetchrow(
                        "SELECT id, balance FROM accounts WHERE id = $1",
                        request.from_account
                    )
                    
                    to_account_data = await conn.fetchrow(
                        "SELECT id, balance FROM accounts WHERE id = $1",
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
                            execution_time=time.time() - start_time
                        )
                    
                    ############################업데이트 부분############################
                    new_from_balance = from_account_data['balance'] - request.amount
                    new_to_balance = to_account_data['balance'] + request.amount
                    
                    # 분산락으로 보호되므로 일반 UPDATE 사용
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
                        message="이체가 성공했습니다. (Redis 분산락 사용 - Python 방식)",
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
        """테스트를 위한 계좌 초기화 함수
        1. 기존 계좌값 전체 삭제
        2. 새로운 계좌 생성 & 초기화 값 입력
        account_a: 100000, account_b: 100000
        """
        async with get_distributed_connection() as conn:
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
        async with get_distributed_connection() as conn:
            rows = await conn.fetch(
                "SELECT id, balance FROM accounts WHERE id IN ('account_a', 'account_b')"
            )
            
            balances = {}
            for row in rows:
                balances[row['id']] = row['balance']
            
            return balances
    
    async def get_lock_info(self):
        """현재 락 상태 조회 (디버깅용)"""
        redis = await get_redis_client()
        
        # 모든 transfer_lock 키 조회
        lock_keys = await redis.keys("transfer_lock:*")
        
        lock_info = {}
        for key in lock_keys:
            ttl = await redis.ttl(key)
            value = await redis.get(key)
            lock_info[key] = {
                "value": value,
                "ttl": ttl
            }
        
        return lock_info 