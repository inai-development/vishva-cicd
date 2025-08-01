import os
import json
import warnings
from typing import List, Tuple, Dict

import numpy as np
from pydub import AudioSegment
from langdetect import detect
from langdetect.detector_factory import DetectorFactory


# os.environ["PATH"] += os.pathsep + r"D:\AA\vishume\ffmpeg\bin"
# AudioSegment.converter = r"D:\AA\vishume\ffmpeg\bin\ffmpeg.exe"

AudioSegment.converter = "ffmpeg"


DetectorFactory.seed = 0
warnings.filterwarnings("ignore")

# ------------------- SHAPE KEY MAPPING -------------------
shape_key_map = {
    "A":["m","b","p","em","bm","i"],
    "B":["d","t","n","l","s","z","e","nd","nt"],
    "C":["k","g","gh","kh","ng"],
    "D":["r","rr","ll","ey","er","dh"],
    "E":["u","uw","o","w","wh","ch","jh","sh","zh","th"],
    "F":["f","v"],
    "G":["hh","h","uh","ih"],
    "H":["aa","ae","ah","ao","aw","ay","a","eh","iy","ee","y"],
    "x":[" ", "sil", "sp", "pause"]
}
phoneme_to_shape = {}
for shape, phonemes in shape_key_map.items():
    for phoneme in sorted(phonemes, key=len, reverse=True):
        phoneme_to_shape[phoneme] = shape

# ------------------- CORE UTILS -------------------
def analyze_audio_segment(audio: AudioSegment) -> Tuple[np.ndarray, int]:
    if audio.channels > 1:
        audio = audio.set_channels(1)
    if audio.sample_width != 2:
        audio = audio.set_sample_width(2)
    samples = np.array(audio.get_array_of_samples())
    return samples, audio.frame_rate

def detect_silence(audio: AudioSegment,
                   threshold_db: float = -40.0,
                   min_silence_duration: float = 0.1) -> List[Tuple[float, float]]:
    samples, sr = analyze_audio_segment(audio)
    if len(samples) == 0:
        return []
    samples = samples.astype(np.float32) / 32768.0
    window_size = int(0.02 * sr)
    hop_size = window_size // 2

    rms = []
    for i in range(0, len(samples), hop_size):
        window = samples[i:i+window_size]
        if len(window) == 0:
            continue
        rms_val = np.sqrt(np.mean(window**2))
        rms.append(20 * np.log10(max(rms_val, 1e-10)))

    silent_windows = [i for i, val in enumerate(rms) if val < threshold_db]
    silent_periods = []
    for window_idx in silent_windows:
        start_time = window_idx * hop_size / sr
        end_time = (window_idx * hop_size + window_size) / sr
        if silent_periods and start_time <= silent_periods[-1][1]:
            silent_periods[-1] = (silent_periods[-1][0], end_time)
        else:
            silent_periods.append((start_time, end_time))
    return [(s, e) for s, e in silent_periods if (e - s) >= min_silence_duration]

def text_to_phonemes(text: str, lang: str = 'en') -> List[str]:
    text = text.strip().lower()
    if not text:
        return []

    if lang == 'en':
        try:
            from eng_to_ipa import convert as ipa_convert
            ipa_text = ipa_convert(text)
            ipa_to_phoneme = {
                'i': 'iy', 'ɪ': 'ih', 'e': 'ey', 'ɛ': 'eh', 'æ': 'ae',
                'ɑ': 'aa', 'ʌ': 'ah', 'ɔ': 'ao', 'ʊ': 'uh', 'u': 'uw',
                'aʊ': 'aw', 'aɪ': 'ay', 'ɔɪ': 'oy', 'oʊ': 'ow',
                'p': 'p', 'b': 'b', 't': 't', 'd': 'd', 'k': 'k', 'ɡ': 'g',
                'm': 'm', 'n': 'n', 'ŋ': 'ng', 'f': 'f', 'v': 'v',
                'θ': 'th', 'ð': 'dh', 's': 's', 'z': 'z', 'ʃ': 'sh', 'ʒ': 'zh',
                'h': 'hh', 'l': 'l', 'r': 'r', 'j': 'y', 'w': 'w',
                'tʃ': 'ch', 'dʒ': 'jh', ' ': ' '
            }
            phonemes = []
            i = 0
            while i < len(ipa_text):
                found = False
                for length in [2, 1]:
                    if i + length <= len(ipa_text):
                        substr = ipa_text[i:i+length]
                        if substr in ipa_to_phoneme:
                            phonemes.append(ipa_to_phoneme[substr])
                            i += length
                            found = True
                            break
                if not found:
                    i += 1
            return phonemes
        except Exception as e:
            print(f"IPA conversion failed: {e}")

    def romanized_to_phonemes(text: str) -> List[str]:
        clusters = ['ch', 'jh', 'sh', 'th', 'dh', 'gh', 'kh', 'ng',
                    'aa', 'ee', 'ii', 'oo', 'uu', 'ae', 'ai', 'au', 'aw',
                    'rr', 'll', 'ny', 'ly', 'hy']
        tokens = []
        i = 0
        while i < len(text):
            found = False
            for cluster in sorted(clusters, key=len, reverse=True):
                if text.startswith(cluster, i):
                    tokens.append(cluster)
                    i += len(cluster)
                    found = True
                    break
            if not found:
                tokens.append(text[i])
                i += 1
        return tokens

    return romanized_to_phonemes(text)

def generate_value_mapping(phonemes: List[str],
                           audio: AudioSegment,
                           silence_threshold: float = -40.0) -> List[Dict]:
    duration = len(audio) / 1000
    if duration <= 0 or not phonemes:
        return []
    silent_periods = detect_silence(audio, threshold_db=silence_threshold)
    total_phoneme_units = len([p for p in phonemes if p != ' '])
    if total_phoneme_units == 0:
        return []

    base_duration = duration / total_phoneme_units
    mapping = []
    current_time = 0.0
    for phoneme in phonemes:
        if phoneme == ' ':
            space_duration = base_duration * 0.3
            mapping.append({
                'value': 'X',
                'start': round(current_time, 3),
                'end': round(current_time + space_duration, 3)
            })
            current_time += space_duration
            continue

        phoneme_duration = base_duration
        phoneme_end = current_time + phoneme_duration
        is_silent = any(not (phoneme_end < s or current_time > e) for s, e in silent_periods)
        value = 'X' if is_silent else phoneme_to_shape.get(phoneme, 'A')
        mapping.append({
            'value': value,
            'start': round(current_time, 3),
            'end': round(phoneme_end, 3)
        })
        current_time = phoneme_end

    if mapping and current_time < duration:
        mapping[-1]['end'] = round(duration, 3)

    return mapping

def generate_lip_sync_json(input_audio_path: str, input_text_path: str, output_json_path: str) -> str:
    print(":rocket: Starting value mapping process...")

    try:
        with open(input_text_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            raise ValueError("Text file is empty.")

        lang = detect(text)[:2]
        phonemes = text_to_phonemes(text, lang)
        audio = AudioSegment.from_file(input_audio_path)
        mapping = generate_value_mapping(phonemes, audio)

        print(":floppy_disk: Saving output JSON...")
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({"mouthCues": mapping}, f, indent=2)

        print(f":white_check_mark: Lip sync JSON saved to: {output_json_path}")
        return output_json_path

    except Exception as e:
        print(f":x: Error: {str(e)}")
        raise
