from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("ubuntucare.ml.guardrails.phi")

PHI_PATTERNS: dict[str, str] = {
    "nrc_number": r"\b\d{6}/\d{2}/\d\b",
    "nhima_number": r"\b(NHIMA|NHI)[-\s]?\d{6,10}\b",
    "nupi_number": r"\b\d{10,12}\b",
    "zambia_phone": r"(\+260|0)(9[5-8]|7[5-9]|6[5-9])\d{7}",
    "zambia_passport": r"\b[A-Z]{2}\d{6,8}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "patient_id": r"\b(PAT|PT|ZMH|PATIENT)[-/]?\d{5,10}\b",
    "ssn_usa": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

PHI_CONTEXT_KEYWORDS = [
    "diagnosis", "patient", "treatment", "prescription", "medication",
    "symptoms", "complaint", "history", "examination", "lab", "test",
    "result", "admission", "discharge", "referral", "consultation",
    "name", "address", "phone", "contact", "next of kin", "relative",
    "national registration", "nrc", "nhima", "nupi", "insurance",
]


@dataclass
class PHIResult:
    detected: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0
    redacted_text: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "findings": self.findings,
            "risk_score": self.risk_score,
            "redacted_text": self.redacted_text,
        }


REDACTION_STRATEGIES = {
    "mask": lambda m: f"[REDACTED_{m.group(0)[0:2]}]",
    "hash": lambda m: f"[HASH_{abs(hash(m.group(0))) % 10**8:08d}]",
    "remove": lambda m: "",
    "partial": lambda m: m.group(0)[:2] + "****" + m.group(0)[-2:] if len(m.group(0)) > 4 else "[REDACTED]",
}


def detect_phi(
    text: str,
    context_aware: bool = True,
    redaction_strategy: str = "mask",
) -> PHIResult:
    findings: list[dict[str, Any]] = []
    risk_score = 0.0
    for phi_type, pattern in PHI_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matched_text = match.group(0)
            if phi_type == "zambia_phone" and len(re.sub(r"\D", "", matched_text)) < 9:
                continue
            finding = {
                "type": phi_type,
                "match": matched_text,
                "start": match.start(),
                "end": match.end(),
                "confidence": _phi_confidence(phi_type, matched_text),
            }
            findings.append(finding)
            risk_score += finding["confidence"]

    phi_detected = len(findings) > 0
    if context_aware and phi_detected:
        risk_score = _context_risk_adjust(text, risk_score)

    redacted = None
    if phi_detected and redaction_strategy:
        redacted = _redact_text(text, findings, redaction_strategy)

    return PHIResult(
        detected=phi_detected,
        findings=findings,
        risk_score=min(risk_score / 10.0, 1.0),
        redacted_text=redacted,
    )


def _phi_confidence(phi_type: str, match: str) -> float:
    confidence_map: dict[str, float] = {
        "nrc_number": 0.95,
        "nhima_number": 0.90,
        "nupi_number": 0.80,
        "zambia_phone": 0.85,
        "zambia_passport": 0.80,
        "email": 0.70,
        "patient_id": 0.75,
        "ssn_usa": 0.95,
        "credit_card": 0.95,
        "ip_address": 0.60,
    }
    base = confidence_map.get(phi_type, 0.5)
    if len(match) > 20:
        base *= 1.1
    return min(base, 1.0)


def _context_risk_adjust(text: str, risk_score: float) -> float:
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in PHI_CONTEXT_KEYWORDS if kw in text_lower)
    if keyword_hits > 2:
        risk_score *= min(1.0 + (keyword_hits * 0.1), 2.0)
    return risk_score


def _redact_text(
    text: str,
    findings: list[dict[str, Any]],
    strategy: str = "mask",
) -> str:
    redactor = REDACTION_STRATEGIES.get(strategy, REDACTION_STRATEGIES["mask"])
    sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
    result = text
    for finding in sorted_findings:
        pattern = re.escape(finding["match"])
        try:
            result = re.sub(pattern, redactor, result, count=1)
        except re.error:
            result = result[: finding["start"]] + redactor(re.match(".", "x")) + result[finding["end"] :]
    return result


def detect_phi_presidio(text: str) -> PHIResult:
    try:
        from presidio_analyzer import AnalyzerEngine
        analyzer = AnalyzerEngine()
        results = analyzer.analyze(text=text, language="en")
        findings: list[dict[str, Any]] = []
        for result in results:
            findings.append({
                "type": result.entity_type,
                "match": text[result.start : result.end],
                "start": result.start,
                "end": result.end,
                "confidence": result.score,
            })
        phi_detected = len(findings) > 0
        risk_score = sum(f["confidence"] for f in findings) / 10.0 if findings else 0.0
        return PHIResult(
            detected=phi_detected,
            findings=findings,
            risk_score=min(risk_score, 1.0),
        )
    except ImportError:
        logger.warning("Presidio not available, using regex PHI detection")
        return detect_phi(text)


def batch_detect_phi(texts: list[str]) -> list[PHIResult]:
    return [detect_phi(t) for t in texts]
