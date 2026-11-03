from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    VLLM = "vllm"
    OLLAMA = "ollama"
    TGI = "tgi"
    LLAMA_CPP = "llama_cpp"
    OPENAI_COMPATIBLE = "openai_compatible"


class FallbackStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    PARALLEL_VOTE = "parallel_vote"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    endpoint: str
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.95
    timeout: int = 120
    context_length: int = 8192
    stop_sequences: List[str] = field(default_factory=list)

    @property
    def is_medical_model(self) -> bool:
        medical_keywords = ["meditron", "openbiollm", "biomedlm", "clinical"]
        return any(kw in self.model_name.lower() for kw in medical_keywords)

    @property
    def is_reasoning_model(self) -> bool:
        reasoning_keywords = ["deepseek-r1", "deepseek-r1", "qwq", "reason"]
        return any(kw in self.model_name.lower() for kw in reasoning_keywords)


FALLBACK_CHAIN: List[ModelConfig] = [
    ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="qwen2.5:1.5b",
        endpoint="http://host.docker.internal:11434",
        temperature=0.1,
        max_tokens=1024,
        context_length=4096,
        timeout=120,
    ),
    ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="qwen2.5:1.5b",
        endpoint="http://host.docker.internal:11434",
        temperature=0.3,
        max_tokens=1024,
        context_length=4096,
        timeout=180,
    ),
]


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    content: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model_used: str = ""
    tools_used: List[str] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    requires_followup: bool = False
    followup_question: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    citations: List[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    fallback_chain: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class AgentContext(BaseModel):
    conversation_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    language: str = "en"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Dict[str, str]] = Field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_context_window(self, max_messages: int = 20) -> List[Dict[str, str]]:
        return self.messages[-max_messages:]


class ToolDef(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    sensitive: bool = False

    class Config:
        arbitrary_types_allowed = True


class LLMClient:
    def __init__(self, config: ModelConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                follow_redirects=True,
            )
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload: Dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "stop": self.config.stop_sequences or None,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        if self.config.provider == ModelProvider.OLLAMA:
            return await self._call_ollama(payload, client)
        return await self._call_openai_compatible(payload, headers, client)

    async def _call_openai_compatible(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        url = f"{self.config.endpoint.rstrip('/')}/chat/completions"
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        choice = result["choices"][0]
        return {
            "content": choice["message"].get("content", ""),
            "tool_calls": choice["message"].get("tool_calls", []),
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": result.get("usage", {}),
            "model": result.get("model", self.config.model_name),
        }

    async def _call_ollama(
        self,
        payload: Dict[str, Any],
        client: httpx.AsyncClient,
    ) -> Dict[str, Any]:
        url = f"{self.config.endpoint.rstrip('/')}/api/chat"
        ollama_payload = {
            "model": payload["model"],
            "messages": payload["messages"],
            "stream": False,
            "options": {
                "temperature": payload.get("temperature", 0.1),
                "num_predict": payload.get("max_tokens", 4096),
                "top_p": payload.get("top_p", 0.95),
            },
        }
        if "tools" in payload:
            ollama_payload["tools"] = payload["tools"]

        response = await client.post(url, json=ollama_payload)
        response.raise_for_status()
        result = response.json()
        return {
            "content": result["message"].get("content", ""),
            "tool_calls": result["message"].get("tool_calls", []),
            "finish_reason": "stop",
            "usage": {},
            "model": result.get("model", self.config.model_name),
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


class BaseAgent(ABC):
    def __init__(
        self,
        agent_name: str,
        model_configs: Optional[List[ModelConfig]] = None,
        fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL,
    ):
        self.agent_name = agent_name
        self._model_configs = model_configs or FALLBACK_CHAIN
        self._fallback_strategy = fallback_strategy
        self._clients: Dict[str, LLMClient] = {}
        self._tools: Dict[str, ToolDef] = {}
        self._prompt_templates: Dict[str, str] = {}
        self._current_model_index: int = 0

    def register_tool(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for tool in self._tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters or {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
            schemas.append(schema)
        return schemas

    def register_prompt(self, name: str, template: str) -> None:
        self._prompt_templates[name] = template

    def render_prompt(self, name: str, **kwargs: Any) -> str:
        template = self._prompt_templates.get(name)
        if not template:
            raise ValueError(f"Prompt template '{name}' not found")
        return template.format(**kwargs)

    def _get_client(self, config: ModelConfig) -> LLMClient:
        key = f"{config.provider}:{config.model_name}"
        if key not in self._clients:
            self._clients[key] = LLMClient(config)
        return self._clients[key]

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        use_fallbacks: bool = True,
    ) -> AgentResponse:
        start_time = time.monotonic()
        fallback_chain_used: List[str] = []
        last_error: Optional[str] = None

        model_indices = (
            [self._current_model_index]
            if not use_fallbacks
            else range(len(self._model_configs))
        )

        for idx in model_indices:
            if idx >= len(self._model_configs):
                break
            config = self._model_configs[idx]
            self._current_model_index = idx

            try:
                client = self._get_client(config)
                result = await client.generate(messages, tools, response_format)
                content = result.get("content", "")
                model_name = result.get("model", config.model_name)
                fallback_chain_used.append(model_name)

                confidence = await self._compute_confidence(
                    content, config, result.get("usage", {})
                )

                tool_results = await self._process_tool_calls(
                    result.get("tool_calls", [])
                )

                processing_time = (time.monotonic() - start_time) * 1000
                return AgentResponse(
                    content=content,
                    confidence=confidence,
                    model_used=model_name,
                    tools_used=[tr.tool_name for tr in tool_results],
                    tool_results=tool_results,
                    processing_time_ms=processing_time,
                    fallback_chain=fallback_chain_used,
                )
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                fallback_chain_used.append(
                    f"{config.model_name} (FAILED: {last_error})"
                )
                logger.warning(
                    "Model %s failed for agent %s: %s",
                    config.model_name,
                    self.agent_name,
                    last_error,
                )
            except httpx.TimeoutException:
                last_error = "timeout"
                fallback_chain_used.append(f"{config.model_name} (FAILED: timeout)")
                logger.warning("Model %s timed out for agent %s", config.model_name, self.agent_name)
            except Exception as e:
                last_error = str(e)[:200]
                fallback_chain_used.append(
                    f"{config.model_name} (FAILED: {last_error})"
                )
                logger.exception(
                    "Model %s failed for agent %s: %s",
                    config.model_name,
                    self.agent_name,
                    last_error,
                )

        processing_time = (time.monotonic() - start_time) * 1000
        return AgentResponse(
            content="",
            confidence=0.0,
            model_used=fallback_chain_used[-1] if fallback_chain_used else "none",
            processing_time_ms=processing_time,
            fallback_chain=fallback_chain_used,
            error=last_error or "All models in fallback chain failed",
        )

    async def _process_tool_calls(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        results: List[ToolResult] = []
        for tc in tool_calls:
            function_data = tc.get("function", tc)
            tool_name = function_data.get("name", "unknown")
            try:
                arguments = json.loads(function_data.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                arguments = {}

            tool_def = self._tools.get(tool_name)
            if not tool_def or not tool_def.handler:
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Tool '{tool_name}' not registered",
                    )
                )
                continue

            try:
                start = time.monotonic()
                result_data = await tool_def.handler(**arguments)
                elapsed = (time.monotonic() - start) * 1000
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=True,
                        data=result_data,
                        execution_time_ms=elapsed,
                    )
                )
            except Exception as e:
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=str(e),
                    )
                )
        return results

    async def _compute_confidence(
        self,
        content: str,
        config: ModelConfig,
        usage: Dict[str, Any],
    ) -> float:
        if not content or not content.strip():
            return 0.0

        base_confidence = 0.8 if config.is_medical_model else 0.7

        medical_terms = [
            "diagnosis", "treatment", "symptom", "prescribe", "dosage",
            "contraindication", "prognosis", "therapeutic", "clinical",
        ]
        term_count = sum(1 for t in medical_terms if t.lower() in content.lower())
        medical_relevance = min(term_count / len(medical_terms), 1.0)

        length_bonus = min(len(content.split()) / 200, 0.1)

        uncertainty_indicators = [
            "i'm not sure", "i don't know", "uncertain", "maybe",
            "perhaps", "could be", "might be", "not clear",
        ]
        has_uncertainty = any(
            phrase in content.lower() for phrase in uncertainty_indicators
        )
        uncertainty_penalty = 0.15 if has_uncertainty else 0.0

        if config.is_reasoning_model:
            reasoning_bonus = 0.05
        else:
            reasoning_bonus = 0.0

        confidence = (
            base_confidence
            + (medical_relevance * 0.15)
            + length_bonus
            + reasoning_bonus
            - uncertainty_penalty
        )
        return max(0.0, min(1.0, confidence))

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResponse:
        ...

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
