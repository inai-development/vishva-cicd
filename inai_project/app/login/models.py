from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from inai_project.database import Base
from sqlalchemy.sql import func

class LoginRecord(Base):
    __tablename__ = "login_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ✅ સુધારેલું
    email = Column(String, nullable=False)
    login_method = Column(String, nullable=True) 
    ip_address = Column(String, nullable=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now())
