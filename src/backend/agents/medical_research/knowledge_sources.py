from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PubMedClient:
    def __init__(self, email: str = "info@ubuntucare.zm", tool: str = "ubuntucare"):
        self._base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self._email = email
        self._tool = tool
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        params: Dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": sort,
            "retmode": "json",
            "email": self._email,
            "tool": self._tool,
        }
        if date_from:
            params["mindate"] = date_from
            params["datetype"] = "pdat"
        if date_to:
            params["maxdate"] = date_to

        resp = await client.get(f"{self._base_url}/esearch.fcgi", params=params)
        resp.raise_for_status()
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        return {"ids": id_list, "count": data.get("esearchresult", {}).get("count", "0"), "query": query}

    async def fetch_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        if not pmids:
            return []
        client = await self._get_client()
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self._email,
            "tool": self._tool,
        }
        resp = await client.get(f"{self._base_url}/efetch.fcgi", params=params)
        resp.raise_for_status()
        return self._parse_pubmed_xml(resp.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        articles = []
        try:
            root = ET.fromstring(xml_text)
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._parse_article(article_elem)
                if article:
                    articles.append(article)
        except ET.ParseError as e:
            logger.warning("Failed to parse PubMed XML: %s", e)
        return articles

    def _parse_article(self, article_elem: ET.Element) -> Optional[Dict[str, Any]]:
        try:
            pmid_elem = article_elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title"

            abstract_elems = article_elem.findall(".//AbstractText")
            abstract_parts = []
            for ae in abstract_elems:
                label = ae.get("Label", "")
                text = ae.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"

            authors = []
            for author_elem in article_elem.findall(".//Author"):
                last = author_elem.findtext("LastName", "")
                fore = author_elem.findtext("ForeName", "")
                if last:
                    authors.append(f"{fore} {last}".strip())

            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""

            year_elem = article_elem.find(".//PubDate/Year")
            year = year_elem.text if year_elem is not None else ""

            pub_types = []
            for pt in article_elem.findall(".//PublicationType"):
                if pt.text:
                    pub_types.append(pt.text)

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "publication_types": pub_types,
                "citation": self._format_citation(authors, title, journal, year, pmid),
            }
        except Exception as e:
            logger.warning("Error parsing article: %s", e)
            return None

    def _format_citation(self, authors: List[str], title: str, journal: str, year: str, pmid: str) -> str:
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."
        return f"{author_str} ({year}). {title}. {journal}. PMID: {pmid}."

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        search_result = await self.search(query, max_results=max_results)
        ids = search_result.get("ids", [])
        if not ids:
            return []
        return await self.fetch_details(ids)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class WHOGuidelinesAccessor:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def get_treatment_guideline(self, condition: str) -> List[Dict[str, Any]]:
        client = await self._get_client()
        query = f"WHO treatment guideline {condition}"
        params = {"q": query, "format": "json", "rows": 5}
        try:
            resp = await client.get("https://www.who.int/api/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "url": f"https://www.who.int{r.get('url', '')}" if r.get("url") else "",
                    "snippet": r.get("snippet", ""),
                    "source": "WHO",
                }
                for r in data.get("results", [])
            ]
        except Exception as exc:
            logger.warning("WHO search failed for %s: %s", condition, exc)
            return []

    async def get_essential_medicines(self, condition: Optional[str] = None) -> List[Dict[str, Any]]:
        eml_conditions = {
            "malaria": ["Artemether + Lumefantrine", "Artesunate", "Primaquine", "Chloroquine"],
            "hiv": ["Tenofovir", "Lamivudine", "Dolutegravir", "Efavirenz"],
            "tb": ["Rifampicin", "Isoniazid", "Pyrazinamide", "Ethambutol"],
            "hypertension": ["Amlodipine", "Enalapril", "Hydrochlorothiazide"],
            "diabetes": ["Metformin", "Glibenclamide", "Insulin"],
            "pneumonia": ["Amoxicillin", "Azithromycin", "Ceftriaxone"],
        }
        if condition and condition.lower() in eml_conditions:
            return [{"condition": condition, "medications": eml_conditions[condition.lower()], "source": "WHO EML"}]
        return [{"condition": c, "medications": m, "source": "WHO EML"} for c, m in eml_conditions.items()]


class ZambiaMOHGuidelinesAccessor:
    def __init__(self):
        self._guidelines = {
            "malaria": {
                "title": "Zambia National Malaria Elimination Strategic Plan",
                "source": "Zambia Ministry of Health",
                "first_line": "Artemether-Lumefantrine (AL)",
                "second_line": "Artesunate + Amodiaquine",
                "severe": "IV Artesunate",
                "prevention": "ITNs, IRS, SMC in children under 5",
                "testing": "RDT or microscopy before treatment",
            },
            "hiv": {
                "title": "Zambia Consolidated Guidelines for HIV Treatment",
                "source": "Zambia Ministry of Health",
                "first_line_art": "TLD (Tenofovir + Lamivudine + Dolutegravir)",
                "second_line_art": "AZT + 3TC + ATV/r or LPV/r",
                "prep": "Daily TDF/FTC",
                "testing": "HIV rapid test (Determine, Bioline, Unigold)",
            },
            "tb": {
                "title": "Zambia National TB Program Guidelines",
                "source": "Zambia Ministry of Health",
                "first_line": "RHZE (Rifampicin, Isoniazid, Pyrazinamide, Ethambutol) 2 months, RH 4 months",
                "mdr_tb": "BDQ+CFZ+LEVO+LZD+CS",
                "testing": "GeneXpert MTB/RIF as first line",
            },
            "maternal_health": {
                "title": "Zambia Reproductive Health Guidelines",
                "source": "Zambia Ministry of Health",
                "anc_visits": "8 contacts model",
                "skilled_birth_attendant": "Deliveries by skilled health worker",
                "emergency_obstetric": "CEmONC at district hospitals, BEmONC at clinics",
            },
            "immunization": {
                "title": "Zambia National Immunization Program",
                "source": "Zambia Ministry of Health",
                "vaccines": {
                    "BCG": "At birth",
                    "OPV": "At birth, 6, 10, 14 weeks",
                    "IPV": "14 weeks",
                    "PCV13": "6, 10, 14 weeks",
                    "Rotavirus": "6, 10 weeks",
                    "Measles-Rubella": "9 and 18 months",
                    "Td": "Pregnant women (2 doses)",
                    "HPV": "Girls 9-14 years (2 doses)",
                },
            },
        }

    async def get_guideline(self, topic: str) -> Dict[str, Any]:
        topic_lower = topic.lower()
        for key, value in self._guidelines.items():
            if key in topic_lower or topic_lower in key:
                return value
        return {"title": "Not found", "source": "Zambia MoH", "message": f"No specific guideline found for: {topic}"}

    async def list_available_topics(self) -> List[str]:
        return list(self._guidelines.keys())

    async def get_standard_treatment(self, condition: str) -> Dict[str, Any]:
        return await self.get_guideline(condition)


class CochraneLibraryClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def search_reviews(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params = {"q": query, "rows": max_results, "format": "json"}
        try:
            resp = await client.get(
                "https://www.cochranelibrary.com/api/search", params=params
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "authors": r.get("authors", ""),
                    "year": r.get("year", ""),
                    "source": "Cochrane Library",
                }
                for r in data.get("results", [])
            ]
        except Exception as exc:
            logger.warning("Cochrane search failed for %s: %s", query, exc)
            return []


class OpenDrugBankClient:
    def __init__(self):
        self._drug_info: Dict[str, Dict[str, Any]] = {
            "artemether": {
                "name": "Artemether",
                "class": "Antimalarial",
                "mechanism": "Artemisinin derivative; produces free radicals that damage parasite proteins",
                "indications": ["Uncomplicated malaria", "Severe malaria (with lumefantrine)"],
                "contraindications": ["Hypersensitivity to artemisinins"],
                "side_effects": ["Nausea", "Vomiting", "Headache", "Dizziness"],
                "pregnancy": "Category C - use if benefit outweighs risk",
            },
            "lumefantrine": {
                "name": "Lumefantrine",
                "class": "Antimalarial",
                "mechanism": "Inhibits haemozoin formation in parasite",
                "indications": ["Uncomplicated malaria (with artemether)"],
                "contraindications": ["Severe malaria alone", "Hypersensitivity"],
                "side_effects": ["Abdominal pain", "Anorexia", "Fatigue"],
                "pregnancy": "Category C",
            },
            "tenofovir": {
                "name": "Tenofovir Disoproxil Fumarate",
                "class": "NRTI",
                "mechanism": "Nucleotide reverse transcriptase inhibitor",
                "indications": ["HIV-1 infection", "Chronic hepatitis B"],
                "contraindications": ["CrCl <30 mL/min"],
                "side_effects": ["Renal toxicity", "Decreased bone density"],
                "pregnancy": "Category B",
            },
            "dolutegravir": {
                "name": "Dolutegravir",
                "class": "Integrase inhibitor",
                "mechanism": "Integrase strand transfer inhibitor",
                "indications": ["HIV-1 infection"],
                "contraindications": ["Known hypersensitivity"],
                "side_effects": ["Insomnia", "Headache", "Weight gain"],
                "pregnancy": "Category B - preferred in pregnancy per WHO",
            },
            "rifampicin": {
                "name": "Rifampicin",
                "class": "Rifamycin antibiotic",
                "mechanism": "Inhibits DNA-dependent RNA polymerase",
                "indications": ["TB", "Leprosy", "MRSA (combination)"],
                "contraindications": ["Jaundice", "Hypersensitivity"],
                "side_effects": ["Hepatotoxicity", "Orange discoloration of body fluids"],
                "pregnancy": "Category C",
            },
        }

    async def get_drug_info(self, drug_name: str) -> Dict[str, Any]:
        key = drug_name.lower().strip()
        if key in self._drug_info:
            return self._drug_info[key]
        return {"name": drug_name, "message": "Drug information not available in local database"}

    async def search_drugs(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for key, info in self._drug_info.items():
            if query_lower in key or query_lower in info["name"].lower():
                results.append(info)
        return results

    async def get_all_drugs(self) -> List[Dict[str, Any]]:
        return list(self._drug_info.values())
