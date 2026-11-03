from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from src.backend.core.config.settings import settings
from src.backend.ml.models.guardrails.phi_detection import detect_phi
from src.backend.ml.models.guardrails.policies import (
    AgentType,
    GuardrailPolicy,
    HarmfulContentCategory,
    MedicalContentCategory,
    get_policy,
)

logger = logging.getLogger("ubuntucare.ml.guardrails")

_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|above)\s+(instructions|prompts|directions)",
    r"(?i)forget\s+(all\s+)?(previous|above)\s+(instructions|prompts|directions)",
    r"(?i)you\s+are\s+(now|free|not\s+bound)",
    r"(?i)new\s+instruction[s]?[\s:]*",
    r"(?i)override\s+(instructions|prompts|commands)",
    r"(?i)system\s+prompt[\s:]*",
    r"(?i)act\s+as\s+(if\s+)?(you\s+are|your\s+are)",
    r"(?i)do\s+not\s+(follow|obey|adhere)",
    r"(?i)you\s+must\s+(ignore|disregard|bypass)",
    r"(?i)change\s+your\s+(behavior|role|persona)",
]

_JAILBREAK_PATTERNS = [
    r"(?i)DAN\b",
    r"(?i)do\s+anything\s+now",
    r"(?i)no\s+(restrictions|limits|boundaries|filter)",
    r"(?i)you\s+are\s+uncensored",
    r"(?i)remove\s+(all\s+)?(safety|filtering|restrictions)",
    r"(?i)hypothetical[\s\S]{0,50}(harm|kill|die|weapon)",
    r"(?i)roleplay[\s\S]{0,50}(harm|kill|weapon|drug)",
]

_HALLUCINATION_PATTERNS = [
    r"\b\d{4}\s+study\s+(found|showed|demonstrated)\b",
    r"\baccording\s+to\s+(research|studies|clinical\s+trials)\b",
]


class GuardrailsService:
    def __init__(self) -> None:
        self._llama_guard_model: Any = None

    async def _load_llama_guard(self) -> None:
        if self._llama_guard_model is not None:
            return
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            model_name = settings.GUARDRAILS_MODEL
            self._llama_guard_model = AutoModelForSequenceClassification.from_pretrained(
                model_name, device_map="auto"
            )
            self._llama_guard_tokenizer = AutoTokenizer.from_pretrained(model_name)
            logger.info("Loaded Llama Guard model: %s", model_name)
        except Exception as exc:
            logger.warning("Llama Guard load failed: %s", exc)
            self._llama_guard_model = False

    def _check_prompt_injection(self, text: str) -> dict[str, Any]:
        for pattern in _INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"detected": True, "pattern": pattern, "match": match.group(0)}
        return {"detected": False}

    def _check_jailbreak(self, text: str) -> dict[str, Any]:
        for pattern in _JAILBREAK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"detected": True, "pattern": pattern, "match": match.group(0)}
        return {"detected": False}

    async def check_injection(self, text: str) -> dict[str, Any]:
        injection = self._check_prompt_injection(text)
        jailbreak = self._check_jailbreak(text)
        return {
            "prompt_injection": injection,
            "jailbreak": jailbreak,
            "safe": not injection["detected"] and not jailbreak["detected"],
        }

    async def check_phi(self, text: str, redaction_strategy: str = "mask") -> dict[str, Any]:
        result = detect_phi(text, redaction_strategy=redaction_strategy)
        phi_result = result.to_dict()
        return {
            "phi_detected": result.detected,
            "findings": result.findings,
            "risk_score": result.risk_score,
            "redacted_text": result.redacted_text,
            "safe": not result.detected,
        }

    async def check_content_safety(self, text: str) -> dict[str, Any]:
        categories_found: list[str] = []
        harmful_categories: list[str] = []

        category_keywords: dict[MedicalContentCategory, list[str]] = {
            MedicalContentCategory.DIAGNOSIS: ["diagnosis", "diagnose", "symptoms", "condition"],
            MedicalContentCategory.TREATMENT: ["treatment", "therapy", "management", "regimen"],
            MedicalContentCategory.MEDICATION: ["medication", "drug", "prescription", "dosage", "dose"],
            MedicalContentCategory.SURGERY: ["surgery", "surgical", "operation", "procedure"],
            MedicalContentCategory.MATERNAL: ["pregnancy", "maternal", "antenatal", "postnatal", "obstetric"],
            MedicalContentCategory.CHILD: ["child", "infant", "pediatric", "neonatal", "under five"],
            MedicalContentCategory.MENTAL: ["mental", "depression", "anxiety", "psychiatric", "counseling"],
            MedicalContentCategory.NUTRITION: ["nutrition", "diet", "malnutrition", "feeding", "breastfeeding"],
            MedicalContentCategory.IMMUNIZATION: ["vaccine", "immunization", "vaccination", "shots"],
            MedicalContentCategory.INFECTIOUS_DISEASE: ["malaria", "tb", "tuberculosis", "hiv", "cholera", "typhoid"],
            MedicalContentCategory.NCD: ["hypertension", "diabetes", "cancer", "cardiovascular", "ncd"],
            MedicalContentCategory.EMERGENCY: ["emergency", "urgent", "severe", "critical", "life-threatening"],
            MedicalContentCategory.PUBLIC_HEALTH: ["outbreak", "surveillance", "epidemic", "public health"],
        }
        text_lower = text.lower()
        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories_found.append(category.value)

        harmful_keywords: dict[HarmfulContentCategory, list[str]] = {
            HarmfulContentCategory.MEDICAL_MISINFORMATION: [
                "vaccines cause", "cure for", "miracle cure", "alternative medicine",
            ],
            HarmfulContentCategory.DANGEROUS_MEDICAL_ADVICE: [
                "stop taking", "discontinue medication", "ignore doctor", "self-medicate",
            ],
            HarmfulContentCategory.VIOLENCE: ["kill", "hurt", "attack", "weapon"],
            HarmfulContentCategory.SELF_HARM: ["suicide", "self-harm", "hurt myself"],
        }
        for hc, keywords in harmful_keywords.items():
            if any(kw in text_lower for kw in keywords):
                harmful_categories.append(hc.value)

        return {
            "medical_categories": categories_found,
            "harmful_categories": harmful_categories,
            "safe": len(harmful_categories) == 0,
        }

    async def check_topic(
        self, text: str, policy: GuardrailPolicy
    ) -> dict[str, Any]:
        if not policy.topic_control_enabled:
            return {"allowed": True}
        text_lower = text.lower()
        for topic in policy.blocked_topics:
            if topic.replace("_", " ") in text_lower:
                return {"allowed": False, "blocked_topic": topic}
        return {"allowed": True}

    async def check_hallucination(
        self, text: str, rag_context: Optional[str] = None
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        for pattern in _HALLUCINATION_PATTERNS:
            for match in re.finditer(pattern, text):
                findings.append({
                    "pattern": pattern,
                    "match": match.group(0),
                    "position": match.start(),
                })
        if rag_context and findings:
            verified = []
            for f in findings:
                claim = f["match"]
                if rag_context and claim[:50] in rag_context:
                    f["verified"] = True
                else:
                    f["verified"] = False
                verified.append(f)
            findings = verified
        return {
            "potential_hallucinations": len(findings),
            "findings": findings,
            "safe": len(findings) == 0,
        }

    async def check_all(
        self,
        text: str,
        agent_type: AgentType = AgentType.TRIAGE,
        rag_context: Optional[str] = None,
    ) -> dict[str, Any]:
        policy = get_policy(agent_type)
        results: dict[str, Any] = {
            "agent_type": agent_type.value,
            "input_length": len(text),
        }

        results["phi"] = await self.check_phi(text, policy.phi_redaction_strategy) if policy.phi_detection_enabled else {"safe": True, "phi_detected": False}
        text_to_check = results["phi"].get("redacted_text", text)

        results["injection"] = await self.check_injection(text_to_check) if policy.prompt_injection_detection else {"safe": True}
        results["content_safety"] = await self.check_content_safety(text_to_check) if policy.content_safety_filter else {"safe": True}
        results["topic"] = await self.check_topic(text_to_check, policy) if policy.topic_control_enabled else {"allowed": True}
        results["hallucination"] = await self.check_hallucination(text, rag_context) if policy.hallucination_detection else {"safe": True}

        safe = all([
            not results["phi"]["phi_detected"],
            results["injection"]["safe"],
            results["content_safety"]["safe"],
            results["topic"].get("allowed", True),
            results["hallucination"]["safe"],
        ])
        results["safe"] = safe
        if not safe:
            reasons = []
            if results["phi"]["phi_detected"]:
                reasons.append("PHI detected")
            if not results["injection"]["safe"]:
                reasons.append("Prompt injection detected")
            if not results["content_safety"]["safe"]:
                reasons.append("Content safety violation")
            if not results["topic"].get("allowed", True):
                reasons.append(f"Topic blocked: {results['topic'].get('blocked_topic')}")
            if not results["hallucination"]["safe"]:
                reasons.append("Potential hallucinations detected")
            results["reasons"] = reasons

        return results

    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "phi_detection": True,
            "injection_detection": True,
            "content_safety": True,
            "policies": [at.value for at in AgentType],
        }


guardrails_service = GuardrailsService()
