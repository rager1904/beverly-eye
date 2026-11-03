import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.emr.schemas import (
    ClinicalNoteCreate,
    ClinicalNoteResponse,
    ClinicalNoteUpdate,
)
from src.backend.services.emr.services import ClinicalNoteService

router = APIRouter()


@router.post("", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(data: ClinicalNoteCreate, session: EMRSession = Depends(get_emr_session)):
    service = ClinicalNoteService(session.db, session.hospital_id, session.user_id, session.user_name)
    return await service.create_note(data)


@router.get("/{note_id}", response_model=ClinicalNoteResponse)
async def get_note(note_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = ClinicalNoteService(session.db, session.hospital_id, session.user_id, session.user_name)
    note = await service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
    return note


@router.get("", response_model=dict)
async def list_notes(
    patient_id: Optional[uuid.UUID] = Query(None),
    encounter_id: Optional[uuid.UUID] = Query(None),
    note_type: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: EMRSession = Depends(get_emr_session),
):
    service = ClinicalNoteService(session.db, session.hospital_id, session.user_id, session.user_name)
    notes, total = await service.list_notes(patient_id, encounter_id, note_type, author, page, per_page)
    return {
        "items": [ClinicalNoteResponse.model_validate(n) for n in notes],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.patch("/{note_id}", response_model=ClinicalNoteResponse)
async def update_note(note_id: uuid.UUID, data: ClinicalNoteUpdate, session: EMRSession = Depends(get_emr_session)):
    service = ClinicalNoteService(session.db, session.hospital_id, session.user_id, session.user_name)
    try:
        note = await service.update_note(note_id, data)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
        return note
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{note_id}/finalize", response_model=ClinicalNoteResponse)
async def finalize_note(note_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = ClinicalNoteService(session.db, session.hospital_id, session.user_id, session.user_name)
    note = await service.finalize_note(note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
    return note
