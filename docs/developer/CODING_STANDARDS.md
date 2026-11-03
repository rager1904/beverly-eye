# UbuntuCare Coding Standards

## Language Conventions

### Python (Backend)

**Style**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with [ruff](https://docs.astral.sh/ruff/) enforcement.

#### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Packages | `snake_case` | `clinical_documentation` |
| Modules | `snake_case` | `agent.py`, `service.py` |
| Classes | `PascalCase` | `ClinicalDocumentationAgent` |
| Functions | `snake_case` | `generate_soap_note()` |
| Variables | `snake_case` | `patient_name` |
| Constants | `UPPER_SNAKE` | `MAX_RETRY_COUNT = 3` |
| Private | `_prefixed` | `_internal_method()` |
| Type vars | `T`, `K`, `V` | `T = TypeVar('T')` |

#### Imports (sorted by ruff)

```python
# Standard library
from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Third-party
import httpx
from pydantic import BaseModel, Field

# Local
from src.backend.agents.agent_base import AgentContext, AgentResponse, BaseAgent
```

#### Docstrings (Google style)

```python
def generate_soap_note(
    transcript: str,
    patient_id: str,
    encounter_id: Optional[str] = None,
) -> Dict[str, str]:
    """Generate a SOAP-format clinical note from a transcript.

    Args:
        transcript: The full conversation transcript.
        patient_id: UUID of the patient.
        encounter_id: Optional encounter UUID for context.

    Returns:
        Dict with keys: subjective, objective, assessment, plan.

    Raises:
        ValueError: If transcript is empty or too short.
    """
```

### TypeScript / JavaScript (Frontend)

**Style**: Follow [StandardJS](https://standardjs.com/) with ESLint + Prettier.

#### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Components | `PascalCase` | `PatientProfile.tsx` |
| Functions | `camelCase` | `fetchPatientData()` |
| Variables | `camelCase` | `patientName` |
| Constants | `UPPER_SNAKE` (config) | `API_BASE_URL` |
| Types | `PascalCase` | `PatientData` |
| Interfaces | `I` prefix | `IPatientProps` |
| Hooks | `use` prefix | `usePatientData()` |
| CSS classes | `kebab-case` | `patient-profile` |

#### File Organization

```
components/
├── PatientProfile/
│   ├── PatientProfile.tsx      # Component
│   ├── PatientProfile.test.tsx # Tests
│   ├── PatientProfile.module.css # Styles
│   └── index.ts               # Re-export
```

---

## Architecture Standards

### Service Pattern

Every backend service follows this structure:

```
services/example/
├── __init__.py           # Exports
├── main.py              # FastAPI app factory
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic request/response schemas
├── services.py          # Business logic
├── dependencies.py      # FastAPI dependencies
└── routers/
    ├── __init__.py
    ├── resource1.py     # CRUD endpoints
    └── resource2.py
```

### Agent Pattern

```
agents/example_agent/
├── __init__.py           # Agent registration, capabilities
├── agent.py             # Extends BaseAgent
├── prompts.py           # Agent prompt templates
└── tools.py (optional)  # Agent-specific tools
```

### Error Handling

```python
# Use custom exception hierarchy
from src.backend.shared.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
    AuthError,
    ForbiddenError,
    ConflictError,
    ServiceUnavailableError,
)

# All endpoints use standard error response format
@app.get("/patients/{id}")
async def get_patient(id: UUID):
    patient = await patient_service.get(id)
    if not patient:
        raise NotFoundError(f"Patient {id} not found")
    return patient
```

---

## Testing Standards

### Test Coverage

| Module | Minimum Coverage |
|--------|-----------------|
| Core modules | 90% |
| Services | 85% |
| Agents | 80% |
| API routes | 90% |
| Frontend components | 70% |

### Test Structure

```python
# tests/services/test_emr_patients.py

class TestPatientService:
    async def test_create_patient_with_valid_data(self):
        """Should create patient with all required fields."""
        ...

    async def test_create_patient_duplicate_nrc(self):
        """Should raise ConflictError for duplicate NRC."""
        ...

    async def test_search_patient_by_phone(self):
        """Should find patient by phone number."""
        ...
```

### Mocking AI Services

```python
# For tests, use mock AI responses
@pytest.fixture
def mock_agent():
    with patch("src.backend.agents.orchestrator.AgentOrchestrator.process") as mock:
        mock.return_value = AgentResponse(
            content="Mocked response",
            confidence=0.95,
            model_used="mock-model",
        )
        yield mock
```

---

## Git Conventions

### Branch Naming

- `feat/description` — New feature
- `fix/description` — Bug fix
- `docs/description` — Documentation
- `refactor/description` — Code refactoring
- `chore/description` — Maintenance
- `test/description` — Testing

### Commit Messages

```
feat: add NHIMA claim submission endpoint
fix: resolve null pointer in triage scoring
docs: update Zambia deployment guide
refactor: extract sync logic to service
chore: update Python dependencies
test: add triage agent unit tests
```

### PR Title Format

```
feat(emr): add NHIMA claim submission (#123)
fix(triage): handle null vitals in MEWS scoring (#124)
docs: update offline deployment guide (#125)
```

---

## Security Standards

- **No PHI in logs** — Use `log_pii=False` parameter, redact PHI
- **No secrets in code** — Use environment variables or Vault
- **SQL injection prevention** — Always use parameterized queries (SQLAlchemy ORM)
- **XSS prevention** — Never render raw HTML in React, use sanitization
- **CSRF protection** — Keycloak token-based, SameSite cookies
- **Rate limiting** — All endpoints must have rate limits
- **Input validation** — All inputs validated by Pydantic schemas

---

## Performance Standards

| Metric | Target | Measurement |
|--------|--------|-------------|
| API response (p95) | < 500ms | Prometheus |
| ASR transcription (60s audio) | < 5s | Application metric |
| LLM response (p95) | < 15s | Application metric |
| RAG query (p95) | < 500ms | Qdrant metric |
| Database query (p95) | < 100ms | PostgreSQL |

---

## Documentation Standards

- Code is self-documenting with clear naming
- Public APIs have docstrings
- Complex logic has inline comments
- README updated for any new feature
- API changes reflected in OpenAPI spec
- Architecture decisions recorded in ADRs
