import subprocess
import os
import tempfile
import json
import uuid
# ───── CONFIGURATION ─────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RHUBARB_PATH = os.path.join(BASE_DIR, 'Models', 'Rhubarb', 'rhubarb.exe')
FFMPEG_PATH = os.path.join(BASE_DIR, 'Models', 'ffmpeg', 'bin', 'ffmpeg.exe')
# ─────────────────────────
def convert_to_wav(input_audio_path: str, output_wav_path: str):
    subprocess.run([
        FFMPEG_PATH,
        "-y",
        "-i", input_audio_path,
        "-ar", "48000",
        output_wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def run_rhubarb(audio_wav_path: str, transcript_path: str) -> dict:
    tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
    cmd = [
        RHUBARB_PATH,
        audio_wav_path,
        "--machineReadable",
        "-f", "json",
        "--dialogFile", transcript_path,
        "-o", tmp_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(":x: Rhubarb CLI failed:\n", result.stderr)
        raise RuntimeError("Rhubarb failed")
    try:
        with open(tmp_output, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        os.remove(tmp_output)
        return raw_data
    except Exception as e:
        print(":x: Failed to read Rhubarb output JSON:", e)
        raise
def convert_to_start_end(rhubarb_json: dict) -> dict:
    cues = rhubarb_json.get("mouthCues", [])
    updated_cues = []
    for i, cue in enumerate(cues):
        start = cue["start"]
        end = cues[i + 1]["start"] if i + 1 < len(cues) else start + 0.1
        updated_cues.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "value": cue["value"]
        })
    return {"mouthCues": updated_cues}
def generate_lip_sync_json(input_audio_path: str, input_text_path: str, output_json_path: str) -> str:
    print(":arrows_counterclockwise: Step 1: Converting audio to 48kHz WAV...")
    tmp_wav = os.path.join(tempfile.gettempdir(), f"rhubarb_tmp_{uuid.uuid4()}.wav")
    convert_to_wav(input_audio_path, tmp_wav)
    print(":clapper: Step 2: Running Rhubarb...")
    raw_json = run_rhubarb(tmp_wav, input_text_path)
    print(":pencil2: Step 3: Post-processing to add end times...")
    processed_json = convert_to_start_end(raw_json)
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(processed_json, f, indent=2)
    os.remove(tmp_wav)
    print(f":white_check_mark: Done! Output saved to: {output_json_path}")
    return output_json_path