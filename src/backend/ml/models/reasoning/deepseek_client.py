from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.reasoning.deepseek")

DEEPSEEK_SYSTEM_PROMPT = """You are DeepSeek-R1, a reasoning model. Think step-by-step before answering. Show your reasoning process clearly. For medical queries, be thorough and precise."""


class DeepSeekClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.LLM_ENDPOINT
        self.model_name = model_name or "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"

    async def _post(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 8192),
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.endpoint}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    def _extract_reasoning(self, content: str) -> tuple[str, str]:
        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", content, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        answer = re.sub(r"<reasoning>.*?</reasoning>", "", content, flags=re.DOTALL).strip()
        return reasoning, answer

    async def reason(
        self,
        prompt: str,
        extract_reasoning_chain: bool = True,
    ) -> dict[str, Any]:
        response = await self._post([
            {"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        reasoning = ""
        answer = content
        if extract_reasoning_chain:
            reasoning, answer = self._extract_reasoning(content)
        return {
            "reasoning": reasoning,
            "answer": answer,
            "full_content": content,
            "raw_response": response,
        }

    async def clinical_analysis(
        self,
        case_data: str,
        analysis_type: str = "diagnostic",
    ) -> dict[str, Any]:
        prompt = f"""Perform a detailed {analysis_type} analysis of the following clinical case.

Case Data:
{case_data}

Think step-by-step:
1. Identify key clinical findings
2. Consider possible diagnoses
3. Evaluate diagnostic options
4. Formulate management plan
5. Identify gaps in information

Use <reasoning> tags for your reasoning process."""
        return await self.reason(prompt)

    async def generate_code(
        self,
        task: str,
        language: str = "python",
    ) -> dict[str, Any]:
        prompt = f"""Generate {language} code for the following task:

{task}

Provide clean, well-structured code with comments. Include error handling."""
        response = await self._post([
            {"role": "system", "content": "You are a code generation assistant. Write production-quality code."},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"code": content, "language": language, "raw_response": response}

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.endpoint}/health")
                return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}


deepseek = DeepSeekClient()
