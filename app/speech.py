import os
import base64
import uuid
import re
from pydub import AudioSegment
import speech_recognition as sr


class SpeechRecognition:
    def __init__(self, logger):
        self.logger = logger

        # Optional: predefined trigger phrases for mode switching
        self.mode_phrases = {
            "friend": ["friend mode", "switch to friend mode", "start friend mode"],
            "info": ["info mode", "switch to info mode", "start info mode"],
            "elder": ["elder mode", "switch to elder mode", "start elder mode", "dadi mode"],
            "love": ["love mode", "switch to love mode", "start love mode"],
        }

    async def process_audio(self, audio_base64: str) -> str:
        try:
            audio_bytes = base64.b64decode(audio_base64)
            raw_path = f"Data/raw_{uuid.uuid4()}.webm"
            wav_path = f"Data/input_{uuid.uuid4()}.wav"

            # Save the audio
            with open(raw_path, "wb") as f:
                f.write(audio_bytes)

            # Convert to 16kHz mono WAV
            audio = AudioSegment.from_file(raw_path)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            audio.export(wav_path, format="wav")
            os.remove(raw_path)

            # Transcribe
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                try:
                    query = recognizer.recognize_google(audio_data, language="en-IN")
                    self.logger.info(f"🎙️ Transcribed: {query}")
                except sr.UnknownValueError:
                    query = "Sorry, I couldn't understand your voice."
                except sr.RequestError as e:
                    query = f"Could not connect to Google Speech Recognition service: {e}"

            os.remove(wav_path)
            return query

        except Exception as e:
            self.logger.error(f"❌ Error processing voice input: {e}")
            return "Voice input error."

    def detect_mode_from_text(self, query: str) -> str | None:
        """
        Optional helper to detect mode from spoken text (used in main.py)
        Returns 'friend', 'info', etc. or None.
        """
        q = query.lower()
        for mode, triggers in self.mode_phrases.items():
            for phrase in triggers:
                if phrase in q:
                    return mode
        return None
