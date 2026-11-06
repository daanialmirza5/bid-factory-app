# BidFactory evaluation results

Run on 2026-11-06 with `python -m eval.run_eval`. Labels are in `eval/gold`.

## Retrieval and compliance (50 labelled requirements: 30 supported, 20 unsupported)

| Metric | Result |
| --- | --- |
| Correct source document ranked first | 93.3% (28/30) |
| Correct source document in the top 5 | 96.7% (29/30) |
| Supported requirements labelled Covered or Partial | 0.0% (0/30) |
| Supported requirements labelled Covered | 0.0% (0/30) |
| Covered labels that were correct (precision) | n/a |
| **Unsupported requirements wrongly labelled Covered** | **0.0% (0/20)** |
| ...of those, with no conflict flag for the reviewer | 0.0% (0/20) |
| Latency per requirement, p50 / p95 | 18.2 ms / 23.2 ms |

| Label | COVERED | PARTIALLY_COVERED | NOT_FOUND | NEEDS_HUMAN_REVIEW |
| --- | --- | --- | --- | --- |
| supported | 0 | 0 | 1 | 29 |
| unsupported | 0 | 0 | 9 | 11 |

### Failures


Supported requirements not labelled Covered or Partial:
- S01 (NEEDS_HUMAN_REVIEW, score 0.466): The vendor must enforce role-based access control.
- S02 (NEEDS_HUMAN_REVIEW, score 0.394): The vendor must require multi-factor authentication.
- S03 (NEEDS_HUMAN_REVIEW, score 0.435): All customer data must be encrypted at rest using AES-256.
- S04 (NEEDS_HUMAN_REVIEW, score 0.447): Data in transit must be secured using TLS 1.3.
- S05 (NEEDS_HUMAN_REVIEW, score 0.372): The vendor must guarantee 99.9% uptime.
- S06 (NEEDS_HUMAN_REVIEW, score 0.429): The vendor must provide 24/7 support.
- S07 (NEEDS_HUMAN_REVIEW, score 0.447): The vendor must respond to critical incidents within one hour.
- S08 (NEEDS_HUMAN_REVIEW, score 0.464): The vendor must hold ISO 27001 certification.
- S09 (NEEDS_HUMAN_REVIEW, score 0.371): The vendor must hold a SOC 2 Type II attestation.
- S10 (NEEDS_HUMAN_REVIEW, score 0.373): Independent third parties must conduct annual penetration tests.
- S11 (NEEDS_HUMAN_REVIEW, score 0.336): Access reviews must occur quarterly.
- S12 (NEEDS_HUMAN_REVIEW, score 0.395): The vendor must perform automated daily backups.
- S13 (NEEDS_HUMAN_REVIEW, score 0.397): The vendor must have a Recovery Time Objective of 1 hour.
- S14 (NEEDS_HUMAN_REVIEW, score 0.394): The vendor must have a Recovery Point Objective of 24 hours.
- S15 (NEEDS_HUMAN_REVIEW, score 0.403): Logs must be retained for a minimum of 1 year.
- S16 (NEEDS_HUMAN_REVIEW, score 0.432): Client information must be destroyed 30 days after contract termination.
- S17 (NEEDS_HUMAN_REVIEW, score 0.433): The solution must be hostable on AWS, Microsoft Azure and Google Cloud Platform.
- S18 (NEEDS_HUMAN_REVIEW, score 0.495): Deployments must be containerized using Kubernetes and Docker and auto-scale.
- S19 (NEEDS_HUMAN_REVIEW, score 0.375): The solution must expose RESTful and GraphQL APIs.
- S20 (NEEDS_HUMAN_REVIEW, score 0.403): The vendor must have built a HIPAA-compliant healthcare data lake.
- S21 (NEEDS_HUMAN_REVIEW, score 0.413): The vendor must have automated a bank's loan origination system.
- S22 (NEEDS_HUMAN_REVIEW, score 0.468): The MLOps pipeline must include automated drift detection and continuous retraining.
- S23 (NEEDS_HUMAN_REVIEW, score 0.415): The solution must provide automated document OCR and layout detection.
- S24 (NEEDS_HUMAN_REVIEW, score 0.553): The software must support GDPR compliance with geographical data residency and audit trails.
- S25 (NEEDS_HUMAN_REVIEW, score 0.55): The vendor must enforce a zero-trust network architecture.
- S26 (NOT_FOUND, score 0.0): The vendor must have a regional office in London.
- S27 (NEEDS_HUMAN_REVIEW, score 0.45): The vendor must employ over 500 engineers, data scientists and cloud architects.
- S28 (NEEDS_HUMAN_REVIEW, score 0.45): The vendor must provide dedicated technical account managers.
- S29 (NEEDS_HUMAN_REVIEW, score 0.471): Issues unresolved for two hours must be escalated to the executive engineering team.
- S30 (NEEDS_HUMAN_REVIEW, score 0.364): The vendor must be able to implement the solution in on-premise environments.

## Requirement extraction

A gold requirement counts as found when an extracted requirement contains at least 60% of its words. An extracted requirement counts as grounded when at least 80% of its words appear in the source document.

| Extractor | Recall | Grounded in source | Schema valid | Latency p50 / p95 |
| --- | --- | --- | --- | --- |
| Rule-based fallback | 92.0% (23/25) | 100.0% (23/23) | n/a | 0.0 s / 0.0 s |

## What these numbers do not show

The knowledge base is 12 synthetic company documents, and the labelled sets are small. These results measure this configuration and do not predict accuracy on real tenders.
