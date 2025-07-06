# 간단한 은행계좌 이체 시스템

## 전체 시나리오
* 두 계좌 account_a, account_b 존재 (account_a: 100000원, account_b: 100000원)
* account_a 에서 account_b로 10000원을 이체하는 요청이 여러개 옴
* 이때 동시성 문제로 계좌 잔액이 틀어지지 않도록 락 방식 실험


### 시나리오1: 비관적락 
읽는 시점에 데이터 변경 있을 수 있다고 가정하고 읽는 시점에 데이터에 락을 거는 방법
따라서 속도가 느릴 수 있지만, 충돌 자체를 사전에 차단하는 방법.
은행이라던가... 데이터 일관성이 중요할때 사용.

* DB: Postgres
* db_name: pessimistic

### 시나리오2 : 낙관적락
왠만하면 충돌 나는 상황이 많지 않다고 가정하고, 
읽는 시점에는 락을 걸지 않음.
버전 칼럼으로 충돌이 난 경우를 감지해서 충돌이 나면 잠시 타임아웃 이후에 재시도.

* DB: Postgres
* db_name: optimistic

### 시나리오3: 분산락
비관적락은 for update가 같은 db 커넥션 안에서만 작동하기 때문에 분산 환경에 취약.
낙관적락은 충돌감지를 하더라도 서버b에서 작업중일때 서버a가 접근하는걸 막을 수단이 없음.
락의 권한을 db 레디스에 맞겨서 다른 서버에서 동시에 작업이 오더라도 락 가능


* lock_key = "transfer_lock:account_a" # 출금계좌 기준으로 락 생성. 
* lock_value = str(uuid.uuid4())

락키를 출금계좌 기준으로 잡아서 보내는 사람의 돈이 마이너스인데도 출금되는 상황 제외


* DB: redis (SETNX + TTL로 분산락 구현 쉬움)
| 이유       | 설명                                   |
| -------- | ------------------------------------ |
| ✅ 빠름     | In-memory라서 락 걸고 해제하는 속도가 **매우 빠름**  |
| ✅ 간단함    | `SET NX key value EX 5` 만으로도 락 구현 가능 |
| ✅ TTL 있음 | 락을 자동으로 풀 수 있어서 **영원히 걸리는 락 방지 가능**  |
| ✅ 널리 쓰임  | 인프라에 이미 Redis가 깔려 있는 경우가 많음          |

```
result = await redis.set(
    lock_key, 
    lock_value, 
    nx=True,  # not Exist = True => 레디스에 이 키가 없을때만 set
    ex=10  # Expire = 10초 뒤 자동 만료로 사라짐  
)
```



## 테스트 
* init: account_a: 100000원, account_b: 100000원
* 동시에 10개의 요청 * 10000 = 총 10만원 보냄
* 최종: account_a : 0원 , account_b = 20만원
* + 걸리는데 걸리는 시간 테스트

`fastapi` , `sql`, `postgres`, `redis` , `docker`


## 실행

* DB 초기화 값
