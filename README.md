# 🎙️ Whisper 音频转写工具

基于 OpenAI Whisper 的强大音频转写工具，支持单文件和批量处理，提供多种输出格式。

## ✨ 主要特性

- 🚀 **批量处理** - 自动扫描文件夹，批量转写所有音频文件
- 📝 **多格式输出** - 支持 Word (docx)、纯文本 (txt)、字幕 (srt) 格式
- 💾 **智能缓存** - 自动缓存转写结果，避免重复处理
- 🎯 **VAD 过滤** - 智能检测语音活动，跳过静音部分
- 🌏 **繁简转换** - 自动将繁体中文转换为简体
- ✍️ **标点优化** - 智能添加标点符号
- 📊 **进度显示** - 实时显示处理进度
- 🔧 **灵活配置** - 丰富的命令行参数

## 📦 安装

```bash
# 克隆仓库
git clone <repository-url>
cd whisper

# 安装依赖
pip install -r requirements.txt

# 可选：安装 GPU 支持（推荐）
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## 🚀 快速开始

### 单文件转写

```bash
python transcribe.py --audio 音频文件.m4a
```

### 批量转写（推荐）⭐

```bash
# 处理文件夹中所有音频
python transcribe.py --dir ./音频文件夹

# 递归搜索子目录
python transcribe.py --dir ./音频文件夹 --recursive

# 指定输出目录
python transcribe.py --dir ./input --output-dir ./output
```

## 📖 详细用法

### 基础示例

```bash
# 单文件，生成 Word 文档
python transcribe.py --audio 音频.m4a

# 批量处理，生成多种格式
python transcribe.py --dir ./音频 --format docx,txt,srt

# 使用较小模型（更快）
python transcribe.py --dir ./音频 --model medium

# CPU 模式（无 GPU）
python transcribe.py --audio 音频.m4a --device cpu --compute-type int8 --model small
```

### 高级示例

```bash
# 只处理 MP3 文件
python transcribe.py --dir ./音频 --pattern "*.mp3"

# 递归搜索并保持目录结构
python transcribe.py --dir ./input --output-dir ./output --recursive

# 自定义分段长度（10分钟一段）
python transcribe.py --audio 长音频.mp3 --segment-length 600

# 完整配置示例
python transcribe.py \
  --dir ./音频 \
  --recursive \
  --pattern "*.m4a" \
  --model medium \
  --format docx,txt,srt \
  --output-dir ./转写结果 \
  --segment-length 300
```

## 📋 命令行参数

### 输入选项（必选其一）

| 参数 | 说明 |
|------|------|
| `--audio` | 单个音频文件路径 |
| `--dir` | 批量处理：音频文件所在目录 |

### 批量处理选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output-dir` | 批量输出目录 | 与源文件相同 |
| `--recursive` | 递归搜索子目录 | 否 |
| `--pattern` | 文件匹配模式（如 "*.mp3"） | * (所有音频) |

### 转写选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model` | 模型大小：tiny/base/small/medium/large-v2/large-v3 | large-v3 |
| `--device` | 设备类型：cuda/cpu | cuda |
| `--compute-type` | 计算类型：float16/int8/int8_float16/float32 | float16 |
| `--segment-length` | 每段时长（秒） | 300 |
| `--language` | 音频语言代码 | zh |
| `--beam-size` | Beam search 大小 | 5 |

### 输出选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output` | 输出文件路径（单文件模式） | 自动生成 |
| `--format` | 输出格式：docx/txt/srt（可多选，逗号分隔） | docx |

### 其他选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--no-cache` | 禁用缓存 | 否 |
| `--no-vad` | 禁用语音活动检测 | 否 |
| `--log-level` | 日志级别：DEBUG/INFO/WARNING/ERROR | INFO |

完整参数列表：
```bash
python transcribe.py --help
```

## 🎯 模型选择指南

| 模型 | 参数量 | 相对速度 | 准确度 | 推荐场景 |
|------|--------|----------|--------|----------|
| tiny | 39M | 最快 | 较低 | 快速测试 |
| base | 74M | 很快 | 一般 | 简单对话 |
| small | 244M | 快 | 良好 | 日常使用 |
| medium | 769M | 中等 | 很好 | 高质量转写 |
| large-v3 | 1550M | 较慢 | 最佳 | 专业级质量 |

**建议**：
- 💻 **有 GPU**：使用 `large-v3` 或 `medium`，配置 `--compute-type float16`
- 🖥️ **仅 CPU**：使用 `small` 或 `base`，配置 `--compute-type int8`

## 📂 输出格式说明

### Word 文档 (.docx)
- 包含标题、元数据、分段文本
- 自动设置字体和格式
- 适合编辑和阅读

### 纯文本 (.txt)
- 简洁的文本格式
- 包含时间戳
- 适合快速查看和处理

### 字幕文件 (.srt)
- 标准 SRT 格式
- 可直接用于视频字幕
- 包含精确时间戳

## 💡 实用场景

### 会议录音整理

```bash
python transcribe.py \
  --dir ./会议录音 \
  --pattern "meeting_*.m4a" \
  --output-dir ./会议记录 \
  --format docx,txt
```

### 课程视频转字幕

```bash
python transcribe.py \
  --dir ./课程视频 \
  --recursive \
  --format srt \
  --output-dir ./字幕文件
```

### 播客批量转文字

```bash
python transcribe.py \
  --dir ./播客 \
  --pattern "*.mp3" \
  --model medium \
  --format docx,txt
```

### 采访录音整理

```bash
python transcribe.py \
  --dir ./采访 \
  --recursive \
  --segment-length 600 \
  --output-dir ./采访稿
```

## 💾 缓存机制

工具会自动缓存转写结果到 `.cache` 目录：
- 相同音频和模型的组合会复用缓存
- 音频文件修改后会自动重新转写
- 使用 `--no-cache` 可禁用缓存

**示例**：
```bash
# 第一次：完整转写（较慢）
python transcribe.py --dir ./音频 --format docx

# 第二次：使用缓存（瞬间完成）
python transcribe.py --dir ./音频 --format txt,srt
```

## 🔥 批量处理优势

### 1. 性能提升

**传统方式**（每个文件单独运行）：
```bash
python transcribe.py --audio file1.mp3  # 加载模型 10秒
python transcribe.py --audio file2.mp3  # 再次加载 10秒
python transcribe.py --audio file3.mp3  # 又加载 10秒
```

**批量模式**（模型只加载一次）：
```bash
python transcribe.py --dir ./音频  # 加载模型 10秒，处理所有文件
```

节省时间：处理10个文件节省 1.5-3 分钟

### 2. 智能错误处理

- 单个文件失败不影响其他文件
- 自动记录失败原因
- 继续处理剩余文件
- 最后统一报告

### 3. 详细统计报告

```
批量转写完成！
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
```

## 📊 处理时间参考

| 音频时长 | 模型 | 设备 | 预计时间 |
|---------|------|------|---------|
| 1 小时 | small | GPU | 3-5 分钟 |
| 1 小时 | medium | GPU | 5-8 分钟 |
| 1 小时 | large-v3 | GPU | 8-15 分钟 |
| 1 小时 | small | CPU | 15-30 分钟 |
| 1 小时 | medium | CPU | 30-60 分钟 |

## 🧪 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest tests/ -v

# 查看覆盖率
pytest tests/ --cov=. --cov-report=html
```

## 🛠️ 项目结构

```
whisper/
├── transcribe.py       # 主程序
├── config.py          # 配置管理
├── utils.py           # 工具函数
├── formatters.py      # 输出格式化
├── requirements.txt   # 依赖列表
├── tests/            # 单元测试
│   ├── test_utils.py
│   ├── test_config.py
│   └── test_formatters.py
├── .cache/           # 缓存目录（自动生成）
└── README.md         # 本文档
```

## ⚠️ 注意事项

1. **首次运行**：首次使用时，程序会自动下载 Whisper 模型，可能需要一些时间
2. **内存需求**：large-v3 模型需要约 5GB GPU 显存或 10GB 系统内存
3. **支持格式**：支持常见音频格式（mp3、m4a、wav、flac、ogg、mp4 等）
4. **处理时间**：通常为音频时长的 0.3-2 倍，取决于模型大小和硬件配置

## 🐛 常见问题

### Q: 找不到 CUDA / GPU 相关错误
**A**: 使用 CPU 模式
```bash
python transcribe.py --audio 音频.m4a --device cpu --compute-type int8 --model small
```

### Q: 转写速度太慢
**A**: 尝试以下方法
- 使用较小的模型：`--model medium` 或 `--model small`
- 启用 GPU（如果有）：确保安装 CUDA 版本的 PyTorch
- 降低 beam size：`--beam-size 3`

### Q: 转写结果不准确
**A**: 提高准确度
- 使用更大的模型：`--model large-v3`
- 增加 beam size：`--beam-size 10`
- 确保音频质量良好（清晰、无杂音）

### Q: 批量处理时某些文件失败
**A**: 
- 查看错误报告中的失败原因
- 单独处理失败文件并开启调试模式：
  ```bash
  python transcribe.py --audio failed_file.mp3 --log-level DEBUG
  ```

### Q: 如何处理超长音频（>3小时）
**A**: 程序已支持任意长度音频，会自动分段处理。可以调整分段长度：
```bash
python transcribe.py --audio 长音频.mp3 --segment-length 600
```

### Q: 批量处理时如何保持目录结构
**A**: 使用 `--output-dir` 参数，程序会自动保持源目录结构：
```bash
python transcribe.py --dir ./input --output-dir ./output --recursive
```

### Q: 如何只重新转写某些文件
**A**: 使用文件匹配模式或禁用缓存：
```bash
# 使用模式匹配
python transcribe.py --dir ./音频 --pattern "meeting_*.mp3"

# 或禁用缓存强制重新转写
python transcribe.py --dir ./音频 --no-cache
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 支持

如有问题或建议，请提交 Issue。

---

**祝使用愉快！** 🎉
