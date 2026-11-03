from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    TRIAGE = "triage"
    CLINICAL_DOCUMENTATION = "clinical_documentation"
    MEDICAL_RESEARCH = "medical_research"
    APPOINTMENT = "appointment"
    PATIENT_SUPPORT = "patient_support"
    ADMIN = "admin"
    PUBLIC_HEALTH = "public_health"
    GENERAL = "general"


class ResponseFormatStyle(str, Enum):
    NARRATIVE = "narrative"
    BULLETED = "bulleted"
    STRUCTURED = "structured"
    CONVERSATIONAL = "conversational"
    EMPATHETIC = "empathetic"


@dataclass
class FormattedSection:
    heading: str = ""
    body: str = ""
    style: str = "paragraph"
    items: List[str] = field(default_factory=list)


@dataclass
class FormattedResponse:
    text: str
    sections: List[FormattedSection] = field(default_factory=list)
    style: ResponseFormatStyle = ResponseFormatStyle.NARRATIVE
    agent_type: AgentType = AgentType.GENERAL
    confidence: Optional[float] = None
    html: str = ""


def detect_agent_type(content: str, agent_name: Optional[str] = None) -> AgentType:
    if agent_name:
        name_map = {
            "triage": AgentType.TRIAGE,
            "clinical_documentation": AgentType.CLINICAL_DOCUMENTATION,
            "medical_research": AgentType.MEDICAL_RESEARCH,
            "appointment": AgentType.APPOINTMENT,
            "patient_support": AgentType.PATIENT_SUPPORT,
            "admin": AgentType.ADMIN,
            "public_health": AgentType.PUBLIC_HEALTH,
        }
        for key, agent_type in name_map.items():
            if key in agent_name.lower():
                return agent_type

    content_lower = content.lower()
    if any(w in content_lower for w in ["analytics report", "kpi", "key performance", "bed occupancy"]):
        return AgentType.ADMIN
    if any(w in content_lower for w in ["triage", "urgency", "symptom", "chief complaint"]):
        return AgentType.TRIAGE
    if any(w in content_lower for w in ["soap", "subjective", "objective", "assessment", "plan"]):
        return AgentType.CLINICAL_DOCUMENTATION
    if any(w in content_lower for w in ["appointment", "scheduled", "reschedule"]):
        return AgentType.APPOINTMENT
    if any(w in content_lower for w in ["faq", "health education", "medication reminder"]):
        return AgentType.PATIENT_SUPPORT
    if any(w in content_lower for w in ["surveillance", "outbreak", "vaccination coverage", "disease trend"]):
        return AgentType.PUBLIC_HEALTH
    if any(w in content_lower for w in ["research", "evidence", "guideline", "clinical trial"]):
        return AgentType.MEDICAL_RESEARCH
    return AgentType.GENERAL


def _extract_confidence(content: str) -> Optional[float]:
    m = re.search(r'\*\*Confidence:\*\*\s*\[?([\d.]+)]?', content)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _strip_confidence_line(content: str) -> str:
    return re.sub(r'\n?\*\*Confidence:\*\*\s*\[?[\d.]+]?\s*', '', content).strip()


def _unescape_bold(text: str) -> str:
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text)


def _to_plain(text: str) -> str:
    text = _unescape_bold(text)
    text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _parse_sections(text: str) -> List[FormattedSection]:
    sections: List[FormattedSection] = []
    pattern = r'\*\*(.+?):\*\*\s*([\s\S]*?)(?=\n\*\*|\Z)'
    matches = list(re.finditer(pattern, text))
    if not matches:
        sections.append(FormattedSection(body=_to_plain(text)))
        return sections
    for match in matches:
        heading = match.group(1).strip()
        body = match.group(2).strip()
        items = []
        for line in body.split('\n'):
            stripped = line.strip()
            if stripped.startswith('-') or stripped.startswith('*'):
                items.append(stripped.lstrip('-* ').strip())
            elif stripped.startswith('•'):
                items.append(stripped.lstrip('• ').strip())
        clean_body = re.sub(r'^[-*•]\s+', '', body, flags=re.MULTILINE).strip()
        sections.append(FormattedSection(
            heading=heading,
            body=_to_plain(clean_body),
            items=items,
            style="bulleted" if items else "paragraph",
        ))
    return sections


def _build_html(sections: List[FormattedSection]) -> str:
    parts: List[str] = []
    for sec in sections:
        if sec.heading:
            parts.append(f"<h4>{html.escape(sec.heading)}</h4>")
        if sec.items:
            parts.append("<ul>")
            for item in sec.items:
                parts.append(f"<li>{html.escape(item)}</li>")
            parts.append("</ul>")
        elif sec.body:
            parts.append(f"<p>{html.escape(sec.body)}</p>")
    return "\n".join(parts)


FORMATTERS: Dict[AgentType, Dict[str, Any]] = {
    AgentType.TRIAGE: {
        "style": ResponseFormatStyle.STRUCTURED,
        "icon_map": {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"},
    },
    AgentType.CLINICAL_DOCUMENTATION: {"style": ResponseFormatStyle.NARRATIVE},
    AgentType.MEDICAL_RESEARCH: {"style": ResponseFormatStyle.STRUCTURED},
    AgentType.APPOINTMENT: {"style": ResponseFormatStyle.CONVERSATIONAL},
    AgentType.PATIENT_SUPPORT: {"style": ResponseFormatStyle.EMPATHETIC},
    AgentType.ADMIN: {"style": ResponseFormatStyle.STRUCTURED},
    AgentType.PUBLIC_HEALTH: {"style": ResponseFormatStyle.STRUCTURED},
    AgentType.GENERAL: {"style": ResponseFormatStyle.NARRATIVE},
}


def format_response(content: str, agent_name: Optional[str] = None) -> FormattedResponse:
    if not content or not content.strip():
        return FormattedResponse(text=content or "", html="")

    agent_type = detect_agent_type(content, agent_name)
    config = FORMATTERS.get(agent_type, FORMATTERS[AgentType.GENERAL])
    style = config["style"]
    confidence = _extract_confidence(content)
    cleaned = _strip_confidence_line(content)

    try:
        sections = _parse_sections(cleaned)
        plain_text = "\n\n".join(
            f"{s.heading}: {s.body}" if s.heading else s.body
            for s in sections
        )
        html_output = _build_html(sections)

        return FormattedResponse(
            text=plain_text,
            sections=sections,
            style=style,
            agent_type=agent_type,
            confidence=confidence,
            html=html_output,
        )
    except Exception as e:
        logger.warning("Response formatting failed for %s: %s", agent_type, e)
        fallback = _to_plain(cleaned)
        return FormattedResponse(
            text=fallback,
            style=style,
            agent_type=agent_type,
            confidence=confidence,
            html=f"<p>{html.escape(fallback)}</p>",
        )
