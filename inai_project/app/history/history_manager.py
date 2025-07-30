import asyncpg
import boto3
import uuid
import os
from datetime import datetime
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
        self.active_conversations = {}
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
            # ssl_context = ssl.create_default_context(cafile=r"D:\INAI_Backend_MD\certs\rds-ca.pem")
            ssl_context = ssl.create_default_context(cafile=r"/home/ubuntu/INAI_Backend/certs/rds-ca.pem")
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
                        user_id TEXT NOT NULL,
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
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)""")
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)""")
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_conversations_mode ON conversations(mode)""")
                await conn.execute("""CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)""")
            self.logger.info("✅ Database tables created successfully.")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection closed")

    async def create_new_conversation(self, user_id: str, mode: str, title: str = "New Conversation") -> str:
        conversation_id = str(uuid.uuid4())
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversations (id, user_id, title, mode)
                    VALUES ($1, $2, $3, $4)
                """, conversation_id, user_id, title, mode)
            self.active_conversations[user_id] = conversation_id
            self.logger.info(f"✅ NEW CHAT: Created conversation {conversation_id} for user {user_id}")
            return conversation_id
        except Exception as e:
            self.logger.error(f"❌ Failed to create new conversation: {e}")
            raise

    async def get_or_create_conversation(self, user_id: str, mode: str) -> str:
        if user_id in self.active_conversations:
            conversation_id = self.active_conversations[user_id]
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id FROM conversations WHERE id = $1 AND mode = $2
                """, conversation_id, mode)
                if row:
                    self.logger.info(f"📝 Using active conversation: {conversation_id} for user {user_id}")
                    return conversation_id
                else:
                    del self.active_conversations[user_id]
        return await self.create_new_conversation(user_id, mode)

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
            self.logger.info(f"💾 Saved message to conversation {conversation_id}")
        except Exception as e:
            self.logger.error(f"❌ Failed to save message: {e}")
            raise

    async def save_message_with_audio_bytes(self, conversation_id: str, role: str, content: str, audio_bytes: bytes = None):
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
            self.logger.info(f"🆙 Audio uploaded: {url}")
            return url
        except Exception as e:
            self.logger.error(f"❌ Error uploading audio: {e}")
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
            self.logger.error(f"❌ Failed to get messages: {e}")
            return []

    # Updated method: Get conversations by mode with proper grouping
    async def get_user_conversations_by_mode(self, user_id: str, mode: str) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        c.id, 
                        c.title, 
                        c.mode, 
                        c.created_at, 
                        c.updated_at,
                        c.is_archived,
                        m.content as last_message,
                        COUNT(msg.id) as message_count
                    FROM conversations c
                    LEFT JOIN LATERAL (
                        SELECT content 
                        FROM messages 
                        WHERE conversation_id = c.id 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    ) m ON true
                    LEFT JOIN messages msg ON msg.conversation_id = c.id
                    WHERE c.user_id = $1 AND c.mode = $2 AND c.is_archived = false
                    GROUP BY c.id, c.title, c.mode, c.created_at, c.updated_at, c.is_archived, m.content
                    ORDER BY c.updated_at DESC
                """, user_id, mode)
            
            conversations = []
            for row in rows:
                conv = dict(row)
                if conv['last_message']:
                    conv['preview'] = conv['last_message'][:50] + "..." if len(conv['last_message']) > 50 else conv['last_message']
                else:
                    conv['preview'] = "No messages yet"
                conversations.append(conv)
            
            self.logger.info(f"📋 Found {len(conversations)} conversations for user {user_id} in mode {mode}")
            return conversations
        except Exception as e:
            self.logger.error(f"❌ Failed to get mode-wise conversations for {user_id}: {e}")
            return []

    # New method: Get conversation modes summary
    async def get_user_modes_summary(self, user_id: str) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        mode,
                        COUNT(*) as conversation_count,
                        MAX(updated_at) as last_updated
                    FROM conversations
                    WHERE user_id = $1 AND is_archived = false
                    GROUP BY mode
                    ORDER BY last_updated DESC
                """, user_id)
            
            modes_summary = []
            for row in rows:
                mode_data = dict(row)
                # Add mode display names
                mode_names = {
                    'friend': 'Friend Mode',
                    'information': 'Information Mode', 
                    'love': 'Love Mode',
                    'elder': 'Elder Mode'
                }
                mode_data['display_name'] = mode_names.get(mode_data['mode'], mode_data['mode'].title())
                modes_summary.append(mode_data)
            
            self.logger.info(f"📊 Found {len(modes_summary)} active modes for user {user_id}")
            return modes_summary
        except Exception as e:
            self.logger.error(f"❌ Failed to get modes summary for {user_id}: {e}")
            return []

    # Updated method: Get all conversations with better structure
    async def get_user_conversations_with_preview(self, user_id: str) -> List[Dict]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        c.id, 
                        c.title, 
                        c.mode, 
                        c.created_at, 
                        c.updated_at,
                        c.is_archived,
                        m.content as last_message,
                        COUNT(msg.id) as message_count
                    FROM conversations c
                    LEFT JOIN LATERAL (
                        SELECT content 
                        FROM messages 
                        WHERE conversation_id = c.id 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    ) m ON true
                    LEFT JOIN messages msg ON msg.conversation_id = c.id
                    WHERE c.user_id = $1 AND c.is_archived = false
                    GROUP BY c.id, c.title, c.mode, c.created_at, c.updated_at, c.is_archived, m.content
                    ORDER BY c.updated_at DESC
                """, user_id)
            
            conversations = []
            for row in rows:
                conv = dict(row)
                if conv['last_message']:
                    conv['preview'] = conv['last_message'][:50] + "..." if len(conv['last_message']) > 50 else conv['last_message']
                else:
                    conv['preview'] = "No messages yet"
                conversations.append(conv)
            return conversations
        except Exception as e:
            self.logger.error(f"❌ Failed to get conversations for user {user_id}: {e}")
            return []

    async def save_audio_message_from_file(self, conversation_id: str, audio_path: str):
        if os.path.exists(audio_path):
            with open(audio_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
            audio_url = await self.upload_audio_bytes(audio_bytes)
            await self.save_message(conversation_id, "assistant", "Here is your audio file", audio_url=audio_url)
            return audio_url
        else:
            self.logger.warning(f"⚠️ Audio file not found at {audio_path}. Skipping audio upload.")
            return None

    async def set_active_conversation(self, user_id: str, conversation_id: str):
        # Verify conversation belongs to user
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id FROM conversations 
                    WHERE id = $1 AND user_id = $2 AND is_archived = false
                """, conversation_id, user_id)
                
                if row:
                    self.active_conversations[user_id] = conversation_id
                    self.logger.info(f"🔄 Active conversation changed to {conversation_id} for user {user_id}")
                else:
                    raise Exception("Conversation not found or doesn't belong to user")
        except Exception as e:
            self.logger.error(f"❌ Failed to set active conversation: {e}")
            raise

    async def archive_conversation(self, conversation_id: str, user_id: str):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE conversations 
                    SET is_archived = true 
                    WHERE id = $1 AND user_id = $2
                """, conversation_id, user_id)
            
            if user_id in self.active_conversations and self.active_conversations[user_id] == conversation_id:
                del self.active_conversations[user_id]
            
            self.logger.info(f"🗄️ Archived conversation {conversation_id} for user {user_id}")
        except Exception as e:
            self.logger.error(f"❌ Failed to archive conversation: {e}")
            raise

    async def update_conversation_title(self, conversation_id: str, new_title: str, user_id: str):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE conversations 
                    SET title = $1, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = $2 AND user_id = $3
                """, new_title, conversation_id, user_id)
            self.logger.info(f"📝 Updated conversation title: {conversation_id} -> {new_title}")
        except Exception as e:
            self.logger.error(f"❌ Failed to update conversation title: {e}")
            raise

    # New method: Get conversation details with basic info
    async def get_conversation_details(self, conversation_id: str, user_id: str) -> Optional[Dict]:
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, title, mode, created_at, updated_at, is_archived
                    FROM conversations
                    WHERE id = $1 AND user_id = $2
                """, conversation_id, user_id)
                
                if row:
                    return dict(row)
                return None
        except Exception as e:
            self.logger.error(f"❌ Failed to get conversation details: {e}")
            return None