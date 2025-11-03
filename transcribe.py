from faster_whisper import WhisperModel
from opencc import OpenCC

# ========= 配置 =========
AUDIO_FILE = "星雨街.m4a"    # 修改为你的文件名
OUTPUT_FILE = "test.txt"
MODEL_SIZE = "large-v3"     # 可用：base / small / medium / large-v3
DEVICE = "cuda"             # CPU请改为 "cpu"
COMPUTE_TYPE = "float16"    # 如果失败→ float32
# ========================


def main():
    cc = OpenCC("t2s")  # 繁 → 简

    print(">>> 正在加载模型...")
    model = WhisperModel(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE
    )

    print(f">>> 开始转写：{AUDIO_FILE}")

    segments, info = model.transcribe(
        AUDIO_FILE,
        beam_size=5,     # 提升准确率
        language="zh",   # 强制中文
    )

    print(f">>> 识别语言：{info.language}")
    print(f">>> 时长：{info.duration:.2f} 秒")

    results = []

    for seg in segments:
        text = cc.convert(seg.text.strip())
        line = f"[{format_time(seg.start)} → {format_time(seg.end)}] {text}"
        print(line)
        results.append(line)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"\n✅ 已写入：{OUTPUT_FILE}")


def format_time(seconds):
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


if __name__ == "__main__":
    main()
