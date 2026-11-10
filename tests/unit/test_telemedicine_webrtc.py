import base64
import asyncio
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone

from src.backend.config import settings
from src.backend.services.telemedicine import models
from src.backend.services.telemedicine.services import get_invited_consultation, ice_server_config


def test_ice_server_config_uses_only_public_stun_by_default(monkeypatch):
    monkeypatch.setattr(settings, "webrtc_stun_servers", "stun:stun.example.test:3478")
    monkeypatch.setattr(settings, "webrtc_turn_url", "")
    monkeypatch.setattr(settings, "webrtc_turn_secret", "")

    assert ice_server_config("room-1") == [{"urls": ["stun:stun.example.test:3478"]}]


def test_turn_credentials_are_short_lived_and_derived_server_side(monkeypatch):
    secret = "test-coturn-secret"
    monkeypatch.setattr(settings, "webrtc_stun_servers", "")
    monkeypatch.setattr(settings, "webrtc_turn_url", "turn:turn.example.test:3478,turns:turn.example.test:5349")
    monkeypatch.setattr(settings, "webrtc_turn_secret", secret)

    turn = ice_server_config("consultation-123")[0]
    expiry, identity = turn["username"].split(":", 1)
    expected = base64.b64encode(
        hmac.new(secret.encode(), turn["username"].encode(), hashlib.sha1).digest()
    ).decode("ascii")

    assert identity == "consultation-123"
    assert int(time.time()) < int(expiry) <= int(time.time()) + 3600
    assert turn["credential"] == expected
    assert turn["urls"] == ["turn:turn.example.test:3478", "turns:turn.example.test:5349"]


def test_invite_tokens_are_verified_by_hash_and_expiry():
    consultation_id = uuid.uuid4()
    raw_token = "high-entropy-invite"
    consultation = models.Teleconsultation(
        id=consultation_id,
        hospital_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        provider_id=uuid.uuid4(),
        consultation_type=models.ConsultationType.video,
        status=models.ConsultationStatus.scheduled,
    )
    waiting_room = models.WaitingRoom(
        id=uuid.uuid4(),
        hospital_id=consultation.hospital_id,
        consultation_id=consultation_id,
        invite_token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        invite_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5),
        is_active=True,
    )

    class Result:
        def one_or_none(self):
            return consultation, waiting_room

    class Session:
        async def execute(self, _statement):
            return Result()

    valid = asyncio.run(get_invited_consultation(Session(), consultation_id, raw_token))
    invalid = asyncio.run(get_invited_consultation(Session(), consultation_id, "wrong-token"))
    assert valid == (consultation, waiting_room)
    assert invalid is None

    waiting_room.invite_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
    expired = asyncio.run(get_invited_consultation(Session(), consultation_id, raw_token))
    assert expired is None
