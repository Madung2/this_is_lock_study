import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor
import json

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

# 결과 수집용 카운터
success_counter = ThreadSafeCounter()
failure_counter = ThreadSafeCounter()
results = []
results_lock = threading.Lock()

def single_transfer_request(thread_id, amount=10000):
    """단일 이체 요청 함수"""
    try:
        start_time = time.time()
        
        # HTTP 요청
        response = requests.post(
            "http://localhost:8000/pessimistic/transfer",
            json={
                "from_account": "account_a",
                "to_account": "account_b", 
                "amount": amount
            },
            timeout=30
        )
        
        end_time = time.time()
        result = response.json()
        
        # 결과 저장
        with results_lock:
            results.append({
                "thread_id": thread_id,
                "success": result.get('success', False),
                "message": result.get('message', ''),
                "duration": end_time - start_time,
                "amount": amount
            })
        
        if result.get('success'):
            success_counter.increment()
            print(f"✅ [쓰레드 {thread_id:2d}] 성공: {amount:,}원 이체 ({end_time - start_time:.3f}초)")
        else:
            failure_counter.increment()
            print(f"❌ [쓰레드 {thread_id:2d}] 실패: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        failure_counter.increment()
        print(f"💥 [쓰레드 {thread_id:2d}] 예외: {str(e)}")

def test_with_threading_module():
    """기본 threading 모듈 사용"""
    print("=== 기본 threading 모듈 테스트 ===")
    
    # 계좌 초기화
    requests.post("http://localhost:8000/pessimistic/initialize")
    
    # 결과 초기화
    global results
    results = []
    success_counter._value = 0
    failure_counter._value = 0
    
    # 10개 쓰레드 생성 및 실행
    threads = []
    start_time = time.time()
    
    for i in range(10):
        thread = threading.Thread(
            target=single_transfer_request,
            args=(i + 1, 10000)
        )
        threads.append(thread)
        thread.start()
    
    # 모든 쓰레드 완료 대기
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    print(f"\n📊 결과:")
    print(f"성공: {success_counter.value}")
    print(f"실패: {failure_counter.value}")
    print(f"총 시간: {end_time - start_time:.3f}초")
    
    # 잔액 확인
    response = requests.get("http://localhost:8000/pessimistic/balances")
    balances = response.json()['balances']
    print(f"최종 잔액: {balances}")

def test_with_thread_pool():
    """ThreadPoolExecutor 사용"""
    print("\n=== ThreadPoolExecutor 테스트 ===")
    
    # 계좌 초기화
    requests.post("http://localhost:8000/pessimistic/initialize")
    
    # 결과 초기화
    global results
    results = []
    success_counter._value = 0
    failure_counter._value = 0
    
    start_time = time.time()
    
    # 쓰레드 풀 사용
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 다양한 금액으로 테스트
        amounts = [5000, 10000, 15000, 20000, 25000]
        
        # Future 객체 생성
        futures = []
        for i in range(10):
            amount = amounts[i % len(amounts)]
            future = executor.submit(single_transfer_request, i + 1, amount)
            futures.append(future)
        
        # 모든 작업 완료 대기
        for future in futures:
            future.result()  # 예외 발생 시 여기서 처리
    
    end_time = time.time()
    
    print(f"\n📊 결과:")
    print(f"성공: {success_counter.value}")
    print(f"실패: {failure_counter.value}")
    print(f"총 시간: {end_time - start_time:.3f}초")
    
    # 상세 결과 분석
    if results:
        avg_duration = sum(r['duration'] for r in results) / len(results)
        print(f"평균 응답 시간: {avg_duration:.3f}초")
        
        successful_transfers = [r for r in results if r['success']]
        if successful_transfers:
            total_amount = sum(r['amount'] for r in successful_transfers)
            print(f"총 이체 금액: {total_amount:,}원")
    
    # 잔액 확인
    response = requests.get("http://localhost:8000/pessimistic/balances")
    balances = response.json()['balances']
    print(f"최종 잔액: {balances}")

def stress_test_with_many_threads():
    """많은 쓰레드로 스트레스 테스트"""
    print("\n=== 고강도 스트레스 테스트 (50개 쓰레드) ===")
    
    # 계좌 초기화
    requests.post("http://localhost:8000/pessimistic/initialize")
    
    # 결과 초기화
    global results
    results = []
    success_counter._value = 0
    failure_counter._value = 0
    
    start_time = time.time()
    
    # 50개 쓰레드로 테스트
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(50):
            future = executor.submit(single_transfer_request, i + 1, 2000)  # 2천원씩
            futures.append(future)
        
        # 모든 작업 완료 대기
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Future 오류: {e}")
    
    end_time = time.time()
    
    print(f"\n📊 고강도 테스트 결과:")
    print(f"총 요청: 50개")
    print(f"성공: {success_counter.value}")
    print(f"실패: {failure_counter.value}")
    print(f"성공률: {(success_counter.value / 50) * 100:.1f}%")
    print(f"총 시간: {end_time - start_time:.3f}초")
    print(f"초당 처리량: {50 / (end_time - start_time):.1f} requests/sec")
    
    # 잔액 확인
    response = requests.get("http://localhost:8000/pessimistic/balances")
    balances = response.json()['balances']
    expected_a = 100000 - (success_counter.value * 2000)
    expected_b = 100000 + (success_counter.value * 2000)
    
    print(f"최종 잔액: {balances}")
    print(f"예상 잔액: account_a={expected_a:,}, account_b={expected_b:,}")
    
    if balances['account_a'] == expected_a and balances['account_b'] == expected_b:
        print("✅ 데이터 일관성 유지됨!")
    else:
        print("❌ 데이터 일관성 문제 발생!")

def main():
    """메인 함수"""
    print("🚀 멀티쓰레드 테스트 시작!")
    print("서버가 실행중인지 확인하세요: http://localhost:8000")
    
    try:
        # 서버 연결 확인
        response = requests.get("http://localhost:8000/", timeout=5)
        print("✅ 서버 연결 확인")
        
        # 1. 기본 쓰레딩 테스트
        test_with_threading_module()
        
        # 2. 쓰레드 풀 테스트
        test_with_thread_pool()
        
        # 3. 고강도 스트레스 테스트
        stress_test_with_many_threads()
        
        print("\n🎉 모든 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("다음 명령어로 서버를 실행하세요: python run.py")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    main() 