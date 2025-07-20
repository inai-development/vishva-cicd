# serve.py

import os
import sys
from fastapi import FastAPI
from dotenv import load_dotenv

# --- Step 1: Path setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))

# --- Step 2: Load environment variables ---
load_dotenv()

# --- Step 3: Import sub-apps and routers ---
from app.main import INAIApplication, AuthApplication
from inai_project.app.history.history_routes import router as history_router
from inai_project.app.history.history_manager import HistoryManager
from app.logger import Logger

# --- Step 4: Logger ---
logger = Logger()

# --- Step 5: History Manager setup ---
history_manager = HistoryManager(
    db_url=os.getenv("DATABASE_URL"),
    bucket_name=os.getenv("AWS_BUCKET_NAME"),
    aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region=os.getenv("AWS_REGION"),
    logger=logger
)

# --- Step 6: Create main FastAPI app ---
app = FastAPI()

# --- Step 7: Mount the Auth sub-app ---
auth_app = AuthApplication().get_app()
app.mount("/auth", auth_app)

# --- Step 8: Mount the INAI socket app ---
inai = INAIApplication(history_manager)
app.mount("/", inai.asgi_app)


# --- Step 9: Include History APIs directly ---
app.include_router(history_router, prefix="/history")


# --- Step 10: Startup and Shutdown Events for History Manager ---
@app.on_event("startup")
async def startup():
    await history_manager.init_db()
    app.state.history_manager = history_manager


@app.on_event("shutdown")
async def shutdown():
    await history_manager.close()


# --- Step 11: Export for Uvicorn ---
sio_app = app
