import os
import threading
from dotenv import dotenv_values, load_dotenv
from typing import Dict, List, Any
from uuid import uuid4
from threading import Lock
import time
from datetime import datetime, timedelta

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
# Track exhausted keys with optional expiry (epoch seconds). If you don't use cooldowns, store 0.
exhausted_keys: Dict[str, float] = {}

# Log every transfer (user -> new key) with timestamps
transfer_log: List[Dict[str, Any]] = []

load_dotenv()

class APIManager:
    def __init__(self):
        keys_raw = os.getenv("OPENAI_API_KEYS", "")
        self.api_keys = [key.strip() for key in keys_raw.split(",") if key.strip()]
        self.key_limit = int(os.getenv("KEY_LIMIT", "100"))

        self.key_usage: Dict[str, int] = {key: 0 for key in self.api_keys}
        self.exhausted_keys: set = set()
        self.lock = threading.Lock()
        self.start_daily_reset_thread()

    def mark_exhausted(self, key: str):
        with self.lock:
            self.exhausted_keys.add(key)
            print(f"❌ Marked exhausted: {key}")

    def increment_usage(self, key: str):
        with self.lock:
            self.key_usage[key] += 1
            if self.key_usage[key] >= self.key_limit:
                self.mark_exhausted(key)

    def is_exhausted(self, key: str) -> bool:
        return key in self.exhausted_keys
    
    def start_daily_reset_thread(self):
        def reset_loop():
            while True:
                now = datetime.now()
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                seconds_until_reset = (next_midnight - now).total_seconds()
                time.sleep(seconds_until_reset)
                with self.lock:
                    self.key_usage = {key: 0 for key in self.api_keys}
                    self.exhausted_keys.clear()
                    print("🔄 API keys reset at midnight.")
        threading.Thread(target=reset_loop, daemon=True).start()

# ✅ Debug print
print(f"🔐 Loaded {len(api_keys)} API keys")
for i, key in enumerate(api_keys):
    print(f"[{i+1:02d}] {key[:10]}...")

def log_key_transfer(user_id: str, from_key: str | None, to_key: str | None, reason: str = "rate_limit"):
    transfer_log.append({
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "user_id": user_id,
        "from_key": from_key,
        "to_key": to_key,
        "reason": reason,
    })

def get_exhausted_keys() -> List[str]:
    # uses your global exhausted_keys dict
    return list(exhausted_keys.keys())
    
def get_active_keys_per_user() -> Dict[str, str]:
    with lock:
        return {user_id: session["api_key"] for user_id, session in user_sessions.items()}
transfer_log: List[Dict[str, Any]] = []  # already declared above, keep it global

def get_transfer_log() -> List[Dict[str, Any]]:
    # return latest 200 to avoid bloat
    return transfer_log[-200:]

# ✅ Assign key to user (with auto fallback)
def assign_key_to_user(user_id: str, task: str = "Unknown Task") -> Dict:
    with lock:
        if user_id in user_sessions:
            return {
                "api_key": user_sessions[user_id]["api_key"],
                "message": "Already assigned"
            }

        # ✅ never consider exhausted or removed keys
        for key in list(api_keys):
            if key in exhausted_keys or key not in key_usage:
                continue
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
        return {"error": "⚠ User session not found or already released"}

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
            },
            "exhausted_keys": list(exhausted_keys.keys()),  # ✅ add this
            "transfer_log": transfer_log 
        }
    
def mark_key_exhausted_for_user(user_id: str, cooldown_seconds: int = 0):
    with lock:
        session = user_sessions.get(user_id)
        if not session:
            return {"error": "⚠ No session found for user"}
        key = session["api_key"]
        # mark + remove key fully
        exhausted_keys[key] = time.time() + cooldown_seconds if cooldown_seconds else 0
        key_usage.pop(key, None)
        if key in api_keys:
            api_keys.remove(key)
        # rotate this user immediately
        return _rotate_key_for_user_internal(user_id, task=session.get("task", "chat"), reason="rate_limit", keep_session=True)

def rotate_key_for_user(user_id: str, task: str = "chat", reason: str = "rate_limit") -> Dict:
    with lock:
        return _rotate_key_for_user_internal(user_id, task=task, reason=reason, keep_session=True)


def _rotate_key_for_user_internal(user_id: str, task: str, reason: str, keep_session: bool) -> Dict:
    session = user_sessions.get(user_id)

    old_key = None
    if session:
        old_key = session["api_key"]
        if old_key in key_usage and key_usage[old_key] > 0:
            key_usage[old_key] -= 1

    # ✅ pick only non-exhausted, still-tracked keys
    new_key = None
    for k in list(api_keys):
        if k in exhausted_keys or k not in key_usage:
            continue
        if key_usage[k] < MAX_USERS_PER_KEY:
            new_key = k
            break

    if not new_key:
        # rollback usage decrement on old key if we failed
        if old_key and old_key in key_usage:
            key_usage[old_key] += 1
        return {"error": "🚫 No available keys to rotate to"}

    key_usage[new_key] += 1

    if keep_session and session:
        session["api_key"] = new_key
        session["last_active"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        session["task"] = task
    else:
        session_id = str(uuid4())
        user_sessions[user_id] = {
            "session_id": session_id,
            "api_key": new_key,
            "start_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "task": task,
            "last_active": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "sid": session["sid"] if session else None
        }

    transfer_log.append({
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "user_id": user_id,
        "from_key": old_key,
        "to_key": new_key,
        "reason": reason
    })

    return {"api_key": new_key, "message": "✅ Rotated key"}

def exhaust_key_and_migrate_users(api_key: str, reason: str = "rate_limit", task: str = "chat") -> Dict:
    """
    Mark a key exhausted, remove it from api_keys & key_usage, and rotate every user on it.
    """
    with lock:
        # ✅ mark & remove key from pools
        exhausted_keys[api_key] = 0
        key_usage.pop(api_key, None)
        if api_key in api_keys:
            api_keys.remove(api_key)

        moved, failed = [], []
        affected = [uid for uid, s in user_sessions.items() if s["api_key"] == api_key]

        for user_id in affected:
            res = _rotate_key_for_user_internal(user_id, task=task, reason=reason, keep_session=True)
            if "api_key" in res:
                moved.append({"user_id": user_id, "to_key": res["api_key"]})
            else:
                failed.append(user_id)

        return {"moved": moved, "failed": failed, "exhausted": api_key}


def get_user_key(user_id: str) -> Dict:
    with lock:
        session = user_sessions.get(user_id)
        if session:
            return {"api_key": session["api_key"]}
        return {"error": "❌ No key assigned"}