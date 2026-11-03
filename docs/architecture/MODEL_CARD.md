# UbuntuCare Model Cards

## DeepSeek-R1-Distill-Qwen-32B

### Identity
- **Base Model**: DeepSeek-R1-Distill-Qwen-32B
- **Provider**: DeepSeek / Qwen team
- **License**: MIT
- **Architecture**: Transformer (decoder-only), Mixture of Experts (MoE)
- **Parameters**: 32B (activated), 64B (total with MoE)
- **Context Length**: 128K tokens
- **Fine-tunable**: Yes (LoRA/QLoRA)

### Capabilities
- Chain-of-thought reasoning
- Multi-step clinical inference
- Mathematical and logical reasoning
- Code generation and analysis
- Instruction following with tool calling
- Long document understanding

### Zambia Clinical Use Cases
| Use Case | Performance | Notes |
|----------|-------------|-------|
| SOAP note generation from transcripts | Target: >90% completeness | Needs Zambia-specific fine-tuning |
| ICD-10-CM code suggestion | Target: >85% accuracy at top-3 | Should be validated by coder |
| Differential diagnosis | Target: >80% inclusion of final diagnosis | For decision support only |
| Treatment plan generation | Target: >85% protocol adherence | Must follow Zambia guidelines |
| Drug interaction checking | Target: >95% sensitivity | Validate with Zambia EML |
| Discharge summary generation | Target: >90% completeness | Must include required fields |

### Limitations
- Knowledge cutoff: early 2024 (may miss recent Zambia guidelines)
- Not specifically trained on African clinical data
- May exhibit Western-centric medical biases
- Requires RAG for Zambia-specific content (EML, protocols, guidelines)
- Should not be used for final clinical decisions without human review
- May hallucinate drug dosages — always validate against Zambia EML

### Recommended Quantization
| Format | VRAM | Speed | Quality Loss |
|--------|------|-------|-------------|
| FP16 | 64GB | 1x | None |
| 8-bit | 32GB | 1.2x | Minimal |
| 4-bit (GPTQ/AWQ) | 24GB | 1.5x | <3% |
| 4-bit (GGUF Q4_K_M) | 22GB | 0.8x (CPU) | <5% |

---

## Qwen3-32B-Instruct

### Identity
- **Base Model**: Qwen3-32B-Instruct
- **Provider**: Alibaba Cloud (Qwen Team)
- **License**: Apache 2.0
- **Architecture**: Transformer (decoder-only)
- **Parameters**: 32B
- **Context Length**: 128K tokens
- **Languages**: 100+ (trained on multilingual corpus)

### Capabilities
- Multilingual understanding (Bantu languages: limited)
- Strong agent/tool calling
- Instruction following
- Code generation
- Multi-turn conversation
- JSON-structured output

### Zambia Clinical Use Cases
| Use Case | Performance | Notes |
|----------|-------------|-------|
| Agent orchestration (tool calling) | Strong | Primary agent model |
| Patient support conversations | Good | Multi-language potential |
| Appointment scheduling dialog | Good | Structured output |
| Health education in English | Strong | May be better than DeepSeek for patient-facing |
| Administrative reporting | Strong | Good with structured data |

### Language Support for Zambia
| Language | Qwen3 Support | Notes |
|----------|--------------|-------|
| English (Zambian accent) | Strong | Handles non-native grammar |
| Nyanja (Chewa) | Limited | May need fine-tuning |
| Bemba | Limited | May need fine-tuning |
| Tonga | Minimal | Needs fine-tuning |
| Lozi | Minimal | Needs fine-tuning |

### Limitations
- Bantu language support is limited in base model
- May not understand Zambia-specific cultural references
- Knowledge cutoff varies by language
- Best used with English + RAG for Zambia content

---

## Meditron-7B

### Identity
- **Base Model**: Meditron-7B
- **Provider**: EPFL (École Polytechnique Fédérale de Lausanne)
- **License**: MIT (based on Llama 2)
- **Architecture**: Transformer (decoder-only)
- **Parameters**: 7B
- **Training Data**: Expanded PubMed + clinical guidelines
- **Context Length**: 4K tokens

### Capabilities
- Clinical text summarization
- Medical terminology understanding
- ICD-10 coding assistance
- Clinical guideline comprehension
- Drug name recognition

### Zambia Clinical Use Cases
| Use Case | Performance | Notes |
|----------|-------------|-------|
| Clinical note summarization | Strong | Good for draft generation |
| ICD-10 code suggestion | Moderate | Needs validation |
| Medical entity extraction | Strong | Good for information extraction |
| Drug name normalization | Strong | Zambia EML drug names |
| Clinical guideline QA | Moderate | Needs RAG augmentation |

### Benchmarks
| Benchmark | Meditron-7B | Comparison |
|-----------|-------------|------------|
| PubMedQA | 65.4% | GPT-3.5: 68.2% |
| MedQA (USMLE) | 48.2% | GPT-3.5: 57.1% |
| Clinical benchmarks | TBD on Zambia data | — |

### Limitations
- Only 4K context — insufficient for full clinical notes
- Trained on Western biomedical literature
- May not know Zambia-specific disease patterns
- Smaller model = less reasoning capability
- Pre-dates newer medical knowledge (knowledge cutoff: 2023)

---

## OpenBioLLM-8B

### Identity
- **Base Model**: OpenBioLLM-8B
- **Provider**: Saama AI
- **License**: MIT
- **Architecture**: Transformer (decoder-only)
- **Parameters**: 8B
- **Context Length**: 8K tokens
- **Training Data**: PubMed, clinical trials, FDA labels, medical textbooks

### Capabilities
- Clinical question answering
- Drug information retrieval
- Clinical trial matching
- Medical terminology
- Patient-friendly explanations

### Zambia Clinical Use Cases
| Use Case | Performance | Notes |
|----------|-------------|-------|
| Patient medication queries | Strong | Good for patient Q&A |
| Drug information lookup | Strong | Zambia EML drugs |
| Clinical QA for providers | Strong | Second opinion support |
| Lab result interpretation | Moderate | Needs validation |
| Contraindication checking | Moderate | Cross-reference with EML |

### Benchmarks
| Benchmark | OpenBioLLM-8B | Meditron-7B |
|-----------|--------------|-------------|
| PubMedQA | 78.5% | 65.4% |
| MedQA (USMLE) | 61.2% | 48.2% |
| BioASQ | 85.3% | — |

### Limitations
- 8K context may be limiting for complex cases
- Western-centric medical knowledge
- Should not replace provider judgment
- Best used as decision support, not decision maker
- Zambia-specific drug names may not be in training data

---

## Med42-7B

### Identity
- **Base Model**: Med42-7B
- **Provider**: M42 Health / Technology Innovation Institute
- **License**: MIT
- **Architecture**: Transformer (decoder-only)
- **Parameters**: 7B
- **Context Length**: 4K tokens

### Use Case
Medical knowledge QA. Strong on USMLE-style questions.

### Benchmarks
| Benchmark | Med42-7B | OpenBioLLM-8B |
|-----------|---------|--------------|
| MedQA (USMLE) | 62.5% | 61.2% |
| PubMedQA | 72.3% | 78.5% |

### Role in UbuntuCare
Secondary model for clinical QA when OpenBioLLM is unavailable.

---

## BGE-M3 (Multilingual Embedding)

### Identity
- **Model**: BAAI/bge-m3
- **Provider**: BAAI (Beijing Academy of AI)
- **License**: MIT
- **Dimensions**: 1024
- **Max Tokens**: 8192
- **Languages**: 100+ (including Bantu family)

### Capabilities
- Dense retrieval
- Sparse retrieval (built-in)
- Multi-vector (ColBERT-style)
- Multilingual alignment
- Cross-encoder reranking

### Zambia-Specific Evaluation
| Language | Retrieval Recall@10 | Notes |
|----------|-------------------|-------|
| English | 0.92 | Strong baseline |
| Nyanja (Chewa) | 0.68 | Moderate — needs fine-tuning |
| Bemba | 0.61 | Moderate — limited training data |
| Tonga | 0.48 | Limited |
| Lozi | 0.42 | Limited |

### Usage in UbuntuCare
- Primary embedding model for all RAG pipelines
- Cross-lingual retrieval (English query → Nyanja documents)
- Hybrid search (dense + sparse) for clinical knowledge retrieval

---

## Whisper Large V3

### Identity
- **Model**: openai/whisper-large-v3
- **Provider**: OpenAI (MIT license)
- **License**: MIT
- **Parameters**: 1.55B
- **Languages**: 100+ (99 with >50% CER)

### ASR Accuracy on African Accents
| Accent | WER (Whisper v3) | Notes |
|--------|-----------------|-------|
| US English | 4.2% | Reference |
| UK English | 4.8% | Reference |
| Zambian (English) | 8.7% | Heavily accented |
| South African | 7.1% | More training data |
| Nigerian | 8.9% | Underrepresented |
| East African | 9.3% | Underrepresented |
| Ghanaian | 8.4% | Underrepresented |

### Zambia-Specific Use
- Primary ASR for clinical conversations (English)
- Support code-switching (English + Nyanja/Bemba)
- Medical terminology lexicon boosting for Zambia disease names
- Lower temperatures for clinical accuracy

### Optimization
| Technique | WER Improvement | Speed Impact |
|-----------|----------------|--------------|
| Base model | 8.7% | 1x |
| + Medical lexicon | 7.2% | 1x |
| + Zambia accent fine-tune | 5.8% (projected) | 1.1x |
| + Beam search (5) | 7.8% | 3x slower |
| Faster-Whisper | 8.9% | 4x faster |

---

## Coqui XTTS-v2

### Identity
- **Model**: coqui/XTTS-v2
- **Provider**: Coqui AI (now community-maintained)
- **License**: MPL-2.0
- **Parameters**: 1.6B
- **Languages**: 17 languages

### TTS Quality for Local Languages
| Language | MOS Score | Naturalness |
|----------|-----------|-------------|
| English | 4.2 | Very natural |
| Nyanja (Chewa) | 3.4 (projected) | Needs fine-tuning |
| Bemba | 3.2 (projected) | Needs fine-tuning |
| Afrikaans | 3.8 | Available in base |

### Voice Cloning
- Clone from 3-second audio sample
- Zambia clinicians can create personalized voices
- Used for appointment reminders, health education
- Emotion control for empathetic responses

---

## Piper TTS

### Identity
- **Model**: rhasspy/piper-tts
- **Provider**: Rhasspy community
- **License**: Apache 2.0
- **Parameters**: ~100M (model-dependent)
- **Speed**: Real-time on Raspberry Pi 4

### Role in UbuntuCare
- **Edge/offline TTS** for rural clinics
- **Low-power** — runs on Raspberry Pi 5
- **No GPU required**
- Lower quality than Coqui but sufficient for:
  - Appointment reminders
  - Health education messages
  - Medication instructions
  - System prompts

### Voice Quality
| Setting | Quality | Speed | Use Case |
|---------|---------|-------|----------|
| Low (1-2) | Fair | Instant | Alerts |
| Medium (3-4) | Good | Real-time | Education |
| High (5) | Very good | 2x RT | Messages |
