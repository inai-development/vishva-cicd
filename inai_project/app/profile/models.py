# app/profile/models.py
from sqlalchemy import Column, Integer, String
from inai_project.database import Base
class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {'extend_existing': True}  # :white_check_mark: FIX: avoid duplicate table error!
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    profile_photo = Column(String, nullable=True)