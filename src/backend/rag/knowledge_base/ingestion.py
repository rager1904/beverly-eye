from __future__ import annotations

import hashlib
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import aiofiles
import httpx
from pypdf import PdfReader

from src.backend.core.config.settings import settings
from src.backend.rag.embeddings.service import embed_batch, embed_texts
from src.backend.rag.vector_store.pgvector_client import pgvector_store
from src.backend.rag.vector_store.qdrant_client import qdrant_store

logger = logging.getLogger("ubuntucare.rag.ingestion")

CHUNK_SIZES = {"semantic": 512, "recursive": 256, "sliding": 128}
CHUNK_OVERLAP = 32


def _doc_id(content: str, source: str) -> str:
    raw = f"{source}:{content[:200]}"
    return hashlib.md5(raw.encode()).hexdigest()


def split_semantic(text: str, max_chunks: Optional[int] = None) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sent in sentences:
        sent_len = len(sent.split())
        if current_len + sent_len > CHUNK_SIZES["semantic"] and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(sent)
        current_len += sent_len
    if current:
        chunks.append(" ".join(current))
    if max_chunks:
        chunks = chunks[:max_chunks]
    return chunks or [text]


def split_recursive(text: str, max_chunks: Optional[int] = None) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        para_len = len(para.split())
        if current_len + para_len > CHUNK_SIZES["recursive"] and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len
    if current:
        chunks.append("\n\n".join(current))
    if max_chunks:
        chunks = chunks[:max_chunks]
    return chunks or [text]


def split_sliding_window(text: str, max_chunks: Optional[int] = None) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZES["sliding"], len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += CHUNK_SIZES["sliding"] - CHUNK_OVERLAP
    if max_chunks:
        chunks = chunks[:max_chunks]
    return chunks or [text]


def extract_metadata(text: str, source: Optional[str] = None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    if source:
        meta["source"] = source
    title_match = re.search(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()
    word_count = len(text.split())
    meta["word_count"] = word_count
    char_count = len(text)
    meta["char_count"] = char_count
    return meta


async def parse_pdf(path: str | Path) -> str:
    reader = PdfReader(str(path))
    texts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texts.append(page_text)
    return "\n\n".join(texts)


async def parse_html(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


async def parse_markdown(md: str) -> str:
    return md


async def parse_document(
    content: bytes | str,
    source_type: str = "text",
    source_url: Optional[str] = None,
) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {"source_type": source_type}
    if source_url:
        meta["source_url"] = source_url

    if source_type == "pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            if isinstance(content, str):
                content = content.encode()
            tmp.write(content)
            tmp_path = tmp.name
        text = await parse_pdf(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)
    elif source_type == "html":
        text = await parse_html(content if isinstance(content, str) else content.decode("utf-8", errors="replace"))
    elif source_type == "markdown":
        text = await parse_markdown(content if isinstance(content, str) else content.decode("utf-8", errors="replace"))
    else:
        text = content if isinstance(content, str) else content.decode("utf-8", errors="replace")

    meta.update(extract_metadata(text, source=source_url))
    return text, meta


async def ingest_document(
    content: bytes | str,
    *,
    source_type: str = "text",
    source_url: Optional[str] = None,
    title: Optional[str] = None,
    chunk_strategy: str = "recursive",
    hospital_id: Optional[str] = None,
    department: Optional[str] = None,
    specialty: Optional[str] = None,
    language: Optional[str] = None,
    author: Optional[str] = None,
    published_date: Optional[str] = None,
    version: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> int:
    text, parsed_meta = await parse_document(content, source_type, source_url)
    splitter_map = {
        "semantic": split_semantic,
        "recursive": split_recursive,
        "sliding": split_sliding_window,
    }
    splitter = splitter_map.get(chunk_strategy, split_recursive)
    chunks = splitter(text)
    logger.info("Ingesting %d chunks from '%s'", len(chunks), title or source_url or "unknown")

    embeddings = await embed_batch(chunks)
    chunk_meta_base = {
        "source_type": source_type,
        "source_url": source_url,
        "title": title or parsed_meta.get("title"),
        "hospital_id": hospital_id,
        "department": department,
        "specialty": specialty,
        "language": language or "en",
        "author": author,
        "published_date": published_date,
        "version": version,
        "metadata": {**(metadata or {}), **parsed_meta},
    }
    doc_count = 0
    qdrant_points: list[dict[str, Any]] = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        doc_id = _doc_id(chunk, source_url or str(i))
        chunk_meta = {**chunk_meta_base, "chunk_index": i, "total_chunks": len(chunks)}
        await pgvector_store.insert(
            content=chunk,
            embedding=emb,
            external_id=doc_id,
            title=chunk_meta["title"],
            source_type=source_type,
            source_url=source_url,
            hospital_id=hospital_id,
            department=department,
            specialty=specialty,
            author=author,
            published_date=published_date,
            version=version,
            metadata=chunk_meta,
            language=language or "en",
        )
        qdrant_points.append({
            "id": doc_id,
            "vector": emb,
            "payload": chunk_meta,
        })
        doc_count += 1

    if qdrant_points:
        qdrant_store.ensure_collection(vector_size=len(embeddings[0]) if embeddings else 1024)
        qdrant_store.upsert_points(qdrant_points)

    return doc_count


async def ingest_from_url(
    url: str,
    source_type: Optional[str] = None,
    **kwargs: Any,
) -> int:
    inferred_type = source_type or _infer_source_type(url)
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
    return await ingest_document(
        content,
        source_type=inferred_type,
        source_url=url,
        **kwargs,
    )


def _infer_source_type(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith(".html") or path.endswith(".htm"):
        return "html"
    if path.endswith(".md"):
        return "markdown"
    return "html"


async def delete_document(external_id: str) -> bool:
    return await pgvector_store.delete_by_filter(external_id=external_id) > 0


async def get_knowledge_base_stats() -> dict[str, Any]:
    total_docs = await pgvector_store.count()
    qdrant_count = qdrant_store.count_points()
    return {
        "pgvector_documents": total_docs,
        "qdrant_points": qdrant_count,
        "total": total_docs + qdrant_count,
    }
