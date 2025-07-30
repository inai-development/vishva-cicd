# app/gender/routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from inai_project.app.gender import models, schemas
from inai_project.database import SessionLocal
from inai_project.app.core.security import SECRET_KEY, ALGORITHM
from inai_project.app.core.error_handler import InvalidGenderException
from inai_project.app.signup.models import User
from inai_project.app.core.error_handler import InvalidTokenException


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenException()
        return int(user_id)
    except JWTError:
        raise InvalidTokenException()


@router.post("/choose/", summary="Choose gender (male/female/other)")
def choose_gender(
    gender: schemas.GenderChoice,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if gender.gender not in ["male", "female", "other"]:
        raise InvalidGenderException()

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if gender record exists
    record = db.query(models.Gender).filter(models.Gender.user_id == user_id).first()

    if record:
        record.gender = gender.gender
    else:
        record = models.Gender(
            user_id=user_id,
            gender=gender.gender
        )
        db.add(record)

    db.commit()

    return {
        "message": "Gender updated",
        "user_id": user_id,
        "username": user.username,
        "gender": record.gender
    }
