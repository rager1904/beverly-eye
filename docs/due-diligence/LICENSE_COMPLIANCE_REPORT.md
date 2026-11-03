# UbuntuCare License Compliance Report

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Summary

The repository has been moved to a proprietary all-rights-reserved licensing posture for UbuntuCare-owned materials. Third-party dependencies, models, frameworks, templates, generated files, and external assets remain governed by their own licenses.

Owner representation: the repository has not been published or shared with third parties under the earlier Apache-2.0/open-source documentation posture. This report is not legal advice.

## Current Repository License Declaration

Current intended posture:

- Proprietary UbuntuCare materials are owned by Francis Banda.
- No copying, modification, distribution, sublicensing, hosting, commercialization, or derivative works are permitted without written permission.
- Third-party notices and obligations remain intact.

## Missing Compliance Artifacts

| Artifact | Status | Risk |
|---|---|---|
| Third-party notices | Preliminary notice added | Medium |
| SBOM | Preliminary human-readable summary added; machine-generated SBOM pending | Medium |
| Model license register | Preliminary model register added; exact artifact evidence pending | Medium |
| Asset register | Not found | Medium |
| Contributor assignment evidence | Ownership attestation added; formal contributor assignments pending if contributors exist | Medium |
| Owner non-publication attestation | Documented in due diligence reports | Low |

## What Can Remain Proprietary

Likely proprietary, subject to ownership evidence:

- Brand, product name, proprietary documentation, product architecture, custom code, custom workflows, prompts, local deployment strategy, local-language/clinical datasets, fine-tunes, evaluation sets, customer-specific configurations, and commercial implementation materials.

## Third-Party Obligations

Likely obligations:

- Preserve MIT/BSD/ISC/Apache notices where applicable.
- Include Apache-2.0 license/NOTICE materials for Apache dependencies.
- Track MPL-2.0 obligations for Coqui XTTS-v2 if modified or distributed.
- Follow custom model terms for Llama-derived or provider-specific models.
- Respect Flutter, React, Next.js, Radix, Tailwind, Python, and container image licenses.

## Potential Conflicts

| Item | Concern | Action |
|---|---|---|
| Historical Apache/open-source docs | Could confuse reviewers if old copies exist | Keep current proprietary license/docs consistent and retain owner non-publication attestation. |
| Open-source statements in older docs | Confuses diligence | Update docs consistently. |
| Model licenses | Some may restrict commercial or redistribution use | Verify exact model artifacts. |
| UI/template provenance | Attribution may be required | Record source and notices. |

## Required Disclosures

Before investor or enterprise review, prepare:

- `THIRD_PARTY_NOTICES.md`
- CycloneDX or SPDX SBOMs for Python, npm, Flutter, Docker images, and models.
- Model license register.
- Asset register.
- Contributor/IP assignment evidence.
- Owner attestation that the repository was not published or shared under any prior open-source license.
