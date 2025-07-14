import os
import json
import logging
import argparse
from .gentle_align import align_with_gentle
from .phoneme_to_viseme import map_phonemes_to_visemes

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def process_audio_to_visemes(audio_path, transcript_text=None, transcript_path=None, output_dir="output", return_json=False):
    """
    Process an audio file and transcript to generate phoneme and viseme JSON files.

    Args:
        audio_path (str): Path to the audio file (.mp3 or .wav).
        transcript_text (str): Transcript text to align (optional if transcript_path is provided).
        transcript_path (str): Path to existing transcript file (optional).
        output_dir (str): Directory where outputs are saved.
        return_json (bool): If True, returns the phoneme and viseme JSON data instead of paths.

    Returns:
        tuple: (phoneme_path, viseme_path) OR (phoneme_json, viseme_json)
    """
    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Resolve transcript path
        if transcript_path:
            if not os.path.exists(transcript_path):
                raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
        elif transcript_text:
            transcript_path = os.path.join(temp_dir, f"{base_name}.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript_text)
        else:
            raise ValueError("You must provide either transcript_text or transcript_path.")

        phoneme_output_path = os.path.join(temp_dir, f"{base_name}_phonemes.json")
        viseme_output_path = os.path.join(temp_dir, f"{base_name}_visemes.json")

        logger.info("🔠 Aligning phonemes...")
        align_with_gentle(audio_path, transcript_path, phoneme_output_path)

        logger.info("🧠 Mapping phonemes to visemes...")
        map_phonemes_to_visemes(phoneme_output_path, viseme_output_path)

        logger.info(f"✅ Done: {base_name}")
        if return_json:
            with open(phoneme_output_path, "r", encoding="utf-8") as pf:
                phoneme_data = json.load(pf)
            with open(viseme_output_path, "r", encoding="utf-8") as vf:
                viseme_data = json.load(vf)
            return phoneme_data, viseme_data

        return phoneme_output_path, viseme_output_path

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process audio file into phoneme and viseme JSONs using Gentle.")
    parser.add_argument("--audio", required=True, help="Path to audio file (.wav or .mp3)")
    parser.add_argument("--text", help="Transcript text for alignment (use either --text or --transcript)")
    parser.add_argument("--transcript", help="Path to a transcript text file")
    parser.add_argument("--out", default="output", help="Output directory (default: output)")
    parser.add_argument("--json", action="store_true", help="Return and print JSON data instead of file paths")

    args = parser.parse_args()

    result = process_audio_to_visemes(
        audio_path=args.audio,
        transcript_text=args.text,
        transcript_path=args.transcript,
        output_dir=args.out,
        return_json=args.json
    )

    if args.json:
        phoneme_json, viseme_json = result
        print("\n📄 Phoneme JSON:\n", json.dumps(phoneme_json, indent=2))
        print("\n🎭 Viseme JSON:\n", json.dumps(viseme_json, indent=2))
    else:
        phoneme_path, viseme_path = result
        print(f"\n📄 Phoneme File: {phoneme_path}")
        print(f"🎭 Viseme File: {viseme_path}")
