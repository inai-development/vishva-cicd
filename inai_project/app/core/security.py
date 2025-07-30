# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from pathlib import Path

# ✅ Load .env from the project root (3 levels up from this file)
BASE_DIR = Path(__file__).resolve().parents[2]
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# ✅ DEBUG: Print to confirm .env is found
print("ENV FILE FOUND:", env_path, env_path.exists())

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
print("SECRET_KEY LOADED:", repr(SECRET_KEY))  # Remove in production

# ✅ Config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 30  # 30 years

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    if not SECRET_KEY or not isinstance(SECRET_KEY, str) or SECRET_KEY.strip() == "":
        raise Exception("SECRET_KEY not loaded correctly from .env file")

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
