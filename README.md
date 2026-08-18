# 声迹（SoundChase）

基于 `faster-whisper` 的高性能语音转写服务（Speech-to-Text Service）：提供 CLI 批量转写 + HTTP API（同步 / 异步任务）。

## 功能

- 批量/递归转写：目录扫描、通配符过滤
- 多输出格式：`docx` / `txt` / `srt` / `md`
- VAD 静音过滤、简繁转换（OpenCC）、基础标点优化
- 缓存：API 侧基于“音频 SHA256 + 参数”缓存转写结果（默认开启）
- 可选：说话人分离（diarization，依赖环境/模型配置）

## QLoRA 微调

该项目包含 QLoRA 微调流程与产出：

- 训练脚本：`train_qlora.py`
- 基座模型：`openai/whisper-large-v3`
- 量化与 LoRA：4-bit 量化 + LoRA（`r=8`, `alpha=32`, `dropout=0.05`，目标层 `q_proj` / `v_proj`）
- 输出目录：`./qlora_out`（保存 LoRA 适配器与合并后的模型）

### 微调数据

- 数据清单：`dataset/manifest.jsonl`
- 数据字段：`audio`（相对路径）与 `text`（转写文本）
- 数据规模：98 条样本（98 个音频引用，均可在 `dataset/audio` 中找到）
- 音频基路径：`dataset/`（脚本会拼接 `audio_base_path`）

示例：
```json
{"audio": "audio/0001.mp3", "text": "……"}
```

## 安装

```bash
pip install -r requirements.txt
```

API 服务（可选）：

```bash
pip install -r requirements.api.txt
```

说明：
- 部分音频格式需要本机安装 `ffmpeg`。
- 首次运行会加载模型，耗时取决于硬件与模型大小。

## CLI 使用

单文件：

```bash
python transcribe.py --audio path/to/audio.mp3
```

批量（推荐）：

```bash
python transcribe.py --dir ./audio --recursive --pattern "*.mp3" --format docx,txt,srt
```

DOCX 模板化导出（含颂词自动识别）：
```bash
python transcribe.py --audio path/to/audio.mp3 --format docx ^
  --docx-template "C:\\path\\to\\template.docx" ^
  --docx-verse-style "Body Text" ^
  --docx-prose-style "Normal" ^
  --docx-margin-top 2.54 --docx-margin-bottom 2.54 ^
  --docx-margin-left 3.18 --docx-margin-right 3.18
```

启用 LLM 润色导出文稿（可选）：
```bash
set OPENAI_API_KEY=你的密钥
python transcribe.py --audio path/to/audio.mp3 --format docx,txt ^
  --llm-polish --llm-model gpt-5.2 ^
  --llm-base-url "https://api.bltcy.ai/v1"
```

## API 使用（FastAPI）

启动服务：

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

同步转写：

```bash
curl -X POST "http://localhost:8000/v1/transcribe?model=large-v3&language=zh&use_cache=true" ^
  -F "file=@path/to/audio.mp3"
```

返回示例（节选）：

```json
{
  "text": "...",
  "segments": [{"start": 0.0, "end": 3.2, "text": "..."}],
  "model": "large-v3",
  "cached": false,
  "elapsed_ms": 1234
}
```

异步任务（适合长音频）：

```bash
curl -X POST "http://localhost:8000/v1/jobs" -F "file=@path/to/audio.mp3"
curl "http://localhost:8000/v1/jobs/<job_id>"
```

## API 参数

`/v1/transcribe` 与 `/v1/jobs` 共享参数（Query）：

- `model`：默认 `large-v3`
- `device`：`cuda` / `cpu`
- `compute_type`：`float16` / `int8` / `int8_float16` / `float32`
- `language`：默认 `zh`
- `beam_size`：默认 `5`
- `vad_filter`：默认 `true`
- `enable_diarization`：默认 `false`
- `diarization_model`：默认 `pyannote/speaker-diarization`
- `use_cache`：默认 `true`

## 简历写法（可直接套用）

你可以用“系统能力 + 指标”来写，避免显得只是调用模型：

- 搭建语音转写服务（FastAPI），支持同步/异步任务、参数化推理与错误回传；实现基于音频 `SHA256` 的结果缓存以减少重复计算
- 设计转写流水线（VAD/后处理/多格式导出），在会议/讲座场景输出可直接用于字幕与文档归档的结构化结果（segments + timestamps）
- 补充量化指标：RTF（实时率）、P95 延迟、吞吐（音频小时/天）、单小时成本、CER/WER（自建小评测集即可）

## License

MIT，见 `LICENSE`。
