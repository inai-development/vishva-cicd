import asyncio
import base64
import random
from .key_manager import assign_key_to_user, release_key_for_user, update_last_active
from .lip_sync import generate_lip_sync_json
import os

class SocketHandler:
    def __init__(self, sio, session_manager, config, tts, chat_manager, speech_recognition, history, modes, logger):
        self.sio = sio
        self.session_manager = session_manager
        self.config = config
        self.tts = tts
        self.chat_manager = chat_manager
        self.speech_recognition = speech_recognition
        self.history = history
        self.modes = modes
        self.logger = logger

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
            user_id = str(data.get("user_id", "default_user")).replace(" ", "_").lower()
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
            user_id = str(data.get("user_id", "default_user")).replace(" ", "_").lower()
            self.logger.info(f"Stop response requested by user: {user_id}")
            self.session_manager.cancel_user_tasks(user_id)

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

    async def handle_user_message(self, sid, data):
        self.config.reload_env()
        if self.config.is_maintenance_on():
            await self.sio.emit("response", {
                "text": "🚧 INAI is under maintenance. Please try again later.",
                "audio": ""
            }, room=sid)
            await self.sio.disconnect(sid)
            return

        user_id = str(data.get("user_id", "default_user")).replace(" ", "_").lower()
        mode = data.get("mode", "friend")
        query = data.get("text", "").strip()

        audio_path = os.path.join("Data", f"{user_id}.wav")
        text_path = os.path.join("Data", f"{user_id}.txt")
        json_path = os.path.join("Data", f"{user_id}.json")
        json_url = f"/viseme/{user_id}.json"
        audio_url = f"/audio/{user_id}.wav"

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
                self.session_manager.cancel_user_tasks(user_id)
                return 

        if mode != "info" and any(word in query_lower for word in ["stop", "wait", "ruko", "arre", "sun"]):
            self.session_manager.cancel_user_tasks(user_id)
            self.session_manager.stop_current_tts(user_id)
            reply = random.choice(self.modes.interrupt_responses[mode])
            audio = await self.tts.generate_tts(reply, user_id, mode)
            await self.sio.emit("response", {"text": reply, "audio": audio}, room=sid)
            return

        self.session_manager.cancel_user_tasks(user_id)
        
        conversation_id = await self.history.get_or_create_conversation(user_id, mode)
        await self.history.save_message(conversation_id, "user", query)

        async def process_response():
            try:
                response = await self.chat_manager.chat_with_groq(user_id, mode, query)
                await self.history.save_message(conversation_id, "assistant", response)
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(response)

                if mode == "info":
                    await self.sio.emit("response", {
                        "text": response,
                        "audio": "",
                        "visemes": ""
                    }, room=sid)
                    await self.handle_streaming_tts_for_info(user_id, response, sid)
                else:
                    audio = await self.tts.generate_tts(response, user_id, mode)
                    with open(audio_path, "wb") as f:
                        f.write(base64.b64decode(audio))
                    generate_lip_sync_json(audio_path, text_path, json_path)
                    await self.sio.emit("response", {
                        "text": response,
                        "audio": audio,
                        "visemes": json_url
                    }, room=sid)

            except asyncio.CancelledError:
                self.logger.info(f"Processing cancelled for {user_id}")
            except Exception as e:
                self.logger.error(f"Error for {user_id}: {e}")
                await self.sio.emit("response", {
                    "text": "⚠ I faced an error. Try again.",
                    "audio": "",
                    "visemes": ""
                }, room=sid)

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

        user_id = str(data.get("user_id", "default_user")).replace(" ", "_").lower()
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
            "user_id": user_id,
            "mode": mode,
            "text": query
        })