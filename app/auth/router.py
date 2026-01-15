import random
import os
import resend
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt

# Internal Imports
from app.api.deps import get_db
from app.models.app_models import User, OTP
from app.models.auth_utils import verify_password, create_access_token, hash_password
from .schemas import UserCreate, LoginRequest, Token, VerifyOTPRequest, ForgotPasswordRequest, ResetPasswordSubmit

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Environment Variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
resend.api_key = os.getenv("RESEND_API_KEY")

# --- EMAIL LOGIC ---
def send_otp_email(target_email: str, otp_code: str, subject: str):
    """Sends a branded HTML email via Resend."""
    try:
        resend.Emails.send({
            "from": "KwikPesa <chikusehopeson@gmail.com>", # Update this after domain verification
            "to": [target_email],
            "subject": subject,
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px; max-width: 500px; margin: auto;">
                    <h2 style="color: #2b6cb0; text-align: center;">KwikPesa Security</h2>
                    <p>Hello,</p>
                    <p>Use the code below to verify your account. It will expire in 10 minutes:</p>
                    <div style="background: #f7fafc; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <h1 style="letter-spacing: 8px; font-size: 32px; color: #1a202c; margin: 0;">{otp_code}</h1>
                    </div>
                    <p style="font-size: 12px; color: #718096; text-align: center;">
                        If you did not request this code, please ignore this email or contact support.
                    </p>
                </div>
            """
        })
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to send email to {target_email}: {e}")

# --- ROUTES ---

@router.post("/auth/register")
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Prevent duplicate emails
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create unverified user
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
    
    # 3. Generate OTP
    otp_code = f"{random.randint(100000, 999999)}"
    db.add(OTP(email=user_data.email, code=otp_code))
    
    db.commit()
    
    # 4. Background Email
    background_tasks.add_task(send_otp_email, user_data.email, otp_code, "Welcome to KwikPesa - Verify Your Account")
    
    return {"message": "Registration successful. OTP sent.", "email": user_data.email}

@router.post("/auth/login")
async def login(payload: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate Login OTP
    otp_code = f"{random.randint(100000, 999999)}"
    
    # Clear old OTPs for this user and save new one
    db.query(OTP).filter(OTP.email == user.email).delete()
    db.add(OTP(email=user.email, code=otp_code))
    db.commit()

    background_tasks.add_task(send_otp_email, user.email, otp_code, "Your Login Verification Code")

    return {"message": "OTP sent", "email": user.email}

@router.post("/auth/verify-otp-login", response_model=Token)
async def verify_otp_login(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(
        OTP.email == payload.email, 
        OTP.code == payload.code, 
        OTP.is_used == False
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = db.query(User).filter(User.email == payload.email).first()
    
    # Successful verification
    otp_record.is_used = True
    user.is_verified = True 
    db.commit()

    # Issue JWT Token
    access_token = create_access_token(data={
        "sub": user.email, 
        "role": user.role,
        "user_id": str(user.id)
    })

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # For security, don't confirm if email exists or not
        return {"message": "If this email exists, a reset code has been sent."}

    otp_code = f"{random.randint(100000, 999999)}"
    
    # Update or create OTP record
    db.query(OTP).filter(OTP.email == user.email).delete()
    db.add(OTP(email=user.email, code=otp_code))
    db.commit()

    background_tasks.add_task(send_otp_email, user.email, otp_code, "Reset Your KwikPesa Password")
    
    return {"message": "Reset code sent to your email."}

@router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordSubmit, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(
        OTP.email == payload.email, 
        OTP.code == payload.code, 
        OTP.is_used == False
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update password and mark OTP as used
    user.password_hash = hash_password(payload.new_password)
    otp_record.is_used = True
    db.commit()

    return {"message": "Password updated successfully. You can now login."}


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    # Fetch user from DB
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
        
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified")
        
    return user