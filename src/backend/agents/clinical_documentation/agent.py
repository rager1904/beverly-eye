from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from src.backend.agents.agent_base import (
    AgentContext,
    AgentResponse,
    BaseAgent,
    FallbackStrategy,
    ModelConfig,
    ModelProvider,
    ToolDef,
    FALLBACK_CHAIN,
)

from .prompts import (
    BEMBA_SOAP_PROMPT,
    CLINICAL_SUMMARY_PROMPT,
    FOLLOWUP_PLAN_PROMPT,
    ICD10_CODING_PROMPT,
    NYANJA_SOAP_PROMPT,
    SOAP_NOTE_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)

MEDICAL_MODEL_CHAIN: List[ModelConfig] = [
    ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="qwen2.5:1.5b",
        endpoint="http://host.docker.internal:11434",
        temperature=0.05,
        max_tokens=2048,
        context_length=8192,
        timeout=300,
    ),
    ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="deepseek-r1:7b",
        endpoint="http://host.docker.internal:11434",
        temperature=0.05,
        max_tokens=2048,
        context_length=8192,
        timeout=300,
    ),
]


class ClinicalDocumentationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="clinical_documentation",
            model_configs=MEDICAL_MODEL_CHAIN,
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
        )
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("soap_note", SOAP_NOTE_EXTRACTION_PROMPT)
        self.register_prompt("soap_note_bemba", BEMBA_SOAP_PROMPT)
        self.register_prompt("soap_note_nyanja", NYANJA_SOAP_PROMPT)
        self.register_prompt("icd10_coding", ICD10_CODING_PROMPT)
        self.register_prompt("clinical_summary", CLINICAL_SUMMARY_PROMPT)
        self.register_prompt("followup_plan", FOLLOWUP_PLAN_PROMPT)

    def _register_tools(self) -> None:
        validate_soap_tool = ToolDef(
            name="validate_soap_format",
            description="Validate that the SOAP note follows correct medical documentation standards",
            parameters={
                "type": "object",
                "properties": {
                    "soap_note": {"type": "string", "description": "The SOAP note to validate"},
                },
                "required": ["soap_note"],
            },
            handler=self._validate_soap_format,
        )
        self.register_tool(validate_soap_tool)

    async def _validate_soap_format(self, soap_note: str) -> Dict[str, Any]:
        sections = ["subjective", "objective", "assessment", "plan"]
        found = [s for s in sections if s in soap_note.lower()]
        return {
            "valid": len(found) == len(sections),
            "found_sections": found,
            "missing_sections": [s for s in sections if s not in found],
            "note_length": len(soap_note),
        }

    async def generate_soap_note(
        self,
        transcript: str,
        facility_name: str = "Unknown Facility",
        provider_name: str = "Unknown Provider",
        patient_age: int = 0,
        patient_sex: str = "unknown",
        encounter_date: str = "",
        language: str = "en",
    ) -> AgentResponse:
        if language == "bem":
            prompt_template = "soap_note_bemba"
        elif language == "ny":
            prompt_template = "soap_note_nyanja"
        else:
            prompt_template = "soap_note"

        prompt = self.render_prompt(
            prompt_template,
            facility_name=facility_name,
            provider_name=provider_name,
            patient_age=patient_age,
            patient_sex=patient_sex,
            encounter_date=encounter_date,
            language=language,
            transcript=transcript,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian clinical documentation specialist."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def _lookup_icd10(self, query: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "http://emr:8001/api/v1/emr/encounters/icd10/search",
                    params={"query": query},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return []

    async def suggest_icd10_codes(
        self,
        assessment: str,
        age: int = 0,
        sex: str = "unknown",
        province: str = "Lusaka",
    ) -> AgentResponse:
        real_codes = await self._lookup_icd10(assessment)

        extra_context = ""
        if real_codes:
            codes_text = "\n".join(
                f"- {c['code']}: {c['description']}" for c in real_codes
            )
            extra_context = f"\n\nREAL ICD-10 CODES FOUND FOR THIS QUERY:\n{codes_text}\n\nUse these codes where applicable. Prefer real codes over invented ones."

        prompt = self.render_prompt(
            "icd10_coding",
            assessment=assessment + extra_context,
            age=age,
            sex=sex,
            province=province,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian medical coding specialist."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def generate_clinical_summary(
        self,
        patient_name: str,
        patient_age: int,
        patient_sex: str,
        nupi: str,
        facility: str,
        date: str,
        provider: str,
        encounter_details: str,
        previous_history: str = "",
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "clinical_summary",
            patient_name=patient_name,
            patient_age=patient_age,
            patient_sex=patient_sex,
            nupi=nupi,
            facility=facility,
            date=date,
            provider=provider,
            encounter_details=encounter_details,
            previous_history=previous_history,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian clinical officer."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def generate_followup_plan(
        self,
        patient_name: str,
        diagnosis: str,
        treatment: str,
        facility_level: str,
        district: str,
        province: str,
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "followup_plan",
            patient_name=patient_name,
            diagnosis=diagnosis,
            treatment=treatment,
            facility_level=facility_level,
            district=district,
            province=province,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian treatment planning specialist."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "soap_note")

        if action == "soap_note":
            transcript = metadata.get("transcript", "")
            if not transcript:
                transcript = context.get_context_window(1)[-1]["content"] if context.messages else ""
            return await self.generate_soap_note(
                transcript=transcript,
                facility_name=metadata.get("facility_name", ""),
                provider_name=metadata.get("provider_name", ""),
                patient_age=metadata.get("patient_age", 0),
                patient_sex=metadata.get("patient_sex", ""),
                encounter_date=metadata.get("encounter_date", ""),
                language=context.language,
            )
        elif action == "icd10_coding":
            return await self.suggest_icd10_codes(
                assessment=metadata.get("assessment", ""),
                age=metadata.get("age", 0),
                sex=metadata.get("sex", ""),
                province=metadata.get("province", "Lusaka"),
            )
        elif action == "clinical_summary":
            return await self.generate_clinical_summary(
                patient_name=metadata.get("patient_name", ""),
                patient_age=metadata.get("patient_age", 0),
                patient_sex=metadata.get("patient_sex", ""),
                nupi=metadata.get("nupi", ""),
                facility=metadata.get("facility", ""),
                date=metadata.get("date", ""),
                provider=metadata.get("provider", ""),
                encounter_details=metadata.get("encounter_details", ""),
                previous_history=metadata.get("previous_history", ""),
            )
        elif action == "followup_plan":
            return await self.generate_followup_plan(
                patient_name=metadata.get("patient_name", ""),
                diagnosis=metadata.get("diagnosis", ""),
                treatment=metadata.get("treatment", ""),
                facility_level=metadata.get("facility_level", ""),
                district=metadata.get("district", ""),
                province=metadata.get("province", ""),
            )

        user_message = context.get_context_window(1)[-1]["content"] if context.messages else ""
        return await self.generate_soap_note(transcript=user_message)
