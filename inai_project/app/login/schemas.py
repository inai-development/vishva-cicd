from pydantic import BaseModel, EmailStr, validator, StringConstraints
from typing import Annotated , Optional, Literal
import re


class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    google_id: Optional[str] = None
    facebook_id: Optional[str] = None
    login_method: Literal["manual", "google", "facebook"] = "manual"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    

class ForgotPasswordEmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: Annotated[str, StringConstraints(min_length=4, max_length=8)]

class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

    @validator("new_password")
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
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match.")
        return v