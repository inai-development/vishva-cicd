from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import random, uuid

from inai_project.app.signup import models, schemas
from inai_project.app.core.security import create_access_token
from inai_project.app.core.email_utils import send_email_otp
from inai_project.app.core.error_handler import (
    UserNotFoundException,
    InvalidOTPException,
    EmailTakenException
)
from inai_project.database import SessionLocal
from inai_project.app.core.oauth_utils import get_email_from_google_token
from inai_project.app.signup.models import User
from inai_project.app.signup.dependencies import get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register/")
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if user.google_id and not user.facebook_id:
        try:
            google_user = get_email_from_google_token(user.google_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        existing_user = db.query(User).filter(User.google_id == google_user["google_id"]).first()
        if existing_user:
            raise EmailTakenException("Google account already registered")

        new_user = User(
            username=google_user["username"],
            email=google_user["email"],
            hashed_password=pwd_context.hash(str(uuid.uuid4())),  # Dummy hashed pw
            google_id=google_user["google_id"],
            login_method="google",
            is_verified=True
        )

    elif user.facebook_id and not user.google_id:
        fb_email = f"{user.facebook_id}@facebook.com"
        fb_username = f"user_{uuid.uuid4().hex[:6]}"

        existing_user = db.query(User).filter(User.facebook_id == user.facebook_id).first()
        if existing_user:
            raise EmailTakenException("Facebook account already registered")

        new_user = User(
            username=fb_username,
            email=fb_email,
            hashed_password=pwd_context.hash(str(uuid.uuid4())),  # Dummy hashed pw
            facebook_id=user.facebook_id,
            login_method="facebook",
            is_verified=True
        )

    else:
        # Manual Signup
        if db.query(User).filter(User.email == user.email).first():
            raise EmailTakenException("Email already registered")

        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        hashed_password = pwd_context.hash(user.password)
        otp = str(random.randint(100000, 999999))

        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            otp=otp,
            login_method="manual",
            is_verified=False
        )

        await send_email_otp(user.email, otp)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({"sub": str(new_user.id), "username": new_user.username})

    return {
        "message": "Signup initiated successfully. An OTP has been sent to your email. Please verify to complete registration.",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "login_method": new_user.login_method,
        "is_verified": new_user.is_verified,
        "access_token": access_token,
        "token_type": "bearer"
    }


class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp: str


@router.post("/confirm/")
def verify_otp(data: OTPVerifySchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise UserNotFoundException("User not found")
    if user.otp != data.otp:
        raise InvalidOTPException("Invalid OTP")

    user.is_verified = True
    user.otp = None
    db.commit()

    return {"message": "OTP successfully verified. You can now login."}


@router.get("/me/")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }
