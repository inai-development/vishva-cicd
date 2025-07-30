from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
import re

class UserCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    google_id: Optional[str] = None
    facebook_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r".+@(gmail|yahoo|outlook|hotmail|protonmail|icloud|aol|zoho|gmx|mail|yandex|me|fastmail|msn|live|rocketmail|rediffmail|inbox)\.com$", v):
            raise ValueError("Only major .com email providers are allowed.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v:
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

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match.")
        return v

    @model_validator(mode="after")
    def at_least_one_signup_method(cls, values):
        if not (
            values.password
            or values.google_id
            or values.facebook_id
        ):
            raise ValueError("At least one of password, google_id, or facebook_id must be provided.")
        return values
