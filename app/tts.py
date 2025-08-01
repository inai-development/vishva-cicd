import os
import re
import uuid
import base64
import edge_tts
from langdetect import detect


class TextToSpeech:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.last_audio_data = {}

    def split_into_sentence_chunks(self, text, max_sentences_per_chunk=2):

        text = re.sub(r"\((.*?)\)", r"\1", text) 
        text = re.sub(r"(.?)", r"\1", text).strip()

        if not text:
            return []

        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return [text]

        chunks = []
        current_chunk = []

        for sentence in sentences:
            current_chunk.append(sentence)
            if len(current_chunk) >= max_sentences_per_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks
    

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\((.*?)\)", "", text)
        text = re.sub(r"[*#@%^&_=+\[\]{}<>|~`]", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        # Remove emojis
        text = re.sub(r'[\U0001F600-\U0001F64F'
                      r'\U0001F300-\U0001F5FF'
                      r'\U0001F680-\U0001F6FF'
                      r'\U0001F1E0-\U0001F1FF'
                      r'\U00002700-\U000027BF'
                      r'\U0001F900-\U0001F9FF'
                      r'\U00002600-\U000026FF'
                      r'\U00002B00-\U00002BFF'
                      r'\U0001FA70-\U0001FAFF'
                      r'\U000025A0-\U000025FF]+', '', text)
        return text.strip()
    


    def _detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}")
            return "en"

    async def generate_tts_chunk(self, text: str, chunk_id: int) -> str:
        try:
            clean_text = self._clean_text(text)

            if not clean_text:
                return ''
            
            voice = self.config.assistant_voice
            if self.config.mode == "info":
                lang = self._detect_language(clean_text)
                voice = self.config.voice_map.get(lang, self.config.assistant_voice)

            output_file = f"Data/speech_chunk_{chunk_id}_{uuid.uuid4()}.mp3"
            communicate = edge_tts.Communicate(clean_text, voice=voice)
            await communicate.save(output_file)

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                self.logger.warning(f"Generated TTS file is empty or missing: {output_file}")
                return ''

            with open(output_file, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode("utf-8")

            try:
                os.remove(output_file)
                self.logger.info(f"Deleted temporary TTS file: {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to delete temporary TTS file {output_file}: {e}")

            return audio_data

        except Exception as e:
            self.logger.error(f"TTS chunk error for text '{text[:50]}...': {e}")
            return ''

    async def generate_tts(self, text: str, user_id: str, mode: str = "friend") -> str:
        try:
            if mode == "info":
                return ""

            clean_text = self._clean_text(text)

            if not clean_text:
                return ''

            output_file = f"Data/speech_{uuid.uuid4()}.mp3"
            communicate = edge_tts.Communicate(clean_text, voice=self.config.assistant_voice)
            await communicate.save(output_file)

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                self.logger.warning(f"Generated TTS file is empty or missing: {output_file}")
                return ''

            with open(output_file, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode("utf-8")

            try:
                os.remove(output_file)
                self.logger.info(f"Deleted temporary TTS file: {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to delete temporary TTS file {output_file}: {e}")

            self.last_audio_data[user_id] = audio_data
            return audio_data

        except Exception as e:
            self.logger.error(f"TTS error for text '{text[:50]}...': {e}")
            return ''