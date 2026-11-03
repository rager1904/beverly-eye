from __future__ import annotations

import logging
from typing import Any, Optional

from src.backend.core.config.settings import settings
from src.backend.rag.embeddings.service import embed_query, embed_texts
from src.backend.rag.retriever.search_strategies import (
    SearchStrategy,
    SimpleSemanticSearch,
    HybridSearch,
    MultiHopRetrieval,
    ParentChildRetrieval,
    TemporalFilteredSearch,
)
from src.backend.rag.vector_store.pgvector_client import pgvector_store
from src.backend.rag.vector_store.qdrant_client import qdrant_store

logger = logging.getLogger("ubuntucare.rag.retriever")

RRF_K = 60
MIN_RELEVANCE_SCORE = 0.35
MAX_CONTEXT_TOKENS = 4096


class RetrievedDocument:
    def __init__(
        self,
        content: str,
        score: float,
        source: str,
        source_type: str,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        citation: Optional[str] = None,
        confidence: float = 0.0,
    ):
        self.content = content
        self.score = score
        self.source = source
        self.source_type = source_type
        self.title = title
        self.metadata = metadata or {}
        self.citation = citation
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "metadata": self.metadata,
            "citation": self.citation,
            "confidence": self.confidence,
        }


class RetrievalService:
    def __init__(self) -> None:
        self._strategies: dict[str, SearchStrategy] = {
            "simple": SimpleSemanticSearch(),
            "hybrid": HybridSearch(),
            "multi_hop": MultiHopRetrieval(),
            "parent_child": ParentChildRetrieval(),
            "temporal": TemporalFilteredSearch(),
        }

    def _rrf_score(self, rank: int) -> float:
        return 1.0 / (RRF_K + rank)

    def _rrf_merge(
        self, results_list: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        scores: dict[str, dict[str, Any]] = {}
        for source_results in results_list:
            for rank, doc in enumerate(source_results):
                key = doc.get("content", "")[:200]
                if key not in scores:
                    scores[key] = {**doc, "_rrf_score": 0.0, "_sources": []}
                scores[key]["_rrf_score"] += self._rrf_score(rank)
                scores[key]["_sources"].append(doc.get("source_type", "unknown"))
        sorted_docs = sorted(scores.values(), key=lambda x: x["_rrf_score"], reverse=True)
        for doc in sorted_docs:
            doc.pop("_rrf_score", None)
            doc.pop("_sources", None)
        return sorted_docs

    def _compute_confidence(
        self, doc: dict[str, Any], query: str
    ) -> float:
        score = doc.get("score", 0.0) or doc.get("similarity", 0.0)
        title = doc.get("title", "") or ""
        content = doc.get("content", "") or ""
        title_match = 1.0 if any(word in title.lower() for word in query.lower().split()) else 0.0
        source_quality = 1.0 if doc.get("source_type") in ("guideline", "protocol", "formulary") else 0.7
        return round(0.5 * score + 0.3 * title_match + 0.2 * source_quality, 4)

    def _generate_citation(self, doc: dict[str, Any]) -> str:
        title = doc.get("title", "Untitled")
        source = doc.get("source", "")
        source_type = doc.get("source_type", "document")
        year = doc.get("published_date", "")[:4] if doc.get("published_date") else "n.d."
        if source_type == "guideline":
            return f"{title} ({source}, {year}) - Clinical Guideline"
        elif source_type == "protocol":
            return f"{title} - Treatment Protocol ({source}, {year})"
        elif source_type == "formulary":
            return f"{title} - Drug Formulary ({source}, {year})"
        elif source_type == "literature":
            return f"{title} ({source}, {year})"
        return f"{title} ({source})"

    async def retrieve(
        self,
        query: str,
        strategy: str = "hybrid",
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
        use_sources: Optional[list[str]] = None,
    ) -> list[RetrievedDocument]:
        strategy_impl = self._strategies.get(strategy, self._strategies["hybrid"])
        raw_results = await strategy_impl.execute(query, limit=limit, filters=filters)

        if use_sources:
            filtered = []
            for doc in raw_results:
                if doc.get("source_type") in use_sources:
                    filtered.append(doc)
            raw_results = filtered

        if use_sources is None or len(use_sources or []) > 1:
            qdrant_filter = dict(filters) if filters else {}
            if use_sources:
                qdrant_filter["source_type"] = {"in": use_sources}
            query_vec = await embed_query(query)
            qdrant_results = qdrant_store.search(
                query_vector=query_vec,
                limit=limit,
                filters=qdrant_filter or None,
            )
            pgv_results = await pgvector_store.search(
                embedding=query_vec,
                limit=limit,
                filters=filters,
            )
            raw_results = self._rrf_merge([raw_results, qdrant_results, pgv_results])

        documents = []
        for doc in raw_results[:limit]:
            confidence = self._compute_confidence(doc, query)
            if confidence < MIN_RELEVANCE_SCORE:
                continue
            citation = self._generate_citation(doc)
            documents.append(
                RetrievedDocument(
                    content=doc.get("content", ""),
                    score=doc.get("score", 0.0) or doc.get("similarity", 0.0),
                    source=doc.get("source_url", "") or doc.get("source", ""),
                    source_type=doc.get("source_type", "unknown"),
                    title=doc.get("title"),
                    metadata=doc.get("metadata") or doc.get("metadata_") or {},
                    citation=citation,
                    confidence=confidence,
                )
            )
        return documents

    async def retrieve_with_expansion(
        self,
        query: str,
        strategy: str = "hybrid",
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedDocument]:
        expanded_queries = await self._expand_query(query)
        all_results: list[list[dict[str, Any]]] = []
        for eq in expanded_queries:
            strategy_impl = self._strategies.get(strategy, self._strategies["hybrid"])
            results = await strategy_impl.execute(eq, limit=limit, filters=filters)
            all_results.append(results)
        merged = self._rrf_merge(all_results)
        query_vec = await embed_query(query)
        qdrant_results = qdrant_store.search(query_vector=query_vec, limit=limit)
        merged = self._rrf_merge([merged, qdrant_results])
        documents = []
        for doc in merged[:limit]:
            confidence = self._compute_confidence(doc, query)
            if confidence < MIN_RELEVANCE_SCORE:
                continue
            citation = self._generate_citation(doc)
            documents.append(
                RetrievedDocument(
                    content=doc.get("content", ""),
                    score=doc.get("score", 0.0) or doc.get("similarity", 0.0),
                    source=doc.get("source_url", "") or doc.get("source", ""),
                    source_type=doc.get("source_type", "unknown"),
                    title=doc.get("title"),
                    metadata=doc.get("metadata") or doc.get("metadata_") or {},
                    citation=citation,
                    confidence=confidence,
                )
            )
        return documents

    async def _expand_query(self, query: str) -> list[str]:
        expansions = [query]
        medical_prefixes = [
            "diagnosis and treatment of",
            "clinical management of",
            "symptoms and signs of",
            "pharmacological treatment for",
        ]
        import random
        for prefix in random.sample(medical_prefixes, min(2, len(medical_prefixes))):
            expansions.append(f"{prefix} {query.lower().lstrip(prefix)}")
        return expansions

    async def compress_context(
        self, documents: list[RetrievedDocument], max_tokens: int = MAX_CONTEXT_TOKENS
    ) -> str:
        sorted_docs = sorted(documents, key=lambda d: d.confidence, reverse=True)
        context_parts: list[str] = []
        total_tokens = 0
        for doc in sorted_docs:
            approx_tokens = len(doc.content.split())
            if total_tokens + approx_tokens > max_tokens:
                remaining = max_tokens - total_tokens
                if remaining > 50:
                    words = doc.content.split()[:remaining]
                    context_parts.append(f"[Source: {doc.citation}]\n{' '.join(words)}")
                break
            context_parts.append(f"[Source: {doc.citation}]\n{doc.content}")
            total_tokens += approx_tokens
        return "\n\n---\n\n".join(context_parts)


retrieval_service = RetrievalService()
