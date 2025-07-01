from openai import OpenAI

class ChatManager:
    def __init__(self, config, modes, database, logger):
        self.config = config
        self.modes = modes
        self.database = database
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

            reply = reply.strip()
            history.append({"role": "assistant", "content": reply})

            await self.database.save_message(user_id, mode, "user", message)
            await self.database.save_message(user_id, mode, "assistant", reply)

            return reply

        except Exception as e:
            self.logger.error(f"Groq error for user {user_id}: {e}")
            return "I'm having trouble responding right now."
