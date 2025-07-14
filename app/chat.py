from openai import OpenAI
import re
<<<<<<< HEAD

=======
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
class ChatManager:
    def __init__(self, config, modes, database, logger):
        self.config = config
        self.modes = modes
        self.database = database
        self.logger = logger
        self.chat_histories = {}
<<<<<<< HEAD

        # ✅ Initialize Groq client with key from config
=======
        # :white_tick: Use key from config (2nd key by default)
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.groq_api_key
        )
<<<<<<< HEAD

    async def chat_with_groq(self, user_id: str, mode: str, message: str) -> str:
        try:
            # ✅ Retrieve or create user history
            history = self.chat_histories.setdefault(user_id, {}).setdefault(mode, [])
            history.append({"role": "user", "content": message})

            # ✅ Prepare messages (system prompt + last 10 exchanges)
            messages = [{"role": "system", "content": self.modes.modes[mode]}, *history[-10:]]

            # ✅ Call Groq LLaMA 3 model
=======
    async def chat_with_groq(self, user_id: str, mode: str, message: str) -> str:
        try:
            # Get or create history
            history = self.chat_histories.setdefault(user_id, {}).setdefault(mode, [])
            history.append({"role": "user", "content": message})
            # Include last 10 messages
            messages = [{"role": "system", "content": self.modes.modes[mode]}, *history[-10:]]
            # Request completion
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
            completion = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.7
            )
<<<<<<< HEAD

            reply = completion.choices[0].message.content
            if not reply:
                reply = "I'm sorry, I couldn't think of a good answer."

            # ✅ Clean up formatting (e.g. markdown)
            reply = re.sub(r"(?<!\*)\*[^*\n]+\*(?!\*)", "", reply).strip()

            # ✅ Update history with assistant's reply
            history.append({"role": "assistant", "content": reply})

            # ✅ Persist messages
            await self.database.save_message(user_id, mode, "user", message)
            await self.database.save_message(user_id, mode, "assistant", reply)

            return reply

        except Exception as e:
            self.logger.error(f"Groq error for user {user_id}: {e}")
            return "⚠️ I'm having trouble responding right now."
=======
            reply = completion.choices[0].message.content
            if not reply:
                reply = "I'm sorry, I couldn't think of a good answer."
            # Clean reply formatting (e.g., remove *markdown*)
            reply = re.sub(r"(?<!\*)\*[^*\n]+\*(?!\*)", "", reply).strip()

            
            # Append assistant reply to history
            history.append({"role": "assistant", "content": reply})
            # Save to database
            await self.database.save_message(user_id, mode, "user", message)
            await self.database.save_message(user_id, mode, "assistant", reply)
            return reply
        except Exception as e:
            self.logger.error(f"Groq error for user {user_id}: {e}")
            return ":warning: I'm having trouble responding right now."
>>>>>>> b92b2d756284e822d1aff095435e50ec9b3ee36d
