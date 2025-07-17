import os
from dotenv import dotenv_values
from typing import Dict
from uuid import uuid4
from threading import Lock
from datetime import datetime

# ✅ Load and parse environment variables using dotenv_values (more reliable than os.getenv for .env files)
env_vars = dotenv_values(".env")

# ✅ Load all API keys as a list (comma-separated)
api_keys = [k.strip() for k in env_vars.get("OPENAI_API_KEY", "").split(",") if k.strip()]
if not api_keys:
    raise ValueError("❌ No API keys found in OPENAI_API_KEY")

# ✅ Configuration
MAX_USERS_PER_KEY = 5  # Adjustable
key_usage: Dict[str, int] = {key: 0 for key in api_keys}
user_sessions: Dict[str, Dict] = {}
lock = Lock()

# ✅ Debug print
print(f"🔐 Loaded {len(api_keys)} API keys")
for i, key in enumerate(api_keys):
    print(f"[{i+1:02d}] {key[:10]}...")

# ✅ Assign key to user (with auto fallback)
def assign_key_to_user(user_id: str, task: str = "Unknown Task") -> Dict:
    with lock:
        if user_id in user_sessions:
            return {
                "api_key": user_sessions[user_id]["api_key"],
                "message": "Already assigned"
            }
        for key in api_keys:
            if key_usage[key] < MAX_USERS_PER_KEY:
                key_usage[key] += 1
                session_id = str(uuid4())
                user_sessions[user_id] = {
                    "session_id": session_id,
                    "api_key": key,
                    "start_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    "task": task,
                    "last_active": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    "sid": None
                }
                return {
                    "api_key": key,
                    "message": f"✅ Assigned successfully to {user_id}"
                }

        return {
            "error": "🚫 All API keys are fully used",
            "usage": key_usage
        }

# ✅ Update user session activity
def update_last_active(user_id: str, sid: str = None):
    with lock:
        if user_id in user_sessions:
            user_sessions[user_id]["last_active"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if sid:
                user_sessions[user_id]["sid"] = sid

# ✅ Release a key when a user disconnects
def release_key_for_user(user_id: str) -> Dict:
    with lock:
        session = user_sessions.pop(user_id, None)
        if session:
            key = session["api_key"]
            if key in key_usage and key_usage[key] > 0:
                key_usage[key] -= 1
            return {"message": f"✅ Released key for {user_id}"}
        return {"error": "⚠️ User session not found or already released"}

# ✅ Admin: Monitor usage and sessions
def get_monitor_data() -> Dict:
    with lock:
        return {
            "key_usage": key_usage.copy(),
            "user_sessions": {
                user_id: {
                    **session,
                    "user_id": user_id
                }
                for user_id, session in user_sessions.items()
            }
        }
