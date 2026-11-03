from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from src.backend.rag.knowledge_base.ingestion import ingest_document, ingest_from_url

logger = logging.getLogger("ubuntucare.rag.sources")


@dataclass
class KnowledgeSource:
    name: str
    base_url: str
    source_type: str
    language: str = "en"
    refresh_interval_hours: int = 168
    last_refreshed: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    def __init__(self, source: KnowledgeSource) -> None:
        self.source = source

    @abstractmethod
    async def fetch_updates(self) -> int:
        ...

    async def ingest(self, content: bytes | str, **kwargs: Any) -> int:
        return await ingest_document(
            content,
            source_type=self.source.source_type,
            language=self.source.language,
            metadata=self.source.metadata,
            **kwargs,
        )


class WHOConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="WHO Guidelines",
                base_url="https://www.who.int/publications",
                source_type="html",
                metadata={"organization": "WHO", "category": "guidelines"},
            )
        )

    async def fetch_updates(self) -> int:
        urls = [
            "https://www.who.int/publications/i/item/WHO-MHP-18.4",
            "https://www.who.int/publications/i/item/9789241549721",
            "https://www.who.int/publications/i/item/9789241550697",
        ]
        count = 0
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    await self.ingest(resp.content, source_url=url, title=f"WHO: {url.split('/')[-1]}")
                    count += 1
                except Exception as exc:
                    logger.warning("WHO fetch failed: %s", exc)
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count


class ZambiaMOHConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="Zambia Ministry of Health",
                base_url="https://www.moh.gov.zm",
                source_type="html",
                metadata={"organization": "Zambia MOH", "country": "Zambia"},
            )
        )

    async def fetch_updates(self) -> int:
        urls = [
            "https://www.moh.gov.zm/?page_id=100",
            "https://www.moh.gov.zm/?page_id=101",
            "https://www.moh.gov.zm/?page_id=102",
        ]
        count = 0
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    await self.ingest(resp.content, source_url=url, title=f"Zambia MOH: {url.split('=')[-1]}")
                    count += 1
                except Exception as exc:
                    logger.warning("Zambia MOH fetch failed: %s", exc)
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count


class CDCConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="CDC Guidelines",
                base_url="https://www.cdc.gov",
                source_type="html",
                metadata={"organization": "CDC", "category": "guidelines"},
            )
        )

    async def fetch_updates(self) -> int:
        urls = [
            "https://www.cdc.gov/travel/page/zambia",
            "https://www.cdc.gov/malaria/about/index.html",
            "https://www.cdc.gov/tb/about/index.html",
            "https://www.cdc.gov/hiv/basics/index.html",
        ]
        count = 0
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    await self.ingest(resp.content, source_url=url, title=f"CDC: {url.split('/')[-2]}")
                    count += 1
                except Exception as exc:
                    logger.warning("CDC fetch failed: %s", exc)
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count


class PubMedConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="PubMed/PMC",
                base_url="https://eutils.ncbi.nlm.nih.gov",
                source_type="html",
                metadata={"organization": "NCBI", "category": "literature"},
            )
        )

    async def fetch_updates(self) -> int:
        queries = [
            "malaria Zambia treatment",
            "tuberculosis Zambia guidelines",
            "HIV Zambia antiretroviral",
            "maternal health Zambia",
            "cholera Zambia outbreak",
        ]
        count = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries:
                try:
                    search_url = (
                        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                        f"?db=pubmed&term={query.replace(' ', '+')}&retmax=10&retmode=json"
                    )
                    resp = await client.get(search_url)
                    resp.raise_for_status()
                    data = resp.json()
                    pmids = data.get("esearchresult", {}).get("idlist", [])
                    for pmid in pmids[:3]:
                        summary_url = (
                            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                            f"?db=pubmed&id={pmid}&retmode=json"
                        )
                        sresp = await client.get(summary_url)
                        if sresp.status_code == 200:
                            sdata = sresp.json()
                            result = sdata.get("result", {}).get(pmid, {})
                            title = result.get("title", "")
                            source = result.get("source", "")
                            pubdate = result.get("pubdate", "")
                            await ingest_document(
                                json.dumps(result),
                                source_type="literature",
                                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                title=title,
                                author=source,
                                published_date=pubdate,
                                metadata={"pmid": pmid, "source": "PubMed", "query": query},
                            )
                            count += 1
                except Exception as exc:
                    logger.warning("PubMed query '%s' failed: %s", query, exc)
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count


class TreatmentProtocolConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="Treatment Protocols",
                base_url="https://www.who.int/teams/health-product-policy-and-standards",
                source_type="html",
                metadata={"category": "protocol"},
            )
        )

    async def fetch_updates(self) -> int:
        protocols = {
            "Integrated Management of Childhood Illness": "https://www.who.int/publications/i/item/9789241517836",
            "Pregnancy and Childbirth Guidelines": "https://www.who.int/publications/i/item/9789241549356",
            "TB Treatment Guidelines": "https://www.who.int/publications/i/item/9789240037023",
        }
        count = 0
        for title, url in protocols.items():
            try:
                count += await ingest_from_url(url, title=title, source_type="html", specialty="general")
            except Exception as exc:
                logger.warning("Protocol '%s' failed: %s", title, exc)
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count


class DrugFormularyConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="Zambia Essential Medicines List",
                base_url="https://www.moh.gov.zm",
                source_type="text",
                language="en",
                metadata={"category": "formulary", "country": "Zambia"},
            )
        )

    async def fetch_updates(self) -> int:
        eml_data = self._build_zambia_eml()
        count = 0
        for drug in eml_data:
            text = (
                f"Drug: {drug['name']}\n"
                f"Form: {drug['form']}\n"
                f"Strength: {drug['strength']}\n"
                f"Level: {drug['level']}\n"
                f"Indications: {drug['indications']}\n"
                f"Side Effects: {drug['side_effects']}\n"
                f"Contraindications: {drug['contraindications']}"
            )
            await self.ingest(
                text,
                source_type="formulary",
                title=f"Zambia EML: {drug['name']}",
                specialty="pharmacy",
                metadata=drug,
            )
            count += 1
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count

    def _build_zambia_eml(self) -> list[dict[str, str]]:
        return [
            {
                "name": "Artemether + Lumefantrine",
                "form": "Tablet",
                "strength": "20/120 mg",
                "level": "Health Post",
                "indications": "Uncomplicated malaria",
                "side_effects": "Headache, dizziness, nausea",
                "contraindications": "Severe malaria, first trimester pregnancy",
            },
            {
                "name": "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol",
                "form": "Tablet",
                "strength": "150/75/400/275 mg",
                "level": "District Hospital",
                "indications": "Tuberculosis (initial phase)",
                "side_effects": "Hepatotoxicity, rash, neuropathy",
                "contraindications": "Liver disease, alcohol use disorder",
            },
            {
                "name": "Zidovudine + Lamivudine + Nevirapine",
                "form": "Tablet",
                "strength": "300/150/200 mg",
                "level": "Clinic",
                "indications": "HIV/AIDS first-line ART",
                "side_effects": "Anemia, rash, hepatotoxicity",
                "contraindications": "Severe anemia, hepatic impairment",
            },
            {
                "name": "Oxytocin",
                "form": "Injection",
                "strength": "10 IU/ml",
                "level": "Health Post",
                "indications": "Postpartum hemorrhage prevention",
                "side_effects": "Nausea, vomiting, hypotension",
                "contraindications": "None in appropriate obstetric use",
            },
            {
                "name": "Oral Rehydration Salts",
                "form": "Powder for solution",
                "strength": "20.5 g/L",
                "level": "Community",
                "indications": "Diarrhea with dehydration",
                "side_effects": "None when used correctly",
                "contraindications": "Severe dehydration requiring IV fluids",
            },
            {
                "name": "Zinc Sulfate",
                "form": "Tablet (dispersible)",
                "strength": "20 mg",
                "level": "Community",
                "indications": "Diarrhea (adjunct to ORS)",
                "side_effects": "Nausea, metallic taste",
                "contraindications": "None significant",
            },
            {
                "name": "Amoxicillin",
                "form": "Capsule/Suspension",
                "strength": "250 mg, 500 mg",
                "level": "Clinic",
                "indications": "Respiratory tract infections, otitis media",
                "side_effects": "Rash, diarrhea, allergy",
                "contraindications": "Penicillin allergy",
            },
            {
                "name": "Artesunate",
                "form": "Injection",
                "strength": "60 mg",
                "level": "District Hospital",
                "indications": "Severe malaria",
                "side_effects": "Delayed hemolysis, neutropenia",
                "contraindications": "None (life-saving)",
            },
            {
                "name": "Magnesium Sulfate",
                "form": "Injection",
                "strength": "50% (5 g/10 ml)",
                "level": "District Hospital",
                "indications": "Severe pre-eclampsia/eclampsia",
                "side_effects": "Flushing, respiratory depression",
                "contraindications": "Myasthenia gravis, renal failure",
            },
            {
                "name": "Misoprostol",
                "form": "Tablet",
                "strength": "200 mcg",
                "level": "Health Post",
                "indications": "Postpartum hemorrhage, medical abortion",
                "side_effects": "Fever, shivering, diarrhea",
                "contraindications": "Previous uterine scar, allergy",
            },
        ]


class LocalClinicalGuidelinesConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(
            KnowledgeSource(
                name="Local Clinical Guidelines",
                base_url="https://www.moh.gov.zm/guidelines",
                source_type="text",
                metadata={"category": "guidelines", "country": "Zambia"},
            )
        )

    async def fetch_updates(self) -> int:
        guidelines = self._build_guidelines()
        count = 0
        for guideline in guidelines:
            await self.ingest(
                guideline["content"],
                source_type="guideline",
                title=guideline["title"],
                department=guideline.get("department"),
                specialty=guideline.get("specialty"),
                published_date=guideline.get("year"),
                metadata={"guideline_id": guideline.get("id")},
            )
            count += 1
        self.source.last_refreshed = datetime.now(timezone.utc)
        return count

    def _build_guidelines(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "ZM-MAL-2024",
                "title": "Zambia National Malaria Elimination Guidelines 2024",
                "department": "Public Health",
                "specialty": "Infectious Disease",
                "year": "2024",
                "content": (
                    "Zambia National Malaria Elimination Guidelines 2024\n\n"
                    "1. Diagnosis: All suspected malaria cases must be confirmed by RDT or microscopy before treatment.\n"
                    "2. Uncomplicated Malaria: Artemether-Lumefantrine (AL) is first-line treatment for uncomplicated malaria.\n"
                    "   - Weight-based dosing: 5-14 kg: 1 tab x 2/day x 3 days\n"
                    "   - 15-24 kg: 2 tabs x 2/day x 3 days\n"
                    "   - 25-34 kg: 3 tabs x 2/day x 3 days\n"
                    "   - >34 kg: 4 tabs x 2/day x 3 days\n"
                    "3. Severe Malaria: IV Artesunate 2.4 mg/kg at 0, 12, 24 hours, then daily.\n"
                    "4. Pregnant Women: AL is safe in all trimesters. First trimester: Quinine + Clindamycin.\n"
                    "5. Prevention: ITNs, IRS with residual insecticides, IPTp in pregnancy.\n"
                    "6. Seasonal Malaria Chemoprevention (SMC): For children 3-59 months in high transmission areas."
                ),
            },
            {
                "id": "ZM-TB-2024",
                "title": "Zambia National TB Control Guidelines 2024",
                "department": "Public Health",
                "specialty": "Infectious Disease",
                "year": "2024",
                "content": (
                    "Zambia National TB Control Guidelines 2024\n\n"
                    "1. Diagnosis: GeneXpert MTB/RIF is the initial diagnostic test for all presumptive TB cases.\n"
                    "2. Drug-Susceptible TB: 2HRZE/4HR regimen (2 months Rifampicin, Isoniazid, Pyrazinamide, Ethambutol followed by 4 months Rifampicin, Isoniazid).\n"
                    "3. MDR-TB: All-oral shorter regimen (6-9 months): Bedaquiline, Linezolid, Levofloxacin, Clofazimine, Cycloserine.\n"
                    "4. TB/HIV Co-infection: Start ART within 2 weeks of TB treatment initiation.\n"
                    "5. DOTS: Directly Observed Therapy is standard of care.\n"
                    "6. Contact Tracing: All household contacts should be evaluated for TB."
                ),
            },
            {
                "id": "ZM-HIV-2024",
                "title": "Zambia National HIV/AIDS Treatment Guidelines 2024",
                "department": "Public Health",
                "specialty": "HIV Medicine",
                "year": "2024",
                "content": (
                    "Zambia National HIV/AIDS Treatment Guidelines 2024\n\n"
                    "1. ART Initiation: All people living with HIV should start ART regardless of CD4 count.\n"
                    "2. First-Line ART: TLD (Tenofovir Disoproxil Fumarate 300mg + Lamivudine 300mg + Dolutegravir 50mg)\n"
                    "   - Once daily, fixed-dose combination.\n"
                    "3. Second-Line ART: AZT + 3TC + ATV/r or LPV/r\n"
                    "4. Third-Line ART: Based on genotypic resistance testing.\n"
                    "5. PMTCT: Option B+ - All pregnant women initiate lifelong ART.\n"
                    "6. PrEP: Offered to HIV-negative individuals at substantial risk.\n"
                    "7. PEP: 28-day course of TLD + Dolutegravir, initiated within 72 hours of exposure."
                ),
            },
            {
                "id": "ZM-MNCH-2024",
                "title": "Zambia Maternal, Newborn and Child Health Guidelines 2024",
                "department": "Maternal Health",
                "specialty": "Obstetrics",
                "year": "2024",
                "content": (
                    "Zambia Maternal, Newborn and Child Health Guidelines 2024\n\n"
                    "1. Antenatal Care: Focused ANC model - minimum 8 contacts.\n"
                    "2. Skilled Birth Attendance: All deliveries should be attended by skilled health personnel.\n"
                    "3. Postnatal Care: Mother and baby should receive care within 48 hours, 7-14 days, and 6 weeks.\n"
                    "4. Essential Newborn Care: Immediate drying, skin-to-skin contact, delayed cord clamping.\n"
                    "5. Immunization: BCG, OPV, DPT-HepB-Hib, PCV, Rotavirus, Measles-Rubella, IPV.\n"
                    "6. Nutrition: Exclusive breastfeeding for 6 months, complementary feeding thereafter.\n"
                    "7. Integrated Management of Childhood Illness (IMCI): Standardized approach for children under 5."
                ),
            },
            {
                "id": "ZM-NCD-2024",
                "title": "Zambia Non-Communicable Diseases Management Guidelines 2024",
                "department": "Internal Medicine",
                "specialty": "NCD",
                "year": "2024",
                "content": (
                    "Zambia Non-Communicable Diseases Management Guidelines 2024\n\n"
                    "1. Hypertension: First-line: Thiazide diuretic or CCB. Target BP <140/90.\n"
                    "2. Diabetes Mellitus: Metformin is first-line for type 2 diabetes.\n"
                    "3. Cervical Cancer Screening: VIA (Visual Inspection with Acetic Acid) every 3 years for women 25-49.\n"
                    "4. Mental Health: Integration of mental health services into primary care.\n"
                    "5. Palliative Care: Oral morphine is available at district hospitals for pain management."
                ),
            },
        ]


class KnowledgeSourceOrchestrator:
    def __init__(self) -> None:
        self.connectors: list[BaseConnector] = [
            WHOConnector(),
            ZambiaMOHConnector(),
            CDCConnector(),
            PubMedConnector(),
            TreatmentProtocolConnector(),
            DrugFormularyConnector(),
            LocalClinicalGuidelinesConnector(),
        ]

    async def refresh_all(self) -> dict[str, int]:
        results: dict[str, int] = {}
        for connector in self.connectors:
            try:
                count = await connector.fetch_updates()
                results[connector.source.name] = count
                logger.info("Refreshed '%s': %d documents", connector.source.name, count)
            except Exception as exc:
                logger.error("Failed to refresh '%s': %s", connector.source.name, exc)
                results[connector.source.name] = -1
        return results

    async def refresh_source(self, name: str) -> int:
        for connector in self.connectors:
            if connector.source.name.lower() == name.lower():
                return await connector.fetch_updates()
        raise ValueError(f"Unknown source: {name}")

    def get_source_status(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.source.name,
                "base_url": c.source.base_url,
                "type": c.source.source_type,
                "last_refreshed": c.source.last_refreshed.isoformat() if c.source.last_refreshed else None,
                "refresh_interval_hours": c.source.refresh_interval_hours,
            }
            for c in self.connectors
        ]


orchestrator = KnowledgeSourceOrchestrator()
