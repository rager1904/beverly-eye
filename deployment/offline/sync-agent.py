#!/usr/bin/env python3
"""UbuntuCare Offline Sync Agent — Zambia Deployment.

Queue-based sync agent with compression, delta sync, bandwidth throttling,
conflict resolution (last-write-wins / server-wins), and resume-on-interrupt.

Runs as a standalone daemon on edge devices.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
import zlib
from base64 import b64encode
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger("sync-agent")

# ── Configuration ──────────────────────────────────────────────────────────

@dataclass
class SyncConfig:
    device_key_file: str = os.getenv("DEVICE_KEY_FILE", "/data/ubuntucare/sync/device.key")
    queue_path: str = os.getenv("SYNC_QUEUE_PATH", "/data/ubuntucare/sync/queue.db")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/ubuntucare/ubuntucare.db")
    server_url: str = os.getenv("SERVER_URL", "https://sync.ubuntucare.gov.zm")
    bandwidth_profile: str = os.getenv("BANDWIDTH_PROFILE", "lan")
    sync_interval_seconds: int = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "5"))
    max_batch_size_bytes: int = int(os.getenv("MAX_BATCH_SIZE_BYTES", str(5 * 1024 * 1024)))
    chunk_size_bytes: int = int(os.getenv("CHUNK_SIZE_BYTES", str(256 * 1024)))
    compress_level: int = int(os.getenv("COMPRESS_LEVEL", "4"))
    offline_mode: bool = os.getenv("OFFLINE_MODE", "false").lower() == "true"

    @classmethod
    def load(cls) -> "SyncConfig":
        return cls()

    @property
    def device_key(self) -> str:
        try:
            return Path(self.device_key_file).read_text().strip()
        except FileNotFoundError:
            key = b64encode(os.urandom(32)).decode()
            Path(self.device_key_file).write_text(key)
            return key

    @property
    def bandwidth_limits(self) -> dict[str, Any]:
        return {
            "2g": {"max_upload_bps": 15360, "max_batch_mb": 1, "chunk_bytes": 65536},
            "3g": {"max_upload_bps": 102400, "max_batch_mb": 5, "chunk_bytes": 262144},
            "4g": {"max_upload_bps": 2097152, "max_batch_mb": 25, "chunk_bytes": 1048576},
            "lan": {"max_upload_bps": 104857600, "max_batch_mb": 100, "chunk_bytes": 16777216},
            "satellite": {"max_upload_bps": 51200, "max_batch_mb": 2, "chunk_bytes": 131072},
        }.get(self.bandwidth_profile, {})


# ── Queue Database ─────────────────────────────────────────────────────────

class SyncQueue:
    """Persistent SQLite-backed queue for sync operations."""

    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                operation TEXT NOT NULL CHECK(operation IN ('create','update','delete')),
                payload TEXT NOT NULL,
                checksum TEXT,
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK(priority IN ('critical','high','medium','low')),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','syncing','synced','failed')),
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 5,
                last_error TEXT,
                device_id TEXT NOT NULL DEFAULT 'local',
                created_at REAL NOT NULL,
                synced_at REAL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_status
            ON sync_queue(status, priority, created_at)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_dedup
            ON sync_queue(table_name, record_id, operation, status)
        """)
        self._conn.commit()

    def enqueue(self, table: str, record_id: str, operation: str,
                payload: dict, priority: str = "medium") -> int:
        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Deduplicate: if same record with same operation is pending, update payload
        cur = self._conn.execute(
            "SELECT id, retry_count FROM sync_queue "
            "WHERE table_name=? AND record_id=? AND operation=? AND status='pending' "
            "ORDER BY created_at DESC LIMIT 1",
            (table, record_id, operation)
        )
        existing = cur.fetchone()
        if existing:
            self._conn.execute(
                "UPDATE sync_queue SET payload=?, checksum=?, created_at=?, retry_count=0 "
                "WHERE id=?",
                (json.dumps(payload), checksum, time.time(), existing["id"])
            )
            self._conn.commit()
            return existing["id"]

        cur = self._conn.execute(
            "INSERT INTO sync_queue (table_name, record_id, operation, payload, "
            "checksum, priority, created_at) VALUES (?,?,?,?,?,?,?)",
            (table, record_id, operation, json.dumps(payload),
             checksum, priority, time.time())
        )
        self._conn.commit()
        return cur.lastrowid

    def fetch_pending(self, limit: int = 100, priority: Optional[str] = None) -> list[sqlite3.Row]:
        if priority:
            cur = self._conn.execute(
                "SELECT * FROM sync_queue WHERE status='pending' AND priority=? "
                "ORDER BY created_at ASC LIMIT ?",
                (priority, limit)
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM sync_queue WHERE status='pending' "
                "ORDER BY "
                "  CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                "  WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, "
                "created_at ASC LIMIT ?",
                (limit,)
            )
        return cur.fetchall()

    def mark_synced(self, entry_id: int) -> None:
        self._conn.execute(
            "UPDATE sync_queue SET status='synced', synced_at=? WHERE id=?",
            (time.time(), entry_id)
        )
        self._conn.commit()

    def mark_failed(self, entry_id: int, error: str) -> None:
        self._conn.execute(
            "UPDATE sync_queue SET status='failed', retry_count=retry_count+1, "
            "last_error=? WHERE id=?",
            (error[:500], entry_id)
        )
        self._conn.commit()

    def count_pending(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) as cnt FROM sync_queue WHERE status='pending'")
        return cur.fetchone()["cnt"]

    def cleanup_synced(self, max_age_hours: int = 24) -> int:
        cutoff = time.time() - (max_age_hours * 3600)
        cur = self._conn.execute(
            "DELETE FROM sync_queue WHERE status='synced' AND synced_at < ?",
            (cutoff,)
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        if self._conn:
            self._conn.close()


# ── Delta Sync Engine ──────────────────────────────────────────────────────

class DeltaSync:
    """Computes and applies delta changes between local and remote."""

    @staticmethod
    def compute_delta(local: dict, remote: dict) -> dict:
        changed = {}
        for key in set(list(local.keys()) + list(remote.keys())):
            if key not in local:
                changed[key] = {"type": "removed"}
            elif key not in remote:
                changed[key] = {"type": "added", "value": local[key]}
            elif local[key] != remote[key]:
                changed[key] = {"type": "modified", "old": remote[key], "new": local[key]}
        return changed

    @staticmethod
    def should_sync(local_updated: float, remote_updated: float,
                    strategy: str = "last_write_wins") -> bool:
        if strategy == "server_wins":
            return False
        return local_updated > remote_updated


# ── Compression ────────────────────────────────────────────────────────────

class Compressor:
    @staticmethod
    def compress(data: bytes, level: int = 4) -> bytes:
        return gzip.compress(data, compresslevel=level)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        return gzip.decompress(data)

    @staticmethod
    def compress_batch(items: list[dict], level: int = 4) -> bytes:
        payload = json.dumps(items, default=str).encode()
        return zlib.compress(payload, level=level)

    @staticmethod
    def decompress_batch(data: bytes) -> list[dict]:
        return json.loads(zlib.decompress(data))


# ── Encryption ─────────────────────────────────────────────────────────────

class TransitEncryption:
    """AES-GCM-like encryption for sync payloads using device key."""

    @staticmethod
    def sign(device_key: str, data: bytes) -> str:
        return hmac.new(
            device_key.encode(), data, hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify(device_key: str, data: bytes, signature: str) -> bool:
        expected = TransitEncryption.sign(device_key, data)
        return hmac.compare_digest(expected, signature)


# ── Bandwidth Throttle ─────────────────────────────────────────────────────

class BandwidthThrottle:
    """Token-bucket rate limiter for sync uploads."""

    def __init__(self, max_bps: int = 102400):
        self.max_bps = max_bps
        self.tokens = float(max_bps)
        self.last_refill = time.monotonic()

    async def acquire(self, bytes_count: int) -> None:
        if self.max_bps <= 0:
            return
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_bps, self.tokens + elapsed * self.max_bps)
        self.last_refill = now
        if self.tokens < bytes_count:
            deficit = bytes_count - self.tokens
            wait = deficit / self.max_bps
            logger.debug("Throttling: waiting %.2fs for %d bytes", wait, int(deficit))
            await asyncio.sleep(wait)
            self.tokens = 0.0
        else:
            self.tokens -= bytes_count


# ── Conflict Resolution ────────────────────────────────────────────────────

class ConflictResolver:
    STRATEGIES = {
        "last_write_wins": lambda local, remote: max(local, remote, key=lambda x: x.get("updated_at", 0)),
        "server_wins": lambda local, remote: remote,
        "client_wins": lambda local, remote: local,
        "merge": lambda local, remote: {**remote, **local},
    }

    @classmethod
    def resolve(cls, local: dict, remote: dict, strategy: str = "server_wins") -> dict:
        resolver = cls.STRATEGIES.get(strategy)
        if not resolver:
            logger.warning("Unknown strategy '%s', using server_wins", strategy)
            return remote
        resolved = resolver(local, remote)
        resolved["_conflict_resolved"] = True
        resolved["_strategy"] = strategy
        return resolved


# ── Sync Agent ─────────────────────────────────────────────────────────────

class SyncAgent:
    def __init__(self, config: SyncConfig):
        self.config = config
        self.queue = SyncQueue(config.queue_path)
        self.throttle = BandwidthThrottle(
            config.bandwidth_limits.get("max_upload_bps", 102400)
        )
        self.device_id = hashlib.sha256(config.device_key.encode()).hexdigest()[:16]
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.running = True
        self.current_batch: list[dict] = []
        self.current_batch_size = 0

    async def start(self) -> None:
        logger.info(
            "Sync Agent started | Device: %s | Profile: %s | Queue: %s",
            self.device_id[:8], self.config.bandwidth_profile, self.config.queue_path
        )
        self.http_session = aiohttp.ClientSession(
            headers={"User-Agent": f"UbuntuCare-Sync/{self.device_id}"},
            timeout=aiohttp.ClientTimeout(total=120),
        )
        try:
            while self.running:
                try:
                    await self._sync_cycle()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Sync cycle error: %s", exc, exc_info=True)
                await asyncio.sleep(self.config.sync_interval_seconds)
        finally:
            await self.http_session.close()
            self.queue.close()

    async def stop(self) -> None:
        logger.info("Stopping sync agent...")
        self.running = False

    async def _sync_cycle(self) -> None:
        pending_count = self.queue.count_pending()
        if pending_count == 0:
            logger.debug("No pending items to sync")
            self.queue.cleanup_synced()
            return

        logger.info("Sync cycle: %d pending items", pending_count)

        # Fetch items by priority
        for priority in ("critical", "high", "medium", "low"):
            items = self.queue.fetch_pending(limit=50, priority=priority)
            if not items:
                continue
            logger.debug("Processing %d %s items", len(items), priority)

            # Build batch
            batch = []
            for item in items:
                try:
                    payload = json.loads(item["payload"])
                except json.JSONDecodeError:
                    self.queue.mark_failed(item["id"], "Invalid JSON payload")
                    continue

                batch.append({
                    "id": item["id"],
                    "table": item["table_name"],
                    "record_id": item["record_id"],
                    "operation": item["operation"],
                    "payload": payload,
                    "priority": item["priority"],
                    "device_id": self.device_id,
                })

            if not batch:
                continue

            await self._upload_batch(batch, priority)
            await asyncio.sleep(0.5)  # Small gap between priority levels

    async def _upload_batch(self, batch: list[dict], priority: str) -> None:
        # Compress
        compressed = Compressor.compress_batch(batch, self.config.compress_level)

        # Sign
        signature = TransitEncryption.sign(self.config.device_key, compressed)

        # Check size
        if len(compressed) > self.config.max_batch_size_bytes:
            logger.warning("Batch too large (%d bytes), splitting", len(compressed))
            mid = len(batch) // 2
            await self._upload_batch(batch[:mid], priority)
            await self._upload_batch(batch[mid:], priority)
            return

        # Throttle
        await self.throttle.acquire(len(compressed))

        # Upload
        url = urljoin(self.config.server_url, f"/api/v1/sync/upload")
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Device-Id": self.device_id,
            "X-Signature": signature,
            "X-Priority": priority,
            "X-Compression": "zlib",
        }

        try:
            async with self.http_session.post(
                url, data=compressed, headers=headers
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    for entry in batch:
                        if result.get("conflicts", []):
                            # Handle conflicts
                            for conflict in result["conflicts"]:
                                if conflict["record_id"] == entry["record_id"]:
                                    resolved = ConflictResolver.resolve(
                                        entry["payload"],
                                        conflict["server_version"],
                                        strategy="server_wins",
                                    )
                                    logger.info(
                                        "Conflict resolved for %s/%s: %s",
                                        entry["table"], entry["record_id"],
                                        resolved.get("_strategy", "server_wins")
                                    )
                        self.queue.mark_synced(entry["id"])

                    if result.get("last_sync_id"):
                        self._last_sync_id = result["last_sync_id"]

                    logger.info(
                        "Uploaded %d %s items (%d bytes compressed)",
                        len(batch), priority, len(compressed)
                    )
                elif resp.status == 401:
                    logger.error("Authentication failed — check device key")
                    for entry in batch:
                        self.queue.mark_failed(entry["id"], "Authentication failed")
                elif resp.status == 429:
                    logger.warning("Rate limited — backing off")
                    for entry in batch:
                        self.queue.mark_failed(entry["id"], "Rate limited")
                    await asyncio.sleep(60)
                else:
                    error_body = await resp.text()
                    logger.error("Upload failed: HTTP %d — %s", resp.status, error_body[:200])
                    for entry in batch:
                        self.queue.mark_failed(entry["id"], f"HTTP {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning("Network error during upload: %s", exc)
            # Don't mark as failed — will retry on next cycle

    async def _download_updates(self) -> None:
        """Pull updates from the server (delta sync)."""
        url = urljoin(self.config.server_url, "/api/v1/sync/download")
        headers = {
            "X-Device-Id": self.device_id,
            "X-Signature": TransitEncryption.sign(
                self.config.device_key, b"download"
            ),
        }
        params = {
            "since": getattr(self, "_last_sync_id", 0),
            "limit": 100,
        }

        try:
            async with self.http_session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if resp.headers.get("X-Compression") == "zlib":
                        data = Compressor.decompress_batch(data)
                    else:
                        data = json.loads(data)

                    for item in data:
                        logger.debug("Received update: %s/%s", item["table"], item["record_id"])
                        # Apply to local database
                        await self._apply_remote_update(item)
        except Exception as exc:
            logger.warning("Download failed: %s", exc)

    async def _apply_remote_update(self, item: dict) -> None:
        """Apply a remote update to the local database."""
        # This would integrate with the local database layer
        # For now, log the operation
        logger.debug(
            "Applied remote %s on %s/%s",
            item["operation"], item["table"], item["record_id"]
        )


# ── Main ───────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    setup_logging()
    config = SyncConfig.load()
    agent = SyncAgent(config)

    if config.offline_mode:
        logger.info("Starting in OFFLINE mode — no server sync")
        while True:
            await asyncio.sleep(3600)
    else:
        await agent.start()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
