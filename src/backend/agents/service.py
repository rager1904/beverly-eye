from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from src.backend.agents.agent_base import AgentContext
from src.backend.agents.orchestrator import AgentOrchestrator, OrchestratorConfig
from src.backend.agents.triage.agent import TriageAgent
from src.backend.agents.clinical_documentation.agent import ClinicalDocumentationAgent
from src.backend.agents.medical_research.agent import MedicalResearchAgent
from src.backend.agents.appointment_agent.agent import AppointmentAgent
from src.backend.agents.patient_support.agent import PatientSupportAgent
from src.backend.agents.admin_agent.agent import AdminAgent
from src.backend.agents.public_health_agent.agent import PublicHealthAgent

logger = logging.getLogger(__name__)

orchestrator: Optional[AgentOrchestrator] = None

app = FastAPI(title="UbuntuCare Agent Orchestrator")
router = APIRouter(prefix="/api/v1/agents")


@app.on_event("startup")
async def startup():
    global orchestrator
    config = OrchestratorConfig()
    orchestrator = AgentOrchestrator(config)

    orchestrator.register_agent("triage", TriageAgent(), capabilities=["triage"])
    orchestrator.register_agent("clinical_documentation", ClinicalDocumentationAgent(), capabilities=["clinical_documentation"])
    orchestrator.register_agent("medical_research", MedicalResearchAgent(), capabilities=["medical_research"])
    orchestrator.register_agent("appointment", AppointmentAgent(), capabilities=["appointment"])
    orchestrator.register_agent("patient_support", PatientSupportAgent(), capabilities=["patient_support", "general"])
    orchestrator.register_agent("admin", AdminAgent(), capabilities=["admin"])
    orchestrator.register_agent("public_health", PublicHealthAgent(), capabilities=["public_health"])

    logger.info("Agent orchestrator initialized with %d agents", len(orchestrator.registry.list_agents()))


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    language: str = "en"
    agent: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    agent_used: str
    confidence: float
    processing_time_ms: float


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-orchestrator"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    conv_id = request.conversation_id or str(uuid.uuid4())
    metadata = dict(request.metadata)
    metadata.setdefault("user_input", request.message)
    context = AgentContext(
        conversation_id=conv_id,
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        language=request.language,
        metadata=metadata,
    )
    context.add_message("user", request.message)
    result = await orchestrator.process(request.message, context, agent_override=request.agent)
    if not result.content:
        logger.warning("Empty response for conversation %s, agent_override=%s", conv_id, request.agent)
        result.content = "I'm having trouble processing your request right now. Please try again or contact support."
    return ChatResponse(
        response=result.content,
        conversation_id=conv_id,
        agent_used=result.model_used,
        confidence=result.confidence,
        processing_time_ms=result.processing_time_ms,
    )

app.include_router(router)
