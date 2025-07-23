from pydantic import BaseModel, EmailStr, validator
import re

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("email")
    def validate_email(cls, v):
        if not re.match(r".+@(gmail|yahoo|outlook)\.com$", v):
            raise ValueError("Only Gmail, Yahoo, or Outlook emails are allowed.")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*()_+=\-{}\[\]:;\"'<>,.?/]", v):
            raise ValueError("Password must contain at least one special character.")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match.")
        return v
