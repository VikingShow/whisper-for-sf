# 🎉 批量转写功能使用总结

## ✨ 新功能亮点

你的 Whisper 转写工具现已支持**智能批量处理**！无需编写脚本，一条命令即可处理整个文件夹。

## 🚀 快速开始

### 最简单的用法

```bash
# 处理文件夹中的所有音频文件
python transcribe.py --dir ./音频文件夹
```

就是这么简单！程序会：
- ✅ 自动扫描所有支持的音频格式（mp3, m4a, wav, flac, ogg, mp4等）
- ✅ 逐个转写并显示进度
- ✅ 模型只加载一次，大幅节省时间
- ✅ 自动跳过失败的文件，继续处理
- ✅ 生成详细的批处理报告

## 📋 常用命令示例

### 1. 基础批量转写

```bash
# 处理当前目录
python transcribe.py --dir .

# 处理指定目录
python transcribe.py --dir ./音频

# 生成多种格式
python transcribe.py --dir ./音频 --format docx,txt,srt
```

### 2. 递归搜索子目录

```bash
# 搜索所有子目录中的音频文件
python transcribe.py --dir ./音频 --recursive

# 递归搜索 + 指定输出目录
python transcribe.py --dir ./input --output-dir ./output --recursive
```

### 3. 筛选特定文件

```bash
# 只处理 MP3 文件
python transcribe.py --dir ./音频 --pattern "*.mp3"

# 只处理以 "meeting" 开头的文件
python transcribe.py --dir ./音频 --pattern "meeting*"

# 递归查找特定文件
python transcribe.py --dir ./音频 --pattern "*.m4a" --recursive
```

### 4. 完整配置示例

```bash
python transcribe.py \
  --dir ./会议录音 \
  --recursive \
  --pattern "*.m4a" \
  --model medium \
  --format docx,txt,srt \
  --output-dir ./会议记录 \
  --segment-length 600
```

## 🎯 实际使用场景

### 场景 1: 整理会议录音

```bash
python transcribe.py \
  --dir ./2024会议 \
  --pattern "meeting_*.m4a" \
  --output-dir ./会议记录 \
  --format docx
```

### 场景 2: 课程视频批量转字幕

```bash
python transcribe.py \
  --dir ./课程视频 \
  --recursive \
  --format srt \
  --output-dir ./字幕
```

### 场景 3: 播客整理

```bash
python transcribe.py \
  --dir ./播客 \
  --pattern "*.mp3" \
  --model medium \
  --format docx,txt
```

## 💡 核心优势

### 1. 性能优化

**传统方式**（每个文件单独运行）：
```bash
python transcribe.py --audio file1.mp3  # 加载模型 10秒
python transcribe.py --audio file2.mp3  # 再次加载 10秒
python transcribe.py --audio file3.mp3  # 又加载 10秒
# 总计浪费 30秒+
```

**批量模式**（模型只加载一次）：
```bash
python transcribe.py --dir ./音频  # 加载模型 10秒，处理所有文件
# 节省大量时间！
```

### 2. 智能错误处理

- 单个文件失败不影响整个批处理
- 自动记录失败原因
- 最后统一展示成功/失败统计

### 3. 详细的处理报告

处理完成后会显示：
```
============================================================
批量转写完成！
============================================================
📊 处理统计:
   总文件数: 15
   成功: 14
   失败: 1
   总耗时: 25.3 分钟
   总音频时长: 3.2 小时
   平均处理速度: 7.6x

⚠️  失败的文件:
   - corrupted.mp3: 音频格式错误

📁 输出目录: C:\output
============================================================
```

### 4. 灵活的输出管理

**选项 A：** 输出文件在源文件旁边
```bash
python transcribe.py --dir ./音频
# file1.mp3 → file1.docx (同一目录)
```

**选项 B：** 集中到输出目录
```bash
python transcribe.py --dir ./音频 --output-dir ./results
# ./音频/file1.mp3 → ./results/file1.docx
```

**选项 C：** 保持目录结构
```bash
python transcribe.py --dir ./音频 --output-dir ./results --recursive
# ./音频/sub/file1.mp3 → ./results/sub/file1.docx
```

## 📖 命令行参数说明

### 批量处理专用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--dir` | 要处理的目录 | `--dir ./音频` |
| `--output-dir` | 输出目录（可选） | `--output-dir ./output` |
| `--recursive` | 递归搜索子目录 | `--recursive` |
| `--pattern` | 文件名匹配模式 | `--pattern "*.mp3"` |

### 通用参数（依然有效）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model` | 模型大小 | large-v3 |
| `--device` | 设备类型 | cuda |
| `--format` | 输出格式 | docx |
| `--segment-length` | 分段长度（秒） | 300 |

完整参数列表请运行：
```bash
python transcribe.py --help
```

## 🔥 最佳实践

### 1. 选择合适的模型

| 文件数量 | 推荐模型 | 原因 |
|---------|---------|------|
| < 10 个 | large-v3 | 质量优先 |
| 10-50 个 | medium | 平衡质量和速度 |
| > 50 个 | small | 速度优先 |

### 2. 合理使用缓存

批量处理后，如果需要生成不同格式：
```bash
# 第一次：完整转写（较慢）
python transcribe.py --dir ./音频 --format docx

# 第二次：使用缓存（瞬间完成）
python transcribe.py --dir ./音频 --format txt,srt
```

### 3. 分批处理超大项目

如果有100+文件，建议分批：
```bash
# 按子目录分批
python transcribe.py --dir ./batch1 --output-dir ./results
python transcribe.py --dir ./batch2 --output-dir ./results

# 或按格式分批
python transcribe.py --dir ./all --pattern "*.mp3" --output-dir ./results
python transcribe.py --dir ./all --pattern "*.m4a" --output-dir ./results
```

## 🎓 完整文档

- **详细批量处理指南**：[BATCH_GUIDE.md](BATCH_GUIDE.md)
- **快速入门**：[QUICKSTART.md](QUICKSTART.md)
- **完整说明**：[README.md](README.md)

## 🆘 遇到问题？

### 查看帮助

```bash
python transcribe.py --help
```

### 调试模式

```bash
python transcribe.py --dir ./音频 --log-level DEBUG
```

### 常见问题

**Q: 找不到音频文件？**
A: 检查目录路径和文件模式：
```bash
python transcribe.py --dir ./音频 --log-level INFO
```

**Q: 某些文件失败？**
A: 查看最后的错误报告，单独处理失败的文件：
```bash
python transcribe.py --audio failed_file.mp3 --log-level DEBUG
```

**Q: 如何只重新转写某几个文件？**
A: 使用 `--no-cache` 强制重新转写：
```bash
python transcribe.py --dir ./音频 --no-cache
```

---

## 🎉 开始使用！

现在就试试批量转写功能：

```bash
# 单文件模式（原有功能）
python transcribe.py --audio 音频.m4a

# 批量模式（新功能）
python transcribe.py --dir ./音频文件夹
```

**享受高效的批量处理吧！** 🚀

