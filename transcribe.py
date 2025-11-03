"""
Whisper 音频转写工具
支持多种输出格式、缓存、进度显示等功能
"""
import os
import time
import logging
from typing import List, Tuple, Iterator, Optional
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
        # 检查缓存
        if self.config.use_cache:
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
        if self.config.use_cache:
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
        }
        
        # 启用 VAD（语音活动检测）
        if self.config.vad_filter:
            transcribe_params['vad_filter'] = True
            transcribe_params['vad_parameters'] = {
                'min_silence_duration_ms': 500,
                'speech_pad_ms': 400,
            }
            logger.debug("已启用 VAD 过滤")
        
        try:
            segments, info = self.model.transcribe(**transcribe_params)
            return segments, info
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
        merged_segments = []
        temp_text = ""
        temp_start: Optional[float] = None
        temp_end: Optional[float] = None
        
        # 使用进度条
        with tqdm(desc="处理音频片段", unit="段") as pbar:
            for seg in segments:
                # 繁体转简体
                text = self.converter.convert(seg.text.strip())
                
                # 清理和优化文本
                text = clean_text(text)
                text = add_basic_punctuation(text)
                
                # 初始化起始时间
                if temp_start is None:
                    temp_start = seg.start
                
                temp_end = seg.end
                temp_text += text
                
                # 根据设置的段长合并
                if temp_end - temp_start >= self.config.segment_length:
                    merged_segments.append((temp_start, temp_end, temp_text.strip()))
                    temp_text = ""
                    temp_start = None
                    temp_end = None
                    pbar.update(1)
        
        # 处理剩余文本
        if temp_text:
            merged_segments.append((temp_start, temp_end, temp_text.strip()))
        
        return merged_segments
    
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
        
        for fmt in formats:
            try:
                # 生成输出路径
                output_path = get_output_path(
                    self.config.audio_file,
                    fmt,
                    self.config.output_path
                )
                
                # 创建格式化器并保存
                formatter = FormatterFactory.create(fmt, base_name)
                formatter.format(segments, output_path)
                
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
    
    # 使用管道处理所有文件（复用模型加载）
    with TranscriptionPipeline(config) as pipeline:
        for idx, audio_file in enumerate(audio_files, 1):
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"[{idx}/{len(audio_files)}] 处理: {os.path.basename(audio_file)}")
                logger.info(f"{'=' * 60}")
                
                # 临时修改配置的音频文件
                original_audio_file = config.audio_file
                original_output_path = config.output_path
                
                config.audio_file = audio_file
                
                # 如果指定了输出目录，生成相应的输出路径
                if config.output_dir:
                    # 为批量模式保留目录结构
                    config.output_path = ""  # 让 save_outputs 自动处理
                
                # 转写
                file_start_time = time.time()
                segments, info = pipeline.transcribe()
                
                # 保存输出（处理批量输出路径）
                output_files = []
                formats = [f.strip() for f in config.output_format.split(',')]
                
                for fmt in formats:
                    output_path = get_relative_output_path(
                        audio_file,
                        config.audio_dir,
                        config.output_dir,
                        fmt
                    )
                    
                    formatter = FormatterFactory.create(
                        fmt,
                        os.path.splitext(os.path.basename(audio_file))[0]
                    )
                    formatter.format(segments, output_path)
                    output_files.append(output_path)
                
                file_elapsed_time = time.time() - file_start_time
                
                # 记录成功
                successful.append({
                    'file': audio_file,
                    'duration': info.duration,
                    'elapsed_time': file_elapsed_time,
                    'output_files': output_files
                })
                
                logger.info(f"✅ 完成 ({format_duration(file_elapsed_time)})")
                logger.info(f"   音频时长: {format_duration(info.duration)}")
                logger.info(f"   处理速度: {info.duration / file_elapsed_time:.2f}x")
                
                # 恢复配置
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
