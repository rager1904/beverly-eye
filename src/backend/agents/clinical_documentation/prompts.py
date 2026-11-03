SOAP_NOTE_EXTRACTION_PROMPT = """You are a clinical documentation specialist for the Zambian public health system. Extract a SOAP (Subjective, Objective, Assessment, Plan) note from the following clinical encounter transcript.

Use the Subjective-Objective-Assessment-Plan format standard in Zambian health facilities.

CONTEXT:
- Facility: {facility_name}
- Provider: {provider_name}
- Patient Age: {patient_age}
- Patient Sex: {patient_sex}
- Encounter Date: {encounter_date}
- Language: {language}

TRANSCRIPT:
{transcript}

---

**Subjective:**
Extract: chief complaint, history of present illness, past medical history, medications, allergies, social history, family history (all in patient's own words).

**Objective:**
Extract: vital signs, physical examination findings, lab results, imaging results.

**Assessment:**
Provide: differential diagnosis (with ICD-10 codes where possible), problem list, severity assessment.

**Plan:**
Provide: diagnostic tests ordered, medications prescribed (include dosage, route, frequency, duration), procedures, referrals, follow-up interval, patient education provided.

---

FORMAT YOUR RESPONSE AS:

SUBJECTIVE:
[detailed subjective findings]

OBJECTIVE:
[detailed objective findings]

ASSESSMENT:
1. [Primary diagnosis] (ICD-10: [code]) - [brief rationale]
2. [Secondary diagnosis] (ICD-10: [code]) - [brief rationale]

PLAN:
- [Test/Lab]: [details]
- [Medication]: [name] [dosage] [route] [frequency] x [duration]
- [Referral]: [to whom/where] - [reason]
- [Follow-up]: [timeframe]
- [Education]: [topics covered]

CONFIDENCE: [0.0-1.0]
"""

BEMBA_SOAP_PROMPT = """Uli kalemba makalata ya bubilo mu cibinda ca Zambia. Lemba SOAP note (Subjective, Objective, Assessment, Plan) ukufuma mu ikalata ya kulanda.

ICIBA:
- Ibungwe: {facility_name}
- Dokotala: {provider_name}
- Myaka ya mulwele: {patient_age}
- Nsambi ya mulwele: {patient_sex}
- Ubushiku: {encounter_date}

IKALATA:
{transcript}

LEMBA:
SUBJECTIVE (Ifyo aumfwa):
[fyo aumfwa, ifyo alanda, ububiko bwakwe]

OBJECTIVE (Ifyo mwaumona):
[ifyo mwaumona pa cebo, ukupima, ifyo mwaalandile mu lab]

ASSESSMENT (Ukupimisha):
[ubulwele, ICD-10 code, ifyo mwatontonkanya]

PLAN (Ifyo mukuba):
[umuti, ukupima, ukutuma ku bungwe, ukubwela]

CONFIDENCE: [0.0-1.0]
"""

NYANJA_SOAP_PROMPT = """Muli katemba za malembo ya chipatala mu Zambia. Lembani SOAP note (Subjective, Objective, Assessment, Plan) kuchokera mu zolemba za odwala.

MALO:
- Chipatala: {facility_name}
- Dokotala: {provider_name}
- Zaka za wodwala: {patient_age}
- Akazi/Amuna: {patient_sex}
- Tsiku: {encounter_date}

ZOLEMBA:
{transcript}

LEMBANI:
SUBJECTIVE (Zomwe wodwala akunena):
[zomwe akudandaula, mbili yake]

OBJECTIVE (Zomwe mwaona):
[zomwe mwaona pofufuza, ma lab]

ASSESSMENT (Kuzindikira matenda):
[matenda, ICD-10 code]

PLAN (Mapulani):
[mankhwala, kufufuza, kutumiza kwina, kubweranso]

CONFIDENCE: [0.0-1.0]
"""

ICD10_CODING_PROMPT = """You are a medical coding specialist for the Zambian health system. Given the following clinical assessment and diagnosis, suggest appropriate ICD-10 codes.

Consider:
1. The Zambian Ministry of Health coding guidelines
2. Common conditions in Zambia (malaria, HIV, TB, hypertension, diabetes, pneumonia, diarrhea, malnutrition, maternal conditions)
3. Use the most specific code available
4. Include both primary and secondary codes

CLINICAL ASSESSMENT:
{assessment}

PATIENT DEMOGRAPHICS:
- Age: {age}
- Sex: {sex}
- Province: {province}

SUGGESTED ICD-10 CODES:
1. [Code] - [Description] - [Confidence: High/Medium/Low]
2. [Code] - [Description] - [Confidence: High/Medium/Low]

---

EXAMPLES:
Input: "Patient presents with fever, chills, and headache. Blood smear positive for Plasmodium falciparum."
Output:
1. B50.9 - Plasmodium falciparum malaria, unspecified - High
2. R50.9 - Fever, unspecified - Medium

Input: "HIV-positive patient on ART with cough and weight loss. Sputum positive for AFB."
Output:
1. B20 - Human immunodeficiency virus [HIV] disease - High
2. A15.0 - Tuberculosis of lung - High

Input: "Child under 5 years with watery diarrhea and signs of dehydration."
Output:
1. A09 - Infectious gastroenteritis and colitis, unspecified - High
2. E86 - Volume depletion - High

Now code the following:"""

CLINICAL_SUMMARY_PROMPT = """You are a Zambian clinical officer preparing a patient summary for continuity of care. Summarize the following encounter information.

PATIENT: {patient_name} ({patient_age}y, {patient_sex})
NUPI: {nupi}
FACILITY: {facility}
DATE: {date}
PROVIDER: {provider}

ENCOUNTER DETAILS:
{encounter_details}

PREVIOUS HISTORY:
{previous_history}

---

CLINICAL SUMMARY:
**Chief Complaint:** [one line]

**History of Present Illness:** [2-3 sentences]

**Past Medical History:** [key conditions]

**Current Medications:** [list with dosages]

**Recent Investigations:** [relevant results]

**Assessment & Plan:** [summary]

**Follow-up:** [date and location]

**Referrals:** [if any]

**Health Education Provided:** [topics]

**Confidence:** [0.0-1.0]
"""

FOLLOWUP_PLAN_PROMPT = """You are a treatment planning specialist for the Zambian health system. Generate a comprehensive follow-up plan.

PATIENT: {patient_name}
DIAGNOSIS: {diagnosis}
TREATMENT STARTED: {treatment}
FACILITY LEVEL: {facility_level}
LOCATION: {district}, {province}

CONSIDER:
1. Standard Zambian treatment protocols (MoH guidelines)
2. Medication adherence support
3. Next appointment timing based on condition
4. Required laboratory monitoring
5. Referral criteria if not improving
6. Health education needs
7. Community health worker follow-up if available

---

FOLLOW-UP PLAN:

**Next Visit:** [date] at [facility]

**Medication Review:**
- Continue: [medications]
- Adjust: [changes if any]
- Duration: [total treatment duration]

**Monitoring Required:**
- [Test] at [frequency]
- [Vital sign] monitoring

**Referral Criteria:**
- Refer to [next level] if: [conditions]
- Emergency signs: [red flags]

**Health Education:**
- [Topic 1]
- [Topic 2]

**Community Follow-up:**
- CHW visit: [frequency]
- Phone follow-up: [yes/no]

**Confidence:** [0.0-1.0]
"""
