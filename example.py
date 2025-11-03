"""
使用示例脚本
演示如何在代码中直接使用转写功能
"""
import logging
from config import Config
from transcribe import TranscriptionPipeline, setup_logging


def example_basic():
    """基础使用示例"""
    print("=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)
    
    # 配置日志
    setup_logging('INFO')
    
    # 创建配置
    config = Config()
    config.audio_file = "音频文件.m4a"
    config.model_size = "medium"
    config.device = "cuda"
    config.output_format = "docx"
    
    # 验证配置
    try:
        config.validate()
    except Exception as e:
        print(f"配置验证失败: {e}")
        return
    
    # 执行转写
    with TranscriptionPipeline(config) as pipeline:
        segments, info = pipeline.transcribe()
        output_files = pipeline.save_outputs(segments)
        
        print(f"✅ 转写完成，生成文件: {output_files}")


def example_multiple_formats():
    """多格式输出示例"""
    print("\n" + "=" * 60)
    print("示例 2: 多格式输出")
    print("=" * 60)
    
    setup_logging('INFO')
    
    config = Config()
    config.audio_file = "音频文件.m4a"
    config.model_size = "large-v3"
    config.output_format = "docx,txt,srt"  # 同时生成三种格式
    
    try:
        config.validate()
        
        with TranscriptionPipeline(config) as pipeline:
            segments, info = pipeline.transcribe()
            output_files = pipeline.save_outputs(segments)
            
            print(f"✅ 生成了 {len(output_files)} 个文件:")
            for f in output_files:
                print(f"   - {f}")
    except Exception as e:
        print(f"错误: {e}")


def example_custom_segments():
    """自定义分段长度示例"""
    print("\n" + "=" * 60)
    print("示例 3: 自定义分段")
    print("=" * 60)
    
    setup_logging('INFO')
    
    config = Config()
    config.audio_file = "音频文件.m4a"
    config.segment_length = 600  # 10分钟一段
    config.beam_size = 10  # 提高准确度
    
    try:
        config.validate()
        
        with TranscriptionPipeline(config) as pipeline:
            segments, info = pipeline.transcribe()
            print(f"✅ 共生成 {len(segments)} 个片段")
            print(f"   每段约 {config.segment_length} 秒")
    except Exception as e:
        print(f"错误: {e}")


def example_process_existing_segments():
    """处理已有片段数据示例"""
    print("\n" + "=" * 60)
    print("示例 4: 处理已有数据")
    print("=" * 60)
    
    from formatters import FormatterFactory
    
    # 模拟已有的片段数据
    segments = [
        (0.0, 10.5, "这是第一段文本内容。"),
        (10.5, 25.3, "这是第二段文本内容。"),
        (25.3, 40.0, "这是第三段文本内容。"),
    ]
    
    # 保存为不同格式
    for fmt in ['txt', 'srt', 'docx']:
        formatter = FormatterFactory.create(fmt, '示例文档')
        output_path = f"example_output.{fmt}"
        formatter.format(segments, output_path)
        print(f"✅ 已保存: {output_path}")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║  Whisper 音频转写工具 - 使用示例      ║
    ╚════════════════════════════════════════╝
    
    注意：这些示例仅供参考，需要替换为实际的音频文件路径
    """)
    
    # 运行示例（注释掉以避免实际执行）
    # example_basic()
    # example_multiple_formats()
    # example_custom_segments()
    example_process_existing_segments()
    
    print("\n" + "=" * 60)
    print("💡 提示：取消注释上面的函数调用来运行其他示例")
    print("=" * 60)


