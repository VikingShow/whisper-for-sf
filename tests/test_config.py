"""
config.py 配置模块的单元测试
"""
import pytest
import tempfile
import os
from config import Config


class TestConfig:
    """测试配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert config.model_size == Config.DEFAULT_MODEL_SIZE
        assert config.device == Config.DEFAULT_DEVICE
        assert config.compute_type == Config.DEFAULT_COMPUTE_TYPE
        assert config.segment_length == Config.DEFAULT_SEGMENT_LENGTH
        assert config.language == Config.DEFAULT_LANGUAGE
        assert config.beam_size == Config.DEFAULT_BEAM_SIZE
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        config = Config()
        config.audio_file = "test.mp3"
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['audio_file'] == "test.mp3"
        assert config_dict['model_size'] == Config.DEFAULT_MODEL_SIZE
    
    def test_validate_missing_file(self):
        """测试验证不存在的文件"""
        config = Config()
        config.audio_file = "nonexistent.mp3"
        
        with pytest.raises(FileNotFoundError):
            config.validate()
    
    def test_validate_invalid_format(self):
        """测试验证无效的文件格式"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            config = Config()
            config.audio_file = temp_path
            
            with pytest.raises(ValueError, match="不支持的音频格式"):
                config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_validate_invalid_output_format(self):
        """测试验证无效的输出格式"""
        # 创建临时音频文件
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            temp_path = f.name
        
        try:
            config = Config()
            config.audio_file = temp_path
            config.output_format = "invalid"
            
            with pytest.raises(ValueError, match="不支持的输出格式"):
                config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_validate_multiple_formats(self):
        """测试验证多个输出格式"""
        # 创建临时音频文件
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            temp_path = f.name
        
        try:
            config = Config()
            config.audio_file = temp_path
            config.output_format = "docx,txt,srt"
            
            # 不应该抛出异常
            config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


