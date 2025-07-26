# app/profile/deps.py (or just reuse)
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from app.core.security import SECRET_KEY, ALGORITHM
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signup/login/")
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")
        return int(user_id_str)  # :white_check_mark: safe, now sub is id
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")