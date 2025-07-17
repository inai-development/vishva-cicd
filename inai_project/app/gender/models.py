# app/gender/models.py

from sqlalchemy import Column, Integer, String
from inai_project.database import Base

class Gender(Base):
    __tablename__ = "genders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    gender = Column(String, nullable=False)
