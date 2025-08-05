from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
import re

class UserCreate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    login_method: Optional[str] = "manual"  # manual, google, facebook
    social_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r".+@(gmail|yahoo|outlook|hotmail|protonmail|icloud|aol|zoho|gmx|mail|yandex|me|fastmail|msn|live|rocketmail|rediffmail|inbox)\.com$", v):
            raise ValueError("Only major .com email providers are allowed.")
        return v

    @model_validator(mode="after")
    def validate_all(self):
        if self.login_method not in ["manual", "google", "facebook"]:
            raise ValueError("Invalid login method. Must be manual, google, or facebook.")

        if self.login_method == "manual":
            if not all([self.username, self.email, self.password, self.confirm_password]):
                raise ValueError("All fields are required for manual signup.")

            # Password validations
            if len(self.password) < 8:
                raise ValueError("Password must be at least 8 characters long.")
            if not re.search(r"[A-Z]", self.password):
                raise ValueError("Password must contain at least one uppercase letter.")
            if not re.search(r"[a-z]", self.password):
                raise ValueError("Password must contain at least one lowercase letter.")
            if not re.search(r"[0-9]", self.password):
                raise ValueError("Password must contain at least one digit.")
            if not re.search(r"[!@#$%^&*()_+=\-{}\[\]:;\"'<>,.?/]", self.password):
                raise ValueError("Password must contain at least one special character.")

            if self.password != self.confirm_password:
                raise ValueError("Passwords do not match.")

        elif self.login_method in ["google", "facebook"]:
            if not all([self.username, self.email, self.social_id]):
                raise ValueError(f"username, email, and social_id are required for {self.login_method} login.")

        return self


class ConfirmOTP(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr
