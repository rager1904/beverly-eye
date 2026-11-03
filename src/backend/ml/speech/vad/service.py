from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import numpy as np
import soundfile as sf
import torch

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.speech.vad")

_vad_model = None


def _get_vad():
    global _vad_model
    if _vad_model is None:
        try:
            import silero_vad
            _vad_model = silero_vad.load_silero_vad()
            logger.info("Loaded Silero VAD model")
        except Exception as exc:
            logger.warning("Silero VAD failed to load: %s", exc)
            raise
    return _vad_model


def _load_audio(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    data, orig_sr = sf.read(io.BytesIO(audio_bytes))
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    if orig_sr != sample_rate:
        try:
            import librosa
            data = librosa.resample(data, orig_sr=orig_sr, target_sr=sample_rate)
        except ImportError:
            logger.warning("librosa not available, skipping resample")
    return data.astype(np.float32)


def _audio_to_tensor(audio: np.ndarray, sample_rate: int = 16000) -> torch.Tensor:
    if not isinstance(audio, torch.Tensor):
        audio = torch.from_numpy(audio)
    if audio.dim() == 1:
        audio = audio.unsqueeze(0)
    return audio.float()


async def detect_speech(
    audio_bytes: bytes,
    threshold: float = 0.5,
    sample_rate: int = 16000,
) -> dict[str, Any]:
    model = _get_vad()
    audio = _load_audio(audio_bytes, sample_rate)
    audio_tensor = _audio_to_tensor(audio, sample_rate)
    with torch.no_grad():
        speech_prob = model(audio_tensor, sample_rate).item()
    is_speech = speech_prob >= threshold
    return {
        "is_speech": is_speech,
        "probability": round(speech_prob, 4),
        "threshold": threshold,
        "duration_seconds": round(len(audio) / sample_rate, 2),
    }


async def get_speech_segments(
    audio_bytes: bytes,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 500,
    sample_rate: int = 16000,
) -> dict[str, Any]:
    model = _get_vad()
    audio = _load_audio(audio_bytes, sample_rate)
    audio_tensor = _audio_to_tensor(audio, sample_rate)
    with torch.no_grad():
        speech_segments = model.get_speech_segments(
            audio_tensor,
            sample_rate,
            threshold=threshold,
            min_speech_duration_ms=min_speech_duration_ms,
            min_silence_duration_ms=min_silence_duration_ms,
        )
    segments = []
    if speech_segments is not None and len(speech_segments) > 0:
        for seg in speech_segments:
            start = float(seg[0].item())
            end = float(seg[1].item())
            segments.append({"start": round(start, 3), "end": round(end, 3), "duration": round(end - start, 3)})
    total_speech = sum(s["duration"] for s in segments)
    return {
        "segments": segments,
        "total_speech_duration": round(total_speech, 3),
        "total_audio_duration": round(len(audio) / sample_rate, 3),
        "speech_ratio": round(total_speech / (len(audio) / sample_rate), 4) if len(audio) > 0 else 0.0,
    }


async def extract_speech_segments(
    audio_bytes: bytes,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 500,
    padding_ms: int = 100,
) -> list[bytes]:
    seg_info = await get_speech_segments(
        audio_bytes,
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
    )
    audio, orig_sr = sf.read(io.BytesIO(audio_bytes))
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    extracted: list[bytes] = []
    padding_samples = int(padding_ms * orig_sr / 1000)
    for seg in seg_info["segments"]:
        start_sample = max(0, int(seg["start"] * orig_sr) - padding_samples)
        end_sample = min(len(audio), int(seg["end"] * orig_sr) + padding_samples)
        segment_audio = audio[start_sample:end_sample]
        buf = io.BytesIO()
        sf.write(buf, segment_audio, orig_sr, format="WAV")
        extracted.append(buf.getvalue())
    return extracted


async def stream_vad(
    audio_chunks: AsyncIterator[bytes],
    threshold: float = 0.5,
) -> AsyncIterator[dict[str, Any]]:
    buffer = io.BytesIO()
    async for chunk in audio_chunks:
        buffer.write(chunk)
    audio_bytes = buffer.getvalue()
    result = await detect_speech(audio_bytes, threshold=threshold)
    yield result


async def filter_noise(
    audio_bytes: bytes,
    sample_rate: int = 16000,
    noise_reduction_strength: float = 0.5,
) -> bytes:
    try:
        import noisereduce as nr
        audio = _load_audio(audio_bytes, sample_rate)
        reduced = nr.reduce_noise(y=audio, sr=sample_rate, prop_decrease=noise_reduction_strength)
        buf = io.BytesIO()
        sf.write(buf, reduced, sample_rate, format="WAV")
        return buf.getvalue()
    except ImportError:
        logger.warning("noisereduce not installed, skipping noise filtering")
        return audio_bytes
    except Exception as exc:
        logger.warning("Noise filtering failed: %s", exc)
        return audio_bytes


async def health() -> dict[str, Any]:
    try:
        model = _get_vad()
        dummy = np.zeros(16000, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, dummy, 16000, format="WAV")
        result = await detect_speech(buf.getvalue())
        return {
            "status": "healthy",
            "threshold": settings.VAD_THRESHOLD,
            "min_speech_ms": settings.VAD_MIN_SPEECH_DURATION_MS,
            "min_silence_ms": settings.VAD_MIN_SILENCE_DURATION_MS,
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
