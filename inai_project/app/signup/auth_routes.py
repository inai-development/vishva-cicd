# :white_check_mark: signup route (router)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from inai_project.app.signup import models, schemas
from inai_project.app.core.security import create_access_token
from inai_project.app.core.error_handler import UsernameTakenException, EmailTakenException, PhoneTakenException
from inai_project.database import SessionLocal
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@router.post("/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Username check
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise UsernameTakenException("Username already registered")
    # Email check
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise EmailTakenException("Email already registered")
    # Phone number check
    hashed_password = pwd_context.hash(user.password)
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token_data = {"sub": str(new_user.id), "username": new_user.username}
    access_token = create_access_token(token_data)
    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }






