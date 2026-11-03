from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TriageLevel(str, Enum):
    EMERGENCY = "emergency"
    VERY_URGENT = "very_urgent"
    URGENT = "urgent"
    ROUTINE = "routine"
    MINOR = "minor"


class TriageColor(str, Enum):
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"


LEVEL_TO_COLOR = {
    TriageLevel.EMERGENCY: TriageColor.RED,
    TriageLevel.VERY_URGENT: TriageColor.ORANGE,
    TriageLevel.URGENT: TriageColor.YELLOW,
    TriageLevel.ROUTINE: TriageColor.GREEN,
    TriageLevel.MINOR: TriageColor.BLUE,
}

LEVEL_TO_RESPONSE_MINUTES = {
    TriageLevel.EMERGENCY: 0,
    TriageLevel.VERY_URGENT: 10,
    TriageLevel.URGENT: 60,
    TriageLevel.ROUTINE: 240,
    TriageLevel.MINOR: 480,
}


@dataclass
class VitalSigns:
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    respiratory_rate: Optional[float] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    avpu: str = "alert"
    capillary_refill: Optional[float] = None
    pain_score: Optional[int] = None

    @property
    def map_bp(self) -> Optional[float]:
        if self.systolic_bp is not None and self.diastolic_bp is not None:
            return self.diastolic_bp + (self.systolic_bp - self.diastolic_bp) / 3.0
        return None


@dataclass
class TriageResult:
    level: TriageLevel
    color: TriageColor
    score: float
    response_time_minutes: int
    rationale: List[str] = field(default_factory=list)
    recommended_referral: Optional[str] = None
    warning_flags: List[str] = field(default_factory=list)
    mews_score: Optional[float] = None
    sats_score: Optional[str] = None
    calculated_levels: Dict[str, Any] = field(default_factory=dict)

    @property
    def requires_immediate_care(self) -> bool:
        return self.level in (TriageLevel.EMERGENCY, TriageLevel.VERY_URGENT)


class SATriageScale:
    def __init__(self):
        self._emergency_conditions = [
            "airway obstruction", "no breathing", "agonal breathing",
            "severe respiratory distress", "shock", "cardiac arrest",
            "unconscious", "fitting", "severe haemorrhage",
            "hypoglycaemia", "meningitis signs", "severe dehydration",
        ]
        self._very_urgent_conditions = [
            "chest pain", "severe difficulty breathing", "burns >20%",
            "severe abdominal pain", "head injury", "fracture femur",
            "severe allergic reaction", "high fever with stiff neck",
            "vomiting blood", "passed blood", "diabetic ketoacidosis",
            "eclampsia", "antepartum haemorrhage", "cord prolapse",
        ]

    async def assess(
        self,
        vitals: VitalSigns,
        chief_complaint: str,
        age_years: float,
        is_pregnant: bool = False,
        mobility: str = "walking",
        additional_risk_factors: Optional[List[str]] = None,
    ) -> TriageResult:
        complaints_lower = chief_complaint.lower()
        rationale: List[str] = []
        warning_flags: List[str] = []
        calculated: Dict[str, Any] = {}

        if any(c in complaints_lower for c in self._emergency_conditions):
            rationale.append("Emergency condition identified from chief complaint")
            return TriageResult(
                level=TriageLevel.EMERGENCY,
                color=TriageColor.RED,
                score=1.0,
                response_time_minutes=0,
                rationale=rationale,
                warning_flags=["Immediate resuscitation required"],
                calculated_levels={"sats": "red", "basis": "emergency_condition"},
            )

        if any(c in complaints_lower for c in self._very_urgent_conditions):
            rationale.append("Very urgent condition identified from chief complaint")

        mews_result = await self._calculate_mews(vitals)
        calculated["mews"] = mews_result

        if mews_result["score"] >= 5:
            return TriageResult(
                level=TriageLevel.EMERGENCY,
                color=TriageColor.RED,
                score=1.0,
                response_time_minutes=0,
                rationale=[*rationale, f"MEWS score {mews_result['score']} indicates critical instability"],
                warning_flags=mews_result["flags"],
                mews_score=mews_result["score"],
                calculated_levels=calculated,
            )

        yellow_flags: List[str] = []
        orange_flags: List[str] = []

        if mobility == "stretcher" or "cannot walk" in complaints_lower:
            orange_flags.append("Patient requires stretcher/immobile")

        if vitals.systolic_bp is not None:
            if vitals.systolic_bp < 90:
                orange_flags.append(f"Severe hypotension (SBP: {vitals.systolic_bp})")
            elif vitals.systolic_bp < 100:
                yellow_flags.append(f"Mild hypotension (SBP: {vitals.systolic_bp})")
            elif vitals.systolic_bp > 180:
                orange_flags.append(f"Severe hypertension (SBP: {vitals.systolic_bp})")

        if vitals.heart_rate is not None:
            if vitals.heart_rate > 140:
                orange_flags.append(f"Severe tachycardia (HR: {vitals.heart_rate})")
            elif vitals.heart_rate > 120:
                yellow_flags.append(f"Moderate tachycardia (HR: {vitals.heart_rate})")
            elif vitals.heart_rate < 50:
                orange_flags.append(f"Severe bradycardia (HR: {vitals.heart_rate})")

        if vitals.respiratory_rate is not None:
            if vitals.respiratory_rate > 30:
                orange_flags.append(f"Severe tachypnoea (RR: {vitals.respiratory_rate})")
            elif vitals.respiratory_rate > 24:
                yellow_flags.append(f"Moderate tachypnoea (RR: {vitals.respiratory_rate})")
            elif vitals.respiratory_rate < 10:
                orange_flags.append(f"Severe bradypnoea (RR: {vitals.respiratory_rate})")

        if vitals.oxygen_saturation is not None:
            if vitals.oxygen_saturation < 90:
                orange_flags.append(f"Critical hypoxia (SpO2: {vitals.oxygen_saturation}%)")
            elif vitals.oxygen_saturation < 94:
                yellow_flags.append(f"Moderate hypoxia (SpO2: {vitals.oxygen_saturation}%)")

        if vitals.temperature is not None:
            if vitals.temperature > 41:
                orange_flags.append(f"Hyperpyrexia (Temp: {vitals.temperature}C)")
            elif vitals.temperature > 39:
                yellow_flags.append(f"High fever (Temp: {vitals.temperature}C)")
            elif vitals.temperature < 35:
                orange_flags.append(f"Severe hypothermia (Temp: {vitals.temperature}C)")

        if vitals.avpu.lower() in ("unresponsive", "pain"):
            orange_flags.append(f"AVPU: {vitals.avpu} - neurological impairment")
        elif vitals.avpu.lower() == "voice":
            yellow_flags.append(f"AVPU: {vitals.avpu}")

        if vitals.pain_score is not None and vitals.pain_score >= 8:
            orange_flags.append(f"Severe pain (score: {vitals.pain_score}/10)")
        elif vitals.pain_score is not None and vitals.pain_score >= 5:
            yellow_flags.append(f"Moderate pain (score: {vitals.pain_score}/10)")

        if is_pregnant:
            orange_flags.append("Pregnant patient - obstetric assessment needed")

        warning_flags.extend(orange_flags)
        warning_flags.extend(yellow_flags)

        if orange_flags:
            level = TriageLevel.VERY_URGENT
            score = 0.8
        elif yellow_flags:
            level = TriageLevel.URGENT
            score = 0.6
        else:
            level = TriageLevel.ROUTINE
            score = 0.3

        if mews_result["score"] >= 3:
            if level == TriageLevel.ROUTINE:
                level = TriageLevel.URGENT
                score = 0.6
            rationale.append(f"MEWS score {mews_result['score']} indicates clinical concern")

        color = LEVEL_TO_COLOR[level]
        response_time = LEVEL_TO_RESPONSE_MINUTES[level]

        return TriageResult(
            level=level,
            color=color,
            score=score,
            response_time_minutes=response_time,
            rationale=[*rationale, *orange_flags, *yellow_flags],
            warning_flags=warning_flags,
            mews_score=mews_result["score"],
            calculated_levels=calculated,
        )

    async def _calculate_mews(self, vitals: VitalSigns) -> Dict[str, Any]:
        score = 0
        flags: List[str] = []

        if vitals.systolic_bp is not None:
            if vitals.systolic_bp <= 70:
                score += 3
                flags.append("MEWS BP: Critical hypotension")
            elif vitals.systolic_bp <= 80:
                score += 2
                flags.append("MEWS BP: Severe hypotension")
            elif vitals.systolic_bp <= 100:
                score += 1
                flags.append("MEWS BP: Mild hypotension")
            elif vitals.systolic_bp >= 200:
                score += 2
                flags.append("MEWS BP: Severe hypertension")
            elif vitals.systolic_bp >= 180:
                score += 1
                flags.append("MEWS BP: Moderate hypertension")

        if vitals.heart_rate is not None:
            if vitals.heart_rate <= 40:
                score += 2
                flags.append("MEWS HR: Severe bradycardia")
            elif vitals.heart_rate <= 50:
                score += 1
            elif vitals.heart_rate <= 100:
                pass
            elif vitals.heart_rate <= 110:
                score += 1
            elif vitals.heart_rate <= 130:
                score += 2
            else:
                score += 3
                flags.append("MEWS HR: Severe tachycardia")

        if vitals.respiratory_rate is not None:
            if vitals.respiratory_rate <= 8:
                score += 2
                flags.append("MEWS RR: Severe bradypnoea")
            elif vitals.respiratory_rate <= 14:
                pass
            elif vitals.respiratory_rate <= 20:
                score += 1
            elif vitals.respiratory_rate <= 29:
                score += 2
            else:
                score += 3
                flags.append("MEWS RR: Severe tachypnoea")

        if vitals.temperature is not None:
            if vitals.temperature <= 35:
                score += 2
                flags.append("MEWS Temp: Severe hypothermia")
            elif vitals.temperature <= 36.5:
                score += 1
            elif vitals.temperature <= 37.5:
                pass
            elif vitals.temperature <= 38.5:
                score += 1
            else:
                score += 2
                flags.append("MEWS Temp: High fever")

        if vitals.avpu.lower() != "alert":
            avpu_score_map = {"voice": 1, "pain": 2, "unresponsive": 3}
            score += avpu_score_map.get(vitals.avpu.lower(), 3)
            flags.append(f"MEWS AVPU: {vitals.avpu}")

        return {"score": score, "flags": flags, "timestamp": datetime.utcnow().isoformat()}


class PediatricTriage:
    def __init__(self):
        self.paediatric_emergency_signs = [
            "not feeding well", "vomiting everything", "convulsions",
            "lethargic", "unconscious", "stridor", "severe chest indrawing",
            "oxygen saturation <90%", "grunting", "central cyanosis",
            "signs of shock", "petechial rash",
        ]

    async def assess(
        self,
        vitals: VitalSigns,
        chief_complaint: str,
        age_months: float,
        weight_kg: Optional[float] = None,
        muac_cm: Optional[float] = None,
    ) -> TriageResult:
        complaints_lower = chief_complaint.lower()
        rationale: List[str] = []
        warning_flags: List[str] = []

        if any(s in complaints_lower for s in self.paediatric_emergency_signs):
            return TriageResult(
                level=TriageLevel.EMERGENCY,
                color=TriageColor.RED,
                score=1.0,
                response_time_minutes=0,
                rationale=[f"Paediatric emergency sign identified: {chief_complaint}"],
                warning_flags=["Paediatric emergency - immediate assessment required"],
                calculated_levels={"basis": "paediatric_emergency_sign"},
            )

        if weight_kg is not None and muac_cm is not None:
            if muac_cm < 11.5:
                warning_flags.append(f"Severe acute malnutrition (MUAC: {muac_cm}cm)")
                rationale.append("Severe acute malnutrition detected")
            elif muac_cm < 12.5:
                warning_flags.append(f"Moderate acute malnutrition (MUAC: {muac_cm}cm)")

        sats = await SATriageScale().assess(vitals, chief_complaint, age_months / 12.0)
        if age_months < 3 and vitals.temperature and vitals.temperature > 38:
            sats.level = TriageLevel.VERY_URGENT
            sats.color = TriageColor.ORANGE
            sats.score = 0.8
            sats.rationale.append("Neonate <3 months with fever - high risk")

        sats.warning_flags.extend(warning_flags)
        sats.calculated_levels["paediatric"] = True
        return sats


class ObstetricTriage:
    def __init__(self):
        self.emergency_obstetric_signs = [
            "severe abdominal pain", "vaginal bleeding", "fits",
            "severe headache with visual disturbance", "epigastric pain",
            "no fetal movements", "water broken >12 hours", "cord prolapse",
            "maternal shock", "eclampsia", "antepartum haemorrhage",
            "postpartum haemorrhage", "severe pre-eclampsia",
        ]

    async def assess(
        self,
        vitals: VitalSigns,
        chief_complaint: str,
        gestational_weeks: Optional[float] = None,
        parity: Optional[int] = None,
        gravida: Optional[int] = None,
        is_postpartum: bool = False,
    ) -> TriageResult:
        complaints_lower = chief_complaint.lower()
        rationale: List[str] = []

        if any(s in complaints_lower for s in self.emergency_obstetric_signs):
            return TriageResult(
                level=TriageLevel.EMERGENCY,
                color=TriageColor.RED,
                score=1.0,
                response_time_minutes=0,
                rationale=[f"Obstetric emergency: {chief_complaint}"],
                warning_flags=["Obstetric emergency - immediate review by skilled birth attendant"],
                calculated_levels={"obstetric": True, "basis": "obstetric_emergency"},
            )

        sats = await SATriageScale().assess(vitals, chief_complaint, 30 if not is_postpartum else 30)
        sats.calculated_levels["obstetric"] = True

        if gestational_weeks and gestational_weeks >= 20:
            if vitals.systolic_bp and vitals.systolic_bp >= 140:
                sats.warning_flags.append(f"Possible pre-eclampsia (BP: {vitals.systolic_bp}/{vitals.diastolic_bp})")
                if sats.level == TriageLevel.ROUTINE:
                    sats.level = TriageLevel.URGENT
                    sats.color = TriageColor.YELLOW
                    sats.score = 0.6

        if is_postpartum and vitals.systolic_bp and vitals.systolic_bp < 90:
            sats.warning_flags.append("Postpartum hypotension - possible PPH")
            sats.level = TriageLevel.EMERGENCY
            sats.color = TriageColor.RED
            sats.score = 1.0

        return sats


class TriageScorer:
    def __init__(self):
        self.sats = SATriageScale()
        self.pediatric = PediatricTriage()
        self.obstetric = ObstetricTriage()

    async def score(
        self,
        vitals: VitalSigns,
        chief_complaint: str,
        age_years: float,
        is_pregnant: bool = False,
        is_postpartum: bool = False,
        gestational_weeks: Optional[float] = None,
        weight_kg: Optional[float] = None,
        muac_cm: Optional[float] = None,
        mobility: str = "walking",
        additional_risk_factors: Optional[List[str]] = None,
    ) -> TriageResult:
        if is_pregnant or is_postpartum:
            return await self.obstetric.assess(
                vitals=vitals,
                chief_complaint=chief_complaint,
                gestational_weeks=gestational_weeks,
                is_postpartum=is_postpartum,
            )

        if age_years < 16:
            age_months = age_years * 12
            return await self.pediatric.assess(
                vitals=vitals,
                chief_complaint=chief_complaint,
                age_months=age_months,
                weight_kg=weight_kg,
                muac_cm=muac_cm,
            )

        return await self.sats.assess(
            vitals=vitals,
            chief_complaint=chief_complaint,
            age_years=age_years,
            is_pregnant=is_pregnant,
            mobility=mobility,
            additional_risk_factors=additional_risk_factors,
        )

    async def determine_referral(self, result: TriageResult, facility_level: str) -> Optional[Dict[str, Any]]:
        level_to_referral = {
            TriageLevel.EMERGENCY: {
                "from": "clinic",
                "to": "district_hospital",
                "from_advanced": "tertiary_hospital",
            },
            TriageLevel.VERY_URGENT: {
                "from": "clinic",
                "to": "district_hospital",
            },
            TriageLevel.URGENT: {
                "from": "health_post",
                "to": "clinic",
            },
        }

        if result.level not in level_to_referral:
            return None

        referral_map = level_to_referral[result.level]
        if facility_level == "clinic" and result.level in (TriageLevel.EMERGENCY, TriageLevel.VERY_URGENT):
            return {
                "recommended": True,
                "from": facility_level,
                "to": referral_map["to"],
                "urgency": "emergency" if result.level == TriageLevel.EMERGENCY else "urgent",
                "reason": f"Patient triaged as {result.level.value} - requires higher level of care",
                "mode_of_transport": "emergency_ambulance" if result.level == TriageLevel.EMERGENCY else "referral_ambulance",
            }

        if facility_level == "health_post" and result.level == TriageLevel.URGENT:
            return {
                "recommended": True,
                "from": facility_level,
                "to": referral_map["to"],
                "urgency": "urgent",
                "reason": f"Patient triaged as {result.level.value} - requires clinical assessment",
                "mode_of_transport": "clinic_referral",
            }

        return {"recommended": False}
