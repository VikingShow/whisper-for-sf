from __future__ import annotations

import hashlib
import os
import tempfile
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from config import Config
from transcribe import TranscriptionPipeline, setup_logging
from utils import load_from_cache, save_to_cache


def _cache_path_for_key(key: str, model_size: str) -> str:
    file_hash = hashlib.md5(f"{key}_{model_size}".encode("utf-8")).hexdigest()
    return os.path.join(".cache", f"api_{file_hash}.pkl")


def _segments_to_text(segments: List[Tuple[float, float, str]]) -> str:
    return "\n".join(text for _, _, text in segments if text).strip()


class Segment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    text: str
    segments: List[Segment]
    model: str
    language: Optional[str] = None
    language_probability: Optional[float] = None
    duration: Optional[float] = None
    cached: bool = False
    elapsed_ms: int = 0


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[TranscriptionResult] = None


@dataclass
class _Job:
    id: str
    created_at: float
    status: Literal["queued", "running", "succeeded", "failed"]
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    future: Optional[Future[TranscriptionResult]] = None
    result: Optional[TranscriptionResult] = None


app = FastAPI(title="SoundChase API", version="0.1.0")

_executor = ThreadPoolExecutor(max_workers=int(os.getenv("VOXTRACE_WORKERS", "1")))
_jobs: Dict[str, _Job] = {}
_jobs_lock = Lock()


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


def _build_config(
    audio_file: str,
    model: str,
    device: str,
    compute_type: str,
    language: Optional[str],
    beam_size: int,
    vad_filter: bool,
    enable_diarization: bool,
    diarization_model: str,
) -> Config:
    config = Config()
    config.audio_file = audio_file
    config.model_size = model
    config.device = device
    config.compute_type = compute_type
    config.language = language or config.language
    config.beam_size = beam_size
    config.vad_filter = vad_filter
    config.enable_diarization = enable_diarization
    config.diarization_model = diarization_model
    config.use_cache = False
    config.output_format = "txt"
    return config


def _transcribe_file(
    audio_path: str,
    file_sha256: str,
    model: str,
    device: str,
    compute_type: str,
    language: Optional[str],
    beam_size: int,
    vad_filter: bool,
    enable_diarization: bool,
    diarization_model: str,
    use_cache: bool,
) -> TranscriptionResult:
    started = time.time()
    cache_path = _cache_path_for_key(
        key=f"{file_sha256}:{language}:{beam_size}:{vad_filter}:{enable_diarization}:{diarization_model}:{compute_type}:{device}",
        model_size=model,
    )

    if use_cache:
        cached = load_from_cache(cache_path)
        if isinstance(cached, dict):
            cached["cached"] = True
            cached["elapsed_ms"] = int((time.time() - started) * 1000)
            return TranscriptionResult(**cached)

    config = _build_config(
        audio_file=audio_path,
        model=model,
        device=device,
        compute_type=compute_type,
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter,
        enable_diarization=enable_diarization,
        diarization_model=diarization_model,
    )

    with TranscriptionPipeline(config) as pipeline:
        segments, info = pipeline.transcribe()

    result_dict: Dict[str, Any] = {
        "text": _segments_to_text(segments),
        "segments": [{"start": s, "end": e, "text": t} for s, e, t in segments],
        "model": model,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "cached": False,
        "elapsed_ms": int((time.time() - started) * 1000),
    }

    if use_cache:
        save_to_cache(cache_path, result_dict)

    return TranscriptionResult(**result_dict)


async def _save_upload_to_temp(upload: UploadFile) -> Tuple[str, str]:
    suffix = os.path.splitext(upload.filename or "")[1] or ".bin"
    sha256 = hashlib.sha256()

    fd, path = tempfile.mkstemp(prefix="soundchase_", suffix=suffix)
    os.close(fd)

    try:
        with open(path, "wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                sha256.update(chunk)
                f.write(chunk)
        return path, sha256.hexdigest()
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise


@app.post("/v1/transcribe", response_model=TranscriptionResult)
async def transcribe(
    file: UploadFile = File(...),
    model: str = Query("large-v3"),
    device: Literal["cuda", "cpu"] = Query("cuda"),
    compute_type: Literal["float16", "int8", "int8_float16", "float32"] = Query("float16"),
    language: Optional[str] = Query("zh"),
    beam_size: int = Query(5, ge=1, le=20),
    vad_filter: bool = Query(True),
    enable_diarization: bool = Query(False),
    diarization_model: str = Query("pyannote/speaker-diarization"),
    use_cache: bool = Query(True),
) -> TranscriptionResult:
    setup_logging(os.getenv("VOXTRACE_LOG_LEVEL", "INFO"))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    audio_path, file_sha256 = await _save_upload_to_temp(file)
    try:
        return _transcribe_file(
            audio_path=audio_path,
            file_sha256=file_sha256,
            model=model,
            device=device,
            compute_type=compute_type,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            enable_diarization=enable_diarization,
            diarization_model=diarization_model,
            use_cache=use_cache,
        )
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


@app.post("/v1/jobs", response_model=JobStatus)
async def create_job(
    file: UploadFile = File(...),
    model: str = Query("large-v3"),
    device: Literal["cuda", "cpu"] = Query("cuda"),
    compute_type: Literal["float16", "int8", "int8_float16", "float32"] = Query("float16"),
    language: Optional[str] = Query("zh"),
    beam_size: int = Query(5, ge=1, le=20),
    vad_filter: bool = Query(True),
    enable_diarization: bool = Query(False),
    diarization_model: str = Query("pyannote/speaker-diarization"),
    use_cache: bool = Query(True),
) -> JobStatus:
    setup_logging(os.getenv("VOXTRACE_LOG_LEVEL", "INFO"))

    audio_path, file_sha256 = await _save_upload_to_temp(file)

    job_id = uuid.uuid4().hex
    job = _Job(id=job_id, created_at=time.time(), status="queued")

    def _run() -> TranscriptionResult:
        try:
            return _transcribe_file(
                audio_path=audio_path,
                file_sha256=file_sha256,
                model=model,
                device=device,
                compute_type=compute_type,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                enable_diarization=enable_diarization,
                diarization_model=diarization_model,
                use_cache=use_cache,
            )
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

    with _jobs_lock:
        _jobs[job_id] = job
        job.future = _executor.submit(_run)

    return JobStatus(
        id=job_id,
        status=job.status,
        created_at=job.created_at,
    )


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.future and job.status in ("queued", "running"):
            if job.future.running() and job.status != "running":
                job.status = "running"
                job.started_at = job.started_at or time.time()
            if job.future.done():
                job.finished_at = time.time()
                try:
                    job.result = job.future.result()
                    job.status = "succeeded"
                except Exception as e:  # noqa: BLE001
                    job.status = "failed"
                    job.error = str(e)

        return JobStatus(
            id=job.id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
            result=job.result,
        )
