"""Choose compliance thresholds using only the development half of the labelled set.

Items with odd numbers are development data and items with even numbers are held out
for run_eval.py. The rule: never label an unsupported requirement Covered, then
label as many supported requirements Covered as possible.

    python -m eval.calibrate
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from backend.schemas.compliance import ComplianceStatus
from backend.schemas.requirements import ExtractedRequirement
from backend.services.compliance_analysis import ComplianceAnalysisService
from backend.services.knowledge_base import knowledge_base_service

GOLD = Path(__file__).resolve().parent / "gold" / "compliance.json"


def is_dev(item_id: str) -> bool:
    return int(item_id[1:]) % 2 == 1


class CachedRetriever:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def search(self, query: str) -> dict:
        if query not in self._cache:
            self._cache[query] = knowledge_base_service.search(query)
        return self._cache[query]


def main() -> None:
    items = [i for i in json.loads(GOLD.read_text(encoding="utf-8"))["items"] if is_dev(i["id"])]
    service = ComplianceAnalysisService(CachedRetriever())
    best = None
    print("covered_score covered_overlap | supported_covered false_covered")
    for score, overlap in itertools.product([0.45, 0.5, 0.55, 0.6, 0.65, 0.7], [0.4, 0.5, 0.6, 0.7, 0.8]):
        service.COVERED_SCORE = score
        service.COVERED_OVERLAP = overlap
        service.PARTIAL_SCORE = max(0.0, score - 0.1)
        true_covered = false_covered = 0
        for item in items:
            result = service.analyze([ExtractedRequirement(requirement_text=item["requirement"])]).results[0]
            if result.status is ComplianceStatus.covered:
                if item["label"] == "supported":
                    true_covered += 1
                else:
                    false_covered += 1
        print(f"{score:>13} {overlap:>15} | {true_covered:>17} {false_covered:>13}")
        # Ties go to the stricter setting, which is the safer one.
        key = (false_covered == 0, true_covered, score, overlap)
        if best is None or key > best[0]:
            best = (key, score, overlap, true_covered, false_covered)
    print(f"\nchosen on {len(items)} development items: COVERED_SCORE={best[1]} COVERED_OVERLAP={best[2]} PARTIAL_SCORE={round(best[1] - 0.1, 2)}")
    print(f"development result: {best[3]} supported Covered, {best[4]} false Covered")


if __name__ == "__main__":
    main()
