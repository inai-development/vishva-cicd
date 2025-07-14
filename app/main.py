from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import socketio
import os
import asyncio
from asyncio.exceptions import CancelledError
import random
from datetime import datetime

# Custom modules
from .key_manager import assign_key_to_user, release_key_for_user, get_monitor_data, update_last_active
from .logger import Logger
from .config import Config
from .modes import ChatModes
from .database import Database
from .tts import TextToSpeech
from .session import UserSessionManager
from .chat import ChatManager
from .speech import SpeechRecognition

# Load .env variables
load_dotenv()

class ToggleRequest(BaseModel):
    password: str

class INAIApplication:
    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        self.modes = ChatModes()
        self.database = Database()
        self.tts = TextToSpeech(self.config, self.logger)
        self.chat_manager = ChatManager(self.config, self.modes, self.database, self.logger)
        self.speech_recognition = SpeechRecognition(self.logger)
        self.session_manager = UserSessionManager(self.logger)
        self.templates = Jinja2Templates(directory="templates")

        self.sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
        self.app = FastAPI()
        self.asgi_app = socketio.ASGIApp(self.sio, self.app)

        self.setup_routes()

        if self.config.is_socket_on():
            self.setup_socket_events()
        else:
            self.logger.warning("⚠ Socket is OFF due to maintenance mode")

    def setup_routes(self):
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        self.app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

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
                "key_usage": data["key_usage"],
                "user_sessions": data["user_sessions"]
            })

        @self.app.post("/toggle")
        async def toggle(req: ToggleRequest):
            if not self.config.toggle_state(req.password):
                raise HTTPException(status_code=403, detail="❌ Invalid password")

            self.logger.info("🔁 Maintenance toggle triggered")
            await self.disconnect_all_users()

            if self.config.is_socket_on():
                self.setup_socket_events()
                self.logger.info("✅ Socket events re-enabled after maintenance OFF")

            mode = "MAINTENANCE" if self.config.is_maintenance_on() else "NORMAL"
            return {
                "message": f"🔁 Mode switched to {mode}",
                "maintenance": self.config.is_maintenance_on(),
                "socket": self.config.is_socket_on()
            }

        @self.app.post("/login")
        async def login(req: ToggleRequest):
            if req.password != os.getenv("TOGGLE_PASSWORD"):
                raise HTTPException(status_code=403, detail="❌ Invalid password")
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

    async def disconnect_all_users(self):
        for sid in list(self.session_manager.get_all_sids()):
            try:
                await self.sio.emit("response", {
                    "text": "🚧 INAI has switched to maintenance mode. Disconnecting...",
                    "audio": ""
                }, room=sid)
                await self.sio.disconnect(sid)
            except Exception as e:
                self.logger.error(f"Failed to disconnect SID {sid}: {e}")
        self.session_manager.clear_all_sessions()

    def setup_socket_events(self):
        @self.sio.event
        async def connect(sid, environ):
            self.logger.info(f"[Socket Connected] {sid}")
            return True

        @self.sio.event
        async def disconnect(sid):
            user_to_cleanup = None
            for user_id, session in self.session_manager.user_sessions.items():
                if session['sid'] == sid:
                    user_to_cleanup = user_id
                    break
            if user_to_cleanup:
                release_key_for_user(user_to_cleanup)
                self.session_manager.cleanup_user_session(user_to_cleanup)
                self.logger.info(f"🔌 Disconnected: {user_to_cleanup}")

        @self.sio.event
        async def register_user(sid, data):
            user_id = data.get("username", "default_user").replace(" ", "_").lower()
            self.session_manager.create_user_session(user_id, sid)
            key_data = assign_key_to_user(user_id, task="chat")
            if "api_key" in key_data:
                update_last_active(user_id, sid)
                self.logger.info(f"✅ User {user_id} registered with SID {sid}")
            else:
                await self.sio.emit("response", {
                    "text": "🚫 INAI is full (220 users max). Try again later.",
                    "audio": ""
                }, room=sid)
                await self.sio.disconnect(sid)

        @self.sio.event
        async def user_message(sid, data):
            await self.handle_user_message(sid, data)

        @self.sio.event
        async def user_audio(sid, data):
            await self.handle_user_audio(sid, data)

        @self.sio.event
        async def stop_response(sid, data):
            user_id = data.get("username", "default_user").replace(" ", "_").lower()
            self.logger.info(f"Stop response requested by user: {user_id}")
            self.session_manager.cancel_user_tasks(user_id)

    async def handle_user_message(self, sid, data):
        self.config.reload_env()
        if self.config.is_maintenance_on():
            await self.sio.emit("response", {
                "text": "🚧 INAI is under maintenance. Please try again later.",
                "audio": ""
            }, room=sid)
            await self.sio.disconnect(sid)
            return

        user_id = data.get("username", "default_user").replace(" ", "_").lower()
        mode = data.get("mode", "friend")
        query = data.get("text", "").strip()

        if user_id not in self.session_manager.user_sessions:
            self.session_manager.create_user_session(user_id, sid)

        session = self.session_manager.get_user_session(user_id)
        if not session:
            return

        session['current_mode'] = mode

        if not query:
            await self.sio.emit("response", {"text": "Please say something.", "audio": ""}, room=sid)
            return

        self.session_manager.stop_current_tts(user_id)
        query_lower = query.lower()

        mode_change_phrases = {
            "friend mode": "friend",
            "info mode": "info",
            "elder mode": "elder",
            "love mode": "love",
        }

        for phrase, target_mode in mode_change_phrases.items():
            if phrase in query_lower and target_mode != mode:
                session['current_mode'] = target_mode
                await self.sio.emit("mode_change", {"mode": target_mode}, room=sid)
                confirm_text = self.modes.mode_confirmations[target_mode]
                self.session_manager.cancel_user_tasks(user_id)

                if target_mode == "info":
                    await self.sio.emit("response", {"text": confirm_text, "audio": ""}, room=sid)
                    await self.handle_streaming_tts_for_info(user_id, confirm_text, sid)
                else:
                    confirm_audio = await self.tts.generate_tts(confirm_text, user_id, target_mode)
                    await self.sio.emit("response", {"text": confirm_text, "audio": confirm_audio}, room=sid)
                return

        if mode != "info" and any(word in query_lower for word in ["stop", "wait", "ruko", "arre", "sun"]):
            self.session_manager.cancel_user_tasks(user_id)
            self.session_manager.stop_current_tts(user_id)
            reply = random.choice(self.modes.interrupt_responses[mode])
            audio = await self.tts.generate_tts(reply, user_id, mode)
            await self.sio.emit("response", {"text": reply, "audio": audio}, room=sid)
            return

        self.session_manager.cancel_user_tasks(user_id)

        async def process_response():
            try:
                response = await self.chat_manager.chat_with_groq(user_id, mode, query)
                if mode == "info":
                    await self.sio.emit("response", {"text": response, "audio": ""}, room=sid)
                    await self.handle_streaming_tts_for_info(user_id, response, sid)
                else:
                    audio = await self.tts.generate_tts(response, user_id, mode)
                    await self.sio.emit("response", {"text": response, "audio": audio}, room=sid)
            except CancelledError:
                self.logger.info(f"Processing cancelled for {user_id}")
            except Exception as e:
                self.logger.error(f"Error for {user_id}: {e}")
                await self.sio.emit("response", {"text": "⚠ I faced an error. Try again.", "audio": ""}, room=sid)

        task = asyncio.create_task(process_response())
        self.session_manager.add_task(user_id, task)

    async def handle_streaming_tts_for_info(self, user_id, response, sid):
        try:
            chunks = self.tts.split_into_sentence_chunks(response, max_sentences_per_chunk=2)
            await self.sio.emit("streaming_status", {"can_stop": True}, room=sid)
            for i, chunk in enumerate(chunks):
                if asyncio.current_task().cancelled():
                    break
                session = self.session_manager.get_user_session(user_id)
                if not session:
                    break
                audio_data = await self.tts.generate_tts_chunk(chunk, i)
                if audio_data:
                    await self.sio.emit("streaming_audio", {
                        "text": chunk,
                        "audio": audio_data,
                        "chunk_id": i,
                        "is_final": i == len(chunks) - 1
                    }, room=sid)
                    await asyncio.sleep(1.5)
            await self.sio.emit("streaming_status", {"can_stop": False}, room=sid)
        except Exception as e:
            self.logger.error(f"Streaming error for {user_id}: {e}")

    async def handle_user_audio(self, sid, data):
        self.config.reload_env()
        if self.config.is_maintenance_on():
            await self.sio.emit("response", {
                "text": "🚧 INAI is under maintenance.",
                "audio": ""
            }, room=sid)
            await self.sio.disconnect(sid)
            return

        user_id = data.get("username", "default_user").replace(" ", "_").lower()
        mode = data.get("mode", "friend")
        audio_base64 = data.get("audio", "")

        if not audio_base64:
            await self.sio.emit("response", {"text": "Audio was empty.", "audio": ""}, room=sid)
            return

        if user_id not in self.session_manager.user_sessions:
            self.session_manager.create_user_session(user_id, sid)

        self.session_manager.stop_current_tts(user_id)
        query = await self.speech_recognition.process_audio(audio_base64)

        if "error" in query.lower():
            await self.sio.emit("response", {"text": query, "audio": ""}, room=sid)
            return

        await self.handle_user_message(sid, {
            "username": user_id,
            "mode": mode,
            "text": query
        })

    def run(self, host="0.0.0.0", port=8000):
        import uvicorn
        self.logger.info(f"🚀 Starting INAI on http://{host}:{port}")
        uvicorn.run(self.asgi_app, host=host, port=port, reload=True)
