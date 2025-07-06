import requests
import os

# 환경 변수에서 API URL 가져오기 (도커 환경 대응)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def test_transfer(lock_type="pessimistic", amount=10000):
    """단일 이체 테스트"""
    
    # API 엔드포인트 선택
    endpoints = {
        "pessimistic": f"{API_BASE_URL}/pessimistic/transfer",
        "optimistic": f"{API_BASE_URL}/optimistic/transfer", 
        "distributed": f"{API_BASE_URL}/distributed/transfer"
    }
    
    try:
        # 이체 요청
        response = requests.post(
            endpoints[lock_type],
            json={
                "from_account": "account_a",
                "to_account": "account_b", 
                "amount": amount
            },
            timeout=30
        )
        
        result = response.json()
        print(f"결과: {result}")
        return result
        
    except Exception as e:
        print(f"오류: {e}")
        return None

def initialize_accounts(lock_type="pessimistic"):
    """계좌 초기화"""
    endpoints = {
        "pessimistic": f"{API_BASE_URL}/pessimistic/initialize",
        "optimistic": f"{API_BASE_URL}/optimistic/initialize",
        "distributed": f"{API_BASE_URL}/distributed/initialize"
    }
    
    try:
        response = requests.post(endpoints[lock_type])
        print(f"계좌 초기화 완료")
        return True
    except Exception as e:
        print(f"계좌 초기화 실패: {e}")
        return False

def check_balances(lock_type="pessimistic"):
    """잔액 확인"""
    endpoints = {
        "pessimistic": f"{API_BASE_URL}/pessimistic/balances",
        "optimistic": f"{API_BASE_URL}/optimistic/balances", 
        "distributed": f"{API_BASE_URL}/distributed/balances"
    }
    
    try:
        response = requests.get(endpoints[lock_type])
        balances = response.json()['balances']
        print(f"잔액: {balances}")
        return balances
    except Exception as e:
        print(f"잔액 조회 실패: {e}")
        return None

if __name__ == "__main__":
    # 간단한 테스트
    lock_type = "distributed"  # pessimistic, optimistic, distributed 중 선택
    
    print(f"=== {lock_type} 락 테스트 ===")
    
    # 1. 계좌 초기화
    initialize_accounts(lock_type)
    
    # 2. 초기 잔액 확인
    print("\n초기 잔액:")
    check_balances(lock_type)
    
    # 3. 이체 테스트
    print(f"\n{10000}원 이체 테스트:")
    test_transfer(lock_type, 10000)
    
    # 4. 최종 잔액 확인
    print("\n최종 잔액:")
    check_balances(lock_type) 