from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import text as sa_text
    from src.backend.database import async_session_factory
    _has_sqlalchemy = True
except ImportError:
    _has_sqlalchemy = False

from src.backend.rag.knowledge_graph.entity_extractor import KnowledgeGraphExtractor
from src.backend.rag.knowledge_graph.graph_schema import HAS_SYMPTOM, TREATS, TREATS_SYMPTOM
from src.backend.rag.knowledge_graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class KnowledgeGraphSeeder:
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self.extractor = KnowledgeGraphExtractor()

    async def seed_from_knowledge_base(self) -> Dict[str, int]:
        if not _has_sqlalchemy:
            logger.warning("SQLAlchemy not available, skipping KB seed")
            return {"nodes": 0, "relationships": 0, "error": "sqlalchemy not installed"}
        if not self.client.is_connected:
            logger.warning("Neo4j not connected, skipping seed")
            return {"nodes": 0, "relationships": 0, "error": "not connected"}

        stats = {"nodes": 0, "relationships": 0}

        async with async_session_factory() as session:
            result = await session.execute(
                sa_text("SELECT category, subcategory, title, content, language FROM knowledge_base WHERE is_active = true")
            )
            rows = result.fetchall()

        for row in rows:
            category, subcategory, title, content, language = row
            entities = self.extractor.extract_from_kb_entry(
                category, subcategory, title, content, language or "en"
            )
            for entity in entities:
                try:
                    if entity["type"] == "node":
                        await self.client.create_node(entity["label"], entity["properties"])
                        stats["nodes"] += 1
                    elif entity["type"] == "relationship":
                        await self.client.create_relationship(
                            entity["from_label"],
                            entity["from_props"],
                            entity["to_label"],
                            entity["to_props"],
                            entity["rel_type"],
                        )
                        stats["relationships"] += 1
                except Exception as e:
                    logger.debug("Skipping entity: %s", e)

        logger.info("Knowledge graph seeded: %d nodes, %d relationships", stats["nodes"], stats["relationships"])
        return stats

    async def seed_manual_diseases(self) -> Dict[str, int]:
        if not self.client.is_connected:
            return {"nodes": 0}

        diseases = [
            {"name": "Malaria", "category": "Infectious"},
            {"name": "HIV/AIDS", "category": "Infectious"},
            {"name": "Tuberculosis", "category": "Infectious"},
            {"name": "Cholera", "category": "Infectious"},
            {"name": "Typhoid", "category": "Infectious"},
            {"name": "Pneumonia", "category": "Respiratory"},
            {"name": "Diabetes", "category": "NCD"},
            {"name": "Hypertension", "category": "NCD"},
            {"name": "Malnutrition", "category": "Nutritional"},
            {"name": "Anaemia", "category": "Haematological"},
            {"name": "Measles", "category": "Vaccine-preventable"},
            {"name": "Cervical Cancer", "category": "Oncology"},
            {"name": "Hepatitis B", "category": "Infectious"},
            {"name": "Meningitis", "category": "Infectious"},
            {"name": "COVID-19", "category": "Respiratory"},
        ]
        created = 0
        for d in diseases:
            try:
                await self.client.create_node("Disease", d)
                created += 1
            except Exception:
                pass
        return {"nodes": created}

    async def seed_manual_drugs(self) -> Dict[str, int]:
        if not self.client.is_connected:
            return {"nodes": 0}

        drugs = [
            {"name": "Artemether + Lumefantrine", "code": "ART001", "category": "Antimalarial"},
            {"name": "Artesunate", "code": "ART002", "category": "Antimalarial"},
            {"name": "TLD (Tenofovir/Lamivudine/Dolutegravir)", "code": "HIV001", "category": "Antiretroviral"},
            {"name": "Rifampicin/Isoniazid/Pyrazinamide/Ethambutol", "code": "TB001", "category": "Antitubercular"},
            {"name": "Metformin", "code": "END001", "category": "Antidiabetic"},
            {"name": "Paracetamol", "code": "CNS001", "category": "Analgesic"},
            {"name": "Amoxicillin", "code": "ABX001", "category": "Antibiotic"},
            {"name": "Ceftriaxone", "code": "ABX002", "category": "Antibiotic"},
            {"name": "Oral Rehydration Salts", "code": "GIS001", "category": "GI"},
            {"name": "Zinc Sulfate", "code": "VIT001", "category": "Supplement"},
        ]
        created = 0
        for d in drugs:
            try:
                await self.client.create_node("Drug", d)
                created += 1
            except Exception:
                pass
        return {"nodes": created}

    async def seed_manual_symptoms(self) -> Dict[str, int]:
        if not self.client.is_connected:
            return {"nodes": 0}
        symptoms_list = [
            "Fever", "Headache", "Chills", "Nausea", "Cough",
            "Weight loss", "Sweats", "Fatigue", "Shortness of breath",
            "Diarrhoea", "Vomiting",
        ]
        created = 0
        for s in symptoms_list:
            try:
                await self.client.create_node("Symptom", {"name": s})
                created += 1
            except Exception:
                pass
        return {"nodes": created}

    async def seed_relationships(self) -> Dict[str, int]:
        if not self.client.is_connected:
            return {"relationships": 0}

        rels = [
            ("Drug", {"name": "Artemether + Lumefantrine"}, "Disease", {"name": "Malaria"}, TREATS),
            ("Drug", {"name": "Artesunate"}, "Disease", {"name": "Malaria"}, TREATS),
            ("Drug", {"name": "TLD (Tenofovir/Lamivudine/Dolutegravir)"}, "Disease", {"name": "HIV/AIDS"}, TREATS),
            ("Drug", {"name": "Rifampicin/Isoniazid/Pyrazinamide/Ethambutol"}, "Disease", {"name": "Tuberculosis"}, TREATS),
            ("Drug", {"name": "Metformin"}, "Disease", {"name": "Diabetes"}, TREATS),
            ("Drug", {"name": "Paracetamol"}, "Symptom", {"name": "Fever"}, TREATS_SYMPTOM),
            ("Drug", {"name": "Paracetamol"}, "Symptom", {"name": "Headache"}, TREATS_SYMPTOM),
            ("Drug", {"name": "Oral Rehydration Salts"}, "Disease", {"name": "Cholera"}, TREATS),
            ("Drug", {"name": "Zinc Sulfate"}, "Disease", {"name": "Malnutrition"}, TREATS),
            ("Disease", {"name": "Malaria"}, "Symptom", {"name": "Fever"}, HAS_SYMPTOM),
            ("Disease", {"name": "Malaria"}, "Symptom", {"name": "Headache"}, HAS_SYMPTOM),
            ("Disease", {"name": "Malaria"}, "Symptom", {"name": "Chills"}, HAS_SYMPTOM),
            ("Disease", {"name": "Malaria"}, "Symptom", {"name": "Nausea"}, HAS_SYMPTOM),
            ("Disease", {"name": "Tuberculosis"}, "Symptom", {"name": "Cough"}, HAS_SYMPTOM),
            ("Disease", {"name": "Tuberculosis"}, "Symptom", {"name": "Fever"}, HAS_SYMPTOM),
            ("Disease", {"name": "Tuberculosis"}, "Symptom", {"name": "Weight loss"}, HAS_SYMPTOM),
            ("Disease", {"name": "Tuberculosis"}, "Symptom", {"name": "Sweats"}, HAS_SYMPTOM),
            ("Disease", {"name": "HIV/AIDS"}, "Symptom", {"name": "Fatigue"}, HAS_SYMPTOM),
            ("Disease", {"name": "HIV/AIDS"}, "Symptom", {"name": "Weight loss"}, HAS_SYMPTOM),
            ("Disease", {"name": "Pneumonia"}, "Symptom", {"name": "Cough"}, HAS_SYMPTOM),
            ("Disease", {"name": "Pneumonia"}, "Symptom", {"name": "Fever"}, HAS_SYMPTOM),
            ("Disease", {"name": "Pneumonia"}, "Symptom", {"name": "Shortness of breath"}, HAS_SYMPTOM),
            ("Disease", {"name": "Cholera"}, "Symptom", {"name": "Diarrhoea"}, HAS_SYMPTOM),
            ("Disease", {"name": "Cholera"}, "Symptom", {"name": "Vomiting"}, HAS_SYMPTOM),
            ("Disease", {"name": "Diabetes"}, "Symptom", {"name": "Fatigue"}, HAS_SYMPTOM),
            ("Disease", {"name": "Diabetes"}, "Symptom", {"name": "Weight loss"}, HAS_SYMPTOM),
        ]

        created = 0
        for from_label, from_props, to_label, to_props, rel_type in rels:
            try:
                await self.client.create_relationship(from_label, from_props, to_label, to_props, rel_type)
                created += 1
            except Exception as e:
                logger.debug("Skipping rel %s: %s", rel_type, e)

        return {"relationships": created}

    async def seed_all(self) -> Dict[str, int]:
        total = {"nodes": 0, "relationships": 0}
        for method in [
            self.seed_manual_diseases,
            self.seed_manual_drugs,
            self.seed_manual_symptoms,
            self.seed_from_knowledge_base,
            self.seed_relationships,
        ]:
            try:
                result = await method()
                total["nodes"] += result.get("nodes", 0)
                total["relationships"] += result.get("relationships", 0)
            except Exception as e:
                logger.error("Seeding step failed: %s", e)
        return total
