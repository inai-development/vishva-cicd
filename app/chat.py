from openai import OpenAI
import re

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
            completion = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.7
            )

            reply = completion.choices[0].message.content
            if not reply:
                reply = "I'm sorry, I couldn't think of a good answer."


            reply = re.sub(r"(?<!\*)\*[^*\n]+\*(?!\*)", "", reply).strip()

            history.append({"role": "assistant", "content": reply})

            return reply

        except Exception as e:
            self.logger.error(f"Groq error for user {user_id}: {e}")
            return "⚠️ I had trouble to understanding. Can you ask again?"
