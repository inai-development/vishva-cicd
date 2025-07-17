# serve.py
import sys
import os
from fastapi import FastAPI

# Ensure app module is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))

# Import INAI and Auth apps
from app.main import INAIApplication, AuthApplication

# Create root app
app = FastAPI()

# Mount auth app at /auth
auth_app = AuthApplication().get_app()
app.mount("/auth", auth_app)  # This means: /auth/api/auth/signup/register

# Mount INAI app at /
inai = INAIApplication()
sio_app = inai.asgi_app
app.mount("/", sio_app)

# Final export
sio_app = app
