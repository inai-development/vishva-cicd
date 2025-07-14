import os
import json
import requests
from requests.exceptions import RequestException

def align_with_gentle(audio_path, transcript_path, output_path, gentle_url="http://192.168.1.96:8765/transcriptions?async=false"):
    """
    Align audio with transcript using Gentle forced alignment service and save phoneme data to JSON.
    
    Args:
        audio_path (str): Path to the audio file (e.g., MP3 or WAV).
        transcript_path (str): Path to the transcript text file.
        output_path (str): Path to save the phoneme JSON output.
        gentle_url (str): URL of the Gentle service endpoint.
    """
    print("📡 Sending to Gentle...")
    try:
        with open(audio_path, 'rb') as audio_file, open(transcript_path, 'r', encoding='utf-8') as transcript_file:
            files = {'audio': audio_file, 'transcript': transcript_file}
            response = requests.post(gentle_url, files=files, timeout=30)
            response.raise_for_status()  # Raise exception for bad status codes

        gentle_data = response.json()

        phoneme_list = []
        for word in gentle_data.get("words", []):
            if "start" in word and "phones" in word:
                start_time = word["start"]
                for phone in word["phones"]:
                    phone_label = phone["phone"].split("_")[0]
                    duration = phone["duration"]
                    end_time = start_time + duration
                    phoneme_list.append({
                        "phone": phone_label,
                        "start": round(start_time, 3),
                        "end": round(end_time, 3)
                    })
                    start_time = end_time

        # Save phoneme JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(phoneme_list, f, indent=2)

        print(f"✅ Phoneme output saved: {output_path}")

    except RequestException as e:
        print(f"❌ Error connecting to Gentle service: {e}")
        raise
    except (KeyError, ValueError) as e:
        print(f"❌ Error processing Gentle response: {e}")
        raise
    except IOError as e:
        print(f"❌ File I/O error: {e}")
        raise