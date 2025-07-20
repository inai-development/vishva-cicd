from pydantic import BaseModel, validator
import re
class PhoneSignup(BaseModel):
    phone_number: str
    @validator("phone_number")
    def validate_phone_number(cls, v):
        # Must match +91 followed by exactly 10 digits
        if not re.fullmatch(r"\+91[0-9]{10}", v):
            raise ValueError("Phone number is not valid")
        return v
class ConfirmOTP(BaseModel):
    phone_number: str
    otp: str
