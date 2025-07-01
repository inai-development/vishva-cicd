import os
from dotenv import dotenv_values
class Config:
    def __init__(self):
        env_vars = dotenv_values(".env")
        self.groq_api_key = env_vars.get("OPENAI_API_KEY")
        self.assistant_voice = env_vars.get("AssistantVoice", "en-IN-NeerjaExpressiveNeural")
        self.static_dir = os.path.join(os.getcwd(), "static")
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs("Data", exist_ok=True)
        self.cleanup_temp_files()
    def cleanup_temp_files(self):
        from os import listdir, remove
        from os.path import join, isfile
        try:
            for f in listdir("Data"):
                p = join("Data", f)
                if isfile(p) and p.lower().endswith(('.mp3', '.wav', '.aac')):
                    remove(p)
        except Exception as e:
            print(f"Cleanup error: {e}")