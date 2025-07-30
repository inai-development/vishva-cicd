import re
from openai import OpenAI
from .key_manager import (
    get_user_key,
    assign_key_to_user,
    mark_key_exhausted_for_user,
    rotate_key_for_user
)

class ChatManager:
    def __init__(self, config, modes, logger):
        self.config = config
        self.modes = modes
        self.logger = logger
        self.chat_histories = {}

        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.groq_api_key
        )

    async def chat_with_groq(self, user_id: str, mode: str, message: str) -> str:
        try:
            history = self.chat_histories.setdefault(user_id, {}).setdefault(mode, [])
            history.append({"role": "user", "content": message})
            messages = [{"role": "system", "content": self.modes.modes[mode]}, *history[-10:]]

            key_data = get_user_key(user_id)
            if "error" in key_data:
                key_data = assign_key_to_user(user_id, task="chat")
            if "error" in key_data:
                return "🚫 All API keys are exhausted. Try again later."

            self.client.api_key = key_data["api_key"]

            try:
                completion = self.client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=messages,
                    temperature=0.7
                )
            except Exception as e:
                if hasattr(e, "status_code") and e.status_code == 429:
                    self.logger.warning(f"🚫 Rate limit hit for user {user_id} -> rotating key")
                    mark_key_exhausted_for_user(user_id)
                    new_key_data = rotate_key_for_user(user_id, task="chat")
                    if "api_key" in new_key_data:
                        self.client.api_key = new_key_data["api_key"]
                        completion = self.client.chat.completions.create(
                            model="llama3-70b-8192",
                            messages=messages,
                            temperature=0.7
                        )
                    else:
                        return "🚫 All API keys are exhausted. Try again later."
                else:
                    raise
                
            reply = completion.choices[0].message.content or "I'm sorry, I couldn't think of a good answer."
            reply = re.sub(r"(?<!\*)\*[^*\n]+\*(?!\*)", "", reply).strip()
            history.append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            self.logger.error(f"Groq error for user {user_id}: {e}")
            return "⚠ I'm having trouble responding right now."
