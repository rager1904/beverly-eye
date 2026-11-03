from __future__ import annotations

import base64
import io
import logging
import struct
import tempfile
import wave
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import soundfile as sf
from fastapi import APIRouter, FastAPI, Form, HTTPException, Query
from fastapi.responses import Response

try:
    from src.backend.core.config.settings import settings
    from src.backend.ml.speech.tts.voices import (
        VoiceProfile,
        get_voice,
        load_speaker_embedding,
        modulate_pitch,
        modulate_speed,
    )
except ImportError:
    from core.config.settings import settings
    from ml.speech.tts.voices import (
        VoiceProfile,
        get_voice,
        load_speaker_embedding,
        modulate_pitch,
        modulate_speed,
    )

logger = logging.getLogger("ubuntucare.ml.speech.tts")

_edge_tts_available = False
_gtts_available = False


def _check_edge_tts():
    global _edge_tts_available
    if not _edge_tts_available:
        try:
            import edge_tts
            _edge_tts_available = True
            logger.info("edge-tts available")
        except ImportError:
            logger.warning("edge-tts not installed")
    return _edge_tts_available


def _check_gtts():
    global _gtts_available
    if not _gtts_available:
        try:
            import gtts
            _gtts_available = True
            logger.info("gTTS available")
        except ImportError:
            logger.warning("gTTS not installed")
    return _gtts_available


def _generate_simple_wav(text: str, sample_rate: int = 22050) -> bytes:
    """Generate a simple audible WAV as last-resort fallback."""
    import hashlib
    seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    duration = max(1.0, len(text) * 0.08)
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        freq = 220 + (seed % 200)
        val = int(16000 * 0.5 * __import__("math").sin(2 * 3.14159 * freq * t))
        val = max(-32768, min(32767, val))
        samples.append(val)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


async def _generate_edge_tts(text: str, voice_name: str = "en-US-JennyNeural") -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=voice_name)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    audio = buf.getvalue()
    if not audio:
        raise RuntimeError("edge-tts produced no audio")
    return audio


def _generate_gtts(text: str, lang: str = "en") -> bytes:
    from gtts import gTTS
    import tempfile as tf
    tts = gTTS(text=text, lang=lang[:2], slow=False)
    with tf.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tts.save(tmp.name)
        tmp_path = tmp.name
    with open(tmp_path, "rb") as f:
        audio = f.read()
    Path(tmp_path).unlink(missing_ok=True)
    return audio


EDGE_TTS_VOICE_MAP = {
    "en_female_1": "en-US-JennyNeural",
    "en_male_1": "en-US-GuyNeural",
    "bem_female_1": "en-ZA-LindaNeural",
    "ny_female_1": "en-ZA-LindaNeural",
    "tog_female_1": "en-ZA-LindaNeural",
    "loz_female_1": "en-ZA-LindaNeural",
    "en_female_care_1": "en-US-JennyNeural",
}


async def synthesize(
    text: str,
    voice_name: str = "en_female_1",
    language: Optional[str] = None,
    use_piper: bool = False,
) -> dict[str, Any]:
    voice = get_voice(voice_name)
    lang = language or voice.language
    audio_bytes = None
    errors = []

    # Try providers in order: edge-tts → gTTS → simple WAV
    if not use_piper and _check_edge_tts():
        try:
            edge_voice = EDGE_TTS_VOICE_MAP.get(voice_name, "en-US-JennyNeural")
            audio_bytes = await _generate_edge_tts(text, edge_voice)
        except Exception as exc:
            errors.append(f"edge-tts: {exc}")
            logger.warning("edge-tts failed: %s", exc)

    if audio_bytes is None and _check_gtts():
        try:
            audio_bytes = _generate_gtts(text, lang)
        except Exception as exc:
            errors.append(f"gTTS: {exc}")
            logger.warning("gTTS failed: %s", exc)

    if audio_bytes is None:
        logger.warning("All TTS backends failed (%s), using tone fallback", "; ".join(errors))
        audio_bytes = _generate_simple_wav(text)

    audio_bytes = modulate_pitch(audio_bytes, voice.pitch_shift)
    audio_bytes = modulate_speed(audio_bytes, voice.speed)
    data, sample_rate = sf.read(io.BytesIO(audio_bytes))
    duration = len(data) / sample_rate
    return {
        "audio": base64.b64encode(audio_bytes).decode(),
        "duration_seconds": round(duration, 2),
        "sample_rate": sample_rate,
        "voice": voice_name,
        "language": lang,
        "format": "wav",
    }


async def synthesize_stream(
    text: str,
    voice_name: str = "en_female_1",
    language: Optional[str] = None,
    chunk_size: int = 4096,
) -> AsyncIterator[bytes]:
    result = await synthesize(text, voice_name, language)
    audio_bytes = bytes.fromhex(result["audio"])
    for i in range(0, len(audio_bytes), chunk_size):
        yield audio_bytes[i : i + chunk_size]


async def synthesize_with_ssml(
    ssml: str,
    voice_name: str = "en_female_1",
) -> dict[str, Any]:
    import re
    text = re.sub(r"<[^>]+>", "", ssml)
    return await synthesize(text, voice_name)


async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "edge_tts": _check_edge_tts(),
        "gtts": _check_gtts(),
        "voices": list(EDGE_TTS_VOICE_MAP.keys()),
    }


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="UbuntuCare TTS Service", version="1.0.0")
router = APIRouter(prefix="/api/v1/tts")


@app.get("/health")
async def health_endpoint():
    return await health()


@router.post("/synthesize")
async def synthesize_endpoint(
    text: str = Form(...),
    voice_name: str = Form("en_female_1"),
    language: Optional[str] = Form(None),
):
    try:
        result = await synthesize(text, voice_name=voice_name, language=language)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

app.include_router(router)
