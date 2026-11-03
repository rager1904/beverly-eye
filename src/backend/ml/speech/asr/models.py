from __future__ import annotations

import gc
import logging
from enum import Enum
from typing import Any, Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from src.backend.core.config.settings import settings
except ImportError:
    from core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.asr.models")


class ModelPrecision(str, Enum):
    FP16 = "float16"
    INT8 = "int8"
    INT4 = "int4_float16"


_MODEL_REGISTRY: dict[str, dict[str, Any]] = {}
_ACTIVE_LOADED: dict[str, Any] = {}

_FALLBACK_CHAIN = ("large-v3", "medium", "small", "base", "tiny")


def _model_key(name: str, precision: str) -> str:
    return f"whisper:{name}:{precision}"


def get_device() -> str:
    if TORCH_AVAILABLE and torch.cuda.is_available():
        return "cuda"
    return settings.WHISPER_DEVICE or "cpu"


def get_compute_type(precision: ModelPrecision) -> str:
    mapping = {
        ModelPrecision.FP16: "float16",
        ModelPrecision.INT8: "int8",
        ModelPrecision.INT4: "int4_float16",
    }
    return mapping.get(precision, settings.WHISPER_COMPUTE_TYPE or "int8")


def load_model(
    model_size: str = "large-v3",
    precision: ModelPrecision = ModelPrecision.INT8,
    device: Optional[str] = None,
    model_path: Optional[str] = None,
) -> Any:
    from faster_whisper import WhisperModel

    size_or_path = model_path or model_size
    key = _model_key(size_or_path, precision.value)
    if key in _ACTIVE_LOADED:
        logger.info("Using cached model: %s", key)
        return _ACTIVE_LOADED[key]

    compute = get_compute_type(precision)
    dev = device or get_device()

    logger.info("Loading Whisper model: %s (compute=%s, device=%s)", size_or_path, compute, dev)
    model = WhisperModel(
        size_or_path,
        device=dev,
        compute_type=compute,
        download_root=None,
        cpu_threads=4,
        num_workers=2,
    )
    _ACTIVE_LOADED[key] = model
    _MODEL_REGISTRY[key] = {
        "model_size": size_or_path,
        "precision": precision.value,
        "device": dev,
        "compute_type": compute,
    }
    return model


def load_with_fallback(
    preferred_size: str = "large-v3",
    precision: ModelPrecision = ModelPrecision.INT8,
    model_path: Optional[str] = None,
) -> Any:
    if model_path:
        return load_model(preferred_size, precision, model_path=model_path)

    last_error: Optional[Exception] = None
    sizes = [preferred_size] + [s for s in _FALLBACK_CHAIN if s != preferred_size]
    for size in sizes:
        try:
            return load_model(size, precision)
        except (RuntimeError, MemoryError, ValueError) as exc:
            logger.warning("Failed to load %s (%s): %s", size, precision.value, exc)
            last_error = exc
            unload_model(size, precision.value)
            gc.collect()
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
            continue
    raise RuntimeError("All Whisper model sizes failed to load") from last_error


def unload_model(model_size: str, precision: str = "int8") -> None:
    key = _model_key(model_size, precision)
    if key in _ACTIVE_LOADED:
        model = _ACTIVE_LOADED.pop(key)
        try:
            del model
        except Exception:
            pass
    _MODEL_REGISTRY.pop(key, None)
    gc.collect()
    if TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Unloaded model: %s", key)


def unload_all() -> int:
    count = len(_ACTIVE_LOADED)
    for key in list(_ACTIVE_LOADED.keys()):
        unload_model(*key.split(":")[1:3])
    return count


def get_loaded_models() -> list[dict[str, Any]]:
    return [
        {
            "key": k,
            **v,
        }
        for k, v in _MODEL_REGISTRY.items()
    ]


def get_gpu_memory() -> dict[str, Any]:
    if not TORCH_AVAILABLE or not torch.cuda.is_available():
        return {"available": False}
    try:
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return {
            "available": True,
            "device": torch.cuda.get_device_name(0),
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "free_gb": round(total - allocated, 2),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def optimize_memory() -> bool:
    freed = 0
    try:
        for key in list(_ACTIVE_LOADED.keys()):
            if len(_ACTIVE_LOADED) > 1:
                unload_model(*key.split(":")[1:3])
                freed += 1
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True
    except Exception:
        return False
