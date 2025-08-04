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
    user = None

    # ----- Manual Login -----
    if login_method == "manual":
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise UserNotFoundException("User not found. Please register first before logging in.")
        if not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsException("Invalid email or password.")

    # ----- Google / Facebook Login -----
    elif login_method in ["google", "facebook"]:
        if payload.email:
            user = db.query(User).filter(User.email == payload.email).first()
        if not user and payload.social_id:
            user = db.query(User).filter(User.social_id == payload.social_id).first()

        # Update existing user info
        if user:
            user.username = payload.username or user.username
            user.email = payload.email or user.email
            if getattr(payload, "picture", None):
                user.picture = payload.picture
            if getattr(payload, "gender", None):
                user.gender = payload.gender
            if getattr(payload, "phone_number", None):
                user.phone_number = payload.phone_number
            db.commit()
            db.refresh(user)

        # Create new user if not exists
        if not user:
            social_id_to_save = payload.social_id
            if db.query(User).filter(User.social_id == payload.social_id).first():
                social_id_to_save = f"{payload.social_id}_{uuid.uuid4().hex}"

            user = User(
                username=payload.username or (payload.email.split("@")[0] if payload.email else f"{login_method}_user"),
                email=payload.email,
                hashed_password="",  # No password for social login
                is_verified=True,
                login_method=login_method,
                social_id=social_id_to_save,
                picture=getattr(payload, "picture", None),
                gender=getattr(payload, "gender", None),
                phone_number=getattr(payload, "phone_number", None),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    else:
        raise InvalidCredentialsException("Invalid login method.")

    # ✅ Generate tokens
    access_token = create_access_token({"sub": str(user.user_id), "username": user.username})
    refresh_token = create_refresh_token({"sub": str(user.user_id)})
    db.add(user)       # INSERT into DB only now!
    db.commit()
    db.refresh(user)

    # Log login
    client_ip = request.client.host
    db.add(login_models.LoginRecord(
        user_id=user.user_id,
        username=user.username,
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


# ✅ Forgot Password - Send OTP
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


# ✅ Forgot Password - Verify OTP
@router.post("/forgot-password/verify-otp/", summary="Step 2: Verify OTP")
def verify_otp(data: schemas.OTPVerifyRequest, db: Session = Depends(get_db)):
    record = otp_store.get(data.email)
    if not record:
        raise NoOTPException("No OTP request found.")

    if datetime.utcnow() - record["created_at"] > timedelta(minutes=5):
        raise OTPExpiredException("OTP expired.")

    if record["otp"] != data.otp:
        raise InvalidTokenException("Invalid OTP.")

    otp_store[data.email]["verified"] = True
    return {"status": True, "message": "OTP verified successfully."}


# ✅ Forgot Password - Reset Password
@router.post("/forgot-password/reset/")
def reset_password(data: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    if data.new_password != data.confirm_password:
        raise PasswordMismatchException("Passwords do not match.")

    record = otp_store.get(data.email)
    if not record or not record.get("verified"):
        raise NoOTPException("OTP not verified.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise UserNotFoundException("User not found.")

    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()

    otp_store.pop(data.email, None)
    return {"status": True, "message": "Password reset successfully."}
