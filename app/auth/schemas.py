from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    personal_phone: str
    business_name: Optional[str] = None
    business_phone: Optional[str] = None
    business_category: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordSubmit(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str