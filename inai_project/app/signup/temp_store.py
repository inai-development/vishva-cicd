from datetime import datetime, timedelta
from inai_project.app.core.error_handler import (
    InvalidTokenException,
    OTPExpiredException
)

# In-memory OTP storage (reset on server restart)
pending_email_changes = {}  # { user_id: { "new_email": ..., "otp": ..., "expires_at": datetime } }
unverified_users = {}  # { email: { "otp": ..., "user_data": UserCreate } }
otp_store = {}
# ✅ Store OTP
def store_otp(user_id: int, new_email: str, otp: str):
    expires_at = datetime.utcnow() + timedelta(minutes=1)
    pending_email_changes[user_id] = {
        "new_email": new_email,
        "otp": otp,  # Ensure stored as string
        "expires_at": expires_at
    }

# ✅ Verify OTP with detailed exception
def verify_otp(user_id: int, otp: str):
    data = pending_email_changes.get(user_id)
    if not data:
        # raise InvalidTokenException("Invalid OTP")
        return False
    if str(data["otp"]) != str(otp):
        # raise InvalidTokenException("Invalid OTP")
        return False
    if data["expires_at"] < datetime.utcnow():
        # raise OTPExpiredException("OTP has expired. Please request a new one.")
        return False
    return True

# ✅ Remove OTP from store
def remove_otp(user_id: int):
    pending_email_changes.pop(user_id, None)

# ✅ Get new pending email (after successful OTP)
def get_pending_new_email(user_id: int):
    data = pending_email_changes.get(user_id)
    return data["new_email"] if data else None
