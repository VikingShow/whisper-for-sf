"""
输出格式化模块
支持多种输出格式：Word、纯文本、字幕（SRT）
"""
from typing import List, Tuple
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import logging
from utils import format_time, format_timestamp

logger = logging.getLogger(__name__)


class BaseFormatter:
    """基础格式化器"""
    
    def __init__(self, title: str):
        self.title = title
    
    def format(self, segments: List[Tuple[float, float, str]], output_path: str) -> None:
        """
        格式化并保存输出
        
        Args:
            segments: 片段列表 [(start_time, end_time, text), ...]
            output_path: 输出文件路径
        """
        raise NotImplementedError


class DocxFormatter(BaseFormatter):
    """Word 文档格式化器"""
    
    def format(self, segments: List[Tuple[float, float, str]], output_path: str) -> None:
        """
        生成 Word 文档
        
        Args:
            segments: 片段列表 [(start_time, end_time, text), ...]
            output_path: 输出文件路径
        """
        try:
            doc = Document()
            
            # 设置默认字体
            style = doc.styles['Normal']
            style.font.name = 'SimSun'
            style.font.size = Pt(12)
            
            # 添加标题
            title = doc.add_heading(self.title, level=1)
            title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            # 添加元数据
            total_duration = segments[-1][1] if segments else 0
            meta = doc.add_paragraph()
            meta.add_run(f"总时长: {format_time(total_duration)}\n")
            meta.add_run(f"段落数: {len(segments)}")
            meta.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            # 添加分隔线
            doc.add_paragraph("─" * 50)
            
            # 添加各个片段
            for i, (start, end, text) in enumerate(segments, 1):
                # 添加段落标题
                heading = doc.add_heading(
                    f"第 {i} 段（{format_time(start)} → {format_time(end)}）",
                    level=2
                )
                heading.runs[0].font.color.rgb = RGBColor(0, 112, 192)
                
                # 添加正文
                paragraph = doc.add_paragraph(text)
                paragraph.paragraph_format.line_spacing = 1.5
                paragraph.paragraph_format.space_after = Pt(12)
            
            # 保存文档
            doc.save(output_path)
            logger.info(f"已保存 Word 文档: {output_path}")
            
        except Exception as e:
            logger.error(f"生成 Word 文档失败: {e}")
            raise


class TxtFormatter(BaseFormatter):
    """纯文本格式化器"""
    
    def format(self, segments: List[Tuple[float, float, str]], output_path: str) -> None:
        """
        生成纯文本文件
        
        Args:
            segments: 片段列表 [(start_time, end_time, text), ...]
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入标题和元数据
                f.write(f"{'=' * 60}\n")
                f.write(f"{self.title}\n")
                f.write(f"{'=' * 60}\n\n")
                
                total_duration = segments[-1][1] if segments else 0
                f.write(f"总时长: {format_time(total_duration)}\n")
                f.write(f"段落数: {len(segments)}\n")
                f.write(f"{'-' * 60}\n\n")
                
                # 写入各个片段
                for i, (start, end, text) in enumerate(segments, 1):
                    f.write(f"【第 {i} 段】{format_time(start)} → {format_time(end)}\n")
                    f.write(f"{text}\n\n")
                    f.write(f"{'-' * 60}\n\n")
            
            logger.info(f"已保存纯文本文件: {output_path}")
            
        except Exception as e:
            logger.error(f"生成纯文本文件失败: {e}")
            raise


class SrtFormatter(BaseFormatter):
    """SRT 字幕格式化器"""
    
    def format(self, segments: List[Tuple[float, float, str]], output_path: str) -> None:
        """
        生成 SRT 字幕文件
        
        Args:
            segments: 片段列表 [(start_time, end_time, text), ...]
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, (start, end, text) in enumerate(segments, 1):
                    # SRT 格式：
                    # 序号
                    # 开始时间 --> 结束时间
                    # 字幕文本
                    # 空行
                    f.write(f"{i}\n")
                    f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
                    f.write(f"{text}\n\n")
            
            logger.info(f"已保存 SRT 字幕文件: {output_path}")
            
        except Exception as e:
            logger.error(f"生成 SRT 字幕文件失败: {e}")
            raise


class FormatterFactory:
    """格式化器工厂"""
    
    _formatters = {
        'docx': DocxFormatter,
        'txt': TxtFormatter,
        'srt': SrtFormatter,
    }
    
    @classmethod
    def create(cls, format_type: str, title: str) -> BaseFormatter:
        """
        创建格式化器
        
        Args:
            format_type: 格式类型
            title: 文档标题
            
        Returns:
            格式化器实例
        """
        formatter_class = cls._formatters.get(format_type.lower())
        if not formatter_class:
            raise ValueError(f"不支持的格式: {format_type}")
        
        return formatter_class(title)
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """获取支持的格式列表"""
        return list(cls._formatters.keys())


