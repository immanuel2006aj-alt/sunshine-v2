from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    username: str
    password: str
    upi: str
    email: EmailStr          # mandatory
    usdt: str = ""           # optional, default empty

class LoginRequest(BaseModel):
    username: str
    password: str

class WithdrawRequest(BaseModel):
    user_id: str
