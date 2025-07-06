import asyncio
import httpx
import time

async def test_pessimistic_lock():
    """비관적락 테스트"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("=== 비관적락 테스트 시작 ===")
        
        # 1. 계좌 초기화
        print("1. 계좌 초기화 중...")
        response = await client.post(f"{base_url}/pessimistic/initialize")
        print(f"초기화 결과: {response.json()}")
        
        # 2. 초기 잔액 확인
        print("\n2. 초기 잔액 확인...")
        response = await client.get(f"{base_url}/pessimistic/balances")
        print(f"초기 잔액: {response.json()}")
        
        # 3. 단일 이체 테스트
        print("\n3. 단일 이체 테스트...")
        transfer_data = {
            "from_account": "account_a",
            "to_account": "account_b",
            "amount": 10000
        }
        response = await client.post(f"{base_url}/pessimistic/transfer", json=transfer_data)
        print(f"이체 결과: {response.json()}")
        
        # 4. 잔액 확인
        print("\n4. 이체 후 잔액 확인...")
        response = await client.get(f"{base_url}/pessimistic/balances")
        print(f"이체 후 잔액: {response.json()}")
        
        # 5. 스트레스 테스트
        print("\n5. 스트레스 테스트 (10개 동시 이체)...")
        start_time = time.time()
        response = await client.post(f"{base_url}/pessimistic/stress-test")
        end_time = time.time()
        
        result = response.json()
        print(f"스트레스 테스트 완료!")
        print(f"총 요청 수: {result['total_requests']}")
        print(f"성공 수: {result['success_count']}")
        print(f"실패 수: {result['failed_count']}")
        print(f"총 실행 시간: {result['total_execution_time']:.3f}초")
        print(f"최종 잔액: {result['final_balances']}")
        print(f"예상 잔액: {result['expected_balances']}")
        
        # 6. 정확성 검증
        print("\n6. 정확성 검증...")
        final_balances = result['final_balances']
        expected_balances = result['expected_balances']
        
        if (final_balances['account_a'] == expected_balances['account_a'] and 
            final_balances['account_b'] == expected_balances['account_b']):
            print("✅ 테스트 성공! 동시성 문제가 해결되었습니다.")
        else:
            print("❌ 테스트 실패! 동시성 문제가 발생했습니다.")
            print(f"실제 잔액: {final_balances}")
            print(f"예상 잔액: {expected_balances}")

if __name__ == "__main__":
    asyncio.run(test_pessimistic_lock()) 