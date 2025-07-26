import os
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Routers
from inai_project.app.signup.auth_routes import router as signup_router
from inai_project.app.login.routes import router as login_router
from inai_project.app.profile.routes import router as profile_router
from inai_project.app.gender.routes import router as gender_router
from inai_project.app.phone_number.otp_routes import router as otp_router
from inai_project.app.history.history_routes import router as history_router

# Error handlers and exceptions
from inai_project.app.core.error_handler import (
    validation_exception_handler,
    internal_server_error_handler,
    invalid_gender_handler,
    user_already_exists_handler,
    username_taken_handler,
    email_taken_handler,
    phone_taken_handler,
    invalid_credentials_handler,
    photo_not_uploaded_handler,
    InvalidGenderException,
    UserAlreadyExistsException,
    UsernameTakenException,
    EmailTakenException,
    PhoneTakenException,
    InvalidCredentialsException,
    PhotoNotUploadedException,
)

# History manager and logger
from inai_project.app.history.history_manager import HistoryManager
from app.logger import Logger

# Database setup
from inai_project.database import SessionLocal, engine, Base

logger = Logger()


class AuthApplication:
    def __init__(self):
        self.app = FastAPI(
            title="INAI FastAPI Auth API",
            description="Signup, Login, JWT, Phone OTP, Profile Upload with JWT",
            version="1.0.0"
        )
        self.history_manager = self.setup_history_manager()
        self.create_tables()
        self.test_db_connection()
        self.register_exception_handlers()
        self.register_routes()

    def register_exception_handlers(self):
        self.app.add_exception_handler(RequestValidationError, validation_exception_handler)
        self.app.add_exception_handler(Exception, internal_server_error_handler)
        self.app.add_exception_handler(InvalidGenderException, invalid_gender_handler)
        self.app.add_exception_handler(UserAlreadyExistsException, user_already_exists_handler)
        self.app.add_exception_handler(UsernameTakenException, username_taken_handler)
        self.app.add_exception_handler(EmailTakenException, email_taken_handler)
        self.app.add_exception_handler(PhoneTakenException, phone_taken_handler)
        self.app.add_exception_handler(InvalidCredentialsException, invalid_credentials_handler)
        self.app.add_exception_handler(PhotoNotUploadedException, photo_not_uploaded_handler)

    def register_routes(self):
        self.app.include_router(signup_router, prefix="/signup", tags=["Signup"])
        self.app.include_router(login_router, prefix="/login", tags=["Login"])
        self.app.include_router(profile_router, prefix="/profile", tags=["Profile"])
        self.app.include_router(gender_router, prefix="/gender", tags=["Gender"])
        self.app.include_router(otp_router, prefix="/phone", tags=["Phone"])
        self.app.include_router(otp_router, prefix="/otp", tags=["OTP"])
        self.app.include_router(history_router, prefix="/history", tags=["History"])

        @self.app.get("/")
        def health_check():
            return {"message": ":rocket: FastAPI Auth API Running!"}

    def setup_history_manager(self):
        return HistoryManager(
            db_url=os.getenv("DATABASE_URL"),
            bucket_name=os.getenv("AWS_BUCKET_NAME"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION"),
            logger=logger
        )

    def create_tables(self):
        Base.metadata.create_all(bind=engine)

    def test_db_connection(self):
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            print("✅ PostgreSQL Connected Successfully!")
        except OperationalError as e:
            print("❌ PostgreSQL Connection Failed:", e)
        finally:
            db.close()

    def get_app(self):
        return self.app
