import aiosqlite

class Database:
    def __init__(self):
        self.db_path = "chat_history.db"

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    mode TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_message(self, user_id, mode, role, content):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO chat_history (user_id, mode, role, content) VALUES (?, ?, ?, ?)",
                (user_id, mode, role, content)
            )
            await db.commit()
