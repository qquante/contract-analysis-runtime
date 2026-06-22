"""Post-run scoring for the historical exploit corpus.

The scorer is deliberately post-run only. It reads hidden corpus labels after a
design has already produced artifacts from blind inputs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from vassago_contract_runtime.design_runtime.manifest import atomic_write_json, read_json
from vassago_contract_runtime.design_runtime.models import ContractTarget, ModelValidationError
from vassago_contract_runtime.historical_corpus import DEFAULT_HISTORICAL_CORPUS


DEFAULT_SCORE_OUTPUT = "historical-corpus-score"
FINAL_REPORT_PATH = Path("phases") / "10_final_report" / "sc01-final-report.json"


def build_historical_score(
    run_dir: str | Path,
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    family: str | None = None,
    benchmark_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    run_root = Path(run_dir)
    manifest = read_json(manifest_path)
    run_manifest = _read_optional_json(run_root / "run-manifest.json")
    cases = _filtered_cases(manifest, family=family, benchmark_id=benchmark_id, limit=limit)
    records = [_score_case(run_root, case) for case in cases]
    by_signal = Counter(record["signal_level"] for record in records)
    by_status = Counter(record["status"] for record in records)
    by_family: dict[str, dict[str, int]] = {}
    family_signals: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        family_signals[str(record["family"])][str(record["signal_level"])] += 1
    for key, counts in family_signals.items():
        by_family[key] = dict(sorted(counts.items()))
    actionable = {"compile_only", "runtime_ready", "runtime"}
    return {
        "status": "completed",
        "kind": "vassago-historical-corpus-score",
        "run": {
            "path": str(run_root),
            "run_id": run_manifest.get("run_id"),
            "summary": run_manifest.get("summary") or {},
        },
        "manifest": {
            "path": str(manifest_path),
            "kind": manifest.get("kind"),
            "version": manifest.get("version"),
            "generated_from": manifest.get("generated_from"),
        },
        "scope": {"family": family, "benchmark_id": benchmark_id, "limit": limit},
        "summary": {
            "case_count": len(records),
            "scored_count": sum(1 for record in records if record["status"] == "scored"),
            "missing_final_report_count": sum(1 for record in records if record["status"] == "final_report_missing"),
            "invalid_target_count": sum(1 for record in records if record["status"] == "invalid_target"),
            "actionable_count": sum(1 for record in records if record["signal_level"] in actionable),
            "runtime_count": by_signal.get("runtime", 0),
            "runtime_ready_count": by_signal.get("runtime_ready", 0),
            "compile_only_count": by_signal.get("compile_only", 0),
            "source_truth_count": by_signal.get("source_truth", 0),
            "candidate_count": by_signal.get("candidate", 0),
            "none_count": by_signal.get("none", 0),
            "by_signal": dict(sorted(by_signal.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_family_signal": by_family,
        },
        "records": records,
        "policy": {
            "post_run_only": True,
            "hidden_ground_truth_used_for_scoring_only": True,
            "no_live_exploitability_claim": True,
            "no_broadcast": True,
        },
        "next_steps": _next_steps(records),
    }


def write_historical_score(
    run_dir: str | Path,
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    output_dir: str | Path | None = None,
    family: str | None = None,
    benchmark_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    score = build_historical_score(run_dir, manifest_path, family=family, benchmark_id=benchmark_id, limit=limit)
    output_root = Path(output_dir) if output_dir else Path(run_dir) / DEFAULT_SCORE_OUTPUT
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "historical-corpus-score.json"
    md_path = output_root / "historical-corpus-score.md"
    atomic_write_json(json_path, score)
    md_path.write_text(_markdown(score), encoding="utf-8")
    return {
        "status": "completed",
        "score": score,
        "artifacts": {
            "json": str(json_path),
            "markdown": str(md_path),
        },
    }


def _score_case(run_root: Path, case: dict[str, Any]) -> dict[str, Any]:
    benchmark_id = str(case.get("benchmark_id") or "")
    family = str(case.get("family") or "unknown")
    hidden = case.get("hidden_ground_truth") or {}
    target = _target_from_case(case)
    if target is None:
        return {
            "benchmark_id": benchmark_id,
            "family": family,
            "status": "invalid_target",
            "signal_level": "invalid_target",
            "blockers": ["invalid_blind_target"],
        }
    final_report_path = run_root / "targets" / target.target_id / FINAL_REPORT_PATH
    if not final_report_path.is_file():
        return {
            "benchmark_id": benchmark_id,
            "case_id": case.get("case_id"),
            "family": family,
            "target_id": target.target_id,
            "chain": target.chain,
            "address": target.address,
            "status": "final_report_missing",
            "signal_level": "missing",
            "blockers": ["final_report_missing"],
            "hidden_quality": _hidden_quality(hidden),
        }
    report = read_json(final_report_path)
    signal = _signal_level(report)
    return {
        "benchmark_id": benchmark_id,
        "case_id": case.get("case_id"),
        "family": family,
        "target_id": target.target_id,
        "chain": target.chain,
        "address": target.address,
        "status": "scored",
        "signal_level": signal,
        "final_status": report.get("final_status"),
        "evidence_status": report.get("evidence_status"),
        "queue_count": int(report.get("queue_count") or 0),
        "source_truth_verified_count": int(report.get("source_truth_verified_count") or 0),
        "compile_status": report.get("compile_status"),
        "runtime_ready_count": int(report.get("runtime_ready_count") or 0),
        "foundry_allowed": bool(report.get("foundry_allowed")),
        "runtime_status": report.get("runtime_status"),
        "hidden_quality": _hidden_quality(hidden),
    }


def _signal_level(report: dict[str, Any]) -> str:
    if report.get("evidence_status") == "runtime_local":
        return "runtime"
    if report.get("runtime_status") in {"runtime_completed", "not_reproduced"}:
        return "runtime"
    if bool(report.get("foundry_allowed")) or int(report.get("runtime_ready_count") or 0) > 0:
        return "runtime_ready"
    if report.get("compile_status") == "compile_only_passed":
        return "compile_only"
    if int(report.get("source_truth_verified_count") or 0) > 0:
        return "source_truth"
    if int(report.get("queue_count") or 0) > 0:
        return "candidate"
    return "none"


def _hidden_quality(hidden: dict[str, Any]) -> dict[str, Any]:
    return {
        "has_attack_tx": bool(hidden.get("attack_txs")),
        "has_fork_block": bool(hidden.get("fork_blocks")),
        "has_vulnerable_contract": bool(hidden.get("vulnerable_contracts")),
        "loss_label": hidden.get("loss_label"),
    }


def _filtered_cases(
    manifest: dict[str, Any],
    *,
    family: str | None,
    benchmark_id: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    cases = [case for case in manifest.get("cases") or [] if isinstance(case, dict)]
    if family:
        cases = [case for case in cases if str(case.get("family")) == family]
    if benchmark_id:
        cases = [case for case in cases if str(case.get("benchmark_id")) == benchmark_id]
    if limit is not None:
        cases = cases[: max(0, limit)]
    return cases


def _target_from_case(case: dict[str, Any]) -> ContractTarget | None:
    blind = case.get("blind_inputs") or {}
    try:
        return ContractTarget(
            chain=str(blind.get("chain") or ""),
            address=str(blind.get("target_address") or ""),
            label=str(case.get("benchmark_id") or case.get("case_id") or "historical-case"),
            metadata={
                "historical_corpus": True,
                "benchmark_id": case.get("benchmark_id"),
                "case_id": case.get("case_id"),
                "family_hint": case.get("family"),
                "source_repo_path": blind.get("source_repo_path"),
                "has_foundry_poc": bool(blind.get("has_foundry_poc")),
            },
        )
    except ModelValidationError:
        return None


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return read_json(path)


def _next_steps(records: list[dict[str, Any]]) -> list[str]:
    missing = sum(1 for record in records if record["status"] == "final_report_missing")
    source_truth = sum(1 for record in records if record["signal_level"] == "source_truth")
    actionable = sum(1 for record in records if record["signal_level"] in {"compile_only", "runtime_ready", "runtime"})
    steps: list[str] = []
    if missing:
        steps.append("Resume or rerun the blind benchmark until every target has a final report.")
    if source_truth:
        steps.append("Inspect source_truth cases and add proof-piece mappers for actor, args, reader and delta.")
    if actionable:
        steps.append("Review actionable cases one by one before any local Foundry runtime.")
    if not steps:
        steps.append("Inspect none/candidate buckets and improve acquisition, source resolution or thesis mappers.")
    return steps


def _markdown(score: dict[str, Any]) -> str:
    summary = score["summary"]
    lines = [
        "# Historical Corpus Score",
        "",
        f"- Run: `{score['run']['path']}`",
        f"- Manifest: `{score['manifest']['path']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Scored: `{summary['scored_count']}`",
        f"- Missing final report: `{summary['missing_final_report_count']}`",
        f"- Actionable: `{summary['actionable_count']}`",
        f"- Runtime: `{summary['runtime_count']}`",
        f"- Runtime ready: `{summary['runtime_ready_count']}`",
        f"- Compile only: `{summary['compile_only_count']}`",
        f"- Source truth: `{summary['source_truth_count']}`",
        f"- Candidate only: `{summary['candidate_count']}`",
        f"- None: `{summary['none_count']}`",
        "",
        "## By Family",
        "",
    ]
    for family, counts in sorted(summary["by_family_signal"].items()):
        rendered = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        lines.append(f"- `{family}`: {rendered}")
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in score["next_steps"])
    lines.append("")
    return "\n".join(lines)
