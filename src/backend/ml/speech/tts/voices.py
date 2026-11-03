from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ubuntucare.ml.tts.voices")

VOICE_CACHE_DIR = Path("data/voices")
VOICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VoiceProfile:
    name: str
    language: str
    gender: str = "female"
    speaker_embedding_path: Optional[str] = None
    pitch_shift: float = 0.0
    speed: float = 1.0
    emotion: str = "neutral"
    style: str = "default"
    fallback_language: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "speaker_embedding_path": self.speaker_embedding_path,
            "pitch_shift": self.pitch_shift,
            "speed": self.speed,
            "emotion": self.emotion,
            "style": self.style,
            "fallback_language": self.fallback_language,
        }


DEFAULT_VOICES: dict[str, VoiceProfile] = {
    "en_female_1": VoiceProfile(
        name="en_female_1",
        language="en",
        gender="female",
        style="clinical",
        metadata={"accent": "zambian", "role": "nurse"},
    ),
    "en_male_1": VoiceProfile(
        name="en_male_1",
        language="en",
        gender="male",
        style="clinical",
        metadata={"accent": "zambian", "role": "doctor"},
    ),
    "bem_female_1": VoiceProfile(
        name="bem_female_1",
        language="bem",
        gender="female",
        fallback_language="en",
        metadata={"region": "northern", "role": "community_health_worker"},
    ),
    "ny_female_1": VoiceProfile(
        name="ny_female_1",
        language="ny",
        gender="female",
        fallback_language="ny",
        metadata={"region": "lusaka", "role": "nurse"},
    ),
    "tog_female_1": VoiceProfile(
        name="tog_female_1",
        language="tog",
        gender="female",
        fallback_language="en",
        metadata={"region": "southern", "role": "community_health_worker"},
    ),
    "loz_female_1": VoiceProfile(
        name="loz_female_1",
        language="loz",
        gender="female",
        fallback_language="en",
        metadata={"region": "western", "role": "community_health_worker"},
    ),
    "en_female_care_1": VoiceProfile(
        name="en_female_care_1",
        language="en",
        gender="female",
        emotion="compassionate",
        style="patient_care",
        metadata={"accent": "zambian", "role": "patient_support"},
    ),
}


SPEAKER_EMBEDDING_CACHE: dict[str, list[float]] = {}


def get_voice(name: str) -> VoiceProfile:
    if name in DEFAULT_VOICES:
        return DEFAULT_VOICES[name]
    raise ValueError(f"Unknown voice profile: {name}")


def list_voices(language: Optional[str] = None) -> list[dict[str, Any]]:
    voices = DEFAULT_VOICES.values()
    if language:
        voices = [v for v in voices if v.language == language]
    return [v.to_dict() for v in voices]


def save_speaker_embedding(voice_name: str, embedding: list[float]) -> None:
    path = VOICE_CACHE_DIR / f"{voice_name}.emb.json"
    with open(path, "w") as f:
        json.dump({"voice": voice_name, "embedding": embedding}, f)
    SPEAKER_EMBEDDING_CACHE[voice_name] = embedding
    logger.info("Saved speaker embedding for '%s' (%d dims)", voice_name, len(embedding))


def load_speaker_embedding(voice_name: str) -> Optional[list[float]]:
    if voice_name in SPEAKER_EMBEDDING_CACHE:
        return SPEAKER_EMBEDDING_CACHE[voice_name]
    path = VOICE_CACHE_DIR / f"{voice_name}.emb.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            emb = data["embedding"]
            SPEAKER_EMBEDDING_CACHE[voice_name] = emb
            return emb
    return None


def remove_speaker_embedding(voice_name: str) -> None:
    SPEAKER_EMBEDDING_CACHE.pop(voice_name, None)
    path = VOICE_CACHE_DIR / f"{voice_name}.emb.json"
    path.unlink(missing_ok=True)


def modulate_pitch(audio: bytes, pitch_shift: float) -> bytes:
    if abs(pitch_shift) < 0.01:
        return audio
    try:
        import librosa
        import soundfile as sf
        import io
        import numpy as np
        data, sr = sf.read(io.BytesIO(audio))
        shifted = librosa.effects.pitch_shift(data, sr=sr, n_steps=pitch_shift)
        buf = io.BytesIO()
        sf.write(buf, shifted, sr, format="WAV")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Pitch modulation failed: %s", exc)
        return audio


def modulate_speed(audio: bytes, speed: float) -> bytes:
    if abs(speed - 1.0) < 0.01:
        return audio
    try:
        import librosa
        import soundfile as sf
        import io
        data, sr = sf.read(io.BytesIO(audio))
        sped = librosa.effects.time_stretch(data, rate=speed)
        buf = io.BytesIO()
        sf.write(buf, sped, sr, format="WAV")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Speed modulation failed: %s", exc)
        return audio
