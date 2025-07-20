# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt
SECRET_KEY = "django-insecure-ysw4d=_8m^3(3hdo**uo8lb3c@-l2@k)p_g@)ja6qzm!p0ces3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 30  # 30 years
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt