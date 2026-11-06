"""Measure BidFactory against labelled data and write eval/results/latest.{json,md}.

Run from the repository root:

    python scripts/ingest_kb.py
    python -m eval.run_eval              # retrieval, compliance, rule-based extraction
    GROQ_API_KEY=... python -m eval.run_eval --llm --repeats 3   # also LLM extraction and drafting

Each labelled set lives in eval/gold. The labels were written before the first run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from backend.schemas.compliance import ComplianceStatus, ConflictSeverity
from backend.schemas.requirements import ExtractedRequirement
from backend.services.compliance_analysis import ComplianceAnalysisService
from backend.services.knowledge_base import knowledge_base_service
from backend.services.requirement_extraction import (
    ai_requirement_extraction_service,
    requirement_extraction_service,
)
from backend.services.orchestration import BidAnalysisOrchestrator
from backend.services.response_generation import ResponseGenerationService, draft_stats, unsupported_numbers

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "eval" / "gold"
RESULTS = ROOT / "eval" / "results"
STOP = {"the", "a", "an", "must", "shall", "should", "be", "of", "for", "to", "and", "in", "on", "all", "their", "have", "has", "with", "using", "use"}


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}% ({numerator}/{denominator})" if denominator else "n/a"


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9.%/]+", text.lower().replace("-", " ")) if t.strip(".") and t not in STOP}


def containment(needle: str, haystack: str) -> float:
    needle_tokens = tokens(needle)
    return len(needle_tokens & tokens(haystack)) / len(needle_tokens) if needle_tokens else 0.0


def stem(name: str) -> str:
    return Path(name).stem


def evaluate_compliance() -> tuple[dict, list[dict]]:
    gold = json.loads((GOLD / "compliance.json").read_text(encoding="utf-8"))["items"]
    service = ComplianceAnalysisService(knowledge_base_service)
    rows, latencies = [], []
    for item in gold:
        requirement = ExtractedRequirement(requirement_text=item["requirement"])
        started = time.perf_counter()
        result = service.analyze([requirement]).results[0]
        latencies.append((time.perf_counter() - started) * 1000)
        documents = [stem(e.document_name) for e in result.supporting_evidence]
        conflict = bool(result.conflict_analysis and result.conflict_analysis.severity is not ConflictSeverity.no_conflict)
        rows.append({
            "id": item["id"],
            "label": item["label"],
            "kind": item.get("kind"),
            "requirement": item["requirement"],
            "status": result.status.value,
            "conflict": conflict,
            "top_score": round(max((e.similarity_score for e in result.supporting_evidence), default=0.0), 3),
            "top_1_hit": bool(documents and documents[0] in item["sources"]),
            "top_5_hit": any(d in item["sources"] for d in documents),
        })

    metrics = summarise(rows)
    metrics["latency_ms_p50"] = round(statistics.median(latencies), 1)
    metrics["latency_ms_p95"] = round(percentile(latencies, 0.95), 1)
    # Thresholds are tuned on odd-numbered items (eval/calibrate.py); even-numbered items are held out.
    metrics["held_out"] = summarise([r for r in rows if int(r["id"][1:]) % 2 == 0])
    return metrics, rows


def summarise(rows: list[dict]) -> dict:
    supported = [r for r in rows if r["label"] == "supported"]
    unsupported = [r for r in rows if r["label"] == "unsupported"]
    covered = ComplianceStatus.covered.value
    partial = ComplianceStatus.partially_covered.value
    predicted_covered = [r for r in rows if r["status"] == covered]
    true_covered = [r for r in predicted_covered if r["label"] == "supported"]
    false_covered = [r for r in unsupported if r["status"] == covered]
    auto_answered = [r for r in false_covered if not r["conflict"]]
    return {
        "items": len(rows),
        "supported": len(supported),
        "unsupported": len(unsupported),
        "retrieval_top_1": [sum(r["top_1_hit"] for r in supported), len(supported)],
        "retrieval_top_5": [sum(r["top_5_hit"] for r in supported), len(supported)],
        "supported_found": [sum(r["status"] in (covered, partial) for r in supported), len(supported)],
        "supported_covered": [len(true_covered), len(supported)],
        "covered_precision": [len(true_covered), len(predicted_covered)],
        "false_covered": [len(false_covered), len(unsupported)],
        "false_covered_no_conflict_flag": [len(auto_answered), len(unsupported)],
        "unsupported_partial": [sum(r["status"] == partial for r in unsupported), len(unsupported)],
        "status_by_label": {
            "supported": dict(Counter(r["status"] for r in supported)),
            "unsupported": dict(Counter(r["status"] for r in unsupported)),
        },
    }


def score_extraction(extracted: list[str], gold: list[str], source_text: str) -> dict:
    remaining = list(extracted)
    matched = 0
    for requirement in gold:
        best = max(remaining, key=lambda e: containment(requirement, e), default=None)
        if best is not None and containment(requirement, best) >= 0.6:
            matched += 1
            remaining.remove(best)
    grounded = sum(containment(e, source_text) >= 0.8 for e in extracted)
    return {"gold": len(gold), "matched": matched, "extracted": len(extracted), "grounded": grounded}


def evaluate_extraction(mode: str, repeats: int = 1) -> dict:
    documents = json.loads((GOLD / "extraction.json").read_text(encoding="utf-8"))["documents"]
    totals = Counter()
    latencies: list[float] = []
    per_document = []
    schema_ok = schema_total = 0

    if mode == "llm":
        from backend.services.rocketride_service import RocketRideService
        pipeline = RocketRideService()

    for document in documents:
        path = ROOT / document["path"]
        source = _plain_text(path)
        for _ in range(repeats if mode == "llm" else 1):
            started = time.perf_counter()
            if mode == "rules":
                extracted = [r.requirement_text for r in requirement_extraction_service.extract(source).requirements]
            else:
                schema_total += 1
                try:
                    bid = SimpleNamespace(id="eval", rfp=SimpleNamespace(filename=path.name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
                    response = asyncio.run(pipeline._direct_extraction(bid, path.read_bytes()))
                    parsed = ai_requirement_extraction_service.extract_ai(response)
                    schema_ok += 1
                    extracted = [r.requirement_text for r in parsed.requirements]
                except Exception as exc:  # a failed run counts against recall
                    print(f"extraction failed for {path.name}: {type(exc).__name__}: {exc}")
                    extracted = []
                time.sleep(2)
            latencies.append(time.perf_counter() - started)
            score = score_extraction(extracted, document["requirements"], source)
            totals.update(score)
            per_document.append({"document": path.name, **score})

    metrics = {
        "recall": [totals["matched"], totals["gold"]],
        "precision_grounded": [totals["grounded"], totals["extracted"]],
        "per_run": per_document,
        "latency_s_p50": round(statistics.median(latencies), 2),
        "latency_s_p95": round(percentile(latencies, 0.95), 2),
    }
    if mode == "llm":
        metrics["schema_valid"] = [schema_ok, schema_total]
        metrics["repeats"] = repeats
    return metrics


def _plain_text(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    lines = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


def evaluate_drafts() -> dict:
    """Check the figures in LLM drafts, before and after the figure check in response_generation."""
    gold = json.loads((GOLD / "compliance.json").read_text(encoding="utf-8"))["items"]
    compliance = ComplianceAnalysisService(knowledge_base_service)
    generator = ResponseGenerationService()
    draft_stats.clear()
    responses = clean = refused = refusal_total = 0
    violations, latencies = [], []
    for item in gold:
        requirement = ExtractedRequirement(requirement_text=item["requirement"])
        result = compliance.analyze([requirement]).results[0]
        if result.status is ComplianceStatus.not_found:
            response = generator.generate([requirement], [result]).responses[0]
            refusal_total += 1
            refused += "unavailable" in response.proposed_response.lower()
            continue
        started = time.perf_counter()
        before = draft_stats["rejected"]
        response = generator.generate([requirement], [result]).responses[0]
        latencies.append(time.perf_counter() - started)
        if draft_stats["rejected"] > before:
            violations.append(item["id"])
        # A rejected draft falls back to quoting evidence with its document name, such as Pricing_Guide_2026.
        evidence = " ".join(f"{e.document_name} {e.source_path} {e.retrieved_text}" for e in result.supporting_evidence)
        responses += 1
        clean += not unsupported_numbers(response.proposed_response, evidence, item["requirement"])
        time.sleep(1.5)
    return {
        "llm_drafts": draft_stats["drafted"],
        "rejected_by_figure_check": [draft_stats["rejected"], draft_stats["drafted"]],
        "rejected_ids": violations,
        "final_answers_with_supported_figures": [clean, responses],
        "not_found_refusals": [refused, refusal_total],
        "latency_s_p50": round(statistics.median(latencies), 2) if latencies else 0,
    }


def to_markdown(report: dict) -> str:
    c = report["compliance"]
    pair = lambda key, block=c: pct(*block[key])
    lines = [
        "# BidFactory evaluation results",
        "",
        f"Run on {report['date']} with `python -m eval.run_eval`. Labels are in `eval/gold`.",
        "",
        f"## Retrieval and compliance ({c['items']} labelled requirements: {c['supported']} supported, {c['unsupported']} unsupported)",
        "",
        "Thresholds were tuned only on the odd-numbered items. The held-out column is the even-numbered items, which played no part in tuning.",
        "",
        "| Metric | All items | Held out |",
        "| --- | --- | --- |",
    ]
    held = c.get("held_out")
    for title, key in [
        ("Correct source document ranked first", "retrieval_top_1"),
        ("Correct source document in the top 5", "retrieval_top_5"),
        ("Supported requirements labelled Covered or Partial", "supported_found"),
        ("Supported requirements labelled Covered", "supported_covered"),
        ("Covered labels that were correct (precision)", "covered_precision"),
        ("Unsupported requirements wrongly labelled Covered", "false_covered"),
        ("...of those, with no conflict flag for the reviewer", "false_covered_no_conflict_flag"),
        ("Unsupported requirements labelled Partial (always sent to a reviewer)", "unsupported_partial"),
    ]:
        lines.append(f"| {title} | {pair(key)} | {pct(*held[key])} |")
    lines += [
        "",
        f"Latency per requirement: {c['latency_ms_p50']} ms p50, {c['latency_ms_p95']} ms p95.",
        "",
        "| Label | " + " | ".join(s.value for s in ComplianceStatus) + " |",
        "| --- | " + " | ".join("---" for _ in ComplianceStatus) + " |",
    ]
    for label in ("supported", "unsupported"):
        counts = c["status_by_label"][label]
        lines.append(f"| {label} | " + " | ".join(str(counts.get(s.value, 0)) for s in ComplianceStatus) + " |")

    wrong = [r for r in report["compliance_rows"] if r["label"] == "unsupported" and r["status"] == ComplianceStatus.covered.value]
    missed = [r for r in report["compliance_rows"] if r["label"] == "supported" and r["status"] not in (ComplianceStatus.covered.value, ComplianceStatus.partially_covered.value)]
    lines += ["", "### Failures", ""]
    if wrong:
        lines.append("Unsupported requirements labelled Covered:")
        lines += [f"- {r['id']} ({r['kind']}, score {r['top_score']}, conflict flag: {'yes' if r['conflict'] else 'no'}): {r['requirement']}" for r in wrong]
    if missed:
        lines += ["", "Supported requirements not labelled Covered or Partial:"]
        lines += [f"- {r['id']} ({r['status']}, score {r['top_score']}): {r['requirement']}" for r in missed]

    rules = report["extraction_rules"]
    lines += [
        "", "## Requirement extraction", "",
        "A gold requirement counts as found when an extracted requirement contains at least 60% of its words. An extracted requirement counts as grounded when at least 80% of its words appear in the source document.", "",
        "| Extractor | Recall | Grounded in source | Schema valid | Latency p50 / p95 |",
        "| --- | --- | --- | --- | --- |",
        f"| Rule-based fallback | {pair('recall', rules)} | {pair('precision_grounded', rules)} | n/a | {rules['latency_s_p50']} s / {rules['latency_s_p95']} s |",
    ]
    if "extraction_llm" in report:
        llm = report["extraction_llm"]
        lines.append(f"| LLM ({llm['repeats']} runs per document) | {pair('recall', llm)} | {pair('precision_grounded', llm)} | {pair('schema_valid', llm)} | {llm['latency_s_p50']} s / {llm['latency_s_p95']} s |")
    if "drafts" in report:
        d = report["drafts"]
        lines += [
            "", "## Draft answers", "",
            "| Metric | Result |", "| --- | --- |",
            f"| LLM drafts rejected for a figure found in neither the evidence nor the requirement | {pair('rejected_by_figure_check', d)} |",
            f"| Final answers where every figure is supported | {pair('final_answers_with_supported_figures', d)} |",
            f"| No-evidence requirements that got a refusal instead of a claim | {pair('not_found_refusals', d)} |",
            f"| Draft latency, p50 | {d['latency_s_p50']} s |",
        ]
        if d["rejected_ids"]:
            lines += ["", f"Rejected drafts fell back to quoting the evidence: {', '.join(d['rejected_ids'])}."]
    lines += [
        "", "## What these numbers do not show", "",
        "The knowledge base is 12 synthetic company documents, and the labelled sets are small. These results measure this configuration and do not predict accuracy on real tenders.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="also run LLM extraction and drafting (needs a Groq key)")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    compliance_metrics, rows = evaluate_compliance()
    report = {
        "date": date.today().isoformat(),
        "compliance": compliance_metrics,
        "compliance_rows": rows,
        "extraction_rules": evaluate_extraction("rules"),
    }
    if args.llm:
        if not (os.getenv("ROCKETRIDE_GROQ_KEY") or os.getenv("GROQ_API_KEY")):
            raise SystemExit("--llm needs ROCKETRIDE_GROQ_KEY or GROQ_API_KEY")
        os.environ.setdefault("ROCKETRIDE_GROQ_KEY", os.environ.get("GROQ_API_KEY", ""))
        report["extraction_llm"] = evaluate_extraction("llm", args.repeats)
        report["drafts"] = evaluate_drafts()

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = to_markdown(report)
    (RESULTS / "latest.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
