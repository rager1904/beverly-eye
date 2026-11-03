import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.emr.schemas import (
    AllergyCreate,
    AllergyResponse,
    FamilyHistoryCreate,
    FamilyHistoryResponse,
    ImmunizationCreate,
    ImmunizationResponse,
    MedicationCreate,
    MedicationResponse,
    PatientCreate,
    PatientResponse,
    PatientSummary,
    PatientUpdate,
    ProblemCreate,
    ProblemResponse,
    SocialHistoryCreate,
    SocialHistoryResponse,
)
from src.backend.services.emr.services import (
    AllergyService,
    FamilyHistoryService,
    ImmunizationService,
    MedicationService,
    PatientService,
    ProblemListService,
    SocialHistoryService,
    FHIRConverter,
)

router = APIRouter()


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(data: PatientCreate, session: EMRSession = Depends(get_emr_session)):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    try:
        patient = await service.register_patient(data)
        return patient
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    patient = await service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.get("", response_model=dict)
async def search_patients(
    query: Optional[str] = Query(None),
    nrc_number: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: EMRSession = Depends(get_emr_session),
):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    patients, total = await service.search_patients(query, nrc_number, phone, province, page, per_page)
    return {
        "items": [PatientSummary.model_validate(p) for p in patients],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: uuid.UUID, data: PatientUpdate, session: EMRSession = Depends(get_emr_session)):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    patient = await service.update_patient(patient_id, data)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    deleted = await service.soft_delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


@router.get("/{patient_id}/fhir")
async def get_patient_fhir(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = PatientService(session.db, session.hospital_id, session.user_id, session.user_name)
    patient = await service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return FHIRConverter.patient_to_fhir(patient)


# ─── Allergies ─────────────────────────────────────────────────────────────────
@router.post("/{patient_id}/allergies", response_model=AllergyResponse, status_code=status.HTTP_201_CREATED)
async def add_allergy(patient_id: uuid.UUID, data: AllergyCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = AllergyService(session.db, session.hospital_id)
    return await service.add_allergy(data)


@router.get("/{patient_id}/allergies", response_model=list[AllergyResponse])
async def get_allergies(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = AllergyService(session.db, session.hospital_id)
    return await service.get_patient_allergies(patient_id)


# ─── Medications ───────────────────────────────────────────────────────────────
@router.post("/{patient_id}/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def prescribe_medication(patient_id: uuid.UUID, data: MedicationCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = MedicationService(session.db, session.hospital_id)
    return await service.prescribe(data)


@router.get("/{patient_id}/medications", response_model=list[MedicationResponse])
async def get_medications(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = MedicationService(session.db, session.hospital_id)
    return await service.get_patient_medications(patient_id)


# ─── Immunizations ─────────────────────────────────────────────────────────────
@router.post("/{patient_id}/immunizations", response_model=ImmunizationResponse, status_code=status.HTTP_201_CREATED)
async def add_immunization(patient_id: uuid.UUID, data: ImmunizationCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = ImmunizationService(session.db, session.hospital_id)
    return await service.add_immunization(data)


@router.get("/{patient_id}/immunizations", response_model=list[ImmunizationResponse])
async def get_immunizations(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = ImmunizationService(session.db, session.hospital_id)
    return await service.get_patient_immunizations(patient_id)


# ─── Problem List ──────────────────────────────────────────────────────────────
@router.post("/{patient_id}/problems", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def add_problem(patient_id: uuid.UUID, data: ProblemCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = ProblemListService(session.db, session.hospital_id)
    return await service.add_problem(data)


@router.get("/{patient_id}/problems", response_model=list[ProblemResponse])
async def get_active_problems(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = ProblemListService(session.db, session.hospital_id)
    return await service.get_active_problems(patient_id)


# ─── Social History ────────────────────────────────────────────────────────────
@router.post("/{patient_id}/social-history", response_model=SocialHistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_social_history(patient_id: uuid.UUID, data: SocialHistoryCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = SocialHistoryService(session.db, session.hospital_id)
    return await service.add_social_history(data)


@router.get("/{patient_id}/social-history", response_model=list[SocialHistoryResponse])
async def get_social_history(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = SocialHistoryService(session.db, session.hospital_id)
    return await service.get_patient_social_history(patient_id)


# ─── Family History ────────────────────────────────────────────────────────────
@router.post("/{patient_id}/family-history", response_model=FamilyHistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_family_history(patient_id: uuid.UUID, data: FamilyHistoryCreate, session: EMRSession = Depends(get_emr_session)):
    data.patient_id = patient_id
    service = FamilyHistoryService(session.db, session.hospital_id)
    return await service.add_family_history(data)


@router.get("/{patient_id}/family-history", response_model=list[FamilyHistoryResponse])
async def get_family_history(patient_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = FamilyHistoryService(session.db, session.hospital_id)
    return await service.get_patient_family_history(patient_id)
