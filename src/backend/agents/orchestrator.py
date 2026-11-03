from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel, Field

from src.backend.agents.agent_base import (
    AgentContext,
    AgentResponse,
    BaseAgent,
    FallbackStrategy,
    ModelConfig,
)
from src.backend.agents.response_formatter import format_response

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_ESCALATION = "needs_escalation"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    CLINICAL_DOCUMENTATION = "clinical_documentation"
    TRIAGE = "triage"
    MEDICAL_RESEARCH = "medical_research"
    APPOINTMENT = "appointment"
    PATIENT_SUPPORT = "patient_support"
    ADMIN = "admin"
    PUBLIC_HEALTH = "public_health"
    GENERAL = "general"


@dataclass
class Task:
    id: str
    type: TaskType
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    agent_name: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output: Optional[AgentResponse] = None
    subtasks: List[Task] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3


class OrchestratorConfig(BaseModel):
    max_concurrent_tasks: int = 5
    enable_task_planning: bool = True
    enable_fallback: bool = True
    enable_memory: bool = True
    planning_model: Optional[ModelConfig] = None
    default_fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL
    task_timeout_seconds: int = 300
    max_subtask_depth: int = 3
    enable_audit_logging: bool = True


class MemoryEntry(BaseModel):
    agent_name: str
    context: str
    response_summary: str
    confidence: float
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capabilities: Dict[str, List[str]] = {}

    def register(self, name: str, agent: BaseAgent, capabilities: Optional[List[str]] = None) -> None:
        self._agents[name] = agent
        self._capabilities[name] = capabilities or []

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def find_by_capability(self, capability: str) -> List[str]:
        return [
            name
            for name, caps in self._capabilities.items()
            if capability in caps
        ]

    def find_best_agent(self, task_type: TaskType, input_data: Dict[str, Any]) -> Optional[str]:
        type_to_capability = {
            TaskType.CLINICAL_DOCUMENTATION: "clinical_documentation",
            TaskType.TRIAGE: "triage",
            TaskType.MEDICAL_RESEARCH: "medical_research",
            TaskType.APPOINTMENT: "appointment",
            TaskType.PATIENT_SUPPORT: "patient_support",
            TaskType.ADMIN: "admin",
            TaskType.PUBLIC_HEALTH: "public_health",
            TaskType.GENERAL: "general",
        }
        capability = type_to_capability.get(task_type)
        if not capability:
            return None
        candidates = self.find_by_capability(capability)
        return candidates[0] if candidates else None


class TaskPlanner:
    def __init__(self, registry: AgentRegistry):
        self._registry = registry

        self._task_signatures: Dict[TaskType, Dict[str, Any]] = {
            TaskType.TRIAGE: {
                "priority": 1,
                "keywords": {
                    "emergency": 1.0, "urgent": 0.9, "symptom": 0.4,
                    "symptoms": 0.5, "pain": 0.7, "fever": 0.7,
                    "injury": 0.8, "accident": 0.9, "bleeding": 0.9,
                    "chest pain": 0.95, "shortness of breath": 0.95,
                    "difficulty breathing": 0.95, "unconscious": 1.0,
                    "severe": 0.3, "burn": 0.7, "fracture": 0.7,
                    "poison": 0.8, "allergic reaction": 0.8,
                    "heart attack": 1.0, "stroke": 1.0, "seizure": 0.9,
                    "head injury": 0.9, "headache": 0.2,
                },
            },
            TaskType.MEDICAL_RESEARCH: {
                "priority": 2,
                "keywords": {
                    "research": 0.6, "study": 0.4, "evidence": 0.7,
                    "guideline": 0.8, "guidelines": 0.8, "drug": 0.7,
                    "drugs": 0.7, "interaction": 0.8, "medication": 0.7,
                    "medications": 0.7, "treatment": 0.6, "therapy": 0.5,
                    "pubmed": 0.9, "literature": 0.7, "dosage": 0.8,
                    "dose": 0.6, "prescribe": 0.7, "prescription": 0.7,
                    "contraindication": 0.8, "side effect": 0.7,
                    "clinical trial": 0.8, "medicine": 0.6,
                },
            },
            TaskType.APPOINTMENT: {
                "priority": 4,
                "keywords": {
                    "appointment": 0.8, "schedule": 0.5, "book": 0.3,
                    "reschedule": 0.8, "reminder": 0.4, "booking": 0.4,
                },
            },
            TaskType.CLINICAL_DOCUMENTATION: {
                "priority": 5,
                "keywords": {
                    "document": 0.6, "note": 0.5, "transcript": 0.7,
                    "summary": 0.4, "encounter": 0.6, "chart": 0.5,
                    "record": 0.4,
                },
            },
            TaskType.PATIENT_SUPPORT: {
                "priority": 6,
                "keywords": {
                    "question": 0.2, "education": 0.5, "prevention": 0.5,
                    "prevent": 0.4, "healthy": 0.3, "wellness": 0.4,
                    "nutrition": 0.5, "diet": 0.4, "exercise": 0.4,
                    "appointment reminder": 0.6,
                },
            },
            TaskType.ADMIN: {
                "priority": 7,
                "keywords": {
                    "analytics": 0.7, "report": 0.5, "staff": 0.5,
                    "resource": 0.4, "dashboard": 0.7, "statistics": 0.6,
                    "admin": 0.3, "administrative": 0.5,
                },
            },
            TaskType.PUBLIC_HEALTH: {
                "priority": 8,
                "keywords": {
                    "surveillance": 0.8, "outbreak": 0.9, "vaccination": 0.6,
                    "immunization": 0.6, "malaria": 0.3, "hiv": 0.3,
                    "tb": 0.3, "epidemic": 0.8, "pandemic": 0.8,
                    "disease outbreak": 0.8, "public health": 0.5,
                    "vaccine coverage": 0.7, "mosquito": 0.2,
                },
            },
        }

        self._treatment_phrases: List[Tuple[str, float]] = [
            ("what medication", 1.5), ("what drug", 1.5),
            ("what treatment", 1.5), ("how to treat", 1.5),
            ("treatment for", 1.2), ("medication for", 1.5),
            ("drug for", 1.2), ("therapy for", 1.0),
            ("prescribe for", 1.5), ("should i take", 1.2),
            ("should i give", 1.2), ("what to give", 1.5),
            ("what medicine", 1.5), ("medicine for", 1.2),
            ("cure for", 1.2), ("management of", 1.0),
            ("treatment of", 1.0), ("what is the dose", 1.5),
            ("what is the dosage", 1.5), ("how much to give", 1.5),
            ("what is the best", 0.8), ("recommended for", 0.8),
            ("first-line treatment", 1.5), ("first line treatment", 1.5),
            ("clinical guideline", 1.2), ("standard of care", 1.2),
            ("what do you recommend", 0.8), ("should i use", 0.8),
        ]

    async def plan(
        self,
        user_input: str,
        context: AgentContext,
        available_tasks: List[TaskType],
    ) -> List[Task]:
        tasks: List[Task] = []

        input_lower = user_input.lower()
        scores: Dict[TaskType, float] = {}

        for task_type, config in self._task_signatures.items():
            if task_type not in available_tasks:
                continue
            score = self._score_input(input_lower, config)
            if score > 0:
                scores[task_type] = score

        treatment_bonus = self._compute_treatment_bonus(input_lower)
        if treatment_bonus > 0 and TaskType.MEDICAL_RESEARCH in scores:
            scores[TaskType.MEDICAL_RESEARCH] += treatment_bonus

        if not scores:
            scores[TaskType.GENERAL] = 0.0

        selected = self._select_best(scores)

        task = Task(
            id=str(uuid.uuid4()),
            type=selected,
            description=self._generate_task_description(selected, user_input),
            input_data={"user_input": user_input, "original_context": context.model_dump()},
        )
        tasks.append(task)

        return tasks

    def _score_input(self, input_lower: str, config: Dict[str, Any]) -> float:
        score = 0.0
        for keyword, weight in config["keywords"].items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, input_lower):
                score += weight
        return score

    def _compute_treatment_bonus(self, input_lower: str) -> float:
        bonus = 0.0
        for phrase, weight in self._treatment_phrases:
            if phrase in input_lower:
                bonus = max(bonus, weight)
        return bonus

    def _select_best(self, scores: Dict[TaskType, float]) -> TaskType:
        if not scores:
            return TaskType.GENERAL

        if len(scores) == 1:
            return next(iter(scores))

        sorted_types = sorted(
            scores.items(),
            key=lambda item: (-item[1], self._task_signatures.get(item[0], {}).get("priority", 99)),
        )
        best_type, best_score = sorted_types[0]

        second_score = sorted_types[1][1] if len(sorted_types) > 1 else 0
        if best_score - second_score < 0.3:
            best_priority = self._task_signatures.get(best_type, {}).get("priority", 99)
            second_type = sorted_types[1][0]
            second_priority = self._task_signatures.get(second_type, {}).get("priority", 99)
            if second_priority < best_priority:
                return second_type

        return best_type

    def _generate_task_description(self, task_type: TaskType, user_input: str) -> str:
        descriptions = {
            TaskType.CLINICAL_DOCUMENTATION: f"Generate clinical documentation from: {user_input[:200]}",
            TaskType.TRIAGE: f"Perform triage assessment for: {user_input[:200]}",
            TaskType.MEDICAL_RESEARCH: f"Research medical information about: {user_input[:200]}",
            TaskType.APPOINTMENT: f"Handle appointment request: {user_input[:200]}",
            TaskType.PATIENT_SUPPORT: f"Provide patient support for: {user_input[:200]}",
            TaskType.ADMIN: f"Generate administrative report/analytics for: {user_input[:200]}",
            TaskType.PUBLIC_HEALTH: f"Analyze public health data for: {user_input[:200]}",
            TaskType.GENERAL: f"Process general query: {user_input[:200]}",
        }
        return descriptions.get(task_type, f"Process: {user_input[:200]}")

    def _set_dependencies(self, tasks: List[Task]) -> None:
        priority_order = [
            TaskType.TRIAGE,
            TaskType.CLINICAL_DOCUMENTATION,
            TaskType.MEDICAL_RESEARCH,
            TaskType.APPOINTMENT,
            TaskType.PATIENT_SUPPORT,
            TaskType.ADMIN,
            TaskType.PUBLIC_HEALTH,
        ]
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                priority_order.index(t.type)
                if t.type in priority_order
                else len(priority_order)
            ),
        )
        for i in range(1, len(sorted_tasks)):
            sorted_tasks[i].depends_on.append(sorted_tasks[i - 1].id)
        tasks[:] = sorted_tasks


class MemoryManager:
    def __init__(self, max_entries: int = 1000):
        self._entries: Dict[str, List[MemoryEntry]] = {}
        self._max_entries = max_entries

    def add(self, agent_name: str, entry: MemoryEntry) -> None:
        if agent_name not in self._entries:
            self._entries[agent_name] = []
        self._entries[agent_name].append(entry)
        if len(self._entries[agent_name]) > self._max_entries:
            self._entries[agent_name] = self._entries[agent_name][-self._max_entries:]

    def get_recent(
        self,
        agent_name: str,
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> List[MemoryEntry]:
        entries = self._entries.get(agent_name, [])
        filtered = [e for e in entries if e.confidence >= min_confidence]
        return filtered[-limit:]

    def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        query_lower = query.lower()
        results: List[tuple[float, MemoryEntry]] = []
        for entries in self._entries.values():
            for entry in entries:
                score = 0.0
                if query_lower in entry.context.lower():
                    score += 1.0
                if query_lower in entry.response_summary.lower():
                    score += 0.8
                if query_lower in str(entry.metadata).lower():
                    score += 0.3
                if score > 0:
                    results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]

    def clear(self, agent_name: Optional[str] = None) -> None:
        if agent_name:
            self._entries.pop(agent_name, None)
        else:
            self._entries.clear()


class AgentOrchestrator:
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
    ):
        self.config = config or OrchestratorConfig()
        self.registry = AgentRegistry()
        self.planner = TaskPlanner(self.registry)
        self.memory = MemoryManager()
        self._active_tasks: Dict[str, Task] = {}
        self._max_active_tasks = 500

    def register_agent(
        self,
        name: str,
        agent: BaseAgent,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        self.registry.register(name, agent, capabilities)
        logger.info("Registered agent '%s' with capabilities: %s", name, capabilities)

    async def process(
        self,
        user_input: str,
        context: Optional[AgentContext] = None,
        available_tasks: Optional[List[TaskType]] = None,
        agent_override: Optional[str] = None,
    ) -> AgentResponse:
        start_time = time.monotonic()
        if context is None:
            context = AgentContext(
                conversation_id=str(uuid.uuid4()),
            )

        available = available_tasks or list(TaskType)

        if agent_override and self.registry.get(agent_override):
            tasks = [Task(
                id=str(uuid.uuid4()),
                type=TaskType.GENERAL,
                description=f"Process with agent {agent_override}: {user_input[:200]}",
                input_data={"user_input": user_input},
            )]
        else:
            tasks = await self.planner.plan(user_input, context, available)
            if not tasks:
                return AgentResponse(
                    content="No tasks could be generated from your request.",
                    processing_time_ms=(time.monotonic() - start_time) * 1000,
                )

        self._prune_old_tasks()

        results: List[AgentResponse] = []
        task_map: Dict[str, Task] = {t.id: t for t in tasks}
        executed: Set[str] = set()

        while len(executed) < len(tasks):
            ready = [
                t for t in tasks
                if t.id not in executed
                and all(dep in executed for dep in t.depends_on)
            ]
            if not ready:
                break

            batch_results = await asyncio.gather(*[
                self._execute_task(t, context, agent_override if agent_override else None) for t in ready
            ], return_exceptions=True)

            for t, result in zip(ready, batch_results):
                if isinstance(result, Exception):
                    result = AgentResponse(
                        content=f"Task failed: {result}",
                        error=str(result),
                    )
                results.append(result)
                self._store_memory(t, result, context)
                executed.add(t.id)

        merged = self._merge_responses(results, user_input)
        merged.processing_time_ms = (time.monotonic() - start_time) * 1000
        return merged

    async def _execute_task(
        self, task: Task, context: AgentContext, agent_override: Optional[str] = None
    ) -> AgentResponse:
        task.status = TaskStatus.EXECUTING
        task.created_at = time.time()
        if len(self._active_tasks) >= self._max_active_tasks:
            self._prune_old_tasks()
        self._active_tasks[task.id] = task

        if agent_override and self.registry.get(agent_override):
            agent_name = agent_override
        else:
            agent_name = self.registry.find_best_agent(task.type, task.input_data)
        if not agent_name:
            task.status = TaskStatus.FAILED
            task.error = f"No agent available for task type: {task.type}"
            return AgentResponse(
                content=task.error,
                error=task.error,
            )

        task.agent_name = agent_name
        agent = self.registry.get(agent_name)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"Agent '{agent_name}' not found in registry"
            return AgentResponse(
                content=task.error,
                error=task.error,
            )

        try:
            response = await asyncio.wait_for(
                agent.run(context),
                timeout=self.config.task_timeout_seconds,
            )
            task.output = response
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.execution_time_ms = response.processing_time_ms
            return response
        except asyncio.TimeoutError:
            logger.error("Task %s timed out after %ds", task.id, self.config.task_timeout_seconds)
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {self.config.task_timeout_seconds}s"
            return AgentResponse(
                content=task.error,
                error=task.error,
            )
        except Exception as e:
            logger.exception("Task %s failed: %s", task.id, e)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info("Retrying task %s (attempt %d/%d)", task.id, task.retry_count, task.max_retries)
                return await self._execute_task(task, context, agent_override)
            return AgentResponse(
                content=f"Task failed after {task.retry_count} retries: {task.error}",
                error=task.error,
            )

    def _store_memory(self, task: Task, response: AgentResponse, context: AgentContext) -> None:
        if not self.config.enable_memory:
            return
        entry = MemoryEntry(
            agent_name=task.agent_name or task.type.value,
            context=task.description,
            response_summary=response.content[:500] if response.content else "",
            confidence=response.confidence,
            metadata={
                "task_id": task.id,
                "task_type": task.type.value,
                "model_used": response.model_used,
            },
        )
        self.memory.add(task.agent_name or task.type.value, entry)

    def _merge_responses(
        self, results: List[AgentResponse], original_input: str
    ) -> AgentResponse:
        if not results:
            return AgentResponse(
                content="No results were produced.",
                processing_time_ms=0.0,
            )

        if len(results) == 1:
            r = results[0]
            formatted = format_response(r.content, r.model_used)
            r.content = formatted.text
            r.structured_data = {
                "_formatted": {
                    "sections": [s.__dict__ for s in formatted.sections],
                    "style": formatted.style.value,
                    "agent_type": formatted.agent_type.value,
                    "html": formatted.html,
                }
            }
            r.fallback_chain = list(
                dict.fromkeys(
                    chain
                    for res in results
                    for chain in res.fallback_chain
                )
            )
            return r

        all_content = []
        all_tools: List[str] = []
        all_tool_results: List = []
        all_citations: List[str] = []
        fallback_chains: List[str] = []
        max_confidence = 0.0

        for i, r in enumerate(results):
            if r.content:
                all_content.append(f"[{i + 1}] {r.content}")
            all_tools.extend(r.tools_used)
            all_tool_results.extend(r.tool_results)
            all_citations.extend(r.citations)
            fallback_chains.extend(r.fallback_chain)
            max_confidence = max(max_confidence, r.confidence)

        raw_content = "\n\n".join(all_content)
        formatted = format_response(raw_content)
        merged = AgentResponse(
            content=formatted.text,
            structured_data={
                "_formatted": {
                    "sections": [s.__dict__ for s in formatted.sections],
                    "style": formatted.style.value,
                    "agent_type": formatted.agent_type.value,
                    "html": formatted.html,
                }
            },
            confidence=max_confidence,
            model_used=results[-1].model_used if results else "unknown",
            tools_used=list(set(all_tools)),
            tool_results=all_tool_results,
            citations=list(set(all_citations)),
            fallback_chain=list(dict.fromkeys(fallback_chains)),
            requires_followup=any(r.requires_followup for r in results),
        )
        return merged

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        return self._active_tasks.get(task_id)

    def _prune_old_tasks(self, max_age_seconds: float = 3600) -> None:
        now = time.time()
        stale = [
            tid for tid, t in self._active_tasks.items()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            and t.completed_at
            and (now - t.completed_at) > max_age_seconds
        ]
        for tid in stale:
            del self._active_tasks[tid]

    async def close(self) -> None:
        for agent_name in self.registry.list_agents():
            agent = self.registry.get(agent_name)
            if agent:
                await agent.close()

    @property
    def is_healthy(self) -> bool:
        return len(self.registry.list_agents()) > 0
