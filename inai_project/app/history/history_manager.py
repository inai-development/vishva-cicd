import asyncpg
import boto3
import uuid
from datetime import datetime
import os
from pathlib import Path
from typing import List, Dict, Optional
import logging
import ssl

logger = logging.getLogger("HistoryManager")
logging.basicConfig(level=logging.INFO)


class HistoryManager:
    def __init__(self, db_url: str, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str, logger):
        self.db_url = db_url
        self.pool = None
        self.logger = logger
        self.bucket_name = bucket_name
        self.region = region
        try:
            self.s3 = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            self.logger.info("S3 client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            self.s3 = None

    async def init_db(self):
        try:
            ssl_path = Path(__file__).resolve().parent.parent.parent.parent / "certs" / "rds-ca.pem"

            # Step 2: If file exists, create SSL context
            ssl_context = None
            if ssl_path.exists():
                ssl_context = ssl.create_default_context(cafile=str(ssl_path))
                self.logger.info(f"SSL context created with: {ssl_path}")
            else:
                self.logger.warning(f"SSL certificate not found at {ssl_path}, continuing without SSL.")

            # Step 3: Connect to database with or without SSL
            self.pool = await asyncpg.create_pool(
                dsn=self.db_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
                ssl=ssl_context
            )

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id UUID PRIMARY KEY,
                        username TEXT NOT NULL,
                        title TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_archived BOOLEAN DEFAULT FALSE
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        audio_url TEXT
                    )
                """)
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_conversations_username ON conversations(username)""")
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)""")
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)""")
            self.logger.info("Database tables created")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection closed")

    async def get_or_create_conversation(self, user_id: str, mode: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id FROM conversations
                WHERE username = $1 AND mode = $2 AND is_archived = false
                ORDER BY updated_at DESC
                LIMIT 1
            """, user_id, mode)


            if row:
                conversation_id = str(row["id"])
                self.logger.info(f"Retrieved existing conversation: {conversation_id} for user {user_id}")
            else:
                conversation_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO conversations (id, username, title, mode)
                    VALUES ($1, $2, $3, $4)
                """, conversation_id, user_id, "New Conversation", mode)
                self.logger.info(f"Created new conversation: {conversation_id} for user {user_id}")
            return conversation_id

    async def create_conversation(self, username: str, title: str, mode: str) -> str:
        conversation_id = str(uuid.uuid4())
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversations (id, username, title, mode)
                    VALUES ($1, $2, $3, $4)
                """, conversation_id, username, title, mode)
            self.logger.info(f"Created conversation {conversation_id} for user {username}")
            return conversation_id
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise

    async def save_message(self, conversation_id: str, role: str, content: str, audio_url: str = None):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO messages (conversation_id, role, content, audio_url)
                    VALUES ($1, $2, $3, $4)
                """, conversation_id, role, content, audio_url)
                await conn.execute("""
                    UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = $1
                """, conversation_id)
            self.logger.info(f"Saved message to conversation {conversation_id}")
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise

    async def save_message_with_audio_bytes(self, conversation_id: str, role: str, content: str, audio_bytes: bytes = None):
        """Save message and upload audio bytes to S3 if provided"""
        audio_url = None
        if audio_bytes:
            audio_url = await self.upload_audio_bytes(audio_bytes)
        
        await self.save_message(conversation_id, role, content, audio_url)
        return audio_url

    async def upload_audio_bytes(self, audio_bytes: bytes) -> Optional[str]:
        if not self.s3:
            self.logger.error("S3 client not initialized")
            return None
        try:
            filename = f"audio_{uuid.uuid4()}.mp3"
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=audio_bytes,
                ContentType='audio/mpeg'
            )
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{filename}"
            self.logger.info(f"Audio uploaded: {url}")
            return url
        except Exception as e:
            self.logger.error(f"Error uploading audio: {e}")
            return None

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT role, content, created_at, audio_url FROM messages
                    WHERE conversation_id = $1
                    ORDER BY created_at ASC
                """, conversation_id)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return []

    async def get_user_conversations(self, username: str) -> List[Dict]:
        """Get all conversations for a user"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, mode, created_at, updated_at, is_archived
                    FROM conversations
                    WHERE username = $1
                    ORDER BY updated_at DESC
                """, username)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get conversations for user {username}: {e}")
            return []

    async def save_audio_message_from_file(self, conversation_id: str, audio_path: str):
        """Save audio message from file path"""
        if os.path.exists(audio_path):
            with open(audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
            audio_url = await self.upload_audio_bytes(audio_bytes)
            await self.save_message(conversation_id, "assistant", "Here is your audio file", audio_url=audio_url)
            return audio_url
        else:
            self.logger.warning(f"Audio file not found at {audio_path}. Skipping audio upload.")
            return None