# build_manifest.py
import os
import json

AUDIO_DIR = "dataset/audio"
TEXT_DIR = "dataset/text"
MANIFEST = "dataset/manifest.jsonl"

with open(MANIFEST, "w", encoding="utf-8") as fout:
    for file in os.listdir(AUDIO_DIR):
        if not file.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
            continue
        
        audio_path = os.path.join("audio", file)
        txt_name = file.rsplit(".", 1)[0] + ".txt"
        txt_path = os.path.join(TEXT_DIR, txt_name)

        if not os.path.exists(txt_path):
            print("⚠️ Missing transcript:", txt_name)
            continue

        with open(txt_path, "r", encoding="utf-8") as fin:
            text = fin.read().strip()

        record = {
            "audio": audio_path,
            "text": text
        }
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

print("✅ manifest.jsonl generated!")
