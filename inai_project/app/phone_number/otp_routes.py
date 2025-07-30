# app/phone_number/otp_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import random

from inai_project.app.phone_number import models, schemas
from inai_project.app.core import security
from inai_project.database import SessionLocal
from inai_project.app.core.error_handler import InvalidTokenException


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")  # your login endpoint

SECRET_KEY = security.SECRET_KEY
ALGORITHM = security.ALGORITHM

# DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT helper: get user_id from signup JWT
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenException()
        return int(user_id)
    except JWTError:
        raise InvalidTokenException()



# ✅ Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# ✅ Request OTP → JWT required!
@router.post("/request/", summary="Request OTP for phone")
def request_otp(
    data: schemas.PhoneSignup,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    otp = generate_otp()

    phone_otp = db.query(models.PhoneOTP).filter(models.PhoneOTP.phone_number == data.phone_number).first()
    if phone_otp:
        phone_otp.otp = otp
        phone_otp.user_id = user_id
    else:
        phone_otp = models.PhoneOTP(
            phone_number=data.phone_number,
            otp=otp,
            user_id=user_id
        )
        db.add(phone_otp)

    db.commit()
    db.refresh(phone_otp)

    print(f"[DEBUG] OTP {otp} for {phone_otp.phone_number} by user_id={user_id}")

    return {
        "message": "OTP generated",
        "phone_number": phone_otp.phone_number,
        "user_id": user_id
    }

# ✅ Confirm OTP → get JWT for phone
@router.post("/confirm/", summary="Confirm OTP & get JWT for phone")
def confirm_otp(
    data: schemas.ConfirmOTP,
    db: Session = Depends(get_db)
):
    phone_otp = db.query(models.PhoneOTP).filter(models.PhoneOTP.phone_number == data.phone_number).first()
    if not phone_otp or phone_otp.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    return {
        "message": "OTP verified",
        "phone_number": phone_otp.phone_number
    }

# ✅ Protected
def get_current_phone_number(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone_number: str = payload.get("sub")
        if phone_number is None:
            raise InvalidTokenException()
        return phone_number
    except JWTError:
        raise InvalidTokenException()

@router.get("/me/", summary="Get phone info (protected)")
def me(phone_number: str = Depends(get_current_phone_number)):
    return {"phone_number": phone_number}
