from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from inai_project.app.signup import models
from inai_project.database import SessionLocal
from inai_project.app.core.security import create_access_token
from . import schemas  # :point_left: use your schemas
from fastapi import Request  # :white_check_mark: to get IP
from inai_project.app.login import models as login_models  # :white_check_mark: import your LoginRecord model
from inai_project.app.core.error_handler import InvalidCredentialsException
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@router.post("/login/", summary="Login with email and password")
def login(
    creds: schemas.LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == creds.email).first()
    if not user or not pwd_context.verify(creds.password, user.hashed_password):
        raise InvalidCredentialsException()  # :white_check_mark: Raise custom error
    # Generate token and store login record (as you already do)
    token_data = {"sub": user.username, "user_id": user.id}
    access_token = create_access_token(data=token_data)
    ip_address = request.client.host
    record = login_models.LoginRecord(
        user_id=user.id,
        email=user.email,
        ip_address=ip_address
    )
    db.add(record)
    db.commit()
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }