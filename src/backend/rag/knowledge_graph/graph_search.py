from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.backend.rag.knowledge_graph.neo4j_client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


class GraphSearchTool:
    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or get_neo4j_client()

    async def search_drugs_for_disease(self, disease_name: str) -> List[Dict[str, Any]]:
        related = await self.client.get_related(
            "Disease", {"name": disease_name}, rel_types=["TREATS"], direction="in"
        )
        return [{"drug_name": r["related"].get("name", ""),
                 "category": r["related"].get("category", ""),
                 "code": r["related"].get("code", "")} for r in related]

    async def search_diseases_for_drug(self, drug_name: str) -> List[Dict[str, Any]]:
        related = await self.client.get_related(
            "Drug", {"name": drug_name}, rel_types=["TREATS"], direction="out"
        )
        return [{"disease_name": r["related"].get("name", ""),
                 "category": r["related"].get("category", "")} for r in related]

    async def search_symptoms_for_disease(self, disease_name: str) -> List[Dict[str, Any]]:
        related = await self.client.get_related(
            "Disease", {"name": disease_name}, rel_types=["HAS_SYMPTOM"], direction="out"
        )
        return [{"symptom": r["related"].get("name", "")} for r in related]

    async def search_diseases_for_symptom(self, symptom: str) -> List[Dict[str, Any]]:
        related = await self.client.get_related(
            "Symptom", {"name": symptom}, rel_types=["HAS_SYMPTOM"], direction="in"
        )
        return [{"disease_name": r["related"].get("name", ""),
                 "category": r["related"].get("category", "")} for r in related]

    async def search_vaccines_for_disease(self, disease_name: str) -> List[Dict[str, Any]]:
        related = await self.client.get_related(
            "Disease", {"name": disease_name}, rel_types=["ADMINISTERED_FOR", "PREVENTS"], direction="in"
        )
        return [{"vaccine_name": r["related"].get("name", ""),
                 "code": r["related"].get("code", "")} for r in related]

    async def find_path(
        self, from_label: str, from_value: str, to_label: str, to_value: str
    ) -> List[Dict[str, Any]]:
        return await self.client.find_path(
            from_label, {"name": from_value},
            to_label, {"name": to_value},
        )

    async def get_related(
        self,
        label: str,
        name: str,
        rel_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        return await self.client.get_related(label, {"name": name}, rel_types, limit=limit)

    async def explain_relationship(
        self,
        drug_name: str,
        disease_name: str,
    ) -> Dict[str, Any]:
        result = await self.client.find_path(
            "Drug", {"name": drug_name},
            "Disease", {"name": disease_name},
        )
        if result:
            row = result[0] if isinstance(result, list) else result
            return {"nodes": row.get("nodes", []), "relationships": row.get("rels", row.get("relationships", []))}
        return {"nodes": [], "relationships": [], "error": "No path found"}

    async def search(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        all_results = []
        for label in ["Drug", "Disease", "Symptom", "Vaccine", "Guideline", "Protocol", "Facility"]:
            try:
                results = await self.client.search_similar(label, "name", query_text, limit)
                all_results.extend(results)
            except Exception:
                pass
            try:
                results = await self.client.search_similar(label, "title", query_text, limit)
                all_results.extend(results)
            except Exception:
                pass
            try:
                results = await self.client.search_similar(label, "code", query_text, limit)
                all_results.extend(results)
            except Exception:
                pass
        return all_results[:limit]

    async def get_stats(self) -> Dict[str, Any]:
        return await self.client.get_stats()
