import os
import io
import boto3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from botocore.exceptions import BotoCoreError, ClientError

from inai_project.app.profile import models
from inai_project.database import SessionLocal
from inai_project.app.core import security
from inai_project.app.signup import models as signup_models

# === Config ===
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")
SECRET_KEY = security.SECRET_KEY
ALGORITHM = security.ALGORITHM

# S3 Client setup
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)
S3_BUCKET = os.getenv("AWS_BUCKET_NAME")


# === Dependencies ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")
        return int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


# === Upload Profile Picture ===
@router.post("/upload/")
async def upload_profile_pic(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return JSONResponse(
            status_code=400,
            content={"status": False, "message": "Unsupported file format"}
        )

    try:
        # Prepare file and S3 key
        file_data = await file.read()
        s3_key = f"profile_pics/{user_id}_{file.filename}"

        # Upload to S3
        s3.upload_fileobj(
            Fileobj=io.BytesIO(file_data),
            Bucket=S3_BUCKET,
            Key=s3_key,
            ExtraArgs={"ContentType": file.content_type}
        )

        # Generate public URL
        file_location = f"https://{S3_BUCKET}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_key}"

        # Get user and update/create profile
        user_account = db.query(signup_models.User).filter(signup_models.User.id == user_id).first()
        if not user_account:
            raise HTTPException(status_code=404, detail="User not found")

        user_profile = db.query(models.UserProfile).filter(
            models.UserProfile.username == user_account.username
        ).first()

        if not user_profile:
            user_profile = models.UserProfile(
                username=user_account.username,
                profile_photo=file_location
            )
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

    except (BotoCoreError, ClientError) as s3_err:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(s3_err)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Profile photo upload failed. Try again.")