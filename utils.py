"""
工具函数模块
"""
import re
import os
import hashlib
import pickle
import fnmatch
from typing import Optional, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """
    格式化时间为 HH:MM:SS 格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串
    """
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def format_timestamp(seconds: float, include_ms: bool = True) -> str:
    """
    格式化时间戳（用于字幕文件）
    
    Args:
        seconds: 秒数
        include_ms: 是否包含毫秒
        
    Returns:
        格式化后的时间戳 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if include_ms:
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def add_basic_punctuation(text: str) -> str:
    """
    改进的中文标点优化
    
    Args:
        text: 输入文本
        
    Returns:
        添加标点后的文本
    """
    # 去除多余空格（中文通常不需要空格）
    text = re.sub(r"\s+", "", text)
    text = text.strip()
    
    if not text:
        return text
    
    # 检查是否已有标点结尾
    if not re.search(r'[。！？；,，、]$', text):
        # 根据句子内容智能添加标点
        if re.search(r'[吗呢啊]$', text):
            # 疑问或语气词
            if text[-1] in ['吗', '呢']:
                text += '？'
            else:
                text += '！'
        elif re.search(r'[啊呀哦哇]$', text):
            # 感叹语气
            text += '！'
        else:
            # 默认添加句号
            text += '。'
    
    return text


def clean_text(text: str) -> str:
    """
    清理文本中的特殊字符和多余空格
    
    Args:
        text: 输入文本
        
    Returns:
        清理后的文本
    """
    # 移除控制字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # 合并多个空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_cache_path(audio_file: str, model_size: str) -> str:
    """
    生成缓存文件路径
    
    Args:
        audio_file: 音频文件路径
        model_size: 模型大小
        
    Returns:
        缓存文件路径
    """
    # 使用音频文件的绝对路径和修改时间生成哈希
    abs_path = os.path.abspath(audio_file)
    mtime = os.path.getmtime(abs_path) if os.path.exists(abs_path) else 0
    cache_key = f"{abs_path}_{model_size}_{mtime}"
    file_hash = hashlib.md5(cache_key.encode()).hexdigest()
    
    cache_dir = ".cache"
    return os.path.join(cache_dir, f"{file_hash}.pkl")


def load_from_cache(cache_path: str) -> Optional[Any]:
    """
    从缓存加载结果
    
    Args:
        cache_path: 缓存文件路径
        
    Returns:
        缓存的数据，如果不存在返回 None
    """
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
            logger.info(f"从缓存加载成功: {cache_path}")
            return data
    except Exception as e:
        logger.warning(f"加载缓存失败: {e}")
        return None


def save_to_cache(cache_path: str, data: Any) -> None:
    """
    保存数据到缓存
    
    Args:
        cache_path: 缓存文件路径
        data: 要缓存的数据
    """
    try:
        cache_dir = os.path.dirname(cache_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"已保存到缓存: {cache_path}")
    except Exception as e:
        logger.warning(f"保存缓存失败: {e}")


def get_output_path(audio_file: str, output_format: str, custom_path: str = "") -> str:
    """
    生成输出文件路径
    
    Args:
        audio_file: 音频文件路径
        output_format: 输出格式
        custom_path: 自定义输出路径
        
    Returns:
        输出文件路径
    """
    if custom_path:
        # 如果指定了自定义路径，确保有正确的扩展名
        base, ext = os.path.splitext(custom_path)
        if ext.lower() != f'.{output_format}':
            return f"{base}.{output_format}"
        return custom_path
    
    # 自动生成路径
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    return f"{base_name}.{output_format}"


def estimate_processing_time(duration: float, model_size: str, device: str) -> float:
    """
    估算处理时间
    
    Args:
        duration: 音频时长（秒）
        model_size: 模型大小
        device: 设备类型
        
    Returns:
        估算的处理时间（秒）
    """
    # 基于经验的估算系数
    model_factors = {
        'tiny': 0.1,
        'base': 0.15,
        'small': 0.2,
        'medium': 0.3,
        'large-v2': 0.5,
        'large-v3': 0.5,
    }
    
    device_factor = 1.0 if device == 'cuda' else 4.0
    model_factor = model_factors.get(model_size, 0.3)
    
    return duration * model_factor * device_factor


def format_duration(seconds: float) -> str:
    """
    格式化时长为可读字符串
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} 分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} 小时"


def find_audio_files(
    directory: str, 
    pattern: str = "*", 
    recursive: bool = False
) -> List[str]:
    """
    在目录中查找音频文件
    
    Args:
        directory: 搜索目录
        pattern: 文件名匹配模式（支持通配符）
        recursive: 是否递归搜索子目录
        
    Returns:
        音频文件路径列表
    """
    # 支持的音频格式
    audio_extensions = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.mp4', '.avi', '.mkv'}
    
    audio_files = []
    directory_path = Path(directory)
    
    # 根据是否递归选择遍历方式
    if recursive:
        file_iterator = directory_path.rglob(pattern)
    else:
        file_iterator = directory_path.glob(pattern)
    
    for file_path in file_iterator:
        if file_path.is_file():
            # 检查扩展名
            if file_path.suffix.lower() in audio_extensions:
                audio_files.append(str(file_path.absolute()))
    
    # 如果 pattern 不是 * 且没有扩展名，尝试匹配所有音频格式
    if pattern != "*" and not any(pattern.endswith(ext) for ext in audio_extensions):
        # 再次搜索，匹配所有音频扩展名
        for ext in audio_extensions:
            pattern_with_ext = f"{pattern}{ext}"
            if recursive:
                file_iterator = directory_path.rglob(pattern_with_ext)
            else:
                file_iterator = directory_path.glob(pattern_with_ext)
            
            for file_path in file_iterator:
                if file_path.is_file():
                    abs_path = str(file_path.absolute())
                    if abs_path not in audio_files:
                        audio_files.append(abs_path)
    
    # 排序以保证顺序一致
    audio_files.sort()
    
    logger.info(f"在 {directory} 中找到 {len(audio_files)} 个音频文件")
    if audio_files:
        logger.debug(f"找到的文件: {audio_files[:5]}{'...' if len(audio_files) > 5 else ''}")
    
    return audio_files


def get_relative_output_path(
    audio_file: str,
    base_input_dir: str,
    base_output_dir: str,
    output_format: str
) -> str:
    """
    生成保持目录结构的输出路径
    
    Args:
        audio_file: 音频文件路径
        base_input_dir: 输入基础目录
        base_output_dir: 输出基础目录
        output_format: 输出格式
        
    Returns:
        输出文件路径
    """
    audio_path = Path(audio_file)
    input_path = Path(base_input_dir)
    
    # 获取相对路径
    try:
        rel_path = audio_path.relative_to(input_path)
    except ValueError:
        # 如果不在同一目录树，使用文件名
        rel_path = Path(audio_path.name)
    
    # 更改扩展名
    output_filename = rel_path.stem + f".{output_format}"
    
    # 组合输出路径
    if base_output_dir:
        output_path = Path(base_output_dir) / rel_path.parent / output_filename
    else:
        # 如果没有指定输出目录，在源文件旁边生成
        output_path = audio_path.parent / output_filename
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return str(output_path)

