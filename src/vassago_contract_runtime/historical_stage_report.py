"""Stage-level failure report for historical blind benchmarks.

This report is post-run only. It may read hidden corpus labels after the blind
runtime has completed, but it never feeds those labels back into detection.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from vassago_contract_runtime.design_runtime.manifest import atomic_write_json, read_json
from vassago_contract_runtime.historical_corpus import DEFAULT_HISTORICAL_CORPUS
from vassago_contract_runtime.historical_scoring import build_historical_score


DEFAULT_STAGE_OUTPUT = "historical-stage-failure"

PHASE_FILES = {
    "corpus_candidates": Path("phases") / "03_corpus_motifs" / "sc01-thesis-candidates.json",
    "thesis_queue": Path("phases") / "04_thesis_acquisition" / "sc01-thesis-queue.json",
    "source_truth": Path("phases") / "05_source_truth" / "sc01-source-truth.json",
    "proof_pieces": Path("phases") / "07_proof_pieces" / "sc01-proof-piece-state.json",
    "runtime_ready": Path("phases") / "07_proof_pieces" / "sc01-runtime-ready.json",
    "compile_result": Path("phases") / "08_compile_only" / "compile-result.json",
    "runtime_result": Path("phases") / "09_runtime_foundry" / "foundry-runtime-result.json",
}

FAMILY_PRIORITY = [
    "proxy_upgrade_signature",
    "oracle_accounting",
    "reentrancy_token",
    "sc01_access_control",
    "bridge_message_auth",
]


def build_historical_stage_report(
    run_dir: str | Path,
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    family: str | None = None,
    benchmark_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    run_root = Path(run_dir)
    score = build_historical_score(run_root, manifest_path, family=family, benchmark_id=benchmark_id, limit=limit)
    records = [_stage_record(run_root, record) for record in score["records"]]
    by_stage = Counter(record["blocking_stage"] for record in records)
    by_family_stage: dict[str, dict[str, int]] = {}
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        family_counts[str(record["family"])][str(record["blocking_stage"])] += 1
    for family_name, counts in family_counts.items():
        by_family_stage[family_name] = dict(sorted(counts.items()))
    candidate_records = [record for record in records if record["signal_level"] == "candidate"]
    return {
        "kind": "vassago-historical-stage-failure-report",
        "status": "completed",
        "run": score["run"],
        "manifest": score["manifest"],
        "scope": score["scope"],
        "summary": {
            "case_count": len(records),
            "candidate_count": len(candidate_records),
            "runtime_ready_count": sum(1 for record in records if record["signal_level"] == "runtime_ready"),
            "runtime_count": sum(1 for record in records if record["signal_level"] == "runtime"),
            "by_stage": dict(sorted(by_stage.items())),
            "by_family_stage": by_family_stage,
            "candidate_priority": _candidate_priority(candidate_records),
        },
        "records": records,
        "candidate_records": candidate_records,
        "priority_plan": _priority_plan(candidate_records),
        "policy": {
            "post_run_only": True,
            "hidden_ground_truth_used_for_scoring_only": True,
            "detector_must_not_read_this_report": True,
            "no_live_exploitability_claim": True,
            "no_broadcast": True,
        },
    }


def write_historical_stage_report(
    run_dir: str | Path,
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    output_dir: str | Path | None = None,
    family: str | None = None,
    benchmark_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    report = build_historical_stage_report(
        run_dir,
        manifest_path,
        family=family,
        benchmark_id=benchmark_id,
        limit=limit,
    )
    output_root = Path(output_dir) if output_dir else Path(run_dir) / DEFAULT_STAGE_OUTPUT
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "historical-stage-failure-report.json"
    md_path = output_root / "historical-stage-failure-report.md"
    atomic_write_json(json_path, report)
    md_path.write_text(_markdown(report), encoding="utf-8")
    return {
        "status": "completed",
        "report": report,
        "artifacts": {
            "json": str(json_path),
            "markdown": str(md_path),
        },
    }


def _stage_record(run_root: Path, score_record: dict[str, Any]) -> dict[str, Any]:
    target_id = score_record.get("target_id")
    sidecars = _sidecars(run_root, str(target_id)) if target_id else {}
    blocking_stage, blocker_summary = _blocking_stage(score_record, sidecars)
    source_truth = sidecars.get("source_truth") or {}
    proof_pieces = sidecars.get("proof_pieces") or {}
    thesis_queue = sidecars.get("thesis_queue") or {}
    return {
        **score_record,
        "blocking_stage": blocking_stage,
        "blocker_summary": blocker_summary,
        "thesis_ids": _unique_thesis_ids(thesis_queue, source_truth, proof_pieces),
        "candidate_ids": _unique_candidate_ids(thesis_queue, source_truth, proof_pieces),
        "matched_functions": _matched_functions(thesis_queue, source_truth),
        "missing_pieces": _missing_pieces(source_truth, proof_pieces),
        "state_blockers": _state_blockers(proof_pieces),
        "recommended_mapper": _recommended_mapper(score_record, blocking_stage),
        "next_action": _next_action(score_record, blocking_stage),
    }


def _sidecars(run_root: Path, target_id: str) -> dict[str, dict[str, Any]]:
    target_root = run_root / "targets" / target_id
    return {name: _read_optional_json(target_root / rel_path) for name, rel_path in PHASE_FILES.items()}


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return read_json(path)


def _blocking_stage(score_record: dict[str, Any], sidecars: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    status = score_record.get("status")
    signal = score_record.get("signal_level")
    if status == "invalid_target":
        return "00_invalid_target", ["invalid_blind_target"]
    if status == "final_report_missing":
        return "10_final_report_missing", ["final_report_missing"]
    if signal == "runtime":
        return "09_runtime_completed", [_runtime_status(sidecars)]
    if signal == "runtime_ready":
        return "09_runtime_authorization_pending", ["runtime_ready_but_runtime_not_authorized_in_blind_run"]
    if signal == "compile_only":
        return "08_compile_only_no_runtime_gate", _blockers(sidecars.get("runtime_ready") or {})
    queue_count = int(score_record.get("queue_count") or 0)
    source_truth_count = int(score_record.get("source_truth_verified_count") or 0)
    if queue_count <= 0:
        return "04_no_thesis_candidate", _no_candidate_reasons(sidecars)
    if source_truth_count <= 0:
        return "05_source_truth_not_verified", _blockers(sidecars.get("source_truth") or {})
    compile_status = str(score_record.get("compile_status") or "")
    if compile_status == "compile_skipped_not_ready":
        return "07_proof_pieces_incomplete", _blockers(sidecars.get("proof_pieces") or {})
    if compile_status and compile_status not in {"compile_only_passed", "None"}:
        return "08_compile_failed_or_skipped", _blockers(sidecars.get("compile_result") or {})
    return "07_runtime_gate_incomplete", _blockers(sidecars.get("runtime_ready") or {})


def _runtime_status(sidecars: dict[str, dict[str, Any]]) -> str:
    runtime = sidecars.get("runtime_result") or {}
    return str(runtime.get("status") or "runtime_completed")


def _no_candidate_reasons(sidecars: dict[str, dict[str, Any]]) -> list[str]:
    candidates = sidecars.get("corpus_candidates") or {}
    reasons = list(candidates.get("blockers") or [])
    if not reasons and int(candidates.get("candidate_count") or 0) == 0:
        reasons.append("no_corpus_or_semantic_motif_matched")
    return reasons or ["no_thesis_candidate"]


def _blockers(payload: dict[str, Any]) -> list[str]:
    values = payload.get("blockers")
    if isinstance(values, list):
        return [str(item) for item in values if item]
    status = payload.get("status")
    if status:
        return [str(status)]
    return ["no_blocker_detail"]


def _unique_thesis_ids(*payloads: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for payload in payloads:
        for key in ("queue", "reviews", "pieces"):
            for item in payload.get(key) or []:
                thesis_id = item.get("thesis_id")
                if thesis_id:
                    values.append(str(thesis_id))
    return sorted(set(values))


def _unique_candidate_ids(*payloads: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for payload in payloads:
        for key in ("queue", "reviews", "pieces"):
            for item in payload.get(key) or []:
                candidate_id = item.get("candidate_id")
                if candidate_id:
                    values.append(str(candidate_id))
    return sorted(set(values))


def _matched_functions(thesis_queue: dict[str, Any], source_truth: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for payload, key in ((thesis_queue, "queue"), (source_truth, "reviews")):
        for item in payload.get(key) or []:
            values.extend(str(value) for value in item.get("matched_functions") or [])
    return sorted(set(values))


def _missing_pieces(source_truth: dict[str, Any], proof_pieces: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for review in source_truth.get("reviews") or []:
        values.extend(str(item) for item in review.get("missing_proof_pieces") or [])
    for piece in proof_pieces.get("pieces") or []:
        values.extend(str(item) for item in piece.get("missing_pieces") or [])
    return sorted(set(values))


def _state_blockers(proof_pieces: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for piece in proof_pieces.get("pieces") or []:
        values.extend(str(item) for item in piece.get("state_blockers") or [])
    return sorted(set(values))


def _recommended_mapper(record: dict[str, Any], stage: str) -> str:
    family = str(record.get("family") or "unknown")
    if stage == "04_no_thesis_candidate":
        return "semantic_surface_or_thesis_acquisition_mapper"
    if family == "proxy_upgrade_signature":
        return "proxy_upgrade_signature_mapper"
    if family == "oracle_accounting":
        return "oracle_accounting_impact_mapper"
    if family == "reentrancy_token":
        return "reentrancy_token_flow_mapper"
    if family == "sc01_access_control":
        return "sc01_access_control_source_truth_mapper"
    if family == "bridge_message_auth":
        return "bridge_message_auth_mapper"
    return f"{family}_mapper"


def _next_action(record: dict[str, Any], stage: str) -> str:
    if stage == "04_no_thesis_candidate":
        return "Improve semantic roles/thesis acquisition before source-truth."
    if stage == "05_source_truth_not_verified":
        return "Validate source truth with IR/source-backed actor and critical-effect analysis."
    if stage == "07_proof_pieces_incomplete":
        return "Build actor, args, reader, delta and predicate sidecars."
    if stage.startswith("08_"):
        return "Repair compile context or harness generation."
    if stage.startswith("09_runtime_authorization"):
        return "Review runtime-ready case and run local Foundry only when authorized."
    if stage.startswith("09_runtime_completed"):
        return "Preserve runtime evidence and do not claim live risk without current-state review."
    return "Inspect target artifacts and rerun the stage after the missing mapper exists."


def _candidate_priority(candidate_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in candidate_records:
        grouped[str(record.get("family") or "unknown")].append(record)
    result: list[dict[str, Any]] = []
    seen = set()
    for family in FAMILY_PRIORITY:
        if family in grouped:
            seen.add(family)
            result.append(_family_priority_item(family, grouped[family]))
    for family in sorted(set(grouped) - seen):
        result.append(_family_priority_item(family, grouped[family]))
    return result


def _family_priority_item(family: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    stages = Counter(str(item["blocking_stage"]) for item in records)
    return {
        "family": family,
        "candidate_count": len(records),
        "by_stage": dict(sorted(stages.items())),
        "recommended_mapper": _recommended_mapper({"family": family}, "05_source_truth_not_verified"),
        "top_benchmark_ids": [str(item["benchmark_id"]) for item in records[:10]],
    }


def _priority_plan(candidate_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "order": index + 1,
            "reason": "Prioritized by current candidate count and requested family order.",
        }
        for index, item in enumerate(_candidate_priority(candidate_records))
    ]


def _markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Historical Stage Failure Report",
        "",
        f"- Run: `{report['run']['path']}`",
        f"- Manifest: `{report['manifest']['path']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Candidates: `{summary['candidate_count']}`",
        f"- Runtime ready: `{summary['runtime_ready_count']}`",
        f"- Runtime completed: `{summary['runtime_count']}`",
        "",
        "## By Stage",
        "",
    ]
    for stage, count in sorted(summary["by_stage"].items()):
        lines.append(f"- `{stage}`: `{count}`")
    lines.extend(["", "## Candidate Priority", ""])
    for item in report["priority_plan"]:
        lines.append(
            f"{item['order']}. `{item['family']}`: `{item['candidate_count']}` candidates; "
            f"mapper `{item['recommended_mapper']}`; top `{', '.join(item['top_benchmark_ids'])}`"
        )
    lines.extend(["", "## Candidate Records", ""])
    for record in report["candidate_records"]:
        lines.append(
            "- "
            f"`{record['benchmark_id']}` `{record['family']}` `{record['blocking_stage']}` "
            f"mapper=`{record['recommended_mapper']}` "
            f"missing=`{', '.join(record['missing_pieces'][:6]) or 'n/a'}`"
        )
    lines.append("")
    return "\n".join(lines)
