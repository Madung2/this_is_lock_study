from fastapi import APIRouter
import asyncio
import time
from ..models import TransferRequest, TransferResponse
from ..scenarios.distributed import DistributedLockTransferService

# 분산락 전용 라우터 생성
router = APIRouter(
    prefix="/distributed",
    tags=["Distributed Lock (Redis)"],
    responses={404: {"description": "Not found"}}
)

# 서비스 인스턴스 생성
service = DistributedLockTransferService()

@router.post("/transfer", response_model=TransferResponse)
async def distributed_transfer(request: TransferRequest):
    """Redis 분산락을 사용한 계좌 이체"""
    return await service.transfer(request)

@router.post("/initialize")
async def initialize_accounts():
    """계좌 초기화 (account_a: 100000, account_b: 100000)"""
    balances = await service.initialize_accounts()
    return {"message": "계좌가 초기화되었습니다.", "balances": balances}

@router.get("/balances")
async def get_balances():
    """현재 잔액 조회"""
    balances = await service.get_balances()
    return {"balances": balances}

@router.get("/lock-info")
async def get_lock_info():
    """현재 Redis 락 상태 조회 (디버깅용)"""
    lock_info = await service.get_lock_info()
    return {
        "message": "현재 Redis 락 상태",
        "locks": lock_info,
        "lock_count": len(lock_info)
    }

@router.post("/stress-test")
async def stress_test():
    """스트레스 테스트: 10개의 동시 이체 요청 (각각 10000원)
    Redis 분산락으로 동시성 제어
    최종 잔액 확인:
    account_a: 0원
    account_b: 200000원
    """
    
    # 먼저 계좌 초기화
    await service.initialize_accounts()
    
    # 10개의 동시 이체 요청 생성
    tasks = []
    for i in range(10):
        request = TransferRequest(
            from_account="account_a",
            to_account="account_b",
            amount=10000
        )
        task = service.transfer(request)
        tasks.append(task)
    
    # 시작 시간 기록
    start_time = time.time()
    
    # 모든 이체 요청을 동시에 실행
    results = await asyncio.gather(*tasks)
    
    # 총 실행 시간 계산
    total_time = time.time() - start_time
    
    # 최종 잔액 확인
    final_balances = await service.get_balances()
    
    # 성공/실패 통계
    success_count = sum(1 for result in results if result.success)
    failed_count = len(results) - success_count
    
    # 락 관련 통계
    lock_failure_count = sum(1 for result in results if "락 획득 실패" in result.message)
    
    # 최종 락 상태 확인
    final_lock_info = await service.get_lock_info()
    
    return {
        "message": "Redis 분산락 스트레스 테스트 완료",
        "total_requests": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "lock_failure_count": lock_failure_count,
        "total_execution_time": total_time,
        "final_balances": final_balances,
        "expected_balances": {"account_a": 0, "account_b": 200000},
        "final_lock_count": len(final_lock_info),
        "results": results
    }

@router.get("/info")
async def distributed_info():
    """Redis 분산락 방식 정보"""
    return {
        "method": "Distributed Lock",
        "technology": "Redis",
        "technique": "SET NX EX (Redis Atomic Operations)",
        "description": "Redis를 사용한 분산락으로 동시성 문제를 해결하는 방식",
        "status": "✅ 구현 완료",
    } 