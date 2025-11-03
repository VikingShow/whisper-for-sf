# 🎙️ Whisper 音频转写工具

一个功能强大的音频转写工具，基于 OpenAI Whisper 模型，支持多种输出格式、智能分段、缓存机制等功能。

## ✨ 特性

- 🚀 **高性能转写**：基于 faster-whisper 实现，支持 GPU 加速
- 📝 **多格式输出**：支持 Word (docx)、纯文本 (txt)、字幕 (srt) 格式
- 🧠 **智能分段**：自动按时长合并片段，便于阅读
- 💾 **缓存机制**：避免重复转写，节省时间
- 🎯 **VAD 过滤**：智能检测语音活动，过滤静音部分
- 🌏 **繁简转换**：自动将繁体中文转换为简体
- ✍️ **标点优化**：智能添加标点符号
- 📊 **进度显示**：实时显示处理进度和预估时间
- 🔧 **灵活配置**：丰富的命令行参数，满足不同需求

## 📦 安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd whisper
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. GPU 支持（可选）

如果你有 NVIDIA GPU 并想使用 CUDA 加速：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## 🚀 快速开始

### 基础用法

**单文件转写：**
```bash
python transcribe.py --audio 音频文件.m4a
```

**批量转写（处理文件夹中所有音频）：**
```bash
python transcribe.py --dir ./音频文件夹
```

这将自动扫描文件夹中的所有音频文件并批量转写！

### 常用示例

#### 1. 生成多种格式

```bash
python transcribe.py --audio 音频.m4a --format docx,txt,srt
```

#### 2. 使用较小的模型（速度更快）

```bash
python transcribe.py --audio 音频.m4a --model medium
```

#### 3. CPU 模式（无 GPU）

```bash
python transcribe.py --audio 音频.m4a --device cpu --compute-type int8
```

#### 4. 自定义分段长度

```bash
python transcribe.py --audio 音频.m4a --segment-length 600
```

#### 5. 批量转写文件夹中的所有音频

```bash
python transcribe.py --dir ./音频文件夹
```

#### 6. 批量转写 + 递归搜索子目录

```bash
python transcribe.py --dir ./音频文件夹 --recursive
```

#### 7. 批量转写特定文件（使用通配符）

```bash
# 只转写 mp3 文件
python transcribe.py --dir ./音频文件夹 --pattern "*.mp3"

# 只转写以"lecture"开头的文件
python transcribe.py --dir ./音频文件夹 --pattern "lecture_*"
```

#### 8. 批量转写并指定输出目录

```bash
python transcribe.py --dir ./音频文件夹 --output-dir ./转写结果
```

#### 9. 禁用缓存

```bash
python transcribe.py --audio 音频.m4a --no-cache
```

## 📖 命令行参数

### 输入选项（二选一）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--audio` | 单个音频文件路径 | - |
| `--dir` | 批量处理：音频文件所在目录 | - |

### 批量处理选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output-dir` | 批量输出目录 | 与源文件相同 |
| `--recursive` | 递归扫描子目录 | False |
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
| `--format` | 输出格式：docx/txt/srt（可多选，用逗号分隔） | docx |

### 其他选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--no-cache` | 禁用缓存 | False |
| `--no-vad` | 禁用语音活动检测 | False |
| `--log-level` | 日志级别：DEBUG/INFO/WARNING/ERROR | INFO |

## 🎯 模型选择指南

| 模型 | 参数量 | 相对速度 | 准确度 | 推荐场景 |
|------|--------|----------|--------|----------|
| tiny | 39M | 最快 | 较低 | 快速测试 |
| base | 74M | 很快 | 一般 | 简单对话 |
| small | 244M | 快 | 良好 | 日常使用 |
| medium | 769M | 中等 | 很好 | 高质量转写 |
| large-v3 | 1550M | 较慢 | 最佳 | 专业级质量 |

**建议**：
- 💻 **有 GPU**：使用 large-v3 或 medium，`--compute-type float16`
- 🖥️ **仅 CPU**：使用 small 或 base，`--compute-type int8`

## 📂 输出格式说明

### Word 文档 (.docx)
- 包含标题、元数据、分段文本
- 自动设置字体和格式
- 适合编辑和阅读

### 纯文本 (.txt)
- 简洁的文本格式
- 包含时间戳
- 适合快速查看

### 字幕文件 (.srt)
- 标准 SRT 格式
- 可直接用于视频字幕
- 包含精确时间戳

## 💾 缓存机制

工具会自动缓存转写结果到 `.cache` 目录：
- 相同音频和模型的组合会复用缓存
- 音频文件修改后会自动重新转写
- 使用 `--no-cache` 可禁用缓存

## 🔧 项目结构

```
whisper/
├── transcribe.py       # 主程序
├── config.py          # 配置管理
├── utils.py           # 工具函数
├── formatters.py      # 输出格式化
├── requirements.txt   # 依赖列表
├── tests/            # 单元测试
│   └── test_utils.py
├── .cache/           # 缓存目录（自动生成）
└── README.md         # 说明文档
```

## 🧪 运行测试

```bash
pytest tests/ -v
```

## ⚠️ 注意事项

1. **首次运行**：首次使用时，程序会自动下载 Whisper 模型，可能需要一些时间
2. **内存需求**：large-v3 模型需要约 5GB GPU 显存或 10GB 系统内存
3. **支持格式**：支持常见音频格式（mp3、m4a、wav、flac、ogg 等）
4. **处理时间**：通常为音频时长的 0.3-2 倍，取决于模型大小和硬件配置

## 🐛 常见问题

### Q: 出现 CUDA 错误怎么办？
A: 使用 CPU 模式：`--device cpu --compute-type int8`

### Q: 转写速度太慢？
A: 尝试使用较小的模型：`--model medium` 或 `--model small`

### Q: 转写结果不准确？
A: 
- 使用更大的模型：`--model large-v3`
- 增加 beam size：`--beam-size 10`
- 确保音频质量良好

### Q: 如何处理长音频？
A: 程序已支持任意长度音频，会自动分段处理

### Q: 如何批量处理多个文件？
A: 使用 `--dir` 参数指定目录：
```bash
python transcribe.py --dir ./音频文件夹
```

### Q: 批量处理时如何保持目录结构？
A: 使用 `--output-dir` 参数，程序会自动保持源目录结构：
```bash
python transcribe.py --dir ./input --output-dir ./output --recursive
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，请提交 Issue。

---

**祝使用愉快！ 🎉**


