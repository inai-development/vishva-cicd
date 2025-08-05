from fastapi import APIRouter, Depends
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from inai_project.app.core.error_handler import (
    IncorrectOldPasswordException,
    UserNotFoundException,
    PasswordMismatchException
)
from inai_project.app.signup import models as signup_models
from inai_project.app.signup.deps import get_current_user
from inai_project.app.change_password.schemas import PasswordChangeRequest
from inai_project.database import SessionLocal

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ Reusable DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/request-change-password/", summary="Change user password")
def change_password(
    data: PasswordChangeRequest,
    current_user: signup_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ✅ user already fetched and validated by get_current_user
    user = db.query(signup_models.User).filter(
        signup_models.User.user_id == current_user.user_id
    ).first()

    if not user:
        raise UserNotFoundException("User not found.")

    # ✅ Check old password
    if not pwd_context.verify(data.old_password, user.hashed_password):
        raise IncorrectOldPasswordException("Old password is incorrect.")

    # ✅ Ensure new and confirm match
    if data.new_password != data.confirm_password:
        raise PasswordMismatchException("New passwords do not match.")

    # ✅ Hash and update new password
    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
    db.refresh(user)

    return {
        "status": True,
        "message": "Password changed successfully",
        "user_id": user.user_id
    }