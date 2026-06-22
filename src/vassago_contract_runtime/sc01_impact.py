"""SC01 impact review sidecars.

Impact review is intentionally separated from runtime reproduction. A local
Foundry replay can prove a predicate, but severity still needs historical
context and current-state scope. This module writes that distinction as
auditable artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.design_runtime.manifest import load_run_manifest
from vassago_contract_runtime.design_runtime.models import short_hash


IMPACT_PHASE_ID = "11_impact_review"
IMPACT_JSON = "sc01-impact-review.json"
IMPACT_MD = "sc01-impact-review.md"
AUDIUS_GOVERNANCE_PROXY = "0x4deca517d6817b6510798b7328f2314d3003abac"
WORMHOLE_PROXY = "0x98f3c9e6e3face36baad05fe09d375ef1464288b"
NOMAD_REPLICA_PROXY = "0x5d94309e5a0090b165fa4181519701637b6daeba"


def write_sc01_impact_review(run_dir: str | Path, target_id: str) -> dict[str, Any]:
    """Build and write an SC01 impact review for one completed target."""

    manifest = load_run_manifest(run_dir)
    store = ArtifactStore(run_dir, manifest["run_id"])
    review = build_sc01_impact_review(run_dir, target_id)
    json_artifact = store.write_json_artifact(target_id, IMPACT_PHASE_ID, IMPACT_JSON, review)
    md_artifact = store.write_text_artifact(target_id, IMPACT_PHASE_ID, IMPACT_MD, render_sc01_impact_review_markdown(review))
    return {
        "status": review["status"],
        "run_id": manifest["run_id"],
        "target_id": target_id,
        "impact_review_id": review["impact_review_id"],
        "artifacts": [json_artifact, md_artifact],
        "summary": review["summary"],
    }


def build_sc01_impact_review(run_dir: str | Path, target_id: str) -> dict[str, Any]:
    manifest = load_run_manifest(run_dir)
    store = ArtifactStore(run_dir, manifest["run_id"])
    final_report = _read_json(store, target_id, "10_final_report", "sc01-final-report.json")
    assertion = _read_json(store, target_id, "09_runtime_foundry", "assertion-result.json")
    runtime = _read_json(store, target_id, "09_runtime_foundry", "foundry-runtime-result.json")
    source_truth = _read_json(store, target_id, "05_source_truth", "sc01-source-truth.json")
    source_manifest = _read_json(store, target_id, "01_dossier", "source-manifest.json")
    target = dict(source_manifest.get("target") or {})
    address = str(target.get("address") or final_report.get("address") or "").lower()
    run_id = str(manifest["run_id"])
    review_id = f"AIR-{short_hash(f'{run_id}|{target_id}|{address}|sc01')}"

    if _is_audius_proxy(address, source_truth):
        return _audius_impact_review(
            review_id=review_id,
            run_id=manifest["run_id"],
            target_id=target_id,
            target=target,
            final_report=final_report,
            assertion=assertion,
            runtime=runtime,
            source_truth=source_truth,
        )
    if _is_wormhole_proxy(address, source_truth):
        return _wormhole_impact_review(
            review_id=review_id,
            run_id=manifest["run_id"],
            target_id=target_id,
            target=target,
            final_report=final_report,
            assertion=assertion,
            runtime=runtime,
            source_truth=source_truth,
        )
    if _is_nomad_replica(address, source_truth):
        return _nomad_impact_review(
            review_id=review_id,
            run_id=manifest["run_id"],
            target_id=target_id,
            target=target,
            final_report=final_report,
            assertion=assertion,
            runtime=runtime,
            source_truth=source_truth,
        )
    return _generic_sc01_impact_review(
        review_id=review_id,
        run_id=manifest["run_id"],
        target_id=target_id,
        target=target,
        final_report=final_report,
        assertion=assertion,
        runtime=runtime,
    )


def render_sc01_impact_review_markdown(review: dict[str, Any]) -> str:
    summary = dict(review.get("summary") or {})
    current = dict(review.get("current_live_risk") or {})
    reproduction = dict(review.get("local_reproduction") or {})
    historical = dict(review.get("historical_impact") or {})
    lines = [
        "# SC01 Impact Review",
        "",
        f"- Status: `{review.get('status')}`",
        f"- Impact review id: `{review.get('impact_review_id')}`",
        f"- Target: `{review.get('chain')}` `{review.get('address')}`",
        f"- Bug class: `{review.get('bug_class')}`",
        f"- Summary verdict: `{summary.get('verdict')}`",
        f"- Severity posture: `{summary.get('severity_posture')}`",
        f"- Historical severity: `{historical.get('severity')}`",
        f"- Local runtime: `{reproduction.get('status')}`",
        f"- Assertion: `{reproduction.get('assertion_status')}`",
        f"- Current live risk: `{current.get('status')}`",
        "",
        "## Reasoning",
        "",
        str(summary.get("reasoning") or ""),
        "",
        "## Evidence Boundary",
        "",
        "- This review does not broadcast transactions.",
        "- Runtime evidence is local/fork-only.",
        "- Historical severity is not automatically a current live severity claim.",
        "",
    ]
    for item in review.get("next_steps") or []:
        if "## Next Steps" not in lines:
            lines.extend(["## Next Steps", ""])
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _audius_impact_review(
    *,
    review_id: str,
    run_id: str,
    target_id: str,
    target: dict[str, Any],
    final_report: dict[str, Any],
    assertion: dict[str, Any],
    runtime: dict[str, Any],
    source_truth: dict[str, Any],
) -> dict[str, Any]:
    runtime_status = str(runtime.get("status") or final_report.get("runtime_status") or "")
    assertion_status = str(assertion.get("status") or "")
    reproduced = runtime_status == "runtime_completed" and assertion_status == "passed"
    return {
        "status": "completed",
        "impact_review_id": review_id,
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or final_report.get("chain") or "eth"),
        "address": str(target.get("address") or final_report.get("address") or AUDIUS_GOVERNANCE_PROXY),
        "bug_class": "proxy_storage_collision_reinitializer_governance_takeover",
        "summary": {
            "verdict": "historical_reproduced_critical" if reproduced else "historical_context_runtime_not_reproduced",
            "severity_posture": "critical_historical_do_not_claim_live_without_current_state_review",
            "reasoning": (
                "The local fork replay proves that proxy-delegated initialize changes Audius governance privileged "
                "state. Public post-mortem context records a governance takeover and treasury token transfer. "
                "This artifact does not prove a current live exploitable balance or unpatched deployment."
            ),
        },
        "historical_impact": {
            "severity": "critical_historical",
            "affected_system": "Audius governance, staking and delegation contracts",
            "reported_assets_moved": "18,564,497 AUDIO",
            "reported_loss_context": "public reports describe roughly 704 ETH / about $1.08M realized after sale",
            "impact_classes": [
                "governance_takeover",
                "treasury_asset_transfer",
                "privileged_state_reinitialization",
            ],
        },
        "local_reproduction": {
            "status": runtime_status,
            "assertion_status": assertion_status,
            "evidence_status": assertion.get("evidence_status"),
            "predicate": assertion.get("predicate"),
            "measured_delta": assertion.get("measured_delta"),
            "final_status": final_report.get("final_status"),
            "runtime_ready_count": final_report.get("runtime_ready_count"),
            "source_truth_verified_count": final_report.get("source_truth_verified_count"),
            "no_broadcast": bool(runtime.get("no_broadcast", True)),
        },
        "current_live_risk": {
            "status": "not_claimed",
            "reason": (
                "Audius publicly reported remediation. This run did not perform a fresh current-state review of all "
                "patched contracts, token balances, proxies, governance state and access-control state."
            ),
            "required_to_upgrade_to_live_severity": [
                "current proxy implementation and admin state",
                "current initializer/reinitializer status",
                "current treasury/proxy token balances and permissions",
                "proof that the same call path still mutates privileged proxy storage",
            ],
        },
        "source_truth": {
            "status": source_truth.get("status"),
            "verified_count": source_truth.get("source_truth_verified_count"),
            "evidence_kinds": sorted({str(item.get("evidence_kind")) for item in source_truth.get("reviews") or []}),
        },
        "external_context": {
            "status": "public_historical_context",
            "sources": [
                {
                    "name": "Audius governance takeover post-mortem",
                    "url": "https://blog.audius.co/article/audius-governance-takeover-post-mortem-7-23-22",
                },
                {
                    "name": "DeFiHackLabs Audius exploit reproduction",
                    "url": "https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/src/test/2022-07/Audius_exp.sol",
                },
                {
                    "name": "ChainLight Audius variant scanner",
                    "url": "https://blog.chainlight.io/en-audius-variant-scanner-scanning-storage-collisions-between-ethereum-contracts-4d2d64b77566",
                },
            ],
        },
        "next_steps": [
            "If discussing live severity, run a current-state review against the patched Audius deployments.",
            "Keep this as historical reproduced critical unless current exploitability is independently revalidated.",
            "Use the proxy-collision mapper as a regression pattern for Wormhole-style implementation context next.",
        ],
    }


def _wormhole_impact_review(
    *,
    review_id: str,
    run_id: str,
    target_id: str,
    target: dict[str, Any],
    final_report: dict[str, Any],
    assertion: dict[str, Any],
    runtime: dict[str, Any],
    source_truth: dict[str, Any],
) -> dict[str, Any]:
    runtime_status = str(runtime.get("status") or final_report.get("runtime_status") or "")
    assertion_status = str(assertion.get("status") or "")
    reproduced = runtime_status == "runtime_completed" and assertion_status == "passed"
    return {
        "status": "completed",
        "impact_review_id": review_id,
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or final_report.get("chain") or "eth"),
        "address": str(target.get("address") or final_report.get("address") or WORMHOLE_PROXY),
        "bug_class": "wormhole_uninitialized_implementation_guardian_takeover",
        "summary": {
            "verdict": "historical_reproduced_critical" if reproduced else "historical_context_runtime_not_reproduced",
            "severity_posture": "critical_historical_do_not_claim_live_without_current_state_review",
            "reasoning": (
                "The local historical fork replay proves that an uninitialized Wormhole implementation context "
                "can be initialized with an attacker guardian and can reach the guardian-governed "
                "submitContractUpgrade path into a malicious implementation. Public Immunefi context describes "
                "this as a critical historical issue that could have locked protocol funds; this artifact does "
                "not prove current live exploitability."
            ),
        },
        "historical_impact": {
            "severity": "critical_historical",
            "affected_system": "Wormhole Ethereum core bridge implementation context",
            "reported_assets_at_risk": "about $1.8B at submission time per public Immunefi review",
            "reported_loss_context": "fixed before funds were lost",
            "impact_classes": [
                "guardian_takeover_in_implementation_context",
                "malicious_upgrade_path",
                "potential_bridge_fund_lock_or_denial_of_service",
            ],
        },
        "local_reproduction": {
            "status": runtime_status,
            "assertion_status": assertion_status,
            "evidence_status": assertion.get("evidence_status"),
            "predicate": assertion.get("predicate"),
            "measured_delta": assertion.get("measured_delta"),
            "final_status": final_report.get("final_status"),
            "runtime_ready_count": final_report.get("runtime_ready_count"),
            "source_truth_verified_count": final_report.get("source_truth_verified_count"),
            "no_broadcast": bool(runtime.get("no_broadcast", True)),
            "fork_block_number": 13_818_843,
        },
        "current_live_risk": {
            "status": "not_claimed",
            "reason": (
                "Wormhole publicly fixed the uninitialized implementation. This run uses a historical fork block "
                "and does not perform current-state verification of the live proxy, implementation and guardian state."
            ),
            "required_to_upgrade_to_live_severity": [
                "current implementation slot and code hash",
                "current implementation initializer state",
                "current guardian set and upgrade governance state",
                "proof that the same direct implementation initialize path is still callable",
            ],
        },
        "source_truth": {
            "status": source_truth.get("status"),
            "verified_count": source_truth.get("source_truth_verified_count"),
            "evidence_kinds": sorted({str(item.get("evidence_kind")) for item in source_truth.get("reviews") or []}),
        },
        "external_context": {
            "status": "public_historical_context",
            "sources": [
                {
                    "name": "Immunefi Wormhole uninitialized proxy bugfix review",
                    "url": "https://immunefi.com/blog/bug-fix-reviews/wormhole-uninitialized-proxy-bugfix-review/",
                },
                {
                    "name": "Immunefi Wormhole uninitialized PoC repository",
                    "url": "https://github.com/immunefi-team/wormhole-uninitialized",
                },
            ],
        },
        "next_steps": [
            "Keep this as historical reproduced critical unless current exploitability is independently revalidated.",
            "Use this runner as a regression pattern for implementation-context initializer bugs.",
            "Move Nomad to a separate bridge root/proof mapper; do not reuse this Wormhole VM runner for Nomad.",
        ],
    }


def _generic_sc01_impact_review(
    *,
    review_id: str,
    run_id: str,
    target_id: str,
    target: dict[str, Any],
    final_report: dict[str, Any],
    assertion: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "completed",
        "impact_review_id": review_id,
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or final_report.get("chain") or ""),
        "address": str(target.get("address") or final_report.get("address") or ""),
        "bug_class": "sc01_access_control",
        "summary": {
            "verdict": "impact_not_classified",
            "severity_posture": "do_not_claim_severity_without_threat_model_and_current_state",
            "reasoning": "No project-specific impact mapper exists for this target.",
        },
        "historical_impact": {"severity": "unclassified"},
        "local_reproduction": {
            "status": runtime.get("status"),
            "assertion_status": assertion.get("status"),
            "predicate": assertion.get("predicate"),
            "measured_delta": assertion.get("measured_delta"),
            "no_broadcast": bool(runtime.get("no_broadcast", True)),
        },
        "current_live_risk": {
            "status": "not_claimed",
            "reason": "Generic SC01 impact review does not establish current live exploitability.",
        },
        "next_steps": ["Add a project-specific impact mapper before discussing severity."],
    }


def _nomad_impact_review(
    *,
    review_id: str,
    run_id: str,
    target_id: str,
    target: dict[str, Any],
    final_report: dict[str, Any],
    assertion: dict[str, Any],
    runtime: dict[str, Any],
    source_truth: dict[str, Any],
) -> dict[str, Any]:
    runtime_status = str(runtime.get("status") or final_report.get("runtime_status") or "")
    assertion_status = str(assertion.get("status") or "")
    reproduced = runtime_status == "runtime_completed" and assertion_status == "passed"
    return {
        "status": "completed",
        "impact_review_id": review_id,
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or final_report.get("chain") or "eth"),
        "address": str(target.get("address") or final_report.get("address") or NOMAD_REPLICA_PROXY),
        "bug_class": "nomad_bridge_root_proof_message_authentication_bypass",
        "summary": {
            "verdict": "historical_reproduced_critical" if reproduced else "historical_context_runtime_not_reproduced",
            "severity_posture": "critical_historical_do_not_claim_live_without_current_state_review",
            "reasoning": (
                "The local historical fork replay proves that Nomad Replica accepted and processed a forged "
                "unproven message through the root/proof validation path. Public Nomad and incident-analysis "
                "reports describe this as the bridge message-authentication failure that enabled the 2022 drain. "
                "This artifact does not claim current live exploitability."
            ),
        },
        "historical_impact": {
            "severity": "critical_historical",
            "affected_system": "Nomad Replica / bridge message authentication",
            "reported_loss_context": "public reports describe roughly $190M drained in August 2022",
            "impact_classes": [
                "forged_cross_chain_message_execution",
                "bridge_router_authentication_bypass",
                "token_bridge_drain_historical",
            ],
        },
        "local_reproduction": {
            "status": runtime_status,
            "assertion_status": assertion_status,
            "evidence_status": assertion.get("evidence_status"),
            "predicate": assertion.get("predicate"),
            "measured_delta": assertion.get("measured_delta"),
            "final_status": final_report.get("final_status"),
            "runtime_ready_count": final_report.get("runtime_ready_count"),
            "source_truth_verified_count": final_report.get("source_truth_verified_count"),
            "no_broadcast": bool(runtime.get("no_broadcast", True)),
            "fork_block_number": 15_259_100,
        },
        "current_live_risk": {
            "status": "not_claimed",
            "reason": (
                "The run uses a pinned historical fork and the proxy source currently resolves to a fixed "
                "implementation. Current live severity would require a fresh implementation, root-state and "
                "message-authentication review."
            ),
            "required_to_upgrade_to_live_severity": [
                "current Replica implementation slot and code hash",
                "current acceptableRoot/default root behavior",
                "current message/root state for bridge deployments",
                "proof that a forged message still reaches an asset-moving recipient",
            ],
        },
        "source_truth": {
            "status": source_truth.get("status"),
            "verified_count": source_truth.get("source_truth_verified_count"),
            "evidence_kinds": sorted({str(item.get("evidence_kind")) for item in source_truth.get("reviews") or []}),
        },
        "external_context": {
            "status": "public_historical_context",
            "sources": [
                {
                    "name": "Nomad bridge hack root cause analysis",
                    "url": "https://medium.com/nomad-xyz-blog/nomad-bridge-hack-root-cause-analysis-875ad2e5aacd",
                },
                {
                    "name": "BlockSec Nomad unchecked mapping analysis",
                    "url": "https://blocksec.com/blog/how-unchecked-mapping-makes-200-M-losses-of-nomad-bridge",
                },
                {
                    "name": "Coinbase Nomad incident analysis",
                    "url": "https://www.coinbase.com/blog/nomad-bridge-incident-analysis",
                },
            ],
        },
        "next_steps": [
            "Keep this as historical reproduced critical unless current exploitability is independently revalidated.",
            "Use this mapper as a regression pattern for bridge root/proof and default mapping authentication failures.",
            "Build the next bridge mapper around proof/root/processed-message readers, not initializer heuristics.",
        ],
    }


def _read_json(store: ArtifactStore, target_id: str, phase_id: str, name: str) -> dict[str, Any]:
    payload = store.read_artifact(store.uri(target_id, phase_id, name))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _is_audius_proxy(address: str, source_truth: dict[str, Any]) -> bool:
    if address.lower() == AUDIUS_GOVERNANCE_PROXY:
        return True
    return any(
        item.get("evidence_kind") == "proxy_storage_collision_reinitializer"
        for item in source_truth.get("reviews") or []
    )


def _is_wormhole_proxy(address: str, source_truth: dict[str, Any]) -> bool:
    if address.lower() == WORMHOLE_PROXY:
        return True
    return any(
        item.get("evidence_kind") == "wormhole_uninitialized_implementation"
        for item in source_truth.get("reviews") or []
    )


def _is_nomad_replica(address: str, source_truth: dict[str, Any]) -> bool:
    if address.lower() == NOMAD_REPLICA_PROXY:
        return True
    return any(
        item.get("evidence_kind") == "nomad_root_proof_message_auth_bypass"
        for item in source_truth.get("reviews") or []
    )
