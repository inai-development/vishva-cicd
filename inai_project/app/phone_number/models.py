# app/phone_number/models.py

from sqlalchemy import Column, Integer, String
from inai_project.database import Base

class PhoneOTP(Base):
    __tablename__ = "phone_otps"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    otp = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)  # optional if you link to signup user
