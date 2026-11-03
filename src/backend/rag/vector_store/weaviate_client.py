from __future__ import annotations

import json
import logging
from typing import Any, Optional

import weaviate
from weaviate.classes.config import Configure, Property, DataType, Tokenization
from weaviate.classes.query import Filter, HybridFusion
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateClosedError, WeaviateQueryError

from src.backend.core.config.settings import settings

logger = logging.getLogger("ubuntucare.rag.weaviate")

DEFAULT_CLASS_NAME = "HealthcareDocument"


class WeaviateVectorStore:
    def __init__(self) -> None:
        self._client: Optional[weaviate.WeaviateClient] = None

    def _connect(self) -> weaviate.WeaviateClient:
        if self._client is not None:
            try:
                self._client.is_connected()
                return self._client
            except (WeaviateClosedError, AttributeError):
                self._client = None
        connection = ConnectionParams.from_params(
            http_host=settings.WEAVIATE_HOST,
            http_port=settings.WEAVIATE_PORT,
            http_secure=settings.WEAVIATE_HTTPS,
            grpc_host=settings.WEAVIATE_HOST,
            grpc_port=settings.WEAVIATE_GRPC_PORT,
            grpc_secure=settings.WEAVIATE_HTTPS,
        )
        auth = None
        if settings.WEAVIATE_API_KEY:
            auth = weaviate.auth.AuthApiKey(settings.WEAVIATE_API_KEY)
        self._client = weaviate.WeaviateClient(
            connection_params=connection,
            auth_client_secret=auth,
        )
        self._client.connect()
        return self._client

    async def health(self) -> dict[str, Any]:
        try:
            meta = self._connect().get_meta()
            return {"status": "healthy", "version": meta.get("version", "unknown")}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    def ensure_schema(self, class_name: str = DEFAULT_CLASS_NAME) -> None:
        client = self._connect()
        if client.collections.exists(class_name):
            logger.info("Class '%s' exists", class_name)
            return
        client.collections.create(
            name=class_name,
            properties=[
                Property(name="content", data_type=DataType.TEXT, tokenization=Tokenization.WORD),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="source_type", data_type=DataType.TEXT),
                Property(name="source_url", data_type=DataType.TEXT),
                Property(name="language", data_type=DataType.TEXT),
                Property(name="hospital_id", data_type=DataType.TEXT),
                Property(name="department", data_type=DataType.TEXT),
                Property(name="specialty", data_type=DataType.TEXT),
                Property(name="author", data_type=DataType.TEXT),
                Property(name="published_date", data_type=DataType.DATE),
                Property(name="version", data_type=DataType.TEXT),
                Property(name="metadata", data_type=DataType.TEXT),
            ],
            vectorizer_config=Configure.Vectorizer.none(),
            generative_config=Configure.Generative.none(),
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        )
        logger.info("Created class '%s' with multi-tenancy", class_name)

    def _collection(self, class_name: str = DEFAULT_CLASS_NAME):
        return self._connect().collections.get(class_name)

    def insert_object(
        self,
        obj: dict[str, Any],
        vector: list[float],
        class_name: str = DEFAULT_CLASS_NAME,
        tenant: Optional[str] = None,
    ) -> str:
        col = self._collection(class_name)
        metadata_str = json.dumps(obj.pop("metadata", {}))
        properties = {**{k: v for k, v in obj.items() if v is not None}, "metadata": metadata_str}
        kwargs: dict[str, Any] = {"properties": properties, "vector": vector}
        if tenant:
            kwargs["tenant"] = tenant
        result = col.data.insert(**kwargs)
        return str(result)

    def insert_objects_batch(
        self,
        objects: list[tuple[dict[str, Any], list[float]]],
        class_name: str = DEFAULT_CLASS_NAME,
        tenant: Optional[str] = None,
    ) -> int:
        col = self._collection(class_name)
        count = 0
        with col.batch.fixed_size(batch_size=100) as batch:
            for obj, vector in objects:
                metadata_str = json.dumps(obj.pop("metadata", {}))
                properties = {**{k: v for k, v in obj.items() if v is not None}, "metadata": metadata_str}
                kwargs: dict[str, Any] = {"properties": properties, "vector": vector}
                if tenant:
                    kwargs["tenant"] = tenant
                batch.add_object(**kwargs)
                count += 1
        return count

    def get_object(
        self,
        uuid: str,
        class_name: str = DEFAULT_CLASS_NAME,
        tenant: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        col = self._collection(class_name)
        kwargs: dict[str, Any] = {"uuid": uuid}
        if tenant:
            kwargs["tenant"] = tenant
        obj = col.query.fetch_object_by_id(**kwargs)
        if obj is None:
            return None
        return obj.properties

    def update_object(
        self,
        uuid: str,
        properties: dict[str, Any],
        class_name: str = DEFAULT_CLASS_NAME,
        tenant: Optional[str] = None,
    ) -> None:
        col = self._collection(class_name)
        kwargs: dict[str, Any] = {"uuid": uuid, "properties": properties}
        if tenant:
            kwargs["tenant"] = tenant
        col.data.update(**kwargs)

    def delete_object(
        self,
        uuid: str,
        class_name: str = DEFAULT_CLASS_NAME,
        tenant: Optional[str] = None,
    ) -> None:
        col = self._collection(class_name)
        kwargs: dict[str, Any] = {"uuid": uuid}
        if tenant:
            kwargs["tenant"] = tenant
        col.data.delete_by_id(**kwargs)

    def search_near_vector(
        self,
        vector: list[float],
        limit: int = 20,
        class_name: str = DEFAULT_CLASS_NAME,
        filters: Optional[dict[str, Any]] = None,
        tenant: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        col = self._collection(class_name)
        wfilters = None
        if filters:
            wfilters = self._build_filter(filters)
        kwargs: dict[str, Any] = {
            "near_vector": vector,
            "limit": limit,
            "return_metadata": ["distance", "certainty"],
        }
        if wfilters is not None:
            kwargs["filter"] = wfilters
        if tenant:
            kwargs["tenant"] = tenant
        results = col.query.near_vector(**kwargs)
        return [{"uuid": str(o.uuid), "properties": o.properties, "metadata": o.metadata} for o in results.objects]

    def search_hybrid(
        self,
        query: str,
        vector: list[float],
        alpha: float = 0.5,
        limit: int = 20,
        class_name: str = DEFAULT_CLASS_NAME,
        filters: Optional[dict[str, Any]] = None,
        tenant: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        col = self._collection(class_name)
        wfilters = None
        if filters:
            wfilters = self._build_filter(filters)
        kwargs: dict[str, Any] = {
            "query": query,
            "vector": vector,
            "alpha": alpha,
            "limit": limit,
            "fusion_type": HybridFusion.RELATIVE_SCORE,
            "return_metadata": ["score", "distance"],
        }
        if wfilters is not None:
            kwargs["filter"] = wfilters
        if tenant:
            kwargs["tenant"] = tenant
        results = col.query.hybrid(**kwargs)
        return [{"uuid": str(o.uuid), "properties": o.properties, "metadata": o.metadata} for o in results.objects]

    def search_graphql(
        self,
        query_str: str,
    ) -> list[dict[str, Any]]:
        client = self._connect()
        results = client.graphql_raw_query(query_str)
        return results

    def _build_filter(self, filters: dict[str, Any]) -> Filter:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    if op == "eq":
                        conditions.append(Filter.by_property(key).equal(val))
                    elif op == "gt":
                        conditions.append(Filter.by_property(key).greater_than(val))
                    elif op == "gte":
                        conditions.append(Filter.by_property(key).greater_or_equal(val))
                    elif op == "lt":
                        conditions.append(Filter.by_property(key).less_than(val))
                    elif op == "lte":
                        conditions.append(Filter.by_property(key).less_or_equal(val))
                    elif op == "in":
                        conditions.append(Filter.by_property(key).contains_any(val))
                    elif op == "like":
                        conditions.append(Filter.by_property(key).like(val))
            else:
                conditions.append(Filter.by_property(key).equal(value))
        if len(conditions) == 1:
            return conditions[0]
        return Filter.all_of(conditions)

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


weaviate_store = WeaviateVectorStore()
