# 📦 批量处理指南

本指南详细介绍如何使用批量转写功能高效处理多个音频文件。

## 🎯 基础批量处理

### 1. 处理单个文件夹

最简单的用法，处理指定文件夹中的所有音频文件：

```bash
python transcribe.py --dir ./音频文件夹
```

**效果：**
- ✅ 自动扫描文件夹中所有支持的音频格式
- ✅ 逐个转写，显示进度
- ✅ 输出文件与源文件在同一目录
- ✅ 自动缓存，避免重复处理

### 2. 递归处理子目录

如果你的音频文件分散在多个子文件夹中：

```bash
python transcribe.py --dir ./音频文件夹 --recursive
```

**目录结构示例：**
```
音频文件夹/
├── 第一章/
│   ├── 1-1.mp3
│   └── 1-2.mp3
├── 第二章/
│   ├── 2-1.mp3
│   └── 2-2.mp3
└── 其他.m4a
```

所有文件都会被找到并处理！

### 3. 指定输出目录

将转写结果统一保存到指定目录，并保持原目录结构：

```bash
python transcribe.py --dir ./input --output-dir ./output --recursive
```

**输出结构：**
```
output/
├── 第一章/
│   ├── 1-1.docx
│   └── 1-2.docx
├── 第二章/
│   ├── 2-1.docx
│   └── 2-2.docx
└── 其他.docx
```

## 🎨 高级筛选

### 1. 按文件格式筛选

只处理特定格式的音频文件：

```bash
# 只处理 MP3
python transcribe.py --dir ./音频文件夹 --pattern "*.mp3"

# 只处理 M4A
python transcribe.py --dir ./音频文件夹 --pattern "*.m4a"

# 只处理 WAV
python transcribe.py --dir ./音频文件夹 --pattern "*.wav"
```

### 2. 按文件名筛选

使用通配符匹配特定文件名：

```bash
# 只处理以 "lecture" 开头的文件
python transcribe.py --dir ./音频文件夹 --pattern "lecture*"

# 只处理以 "2024" 开头的文件
python transcribe.py --dir ./音频文件夹 --pattern "2024*"

# 只处理包含 "meeting" 的文件
python transcribe.py --dir ./音频文件夹 --pattern "*meeting*"
```

### 3. 组合筛选

```bash
# 递归查找所有以 "lecture" 开头的 MP3 文件
python transcribe.py --dir ./音频文件夹 --pattern "lecture*.mp3" --recursive
```

## 📊 批量处理模式优势

### 1. 模型只加载一次

传统方式每个文件都要加载模型：
```bash
# ❌ 低效：每次都加载模型
python transcribe.py --audio file1.mp3  # 加载模型...
python transcribe.py --audio file2.mp3  # 再次加载模型...
python transcribe.py --audio file3.mp3  # 又加载模型...
```

批量模式只加载一次：
```bash
# ✅ 高效：模型只加载一次
python transcribe.py --dir ./音频文件夹  # 加载模型一次，处理所有文件
```

**时间节省：**
- Large-v3 模型加载需要 10-20 秒
- 处理 10 个文件可节省 1.5-3 分钟

### 2. 统一的处理报告

批量完成后会生成详细的统计报告：

```
============================================================
批量转写完成！
============================================================
📊 处理统计:
   总文件数: 10
   成功: 9
   失败: 1
   总耗时: 15.3 分钟
   总音频时长: 2.5 小时
   平均处理速度: 9.8x

⚠️  失败的文件:
   - broken_audio.mp3: 音频格式不支持

📁 输出目录: C:\output
============================================================
```

### 3. 自动错误处理

单个文件失败不会影响整个批处理：
- ✅ 自动跳过损坏的文件
- ✅ 记录错误原因
- ✅ 继续处理剩余文件
- ✅ 最后统一报告

## 🔧 实用场景

### 场景 1: 会议录音整理

```bash
# 处理所有会议录音，生成会议记录
python transcribe.py \
  --dir ./会议录音 \
  --pattern "meeting_*.m4a" \
  --format docx,txt \
  --output-dir ./会议记录 \
  --segment-length 600
```

### 场景 2: 课程视频转字幕

```bash
# 批量生成课程字幕
python transcribe.py \
  --dir ./课程视频 \
  --recursive \
  --format srt \
  --output-dir ./字幕文件
```

### 场景 3: 播客转文字

```bash
# 处理播客音频，使用较小模型加快速度
python transcribe.py \
  --dir ./播客 \
  --pattern "*.mp3" \
  --model medium \
  --format docx,txt \
  --output-dir ./播客文稿
```

### 场景 4: 采访录音整理

```bash
# 递归处理所有采访录音
python transcribe.py \
  --dir ./采访 \
  --recursive \
  --format docx \
  --output-dir ./采访稿 \
  --segment-length 300
```

## 💡 最佳实践

### 1. 使用缓存

批量处理时，缓存特别有用：
- 第一次处理后，结果会被缓存
- 如果需要重新生成不同格式，几乎瞬间完成
- 音频文件修改后会自动重新转写

```bash
# 第一次：完整转写
python transcribe.py --dir ./音频 --format docx

# 第二次：使用缓存，瞬间生成 TXT 和 SRT
python transcribe.py --dir ./音频 --format txt,srt
```

### 2. 合理选择模型

根据音频数量和质量要求选择模型：

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| 少量文件（<10），需要高质量 | large-v3 | 质量最佳 |
| 大量文件（>50），质量要求不高 | medium 或 small | 速度更快 |
| 超大批量（>100） | small 或 base | 显著节省时间 |
| 音质较差的录音 | large-v3 | 容错能力强 |

### 3. 分批处理大型项目

如果有数百个文件：

```bash
# 按目录分批处理
python transcribe.py --dir ./batch1 --output-dir ./results
python transcribe.py --dir ./batch2 --output-dir ./results
python transcribe.py --dir ./batch3 --output-dir ./results
```

或使用筛选逐步处理：

```bash
# 先处理 MP3
python transcribe.py --dir ./all --pattern "*.mp3" --output-dir ./results

# 再处理 M4A
python transcribe.py --dir ./all --pattern "*.m4a" --output-dir ./results
```

### 4. 合理使用输出目录

**不指定输出目录：** 输出文件在源文件旁边
```bash
python transcribe.py --dir ./音频
# 结果：音频/file1.mp3 → 音频/file1.docx
```

**指定输出目录：** 统一管理转写结果
```bash
python transcribe.py --dir ./音频 --output-dir ./results
# 结果：音频/file1.mp3 → results/file1.docx
```

**递归 + 输出目录：** 保持目录结构
```bash
python transcribe.py --dir ./音频 --output-dir ./results --recursive
# 结果：音频/sub/file1.mp3 → results/sub/file1.docx
```

## ⚡ 性能优化

### 1. 硬件优化

```bash
# GPU 加速（推荐）
python transcribe.py --dir ./音频 --device cuda --compute-type float16

# CPU 模式（无 GPU）
python transcribe.py --dir ./音频 --device cpu --compute-type int8 --model small
```

### 2. 启用 VAD

语音活动检测可以跳过静音部分：

```bash
python transcribe.py --dir ./音频  # VAD 默认开启
```

如果音频质量很好，可以禁用 VAD 获得更完整的转写：

```bash
python transcribe.py --dir ./音频 --no-vad
```

### 3. 调整日志级别

处理大批量文件时，可以降低日志详细程度：

```bash
# 只显示关键信息
python transcribe.py --dir ./音频 --log-level WARNING

# 显示详细调试信息（排查问题）
python transcribe.py --dir ./音频 --log-level DEBUG
```

## 🔍 监控和调试

### 查看处理进度

程序会实时显示：
- 当前处理的文件（X/总数）
- 每个文件的处理时间
- 音频时长和处理速度

### 处理失败排查

如果某些文件失败：

1. **查看错误信息**：程序会列出失败文件和原因
2. **单独处理失败文件**：
   ```bash
   python transcribe.py --audio failed_file.mp3 --log-level DEBUG
   ```
3. **常见失败原因**：
   - 音频文件损坏
   - 格式不支持
   - 文件太大导致内存不足
   - 权限问题

## 📝 输出文件组织

### 默认行为（不指定输出目录）

```
音频文件夹/
├── lecture1.mp3
├── lecture1.docx       ← 生成
├── lecture2.mp3
└── lecture2.docx       ← 生成
```

### 使用输出目录

```
input/
├── lecture1.mp3
└── lecture2.mp3

output/                  ← 指定
├── lecture1.docx       ← 生成
└── lecture2.docx       ← 生成
```

### 递归 + 输出目录

```
input/
├── day1/
│   └── session1.mp3
└── day2/
    └── session1.mp3

output/                  ← 指定
├── day1/               ← 保持结构
│   └── session1.docx
└── day2/
    └── session1.docx
```

## 🎓 学习更多

- 查看完整文档：[README.md](README.md)
- 快速入门：[QUICKSTART.md](QUICKSTART.md)
- 代码示例：[example.py](example.py)

---

**开始高效批量转写吧！** 🚀

