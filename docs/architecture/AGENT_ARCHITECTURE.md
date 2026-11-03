# UbuntuCare Agent Architecture

## Multi-Agent Orchestration

UbuntuCare uses a **hierarchical multi-agent system** built on LangGraph with a custom orchestrator that manages task planning, agent routing, memory, and failure recovery.

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Task        │  │ Agent       │  │ Memory              │ │
│  │ Planner     │──│ Registry    │──│ Manager             │ │
│  │             │  │             │  │                     │ │
│  │ Intent      │  │ Capability  │  │ Conversation hist   │ │
│  │ Detection   │  │ Matching    │  │ Cross-agent recall  │ │
│  │ Decompose   │  │ Load-Bal    │  │ Confidence scoring  │ │
│  │ Dependen-   │  │ Fallback    │  │ Memory pruning     │ │
│  │ cies        │  │ Routing     │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘ │
│         │                │                                  │
│         └────────────────┴──────────────────────────────────┘
│                              │
│  ┌───────────────────────────▼────────────────────────────┐
│  │              Agent Execution Loop                       │
│  │                                                         │
│  │  Input → Retrieve → Reason → Act → Observe → Respond   │
│  │                     │                                   │
│  │                Fallback Chain                           │
│  │          ┌──────────┼──────────┐                       │
│  │          ▼          ▼          ▼                       │
│  │     DeepSeek    Qwen3     Llama-4                      │
│  │     -R1-32B     -32B      -17B                         │
│  └─────────────────────────────────────────────────────────┘
```

---

## Agent Hierarchy

```
                    ┌─────────────────────┐
                    │    Orchestrator      │
                    │  (LangGraph Graph)   │
                    └─────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                  │
     ┌─────▼─────┐    ┌─────▼─────┐    ┌──────▼──────┐
     │ Clinical  │    │  Triage   │    │  Medical    │
     │ Doc Agent │    │  Agent    │    │  Research   │
     │           │    │           │    │  Agent      │
     │ DeepSeek  │    │ DeepSeek  │    │ Qwen3 + RAG │
     │ + Meditron│    │ + scoring │    │ + PubMed    │
     └───────────┘    └───────────┘    └──────────────┘
           │                 │                  │
           └─────────────────┼──────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                   │
     ┌─────▼─────┐     ┌─────▼─────┐     ┌──────▼──────┐
     │Appointment│     │ Patient   │     │  Public     │
     │ Agent     │     │ Support   │     │  Health     │
     │           │     │ Agent     │     │  Agent      │
     │ Qwen3     │     │ Qwen3+RAG │     │ DeepSeek    │
     │ + SMS     │     │ + FAQs    │     │ + DHIS2     │
     └───────────┘     └───────────┘     └─────────────┘
           │                                          │
           └──────────────────┬───────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    Admin Agent    │
                    │    Qwen3 + DB     │
                    └───────────────────┘
```

### Agent Roles

| Agent | Primary Model | Failover | Max Latency | Criticality |
|-------|--------------|----------|-------------|-------------|
| Clinical Documentation | DeepSeek-R1-32B | Meditron-7B | 30s | High |
| Triage | DeepSeek-R1-32B | Qwen3-32B | 10s | Critical |
| Medical Research | Qwen3-32B | DeepSeek-R1-32B | 60s | Medium |
| Appointment | Qwen3-32B | Llama-4-17B | 5s | Medium |
| Patient Support | Qwen3-32B | Mistral-7B | 10s | Low |
| Public Health | DeepSeek-R1-32B | Qwen3-32B | 120s | High |
| Admin | Qwen3-32B | Llama-4-17B | 30s | Low |

---

## Agent Communication Protocol

Agents communicate through a **structured message protocol** over Redis PubSub with guaranteed delivery.

### Message Format

```json
{
  "message_id": "msg_abc123",
  "agent_id": "clinical_doc_agent",
  "target_agent": "triage_agent",
  "message_type": "request | response | event | error",
  "conversation_id": "conv_xyz",
  "timestamp": "2026-06-17T10:30:00Z",
  "payload": {
    "action": "get_patient_risk_score",
    "parameters": {
      "patient_id": "P-12345",
      "symptoms": ["fever", "headache", "rash"]
    }
  },
  "metadata": {
    "priority": "high",
    "ttl_seconds": 30,
    "requires_audit": true
  }
}
```

### Communication Patterns

| Pattern | Mechanism | Use Case |
|---------|-----------|----------|
| **Request-Response** | HTTP/REST (sync) | Agent → EMR service query |
| **Async Event** | Redis PubSub (fire-and-forget) | Clinical note → Disease surveillance |
| **Agent-to-Agent** | Redis PubSub (targeted) | Triage → Appointment (urgent booking) |
| **Streaming** | WebSocket | ASR transcription → Clinical Doc Agent |
| **Batch** | Celery task queue | Research Agent → PubMed bulk search |

---

## Tool Calling Framework

Every agent can register and call tools. The framework handles schema generation, execution, and result processing.

### Tool Registry

```python
# Defined in src/backend/agents/tools.py
tool_registry = {
    "get_patient": EMRTool.get_patient,
    "search_patient": EMRTool.search_patient,
    "create_encounter": EMRTool.create_encounter,
    "schedule_appointment": AppointmentTool.schedule,
    "order_lab_test": LabOrderingTool.order_test,
    "prescribe_medication": PrescriptionTool.prescribe,
    "check_drug_interaction": DrugInteractionTool.check_interaction,
    "search_medical_literature": MedicalLiteratureTool.search_pubmed,
    "get_who_guidelines": WHOGuidelineTool.search_guidelines,
    "search_rag": RAGSearchTool.search,
    "get_facilities": ReferralTool.list_facilities,
    "create_referral": ReferralTool.create_referral,
}
```

### Tool Schema Generation

Each tool auto-generates an OpenAI-compatible function-calling schema:

```json
{
  "type": "function",
  "function": {
    "name": "prescribe_medication",
    "description": "Create a new prescription order",
    "parameters": {
      "type": "object",
      "properties": {
        "patient_id": { "type": "string", "description": "Patient UUID" },
        "medication_name": { "type": "string" },
        "dosage": { "type": "string" },
        "frequency": { "type": "string" },
        "duration_days": { "type": "integer" }
      },
      "required": ["patient_id", "medication_name", "dosage", "frequency"]
    }
  }
}
```

### Tool Execution Pipeline

1. LLM generates tool call with arguments
2. Tool name validated against registry
3. Arguments parsed and validated (Pydantic)
4. Tool handler executed (with timeout)
5. Result returned to LLM for response generation
6. All tool calls logged for audit

---

## Memory Management

### Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Short-Term Memory                         │
│  (In-memory: active conversation context)                   │
│  - Recent 20 messages                                       │
│  - Current task state                                       │
│  - Active tool results                                      │
│  - TTL: session duration                                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   Long-Term Memory                           │
│  (Redis + PostgreSQL: cross-session)                        │
│  - Conversation history (7-day retention)                   │
│  - Patient preferences                                      │
│  - Previous clinical summaries                              │
│  - TTL: 7-90 days per policy                                │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   Episodic Memory                            │
│  (Vector DB: semantic recall)                               │
│  - Past interactions embedded and indexed                   │
│  - Clinical decision history                                 │
│  - Similar case retrieval                                   │
│  - Retention: configurable (default 1 year)                 │
└─────────────────────────────────────────────────────────────┘
```

### MemoryEntry Schema

```python
class MemoryEntry(BaseModel):
    agent_name: str
    context: str                    # The input/query
    response_summary: str           # Condensed response
    confidence: float               # 0.0-1.0 confidence score
    timestamp: float
    metadata: Dict[str, Any]        # task_id, task_type, model_used
```

### Memory Search

- **Keyword search**: Agent-specific recent entries
- **Semantic search**: Cross-agent similarity search (via BGE-M3 embeddings)
- **Temporal search**: Time-bounded queries
- **Confidence-filtered**: Only recall high-confidence results

---

## Fallback Chain

When the primary model fails (timeout, error, low confidence), the system automatically falls back through the model hierarchy.

### Fallback Configuration

```python
FALLBACK_CHAIN = [
    ModelConfig(
        provider="vllm",
        model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        temperature=0.1, max_tokens=8192, context_length=32768,
    ),
    ModelConfig(
        provider="vllm",
        model="Qwen/Qwen3-32B-Instruct",
        temperature=0.1, max_tokens=4096, context_length=32768,
    ),
    ModelConfig(
        provider="vllm",
        model="meta-llama/Llama-4-17B-Instruct",
        temperature=0.1, max_tokens=4096,
    ),
    ModelConfig(
        provider="vllm",
        model="mistralai/Mistral-7B-Instruct-v0.3",
        temperature=0.1, max_tokens=4096,
    ),
]
```

### Fallback Strategies

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| **Sequential** | Try models in order until success | Default for all agents |
| **Confidence Threshold** | Use best response above threshold | Clinical documentation |
| **Parallel Vote** | Run 2+ models, pick most consistent | Triage decisions |

### Failure Handling

| Failure Mode | Action | Retries |
|-------------|--------|---------|
| HTTP Timeout | Log warning, try next model | 0 |
| HTTP 5xx | Wait 1s, retry same model | 3 |
| Empty response | Try next model | 0 |
| Low confidence (<0.3) | Try next model | 0 |
| Tool call error | Retry tool, then fallback | 2 |

---

## Guardrails Integration

UbuntuCare replaces NVIDIA NeMo Guardrails with **Guardrails AI** plus custom guardrail layers.

### Guardrail Layers

```
User Input
    │
    ▼
┌──────────────┐
│ Input Guard  │  — Profanity, PHI leakage prevention
│              │  — Topic restriction (health only)
│              │  — Language detection
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Content      │  — Llama Guard 3 (safety classification)
│ Safety       │  — Custom Zambia-specific content policies
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Clinical     │  — Medical advice boundaries
│ Guardrail    │  — "Consult a provider" disclaimers
│              │  — Emergency escalation triggers
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Output       │  — Hallucination detection
│ Guardrail    │  — Factual consistency check
│              │  — Confidence scoring
└──────┬───────┘
       │
       ▼
    Response
```

### Guardrail Rules (Zambia-Specific)

| Rule | Trigger | Action |
|------|---------|--------|
| Emergency keyword | "chest pain", "unconscious", "severe bleeding" | Immediate triage escalation |
| Drug dosage check | Any medication mention | Validate against Zambia EML |
| Pregnancy check | Female patient 12-50 | Pregnancy test recommendation |
| Malaria protocol | Fever + travel to endemic area | Malaria RDT recommendation |
| HIV disclosure | Positive test result | Provider-only disclosure |
| Child vaccination | Child <5 years | EPI schedule verification |

---

## RAG Integration

UbuntuCare uses a hybrid retrieval strategy combining dense (vector) and sparse (keyword) search across multiple knowledge bases.

### Knowledge Base Sources

| Source | Collection | Update Frequency |
|--------|-----------|-----------------|
| Zambia National Treatment Guidelines | `zambia_treatment_guidelines` | Annual |
| WHO Treatment Guidelines | `who_guidelines` | As published |
| Zambia Essential Medicines List | `zambia_eml` | Annual |
| SmartCare Clinical Protocols | `smartcare_protocols` | Per update |
| PubMed Medical Literature | `pubmed_abstracts` | Weekly |
| Drug Interaction Database | `drug_interactions` | Quarterly |
| Vaccine Schedules (Zambia EPI) | `zambia_epi` | Annual |
| ICD-10-CM Code Descriptions | `icd10_codes` | Annual |
| Malaria Treatment Protocols | `malaria_protocols` | Per WHO update |
| TB/HIV Co-management Guidelines | `tb_hiv_guidelines` | Per MoH update |

### Retrieval Pipeline

```
Query
  │
  ├─▶ Dense Retrieval (BGE-M3 embeddings → Qdrant)
  │     │
  │     └─▶ Vector similarity search (top 20)
  │
  ├─▶ Sparse Retrieval (BM25 → PostgreSQL FTS)
  │     │
  │     └─▶ Keyword match (top 10)
  │
  └─▶ Hybrid Fusion (Reciprocal Rank Fusion)
        │
        └─▶ Top 5 combined results
              │
              └─▶ LLM context window
```

### Embedding Strategy

| Model | Dimensions | Language Support | Use Case |
|-------|-----------|-----------------|----------|
| BGE-M3 | 1024 | 100+ languages incl. Bantu | Primary embedding |
| BGE-Small-EN-v1.5 | 384 | English | Fast retrieval |
| Custom (planned) | 768 | Nyanja, Bemba, Tonga, Lozi | Local language RAG |

---

## Clinical Workflow Automation

### Workflow: Outpatient Visit

```
1. Patient Registration
   │
2. Triage Assessment
   │  ├─ Vitals recording
   │  ├─ Symptom analysis
   │  ├─ MEWS scoring
   │  └─ Urgency determination
   │
3. Queue Assignment
   │  ├─ Appropriate department
   │  └─ Estimated wait time
   │
4. Clinical Encounter
   │  ├─ Voice conversation
   │  ├─ Real-time transcription
   │  ├─ SOAP note generation
   │  └─ ICD-10 coding
   │
5. Orders & Prescriptions
   │  ├─ Lab tests
   │  ├─ Imaging
   │  ├─ Medications
   │  └─ Referrals
   │
6. Patient Education
   │  ├─ Diagnosis explanation
   │  ├─ Medication instructions
   │  └─ Follow-up plan
   │
7. Follow-up Scheduling
   │  ├─ Appointment booking
   │  └─ SMS reminder
   │
8. Billing & Claims
   │  ├─ NHIMA claim
   │  └─ Payment processing
   │
9. Disease Surveillance (if applicable)
      └─ Notifiable disease report
```

### Workflow: Disease Outbreak Detection

```
Daily
  │
  ├─ Aggregate syndromic data from all facilities
  │
  ├─ Run temporal cluster detection (Poisson model)
  │     └─ Threshold exceedance alert
  │
  ├─ Run spatial cluster detection (Kulldorff scan)
  │     └─ Geographic cluster
  │
  ├─ Agent cross-references with:
  │     ├─ Lab confirmed cases
  │     ├─ CHW field reports
  │     └─ Nearby facility reports
  │
  └─ If confirmed: Auto-generate outbreak alert
        │
        ├─ Notify District Health Office
        ├─ Notify Zambia National Public Health Institute
        ├─ Activate response protocol
        └─ Deploy CHW alerts
```
