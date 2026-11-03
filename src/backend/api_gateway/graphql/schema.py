import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info as StrawberryInfo

from src.backend.config import settings

logger = logging.getLogger(__name__)


@strawberry.type
class Patient:
    id: str
    nrc: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: Optional[str] = None
    email: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    smartcare_id: Optional[str] = None


@strawberry.type
class Encounter:
    id: str
    patient_id: str
    provider_id: str
    facility_id: str
    encounter_type: str
    encounter_date: str
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    vitals: Optional[str] = None
    notes: Optional[str] = None


@strawberry.type
class Appointment:
    id: str
    patient_id: str
    provider_id: str
    facility_id: str
    appointment_date: str
    appointment_type: str
    status: str
    created_at: str
    updated_at: Optional[str] = None


@strawberry.type
class ClinicalNote:
    id: str
    patient_id: str
    encounter_id: str
    provider_id: str
    note_type: str
    content: str
    created_at: str
    updated_at: Optional[str] = None


@strawberry.type
class AnalyticsSummary:
    total_patients: int
    total_encounters: int
    total_appointments: int
    total_telemedicine_sessions: int
    active_disease_outbreaks: int
    bed_occupancy_rate: float
    average_wait_time_minutes: float
    period_start: str
    period_end: str


@strawberry.type
class Query:
    @strawberry.field
    async def patient(self, id: str) -> Optional[Patient]:
        return Patient(
            id=id,
            nrc="123456/78/1",
            first_name="Grace",
            last_name="Banda",
            date_of_birth="1990-05-15",
            gender="female",
            phone="+260977000001",
            district="Lusaka",
            province="Lusaka",
        )

    @strawberry.field
    async def patients(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> List[Patient]:
        return []

    @strawberry.field
    async def encounter(self, id: str) -> Optional[Encounter]:
        return None

    @strawberry.field
    async def encounters(
        self,
        patient_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Encounter]:
        return []

    @strawberry.field
    async def appointment(self, id: str) -> Optional[Appointment]:
        return None

    @strawberry.field
    async def appointments(
        self,
        patient_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Appointment]:
        return []

    @strawberry.field
    async def clinical_note(self, id: str) -> Optional[ClinicalNote]:
        return None

    @strawberry.field
    async def clinical_notes(
        self,
        patient_id: Optional[str] = None,
        encounter_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ClinicalNote]:
        return []

    @strawberry.field
    async def analytics(
        self,
        facility_id: Optional[str] = None,
        period_start: str = "",
        period_end: str = "",
    ) -> AnalyticsSummary:
        return AnalyticsSummary(
            total_patients=0,
            total_encounters=0,
            total_appointments=0,
            total_telemedicine_sessions=0,
            active_disease_outbreaks=0,
            bed_occupancy_rate=0.0,
            average_wait_time_minutes=0.0,
            period_start=period_start,
            period_end=period_end,
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_patient(
        self,
        nrc: str,
        first_name: str,
        last_name: str,
        date_of_birth: str,
        gender: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        village: Optional[str] = None,
        district: Optional[str] = None,
        province: Optional[str] = None,
    ) -> Patient:
        return Patient(
            id="new-uuid",
            nrc=nrc,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            phone=phone,
            email=email,
            village=village,
            district=district,
            province=province,
        )

    @strawberry.mutation
    async def update_patient(
        self,
        id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        village: Optional[str] = None,
        district: Optional[str] = None,
        province: Optional[str] = None,
    ) -> Optional[Patient]:
        return None

    @strawberry.mutation
    async def create_appointment(
        self,
        patient_id: str,
        provider_id: str,
        facility_id: str,
        appointment_date: str,
        appointment_type: str,
    ) -> Appointment:
        return Appointment(
            id="new-uuid",
            patient_id=patient_id,
            provider_id=provider_id,
            facility_id=facility_id,
            appointment_date=appointment_date,
            appointment_type=appointment_type,
            status="scheduled",
            created_at=datetime.utcnow().isoformat(),
        )

    @strawberry.mutation
    async def update_appointment_status(
        self,
        id: str,
        status: str,
    ) -> Optional[Appointment]:
        return None

    @strawberry.mutation
    async def create_clinical_note(
        self,
        patient_id: str,
        encounter_id: str,
        provider_id: str,
        note_type: str,
        content: str,
    ) -> ClinicalNote:
        return ClinicalNote(
            id="new-uuid",
            patient_id=patient_id,
            encounter_id=encounter_id,
            provider_id=provider_id,
            note_type=note_type,
            content=content,
            created_at=datetime.utcnow().isoformat(),
        )


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def appointment_updates(self, facility_id: str) -> AsyncGenerator[Appointment, None]:
        yield Appointment(
            id="update-uuid",
            patient_id="patient-id",
            provider_id="provider-id",
            facility_id=facility_id,
            appointment_date=datetime.utcnow().isoformat(),
            appointment_type="general",
            status="updated",
            created_at=datetime.utcnow().isoformat(),
        )

    @strawberry.subscription
    async def encounter_created(self, facility_id: str) -> AsyncGenerator[Encounter, None]:
        yield Encounter(
            id="encounter-uuid",
            patient_id="patient-id",
            provider_id="provider-id",
            facility_id=facility_id,
            encounter_type="consultation",
            encounter_date=datetime.utcnow().isoformat(),
        )


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
graphql_app = GraphQLRouter(schema, graphql_ide="apollo-sandbox")
