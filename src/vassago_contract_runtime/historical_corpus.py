"""Historical exploit corpus helpers.

The historical corpus is an evaluation input, not detector logic. Runtime
phases may consume only ``blind_inputs``. ``hidden_ground_truth`` is reserved
for offline scoring after a blind run.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from vassago_contract_runtime.design_runtime.manifest import atomic_write_json, read_json
from vassago_contract_runtime.design_runtime.models import ADDRESS_RE, ContractTarget, ModelValidationError


DEFAULT_HISTORICAL_CORPUS = Path("designs/historical-exploits/manifest.json")


def build_historical_corpus_report(
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    family: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    cases = _filtered_cases(manifest, family=family, limit=limit)
    invalid = [_validate_case(case) for case in cases]
    invalid = [item for item in invalid if item]
    targets = [_target_from_case(case) for case in cases if _target_from_case(case)]
    duplicate_targets = _duplicates(f"{item['chain']}|{item['address']}" for item in targets)
    return {
        "status": "completed" if not invalid else "invalid",
        "manifest": {
            "path": str(manifest_path),
            "kind": manifest.get("kind"),
            "version": manifest.get("version"),
            "generated_from": manifest.get("generated_from"),
        },
        "policy": manifest.get("policy") or {},
        "summary": {
            "case_count": len(cases),
            "target_count": len(targets),
            "by_family": dict(Counter(str(case.get("family")) for case in cases)),
            "ready_for_blind_benchmark": sum(
                1 for case in cases if (case.get("quality") or {}).get("ready_for_blind_benchmark")
            ),
            "with_attack_tx": sum(1 for case in cases if (case.get("quality") or {}).get("has_attack_tx")),
            "with_fork_block": sum(1 for case in cases if (case.get("quality") or {}).get("has_fork_block")),
            "with_vulnerable_contract": sum(
                1 for case in cases if (case.get("quality") or {}).get("has_vulnerable_contract")
            ),
            "duplicate_target_count": len(duplicate_targets),
        },
        "invalid_cases": invalid,
        "duplicate_targets": duplicate_targets,
        "targets": targets,
        "evidence_status": "historical_metadata_only",
        "note": "Use targets/blind_inputs for runs. hidden_ground_truth is scoring-only and must not drive detection.",
    }


def write_historical_blind_targets(
    output_path: str | Path,
    manifest_path: str | Path = DEFAULT_HISTORICAL_CORPUS,
    *,
    family: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    report = build_historical_corpus_report(manifest_path, family=family, limit=limit)
    payload = {
        "kind": "vassago-contract-target-list",
        "source": {
            "corpus_manifest": str(manifest_path),
            "family": family,
            "limit": limit,
            "blind": True,
        },
        "targets": report["targets"],
    }
    atomic_write_json(output_path, payload)
    return {
        "status": "completed",
        "output": str(output_path),
        "target_count": len(payload["targets"]),
        "corpus_status": report["status"],
        "invalid_case_count": len(report["invalid_cases"]),
    }


def _filtered_cases(manifest: dict[str, Any], *, family: str | None, limit: int | None) -> list[dict[str, Any]]:
    cases = [case for case in manifest.get("cases") or [] if isinstance(case, dict)]
    if family:
        cases = [case for case in cases if str(case.get("family")) == family]
    if limit is not None:
        cases = cases[: max(0, limit)]
    return cases


def _validate_case(case: dict[str, Any]) -> dict[str, Any] | None:
    errors: list[str] = []
    if not case.get("benchmark_id"):
        errors.append("missing_benchmark_id")
    if not case.get("family"):
        errors.append("missing_family")
    blind = case.get("blind_inputs") or {}
    target_address = str(blind.get("target_address") or "")
    if not ADDRESS_RE.match(target_address):
        errors.append("invalid_blind_target_address")
    if "hidden_ground_truth" not in case:
        errors.append("missing_hidden_ground_truth")
    if errors:
        return {"benchmark_id": case.get("benchmark_id"), "case_id": case.get("case_id"), "errors": errors}
    return None


def _target_from_case(case: dict[str, Any]) -> dict[str, Any] | None:
    blind = case.get("blind_inputs") or {}
    replay_fork_block = _replay_fork_block(case)
    try:
        target = ContractTarget(
            chain=str(blind.get("chain") or "unknown"),
            address=str(blind.get("target_address") or ""),
            label=str(case.get("benchmark_id") or case.get("case_id") or "historical-case"),
            metadata={
                "historical_corpus": True,
                "benchmark_id": case.get("benchmark_id"),
                "case_id": case.get("case_id"),
                "family_hint": case.get("family"),
                "source_repo_path": blind.get("source_repo_path"),
                "has_foundry_poc": bool(blind.get("has_foundry_poc")),
                **({"replay_fork_block_number": replay_fork_block} if replay_fork_block is not None else {}),
            },
        )
    except ModelValidationError:
        return None
    return target.to_json()


def _replay_fork_block(case: dict[str, Any]) -> int | None:
    """Return a historical replay fork block without exposing detector labels.

    This value is operational metadata for local/fork runtime reproduction. It
    must not be used by source-truth, scoring, or target selection logic.
    """

    truth = case.get("hidden_ground_truth") or {}
    blocks = truth.get("fork_blocks") or []
    if not blocks:
        return None
    try:
        block = int(str(blocks[0]))
    except (TypeError, ValueError):
        return None
    return block if block > 0 else None


def _duplicates(values: Any) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)
