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
from src.backend.agents.tools import GraphKnowledgeTool

from .faq_data import FAQDatabase

logger = logging.getLogger(__name__)


FAQ_ANSWER_PROMPT = """You are a friendly and knowledgeable patient support agent for the Zambian health system. Answer the patient's question with accurate, empathetic responses.

PATIENT QUESTION: {question}
LANGUAGE: {language}
PATIENT LOCATION: {district}, {province}

RELEVANT FAQ INFORMATION:
{faq_context}

PREVIOUS CONTEXT (if any):
{previous_context}

---

**Answer:** [Your response in {language}]

**Key Points:**
1. [Point 1]
2. [Point 2]

**When to See a Doctor:** [if applicable]
**Related Information:** [optional related topics]

**Confidence:** [0.0-1.0]
"""

MEDICATION_REMINDER_PROMPT = """You are a medication adherence support agent for Zambia. Create a medication reminder plan.

PATIENT: {patient_name}
CONDITION: {condition}
MEDICATIONS: {medications}
LANGUAGE: {language}
PREFERRED CONTACT METHOD: {contact_method}
PHONE: {phone}

---

**Medication Schedule:**
[Time] - [Medication] - [Dosage] - [With/without food]

**Adherence Tips:**
1. [Tip 1]
2. [Tip 2]

**Expected Side Effects to Report:**
- [Side effect]

**Missed Dose Instructions:**
[What to do if a dose is missed]

**Next Refill Date:** [date]

**Confidence:** [0.0-1.0]
"""

HEALTH_EDUCATION_PROMPT = """You are a health educator for the Zambian health system. Provide health education on the following topic.

TOPIC: {topic}
AUDIENCE: {audience}
LANGUAGE: {language}
DURATION: {duration} minutes

---

**Health Education Content:**

**Key Messages:**
1. [Message 1]
2. [Message 2]
3. [Message 3]

**Key Facts:**
- [Fact 1]
- [Fact 2]

**Call to Action:**
[What the person should do]

**Where to Get Help:**
[Nearest facility / Helpline]

**Confidence:** [0.0-1.0]
"""

BEMBA_FAQ_PROMPT = """Nimwe bakwafwilisha abalwele mu Zambia. Aisuka ifyo balefwaisha.

IPUSHO: {question}

IFYO TWAKWATA:
{faq_context}

**AISUKA MU CIBEMBA:**
[answer in Bemba]

**Confidence:** [0.0-1.0]
"""

NYANJA_FAQ_PROMPT = """Muli wothandiza odwala mu chipatala cha Zambia. Yankhani funso la wodwalayo.

FUNSO: {question}

ZOMWE TILI NAZO:
{faq_context}

**YANKHO MU CHICHEWA:**
[answer in Chichewa]

**Confidence:** [0.0-1.0]
"""

TONGA_FAQ_PROMPT = """Muli muswaangani wakukwabilila bakala mu Zambia. Mwaike mubuzyo wakamwaa.

MBUZYO: {question}

**AASUKA MU TONGA:**
[answer in Tonga]

**Confidence:** [0.0-1.0]
"""

LOZI_FAQ_PROMPT = """Ki mushwa wa kuzamaisa bakuli kwa Zambia. Alaba lipuzo la mukuli.

LIPUZO: {question}

**ALABO KA LISINA LOZI:**
[answer in Lozi]

**Confidence:** [0.0-1.0]
"""


class PatientSupportAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="patient_support",
            model_configs=[
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_name="qwen2.5:1.5b",
                    endpoint="http://host.docker.internal:11434",
                    temperature=0.1,
                    max_tokens=1024,
                    context_length=4096,
                    timeout=120,
                ),
                ModelConfig(
                    provider=ModelProvider.OLLAMA,
                    model_name="qwen2.5:1.5b",
                    endpoint="http://host.docker.internal:11434",
                    temperature=0.3,
                    max_tokens=1024,
                    context_length=4096,
                    timeout=180,
                ),
            ],
            fallback_strategy=FallbackStrategy.SEQUENTIAL,
        )
        self.faq_db = FAQDatabase()
        self.graph_knowledge_tool = GraphKnowledgeTool()
        self._register_prompts()
        self._register_tools()

    def _register_prompts(self) -> None:
        self.register_prompt("faq_answer", FAQ_ANSWER_PROMPT)
        self.register_prompt("medication_reminder", MEDICATION_REMINDER_PROMPT)
        self.register_prompt("health_education", HEALTH_EDUCATION_PROMPT)
        self.register_prompt("faq_bemba", BEMBA_FAQ_PROMPT)
        self.register_prompt("faq_nyanja", NYANJA_FAQ_PROMPT)
        self.register_prompt("faq_tonga", TONGA_FAQ_PROMPT)
        self.register_prompt("faq_lozi", LOZI_FAQ_PROMPT)

    def _register_tools(self) -> None:
        search_faq_tool = ToolDef(
            name="search_faq_database",
            description="Search the Zambia health FAQ database",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["query"],
            },
            handler=self._handle_search_faq,
        )
        self.register_tool(search_faq_tool)

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

    async def _handle_search_faq(
        self, query: str, category: Optional[str] = None, language: str = "en"
    ) -> List[Dict[str, Any]]:
        results = self.faq_db.search(query, language=language, category=category)
        return [
            {
                "question": faq.question,
                "answer": self.faq_db.get_translation(faq, language),
                "category": faq.category,
                "requires_professional": faq.requires_professional,
            }
            for faq in results
        ]

    async def answer_question(
        self,
        question: str,
        language: str = "en",
        district: str = "Lusaka",
        province: str = "Lusaka",
        previous_context: str = "",
    ) -> AgentResponse:
        faq_results = self.faq_db.search(question, language=language)
        faq_context = "\n\n".join(
            f"Q: {faq.question}\nA: {self.faq_db.get_translation(faq, language)}"
            for faq in faq_results
        ) or "No exact FAQ match found."

        prompt_map = {
            "bem": "faq_bemba",
            "ny": "faq_nyanja",
            "to": "faq_tonga",
            "lo": "faq_lozi",
        }
        prompt_name = prompt_map.get(language, "faq_answer")

        prompt = self.render_prompt(
            prompt_name,
            question=question,
            language=language,
            district=district,
            province=province,
            faq_context=faq_context,
            previous_context=previous_context or "No previous context",
        )

        messages = [
            {"role": "system", "content": "You are a helpful Zambian healthcare support agent. Be compassionate and accurate."},
            {"role": "user", "content": prompt},
        ]

        response = await self.generate(messages)

        if faq_results:
            response.structured_data = {
                "faq_matched": True,
                "faq_count": len(faq_results),
                "faq_categories": list(set(f.category for f in faq_results)),
                "requires_professional": any(f.requires_professional for f in faq_results),
            }

        return response

    async def generate_reminder(
        self,
        patient_name: str,
        condition: str,
        medications: List[str],
        contact_method: str = "sms",
        phone: str = "",
        language: str = "en",
    ) -> AgentResponse:
        prompt = self.render_prompt(
            "medication_reminder",
            patient_name=patient_name,
            condition=condition,
            medications=", ".join(medications),
            language=language,
            contact_method=contact_method,
            phone=phone,
        )

        messages = [
            {"role": "system", "content": "You are a Zambian medication adherence support agent."},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def educate(
        self,
        topic: str,
        audience: str = "general public",
        language: str = "en",
        duration: int = 5,
    ) -> AgentResponse:
        faq_results = self.faq_db.search(topic, language=language)
        context = "\n".join(f"- {f.question}: {f.answer[:200]}" for f in faq_results[:3]) if faq_results else ""

        prompt = self.render_prompt(
            "health_education",
            topic=topic,
            audience=audience,
            language=language,
            duration=duration,
        )

        messages = [
            {"role": "system", "content": f"You are a Zambian health educator. Content:\n{context}"},
            {"role": "user", "content": prompt},
        ]

        return await self.generate(messages)

    async def run(self, context: AgentContext) -> AgentResponse:
        metadata = context.metadata
        action = metadata.get("action", "faq")

        if action == "medication_reminder":
            return await self.generate_reminder(
                patient_name=metadata.get("patient_name", ""),
                condition=metadata.get("condition", ""),
                medications=metadata.get("medications", []),
                contact_method=metadata.get("contact_method", "sms"),
                phone=metadata.get("phone", ""),
                language=context.language,
            )
        elif action == "educate":
            return await self.educate(
                topic=metadata.get("topic", ""),
                audience=metadata.get("audience", "general public"),
                language=context.language,
                duration=metadata.get("duration", 5),
            )

        user_message = context.get_context_window(1)[-1]["content"] if context.messages else ""
        return await self.answer_question(
            question=metadata.get("question", user_message),
            language=context.language,
            district=metadata.get("district", "Lusaka"),
            province=metadata.get("province", "Lusaka"),
            previous_context=metadata.get("previous_context", ""),
        )
