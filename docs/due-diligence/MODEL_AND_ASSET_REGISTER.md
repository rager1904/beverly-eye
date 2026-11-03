# UbuntuCare Model and Asset Register

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Purpose

This register tracks model and media asset provenance for due diligence. It is preliminary and must be completed with exact artifact versions, source URLs, checksums, and reviewed license terms before production use or external diligence.

## Model Register

| Model/family | Intended use | Current license status | Diligence status |
|---|---|---|---|
| DeepSeek-R1-Distill-Qwen | Reasoning, clinical documentation drafts | MIT stated in project docs | Verify exact artifact, source URL, checksum, and license. |
| Qwen instruct family | Agent orchestration, multilingual interaction | Apache-2.0 stated in project docs | Verify exact artifact, source URL, checksum, and license. |
| Llama-family models | Fallback reasoning | Custom/provider terms | Legal review required before commercial use. |
| Mistral-family models | Fallback reasoning | Not fully resolved | Verify exact artifact and license. |
| Meditron | Medical reasoning | MIT stated with upstream caveat | Verify upstream obligations and permitted use. |
| OpenBioLLM | Clinical QA | MIT stated | Verify artifact and license. |
| Med42 | Clinical QA | MIT stated | Verify artifact and license. |
| Whisper/Faster-Whisper | Speech recognition | MIT stated | Verify implementation and model artifact terms. |
| Coqui XTTS-v2 | Text-to-speech | MPL-2.0 stated | Track file-level copyleft obligations if modified/distributed. |
| Piper TTS | Edge text-to-speech | Apache-2.0 stated | Preserve notices. |
| Silero VAD | Voice activity detection | Not fully resolved | Verify commercial terms. |
| pyannote | Speaker diarization | Not fully resolved | Verify access, model card, and commercial restrictions. |
| BGE embeddings | Retrieval embeddings | Not fully resolved | Verify artifact license and redistribution terms. |

## Media Asset Register

| Asset | Location | Current owner/source evidence | Status |
|---|---|---|---|
| ambientprovider.png | `assets/ambientprovider.png`, `src/frontend/web/public/images/ambientprovider.png` | Not documented in repository | Needs source, creator, date, license, and permission record. |
| architecture-diagram.png | `assets/architecture-diagram.png`, `src/frontend/web/public/images/architecture-diagram.png` | Not documented in repository | Needs source, creator, date, license, and permission record. |

## Required Evidence Fields

For every model and media asset, collect:

- Exact name and version.
- Provider/source URL.
- License name and license URL.
- Commercial-use status.
- Redistribution status.
- Modification/fine-tuning status.
- Download or creation date.
- Checksum where applicable.
- Owner approval.

