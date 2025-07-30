from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from inai_project.app.signup import models as signup_models
from inai_project.app.signup.models import User
from inai_project.database import SessionLocal
from inai_project.app.core.security import create_access_token, verify_password
from . import schemas
from inai_project.app.login import models as login_models
from inai_project.app.core.email_utils import send_email_otp
from datetime import datetime, timedelta
import random
from inai_project.app.core.oauth_utils import get_email_from_google_token, get_email_from_facebook_token
from inai_project.app.core.error_handler import (
    InvalidCredentialsException,
    EmailNotVerifiedException,
)
from inai_project.app.login.schemas import LoginRequest
from pydantic import BaseModel, EmailStr


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ✅ Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Login route
@router.post("/login/")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    login_method = None
    user = None

    if payload.password and payload.email:
        login_method = "manual"
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

    elif payload.google_id:
        login_method = "google"
        email = get_email_from_google_token(payload.google_id)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    elif payload.facebook_id:
        login_method = "facebook"
        email = get_email_from_facebook_token(payload.facebook_id)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid Facebook token")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    else:
        raise HTTPException(status_code=400, detail="Provide valid login credentials")

    # ✅ Save login record
    client_ip = request.client.host
    login_record = login_models.LoginRecord(
        user_id=user.id,
        email=user.email,
        login_method=login_method,
        ip_address=client_ip
    )
    db.add(login_record)
    db.commit()

    # ✅ Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "login_method": login_method,
        "is_verified": user.is_verified,
        "access_token": access_token,
        "token_type": "bearer"
    }


# ✅ Password Reset Request
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str


@router.post("/forgot-password/email/", summary="Step 1: Send OTP to email")
async def send_otp_email(data: schemas.ForgotPasswordEmailRequest, db: Session = Depends(get_db)):
    user = db.query(signup_models.User).filter(signup_models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_created_at = datetime.utcnow()
    db.commit()

    await send_email_otp(user.email, otp, purpose="password_reset")
    return {"message": "OTP sent to your email."}


@router.post("/forgot-password/verify-otp/", summary="Step 2: Verify OTP")
def verify_otp(data: schemas.OTPVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(signup_models.User).filter(signup_models.User.email == data.email).first()
    if not user or not user.otp or not user.otp_created_at:
        raise HTTPException(status_code=400, detail="Invalid request.")

    # Check OTP validity
    if datetime.utcnow() - user.otp_created_at > timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="OTP expired.")

    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    user.otp = None  # clear OTP for security
    db.commit()

    return {"message": "OTP verified successfully."}


@router.post("/forgot-password/reset/", summary="Step 3: Reset password")
def reset_password(data: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    user = db.query(signup_models.User).filter(signup_models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    hashed_pw = pwd_context.hash(data.new_password)
    user.hashed_password = hashed_pw
    db.commit()

    return {"message": "Password reset successfully."}
