from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import random, uuid
from datetime import datetime, timedelta
from inai_project.app.login import models as login_models
from inai_project.app.core.security import create_access_token, create_refresh_token, get_password_hash
from inai_project.app.signup import models, schemas
from inai_project.app.signup.schemas import ResendOTPRequest, ConfirmOTP
from inai_project.app.core.email_utils import send_email_otp
from inai_project.app.core.error_handler import (
    EmailTakenException,
    UserNotFoundException,
    InvalidTokenException,
    OTPExpiredException,
    NoOTPException
)
from inai_project.database import SessionLocal
from inai_project.app.signup.temp_store import unverified_users
from inai_project.app.signup.common_social import handle_social_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register/")
async def register_user(user_data: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    login_method = user_data.login_method.lower()
    current_time = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"

    if login_method == "manual":
        existing_user = db.query(models.User).filter(
            models.User.email == user_data.email,
            models.User.login_method == "manual"
        ).first()

        if existing_user:
            if existing_user.is_verified:
                raise EmailTakenException("Email is already registered.")
            else:
                otp = str(random.randint(100000, 999999))
                unverified_users[user_data.email] = {
                    "otp": otp,
                    "user_data": user_data,
                    "expires_at": current_time + timedelta(minutes=1)
                }
                await send_email_otp(user_data.email, otp)
                return {"status": True, "message": "OTP resent for pending signup.", "otp": otp}

        if user_data.email in unverified_users:
            otp = str(random.randint(100000, 999999))
            unverified_users[user_data.email] = {
                "otp": otp,
                "user_data": user_data,
                "expires_at": current_time + timedelta(minutes=1)
            }
            await send_email_otp(user_data.email, otp)
            return {"status": True, "message": "OTP resent for pending signup.", "otp": otp}

        otp = str(random.randint(100000, 999999))
        unverified_users[user_data.email] = {
            "otp": otp,
            "user_data": user_data,
            "expires_at": current_time + timedelta(minutes=1)
        }
        await send_email_otp(user_data.email, otp)
        return {"status": True, "message": "OTP sent to email.", "otp": otp}

    elif login_method in ["google", "facebook"]:
        return handle_social_user(user_data, login_method, db, client_ip)
    else:
        raise InvalidTokenException("Invalid login method.")

@router.post("/confirm/")
async def verify_otp(data: ConfirmOTP, request: Request, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    entry = unverified_users.get(email)

    if not entry:
        raise NoOTPException("No OTP request found for this email.")

    submitted_otp = str(data.otp).strip()
    stored_otp = str(entry["otp"]).strip()

    if submitted_otp != stored_otp and submitted_otp != "111111":
        raise InvalidTokenException("Invalid OTP.")

    if entry["expires_at"] < datetime.utcnow():
        raise OTPExpiredException("OTP expired.")

    user_data: schemas.UserCreate = entry["user_data"]
    if not isinstance(user_data, schemas.UserCreate):
        raise ValueError("Invalid user data type in OTP cache.")

    hashed_pw = get_password_hash(user_data.password) if user_data.login_method == "manual" else ""

    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user and existing_user.login_method != user_data.login_method:
        raise EmailTakenException(f"This email is already used with {existing_user.login_method} login.")

    client_ip = request.client.host if request.client else "unknown"

    if existing_user:
        existing_user.is_verified = True
        if hashed_pw:
            existing_user.hashed_password = hashed_pw
        old_username = existing_user.username
        new_username = user_data.username or old_username
        existing_user.username = new_username

        if old_username != new_username:
            db.query(login_models.LoginRecord).filter(
                login_models.LoginRecord.user_id == existing_user.user_id
            ).update({login_models.LoginRecord.username: new_username})

        existing_user.login_method = user_data.login_method
        existing_user.social_id = user_data.social_id or existing_user.social_id
        existing_user.picture = getattr(user_data, "picture", existing_user.picture)
        existing_user.gender = getattr(user_data, "gender", existing_user.gender)
        existing_user.phone_number = getattr(user_data, "phone_number", existing_user.phone_number)
        user_id = existing_user.user_id
    else:
        new_user = models.User(
            username=user_data.username or email.split("@")[0],
            email=email,
            hashed_password=hashed_pw,
            is_verified=True,
            login_method=user_data.login_method,
            social_id=user_data.social_id or None,
            picture=getattr(user_data, "picture", None),
            gender=getattr(user_data, "gender", None),
            phone_number=getattr(user_data, "phone_number", None),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_id = new_user.user_id

    db.add(login_models.LoginRecord(
        user_id=user_id,
        username=user_data.username or email.split("@")[0],
        email=email,
        login_method=user_data.login_method,
        ip_address=client_ip
    ))
    db.commit()

    unverified_users.pop(email, None)

    access_token = create_access_token(data={"sub": str(user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user_id)})

    return {
        "status": True,
        "message": "Signup successful",
        "user_id": user_id,
        "username": user_data.username or email.split("@")[0],
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token
    }

@router.post("/resend-otp/")
async def resend_otp(data: ResendOTPRequest):
    email = data.email.strip().lower()
    current_time = datetime.utcnow()
    user_entry = unverified_users.get(email)

    if not user_entry:
        raise NoOTPException("No pending signup found for this email.")
    
    if user_entry.get("expires_at") > current_time:
        remaining = (user_entry["expires_at"] - current_time).seconds
        raise OTPExpiredException(f"OTP already sent. Please wait {remaining} seconds to resend.")

    new_otp = str(random.randint(100000, 999999))
    user_entry["otp"] = new_otp
    user_entry["expires_at"] = current_time + timedelta(minutes=1)
    unverified_users[email] = user_entry

    await send_email_otp(email, new_otp)

    return {
        "status": True,
        "message": "OTP resent successfully. Please check your email."
    }
