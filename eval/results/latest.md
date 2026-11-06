# BidFactory evaluation results

Run on 2026-11-06 with `python -m eval.run_eval`. Labels are in `eval/gold`.

## Retrieval and compliance (50 labelled requirements: 30 supported, 20 unsupported)

Thresholds were tuned only on the odd-numbered items. The held-out column is the even-numbered items, which played no part in tuning.

| Metric | All items | Held out |
| --- | --- | --- |
| Correct source document ranked first | 100.0% (30/30) | 100.0% (15/15) |
| Correct source document in the top 5 | 100.0% (30/30) | 100.0% (15/15) |
| Supported requirements labelled Covered or Partial | 100.0% (30/30) | 100.0% (15/15) |
| Supported requirements labelled Covered | 83.3% (25/30) | 80.0% (12/15) |
| Covered labels that were correct (precision) | 100.0% (25/25) | 100.0% (12/12) |
| Unsupported requirements wrongly labelled Covered | 0.0% (0/20) | 0.0% (0/10) |
| ...of those, with no conflict flag for the reviewer | 0.0% (0/20) | 0.0% (0/10) |
| Unsupported requirements labelled Partial (always sent to a reviewer) | 5.0% (1/20) | 10.0% (1/10) |

Latency per requirement: 9.4 ms p50, 14.4 ms p95.

| Label | COVERED | PARTIALLY_COVERED | NOT_FOUND | NEEDS_HUMAN_REVIEW |
| --- | --- | --- | --- | --- |
| supported | 25 | 5 | 0 | 0 |
| unsupported | 0 | 1 | 5 | 14 |

### Failures


## Requirement extraction

A gold requirement counts as found when an extracted requirement contains at least 60% of its words. An extracted requirement counts as grounded when at least 80% of its words appear in the source document.

| Extractor | Recall | Grounded in source | Schema valid | Latency p50 / p95 |
| --- | --- | --- | --- | --- |
| Rule-based fallback | 92.0% (23/25) | 100.0% (23/23) | n/a | 0.0 s / 0.0 s |
| LLM (3 runs per document) | 84.0% (63/75) | 94.5% (69/73) | 91.7% (11/12) | 4.66 s / 12.86 s |

## Draft answers

| Metric | Result |
| --- | --- |
| LLM drafts rejected for a figure found in neither the evidence nor the requirement | 2.2% (1/45) |
| Final answers where every figure is supported | 100.0% (45/45) |
| No-evidence requirements that got a refusal instead of a claim | 100.0% (5/5) |
| Draft latency, p50 | 1.85 s |

Rejected drafts fell back to quoting the evidence: S30.

## What these numbers do not show

The knowledge base is 12 synthetic company documents, and the labelled sets are small. These results measure this configuration and do not predict accuracy on real tenders.
