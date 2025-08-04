from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from inai_project.database import Base

class LoginRecord(Base):
    __tablename__ = "login_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    username = Column(String, nullable=False) 
    email = Column(String, nullable=False)
    login_method = Column(String, nullable=False)
    ip_address = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
