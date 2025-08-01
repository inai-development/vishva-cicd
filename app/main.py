from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
import os
import logging
import socketio
from .key_manager import assign_key_to_user, release_key_for_user, get_monitor_data
from .logger import Logger
from .config import Config
from .modes import ChatModes
from .tts import TextToSpeech
from .session import UserSessionManager
from .chat import ChatManager
from .speech import SpeechRecognition
from .socket import SocketHandler 
from inai_project.app.history.history_manager import HistoryManager
from inai_project.app.history import history_routes
from inai_project.app.signup import models as signup_models
from inai_project.database import engine

signup_models.Base.metadata.create_all(bind=engine)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MainApp")


DB_URL = "your_postgres_url"
BUCKET_NAME = "your-s3-bucket"
AWS_ACCESS_KEY = "your-access-key"
AWS_SECRET_KEY = "your-secret-key"
REGION = "ap-south-1"
app = FastAPI()
@app.on_event("startup")
async def startup():
    app.state.history_manager = HistoryManager(
        db_url=DB_URL,
        bucket_name=BUCKET_NAME,
        aws_access_key=AWS_ACCESS_KEY,
        aws_secret_key=AWS_SECRET_KEY,
        region=REGION,
        logger=logger
    )
    await app.state.history_manager.init_db()
@app.on_event("shutdown")
async def shutdown():
    await app.state.history_manager.close()

load_dotenv()
class ToggleRequest(BaseModel):
    password: str
class INAIApplication:
    def __init__(self, history_manager):
        self.logger = Logger()
        self.config = Config()
        self.modes = ChatModes()
        self.history = history_manager
        self.tts = TextToSpeech(self.config, self.logger)
        self.chat_manager = ChatManager(self.config, self.modes, self.logger)
        self.speech_recognition = SpeechRecognition(self.logger)
        self.session_manager = UserSessionManager(self.logger)
        self.templates = Jinja2Templates(directory="templates")
        self.sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
        self.app = app
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.asgi_app = socketio.ASGIApp(self.sio, self.app, socketio_path="/socket.io")
        self.socket_handler = SocketHandler(
            sio=self.sio,
            session_manager=self.session_manager,
            config=self.config,
            tts=self.tts,
            chat_manager=self.chat_manager,
            speech_recognition=self.speech_recognition,
            history=self.history,
            modes=self.modes,
            logger=self.logger
        )
        self.setup_routes()
        if self.config.is_socket_on():
            self.socket_handler.setup_socket_events()
        else:
            self.logger.warning(":warning: Socket is OFF due to maintenance mode")
 
    def setup_routes(self):
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        self.app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
        self.app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
        os.makedirs("Data", exist_ok=True)
        self.app.mount("/data", StaticFiles(directory="Data"), name="data")
        @self.app.get("/chat", response_class=HTMLResponse)
        async def index():
            frontend_index = os.path.join(frontend_dir, "index.html")
            if os.path.exists(frontend_index):
                return FileResponse(frontend_index)
            try:
                with open(os.path.join(self.config.static_dir, "index.html"), "r", encoding='utf-8') as f:
                    return HTMLResponse(content=f.read())
            except FileNotFoundError:
                return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)

        @self.app.get("/status")
        async def get_status():
            self.config.reload_env()
            return {
                "maintenance": self.config.is_maintenance_on(),
                "socket": self.config.is_socket_on()
            }
 
        @self.app.get("/INAI520", response_class=HTMLResponse)
        async def admin_panel(request: Request):
            error = request.query_params.get("error")
            return self.templates.TemplateResponse("login.html", {"request": request, "error": error})
 
        @self.app.post("/INAI520", response_class=RedirectResponse)
        async def verify_admin(req: Request):
            form = await req.form()
            password = form.get("password")
            if password != os.getenv("TOGGLE_PASSWORD"):
                return RedirectResponse(url="/INAI520?error=1", status_code=303)
            response = RedirectResponse(url="/INAI520/home", status_code=303)
            response.set_cookie("INAI520", password)
            return response
  
        @self.app.get("/audio/{filename}", response_class=FileResponse)
        async def serve_audio_file(filename: str):
            file_path = os.path.abspath(os.path.join("Data", filename))
            logging.info(f"Request for audio file: {file_path}")
            if not os.path.isfile(file_path):
                logging.warning(f"File not found: {file_path}")
                raise HTTPException(status_code=404, detail="Audio file not found")
            if filename.endswith(".wav"):
                return FileResponse(file_path, media_type="audio/wav")
            elif filename.endswith(".mp3"):
                return FileResponse(file_path, media_type="audio/mpeg")
            else:
                raise HTTPException(status_code=400, detail="Unsupported audio format")
  
        @self.app.get("/viseme/{filename}", response_class=FileResponse)
        async def serve_viseme_file(filename: str):
            if not filename.endswith(".json"):
                raise HTTPException(status_code=400, detail="Only .json files are supported here")
            file_path = os.path.join("Data", filename)
            if not os.path.isfile(file_path):
                raise HTTPException(status_code=404, detail="JSON file not found")
            return FileResponse(file_path, media_type="application/json")
   
        @self.app.get("/INAI520/home", response_class=HTMLResponse)
        async def admin_home(request: Request):
            if request.cookies.get("INAI520") != os.getenv("TOGGLE_PASSWORD"):
                return RedirectResponse(url="/INAI520")
            return self.templates.TemplateResponse("admin_panel.html", {"request": request})
   
        @self.app.get("/INAI520/maintenance", response_class=HTMLResponse)
        async def admin_maintenance(request: Request):
            if request.cookies.get("INAI520") != os.getenv("TOGGLE_PASSWORD"):
                return RedirectResponse(url="/INAI520")
            return self.templates.TemplateResponse("maintenance.html", {
                "request": request,
                "socket": self.config.is_socket_on(),
                "maintenance": self.config.is_maintenance_on(),
            })
  
        @self.app.get("/INAI520/monitor", response_class=HTMLResponse)
        async def monitor_ui(request: Request):
            if request.cookies.get("INAI520") != os.getenv("TOGGLE_PASSWORD"):
                return RedirectResponse(url="/INAI520")
            
            data = get_monitor_data()
            request.state.timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            return self.templates.TemplateResponse("monitor.html", {
                "request": request,
                "user_sessions": data["user_sessions"],
                "key_usage": data["key_usage"]
            })
   
        @self.app.post("/toggle")
        async def toggle(req: ToggleRequest):
            if not self.config.toggle_state(req.password):
                raise HTTPException(status_code=403, detail=":x: Invalid password")
            self.logger.info(":repeat: Maintenance toggle triggered")
            await self.socket_handler.disconnect_all_users()
            if self.config.is_socket_on():
                self.socket_handler.setup_socket_events()
                self.logger.info(":white_check_mark: Socket events re-enabled after maintenance OFF")
            mode = "MAINTENANCE" if self.config.is_maintenance_on() else "NORMAL"
            return {
                "message": f":repeat: Mode switched to {mode}",
                "maintenance": self.config.is_maintenance_on(),
                "socket": self.config.is_socket_on()
            }
  
        @self.app.post("/login")
        async def login(req: ToggleRequest):
            if req.password != os.getenv("TOGGLE_PASSWORD"):
                raise HTTPException(status_code=403, detail=":x: Invalid password")
            return {
                "maintenance": self.config.is_maintenance_on(),
                "socket": self.config.is_socket_on()
            }
  
        @self.app.post("/assign-key")
        async def assign_key(request: Request):
            data = await request.json()
            user_id = data.get("user_id")
            task = data.get("task", "Unknown")
            return assign_key_to_user(user_id, task)
  
        @self.app.post("/release-key")
        async def release_key(request: Request):
            data = await request.json()
            user_id = data.get("user_id")
            return release_key_for_user(user_id)