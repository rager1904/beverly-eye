from __future__ import annotations

import logging
from typing import Any, Optional

from qdrant_client import QdrantClient as QdrantSync
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.rag.qdrant")

COLLECTION_CONFIG = {
    "distance": qmodels.Distance.COSINE,
    "on_disk": True,
    "hnsw_config": qmodels.HnswConfigDiff(m=32, ef_construct=200, full_scan_threshold=10000),
    "optimizers_config": qmodels.OptimizersConfigDiff(memmap_threshold=20000),
    "sparse_vectors": {
        "sparse": qmodels.SparseVectorParams(
            index=qmodels.SparseIndexParams(on_disk=True),
        ),
    },
}

DEFAULT_COLLECTION_NAME = "healthcare_knowledge"


class QdrantVectorStore:
    def __init__(self) -> None:
        self._client: Optional[QdrantSync] = None

    def _get_client(self) -> QdrantSync:
        if self._client is None:
            self._client = QdrantSync(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                grpc_port=settings.QDRANT_GRPC_PORT,
                api_key=settings.QDRANT_API_KEY,
                prefer_grpc=settings.QDRANT_PREFER_GRPC,
                https=settings.QDRANT_HTTPS,
            )
        return self._client

    async def health(self) -> dict[str, Any]:
        try:
            info = self._get_client().get_collections()
            return {"status": "healthy", "collections": len(info.collections)}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def ensure_collection(self, name: str = DEFAULT_COLLECTION_NAME, vector_size: int = 1024) -> None:
        client = self._get_client()
        try:
            client.get_collection(name)
            logger.info("Collection '%s' exists", name)
        except UnexpectedResponse:
            logger.info("Creating collection '%s' (dim=%d)", name, vector_size)
            client.create_collection(
                collection_name=name,
                vectors_config={
                    "dense": qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE,
                        on_disk=True,
                    ),
                },
                sparse_vectors=COLLECTION_CONFIG["sparse_vectors"],
                hnsw_config=COLLECTION_CONFIG["hnsw_config"],
                optimizers_config=COLLECTION_CONFIG["optimizers_config"],
            )
            client.create_payload_index(
                collection_name=name,
                field_name="hospital_id",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=name,
                field_name="department",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=name,
                field_name="specialty",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=name,
                field_name="source_type",
                field_type=qmodels.PayloadSchemaType.KEYWORD,
            )

    def upsert_points(
        self,
        points: list[dict[str, Any]],
        collection: str = DEFAULT_COLLECTION_NAME,
    ) -> int:
        client = self._get_client()
        qdrant_points: list[qmodels.PointStruct] = []
        for pt in points:
            qdrant_points.append(
                qmodels.PointStruct(
                    id=pt["id"],
                    vector={
                        "dense": pt["vector"],
                        **({"sparse": pt["sparse_vector"]} if "sparse_vector" in pt else {}),
                    },
                    payload=pt.get("payload", {}),
                )
            )
        result = client.upsert(collection_name=collection, points=qdrant_points)
        return len(qdrant_points)

    def delete_points(
        self,
        point_ids: list[str | int],
        collection: str = DEFAULT_COLLECTION_NAME,
    ) -> None:
        client = self._get_client()
        client.delete(collection_name=collection, points_selector=qmodels.PointIdsList(points=point_ids))

    def delete_by_filter(
        self,
        filter_dict: dict[str, Any],
        collection: str = DEFAULT_COLLECTION_NAME,
    ) -> None:
        client = self._get_client()
        client.delete(
            collection_name=collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(**qmodels.Filter.model_validate(filter_dict)),
            ),
        )

    def search(
        self,
        query_vector: list[float],
        collection: str = DEFAULT_COLLECTION_NAME,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[dict[str, Any]] = None,
        with_payload: bool = True,
        with_vectors: bool = False,
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        qfilter = None
        if filters:
            qfilter = qmodels.Filter(**filters)
        results = client.search(
            collection_name=collection,
            query_vector=("dense", query_vector),
            query_filter=qfilter,
            limit=limit,
            offset=offset,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )
        return [r.model_dump() for r in results]

    def search_hybrid(
        self,
        dense_vector: list[float],
        sparse_vector: dict[str, list[float] | list[int]],
        collection: str = DEFAULT_COLLECTION_NAME,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        qfilter = None
        if filters:
            qfilter = qmodels.Filter(**filters)
        prefetch = [
            qmodels.Prefetch(query=("dense", dense_vector), limit=limit * 2),
            qmodels.Prefetch(query=("sparse", qmodels.SparseVector(**sparse_vector)), limit=limit * 2),
        ]
        results = client.search_batch(
            collection_name=collection,
            requests=[
                qmodels.SearchRequest(
                    prefetch=prefetch,
                    query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                    limit=limit,
                    filter=qfilter,
                    with_payload=True,
                )
            ],
        )
        if results:
            return [r.model_dump() for r in results[0]]
        return []

    def scroll(
        self,
        collection: str = DEFAULT_COLLECTION_NAME,
        filter_dict: Optional[dict[str, Any]] = None,
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        client = self._get_client()
        qfilter = None
        if filter_dict:
            qfilter = qmodels.Filter(**filter_dict)
        points, next_offset = client.scroll(
            collection_name=collection,
            filter=qfilter,
            limit=limit,
            offset=offset,
            with_payload=True,
        )
        return [p.model_dump() for p in points], next_offset

    def count_points(self, collection: str = DEFAULT_COLLECTION_NAME) -> int:
        client = self._get_client()
        result = client.count(collection_name=collection)
        return result.count

    def delete_collection(self, name: str = DEFAULT_COLLECTION_NAME) -> None:
        self._get_client().delete_collection(name)
        logger.info("Deleted collection '%s'", name)

    def list_collections(self) -> list[str]:
        resp = self._get_client().get_collections()
        return [c.name for c in resp.collections]

    def backup_snapshot(self, collection: str = DEFAULT_COLLECTION_NAME) -> str:
        client = self._get_client()
        result = client.create_snapshot(collection_name=collection)
        return str(result.name or "")


qdrant_store = QdrantVectorStore()
