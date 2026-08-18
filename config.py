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
        self.output_format: str = "docx,srt"  # docx, txt, srt
        self.use_cache: bool = True
        self.vad_filter: bool = True
        self.log_level: str = "INFO"
        self.recursive: bool = False  # 递归扫描子目录
        self.file_pattern: str = "*"  # 文件匹配模式
        # 多人语音（说话人分离）
        self.enable_diarization: bool = False
        self.diarization_model: str = "pyannote/speaker-diarization"
        # DOCX 导出增强配置
        self.docx_template: str = ""
        self.docx_prose_style: str = ""
        self.docx_verse_style: str = ""
        self.docx_add_timestamps: bool = True
        self.docx_timestamp_interval: int = 300  # 时间戳间隔（秒），默认5分钟
        self.docx_margin_top_cm: float = 2.54
        self.docx_margin_bottom_cm: float = 2.54
        self.docx_margin_left_cm: float = 3.18
        self.docx_margin_right_cm: float = 3.18
        # LLM 后处理（可选）
        self.llm_polish: bool = False
        self.llm_model: str = "claude-opus-4-6"
        self.llm_search_model: str = "gpt-4o-all"
        self.llm_search_base_url: str = ""  # empty = use llm_base_url
        self.llm_search_api_key_env: str = ""  # empty = use llm_api_key_env
        self.llm_base_url: str = "https://api.bltcy.ai/v1"
        self.llm_api_key_env: str = "OPENAI_API_KEY"
        self.llm_timeout: int = 300
        self.llm_chunk_chars: int = 3000
        self.llm_max_tokens: int = 0  # 0 = let API decide
        # 并行润色（转写与 LLM 润色流水线并行）
        self.parallel_polish: bool = True
        self.parallel_polish_workers: int = 2

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
            help="模型名称 (如 'large-v3') 或本地 CTranslate2 模型的路径"
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
            default='docx,srt',
            help='输出格式: docx, txt, md(markdown), srt 或多个用逗号分隔 (默认: docx,srt)'
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

        parser.add_argument(
            '--diarization',
            action='store_true',
            help='启用多人语音说话人分离（需要 faster-whisper 的说话人分离依赖）'
        )

        parser.add_argument(
            '--diarization-model',
            type=str,
            default='pyannote/speaker-diarization',
            help='说话人分离模型名称或路径 (默认: pyannote/speaker-diarization)'
        )

        parser.add_argument(
            '--docx-template',
            type=str,
            default='',
            help='DOCX 模板路径（可选）。提供后会复用模板样式并清空模板正文再写入内容'
        )

        parser.add_argument(
            '--docx-prose-style',
            type=str,
            default='',
            help='DOCX 正文样式名（可选，如 "Normal"）'
        )

        parser.add_argument(
            '--docx-verse-style',
            type=str,
            default='',
            help='DOCX 颂词样式名（可选，如 "Body Text"）'
        )

        parser.add_argument(
            '--docx-add-timestamps',
            action=argparse.BooleanOptionalAction,
            default=True,
            help='DOCX 中插入时间戳（默认开启，--no-docx-add-timestamps 关闭）'
        )

        parser.add_argument(
            '--docx-timestamp-interval',
            type=int,
            default=300,
            help='DOCX 时间戳间隔秒数（默认: 300，即每5分钟）'
        )

        parser.add_argument(
            '--docx-margin-top',
            type=float,
            default=2.54,
            help='DOCX 上页边距（厘米，默认: 2.54）'
        )

        parser.add_argument(
            '--docx-margin-bottom',
            type=float,
            default=2.54,
            help='DOCX 下页边距（厘米，默认: 2.54）'
        )

        parser.add_argument(
            '--docx-margin-left',
            type=float,
            default=3.18,
            help='DOCX 左页边距（厘米，默认: 3.18）'
        )

        parser.add_argument(
            '--docx-margin-right',
            type=float,
            default=3.18,
            help='DOCX 右页边距（厘米，默认: 3.18）'
        )

        parser.add_argument(
            '--llm-polish',
            action='store_true',
            help='启用 LLM 对导出文稿做轻量润色（默认关闭）'
        )

        parser.add_argument(
            '--llm-model',
            type=str,
            default='claude-opus-4-6',
            help='LLM polish model (default: claude-opus-4-6)'
        )

        parser.add_argument(
            '--llm-search-model',
            type=str,
            default='gpt-4o-all',
            help='Search model for proper noun correction (default: gpt-4o-all, empty to disable)'
        )

        parser.add_argument(
            '--llm-search-base-url',
            type=str,
            default='',
            help='搜索模型 API Base URL（空则使用 --llm-base-url）'
        )
        parser.add_argument(
            '--llm-search-api-key-env',
            type=str,
            default='',
            help='搜索模型 API Key 环境变量名（空则使用 --llm-api-key-env）'
        )

        parser.add_argument(
            '--llm-base-url',
            type=str,
            default='https://api.bltcy.ai/v1',
            help='LLM API Base URL（OpenAI 兼容，默认: https://api.bltcy.ai/v1）'
        )

        parser.add_argument(
            '--llm-api-key-env',
            type=str,
            default='OPENAI_API_KEY',
            help='存放 API Key 的环境变量名（默认: OPENAI_API_KEY）'
        )

        parser.add_argument(
            '--llm-timeout',
            type=int,
            default=300,
            help='LLM request timeout in seconds (default: 300)'
        )

        parser.add_argument(
            '--llm-chunk-chars',
            type=int,
            default=3000,
            help='LLM 分块字符数（默认: 3000）'
        )

        parser.add_argument(
            '--llm-max-tokens',
            type=int,
            default=0,
            help='LLM 最大输出 token 数（0 = 由 API 决定，推理模型推荐设为 0）'
        )

        parser.add_argument(
            '--no-parallel-polish',
            action='store_true',
            help='禁用并行润色，强制串行处理（调试用）'
        )
        parser.add_argument(
            '--polish-workers',
            type=int,
            default=2,
            help='并行润色工作线程数（默认: 2）'
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
        config.enable_diarization = args.diarization
        config.diarization_model = args.diarization_model
        config.docx_template = args.docx_template or ""
        config.docx_prose_style = args.docx_prose_style or ""
        config.docx_verse_style = args.docx_verse_style or ""
        config.docx_add_timestamps = args.docx_add_timestamps
        config.docx_timestamp_interval = args.docx_timestamp_interval
        config.docx_margin_top_cm = args.docx_margin_top
        config.docx_margin_bottom_cm = args.docx_margin_bottom
        config.docx_margin_left_cm = args.docx_margin_left
        config.docx_margin_right_cm = args.docx_margin_right
        config.llm_polish = args.llm_polish
        config.llm_model = args.llm_model
        config.llm_search_model = args.llm_search_model
        config.llm_search_base_url = args.llm_search_base_url or ""
        config.llm_search_api_key_env = args.llm_search_api_key_env or ""
        config.llm_base_url = args.llm_base_url
        config.llm_api_key_env = args.llm_api_key_env
        config.llm_timeout = args.llm_timeout
        config.llm_chunk_chars = args.llm_chunk_chars
        config.parallel_polish = not args.no_parallel_polish
        config.parallel_polish_workers = args.polish_workers

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

        if self.docx_template and not os.path.exists(self.docx_template):
            raise FileNotFoundError(f"DOCX 模板不存在: {self.docx_template}")
        if self.docx_margin_top_cm <= 0 or self.docx_margin_bottom_cm <= 0:
            raise ValueError("DOCX 上下页边距必须大于 0")
        if self.docx_margin_left_cm <= 0 or self.docx_margin_right_cm <= 0:
            raise ValueError("DOCX 左右页边距必须大于 0")
        if self.llm_timeout <= 0:
            raise ValueError("LLM 超时必须大于 0")
        if self.llm_chunk_chars < 500:
            raise ValueError("LLM 分块字符数不能小于 500")
        if self.parallel_polish_workers < 1:
            raise ValueError("并行润色工作线程数不能小于 1")
    
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
            'enable_diarization': self.enable_diarization,
            'diarization_model': self.diarization_model,
            'docx_template': self.docx_template,
            'docx_prose_style': self.docx_prose_style,
            'docx_verse_style': self.docx_verse_style,
            'docx_add_timestamps': self.docx_add_timestamps,
            'docx_timestamp_interval': self.docx_timestamp_interval,
            'docx_margin_top_cm': self.docx_margin_top_cm,
            'docx_margin_bottom_cm': self.docx_margin_bottom_cm,
            'docx_margin_left_cm': self.docx_margin_left_cm,
            'docx_margin_right_cm': self.docx_margin_right_cm,
            'llm_polish': self.llm_polish,
            'llm_model': self.llm_model,
            'llm_search_model': self.llm_search_model,
            'llm_search_base_url': self.llm_search_base_url,
            'llm_search_api_key_env': self.llm_search_api_key_env,
            'llm_base_url': self.llm_base_url,
            'llm_api_key_env': self.llm_api_key_env,
            'llm_timeout': self.llm_timeout,
            'llm_chunk_chars': self.llm_chunk_chars,
            'parallel_polish': self.parallel_polish,
            'parallel_polish_workers': self.parallel_polish_workers,
        }


