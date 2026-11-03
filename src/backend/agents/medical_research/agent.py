from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.backend.agents.agent_base import (
    AgentContext,
    AgentResponse,
    BaseAgent,
    FallbackStrategy,
    ModelConfig,
    ModelProvider,
    ToolDef,
)
from src.backend.agents.tools import DrugInteractionTool, GraphKnowledgeTool, MedicalLiteratureTool, WHOGuidelineTool

from .knowledge_sources import (
    CochraneLibraryClient,
    OpenDrugBankClient,
    PubMedClient,
    WHOGuidelinesAccessor,
    ZambiaMOHGuidelinesAccessor,
)

logger = logging.getLogger(__name__)


MEDICAL_RESEARCH_PROMPT = """You are a medical research assistant supporting healthcare workers in Zambia. Research the following clinical question using available evidence.

CLINICAL QUESTION:
{question}

PATIENT CONTEXT (if applicable):
{patient_context}

AVAILABLE EVIDENCE:
{pubmed_evidence}

GUIDELINE REFERENCES:
{guidelines}

---

EVIDENCE-BASED RESPONSE:

**Clinical Question:** {question}

**Summary of Evidence:**
[2-3 paragraph synthesis]

**Key Findings:**
1. [Finding with citation]
2. [Finding with citation]
3. [Finding with citation]

**Applicability to Zambian Context:**
[How this applies in Zambia]

**Recommendations:**
1. [Recommendation with evidence level]
2. [Recommendation with evidence level]

**References:**
[citations]

**Confidence:** [0.0-1.0]
"""

DRUG_INTERACTION_PROMPT = """You are a clinical pharmacist in Zambia. Check for drug-drug interactions and provide recommendations.

PATIENT:
- Age: {age}
- Sex: {sex}
- Conditions: {conditions}

MEDICATIONS TO CHECK:
{medications}

CURRENT MEDICATIONS:
{current_medications}

---

DRUG INTERACTION ANALYSIS:

**Potential Interactions:**
{interaction_results}

**Clinical Recommendations:**
1. [Recommendation]
2. [Recommendation]
3. [Recommendation]

**Monitoring Required:**
- [Monitoring parameter]

**Alternative Options:**
- [Alternative]

**Confidence:** [0.0-1.0]
"""

EVIDENCE_RECOMMENDATION_PROMPT = """You are an evidence-based medicine specialist. Grade the following recommendation using the GRADE system.

RECOMMENDATION: {recommendation}
CONDITION: {condition}
POPULATION: {population}
EVIDENCE SUMMARY: {evidence_summary}

---

GRADE ASSESSMENT:
**Quality of Evidence:** [High/Moderate/Low/Very Low]
**Strength of Recommendation:** [Strong For/Weak For/Weak Against/Strong Against]

**Rationale:**
- [Reason for quality rating]
- [Reason for strength]

**Applicability to Zambia:**
[Applicability note considering local resources]

**Confidence:** [0.0-1.0]
"""


class MedicalResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="medical_research",
                model_configs=[
                    ModelConfig(
                        provider=ModelProvider.OLLAMA,
                        model_name="qwen2.5:1.5b",
                        endpoint="http://host.docker.internal:11434",
                        temperature=0.05,
                        max_tokens=1024,
                        context_length=4096,
                        timeout=300,
                    ),
                    ModelConfig(
                        provider=ModelProvider.OLLAMA,
                        model_name="qwen2.5:1.5b",
                        endpoint="http://host.docker.internal:11434",
                        temperature=0.15,
                        max_tokens=1024,
                        context_length=4096,
                        timeout=300,
                    ),
                ],
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
        )
        self.pubmed = PubMedClient()
        self.who_guidelines = WHOGuidelinesAccessor()
        self.zambia_moh = ZambiaMOHGuidelinesAccessor()
        self.cochrane = CochraneLibraryClient()
        self.drugbank = OpenDrugBankClient()
        self.literature_tool = MedicalLiteratureTool()
        self.who_tool = WHOGuidelineTool()
        self.drug_interaction_tool = DrugInteractionTool()
        self.graph_knowledge_tool = GraphKnowledgeTool()
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("medical_research", MEDICAL_RESEARCH_PROMPT)
        self.register_prompt("drug_interaction", DRUG_INTERACTION_PROMPT)
        self.register_prompt("evidence_recommendation", EVIDENCE_RECOMMENDATION_PROMPT)

    def _register_tools(self) -> None:
        search_pubmed_tool = ToolDef(
            name="search_pubmed",
            description="Search PubMed for medical literature",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
            handler=self._handle_search_pubmed,
        )
        self.register_tool(search_pubmed_tool)

        search_who_tool = ToolDef(
            name="search_who_guidelines",
            description="Search WHO guidelines",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=self._handle_search_who,
        )
        self.register_tool(search_who_tool)

        check_interaction_tool = ToolDef(
            name="check_drug_interaction",
            description="Check for drug-drug interactions",
            parameters={
                "type": "object",
                "properties": {
                    "drug_a": {"type": "string"},
                    "drug_b": {"type": "string"},
                },
                "required": ["drug_a", "drug_b"],
            },
            handler=self._handle_check_interaction,
        )
        self.register_tool(check_interaction_tool)

        get_zambia_guideline_tool = ToolDef(
            name="get_zambia_moh_guideline",
            description="Get Zambia Ministry of Health treatment guideline",
            parameters={
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
            handler=self._handle_get_zambia_guideline,
        )
        self.register_tool(get_zambia_guideline_tool)

        graph_search_tool = ToolDef(
            name="graph_knowledge_search",
            description="Search the medical knowledge graph for diseases, drugs, symptoms and their relationships",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query for the knowledge graph"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 10},
                },
                "required": ["query"],
            },
            handler=self._handle_graph_search,
        )
        self.register_tool(graph_search_tool)

        graph_query_disease_tool = ToolDef(
            name="graph_query_disease",
            description="Get detailed information about a disease from the knowledge graph including associated drugs and symptoms",
            parameters={
                "type": "object",
                "properties": {
                    "disease_name": {"type": "string", "description": "Name of the disease to look up"},
                },
                "required": ["disease_name"],
            },
            handler=self._handle_graph_query_disease,
        )
        self.register_tool(graph_query_disease_tool)

        graph_query_drug_tool = ToolDef(
            name="graph_query_drug",
            description="Get detailed information about a drug from the knowledge graph including diseases it treats",
            parameters={
                "type": "object",
                "properties": {
                    "drug_name": {"type": "string", "description": "Name of the drug to look up"},
                },
                "required": ["drug_name"],
            },
            handler=self._handle_graph_query_drug,
        )
        self.register_tool(graph_query_drug_tool)

    async def _handle_graph_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return await self.graph_knowledge_tool.search(query, limit=limit)

    async def _handle_graph_query_disease(self, disease_name: str) -> Dict[str, Any]:
        return await self.graph_knowledge_tool.query_disease(disease_name)

    async def _handle_graph_query_drug(self, drug_name: str) -> Dict[str, Any]:
        return await self.graph_knowledge_tool.query_drug(drug_name)

    async def _handle_search_pubmed(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return await self.pubmed.search_and_fetch(query, max_results=max_results)

    async def _handle_search_who(self, query: str) -> List[Dict[str, Any]]:
        return await self.who_guidelines.get_treatment_guideline(query)

    async def _handle_check_interaction(self, drug_a: str, drug_b: str) -> Dict[str, Any]:
        return await self.drug_interaction_tool.check_interaction(drug_a, drug_b)

    async def _handle_get_zambia_guideline(self, topic: str) -> Dict[str, Any]:
        return await self.zambia_moh.get_guideline(topic)

    async def research_question(
        self,
        question: str,
        patient_context: str = "",
    ) -> AgentResponse:
        try:
            pubmed_results = await self.pubmed.search_and_fetch(question, max_results=3)
        except Exception as exc:
            logger.warning("PubMed search failed: %s", exc)
            pubmed_results = []
        pubmed_evidence = "\n\n".join(
            f"PMID {r['pmid']}: {r['title']}\nAbstract: {r['abstract'][:500]}"
            for r in pubmed_results
        ) or "No PubMed results found."

        try:
            who_evidence = await self.who_guidelines.get_treatment_guideline(question)
        except Exception as exc:
            logger.warning("WHO guidelines search failed: %s", exc)
            who_evidence = []
        try:
            zambia_evidence = await self.zambia_moh.get_guideline(question)
        except Exception as exc:
            logger.warning("Zambia MoH guidelines search failed: %s", exc)
            zambia_evidence = {}

        guidelines_text = "WHO Guidelines:\n" + "\n".join(
            f"- {g['title']}" for g in who_evidence
        ) if who_evidence else ""
        guidelines_text += "\n\nZambia MoH Guidelines:\n" + str(zambia_evidence)

        prompt = self.render_prompt(
            "medical_research",
            question=question,
            patient_context=patient_context or "Not specified",
            pubmed_evidence=pubmed_evidence or "No evidence found",
            guidelines=guidelines_text or "No guidelines found",
        )

        messages = [
            {"role": "system", "content": "You are a Zambian medical research assistant."},
            {"role": "user", "content": prompt},
        ]

        response = await self.generate(messages, use_fallbacks=True)
        if pubmed_results:
            response.citations = [r.get("citation", f"PMID: {r['pmid']}") for r in pubmed_results if r.get("pmid")]
        return response

    async def check_drug_interactions(
        self,
        medications: List[str],
        current_medications: List[str],
        age: int = 30,
        sex: str = "unknown",
        conditions: str = "",
    ) -> AgentResponse:
        all_meds = list(set(medications + current_medications))
        interaction_results = await self.drug_interaction_tool.batch_check(all_meds)

        interaction_text = "\n".join(
            f"- {r['drug_a']} + {r['drug_b']}: {r['severity']} - {r['description']}"
            for r in interaction_results
        ) or "No interactions found."

        drug_info = []
        for med in all_meds:
            info = await self.drugbank.get_drug_info(med)
            if "name" in info:
                drug_info.append(info)

        prompt = self.render_prompt(
            "drug_interaction",
            age=age,
            sex=sex,
            conditions=conditions or "Not specified",
            medications=", ".join(medications),
            current_medications=", ".join(current_medications),
            interaction_results=interaction_text,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian clinical pharmacist."},
            {"role": "user", "content": prompt},
        ]

        response = await self.generate(messages)
        response.structured_data = {
            "interactions": interaction_results,
            "drug_information": drug_info,
        }
        return response

    async def grade_recommendation(
        self,
        recommendation: str,
        condition: str,
        population: str = "General",
        evidence_summary: str = "",
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "evidence_recommendation",
            recommendation=recommendation,
            condition=condition,
            population=population,
            evidence_summary=evidence_summary or "No specific evidence provided.",
        )

        messages = [
            {"role": "system", "content": "You are a GRADE evidence-based medicine specialist."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "research")

        if action == "drug_interaction":
            return await self.check_drug_interactions(
                medications=metadata.get("medications", []),
                current_medications=metadata.get("current_medications", []),
                age=metadata.get("age", 30),
                sex=metadata.get("sex", ""),
                conditions=metadata.get("conditions", ""),
            )
        elif action == "grade_recommendation":
            return await self.grade_recommendation(
                recommendation=metadata.get("recommendation", ""),
                condition=metadata.get("condition", ""),
                population=metadata.get("population", ""),
                evidence_summary=metadata.get("evidence_summary", ""),
            )

        user_message = context.get_context_window(1)[-1]["content"] if context.messages else ""
        return await self.research_question(question=metadata.get("question", user_message))

    async def close(self) -> None:
        await self.pubmed.close()
        await self.literature_tool.close()
        await self.who_tool.close()
        await self.drug_interaction_tool.close()
        await self.graph_knowledge_tool.close()
        await super().close()
