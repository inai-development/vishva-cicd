import os
import threading
from dotenv import dotenv_values, load_dotenv
from typing import Dict, List, Any, Optional
from uuid import uuid4
from threading import Lock
import time
from datetime import datetime, timedelta

load_dotenv()

env_vars = dotenv_values(".env")

# ✅ Load all API keys as a list (comma-separated)
primary_api_keys = [k.strip() for k in env_vars.get("OPENAI_API_KEY", "").split(",") if k.strip()]
if not primary_api_keys:
    raise ValueError("❌ No API keys found in OPENAI_API_KEY")

backup_api_keys: List[str] = [k.strip() for k in env_vars.get("BACKUP_OPENAI_API_KEY", "").split(",") if k.strip()]

# ✅ Configuration
MAX_USERS_PER_KEY = 5  # Adjustable
key_usage: Dict[str, int] = {key: 0 for key in (primary_api_keys+ backup_api_keys)}
user_sessions: Dict[str, Dict] = {}
transfer_log: List[Dict[str, Any]] = []
exhausted_keys: Dict[str, float] = {}
backup_rr_index: int = 0
lock = Lock()

class APIManager:
    def _init_(self):
        keys_raw = os.getenv("OPENAI_API_KEY", "")
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
print(f"🔐 Loaded {len(primary_api_keys)} API keys")
for i, key in enumerate(primary_api_keys):
    print(f"[{i+1:02d}] {key[:10]}...")

print(f"🔐 Loaded {len(backup_api_keys)} backup API keys")
for i, key in enumerate(backup_api_keys):
    print(f"[B{i+1:02d}] {key[:10]}...")

def _now() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def _is_key_available(key: str) -> bool:
    """Key must not be exhausted and must be tracked and not full."""
    if key in exhausted_keys:
        until = exhausted_keys[key]
        if until and until > time.time():
            return False
    if key not in key_usage:
        key_usage[key] = 0  
    if key in primary_api_keys:
        return key_usage[key] < MAX_USERS_PER_KEY

    # ✅ Backup keys → no limit
    return key in backup_api_keys

def _assign_to_user(user_id: str, key: str, task: str, pool: str) -> Dict:
    """Common assign logic, expects caller to be inside the lock."""
    global key_usage
    key_usage[key] += 1
    session_id = str(uuid4())
    user_sessions[user_id] = {
        "session_id": session_id,
        "api_key": key,
        "start_time": _now(),
        "task": task,
        "last_active": _now(),
        "sid": None,
        "pool": pool  # "primary" or "backup"
    }
    return {"api_key": key, "message": f"✅ Assigned successfully to {user_id} ({pool})"}

def _assign_from_primary(user_id: str, task: str) -> Optional[Dict]:
    for key in primary_api_keys:
        if _is_key_available(key):
            return _assign_to_user(user_id, key, task, pool="primary")
    return None

def _assign_from_backup_rr(user_id: str, task: str) -> Optional[Dict]:
    """Strict round-robin across backup_api_keys."""
    global backup_rr_index
    if not backup_api_keys:
        return None

    n = len(backup_api_keys)
    start = backup_rr_index

    for offset in range(n):
        idx = (start + offset) % n
        key = backup_api_keys[idx]
        if _is_key_available(key):
            # next call starts from the NEXT key
            backup_rr_index = (idx + 1) % n
            return _assign_to_user(user_id, key, task, pool="backup")

    return None

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

        # Try PRIMARY pool first
        res = _assign_from_primary(user_id, task)
        if res:
            return res

        # PRIMARY full → go to BACKUP pool (strict RR)
        res = _assign_from_backup_rr(user_id, task)
        if res:
            return res

        # Both pools full → maintenance
        return {
            "error": "🚫 All API keys (primary + backup) are fully used → Maintenance mode",
            "usage": key_usage.copy()
        }

# ✅ Update user session activity
def update_last_active(user_id: str, sid: str = None):
    with lock:
        if user_id in user_sessions:
            user_sessions[user_id]["last_active"] = _now()
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
        primary_usage = {k: key_usage.get(k, 0) for k in primary_api_keys}
        backup_usage = {k: key_usage.get(k, 0) for k in backup_api_keys}

        return {
            "primary_key_usage": primary_usage,
            "backup_key_usage": backup_usage,
            "total_key_usage": key_usage.copy(),
            "user_sessions": {
                user_id: {
                    **session,
                    "user_id": user_id
                }
                for user_id, session in user_sessions.items()
            },
            "exhausted_keys": list(exhausted_keys.keys()),
            "transfer_log": transfer_log[-200:],
            "primary_keys_count": len(primary_api_keys),
            "backup_keys_count": len(backup_api_keys),
            "backup_rr_index": backup_rr_index
        }


def mark_key_exhausted_for_user(user_id: str, cooldown_seconds: int = 0):
    with lock:
        session = user_sessions.get(user_id)
        if not session:
            return {"error": "⚠ No session found for user"}
        key = session["api_key"]
        _exhaust_key(key, cooldown_seconds=cooldown_seconds)

        # rotate this user immediately
        return _rotate_key_for_user_internal(
            user_id,
            task=session.get("task", "chat"),
            reason="rate_limit",
            keep_session=True
        )

def rotate_key_for_user(user_id: str, task: str = "chat", reason: str = "rate_limit") -> Dict:
    with lock:
        return _rotate_key_for_user_internal(user_id, task=task, reason=reason, keep_session=True)


def _rotate_key_for_user_internal(user_id: str, task: str, reason: str, keep_session: bool) -> Dict:
    with lock:
        session = user_sessions.get(user_id)

        old_key = None
        old_pool = None
        if session:
            old_key = session["api_key"]
            old_pool = session.get("pool", "primary")
            if old_key in key_usage and key_usage[old_key] > 0:
                key_usage[old_key] -= 1

        new_key = None
        new_pool = "primary"
        for k in primary_api_keys:
            if _is_key_available(k):
                new_key = k
                break

        if not new_key:
            # we want strict RR even for rotations when we switch to backup
            res = _assign_from_backup_rr(user_id, task)
            if res and "api_key" in res:
                new_key = res["api_key"]
                new_pool = "backup"
                # we already assigned & updated session inside _assign_from_backup_rr
                log_key_transfer(user_id, old_key, new_key, reason)
                return {"api_key": new_key, "message": "✅ Rotated key (backup)"}
            else:
                # rollback usage decrement on old key if we failed
                if old_key and old_key in key_usage:
                    key_usage[old_key] += 1
                return {"error": "🚫 No available keys (primary + backup) to rotate to"}
            
        key_usage[new_key] += 1

        if keep_session and session:
            session["api_key"] = new_key
            session["last_active"] = _now()
            session["task"] = task
            session["pool"] = new_pool
        else:
            session_id = str(uuid4())
            user_sessions[user_id] = {
                "session_id": session_id,
                "api_key": new_key,
                "start_time": _now(),
                "task": task,
                "last_active": _now(),
                "sid": session["sid"] if session else None,
                "pool": new_pool
            }

        log_key_transfer(user_id, old_key, new_key, reason)

        return {"api_key": new_key, "message": "✅ Rotated key"}

def exhaust_key_and_migrate_users(api_key: str, reason: str = "rate_limit", task: str = "chat") -> Dict:
    """
    Mark a key exhausted, remove it from api_keys & key_usage, and rotate every user on it.
    """
    with lock:
        # ✅ mark & remove key from pools
        exhausted_keys[api_key] = 0
        key_usage.pop(api_key, None)
        if api_key in primary_api_keys:
            primary_api_keys.remove(api_key)

        moved, failed = [], []
        affected = [uid for uid, s in user_sessions.items() if s["api_key"] == api_key]

        for user_id in affected:
            res = _rotate_key_for_user_internal(user_id, task=task, reason=reason, keep_session=True)
            if "api_key" in res:
                moved.append({"user_id": user_id, "to_key": res["api_key"]})
            else:
                failed.append(user_id)

        return {"moved": moved, "failed": failed, "exhausted": api_key}
    
def _exhaust_key(key: str, cooldown_seconds: int = 0):
    """Mark a key exhausted and remove it from primary/backup pools and key_usage."""
    exhausted_keys[key] = time.time() + cooldown_seconds if cooldown_seconds else 0
    key_usage.pop(key, None)

    # remove from pools if present
    if key in primary_api_keys:
        primary_api_keys.remove(key)
    if key in backup_api_keys:
        backup_api_keys.remove(key)


def get_user_key(user_id: str) -> Dict:
    with lock:
        session = user_sessions.get(user_id)
        if session:
            return {"api_key": session["api_key"]}
        return {"error": "❌ No key assigned"}
    




#     You now have two pools of keys:

# Primary pool: your 44 keys (OPENAI_API_KEY)

# Backup pool: extra 10 keys (OPENAI_API_KEY_BACKUP)

# Each key can handle MAX_USERS_PER_KEY = 5 → primary = 220 users.

# User 221+ will automatically be assigned from the backup pool.

# Only if both pools are full will the user get the “fully used / maintenance” response.