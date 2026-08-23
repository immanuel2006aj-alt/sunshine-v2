from pydantic import BaseModel

class SignupRequest(BaseModel):
    username: str
    password: str
    upi: str
    usdt: str

class LoginRequest(BaseModel):
    username: str
    password: str

class WithdrawRequest(BaseModel):
    user_id: str
