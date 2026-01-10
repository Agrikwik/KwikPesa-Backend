import bcrypt
if not hasattr(bcrypt, "__about__"):
    class About:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = About()

# Now the rest of your imports
from passlib.context import CryptContext

import random
import smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.app_models import User, OTP
from app.models.auth_utils import verify_password, create_access_token, hash_password
from .schemas import UserCreate, LoginRequest, Token, ForgotPasswordRequest, ResetPasswordSubmit
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
from sqlalchemy import text
import resend
from pydantic import BaseModel


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "KWACHAPOINT_SUPER_SECRET_KEY_2026")
ALGORITHM = "HS256"
resend.api_key = os.getenv("RESEND_API_KEY")

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

def send_otp_email(target_email: str, otp_code: str):
    print(f"DEBUG: Attempting to send OTP {otp_code} to {target_email} via Resend API")

    try:
        params = {
            "from": "Kwikpesa <onboarding@resend.dev>",
            "to": [target_email],
            "subject": "Verify Your KwikPesa Account",
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                    <h2>Verify Your Account</h2>
                    <p>Your KwikPesa Verification Code is:</p>
                    <h1 style="color: #2b6cb0;">{otp_code}</h1>
                    <p>This code expires in 10 minutes.</p>
                </div>
            """,
        }

        email = resend.Emails.send(params)
        print(f"SUCCESS: Email sent! ID: {email['id']}")
        
    except Exception as e:
        print(f"ERROR: Resend API failed: {e}")

@router.post("/auth/register")
async def register_merchant(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        personal_phone=user_data.personal_phone,
        business_name=user_data.business_name,
        business_phone=user_data.business_phone,
        business_category=user_data.business_category,
        is_verified=False
    )
    db.add(new_user)
    
    otp_code = f"{random.randint(100000, 999999)}"
    new_otp = OTP(email=user_data.email, code=otp_code)
    db.add(new_otp)
    
    db.commit()

    background_tasks.add_task(send_otp_email, user_data.email, otp_code)

    return {"message": "OTP sent to email. Please verify to complete registration."}


"""
@router.post("/auth/verify-otp")
async def verify_otp(email: str, code: str, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(
        OTP.email == email, 
        OTP.code == code, 
        OTP.is_used == False
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = db.query(User).filter(User.email == email).first()
    user.is_verified = True
    
    otp_record.is_used = True
    
    db.commit()
    return {"message": "Account verified successfully. You can now login."}
"""

@router.post("/auth/verify-otp")
async def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    # 1. Search for the code
    otp_record = db.query(OTP).filter(
        OTP.email == payload.email, 
        OTP.code == payload.code, 
        OTP.is_used == False
    ).first()

    if not otp_record:
        print(f"FAILED VERIFY: No unused code {payload.code} found for {payload.email}")
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # 2. Find and update the user
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    otp_record.is_used = True
    
    db.commit()
    print(f"SUCCESS: {payload.email} is now verified.")
    return {"message": "Account verified successfully. You can now login."}


@router.post("/auth/login", response_model=Token)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Please verify your email before logging in."
        )

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
        return {"message": "If this email is registered, a reset code has been sent."}

    otp_code = f"{random.randint(100000, 999999)}"
    new_otp = OTP(email=payload.email, code=otp_code, purpose="password_reset")
    db.add(new_otp)
    db.commit()

    msg_content = f"Your KwikPesa Password Reset Code is: {otp_code}"
    background_tasks.add_task(send_otp_email, payload.email, otp_code)

    return {"message": "Reset OTP sent to email."}

@router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordSubmit, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(
        OTP.email == payload.email,
        OTP.code == payload.otp_code,
        OTP.purpose == "password_reset",
        OTP.is_used == False
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user = db.query(User).filter(User.email == payload.email).first()
    user.password_hash = hash_password(payload.new_password)
    
    otp_record.is_used = True
    
    db.commit()
    return {"message": "Password updated successfully. You can now login with your new password."}


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Decode the JWT Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if email is None or user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    # 2. Verify the merchant exists in the DB -- change users to merchants if it crashes --
    query = text("SELECT id, email, business_name FROM ledger.users WHERE id = :uid")
    user = db.execute(query, {"uid": user_id}).fetchone()
    
    if user is None:
        raise credentials_exception
        
    # 3. Return the user data to the route
    return {
        "user_id": user.id,
        "email": user.email,
        "business_name": user.business_name
    }


def cleanup_old_otps(email: str, db: Session):
    db.query(OTP).filter(OTP.email == email, OTP.is_used == False).update({"is_used": True})
    db.commit()