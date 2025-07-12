import os
from dotenv import load_dotenv, dotenv_values
class Config:
    def __init__(self):
        load_dotenv()
        self.env_path = ".env"
        self.env_vars = dotenv_values(self.env_path)
        # :white_tick: Load and split all 44+ keys
        self.api_keys = self._load_api_keys()
        if not self.api_keys:
            raise ValueError(":x: OPENAI_API_KEY is missing in .env")
        # :white_tick: Default Groq key (2nd key by index)
        self.groq_api_key = self.api_keys[1] if len(self.api_keys) >= 2 else self.api_keys[0]
        self.assistant_voice = self.env_vars.get("AssistantVoice", "en-IN-NeerjaExpressiveNeural")
        self.maintenance_password = self.env_vars.get("TOGGLE_PASSWORD")
        self.toggle_key = self.env_vars.get("TOGGLE_KEY", "off").lower()
        print(":closed_lock_with_key: Loaded API keys:", len(self.api_keys))
        print(":brain: Using Groq Key:", self.groq_api_key)
        self.static_dir = os.path.join(os.getcwd(), "static")
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs("Data", exist_ok=True)
        self.cleanup_temp_files()
    def _load_api_keys(self):
        keys = self.env_vars.get("OPENAI_API_KEY", "")
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
        self.env_vars = dotenv_values(self.env_path)
        self.toggle_key = self.env_vars.get("TOGGLE_KEY", "off").lower()
    def is_maintenance_on(self):
        return self.toggle_key == "on"
    def is_socket_on(self):
        return self.toggle_key == "off"
    def toggle_state(self, password: str) -> bool:
        self.reload_env()
        if password != self.maintenance_password:
            return False
        new_state = "on" if self.toggle_key == "off" else "off"
        self._set_env_value("TOGGLE_KEY", new_state)
        self.reload_env()
        return True
    def get(self, key, default=None):
        return self.env_vars.get(key, default)
    def _set_env_value(self, key: str, value: str):
        if not os.path.exists(self.env_path):
            return
        with open(self.env_path, "r") as f:
            lines = f.readlines()
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break
        if not key_found:
            lines.append(f"{key}={value}\n")
        with open(self.env_path, "w") as f:
            f.writelines(lines)