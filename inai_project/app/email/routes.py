# app/routes/email_change.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from inai_project.database import SessionLocal
from inai_project.app.signup.models import User
from inai_project.app.signup.dependencies import get_current_user
from inai_project.app.core.email_utils import send_email_otp
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import random

from inai_project.app.core.error_handler import (
    InvalidOTPException, OTPExpiredException,
    EmailTakenException, NoOTPException
)

router = APIRouter()

# ✅ DB session લાવવો
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Email change માટેનો request body
class ChangeEmailRequest(BaseModel):
    new_email: EmailStr

# ✅ New Email change માટે OTP મોકલવાનું route
@router.post("/request-change-email")
async def request_email_change(
    data: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 👉 અહીં સુધારાયું: user_id ના બદલે id
    current_user = db.query(User).filter(User.id == current_user.id).first()

    if db.query(User).filter(User.email == data.new_email).first():
        raise EmailTakenException("Email already in use")

    otp = str(random.randint(100000, 999999))
    current_user.new_email = data.new_email
    current_user.email_change_otp = otp
    current_user.otp_created_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    await send_email_otp(data.new_email, otp, purpose="email_change")
    return {"message": f"OTP sent to {data.new_email}"}

# ✅ OTP verify કરવાનું request model
class VerifyEmailChange(BaseModel):
    otp: str

# ✅ OTP verify કરીને email change confirm કરવાનું route
@router.post("/verify-change-email")
async def verify_email_change(
    data: VerifyEmailChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 👉 અહીં પણ સુધારાયું: user_id -> id
    current_user = db.query(User).filter(User.id == current_user.id).first()

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not current_user.email_change_otp or not current_user.otp_created_at:
        raise NoOTPException()

    if current_user.email_change_otp != data.otp:
        raise InvalidOTPException("Invalid OTP")

    if datetime.utcnow() > current_user.otp_created_at + timedelta(minutes=10):
        raise OTPExpiredException("OTP has expired. Please request a new one.")

    current_user.email = current_user.new_email
    current_user.new_email = None
    current_user.email_change_otp = None
    current_user.otp_created_at = None

    db.commit()
    db.refresh(current_user)

    await send_email_otp(current_user.email, "✅ Your email has been successfully updated.")
    return {"message": "Email changed successfully."}

# ✅ Resend OTP માટેનું route
@router.post("/resend-change-email-otp")
async def resend_email_change_otp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.new_email:
        raise HTTPException(status_code=400, detail="No pending email change found")

    otp = str(random.randint(100000, 999999))
    current_user.email_change_otp = otp
    current_user.otp_created_at = datetime.utcnow()

    db.commit()

    await send_email_otp(current_user.new_email, otp)
    return {"message": f"New OTP resent to {current_user.new_email}"}
