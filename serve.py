# serve.py
import os
import sys
from fastapi import FastAPI
from dotenv import load_dotenv
# Step 1: Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
# Step 2: Load environment variables
load_dotenv()
# Step 3: Import
from app.main import INAIApplication
from inai_project.main import AuthApplication
from inai_project.app.history.history_routes import router as history_router
from inai_project.app.history.history_manager import HistoryManager
from app.logger import Logger
# Step 4: Logger
logger = Logger()
# Step 5: History Manager
history_manager = HistoryManager(
    db_url=os.getenv("DATABASE_URL"),
    bucket_name=os.getenv("AWS_BUCKET_NAME"),
    aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region=os.getenv("AWS_REGION"),
    logger=logger
)
# Step 6: Create root FastAPI app
app = FastAPI()
# Step 7: Mount Auth routes FIRST (specific routes before general ones)
auth_app = AuthApplication().get_app()
app.mount("/auth", auth_app)

# Step 8: Include History API BEFORE mounting INAI app
app.include_router(history_router, prefix="/history")
# Step 9: Create INAI app but DON'T mount it yet - we'll handle routes manually
inai_app = INAIApplication(history_manager)
# Step 10: Mount the INAI app's internal FastAPI app (not the ASGI app)
# This gives us access to /chat, /status, /audio/{filename}, etc.
app.mount("/", inai_app.app)
# Step 11: Handle Socket.IO separately by creating a combined ASGI app
# Import socketio to create the final ASGI app
import socketio
# Create the final ASGI app that combines FastAPI + Socket.IO
sio_app = socketio.ASGIApp(inai_app.sio, app, socketio_path="/socket.io")
# Optional Test DB route (add this to the main app before mounting)
@app.get("/test-db")
async def test_db():
    async with history_manager.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM conversations")
        return [dict(r) for r in rows]
# Health check
@app.get("/health")
def health_check():
    return {"status": "INAI running at root :rocket:"}
# Step 12: Lifecycle events
@app.on_event("startup")
async def startup():
    await history_manager.init_db()
    app.state.history_manager = history_manager
@app.on_event("shutdown")
async def shutdown():
    await history_manager.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(sio_app, host="0.0.0.0", port=8000)
    # uvicorn.run(sio_app, host="0.0.0.0", port=4210)