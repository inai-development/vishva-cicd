# inai_project/app/change_password/change_password.py

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from inai_project.app.core.error_handler import (
    IncorrectOldPasswordException,
    UserNotFoundException,
    PasswordMismatchException
)
from inai_project.app.signup import models as signup_models
from inai_project.database import SessionLocal
from inai_project.app.signup.deps import get_current_user
from inai_project.app.change_password.schemas import PasswordChangeRequest

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Clean route (no trailing slash)
@router.post("/request-change-password")
def change_password(
    data: PasswordChangeRequest,
    current_user: signup_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("📥 Incoming change password request for user ID:", current_user.id)
    print("🔐 Request body:", data)

    # ✅ Find user
    user = db.query(signup_models.User).filter(
        signup_models.User.id == current_user.id
    ).first()

    if not user:
        raise UserNotFoundException()

    # ✅ Verify old password
    try:
        if not pwd_context.verify(data.old_password, user.hashed_password):
            raise IncorrectOldPasswordException()
    except Exception as e:
        print("⚠️ Error verifying password:", e)
        raise HTTPException(status_code=400, detail="Password verification failed")

    # ✅ Confirm new passwords match
    if data.new_password != data.confirm_password:
        raise PasswordMismatchException()

    # ✅ Update password
    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
    db.refresh(user)

    print("✅ Password updated successfully for user:", user.email)

    return {
        "message": "Password changed successfully",
        "user_id": user.id
    }
