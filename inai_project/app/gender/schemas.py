# app/gender/schemas.py

from pydantic import BaseModel

class GenderChoice(BaseModel):
    gender: str

class GenderResponse(BaseModel):
    user_id: int
    gender: str

    class Config:
        from_attributes = True  # Pydantic v2 fix for orm_mode
