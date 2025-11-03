"""
formatters.py 格式化模块的单元测试
"""
import pytest
import os
import tempfile
from formatters import (
    DocxFormatter,
    TxtFormatter,
    SrtFormatter,
    FormatterFactory,
)


@pytest.fixture
def sample_segments():
    """示例片段数据"""
    return [
        (0.0, 10.5, "这是第一段文本。"),
        (10.5, 25.3, "这是第二段文本，内容更长一些。"),
        (25.3, 40.0, "这是第三段文本，包含更多信息。"),
    ]


class TestFormatterFactory:
    """测试格式化器工厂"""
    
    def test_create_docx_formatter(self):
        """测试创建 DOCX 格式化器"""
        formatter = FormatterFactory.create('docx', 'Test')
        assert isinstance(formatter, DocxFormatter)
    
    def test_create_txt_formatter(self):
        """测试创建 TXT 格式化器"""
        formatter = FormatterFactory.create('txt', 'Test')
        assert isinstance(formatter, TxtFormatter)
    
    def test_create_srt_formatter(self):
        """测试创建 SRT 格式化器"""
        formatter = FormatterFactory.create('srt', 'Test')
        assert isinstance(formatter, SrtFormatter)
    
    def test_create_invalid_formatter(self):
        """测试创建无效格式化器"""
        with pytest.raises(ValueError, match="不支持的格式"):
            FormatterFactory.create('invalid', 'Test')
    
    def test_get_supported_formats(self):
        """测试获取支持的格式"""
        formats = FormatterFactory.get_supported_formats()
        assert 'docx' in formats
        assert 'txt' in formats
        assert 'srt' in formats


class TestTxtFormatter:
    """测试纯文本格式化器"""
    
    def test_txt_format(self, sample_segments):
        """测试纯文本格式化"""
        formatter = TxtFormatter('测试标题')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            output_path = f.name
        
        try:
            formatter.format(sample_segments, output_path)
            assert os.path.exists(output_path)
            
            # 验证内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '测试标题' in content
                assert '第一段文本' in content
                assert '00:00:00' in content
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestSrtFormatter:
    """测试 SRT 字幕格式化器"""
    
    def test_srt_format(self, sample_segments):
        """测试 SRT 格式化"""
        formatter = SrtFormatter('测试标题')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            output_path = f.name
        
        try:
            formatter.format(sample_segments, output_path)
            assert os.path.exists(output_path)
            
            # 验证内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '1\n' in content  # 序号
                assert '-->' in content  # 时间分隔符
                assert '第一段文本' in content
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_srt_format_structure(self, sample_segments):
        """测试 SRT 文件结构"""
        formatter = SrtFormatter('测试')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            output_path = f.name
        
        try:
            formatter.format(sample_segments, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 验证第一个字幕块
            assert lines[0].strip() == '1'
            assert '-->' in lines[1]
            assert '第一段文本' in lines[2]
            
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestDocxFormatter:
    """测试 Word 文档格式化器"""
    
    def test_docx_format(self, sample_segments):
        """测试 DOCX 格式化"""
        formatter = DocxFormatter('测试标题')
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            output_path = f.name
        
        try:
            formatter.format(sample_segments, output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


