"""
Unit tests for llm_polish.py.
"""
from llm_polish import (
    _chunk_segments,
    _extract_json_block,
    _is_meaningful_ascii_token,
    _is_safe_polish,
    _repair_json_string,
    polish_segments_with_llm,
)


def test_chunk_segments_splits_by_size():
    segments = [
        (0.0, 1.0, "a" * 400),
        (1.0, 2.0, "b" * 400),
        (2.0, 3.0, "c" * 400),
    ]
    chunks = _chunk_segments(segments, max_chars=700)
    assert len(chunks) == 3


def test_polish_returns_original_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    segments = [(0.0, 1.0, "原始文本。")]
    result = polish_segments_with_llm(
        segments,
        enabled=True,
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        timeout_seconds=10,
        api_key_env="OPENAI_API_KEY",
        chunk_chars=6000,
    )
    assert result == segments


def test_is_safe_polish_allows_number_conversion():
    original = "会议在2026年3月1日开始，共有12人。"
    changed = "会议在二零二六年三月一日开始，共有十二人。"
    assert _is_safe_polish(original, changed) is True


def test_is_safe_polish_accepts_light_edit():
    original = "今天我们继续学习上师瑜伽。"
    changed = "今天我们继续学习上师瑜伽。"
    assert _is_safe_polish(original, changed) is True


def test_is_meaningful_ascii_token_filters_asr_noise():
    assert _is_meaningful_ascii_token("fora") is False
    assert _is_meaningful_ascii_token("DeepSeek") is True
    assert _is_meaningful_ascii_token("gpt-4o") is True


def test_repair_json_escapes_raw_newlines_in_strings():
    broken = '{"segments": [{"index": 0, "text": "第一行\n第二行"}]}'
    parsed = _extract_json_block(broken)
    assert parsed["segments"][0]["text"] == "第一行\n第二行"


def test_repair_json_strips_trailing_commas():
    broken = '{"segments": [{"index": 0, "text": "a"},]}'
    parsed = _extract_json_block(broken)
    assert parsed["segments"][0]["index"] == 0


def test_repair_json_string_leaves_valid_input_unchanged():
    good = '{"a": "b\\nc"}'
    assert _repair_json_string(good) == good


def test_repair_json_escapes_unescaped_inner_quotes():
    broken = '{"segments": [{"index": 0, "text": "讲到"现见三有"主要是从"}]}'
    parsed = _extract_json_block(broken)
    assert parsed["segments"][0]["text"] == '讲到"现见三有"主要是从'


def test_repair_json_preamble_then_fenced_block():
    broken = 'Some prose reasoning\n\n```json\n{"segments": [{"index": 0, "text": "a"}]}\n```'
    parsed = _extract_json_block(broken)
    assert parsed["segments"][0]["text"] == "a"
