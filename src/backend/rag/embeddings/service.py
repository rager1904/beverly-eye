from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from src.backend.core.cache.redis_client import redis_client
from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.rag.embeddings")

EMBEDDING_DIM = 1024
CACHE_TTL = 86400 * 7
BATCH_SIZE = 32

_MODELS: dict[str, SentenceTransformer] = {}
_FALLBACK_CHAIN = (
    "BAAI/bge-m3",
    "jinaai/jina-embeddings-v4",
    "nomic-ai/nomic-embed-text-v1",
)


def _model_key(name: str) -> str:
    return f"emb_model:{name}"


def _cache_key(texts: tuple[str, ...], model: str) -> str:
    raw = f"{model}:{':'.join(texts)}"
    return f"emb:{hashlib.sha256(raw.encode()).hexdigest()}"


def _load_model(model_name: str) -> SentenceTransformer:
    key = _model_key(model_name)
    if key not in _MODELS:
        logger.info("Loading embedding model: %s", model_name)
        _MODELS[key] = SentenceTransformer(
            model_name,
            device=settings.WHISPER_DEVICE,
            trust_remote_code=True,
        )
    return _MODELS[key]


def _unload_model(model_name: str) -> None:
    key = _model_key(model_name)
    if key in _MODELS:
        model = _MODELS.pop(key)
        model.cpu()
        import gc
        del model
        gc.collect()
        logger.info("Unloaded model: %s", model_name)


def _normalize_text(text: str, healthcare: bool = True) -> str:
    text = " ".join(text.split())
    if healthcare:
        prefixes = [
            "Medical query: ",
            "Clinical document: ",
            "Patient record: ",
            "Medical literature: ",
            "Treatment guideline: ",
        ]
        found = False
        for p in prefixes:
            if text.startswith(p):
                found = True
                break
        if not found:
            text = f"Clinical document: {text}"
    return text


async def embed_texts(
    texts: list[str],
    model_name: Optional[str] = None,
    healthcare_optimize: bool = True,
) -> list[list[float]]:
    if not texts:
        return []

    model_name = model_name or _FALLBACK_CHAIN[0]
    texts = [_normalize_text(t, healthcare=healthcare_optimize) for t in texts]

    cache_key = _cache_key(tuple(texts), model_name)
    cached = await redis_client.get(cache_key)
    if cached is not None:
        return cached

    results: list[list[float]] = []
    last_error: Optional[Exception] = None

    for candidate in (model_name, *_FALLBACK_CHAIN):
        try:
            model = _load_model(candidate)
            embeddings = model.encode(
                texts,
                batch_size=BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            results = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
            break
        except Exception as exc:
            logger.warning("Embedding fallback %s failed: %s", candidate, exc)
            last_error = exc
            continue

    if not results and last_error:
        raise RuntimeError("All embedding models failed") from last_error

    await redis_client.set(cache_key, results, ttl=CACHE_TTL)
    return results


async def embed_query(
    query: str,
    model_name: Optional[str] = None,
    healthcare_optimize: bool = True,
) -> list[float]:
    emb = await embed_texts([query], model_name=model_name, healthcare_optimize=healthcare_optimize)
    return emb[0]


async def embed_batch(
    texts: list[str],
    batch_size: int = BATCH_SIZE,
    model_name: Optional[str] = None,
) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        chunk_emb = await embed_texts(chunk, model_name=model_name)
        all_embeddings.extend(chunk_emb)
    return all_embeddings


def compute_similarity(
    emb1: list[float] | NDArray,
    emb2: list[float] | NDArray,
) -> float:
    a = np.array(emb1, dtype=np.float32)
    b = np.array(emb2, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


async def preload_model() -> None:
    _load_model(_FALLBACK_CHAIN[0])

async def health() -> dict[str, Any]:
    statuses: dict[str, str] = {}
    primary = _FALLBACK_CHAIN[0]
    try:
        model = _load_model(primary)
        statuses[primary] = "healthy" if model else "unhealthy"
    except Exception as exc:
        statuses[primary] = f"unhealthy: {exc}"
    return {"models": statuses}
