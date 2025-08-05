from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
import random
from inai_project.app.login import models as login_models
from inai_project.database import SessionLocal
from inai_project.app.signup.models import User
from inai_project.app.signup.deps import get_current_user
from inai_project.app.core.email_utils import send_email_otp
from inai_project.app.signup.temp_store import (
    store_otp,
    verify_otp,
    remove_otp,
    get_pending_new_email,
    pending_email_changes
)
from inai_project.app.core.error_handler import (
    EmailTakenException,
    InvalidOrExpiredTokenException,
    UserNotFoundException,
    NoOTPException
)

router = APIRouter()

# ✅ Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Request Schemas
class ChangeEmailRequest(BaseModel):
    new_email: EmailStr

class VerifyChangeEmail(BaseModel):
    otp: str


# ✅ STEP 1: Request Email Change - Send OTP
@router.post("/request-change-email/")
async def request_email_change(
    data: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == data.new_email).first():
        raise EmailTakenException("New email is already in use.")

    otp = str(random.randint(100000, 999999))
    store_otp(current_user.user_id, data.new_email, otp)

    await send_email_otp(data.new_email, otp, purpose="email_change")
    return {
        "status": True,
        "message": f"OTP sent to {data.new_email}"
    }


# ✅ STEP 2: Verify OTP and Update Email
@router.post("/verify-change-email/")
def verify_email_change(
    data: VerifyChangeEmail,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_otp(current_user.user_id, data.otp):
        raise InvalidOrExpiredTokenException("Invalid or expired OTP.")
    new_email = get_pending_new_email(current_user.user_id)
    if not new_email:
        raise NoOTPException("No pending email change found.")
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise UserNotFoundException()
    # :white_check_mark: Update user table
    user.email = new_email
    db.commit()
    db.refresh(user)
    # :white_check_mark: Update all login_records with the new email
    login_records = db.query(login_models.LoginRecord).filter(
        login_models.LoginRecord.user_id == user.user_id
    ).all()
    for record in login_records:
        record.email = new_email
    db.commit()
    remove_otp(current_user.user_id)
    return {
        "status": True,
        "message": "Email changed successfully"
    }



# ✅ STEP 3: Resend OTP
@router.post("/resend-change-email/")
async def resend_change_email_otp(
    current_user: User = Depends(get_current_user)
):
    change_data = pending_email_changes.get(current_user.user_id)
    if not change_data:
        raise NoOTPException("No pending email change found.")

    new_email = change_data["new_email"]
    expires_at = change_data.get("expires_at")

    now = datetime.utcnow()
    if expires_at:
        seconds_remaining = int((expires_at - now).total_seconds())
        if seconds_remaining > 0:
            return {
                "status": False,
                "message": f"OTP already sent. Wait {seconds_remaining} seconds.",
                "seconds_remaining": seconds_remaining
            }

    otp = str(random.randint(100000, 999999))
    store_otp(current_user.user_id, new_email, otp)

    await send_email_otp(new_email, otp, purpose="email_change")
    return {
        "status": True,
        "message": f"New OTP sent to {new_email}"
    }
