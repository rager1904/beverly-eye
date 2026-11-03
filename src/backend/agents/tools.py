from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class EMRTool:
    def __init__(self, fhir_base_url: str = "http://emr:8001/fhir"):
        self.base_url = fhir_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/Patient/{patient_id}")
        resp.raise_for_status()
        return resp.json()

    async def search_patient(self, **kwargs: Any) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params = {k: v for k, v in kwargs.items() if v is not None}
        resp = await client.get(f"{self.base_url}/Patient", params=params)
        resp.raise_for_status()
        bundle = resp.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    async def create_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(f"{self.base_url}/Patient", json=data)
        resp.raise_for_status()
        return resp.json()

    async def update_patient(self, patient_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.put(f"{self.base_url}/Patient/{patient_id}", json=data)
        resp.raise_for_status()
        return resp.json()

    async def get_encounter(self, encounter_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/Encounter/{encounter_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_encounter(self, data: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(f"{self.base_url}/Encounter", json=data)
        resp.raise_for_status()
        return resp.json()

    async def get_observations(
        self,
        patient_id: str,
        code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, str] = {"patient": patient_id}
        if code:
            params["code"] = code
        if date_from:
            params["date"] = f"ge{date_from}"
        if date_to:
            params["date"] = f"{params.get('date', '')}&date=le{date_to}"
        resp = await client.get(f"{self.base_url}/Observation", params=params)
        resp.raise_for_status()
        bundle = resp.json()
        return [e["resource"] for e in bundle.get("entry", [])]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class AppointmentTool:
    def __init__(self, api_base_url: str = "http://emr:8001/api/v1"):
        self.base_url = api_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30,
                headers={
                    "X-Hospital-Id": "00000000-0000-0000-0000-000000000000",
                    "X-User-Id": "system",
                },
            )
        return self._client

    async def schedule(
        self,
        patient_id: str,
        provider_id: str,
        start_time: str,
        end_time: str,
        appointment_type: str = "outpatient",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "patient_id": patient_id,
            "provider_id": provider_id,
            "start_time": start_time,
            "end_time": end_time,
            "type": appointment_type,
            "reason": reason,
        }
        resp = await client.post(f"{self.base_url}/appointments", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def reschedule(
        self,
        appointment_id: str,
        new_start_time: str,
        new_end_time: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "start_time": new_start_time,
            "end_time": new_end_time,
            "reason": reason,
        }
        resp = await client.patch(
            f"{self.base_url}/appointments/{appointment_id}/reschedule",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def cancel(self, appointment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/appointments/{appointment_id}/cancel",
            json={"reason": reason},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_slots(
        self,
        provider_id: str,
        date: str,
        appointment_type: str = "outpatient",
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params = {"provider_id": provider_id, "date": date, "type": appointment_type}
        resp = await client.get(f"{self.base_url}/appointments/slots", params=params)
        resp.raise_for_status()
        return resp.json()

    async def list_upcoming(
        self,
        patient_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, Any] = {"days": days}
        if patient_id:
            params["patient_id"] = patient_id
        if provider_id:
            params["provider_id"] = provider_id
        resp = await client.get(f"{self.base_url}/appointments", params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class LabOrderingTool:
    def __init__(self, api_base_url: str = "http://api-gateway:8000/api/v1"):
        self.base_url = api_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def order_test(
        self,
        patient_id: str,
        test_code: str,
        test_name: str,
        ordered_by: str,
        encounter_id: Optional[str] = None,
        priority: str = "routine",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "patient_id": patient_id,
            "test_code": test_code,
            "test_name": test_name,
            "ordered_by": ordered_by,
            "encounter_id": encounter_id,
            "priority": priority,
            "notes": notes,
        }
        resp = await client.post(f"{self.base_url}/lab/orders", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_results(
        self,
        order_id: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, str] = {}
        if order_id:
            params["order_id"] = order_id
        if patient_id:
            params["patient_id"] = patient_id
        resp = await client.get(f"{self.base_url}/lab/results", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_test_catalog(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/lab/catalog")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class PrescriptionTool:
    def __init__(self, api_base_url: str = "http://api-gateway:8000/api/v1"):
        self.base_url = api_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def prescribe(
        self,
        patient_id: str,
        medication_code: str,
        medication_name: str,
        dosage: str,
        route: str,
        frequency: str,
        duration_days: int,
        prescribed_by: str,
        encounter_id: Optional[str] = None,
        quantity: Optional[int] = None,
        refills: int = 0,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "patient_id": patient_id,
            "medication_code": medication_code,
            "medication_name": medication_name,
            "dosage": dosage,
            "route": route,
            "frequency": frequency,
            "duration_days": duration_days,
            "prescribed_by": prescribed_by,
            "encounter_id": encounter_id,
            "quantity": quantity,
            "refills": refills,
            "notes": notes,
        }
        resp = await client.post(f"{self.base_url}/pharmacy/prescriptions", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_prescriptions(
        self,
        patient_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, Any] = {"active_only": active_only}
        if patient_id:
            params["patient_id"] = patient_id
        resp = await client.get(f"{self.base_url}/pharmacy/prescriptions", params=params)
        resp.raise_for_status()
        return resp.json()

    async def check_interactions(
        self, medication_codes: List[str]
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/pharmacy/interactions",
            json={"medications": medication_codes},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class ReferralTool:
    def __init__(self, api_base_url: str = "http://api-gateway:8000/api/v1"):
        self.base_url = api_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def create_referral(
        self,
        patient_id: str,
        from_facility: str,
        to_facility: str,
        reason: str,
        referral_type: str,
        urgency: str = "routine",
        clinical_summary: Optional[str] = None,
        referred_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "patient_id": patient_id,
            "from_facility": from_facility,
            "to_facility": to_facility,
            "reason": reason,
            "type": referral_type,
            "urgency": urgency,
            "clinical_summary": clinical_summary,
            "referred_by": referred_by,
        }
        resp = await client.post(f"{self.base_url}/referrals", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_referral(self, referral_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/referrals/{referral_id}")
        resp.raise_for_status()
        return resp.json()

    async def list_facilities(
        self,
        level: Optional[str] = None,
        province: Optional[str] = None,
        district: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, str] = {}
        if level:
            params["level"] = level
        if province:
            params["province"] = province
        if district:
            params["district"] = district
        resp = await client.get(f"{self.base_url}/facilities", params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class RAGSearchTool:
    def __init__(self, vector_store_url: str = "http://qdrant:6333"):
        self.base_url = vector_store_url

    async def search(
        self,
        query: str,
        collection: str = "medical_knowledge",
        top_k: int = 5,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "query": query,
                "collection": collection,
                "top_k": top_k,
                "threshold": threshold,
                "filters": filters or {},
            }
            resp = await client.post(
                f"{self.base_url}/collections/{collection}/points/search",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def hybrid_search(
        self,
        query: str,
        collection: str = "medical_knowledge",
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "query": query,
                "collection": collection,
                "top_k": top_k,
                "alpha": alpha,
            }
            resp = await client.post(
                f"{self.base_url}/collections/{collection}/points/search/hybrid",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


class GraphKnowledgeTool:
    def __init__(self, rag_base_url: str = "http://rag:8005"):
        self.base_url = rag_base_url

    async def close(self) -> None:
        pass

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/rag/graph/search",
                json={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("results", [])

    async def query_disease(self, disease_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/rag/graph/query",
                json={"disease_name": disease_name},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def query_drug(self, drug_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/rag/graph/query",
                json={"drug_name": drug_name},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def query_symptom(self, symptom: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/rag/graph/query",
                json={"symptom": symptom},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def find_path(
        self, from_label: str, from_value: str, to_label: str, to_value: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {}
            if from_label == "Drug":
                payload["drug_name"] = from_value
            if to_label == "Disease":
                payload["disease_name"] = to_value
            if from_label == "Symptom":
                payload["symptom"] = from_value
            resp = await client.post(
                f"{self.base_url}/api/v1/rag/graph/query",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})


class MedicalLiteratureTool:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self._client

    async def search_pubmed(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "sort": sort,
            "retmode": "json",
        }
        resp = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=params,
        )
        resp.raise_for_status()
        search_data = resp.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
        }
        fetch_resp = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params=fetch_params,
        )
        fetch_resp.raise_for_status()
        return [{"pmid": pmid, "query": query} for pmid in id_list]

    async def fetch_article(self, pmid: str) -> Dict[str, Any]:
        client = await self._get_client()
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
        }
        resp = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params=params,
        )
        resp.raise_for_status()
        return {"pmid": pmid, "xml": resp.text[:5000]}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class WHOGuidelineTool:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def search_guidelines(
        self, query: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params = {
            "q": query,
            "format": "json",
            "rows": max_results,
        }
        resp = await client.get(
            "https://www.who.int/api/search", params=params
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    async def get_guideline(self, guideline_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(
            f"https://www.who.int/api/publications/{guideline_id}"
        )
        resp.raise_for_status()
        return resp.json()

    async def get_zambia_guidelines(
        self, topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, Any] = {
            "q": topic or "Zambia treatment guidelines",
            "format": "json",
            "rows": 10,
        }
        resp = await client.get(
            "https://www.who.int/api/search", params=params
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


class DrugInteractionTool:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._drugbank_base = "https://go.drugbank.com"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def check_interaction(
        self, drug_a: str, drug_b: str
    ) -> Dict[str, Any]:
        known_interactions: Dict[str, Dict[str, str]] = {
            ("artemether", "lumefantrine"): {
                "severity": "minor",
                "description": "Synergistic antimalarial effect; no adverse interaction.",
            },
            ("rifampicin", "artemether"): {
                "severity": "moderate",
                "description": "Rifampicin may reduce artemether levels. Monitor for reduced efficacy.",
            },
            ("zidovudine", "rifampicin"): {
                "severity": "moderate",
                "description": "Reduced zidovudine levels. Consider dose adjustment.",
            },
            ("tenofovir", "efavirenz"): {
                "severity": "minor",
                "description": "No significant clinical interaction.",
            },
        }
        key = (drug_a.lower().strip(), drug_b.lower().strip())
        reverse_key = (drug_b.lower().strip(), drug_a.lower().strip())
        interaction = known_interactions.get(key) or known_interactions.get(reverse_key)
        if interaction:
            return {
                "drug_a": drug_a,
                "drug_b": drug_b,
                "severity": interaction["severity"],
                "description": interaction["description"],
                "source": "ubuntucare-knowledge-base",
            }
        return {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "severity": "unknown",
            "description": "No known interaction in local database.",
            "source": "ubuntucare-knowledge-base",
        }

    async def batch_check(
        self, medications: List[str]
    ) -> List[Dict[str, Any]]:
        results = []
        for i in range(len(medications)):
            for j in range(i + 1, len(medications)):
                result = await self.check_interaction(
                    medications[i], medications[j]
                )
                results.append(result)
        return results

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
