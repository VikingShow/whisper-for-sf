import os
from dataclasses import dataclass, field
import torch
from torch.utils.data import DataLoader
import librosa
from datasets import load_dataset, Audio

from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig  # <-- 导入
)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


# =========================================================
# ✅ 基本路径
# =========================================================

BASE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(BASE, "dataset", "manifest.jsonl")
# 注意：AUDIO_BASE 变量没有被使用，datasets 会自动处理相对路径
AUDIO_BASE = os.path.join(BASE, "dataset") 


MODEL_NAME = "openai/whisper-large-v3"
OUTPUT_DIR = "./qlora_out" # 建议为 QLoRA 输出换个新目录


# =========================================================
# ✅ 加载 Processor
# =========================================================
processor = WhisperProcessor.from_pretrained(MODEL_NAME)
feature_extractor = processor.feature_extractor
tokenizer = processor.tokenizer

# (已移除 load_audio 函数，不再需要)

# =========================================================
# ✅ 加载 JSON 数据
# =========================================================
dataset = load_dataset("json", data_files={"train": MANIFEST})["train"]

# 让 "audio" 字段被 datasets 自动加载并重采样
# 这会把 audio 字段变成一个字典: {'path': ..., 'array': ..., 'sampling_rate': 16000}
# dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))


# =========================================================
# ✅ 数据格式转换 (已修复)
# =========================================================
def prepare(batch):
    # 'batch["audio"]' 现在只是一个相对路径字符串, e.g., "audio\\0001.mp3"
    audio_path_suffix = batch["audio"]
    
    # 构建完整的文件路径
    full_path = os.path.join(AUDIO_BASE, audio_path_suffix)
    
    # 使用 librosa 加载、重采样到 16kHz、并转为单声道
    # librosa.load 会自动调用 ffmpeg (如果需要)
    try:
        audio_data, sr = librosa.load(full_path, sr=16000, mono=True)
    except Exception as e:
        print(f"Error loading audio file {full_path}: {e}")
        # 返回 None 或空数据，以便在 collate_fn 中跳过或处理
        return None # 或者你可以 raise e

    text = batch["text"]

    # 使用 processor 处理
    inputs = processor(
        audio_data,
        sampling_rate=16000,
        text=text,
        return_tensors="pt",
    )
    
    batch["input_features"] = inputs["input_features"].squeeze(0)
    batch["labels"] = inputs["labels"].squeeze(0)

    return batch


# 建议：如果数据集较大，可以开启多进程处理（Windows 上请小心使用）
# dataset = dataset.map(prepare, remove_columns=dataset.column_names, num_proc=2)
dataset = dataset.map(prepare, remove_columns=dataset.column_names)


# =========================================================
# ✅ collate_fn (保持不变, 你的实现是正确的)
# =========================================================
def collate_fn(batch):
    input_features = torch.stack([x["input_features"] for x in batch])
    labels = [x["labels"] for x in batch]

    # pad labels → -100
    labels = torch.nn.utils.rnn.pad_sequence(
        labels, batch_first=True, padding_value=-100
    )

    return {
        "input_features": input_features,
        "labels": labels
    }


# =========================================================
# ✅ Model + QLoRA (关键修改)
# =========================================================

# 1. 配置 4-bit 量化 (QLoRA 的核心)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,  # 推荐 40 系显卡使用 bfloat16
    bnb_4bit_use_double_quant=True,
)

# 2. 加载量化后的模型
model = WhisperForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,   # <-- 应用量化配置
    device_map={"": 0}                 # <-- 自动将模型分配到 GPU
)

# 3. (可选但推荐) 准备模型进行 k-bit 训练
model = prepare_model_for_kbit_training(model)

# 4. LoRA 配置
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], # 适用于 Whisper
    bias="none",
    task_type="SEQ_2_SEQ_LM"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()


# =========================================================
# ✅ TrainingArguments (关键修改, 适应 8GB VRAM)
# =========================================================
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=1,   # <-- 必须为 1
    gradient_accumulation_steps=8, # <-- 增大 (有效 batch size = 1 * 8 = 8)
    learning_rate=1e-4,
    warmup_steps=50,
    num_train_epochs=3,
    bf16=True,                       # <-- 使用 bf16 (比 fp16 更稳定)
    logging_steps=10,
    save_steps=500,
    eval_strategy="no",              # 不使用 eval
    report_to="none"                 # 或 "wandb"
)


# =========================================================
# ✅ Trainer
# =========================================================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    data_collator=collate_fn,
)

# 启动训练
trainer.train()

# =========================================================
# ✅ 保存 LoRA
# =========================================================
# 仅保存 LoRA 适配器权重
trainer.model.save_pretrained(OUTPUT_DIR)
print(f"QLoRA 适配器已保存至: {OUTPUT_DIR}")