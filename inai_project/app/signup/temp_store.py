from datetime import datetime, timedelta

# ✅ Add this line at the top to fix your import
unverified_users = {}  # { email: { "otp": ..., "user_data": UserCreate } }
pending_email_changes = {} 
otp_store = {}  # { email: { "otp": ..., "expires_at": datetime } }

def store_otp(user_id, new_email, otp):
    expires_at = datetime.utcnow() + timedelta(minutes=1)
    pending_email_changes[user_id] = {
        "new_email": new_email,
        "otp": otp,
        "expires_at": expires_at
    }
    
def get_otp_expiry(user_id: int):
    data = pending_email_changes.get(user_id)
    return data["expires_at"] if data else None 

def verify_otp(user_id: int, otp: str) -> bool:
    data = pending_email_changes.get(user_id)
    if not data:
        return False
    if data["otp"] != otp:
        return False
    if data["expires_at"] < datetime.utcnow():
        return False
    return True

def remove_otp(user_id: int):
    pending_email_changes.pop(user_id, None)

def get_pending_new_email(user_id: int):
    data = pending_email_changes.get(user_id)
    return data["new_email"] if data else None