from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
import random, uuid

from inai_project.app.signup.models import User
from inai_project.database import SessionLocal
from inai_project.app.core.security import create_access_token, create_refresh_token, verify_password
from . import schemas
from inai_project.app.login import models as login_models
from inai_project.app.core.email_utils import send_email_otp
from inai_project.app.core.error_handler import (
    InvalidCredentialsException,
    UserNotFoundException,
    OTPExpiredException,
    NoOTPException,
    InvalidTokenException,
    PasswordMismatchException
)
from inai_project.app.login.schemas import LoginRequest
from inai_project.app.signup.temp_store import otp_store
from inai_project.app.signup.common_social import handle_social_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ✅ DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Login API (Manual + Google + Facebook with auto-signup & always update DB)
@router.post("/login/")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    login_method = payload.login_method.lower()
    client_ip = request.client.host if request.client else "unknown"  # :white_check_mark: Fix here
    # user = None
    # ----- Manual Login -----
    if login_method == "manual":
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise UserNotFoundException("User not found. Please register first before logging in.")
        if not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsException("Invalid email or password.")
    # ----- Google / Facebook Login -----
    elif login_method in ["google", "facebook"]:
        return handle_social_user(payload, login_method, db, client_ip)
    else:
        raise InvalidCredentialsException("Invalid login method.")
    # :white_check_mark: Generate tokens
    access_token = create_access_token({"sub": str(user.user_id), "username": user.username})
    refresh_token = create_refresh_token({"sub": str(user.user_id)})
    # :white_check_mark: Record login
    client_ip = request.client.host
    db.add(login_models.LoginRecord(
        user_id=user.user_id,
        username=user.username,  # Make sure your LoginRecord model has this column
        email=user.email,
        login_method=login_method,
        ip_address=client_ip
    ))
    db.commit()
    return {
        "status": True,
        "message": f"{login_method.capitalize()} login successful",
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# :white_check_mark: Forgot Password - Send OTP
@router.post("/forgot-password/email/", summary="Step 1: Send OTP to email")
async def send_otp_email(data: schemas.ForgotPasswordEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise UserNotFoundException("User not found.")
    record = otp_store.get(data.email)
    if record:
        time_diff = datetime.utcnow() - record["created_at"]
        seconds_remaining = int((timedelta(minutes=1) - time_diff).total_seconds())
        if seconds_remaining > 0:
            raise OTPExpiredException(f"OTP already sent. Please wait {seconds_remaining} seconds to resend.")
    otp = str(random.randint(100000, 999999))
    otp_store[data.email] = {"otp": otp, "created_at": datetime.utcnow()}
    await send_email_otp(user.email, otp, purpose="password_reset")
    return {"status": True, "message": "OTP sent to your email."}



# ✅ Forgot Password - Send OTP
@router.post("/forgot-password/verify-otp/", summary="Step 2: Verify OTP")
async def verify_otp(data: schemas.OTPVerifyRequest, db: Session = Depends(get_db)):
    record = otp_store.get(data.email)
    if not record:
        raise NoOTPException("No OTP request found.")
    # :hourglass_flowing_sand: If OTP expired → auto resend new OTP
    if datetime.utcnow() - record["created_at"] > timedelta(minutes=1):
        new_otp = str(random.randint(100000, 999999))
        otp_store[data.email] = {"otp": new_otp, "created_at": datetime.utcnow()}
        await send_email_otp(data.email, new_otp, purpose="password_reset")
        raise OTPExpiredException("OTP expired. A new OTP has been sent to your email.")
    # :x: If OTP incorrect
    if record["otp"] != data.otp:
        raise InvalidTokenException("Invalid OTP.")
    # :white_check_mark: OTP verified
    otp_store[data.email]["verified"] = True
    return {"status": True, "message": "OTP verified successfully."}





# ✅ Forgot Password - Reset Password
@router.post("/forgot-password/reset/")
def reset_password(data: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    # :small_blue_diamond: 1. Check password match
    if data.new_password != data.confirm_password:
        raise PasswordMismatchException("Passwords do not match.")
    # :small_blue_diamond: 2. Check user exists
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise UserNotFoundException("User not found.")
    # :small_blue_diamond: 3. Update password
    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
    # :small_blue_diamond: 4. Remove OTP from store (optional cleanup)
    otp_store.pop(data.email, None)
    return {"status": True, "message": "Password reset successfully."}