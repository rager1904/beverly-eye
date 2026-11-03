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

from .zambia_health_data import DiseaseOutbreakData, ProvinceHealthData, ZambiaHealthData

logger = logging.getLogger(__name__)


SURVEILLANCE_PROMPT = """You are a disease surveillance officer for the Zambia Ministry of Health. Analyze the following surveillance data.

PROVINCE: {province}
DISTRICT: {district}
PERIOD: {period}
DISEASE: {disease}

DATA:
{surveillance_data}

HISTORICAL COMPARISON:
{historical_data}

---

**Surveillance Analysis**

**Current Situation:**
[Description of current cases and distribution]

**Trend Analysis:**
- Current vs previous period: [increase/decrease/stable]
- Current vs same period last year: [comparison]
- Epidemic threshold: [crossed / not crossed]

**Risk Assessment:**
- Transmission risk: [High/Moderate/Low]
- Affected population: [groups most affected]

**Recommended Actions:**
1. [Immediate action]
2. [Short-term action]
3. [Long-term action]

**Reporting Requirement:**
- [Notify District Health Office / Provincial Health Office / MoH / WHO]

**Confidence:** [0.0-1.0]
"""

OUTBREAK_PROMPT = """You are part of the Zambia National Public Health Emergency Operations Centre. Assess the following potential outbreak.

SUSPECTED DISEASE: {disease}
LOCATION: {district}, {province}
DATE RANGE: {date_range}
CASES: {cases}
DEATHS: {deaths}
ATTACK RATE: {attack_rate}%
CASE FATALITY RATE: {cfr}%

CLINICAL PRESENTATION:
{clinical_presentation}

LABORATORY RESULTS:
{lab_results}

CONTROL MEASURES IMPLEMENTED:
{control_measures}

---

**Outbreak Assessment**

**Classification:** [Suspected outbreak / Confirmed outbreak / Not an outbreak]

**Case Definition:** [Applied case definition]

**Outbreak Parameters:**
- Reproductive number (R0) estimate: [value]
- Epidemic curve: [description]
- Geographic spread: [localized / district-wide / province-wide]

**Response Recommendations:**
1. [Recommendation]
2. [Recommendation]
3. [Recommendation]

**Resource Requirements:**
- [Resource]: [quantity]
- [Resource]: [quantity]

**Communication:**
- Public messaging: [key messages]
- Reporting to: [level]

**Confidence:** [0.0-1.0]
"""

VACCINATION_MONITORING_PROMPT = """You are a vaccination program monitor for the Zambia Expanded Programme on Immunization (EPI). Analyze the following vaccination data.

PROVINCE: {province}
DISTRICT: {district}
PERIOD: {period}
VACCINE: {vaccine}
TARGET POPULATION: {target_population}

COVERAGE DATA:
{coverage_data}

DROPOUT RATES:
{dropout_data}

COLD CHAIN STATUS:
{cold_chain_data}

---

**Vaccination Coverage Analysis**

**Coverage by Antigen:**
- [Antigen]: [%] - [target: 95%]
- [Antigen]: [%] - [target: 95%]

**Dropout Rates:**
- BCG to Measles-Rubella: [%]
- Penta1 to Penta3: [%]
- Dropout alert: [Yes/No if >10%]

**Challenges Identified:**
1. [Challenge]
2. [Challenge]

**Recommendations:**
1. [Recommendation]
2. [Recommendation]

**Confidence:** [0.0-1.0]
"""

MALARIA_MONITORING_PROMPT = """You are a malaria control officer for the Zambia National Malaria Elimination Programme. Analyze the following malaria data.

PROVINCE: {province}
DISTRICT: {district}
PERIOD: {period}

MALARIA DATA:
{malaria_data}

INTERVENTION COVERAGE:
{intervention_data}

---

**Malaria Situation Analysis**

**Malaria Burden:**
- Confirmed cases: [number]
- Test positivity rate: [%]
- Severe malaria cases: [number]
- Malaria deaths: [number]

**Intervention Coverage:**
- ITN ownership: [%]
- IRS coverage: [%]
- IPTp3+ coverage: [%]
- SMC coverage (under 5): [%]

**Trend Analysis:**
[Comparison with previous periods]

**Hotspot Districts:**
[Districts with highest incidence]

**Recommendations:**
1. [Recommendation]
2. [Recommendation]

**Confidence:** [0.0-1.0]
"""


class PublicHealthAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="public_health",
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
        self.zambia_data = ZambiaHealthData()
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("surveillance", SURVEILLANCE_PROMPT)
        self.register_prompt("outbreak", OUTBREAK_PROMPT)
        self.register_prompt("vaccination", VACCINATION_MONITORING_PROMPT)
        self.register_prompt("malaria_monitoring", MALARIA_MONITORING_PROMPT)

    def _register_tools(self) -> None:
        get_province_data_tool = ToolDef(
            name="get_province_health_data",
            description="Get health data for a Zambian province",
            parameters={
                "type": "object",
                "properties": {"province": {"type": "string"}},
                "required": ["province"],
            },
            handler=self._handle_get_province_data,
        )
        self.register_tool(get_province_data_tool)

        get_national_summary_tool = ToolDef(
            name="get_national_health_summary",
            description="Get national health summary for Zambia",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self._handle_get_national_summary,
        )
        self.register_tool(get_national_summary_tool)

        get_disease_burden_tool = ToolDef(
            name="get_disease_burden_summary",
            description="Get disease burden summary for major diseases in Zambia",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self._handle_get_disease_burden,
        )
        self.register_tool(get_disease_burden_tool)

    async def _handle_get_province_data(self, province: str) -> Optional[Dict[str, Any]]:
        data = self.zambia_data.get_province(province)
        if data:
            return {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        return None

    async def _handle_get_national_summary(self) -> Dict[str, Any]:
        return self.zambia_data.get_national_summary()

    async def _handle_get_disease_burden(self) -> Dict[str, Any]:
        return self.zambia_data.disease_burden_summary()

    async def analyze_surveillance(
        self,
        province: str,
        district: str,
        period: str,
        disease: str,
        surveillance_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        data_text = "\n".join(f"- {k}: {v}" for k, v in surveillance_data.items())
        hist_text = "\n".join(f"- {k}: {v}" for k, v in (historical_data or {}).items()) or "No historical data"

        prompt = self.render_prompt(
            "surveillance",
            province=province,
            district=district,
            period=period,
            disease=disease,
            surveillance_data=data_text,
            historical_data=hist_text,
        )

        messages = [
            {"role": "system", "content": f"You are a Zambian disease surveillance officer. Use this reference data: {self._get_province_context(province)}"},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def assess_outbreak(
        self,
        disease: str,
        district: str,
        province: str,
        date_range: str,
        cases: int,
        deaths: int,
        attack_rate: float,
        cfr: float,
        clinical_presentation: str = "",
        lab_results: str = "",
        control_measures: str = "",
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "outbreak",
            disease=disease,
            district=district,
            province=province,
            date_range=date_range,
            cases=cases,
            deaths=deaths,
            attack_rate=attack_rate,
            cfr=cfr,
            clinical_presentation=clinical_presentation or "Not specified",
            lab_results=lab_results or "Pending",
            control_measures=control_measures or "None reported",
        )

        prov_context = self._get_province_context(province)
        system_msg = "You are a Zambian public health emergency officer."
        if prov_context:
            system_msg += f" Reference province data: {prov_context}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        response = await self.generate(messages)
        prov_data = self.zambia_data.get_province(province)
        if prov_data:
            response.structured_data = {
                "province_context": {k: v for k, v in prov_data.__dict__.items() if not k.startswith("_")},
            }
        return response

    async def monitor_vaccination(
        self,
        province: str,
        district: str,
        period: str,
        vaccine: str,
        target_population: int,
        coverage_data: Dict[str, Any],
        dropout_data: Optional[Dict[str, Any]] = None,
        cold_chain_data: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        cov_text = "\n".join(f"- {k}: {v}%" for k, v in coverage_data.items())
        drop_text = "\n".join(f"- {k}: {v}%" for k, v in (dropout_data or {}).items()) or "No dropout data"
        cold_text = "\n".join(f"- {k}: {v}" for k, v in (cold_chain_data or {}).items()) or "No cold chain data"

        prompt = self.render_prompt(
            "vaccination",
            province=province,
            district=district,
            period=period,
            vaccine=vaccine,
            target_population=target_population,
            coverage_data=cov_text,
            dropout_data=drop_text,
            cold_chain_data=cold_text,
        )

        prov_context = self._get_province_context(province)
        system_msg = "You are a Zambian EPI vaccination monitor."
        if prov_context:
            system_msg += f" Reference province data: {prov_context}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    def _get_province_context(self, province_name: str) -> str:
        data = self.zambia_data.get_province(province_name)
        if not data:
            return ""
        return (
            f"Population: {data.population:,}, Malaria incidence: {data.malaria_incidence_per_1000}/1000, "
            f"HIV prevalence: {data.hiv_prevalence_pct}%, Immunization: {data.immunization_coverage_pct}%, "
            f"Hospitals: {data.hospitals}, Clinics: {data.clinics}"
        )

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "surveillance")

        if action == "outbreak":
            return await self.assess_outbreak(
                disease=metadata.get("disease", ""),
                district=metadata.get("district", ""),
                province=metadata.get("province", ""),
                date_range=metadata.get("date_range", ""),
                cases=metadata.get("cases", 0),
                deaths=metadata.get("deaths", 0),
                attack_rate=metadata.get("attack_rate", 0.0),
                cfr=metadata.get("cfr", 0.0),
                clinical_presentation=metadata.get("clinical_presentation", ""),
                lab_results=metadata.get("lab_results", ""),
                control_measures=metadata.get("control_measures", ""),
            )
        elif action == "vaccination":
            return await self.monitor_vaccination(
                province=metadata.get("province", ""),
                district=metadata.get("district", ""),
                period=metadata.get("period", ""),
                vaccine=metadata.get("vaccine", ""),
                target_population=metadata.get("target_population", 0),
                coverage_data=metadata.get("coverage_data", {}),
                dropout_data=metadata.get("dropout_data"),
                cold_chain_data=metadata.get("cold_chain_data"),
            )
        elif action == "disease_burden":
            summary = self.zambia_data.disease_burden_summary()
            return AgentResponse(
                content=str(summary),
                confidence=1.0,
                model_used=self.agent_name,
                structured_data=summary,
            )

        user_message = context.get_context_window(1)[-1]["content"] if context.messages else ""
        return await self.analyze_surveillance(
            province=metadata.get("province", ""),
            district=metadata.get("district", ""),
            period=metadata.get("period", ""),
            disease=metadata.get("disease", ""),
            surveillance_data=metadata.get("data", {"query": user_message}),
            historical_data=metadata.get("historical_data"),
        )
