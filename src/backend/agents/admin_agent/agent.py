from __future__ import annotations

import logging
from datetime import datetime, timedelta
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

logger = logging.getLogger(__name__)


ANALYTICS_PROMPT = """You are a hospital administrator for the Zambian health system. Generate a concise analytics report using ONLY the data and computed KPIs provided below. DO NOT invent any numbers or fill in bracketed placeholders — use the exact values given. If a KPI is not in the data, state "Not available" rather than guessing.

FACILITY: {facility_name}
FACILITY LEVEL: {facility_level}
DISTRICT: {district}
PROVINCE: {province}
REPORT PERIOD: {period}
REPORT TYPE: {report_type}

DATA:
{data}

---

Write the report as a narrative using the real data above. Do not include brackets, placeholders, or fabricated numbers in your response."""

STAFF_SCHEDULING_PROMPT = """You are a staff scheduling coordinator for a Zambian health facility. Create an optimal staff schedule.

FACILITY: {facility_name}
FACILITY LEVEL: {facility_level}
SCHEDULE PERIOD: {period} ({start_date} to {end_date})

STAFF AVAILABILITY:
{staff_data}

MINIMUM STAFF REQUIREMENTS:
{staff_requirements}

SPECIAL CONSTRAINTS:
{constraints}

---

**Staff Schedule:**

| Day | Shift | Required | Assigned | Notes |
|-----|-------|----------|----------|-------|
| [date] | Morning | [n] | [names] | |
| [date] | Afternoon | [n] | [names] | |
| [date] | Night | [n] | [names] | |

**Coverage Gaps:**
[Days/shifts with insufficient coverage]

**Overtime Summary:**
[Staff with overtime hours]

**Recommendations:**
1. [Recommendation to address gaps]

**Confidence:** [0.0-1.0]
"""

MOH_REPORTING_PROMPT = """You are a health information officer preparing a Ministry of Health report for Zambia.

FACILITY: {facility_name}
FACILITY LEVEL: {facility_level}
DISTRICT: {district}
PROVINCE: {province}
REPORTING PERIOD: {period}
REPORT TYPE: {report_type}

HMS DATA:
{hmis_data}

DHIS2 DATA:
{dhis2_data}

---

**Ministry of Health Report**

**Section A: Service Delivery**
- OPD attendances: [number]
- IPD admissions: [number]
- Deliveries (total): [number]
- Caesarean sections: [number]

**Section B: Disease Surveillance**
- Malaria confirmed cases: [number]
- Diarrhoea with dehydration: [number]
- Pneumonia: [number]
- TB new cases: [number]
- HIV new on ART: [number]

**Section C: Maternal & Child Health**
- ANC first visit before 12 weeks: [number]
- IPTp3+ coverage: [percentage]%
- Fully immunized children <1: [number]

**Section D: Resources**
- Staffing levels: [by cadre]
- Medicine availability: [top 10 tracer medicines]

**Section E: Challenges & Recommendations**
[As per HMIS guidelines]

**Confidence:** [0.0-1.0]
"""

OPERATIONAL_REPORT_PROMPT = """You are a hospital operations manager in Zambia. Provide an operational report.

FACILITY: {facility_name}
PERIOD: {period}

OPERATIONAL DATA:
{operational_data}

---

**Operational Report**

**Patient Flow:**
- Average waiting time: [minutes]
- Average consultation time: [minutes]
- Patients seen per clinician per day: [number]

**Resource Status:**
- Bed occupancy: [percentage]%
- Medicine stockout rate: [percentage]%
- Lab turnaround time: [hours]

**Financial Summary:**
- Revenue collected: [amount] ZMW
- NHIMA claims submitted: [amount] ZMW
- Expenditure: [amount] ZMW

**Incidents Reported:**
- [Number] clinical incidents
- [Number] patient complaints

**Action Items:**
1. [Action item]

**Confidence:** [0.0-1.0]
"""


class AdminAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="admin_agent",
            model_configs=[
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
            ],
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
        )
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("analytics", ANALYTICS_PROMPT)
        self.register_prompt("staff_scheduling", STAFF_SCHEDULING_PROMPT)
        self.register_prompt("moh_reporting", MOH_REPORTING_PROMPT)
        self.register_prompt("operational_report", OPERATIONAL_REPORT_PROMPT)

    def _register_tools(self) -> None:
        calculate_kpis = ToolDef(
            name="calculate_kpis",
            description="Calculate hospital key performance indicators",
            parameters={
                "type": "object",
                "properties": {
                    "outpatient_visits": {"type": "number"},
                    "admissions": {"type": "number"},
                    "bed_capacity": {"type": "number"},
                    "inpatient_days": {"type": "number"},
                },
                "required": ["outpatient_visits", "admissions", "bed_capacity", "inpatient_days"],
            },
            handler=self._handle_calculate_kpis,
        )
        self.register_tool(calculate_kpis)

    async def _handle_calculate_kpis(
        self,
        outpatient_visits: float,
        admissions: float,
        bed_capacity: float,
        inpatient_days: float,
    ) -> Dict[str, Any]:
        bed_occupancy = (inpatient_days / (bed_capacity * 30.44)) * 100 if bed_capacity > 0 else 0
        avg_length_of_stay = inpatient_days / admissions if admissions > 0 else 0
        return {
            "bed_occupancy_pct": round(bed_occupancy, 1),
            "avg_length_of_stay_days": round(avg_length_of_stay, 1),
            "outpatient_per_day": round(outpatient_visits / 30.44, 0),
            "admission_rate": round(admissions / outpatient_visits * 100, 2) if outpatient_visits > 0 else 0,
        }

    async def generate_analytics_report(
        self,
        facility_name: str,
        facility_level: str,
        district: str,
        province: str,
        period: str,
        report_type: str,
        data: Dict[str, Any],
    ) -> AgentResponse:
        data_text = "\n".join(f"- {k}: {v}" for k, v in data.items()) if isinstance(data, dict) else str(data)

        prompt = self.render_prompt(
            "analytics",
            facility_name=facility_name,
            facility_level=facility_level,
            district=district,
            province=province,
            period=period,
            report_type=report_type,
            data=data_text,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian hospital administrator."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def generate_moh_report(
        self,
        facility_name: str,
        facility_level: str,
        district: str,
        province: str,
        period: str,
        report_type: str = "monthly",
        hmis_data: Optional[Dict[str, Any]] = None,
        dhis2_data: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        hmis_text = "\n".join(f"- {k}: {v}" for k, v in (hmis_data or {}).items())
        dhis2_text = "\n".join(f"- {k}: {v}" for k, v in (dhis2_data or {}).items())

        prompt = self.render_prompt(
            "moh_reporting",
            facility_name=facility_name,
            facility_level=facility_level,
            district=district,
            province=province,
            period=period,
            report_type=report_type,
            hmis_data=hmis_text or "No HMIS data provided",
            dhis2_data=dhis2_text or "No DHIS2 data provided",
        )

        messages = [
            {"role": "system", "content": "You are a Zambian health information officer."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "analytics")

        if action == "moh_report":
            return await self.generate_moh_report(
                facility_name=metadata.get("facility_name", "Lusaka General Hospital"),
                facility_level=metadata.get("facility_level", "Level 1"),
                district=metadata.get("district", "Lusaka"),
                province=metadata.get("province", "Lusaka"),
                period=metadata.get("period", "Monthly"),
                report_type=metadata.get("report_type", "monthly"),
                hmis_data=metadata.get("hmis_data"),
                dhis2_data=metadata.get("dhis2_data"),
            )

        data = metadata.get("data", {})
        if not isinstance(data, dict):
            data = {}
        if "query" not in data:
            computed_kpis = await self._handle_calculate_kpis(
                outpatient_visits=float(data.get("outpatient_visits", metadata.get("outpatient_visits", 0))),
                admissions=float(data.get("admissions", metadata.get("admissions", 0))),
                bed_capacity=float(data.get("bed_capacity", metadata.get("bed_capacity", 0))),
                inpatient_days=float(data.get("inpatient_days", metadata.get("inpatient_days", 0))),
            )
            data.update(computed_kpis)

        return await self.generate_analytics_report(
            facility_name=metadata.get("facility_name", "Lusaka General Hospital"),
            facility_level=metadata.get("facility_level", "Level 1"),
            district=metadata.get("district", "Lusaka"),
            province=metadata.get("province", "Lusaka"),
            period=metadata.get("period", "Monthly"),
            report_type=metadata.get("report_type", "monthly"),
            data=data,
        )
