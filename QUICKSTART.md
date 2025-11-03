# 🚀 快速入门指南

## 5 分钟上手教程

### 步骤 1: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 2: 准备音频文件

确保你有一个音频文件，支持的格式：
- `.mp3`
- `.m4a`
- `.wav`
- `.flac`
- `.ogg`

### 步骤 3: 运行转写

最简单的使用方式：

```bash
python transcribe.py --audio 你的音频文件.m4a
```

这将：
- ✅ 使用 large-v3 模型（最高质量）
- ✅ 自动检测并使用 GPU（如果可用）
- ✅ 生成 Word 文档（文件名与音频相同）
- ✅ 自动分段（每 5 分钟一段）

### 步骤 4: 查看结果

程序完成后，你会在当前目录看到：
```
你的音频文件.docx
```

打开这个 Word 文档，你就能看到完整的转写结果！

## 🎯 常用场景

### 场景 1: 快速转写（使用较小模型）

```bash
python transcribe.py --audio 音频.m4a --model medium
```

速度提升 2 倍，质量仍然很好！

### 场景 2: 生成字幕文件

```bash
python transcribe.py --audio 视频.mp4 --format srt
```

生成标准 SRT 字幕文件，可直接用于视频！

### 场景 3: 一次生成多种格式

```bash
python transcribe.py --audio 音频.m4a --format docx,txt,srt
```

同时生成 Word、纯文本和字幕文件！

### 场景 4: 批量转写整个文件夹

```bash
python transcribe.py --dir ./音频文件夹
```

自动处理文件夹中的所有音频文件！

### 场景 5: 批量转写 + 递归子目录

```bash
python transcribe.py --dir ./音频文件夹 --recursive --output-dir ./转写结果
```

搜索所有子目录，保持目录结构输出！

### 场景 6: 只转写特定格式文件

```bash
python transcribe.py --dir ./音频文件夹 --pattern "*.mp3"
```

只处理 MP3 文件！

### 场景 7: CPU 模式（没有 GPU）

```bash
python transcribe.py --audio 音频.m4a --device cpu --compute-type int8 --model small
```

即使没有 GPU，也能快速转写！

### 场景 8: 长音频（自定义分段）

```bash
python transcribe.py --audio 长音频.mp3 --segment-length 600
```

每 10 分钟一段，更适合长时间录音！

## 📊 处理时间参考

| 音频时长 | 模型 | 设备 | 预计时间 |
|---------|------|------|---------|
| 1 小时 | small | GPU | 3-5 分钟 |
| 1 小时 | medium | GPU | 5-8 分钟 |
| 1 小时 | large-v3 | GPU | 8-15 分钟 |
| 1 小时 | small | CPU | 15-30 分钟 |
| 1 小时 | medium | CPU | 30-60 分钟 |

## 💡 小技巧

### 1. 利用缓存

第一次转写后，结果会被缓存。如果再次运行相同的音频和模型，会直接使用缓存结果，几乎瞬间完成！

### 2. 禁用缓存

如果你修改了音频或想重新转写：

```bash
python transcribe.py --audio 音频.m4a --no-cache
```

### 3. 查看详细日志

```bash
python transcribe.py --audio 音频.m4a --log-level DEBUG
```

### 4. 批量处理

**超简单！** 不需要写脚本，直接使用内置批量功能：

```bash
# 处理当前目录所有音频
python transcribe.py --dir .

# 处理指定目录
python transcribe.py --dir ./音频文件夹

# 递归处理所有子目录
python transcribe.py --dir ./音频文件夹 --recursive

# 指定输出目录
python transcribe.py --dir ./input --output-dir ./output
```

**传统方法（如果你需要）：**

```bash
# Windows (batch.bat)
for %%f in (*.m4a) do python transcribe.py --audio "%%f"

# Linux/Mac (batch.sh)
for file in *.m4a; do
    python transcribe.py --audio "$file"
done
```

## ⚠️ 常见问题快速解决

### 问题：找不到 CUDA

**解决方案**：使用 CPU 模式
```bash
python transcribe.py --audio 音频.m4a --device cpu --compute-type int8
```

### 问题：内存不足

**解决方案**：使用较小的模型
```bash
python transcribe.py --audio 音频.m4a --model small
```

### 问题：转写结果不准确

**解决方案**：使用更大的模型和更高的 beam size
```bash
python transcribe.py --audio 音频.m4a --model large-v3 --beam-size 10
```

### 问题：处理速度太慢

**解决方案**：
1. 使用较小的模型：`--model small`
2. 启用 GPU：确保安装了 CUDA 版本的 PyTorch
3. 降低 beam size：`--beam-size 3`

## 🎓 下一步

- 📖 阅读完整的 [README.md](README.md)
- 💻 查看代码示例 [example.py](example.py)
- 🧪 运行测试：`pytest tests/ -v`
- 🤝 参与贡献 [CONTRIBUTING.md](CONTRIBUTING.md)

## 🆘 获取帮助

查看所有可用选项：
```bash
python transcribe.py --help
```

---

**开始你的转写之旅吧！** 🎉


