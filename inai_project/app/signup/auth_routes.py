from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from inai_project.app.signup import models, schemas
from inai_project.app.core.security import create_access_token
from inai_project.database import SessionLocal

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", summary="Register new user")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        db_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_email:
            raise HTTPException(status_code=400, detail="Email already registered")

        if user.password != user.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        hashed_password = pwd_context.hash(user.password)
        new_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        token_data = {
            "sub": str(new_user.id),
            "username": new_user.username
        }
        access_token = create_access_token(data=token_data)

        return {
            "message": "User created successfully",
            "user_id": new_user.id,
            "access_token": access_token
        }

    except Exception as e:
        print("❌ Internal Error:", str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

