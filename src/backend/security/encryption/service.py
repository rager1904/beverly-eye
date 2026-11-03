from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.backend.core.config.settings import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    pass


class KeyManagementError(EncryptionError):
    pass


@dataclass
class EncryptedData:
    ciphertext: str
    iv: str
    key_id: str
    algorithm: str = "AES-256-GCM"
    tag: str = ""

    def encode(self) -> str:
        return base64.b64encode(
            json.dumps({
                "ciphertext": self.ciphertext,
                "iv": self.iv,
                "key_id": self.key_id,
                "algorithm": self.algorithm,
            }).encode()
        ).decode()

    @classmethod
    def decode(cls, data: str) -> EncryptedData:
        raw = json.loads(base64.b64decode(data).decode())
        return cls(
            ciphertext=raw["ciphertext"],
            iv=raw["iv"],
            key_id=raw.get("key_id", ""),
            algorithm=raw.get("algorithm", "AES-256-GCM"),
        )


class KeyManager:
    def __init__(self, master_key: bytes | None = None):
        self._master_key = master_key or self._load_master_key()
        self._current_key_id = f"key-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self._key_cache: dict[str, bytes] = {}
        self._derive_key(self._current_key_id)

    def _load_master_key(self) -> bytes:
        key_from_env = os.environ.get("ENCRYPTION_MASTER_KEY")
        if key_from_env:
            return base64.b64decode(key_from_env)
        derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        logger.warning("Using derived master key from SECRET_KEY. Set ENCRYPTION_MASTER_KEY in production.")
        return derived

    def _derive_key(self, key_id: str) -> bytes:
        if key_id not in self._key_cache:
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=key_id.encode("utf-8"),
            )
            self._key_cache[key_id] = hkdf.derive(self._master_key)
        return self._key_cache[key_id]

    def get_key(self, key_id: str) -> bytes:
        if key_id not in self._key_cache:
            return self._derive_key(key_id)
        return self._key_cache[key_id]

    def rotate_key(self) -> str:
        new_key_id = f"key-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-rotated"
        self._derive_key(new_key_id)
        self._current_key_id = new_key_id
        return new_key_id

    @property
    def current_key_id(self) -> str:
        return self._current_key_id


class EncryptionService:
    def __init__(self, key_manager: KeyManager | None = None):
        self.key_manager = key_manager or KeyManager()

    def encrypt(self, plaintext: str, aad: bytes | None = None) -> EncryptedData:
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty data")
        key_id = self.key_manager.current_key_id
        key = self.key_manager.get_key(key_id)
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        data = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(iv, data, aad or b"")
        return EncryptedData(
            ciphertext=base64.b64encode(ciphertext).decode(),
            iv=base64.b64encode(iv).decode(),
            key_id=key_id,
            algorithm="AES-256-GCM",
        )

    def decrypt(self, encrypted: EncryptedData, aad: bytes | None = None) -> str:
        key = self.key_manager.get_key(encrypted.key_id)
        aesgcm = AESGCM(key)
        iv = base64.b64decode(encrypted.iv)
        ciphertext = base64.b64decode(encrypted.ciphertext)
        plaintext = aesgcm.decrypt(iv, ciphertext, aad or b"")
        return plaintext.decode("utf-8")

    def encrypt_field(self, value: str, context: str = "") -> str:
        aad = context.encode("utf-8") if context else None
        encrypted = self.encrypt(value, aad)
        return encrypted.encode()

    def decrypt_field(self, encrypted_str: str, context: str = "") -> str:
        aad = context.encode("utf-8") if context else None
        encrypted = EncryptedData.decode(encrypted_str)
        return self.decrypt(encrypted, aad)

    def encrypt_dict(self, data: dict, fields_to_encrypt: list[str]) -> dict:
        result = {}
        for key, value in data.items():
            if key in fields_to_encrypt and isinstance(value, str):
                try:
                    result[key] = self.encrypt_field(value, key)
                except Exception as e:
                    logger.error("Failed to encrypt field %s: %s", key, e)
                    result[key] = value
            else:
                result[key] = value
        return result

    def decrypt_dict(self, data: dict, fields_to_decrypt: list[str]) -> dict:
        result = {}
        for key, value in data.items():
            if key in fields_to_decrypt and isinstance(value, str) and value:
                try:
                    result[key] = self.decrypt_field(value, key)
                except Exception as e:
                    logger.error("Failed to decrypt field %s: %s", key, e)
                    result[key] = value
            else:
                result[key] = value
        return result

    def generate_field_key(self, context: str) -> str:
        derived = hashlib.blake2b(
            (context + settings.SECRET_KEY).encode("utf-8"),
            digest_size=16,
        ).hexdigest()
        return derived

    @staticmethod
    def mask_phi(value: str, visible_chars: int = 4) -> str:
        if len(value) <= visible_chars:
            return value
        return value[:visible_chars] + "*" * (len(value) - visible_chars)

    @staticmethod
    def mask_email(email: str) -> str:
        if "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            return f"{local[0]}*@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"

    @staticmethod
    def mask_nrc(nrc: str) -> str:
        if len(nrc) >= 4:
            return nrc[:-4] + "****"
        return nrc


class DatabaseEncryption:
    def __init__(self, encryption_service: EncryptionService | None = None):
        self.encryption_service = encryption_service or EncryptionService()

    def encrypt_column(self, value: str) -> str:
        return self.encryption_service.encrypt_field(value, "db_column")

    def decrypt_column(self, value: str) -> str:
        return self.encryption_service.decrypt_field(value, "db_column")


class BackupEncryption:
    def __init__(self, encryption_service: EncryptionService | None = None):
        self.encryption_service = encryption_service or EncryptionService()

    def encrypt_backup(self, data: bytes) -> bytes:
        key_id = self.encryption_service.key_manager.current_key_id
        key = self.encryption_service.key_manager.get_key(key_id)
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv, data, b"backup")
        header = json.dumps({"key_id": key_id, "iv": base64.b64encode(iv).decode()}).encode()
        return header + b"\n" + ciphertext

    def decrypt_backup(self, data: bytes) -> bytes:
        header_bytes, ciphertext = data.split(b"\n", 1)
        header = json.loads(header_bytes.decode())
        key = self.encryption_service.key_manager.get_key(header["key_id"])
        aesgcm = AESGCM(key)
        iv = base64.b64decode(header["iv"])
        return aesgcm.decrypt(iv, ciphertext, b"backup")


encryption_service = EncryptionService()
database_encryption = DatabaseEncryption(encryption_service)
backup_encryption = BackupEncryption(encryption_service)
