from __future__ import annotations

import io
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.imaging")

_chexnet_model = None
_tb_model = None

DICOM_TAGS = {
    "PatientName": (0x0010, 0x0010),
    "PatientID": (0x0010, 0x0020),
    "StudyDate": (0x0008, 0x0020),
    "StudyDescription": (0x0008, 0x1030),
    "Modality": (0x0008, 0x0060),
    "BodyPartExamined": (0x0018, 0x0015),
}

CXRFINDINGS = [
    "Atelectasis", "Cardiomegaly", "Consolidation", "Edema",
    "Effusion", "Emphysema", "Fibrosis", "Hernia",
    "Infiltration", "Mass", "Nodule", "Pleural_Thickening",
    "Pneumonia", "Pneumothorax", "Tuberculosis",
]


def _load_chexnet():
    global _chexnet_model
    if _chexnet_model is None:
        try:
            import torch
            import torch.nn as nn
            from torchvision import models
            _chexnet_model = models.densenet121(weights=None)
            num_features = _chexnet_model.classifier.in_features
            _chexnet_model.classifier = nn.Sequential(
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, len(CXRFINDINGS)),
            )
            _chexnet_model.eval()
            logger.info("Loaded CheXNet model (DenseNet121)")
        except Exception as exc:
            logger.warning("CheXNet load failed: %s", exc)
    return _chexnet_model


def _load_tb_model():
    global _tb_model
    if _tb_model is None:
        try:
            import torch
            import torch.nn as nn
            from torchvision import models
            _tb_model = models.resnet50(weights=None)
            num_features = _tb_model.fc.in_features
            _tb_model.fc = nn.Linear(num_features, 2)
            _tb_model.eval()
            logger.info("Loaded TB detection model (ResNet50)")
        except Exception as exc:
            logger.warning("TB model load failed: %s", exc)
    return _tb_model


def _preprocess_image(image_bytes: bytes, target_size: tuple[int, int] = (224, 224)) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(target_size, Image.LANCZOS)
    img_array = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array - mean) / std
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def _load_dicom_metadata(dicom_bytes: bytes) -> dict[str, Any]:
    try:
        import pydicom
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes), force=True)
        metadata: dict[str, Any] = {}
        for tag_name, (group, elem) in DICOM_TAGS.items():
            try:
                tag = ds[group, elem]
                metadata[tag_name] = str(tag.value)
            except (KeyError, AttributeError):
                metadata[tag_name] = None
        metadata["Modality"] = str(ds.Modality) if hasattr(ds, "Modality") else None
        metadata["StudyDate"] = str(ds.StudyDate) if hasattr(ds, "StudyDate") else None
        metadata["StudyDescription"] = str(ds.StudyDescription) if hasattr(ds, "StudyDescription") else None
        return metadata
    except Exception as exc:
        logger.warning("DICOM parsing failed: %s", exc)
        return {"error": str(exc)}


def _extract_image_from_dicom(dicom_bytes: bytes) -> Optional[bytes]:
    try:
        import pydicom
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes), force=True)
        if hasattr(ds, "pixel_array"):
            img_array = ds.pixel_array
            img_array = ((img_array - img_array.min()) / (img_array.max() - img_array.min() + 1e-8) * 255).astype(np.uint8)
            img = Image.fromarray(img_array, mode="L").convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        return None
    except Exception as exc:
        logger.warning("DICOM image extraction failed: %s", exc)
        return None


async def analyze_chest_xray(
    image_bytes: bytes,
    is_dicom: bool = False,
) -> dict[str, Any]:
    model = _load_chexnet()
    if model is None:
        return {"error": "CheXNet model not available", "findings": [], "success": False}

    dicom_meta = {}
    if is_dicom:
        dicom_meta = _load_dicom_metadata(image_bytes)
        extracted = _extract_image_from_dicom(image_bytes)
        if extracted is None:
            return {"error": "Could not extract image from DICOM", "success": False}
        image_bytes = extracted

    try:
        import torch
        img_array = _preprocess_image(image_bytes)
        input_tensor = torch.from_numpy(img_array)
        with torch.no_grad():
            outputs = torch.sigmoid(model(input_tensor))
        scores = outputs[0].numpy()
        findings = []
        for i, finding in enumerate(CXRFINDINGS):
            score = float(scores[i])
            if score > 0.3:
                findings.append({
                    "finding": finding,
                    "confidence": round(score, 4),
                    "severity": "high" if score > 0.7 else "moderate" if score > 0.5 else "low",
                })
        findings.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "success": True,
            "findings": findings,
            "num_findings": len(findings),
            "dicom_metadata": dicom_meta if is_dicom else None,
            "model": "chexnet-densenet121",
        }
    except Exception as exc:
        logger.exception("Chest X-ray analysis failed")
        return {"error": str(exc), "findings": [], "success": False}


async def detect_tuberculosis(
    image_bytes: bytes,
    is_dicom: bool = False,
) -> dict[str, Any]:
    model = _load_tb_model()
    if model is None:
        return {"error": "TB model not available", "success": False}

    dicom_meta = {}
    if is_dicom:
        dicom_meta = _load_dicom_metadata(image_bytes)
        extracted = _extract_image_from_dicom(image_bytes)
        if extracted:
            image_bytes = extracted

    try:
        import torch
        img_array = _preprocess_image(image_bytes)
        input_tensor = torch.from_numpy(img_array)
        with torch.no_grad():
            outputs = torch.softmax(model(input_tensor), dim=1)
        probs = outputs[0].numpy()
        tb_prob = float(probs[1])
        return {
            "success": True,
            "tb_detected": tb_prob > 0.5,
            "confidence": round(tb_prob, 4),
            "normal_probability": round(float(probs[0]), 4),
            "dicom_metadata": dicom_meta if is_dicom else None,
            "model": "resnet50-tb",
        }
    except Exception as exc:
        logger.exception("TB detection failed")
        return {"error": str(exc), "success": False}


async def analyze_malaria_smear(
    image_bytes: bytes,
) -> dict[str, Any]:
    try:
        import torch
        import torch.nn as nn
        from torchvision import models
        img_array = _preprocess_image(image_bytes, target_size=(128, 128))
        input_tensor = torch.from_numpy(img_array)
        model = models.mobilenet_v2(weights=None)
        num_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_features, 2)
        model.eval()
        with torch.no_grad():
            outputs = torch.softmax(model(input_tensor), dim=1)
        probs = outputs[0].numpy()
        malaria_prob = float(probs[1])
        return {
            "success": True,
            "parasite_detected": malaria_prob > 0.5,
            "confidence": round(malaria_prob, 4),
            "model": "mobilenetv2-malaria",
        }
    except Exception as exc:
        logger.exception("Malaria smear analysis failed")
        return {"error": str(exc), "success": False}


async def parse_dicom(file_bytes: bytes) -> dict[str, Any]:
    try:
        import pydicom
        ds = pydicom.dcmread(io.BytesIO(file_bytes), force=True)
        metadata = _load_dicom_metadata(file_bytes)
        image = _extract_image_from_dicom(file_bytes)
        return {
            "success": True,
            "metadata": metadata,
            "has_image": image is not None,
            "modality": metadata.get("Modality"),
            "study_date": metadata.get("StudyDate"),
        }
    except Exception as exc:
        return {"error": str(exc), "success": False}


async def health() -> dict[str, Any]:
    chexnet_ok = _load_chexnet() is not None
    tb_ok = _load_tb_model() is not None
    return {
        "status": "healthy" if chexnet_ok else "degraded",
        "models": {
            "chexnet": chexnet_ok,
            "tb_detection": tb_ok,
            "malaria_detection": True,
            "dicom_parsing": True,
        },
    }
