from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND

# ✅ Custom Exceptions
class UserAlreadyExistsException(Exception):
    def __init__(self, message="User already exists"):
        self.message = message

class UsernameTakenException(Exception):
    def __init__(self, message="Username already taken"):
        self.message = message

class InvalidOTPException(Exception):
    def __init__(self, message="Invalid OTP"):
        self.message = message

class UserNotFoundException(Exception):
    def __init__(self, message="User not found"):
        self.message = message

class EmailTakenException(Exception):
    def __init__(self, message="Email already taken"):
        self.message = message

class EmailNotVerifiedException(Exception):
    def __init__(self, message="Please verify your email before logging in."):
        self.message = message

class PhoneTakenException(Exception):
    def __init__(self, message="Phone number already taken"):
        self.message = message

class InvalidCredentialsException(Exception):
    def __init__(self, message="Invalid email or password"):
        self.message = message

class PhotoNotUploadedException(Exception):
    def __init__(self, message="Profile photo not uploaded"):
        self.message = message

class InvalidGenderException(Exception):
    def __init__(self, message="Gender must be male or female"):
        self.message = message

class OTPExpiredException(Exception):
    def __init__(self, message="OTP has expired. Please request a new one."):
        self.message = message

class NoOTPException(Exception):
    def __init__(self, message="No OTP found. Please request a new one."):
        self.message = message

class IncorrectOldPasswordException(Exception):
    def __init__(self, message="Old password is incorrect"):
        self.message = message

class PasswordMismatchException(Exception):
    def __init__(self, message="New passwords do not match"):
        self.message = message

class InvalidTokenException(Exception):
    def __init__(self, message="Invalid or expired token"):
        self.message = message

# ✅ Error Handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if exc.errors():
        err = exc.errors()[0]
        msg = err['msg']
        if msg.lower().startswith("value error, "):
            msg = msg[len("Value error, "):]
        loc = " -> ".join(str(l) for l in err['loc'])
        full_msg = msg
    else:
        full_msg = "Validation error"
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": full_msg},
    )

async def internal_server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": False, "message": "Internal server error. Please try again later."},
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "message": exc.detail},
    )

async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def username_taken_handler(request: Request, exc: UsernameTakenException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def invalid_otp_handler(request: Request, exc: InvalidOTPException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def user_not_found_exception_handler(request: Request, exc: UserNotFoundException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def email_taken_handler(request: Request, exc: EmailTakenException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def email_not_verified_handler(request: Request, exc: EmailNotVerifiedException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def phone_taken_handler(request: Request, exc: PhoneTakenException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def photo_not_uploaded_handler(request: Request, exc: PhotoNotUploadedException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def invalid_gender_handler(request: Request, exc: InvalidGenderException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def otp_expired_handler(request: Request, exc: OTPExpiredException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def no_otp_handler(request: Request, exc: NoOTPException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def incorrect_old_password_handler(request: Request, exc: IncorrectOldPasswordException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def password_mismatch_handler(request: Request, exc: PasswordMismatchException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def invalid_token_handler(request: Request, exc: InvalidTokenException):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"status": False, "message": exc.message})

async def user_not_found_handler(request: Request, exc: UserNotFoundException):
    return JSONResponse(status_code=HTTP_404_NOT_FOUND, content={"status": False, "message": exc.message})
