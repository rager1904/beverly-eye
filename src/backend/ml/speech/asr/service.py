from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import numpy as np
import soundfile as sf
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

try:
    from src.backend.core.config.settings import settings
    from src.backend.ml.speech.asr.models import (
        ModelPrecision,
        load_model,
        load_with_fallback,
    )
except ImportError:
    from core.config.settings import settings
    from ml.speech.asr.models import (
        ModelPrecision,
        load_model,
        load_with_fallback,
    )

logger = logging.getLogger("ubuntucare.ml.speech.asr")

MEDICAL_VOCABULARY = [
    "malaria", "tuberculosis", "TB", "HIV", "AIDS", "ART", "antiretroviral",
    "artemether", "lumefantrine", "rifampicin", "isoniazid", "pyrazinamide",
    "ethambutol", "dolutegravir", "tenofovir", "lamivudine", "nevirapine",
    "oxytocin", "misoprostol", "magnesium sulfate", "artesunate",
    "amoxicillin", "zinc sulfate", "oral rehydration salts",
    "pneumonia", "diarrhea", "cholera", "typhoid", "dysentery",
    "hypertension", "diabetes", "epilepsy", "asthma", "anemia",
    "malnutrition", "stunting", "wasting", "kwashiorkor", "marasmus",
    "preeclampsia", "eclampsia", "postpartum hemorrhage", "sepsis",
    "meningitis", "encephalitis", "hepatitis", "cirrhosis",
    "schistosomiasis", "lymphatic filariasis", "onchocerciasis",
    "zambia", "lusaka", "copperbelt", "nhima", "smartcare",
    "nrc", "nupi", "bem", "bemba", "nyanja", "tonga", "lozi",
]

SUPPORTED_LANGUAGES = {"en": "english", "bem": "bemba", "ny": "nyanja", "tog": "tonga", "loz": "lozi"}
WHISPER_LANG_MAP = {"en": "en", "bem": "en", "ny": "ny", "tog": "en", "loz": "en"}

_whisper_model = None
_HOTWORDS = " ".join(MEDICAL_VOCABULARY)


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = load_with_fallback(
            preferred_size=settings.WHISPER_MODEL_SIZE,
            precision=ModelPrecision.INT8,
            model_path=settings.WHISPER_MODEL_PATH,
        )
    return _whisper_model


def preprocess_audio(audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
    try:
        import librosa
        audio_array, orig_sr = sf.read(io.BytesIO(audio_bytes))
        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)
        if orig_sr != sample_rate:
            audio_array = librosa.resample(audio_array, orig_sr=orig_sr, target_sr=sample_rate)
        audio_array = audio_array / (np.max(np.abs(audio_array)) + 1e-10)
        buf = io.BytesIO()
        sf.write(buf, audio_array, sample_rate, format="WAV")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Audio preprocessing failed, using raw: %s", exc)
        return audio_bytes


def _detect_language(audio_bytes: bytes) -> tuple[str, float]:
    model = _get_model()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, info = model.transcribe(tmp_path, beam_size=1, language=None)
        lang = info.language if info else "en"
        prob = info.language_probability if info else 0.0
        return lang, prob
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def transcribe(
    audio_bytes: bytes,
    language: Optional[str] = None,
    word_timestamps: bool = True,
    use_vad: bool = True,
) -> dict[str, Any]:
    audio_bytes = preprocess_audio(audio_bytes)
    model = _get_model()
    detected_lang = language
    if not detected_lang:
        detected_lang, lang_prob = _detect_language(audio_bytes)
        logger.info("Detected language: %s (%.2f)", detected_lang, lang_prob)
    whisper_lang = WHISPER_LANG_MAP.get(detected_lang, "en")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language=whisper_lang,
            vad_filter=use_vad,
            hotwords=_HOTWORDS,
            word_timestamps=word_timestamps,
        )
        result_segments = []
        full_text = []
        for segment in segments:
            words_list = []
            if segment.words:
                words_list = [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in segment.words
                ]
            result_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.no_speech_prob if hasattr(segment, "no_speech_prob") else 1.0,
                "words": words_list,
            })
            full_text.append(segment.text.strip())
        return {
            "text": " ".join(full_text),
            "language": detected_lang or info.language,
            "language_probability": info.language_probability if info else 0.0,
            "segments": result_segments,
            "duration": info.duration if info else 0.0,
            "word_count": sum(len(s.get("words", [])) for s in result_segments),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def transcribe_stream(
    audio_chunks: AsyncIterator[bytes],
    language: Optional[str] = None,
) -> AsyncIterator[dict[str, Any]]:
    buffer = io.BytesIO()
    chunk_count = 0
    async for chunk in audio_chunks:
        buffer.write(chunk)
        chunk_count += 1
    audio_bytes = preprocess_audio(buffer.getvalue())
    result = await transcribe(audio_bytes, language=language)
    for segment in result["segments"]:
        yield segment


async def transcribe_batch(
    audio_files: list[bytes],
    language: Optional[str] = None,
) -> list[dict[str, Any]]:
    results = []
    for audio in audio_files:
        result = await transcribe(audio, language=language)
        results.append(result)
    return results


async def streaming_transcribe(
    audio_bytes: bytes,
    previous_context: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, Any]:
    result = await transcribe(audio_bytes, language=language, word_timestamps=True)
    if previous_context:
        result["text"] = f"{previous_context} {result['text']}"
    return result


async def health() -> dict[str, Any]:
    try:
        _get_model()
        try:
            torch_avail = bool(__import__("torch").cuda.is_available())
        except (ImportError, AttributeError):
            torch_avail = False
        return {
            "status": "healthy",
            "model": settings.WHISPER_MODEL_SIZE,
            "language_support": list(SUPPORTED_LANGUAGES.keys()),
            "gpu": str(torch_avail),
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="UbuntuCare ASR Service", version="1.0.0")
router = APIRouter(prefix="/api/v1/asr")


@app.get("/health")
async def health_endpoint():
    return await health()


@router.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    word_timestamps: bool = Form(True),
):
    audio_bytes = await file.read()
    try:
        result = await transcribe(
            audio_bytes,
            language=language,
            word_timestamps=word_timestamps,
            use_vad=True,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transcribe-batch")
async def transcribe_batch_endpoint(
    files: list[UploadFile] = File(...),
    language: Optional[str] = Form(None),
):
    audio_files = [await f.read() for f in files]
    try:
        results = await transcribe_batch(audio_files, language=language)
        return {"results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

app.include_router(router)
