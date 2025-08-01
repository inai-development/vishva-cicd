from dotenv import dotenv_values
from typing import Dict
from uuid import uuid4
from threading import Lock
from datetime import datetime
from config import Config

config = Config()

api_keys = config.api_keys
if not api_keys:
    raise ValueError("❌ No API keys found in OPENAI_API_KEY")

user_sessions: Dict[str, Dict] = {}
key_usage_count: Dict[str, int] = {key: 0 for key in api_keys}
lock = Lock()

print(f"🔐 Loaded {len(api_keys)} API keys")
for i, key in enumerate(api_keys):
    print(f"[{i+1:02d}] {key[:10]}...")

def assign_key_to_user(user_id: str, task: str = "Unknown Task") -> Dict:
    with lock:
        if user_id in user_sessions:
            return {
                "api_key": user_sessions[user_id]["api_key"],
                "message": "Already assigned"
            }

        min_usage = min(key_usage_count.values())
        candidates = [key for key, count in key_usage_count.items() if count == min_usage]
        key = candidates[0]  

        key_usage_count[key] += 1
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
            "message": f"✅ Assigned least-loaded key {api_keys.index(key)+1} to {user_id}"
        }

def update_last_active(user_id: str, sid: str = None):
    with lock:
        if user_id in user_sessions:
            user_sessions[user_id]["last_active"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if sid:
                user_sessions[user_id]["sid"] = sid

def release_key_for_user(user_id: str) -> Dict:
    with lock:
        session = user_sessions.pop(user_id, None)
        if session:
            key = session["api_key"]
            if key in key_usage_count:
                key_usage_count[key] = max(0, key_usage_count[key] - 1)
            return {"message": f"✅ Released key for {user_id}"}
        return {"error": "⚠️ User session not found or already released"}

def get_monitor_data() -> Dict:
    with lock:
        return {
            "total_keys": len(api_keys),
            "key_usage": key_usage_count,
            "user_sessions": {
                user_id: {
                    **session,
                    "user_id": user_id
                }
                for user_id, session in user_sessions.items()
            }
        }
