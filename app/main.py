from fastapi import FastAPI
from .views import pessimistic, optimistic, distributed
from .models import TransferRequest, TransferResponse

app = FastAPI(
    title="은행계좌 이체 시스템 - 동시성 테스트",
    description="비관적락, 낙관적락, 분산락을 사용한 동시성 문제 해결 비교 시스템",
    version="1.0.0"
)

# 라우터 등록
app.include_router(pessimistic.router)
app.include_router(optimistic.router)
app.include_router(distributed.router)

@app.get("/")
async def root():
    """메인 페이지"""
    return {
        "message": "은행계좌 이체 시스템 - 동시성 테스트",
        "version": "1.0.0",
        "available_methods": [
            "/pessimistic - 비관적락 방식 (PostgreSQL SELECT FOR UPDATE)",
            "/optimistic - 낙관적락 방식 (PostgreSQL Version Column)",
            "/distributed - 분산락 방식 (Redis SET NX EX)"
        ],
        "comparison": {
            "pessimistic": "데이터를 읽을 때 미리 락을 걸어서 충돌 방지",
            "optimistic": "데이터 변경 시점에 버전을 확인하여 충돌 감지",
            "distributed": "Redis를 사용한 애플리케이션 레벨의 분산락"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "healthy"} 