import os
<<<<<<< HEAD
from dotenv import dotenv_values
=======
from dotenv import load_dotenv
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
from typing import Dict
from uuid import uuid4
from threading import Lock
from datetime import datetime
<<<<<<< HEAD

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
=======
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
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
        if user_id in user_sessions:
            return {
                "api_key": user_sessions[user_id]["api_key"],
                "message": "Already assigned"
            }
<<<<<<< HEAD

=======
        # :large_green_circle: Assign from pool of available keys
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
        for key in api_keys:
            if key_usage[key] < MAX_USERS_PER_KEY:
                key_usage[key] += 1
                session_id = str(uuid4())
                user_sessions[user_id] = {
                    "session_id": session_id,
                    "api_key": key,
                    "start_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
<<<<<<< HEAD
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
=======
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
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
def release_key_for_user(user_id: str) -> Dict:
    with lock:
        session = user_sessions.pop(user_id, None)
        if session:
            key = session["api_key"]
            if key in key_usage and key_usage[key] > 0:
                key_usage[key] -= 1
<<<<<<< HEAD
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
=======
            return {"message": f"Released key for {user_id}"}
        return {"error": "User session not found or already released"}
def get_monitor_data():
    with lock:
        return key_usage.copy(), user_sessions.copy()
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
