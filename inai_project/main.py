from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.signup.auth_routes import router as signup_router
from app.phone_number.otp_routes import router as phone_otp_router
from app.profile.routes import router as profile_router
from app.gender.routes import router as gender_router
from app.login.routes import router as login_router  # :white_check_mark: NEW: Login
from database import engine
from app.signup import models as signup_models
from app.phone_number import models as phone_models
from app.profile import models as profile_models
from app.gender import models as gender_models
from app.login import models as login_models  # :white_check_mark: NEW: LoginRecord
from app.core.error_handler import (
    validation_exception_handler,
    internal_server_error_handler,
    user_already_exists_handler,
    username_taken_handler,
    email_taken_handler,
    phone_taken_handler,
    photo_not_uploaded_handler,
    invalid_credentials_handler,
    invalid_gender_handler,
    UserAlreadyExistsException,
    UsernameTakenException,
    EmailTakenException,
    PhoneTakenException,
    InvalidCredentialsException,
    PhotoNotUploadedException,
    InvalidGenderException
)
from fastapi.exceptions import RequestValidationError
# :white_check_mark: FastAPI app config
app = FastAPI(
    title="INAI FastAPI Auth API",
    description="Signup, Login, JWT, Phone OTP, Profile Upload with JWT",
    version="1.0.0"
)
# :white_check_mark: CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# :white_check_mark: Register all routers
app.include_router(signup_router, prefix="/api/auth/signup", tags=["Signup"])
app.include_router(login_router, prefix="/api/auth/login", tags=["Login"])  # :white_check_mark: NEW
app.include_router(phone_otp_router, prefix="/api/phone", tags=["Phone OTP"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(gender_router, prefix="/api/gender", tags=["Gender"])
# Register the handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(UserAlreadyExistsException, user_already_exists_handler)
app.add_exception_handler(UsernameTakenException, username_taken_handler)
app.add_exception_handler(EmailTakenException, email_taken_handler)
app.add_exception_handler(PhoneTakenException, phone_taken_handler)
app.add_exception_handler(InvalidCredentialsException, invalid_credentials_handler)
app.add_exception_handler(Exception, internal_server_error_handler)  # :white_check_mark: 500 handler
app.add_exception_handler(PhotoNotUploadedException, photo_not_uploaded_handler)
app.add_exception_handler(InvalidGenderException, invalid_gender_handler)
# :white_check_mark: Create all tables
signup_models.Base.metadata.create_all(bind=engine)
phone_models.Base.metadata.create_all(bind=engine)
profile_models.Base.metadata.create_all(bind=engine)
gender_models.Base.metadata.create_all(bind=engine)
login_models.Base.metadata.create_all(bind=engine)  # :white_check_mark: NEW
# :white_check_mark: Health check
@app.get("/")
def root():
    return {"message": ":rocket: FastAPI Auth API Running!"}
