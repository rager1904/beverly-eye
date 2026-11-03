from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.backend.core.config.settings import settings
from src.backend.rag.embeddings.service import health as embeddings_health
from src.backend.rag.knowledge_graph.graph_search import GraphSearchTool
from src.backend.rag.knowledge_graph.neo4j_client import get_neo4j_client
from src.backend.rag.knowledge_base.ingestion import (
    delete_document,
    get_knowledge_base_stats,
    ingest_document,
    ingest_from_url,
)
from src.backend.rag.knowledge_base.sources import orchestrator as source_orchestrator
from src.backend.rag.retriever.service import retrieval_service
from src.backend.rag.vector_store.pgvector_client import pgvector_store
from src.backend.rag.vector_store.qdrant_client import qdrant_store
from src.backend.shared.models.base import APIResponse

logger = logging.getLogger("ubuntucare.rag.api")

rag_router = APIRouter(prefix="/rag", tags=["RAG"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    strategy: str = Field(default="hybrid", pattern="^(simple|hybrid|multi_hop|parent_child|temporal)$")
    limit: int = Field(default=10, ge=1, le=100)
    filters: Optional[dict[str, Any]] = None
    sources: Optional[list[str]] = None


class RetrieveRequest(SearchRequest):
    include_citations: bool = True
    min_confidence: float = Field(default=0.35, ge=0.0, le=1.0)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    strategy: str = Field(default="hybrid", pattern="^(simple|hybrid|multi_hop|parent_child|temporal)$")
    filters: Optional[dict[str, Any]] = None
    max_context_tokens: int = Field(default=2048, ge=256, le=8192)
    model: Optional[str] = None
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)


class IngestRequest(BaseModel):
    content: str
    source_type: str = Field(default="text", pattern="^(text|html|markdown|pdf)$")
    source_url: Optional[str] = None
    title: Optional[str] = None
    chunk_strategy: str = Field(default="recursive", pattern="^(semantic|recursive|sliding)$")
    hospital_id: Optional[str] = None
    department: Optional[str] = None
    specialty: Optional[str] = None
    language: Optional[str] = "en"
    author: Optional[str] = None
    published_date: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class IngestUrlRequest(BaseModel):
    url: str = Field(min_length=1)
    source_type: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    specialty: Optional[str] = None


@rag_router.get("/health")
async def health() -> dict[str, Any]:
    pgv_health = await pgvector_store.health()
    qd_health = await qdrant_store.health()
    emb_health = await embeddings_health()
    return {
        "status": "healthy" if pgv_health.get("status") == "healthy" else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "pgvector": pgv_health,
            "qdrant": qd_health,
            "embeddings": emb_health,
        },
    }


@rag_router.post("/search")
async def search(request: SearchRequest) -> APIResponse:
    try:
        results = await retrieval_service.retrieve(
            query=request.query,
            strategy=request.strategy,
            limit=request.limit,
            filters=request.filters,
            use_sources=request.sources,
        )
        return APIResponse(
            success=True,
            message=f"Found {len(results)} results",
            data=[r.to_dict() for r in results],
        )
    except Exception as exc:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.post("/retrieve")
async def retrieve(request: RetrieveRequest) -> APIResponse:
    try:
        results = await retrieval_service.retrieve(
            query=request.query,
            strategy=request.strategy,
            limit=request.limit,
            filters=request.filters,
            use_sources=request.sources,
        )
        filtered = [r for r in results if r.confidence >= request.min_confidence]
        return APIResponse(
            success=True,
            message=f"Found {len(filtered)} results (filtered from {len(results)})",
            data=[r.to_dict() for r in filtered],
        )
    except Exception as exc:
        logger.exception("Retrieve failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.post("/ask")
async def ask(request: AskRequest) -> APIResponse:
    try:
        documents = await retrieval_service.retrieve(
            query=request.query,
            strategy=request.strategy,
            limit=10,
            filters=request.filters,
        )
        context = await retrieval_service.compress_context(
            documents, max_tokens=request.max_context_tokens
        )
        system_msg = (
            "You are a clinical decision support assistant for healthcare workers in Zambia. "
            "Answer the question using ONLY the provided context. "
            "If the context does not contain enough information, state that you cannot answer. "
            "Include citations from the sources. Be concise and clinically accurate."
        )
        prompt = f"{system_msg}\n\nContext:\n{context}\n\nQuestion: {request.query}"

        import httpx
        payload: dict[str, Any] = {
            "model": request.model or settings.LLM_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_context_tokens,
        }
        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.LLM_ENDPOINT}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            llm_response = resp.json()
            answer = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")

        return APIResponse(
            success=True,
            data={
                "answer": answer,
                "sources": [d.to_dict() for d in documents[:5]],
                "context": context,
            },
        )
    except Exception as exc:
        logger.exception("Ask failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.post("/ingest")
async def ingest(request: IngestRequest) -> APIResponse:
    try:
        count = await ingest_document(
            request.content,
            source_type=request.source_type,
            source_url=request.source_url,
            title=request.title,
            chunk_strategy=request.chunk_strategy,
            hospital_id=request.hospital_id,
            department=request.department,
            specialty=request.specialty,
            language=request.language,
            author=request.author,
            published_date=request.published_date,
            version=request.version,
            metadata=request.metadata,
        )
        return APIResponse(success=True, message=f"Ingested {count} chunks", data={"chunks": count})
    except Exception as exc:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.post("/ingest/url")
async def ingest_url(request: IngestUrlRequest) -> APIResponse:
    try:
        count = await ingest_from_url(
            request.url,
            source_type=request.source_type,
            title=request.title,
            department=request.department,
            specialty=request.specialty,
        )
        return APIResponse(success=True, message=f"Ingested {count} chunks from URL", data={"chunks": count})
    except Exception as exc:
        logger.exception("Ingest URL failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.get("/sources")
async def get_sources() -> APIResponse:
    return APIResponse(data=source_orchestrator.get_source_status())


@rag_router.post("/sources/refresh")
async def refresh_sources() -> APIResponse:
    try:
        results = await source_orchestrator.refresh_all()
        return APIResponse(success=True, message="Sources refreshed", data=results)
    except Exception as exc:
        logger.exception("Source refresh failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.post("/sources/refresh/{name}")
async def refresh_source(name: str) -> APIResponse:
    try:
        count = await source_orchestrator.refresh_source(name)
        return APIResponse(success=True, message=f"Refreshed '{name}': {count} documents", data={"count": count})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Source refresh failed")
        raise HTTPException(status_code=500, detail=str(exc))


@rag_router.get("/stats")
async def stats() -> APIResponse:
    stats_data = await get_knowledge_base_stats()
    return APIResponse(data=stats_data)


@rag_router.delete("/documents/{external_id}")
async def remove_document(external_id: str) -> APIResponse:
    deleted = await delete_document(external_id)
    return APIResponse(success=deleted, message="Deleted" if deleted else "Not found")


# ── Knowledge Graph endpoints ─────────────────────────────────────────────

class GraphSearchRequest(BaseModel):
    query: str = Field(..., description="Free-text search across graph nodes")
    limit: int = Field(default=10, ge=1, le=50)


class GraphDrugDiseaseRequest(BaseModel):
    drug_name: Optional[str] = Field(None, description="Find diseases treated by this drug")
    disease_name: Optional[str] = Field(None, description="Find drugs that treat this disease")
    symptom: Optional[str] = Field(None, description="Find diseases with this symptom")


@rag_router.get("/graph/health")
async def graph_health():
    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()
    stats = await client.get_stats()
    return APIResponse(data=stats)


@rag_router.post("/graph/search")
async def graph_search(req: GraphSearchRequest):
    tool = GraphSearchTool()
    results = await tool.search(req.query, req.limit)
    return APIResponse(data={"results": results, "count": len(results)})


@rag_router.post("/graph/query")
async def graph_query(req: GraphDrugDiseaseRequest):
    tool = GraphSearchTool()
    data = {}
    if req.drug_name:
        data["diseases"] = await tool.search_diseases_for_drug(req.drug_name)
    if req.disease_name:
        data["drugs"] = await tool.search_drugs_for_disease(req.disease_name)
        data["symptoms"] = await tool.search_symptoms_for_disease(req.disease_name)
        data["vaccines"] = await tool.search_vaccines_for_disease(req.disease_name)
    if req.symptom:
        data["diseases"] = await tool.search_diseases_for_symptom(req.symptom)
    return APIResponse(data=data)


@rag_router.post("/graph/seed")
async def graph_seed():
    from src.backend.rag.knowledge_graph.graph_seeder import KnowledgeGraphSeeder
    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()
    seeder = KnowledgeGraphSeeder(client)
    result = await seeder.seed_all()
    return APIResponse(data=result, message="Knowledge graph seeded")


@rag_router.get("/graph/stats")
async def graph_stats():
    tool = GraphSearchTool()
    stats = await tool.get_stats()
    return APIResponse(data=stats)


def create_rag_app() -> FastAPI:
    app = FastAPI(title="UbuntuCare RAG Service", version="1.0.0")

    @app.on_event("startup")
    async def startup():
        try:
            client = get_neo4j_client()
            await client.connect()
            if client.is_connected:
                logger.info("Neo4j knowledge graph connected")
        except Exception as e:
            logger.warning("Neo4j startup failed (graph features will be unavailable): %s", e)

        try:
            from src.backend.rag.embeddings.service import preload_model
            await preload_model()
            logger.info("Embedding model preloaded on startup")
        except Exception as e:
            logger.warning("Embedding model preload failed (will load on demand): %s", e)

        try:
            from src.backend.core.cache.redis_client import redis_client
            await redis_client.initialize()
            logger.info("Redis client initialized")
        except Exception as e:
            logger.warning("Redis init failed (caching disabled): %s", e)

    app.include_router(rag_router, prefix="/api/v1")
    return app

app = create_rag_app()
