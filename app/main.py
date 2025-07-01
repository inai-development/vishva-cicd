# # app/main.py
# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import HTMLResponse
# import socketio
# from .logger import Logger
# from .config import Config
# from .modes import ChatModes
# from .database import Database
# from .tts import TextToSpeech
# from .session import UserSessionManager
# from .chat import ChatManager
# from .speech import SpeechRecognition
# import os
# import asyncio
# from asyncio.exceptions import CancelledError

# class INAIApplication:
#     def __init__(self):
#         self.logger = Logger()
#         self.config = Config()
#         self.modes = ChatModes()
#         self.database = Database()
#         self.tts = TextToSpeech(self.config, self.logger)
#         self.chat_manager = ChatManager(self.config, self.modes, self.database, self.logger)
#         self.speech_recognition = SpeechRecognition(self.logger)
#         self.session_manager = UserSessionManager(self.logger)

#         self.sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
#         self.app = FastAPI()
#         self.asgi_app = socketio.ASGIApp(self.sio, self.app)

#         self.setup_routes()
#         self.setup_socket_events()

#     def setup_routes(self):
#         self.app.mount("/static", StaticFiles(directory=self.config.static_dir), name="static")

#         @self.app.on_event("startup")
#         async def startup():
#             await self.database.init_db()
#             self.config.cleanup_temp_files()

#         @self.app.get("/", response_class=HTMLResponse)
#         async def index():
#             try:
#                 with open(os.path.join(self.config.static_dir, "index.html"), "r", encoding='utf-8') as f:
#                     return HTMLResponse(content=f.read())
#             except FileNotFoundError:
#                 return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)

#     def setup_socket_events(self):
#         @self.sio.event
#         async def connect(sid, environ):
#             self.logger.info(f"Connected: {sid}")
#             return True

#         @self.sio.event
#         async def disconnect(sid):
#             user_to_cleanup = None
#             for user_id, session in self.session_manager.user_sessions.items():
#                 if session['sid'] == sid:
#                     user_to_cleanup = user_id
#                     break
#             if user_to_cleanup:
#                 self.session_manager.cleanup_user_session(user_to_cleanup)
#                 self.logger.info(f"Cleaned up session for user: {user_to_cleanup}")
#             self.logger.info(f"Disconnected: {sid}")

#         @self.sio.event
#         async def register_user(sid, data):
#             user_id = data.get("username", "default_user").replace(" ", "_").lower()
#             self.session_manager.create_user_session(user_id, sid)
#             self.logger.info(f"User {user_id} registered with SID {sid}")

#         @self.sio.event
#         async def user_message(sid, data):
#             await self.handle_user_message(sid, data)

#         @self.sio.event
#         async def user_audio(sid, data):
#             await self.handle_user_audio(sid, data)

#         @self.sio.event
#         async def stop_response(sid, data):
#             user_id = data.get("username", "default_user").replace(" ", "_").lower()
#             self.logger.info(f"Stop response requested for user: {user_id}")
#             self.session_manager.cancel_user_tasks(user_id)

#     async def handle_user_message(self, sid, data):
#         # This would contain your complete message logic
#         pass

#     async def handle_user_audio(self, sid, data):
#         # This would contain your audio processing logic
#         pass

#     def run(self, host="0.0.0.0", port=8000):
#         import uvicorn
#         self.logger.info(f"Starting INAI on http://{host}:{port}")
#         uvicorn.run(self.asgi_app, host=host, port=port)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import socketio
from .logger import Logger
from .config import Config
from .modes import ChatModes
from .database import Database
from .tts import TextToSpeech
from .session import UserSessionManager
from .chat import ChatManager
from .speech import SpeechRecognition
import os
import asyncio
from asyncio.exceptions import CancelledError
import random

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

        self.sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
        self.app = FastAPI()
        self.asgi_app = socketio.ASGIApp(self.sio, self.app)

        self.setup_routes()
        self.setup_socket_events()

    def setup_routes(self):
        self.app.mount("/static", StaticFiles(directory=self.config.static_dir), name="static")

        @self.app.on_event("startup")
        async def startup():
            await self.database.init_db()
            self.config.cleanup_temp_files()

        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            try:
                with open(os.path.join(self.config.static_dir, "index.html"), "r", encoding='utf-8') as f:
                    return HTMLResponse(content=f.read())
            except FileNotFoundError:
                return HTMLResponse(content="<h1>UI not found</h1>", status_code=404)

    def setup_socket_events(self):
        @self.sio.event
        async def connect(sid, environ):
            self.logger.info(f"Connected: {sid}")
            return True

        @self.sio.event
        async def disconnect(sid):
            user_to_cleanup = None
            for user_id, session in self.session_manager.user_sessions.items():
                if session['sid'] == sid:
                    user_to_cleanup = user_id
                    break

            if user_to_cleanup:
                self.session_manager.cleanup_user_session(user_to_cleanup)
                self.logger.info(f"Cleaned up session for user: {user_to_cleanup}")

            self.logger.info(f"Disconnected: {sid}")

        @self.sio.event
        async def register_user(sid, data):
            user_id = data.get("username", "default_user").replace(" ", "_").lower()
            self.session_manager.create_user_session(user_id, sid)
            self.logger.info(f"User {user_id} registered with SID {sid}")

        @self.sio.event
        async def user_message(sid, data):
            await self.handle_user_message(sid, data)

        @self.sio.event
        async def user_audio(sid, data):
            await self.handle_user_audio(sid, data)

        @self.sio.event
        async def stop_response(sid, data):
            user_id = data.get("username", "default_user").replace(" ", "_").lower()
            self.logger.info(f"Stop response requested for user: {user_id}")
            self.session_manager.cancel_user_tasks(user_id)

    async def handle_streaming_tts_for_info(self, user_id: str, response: str, sid: str):
        try:
            chunks = self.tts.split_into_sentence_chunks(response, max_sentences_per_chunk=2)
            
            await self.sio.emit("streaming_status", {"can_stop": True}, room=sid)

            for i, chunk in enumerate(chunks):
                await asyncio.sleep(0)
                current_task = asyncio.current_task()
                if current_task and current_task.cancelled():
                    self.logger.info(f"Streaming TTS task cancelled for user {user_id} during chunk {i}.")
                    break

                session = self.session_manager.get_user_session(user_id)
                if not session:
                    self.logger.warning(f"Session not found for user {user_id} during streaming TTS.")
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
            if not audio_data:
                self.logger.warning(f"Chunk {i} generated no audio, skipping.")
            else:
                self.logger.info(f"Sending chunk {i} to frontend.")

                
        except CancelledError:
            self.logger.info(f"Streaming TTS task for user {user_id} was explicitly cancelled.")
        except Exception as e:
            self.logger.error(f"Streaming TTS error for user {user_id}: {e}")
            await self.sio.emit("streaming_status", {"can_stop": False}, room=sid)


    async def handle_user_message(self, sid, data):
        user_id = data.get("username", "default_user").replace(" ", "_").lower()
        mode = data.get("mode", "friend")
        query = data.get("text", "").strip()

        if user_id not in self.session_manager.user_sessions:
            self.session_manager.create_user_session(user_id, sid)

        session = self.session_manager.get_user_session(user_id)
        if not session:
            self.logger.error(f"Session not found for user {user_id} after creation attempt.")
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

        new_mode_from_query = None
        for phrase, target_mode in mode_change_phrases.items():
            if phrase in query_lower:
                new_mode_from_query = target_mode
                break

        if new_mode_from_query and new_mode_from_query != mode:
            self.logger.info(f"Mode change detected from query for {user_id}: {mode} -> {new_mode_from_query}")
            session['current_mode'] = new_mode_from_query
            await self.sio.emit("mode_change", {"mode": new_mode_from_query}, room=sid)

            confirm_text = self.modes.mode_confirmations[new_mode_from_query]
            self.session_manager.cancel_user_tasks(user_id)

            if new_mode_from_query == "info":
                await self.sio.emit("response", {"text": confirm_text, "audio": ""}, room=sid)
                task = asyncio.create_task(self.handle_streaming_tts_for_info(user_id, confirm_text, sid))
            else:
                confirm_audio = await self.tts.generate_tts(confirm_text, user_id, new_mode_from_query)
                await self.sio.emit("response", {"text": confirm_text, "audio": confirm_audio}, room=sid)
            return

        if mode != "info" and any(word in query_lower for word in ["stop", "wait", "ruko", "arre", "sun"]):
            self.session_manager.cancel_user_tasks(user_id)
            self.session_manager.stop_current_tts(user_id)
            reply = random.choice(self.modes.interrupt_responses[mode])
            audio = await self.tts.generate_tts(reply, user_id, mode)
            await self.sio.emit("response", {"text": reply, "audio": audio}, room=sid)
            self.logger.info(f"User {user_id} interrupted in {mode} mode.")
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
                self.logger.info(f"Response processing task cancelled for user {user_id}")
            except Exception as e:
                self.logger.error(f"Error during response processing for user {user_id}: {e}")
                await self.sio.emit("response", {"text": "I encountered an error. Please try again.", "audio": ""}, room=sid)

        task = asyncio.create_task(process_response())
        self.session_manager.add_task(user_id, task)

    async def handle_user_audio(self, sid, data):
        self.logger.info("Received user_audio")
        user_id = data.get("username", "default_user").replace(" ", "_").lower()
        current_mode = data.get("mode", "friend")
        audio_base64 = data.get("audio", "")

        if user_id not in self.session_manager.user_sessions:
            self.session_manager.create_user_session(user_id, sid)

        if not audio_base64:
            await self.sio.emit("response", {"text": "Audio was empty.", "audio": ""}, room=sid)
            return

        self.session_manager.stop_current_tts(user_id)

        query = await self.speech_recognition.process_audio(audio_base64)

        if "error" in query.lower():
            await self.sio.emit("response", {"text": query, "audio": ""}, room=sid)
            return

        await self.handle_user_message(sid, {
            "username": user_id,
            "mode": current_mode,
            "text": query
        })

    def run(self, host="0.0.0.0", port=8000):
        import uvicorn
        self.logger.info(f"Starting INAI application on http://{host}:{port}")
        uvicorn.run(self.asgi_app, host=host, port=port, reload=True)
