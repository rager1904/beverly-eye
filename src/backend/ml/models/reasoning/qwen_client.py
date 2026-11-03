from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.ml.reasoning.qwen")

QWEN_SYSTEM_PROMPT = """You are Qwen3, a multilingual AI assistant. You can communicate in English, Bemba, Nyanja, Tonga, and Lozi. Provide accurate, helpful responses. For medical queries, be cautious and recommend consulting a healthcare professional."""


class QwenClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint or settings.LLM_ENDPOINT
        self.model_name = model_name or "Qwen/Qwen3-32B"

    async def _post(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 8192),
            "functions": kwargs.get("functions"),
            "function_call": kwargs.get("function_call"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.endpoint}/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def chat(
        self,
        message: str,
        language: str = "en",
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        sys_msg = system_prompt or QWEN_SYSTEM_PROMPT
        if language != "en":
            sys_msg += f"\nRespond in {language}."
        response = await self._post([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": message},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"response": content, "language": language, "raw_response": response}

    async def chat_multilingual(
        self,
        message: str,
        target_language: str = "bem",
    ) -> dict[str, Any]:
        lang_prompt = f"Please respond in {target_language}."
        response = await self._post([
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": f"{message}\n\n{lang_prompt}"},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"response": content, "language": target_language, "raw_response": response}

    async def function_call(
        self,
        message: str,
        functions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = await self._post(
            messages=[
                {"role": "system", "content": QWEN_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            functions=functions,
            function_call="auto",
        )
        msg = response.get("choices", [{}])[0].get("message", {})
        return {
            "content": msg.get("content", ""),
            "function_call": msg.get("function_call"),
            "raw_response": response,
        }

    async def agent_orchestrate(
        self,
        task: str,
        available_agents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        agents_desc = "\n".join(
            f"- {a['name']}: {a['description']}" for a in available_agents
        )
        prompt = f"""You are orchestrating healthcare agents. Available agents:

{agents_desc}

Task: {task}

Decide which agent(s) should handle this task and in what order."""
        response = await self._post([
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"plan": content, "raw_response": response}

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.endpoint}/health")
                return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}


qwen = QwenClient()
