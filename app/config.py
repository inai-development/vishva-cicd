import os
from dotenv import load_dotenv
from typing import List


class Config:
    def __init__(self, env_path: str = None):
        self.env_path = env_path or os.path.join(os.getcwd(), ".env")
        load_dotenv(self.env_path, override=True)
        self.env_vars = os.environ

        self.api_keys: List[str] = self._load_api_keys()
        if not self.api_keys:
            raise ValueError("❌ OPENAI_API_KEY is missing or empty in .env")

        self.groq_api_key = self.api_keys[1] if len(self.api_keys) >= 2 else self.api_keys[0]

        self.assistant_voice = self.get("AssistantVoice", "en-IN-NeerjaExpressiveNeural")
        self.voice_map = {
            "en": "en-IN-NeerjaExpressiveNeural",
            "hi": "hi-IN-SwaraNeural",
            "gu": "gu-IN-DhwaniNeural"
        }

        self.mode = self.get("ASSISTANT_MODE", "info")
        self.maintenance_password = self.get("TOGGLE_PASSWORD")
        self.toggle_key = self.get("TOGGLE_KEY", "off").lower()

        self.static_dir = os.path.join(os.getcwd(), "static")
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs("Data", exist_ok=True)

        self.cleanup_temp_files()

        print(f"🔐 Loaded API keys: {len(self.api_keys)}")
        print(f"🧠 Using Groq Key: {self.groq_api_key[:30]}...")

    def _load_api_keys(self) -> List[str]:
        keys = self.get("OPENAI_API_KEY", "")
        return [k.strip() for k in keys.split(",") if k.strip()]

    def cleanup_temp_files(self):
        try:
            for f in os.listdir("Data"):
                path = os.path.join("Data", f)
                if os.path.isfile(path) and path.lower().endswith(('.mp3', '.wav', '.aac')):
                    os.remove(path)
        except Exception as e:
            print(f"[Cleanup Error] {e}")

    def reload_env(self):
        load_dotenv(self.env_path, override=True)
        self.env_vars = os.environ
        self.toggle_key = self.get("TOGGLE_KEY", "off").lower()

    def is_maintenance_on(self) -> bool:
        return self.toggle_key == "on"

    def is_socket_on(self) -> bool:
        return self.toggle_key == "off"

    def toggle_state(self, password: str) -> bool:
        self.reload_env()
        if password != self.maintenance_password:
            return False
        new_state = "on" if self.toggle_key == "off" else "off"
        self._set_env_value("TOGGLE_KEY", new_state)
        self.reload_env()
        return True

    def get(self, key: str, default=None) -> str:
        return self.env_vars.get(key, default)

    def _set_env_value(self, key: str, value: str):
        if not os.path.exists(self.env_path):
            return

        with open(self.env_path, "r") as f:
            lines = f.readlines()

        key_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break

        if not key_found:
            lines.append(f"{key}={value}\n")

        with open(self.env_path, "w") as f:
            f.writelines(lines)
