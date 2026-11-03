from dataclasses import dataclass, field


TREATS = "TREATS"
TREATS_SYMPTOM = "TREATS_SYMPTOM"
PREVENTS = "PREVENTS"
DIAGNOSES = "DIAGNOSES"
CONTRAINDICATES = "CONTRAINDICATES"
ADMINISTERED_FOR = "ADMINISTERED_FOR"
GUIDED_BY = "GUIDED_BY"
HAS_SYMPTOM = "HAS_SYMPTOM"
LOCATED_IN = "LOCATED_IN"
PRODUCED_BY = "PRODUCED_BY"


@dataclass
class DrugNode:
    name: str
    code: str = ""
    category: str = ""
    dosage: str = ""
    side_effects: str = ""


@dataclass
class DiseaseNode:
    name: str
    icd10_code: str = ""
    category: str = ""
    description: str = ""


@dataclass
class SymptomNode:
    name: str
    description: str = ""


@dataclass
class VaccineNode:
    name: str
    code: str = ""
    schedule: str = ""
    route: str = ""


@dataclass
class GuidelineNode:
    title: str
    source: str = ""
    language: str = ""
    version: str = ""


@dataclass
class ProtocolNode:
    name: str
    condition: str = ""
    regimen: str = ""
    duration: str = ""


@dataclass
class FacilityNode:
    name: str
    code: str = ""
    level: str = ""
    district: str = ""
    province: str = ""

NODE_LABELS = {
    "Drug": {
        "properties": ["name", "code", "category", "dosage", "side_effects"],
        "description": "Medication or pharmaceutical product",
    },
    "Disease": {
        "properties": ["name", "icd10_code", "category", "description"],
        "description": "Medical condition or disease",
    },
    "Symptom": {
        "properties": ["name", "description"],
        "description": "Clinical symptom or sign",
    },
    "Vaccine": {
        "properties": ["name", "code", "schedule", "route"],
        "description": "Vaccine or immunization",
    },
    "Guideline": {
        "properties": ["title", "source", "language", "version"],
        "description": "Clinical guideline or protocol document",
    },
    "Protocol": {
        "properties": ["name", "condition", "regimen", "duration"],
        "description": "Treatment protocol or regimen",
    },
    "Facility": {
        "properties": ["name", "code", "level", "district", "province"],
        "description": "Healthcare facility",
    },
}

RELATIONSHIP_TYPES = {
    TREATS: {"from": ["Drug", "Protocol"], "to": ["Disease"], "description": "Treats a condition"},
    TREATS_SYMPTOM: {"from": ["Drug"], "to": ["Symptom"], "description": "Relieves a symptom"},
    PREVENTS: {"from": ["Vaccine", "Drug"], "to": ["Disease"], "description": "Prevents a disease"},
    DIAGNOSES: {"from": ["Symptom", "Protocol"], "to": ["Disease"], "description": "Indicates a disease"},
    CONTRAINDICATES: {"from": ["Drug"], "to": ["Disease", "Drug"], "description": "Should not be used with"},
    ADMINISTERED_FOR: {"from": ["Vaccine"], "to": ["Disease"], "description": "Vaccine targets this disease"},
    GUIDED_BY: {"from": ["Protocol", "Drug"], "to": ["Guideline"], "description": "Based on this guideline"},
    HAS_SYMPTOM: {"from": ["Disease"], "to": ["Symptom"], "description": "Disease presents with symptom"},
    LOCATED_IN: {"from": ["Facility"], "to": ["Facility"], "description": "Located within (hierarchy)"},
}


def get_constraint_queries() -> list[str]:
    return [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Drug) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Disease) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Symptom) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Vaccine) REQUIRE n.code IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Guideline) REQUIRE n.title IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Facility) REQUIRE n.code IS UNIQUE",
    ]
