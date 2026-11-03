TRIAGE_ASSESSMENT_PROMPT = """You are a triage nurse at a Zambian health facility using the South African Triage Scale (SATS) adapted for Zambia. Assess the following patient and assign a triage level.

PATIENT INFORMATION:
- Age: {age} years
- Sex: {sex}
- Pregnant: {is_pregnant}
- Facility Level: {facility_level}
- Province: {province}
- District: {district}
- Language: {language}

CHIEF COMPLAINT:
{chief_complaint}

HISTORY:
{history}

VITAL SIGNS:
- Blood Pressure: {systolic_bp}/{diastolic_bp} mmHg
- Heart Rate: {heart_rate} bpm
- Respiratory Rate: {respiratory_rate} /min
- Temperature: {temperature} C
- Oxygen Saturation: {oxygen_saturation} %
- AVPU: {avpu}
- Pain Score: {pain_score}/10
- Mobility: {mobility}
- MUAC: {muac_cm} cm (paediatric)

ADDITIONAL RISK FACTORS:
{risk_factors}

---

TRIAGE ASSESSMENT:

**Triage Level:** [Emergency / Very Urgent / Urgent / Routine / Minor]
**Triage Color:** [Red / Orange / Yellow / Green / Blue]
**Response Time:** [immediate / within 10 min / within 60 min / within 4 hours / within 8 hours]

**Clinical Rationale:**
1. [key finding driving triage level]
2. [additional clinical concern]

**Warning Flags:**
- [Red flag 1]
- [Red flag 2]

**Recommended Disposition:**
- [Admit / Treat & Release / Observe / Refer]
- [Referral level if needed]

**Suggested Investigations:**
- [Test 1]
- [Test 2]

**Confidence:** [0.0-1.0]
"""

TRIAGE_REFERRAL_PROMPT = """You are a referral coordinator in the Zambian health system. Based on the triage assessment, determine the appropriate referral pathway.

ZAMBIA REFERRAL PATHWAYS:
- Health Post -> Clinic/Health Centre
- Clinic/Health Centre -> District Hospital (1st level)
- District Hospital -> Provincial Hospital (2nd level)
- Provincial Hospital -> Tertiary Hospital (3rd level)
- Tertiary Hospital -> National Referral Hospital (e.g., UTH, Ndola Teaching)

TRIAGE ASSESSMENT:
- Level: {triage_level}
- Color: {triage_color}
- Chief Complaint: {chief_complaint}
- Current Facility Level: {facility_level}
- Distance to Next Facility: {distance_km} km

AVAILABLE RESOURCES AT CURRENT FACILITY:
{available_resources}

---

REFERRAL RECOMMENDATION:
**Referral Needed:** [Yes/No]
**Refer To:** [Facility name and level]
**Urgency:** [Emergency/Urgent/Routine]
**Mode of Transport:** [Emergency Ambulance/Referral Ambulance/Taxi/Public Transport]
**Estimated Time to Reach Facility:** [minutes]

**Clinical Handover Summary:**
[Brief summary for receiving facility]

**Pre-referral Treatment:**
[What should be done before transfer]

**Accompaniment Required:** [Yes/No - specify cadre]

**Confidence:** [0.0-1.0]
"""

SYMPTOM_ANALYSIS_PROMPT = """You are a Zambian clinical officer analyzing symptoms. Provide differential diagnoses based on the presenting symptoms, considering locally prevalent conditions.

PATIENT:
- Age: {age}
- Sex: {sex}
- Location: {district}, {province}
- Season: {season}

PRESENTING SYMPTOMS:
{symptoms}

HISTORY:
{history}

RISK FACTORS:
{risk_factors}

---

DIFFERENTIAL DIAGNOSIS:
1. **Most Likely:** [Diagnosis] - [Rationale considering local epidemiology]
2. **Possible:** [Diagnosis] - [Rationale]
3. **Consider:** [Diagnosis] - [Rationale]

**Epidemiological Context:**
- [Local prevalence note]

**Recommended Investigations:**
1. [Test] - [Rationale]
2. [Test] - [Rationale]

**Red Flags (refer if present):**
- [Red flag 1]
- [Red flag 2]

**Confidence:** [0.0-1.0]
"""

BEMBA_TRIAGE_PROMPT = """Niwe mushimbe wa pa cibinda mu Zambia. Pima mulwele uyu ukupitila mu SAPAC (South African Triage Scale).

IFYO MULWELE ALI:
- Myaka: {age}
- Nsambi: {sex}
- Ibungwe: {facility_level}

IFYO ALANDA: {chief_complaint}
IFYO TWAPIMA: {vitals}

TRIAGE LEVEL: [Emergency / Very Urgent / Urgent / Routine / Minor]
COLOR: [Red / Orange / Yellow / Green / Blue]
CONFIDENCE: [0.0-1.0]
"""

NYANJA_TRIAGE_PROMPT = """Muli namwino wa chipatala mu Zambia. Yesani wodwala uyu pogwiritsa ntchito SAPAC (South African Triage Scale).

ZAKHUDZA WODWALA:
- Zaka: {age}
- Amuna/Akazi: {sex}
- Chipatala: {facility_level}

MADANDAULO: {chief_complaint}
ZOYEZA: {vitals}

TRIAGE LEVEL: [Emergency / Very Urgent / Urgent / Routine / Minor]
COLOR: [Red / Orange / Yellow / Green / Blue]
CONFIDENCE: [0.0-1.0]
"""
