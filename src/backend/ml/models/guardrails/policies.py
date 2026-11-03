from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MedicalContentCategory(str, Enum):
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    MEDICATION = "medication"
    SURGERY = "surgery"
    PREVENTION = "prevention"
    SCREENING = "screening"
    REHABILITATION = "rehabilitation"
    PALLIATIVE = "palliative"
    MATERNAL = "maternal_health"
    CHILD = "child_health"
    MENTAL = "mental_health"
    NUTRITION = "nutrition"
    IMMUNIZATION = "immunization"
    INFECTIOUS_DISEASE = "infectious_disease"
    NCD = "non_communicable_disease"
    EMERGENCY = "emergency_medicine"
    PUBLIC_HEALTH = "public_health"
    GENERAL = "general"


class HarmfulContentCategory(str, Enum):
    VIOLENCE = "violence"
    SEXUAL = "sexual"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    SELF_HARM = "self_harm"
    ILLEGAL_DRUGS = "illegal_drugs"
    MEDICAL_MISINFORMATION = "medical_misinformation"
    DANGEROUS_MEDICAL_ADVICE = "dangerous_medical_advice"
    MALPRACTICE = "malpractice"
    UNETHICAL = "unethical"
    DISCRIMINATION = "discrimination"


class AgentType(str, Enum):
    TRIAGE = "triage"
    CLINICAL_DOCUMENTATION = "clinical_documentation"
    PATIENT_SUPPORT = "patient_support"
    MEDICAL_RESEARCH = "medical_research"
    PUBLIC_HEALTH = "public_health"
    APPOINTMENT = "appointment"
    ADMIN = "admin"


@dataclass
class GuardrailPolicy:
    agent_type: AgentType
    allowed_categories: list[MedicalContentCategory] = field(default_factory=lambda: list(MedicalContentCategory))
    blocked_categories: list[HarmfulContentCategory] = field(default_factory=list)
    phi_detection_enabled: bool = True
    phi_redaction_strategy: str = "mask"
    prompt_injection_detection: bool = True
    hallucination_detection: bool = False
    content_safety_filter: bool = True
    topic_control_enabled: bool = True
    jailbreak_detection: bool = True
    max_input_length: int = 8000
    max_output_length: int = 4000
    require_citations: bool = False
    require_medical_disclaimer: bool = False
    allowed_languages: list[str] = field(default_factory=lambda: ["en", "bem", "ny", "tog", "loz"])
    blocked_topics: list[str] = field(default_factory=list)
    custom_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_POLICIES: dict[AgentType, GuardrailPolicy] = {
    AgentType.TRIAGE: GuardrailPolicy(
        agent_type=AgentType.TRIAGE,
        allowed_categories=[
            MedicalContentCategory.DIAGNOSIS,
            MedicalContentCategory.TREATMENT,
            MedicalContentCategory.EMERGENCY,
            MedicalContentCategory.INFECTIOUS_DISEASE,
            MedicalContentCategory.MATERNAL,
            MedicalContentCategory.CHILD,
        ],
        phi_detection_enabled=True,
        require_citations=True,
        require_medical_disclaimer=True,
        max_input_length=4000,
        max_output_length=2000,
        blocked_topics=["non_medical_advice", "financial_advice", "legal_advice"],
    ),
    AgentType.CLINICAL_DOCUMENTATION: GuardrailPolicy(
        agent_type=AgentType.CLINICAL_DOCUMENTATION,
        allowed_categories=[
            MedicalContentCategory.DIAGNOSIS,
            MedicalContentCategory.TREATMENT,
            MedicalContentCategory.MEDICATION,
            MedicalContentCategory.GENERAL,
        ],
        phi_detection_enabled=True,
        phi_redaction_strategy="hash",
        require_citations=False,
        max_input_length=8000,
        max_output_length=4000,
        blocked_topics=["non_medical"],
    ),
    AgentType.PATIENT_SUPPORT: GuardrailPolicy(
        agent_type=AgentType.PATIENT_SUPPORT,
        allowed_categories=[
            MedicalContentCategory.GENERAL,
            MedicalContentCategory.PREVENTION,
            MedicalContentCategory.NUTRITION,
            MedicalContentCategory.MENTAL,
            MedicalContentCategory.IMMUNIZATION,
        ],
        phi_detection_enabled=True,
        require_citations=False,
        require_medical_disclaimer=True,
        max_input_length=2000,
        max_output_length=2000,
        content_safety_filter=True,
        blocked_topics=["diagnosis", "prescription", "treatment_plan"],
    ),
    AgentType.MEDICAL_RESEARCH: GuardrailPolicy(
        agent_type=AgentType.MEDICAL_RESEARCH,
        allowed_categories=list(MedicalContentCategory),
        phi_detection_enabled=True,
        require_citations=True,
        max_input_length=8000,
        max_output_length=8000,
        topic_control_enabled=False,
    ),
    AgentType.PUBLIC_HEALTH: GuardrailPolicy(
        agent_type=AgentType.PUBLIC_HEALTH,
        allowed_categories=[
            MedicalContentCategory.PUBLIC_HEALTH,
            MedicalContentCategory.INFECTIOUS_DISEASE,
            MedicalContentCategory.IMMUNIZATION,
            MedicalContentCategory.NUTRITION,
            MedicalContentCategory.MATERNAL,
            MedicalContentCategory.CHILD,
            MedicalContentCategory.PREVENTION,
        ],
        phi_detection_enabled=True,
        require_citations=True,
        max_input_length=4000,
        max_output_length=4000,
        blocked_topics=["individual_diagnosis", "individual_treatment"],
    ),
    AgentType.APPOINTMENT: GuardrailPolicy(
        agent_type=AgentType.APPOINTMENT,
        allowed_categories=[MedicalContentCategory.GENERAL],
        phi_detection_enabled=True,
        require_citations=False,
        max_input_length=1000,
        max_output_length=1000,
        topic_control_enabled=True,
        blocked_topics=["medical_advice"],
    ),
    AgentType.ADMIN: GuardrailPolicy(
        agent_type=AgentType.ADMIN,
        allowed_categories=[MedicalContentCategory.GENERAL],
        phi_detection_enabled=True,
        content_safety_filter=True,
        max_input_length=2000,
        max_output_length=2000,
        topic_control_enabled=True,
        blocked_topics=["clinical_decision", "medical_advice"],
    ),
}


def get_policy(agent_type: AgentType) -> GuardrailPolicy:
    return DEFAULT_POLICIES.get(agent_type, DEFAULT_POLICIES[AgentType.TRIAGE])


def get_all_policies() -> dict[str, dict[str, Any]]:
    return {at.value: p.__dict__ for at, p in DEFAULT_POLICIES.items()}
