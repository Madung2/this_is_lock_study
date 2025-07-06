import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor
import os

# 도커 환경 확인 (컨테이너 안에서는 app 서비스명 사용)
BASE_URL = "http://localhost:8000"

class ThreadSafeCounter:
    """쓰레드 안전한 카운터"""
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self._value += 1
    
    @property
    def value(self):
        return self._value

def test_docker_setup():
    """도커 환경 테스트"""
    print("🐳 도커 환경 테스트 시작!")
    
    try:
        # 1. 서버 연결 확인
        print("1. 서버 연결 확인...")
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"✅ 서버 응답: {response.status_code}")
        
        # 2. 잔액 확인
        print("\n2. 초기 잔액 확인...")
        response = requests.get(f"{BASE_URL}/pessimistic/balances", timeout=10)
        if response.status_code == 200:
            balances = response.json()['balances']
            print(f"✅ 초기 잔액: {balances}")
        else:
            print(f"❌ 잔액 조회 실패: {response.status_code}")
            return False
        
        # 3. 단일 이체 테스트
        print("\n3. 단일 이체 테스트...")
        response = requests.post(
            f"{BASE_URL}/pessimistic/transfer",
            json={
                "from_account": "account_a",
                "to_account": "account_b",
                "amount": 5000
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 이체 결과: {result['success']} - {result['message']}")
        else:
            print(f"❌ 이체 요청 실패: {response.status_code}")
            return False
        
        # 4. 이체 후 잔액 확인
        print("\n4. 이체 후 잔액 확인...")
        response = requests.get(f"{BASE_URL}/pessimistic/balances", timeout=10)
        if response.status_code == 200:
            balances = response.json()['balances']
            print(f"✅ 이체 후 잔액: {balances}")
        
        print("\n🎉 도커 환경 테스트 성공!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("다음 명령어로 서버를 실행하세요: docker-compose up")
        return False
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        return False

def simple_multithread_test():
    """간단한 멀티쓰레드 테스트"""
    print("\n🚀 멀티쓰레드 테스트 시작!")
    
    # 계좌 초기화
    print("계좌 초기화 중...")
    requests.post(f"{BASE_URL}/pessimistic/initialize", timeout=10)
    
    success_counter = ThreadSafeCounter()
    failure_counter = ThreadSafeCounter()
    
    def single_transfer(thread_id):
        try:
            response = requests.post(
                f"{BASE_URL}/pessimistic/transfer",
                json={
                    "from_account": "account_a",
                    "to_account": "account_b",
                    "amount": 10000
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    success_counter.increment()
                    print(f"✅ [쓰레드 {thread_id:2d}] 성공")
                else:
                    failure_counter.increment()
                    print(f"❌ [쓰레드 {thread_id:2d}] 실패: {result['message']}")
            else:
                failure_counter.increment()
                print(f"❌ [쓰레드 {thread_id:2d}] HTTP 오류: {response.status_code}")
                
        except Exception as e:
            failure_counter.increment()
            print(f"💥 [쓰레드 {thread_id:2d}] 예외: {e}")
    
    # 10개 쓰레드로 동시 실행
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(single_transfer, i + 1) for i in range(10)]
        for future in futures:
            future.result()
    
    end_time = time.time()
    
    # 결과 출력
    print(f"\n📊 테스트 결과:")
    print(f"총 요청: 10개")
    print(f"성공: {success_counter.value}")
    print(f"실패: {failure_counter.value}")
    print(f"총 시간: {end_time - start_time:.3f}초")
    
    # 최종 잔액 확인
    response = requests.get(f"{BASE_URL}/pessimistic/balances", timeout=10)
    if response.status_code == 200:
        balances = response.json()['balances']
        print(f"최종 잔액: {balances}")
        
        # 데이터 일관성 검증
        expected_a = 100000 - (success_counter.value * 10000)
        expected_b = 100000 + (success_counter.value * 10000)
        
        if balances['account_a'] == expected_a and balances['account_b'] == expected_b:
            print("✅ 데이터 일관성 유지!")
        else:
            print("❌ 데이터 일관성 문제!")

def main():
    print("🐳 도커 환경에서 은행 이체 시스템 테스트")
    print("=" * 50)
    
    # 기본 테스트
    if test_docker_setup():
        # 멀티쓰레드 테스트
        simple_multithread_test()
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main() 