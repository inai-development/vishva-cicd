from sqlalchemy import Column, Integer, String, Boolean, DateTime
from inai_project.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # Primary ID field
    google_id = Column(String, unique=True, nullable=True)                 # Google OAuth ID
    facebook_id = Column(String, unique=True, nullable=True)               # Facebook OAuth ID
    username = Column(String, nullable=False)                              # Username
    email = Column(String, unique=True, index=True, nullable=False)        # Email (Unique)
    hashed_password = Column(String, nullable=True)                        # Password hash
    otp = Column(String, nullable=True)                                    # OTP for email verification
    is_verified = Column(Boolean, default=False)                           # Email verified or not
    login_method = Column(String, nullable=True)                           # Login method (manual, google, facebook)
    new_email = Column(String, unique=True, nullable=True)                 # New email (for change requests)
    email_change_otp = Column(String, nullable=True)                       # OTP for changing email
    otp_created_at = Column(DateTime, nullable=True)                       # OTP creation time
