from fastapi import FastAPI
from .views import pessimistic, optimistic
from .models import TransferRequest, TransferResponse

app = FastAPI(
    title="은행계좌 이체 시스템 - 동시성 테스트",
    description="비관적락과 낙관적락을 사용한 동시성 문제 해결 비교 시스템",
    version="1.0.0"
)

# 라우터 등록
app.include_router(pessimistic.router)
app.include_router(optimistic.router)

@app.get("/")
async def root():
    """메인 페이지"""
    return {
        "message": "은행계좌 이체 시스템 - 동시성 테스트",
        "version": "1.0.0",
        "available_methods": [
            "/pessimistic - 비관적락 방식",
            "/optimistic - 낙관적락 방식 (구현 예정)"
        ],
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "healthy"} 