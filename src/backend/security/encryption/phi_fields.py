from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import list


class DataClassification(str, Enum):
    restricted = "restricted"
    confidential = "confidential"
    internal = "internal"
    public = "public"


class PHICategory(str, Enum):
    demographic = "demographic"
    identifier = "identifier"
    clinical = "clinical"
    financial = "financial"
    biometric = "biometric"
    contact = "contact"


@dataclass
class PHIField:
    entity: str
    field_name: str
    category: PHICategory
    classification: DataClassification
    required_encryption: bool = True
    required_masking: bool = True
    description: str = ""
    zambia_specific: bool = False
    regulatory_reference: str = ""


PHI_FIELDS: list[PHIField] = [
    # Zambia-specific identifiers
    PHIField("patient", "nrc_number", PHICategory.identifier, DataClassification.restricted,
             description="National Registration Card number (Zambia)", zambia_specific=True,
             regulatory_reference="Zambia NRC Act"),
    PHIField("patient", "nhima_number", PHICategory.identifier, DataClassification.restricted,
             description="NHIMA membership number", zambia_specific=True,
             regulatory_reference="NHIMA Act No. 20 of 2023"),
    PHIField("patient", "passport_number", PHICategory.identifier, DataClassification.restricted,
             description="Passport number", zambia_specific=True),
    PHIField("patient", "smartcare_id", PHICategory.identifier, DataClassification.confidential,
             description="SmartCare unique patient ID", zambia_specific=True),
    PHIField("patient", "nupi", PHICategory.identifier, DataClassification.restricted,
             description="National Unique Patient Identifier (Zambia)", zambia_specific=True,
             regulatory_reference="Zambia MoH NUPI Framework"),

    # Demographics
    PHIField("patient", "first_name", PHICategory.demographic, DataClassification.confidential),
    PHIField("patient", "last_name", PHICategory.demographic, DataClassification.confidential),
    PHIField("patient", "middle_name", PHICategory.demographic, DataClassification.confidential),
    PHIField("patient", "date_of_birth", PHICategory.demographic, DataClassification.confidential),
    PHIField("patient", "gender", PHICategory.demographic, DataClassification.internal),
    PHIField("patient", "marital_status", PHICategory.demographic, DataClassification.internal),
    PHIField("patient", "occupation", PHICategory.demographic, DataClassification.internal),

    # Contact
    PHIField("patient", "phone", PHICategory.contact, DataClassification.restricted),
    PHIField("patient", "email", PHICategory.contact, DataClassification.confidential),
    PHIField("patient", "address_line", PHICategory.contact, DataClassification.restricted),
    PHIField("patient", "city", PHICategory.contact, DataClassification.confidential),
    PHIField("patient", "district", PHICategory.contact, DataClassification.confidential),

    # Emergency contact
    PHIField("patient", "emergency_contact_name", PHICategory.contact, DataClassification.restricted),
    PHIField("patient", "emergency_contact_phone", PHICategory.contact, DataClassification.restricted),
    PHIField("patient", "emergency_contact_relation", PHICategory.contact, DataClassification.internal),

    # Insurance / financial
    PHIField("patient", "insurance_provider", PHICategory.financial, DataClassification.confidential),
    PHIField("patient", "insurance_number", PHICategory.financial, DataClassification.restricted),
    PHIField("patient", "insurance_expiry", PHICategory.financial, DataClassification.confidential),

    # Clinical
    PHIField("encounter", "chief_complaint", PHICategory.clinical, DataClassification.confidential),
    PHIField("encounter", "triage_notes", PHICategory.clinical, DataClassification.confidential),

    # Diagnoses
    PHIField("diagnosis", "icd10_code", PHICategory.clinical, DataClassification.confidential),
    PHIField("diagnosis", "icd10_description", PHICategory.clinical, DataClassification.confidential),
    PHIField("diagnosis", "notes", PHICategory.clinical, DataClassification.confidential),

    # Clinical notes
    PHIField("clinical_note", "subjective", PHICategory.clinical, DataClassification.restricted),
    PHIField("clinical_note", "objective", PHICategory.clinical, DataClassification.restricted),
    PHIField("clinical_note", "assessment", PHICategory.clinical, DataClassification.restricted),
    PHIField("clinical_note", "plan", PHICategory.clinical, DataClassification.restricted),

    # Lab results
    PHIField("result", "result_value", PHICategory.clinical, DataClassification.confidential),
    PHIField("result", "result_description", PHICategory.clinical, DataClassification.confidential),

    # Medications
    PHIField("medication", "medication_name", PHICategory.clinical, DataClassification.confidential),
    PHIField("medication", "dosage", PHICategory.clinical, DataClassification.confidential),
    PHIField("medication", "pharmacy_notes", PHICategory.clinical, DataClassification.confidential),

    # HIV / sensitive conditions (Zambia high-burden)
    PHIField("diagnosis", "is_hiv_related", PHICategory.clinical, DataClassification.restricted,
             description="HIV status indicator", zambia_specific=True,
             regulatory_reference="Zambia HIV/AIDS Act"),
    PHIField("diagnosis", "is_sti_related", PHICategory.clinical, DataClassification.restricted,
             description="STI diagnosis indicator"),

    # Biometric
    PHIField("patient", "photo_url", PHICategory.biometric, DataClassification.restricted),

    # Disease surveillance
    PHIField("disease_case", "patient_name", PHICategory.demographic, DataClassification.restricted),
    PHIField("disease_case", "contact_details", PHICategory.contact, DataClassification.restricted),
    PHIField("disease_case", "location_details", PHICategory.demographic, DataClassification.confidential),

    # Community health
    PHIField("household_visit", "findings", PHICategory.clinical, DataClassification.confidential),
    PHIField("household_visit", "interventions", PHICategory.clinical, DataClassification.confidential),
    PHIField("maternal_health_visit", "findings", PHICategory.clinical, DataClassification.restricted),
]

ENTITY_PHI_FIELDS: dict[str, list[PHIField]] = {}
for field in PHI_FIELDS:
    ENTITY_PHI_FIELDS.setdefault(field.entity, []).append(field)

ZAMBIA_SPECIFIC_FIELDS = [f for f in PHI_FIELDS if f.zambia_specific]

RESTRICTED_FIELDS = [f for f in PHI_FIELDS if f.classification == DataClassification.restricted]
CONFIDENTIAL_FIELDS = [f for f in PHI_FIELDS if f.classification == DataClassification.confidential]


def get_phi_fields(entity: str) -> list[PHIField]:
    return ENTITY_PHI_FIELDS.get(entity, [])


def requires_encryption(entity: str, field_name: str) -> bool:
    for f in PHI_FIELDS:
        if f.entity == entity and f.field_name == field_name:
            return f.required_encryption
    return False


def get_classification(entity: str, field_name: str) -> DataClassification:
    for f in PHI_FIELDS:
        if f.entity == entity and f.field_name == field_name:
            return f.classification
    return DataClassification.internal
