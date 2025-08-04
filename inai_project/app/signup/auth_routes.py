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
router = APIRouter()
# :white_check_mark: DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# :white_check_mark: Register User
@router.post("/register/")
async def register_user(user_data: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    login_method = user_data.login_method.lower()
    current_time = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"
    # ----- Manual Signup -----
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
                if not user_data.social_id:
                    user_data.social_id = None
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
    # ----- Google / Facebook Signup -----
    elif login_method in ["google", "facebook"]:
        existing_social_user = db.query(models.User).filter(
            models.User.social_id == user_data.social_id,
            models.User.login_method == login_method
        ).first()
        if existing_social_user:
            old_username = existing_social_user.username
            new_username = user_data.username or existing_social_user.username
            existing_social_user.username = new_username
            existing_social_user.email = user_data.email or existing_social_user.email
            existing_social_user.picture = getattr(user_data, "picture", existing_social_user.picture)
            existing_social_user.gender = getattr(user_data, "gender", existing_social_user.gender)
            existing_social_user.phone_number = getattr(user_data, "phone_number", existing_social_user.phone_number)
            if old_username != new_username:
                db.query(login_models.LoginRecord).filter(
                    login_models.LoginRecord.user_id == existing_social_user.user_id
                ).update({login_models.LoginRecord.username: new_username})
            db.commit()
            db.add(login_models.LoginRecord(
                user_id=existing_social_user.user_id,
                username=existing_social_user.username or (existing_social_user.email.split("@")[0] if existing_social_user.email else "unknown_user"),
                email=existing_social_user.email,
                login_method=login_method,
                ip_address=client_ip
            ))
            db.commit()
            access_token = create_access_token(data={"sub": str(existing_social_user.user_id)})
            refresh_token = create_refresh_token(data={"sub": str(existing_social_user.user_id)})
            return {
                "status": True,
                "message": f"{login_method.capitalize()} login successful",
                "user_id": existing_social_user.user_id,
                "username": existing_social_user.username,
                "email": existing_social_user.email,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        # :white_check_mark: If no existing user, create one
        social_id_to_save = user_data.social_id
        existing_id_conflict = db.query(models.User).filter(
            models.User.social_id == user_data.social_id
        ).first()
        if existing_id_conflict:
            social_id_to_save = f"{user_data.social_id}_{uuid.uuid4().hex}"
        new_user = models.User(
            username=user_data.username or user_data.email.split("@")[0],
            email=user_data.email,
            hashed_password="",
            login_method=login_method,
            social_id=social_id_to_save,
            picture=getattr(user_data, "picture", None),
            gender=getattr(user_data, "gender", None),
            phone_number=getattr(user_data, "phone_number", None),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.add(login_models.LoginRecord(
            user_id=new_user.user_id,
            username=new_user.username or (new_user.email.split("@")[0] if new_user.email else "unknown_user"),
            email=new_user.email if new_user.email else "unknown@example.com",
            login_method=login_method,
            ip_address=client_ip
        ))
        db.commit()
        access_token = create_access_token(data={"sub": str(new_user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(new_user.user_id)})
        return {
            "status": True,
            "message": f"{login_method.capitalize()} signup successful",
            "user_id": new_user.user_id,
            "username": new_user.username,
            "email": new_user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    else:
        raise InvalidTokenException("Invalid login method.")
# :white_check_mark: Verify OTP
@router.post("/confirm/")
async def verify_otp(data: ConfirmOTP, request: Request, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    entry = unverified_users.get(email)

    if not entry:
        raise NoOTPException("No OTP request found for this email.")

    # 🔍 Sanitize OTPs for accurate comparison
    submitted_otp = str(data.otp).strip()
    stored_otp = str(entry["otp"]).strip()

    # 🧪 Debug print (remove in production)
    print("🧪 Stored OTP:", stored_otp)
    print("🧪 Submitted OTP:", submitted_otp)

    # ✅ OTP Check (allow '111111' for test bypass)
    if submitted_otp != stored_otp and submitted_otp != "111111":
        raise InvalidTokenException("Invalid OTP.")

    if entry["expires_at"] < datetime.utcnow():
        raise OTPExpiredException("OTP expired.")

    user_data: schemas.UserCreate = entry["user_data"]
    if not isinstance(user_data, schemas.UserCreate):
        raise ValueError("Invalid user data type in OTP cache.")

    hashed_pw = get_password_hash(user_data.password) if user_data.login_method == "manual" else ""

    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user and existing_user.login_method != user_data.login_method:
        raise EmailTakenException(f"This email is already used with {existing_user.login_method} login.")

    if existing_user:
        existing_user.is_verified = True
        if hashed_pw:
            existing_user.hashed_password = hashed_pw
        if isinstance(user_data.username, str):
            old_username = existing_user.username
            new_username = user_data.username or existing_user.username
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
            social_id=user_data.social_id if user_data.social_id else None,
            picture=getattr(user_data, "picture", None),
            gender=getattr(user_data, "gender", None),
            phone_number=getattr(user_data, "phone_number", None),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_id = new_user.user_id

    # ✅ Add Login Record after verification
    client_ip = request.client.host if request.client else "unknown"

    user_check = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user_check:
        raise UserNotFoundException()

    db.add(login_models.LoginRecord(
        user_id=user_id,
        username=user_data.username or (email.split("@")[0] if email else "unknown_user"),
        email=email if email else "unknown@example.com",
        login_method=user_data.login_method,
        ip_address=client_ip
    ))
    db.commit()

    # ✅ Clear OTP cache
    unverified_users.pop(email, None)

    # ✅ Generate Tokens
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


# :white_check_mark: Resend OTP
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