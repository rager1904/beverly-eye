# Contributing to UbuntuCare

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

UbuntuCare is a proprietary project. Contributions are accepted only from approved collaborators, employees, contractors, partners, or contributors with prior written authorization from the owner. Contribution does not grant any license to use, copy, distribute, commercialize, or create derivative works from UbuntuCare materials except under a separate written agreement.

---

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct. All contributors must:
- Be respectful and inclusive
- Prioritize patient safety and data privacy
- Follow security best practices
- Maintain confidentiality of any PHI encountered

---

## Getting Started

### Development Setup

```bash
# Clone the authorized repository
git clone <authorized-repository-url>
cd ubuntucare

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Install development dependencies
cd src/backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

cd ../frontend/web
npm install

# Start development environment
docker compose --profile dev up -d
```

### Development Workflow

1. **Find an issue** — Look for `good-first-issue` or `help-wanted` labels
2. **Create a branch** — `git checkout -b feat/my-feature` or `fix/my-bug`
3. **Make changes** — Follow coding standards
4. **Test** — `pytest tests/` for Python, `npm test` for frontend
5. **Submit PR** — Against `main` branch with clear description

---

## Ways to Contribute

### 1. Language Data Collection (High Priority)

Help us improve ASR and TTS for Zambian languages:

- Record conversations in Nyanja, Bemba, Tonga, Lozi
- Transcribe audio in local languages
- Validate existing transcriptions
- Record voice samples for TTS voice cloning

Format: 16kHz mono WAV files with matching JSON transcript.

### 2. Clinical Fine-Tuning

- Curate Zambia-specific clinical datasets
- Fine-tune models on Zambia treatment guidelines
- Add ICD-10 coding for Zambia disease patterns
- Create evaluation benchmarks for Zambia clinical scenarios

### 3. SmartCare Integration

- Improve SmartCare data mapping
- Add new SmartCare data elements
- Fix sync edge cases
- Optimize bulk data transfer

### 4. Documentation

- Translate documentation to local languages
- Write user guides for CHWs
- Create deployment guides for new facility types
- Add architecture diagrams

### 5. Code Contributions

| Area | Files | Skills |
|------|-------|--------|
| Backend services | `src/backend/services/*` | Python, FastAPI, SQLAlchemy |
| AI Agents | `src/backend/agents/*` | Python, LangGraph, LLMs |
| ASR/TTS | `src/backend/ml/speech/*` | Python, Whisper, Coqui |
| RAG/Vector | `src/backend/rag/*` | Python, Qdrant, embeddings |
| Frontend | `src/frontend/web/*` | Next.js, React, TypeScript |
| Mobile | `src/frontend/mobile/*` | React Native |
| Infrastructure | `infra/*` | Docker, K8s, Terraform |
| Deployment | `deployment/*` | Ansible, bash |
| Testing | `tests/*` | pytest, Playwright |

### 6. Bug Reports

Include:
- Device type and OS
- Browser (if frontend issue)
- Service logs
- Steps to reproduce
- Expected vs actual behavior

---

## Pull Request Process

1. **PR title** must follow conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
2. **Description** must explain what and why
3. **Tests** must pass in CI
4. **Linting** must pass (ruff, mypy, ESLint)
5. **Security scanning** must pass (trivy, bandit)
6. **Review** by at least one maintainer required

### PR Checklist

```markdown
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Security reviewed (no PHI in logs/tests)
- [ ] Backwards compatible (or migration guide provided)
- [ ] Linting passes
- [ ] Type checking passes
- [ ] No secrets committed
```

---

## Review Process

1. Automated checks pass
2. Maintainer reviews code quality and security
3. Clinician reviews clinical logic (if applicable)
4. Changes requested or approved
5. Squash merge to `main`

---

## Testing

```bash
# Backend tests
cd src/backend
pytest tests/ -v --cov=src
pytest tests/ -v tests/test_agents/
pytest tests/ -v -k "test_triage"

# Frontend tests
cd src/frontend/web
npm test
npm run test:e2e

# Integration tests
pytest tests/integration/

# Load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## Community

- **Discussions**: GitHub Discussions for Q&A and ideas
- **Issues**: Bug reports and feature requests
- **Security**: Report to security@ubuntucare.zm (see SECURITY.md)
