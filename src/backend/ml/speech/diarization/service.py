from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np
import soundfile as sf
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.speech.diarization")

_diarization_pipeline = None
_embedding_model = None


def _get_pipeline():
    global _diarization_pipeline
    if _diarization_pipeline is None:
        try:
            from pyannote.audio import Pipeline
            _diarization_pipeline = Pipeline.from_pretrained(
                settings.DIARIZATION_MODEL,
                use_auth_token=None,
            )
            if settings.DIARIZATION_DEVICE == "cpu":
                _diarization_pipeline.to(torch.device("cpu"))
            logger.info("Loaded diarization pipeline")
        except Exception as exc:
            logger.warning("Pyannote pipeline failed: %s", exc)
            raise
    return _diarization_pipeline


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from pyannote.audio import Model
            from pyannote.audio.utils.signal import binarize
            _embedding_model = Model.from_pretrained(
                "pyannote/embedding",
                use_auth_token=None,
            )
            logger.info("Loaded speaker embedding model")
        except Exception as exc:
            logger.warning("Embedding model failed: %s", exc)
    return _embedding_model


def _ahc_clustering(embeddings: list[np.ndarray], threshold: float = 0.5) -> list[int]:
    if len(embeddings) == 0:
        return []
    if len(embeddings) == 1:
        return [0]
    emb_matrix = np.stack(embeddings)
    dist_matrix = pdist(emb_matrix, metric="cosine")
    Z = linkage(dist_matrix, method="average")
    labels = fcluster(Z, t=threshold, criterion="distance") - 1
    return labels.tolist()


def _spectral_clustering(embeddings: list[np.ndarray], n_clusters: Optional[int] = None) -> list[int]:
    from sklearn.cluster import SpectralClustering
    emb_matrix = np.stack(embeddings)
    if n_clusters is None:
        n_clusters = min(max(2, len(embeddings) // 3), 10) if len(embeddings) > 3 else 2
    n_clusters = min(n_clusters, len(embeddings))
    clustering = SpectralClustering(
        n_clusters=n_clusters,
        affinity="cosine",
        random_state=42,
    ).fit(emb_matrix)
    return clustering.labels_.tolist()


async def diarize(
    audio_bytes: bytes,
    num_speakers: Optional[int] = None,
    return_embeddings: bool = False,
) -> dict[str, Any]:
    pipeline = _get_pipeline()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        from pyannote.core import Annotation
        diarization = pipeline(tmp_path, num_speakers=num_speakers)
        speaker_turns = []
        speaker_set: set[str] = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_turns.append({
                "speaker": speaker,
                "start": round(turn.start, 3),
                "end": round(turn.end, 3),
                "duration": round(turn.end - turn.start, 3),
            })
            speaker_set.add(speaker)
        total_duration = sum(t["duration"] for t in speaker_turns)
        return {
            "num_speakers": len(speaker_set),
            "speakers": sorted(speaker_set),
            "segments": speaker_turns,
            "total_duration": round(total_duration, 3),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def diarize_with_embeddings(
    audio_bytes: bytes,
    num_speakers: Optional[int] = None,
    cluster_method: str = "ahc",
) -> dict[str, Any]:
    try:
        import torch
        audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        audio_tensor = torch.from_numpy(audio_data).float()
        pipeline = _get_pipeline()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            diarization = pipeline(tmp_path, num_speakers=num_speakers)
            speaker_turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                start_sample = int(turn.start * sample_rate)
                end_sample = int(turn.end * sample_rate)
                segment_audio = audio_tensor[start_sample:end_sample]
                speaker_turns.append({
                    "speaker": speaker,
                    "start": round(turn.start, 3),
                    "end": round(turn.end, 3),
                    "duration": round(turn.end - turn.start, 3),
                    "audio_segment": segment_audio.numpy().tolist(),
                })
            speaker_set = sorted(set(t["speaker"] for t in speaker_turns))
            return {
                "num_speakers": len(speaker_set),
                "speakers": speaker_set,
                "segments": speaker_turns,
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as exc:
        logger.error("Diarization with embeddings failed: %s", exc)
        return await diarize(audio_bytes, num_speakers=num_speakers)


async def diarize_real_time(
    audio_chunks: list[bytes],
    num_speakers: Optional[int] = None,
) -> list[dict[str, Any]]:
    results = []
    for chunk in audio_chunks:
        result = await diarize(chunk, num_speakers=num_speakers)
        results.append(result)
    return results


async def assign_speakers_to_transcript(
    transcript: dict[str, Any],
    diarization: dict[str, Any],
) -> dict[str, Any]:
    segments = transcript.get("segments", [])
    speaker_segments = diarization.get("segments", [])
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        seg_mid = (seg_start + seg_end) / 2
        assigned_speaker = "UNKNOWN"
        for spk_seg in speaker_segments:
            if spk_seg["start"] <= seg_mid <= spk_seg["end"]:
                assigned_speaker = spk_seg["speaker"]
                break
        seg["speaker"] = assigned_speaker
    transcript["diarized_segments"] = segments
    transcript["num_speakers"] = diarization.get("num_speakers", 0)
    return transcript


async def health() -> dict[str, Any]:
    try:
        pipeline = _get_pipeline()
        return {
            "status": "healthy",
            "model": settings.DIARIZATION_MODEL,
            "device": settings.DIARIZATION_DEVICE,
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
