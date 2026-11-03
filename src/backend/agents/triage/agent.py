from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.backend.agents.agent_base import (
    AgentContext,
    AgentResponse,
    BaseAgent,
    FallbackStrategy,
    ModelConfig,
    ModelProvider,
    ToolDef,
)

from .prompts import (
    BEMBA_TRIAGE_PROMPT,
    NYANJA_TRIAGE_PROMPT,
    SYMPTOM_ANALYSIS_PROMPT,
    TRIAGE_ASSESSMENT_PROMPT,
    TRIAGE_REFERRAL_PROMPT,
)
from .scoring import (
    TriageColor,
    TriageLevel,
    TriageResult,
    TriageScorer,
    VitalSigns,
)

logger = logging.getLogger(__name__)


class TriageAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="triage",
            model_configs=[
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_name="qwen2.5:1.5b",
                    endpoint="http://host.docker.internal:11434",
                    temperature=0.05,
                    max_tokens=1024,
                    context_length=4096,
                    timeout=120,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_name="qwen2.5:1.5b",
                    endpoint="http://host.docker.internal:11434",
                    temperature=0.15,
                    max_tokens=1024,
                    context_length=4096,
                    timeout=180,
                ),
            ],
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
        )
        self.scorer = TriageScorer()
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("triage_assessment", TRIAGE_ASSESSMENT_PROMPT)
        self.register_prompt("triage_referral", TRIAGE_REFERRAL_PROMPT)
        self.register_prompt("symptom_analysis", SYMPTOM_ANALYSIS_PROMPT)
        self.register_prompt("triage_bemba", BEMBA_TRIAGE_PROMPT)
        self.register_prompt("triage_nyanja", NYANJA_TRIAGE_PROMPT)

    def _register_tools(self) -> None:
        calculate_triage_tool = ToolDef(
            name="calculate_triage_score",
            description="Calculate triage score using SATS, MEWS, pediatric, or obstetric scales",
            parameters={
                "type": "object",
                "properties": {
                    "systolic_bp": {"type": "number"},
                    "diastolic_bp": {"type": "number"},
                    "heart_rate": {"type": "number"},
                    "respiratory_rate": {"type": "number"},
                    "temperature": {"type": "number"},
                    "oxygen_saturation": {"type": "number"},
                    "avpu": {"type": "string"},
                    "age_years": {"type": "number"},
                    "is_pregnant": {"type": "boolean"},
                    "chief_complaint": {"type": "string"},
                },
                "required": ["chief_complaint", "age_years"],
            },
            handler=self._handle_calculate_triage,
        )
        self.register_tool(calculate_triage_tool)

        determine_referral_tool = ToolDef(
            name="determine_referral",
            description="Determine appropriate referral pathway in Zambian health system",
            parameters={
                "type": "object",
                "properties": {
                    "triage_level": {"type": "string"},
                    "facility_level": {"type": "string"},
                    "chief_complaint": {"type": "string"},
                },
                "required": ["triage_level", "facility_level"],
            },
            handler=self._handle_determine_referral,
        )
        self.register_tool(determine_referral_tool)

    async def _handle_calculate_triage(self, **kwargs: Any) -> Dict[str, Any]:
        vitals = VitalSigns(
            systolic_bp=kwargs.get("systolic_bp"),
            diastolic_bp=kwargs.get("diastolic_bp"),
            heart_rate=kwargs.get("heart_rate"),
            respiratory_rate=kwargs.get("respiratory_rate"),
            temperature=kwargs.get("temperature"),
            oxygen_saturation=kwargs.get("oxygen_saturation"),
            avpu=kwargs.get("avpu", "alert"),
        )
        result = await self.scorer.score(
            vitals=vitals,
            chief_complaint=kwargs.get("chief_complaint", ""),
            age_years=kwargs.get("age_years", 30),
            is_pregnant=kwargs.get("is_pregnant", False),
        )
        return {
            "level": result.level.value,
            "color": result.color.value,
            "score": result.score,
            "response_time_minutes": result.response_time_minutes,
            "warning_flags": result.warning_flags,
            "mews_score": result.mews_score,
            "rationale": result.rationale,
        }

    async def _handle_determine_referral(
        self, triage_level: str, facility_level: str, chief_complaint: str = ""
    ) -> Dict[str, Any]:
        result = TriageResult(
            level=TriageLevel(triage_level),
            color=TriageColor.RED if triage_level == "emergency" else TriageColor.ORANGE,
            score=0.0,
            response_time_minutes=0,
        )
        referral = await self.scorer.determine_referral(result, facility_level)
        return referral or {"recommended": False}

    async def assess(
        self,
        chief_complaint: str,
        history: str = "",
        systolic_bp: Optional[float] = None,
        diastolic_bp: Optional[float] = None,
        heart_rate: Optional[float] = None,
        respiratory_rate: Optional[float] = None,
        temperature: Optional[float] = None,
        oxygen_saturation: Optional[float] = None,
        avpu: str = "alert",
        pain_score: Optional[int] = None,
        mobility: str = "walking",
        age: float = 30,
        sex: str = "unknown",
        is_pregnant: bool = False,
        facility_level: str = "clinic",
        province: str = "Lusaka",
        district: str = "Lusaka",
        language: str = "en",
        additional_risk_factors: Optional[List[str]] = None,
    ) -> AgentResponse:
        if language == "bem":
            prompt_template = "triage_bemba"
        elif language == "ny":
            prompt_template = "triage_nyanja"
        else:
            prompt_template = "triage_assessment"

        vitals = VitalSigns(
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            heart_rate=heart_rate,
            respiratory_rate=respiratory_rate,
            temperature=temperature,
            oxygen_saturation=oxygen_saturation,
            avpu=avpu,
            pain_score=pain_score,
        )

        algorithm_result = await self.scorer.score(
            vitals=vitals,
            chief_complaint=chief_complaint,
            age_years=age,
            is_pregnant=is_pregnant,
            mobility=mobility,
            additional_risk_factors=additional_risk_factors,
        )

        prompt = self.render_prompt(
            prompt_template,
            age=age,
            sex=sex,
            is_pregnant=is_pregnant,
            facility_level=facility_level,
            province=province,
            district=district,
            language=language,
            chief_complaint=chief_complaint,
            history=history,
            systolic_bp=systolic_bp or "N/A",
            diastolic_bp=diastolic_bp or "N/A",
            heart_rate=heart_rate or "N/A",
            respiratory_rate=respiratory_rate or "N/A",
            temperature=temperature or "N/A",
            oxygen_saturation=oxygen_saturation or "N/A",
            avpu=avpu,
            pain_score=pain_score or "N/A",
            mobility=mobility,
            muac_cm="N/A",
            risk_factors="; ".join(additional_risk_factors or ["None"]),
        )

        messages = [
            {"role": "system", "content": "You are a triage nurse in Zambia using SATS."},
            {"role": "user", "content": prompt},
        ]

        llm_response = await self.generate(messages)

        llm_response.structured_data = {
            "algorithm_result": {
                "level": algorithm_result.level.value,
                "color": algorithm_result.color.value,
                "score": algorithm_result.score,
                "response_time_minutes": algorithm_result.response_time_minutes,
                "warning_flags": algorithm_result.warning_flags,
                "mews_score": algorithm_result.mews_score,
                "rationale": algorithm_result.rationale,
            },
            "vital_signs": vitals.__dict__,
        }

        if algorithm_result.requires_immediate_care:
            llm_response.requires_followup = True
            llm_response.followup_question = "Patient requires immediate care. Has emergency transport been arranged?"

        return llm_response

    async def analyze_symptoms(
        self,
        symptoms: str,
        history: str = "",
        age: float = 30,
        sex: str = "unknown",
        district: str = "Lusaka",
        province: str = "Lusaka",
        season: str = "rainy",
        risk_factors: str = "",
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "symptom_analysis",
            age=age,
            sex=sex,
            district=district,
            province=province,
            season=season,
            symptoms=symptoms,
            history=history,
            risk_factors=risk_factors,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian clinical officer."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "assess")
        user_input = metadata.get("user_input", "")

        last_msg = ""
        msgs = context.get_context_window(1)
        if msgs:
            last_msg = msgs[-1].get("content", "")

        if action == "analyze_symptoms":
            return await self.analyze_symptoms(
                symptoms=metadata.get("symptoms", user_input),
                history=metadata.get("history", ""),
                age=metadata.get("age", 30),
                sex=metadata.get("sex", ""),
                district=metadata.get("district", ""),
                province=metadata.get("province", ""),
                season=metadata.get("season", "rainy"),
            )

        return await self.assess(
            chief_complaint=metadata.get("chief_complaint", user_input or last_msg),
            history=metadata.get("history", ""),
            systolic_bp=metadata.get("systolic_bp"),
            diastolic_bp=metadata.get("diastolic_bp"),
            heart_rate=metadata.get("heart_rate"),
            respiratory_rate=metadata.get("respiratory_rate"),
            temperature=metadata.get("temperature"),
            oxygen_saturation=metadata.get("oxygen_saturation"),
            avpu=metadata.get("avpu", "alert"),
            age=metadata.get("age", 30),
            sex=metadata.get("sex", ""),
            is_pregnant=metadata.get("is_pregnant", False),
            facility_level=metadata.get("facility_level", "clinic"),
            province=metadata.get("province", "Lusaka"),
            district=metadata.get("district", "Lusaka"),
            language=context.language,
        )
