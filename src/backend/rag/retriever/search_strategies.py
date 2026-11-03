from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from src.backend.core.config.settings import settings
from src.backend.rag.embeddings.service import embed_query
from src.backend.rag.vector_store.pgvector_client import pgvector_store
from src.backend.rag.vector_store.qdrant_client import qdrant_store

logger = logging.getLogger("ubuntucare.rag.strategies")


class SearchStrategy(ABC):
    @abstractmethod
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        ...


class SimpleSemanticSearch(SearchStrategy):
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        query_vec = await embed_query(query)
        results = await pgvector_store.search(
            embedding=query_vec,
            limit=limit,
            filters=filters,
        )
        return results


class HybridSearch(SearchStrategy):
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        query_vec = await embed_query(query)
        pgv_results = await pgvector_store.search_hybrid(
            embedding=query_vec,
            query_text=query,
            limit=limit,
            filters=filters,
        )
        qdrant_results = qdrant_store.search(
            query_vector=query_vec,
            limit=limit,
            filters=filters,
        )
        seen = set()
        merged = []
        for doc in pgv_results + qdrant_results:
            key = doc.get("content", "")[:200]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged[:limit]


class MultiHopRetrieval(SearchStrategy):
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        query_vec = await embed_query(query)
        hop1 = await pgvector_store.search(embedding=query_vec, limit=limit, filters=filters)
        if not hop1:
            return hop1
        hop1_texts = [d.get("content", "") for d in hop1 if d.get("content")]
        if not hop1_texts:
            return hop1
        combined = f"{query} {' '.join(hop1_texts[:3])}"
        hop2_vec = await embed_query(combined)
        hop2 = await pgvector_store.search(embedding=hop2_vec, limit=limit, filters=filters)
        seen = set()
        merged = []
        for doc in hop1 + hop2:
            key = doc.get("content", "")[:200]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged[:limit]


class ParentChildRetrieval(SearchStrategy):
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        query_vec = await embed_query(query)
        child_results = await pgvector_store.search(
            embedding=query_vec,
            limit=limit * 2,
            filters=filters,
        )
        parent_ids = set()
        children_by_parent: dict[str, list[dict[str, Any]]] = {}
        for doc in child_results:
            parent_id = doc.get("metadata", {}).get("parent_id") if isinstance(doc.get("metadata"), dict) else None
            if not parent_id:
                parent_id = doc.get("metadata_", {}).get("parent_id") if isinstance(doc.get("metadata_"), dict) else None
            if parent_id:
                parent_ids.add(parent_id)
                children_by_parent.setdefault(parent_id, []).append(doc)
        parent_results = []
        for pid in parent_ids:
            parent = await pgvector_store.get_by_id(int(pid)) if pid and str(pid).isdigit() else None
            if parent:
                parent_results.append(parent)
        seen = set()
        merged = []
        for doc in parent_results + child_results:
            key = doc.get("content", "")[:200]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged[:limit]


class TemporalFilteredSearch(SearchStrategy):
    async def execute(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        query_vec = await embed_query(query)
        merged_filters = dict(filters) if filters else {}
        qdrant_results = qdrant_store.search(
            query_vector=query_vec,
            limit=limit,
            filters=merged_filters or None,
        )
        pgv_results = await pgvector_store.search(
            embedding=query_vec,
            limit=limit,
            filters=filters,
        )
        seen = set()
        merged = []
        for doc in qdrant_results + pgv_results:
            key = doc.get("content", "")[:200]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        merged.sort(
            key=lambda d: d.get("published_date", "") or "",
            reverse=True,
        )
        return merged[:limit]
