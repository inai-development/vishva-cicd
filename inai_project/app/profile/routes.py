# app/profile/routes.py

import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

from inai_project.app.profile import models
from inai_project.database import SessionLocal
from inai_project.app.core import security
from inai_project.app.signup import models as signup_models

router = APIRouter()

UPLOAD_DIR = "uploads/profile_pics"
os.makedirs(UPLOAD_DIR, exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")
SECRET_KEY = security.SECRET_KEY
ALGORITHM = security.ALGORITHM

# ✅ DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Get current user ID from JWT
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")
        return int(user_id_str)  # ✅ safe, now sub is id
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


# ✅ Upload profile photo — no manual username!
@router.post("/upload/")
async def upload_profile_pic(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)  # ✅ Get user_id from JWT!
):
    file_location = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_location, "wb") as f:
        f.write(await file.read())

    # ✅ Fetch user by user_id from signup table
    user_account = db.query(signup_models.User).filter(signup_models.User.id == user_id).first()
    if not user_account:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Check or create UserProfile
    user_profile = db.query(models.UserProfile).filter(models.UserProfile.username == user_account.username).first()
    if not user_profile:
        user_profile = models.UserProfile(username=user_account.username, profile_photo=file_location)
        db.add(user_profile)
    else:
        user_profile.profile_photo = file_location

    db.commit()
    db.refresh(user_profile)

    return {
        "message": "Profile photo uploaded",
        "username": user_profile.username,
        "profile_photo": user_profile.profile_photo
    }
