from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.clinical.meditron")

MEDITRON_SYSTEM_PROMPT = """You are Meditron, a clinical decision support AI developed for healthcare in low-resource settings. Provide accurate, evidence-based medical information. Always include relevant differential diagnoses, red flags, and when to refer. Use standard clinical terminology."""


class MeditronClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.LLM_ENDPOINT
        self.model_name = model_name or "epfl-llm/meditron-7b"

    async def _post(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "top_p": kwargs.get("top_p", 0.95),
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.endpoint}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def generate_soap_note(
        self,
        subjective: str,
        objective: str,
        assessment: Optional[str] = None,
        plan: Optional[str] = None,
        format: str = "structured",
    ) -> dict[str, Any]:
        prompt = f"""Generate a clinical SOAP note from the following information.

Subjective: {subjective}
Objective: {objective}
Assessment: {assessment or 'Not provided'}
Plan: {plan or 'Not provided'}

Generate a complete SOAP note with all four sections."""
        response = await self._post([
            {"role": "system", "content": MEDITRON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"note": content, "format": format, "raw_response": response}

    async def clinical_reasoning(
        self,
        case_presentation: str,
        include_differentials: bool = True,
    ) -> dict[str, Any]:
        prompt = f"""Perform clinical reasoning on the following case presentation:

{case_presentation}

Provide:
1. Problem representation
2. Differential diagnosis with rationale
3. Recommended diagnostic workup
4. Initial management plan
5. Red flags / when to refer"""
        response = await self._post([
            {"role": "system", "content": MEDITRON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"reasoning": content, "raw_response": response}

    async def icd10_code(
        self,
        diagnosis_text: str,
    ) -> dict[str, Any]:
        prompt = f"""Assign the most specific ICD-10 code(s) for the following clinical diagnosis. Provide the code, full description, and any applicable coding guidelines.

Diagnosis: {diagnosis_text}"""
        response = await self._post([
            {"role": "system", "content": "You are a clinical coding specialist. Provide accurate ICD-10 codes."},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"icd10_codes": content, "raw_response": response}

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.endpoint}/health")
                return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}


meditron = MeditronClient()
