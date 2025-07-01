import os
import re
import uuid
import base64


class TextToSpeech:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.last_audio_data = {}

    def split_into_sentence_chunks(self, text, max_sentences_per_chunk=2):

        text = re.sub(r"\((.*?)\)", r"\1", text)  # Remove parentheses
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

    async def generate_tts_chunk(self, text: str, chunk_id: int) -> str:
        """
        Generate a single MP3 audio chunk for a chunk of text.
        Returns base64-encoded MP3 audio.
        """
        try:
            import edge_tts

            clean_text = re.sub(r"\((.*?)\)", "", text)
            clean_text = re.sub(r"[*#@%^&_=+\[\]{}<>|~`]", "", clean_text)
            clean_text = re.sub(r"\s{2,}", " ", clean_text).strip()
            if not clean_text:
                return ''

            output_file = f"Data/speech_chunk_{chunk_id}_{uuid.uuid4()}.mp3"
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

            return audio_data 
        

        except Exception as e:
            self.logger.error(f"TTS chunk error for text '{text[:50]}...': {e}")
            return ''

    async def generate_tts(self, text: str, user_id: str, mode: str = "friend") -> str:
        """
        Generate a full TTS response for the given text and user.
        Returns base64-encoded MP3 audio.
        """
        try:
            if mode == "info":
                return ""

            import edge_tts

            clean_text = re.sub(r"\((.*?)\)", "", text)
            clean_text = re.sub(r"[*#@%^&_=+\[\]{}<>|~`]", "", clean_text)
            clean_text = re.sub(r"\s{2,}", " ", clean_text).strip()
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
