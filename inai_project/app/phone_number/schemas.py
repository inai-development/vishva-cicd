# app/phone_number/schemas.py

from pydantic import BaseModel

class PhoneSignup(BaseModel):
    phone_number: str

class ConfirmOTP(BaseModel):
    phone_number: str
    otp: str
