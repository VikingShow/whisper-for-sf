"""
Whisper 音频转写工具
支持多种输出格式、缓存、进度显示等功能
"""
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()
from typing import Dict, List, Tuple, Iterator, Optional
from faster_whisper import WhisperModel
from opencc import OpenCC
from tqdm import tqdm

from config import Config
from utils import (
    add_basic_punctuation,
    clean_text,
    get_cache_path,
    load_from_cache,
    save_to_cache,
    get_output_path,
    estimate_processing_time,
    format_duration,
    find_audio_files,
    get_relative_output_path,
)
from formatters import FormatterFactory
from llm_polish import polish_segments_with_llm

# 配置日志
logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """音频转写管道"""
    
    def __init__(self, config: Config):
        """
        初始化转写管道
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.model: Optional[WhisperModel] = None
        self.converter = OpenCC("t2s")  # 繁体转简体
        # 多人语音（说话人分离）
        self.diarization_pipeline = None
        
    def __enter__(self) -> 'TranscriptionPipeline':
        """上下文管理器入口"""
        logger.info(f"正在加载模型: {self.config.model_size}")
        try:
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type
            )
            logger.info("模型加载成功")

            # 如配置启用多人语音，则初始化说话人分离管道
            if getattr(self.config, "enable_diarization", False):
                try:
                    from faster_whisper.diarization import DiarizationPipeline  # type: ignore
                    self.diarization_pipeline = DiarizationPipeline(
                        self.config.diarization_model,
                        device=self.config.device,
                    )
                    logger.info(f"已初始化说话人分离模型: {self.config.diarization_model}")
                except Exception as e:
                    logger.error(f"无法启用多人语音说话人分离: {e}")
                    logger.error("将以单说话人模式继续转写，如需多人语音请检查 faster-whisper 版本和 pyannote 模型配置")
                    self.diarization_pipeline = None
                    self.config.enable_diarization = False
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self.model:
            del self.model
            self.model = None
            logger.debug("模型资源已释放")
    
    def transcribe(self) -> Tuple[List[Tuple[float, float, str]]]:
        """
        执行音频转写
        
        Returns:
            (合并后的片段列表, 转写信息)
        """
        # 仅在未启用说话人分离时使用缓存，避免不同配置共用结果
        use_cache = self.config.use_cache and not getattr(self.config, "enable_diarization", False)

        # 检查缓存
        if use_cache:
            cache_path = get_cache_path(self.config.audio_file, self.config.model_size)
            cached_data = load_from_cache(cache_path)
            if cached_data:
                logger.info("使用缓存的转写结果")
                return cached_data
        
        # 执行转写
        logger.info(f"开始转写音频: {self.config.audio_file}")
        segments, info = self._transcribe_audio()
        
        logger.info(f"音频时长: {format_duration(info.duration)}")
        logger.info(f"检测到语言: {info.language} (置信度: {info.language_probability:.2%})")
        
        # 处理片段
        logger.info("正在处理转写片段...")
        merged_segments = self._process_segments(segments)
        
        logger.info(f"共生成 {len(merged_segments)} 个片段")
        
        # 保存到缓存
        if use_cache:
            cache_data = (merged_segments, info)
            save_to_cache(cache_path, cache_data)
        
        return merged_segments, info
    
    def _transcribe_audio(self) -> Tuple[Iterator]:
        """
        调用 Whisper 模型进行转写
        
        Returns:
            (片段迭代器, 转写信息)
        """
        if not self.model:
            raise RuntimeError("模型未初始化")
        
        # 准备转写参数
        transcribe_params = {
            'audio': self.config.audio_file,
            'beam_size': self.config.beam_size,
            'language': self.config.language,
            'condition_on_previous_text': False,  # 防止前文错误传染后文
            'no_speech_threshold': 0.8,          # 提高“无语音”判断阈值
            'compression_ratio_threshold': 2.0,  # 过滤可疑乱码/重复
        }
        
        # 启用 VAD（语音活动检测）
        if self.config.vad_filter:
            transcribe_params['vad_filter'] = True
            transcribe_params['vad_parameters'] = {
                'min_silence_duration_ms': 500,
                'speech_pad_ms': 400,
            }
            logger.debug("已启用 VAD 过滤")

        # 启用说话人分离（如果支持）
        if getattr(self.config, "enable_diarization", False) and self.diarization_pipeline is not None:
            transcribe_params['diarization'] = self.diarization_pipeline
        
        try:
            segments, info = self.model.transcribe(**transcribe_params)
            return segments, info
        except TypeError as e:
            # 当前 faster-whisper 版本不支持 diarization 参数，回退到普通模式
            if 'diarization' in transcribe_params and 'unexpected keyword argument' in str(e):
                logger.warning("当前 faster-whisper 不支持 'diarization' 参数，将关闭多人语音说话人分离")
                transcribe_params.pop('diarization', None)
                self.config.enable_diarization = False
                segments, info = self.model.transcribe(**transcribe_params)
                return segments, info
            raise
        except Exception as e:
            logger.error(f"转写失败: {e}")
            raise
    
    def _process_segments(
        self, 
        segments: Iterator
    ) -> List[Tuple[float, float, str]]:
        """
        处理和合并转写片段
        
        Args:
            segments: 原始片段迭代器
            
        Returns:
            合并后的片段列表 [(start_time, end_time, text), ...]
        """
        merged_segments: List[Tuple[float, float, str]] = []
        temp_text = ""
        temp_start: Optional[float] = None
        temp_end: Optional[float] = None
        temp_speaker: Optional[str] = None
        
        # 使用进度条
        with tqdm(desc="处理音频片段", unit="段") as pbar:
            for seg in segments:
                # 繁体转简体
                text = self.converter.convert(seg.text.strip())
                speaker = getattr(seg, "speaker", None)
                
                # 清理文本；开启 LLM 润色时不预加标点，交由 LLM 处理
                text = clean_text(text)
                if not getattr(self.config, "llm_polish", False):
                    text = add_basic_punctuation(text)

                # 初始化起始时间和说话人
                if temp_start is None:
                    temp_start = seg.start
                    temp_speaker = speaker

                same_speaker = (not getattr(self.config, "enable_diarization", False)) or (speaker == temp_speaker)

                # 如果说话人变更，先冻结上一段
                if getattr(self.config, "enable_diarization", False) and not same_speaker:
                    merged_segments.append(
                        (temp_start, temp_end if temp_end is not None else seg.start, self._format_segment_text(temp_text, temp_speaker))
                    )
                    temp_start = seg.start
                    temp_text = ""
                    temp_speaker = speaker

                temp_end = seg.end
                temp_text += text

                # 根据设置的段长合并
                if temp_end - temp_start >= self.config.segment_length:
                    merged_segments.append(
                        (temp_start, temp_end, self._format_segment_text(temp_text, temp_speaker))
                    )
                    temp_text = ""
                    temp_start = None
                    temp_end = None
                    temp_speaker = None
                    pbar.update(1)
        
        # 处理剩余文本
        if temp_text:
            merged_segments.append(
                (temp_start if temp_start is not None else 0.0,
                 temp_end if temp_end is not None else 0.0,
                 self._format_segment_text(temp_text, temp_speaker))
            )
        
        return merged_segments

    def _format_segment_text(self, text: str, speaker: Optional[str]) -> str:
        """
        根据需要在文本开头添加说话人标签，方便 SRT/文档显示多人语音。
        """
        clean = text.strip()
        if not clean:
            return ""

        if not getattr(self.config, "enable_diarization", False) or not speaker:
            return clean

        label = speaker
        if isinstance(speaker, str) and "SPEAKER_" in speaker:
            try:
                idx = int(speaker.split("_")[-1])
                label = f"说话人{idx + 1}"
            except ValueError:
                label = speaker

        return f"[{label}] {clean}"

    def _get_formatter_options(self) -> dict:
        """构建格式化器选项（当前主要用于 DOCX 模板化导出）。"""
        return {
            "docx_template": getattr(self.config, "docx_template", ""),
            "docx_prose_style": getattr(self.config, "docx_prose_style", ""),
            "docx_verse_style": getattr(self.config, "docx_verse_style", ""),
            "docx_add_timestamps": getattr(self.config, "docx_add_timestamps", False),
            "docx_margin_top_cm": getattr(self.config, "docx_margin_top_cm", 2.54),
            "docx_margin_bottom_cm": getattr(self.config, "docx_margin_bottom_cm", 2.54),
            "docx_margin_left_cm": getattr(self.config, "docx_margin_left_cm", 3.18),
            "docx_margin_right_cm": getattr(self.config, "docx_margin_right_cm", 3.18),
        }

    def get_output_segments_for_formats(
        self,
        segments: List[Tuple[float, float, str]],
        formats: List[str],
    ) -> Dict[str, List[Tuple[float, float, str]]]:
        """
        根据格式准备导出文本：
        - srt 保持原始文本
        - docx/txt/md 可选 LLM 润色
        """
        normalized_formats = [fmt.strip().lower() for fmt in formats]
        need_polish = any(fmt in {"docx", "txt", "md", "markdown"} for fmt in normalized_formats)
        polished = segments
        if need_polish:
            polished = polish_segments_with_llm(
                segments,
                enabled=bool(getattr(self.config, "llm_polish", False)),
                model=str(getattr(self.config, "llm_model", "claude-opus-4-6")),
                base_url=str(getattr(self.config, "llm_base_url", "https://api.bltcy.ai/v1")),
                timeout_seconds=int(getattr(self.config, "llm_timeout", 180)),
                api_key_env=str(getattr(self.config, "llm_api_key_env", "OPENAI_API_KEY")),
                chunk_chars=int(getattr(self.config, "llm_chunk_chars", 3000)),
                search_model=str(getattr(self.config, "llm_search_model", "gpt-4o-all")),
                search_base_url=str(getattr(self.config, "llm_search_base_url", "")),
                search_api_key_env=str(getattr(self.config, "llm_search_api_key_env", "")),
            )

        output_map: Dict[str, List[Tuple[float, float, str]]] = {}
        for fmt in normalized_formats:
            if fmt == "srt":
                output_map[fmt] = segments
            else:
                output_map[fmt] = polished
        return output_map
    
    def save_outputs(self, segments: List[Tuple[float, float, str]]) -> List[str]:
        """
        保存转写结果到文件
        
        Args:
            segments: 片段列表
            
        Returns:
            输出文件路径列表
        """
        output_files = []
        base_name = os.path.splitext(os.path.basename(self.config.audio_file))[0]
        
        # 解析输出格式
        formats = [f.strip() for f in self.config.output_format.split(',')]
        output_segments_map = self.get_output_segments_for_formats(segments, formats)
        
        for fmt in formats:
            try:
                # 生成输出路径
                output_path = get_output_path(
                    self.config.audio_file,
                    fmt,
                    self.config.output_path
                )
                
                # 创建格式化器并保存
                formatter = FormatterFactory.create(
                    fmt,
                    base_name,
                    options=self._get_formatter_options(),
                )
                formatter.format(output_segments_map.get(fmt.lower(), segments), output_path)
                
                output_files.append(output_path)
                
            except Exception as e:
                logger.error(f"保存 {fmt} 格式失败: {e}")
                raise
        
        return output_files


def setup_logging(level: str) -> None:
    """
    配置日志系统
    
    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def process_single_file(config: Config) -> None:
    """处理单个文件"""
    # 显示配置信息
    logger.info("=" * 60)
    logger.info("音频转写任务配置:")
    logger.info(f"  音频文件: {config.audio_file}")
    logger.info(f"  模型大小: {config.model_size}")
    logger.info(f"  设备类型: {config.device}")
    logger.info(f"  输出格式: {config.output_format}")
    logger.info(f"  段落长度: {config.segment_length} 秒")
    logger.info("=" * 60)
    
    # 记录开始时间
    start_time = time.time()
    
    # 使用管道进行转写
    with TranscriptionPipeline(config) as pipeline:
        # 转写音频
        segments, info = pipeline.transcribe()
        
        # 保存输出
        logger.info("正在保存转写结果...")
        output_files = pipeline.save_outputs(segments)
    
    # 计算耗时
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # 显示结果
    logger.info("=" * 60)
    logger.info("✅ 转写完成！")
    logger.info(f"⏱  总耗时: {format_duration(elapsed_time)}")
    logger.info(f"📊 音频时长: {format_duration(info.duration)}")
    logger.info(f"⚡ 处理速度: {info.duration / elapsed_time:.2f}x 实时速度")
    logger.info(f"📝 生成文件:")
    for output_file in output_files:
        file_size = os.path.getsize(output_file) / 1024  # KB
        logger.info(f"   - {output_file} ({file_size:.1f} KB)")
    logger.info("=" * 60)


def _polish_and_save_one_file(
    segments: List[Tuple[float, float, str]],
    audio_file: str,
    audio_dir: str,
    output_dir: str,
    output_format: str,
    pipeline: 'TranscriptionPipeline',
) -> Dict:
    """
    在后台线程中执行 LLM 润色 + 保存所有输出格式。

    Returns:
        {'file': str, 'output_files': [str, ...], 'elapsed_time': float}
    """
    file_start = time.time()
    output_files: List[str] = []
    formats = [f.strip() for f in output_format.split(',')]

    output_segments_map = pipeline.get_output_segments_for_formats(segments, formats)

    for fmt in formats:
        output_path = get_relative_output_path(
            audio_file, audio_dir, output_dir, fmt
        )
        formatter = FormatterFactory.create(
            fmt,
            os.path.splitext(os.path.basename(audio_file))[0],
            options=pipeline._get_formatter_options(),
        )
        formatter.format(
            output_segments_map.get(fmt.lower(), segments), output_path
        )
        output_files.append(output_path)
        logger.debug("  Saved: %s", output_path)

    elapsed = time.time() - file_start
    return {
        'file': audio_file,
        'output_files': output_files,
        'elapsed_time': elapsed,
    }


def process_batch(config: Config) -> None:
    """批量处理多个文件"""
    # 查找音频文件
    logger.info("=" * 60)
    logger.info("批量转写模式")
    logger.info(f"  输入目录: {config.audio_dir}")
    logger.info(f"  文件模式: {config.file_pattern}")
    logger.info(f"  递归搜索: {'是' if config.recursive else '否'}")
    logger.info(f"  输出目录: {config.output_dir or '(与源文件相同)'}")
    logger.info(f"  模型大小: {config.model_size}")
    logger.info(f"  输出格式: {config.output_format}")
    logger.info("=" * 60)
    
    # 查找所有音频文件
    audio_files = find_audio_files(
        config.audio_dir,
        config.file_pattern,
        config.recursive
    )
    
    if not audio_files:
        logger.warning(f"⚠️  在 {config.audio_dir} 中没有找到匹配的音频文件")
        logger.info(f"   文件模式: {config.file_pattern}")
        logger.info(f"   支持的格式: .mp3, .m4a, .wav, .flac, .ogg, .mp4")
        return
    
    logger.info(f"📂 找到 {len(audio_files)} 个音频文件，开始批量转写...\n")
    
    # 统计信息
    total_start_time = time.time()
    successful = []
    failed = []
    
    # 判断是否启用并行润色：需要 llm_polish 开启 且 未禁用并行
    llm_polish_enabled = bool(getattr(config, "llm_polish", False))
    parallel_enabled = (
        llm_polish_enabled
        and bool(getattr(config, "parallel_polish", True))
    )

    # 使用管道处理所有文件（复用模型加载）
    with TranscriptionPipeline(config) as pipeline:
        if parallel_enabled:
            # ============================================================
            # 并行模式：转录和 LLM 润色流水线并行
            # ============================================================
            polish_workers = max(1, int(getattr(config, "parallel_polish_workers", 2)))
            logger.info("⚡ 并行润色模式，后台线程数: %d", polish_workers)

            polish_futures: Dict = {}
            results_by_idx: Dict[int, Dict] = {}

            with ThreadPoolExecutor(max_workers=polish_workers) as polish_executor:
                # --- 生产者阶段：串行转录，提交润色到后台 ---
                for idx, audio_file in enumerate(audio_files, 1):
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"[{idx}/{len(audio_files)}] 处理: {os.path.basename(audio_file)}")
                    logger.info(f"{'=' * 60}")

                    try:
                        original_audio_file = config.audio_file
                        original_output_path = config.output_path
                        config.audio_file = audio_file
                        if config.output_dir:
                            config.output_path = ""

                        # 转录（主线程，模型不线程安全）
                        transcribe_start = time.time()
                        segments, info = pipeline.transcribe()
                        transcribe_elapsed = time.time() - transcribe_start
                        logger.info(
                            "  转录完成 (%s)，提交润色后台任务...",
                            format_duration(transcribe_elapsed),
                        )

                        # 提交润色+保存到后台线程池
                        future = polish_executor.submit(
                            _polish_and_save_one_file,
                            segments,
                            audio_file,
                            config.audio_dir,
                            config.output_dir,
                            config.output_format,
                            pipeline,
                        )
                        polish_futures[future] = {
                            'idx': idx,
                            'audio_file': audio_file,
                            'info': info,
                            'transcribe_elapsed': transcribe_elapsed,
                        }

                        # 恢复 config 用于下一轮迭代
                        config.audio_file = original_audio_file
                        config.output_path = original_output_path

                    except Exception as e:
                        logger.error(f"❌ 转录失败: {e}")
                        failed.append({'file': audio_file, 'error': str(e)})
                        config.audio_file = original_audio_file
                        config.output_path = original_output_path
                        continue

                # --- 消费者阶段：等待所有后台润色完成 ---
                for future in as_completed(polish_futures):
                    meta = polish_futures[future]
                    idx = meta['idx']
                    audio_file = meta['audio_file']
                    info = meta['info']
                    transcribe_elapsed = meta['transcribe_elapsed']

                    try:
                        result = future.result()
                        total_elapsed = transcribe_elapsed + result['elapsed_time']
                        logger.info(
                            "✅ [%d/%d] 完成 %s (转录 %s, 润色 %s, 总计 %s)",
                            idx, len(audio_files),
                            os.path.basename(audio_file),
                            format_duration(transcribe_elapsed),
                            format_duration(result['elapsed_time']),
                            format_duration(total_elapsed),
                        )
                        logger.info("   音频时长: %s", format_duration(info.duration))
                        logger.info(
                            "   处理速度: %.2fx",
                            info.duration / total_elapsed if total_elapsed > 0 else 0,
                        )
                        results_by_idx[idx] = {
                            'file': audio_file,
                            'duration': info.duration,
                            'elapsed_time': total_elapsed,
                            'output_files': result['output_files'],
                        }
                    except Exception as e:
                        logger.error(
                            "❌ [%d/%d] 润色失败: %s - %s",
                            idx, len(audio_files),
                            os.path.basename(audio_file), e,
                        )
                        failed.append({'file': audio_file, 'error': str(e)})

            # 按原始顺序重建成功列表
            for idx in sorted(results_by_idx):
                successful.append(results_by_idx[idx])

        else:
            # ============================================================
            # 串行模式：转录 → 润色 → 保存（保持原有行为）
            # ============================================================
            for idx, audio_file in enumerate(audio_files, 1):
                try:
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"[{idx}/{len(audio_files)}] 处理: {os.path.basename(audio_file)}")
                    logger.info(f"{'=' * 60}")

                    original_audio_file = config.audio_file
                    original_output_path = config.output_path

                    config.audio_file = audio_file
                    if config.output_dir:
                        config.output_path = ""

                    # 转录
                    file_start_time = time.time()
                    segments, info = pipeline.transcribe()

                    # 润色 + 保存
                    result = _polish_and_save_one_file(
                        segments,
                        audio_file,
                        config.audio_dir,
                        config.output_dir,
                        config.output_format,
                        pipeline,
                    )

                    file_elapsed_time = time.time() - file_start_time

                    successful.append({
                        'file': audio_file,
                        'duration': info.duration,
                        'elapsed_time': file_elapsed_time,
                        'output_files': result['output_files'],
                    })

                    logger.info(f"✅ 完成 ({format_duration(file_elapsed_time)})")
                    logger.info(f"   音频时长: {format_duration(info.duration)}")
                    logger.info(f"   处理速度: {info.duration / file_elapsed_time:.2f}x")

                    config.audio_file = original_audio_file
                    config.output_path = original_output_path

                except Exception as e:
                    logger.error(f"❌ 处理失败: {e}")
                    failed.append({'file': audio_file, 'error': str(e)})
                    continue
    
    # 总结报告
    total_elapsed_time = time.time() - total_start_time
    
    logger.info("\n" + "=" * 60)
    logger.info("批量转写完成！")
    logger.info("=" * 60)
    logger.info(f"📊 处理统计:")
    logger.info(f"   总文件数: {len(audio_files)}")
    logger.info(f"   成功: {len(successful)}")
    logger.info(f"   失败: {len(failed)}")
    logger.info(f"   总耗时: {format_duration(total_elapsed_time)}")
    
    if successful:
        total_audio_duration = sum(item['duration'] for item in successful)
        logger.info(f"   总音频时长: {format_duration(total_audio_duration)}")
        logger.info(f"   平均处理速度: {total_audio_duration / total_elapsed_time:.2f}x")
    
    if failed:
        logger.warning(f"\n⚠️  失败的文件:")
        for item in failed:
            logger.warning(f"   - {os.path.basename(item['file'])}: {item['error']}")
    
    if config.output_dir:
        logger.info(f"\n📁 输出目录: {os.path.abspath(config.output_dir)}")
    
    logger.info("=" * 60)


def main() -> None:
    """主函数"""
    try:
        # 解析配置
        config = Config.from_args()
        
        # 配置日志
        setup_logging(config.log_level)
        
        # 验证配置
        logger.info("正在验证配置...")
        config.validate()
        
        # 根据模式选择处理方式
        if config.is_batch_mode():
            process_batch(config)
        else:
            process_single_file(config)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断操作")
        exit(1)
    except FileNotFoundError as e:
        logger.error(f"❌ 文件错误: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"❌ 配置错误: {e}")
        exit(1)
    except Exception as e:
        logger.exception(f"❌ 发生错误: {e}")
        exit(1)


if __name__ == "__main__":
    main()
