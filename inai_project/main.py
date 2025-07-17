from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from inai_project.app.signup.auth_routes import router as signup_router
from inai_project.app.login.routes import router as login_router
from inai_project.app.profile.routes import router as profile_router
from inai_project.app.gender.routes import router as gender_router
from inai_project.app.phone_number.otp_routes import router as phone_otp_router

# DB Models
from inai_project.database import engine
from inai_project.app.signup import models as signup_models
from inai_project.app.phone_number import models as phone_models
from inai_project.app.profile import models as profile_models
from inai_project.app.gender import models as gender_models
from inai_project.app.login import models as login_models

# ✅ FastAPI app config
app = FastAPI(
    title="INAI FastAPI Auth API",
    description="Signup, Login, JWT, Phone OTP, Profile Upload with JWT",
    version="1.0.0"
)

# ✅ CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register all routers
app.include_router(signup_router, prefix="/api/auth/signup", tags=["Signup"])
app.include_router(login_router, prefix="/api/auth/login", tags=["Login"])  # ✅ NEW
app.include_router(phone_otp_router, prefix="/api/phone", tags=["Phone OTP"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(gender_router, prefix="/api/gender", tags=["Gender"])

# ✅ Create all tables
signup_models.Base.metadata.create_all(bind=engine)
phone_models.Base.metadata.create_all(bind=engine)
profile_models.Base.metadata.create_all(bind=engine)
gender_models.Base.metadata.create_all(bind=engine)
login_models.Base.metadata.create_all(bind=engine)  # ✅ NEW

# ✅ Health check
@app.get("/")
def root():
    return {"message": "🚀 FastAPI Auth API Running!"}  


