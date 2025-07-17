from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from inai_project.app.signup import models
from inai_project.database import SessionLocal, Base
# from database import SessionLocal
from inai_project.app.core.security import create_access_token
from . import schemas  # 👈 use your schemas
from fastapi import Request  # ✅ to get IP
# from app.login import models as login_models  
from inai_project.app.login import models as login_models 
# login/routes.py
from inai_project.app.signup.models import User  # ✅ Reuse


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
    request: Request,                # ✅ Get request for IP address
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == creds.email).first()
    if not user or not pwd_context.verify(creds.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    # ✅ Create JWT
    token_data = {"sub": user.username, "user_id": user.id}
    access_token = create_access_token(data=token_data)

    # ✅ Save login record
    ip_address = request.client.host  # get user's IP
    record = login_models.LoginRecord(
        user_id=user.id,
        email=user.email,
        ip_address=ip_address
    )
    db.add(record)
    db.commit()

    return {
        "message": "Login successful",
        "username": user.username,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }