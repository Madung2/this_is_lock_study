from fastapi import APIRouter
import asyncio
import time
from ..models import TransferRequest, TransferResponse
from ..scenarios.optimistic import OptimisticLockTransferService

# 낙관적락 전용 라우터 생성
router = APIRouter(
    prefix="/optimistic",
    tags=["Optimistic Lock"],
    responses={404: {"description": "Not found"}}
)

# 서비스 인스턴스 생성
service = OptimisticLockTransferService()

@router.post("/transfer", response_model=TransferResponse)
async def optimistic_transfer(request: TransferRequest):
    """낙관적락을 사용한 계좌 이체"""
    return await service.transfer(request)

@router.post("/initialize")
async def initialize_accounts():
    """계좌 초기화 (account_a: 100000, account_b: 100000)"""
    balances = await service.initialize_accounts()
    return {"message": "계좌가 초기화되었습니다.", "balances": balances}

@router.get("/balances")
async def get_balances():
    """현재 잔액 조회 (version 정보 포함)"""
    balances = await service.get_balances()
    return {"balances": balances}

@router.post("/stress-test")
async def stress_test():
    """스트레스 테스트: 10개의 동시 이체 요청 (각각 10000원)
    낙관적락 특성상 동시성 충돌이 발생할 수 있어 재시도 로직이 동작됩니다.
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
    
    # 재시도 통계
    retry_count = sum(1 for result in results if "재시도" in result.message)
    conflict_count = sum(1 for result in results if "충돌" in result.message)
    
    return {
        "message": "낙관적락 스트레스 테스트 완료",
        "total_requests": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "retry_count": retry_count,
        "conflict_count": conflict_count,
        "total_execution_time": total_time,
        "final_balances": final_balances,
        "expected_balances": {"account_a": {"balance": 0, "version": 10}, "account_b": {"balance": 200000, "version": 10}},
        "results": results
    }

@router.get("/info")
async def optimistic_info():
    """낙관적락 방식 정보"""
    return {
        "method": "Optimistic Lock",
        "database": "PostgreSQL", 
        "technique": "Version Column",
        "description": "데이터 변경 시점에 충돌을 감지하여 동시성 문제를 해결하는 방식",
        "status": "✅ 구현 완료",
        "features": [
            "Version 컬럼을 사용한 충돌 감지",
            "충돌 시 자동 재시도 (최대 5회)",
            "지수 백오프 재시도 전략",
            "락 대기 시간 없음"
        ],
        "pros": [
            "높은 처리량",
            "락 대기 시간 없음",
            "확장성 우수",
            "데드락 발생 없음"
        ],
        "cons": [
            "충돌 시 재시도 필요",
            "구현 복잡도 증가",
            "충돌률이 높으면 성능 저하",
            "재시도 로직 관리 필요"
        ]
    } 