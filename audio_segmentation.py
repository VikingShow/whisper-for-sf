import os
from pydub import AudioSegment

# ==========================
# 配置区域
# ==========================
input_folder = ".\\dataset\\audio"   # 音频文件夹路径
output_folder = ".\\dataset\\audio"      # 裁剪后文件输出路径
segment_length_seconds = 30                   # 每段长度（秒）
output_format = "mp3"                         # 输出音频格式（可以改成 wav, m4a 等）

# 创建输出文件夹
os.makedirs(output_folder, exist_ok=True)

# 支持的音频格式
supported_formats = (".mp3", ".wav", ".m4a", ".flac", ".ogg")

# 全局序号
counter = 1

# ==========================
# 批量处理
# ==========================
for file_name in os.listdir(input_folder):
    if file_name.lower().endswith(supported_formats):
        input_path = os.path.join(input_folder, file_name)
        try:
            audio = AudioSegment.from_file(input_path)
            segment_length_ms = segment_length_seconds * 1000
            total_length_ms = len(audio)
            num_segments = (total_length_ms + segment_length_ms - 1) // segment_length_ms

            # 循环切割
            for i in range(num_segments):
                start_ms = i * segment_length_ms
                end_ms = min((i + 1) * segment_length_ms, total_length_ms)
                segment = audio[start_ms:end_ms]

                output_name = f"{counter:04d}.{output_format}"  # 4位序号，如 0001.mp3
                output_path = os.path.join(output_folder, output_name)
                segment.export(output_path, format=output_format)

                counter += 1

            print(f"[√] 已切割: {file_name} -> {num_segments} 段")
        except Exception as e:
            print(f"[×] 处理失败: {file_name}, 错误: {e}")

print("全部处理完成！")
