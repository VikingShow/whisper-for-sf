"""
配置管理模块
支持命令行参数和配置文件
"""
import argparse
import os
from typing import Dict, Any


class Config:
    """配置类"""
    
    # 默认配置
    DEFAULT_MODEL_SIZE = "large-v3"
    DEFAULT_DEVICE = "cuda"
    DEFAULT_COMPUTE_TYPE = "float16"
    DEFAULT_SEGMENT_LENGTH = 300
    DEFAULT_LANGUAGE = "zh"
    DEFAULT_BEAM_SIZE = 5
    
    def __init__(self):
        self.audio_file: str = ""
        self.audio_dir: str = "audio"  # 批量处理目录
        self.model_size: str = self.DEFAULT_MODEL_SIZE
        self.device: str = self.DEFAULT_DEVICE
        self.compute_type: str = self.DEFAULT_COMPUTE_TYPE
        self.segment_length: int = self.DEFAULT_SEGMENT_LENGTH
        self.language: str = self.DEFAULT_LANGUAGE
        self.beam_size: int = self.DEFAULT_BEAM_SIZE
        self.output_path: str = ""
        self.output_dir: str = ""  # 批量输出目录
        self.output_format: str = "docx"  # docx, txt, srt
        self.use_cache: bool = True
        self.vad_filter: bool = True
        self.log_level: str = "INFO"
        self.recursive: bool = False  # 递归扫描子目录
        self.file_pattern: str = "*"  # 文件匹配模式
    
    @classmethod
    def from_args(cls) -> 'Config':
        """从命令行参数创建配置"""
        parser = argparse.ArgumentParser(
            description='Whisper 音频转写工具',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
示例:
  python transcribe.py --audio 音频.m4a
  python transcribe.py --audio 音频.m4a --model medium --device cpu
  python transcribe.py --audio 音频.m4a --format txt,srt,docx
            '''
        )
        
        # 输入选项（二选一）
        input_group = parser.add_mutually_exclusive_group(required=True)
        
        input_group.add_argument(
            '--audio',
            type=str,
            help='单个音频文件路径'
        )
        
        input_group.add_argument(
            '--dir',
            type=str,
            help='批量处理：音频文件所在目录'
        )
        
        parser.add_argument(
            '--model',
            type=str,
            default=cls.DEFAULT_MODEL_SIZE,
            choices=['tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3'],
            help=f'模型大小 (默认: {cls.DEFAULT_MODEL_SIZE})'
        )
        
        parser.add_argument(
            '--device',
            type=str,
            default=cls.DEFAULT_DEVICE,
            choices=['cuda', 'cpu'],
            help=f'设备类型 (默认: {cls.DEFAULT_DEVICE})'
        )
        
        parser.add_argument(
            '--compute-type',
            type=str,
            default=cls.DEFAULT_COMPUTE_TYPE,
            choices=['float16', 'int8', 'int8_float16', 'float32'],
            help=f'计算类型 (默认: {cls.DEFAULT_COMPUTE_TYPE})'
        )
        
        parser.add_argument(
            '--segment-length',
            type=int,
            default=cls.DEFAULT_SEGMENT_LENGTH,
            help=f'每段时长（秒） (默认: {cls.DEFAULT_SEGMENT_LENGTH})'
        )
        
        parser.add_argument(
            '--language',
            type=str,
            default=cls.DEFAULT_LANGUAGE,
            help=f'音频语言 (默认: {cls.DEFAULT_LANGUAGE})'
        )
        
        parser.add_argument(
            '--beam-size',
            type=int,
            default=cls.DEFAULT_BEAM_SIZE,
            help=f'Beam search 大小 (默认: {cls.DEFAULT_BEAM_SIZE})'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='输出文件路径（单文件模式，不指定则自动生成）'
        )
        
        parser.add_argument(
            '--output-dir',
            type=str,
            help='批量输出目录（批量模式，不指定则在源文件目录）'
        )
        
        parser.add_argument(
            '--recursive',
            action='store_true',
            help='递归扫描子目录（批量模式）'
        )
        
        parser.add_argument(
            '--pattern',
            type=str,
            default='*',
            help='文件匹配模式，如 "*.mp3" 或 "lecture_*" (默认: *，匹配所有音频)'
        )
        
        parser.add_argument(
            '--format',
            type=str,
            default='docx',
            help='输出格式: docx, txt, md(markdown), srt 或多个用逗号分隔 (默认: docx)'
        )
        
        parser.add_argument(
            '--no-cache',
            action='store_true',
            help='禁用缓存'
        )
        
        parser.add_argument(
            '--no-vad',
            action='store_true',
            help='禁用语音活动检测（VAD）'
        )
        
        parser.add_argument(
            '--log-level',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            help='日志级别 (默认: INFO)'
        )
        
        args = parser.parse_args()
        
        # 创建配置对象
        config = cls()
        config.audio_file = args.audio or ""
        config.audio_dir = args.dir or ""
        config.model_size = args.model
        config.device = args.device
        config.compute_type = args.compute_type
        config.segment_length = args.segment_length
        config.language = args.language
        config.beam_size = args.beam_size
        config.output_path = args.output or ""
        config.output_dir = args.output_dir or ""
        config.output_format = args.format
        config.use_cache = not args.no_cache
        config.vad_filter = not args.no_vad
        config.log_level = args.log_level
        config.recursive = args.recursive
        config.file_pattern = args.pattern
        
        return config
    
    def validate(self) -> None:
        """验证配置"""
        # 验证输入
        if self.audio_file:
            # 单文件模式
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"音频文件不存在: {self.audio_file}")
            
            # 检查文件格式
            valid_extensions = ['.m4a', '.mp3', '.wav', '.flac', '.ogg', '.mp4', '.avi', '.mkv']
            ext = os.path.splitext(self.audio_file)[1].lower()
            if ext not in valid_extensions:
                raise ValueError(f"不支持的音频格式: {ext}，支持的格式: {', '.join(valid_extensions)}")
        
        elif self.audio_dir:
            # 批量处理模式
            if not os.path.exists(self.audio_dir):
                raise FileNotFoundError(f"目录不存在: {self.audio_dir}")
            if not os.path.isdir(self.audio_dir):
                raise ValueError(f"不是有效的目录: {self.audio_dir}")
        
        # 验证输出格式（支持别名）
        valid_formats = ['docx', 'txt', 'srt', 'md', 'markdown']
        formats = [f.strip().lower() for f in self.output_format.split(',')]
        for fmt in formats:
            if fmt not in valid_formats:
                raise ValueError(f"不支持的输出格式: {fmt}，支持的格式: {', '.join(valid_formats)}")
    
    def is_batch_mode(self) -> bool:
        """判断是否为批量处理模式"""
        return bool(self.audio_dir)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'audio_file': self.audio_file,
            'audio_dir': self.audio_dir,
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type,
            'segment_length': self.segment_length,
            'language': self.language,
            'beam_size': self.beam_size,
            'output_path': self.output_path,
            'output_dir': self.output_dir,
            'output_format': self.output_format,
            'use_cache': self.use_cache,
            'vad_filter': self.vad_filter,
            'recursive': self.recursive,
            'file_pattern': self.file_pattern,
        }


