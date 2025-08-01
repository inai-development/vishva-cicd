import os
import sys
from fastapi import FastAPI
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
load_dotenv()

from app.main import INAIApplication
from inai_project.main import AuthApplication
from inai_project.app.history.history_routes import router as history_router
from inai_project.app.history.history_manager import HistoryManager
from app.logger import Logger

logger = Logger()

history_manager = HistoryManager(
    db_url=os.getenv("DATABASE_URL"),
    bucket_name=os.getenv("AWS_BUCKET_NAME"),
    aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region=os.getenv("AWS_REGION"),
    logger=logger
)

app = FastAPI()

auth_app = AuthApplication().get_app()
app.mount("/auth", auth_app)

app.include_router(history_router, prefix="/history")

inai_app = INAIApplication(history_manager)
app.mount("/", inai_app.app)

import socketio
sio_app = socketio.ASGIApp(inai_app.sio, app, socketio_path="/socket.io")

@app.get("/test-db")
async def test_db():
    async with history_manager.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM conversations")
        return [dict(r) for r in rows]

@app.get("/health")
def health_check():
    return {"status": "INAI running at root :rocket:"}

@app.on_event("startup")
async def startup():
    await history_manager.init_db()
    app.state.history_manager = history_manager

@app.on_event("shutdown")
async def shutdown():
    await history_manager.close()

if __name__ == "__main__":
    import uvicorn
    host="0.0.0.0"
    port=8000
    logger.info(f"🚀 Starting INAI on http://{host}:{port}")
    uvicorn.run(sio_app, host=host, port=port , reload=True)