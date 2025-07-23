# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt
SECRET_KEY = "2f0083ed84ab135c53a8fd052923766866135c6e2e946a4f2aff080596b3382ce92c9106"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 30  # 30 years
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt