-- 여러 데이터베이스 생성
CREATE DATABASE pessimistic;
CREATE DATABASE optimistic;

-- 각 데이터베이스에 계정 테이블 생성
\c pessimistic;
CREATE TABLE accounts (
    id VARCHAR(50) PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

\c optimistic;
CREATE TABLE accounts (
    id VARCHAR(50) PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 초기 데이터 삽입 (pessimistic)
\c pessimistic;
INSERT INTO accounts (id, balance) VALUES ('account_a', 100000);
INSERT INTO accounts (id, balance) VALUES ('account_b', 100000);

-- 초기 데이터 삽입 (optimistic)
\c optimistic;
INSERT INTO accounts (id, balance) VALUES ('account_a', 100000);
INSERT INTO accounts (id, balance) VALUES ('account_b', 100000); 