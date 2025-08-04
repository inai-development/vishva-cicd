from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, JSON
from sqlalchemy.sql import func
from inai_project.database import Base  # :white_check_mark: central Base

# :white_check_mark: User Table
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    login_method = Column(String, default="manual")  # manual, google, etc.

    # Keep only one definition
    social_id = Column(String, unique=True, nullable=True)

    # Optional profile fields
    picture = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('email', 'login_method', name='uq_email_login_method'),
    )


# :white_check_mark: OTP Table for Email Verification
class EmailOTP(Base):
    __tablename__ = "email_otp"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    otp = Column(String, nullable=False)
    user_data = Column(JSON, nullable=True)  # Store full signup info for later use
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
