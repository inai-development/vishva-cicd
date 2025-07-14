import json
import os

# Gentle phoneme to 9-viseme shape keys
PHONEME_TO_VISEME = {
    # D Group → D
    "AA": "D", "AA0": "D", "AA1": "D", "AA2": "D",
    "AE": "D", "AE0": "D", "AE1": "D", "AE2": "D",
    "AH": "D", "AH0": "D", "AH1": "D", "AH2": "D",
    "AY": "D", "AY0": "D", "AY1": "D", "AY2": "D",
    "AW": "D", "AW0": "D", "AW1": "D", "AW2": "D",
    "IH": "D", "IH0": "D", "IH1": "D", "IH2": "D",
    "IY": "D", "IY0": "D", "IY1": "D", "IY2": "D",

    # C Group → C
    "EH": "C", "EH0": "C", "EH1": "C", "EH2": "C",
    "EY": "C", "EY0": "C", "EY1": "C", "EY2": "C",
    "ER": "C", "ER0": "C", "ER1": "C", "ER2": "C",

    # E Group → E
    "AO": "E", "AO0": "E", "AO1": "E", "AO2": "E",
    "OW": "E", "OW0": "E", "OW1": "E", "OW2": "E",
    "OY": "E", "OY0": "E", "OY1": "E", "OY2": "E",

    # F Group → F
    "UH": "F", "UH0": "F", "UH1": "F", "UH2": "F",
    "UW": "F", "UW0": "F", "UW1": "F", "UW2": "F",
    "W": "F", "R": "F", "HH": "F", "Y": "F", "WH": "F",

    # H Group → H
    "H": "H", "EL": "H", "L": "H",

    # A Group → A
    "M": "A", "B": "A", "P": "A",
    "EM": "A", "EN": "A", "N": "A",
    "NG": "A", "T": "A", "D": "A",
    "G": "A", "K": "A", "DX": "A", "Q": "A",

    # B Group → B
    "SH": "B", "CH": "B", "JH": "B",
    "ZH": "B", "S": "B", "Z": "B",

    # G Group → G
    "F": "G", "V": "G", "TH": "G", "DH": "G",

    # Custom silent → X
    "X": "X"
}

def map_phonemes_to_visemes(phoneme_json_path, viseme_output_path, insert_gap_phoneme=True, min_gap=0.05):
    """
    Map phoneme JSON data to viseme JSON data using PHONEME_TO_VISEME mapping.
    
    Args:
        phoneme_json_path (str): Path to the input phoneme JSON file.
        viseme_output_path (str): Path to save the viseme JSON output.
        insert_gap_phoneme (bool): Whether to insert silent visemes (X) for gaps.
        min_gap (float): Minimum gap duration (seconds) to insert a silent viseme.
    """
    try:
        with open(phoneme_json_path, "r", encoding="utf-8") as f:
            phonemes = json.load(f)

        visemes = []
        last_end = 0.0

        for p in phonemes:
            phone = p["phone"].upper()
            start = p["start"]
            end = p["end"]

            # If there's a gap between last and current
            if insert_gap_phoneme and (start - last_end) >= min_gap:
                visemes.append({
                    "viseme": "X",
                    "start": round(last_end, 3),
                    "end": round(start, 3)
                })

            if phone not in PHONEME_TO_VISEME:
                raise ValueError(f"🚫 Missing phoneme in mapping: '{phone}' — please update PHONEME_TO_VISEME.")

            visemes.append({
                "viseme": PHONEME_TO_VISEME[phone],
                "start": round(start, 3),
                "end": round(end, 3)
            })
            last_end = end

        os.makedirs(os.path.dirname(viseme_output_path), exist_ok=True)
        with open(viseme_output_path, "w", encoding="utf-8") as f:
            json.dump(visemes, f, indent=2)

        print(f"✅ Viseme output saved: {viseme_output_path}")

    except IOError as e:
        print(f"❌ File I/O error: {e}")
        raise
    except (KeyError, ValueError) as e:
        print(f"❌ Error processing phoneme data: {e}")
        raise