"""
Unit tests for config.py.
"""
import os
import tempfile

import pytest

from config import Config


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.model_size == Config.DEFAULT_MODEL_SIZE
        assert config.device == Config.DEFAULT_DEVICE
        assert config.compute_type == Config.DEFAULT_COMPUTE_TYPE
        assert config.segment_length == Config.DEFAULT_SEGMENT_LENGTH
        assert config.language == Config.DEFAULT_LANGUAGE
        assert config.beam_size == Config.DEFAULT_BEAM_SIZE
        assert config.docx_margin_top_cm == 2.54
        assert config.docx_margin_bottom_cm == 2.54
        assert config.docx_margin_left_cm == 3.18
        assert config.docx_margin_right_cm == 3.18
        assert config.llm_polish is False

    def test_config_to_dict(self):
        config = Config()
        config.audio_file = "test.mp3"
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["audio_file"] == "test.mp3"
        assert config_dict["model_size"] == Config.DEFAULT_MODEL_SIZE
        assert config_dict["docx_margin_left_cm"] == 3.18
        assert config_dict["llm_model"] == Config().llm_model

    def test_validate_missing_file(self):
        config = Config()
        config.audio_file = "nonexistent.mp3"
        with pytest.raises(FileNotFoundError):
            config.validate()

    def test_validate_invalid_format(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
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
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        try:
            config = Config()
            config.audio_file = temp_path
            config.output_format = "docx,txt,srt"
            config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_missing_docx_template(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        try:
            config = Config()
            config.audio_file = temp_path
            config.docx_template = "nonexistent-template.docx"
            with pytest.raises(FileNotFoundError, match="DOCX 模板不存在"):
                config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_invalid_margin(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        try:
            config = Config()
            config.audio_file = temp_path
            config.docx_margin_left_cm = 0
            with pytest.raises(ValueError, match="DOCX 左右页边距必须大于 0"):
                config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_validate_invalid_llm_chunk(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name
        try:
            config = Config()
            config.audio_file = temp_path
            config.llm_chunk_chars = 100
            with pytest.raises(ValueError, match="LLM 分块字符数不能小于 500"):
                config.validate()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
