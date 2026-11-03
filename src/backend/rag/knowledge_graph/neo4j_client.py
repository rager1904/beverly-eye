from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple

from src.backend.core.config import settings
from src.backend.rag.knowledge_graph.graph_schema import get_constraint_queries

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncGraphDatabase, AsyncSession, Auth, TrustSystemCAs

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("neo4j driver not installed; using in-memory graph backend")


@dataclass
class _MemNode:
    label: str
    properties: Dict[str, Any]
    created_at: float = field(default_factory=time.time)


@dataclass
class _MemRel:
    from_key: Tuple[str, str]
    to_key: Tuple[str, str]
    rel_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class Neo4jClient:
    """Knowledge graph client with auto-fallback to in-memory store.

    When Neo4j is unreachable or the driver is not installed, all data
    is stored in-memory (process-local, lost on restart).  Callers
    never need to know which backend is active.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ):
        self._uri = uri or getattr(settings, "NEO4J_URI", "bolt://neo4j:7687")
        self._user = user or getattr(settings, "NEO4J_USER", "neo4j")
        self._password = password or getattr(settings, "NEO4J_PASSWORD", "CHANGE_ME__neo4j")
        self._database = database
        self._driver: Any = None
        # in-memory fallback stores
        self._mem_nodes: Dict[Tuple[str, str], _MemNode] = {}
        self._mem_rels: List[_MemRel] = []

    # ---- lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        if self._driver:
            return
        if NEO4J_AVAILABLE:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self._uri,
                    auth=Auth(self._user, self._password),
                    trust=TrustSystemCAs(),
                )
                await self._driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", self._uri)
                await self._ensure_constraints()
                return
            except Exception as e:
                logger.info("Neo4j unavailable (%s); using in-memory graph", e)
        else:
            logger.info("neo4j package not installed; using in-memory graph")
        self._driver = object()  # truthy sentinel → not None, but not real neo4j

    async def close(self) -> None:
        if NEO4J_AVAILABLE and self._driver and type(self._driver).__name__ != "object":
            await self._driver.close()
        self._driver = None
        self._mem_nodes.clear()
        self._mem_rels.clear()

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    @property
    def _is_neo4j(self) -> bool:
        return NEO4J_AVAILABLE and self._driver is not None and type(self._driver).__name__ != "object"

    # ---- Cypher passthrough (only works with real Neo4j) -------------------

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[Any, None]:
        if not self._is_neo4j:
            raise RuntimeError("Neo4j not connected; session unavailable")
        async with self._driver.session(database=self._database) as session:
            yield session

    async def _ensure_constraints(self) -> None:
        try:
            async with self.session() as session:
                for query in get_constraint_queries():
                    await session.run(query)
        except Exception as e:
            logger.warning("Failed to ensure constraints: %s", e)

    async def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not self._is_neo4j:
            return []
        try:
            async with self.session() as session:
                result = await session.run(query, params or {})
                return await result.data()
        except Exception as e:
            logger.error("Neo4j query failed: %s", e)
            return []

    # ---- node / edge operations (backend-agnostic) ------------------------

    async def create_node(
        self, label: str, properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self._driver:
            return None
        if self._is_neo4j:
            props_str = ", ".join(f"{k}: ${k}" for k in properties)
            query = f"MERGE (n:{label} {{{props_str}}}) RETURN n"
            results = await self.run_query(query, properties)
            return results[0] if results else None
        # in-memory
        name = properties.get("name") or properties.get("code") or str(properties)
        key = (label, str(name))
        if key not in self._mem_nodes:
            self._mem_nodes[key] = _MemNode(label=label, properties=properties)
            return {"n": properties}
        return {"n": self._mem_nodes[key].properties}

    async def create_relationship(
        self,
        from_label: str,
        from_props: Dict[str, Any],
        to_label: str,
        to_props: Dict[str, Any],
        rel_type: str,
        rel_props: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._driver:
            return
        if self._is_neo4j:
            from_cond = " AND ".join(f"a.{k} = $from_{k}" for k in from_props)
            to_cond = " AND ".join(f"b.{k} = $to_{k}" for k in to_props)
            params = {f"from_{k}": v for k, v in from_props.items()}
            params.update({f"to_{k}": v for k, v in to_props.items()})
            rel_set = ""
            if rel_props:
                rel_set = "SET " + ", ".join(f"r.{k} = ${k}" for k in rel_props)
                params.update(rel_props)
            query = f"""
                MATCH (a:{from_label} {{{from_cond}}})
                MATCH (b:{to_label} {{{to_cond}}})
                MERGE (a)-[r:{rel_type}]->(b)
                {rel_set}
            """
            await self.run_query(query, params)
            return
        # in-memory
        from_name = str(from_props.get("name") or from_props.get("code") or "")
        to_name = str(to_props.get("name") or to_props.get("code") or "")
        self._mem_rels.append(_MemRel(
            from_key=(from_label, from_name),
            to_key=(to_label, to_name),
            rel_type=rel_type,
            properties=rel_props or {},
        ))

    # ---- search / traversal (backend-agnostic) -----------------------------

    async def search_similar(
        self,
        node_label: str,
        property_name: str,
        search_term: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self._driver:
            return []
        if self._is_neo4j:
            query = f"""
                MATCH (n:{node_label})
                WHERE n.{property_name} CONTAINS $search
                RETURN n, labels(n) as labels
                LIMIT $limit
            """
            return await self.run_query(query, {"search": search_term, "limit": limit})
        # in-memory
        results = []
        for key, node in self._mem_nodes.items():
            if node.label != node_label:
                continue
            val = str(node.properties.get(property_name, ""))
            if search_term.lower() in val.lower():
                results.append({"n": node.properties, "labels": [node_label]})
                if len(results) >= limit:
                    break
        return results

    async def find_path(
        self,
        from_label: str,
        from_prop: Dict[str, Any],
        to_label: str,
        to_prop: Dict[str, Any],
        max_hops: int = 3,
    ) -> List[Dict[str, Any]]:
        if not self._driver:
            return []
        if self._is_neo4j:
            from_cond = " AND ".join(f"a.{k} = $from_{k}" for k in from_prop)
            to_cond = " AND ".join(f"b.{k} = $to_{k}" for k in to_prop)
            params = {f"from_{k}": v for k, v in from_prop.items()}
            params.update({f"to_{k}": v for k, v in to_prop.items()})
            query = f"""
                MATCH path = shortestPath(
                    (a:{from_label} {{{from_cond}}})-[*..{max_hops}]-(b:{to_label} {{{to_cond}}})
                )
                RETURN [n in nodes(path) | {{labels: labels(n), properties: properties(n)}}] as nodes,
                       [r in relationships(path) | {{type: type(r), properties: properties(r)}}] as rels
            """
            return await self.run_query(query, params)
        # in-memory — BFS from source
        from_name = str(from_prop.get("name") or from_prop.get("code") or "")
        to_name = str(to_prop.get("name") or to_prop.get("code") or "")
        source_key = (from_label, from_name)
        target_key = (to_label, to_name)
        return self._bfs_path(source_key, target_key, max_hops)

    def _bfs_path(
        self,
        source: Tuple[str, str],
        target: Tuple[str, str],
        max_hops: int,
    ) -> List[Dict[str, Any]]:
        visited: Set[Tuple[str, str]] = {source}
        parent: Dict[Tuple[str, str], Tuple[Optional[Tuple[str, str]], Optional[_MemRel]]] = {
            source: (None, None)
        }
        queue = [source]
        for _ in range(max_hops):
            next_queue = []
            for current in queue:
                for rel in self._mem_rels:
                    neighbor = None
                    if rel.from_key == current:
                        neighbor = rel.to_key
                    elif rel.to_key == current:
                        neighbor = rel.from_key
                    if neighbor and neighbor not in visited:
                        visited.add(neighbor)
                        parent[neighbor] = (current, rel)
                        next_queue.append(neighbor)
                        if neighbor == target:
                            return self._reconstruct_path(parent, target)
            queue = next_queue
            if not queue:
                break
        return []

    def _reconstruct_path(
        self,
        parent: Dict[Tuple[str, str], Tuple[Optional[Tuple[str, str]], Optional[_MemRel]]],
        target: Tuple[str, str],
    ) -> List[Dict[str, Any]]:
        nodes = []
        rels = []
        current = target
        while current is not None:
            node = self._mem_nodes.get(current)
            props = node.properties if node else {}
            nodes.insert(0, {"labels": [current[0]], "properties": props})
            p, rel = parent.get(current, (None, None))
            if rel:
                rels.insert(0, {"type": rel.rel_type, "properties": rel.properties})
            current = p
        return [{"nodes": nodes, "rels": rels}]

    async def get_related(
        self,
        node_label: str,
        properties: Dict[str, Any],
        rel_types: Optional[List[str]] = None,
        direction: str = "both",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if not self._driver:
            return []
        if self._is_neo4j:
            cond = " AND ".join(f"n.{k} = ${k}" for k in properties)
            rel_filter = ""
            if rel_types:
                rel_filter = " | ".join(f":{r}" for r in rel_types)
                rel_filter = f"[{rel_filter}]"
            dir_arrow = "-" if direction in ("out", "both") else "<-"
            dir_arrow2 = "->" if direction in ("in", "both") else "-"
            params = {**properties, "limit": limit}
            query = f"""
                MATCH (n:{node_label} {{{cond}}}){dir_arrow}[r{rel_filter}]{dir_arrow2}(related)
                RETURN related, labels(related) as labels, type(r) as relationship
                LIMIT $limit
            """
            return await self.run_query(query, params)
        # in-memory
        name = str(properties.get("name") or properties.get("code") or "")
        key = (node_label, name)
        results = []
        for rel in self._mem_rels:
            if direction in ("out", "both") and rel.from_key == key:
                if rel_types and rel.rel_type not in rel_types:
                    continue
                n = self._mem_nodes.get(rel.to_key)
                results.append({
                    "related": n.properties if n else {},
                    "labels": [rel.to_key[0]],
                    "relationship": rel.rel_type,
                })
            elif direction in ("in", "both") and rel.to_key == key:
                if rel_types and rel.rel_type not in rel_types:
                    continue
                n = self._mem_nodes.get(rel.from_key)
                results.append({
                    "related": n.properties if n else {},
                    "labels": [rel.from_key[0]],
                    "relationship": rel.rel_type,
                })
            if len(results) >= limit:
                break
        return results

    async def get_stats(self) -> Dict[str, Any]:
        if not self._driver:
            return {"status": "disconnected"}
        if self._is_neo4j:
            try:
                async with self.session() as session:
                    result = await session.run("""
                        MATCH (n)
                        RETURN labels(n)[0] as label, count(n) as count
                        ORDER BY count DESC
                    """)
                    nodes = await result.data()
                    result2 = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                    rel_count = await result2.data()
                    return {
                        "status": "connected",
                        "backend": "neo4j",
                        "nodes": {r["label"]: r["count"] for r in nodes},
                        "total_relationships": rel_count[0]["rel_count"] if rel_count else 0,
                    }
            except Exception as e:
                return {"status": "error", "message": str(e)}
        # in-memory
        node_counts: Dict[str, int] = {}
        for key in self._mem_nodes:
            node_counts[key[0]] = node_counts.get(key[0], 0) + 1
        return {
            "status": "connected",
            "backend": "memory",
            "nodes": node_counts,
            "total_relationships": len(self._mem_rels),
        }


_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
