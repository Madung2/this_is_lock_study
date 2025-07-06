# 간단한 은행계좌 이체 시스템

## 시나리오
* 두 계좌 account_a, account_b 존재
* account_a 에서 account_b로 10000원을 이체하는 요청이 여러개 옴
* 이때 동시성 문제로 계좌 잔액이 틀어지지 않도록 락 방식 실험


### 시나리오1: 비관적락 
읽는 시점에 데이터 변경 있을 수 있다고 가정하고 읽는 시점에 데이터에 락을 거는 방법
따라서 속도가 느릴 수 있지만, 충돌 자체를 사전에 차단하는 방법.
은행이라던가... 데이터 일관성이 중요할때 사용.

* DB: Postgres
* db_name: pessimistic

### 시나리오2 : 낙관적락
* DB: Postgres
* db_name: optimistic

### 시나리오3: 낙관적락
* DB: redis




## 테스트 
* init: account_a: 100000원, account_b: 100000원
* 동시에 10개의 요청 * 10000 = 총 10만원 보냄
* 최종: account_a : 0원 , account_b = 20만원
* + 걸리는데 걸리는 시간 테스트

`fastapi` , `sql`, `postgres`, `redis` , `docker`


## 실행

* DB 초기화 값
