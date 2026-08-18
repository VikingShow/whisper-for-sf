"""
LLM 后处理模块。
两阶段处理：1) 联网搜索校正专有名词  2) 主模型润色标点和内容
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

Segment = Tuple[float, float, str]
logger = logging.getLogger(__name__)

# Retry policy for LLM calls. Covers transient 5xx / SSL / timeout errors
# as well as the occasional malformed JSON returned by the model.
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk_segments(segments: List[Segment], max_chars: int) -> List[List[Tuple[int, Segment]]]:
    chunks: List[List[Tuple[int, Segment]]] = []
    current: List[Tuple[int, Segment]] = []
    current_size = 0

    for index, segment in enumerate(segments):
        text = segment[2] or ""
        seg_size = max(1, len(text))
        if current and current_size + seg_size > max_chars:
            chunks.append(current)
            current = []
            current_size = 0
        current.append((index, segment))
        current_size += seg_size

    if current:
        chunks.append(current)
    return chunks


def _repair_json_string(text: str) -> str:
    """
    Fix the most common JSON defects we see from LLM output:
    - raw newlines / tabs inside string values (not escaped)
    - unescaped ASCII " quote marks inside string values
      (claude-opus-4-6 copies Chinese quoted phrases using raw " chars)
    - trailing commas before ] or }

    A " is treated as end-of-string only if the next non-whitespace char is
    one of , : } ] (a valid JSON structural token). Otherwise we escape it.
    """
    out: List[str] = []
    in_string = False
    escape = False
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if escape:
            out.append(ch)
            escape = False
            i += 1
            continue
        if ch == "\\":
            out.append(ch)
            escape = True
            i += 1
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                out.append(ch)
                i += 1
                continue
            # In string: decide whether this " is a legitimate terminator.
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j >= n or text[j] in ",:}]":
                in_string = False
                out.append(ch)
            else:
                out.append('\\"')
            i += 1
            continue
        if in_string:
            if ch == "\n":
                # LLM may omit the closing quote before JSON structure close.
                # If this newline is followed by } or ], close the string.
                j = i + 1
                while j < n and text[j] in " \t":
                    j += 1
                if j < n and text[j] in "}]":
                    out.append('"')
                    in_string = False
                    continue  # re-process this newline outside the string
                out.append("\\n")
                i += 1
                continue
            if ch == "\r":
                out.append("\\r")
                i += 1
                continue
            if ch == "\t":
                out.append("\\t")
                i += 1
                continue
        out.append(ch)
        i += 1
    repaired = "".join(out)
    repaired = re.sub(r",(\s*[\]}])", r"\1", repaired)
    return repaired


def _try_loads(candidate: str):
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _extract_json_block(content: str):
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        marker_pos = stripped.find("{")
        if marker_pos >= 0:
            stripped = stripped[marker_pos:]

    candidates = [stripped]

    match = re.search(r"\{.*\}", content, flags=re.S)
    if match:
        candidates.append(match.group(0))

    match = re.search(r"\[.*\]", content, flags=re.S)
    if match:
        candidates.append(match.group(0))

    # For reasoning models: text often surrounds the JSON block.
    # Try extracting from the first { or [ to the very last } or ].
    first_brace = content.find("{")
    first_bracket = content.find("[")
    first = -1
    if first_brace >= 0 and first_bracket >= 0:
        first = min(first_brace, first_bracket)
    elif first_brace >= 0:
        first = first_brace
    elif first_bracket >= 0:
        first = first_bracket
    if first >= 0:
        last_brace = content.rfind("}")
        last_bracket = content.rfind("]")
        last = max(last_brace, last_bracket)
        if last > first:
            tail_candidate = content[first:last + 1]
            if tail_candidate not in candidates:
                candidates.append(tail_candidate)

    # First pass: try each candidate raw.
    for candidate in candidates:
        parsed = _try_loads(candidate)
        if parsed is not None:
            return parsed

    # Second pass: try each candidate after repair.
    for candidate in candidates:
        parsed = _try_loads(_repair_json_string(candidate))
        if parsed is not None:
            logger.debug("JSON parsed only after repair pass")
            return parsed

    raise ValueError("No valid JSON found in LLM response")


def _extract_protected_tokens(text: str) -> Dict[str, List[str]]:
    return {
        "speaker_tags": re.findall(r"\[[^\]]+\]", text),
        "numbers": re.findall(r"\d+(?:[.,]\d+)?%?", text),
        "ascii_words": re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\b", text),
    }


def _is_meaningful_ascii_token(token: str) -> bool:
    token = (token or "").strip()
    if not token:
        return False

    # Mostly Chinese lecture transcripts can contain stray lowercase ASCII
    # noise from ASR. Only protect tokens that look like actual names or
    # technical terms.
    if any(ch.isupper() for ch in token):
        return True
    if any(ch.isdigit() for ch in token):
        return True
    if "_" in token or "-" in token:
        return True
    return len(token) >= 8


def _is_safe_polish(original: str, candidate: str) -> bool:
    src = (original or "").strip()
    dst = (candidate or "").strip()
    if not dst:
        return False

    src_len = max(1, len(src))
    dst_len = len(dst)
    if dst_len < int(src_len * 0.45):
        return False
    if dst_len > int(src_len * 2.2):
        return False

    similarity = SequenceMatcher(None, src, dst).ratio()
    if similarity < 0.35:
        return False

    src_tokens = _extract_protected_tokens(src)
    dst_tokens = _extract_protected_tokens(dst)

    if any(tag not in dst_tokens["speaker_tags"] for tag in src_tokens["speaker_tags"]):
        return False

    # Note: number check removed - Chinese text legitimately converts
    # arabic digits (18) to Chinese numerals (十八) during polish.

    src_ascii = [w.lower() for w in src_tokens["ascii_words"] if _is_meaningful_ascii_token(w)]
    dst_ascii_lower = {w.lower() for w in dst_tokens["ascii_words"] if _is_meaningful_ascii_token(w)}
    if src_ascii:
        preserved = sum(1 for w in src_ascii if w in dst_ascii_lower)
        if preserved < len(src_ascii) * 0.5:
            return False

    return True


# ---------------------------------------------------------------------------
# Low-level API call
# ---------------------------------------------------------------------------

def _call_llm(
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout_seconds: int,
    system_prompt: str,
    user_content: str,
    temperature: float = 0,
    max_tokens: int = 0,  # 0 = let API decide (especially important for reasoning models)
) -> str:
    """Call an OpenAI-compatible chat API via requests library. Returns the assistant content string."""
    import requests as _requests

    endpoint = base_url.rstrip("/") + "/chat/completions"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    body: dict = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if max_tokens > 0:
        body["max_tokens"] = max_tokens

    try:
        resp = _requests.post(
            endpoint,
            json=body,
            headers={"Authorization": "Bearer " + api_key},
            timeout=timeout_seconds,
        )
        if not resp.ok:
            raise RuntimeError(
                "LLM API HTTP error: {} {}".format(resp.status_code, resp.text[:500])
            )
        parsed = resp.json()
    except _requests.exceptions.Timeout as exc:
        raise RuntimeError("LLM API timeout: {}".format(exc))
    except _requests.exceptions.ConnectionError as exc:
        raise RuntimeError("LLM API connection error: {}".format(exc))
    except _requests.exceptions.RequestException as exc:
        raise RuntimeError("LLM API network error: {}".format(exc))

    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError("LLM API returned empty choices")
    msg = (choices[0] or {}).get("message") or {}
    content = (msg.get("content") or "").strip()
    reasoning = (msg.get("reasoning_content") or "").strip()
    # DeepSeek reasoning models may put the real answer in reasoning_content.
    # Merge both: reasoning often contains the structured JSON output.
    if reasoning:
        if content:
            content = content + "\n\n" + reasoning
        else:
            content = reasoning
    if not content:
        raise RuntimeError("LLM API returned empty content")
    return content


# ---------------------------------------------------------------------------
# Phase 1: Web search to build a correction dictionary
# ---------------------------------------------------------------------------

_SEARCH_SYSTEM_PROMPT = (
    "CRITICAL: You are a JSON API endpoint. Your entire response must be a single JSON object "
    "and NOTHING else — no explanations, no markdown, no polite phrases.\n\n"
    "Task: find Chinese ASR misrecognition errors in Buddhist dharma lecture transcripts.\n"
    "Only flag characters that are clearly wrong due to similar pronunciation.\n"
    "Do NOT expand names, add book title marks, or change wording.\n\n"
    "You MUST respond with EXACTLY this format (and nothing else):\n"
    "{\"corrections\":[{\"wrong\":\"错词\",\"correct\":\"正词\"}]}\n\n"
    "If unsure or no errors: {\"corrections\":[]}"
)


def _search_corrections(
    text_sample: str,
    *,
    base_url: str,
    search_model: str,
    api_key: str,
    timeout_seconds: int,
) -> List[Dict[str, str]]:
    """Use a search-capable model to find proper noun corrections."""
    # Fallback: when the model ignores JSON instructions and writes prose,
    # try to extract corrections from natural language patterns.
    def _parse_corrections_from_text(text: str) -> List[Dict[str, str]]:
        corrections: List[Dict[str, str]] = []
        # Pattern: "XXX" -> "YYY" or "XXX"→"YYY" or "XXX" 改为/应为 "YYY"
        for pat in [
            r'"(.{1,15}?)"\s*(?:->|→|→|->|⇒|=>|→|改为|应为|改成|就是|即|应为|应为|应为|应是|应该为|可能是)\s*"(.{1,15}?)"',
            r'「(.{1,15}?)」\s*(?:->|→|→|->|⇒|=>|→|改为|应为)\s*「(.{1,15}?)」',
        ]:
            for m in re.finditer(pat, text):
                wrong = m.group(1).strip()
                correct = m.group(2).strip()
                if wrong and correct and wrong != correct:
                    corrections.append({"wrong": wrong, "correct": correct})
        # Deduplicate by wrong
        seen = set()
        unique: List[Dict[str, str]] = []
        for c in corrections:
            key = c["wrong"]
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    last_error: Optional[Exception] = None
    last_error_str: str = ""
    last_content: Optional[str] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            content = _call_llm(
                base_url=base_url,
                model=search_model,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                system_prompt=_SEARCH_SYSTEM_PROMPT,
                user_content=text_sample,
            )
            last_content = content
            parsed = _extract_json_block(content)
            if isinstance(parsed, dict):
                corrections = parsed.get("corrections", [])
            else:
                corrections = []
            if not isinstance(corrections, list):
                return []
            valid = []
            for c in corrections:
                if isinstance(c, dict) and c.get("wrong") and c.get("correct"):
                    valid.append(c)
            return valid
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            last_error_str = str(exc)
            # Try fallback: extract corrections from natural language prose
            if last_content:
                fallback = _parse_corrections_from_text(last_content)
                if fallback:
                    logger.info("  extracted %d corrections from prose fallback", len(fallback))
                    return fallback
            # Dump the raw response for debugging
            try:
                dump_path = os.path.join(
                    os.path.dirname(__file__) or ".",
                    ".cache", "search_failed_attempt_%d.txt" % attempt,
                )
                os.makedirs(os.path.dirname(dump_path), exist_ok=True)
                with open(dump_path, "w", encoding="utf-8") as fh:
                    fh.write(last_content or f"(API call failed: {last_error_str})")
                logger.warning("  response dumped to %s (len=%d)",
                               dump_path, len(last_content or ""))
            except Exception:
                pass
            if attempt < _MAX_ATTEMPTS:
                logger.warning("Search phase attempt %d failed (%s), retrying...", attempt, exc)
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
    # Last resort after all attempts: try fallback on the final content
    if last_content:
        fallback = _parse_corrections_from_text(last_content)
        if fallback:
            logger.info("  extracted %d corrections from final fallback", len(fallback))
            return fallback
    logger.warning("Search phase failed after %d attempts, skipping: %s",
                   _MAX_ATTEMPTS, last_error)
    return []


# ---------------------------------------------------------------------------
# Phase 2: Main polish
# ---------------------------------------------------------------------------

_POLISH_SYSTEM_PROMPT = (
    "You are a faithful Chinese transcript editor. The input is raw ASR output with almost "
    "no punctuation. You must be FAITHFUL to the original - do not rewrite, expand, or add "
    "information that the speaker did not say.\n\n"
    "Your tasks (in order of priority):\n\n"
    "1. **ADD PUNCTUATION (most critical)**: Insert commas, periods, question marks, "
    "exclamation marks, enumeration commas, colons, semicolons based on semantic meaning. "
    "Break long runs into proper sentences. Use commas to separate clauses.\n"
    "2. **Apply ASR corrections**: If a correction list is provided, apply ONLY those specific "
    "character fixes (these are ASR misrecognition fixes, not expansions).\n"
    "3. **Remove spoken fillers**: Delete filler words (na ge, jiu shi shuo, ran hou ne, "
    "dui ba, en in Chinese) without changing meaning.\n"
    "4. **Book title marks**: Add \u300a\u300b for scripture/classic names.\n\n"
    "STRICTLY FORBIDDEN:\n"
    "- Do NOT add parenthetical notes, annotations, or explanations\n"
    "- Do NOT expand abbreviations or add full names\n"
    "- Do NOT rephrase or restructure sentences\n"
    "- Do NOT add any content the speaker did not say\n"
    "- Do NOT change the speaker's word choices\n\n"
    "Return ONLY JSON."
)


def polish_segments_with_llm(
    segments: List[Segment],
    *,
    enabled: bool,
    model: str,
    base_url: str,
    timeout_seconds: int,
    api_key_env: str,
    chunk_chars: int,
    search_model: str = "",
    search_base_url: str = "",
    search_api_key_env: str = "",
) -> List[Segment]:
    """
    Two-phase LLM polish:
    1. Search phase: use a web-search model to find proper noun corrections
    2. Polish phase: use the main model to add punctuation and apply corrections
    """
    if not enabled:
        return segments
    if not segments:
        return segments

    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        logger.warning("LLM polish enabled but env var %s not found, skipping.", api_key_env)
        return segments

    # -- Phase 1: search corrections --
    corrections: List[Dict[str, str]] = []
    if search_model:
        # Resolve search-specific API config (fall back to main config)
        search_url = search_base_url or base_url
        search_key_env = search_api_key_env or api_key_env
        search_key = api_key
        if search_api_key_env:
            search_key = os.getenv(search_api_key_env, "").strip()
            if not search_key:
                logger.warning("Search API key env var %s not found, falling back to %s",
                               search_api_key_env, api_key_env)
                search_key = api_key
        # Build a sample from all segments for the search model
        all_text = "".join(seg[2] for seg in segments)
        sample = all_text[:4000]

        # Check cache for search corrections (avoid wasting tokens)
        import hashlib as _hashlib
        cache_key = _hashlib.md5(sample.encode("utf-8")).hexdigest()
        cache_dir = os.path.join(os.path.dirname(__file__) or ".", ".cache")
        cache_path = os.path.join(cache_dir, cache_key + "_corrections.json")
        corrections_loaded = False
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as fh:
                    corrections = json.load(fh)
                if isinstance(corrections, list):
                    corrections_loaded = True
                    logger.info("Phase 1: loaded %d corrections from cache", len(corrections))
            except Exception:
                corrections = []

        if not corrections_loaded:
            logger.info("Phase 1: searching corrections with %s @ %s...", search_model, search_url)
            corrections = _search_corrections(
                sample,
                base_url=search_url,
                search_model=search_model,
                api_key=search_key,
                timeout_seconds=min(120, timeout_seconds),
            )
            # Save to cache
            try:
                os.makedirs(cache_dir, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as fh:
                    json.dump(corrections, fh, ensure_ascii=False)
            except Exception:
                pass

        if corrections:
            logger.info("Found %d corrections: %s", len(corrections),
                        ", ".join(c["wrong"] + " -> " + c["correct"] for c in corrections))
        else:
            logger.info("No corrections found from search.")

    # -- Phase 2: polish with main model --
    effective_chunk_chars = max(500, int(chunk_chars))
    result = list(segments)
    chunks = _chunk_segments(segments, effective_chunk_chars)
    total = len(chunks)
    logger.info("Phase 2: polishing %d chunks with %s (concurrent)...", total, model)

    corrections_text = ""
    if corrections:
        corrections_text = json.dumps(corrections, ensure_ascii=False)

    def _process_chunk(chunk_idx: int, chunk: List[Tuple[int, Segment]]) -> None:
        chunk_chars = sum(len(seg[2]) for _, seg in chunk)
        seg_indices = [idx for idx, _ in chunk]
        logger.info("  chunk %d/%d: %d segments (%d chars), indices %s",
                    chunk_idx + 1, total, len(chunk), chunk_chars, seg_indices)
        payload_items = [{"index": idx, "text": text} for idx, (_, _, text) in chunk]
        payload = {
            "task": "polish_transcript",
            "rules": [
                "Add full punctuation to the raw text",
                "Remove spoken filler words",
                "Add book title marks for scriptures/classics",
                "Keep original order, do not expand or summarize",
                "Keep verse/chant style for short lines",
                "Output: {\"segments\": [{\"index\": N, \"text\": \"...\"}]}",
            ],
            "segments": payload_items,
        }
        if corrections_text:
            payload["corrections_to_apply"] = corrections
        user_content = json.dumps(payload, ensure_ascii=False)

        chunk_indices = {idx for idx, _ in chunk}
        updated: Dict[int, str] = {}
        last_error: Optional[Exception] = None
        last_content: Optional[str] = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                content = _call_llm(
                    base_url=base_url,
                    model=model,
                    api_key=api_key,
                    timeout_seconds=max(10, int(timeout_seconds)),
                    system_prompt=_POLISH_SYSTEM_PROMPT,
                    user_content=user_content,
                )
                last_content = content
                response_json = _extract_json_block(content)
            except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS:
                    logger.warning("  chunk %d/%d attempt %d failed (%s), retrying...",
                                   chunk_idx + 1, total, attempt, exc)
                    time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
                continue

            if isinstance(response_json, list):
                polished_items = response_json
            elif isinstance(response_json, dict):
                polished_items = response_json.get("segments", [])
            else:
                polished_items = []
            if not isinstance(polished_items, list):
                polished_items = []

            updated = {}
            for item in polished_items:
                if not isinstance(item, dict):
                    continue
                idx = item.get("index")
                text = item.get("text")
                if not isinstance(idx, int) or idx not in chunk_indices:
                    continue
                if not isinstance(text, str):
                    continue
                cleaned = text.strip()
                if cleaned:
                    updated[idx] = cleaned

            missing = chunk_indices - updated.keys()
            if not missing:
                # Verify safety: reject attempts where the model dropped/added content
                unsafe = [
                    idx for idx, cleaned in updated.items()
                    if not _is_safe_polish(result[idx][2], cleaned)
                ]
                if not unsafe:
                    break
                last_error = ValueError("safety check rejected segments: %s" % unsafe)
                if attempt < _MAX_ATTEMPTS:
                    logger.warning(
                        "  chunk %d/%d attempt %d safety-rejected segs %s, retrying...",
                        chunk_idx + 1, total, attempt, unsafe)
                    time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
                continue
            last_error = ValueError("missing indices in response: %s" % sorted(missing))
            if attempt < _MAX_ATTEMPTS:
                logger.warning("  chunk %d/%d attempt %d incomplete (missing %s), retrying...",
                               chunk_idx + 1, total, attempt, sorted(missing))
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)

        if not updated or (chunk_indices - updated.keys()):
            logger.warning("LLM chunk %d/%d failed after %d attempts, keeping original: %s",
                           chunk_idx + 1, total, _MAX_ATTEMPTS, last_error)
            if last_content:
                dump_path = ".cache/llm_failed_chunk_%d.txt" % (chunk_idx + 1)
                try:
                    with open(dump_path, "w", encoding="utf-8") as fh:
                        fh.write(last_content)
                    logger.warning("  response length: %d chars, dumped to %s",
                                   len(last_content), dump_path)
                except OSError:
                    pass
            if not updated:
                return

        for idx, cleaned in updated.items():
            start, end, original_text = result[idx]
            if _is_safe_polish(original_text, cleaned):
                result[idx] = (start, end, cleaned)
            else:
                sim = SequenceMatcher(None, original_text, cleaned).ratio()
                logger.warning("  safety check rejected seg %d (sim=%.2f, src=%d, dst=%d chars)",
                               idx, sim, len(original_text), len(cleaned))

    max_workers = min(4, total)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_process_chunk, i, chunk)
            for i, chunk in enumerate(chunks)
        ]
        for future in as_completed(futures):
            future.result()

    logger.info("LLM polish done.")
    return result
