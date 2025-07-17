# app/gender/routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from inai_project.app.gender import models, schemas
from inai_project.database import SessionLocal
from inai_project.app.core.security import SECRET_KEY, ALGORITHM

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
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")
        return int(user_id_str)  # ✅ safe, now sub is id
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/choose/", summary="Choose gender (male/female)")
def choose_gender(
    gender: schemas.GenderChoice,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if gender.gender not in ["male", "female"]:
        raise HTTPException(status_code=400, detail="Gender must be male or female")

    record = db.query(models.Gender).filter(models.Gender.user_id == user_id).first()
    if record:
        record.gender = gender.gender
    else:
        record = models.Gender(user_id=user_id, gender=gender.gender)
        db.add(record)

    db.commit()
    return {"message": "Gender updated", "user_id": user_id, "gender": record.gender}
