import bcrypt
if not hasattr(bcrypt, "__about__"):
    class About:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = About()

import random
import os
import resend
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.app_models import User, OTP
from app.models.auth_utils import verify_password, create_access_token, hash_password
from .schemas import UserCreate, LoginRequest, Token, ForgotPasswordRequest, ResetPasswordSubmit

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "KWACHAPOINT_SUPER_SECRET_KEY_2026")
ALGORITHM = "HS256"
resend.api_key = os.getenv("RESEND_API_KEY")

# --- Schemas ---
class VerifyOTPRequest(BaseModel):
    email: str
    code: str

# --- Helpers ---
def send_otp_email(target_email: str, otp_code: str, subject: str = "Verify Your KwikPesa Account"):
    print(f"DEBUG: Attempting to send OTP {otp_code} to {target_email}")
    try:
        resend.Emails.send({
            "from": "Kwikpesa <onboarding@resend.dev>",
            "to": [target_email],
            "subject": subject,
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #2b6cb0;">KwikPesa Security</h2>
                    <p>Your verification code is:</p>
                    <h1 style="letter-spacing: 5px; background: #f7fafc; padding: 10px; text-align: center;">{otp_code}</h1>
                    <p>This code expires in 10 minutes. If you did not request this, please ignore this email.</p>
                </div>
            """
        })
    except Exception as e:
        print(f"ERROR: Resend API failed: {e}")

# --- Routes ---

@router.post("/auth/register")
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        personal_phone=user_data.personal_phone,
        business_name=user_data.business_name,
        business_phone=user_data.business_phone,
        business_category=user_data.business_category,
        role="merchant",
        is_verified=False
    )
    db.add(new_user)
    
    otp_code = f"{random.randint(100000, 999999)}"
    db.add(OTP(email=user_data.email, code=otp_code))
    
    db.commit()
    background_tasks.add_task(send_otp_email, user_data.email, otp_code)
    return {"message": "Registration successful. Please check your email for the OTP."}

@router.post("/auth/verify-otp")
async def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(OTP.email == payload.email, OTP.code == payload.code, OTP.is_used == False).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    otp_record.is_used = True
    db.commit()
    
    return {"message": "Account verified. You can now login."}

@router.post("/auth/login", response_model=Token)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first.")

    access_token = create_access_token(data={
        "sub": user.email, 
        "role": user.role,
        "user_id": str(user.id)
    })

    return {"access_token": access_token, "token_type": "bearer"}

# --- Dependency for Protected Routes ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # SMART QUERY: Look in the Unified Table
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
        
    return user