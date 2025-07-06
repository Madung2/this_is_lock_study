import asyncpg
import os
from typing import Optional
from contextlib import asynccontextmanager

# 환경 변수에서 데이터베이스 URL 가져오기
PESSIMISTIC_DATABASE_URL = os.getenv(
    "PESSIMISTIC_DATABASE_URL", 
    "postgresql://postgres:password@postgres:5432/pessimistic"
) 
OPTIMISTIC_DATABASE_URL = os.getenv(
    "OPTIMISTIC_DATABASE_URL", 
    "postgresql://postgres:password@postgres:5432/optimistic"
)

class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def init_pool(self):
        """커넥션 풀 초기화"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10
            )
    
    async def close_pool(self):
        """커넥션 풀 종료"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    @asynccontextmanager
    async def get_connection(self):
        """커넥션 가져오기"""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            yield conn
    
    async def initialize_db(self):
        """데이터베이스 초기화 (테이블 생성)"""
        if self._initialized:
            return
        
        async with self.get_connection() as conn:
            # 테이블 생성
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id VARCHAR(50) PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 초기 데이터가 없으면 생성
            count = await conn.fetchval("SELECT COUNT(*) FROM accounts")
            if count == 0:
                await conn.execute("""
                    INSERT INTO accounts (id, balance) VALUES 
                    ('account_a', 100000),
                    ('account_b', 100000)
                """)
        
        self._initialized = True

# 전역 데이터베이스 인스턴스들
pessimistic_db = Database(PESSIMISTIC_DATABASE_URL)
optimistic_db = Database(OPTIMISTIC_DATABASE_URL)

# 비관적락 전용 헬퍼 함수
@asynccontextmanager
async def get_pessimistic_connection():
    """비관적락 데이터베이스 커넥션 가져오기"""
    await pessimistic_db.initialize_db()
    async with pessimistic_db.get_connection() as conn:
        yield conn

# 낙관적락 전용 헬퍼 함수
@asynccontextmanager
async def get_optimistic_connection():
    """낙관적락 데이터베이스 커넥션 가져오기"""
    await optimistic_db.initialize_db()
    async with optimistic_db.get_connection() as conn:
        yield conn 