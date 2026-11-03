import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.hospital_management.dependencies import HospitalSession, get_hospital_session
from src.backend.services.hospital_management.schemas import (
    ClaimCreate,
    ClaimResponse,
    TransactionCreate,
    TransactionResponse,
)
from src.backend.services.hospital_management.services import BillingService, NHIMAService

router = APIRouter()


# ─── Financial Transactions ────────────────────────────────────────────────────
@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransactionCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = BillingService(session.db, session.hospital_id, session.user_id)
    return await service.create_transaction(data)


@router.get("/patients/{patient_id}/transactions", response_model=list[TransactionResponse])
async def get_patient_transactions(
    patient_id: uuid.UUID,
    session: HospitalSession = Depends(get_hospital_session),
):
    service = BillingService(session.db, session.hospital_id, session.user_id)
    return await service.get_patient_bills(patient_id)


@router.get("/patients/{patient_id}/balance", response_model=dict)
async def get_patient_balance(
    patient_id: uuid.UUID,
    session: HospitalSession = Depends(get_hospital_session),
):
    service = BillingService(session.db, session.hospital_id, session.user_id)
    balance = await service.get_outstanding_balance(patient_id)
    return {"patient_id": str(patient_id), "outstanding_balance_zmw": balance}


@router.post("/transactions/{transaction_id}/pay", response_model=TransactionResponse)
async def record_payment(
    transaction_id: uuid.UUID,
    amount_zmw: Decimal = Query(...),
    method: Optional[str] = Query(None),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = BillingService(session.db, session.hospital_id, session.user_id)
    txn = await service.record_payment(transaction_id, amount_zmw, method)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return txn


# ─── NHIMA Claims ──────────────────────────────────────────────────────────────
@router.post("/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(data: ClaimCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = NHIMAService(session.db, session.hospital_id, session.user_id)
    return await service.create_claim(data)


@router.get("/claims", response_model=dict)
async def list_claims(
    patient_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = NHIMAService(session.db, session.hospital_id, session.user_id)
    claims, total = await service.get_claims(patient_id, status, page, per_page)
    return {
        "items": [ClaimResponse.model_validate(c) for c in claims],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/claims/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim(claim_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = NHIMAService(session.db, session.hospital_id, session.user_id)
    claim = await service.submit_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim
