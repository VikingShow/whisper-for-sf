"""
utils.py 工具函数的单元测试
"""
import pytest
import os
import tempfile
from utils import (
    format_time,
    format_timestamp,
    add_basic_punctuation,
    clean_text,
    get_cache_path,
    format_duration,
)


class TestFormatTime:
    """测试时间格式化函数"""
    
    def test_format_time_basic(self):
        """测试基本时间格式化"""
        assert format_time(0) == "00:00:00"
        assert format_time(59) == "00:00:59"
        assert format_time(60) == "00:01:00"
        assert format_time(3599) == "00:59:59"
        assert format_time(3600) == "01:00:00"
        assert format_time(3661) == "01:01:01"
    
    def test_format_time_large_values(self):
        """测试大数值"""
        assert format_time(7200) == "02:00:00"
        assert format_time(86400) == "24:00:00"
    
    def test_format_time_float(self):
        """测试浮点数输入"""
        assert format_time(90.5) == "00:01:30"
        assert format_time(3661.9) == "01:01:01"


class TestFormatTimestamp:
    """测试时间戳格式化函数"""
    
    def test_format_timestamp_with_ms(self):
        """测试带毫秒的时间戳"""
        assert format_timestamp(0) == "00:00:00,000"
        assert format_timestamp(1.5) == "00:00:01,500"
        assert format_timestamp(61.123) == "00:01:01,123"
    
    def test_format_timestamp_without_ms(self):
        """测试不带毫秒的时间戳"""
        assert format_timestamp(0, include_ms=False) == "00:00:00"
        assert format_timestamp(1.5, include_ms=False) == "00:00:01"


class TestAddBasicPunctuation:
    """测试标点添加函数"""
    
    def test_add_basic_punctuation_empty(self):
        """测试空字符串"""
        assert add_basic_punctuation("") == ""
    
    def test_add_basic_punctuation_period(self):
        """测试添加句号"""
        assert add_basic_punctuation("这是一句话") == "这是一句话。"
        assert add_basic_punctuation("今天天气很好") == "今天天气很好。"
    
    def test_add_basic_punctuation_question(self):
        """测试添加问号"""
        assert add_basic_punctuation("你好吗") == "你好吗？"
        assert add_basic_punctuation("这是什么呢") == "这是什么呢？"
    
    def test_add_basic_punctuation_exclamation(self):
        """测试添加感叹号"""
        assert add_basic_punctuation("太棒了啊") == "太棒了啊！"
        assert add_basic_punctuation("真是的呀") == "真是的呀！"
    
    def test_add_basic_punctuation_existing(self):
        """测试已有标点的情况"""
        assert add_basic_punctuation("这是一句话。") == "这是一句话。"
        assert add_basic_punctuation("你好吗？") == "你好吗？"
        assert add_basic_punctuation("太好了！") == "太好了！"
    
    def test_add_basic_punctuation_spaces(self):
        """测试去除空格"""
        assert add_basic_punctuation("这 是 一 句 话") == "这是一句话。"
        assert add_basic_punctuation("  前后有空格  ") == "前后有空格。"


class TestCleanText:
    """测试文本清理函数"""
    
    def test_clean_text_basic(self):
        """测试基本清理"""
        assert clean_text("正常文本") == "正常文本"
    
    def test_clean_text_spaces(self):
        """测试多余空格"""
        assert clean_text("多个  空格   测试") == "多个 空格 测试"
        assert clean_text("  前后空格  ") == "前后空格"
    
    def test_clean_text_control_chars(self):
        """测试控制字符"""
        text_with_control = "文本\x00包含\x1f控制\x7f字符"
        assert clean_text(text_with_control) == "文本包含控制字符"


class TestGetCachePath:
    """测试缓存路径生成函数"""
    
    def test_get_cache_path_basic(self):
        """测试基本缓存路径生成"""
        path = get_cache_path("test.mp3", "large-v3")
        assert path.startswith(".cache")
        assert path.endswith(".pkl")
    
    def test_get_cache_path_different_files(self):
        """测试不同文件生成不同路径"""
        path1 = get_cache_path("test1.mp3", "large-v3")
        path2 = get_cache_path("test2.mp3", "large-v3")
        assert path1 != path2
    
    def test_get_cache_path_different_models(self):
        """测试不同模型生成不同路径"""
        path1 = get_cache_path("test.mp3", "large-v3")
        path2 = get_cache_path("test.mp3", "medium")
        assert path1 != path2


class TestFormatDuration:
    """测试时长格式化函数"""
    
    def test_format_duration_seconds(self):
        """测试秒级时长"""
        assert "秒" in format_duration(30)
        assert format_duration(30) == "30.0 秒"
    
    def test_format_duration_minutes(self):
        """测试分钟级时长"""
        assert "分钟" in format_duration(120)
        assert format_duration(120) == "2.0 分钟"
    
    def test_format_duration_hours(self):
        """测试小时级时长"""
        assert "小时" in format_duration(7200)
        assert format_duration(7200) == "2.0 小时"


# Pytest 配置
@pytest.fixture
def temp_audio_file():
    """创建临时音频文件用于测试"""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(b'fake audio data')
        temp_path = f.name
    
    yield temp_path
    
    # 清理
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_cache_operations(temp_audio_file):
    """测试缓存读写操作"""
    from utils import save_to_cache, load_from_cache
    
    cache_path = get_cache_path(temp_audio_file, "test")
    test_data = {"test": "data", "number": 123}
    
    # 保存到缓存
    save_to_cache(cache_path, test_data)
    assert os.path.exists(cache_path)
    
    # 从缓存加载
    loaded_data = load_from_cache(cache_path)
    assert loaded_data == test_data
    
    # 清理
    if os.path.exists(cache_path):
        os.remove(cache_path)
    
    # 清理缓存目录（如果为空）
    cache_dir = os.path.dirname(cache_path)
    if os.path.exists(cache_dir) and not os.listdir(cache_dir):
        os.rmdir(cache_dir)


