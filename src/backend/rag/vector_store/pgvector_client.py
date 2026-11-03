from __future__ import annotations

import json
import logging
from typing import Any, Optional

import asyncpg
from sqlalchemy import Float, Integer, String, Text, text, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.backend.core.config.settings import settings
from src.backend.database import async_session_factory

logger = logging.getLogger("ubuntucare.rag.pgvector")


class PgVectorBase(DeclarativeBase):
    pass


class DocumentEmbedding(PgVectorBase):
    __tablename__ = "document_embeddings"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id = mapped_column(String(255), nullable=True)
    content = mapped_column(Text, nullable=False)
    title = mapped_column(String(500), nullable=True)
    source_type = mapped_column(String(100), nullable=True)
    source_url = mapped_column(String(1024), nullable=True)
    language = mapped_column(String(10), nullable=True)
    hospital_id = mapped_column(String(100), nullable=True, index=True)
    department = mapped_column(String(200), nullable=True, index=True)
    specialty = mapped_column(String(200), nullable=True, index=True)
    author = mapped_column(String(255), nullable=True)
    published_date = mapped_column(String(50), nullable=True)
    version = mapped_column(String(50), nullable=True)
    metadata_ = mapped_column("metadata", JSONB, nullable=True)
    embedding = mapped_column(ARRAY(Float), nullable=False)
    sparse_vector = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(String(50), nullable=True)


EMBEDDING_DIM = 1024


class PgVectorStore:
    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        await self._ensure_extension()
        async with async_session_factory() as session:
            async with session.begin():
                async with session.connection() as conn:
                    await conn.run_sync(DocumentEmbedding.metadata.create_all)
        await self._ensure_indexes()

    async def _ensure_extension(self) -> None:
        async with asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=1,
            max_size=2,
        ) as pool:
            async with pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    async def _ensure_indexes(self) -> None:
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        f"""
                        CREATE INDEX IF NOT EXISTS idx_doc_emb_hnsw
                        ON document_embeddings
                        USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 32, ef_construction = 200)
                        """
                    )
                )
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_doc_emb_content_gin "
                        "ON document_embeddings USING gin(to_tsvector('english', content))"
                    )
                )

    async def health(self) -> dict[str, Any]:
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def insert(
        self,
        content: str,
        embedding: list[float],
        *,
        external_id: Optional[str] = None,
        title: Optional[str] = None,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        language: Optional[str] = None,
        hospital_id: Optional[str] = None,
        department: Optional[str] = None,
        specialty: Optional[str] = None,
        author: Optional[str] = None,
        published_date: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        sparse_vector: Optional[dict[str, Any]] = None,
    ) -> int:
        async with async_session_factory() as session:
            async with session.begin():
                doc = DocumentEmbedding(
                    external_id=external_id,
                    content=content,
                    title=title,
                    source_type=source_type,
                    source_url=source_url,
                    language=language,
                    hospital_id=hospital_id,
                    department=department,
                    specialty=specialty,
                    author=author,
                    published_date=published_date,
                    version=version,
                    metadata_=metadata or {},
                    embedding=embedding,
                    sparse_vector=sparse_vector,
                )
                session.add(doc)
                await session.flush()
                doc_id = doc.id
                await session.commit()
                return doc_id

    async def upsert(self, doc_id: int, embedding: list[float], **kwargs: Any) -> None:
        async with async_session_factory() as session:
            async with session.begin():
                result = await session.get(DocumentEmbedding, doc_id)
                if result is None:
                    result = DocumentEmbedding(id=doc_id, embedding=embedding, **kwargs)
                    session.add(result)
                else:
                    for key, value in kwargs.items():
                        setattr(result, key, value)
                    result.embedding = embedding
                await session.commit()

    async def delete(self, doc_id: int) -> bool:
        async with async_session_factory() as session:
            async with session.begin():
                result = await session.get(DocumentEmbedding, doc_id)
                if result is None:
                    return False
                await session.delete(result)
                await session.commit()
                return True

    def _validate_filter_keys(self, filters: dict[str, Any]) -> None:
        valid_columns = {
            "external_id", "source_type", "source_url", "language",
            "hospital_id", "department", "specialty", "author",
            "published_date", "version",
        }
        for key in filters:
            if key not in valid_columns:
                raise ValueError(f"Invalid filter column: {key}")

    async def delete_by_filter(self, **filters: Any) -> int:
        async with async_session_factory() as session:
            async with session.begin():
                self._validate_filter_keys(filters)
                query = text("DELETE FROM document_embeddings WHERE " + " AND ".join(f"{k}=:{k}" for k in filters))
                result = await session.execute(query, filters)
                await session.commit()
                return result.rowcount

    async def search(
        self,
        embedding: list[float],
        limit: int = 20,
        offset: int = 0,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        emb_str = f"[{','.join(str(v) for v in embedding)}]"
        where_clauses = []
        params: dict[str, Any] = {}
        if filters:
            self._validate_filter_keys(filters)
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"f_{i}"
                where_clauses.append(f"d.{key} = :{param_name}")
                params[param_name] = value
        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        sql = f"""
            SELECT d.*, 1 - (d.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM document_embeddings d
            WHERE {where_sql}
            ORDER BY d.embedding <=> CAST(:emb AS vector)
            LIMIT :limit OFFSET :offset
        """
        params.update({"emb": emb_str, "limit": limit, "offset": offset})
        async with async_session_factory() as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def search_hybrid(
        self,
        embedding: list[float],
        query_text: str,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
        alpha: float = 0.5,
    ) -> list[dict[str, Any]]:
        emb_str = f"[{','.join(str(v) for v in embedding)}]"
        where_clauses = []
        params: dict[str, Any] = {}
        if filters:
            self._validate_filter_keys(filters)
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"f_{i}"
                where_clauses.append(f"d.{key} = :{param_name}")
                params[param_name] = value
        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        sql = f"""
            WITH vector_results AS (
                SELECT d.*, 1 - (d.embedding <=> CAST(:emb AS vector)) AS vector_score,
                       ROW_NUMBER() OVER (ORDER BY d.embedding <=> CAST(:emb AS vector)) AS vr_rank
                FROM document_embeddings d
                WHERE {where_sql}
                LIMIT :limit * 2
            ),
            fulltext_results AS (
                SELECT d.*, ts_rank(to_tsvector('english', d.content), to_tsquery('english', :qtext)) AS text_score,
                       ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('english', d.content), to_tsquery('english', :qtext)) DESC) AS fr_rank
                FROM document_embeddings d
                WHERE {where_sql}
                  AND to_tsvector('english', d.content) @@ to_tsquery('english', :qtext)
                LIMIT :limit * 2
            ),
            fused AS (
                SELECT COALESCE(v.id, f.id) AS id,
                       COALESCE(v.vector_score, 0) AS vs,
                       COALESCE(f.text_score, 0) AS ts,
                       COALESCE(1.0 / (60 + v.vr_rank), 0) AS vrrf,
                       COALESCE(1.0 / (60 + f.fr_rank), 0) AS frrf,
                       (:alpha * COALESCE(v.vector_score, 0) + (1 - :alpha2) * COALESCE(f.text_score, 0) + 0.5 * (COALESCE(1.0 / (60 + v.vr_rank), 0) + COALESCE(1.0 / (60 + f.fr_rank), 0))) AS score
                FROM vector_results v
                FULL OUTER JOIN fulltext_results f ON v.id = f.id
            )
            SELECT d.*, f.score
            FROM fused f
            JOIN document_embeddings d ON d.id = f.id
            ORDER BY f.score DESC
            LIMIT :limit
        """
        params.update({
            "emb": emb_str,
            "qtext": " & ".join(query_text.split()),
            "limit": limit,
            "alpha": alpha,
            "alpha2": alpha,
        })
        async with async_session_factory() as session:
            result = await session.execute(text(sql), params)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def get_by_id(self, doc_id: int) -> Optional[dict[str, Any]]:
        async with async_session_factory() as session:
            result = await session.get(DocumentEmbedding, doc_id)
            if result is None:
                return None
            return {c.name: getattr(result, c.name) for c in result.__table__.columns}

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        where_clauses = []
        params: dict[str, Any] = {}
        if filters:
            self._validate_filter_keys(filters)
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"f_{i}"
                where_clauses.append(f"{key} = :{param_name}")
                params[param_name] = value
        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        sql = f"SELECT COUNT(*) FROM document_embeddings WHERE {where_sql}"
        async with async_session_factory() as session:
            result = await session.execute(text(sql), params)
            return result.scalar() or 0


pgvector_store = PgVectorStore()
