import os
from dotenv import load_dotenv
from typing import Dict
from uuid import uuid4
from threading import Lock
from datetime import datetime
# :white_tick: Load .env file
load_dotenv()
# :white_tick: Load all 44+ API keys from comma-separated string
api_keys = [k.strip() for k in os.getenv("OPENAI_API_KEY", "").split(",") if k.strip()]
if not api_keys:
    raise ValueError(":x: No API keys found in OPENAI_API_KEY")
# :white_tick: Limit per key (you can increase if needed)
MAX_USERS_PER_KEY = 5
# :white_tick: Track how many users use each key
key_usage: Dict[str, int] = {key: 0 for key in api_keys}
# :white_tick: Track sessions per user
user_sessions: Dict[str, Dict] = {}
# :white_tick: Lock for thread-safe access
lock = Lock()
def assign_key_to_user(user_id: str, task: str = "Unknown Task") -> Dict:
    with lock:
        # :large_green_circle: Already has a session? return same key
        if user_id in user_sessions:
            return {
                "api_key": user_sessions[user_id]["api_key"],
                "message": "Already assigned"
            }
        # :large_green_circle: Assign from pool of available keys
        for key in api_keys:
            if key_usage[key] < MAX_USERS_PER_KEY:
                key_usage[key] += 1
                session_id = str(uuid4())
                user_sessions[user_id] = {
                    "session_id": session_id,
                    "api_key": key,
                    "start_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    "task": task
                }
                return {
                    "api_key": key,
                    "message": "Assigned successfully"
                }
        # :x: No keys available
        return {
            "error": "All API keys are fully used",
            "usage": key_usage
        }
def release_key_for_user(user_id: str) -> Dict:
    with lock:
        session = user_sessions.pop(user_id, None)
        if session:
            key = session["api_key"]
            if key in key_usage and key_usage[key] > 0:
                key_usage[key] -= 1
            return {"message": f"Released key for {user_id}"}
        return {"error": "User session not found or already released"}
def get_monitor_data():
    with lock:
        return key_usage.copy(), user_sessions.copy()