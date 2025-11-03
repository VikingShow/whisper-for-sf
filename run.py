import whisper_timestamped as whisper
import json

audio_path = "星雨街.m4a"
model = whisper.load_model("medium")

result = whisper.transcribe(
    model,
    audio_path,
    language="zh",
)

# ✅ 取最终全文（自动标点）
full_text = result["text"]

# ✅ 写入全文
with open("transcript.txt", "w", encoding="utf-8") as f:
    f.write(full_text)

# ✅ 自动分段
with open("transcript_segmented.txt", "w", encoding="utf-8") as f:
    for seg in result["segments"]:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]

        f.write(f"[{start:.2f} - {end:.2f}] {text}\n")

print("✅ 完成：transcript.txt + transcript_segmented.txt")
