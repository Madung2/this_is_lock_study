from fastapi import APIRouter
import asyncio
import time
from ..models import TransferRequest, TransferResponse
from ..scenarios.pessimistic import PessimisticLockTransferService

# 비관적락 전용 라우터 생성
router = APIRouter(
    prefix="/pessimistic",
    tags=["Pessimistic Lock"],
    responses={404: {"description": "Not found"}}
)

# 서비스 인스턴스 생성
service = PessimisticLockTransferService()

@router.post("/transfer", response_model=TransferResponse)
async def pessimistic_transfer(request: TransferRequest):
    """비관적락을 사용한 계좌 이체"""
    return await PessimisticLockTransferService.transfer(request)

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

@router.post("/stress-test")
async def stress_test():
    """스트레스 테스트: 10개의 동시 이체 요청 (각각 10000원)
    일반 for 문으로 실행....
    최종 잔액 확인
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
        task = PessimisticLockTransferService.transfer(request)
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
    
    return {
        "message": "스트레스 테스트 완료",
        "total_requests": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "total_execution_time": total_time,
        "final_balances": final_balances,
        "expected_balances": {"account_a": 0, "account_b": 200000},
        "results": results
    }

@router.get("/info")
async def pessimistic_info():
    """비관적락 방식 정보"""
    return {
        "method": "Pessimistic Lock",
        "database": "PostgreSQL",
        "technique": "SELECT FOR UPDATE",
        "description": "데이터를 읽을 때 미리 락을 걸어서 동시성 문제를 해결하는 방식",
        "pros": [
            "데이터 일관성 보장",
            "데드락 위험이 상대적으로 낮음",
            "구현이 간단함"
        ],
        "cons": [
            "성능 저하 가능성",
            "대기 시간 발생",
            "처리량 감소"
        ]
    } 