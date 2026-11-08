"""Seed Zambia-specific demo data: patients, visits, labs, prescriptions.

Revision ID: 005
Revises: 004
Create Date: 2026-07-03

Creates realistic demo data for 10 patients with Zambia-typical conditions.
Patients reference existing facilities (UH001, KNW001, NDH001) and users
(dr_mwamba, nurse_banda, lab_kasonde) from previous migrations.
"""

from typing import Optional, Sequence
from uuid import uuid4
import os

from alembic import op
from sqlalchemy import text

revision: str = "005"
down_revision: Optional[str] = "004"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def _demo_seed_enabled() -> bool:
    explicit = os.getenv("UBUNTUCARE_SEED_DEMO_DATA")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "production").strip().lower() != "production"

# Pre-generated UUIDs for demo patients (fixed so data is consistent across runs)
P = {  # patient UUIDs
    "chilufya": "a1000001-0000-4000-8000-000000000001",
    "mwila":    "a1000001-0000-4000-8000-000000000002",
    "banda":    "a1000001-0000-4000-8000-000000000003",
    "phiri":    "a1000001-0000-4000-8000-000000000004",
    "tembo":    "a1000001-0000-4000-8000-000000000005",
    "zulu":     "a1000001-0000-4000-8000-000000000006",
    "mwanza":   "a1000001-0000-4000-8000-000000000007",
    "kunda":    "a1000001-0000-4000-8000-000000000008",
    "simwanza": "a1000001-0000-4000-8000-000000000009",
    "nyirenda": "a1000001-0000-4000-8000-00000000000a",
}
V = {  # visit UUIDs
    "chilufya_1": "b2000001-0000-4000-8000-000000000001",
    "chilufya_2": "b2000001-0000-4000-8000-000000000002",
    "mwila_1":    "b2000001-0000-4000-8000-000000000003",
    "banda_1":    "b2000001-0000-4000-8000-000000000004",
    "phiri_1":    "b2000001-0000-4000-8000-000000000005",
    "tembo_1":    "b2000001-0000-4000-8000-000000000006",
    "tembo_2":    "b2000001-0000-4000-8000-000000000007",
    "zulu_1":     "b2000001-0000-4000-8000-000000000008",
    "mwanza_1":   "b2000001-0000-4000-8000-000000000009",
    "kunda_1":    "b2000001-0000-4000-8000-00000000000a",
    "simwanza_1": "b2000001-0000-4000-8000-00000000000b",
    "nyirenda_1": "b2000001-0000-4000-8000-00000000000c",
}
# UUIDs for lab orders
LO = {
    "chilufya_malaria": "c3000001-0000-4000-8000-000000000001",
    "phiri_hiv":        "c3000001-0000-4000-8000-000000000002",
    "tembo_tb":         "c3000001-0000-4000-8000-000000000003",
    "zulu_malaria":     "c3000001-0000-4000-8000-000000000004",
    "mwanza_hb":        "c3000001-0000-4000-8000-000000000005",
    "banda_hiv":        "c3000001-0000-4000-8000-000000000006",
    "nyirenda_glucose": "c3000001-0000-4000-8000-000000000007",
}
NHIMA_IDS = iter([
    "NHIMA-100001", "NHIMA-100002", "NHIMA-100003", "NHIMA-100004",
    "NHIMA-100005", "NHIMA-100006",
])


def _get_facility_id(code: str) -> int:
    """Resolve facility code to PK id via SQL."""
    return int(text(f"SELECT id FROM health_facilities WHERE code = '{code}'"))


def _get_dr_mwamba_id() -> str:
    """Fetch dr_mwamba UUID from users table."""
    return text("SELECT id FROM users WHERE username = 'dr_mwamba'")


def _get_nurse_banda_id() -> str:
    return text("SELECT id FROM users WHERE username = 'nurse_banda'")


def _get_lab_kasonde_id() -> str:
    return text("SELECT id FROM users WHERE username = 'lab_kasonde'")


def upgrade() -> None:
    if not _demo_seed_enabled():
        print("Skipping demo patient data (UBUNTUCARE_SEED_DEMO_DATA is disabled).")
        return
    conn = op.get_bind()

    # Resolve foreign key IDs
    uth_id = conn.execute(
        text("SELECT id FROM health_facilities WHERE code = 'UH001'")
    ).scalar()
    kanyama_id = conn.execute(
        text("SELECT id FROM health_facilities WHERE code = 'KNW001'")
    ).scalar()
    ndola_id = conn.execute(
        text("SELECT id FROM health_facilities WHERE code = 'NDH001'")
    ).scalar()
    dr_mwamba = conn.execute(
        text("SELECT id FROM users WHERE username = 'dr_mwamba'")
    ).scalar()
    nurse_banda = conn.execute(
        text("SELECT id FROM users WHERE username = 'nurse_banda'")
    ).scalar()
    lab_kasonde = conn.execute(
        text("SELECT id FROM users WHERE username = 'lab_kasonde'")
    ).scalar()
    lusaka_district = conn.execute(
        text("SELECT id FROM districts WHERE code = 'LK001'")
    ).scalar()
    ndola_district = conn.execute(
        text("SELECT id FROM districts WHERE code = 'CB001'")
    ).scalar()

    # ── PATIENTS ────────────────────────────────────────────────────────────
    patients = [
        (P["chilufya"], "573201/10/1", "Chilufya", "Banda", "Grace", "2021-08-15",
         "male", "+260977100001", None, "Kanyama Township", None, lusaka_district,
         None, "Kanyama", None, None, "Grace Banda", "+260977100002", "Mother",
         kanyama_id, False, False),
        (P["mwila"], "483201/11/2", "Mwila", "Tembo", "Joyce", "1995-03-22",
         "female", "+260977100003", "+260977100004", "New Kasama", None, lusaka_district,
         None, "Kasama", "Market Vendor", "Married", None, None, None,
         uth_id, False, False),
        (P["banda"], "663201/12/3", "Banda", "Phiri", "Sarah", "1990-11-10",
         "female", "+260977100005", None, "Matero East", None, lusaka_district,
         None, "Matero", "Teacher", "Married", "John Phiri", "+260977100006", "Husband",
         uth_id, False, False),
        (P["phiri"], "753201/13/4", "Phiri", "Zulu", "Michael", "1982-07-05",
         "male", "+260977100007", None, "Chipata Compound", None, lusaka_district,
         None, "Chipata", "Security Guard", "Married", "Mary Zulu", "+260977100008", "Wife",
         uth_id, False, False),
        (P["tembo"], "843201/14/5", "Tembo", "Mwansa", "Agnes", "1975-12-01",
         "female", "+260977100009", None, "Twikatane", None, ndola_district,
         None, "Twikatane", "Farmer", "Widowed", "Peter Mwansa", "+260977100010", "Son",
         ndola_id, False, False),
        (P["zulu"], "933201/15/6", "Zulu", "Banda", "David", "1968-04-18",
         "male", "+260977100011", None, "Kabwata", None, lusaka_district,
         None, "Kabwata", "Taxi Driver", "Married", "Esther Banda", "+260977100012", "Wife",
         uth_id, False, False),
        (P["mwanza"], "103201/10/7", "Mwanza", "Kasonde", "Esther", "1998-09-25",
         "female", "+260977100013", "+260977100014", "Kalingalinga", None, lusaka_district,
         None, "Kalingalinga", "Hairdresser", "Single", "Brenda Kasonde", "+260977100015", "Sister",
         kanyama_id, False, False),
        (P["kunda"], "113201/11/8", "Kunda", "Simwanza", "Patrick", "2023-01-10",
         "male", "+260977100016", None, "Chilenje", None, lusaka_district,
         None, "Chilenje", None, None, "Grace Simwanza", "+260977100017", "Mother",
         uth_id, False, False),
        (P["simwanza"], "123201/12/9", "Simwanza", "Chilufya", "Nathan", "1979-06-30",
         "male", "+260977100018", None, "Olympia Park", None, lusaka_district,
         None, "Olympia", "Accountant", "Married", "Mutinta Chilufya", "+260977100019", "Wife",
         uth_id, False, False),
        (P["nyirenda"], "133201/10/10", "Nyirenda", "Mwila", "Catherine", "1988-02-14",
         "female", "+260977100020", None, "Northmead", None, lusaka_district,
         None, "Northmead", "Nurse", "Single", "Henry Mwila", "+260977100021", "Father",
         uth_id, False, False),
    ]
    for pid, nrc, first, last, other, dob, gender, phone, alt_phone, addr1, addr2, did, chiefdom, village, occupation, marital, nok_name, nok_phone, nok_rel, fac_id, deceased, verified in patients:
        nhima_id = next(NHIMA_IDS) if nrc.startswith(("5", "6", "7")) else None
        conn.execute(text("""
            INSERT INTO patients (id, nrc_number, first_name, last_name, other_names,
                date_of_birth, gender, phone, alt_phone, address_line1, address_line2,
                district_id, chiefdom, village, occupation, marital_status,
                next_of_kin_name, next_of_kin_phone, next_of_kin_relationship,
                registration_facility_id, is_deceased, is_verified)
            VALUES (:pid, :nrc, :first, :last, :other, :dob, :gender,
                :phone, :alt_phone, :addr1, :addr2, :did,
                :chiefdom, :village, :occ, :marital, :nok_name, :nok_phone, :nok_rel,
                :fac_id, :deceased, :verified)
        """), {
            "pid": pid, "nrc": nrc, "first": first, "last": last, "other": other,
            "dob": dob, "gender": gender, "phone": phone, "alt_phone": alt_phone,
            "addr1": addr1, "addr2": addr2, "did": did, "chiefdom": chiefdom,
            "village": village, "occ": occupation, "marital": marital,
            "nok_name": nok_name, "nok_phone": nok_phone, "nok_rel": nok_rel,
            "fac_id": fac_id, "deceased": deceased, "verified": verified,
        })
        if nhima_id:
            # Insert NHIMA record into encounter/insurance (simplified as patient note)
            pass

    # ── VISITS ──────────────────────────────────────────────────────────────
    visits = [
        (V["chilufya_1"], P["chilufya"], kanyama_id, "outpatient", "checked_in",
         "medium", None, None, None, "Fever for 3 days, vomiting. Malaria RDT pending.",
         dr_mwamba, "2026-07-03 09:15:00"),
        (V["chilufya_2"], P["chilufya"], kanyama_id, "immunization", "scheduled",
         "low", None, None, None, "Scheduled for OPV3 and Pentavalent 3 at 14 weeks.",
         nurse_banda, "2026-07-10 08:00:00"),
        (V["mwila_1"], P["mwila"], uth_id, "antenatal", "checked_in",
         "medium", None, None, None, "ANC booking visit. Gravida 2, Para 1. LMP 2026-03-15.",
         nurse_banda, "2026-07-03 10:30:00"),
        (V["banda_1"], P["banda"], uth_id, "outpatient", "checked_in",
         "medium", None, None, None, "Cough and night sweats for 3 weeks. TB screening.",
         dr_mwamba, "2026-07-03 11:00:00"),
        (V["phiri_1"], P["phiri"], uth_id, "chronic_care", "checked_in",
         "high", None, None, None, "HIV follow-up. On TLD. Last CD4 350. Compliant.",
         dr_mwamba, "2026-07-03 11:30:00"),
        (V["tembo_1"], P["tembo"], ndola_id, "outpatient", "checked_in",
         "high", None, None, None, "Persistent cough 4 weeks, weight loss, night sweats.",
         dr_mwamba, "2026-07-03 12:00:00"),
        (V["tembo_2"], P["tembo"], ndola_id, "outpatient", "completed",
         "high", None, None, None, "TB treatment review. On RHZE. Improving.",
         dr_mwamba, "2026-06-20 14:00:00"),
        (V["zulu_1"], P["zulu"], uth_id, "outpatient", "checked_in",
         "critical", None, None, None, "Severe headache, fever 39.5C for 2 days. Malaria suspected.",
         dr_mwamba, "2026-07-03 08:45:00"),
        (V["mwanza_1"], P["mwanza"], kanyama_id, "antenatal", "checked_in",
         "medium", None, None, None, "ANC follow-up. 28 weeks. Complaints of dizziness.",
         nurse_banda, "2026-07-03 09:30:00"),
        (V["kunda_1"], P["kunda"], uth_id, "immunization", "checked_in",
         "low", None, None, None, "6-week immunization visit. BCG scar check, OPV1, Pentavalent 1, PCV1, Rota1.",
         nurse_banda, "2026-07-03 08:30:00"),
        (V["simwanza_1"], P["simwanza"], uth_id, "outpatient", "scheduled",
         "medium", None, None, None, "Annual review. Hypertension follow-up. Refill amlodipine.",
         dr_mwamba, "2026-07-04 10:00:00"),
        (V["nyirenda_1"], P["nyirenda"], uth_id, "outpatient", "checked_in",
         "medium", None, None, None, "Frequent urination, thirst, weight loss. Diabetes screening.",
         dr_mwamba, "2026-07-03 13:00:00"),
    ]
    for vid, pid, fac_id, vtype, vstatus, priority, refer_from, refer_to, admit_at, triage_notes, created_by, created_at in visits:
        conn.execute(text("""
            INSERT INTO visits (id, patient_id, facility_id, visit_type, visit_status,
                priority, triage_notes, created_by, created_at)
            VALUES (:vid, :pid, :fac_id, :vtype, :vstatus, :priority, :triage_notes, :created_by, :created_at)
        """), {
            "vid": vid, "pid": pid, "fac_id": fac_id, "vtype": vtype,
            "vstatus": vstatus, "priority": priority, "triage_notes": triage_notes,
            "created_by": created_by, "created_at": created_at,
        })

    # ── VITALS ──────────────────────────────────────────────────────────────
    vitals_data = [
        (V["chilufya_1"], P["chilufya"], 38.9, 145, 38, None, None, 94, 11.5, None, None, None, None, nurse_banda, "2026-07-03 09:20:00"),
        (V["mwila_1"], P["mwila"], 36.8, 82, 18, 110, 70, 98, 65.0, 162, None, None, None, nurse_banda, "2026-07-03 10:35:00"),
        (V["banda_1"], P["banda"], 37.8, 96, 22, 118, 76, 96, 62.0, 165, None, None, None, nurse_banda, "2026-07-03 11:05:00"),
        (V["phiri_1"], P["phiri"], 36.5, 78, 16, 128, 82, 97, 72.0, 170, None, None, None, nurse_banda, "2026-07-03 11:35:00"),
        (V["tembo_1"], P["tembo"], 37.2, 90, 20, 120, 78, 95, 48.0, 155, None, None, None, nurse_banda, "2026-07-03 12:05:00"),
        (V["zulu_1"], P["zulu"], 39.5, 110, 24, 130, 85, 93, 80.0, 172, None, None, None, nurse_banda, "2026-07-03 08:50:00"),
        (V["mwanza_1"], P["mwanza"], 36.9, 88, 19, 100, 65, 99, 70.5, 160, None, None, None, nurse_banda, "2026-07-03 09:35:00"),
        (V["nyirenda_1"], P["nyirenda"], 36.7, 84, 17, 125, 80, 98, 68.0, 163, None, None, None, nurse_banda, "2026-07-03 13:05:00"),
    ]
    for vid, pid, temp, hr, rr, sys_bp, dia_bp, spo2, wt, ht, bmi, muac, glucose, recorded_by, recorded_at in vitals_data:
        conn.execute(text("""
            INSERT INTO vitals (visit_id, patient_id, temperature_celsius, heart_rate_bpm,
                respiratory_rate, systolic_bp_mmhg, diastolic_bp_mmhg,
                oxygen_saturation_percent, weight_kg, height_cm, bmi, muac_cm,
                blood_glucose_mmol_l, recorded_by, recorded_at)
            VALUES (:vid, :pid, :temp, :hr, :rr, :sys_bp, :dia_bp, :spo2, :wt, :ht,
                :bmi, :muac, :glucose, :recorded_by, :recorded_at)
        """), {
            "vid": vid, "pid": pid, "temp": temp, "hr": hr, "rr": rr,
            "sys_bp": sys_bp, "dia_bp": dia_bp, "spo2": spo2, "wt": wt,
            "ht": ht, "bmi": bmi, "muac": muac, "glucose": glucose,
            "recorded_by": recorded_by, "recorded_at": recorded_at,
        })

    # ── CLINICAL NOTES ─────────────────────────────────────────────────────
    notes = [
        (P["chilufya"], V["chilufya_1"], "consultation", "Fever 3 days, vomiting 2x/day, poor feeding",
         "Acute febrile illness. Child appears unwell. Nae positive for malaria.",
         "Malaria RDT positive → start Artemether/Lumefantrine", True,
         "MAL001", dr_mwamba, "2026-07-03 09:45:00"),
        (P["banda"], V["banda_1"], "consultation",
         "Cough 3 weeks, night sweats, weight loss 4kg unintentionally",
         "Productive cough, night drenching sweats, loss of appetite. TB screening ordered.",
         "Chest X-ray and GeneXpert Ultra sputum TB. Start empirical antibiotics.",
         False, None, dr_mwamba, "2026-07-03 11:20:00"),
        (P["phiri"], V["phiri_1"], "consultation",
         "Routine HIV follow-up. Compliant with TLD. No new complaints.",
         "Stable on ART. No OIs. CD4 350 (6 months ago). VL undetectable (last 2 visits).",
         "Continue TLD. Repeat CD4 and VL. Return 3 months. Cervical screening due.",
         True, "HIV001", dr_mwamba, "2026-07-03 11:50:00"),
        (P["tembo"], V["tembo_1"], "consultation",
         "Cough 4 weeks, weight loss 8kg, night sweats, haemoptysis 2x",
         "Cachectic appearance. Chest auscultation: crepitations right upper lobe. High index for TB.",
         "Admit for TB workup. Sputum GeneXpert, CXR. Start RHZE if positive.",
         False, "TB001", dr_mwamba, "2026-07-03 12:20:00"),
        (P["zulu"], V["zulu_1"], "consultation",
         "Severe headache, high fever, body aches 2 days. No vomiting.",
         "Febrile, tachycardic. Positive rapid malaria test. No signs of severe malaria.",
         "Artemether/Lumefantrine 20/120mg 4 tabs BD x3 days. Paracetamol PRN. Return if no improvement 48h.",
         True, "MAL001", dr_mwamba, "2026-07-03 09:15:00"),
        (P["nyirenda"], V["nyirenda_1"], "consultation",
         "Polyuria, polydipsia, weight loss 5kg over 2 months. Fatigue.",
         "Random blood glucose 14.2 mmol/L. Urine ketones negative. BMI 25.5.",
         "Diagnose Type 2 Diabetes Mellitus. Start Metformin 500mg BD. Dietary counselling. HbA1c, FBC, RFTs.",
         True, "BCH001", dr_mwamba, "2026-07-03 13:30:00"),
    ]
    for pid, vid, note_type, complaint, assessment, plan, confirmed, icd10, created_by, created_at in notes:
        conn.execute(text("""
            INSERT INTO clinical_notes (visit_id, patient_id, note_type, chief_complaint,
                assessment, plan, is_confirmed_diagnosis, diagnosis_icd10_codes, created_by, created_at)
            VALUES (:vid, :pid, :note_type, :complaint, :assessment, :plan,
                :confirmed, ARRAY[:icd10], :created_by, :created_at)
        """), {
            "vid": vid, "pid": pid, "note_type": note_type, "complaint": complaint,
            "assessment": assessment, "plan": plan, "confirmed": confirmed,
            "icd10": icd10, "created_by": created_by, "created_at": created_at,
        })

    # ── LAB ORDERS ──────────────────────────────────────────────────────────
    lab_orders = [
        (LO["chilufya_malaria"], "LO-2026-0001", V["chilufya_1"], P["chilufya"],
         1, "high", "ordered", dr_mwamba, "2026-07-03 09:20:00"),
        (LO["banda_hiv"], "LO-2026-0002", V["banda_1"], P["banda"],
         16, "high", "ordered", dr_mwamba, "2026-07-03 11:10:00"),
        (LO["phiri_hiv"], "LO-2026-0003", V["phiri_1"], P["phiri"],
         17, "medium", "completed", dr_mwamba, "2026-07-03 11:30:00"),
        (LO["tembo_tb"], "LO-2026-0004", V["tembo_1"], P["tembo"],
         13, "critical", "ordered", dr_mwamba, "2026-07-03 12:10:00"),
        (LO["zulu_malaria"], "LO-2026-0005", V["zulu_1"], P["zulu"],
         1, "high", "completed", dr_mwamba, "2026-07-03 08:50:00"),
        (LO["mwanza_hb"], "LO-2026-0006", V["mwanza_1"], P["mwanza"],
         26, "medium", "ordered", nurse_banda, "2026-07-03 09:40:00"),
        (LO["nyirenda_glucose"], "LO-2026-0007", V["nyirenda_1"], P["nyirenda"],
         29, "high", "completed", dr_mwamba, "2026-07-03 13:10:00"),
    ]
    for loid, order_num, vid, pid, test_id, priority, status, ordered_by, ordered_at in lab_orders:
        conn.execute(text("""
            INSERT INTO lab_orders (id, order_number, visit_id, patient_id, test_id,
                priority, status, ordered_by, ordered_at)
            VALUES (:loid, :order_num, :vid, :pid, :test_id, :priority, :status,
                :ordered_by, :ordered_at)
        """), {
            "loid": loid, "order_num": order_num, "vid": vid, "pid": pid,
            "test_id": test_id, "priority": priority, "status": status,
            "ordered_by": ordered_by, "ordered_at": ordered_at,
        })

    # Get lab test catalog IDs for result values
    test_ids = {}
    for code in ["MAL001", "HIV001", "TB001", "CBC002", "BCH001", "HIV002"]:
        tid = conn.execute(
            text("SELECT id FROM lab_test_catalog WHERE code = :code"),
            {"code": code}
        ).scalar()
        test_ids[code] = tid

    # ── LAB RESULTS ─────────────────────────────────────────────────────────
    lab_results = [
        (LO["zulu_malaria"], P["zulu"], "Positive (+++)", None, None, None,
         True, True, "Malaria RDT positive (+++). P. falciparum detected.",
         "Malaria infection confirmed. Start antimalarial therapy.",
         lab_kasonde, "2026-07-03 09:00:00", lab_kasonde, "2026-07-03 09:05:00"),
        (LO["phiri_hiv"], P["phiri"], "Undetectable", 0, "copies/mL", None,
         False, False, "HIV Viral Load: <20 copies/mL (Undetectable)",
         "Excellent treatment response. Continue current ART regimen.",
         lab_kasonde, "2026-07-03 11:55:00", lab_kasonde, "2026-07-03 12:00:00"),
        (LO["nyirenda_glucose"], P["nyirenda"], None, 14.2, "mmol/L", 0,
         True, None, "Random Blood Glucose: 14.2 mmol/L (Non-fasting)",
         "Elevated random glucose. Diagnostic for diabetes when confirmed with HbA1c.",
         lab_kasonde, "2026-07-03 13:15:00", lab_kasonde, "2026-07-03 13:20:00"),
    ]
    for loid, pid, result_text, result_num, result_unit, ref_low, is_abnormal, is_positive, result_value, interpretation, performed_by, performed_at, verified_by, verified_at in lab_results:
        conn.execute(text("""
            INSERT INTO lab_results (lab_order_id, patient_id, result_value, result_numeric,
                result_unit, reference_range_low, is_abnormal, is_positive, result_text,
                interpretation, performed_by, performed_at, verified_by, verified_at)
            VALUES (:loid, :pid, :result_value, :result_num, :result_unit, :ref_low,
                :is_abnormal, :is_positive, :result_text, :interpretation,
                :performed_by, :performed_at, :verified_by, :verified_at)
        """), {
            "loid": loid, "pid": pid, "result_value": result_value,
            "result_num": result_num, "result_unit": result_unit,
            "ref_low": ref_low, "is_abnormal": is_abnormal,
            "is_positive": is_positive, "result_text": result_text,
            "interpretation": interpretation, "performed_by": performed_by,
            "performed_at": performed_at, "verified_by": verified_by,
            "verified_at": verified_at,
        })

    # ── PRESCRIPTIONS ───────────────────────────────────────────────────────
    prescriptions = [
        (P["zulu"], V["zulu_1"], "CNS001", "Paracetamol 500mg",
         "500mg", "8 hourly PRN", "Oral", 3, 9, "Tablet", "dispensed",
         False, dr_mwamba, lab_kasonde, "2026-07-03 09:20:00"),
        (P["chilufya"], V["chilufya_1"], "ART001", "Artemether + Lumefantrine 20/120mg",
         "1 tab (20/120mg)", "12 hourly x 3 days", "Oral", 3, 6, "Tablet", "dispensed",
         False, dr_mwamba, lab_kasonde, "2026-07-03 09:50:00"),
        (P["phiri"], V["phiri_1"], "HIV001", "TLD (Tenofovir/Lamivudine/Dolutegravir)",
         "1 tab daily", "Daily", "Oral", 90, 90, "Tablet", "active",
         False, dr_mwamba, None, None),
        (P["nyirenda"], V["nyirenda_1"], "END001", "Metformin 500mg",
         "500mg", "12 hourly", "Oral", 90, 180, "Tablet", "active",
         False, dr_mwamba, None, None),
    ]
    for pid, vid, med_code, med_name, dosage, freq, route, duration, qty, qty_unit, status, is_controlled, prescribed_by, dispensed_by, dispensed_at in prescriptions:
        conn.execute(text("""
            INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
                medicine_code, medicine_name, dosage, frequency, route,
                duration_days, quantity, quantity_unit, status, is_controlled_drug,
                prescribed_by, dispensed_by, dispensed_at)
            VALUES (:rx_num, :vid, :pid, :med_code, :med_name, :dosage, :freq,
                :route, :duration, :qty, :qty_unit, :status, :is_controlled,
                :prescribed_by, :dispensed_by, :dispensed_at)
            ON CONFLICT DO NOTHING
        """), {
            "rx_num": f"RX-2026-{pid[:8]}",
            "vid": vid, "pid": pid, "med_code": med_code, "med_name": med_name,
            "dosage": dosage, "freq": freq, "route": route,
            "duration": duration, "qty": qty, "qty_unit": qty_unit,
            "status": status, "is_controlled": is_controlled,
            "prescribed_by": prescribed_by, "dispensed_by": dispensed_by,
            "dispensed_at": dispensed_at,
        })

    # ── IMMUNIZATIONS ──────────────────────────────────────────────────────
    immunizations = [
        (P["kunda"], "BCG", "BCG (Tuberculosis)", 0, "2026-01-24",
         "2026-01-24", "administered", "UNICEF-BCG-2026-01", "UNICEF",
         "Left deltoid", "Intradermal", None, nurse_banda, uth_id),
        (P["kunda"], "OPV0", "Oral Polio Vaccine (OPV)", 0, "2026-01-24",
         "2026-01-24", "administered", "UNICEF-OPV-2026-01", "UNICEF",
         None, "Oral", None, nurse_banda, uth_id),
        (P["kunda"], "OPV1", "Oral Polio Vaccine (OPV)", 1, "2026-03-07",
         None, "scheduled", None, None, None, None, None, None, None),
        (P["kunda"], "PENTA1", "Pentavalent (DTP-HepB-Hib)", 1, "2026-03-07",
         None, "scheduled", None, None, None, None, None, None, None),
        (P["kunda"], "PCV1", "Pneumococcal Conjugate (PCV)", 1, "2026-03-07",
         None, "scheduled", None, None, None, None, None, None, None),
        (P["kunda"], "ROTA1", "Rotavirus Vaccine", 1, "2026-03-07",
         None, "scheduled", None, None, None, None, None, None, None),
        (P["chilufya"], "OPV1", "Oral Polio Vaccine (OPV)", 1, "2021-09-26",
         "2021-09-26", "administered", "UNICEF-OPV-2021-B2", "UNICEF",
         None, "Oral", None, nurse_banda, kanyama_id),
        (P["chilufya"], "PENTA1", "Pentavalent (DTP-HepB-Hib)", 1, "2021-09-26",
         "2021-09-26", "administered", "UNICEF-PENTA-2021-B2", "UNICEF",
         "Left thigh", "IM", None, nurse_banda, kanyama_id),
        (P["chilufya"], "PCV1", "Pneumococcal Conjugate (PCV)", 1, "2021-09-26",
         "2021-09-26", "administered", "UNICEF-PCV-2021-B2", "UNICEF",
         "Right thigh", "IM", None, nurse_banda, kanyama_id),
        (P["chilufya"], "ROTA1", "Rotavirus Vaccine", 1, "2021-09-26",
         "2021-09-26", "administered", "UNICEF-ROTA-2021-B2", "UNICEF",
         None, "Oral", None, nurse_banda, kanyama_id),
        (P["chilufya"], "OPV2", "Oral Polio Vaccine (OPV)", 2, "2021-10-24",
         "2021-10-24", "administered", "UNICEF-OPV-2021-B3", "UNICEF",
         None, "Oral", None, nurse_banda, kanyama_id),
        (P["chilufya"], "PENTA2", "Pentavalent (DTP-HepB-Hib)", 2, "2021-10-24",
         "2021-10-24", "administered", "UNICEF-PENTA-2021-B3", "UNICEF",
         "Left thigh", "IM", None, nurse_banda, kanyama_id),
        (P["chilufya"], "MEAS1", "Measles Rubella (MR)", 1, "2022-05-15",
         "2022-05-15", "administered", "UNICEF-MR-2022-A1", "UNICEF",
         "Left upper arm", "SC", None, nurse_banda, kanyama_id),
    ]
    for pid, vac_code, vac_name, dose, scheduled_date, admin_date, status, batch, mfr, site, route_name, adverse_event, administered_by, fac_id in immunizations:
        conn.execute(text("""
            INSERT INTO immunizations (patient_id, vaccine_code, vaccine_name, dose_number,
                scheduled_date, administered_date, status, batch_number, manufacturer,
                administration_site, route, adverse_event, administered_by, facility_id)
            VALUES (:pid, :vac_code, :vac_name, :dose, :scheduled_date,
                CAST(NULLIF(:admin_date, '') AS DATE), :status, :batch, :mfr,
                :site, :route_name, :adverse_event, :administered_by, :fac_id)
        """), {
            "pid": pid, "vac_code": vac_code, "vac_name": vac_name,
            "dose": dose, "scheduled_date": scheduled_date,
            "admin_date": admin_date or "", "status": status,
            "batch": batch, "mfr": mfr, "site": site,
            "route_name": route_name, "adverse_event": adverse_event,
            "administered_by": administered_by, "fac_id": fac_id,
        })

    # ── INVENTORY STOCK ─────────────────────────────────────────────────────
    stock_data = {
        "ART001": ("Artemether + Lumefantrine 20/120mg", "Antimalarial"),
        "HIV001": ("TLD (Tenofovir/Lamivudine/Dolutegravir)", "Antiretroviral"),
        "TB001": ("Rifampicin/Isoniazid/Pyrazinamide/Ethambutol", "Antitubercular"),
        "CNS001": ("Paracetamol 500mg", "Analgesic"),
        "END001": ("Metformin 500mg", "Antidiabetic"),
    }
    stock_updates = [
        ("ART001", uth_id, 5000, 2000, 3000, 500, "Tablet"),
        ("HIV001", uth_id, 12000, 8000, 4000, 1000, "Tablet"),
        ("TB001", uth_id, 3000, 2500, 500, 300, "Tablet"),
        ("CNS001", uth_id, 8000, 6500, 1500, 500, "Tablet"),
        ("END001", uth_id, 6000, 4000, 2000, 400, "Tablet"),
        ("ART001", kanyama_id, 2000, 1400, 600, 200, "Tablet"),
        ("CNS001", kanyama_id, 5000, 3200, 1800, 300, "Tablet"),
    ]
    for item_code, fac_id, received, dispensed, available, reorder, unit in stock_updates:
        row = conn.execute(
            text("SELECT id FROM inventory_items WHERE item_code = :code AND facility_id = :fid"),
            {"code": item_code, "fid": fac_id}
        ).fetchone()
        if not row:
            item_name, category = stock_data[item_code]
            conn.execute(text("""
                INSERT INTO inventory_items (item_code, item_name, category, facility_id,
                    current_stock, minimum_stock, reorder_point, unit_of_measure, is_active)
                VALUES (:code, :item_name, :category,
                    :fid, :available, 100, :reorder, :unit, true)
            """), {"code": item_code, "item_name": item_name, "category": category,
                   "fid": fac_id, "available": available, "reorder": reorder, "unit": unit})
        else:
            conn.execute(text("""
                UPDATE inventory_items SET current_stock = :available, reorder_point = :reorder
                WHERE id = :item_id
            """), {"available": available, "reorder": reorder, "item_id": row[0]})


def downgrade() -> None:
    conn = op.get_bind()
    patient_ids = list(P.values())
    visit_ids = list(V.values())
    lab_order_ids = list(LO.values())

    conn.execute(text("DELETE FROM lab_results WHERE lab_order_id = ANY(:ids)"),
                 {"ids": lab_order_ids})
    conn.execute(text("DELETE FROM lab_orders WHERE id = ANY(:ids)"),
                 {"ids": lab_order_ids})
    conn.execute(text("DELETE FROM prescriptions WHERE patient_id = ANY(:ids)"),
                 {"ids": patient_ids})
    conn.execute(text("DELETE FROM immunizations WHERE patient_id = ANY(:ids)"),
                 {"ids": patient_ids})
    conn.execute(text("DELETE FROM clinical_notes WHERE patient_id = ANY(:ids)"),
                 {"ids": patient_ids})
    conn.execute(text("DELETE FROM vitals WHERE patient_id = ANY(:ids)"),
                 {"ids": patient_ids})
    conn.execute(text("DELETE FROM visits WHERE id = ANY(:ids)"),
                 {"ids": visit_ids})
    conn.execute(text("DELETE FROM patients WHERE id = ANY(:ids)"),
                 {"ids": patient_ids})
    # Reset inventory stock for demo items back to 0
    conn.execute(text("""
        UPDATE inventory_items SET current_stock = 0
        WHERE item_code IN ('ART001','HIV001','TB001','CNS001','END001')
    """))


if __name__ == "__main__":
    upgrade()
