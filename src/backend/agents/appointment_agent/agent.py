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
from src.backend.agents.tools import AppointmentTool

logger = logging.getLogger(__name__)


SCHEDULE_PROMPT = """You are a healthcare appointment scheduler for Zambia. Manage the following appointment request.

PATIENT: {patient_name}
NUPI: {nupi}
PHONE: {patient_phone}
LOCATION: {district}, {province}
PREFERRED LANGUAGE: {language}

REQUEST TYPE: {request_type}
REASON: {reason}
PREFERRED DATE: {preferred_date}
PREFERRED TIME: {preferred_time}
PREFERRED PROVIDER: {preferred_provider}
APPOINTMENT TYPE: {appointment_type}

AVAILABLE SLOTS:
{available_slots}

---

APPOINTMENT RESPONSE:

**Status:** [Confirmed / Rescheduled / Waitlisted / Declined]

**Appointment Details:**
- Date: [date]
- Time: [time]
- Duration: [minutes]
- Provider: [name]
- Facility: [name]
- Location: [address]

**Instructions for Patient:**
1. [Instruction in English]
2. [Instruction in local language if applicable]

**Reminders:**
- SMS reminder: [24h before / 2h before]
- What to bring: [items]

**Waitlist Information:** [if applicable]

**Confidence:** [0.0-1.0]
"""

RESCHEDULE_PROMPT = """You are a healthcare appointment scheduler in Zambia. Handle the following reschedule request.

CURRENT APPOINTMENT:
- ID: {appointment_id}
- Date: {current_date}
- Time: {current_time}
- Provider: {current_provider}
- Facility: {current_facility}

PATIENT: {patient_name}
REASON FOR RESCHEDULE: {reason}
NEW PREFERRED DATE: {preferred_date}
NEW PREFERRED TIME: {preferred_time}

AVAILABLE SLOTS:
{available_slots}

---

RESCHEDULE RESPONSE:
**Status:** [Rescheduled / Declined]

**New Appointment:**
- Date: [date]
- Time: [time]
- Provider: [name]

**Cancellation Policy:** [applicable fees/notice period]

**Confidence:** [0.0-1.0]
"""

REMINDER_PROMPT = """Generate an appointment reminder for the following patient in Zambia.

APPOINTMENT:
- Patient: {patient_name}
- Phone: {patient_phone}
- Date: {appointment_date}
- Time: {appointment_time}
- Provider: {provider_name}
- Facility: {facility_name}
- Address: {facility_address}
- Type: {appointment_type}

LANGUAGE: {language}
REMINDER TYPE: {reminder_type} (24h / 2h / confirmation)

---

REMINDER MESSAGE:
[Concise reminder text in requested language]

[Alternative text in English if different]

**Confidence:** [0.0-1.0]
"""

BEMBA_REMINDER_PROMPT = """Lemba icibusha ca kubwela ku cibinda.

MULWELE: {patient_name}
UBUSHIKU: {appointment_date}
INSHITA: {appointment_time}
DOKOTALA: {provider_name}
IBUNGWE: {facility_name}

LEMBA ICIBUSHA MU CIBEMBA:
[icibusha]

Confidence: [0.0-1.0]
"""


class AppointmentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="appointment_agent",
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
        self.appointment_tool = AppointmentTool()
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("schedule", SCHEDULE_PROMPT)
        self.register_prompt("reschedule", RESCHEDULE_PROMPT)
        self.register_prompt("reminder", REMINDER_PROMPT)
        self.register_prompt("reminder_bemba", BEMBA_REMINDER_PROMPT)

    def _register_tools(self) -> None:
        schedule_tool = ToolDef(
            name="schedule_appointment",
            description="Schedule a new appointment",
            parameters={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "provider_id": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "appointment_type": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["patient_id", "provider_id", "start_time", "end_time"],
            },
            handler=self._handle_schedule,
        )
        self.register_tool(schedule_tool)

        reschedule_tool = ToolDef(
            name="reschedule_appointment",
            description="Reschedule an existing appointment",
            parameters={
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "new_start_time": {"type": "string"},
                    "new_end_time": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["appointment_id", "new_start_time", "new_end_time"],
            },
            handler=self._handle_reschedule,
        )
        self.register_tool(reschedule_tool)

        cancel_tool = ToolDef(
            name="cancel_appointment",
            description="Cancel an appointment",
            parameters={
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["appointment_id"],
            },
            handler=self._handle_cancel,
        )
        self.register_tool(cancel_tool)

        get_slots_tool = ToolDef(
            name="get_available_slots",
            description="Get available appointment slots",
            parameters={
                "type": "object",
                "properties": {
                    "provider_id": {"type": "string"},
                    "date": {"type": "string"},
                    "appointment_type": {"type": "string"},
                },
                "required": ["provider_id", "date"],
            },
            handler=self._handle_get_slots,
        )
        self.register_tool(get_slots_tool)

        list_appointments_tool = ToolDef(
            name="list_upcoming_appointments",
            description="List upcoming appointments for a patient or provider",
            parameters={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "Patient ID or NUPI to look up appointments"},
                    "days": {"type": "integer", "description": "Number of days to look ahead", "default": 30},
                },
                "required": ["patient_id"],
            },
            handler=self._handle_list_upcoming,
        )
        self.register_tool(list_appointments_tool)

    async def _handle_schedule(self, **kwargs: Any) -> Dict[str, Any]:
        return await self.appointment_tool.schedule(**kwargs)

    async def _handle_reschedule(self, **kwargs: Any) -> Dict[str, Any]:
        return await self.appointment_tool.reschedule(**kwargs)

    async def _handle_cancel(self, appointment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return await self.appointment_tool.cancel(appointment_id, reason)

    async def _handle_get_slots(self, provider_id: str, date: str, appointment_type: str = "outpatient") -> List[Dict[str, Any]]:
        return await self.appointment_tool.get_slots(provider_id, date, appointment_type)

    async def _handle_list_upcoming(self, patient_id: str, days: int = 30) -> List[Dict[str, Any]]:
        return await self.appointment_tool.list_upcoming(patient_id=patient_id, days=days)

    async def schedule(
        self,
        patient_name: str,
        nupi: str,
        patient_phone: str,
        reason: str,
        district: str = "Lusaka",
        province: str = "Lusaka",
        preferred_date: str = "",
        preferred_time: str = "",
        preferred_provider: str = "",
        appointment_type: str = "outpatient",
        language: str = "en",
    ) -> AgentResponse:
        slots = []
        if preferred_provider and preferred_date:
            try:
                slots = await self.appointment_tool.get_slots(
                    provider_id=preferred_provider,
                    date=preferred_date,
                    appointment_type=appointment_type,
                )
            except Exception as e:
                logger.warning("Could not fetch slots: %s", e)

        available_slots_text = "\n".join(
            f"- {s.get('start_time', 'N/A')} to {s.get('end_time', 'N/A')} with {s.get('provider_name', 'N/A')}"
            for s in slots
        ) or "Please specify preferred date/time."

        prompt = self.render_prompt(
            "schedule",
            patient_name=patient_name,
            nupi=nupi,
            patient_phone=patient_phone,
            district=district,
            province=province,
            language=language,
            request_type="New Appointment",
            reason=reason,
            preferred_date=preferred_date or "Not specified",
            preferred_time=preferred_time or "Not specified",
            preferred_provider=preferred_provider or "Any available",
            appointment_type=appointment_type,
            available_slots=available_slots_text,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian healthcare appointment scheduler."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def generate_reminder(
        self,
        patient_name: str,
        patient_phone: str,
        appointment_date: str,
        appointment_time: str,
        provider_name: str,
        facility_name: str,
        facility_address: str = "",
        appointment_type: str = "outpatient",
        language: str = "en",
        reminder_type: str = "24h",
    ) -> AgentResponse:
        if language == "bem":
            prompt_template = "reminder_bemba"
        else:
            prompt_template = "reminder"

        prompt = self.render_prompt(
            prompt_template,
            patient_name=patient_name,
            patient_phone=patient_phone,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            provider_name=provider_name,
            facility_name=facility_name,
            facility_address=facility_address or "Contact facility for directions",
            appointment_type=appointment_type,
            language=language,
            reminder_type=reminder_type,
        )

        messages = [
            {"role": "system", "content": "You are a healthcare reminder system for Zambia."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "")

        user_message = context.get_context_window(1)[-1]["content"] if context.messages else ""
        lookup_keywords = ["my appointment", "next appointment", "upcoming", "my appointments", "when is", "appointments", "what appointment"]
        is_lookup = action == "lookup" or (not action and any(kw in user_message.lower() for kw in lookup_keywords))

        if is_lookup:
            patient_id = metadata.get("patient_id") or metadata.get("nupi", "") or context.user_id or ""
            days = metadata.get("days", 30)
            try:
                if not patient_id:
                    return AgentResponse(
                        content="I need your patient ID or NUPI number to look up appointments. Could you please provide that?",
                        model_used=self._model_configs[0].model_name,
                        confidence=0.5,
                    )
                resp = await self.appointment_tool.list_upcoming(patient_id=patient_id, days=days)
                items = resp.get("items", []) if isinstance(resp, dict) else (resp or [])
                if items:
                    lines = []
                    for a in items[:5]:
                        lines.append(f"- {a.get('start_time', '?')} with {a.get('provider_name', '?')} at {a.get('facility_name', '?')} ({a.get('status', '?')})")
                    return AgentResponse(
                        content="Your upcoming appointments:\n" + "\n".join(lines),
                        model_used=self._model_configs[0].model_name,
                        confidence=0.9,
                    )
                return AgentResponse(
                    content="No upcoming appointments found.",
                    model_used=self._model_configs[0].model_name,
                    confidence=0.9,
                )
            except Exception as e:
                logger.warning("Appointment lookup failed: %s", e)
                return AgentResponse(
                    content="I couldn't look up your appointments right now. Please try again later or contact the facility directly.",
                    model_used=self._model_configs[0].model_name,
                    confidence=0.5,
                )

        if action == "reminder":
            return await self.generate_reminder(
                patient_name=metadata.get("patient_name", ""),
                patient_phone=metadata.get("patient_phone", ""),
                appointment_date=metadata.get("appointment_date", ""),
                appointment_time=metadata.get("appointment_time", ""),
                provider_name=metadata.get("provider_name", ""),
                facility_name=metadata.get("facility_name", ""),
                facility_address=metadata.get("facility_address", ""),
                appointment_type=metadata.get("appointment_type", "outpatient"),
                language=context.language,
                reminder_type=metadata.get("reminder_type", "24h"),
            )

        return await self.schedule(
            patient_name=metadata.get("patient_name", ""),
            nupi=metadata.get("nupi", ""),
            patient_phone=metadata.get("patient_phone", ""),
            reason=metadata.get("reason", user_message),
            district=metadata.get("district", "Lusaka"),
            province=metadata.get("province", "Lusaka"),
            preferred_date=metadata.get("preferred_date", ""),
            preferred_time=metadata.get("preferred_time", ""),
            preferred_provider=metadata.get("preferred_provider", ""),
            appointment_type=metadata.get("appointment_type", "outpatient"),
            language=context.language,
        )

    async def close(self) -> None:
        await self.appointment_tool.close()
        await super().close()
