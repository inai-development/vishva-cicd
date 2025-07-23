# :white_check_mark: error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_400_BAD_REQUEST,HTTP_500_INTERNAL_SERVER_ERROR
# :white_check_mark: Custom Exceptions
class UserAlreadyExistsException(Exception):
    def __init__(self, message="User already exists"):
        self.message = message
class UsernameTakenException(Exception):
    def __init__(self, message="Username already taken"):
        self.message = message
class EmailTakenException(Exception):
    def __init__(self, message="Email already taken"):
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
# :white_check_mark: Custom Validation Error Handler (Updated)
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
        content={
            "status": False,
            "message": "Internal server error. Please try again later."
        },
    )
async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )
async def username_taken_handler(request: Request, exc: UsernameTakenException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )
async def email_taken_handler(request: Request, exc: EmailTakenException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )
async def phone_taken_handler(request: Request, exc: PhoneTakenException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )
async def photo_not_uploaded_handler(request: Request, exc: PhotoNotUploadedException):
    return JSONResponse(
        status_code=400,
        content={"status": False, "message": exc.message}
    )
async def invalid_gender_handler(request: Request, exc: InvalidGenderException):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"status": False, "message": exc.message}
    )