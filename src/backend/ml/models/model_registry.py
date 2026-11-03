from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.registry")


class ModelType(str, Enum):
    LLM = "llm"
    EMBEDDING = "embedding"
    ASR = "asr"
    TTS = "tts"
    VAD = "vad"
    DIARIZATION = "diarization"
    GUARDRAILS = "guardrails"
    MEDICAL_IMAGING = "medical_imaging"
    CLINICAL = "clinical"
    REASONING = "reasoning"


class ModelStatus(str, Enum):
    LOADED = "loaded"
    UNLOADED = "unloaded"
    LOADING = "loading"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class ModelMetadata:
    name: str
    model_type: ModelType
    version: str = "1.0.0"
    status: ModelStatus = ModelStatus.UNLOADED
    gpu_required: bool = False
    gpu_memory_gb: float = 0.0
    ram_gb: float = 0.0
    fallback_chain: list[str] = field(default_factory=list)
    endpoint: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    last_loaded: Optional[datetime] = None
    load_count: int = 0
    error_count: int = 0
    avg_inference_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model_type": self.model_type.value,
            "version": self.version,
            "status": self.status.value,
            "gpu_required": self.gpu_required,
            "gpu_memory_gb": self.gpu_memory_gb,
            "ram_gb": self.ram_gb,
            "fallback_chain": self.fallback_chain,
            "endpoint": self.endpoint,
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "load_count": self.load_count,
            "error_count": self.error_count,
            "avg_inference_ms": self.avg_inference_ms,
        }


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelMetadata] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            ModelMetadata(
                name="BAAI/bge-m3",
                model_type=ModelType.EMBEDDING,
                gpu_required=False,
                ram_gb=2.0,
                fallback_chain=["jinaai/jina-embeddings-v4", "nomic-ai/nomic-embed-text-v1"],
            ),
            ModelMetadata(
                name="faster-whisper-large-v3",
                model_type=ModelType.ASR,
                gpu_required=False,
                gpu_memory_gb=6.0,
                ram_gb=4.0,
                fallback_chain=["faster-whisper-medium", "faster-whisper-small"],
            ),
            ModelMetadata(
                name="xtts-v2",
                model_type=ModelType.TTS,
                gpu_required=False,
                gpu_memory_gb=4.0,
                ram_gb=4.0,
                fallback_chain=["piper-tts"],
            ),
            ModelMetadata(
                name="silero-vad",
                model_type=ModelType.VAD,
                gpu_required=False,
                ram_gb=0.5,
            ),
            ModelMetadata(
                name="pyannote-speaker-diarization-3.1",
                model_type=ModelType.DIARIZATION,
                gpu_required=False,
                gpu_memory_gb=2.0,
                ram_gb=2.0,
            ),
            ModelMetadata(
                name="epfl-llm/meditron-7b",
                model_type=ModelType.CLINICAL,
                gpu_required=True,
                gpu_memory_gb=16.0,
                ram_gb=8.0,
                endpoint=settings.LLM_ENDPOINT,
                fallback_chain=["aaditya/OpenBioLLM-8B", "mistralai/Mistral-7B-Instruct-v0.3"],
            ),
            ModelMetadata(
                name="aaditya/OpenBioLLM-8B",
                model_type=ModelType.CLINICAL,
                gpu_required=True,
                gpu_memory_gb=16.0,
                ram_gb=8.0,
                endpoint=settings.LLM_ENDPOINT,
            ),
            ModelMetadata(
                name="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
                model_type=ModelType.REASONING,
                gpu_required=True,
                gpu_memory_gb=16.0,
                ram_gb=8.0,
                endpoint=settings.LLM_ENDPOINT,
            ),
            ModelMetadata(
                name="Qwen/Qwen3-32B",
                model_type=ModelType.REASONING,
                gpu_required=True,
                gpu_memory_gb=64.0,
                ram_gb=32.0,
                endpoint=settings.LLM_ENDPOINT,
                fallback_chain=["Qwen/Qwen3-8B"],
            ),
            ModelMetadata(
                name="meta-llama/LlamaGuard-7b",
                model_type=ModelType.GUARDRAILS,
                gpu_required=True,
                gpu_memory_gb=14.0,
                ram_gb=8.0,
            ),
        ]
        for model in defaults:
            self._models[model.name] = model

    def register(self, metadata: ModelMetadata) -> None:
        self._models[metadata.name] = metadata
        logger.info("Registered model: %s (%s)", metadata.name, metadata.model_type.value)

    def unregister(self, name: str) -> None:
        self._models.pop(name, None)
        logger.info("Unregistered model: %s", name)

    def get(self, name: str) -> Optional[ModelMetadata]:
        return self._models.get(name)

    def get_by_type(self, model_type: ModelType) -> list[ModelMetadata]:
        return [m for m in self._models.values() if m.model_type == model_type]

    def set_status(self, name: str, status: ModelStatus) -> None:
        model = self._models.get(name)
        if model:
            model.status = status
            if status == ModelStatus.LOADED:
                model.last_loaded = datetime.now(timezone.utc)
                model.load_count += 1
            elif status == ModelStatus.ERROR:
                model.error_count += 1

    def record_inference(self, name: str, duration_ms: float) -> None:
        model = self._models.get(name)
        if model:
            alpha = 0.1
            model.avg_inference_ms = (1 - alpha) * model.avg_inference_ms + alpha * duration_ms

    def get_all(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._models.values()]

    def get_health_summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        status_summary: dict[str, int] = {}
        for model in self._models.values():
            by_type[model.model_type.value] = by_type.get(model.model_type.value, 0) + 1
            status_summary[model.status.value] = status_summary.get(model.status.value, 0) + 1
        return {
            "total_models": len(self._models),
            "by_type": by_type,
            "by_status": status_summary,
            "loaded_count": sum(1 for m in self._models.values() if m.status == ModelStatus.LOADED),
        }

    def get_fallback_chain(self, model_name: str) -> list[str]:
        model = self._models.get(model_name)
        if model and model.fallback_chain:
            return [model_name] + model.fallback_chain
        return [model_name]


model_registry = ModelRegistry()
