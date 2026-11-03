from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.clinical.openbiollm")

OPENBIOLLM_SYSTEM_PROMPT = """You are OpenBioLLM, a clinical AI assistant trained on biomedical literature and clinical guidelines. Provide evidence-based answers to clinical queries. Cite your sources when possible. Be concise, accurate, and clinically relevant."""


class OpenBioLLMClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.LLM_ENDPOINT
        self.model_name = model_name or "aaditya/OpenBioLLM-8B"

    async def _post(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.endpoint}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def clinical_qa(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        messages = [{"role": "system", "content": OPENBIOLLM_SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})
        else:
            messages.append({"role": "user", "content": question})
        response = await self._post(messages)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"answer": content, "raw_response": response}

    async def drug_info(
        self,
        drug_name: str,
        include_interactions: bool = True,
    ) -> dict[str, Any]:
        prompt = f"""Provide comprehensive drug information for: {drug_name}

Include:
- Generic and brand names
- Drug class and mechanism of action
- Indications and approved uses
- Dosage and administration
- Side effects and adverse reactions
- Contraindications and precautions
- Drug interactions{f' (focus on drugs commonly used in Zambia/Africa)' if include_interactions else ''}
- Special populations (pregnancy, pediatrics, elderly)
- Storage requirements"""
        response = await self._post([
            {"role": "system", "content": "You are a clinical pharmacology assistant."},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"drug_info": content, "drug": drug_name, "raw_response": response}

    async def treatment_guidelines(
        self,
        condition: str,
        setting: str = "primary_care",
    ) -> dict[str, Any]:
        prompt = f"""Provide evidence-based treatment guidelines for: {condition}

Setting: {setting}
Context: Zambia/Africa (low-resource setting)

Include:
- First-line treatment recommendations
- Second-line alternatives
- Duration of therapy
- Monitoring parameters
- When to refer
- Preventive measures"""
        response = await self._post([
            {"role": "system", "content": OPENBIOLLM_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"guidelines": content, "condition": condition, "raw_response": response}

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.endpoint}/health")
                return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}


openbiollm = OpenBioLLMClient()
