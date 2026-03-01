import os
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import librosa
import torch
from datasets import load_dataset, Audio, DatasetDict
from transformers import (
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    WhisperForConditionalGeneration,
    WhisperProcessor,
    HfArgumentParser,
)
from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training, get_peft_model

# 设置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- 1. 数据处理 Data Collator ---
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    """
    数据整理器，用于将批次数据整理成模型训练所需的格式。
    它负责将音频数据转换为特征向量，并对文本标签进行编码。
    """
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # 从特征中提取 input_features
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        # 从特征中提取 labels
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        # 将 -100 替换为 padding_token_id 以确保在损失计算中被忽略
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        # 如果批次中包含 BOS token，将其移除（Whisper 模型通常在内部处理 BOS）
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels
        

        return batch

# --- 2. 训练参数 Data Class ---
@dataclass
class ModelArguments:
    """模型参数"""
    model_name_or_path: str = field(
        default="openai/whisper-large-v3",
        metadata={"help": "The name or path of the Whisper model to fine-tune."}
    )

@dataclass
class DataTrainingArguments:
    """数据和训练配置"""
    dataset_path: str = field(
        default="./dataset/manifest.jsonl",
        metadata={"help": "Path to the manifest.jsonl file."}
    )
    audio_base_path: str = field(
        default="./dataset",
        metadata={"help": "Base path to resolve relative audio paths in manifest.jsonl."}
    )
    max_input_length: int = field(
        default=3000,
        metadata={"help": "Maximum input audio length in frames (approx. 30s * 50 frames/s)."}
    )
    language: str = field(
        default="zh",
        metadata={"help": "The language of the dataset."}
    )
    # 对于中文，通常不需要任务提示，但如果需要，可以设置
    task: str = field(
        default="transcribe",
        metadata={"help": "The task, either 'transcribe' or 'translate'."}
    )
    sampling_rate: int = field(
        default=16000,
        metadata={"help": "The sampling rate of the audio data."}
    )

@dataclass
class LoraArguments:
    """QLoRA 配置参数"""
    lora_r: int = field(default=8, metadata={"help": "Lora attention dimension."})
    lora_alpha: int = field(default=32, metadata={"help": "The alpha parameter for Lora scaling."})
    lora_dropout: float = field(default=0.05, metadata={"help": "The dropout probability for Lora layers."})
    # 仅在 Linear 层应用 LoRA
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj"])


# --- 3. 预处理函数 ---
def prepare_dataset(batch, processor, max_input_length, target_sampling_rate):
    """音频和文本预处理，手动使用 librosa 加载音频"""
    try:
        # 1. 手动加载音频文件 (batch["audio"] 现在是文件路径字符串)
        audio_path = batch["audio"]
        
        # 使用 librosa.load 手动加载音频，确保采样率正确
        # sr=None 保持原始采样率，然后由 processor 统一处理
        # 或者直接指定目标采样率 target_sampling_rate=16000
        speech_array, sampling_rate = librosa.load(
            audio_path, 
            sr=target_sampling_rate # 目标采样率 16000 Hz
        )

        # 2. 将加载的 NumPy 数组转换为特征向量
        # 注意: Whisper feature_extractor 需要一个 1D NumPy 数组
        batch["input_features"] = processor.feature_extractor(
            speech_array, 
            sampling_rate=sampling_rate
        ).input_features[0]

        # 检查音频长度
        if len(batch["input_features"]) > max_input_length:
            logger.warning(f"音频过长（{len(batch['input_features'])} > {max_input_length}）。跳过文件: {audio_path}")
            return None
        
        # 3. 对文本标签进行编码 (保持不变)
        batch["labels"] = processor.tokenizer(batch["text"], max_length=256, truncation=True).input_ids
    
        return batch

    except Exception as e:
        logger.error(f"处理文件 {batch.get('audio', 'Unknown')} 时出错: {e}")
        # 返回 None 会在后面的 .filter() 步骤中被移除
        return None
        

@dataclass
class CustomTrainingArguments(Seq2SeqTrainingArguments):
    """针对 RTX 4060 (8GB) 优化的训练参数"""
    # 基础设置
    output_dir: str = field(default="./qlora_out", metadata={"help": "Output directory for checkpoints and final model."})
    
    # 硬件优化（针对 8GB VRAM）
    per_device_train_batch_size: int = field(default=1, metadata={"help": "Batch size per device during training."})
    gradient_accumulation_steps: int = field(default=32, metadata={"help": "Number of updates steps to accumulate before performing a backward/update pass."})
    fp16: bool = field(default=True, metadata={"help": "Whether to use 16-bit (mixed) precision training."})
    gradient_checkpointing: bool = field(default=True, metadata={"help": "Use gradient checkpointing to save memory."})
    optim: str = field(default="paged_adamw_8bit", metadata={"help": "Optimizer to use, paged_adamw_8bit is essential for QLoRA memory savings."})
    
    # 训练策略（针对您的小数据集）
    max_steps: int = field(default=15, metadata={"help": "Total number of training steps to perform (approx 5 epochs for your data)."})
    learning_rate: float = field(default=1e-3, metadata={"help": "The initial learning rate for AdamW."})
    warmup_steps: int = field(default=5, metadata={"help": "Number of steps for the warmup phase."})
    
    # 日志与保存
    logging_steps: int = field(default=5, metadata={"help": "Log training metrics every X updates steps."})
    save_steps: int = field(default=10, metadata={"help": "Save checkpoint every X updates steps."})
    overwrite_output_dir: bool = field(default=True, metadata={"help": "Overwrite the content of the output directory."})
    report_to: str = field(default="none", metadata={"help": "Disable external reporting to save memory."})
    
# --- 4. 主函数 ---
def main():
    os.environ["HF_HUB_ENABLE_HF_AUDIO"] = "0"
    os.environ["HF_AUDIO_LOADER"] = "librosa"
    
    # 解析所有参数
    parser = HfArgumentParser((ModelArguments, DataTrainingArguments, LoraArguments, CustomTrainingArguments))
    model_args, data_args, lora_args, training_args = parser.parse_args_into_dataclasses()

    # 初始化 Processor
    processor = WhisperProcessor.from_pretrained(model_args.model_name_or_path, language=data_args.language, task=data_args.task)
    
    # 确保特有的 token 在 tokenizer 中存在
    if processor.tokenizer.bos_token is None:
        processor.tokenizer.add_special_tokens({'bos_token': '<s>'})
    if processor.tokenizer.eos_token is None:
        processor.tokenizer.add_special_tokens({'eos_token': '</s>'})

    # --- 数据加载与准备 ---
    raw_datasets = load_dataset(
        "json",
        data_files={"train": data_args.dataset_path},
    )
    
    # 将文本和相对路径转换为绝对路径
    def resolve_audio_path(example):
        example["audio"] = os.path.join(data_args.audio_base_path, example["audio"])
        return example
        
    raw_datasets = raw_datasets.map(resolve_audio_path)
    
    # 转换为 Audio 特征
    # raw_datasets = raw_datasets.cast_column(
    #     "audio", 
    #     Audio(sampling_rate=data_args.sampling_rate)
    # )
    
    # 在 98 条数据集中，我们不进行拆分，全部用于训练
    train_dataset = raw_datasets["train"]

    # 预处理数据
    logger.info("开始预处理数据集 (音频加载和文本编码)...")
    with training_args.main_process_first(desc="dataset map pre-processing"):
        vectorized_datasets = train_dataset.map(
            lambda batch: prepare_dataset(
                batch, 
                processor, 
                data_args.max_input_length, 
                data_args.sampling_rate
            ),
            remove_columns=train_dataset.column_names,
            num_proc=4, # 可以根据CPU核数调整
        ).filter(lambda x: x is not None) # 过滤掉过长的或处理失败的音频
        
    logger.info(f"成功处理 {len(vectorized_datasets)} 条训练数据。")

    # --- 模型加载与 QLoRA 设置 ---
    
    # 1. 加载基础模型
    model = WhisperForConditionalGeneration.from_pretrained(
        model_args.model_name_or_path,
        load_in_4bit=True, # 启用 4-bit 量化
        torch_dtype=torch.float16,
        device_map="auto",
    )
    
    # 2. 模型配置
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    
    # 将模型转换为 QLoRA 可训练格式
    model = prepare_model_for_kbit_training(model)

    # 3. 设置 LoRA 配置
    lora_config = LoraConfig(
        r=lora_args.lora_r,
        lora_alpha=lora_args.lora_alpha,
        lora_dropout=lora_args.lora_dropout,
        bias="none",
        target_modules=lora_args.target_modules,
        # Whisper 的编码器-解码器结构需要设置为 Seq2Seq
        # task_type="SEQ_2_SEQ_LM", 
    )

    # 4. 获取 Peft 模型
    model = get_peft_model(model, lora_config)
    
    model.print_trainable_parameters() # 打印可训练参数量

    # --- 训练设置 ---
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

    # 由于是微调，我们不需要评估（如果有验证集可以添加）
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=vectorized_datasets,
        eval_dataset=None,
        tokenizer=processor.tokenizer,
        data_collator=data_collator,
    )
    
    # 禁用梯度检查点，以便更好地进行 QLoRA 训练
    if training_args.gradient_checkpointing:
        model.config.use_cache = False

    # --- 训练 ---
    logger.info("开始训练...")
    train_result = trainer.train()
    trainer.save_model()  # 保存训练好的 LoRA 适配器 (adapter)

    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    trainer.save_state()

    # --- 保存最终模型（合并 LoRA 权重）---
    logger.info("正在合并 LoRA 权重并保存完整模型...")
    # 卸载 Peft 模型
    model.config.use_cache = True
    peft_model_id = training_args.output_dir
    
    # 重新加载 Peft 模型
    model = WhisperForConditionalGeneration.from_pretrained(
        model_args.model_name_or_path,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model = PeftModel.from_pretrained(model, peft_model_id)

    # 合并权重
    merged_model = model.merge_and_unload()
    
    # 保存合并后的模型和处理器
    final_output_dir = os.path.join(training_args.output_dir, "final_merged_model")
    merged_model.save_pretrained(final_output_dir)
    processor.save_pretrained(final_output_dir)
    logger.info(f"最终合并模型已保存到: {final_output_dir}")

if __name__ == "__main__":
    main()