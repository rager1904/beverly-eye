"""Enhance demo data: real ICD-10 codes, complete lab results, prescriptions, appointments, follow-up visits.

Revision ID: 006
Revises: 005
Create Date: 2026-07-04

- Replaces lab test codes (MAL001, HIV001, TB001, BCH001) with real ICD-10 codes
- Completes pending lab results with realistic values
- Adds prescriptions for all patients with chronic conditions
- Seeds appointment records for "next appointment" queries
- Adds follow-up visits for longitudinal clinical history
- Expands knowledge base with medication info and health tips
- Fixes lab_kasonde -> pharm_tembo for dispensing
"""

from typing import Optional, Sequence
from uuid import uuid4

from alembic import op
from sqlalchemy import text

revision: str = "006"
down_revision: Optional[str] = "005"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

# Patient UUIDs (must match 005)
P = {
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

# Visit UUIDs (must match 005)
V = {
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

# New visit UUIDs for follow-ups
V2 = {
    "phiri_fu_1": "b3000001-0000-4000-8000-000000000001",
    "tembo_fu_1": "b3000001-0000-4000-8000-000000000002",
    "zulu_fu_1":  "b3000001-0000-4000-8000-000000000003",
    "nyirenda_fu_1": "b3000001-0000-4000-8000-000000000004",
    "simwanza_fu_1": "b3000001-0000-4000-8000-000000000005",
    "mwila_fu_1": "b3000001-0000-4000-8000-000000000006",
}

# Lab order UUIDs (must match 005)
LO = {
    "chilufya_malaria": "c3000001-0000-4000-8000-000000000001",
    "phiri_hiv":        "c3000001-0000-4000-8000-000000000002",
    "tembo_tb":         "c3000001-0000-4000-8000-000000000003",
    "zulu_malaria":     "c3000001-0000-4000-8000-000000000004",
    "mwanza_hb":        "c3000001-0000-4000-8000-000000000005",
    "banda_hiv":        "c3000001-0000-4000-8000-000000000006",
    "nyirenda_glucose": "c3000001-0000-4000-8000-000000000007",
}


def upgrade() -> None:
    conn = op.get_bind()

    # Resolve foreign keys
    uth_id = conn.execute(text("SELECT id FROM health_facilities WHERE code = 'UH001'")).scalar()
    kanyama_id = conn.execute(text("SELECT id FROM health_facilities WHERE code = 'KNW001'")).scalar()
    ndola_id = conn.execute(text("SELECT id FROM health_facilities WHERE code = 'NDH001'")).scalar()
    dr_mwamba = conn.execute(text("SELECT id FROM users WHERE username = 'dr_mwamba'")).scalar()
    nurse_banda = conn.execute(text("SELECT id FROM users WHERE username = 'nurse_banda'")).scalar()
    pharm_tembo = conn.execute(text("SELECT id FROM users WHERE username = 'pharm_tembo'")).scalar()
    lab_kasonde = conn.execute(text("SELECT id FROM users WHERE username = 'lab_kasonde'")).scalar()

    # ── 1. FIX ICD-10 CODES IN CLINICAL NOTES ─────────────────────────────
    icd10_fixes = [
        (V["chilufya_1"], ["B54"]),       # Unspecified malaria (was MAL001)
        (V["phiri_1"],    ["B20"]),        # HIV disease (was HIV001)
        (V["tembo_1"],    ["A15.0"]),      # TB of lung (was TB001)
        (V["zulu_1"],     ["B50.0"]),      # P. falciparum malaria (was MAL001)
        (V["nyirenda_1"], ["E11.9"]),      # Type 2 DM without complications (was BCH001)
    ]
    for vid, codes in icd10_fixes:
        conn.execute(
            text("UPDATE clinical_notes SET diagnosis_icd10_codes = :codes WHERE visit_id = :vid"),
            {"codes": codes, "vid": vid}
        )

    # ── 2. COMPLETE PENDING LAB RESULTS ───────────────────────────────────
    # chilufya_malaria: malaria RDT result (was "ordered", now complete)
    conn.execute(text("""
        UPDATE lab_orders SET status = 'completed' WHERE id = :loid
    """), {"loid": LO["chilufya_malaria"]})
    conn.execute(text("""
        INSERT INTO lab_results (lab_order_id, patient_id, result_value, result_numeric,
            result_unit, is_abnormal, is_positive, result_text, interpretation,
            performed_by, performed_at, verified_by, verified_at)
        VALUES (:loid, :pid, 'Positive (+++)', NULL, NULL, True, True,
            'Malaria RDT: P. falciparum antigen positive (+++)',
            'Malaria infection confirmed. Start AL per guidelines.',
            :lab, :at, :lab, :at2)
    """), {
        "loid": LO["chilufya_malaria"], "pid": P["chilufya"],
        "lab": lab_kasonde, "at": "2026-07-03 09:35:00", "at2": "2026-07-03 09:40:00"
    })

    # banda_hiv: HIV rapid test result
    conn.execute(text("""
        UPDATE lab_orders SET status = 'completed' WHERE id = :loid
    """), {"loid": LO["banda_hiv"]})
    conn.execute(text("""
        INSERT INTO lab_results (lab_order_id, patient_id, result_value,
            is_abnormal, is_positive, result_text, interpretation,
            performed_by, performed_at, verified_by, verified_at)
        VALUES (:loid, :pid, 'Positive (Reactive)', True, True,
            'HIV-1/2 Rapid Test: Reactive. Confirmatory test: Positive.',
            'HIV diagnosis confirmed. Initiate ART (TLD) per guidelines.',
            :lab, :at, :lab, :at2)
    """), {
        "loid": LO["banda_hiv"], "pid": P["banda"],
        "lab": lab_kasonde, "at": "2026-07-03 11:25:00", "at2": "2026-07-03 11:30:00"
    })

    # tembo_tb: GeneXpert result
    conn.execute(text("""
        UPDATE lab_orders SET status = 'completed' WHERE id = :loid
    """), {"loid": LO["tembo_tb"]})
    conn.execute(text("""
        INSERT INTO lab_results (lab_order_id, patient_id, result_value,
            is_abnormal, is_positive, result_text, interpretation,
            performed_by, performed_at, verified_by, verified_at)
        VALUES (:loid, :pid, 'MTB detected (medium), Rifampicin resistance NOT detected', True, True,
            'GeneXpert Ultra: MTB detected, RIF resistance not detected. Ct value: 22 (medium).',
            'Drug-sensitive TB confirmed. Start standard 2HRZE/4HR regimen.',
            :lab, :at, :lab, :at2)
    """), {
        "loid": LO["tembo_tb"], "pid": P["tembo"],
        "lab": lab_kasonde, "at": "2026-07-03 13:30:00", "at2": "2026-07-03 13:45:00"
    })

    # mwanza_hb: haemoglobin result
    conn.execute(text("""
        UPDATE lab_orders SET status = 'completed' WHERE id = :loid
    """), {"loid": LO["mwanza_hb"]})
    conn.execute(text("""
        INSERT INTO lab_results (lab_order_id, patient_id, result_value, result_numeric,
            result_unit, reference_range_low, is_abnormal, result_text, interpretation,
            performed_by, performed_at, verified_by, verified_at)
        VALUES (:loid, :pid, NULL, 9.8, 'g/dL', 12.0, True,
            'Hb: 9.8 g/dL (reference: 12.0-16.0 g/dL)',
            'Mild anaemia in pregnancy. Start ferrous sulfate 200mg + folic acid 5mg daily.',
            :lab, :at, :lab, :at2)
    """), {
        "loid": LO["mwanza_hb"], "pid": P["mwanza"],
        "lab": lab_kasonde, "at": "2026-07-03 09:55:00", "at2": "2026-07-03 10:00:00"
    })

    # ── 3. ADD CLINICAL NOTE for bandia HIV (was missing diagnosis note) ──
    existing = conn.execute(
        text("SELECT id FROM clinical_notes WHERE visit_id = :vid"),
        {"vid": V["banda_1"]}
    ).scalar()
    if not existing:
        conn.execute(text("""
            INSERT INTO clinical_notes (visit_id, patient_id, note_type, chief_complaint,
                assessment, plan, is_confirmed_diagnosis, diagnosis_icd10_codes, created_by, created_at)
            VALUES (:vid, :pid, 'consultation',
                'Cough and night sweats for 3 weeks, weight loss, fatigue',
                'Symptomatic presentation concerning for HIV/TB. HIV rapid test positive. Awaiting CD4 and VL.',
                'Start TLD ART. TB screening - CXR and GeneXpert. Septrin prophylaxis 960mg daily. Schedule follow-up in 2 weeks.',
                True, ARRAY['B20'], :doc, :at)
        """), {
            "vid": V["banda_1"], "pid": P["banda"],
            "doc": dr_mwamba, "at": "2026-07-03 11:45:00"
        })

    # ── 4. ADD PRESCRIPTIONS FOR ALL PATIENTS ─────────────────────────────
    # phiri - already has TLD and is active. Add Septrin prophylaxis.
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-PHIRI-ADJ', :vid, :pid, 'HIV002', 'Septrin (Cotrimoxazole) 960mg',
            '960mg', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, NULL, NULL)
    """), {"vid": V["phiri_1"], "pid": P["phiri"], "doc": dr_mwamba})

    # tembo - TB treatment prescription
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-TEMBO-TB', :vid, :pid, 'TB001', 'RHZE (Rifampicin/Isoniazid/Pyrazinamide/Ethambutol)',
            '4 tabs (150/75/400/275mg)', 'Daily', 'Oral', 56, 224, 'Tablet', 'active',
            False, :doc, :pharm, :at)
    """), {
        "vid": V["tembo_1"], "pid": P["tembo"],
        "doc": dr_mwamba, "pharm": pharm_tembo, "at": "2026-07-03 14:00:00"
    })

    # banda - new HIV patient. TLD + Septrin
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-BANDA-ART', :vid, :pid, 'HIV001', 'TLD (Tenofovir/Lamivudine/Dolutegravir)',
            '1 tab daily', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, :pharm, :at)
    """), {
        "vid": V["banda_1"], "pid": P["banda"],
        "doc": dr_mwamba, "pharm": pharm_tembo, "at": "2026-07-03 12:00:00"
    })
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-BANDA-SEP', :vid, :pid, 'HIV002', 'Septrin (Cotrimoxazole) 960mg',
            '960mg', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, NULL, NULL)
    """), {"vid": V["banda_1"], "pid": P["banda"], "doc": dr_mwamba})

    # mwanza - antenatal, ferrous sulfate + folic acid
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-MWANZA-FE', :vid, :pid, 'CNS001', 'Ferrous Sulfate + Folic Acid',
            '200mg/5mg', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, :pharm, :at)
    """), {
        "vid": V["mwanza_1"], "pid": P["mwanza"],
        "doc": nurse_banda, "pharm": pharm_tembo, "at": "2026-07-03 10:00:00"
    })

    # simwanza - hypertension. Amlodipine
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-SIMWANZA-HTN', :vid, :pid, 'CNS001', 'Amlodipine 5mg',
            '5mg', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, NULL, NULL)
    """), {"vid": V["simwanza_1"], "pid": P["simwanza"], "doc": dr_mwamba})

    # ── 5. FIX lab_kasonde -> pharm_tembo for existing dispensings ────────
    conn.execute(text("""
        UPDATE prescriptions SET dispensed_by = :pharm
        WHERE dispensed_by = :lab AND medicine_code IN ('CNS001', 'ART001')
    """), {"pharm": pharm_tembo, "lab": lab_kasonde})

    # ── 6. ADD FOLLOW-UP VISITS FOR CHRONIC PATIENTS ──────────────────────
    follow_up_visits = [
        (V2["phiri_fu_1"], P["phiri"], uth_id, "chronic_care", "completed", "medium",
         "Routine HIV follow-up. Compliant with TLD. Feels well.",
         dr_mwamba, "2026-06-15 10:00:00"),
        (V2["tembo_fu_1"], P["tembo"], ndola_id, "outpatient", "completed", "medium",
         "TB treatment month 2 review. RHZE continuation. Cough improved, weight stable.",
         dr_mwamba, "2026-07-01 14:00:00"),
        (V2["zulu_fu_1"], P["zulu"], uth_id, "outpatient", "completed", "low",
         "Post-malaria follow-up. Completed AL course. Symptoms resolved.",
         dr_mwamba, "2026-07-10 09:00:00"),
        (V2["nyirenda_fu_1"], P["nyirenda"], uth_id, "chronic_care", "scheduled", "medium",
         "Diabetes follow-up. Check HbA1c results and adjust Metformin dose.",
         dr_mwamba, "2026-07-20 11:00:00"),
        (V2["simwanza_fu_1"], P["simwanza"], uth_id, "chronic_care", "scheduled", "medium",
         "Hypertension follow-up. Check BP control and Amlodipine compliance.",
         dr_mwamba, "2026-07-25 09:00:00"),
        (V2["mwila_fu_1"], P["mwila"], uth_id, "antenatal", "scheduled", "medium",
         "ANC follow-up. 32 weeks. Check BP, IPTp-SP dose 3, Hb.",
         nurse_banda, "2026-07-18 10:30:00"),
    ]
    for vid, pid, fac_id, vtype, vstatus, priority, triage_notes, created_by, created_at in follow_up_visits:
        conn.execute(text("""
            INSERT INTO visits (id, patient_id, facility_id, visit_type, visit_status,
                priority, triage_notes, created_by, created_at)
            VALUES (:vid, :pid, :fac_id, :vtype, :vstatus, :priority, :triage_notes, :created_by, :created_at)
        """), {
            "vid": vid, "pid": pid, "fac_id": fac_id, "vtype": vtype,
            "vstatus": vstatus, "priority": priority, "triage_notes": triage_notes,
            "created_by": created_by, "created_at": created_at,
        })

    # Add vitals for follow-ups
    follow_up_vitals = [
        (V2["phiri_fu_1"], P["phiri"], 36.6, 80, 16, 126, 80, 98, 72.5, None, None, None, None, nurse_banda, "2026-06-15 10:05:00"),
        (V2["tembo_fu_1"], P["tembo"], 36.9, 88, 18, 118, 76, 97, 49.5, None, None, None, None, nurse_banda, "2026-07-01 14:05:00"),
        (V2["zulu_fu_1"], P["zulu"], 36.5, 76, 16, 125, 80, 99, 80.0, None, None, None, None, nurse_banda, "2026-07-10 09:05:00"),
    ]
    for vid, pid, temp, hr, rr, sys_bp, dia_bp, spo2, wt, ht, bmi, muac, glucose, recorded_by, recorded_at in follow_up_vitals:
        conn.execute(text("""
            INSERT INTO vitals (visit_id, patient_id, temperature_celsius, heart_rate_bpm,
                respiratory_rate, systolic_bp_mmhg, diastolic_bp_mmhg,
                oxygen_saturation_percent, weight_kg, recorded_by, recorded_at)
            VALUES (:vid, :pid, :temp, :hr, :rr, :sys_bp, :dia_bp, :spo2, :wt, :recorded_by, :recorded_at)
        """), {
            "vid": vid, "pid": pid, "temp": temp, "hr": hr, "rr": rr,
            "sys_bp": sys_bp, "dia_bp": dia_bp, "spo2": spo2, "wt": wt,
            "recorded_by": recorded_by, "recorded_at": recorded_at,
        })

    # Add clinical notes for follow-up visits
    fu_notes = [
        (P["phiri"], V2["phiri_fu_1"], "consultation",
         "Routine HIV follow-up. Compliant with TLD. No complaints.",
         "Stable on ART. No OIs. BP 126/80. Weight stable.",
         "Continue TLD. Septrin 960mg daily. Repeat CD4/VL. Return 3 months.",
         True, ["B20"], dr_mwamba, "2026-06-15 10:30:00"),
        (P["tembo"], V2["tembo_fu_1"], "consultation",
         "TB treatment month 2 review. Cough improved, no haemoptysis. Appetite returning.",
         "Improving on RHZE. Sputum conversion expected. Weight gain 1.5kg.",
         "Continue RHZE intensive phase for 2 more weeks then switch to continuation RH. DOT continues.",
         True, ["A15.0"], dr_mwamba, "2026-07-01 14:30:00"),
        (P["zulu"], V2["zulu_fu_1"], "consultation",
         "Post-malaria follow-up. Completed AL course. No fever for 5 days.",
         "Clinically recovered. No signs of severe malaria sequelae.",
         "Discharged from follow-up. Return if symptoms recur. Use ITN consistently.",
         True, ["B50.0"], dr_mwamba, "2026-07-10 09:30:00"),
    ]
    for pid, vid, note_type, complaint, assessment, plan, confirmed, icd10, created_by, created_at in fu_notes:
        existing_note = conn.execute(
            text("SELECT id FROM clinical_notes WHERE visit_id = :vid"), {"vid": vid}
        ).scalar()
        if not existing_note:
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

    # ── 7. SEED APPOINTMENTS ──────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS appointments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id UUID NOT NULL,
            patient_name VARCHAR(200),
            patient_phone VARCHAR(20),
            provider_id UUID,
            provider_name VARCHAR(200),
            department VARCHAR(100),
            appointment_type VARCHAR(50),
            appointment_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            duration_minutes INTEGER DEFAULT 30,
            status VARCHAR(50) DEFAULT 'scheduled',
            reason TEXT,
            facility_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    appointments = [
        (P["phiri"], "Dr. Michael Phiri", "+260977100007", dr_mwamba, "Dr. John Mwamba",
         "HIV Clinic", "follow_up", "2026-07-20", "09:00", "09:30", "scheduled",
         "Routine HIV follow-up. CD4 and VL check.", uth_id),
        (P["tembo"], "Agnes Tembo", "+260977100009", dr_mwamba, "Dr. John Mwamba",
         "TB Clinic", "follow_up", "2026-07-15", "14:00", "14:30", "scheduled",
         "TB treatment review. Month 2 sputum check.", ndola_id),
        (P["nyirenda"], "Catherine Nyirenda", "+260977100020", dr_mwamba, "Dr. John Mwamba",
         "Diabetes Clinic", "follow_up", "2026-07-20", "11:00", "11:30", "scheduled",
         "Diabetes follow-up. HbA1c results review.", uth_id),
        (P["simwanza"], "Nathan Simwanza", "+260977100018", dr_mwamba, "Dr. John Mwamba",
         "Hypertension Clinic", "follow_up", "2026-07-25", "09:00", "09:30", "scheduled",
         "Hypertension follow-up. BP check.", uth_id),
        (P["mwila"], "Joyce Mwila", "+260977100003", nurse_banda, "Sister Grace Banda",
         "ANC Clinic", "antenatal", "2026-07-18", "10:30", "11:00", "scheduled",
         "ANC visit. 32 weeks. IPTp-SP dose 3.", uth_id),
        (P["kunda"], "Patrick Kunda", "+260977100016", nurse_banda, "Sister Grace Banda",
         "Immunization Clinic", "general", "2026-07-10", "08:30", "09:00", "scheduled",
         "6-week immunization visit.", uth_id),
        (P["banda"], "Sarah Banda", "+260977100005", dr_mwamba, "Dr. John Mwamba",
         "HIV Clinic", "follow_up", "2026-07-17", "11:00", "11:30", "scheduled",
         "New HIV patient follow-up. Start ART review.", uth_id),
        (P["zulu"], "David Zulu", "+260977100011", dr_mwamba, "Dr. John Mwamba",
         "General Outpatient", "general", "2026-07-28", "09:00", "09:15", "scheduled",
         "General check-up post-malaria.", uth_id),
    ]
    for pid, pname, pphone, provider_id, provider_name, dept, atype, adate, start_t, end_t, status, reason, fac_id in appointments:
        conn.execute(text("""
            INSERT INTO appointments (patient_id, patient_name, patient_phone,
                provider_id, provider_name, department, appointment_type,
                appointment_date, start_time, end_time, duration_minutes,
                status, reason, facility_id, created_at, updated_at)
            VALUES (:pid, :pname, :pphone, :prov, :prov_name, :dept, :atype,
                :adate, :start_t, :end_t, 30,
                :status, :reason, :fac_id, NOW(), NOW())
        """), {
            "pid": pid, "pname": pname, "pphone": pphone,
            "prov": provider_id, "prov_name": provider_name, "dept": dept,
            "atype": atype, "adate": adate, "start_t": start_t, "end_t": end_t,
            "status": status, "reason": reason, "fac_id": fac_id,
        })

    # ── 8. EXPAND KNOWLEDGE BASE ──────────────────────────────────────────
    kb_entries = [
        # Medication information
        ("medication", "antimalarial", "en",
         "Artemether-Lumefantrine (AL) - Zambia Malaria Treatment",
         """Artemether-Lumefantrine (Coartem, AL) is Zambia's first-line treatment for uncomplicated malaria.
Dosage (weight-based): 5-14kg: 1 tab (20/120mg) twice daily x 3 days; 15-24kg: 2 tabs; 25-34kg: 3 tabs; >34kg: 4 tabs.
Take with fatty food to improve absorption. Complete the full 3-day course even if symptoms improve.
Common side effects: nausea, vomiting, headache, dizziness. These usually resolve on their own.
Do not take if you have severe malaria (IV artesunate needed) or known allergy to artemisinin.
Available free at all government health facilities in Zambia."""),

        ("medication", "antiretroviral", "en",
         "TLD (Tenofovir/Lamivudine/Dolutegravir) - Zambia HIV Treatment",
         """TLD is Zambia's first-line ART regimen: Tenofovir 300mg + Lamivudine 300mg + Dolutegravir 50mg once daily.
Dolutegravir is a safe and effective integrase inhibitor with high genetic barrier to resistance.
Take one tablet daily at the same time. Missed dose: take within 12 hours of usual time; if >12 hours, skip and take next dose.
Common side effects (usually resolve in 2-4 weeks): headache, nausea, insomnia, vivid dreams.
Important: Dolutegravir may cause neural tube defects if taken around conception. Pregnancy test recommended for women of childbearing potential.
TLD is free at all government health facilities in Zambia."""),

        ("medication", "diabetes", "en",
         "Metformin - Zambia Diabetes Treatment",
         """Metformin is Zambia's first-line oral medication for Type 2 Diabetes Mellitus.
Starting dose: 500mg once daily with breakfast for 1 week, then increase to 500mg twice daily (with breakfast and dinner).
Maximum dose: 1000mg twice daily (2000mg/day). Extended-release formulation may cause less GI side effects.
Common side effects: nausea, diarrhoea, metallic taste (usually improve within 1-2 weeks).
Take with food to reduce stomach upset. Avoid alcohol while taking Metformin.
Stop Metformin temporarily if you have severe vomiting, diarrhoea, or before contrast dye procedures.
Not for use in severe kidney disease (check eGFR before starting)."""),

        ("medication", "hypertension", "en",
         "Amlodipine - Zambia Hypertension Treatment",
         """Amlodipine is a calcium channel blocker used as first-line treatment for hypertension in Zambia.
Standard dose: 5mg once daily. May be increased to 10mg daily if needed.
Side effects: ankle swelling (oedema), headache, flushing, palpitations, dizziness, fatigue.
Ankle swelling is NOT dangerous - elevate legs, reduce salt intake. It usually decreases over time.
Avoid grapefruit juice while on Amlodipine (increases drug levels).
Do not stop suddenly - may cause rebound hypertension.
Target BP: <140/90 mmHg in most patients; <130/80 if diabetic or have kidney disease."""),

        ("medication", "tb", "en",
         "RHZE (Rifampicin/Isoniazid/Pyrazinamide/Ethambutol) - Zambia TB Treatment",
         """RHZE is Zambia's first-line intensive phase TB treatment: Rifampicin 150mg + Isoniazid 75mg + Pyrazinamide 400mg + Ethambutol 275mg.
Standard adult dose: 4 tablets daily (weight 30-50kg) or 5 tablets daily (>50kg) for 2 months.
Then switch to RH (Rifampicin + Isoniazid) for 4 months continuation phase.
Important: Rifampicin turns urine, sweat, and tears orange-red (harmless).
Isoniazid: take with Pyridoxine (Vitamin B6) 25mg daily to prevent peripheral neuropathy.
Ethambutol: report any vision changes immediately (optic neuropathy - reversible if caught early).
DO NOT drink alcohol during TB treatment (hepatitis risk). DOT (Directly Observed Therapy) is standard in Zambia."""),

        # Health tips for patient queries
        ("health_tip", "malaria_prevention", "en",
         "How to prevent malaria - Health Tips for Zambia",
         """1. Sleep under an insecticide-treated net (ITN) every night, every season.
2. Pregnant women: take SP (Sulfadoxine-Pyrimethamine) at each ANC visit from 16 weeks (at least 3 doses).
3. Clear bushes and standing water around your home (mosquito breeding sites).
4. Keep windows and doors closed in the evenings when mosquitoes are active.
5. If you have fever, go to the clinic immediately for a free malaria test (RDT).
6. Complete your full malaria treatment course even if you feel better.
7. Indoor Residual Spraying (IRS) - allow health workers to spray your home walls."""),

        ("health_tip", "hiv_prevention", "en",
         "How to prevent HIV - Health Tips for Zambia",
         """1. Know your status: get tested for HIV at any health facility (free and confidential).
2. Use condoms correctly and consistently for all sexual encounters (free at clinics).
3. If HIV-negative but at risk: ask about PrEP (pre-exposure prophylaxis) - free at selected facilities.
4. If HIV-positive: start ART immediately and take daily to achieve viral suppression (U=U - Undetectable = Untransmittable).
5. Prevent mother-to-child transmission: all pregnant women should test for HIV and start ART if positive.
6. Male circumcision reduces HIV acquisition risk by approximately 60%.
7. Never share needles or razor blades."""),

        ("health_tip", "healthy_living", "en",
         "General Health Tips for Zambians",
         """1. Eat a balanced diet: nshima, vegetables, beans, groundnuts, fruits, and protein (fish, chicken, soya).
2. Drink clean water: boil or treat water before drinking, or use certified bottled water.
3. Wash hands with soap and clean water: after using the toilet, before eating, after changing baby's nappy.
4. Exercise regularly: 30 minutes of walking, cycling, or farming activity daily.
5. Sleep under a mosquito net every night.
6. Go for regular health check-ups: BP and blood sugar screening annually if over 40.
7. Vaccinate your children according to the EPI schedule (free at all clinics).
8. If pregnant, attend all 8+ ANC visits and deliver at a health facility."""),

        ("health_tip", "child_health", "en",
         "Child Health Tips - Zambia",
         """1. Exclusive breastfeeding for the first 6 months (no water, no other foods).
2. Continue breastfeeding up to 2 years while introducing complementary foods at 6 months.
3. Take your child for immunizations at: birth, 6 weeks, 10 weeks, 14 weeks, 9 months, and 18 months.
4. Growth monitoring: monthly for children under 1 year, quarterly for 1-2 years.
5. Vitamin A supplementation: 6-11 months (100,000 IU), 12-59 months (200,000 IU) every 6 months.
6. If your child has fever, cough, diarrhoea, or is not feeding well, go to the clinic immediately.
7. Give ORS and Zinc if your child has diarrhoea. Continue feeding.
8. Deworming: Albendazole 400mg every 6 months for children 12-59 months."""),

        # Facility information
        ("facility", "uth", "en",
         "University Teaching Hospital (UTH) - Lusaka",
         """University Teaching Hospital (UTH) is Zambia's largest referral hospital located in Lusaka.
Address: Nationalist Road, Lusaka. Phone: +260 211 253 957.
Services: Emergency Medicine, Internal Medicine, Surgery, Paediatrics, Obstetrics & Gynaecology, HIV Clinic, TB Clinic, Diabetes Clinic, Cardiology, Oncology, Radiology.
UTH is a teaching hospital affiliated with the University of Zambia School of Medicine.
It serves as the primary referral centre for Lusaka Province and receives referrals from all over Zambia."""),

        ("facility", "kanyama", "en",
         "Kanyama First Level Hospital - Lusaka",
         """Kanyama First Level Hospital is a district hospital serving the Kanyama compound in Lusaka.
Address: Kanyama Compound, Lusaka. The hospital serves a high-density, low-income community.
Services: Outpatient care, Maternity, Immunization, HIV/ART services, TB treatment, Laboratory, Pharmacy.
It is one of the busiest primary care facilities in Lusaka due to the large population it serves.
The facility has bed capacity, basic laboratory, and provides 24-hour maternity services."""),

        ("facility", "ndola", "en",
         "Ndola Teaching Hospital - Ndola",
         """Ndola Teaching Hospital is a major referral hospital on the Copperbelt Province.
Address: Ndola, Copperbelt Province. Phone: +260 212 617 600.
Services: Emergency Medicine, Internal Medicine, Surgery, Paediatrics, Obstetrics & Gynaecology, TB Clinic.
It serves as the tertiary referral centre for Copperbelt Province and surrounding areas.
The hospital also functions as a teaching hospital for medical students and clinical officers."""),

        # NHIMA information
        ("insurance", "nhima", "en",
         "NHIMA - National Health Insurance Management Authority (Zambia)",
         """NHIMA is Zambia's national health insurance scheme, established under the National Health Insurance Act No. 2 of 2018.
All formally employed Zambians contribute 1% of their monthly salary (minimum contribution).
Benefits include: outpatient care, inpatient care, maternity services, laboratory services, medicines on the EML, immunizations, dental services, eye care.
Registered members receive an NHIMA card and can access care at accredited health facilities across Zambia.
To register: visit any NHIMA office or accredited health facility with your NRC.
Dependents (spouse, up to 5 children) are covered under the member's contribution.
The scheme aims to achieve universal health coverage for all Zambians."""),

        # Zambia-specific disease burden
        ("disease_burden", "zambia", "en",
         "Zambia Disease Burden Overview",
         """Zambia faces a high burden of communicable diseases, with emerging NCD burden.
Malaria: Endemic in all 10 provinces. ~4-6 million cases annually. Peak transmission November-April.
HIV: Prevalence ~11% in adults (15-49). ~1.2 million PLHIV. ~800,000 on ART.
TB: Incidence ~360/100,000. ~60,000 cases annually. High TB/HIV co-infection rate (~60%).
Cholera: Seasonal outbreaks (October-May) in peri-urban areas, especially Lusaka.
Maternal mortality: 213/100,000 live births. Focus on reducing through 8+ ANC contacts, skilled birth attendance.
Under-5 mortality: 59/1,000 live births. Main causes: malaria, pneumonia, diarrhoea, malnutrition.
NCDs: Hypertension (~26% adults), Diabetes (~5% adults). Rapidly increasing, especially in urban areas."""),
    ]

    for cat, subcat, lang, title, content in kb_entries:
        conn.execute(text(f"""
            INSERT INTO knowledge_base (category, subcategory, language, title, content, source)
            VALUES ('{cat}', '{subcat}', '{lang}',
                '{title.replace("'", "''")}', '{content.replace("'", "''")}',
                'UbuntuCare Knowledge Base')
        """))

    # ── 9. ADD follow-up prescriptions (extend ongoing medications) ────────
    # Add Metformin refill for nyirenda (upcoming appointment)
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-NYIRENDA-MET', :vid, :pid, 'END001', 'Metformin 500mg',
            '500mg', '12 hourly', 'Oral', 90, 180, 'Tablet', 'active',
            False, :doc, :pharm, :at)
    """), {
        "vid": V2["nyirenda_fu_1"], "pid": P["nyirenda"],
        "doc": dr_mwamba, "pharm": pharm_tembo, "at": "2026-07-20 11:30:00"
    })

    # Add Amlodipine refill for simwanza
    conn.execute(text("""
        INSERT INTO prescriptions (prescription_number, visit_id, patient_id,
            medicine_code, medicine_name, dosage, frequency, route,
            duration_days, quantity, quantity_unit, status, is_controlled_drug,
            prescribed_by, dispensed_by, dispensed_at)
        VALUES ('RX-2026-SIMWANZA-AML', :vid, :pid, 'CNS001', 'Amlodipine 5mg',
            '5mg', 'Daily', 'Oral', 90, 90, 'Tablet', 'active',
            False, :doc, :pharm, :at)
    """), {
        "vid": V2["simwanza_fu_1"], "pid": P["simwanza"],
        "doc": dr_mwamba, "pharm": pharm_tembo, "at": "2026-07-25 09:30:00"
    })

    # ── 10. ADD VITALS for simwanza (hypertension visit had no vitals) ─────
    existing_simwanza_vitals = conn.execute(
        text("SELECT id FROM vitals WHERE visit_id = :vid"),
        {"vid": V["simwanza_1"]}
    ).scalar()
    if not existing_simwanza_vitals:
        conn.execute(text("""
            INSERT INTO vitals (visit_id, patient_id, temperature_celsius, heart_rate_bpm,
                respiratory_rate, systolic_bp_mmhg, diastolic_bp_mmhg,
                oxygen_saturation_percent, weight_kg, height_cm, recorded_by, recorded_at)
            VALUES (:vid, :pid, 36.7, 82, 17, 148, 92, 97, 72.0, 170, :nurse, :at)
        """), {
            "vid": V["simwanza_1"], "pid": P["simwanza"],
            "nurse": nurse_banda, "at": "2026-07-03 14:00:00"
        })


def downgrade() -> None:
    conn = op.get_bind()

    # Remove new follow-up visit data
    fu_visit_ids = list(V2.values())

    conn.execute(text("DELETE FROM clinical_notes WHERE visit_id = ANY(:ids)"), {"ids": fu_visit_ids})
    conn.execute(text("DELETE FROM vitals WHERE visit_id = ANY(:ids)"), {"ids": fu_visit_ids})
    conn.execute(text("DELETE FROM visits WHERE id = ANY(:ids)"), {"ids": fu_visit_ids})

    # Remove follow-up prescriptions (by prescription_number pattern)
    conn.execute(text("""
        DELETE FROM prescriptions WHERE prescription_number IN (
            'RX-2026-PHIRI-ADJ', 'RX-2026-TEMBO-TB', 'RX-2026-BANDA-ART',
            'RX-2026-BANDA-SEP', 'RX-2026-MWANZA-FE', 'RX-2026-SIMWANZA-HTN',
            'RX-2026-NYIRENDA-MET', 'RX-2026-SIMWANZA-AML'
        )
    """))

    # Remove appointments
    conn.execute(text("DELETE FROM appointments"))

    # Remove new knowledge base entries (by source)
    conn.execute(text("DELETE FROM knowledge_base WHERE source = 'UbuntuCare Knowledge Base'"))

    # Reset lab orders back to 'ordered'
    conn.execute(text("""
        UPDATE lab_orders SET status = 'ordered'
        WHERE id IN (:c, :b, :t, :m)
    """), {
        "c": LO["chilufya_malaria"], "b": LO["banda_hiv"],
        "t": LO["tembo_tb"], "m": LO["mwanza_hb"]
    })

    # Remove completed lab results for those orders
    conn.execute(text("DELETE FROM lab_results WHERE lab_order_id IN (:c, :b, :t, :m)"), {
        "c": LO["chilufya_malaria"], "b": LO["banda_hiv"],
        "t": LO["tembo_tb"], "m": LO["mwanza_hb"]
    })

    # Remove added clinical note for banda
    conn.execute(text("DELETE FROM clinical_notes WHERE visit_id = :vid"), {"vid": V["banda_1"]})

    # Restore original ICD-10 codes
    conn.execute(text("""
        UPDATE clinical_notes SET diagnosis_icd10_codes = ARRAY['MAL001']
        WHERE visit_id = :vid
    """), {"vid": V["chilufya_1"]})
    conn.execute(text("""
        UPDATE clinical_notes SET diagnosis_icd10_codes = ARRAY['HIV001']
        WHERE visit_id = :vid
    """), {"vid": V["phiri_1"]})
    conn.execute(text("""
        UPDATE clinical_notes SET diagnosis_icd10_codes = ARRAY['TB001']
        WHERE visit_id = :vid
    """), {"vid": V["tembo_1"]})
    conn.execute(text("""
        UPDATE clinical_notes SET diagnosis_icd10_codes = ARRAY['MAL001']
        WHERE visit_id = :vid
    """), {"vid": V["zulu_1"]})
    conn.execute(text("""
        UPDATE clinical_notes SET diagnosis_icd10_codes = ARRAY['BCH001']
        WHERE visit_id = :vid
    """), {"vid": V["nyirenda_1"]})

    # Remove the simwanza vitals that were added
    conn.execute(text("DELETE FROM vitals WHERE visit_id = :vid AND recorded_at = '2026-07-03' AND heart_rate_bpm = 82"),
                 {"vid": V["simwanza_1"]})


if __name__ == "__main__":
    upgrade()
