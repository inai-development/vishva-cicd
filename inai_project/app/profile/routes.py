import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse

from inai_project.app.profile import models
from inai_project.database import SessionLocal
from inai_project.app.core import security
from inai_project.app.signup import models as signup_models
from inai_project.app.core.error_handler import InvalidTokenException


router = APIRouter()

UPLOAD_DIR = "uploads/profile_pics"
os.makedirs(UPLOAD_DIR, exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")
SECRET_KEY = security.SECRET_KEY
ALGORITHM = security.ALGORITHM


# ✅ DB Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ Decode token and extract user_id
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenException()
        return int(user_id)
    except JWTError:
        raise InvalidTokenException()


# ✅ Upload profile photo
@router.post("/upload/")
async def upload_profile_pic(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    if not file.filename.lower().endswith(allowed_extensions):
        return JSONResponse(
            status_code=400,
            content={"status": False, "message": "Unsupported file format"}
        )

    try:
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_location = os.path.join(UPLOAD_DIR, filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())

        user_account = db.query(signup_models.User).filter(signup_models.User.id == user_id).first()
        if not user_account:
            raise HTTPException(status_code=404, detail="User not found")

        user_profile = db.query(models.UserProfile).filter(
            models.UserProfile.username == user_account.username
        ).first()

        if not user_profile:
            user_profile = models.UserProfile(
                user_id=user_account.id,
                username=user_account.username,
                profile_photo=file_location
            )
            db.add(user_profile)
        else:
            user_profile.profile_photo = file_location

        db.commit()
        db.refresh(user_profile)

        return {
            "message": "Profile photo uploaded successfully",
            "user_id": user_account.id,
            "username": user_profile.username,
            "profile_photo": user_profile.profile_photo
        }

    except Exception as e:
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail="Profile photo upload failed. Try again.")


# ✅ Update profile username and/or photo
@router.patch("/update/")
async def update_profile(
    new_username: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user_account = db.query(signup_models.User).filter(signup_models.User.id == user_id).first()
    if not user_account:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user_profile = db.query(models.UserProfile).filter(
            models.UserProfile.username == user_account.username
        ).first()

        if not user_profile:
            user_profile = models.UserProfile(
                username=user_account.username,
                user_id=user_account.id
            )
            db.add(user_profile)
            db.commit()
            db.refresh(user_profile)

        if new_username:
            # ✅ Check if username already taken
            existing_user = db.query(signup_models.User).filter(signup_models.User.username == new_username).first()
            if existing_user and existing_user.id != user_id:
                raise HTTPException(status_code=409, detail="Username already exists")

            user_account.username = new_username
            user_profile.username = new_username

        if file:
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                return JSONResponse(
                    status_code=400,
                    content={"status": False, "message": "Unsupported file format"}
                )
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            file_location = os.path.join(UPLOAD_DIR, filename)
            with open(file_location, "wb") as f:
                f.write(await file.read())
            user_profile.profile_photo = file_location

        db.commit()
        db.refresh(user_profile)

        return {
            "message": "Profile updated successfully",
            "username": user_profile.username,
            "profile_photo": user_profile.profile_photo
        }

    except Exception as e:
        print("Update Error:", e)
        raise HTTPException(status_code=500, detail="Profile update failed. Try again.")
