from inai_project.app.core.security import create_access_token, create_refresh_token
from inai_project.app.login import models as login_models
from inai_project.app.signup import models
from inai_project.app.signup.schemas import UserCreate
from sqlalchemy.orm import Session
import uuid

def handle_social_user(user_data: UserCreate, login_method: str, db: Session, client_ip: str) -> dict:
    email = user_data.email.strip().lower() if user_data.email else None
    was_new_user = False

    # Check if user exists by email or social_id
    user = db.query(models.User).filter(models.User.email == email).first() if email else None
    if not user and user_data.social_id:
        user = db.query(models.User).filter(models.User.social_id == user_data.social_id).first()

    if user:
        # Update existing user info
        user.username = user_data.username or user.username
        user.email = email or user.email
        user.picture = getattr(user_data, "picture", user.picture)
        user.gender = getattr(user_data, "gender", user.gender)
        user.phone_number = getattr(user_data, "phone_number", user.phone_number)
        db.commit()
        db.refresh(user)
    else:
        was_new_user = True
        # Handle social_id conflict
        social_id_to_save = user_data.social_id
        if db.query(models.User).filter(models.User.social_id == user_data.social_id).first():
            social_id_to_save = f"{user_data.social_id}_{uuid.uuid4().hex}"

        # Create new user
        user = models.User(
            username=user_data.username or (email.split("@")[0] if email else f"{login_method}_user"),
            email=email,
            hashed_password="",
            is_verified=True,
            login_method=login_method,
            social_id=social_id_to_save,
            picture=getattr(user_data, "picture", None),
            gender=getattr(user_data, "gender", None),
            phone_number=getattr(user_data, "phone_number", None),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create login record
    db.add(login_models.LoginRecord(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        login_method=login_method,
        ip_address=client_ip
    ))
    db.commit()

    # Generate tokens
    access_token = create_access_token({"sub": str(user.user_id)})
    refresh_token = create_refresh_token({"sub": str(user.user_id)})

    return {
        "status": True,
        "message": f"{login_method.capitalize()} {'signup' if was_new_user else 'login'} successful",
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "access_token": access_token,
        "refresh_token": refresh_token
    }
