from pydantic import BaseModel
from typing import Optional

class TransferRequest(BaseModel):
    from_account: str = "account_a"
    to_account: str = "account_b"
    amount: int = 10000

class TransferResponse(BaseModel):
    success: bool
    message: str
    from_balance: Optional[int] = None
    to_balance: Optional[int] = None
    from_version: Optional[int] = None  # 낙관적락용 - 출금 계좌 버전
    to_version: Optional[int] = None    # 낙관적락용 - 입금 계좌 버전
    execution_time: Optional[float] = None

class AccountBalance(BaseModel):
    account_id: str
    balance: int 