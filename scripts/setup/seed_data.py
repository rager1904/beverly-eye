"""Seed the database with realistic Zambian healthcare demo data.

Usage:
    python -m scripts.setup.seed_data

Requires DATABASE_URL env var or running within the Docker backend container.
"""

import asyncio
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from src.backend.database import async_session_factory, engine, Base
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin

# ── Hospital Management models ──────────────────────────────────────────────
from src.backend.services.hospital_management.models import (
    Hospital, HospitalLevel,
)

# ── EMR models ──────────────────────────────────────────────────────────────
from src.backend.services.emr.models import (
    Patient, Encounter, EncounterType, EncounterStatus,
    Diagnosis, DiagnosisType, DiagnosisCertainty,
    Medication, MedicationStatus,
    Allergy, AllergySeverity,
    ProblemList, ProblemStatus,
    Immunization, ImmunizationStatus,
    Order, OrderType, OrderPriority, OrderStatus,
    Result, ResultInterpretation,
    ClinicalNote, NoteType, NoteStatus,
    Gender, MaritalStatus, Province,
)

# ── Disease Surveillance models ─────────────────────────────────────────────
from src.backend.services.disease_surveillance.models import (
    DiseaseCase, CaseStatus, CaseSeverity,
    OutbreakAlert, OutbreakStatus,
    SurveillanceReport, ReportType,
    NotifiableDisease,
)

# ── Appointment models ──────────────────────────────────────────────────────
from src.backend.services.appointments.models import (
    Appointment, AppointmentType, AppointmentStatus,
)

# ── Telemedicine models ─────────────────────────────────────────────────────
from src.backend.services.telemedicine.models import (
    Teleconsultation, ConsultationType, ConsultationStatus,
)

HOSPITAL_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")

PATIENTS_DATA = [
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000001"),
        "nrc_number": "573201/10/1", "first_name": "Chilufya", "last_name": "Banda",
        "date_of_birth": date(2021, 8, 15), "gender": Gender.male,
        "phone": "+260977100001", "address_line": "Kanyama Township",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "emergency_contact_name": "Grace Banda", "emergency_contact_phone": "+260977100002",
        "emergency_contact_relation": "Mother", "nhima_number": "NHIMA-100001",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000002"),
        "nrc_number": "483201/11/2", "first_name": "Mwila", "last_name": "Tembo",
        "date_of_birth": date(1995, 3, 22), "gender": Gender.female,
        "phone": "+260977100003", "address_line": "New Kasama",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Market Vendor", "marital_status": MaritalStatus.married,
        "nhima_member": True,
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000003"),
        "nrc_number": "663201/12/3", "first_name": "Banda", "last_name": "Phiri",
        "date_of_birth": date(1990, 11, 10), "gender": Gender.female,
        "phone": "+260977100005", "address_line": "Matero East",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Teacher", "marital_status": MaritalStatus.married,
        "emergency_contact_name": "John Phiri", "emergency_contact_phone": "+260977100006",
        "emergency_contact_relation": "Husband",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000004"),
        "nrc_number": "753201/13/4", "first_name": "Phiri", "last_name": "Zulu",
        "date_of_birth": date(1982, 7, 5), "gender": Gender.male,
        "phone": "+260977100007", "address_line": "Chipata Compound",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Security Guard", "marital_status": MaritalStatus.married,
        "emergency_contact_name": "Mary Zulu", "emergency_contact_phone": "+260977100008",
        "emergency_contact_relation": "Wife",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000005"),
        "nrc_number": "843201/14/5", "first_name": "Tembo", "last_name": "Mwansa",
        "date_of_birth": date(1975, 12, 1), "gender": Gender.female,
        "phone": "+260977100009", "address_line": "Twikatane",
        "city": "Ndola", "district": "Ndola", "province": Province.copperbelt,
        "occupation": "Farmer", "marital_status": MaritalStatus.widowed,
        "emergency_contact_name": "Peter Mwansa", "emergency_contact_phone": "+260977100010",
        "emergency_contact_relation": "Son",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000006"),
        "nrc_number": "933201/15/6", "first_name": "Zulu", "last_name": "Banda",
        "date_of_birth": date(1968, 4, 18), "gender": Gender.male,
        "phone": "+260977100011", "address_line": "Kabwata",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Taxi Driver", "marital_status": MaritalStatus.married,
        "emergency_contact_name": "Esther Banda", "emergency_contact_phone": "+260977100012",
        "emergency_contact_relation": "Wife",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000007"),
        "nrc_number": "103201/10/7", "first_name": "Mwanza", "last_name": "Kasonde",
        "date_of_birth": date(1998, 9, 25), "gender": Gender.female,
        "phone": "+260977100013", "address_line": "Kalingalinga",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Hairdresser", "marital_status": MaritalStatus.single,
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000008"),
        "nrc_number": "113201/11/8", "first_name": "Kunda", "last_name": "Simwanza",
        "date_of_birth": date(2023, 1, 10), "gender": Gender.male,
        "phone": "+260977100016", "address_line": "Chilenje",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "emergency_contact_name": "Grace Simwanza", "emergency_contact_phone": "+260977100017",
        "emergency_contact_relation": "Mother",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-000000000009"),
        "nrc_number": "123201/12/9", "first_name": "Simwanza", "last_name": "Chilufya",
        "date_of_birth": date(1979, 6, 30), "gender": Gender.male,
        "phone": "+260977100018", "address_line": "Olympia Park",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Accountant", "marital_status": MaritalStatus.married,
        "emergency_contact_name": "Mutinta Chilufya", "emergency_contact_phone": "+260977100019",
        "emergency_contact_relation": "Wife",
    },
    {
        "id": uuid.UUID("a1000001-0000-4000-8000-00000000000a"),
        "nrc_number": "133201/10/10", "first_name": "Nyirenda", "last_name": "Mwila",
        "date_of_birth": date(1988, 2, 14), "gender": Gender.female,
        "phone": "+260977100020", "address_line": "Northmead",
        "city": "Lusaka", "district": "Lusaka", "province": Province.lusaka,
        "occupation": "Nurse", "marital_status": MaritalStatus.single,
        "emergency_contact_name": "Henry Mwila", "emergency_contact_phone": "+260977100021",
        "emergency_contact_relation": "Father",
    },
]

ENCOUNTERS_DATA = [
    # (pid_key, type, datetime, status, chief_complaint, bp_sys, bp_dia, hr, rr, temp, spo2, provider_name)
    ("a1000001-0000-4000-8000-000000000001", EncounterType.outpatient, datetime(2026, 7, 3, 9, 15),
     EncounterStatus.completed, "Fever for 3 days, vomiting", 145, None, 38, None, Decimal("38.9"), 94, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000001", EncounterType.follow_up, datetime(2026, 7, 10, 8, 0),
     EncounterStatus.completed, "Immunization follow-up - OPV3 and Pentavalent 3", None, None, None, None, None, None, "Nurse Banda"),
    ("a1000001-0000-4000-8000-000000000002", EncounterType.outpatient, datetime(2026, 7, 3, 10, 30),
     EncounterStatus.completed, "ANC booking visit - Gravida 2, Para 1", 110, 70, 82, 18, Decimal("36.8"), 98, "Nurse Banda"),
    ("a1000001-0000-4000-8000-000000000003", EncounterType.outpatient, datetime(2026, 7, 3, 11, 0),
     EncounterStatus.completed, "Cough and night sweats for 3 weeks - TB screening", 118, 76, 96, 22, Decimal("37.8"), 96, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000004", EncounterType.outpatient, datetime(2026, 7, 3, 11, 30),
     EncounterStatus.completed, "HIV follow-up - on TLD, last CD4 350", 128, 82, 78, 16, Decimal("36.5"), 97, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000005", EncounterType.outpatient, datetime(2026, 7, 3, 12, 0),
     EncounterStatus.completed, "Persistent cough 4 weeks, weight loss, night sweats", 120, 78, 90, 20, Decimal("37.2"), 95, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000005", EncounterType.follow_up, datetime(2026, 6, 20, 14, 0),
     EncounterStatus.completed, "TB treatment review - on RHZE, improving", None, None, None, None, None, None, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000006", EncounterType.outpatient, datetime(2026, 7, 3, 8, 45),
     EncounterStatus.completed, "Severe headache, fever 39.5C for 2 days - malaria suspected", 130, 85, 110, 24, Decimal("39.5"), 93, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-000000000007", EncounterType.outpatient, datetime(2026, 7, 3, 9, 30),
     EncounterStatus.completed, "ANC follow-up - 28 weeks, dizziness", 100, 65, 88, 19, Decimal("36.9"), 99, "Nurse Banda"),
    ("a1000001-0000-4000-8000-000000000008", EncounterType.outpatient, datetime(2026, 7, 3, 8, 30),
     EncounterStatus.completed, "6-week immunization visit - BCG, OPV1, Pentavalent 1", None, None, None, None, None, None, "Nurse Banda"),
    ("a1000001-0000-4000-8000-000000000009", EncounterType.outpatient, datetime(2026, 7, 4, 10, 0),
     EncounterStatus.completed, "Annual review - hypertension follow-up, refill amlodipine", 135, 85, 76, 16, Decimal("36.6"), 98, "Dr. Mwamba"),
    ("a1000001-0000-4000-8000-00000000000a", EncounterType.outpatient, datetime(2026, 7, 3, 13, 0),
     EncounterStatus.completed, "Frequent urination, thirst, weight loss - diabetes screening", 125, 80, 84, 17, Decimal("36.7"), 98, "Dr. Mwamba"),
]

DIAGNOSES_DATA = [
    ("b2000001-0000-4000-8000-000000000001", "MAL001", "Malaria due to Plasmodium falciparum", DiagnosisType.primary, DiagnosisCertainty.confirmed, True),
    ("b2000001-0000-4000-8000-000000000004", "TB001", "Pulmonary tuberculosis", DiagnosisType.primary, DiagnosisCertainty.suspected, False),
    ("b2000001-0000-4000-8000-000000000005", "HIV001", "HIV disease", DiagnosisType.primary, DiagnosisCertainty.confirmed, True),
    ("b2000001-0000-4000-8000-000000000006", "TB001", "Pulmonary tuberculosis", DiagnosisType.primary, DiagnosisCertainty.confirmed, False),
    ("b2000001-0000-4000-8000-000000000008", "MAL001", "Malaria due to Plasmodium falciparum", DiagnosisType.primary, DiagnosisCertainty.confirmed, False),
    ("b2000001-0000-4000-8000-00000000000b", "I10", "Essential hypertension", DiagnosisType.primary, DiagnosisCertainty.confirmed, True),
    ("b2000001-0000-4000-8000-00000000000c", "E11", "Type 2 diabetes mellitus", DiagnosisType.primary, DiagnosisCertainty.confirmed, True),
]

ORDERS_DATA = [
    # enc_id, patient_id, order_type, code, desc, priority, status, result_val, result_unit, interpretation
    ("b2000001-0000-4000-8000-000000000001", "a1000001-0000-4000-8000-000000000001",
     OrderType.lab, "MAL_RDT", "Malaria Rapid Diagnostic Test", OrderPriority.urgent, OrderStatus.resulted,
     "Positive (+++)", None, ResultInterpretation.abnormal),
    ("b2000001-0000-4000-8000-000000000004", "a1000001-0000-4000-8000-000000000003",
     OrderType.lab, "GENXPERT", "GeneXpert Ultra TB", OrderPriority.urgent, OrderStatus.resulted,
     "Positive (MTB detected)", "RIF Resistance: Not detected", ResultInterpretation.abnormal),
    ("b2000001-0000-4000-8000-000000000005", "a1000001-0000-4000-8000-000000000004",
     OrderType.lab, "HIV_VL", "HIV Viral Load", OrderPriority.routine, OrderStatus.resulted,
     "Undetectable (<20 copies/mL)", "copies/mL", ResultInterpretation.normal),
    ("b2000001-0000-4000-8000-000000000008", "a1000001-0000-4000-8000-000000000006",
     OrderType.lab, "MAL_RDT", "Malaria Rapid Diagnostic Test", OrderPriority.stat, OrderStatus.resulted,
     "Positive (+++)", None, ResultInterpretation.abnormal),
    ("b2000001-0000-4000-8000-00000000000c", "a1000001-0000-4000-8000-00000000000a",
     OrderType.lab, "RBS", "Random Blood Sugar", OrderPriority.urgent, OrderStatus.resulted,
     "14.2", "mmol/L", ResultInterpretation.abnormal),
    ("b2000001-0000-4000-8000-000000000009", "a1000001-0000-4000-8000-000000000007",
     OrderType.lab, "FBC", "Full Blood Count", OrderPriority.routine, OrderStatus.ordered,
     None, None, ResultInterpretation.pending),
]

MEDICATIONS_DATA = [
    ("b2000001-0000-4000-8000-000000000001", "a1000001-0000-4000-8000-000000000001",
     "Artemether + Lumefantrine 20/120mg", "Coartem", "1 tab", "12 hourly x 3 days", "Oral", 3, MedicationStatus.completed),
    ("b2000001-0000-4000-8000-000000000005", "a1000001-0000-4000-8000-000000000004",
     "TLD (Tenofovir/Lamivudine/Dolutegravir)", None, "1 tab", "Daily", "Oral", 90, MedicationStatus.prescribed),
    ("b2000001-0000-4000-8000-000000000008", "a1000001-0000-4000-8000-000000000006",
     "Artemether + Lumefantrine 20/120mg", "Coartem", "4 tabs", "BD x 3 days", "Oral", 3, MedicationStatus.completed),
    ("b2000001-0000-4000-8000-000000000008", "a1000001-0000-4000-8000-000000000006",
     "Paracetamol 500mg", None, "500mg", "8 hourly PRN", "Oral", 3, MedicationStatus.completed),
    ("b2000001-0000-4000-8000-00000000000b", "a1000001-0000-4000-8000-000000000009",
     "Amlodipine 5mg", None, "5mg", "Daily", "Oral", 90, MedicationStatus.prescribed),
    ("b2000001-0000-4000-8000-00000000000c", "a1000001-0000-4000-8000-00000000000a",
     "Metformin 500mg", None, "500mg", "BD", "Oral", 90, MedicationStatus.prescribed),
]

IMMUNIZATIONS_DATA = [
    ("a1000001-0000-4000-8000-000000000008", "BCG", date(2023, 1, 24), "UNICEF-BCG-2023-01", date(2023, 1, 24), 1, 1, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000008", "OPV", date(2023, 1, 24), "UNICEF-OPV-2023-01", date(2023, 3, 7), 1, 3, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000001", "OPV", date(2021, 9, 26), "UNICEF-OPV-2021-B2", date(2021, 9, 26), 1, 3, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000001", "PENTA", date(2021, 9, 26), "UNICEF-PENTA-2021-B2", date(2021, 9, 26), 1, 3, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000001", "PCV", date(2021, 9, 26), "UNICEF-PCV-2021-B2", date(2021, 9, 26), 1, 3, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000001", "ROTA", date(2021, 9, 26), "UNICEF-ROTA-2021-B2", date(2021, 9, 26), 1, 2, ImmunizationStatus.administered),
    ("a1000001-0000-4000-8000-000000000001", "MR", date(2022, 5, 15), "UNICEF-MR-2022-A1", date(2022, 5, 15), 1, 1, ImmunizationStatus.administered),
]

ALLERGIES_DATA = [
    ("a1000001-0000-4000-8000-000000000003", "Penicillin", "Rash and itching", AllergySeverity.moderate),
    ("a1000001-0000-4000-8000-000000000006", "Sulfa drugs", "Urticaria", AllergySeverity.severe),
    ("a1000001-0000-4000-8000-00000000000a", "Latex", "Contact dermatitis", AllergySeverity.mild),
]

PROBLEMS_DATA = [
    ("a1000001-0000-4000-8000-000000000004", "HIV", "HIV disease", "B20", True, ProblemStatus.active),
    ("a1000001-0000-4000-8000-000000000009", "Hypertension", "Essential hypertension", "I10", True, ProblemStatus.active),
    ("a1000001-0000-4000-8000-00000000000a", "Diabetes", "Type 2 diabetes mellitus", "E11", True, ProblemStatus.active),
]

DISEASE_CASES_DATA = [
    ("Cholera", CaseStatus.confirmed, CaseSeverity.severe, "Lusaka", Province.lusaka.value, "Kanyama Clinic", date(2026, 6, 15)),
    ("Malaria", CaseStatus.confirmed, CaseSeverity.moderate, "Lusaka", Province.lusaka.value, "UTH", date(2026, 6, 20)),
    ("Anthrax", CaseStatus.suspected, CaseSeverity.moderate, "Sinazongwe", Province.southern.value, "Sinazongwe District Hospital", date(2026, 6, 28)),
    ("Tuberculosis", CaseStatus.confirmed, CaseSeverity.severe, "Ndola", Province.copperbelt.value, "Ndola Hospital", date(2026, 6, 25)),
    ("Malaria", CaseStatus.confirmed, CaseSeverity.mild, "Chipata", Province.eastern.value, "Chipata Hospital", date(2026, 7, 1)),
    ("Typhoid", CaseStatus.suspected, CaseSeverity.moderate, "Kafue", Province.lusaka.value, "Kafue Clinic", date(2026, 7, 2)),
]

OUTBREAK_ALERTS_DATA = [
    ("Cholera", OutbreakStatus.active, "Lusaka", Province.lusaka.value, "Kanyama Township", datetime(2026, 6, 15, 8, 0), 12, 45, 3, 2),
    ("Anthrax", OutbreakStatus.potential, "Sinazongwe", Province.southern.value, "Sinazongwe District", datetime(2026, 6, 28, 10, 0), 2, 4, 1, 0),
    ("Malaria", OutbreakStatus.active, "Chipata", Province.eastern.value, "Chipata District", datetime(2026, 7, 1, 9, 0), 25, 80, 0, 0),
]

APPOINTMENTS_DATA = [
    ("a1000001-0000-4000-8000-000000000001", AppointmentType.follow_up, date(2026, 7, 20), time(9, 0), time(9, 30), AppointmentStatus.scheduled, "Malaria follow-up"),
    ("a1000001-0000-4000-8000-000000000002", AppointmentType.antenatal, date(2026, 7, 18), time(10, 0), time(10, 30), AppointmentStatus.scheduled, "ANC review"),
    ("a1000001-0000-4000-8000-000000000004", AppointmentType.hiv, date(2026, 7, 15), time(11, 0), time(11, 30), AppointmentStatus.scheduled, "ART refill"),
    ("a1000001-0000-4000-8000-000000000009", AppointmentType.general, date(2026, 7, 16), time(14, 0), time(14, 30), AppointmentStatus.scheduled, "Hypertension review"),
    ("a1000001-0000-4000-8000-00000000000a", AppointmentType.general, date(2026, 7, 17), time(9, 0), time(9, 30), AppointmentStatus.scheduled, "Diabetes review + HbA1c"),
]

TELECONSULTATIONS_DATA = [
    ("a1000001-0000-4000-8000-000000000004", "a1000001-0000-4000-8000-000000000006",
     ConsultationType.video, ConsultationStatus.completed,
     datetime(2026, 7, 3, 14, 0), datetime(2026, 7, 3, 14, 30),
     "Rash on arms - possible allergic reaction",
     "URT investigation follows. Prescribed antihistamines."),
    ("a1000001-0000-4000-8000-000000000006", "a1000001-0000-4000-8000-000000000009",
     ConsultationType.phone, ConsultationStatus.completed,
     datetime(2026, 7, 4, 10, 0), datetime(2026, 7, 4, 10, 20),
     "Medication refill - amlodipine running low",
     "Prescription sent to pharmacy for collection."),
    ("a1000001-0000-4000-8000-000000000002", "a1000001-0000-4000-8000-000000000004",
     ConsultationType.video, ConsultationStatus.in_waiting_room,
     datetime(2026, 7, 6, 11, 0), None,
     "Mild fever and body aches",
     None),
]

SURVEILLANCE_REPORTS = [
    ("weekly", "Weekly Surveillance Report - Lusaka District", date(2026, 6, 24), date(2026, 6, 30),
     "Lusaka", Province.lusaka.value, "47 total cases reported. Cholera outbreak in Kanyama. Malaria cases increasing.",
     47, 3, ReportType.weekly),
    ("monthly", "Monthly Surveillance Summary - Southern Province", date(2026, 6, 1), date(2026, 6, 30),
     "Sinazongwe", Province.southern.value, "Possible anthrax outbreak under investigation. 4 suspected cases.",
     4, 0, ReportType.monthly),
]


def _build_kwargs(exclude_none=True):
    """Use with dataclass-like dicts to filter None values."""
    return {k: v for k, v in kwargs.items() if not (exclude_none and v is None)}


async def seed():
    async with engine.begin() as conn:
        for tbl in ["patients", "immunizations", "visits", "vitals", "lab_orders", "lab_results", "prescriptions"]:
            await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        # ── 1. Create default hospital ──────────────────────────────────────
        existing = await session.get(Hospital, HOSPITAL_ID)
        if not existing:
            hospital = Hospital(
                id=HOSPITAL_ID,
                name="Eye & Dental Hospital",
                code="EDH001",
                level=HospitalLevel.specialized_hospital,
                address_line="Off Great East Road",
                city="Lusaka",
                province="Lusaka",
                district="Lusaka",
                phone="+260211250000",
                email="info@uth.gov.zm",
                bed_count=1655,
                is_active=True,
            )
            session.add(hospital)
            print("Created Eye & Dental Hospital")

        # ── 2. Create patients ─────────────────────────────────────────────
        for pd in PATIENTS_DATA:
            existing = await session.get(Patient, pd["id"])
            if existing:
                continue
            patient = Patient(hospital_id=HOSPITAL_ID, **pd)
            session.add(patient)
        print(f"Created/verified {len(PATIENTS_DATA)} patients")

        # ── 3. Allergies ────────────────────────────────────────────────────
        for pid, allergen, reaction, severity in ALLERGIES_DATA:
            existing_patient = await session.get(Patient, uuid.UUID(pid))
            if not existing_patient:
                continue
            allergy = Allergy(
                patient_id=uuid.UUID(pid), allergen=allergen, reaction=reaction,
                severity=severity, hospital_id=HOSPITAL_ID,
            )
            session.add(allergy)
        print(f"Created {len(ALLERGIES_DATA)} allergies")

        # ── 4. Problems ────────────────────────────────────────────────────
        for pid, problem_name, desc, icd10, is_chronic, status in PROBLEMS_DATA:
            existing_patient = await session.get(Patient, uuid.UUID(pid))
            if not existing_patient:
                continue
            problem = ProblemList(
                patient_id=uuid.UUID(pid), problem_name=problem_name,
                icd10_code=icd10, icd10_description=desc,
                is_chronic=is_chronic, status=status,
                hospital_id=HOSPITAL_ID,
            )
            session.add(problem)
        print(f"Created {len(PROBLEMS_DATA)} chronic conditions")

        # ── 5. Immunizations ────────────────────────────────────────────────
        for pid, vaccine, admin_date, batch, scheduled_date, dose, total, status in IMMUNIZATIONS_DATA:
            existing_patient = await session.get(Patient, uuid.UUID(pid))
            if not existing_patient:
                continue
            imm = Immunization(
                patient_id=uuid.UUID(pid), vaccine_type=vaccine,
                administered_date=admin_date, batch_number=batch,
                dose_number=dose, total_doses=total, status=status,
                administered_by="Nurse Banda", manufacturer="UNICEF",
                facility_id="UTH001", hospital_id=HOSPITAL_ID,
            )
            session.add(imm)
        print(f"Created {len(IMMUNIZATIONS_DATA)} immunizations")

        # ── 6. Encounters + Orders/Results ──────────────────────────────────
        enc_idx = 0
        for ed in ENCOUNTERS_DATA:
            pid_str, enc_type, enc_dt, status, complaint, bp_sys, bp_dia, hr, rr, temp, spo2, provider = ed
            enc_id = uuid.UUID(f"b2000001-0000-4000-8000-{enc_idx + 1:012x}")
            enc_idx += 1
            existing = await session.get(Encounter, enc_id)
            if existing:
                continue
            encounter = Encounter(
                id=enc_id, patient_id=uuid.UUID(pid_str),
                encounter_type=enc_type, encounter_datetime=enc_dt,
                status=status, chief_complaint=complaint,
                blood_pressure_systolic=bp_sys, blood_pressure_diastolic=bp_dia,
                heart_rate=hr, respiratory_rate=rr, temperature=temp,
                oxygen_saturation=spo2, provider_name=provider,
                department="General", facility_id="UTH001",
                hospital_id=HOSPITAL_ID,
            )
            session.add(encounter)

        # ── 7. Diagnoses ────────────────────────────────────────────────────
        for did_str, icd10, desc, dtype, certainty, is_chronic in DIAGNOSES_DATA:
            enc_id = uuid.UUID(did_str)
            existing_enc = await session.get(Encounter, enc_id)
            if not existing_enc:
                continue
            diagnosis = Diagnosis(
                id=uuid.uuid4(), encounter_id=enc_id,
                patient_id=existing_enc.patient_id,
                icd10_code=icd10, icd10_description=desc,
                diagnosis_type=dtype, certainty=certainty,
                is_chronic=is_chronic, hospital_id=HOSPITAL_ID,
            )
            session.add(diagnosis)

        # ── 8. Orders & Results ────────────────────────────────────────────
        for enc_str, pid_str, otype, code, desc, priority, ostatus, result_val, result_unit, interp in ORDERS_DATA:
            enc_id = uuid.UUID(enc_str)
            existing_enc = await session.get(Encounter, enc_id)
            if not existing_enc:
                continue
            order = Order(
                id=uuid.uuid4(), encounter_id=enc_id,
                patient_id=uuid.UUID(pid_str),
                order_type=otype, order_code=code, order_description=desc,
                priority=priority, status=ostatus,
                ordered_by="Dr. Mwamba", ordered_datetime=existing_enc.encounter_datetime,
                hospital_id=HOSPITAL_ID,
            )
            session.add(order)
            await session.flush()
            if result_val:
                result = Result(
                    id=uuid.uuid4(), order_id=order.id,
                    patient_id=order.patient_id,
                    result_type=code, result_code=code, result_description=desc,
                    result_value=result_val, result_unit=result_unit,
                    interpretation=interp,
                    performed_by="Lab Kasonde",
                    performed_datetime=existing_enc.encounter_datetime + timedelta(hours=2),
                    result_datetime=existing_enc.encounter_datetime + timedelta(hours=3),
                    hospital_id=HOSPITAL_ID,
                )
                session.add(result)

        # ── 9. Medications ──────────────────────────────────────────────────
        for enc_str, pid_str, med_name, generic, dosage, freq, route, duration, status in MEDICATIONS_DATA:
            med = Medication(
                id=uuid.uuid4(), encounter_id=uuid.UUID(enc_str),
                patient_id=uuid.UUID(pid_str),
                medication_name=med_name, generic_name=generic,
                dosage=dosage, frequency=freq, route=route,
                duration=duration, duration_unit="days",
                status=status, prescribing_provider_name="Dr. Mwamba",
                hospital_id=HOSPITAL_ID,
            )
            session.add(med)

        # ── 10. Disease Cases ───────────────────────────────────────────────
        for disease, status, severity, district, province, facility, diag_date in DISEASE_CASES_DATA:
            dc = DiseaseCase(
                id=uuid.uuid4(),
                disease=NotifiableDisease(disease),
                status=status, severity=severity,
                district=district, province=province,
                facility_name=facility, diagnosis_date=diag_date,
                reported_by="Dr. Mwamba",
                hospital_id=HOSPITAL_ID,
            )
            session.add(dc)

        # ── 11. Outbreak Alerts ────────────────────────────────────────────
        for disease, status, district, province, location, detected, deaths, confirmed, suspected, case_count in OUTBREAK_ALERTS_DATA:
            oa = OutbreakAlert(
                id=uuid.uuid4(),
                disease=NotifiableDisease(disease),
                status=status, district=district, province=province,
                facility_name=location, detected_date=detected,
                case_count=case_count, suspected_cases=suspected,
                confirmed_cases=confirmed, deaths=deaths,
                response_team_activated=True,
                hospital_id=HOSPITAL_ID,
            )
            session.add(oa)

        # ── 12. Appointments ───────────────────────────────────────────────
        for pid_str, apt_type, apt_date, start, end, status, reason in APPOINTMENTS_DATA:
            apt = Appointment(
                id=uuid.uuid4(),
                patient_id=uuid.UUID(pid_str),
                patient_name=f"Patient {pid_str[:6]}",
                patient_phone="+260977100000",
                appointment_type=apt_type,
                appointment_date=apt_date, start_time=start, end_time=end,
                duration_minutes=30, status=status, reason=reason,
                department="General", facility_id="UTH001",
                hospital_id=HOSPITAL_ID,
            )
            session.add(apt)

        # ── 13. Teleconsultations ──────────────────────────────────────────
        for pid_str, prov_str, ctype, cstatus, scheduled, actual, complaint, treatment in TELECONSULTATIONS_DATA:
            tc = Teleconsultation(
                id=uuid.uuid4(),
                patient_id=uuid.UUID(pid_str),
                provider_id=uuid.UUID(prov_str),
                consultation_type=ctype, status=cstatus,
                scheduled_start=scheduled, actual_start=scheduled,
                actual_end=actual, chief_complaint=complaint,
                treatment_plan=treatment,
                hospital_id=HOSPITAL_ID,
            )
            session.add(tc)

        # ── 14. Surveillance Reports ───────────────────────────────────────
        for title, subtitle, period_start, period_end, district, province, summary, total_cases, total_deaths, report_type in SURVEILLANCE_REPORTS:
            sr = SurveillanceReport(
                id=uuid.uuid4(),
                report_type=report_type, title=f"{title}: {subtitle}",
                period_start=period_start, period_end=period_end,
                district=district, province=province,
                summary=summary, total_cases=total_cases,
                total_deaths=total_deaths, status="final",
                submitted_to_moh=True,
                submitted_by="Dr. Mwamba",
                hospital_id=HOSPITAL_ID,
            )
            session.add(sr)

        await session.commit()
        print("Seed data committed successfully!")

    # ---- DONE ----
    print("=== Seeding complete ===")


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
