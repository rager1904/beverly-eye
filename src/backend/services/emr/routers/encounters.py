import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.emr.schemas import (
    DiagnosisCreate,
    DiagnosisResponse,
    DiagnosisUpdate,
    EncounterCreate,
    EncounterResponse,
    EncounterUpdate,
    MedicationResponse,
)
from src.backend.services.emr.services import (
    DiagnosisService,
    EncounterService,
    MedicationService,
    FHIRConverter,
)

router = APIRouter()


@router.post("", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
async def create_encounter(data: EncounterCreate, session: EMRSession = Depends(get_emr_session)):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    return await service.create_encounter(data)


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(encounter_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    encounter = await service.get_encounter(encounter_id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.get("", response_model=dict)
async def list_encounters(
    patient_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    encounter_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: EMRSession = Depends(get_emr_session),
):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    encounters, total = await service.list_encounters(patient_id, status, encounter_type, from_date, to_date, page, per_page)
    return {
        "items": [EncounterResponse.model_validate(e) for e in encounters],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.patch("/{encounter_id}", response_model=EncounterResponse)
async def update_encounter(encounter_id: uuid.UUID, data: EncounterUpdate, session: EMRSession = Depends(get_emr_session)):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    encounter = await service.update_encounter(encounter_id, data)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.post("/{encounter_id}/discharge", response_model=EncounterResponse)
async def discharge_patient(encounter_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    encounter = await service.discharge(encounter_id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return encounter


@router.get("/{encounter_id}/fhir")
async def get_encounter_fhir(encounter_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = EncounterService(session.db, session.hospital_id, session.user_id, session.user_name)
    encounter = await service.get_encounter(encounter_id)
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
    return FHIRConverter.encounter_to_fhir(encounter)


# ─── Diagnoses ─────────────────────────────────────────────────────────────────
@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
async def add_diagnosis(encounter_id: uuid.UUID, data: DiagnosisCreate, session: EMRSession = Depends(get_emr_session)):
    data.encounter_id = encounter_id
    service = DiagnosisService(session.db, session.hospital_id)
    return await service.add_diagnosis(data)


@router.get("/{encounter_id}/diagnoses", response_model=list[DiagnosisResponse])
async def get_encounter_diagnoses(encounter_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = DiagnosisService(session.db, session.hospital_id)
    return await service.get_encounter_diagnoses(encounter_id)


@router.patch("/{encounter_id}/diagnoses/{diagnosis_id}", response_model=DiagnosisResponse)
async def update_diagnosis(
    encounter_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
    data: DiagnosisUpdate,
    session: EMRSession = Depends(get_emr_session),
):
    service = DiagnosisService(session.db, session.hospital_id)
    diagnosis = await service.update_diagnosis(diagnosis_id, data)
    if not diagnosis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found")
    return diagnosis


@router.get("/icd10/search", response_model=list[dict])
async def search_icd10(query: str = Query(..., min_length=2), session: EMRSession = Depends(get_emr_session)):
    service = DiagnosisService(session.db, session.hospital_id)
    return await service.search_icd10(query)
