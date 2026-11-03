import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from src.backend.config import settings
from .templates import NotificationTemplates

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"
    ussd = "ussd"
    push = "push"


class NotificationPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class NotificationRequest(BaseModel):
    recipient: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.normal
    language: str = "en"
    patient_id: Optional[uuid.UUID] = None
    hospital_id: Optional[uuid.UUID] = None
    template_name: Optional[str] = None
    template_params: Optional[dict] = None


class NotificationResult(BaseModel):
    success: bool
    channel: NotificationChannel
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AfricaTalkingService:
    """SMS via Africa's Talking API."""

    BASE_URL = "https://api.africastalking.com/version1/messaging"

    def __init__(self):
        self.username = settings.africas_talking_username
        self.api_key = settings.africas_talking_api_key
        self.sender_id = settings.africas_talking_sender_id
        self.enabled = bool(self.api_key and self.username)

    async def send(self, to: str, message: str) -> NotificationResult:
        if not self.enabled:
            logger.warning("Africa's Talking not configured. Message queued.")
            return NotificationResult(
                success=False, channel=NotificationChannel.sms, provider="africas_talking",
                error="Not configured",
            )
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                data = {
                    "username": self.username,
                    "to": to,
                    "message": message,
                }
                if self.sender_id:
                    data["from"] = self.sender_id
                resp = await client.post(
                    self.BASE_URL,
                    data=data,
                    headers={
                        "apiKey": self.api_key,
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                if resp.status_code == 201:
                    result = resp.json()
                    msg_id = None
                    if result.get("SMSMessageData", {}).get("Recipients"):
                        msg_id = result["SMSMessageData"]["Recipients"][0].get("messageId")
                    logger.info(f"SMS sent to {to}: {message[:50]}...")
                    return NotificationResult(
                        success=True, channel=NotificationChannel.sms, provider="africas_talking",
                        message_id=msg_id,
                    )
                else:
                    logger.error(f"Africa's Talking error: {resp.status_code} {resp.text}")
                    return NotificationResult(
                        success=False, channel=NotificationChannel.sms, provider="africas_talking",
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            logger.error(f"Africa's Talking exception: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.sms, provider="africas_talking",
                error=str(e),
            )


class TwilioWhatsAppService:
    """WhatsApp via Twilio API."""

    BASE_URL = "https://api.twilio.com/2010-04-01/Accounts"

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_whatsapp_number
        self.enabled = bool(self.account_sid and self.auth_token and self.from_number)

    async def send(self, to: str, message: str) -> NotificationResult:
        if not self.enabled:
            logger.warning("Twilio WhatsApp not configured.")
            return NotificationResult(
                success=False, channel=NotificationChannel.whatsapp, provider="twilio",
                error="Not configured",
            )
        try:
            clean_to = to.replace("+", "").replace(" ", "")
            clean_from = self.from_number.replace("+", "").replace(" ", "")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/{self.account_sid}/Messages.json",
                    data={
                        "To": f"whatsapp:+{clean_to}",
                        "From": f"whatsapp:+{clean_from}",
                        "Body": message,
                    },
                    auth=(self.account_sid, self.auth_token),
                )
                if resp.status_code in (200, 201):
                    result = resp.json()
                    logger.info(f"WhatsApp sent to {to}: {message[:50]}...")
                    return NotificationResult(
                        success=True, channel=NotificationChannel.whatsapp, provider="twilio",
                        message_id=result.get("sid"),
                    )
                else:
                    logger.error(f"Twilio error: {resp.status_code} {resp.text}")
                    return NotificationResult(
                        success=False, channel=NotificationChannel.whatsapp, provider="twilio",
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except Exception as e:
            logger.error(f"Twilio exception: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.whatsapp, provider="twilio",
                error=str(e),
            )


class EmailService:
    """Email via SMTP."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_addr = settings.smtp_from
        self.enabled = bool(self.host and self.user)

    async def send(self, to: str, subject: str, message: str) -> NotificationResult:
        if not self.enabled:
            logger.warning("SMTP not configured.")
            return NotificationResult(
                success=False, channel=NotificationChannel.email, provider="smtp",
                error="Not configured",
            )
        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = self.from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(message)

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=True,
            )
            logger.info(f"Email sent to {to}: {subject}")
            return NotificationResult(
                success=True, channel=NotificationChannel.email, provider="smtp",
            )
        except Exception as e:
            logger.error(f"Email exception: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.email, provider="smtp",
                error=str(e),
            )


class USSDService:
    """USSD for feature phones."""

    async def send(self, phone: str, message: str) -> NotificationResult:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.africas_talking_api_url}/ussd/send"
                    if hasattr(settings, "africas_talking_api_url") and settings.africas_talking_api_url
                    else "https://api.africastalking.com/version1/ussd/push",
                    json={
                        "username": settings.africas_talking_username,
                        "phoneNumber": phone,
                        "message": message,
                    },
                    headers={"apiKey": settings.africas_talking_api_key},
                )
                if resp.status_code == 201:
                    return NotificationResult(
                        success=True, channel=NotificationChannel.ussd, provider="africas_talking",
                    )
                return NotificationResult(
                    success=False, channel=NotificationChannel.ussd, provider="africas_talking",
                    error=resp.text[:200],
                )
        except Exception as e:
            logger.error(f"USSD error: {e}")
            return NotificationResult(
                success=False, channel=NotificationChannel.ussd, provider="africas_talking",
                error=str(e),
            )


class NotificationService:
    """Orchestrates multi-channel notification delivery with offline queue."""

    def __init__(self):
        self.sms = AfricaTalkingService()
        self.whatsapp = TwilioWhatsAppService()
        self.email = EmailService()
        self.ussd = USSDService()
        self.offline_queue: list[NotificationRequest] = []
        self.templates = NotificationTemplates()

    async def send(
        self,
        request: NotificationRequest,
    ) -> NotificationResult:
        message = request.message
        if request.template_name:
            params = request.template_params or {}
            template_fn = getattr(self.templates, request.template_name, None)
            if template_fn:
                message = template_fn(lang=request.language, **params)

        channel_map = {
            NotificationChannel.sms: self.sms.send,
            NotificationChannel.whatsapp: self.whatsapp.send,
            NotificationChannel.email: self.email.send,
            NotificationChannel.ussd: self.ussd.send,
        }

        sender = channel_map.get(request.channel)
        if not sender:
            return NotificationResult(
                success=False, channel=request.channel, provider="unknown",
                error=f"Unsupported channel: {request.channel}",
            )

        result = await sender(request.recipient, message)
        if not result.success and request.priority == NotificationPriority.low:
            self.offline_queue.append(request)
            logger.info(f"Queued offline notification for {request.recipient}")

        return result

    async def flush_offline_queue(self) -> list[NotificationResult]:
        results = []
        remaining = []
        for req in self.offline_queue:
            result = await self.send(req)
            results.append(result)
            if not result.success:
                remaining.append(req)
        self.offline_queue = remaining
        return results

    async def send_appointment_reminder(
        self,
        phone: str,
        patient_name: str,
        datetime_str: str,
        facility: str,
        lang: str = "en",
    ) -> NotificationResult:
        message = self.templates.appointment_reminder(patient_name, datetime_str, facility, lang)
        return await self.send(
            NotificationRequest(
                recipient=phone,
                message=message,
                channel=NotificationChannel.sms,
                language=lang,
            )
        )

    async def send_test_results(
        self,
        phone: str,
        patient_name: str,
        test_name: str,
        lang: str = "en",
    ) -> NotificationResult:
        message = self.templates.test_results_ready(patient_name, test_name, lang)
        return await self.send(
            NotificationRequest(
                recipient=phone,
                message=message,
                channel=NotificationChannel.sms,
                language=lang,
            )
        )

    async def send_medication_reminder(
        self,
        phone: str,
        patient_name: str,
        medication: str,
        dosage: str,
        frequency: str,
        lang: str = "en",
    ) -> NotificationResult:
        message = self.templates.medication_reminder(patient_name, medication, dosage, frequency, lang)
        return await self.send(
            NotificationRequest(
                recipient=phone,
                message=message,
                channel=NotificationChannel.sms,
                language=lang,
            )
        )

    async def broadcast_health_tip(
        self,
        recipients: list[str],
        tip_type: str,
        lang: str = "en",
    ) -> list[NotificationResult]:
        message = self.templates.health_tip(tip_type, lang)
        results = []
        for phone in recipients:
            result = await self.send(
                NotificationRequest(
                    recipient=phone,
                    message=message,
                    channel=NotificationChannel.sms,
                    language=lang,
                )
            )
            results.append(result)
        return results
