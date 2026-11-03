from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.backend.rag.knowledge_graph.graph_schema import (
    ADMINISTERED_FOR,
    GUIDED_BY,
    HAS_SYMPTOM,
    PREVENTS,
    TREATS,
    TREATS_SYMPTOM,
)

logger = logging.getLogger(__name__)


def _extract_medication_entities(
    title: str, content: str, category: str, subcategory: Optional[str]
) -> List[Tuple[str, str, Dict[str, Any]]]:
    entities: List[Tuple[str, str, Dict[str, Any]]] = []
    drug_name = title.strip()
    entities.append(("Drug", {"name": drug_name, "code": category, "category": subcategory or category}))
    diseases = re.findall(r"(malaria|HIV|TB|tuberculosis|hypertension|diabetes|pneumonia|cholera|typhoid|dysentery|measles|cancer|anaemia|malnutrition)", content, re.IGNORECASE)
    seen_diseases = set()
    for d in diseases:
        d_normalized = d.lower().capitalize()
        if d_normalized not in seen_diseases:
            seen_diseases.add(d_normalized)
            entities.append(("Disease", {"name": d_normalized}))
            entities.append(("_rel", "Drug", "Disease", TREATS, {"from": {"name": drug_name}, "to": {"name": d_normalized}}))
    symptoms = re.findall(r"(fever|cough|headache|nausea|vomiting|diarrhoea|pain|rash|fatigue|dizziness|chills|sweats|weight loss|shortness of breath)", content, re.IGNORECASE)
    seen_symptoms = set()
    for s in symptoms:
        s_normalized = s.lower().strip().capitalize()
        if s_normalized not in seen_symptoms:
            seen_symptoms.add(s_normalized)
            entities.append(("Symptom", {"name": s_normalized}))
            entities.append(("_rel", "Drug", "Symptom", TREATS_SYMPTOM, {"from": {"name": drug_name}, "to": {"name": s_normalized}}))
    return entities


def _extract_disease_entities(
    title: str, content: str, category: str
) -> List[Tuple[str, str, Dict[str, Any]]]:
    entities: List[Tuple[str, str, Dict[str, Any]]] = []
    disease_name = title.strip()
    entities.append(("Disease", {"name": disease_name, "category": category}))
    symptoms = re.findall(r"(fever|cough|headache|nausea|vomiting|diarrhoea|pain|rash|fatigue|dizziness|chills|sweats|weight loss|shortness of breath|jaundice|anaemia|convulsions)", content, re.IGNORECASE)
    seen_symptoms = set()
    for s in symptoms:
        s_normalized = s.lower().strip().capitalize()
        if s_normalized not in seen_symptoms:
            seen_symptoms.add(s_normalized)
            entities.append(("Symptom", {"name": s_normalized}))
            entities.append(("_rel", "Disease", "Symptom", HAS_SYMPTOM, {"from": {"name": disease_name}, "to": {"name": s_normalized}}))
    drugs = re.findall(r"(Artemether|Lumefantrine|artesunate|quinine|ACT|Coartem|TLD|Tenofovir|Lamivudine|Dolutegravir|Rifampicin|Isoniazid|Pyrazinamide|Ethambutol|Metformin|Paracetamol|amoxicillin|ceftriaxone)", content, re.IGNORECASE)
    seen_drugs = set()
    for drug in drugs:
        drug_normalized = drug.strip().capitalize()
        if drug_normalized not in seen_drugs:
            seen_drugs.add(drug_normalized)
            entities.append(("Drug", {"name": drug_normalized}))
            entities.append(("_rel", "Drug", "Disease", TREATS, {"from": {"name": drug_normalized}, "to": {"name": disease_name}}))
    return entities


def _extract_vaccine_entities(
    title: str, content: str
) -> List[Tuple[str, str, Dict[str, Any]]]:
    entities: List[Tuple[str, str, Dict[str, Any]]] = []
    vaccine_name = title.strip()
    entities.append(("Vaccine", {"name": vaccine_name, "code": vaccine_name[:5].upper()}))
    diseases = re.findall(r"(tuberculosis|polio|pneumonia|rotavirus|measles|rubella|diphtheria|tetanus|pertussis|Hepatitis|HPV|cervical cancer|cholera|typhoid|meningitis|yellow fever)", content, re.IGNORECASE)
    seen = set()
    for d in diseases:
        d_normalized = d.lower().strip().capitalize()
        if d_normalized not in seen:
            seen.add(d_normalized)
            entities.append(("Disease", {"name": d_normalized}))
            entities.append(("_rel", "Vaccine", "Disease", ADMINISTERED_FOR, {"from": {"name": vaccine_name}, "to": {"name": d_normalized}}))
            entities.append(("_rel", "Vaccine", "Disease", PREVENTS, {"from": {"name": vaccine_name}, "to": {"name": d_normalized}}))
    return entities


def _extract_guideline_entities(
    title: str, content: str, subcategory: Optional[str]
) -> List[Tuple[str, str, Dict[str, Any]]]:
    entities: List[Tuple[str, str, Dict[str, Any]]] = []
    guideline_title = title.strip()
    source = "WHO" if "WHO" in title else "Zambia MoH"
    entities.append(("Guideline", {"title": guideline_title, "source": source, "language": "en"}))
    conditions = re.findall(r"(malaria|HIV|TB|tuberculosis|hypertension|diabetes|pneumonia|cholera|typhoid|malnutrition|HIV/AIDS|TB/HIV)", content, re.IGNORECASE)
    seen = set()
    for c in conditions:
        c_normalized = c.lower().strip().capitalize()
        if c_normalized not in seen:
            seen.add(c_normalized)
            entities.append(("Disease", {"name": c_normalized}))
            entities.append(("_rel", "Guideline", "Disease", GUIDED_BY, {"from": {"title": guideline_title}, "to": {"name": c_normalized}}))
    return entities


def extract_entities_from_kb_entry(
    category: str,
    subcategory: Optional[str],
    title: str,
    content: str,
    language: str = "en",
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    cat_lower = category.lower().strip()
    try:
        if cat_lower in ("medication", "drug", "pharmacy"):
            raw = _extract_medication_entities(title, content, category, subcategory)
        elif cat_lower in ("disease", "condition", "public_health"):
            raw = _extract_disease_entities(title, content, category)
        elif cat_lower in ("immunization", "vaccine"):
            raw = _extract_vaccine_entities(title, content)
        elif cat_lower in ("guideline", "protocol"):
            raw = _extract_guideline_entities(title, content, subcategory)
        else:
            return result
        for item in raw:
            if item[0] == "_rel":
                result.append({
                    "type": "relationship",
                    "from_label": item[1],
                    "to_label": item[2],
                    "rel_type": item[3],
                    "from_props": item[4]["from"],
                    "to_props": item[4]["to"],
                })
            else:
                result.append({
                    "type": "node",
                    "label": item[0],
                    "properties": item[1],
                })
    except Exception as e:
        logger.warning("Entity extraction failed for '%s': %s", title, e)
    return result


class KnowledgeGraphExtractor:
    def extract_from_kb_entry(
        self,
        category: str,
        subcategory: Optional[str],
        title: str,
        content: str,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        return extract_entities_from_kb_entry(category, subcategory, title, content, language)
