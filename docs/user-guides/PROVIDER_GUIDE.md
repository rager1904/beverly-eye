# UbuntuCare Provider Guide

For clinicians, nurses, and clinical officers using UbuntuCare.

---

## Getting Started

1. **Login**: Visit `https://portal.ubuntucare.zm` → Login with MoH credentials → MFA
2. **Dashboard**: See your schedule, pending tasks, recent patients
3. **Profile**: Set language preference, notification settings, signature

### Supported Languages

- English (default)
- Nyanja (partial)
- Bemba (partial)

*Language support via ASR transcription and patient-facing content.*

---

## Clinical Workflow

### 1. Patient Check-In

```
Patient arrival → Clerk registers/checks in → System assigns to queue
    → You receive notification → Patient appears in your queue
```

### 2. Triage (if applicable)

```
Open Triage Dashboard
    → Select patient
    → Vitals auto-filled from encounter (or enter manually)
    → System calculates MEWS score
    → Acuity level displayed
    → Proceed to consultation
```

### 3. Clinical Consultation

```
Open patient encounter
    → Start voice recording (optional)
    → Conduct consultation naturally
    → System transcribes in real-time
    → After consultation: "Generate Note"
    → Review AI-generated SOAP note
    → Edit as needed
    → Add ICD-10 codes (AI-suggested)
    → Sign note
```

#### Voice-Activated Documentation

```bash
# The system listens during the encounter and:
1. Transcribes provider-patient conversation
2. Extracts key clinical information
3. Generates structured SOAP note
4. Suggests ICD-10 codes
5. Checks drug interactions (if medications mentioned)
6. Flags for disease surveillance (if applicable)

# You can speak naturally. The AI understands:
- "Patient has fever for 3 days" → Subjective
- "Temp is 38.5, BP 120/80" → Objective
- "Diagnosis is malaria" → Assessment
- "Prescribe Artemether-Lumefantrine" → Plan
```

### 4. Orders

```
Within an encounter, you can:
    → Lab: Order tests from Zambia lab catalog
    → Imaging: Request X-ray, ultrasound, CT
    → Pharmacy: Prescribe medications (with interaction check)
    → Referral: Refer to specialist or higher facility
    → Procedure: Schedule procedure
```

### 5. Prescriptions

```
Select "New Prescription"
    → Search medication by name (Zambia EML)
    → Dosage auto-calculated (or manual)
    → Drug interaction check runs automatically
    → Antibiotic stewardship prompt (if applicable)
    → Submit → Sent to pharmacy queue
```

### 6. Follow-Up

```
Auto-schedule follow-up based on:
    → Clinical protocol (e.g., malaria: 3-day follow-up)
    → Chronic condition (e.g., HIV: 30-day refill)
    → Or manually set date

Patient receives SMS reminder in their preferred language.
```

---

## AI Features

### Clinical Documentation Agent

The AI listens during consultations and generates SOAP notes. It:
- Separates subjective vs objective information
- Suggests diagnoses with ICD-10 codes
- Generates treatment plan
- Flags incomplete information
- Learns from your corrections

### Drug Interaction Checker

Automatically checks new prescriptions against:
- Current patient medications
- Known allergies
- Zambia EML contraindications
- Pregnancy/lactation warnings

### Clinical Decision Support

```
Use "Ask AI Assistant" for:
    → "What is the Zambia protocol for severe malaria?"
    → "Alternatives to Artemether-Lumefantrine?"
    → "WHO guidelines for TB/HIV co-management"
    → "Drug interactions with Tenofovir"
```

### Triage Agent

For use at triage desk or in emergency:
- Enter symptoms → Get acuity score + recommendation
- Zambia-specific algorithms (malaria severity, HIV symptoms)
- Resource-aware recommendations

---

## Zambia-Specific Features

### SmartCare Integration

- Patient records sync with SmartCare
- View past visits from any facility
- Lab results from other facilities visible
- Continuity of care across sites

### NHIMA Billing

- Insurance verification during check-in
- Claim submission at consultation end
- Real-time eligibility check
- Automated billing code suggestion

### Disease Surveillance

When you diagnose a notifiable disease:
- Auto-filled IDSR report
- Sent to District Health Office
- Case-based surveillance data captured
- Outbreak alerts trigger investigation

### Immunization

- Patient's EPI schedule displayed
- Due/overdue vaccinations highlighted
- Zambia EPI protocol integrated
- Batch/lot number tracking
- Cold chain breach alerts

---

## Tips for Best Results

1. **Speak clearly** — The ASR works best with clear speech
2. **Use clinical terms** — The AI understands medical terminology
3. **Review AI output** — Always verify before signing
4. **Correct mistakes** — The AI learns from corrections
5. **Report issues** — Use the feedback button for ASR/clinical errors
6. **Stay offline-aware** — In rural clinics, sync when connected
7. **Use local languages** — Patient-facing content available in Nyanja/Bemba

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ASR not transcribing | Check microphone, check GPU availability |
| AI response slow | Check network or switch to offline mode |
| Patient not found | Search by NRC, SmartCare ID, or phone |
| Sync error | Check connection, retry in 5 minutes |
| Wrong ICD-10 code | Search manually, report to admin |
| Drug not in system | Use generic name, request formulary update |
