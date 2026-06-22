"""Bridge current-path review for SC01.

This module identifies bridge-message paths that deserve current-state review.
It is intentionally read-only/static: it classifies endpoint/source validation,
processed-message replay, root/proof verification, escrow/supply delta and
recipient asset-moving paths without claiming live exploitability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.design_runtime.manifest import load_run_manifest
from vassago_contract_runtime.design_runtime.models import short_hash


BRIDGE_REVIEW_PHASE_ID = "12_current_state_review"
BRIDGE_REVIEW_JSON = "sc01-bridge-current-review.json"
BRIDGE_REVIEW_MD = "sc01-bridge-current-review.md"


def write_sc01_bridge_current_review(run_dir: str | Path, target_id: str) -> dict[str, Any]:
    manifest = load_run_manifest(run_dir)
    store = ArtifactStore(run_dir, manifest["run_id"])
    source_manifest = _read_json(store, target_id, "01_dossier", "source-manifest.json")
    source_truth = _read_optional_json(store, target_id, "05_source_truth", "sc01-source-truth.json")
    review = build_bridge_current_review(
        source_manifest,
        source_truth=source_truth,
        run_id=str(manifest["run_id"]),
        target_id=target_id,
    )
    json_artifact = store.write_json_artifact(target_id, BRIDGE_REVIEW_PHASE_ID, BRIDGE_REVIEW_JSON, review)
    md_artifact = store.write_text_artifact(target_id, BRIDGE_REVIEW_PHASE_ID, BRIDGE_REVIEW_MD, render_bridge_review_markdown(review))
    return {
        "status": review["status"],
        "run_id": manifest["run_id"],
        "target_id": target_id,
        "review_id": review["review_id"],
        "artifacts": [json_artifact, md_artifact],
        "summary": review["summary"],
    }


def build_bridge_current_review(
    source_manifest: dict[str, Any],
    *,
    source_truth: dict[str, Any] | None = None,
    run_id: str = "RUN-bridge-review",
    target_id: str = "CT-bridge-review",
) -> dict[str, Any]:
    target = dict(source_manifest.get("target") or {})
    text = _source_text(source_manifest)
    abi = _effective_abi(source_manifest)
    protocols = _protocol_fingerprints(text, abi)
    paths = [
        _endpoint_source_path(text, abi, protocols),
        _processed_message_path(text, abi),
        _root_proof_path(text, abi),
        _escrow_supply_path(text, abi),
        _recipient_asset_path(text, abi, protocols),
    ]
    active = [item for item in paths if item["status"] != "not_detected"]
    ready = [item for item in active if item["status"] == "candidate_ready_for_state_review"]
    blocked = [item for item in active if item["status"].startswith("blocked")]
    review_seed = f"{run_id}|{target_id}|{target.get('address')}|bridge"
    return {
        "status": "completed",
        "review_id": f"BCR-{short_hash(review_seed)}",
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or "unknown"),
        "address": str(target.get("address") or "").lower(),
        "protocol_fingerprints": protocols,
        "path_reviews": paths,
        "summary": {
            "verdict": _verdict(active, ready),
            "current_live_risk": "not_claimed",
            "active_path_count": len(active),
            "ready_for_state_review_count": len(ready),
            "blocked_path_count": len(blocked),
        },
        "source_truth_evidence": _source_truth_evidence(source_truth or {}),
        "policy": {
            "read_only": True,
            "no_broadcast": True,
            "no_private_key": True,
            "does_not_execute_foundry": True,
            "does_not_promote_historical_reproduction": True,
        },
    }


def render_bridge_review_markdown(review: dict[str, Any]) -> str:
    summary = dict(review.get("summary") or {})
    lines = [
        "# SC01 Bridge Current-Path Review",
        "",
        f"- Target: `{review.get('chain')}:{review.get('address')}`",
        f"- Verdict: `{summary.get('verdict')}`",
        f"- Current live risk: `{summary.get('current_live_risk')}`",
        f"- Active paths: `{summary.get('active_path_count')}`",
        f"- Ready for state review: `{summary.get('ready_for_state_review_count')}`",
        "",
        "## Protocol Fingerprints",
        "",
    ]
    protocols = list(review.get("protocol_fingerprints") or [])
    lines.extend(f"- `{item['protocol']}` confidence `{item['confidence']}`: {', '.join(item['evidence_refs'])}" for item in protocols)
    if not protocols:
        lines.append("- none")
    lines.extend(["", "## Path Reviews", ""])
    for item in review.get("path_reviews") or []:
        lines.extend(
            [
                f"### `{item['path_id']}`",
                "",
                f"- status: `{item['status']}`",
                f"- hypothesis: {item['hypothesis']}",
                f"- next: `{item['next_required_review']}`",
                f"- evidence: {', '.join(item['evidence_refs']) or 'none'}",
                "",
            ]
        )
    lines.append("No transactions, private keys or broadcasts are used by this review.")
    lines.append("")
    return "\n".join(lines)


def _protocol_fingerprints(text: str, abi: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lower = text.lower()
    names = _abi_names(abi)
    protocols = []
    if {"lzreceive", "trustedremotelookup"} & names or "trustedremotelookup" in lower or "lzendpoint" in lower:
        protocols.append(
            _protocol(
                "layerzero_v1",
                _confidence(["lzreceive" in names, "trustedremotelookup" in lower, "lzendpoint" in lower]),
                [
                    "function:lzReceive" if "lzreceive" in names else "",
                    "source:trustedRemoteLookup" if "trustedremotelookup" in lower else "",
                    "source:lzEndpoint" if "lzendpoint" in lower else "",
                ],
            )
        )
    if "endpointv2" in lower or "oapp" in lower or "origin calldata" in lower or "srcEid".lower() in lower:
        protocols.append(_protocol("layerzero_v2", _confidence(["srcEid".lower() in lower, "origin calldata" in lower]), ["source:Origin/srcEid"]))
    if "iaxelargateway" in lower or "validatecontractcall" in lower or "axelarexecutable" in lower:
        protocols.append(_protocol("axelar_gmp", _confidence(["validatecontractcall" in lower, "iaxelargateway" in lower]), ["source:validateContractCall"]))
    has_hyperlane_mailbox = "imailbox" in lower or "mailbox.process" in lower or "mailbox" in lower
    has_hyperlane_handle = "function handle" in lower or "handle(" in lower
    if has_hyperlane_mailbox and (has_hyperlane_handle or "interchain security module" in lower):
        protocols.append(
            _protocol(
                "hyperlane",
                _confidence(["imailbox" in lower or "mailbox" in lower, has_hyperlane_handle]),
                ["source:handle/mailbox"],
            )
        )
    if "iwormholerelayer" in lower or "receivewormholemessages" in lower or "vaa" in lower:
        protocols.append(_protocol("wormhole", _confidence(["receivewormholemessages" in lower, "vaa" in lower]), ["source:wormhole"]))
    if "acceptableroot" in lower and "confirmat" in lower and "process(bytes" in lower:
        protocols.append(_protocol("nomad_replica", "high", ["source:acceptableRoot/confirmAt/process"]))
    return [item for item in protocols if item["confidence"] != "none"]


def _endpoint_source_path(text: str, abi: list[dict[str, Any]], protocols: list[dict[str, Any]]) -> dict[str, Any]:
    lower = text.lower()
    refs = []
    has_entry = any(name in _abi_names(abi) for name in {"lzreceive", "handle", "execute", "receivewormholemessages"}) or any(
        item["protocol"] in {"layerzero_v1", "layerzero_v2", "axelar_gmp", "hyperlane", "wormhole"} for item in protocols
    )
    checks = [
        ("msg.sender_endpoint", "msg.sender" in lower and ("endpoint" in lower or "mailbox" in lower or "gateway" in lower or "wormholerelayer" in lower)),
        ("trusted_remote", "trustedremote" in lower or "trustedsource" in lower or "trustedremotelookup" in lower),
        ("source_address_hash", "srcaddress" in lower and "keccak256" in lower),
        ("gateway_validate", "validatecontractcall" in lower),
        ("mailbox_or_ism", "ism" in lower or "interchainsecuritymodule" in lower or "mailbox" in lower),
    ]
    refs.extend(name for name, present in checks if present)
    if not has_entry:
        return _path("endpoint_source_validation", "not_detected", "No bridge receive entrypoint detected.", [], [], "none")
    if refs:
        return _path(
            "endpoint_source_validation",
            "candidate_ready_for_state_review",
            "Bridge receive path has source/endpoint validation signals; verify configured endpoint/peer state.",
            refs,
            ["read endpoint/mailbox/gateway address", "read trusted remote/source/peer mapping", "verify handler only accepts protocol caller"],
            "read_endpoint_and_peer_state",
        )
    return _path(
        "endpoint_source_validation",
        "blocked_missing_source_validation_signal",
        "Bridge receive entrypoint exists but no endpoint/source validation was found in source signals.",
        ["function:bridge_receive_entrypoint"],
        ["identify protocol actor", "verify whether entrypoint is internal-only or inherited guard exists"],
        "manual_source_truth_or_protocol_mapper",
    )


def _processed_message_path(text: str, abi: list[dict[str, Any]]) -> dict[str, Any]:
    lower = text.lower()
    signals = [item for item in ("processed", "executed", "consumed", "messageid", "nonce", "replay") if item in lower]
    if not signals:
        return _path("processed_message_replay", "not_detected", "No processed-message/replay signals detected.", [], [], "none")
    has_reader = any(name in _abi_names(abi) for name in {"processedmessages", "processed", "executed", "consumednonces", "failedmessages"})
    return _path(
        "processed_message_replay",
        "candidate_ready_for_state_review" if has_reader else "blocked_reader_missing",
        "Message replay protection signals exist; current-state needs processed/message-id reader and sample message id.",
        [f"source:{item}" for item in signals],
        ["read processed-message mapping", "derive message id", "check before/after replay predicate"],
        "read_processed_message_state" if has_reader else "discover_processed_reader",
    )


def _root_proof_path(text: str, abi: list[dict[str, Any]]) -> dict[str, Any]:
    lower = text.lower()
    signals = [item for item in ("merkleroot", "merkleproof", "proof", "root", "confirmat", "acceptableroot") if item in lower]
    if not signals:
        return _path("root_proof_verifier", "not_detected", "No root/proof verifier signals detected.", [], [], "none")
    names = _abi_names(abi)
    has_root_reader = bool({"acceptableroot", "confirmat", "root", "roots"} & names) or "acceptableroot" in lower
    return _path(
        "root_proof_verifier",
        "candidate_ready_for_state_review" if has_root_reader else "blocked_reader_missing",
        "Root/proof verifier exists; current-state must bind proof/root to exact message and reject defaults.",
        [f"source:{item}" for item in signals],
        ["read root/proof status", "derive message hash", "confirm default/zero root rejection", "verify proof is message-specific"],
        "read_root_proof_state" if has_root_reader else "discover_root_reader",
    )


def _escrow_supply_path(text: str, abi: list[dict[str, Any]]) -> dict[str, Any]:
    lower = text.lower()
    signals = [item for item in ("mint", "burn", "lock", "release", "escrow", "reserve", "liability", "totalsupply") if item in lower]
    if len(signals) < 2:
        return _path("escrow_supply_delta", "not_detected", "No bridge escrow/supply delta surface detected.", [], [], "none")
    names = _abi_names(abi)
    has_reader = bool({"totalsupply", "balanceof", "escrow", "liability", "reserve"} & names) or "balanceof" in lower
    return _path(
        "escrow_supply_delta",
        "candidate_ready_for_state_review" if has_reader else "blocked_reader_missing",
        "Asset-moving bridge path likely needs supply/escrow/liability invariant before runtime.",
        [f"source:{item}" for item in signals],
        ["read token/escrow balances", "read totalSupply or liability", "define before/after invariant"],
        "read_supply_escrow_state" if has_reader else "discover_supply_or_escrow_reader",
    )


def _recipient_asset_path(text: str, abi: list[dict[str, Any]], protocols: list[dict[str, Any]]) -> dict[str, Any]:
    lower = text.lower()
    has_recipient = any(name in _abi_names(abi) for name in {"handle", "process", "execute", "lzreceive", "receivewormholemessages"})
    moves_assets = any(token in lower for token in ("safetransfer", ".transfer(", "transferfrom", ".call{value", "mint(", "burn("))
    if not has_recipient and not moves_assets:
        return _path("recipient_asset_moving", "not_detected", "No recipient asset-moving path detected.", [], [], "none")
    if has_recipient and moves_assets:
        return _path(
            "recipient_asset_moving",
            "candidate_ready_for_state_review",
            "Bridge recipient appears to move assets; current-state needs concrete recipient and asset delta.",
            ["function:bridge_recipient", "source:asset_transfer_or_mint_burn"],
            ["identify recipient target", "read asset balance/supply before state", "define asset-moving delta"],
            "read_recipient_asset_delta",
        )
    return _path(
        "recipient_asset_moving",
        "blocked_asset_delta_missing",
        "Bridge recipient exists but no asset-moving delta was detected.",
        ["function:bridge_recipient"],
        ["map recipient body", "identify token/native transfer or state-changing effect"],
        "manual_recipient_effect_review",
    )


def _path(
    path_id: str,
    status: str,
    hypothesis: str,
    evidence_refs: list[str],
    required_state: list[str],
    next_required_review: str,
) -> dict[str, Any]:
    return {
        "path_id": path_id,
        "status": status,
        "hypothesis": hypothesis,
        "evidence_refs": sorted(set(item for item in evidence_refs if item)),
        "required_state": required_state,
        "next_required_review": next_required_review,
        "evidence_status": "static_only",
    }


def _protocol(protocol: str, confidence: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "protocol": protocol,
        "confidence": confidence,
        "evidence_refs": sorted(set(item for item in evidence_refs if item)),
    }


def _confidence(items: list[bool]) -> str:
    count = sum(1 for item in items if item)
    if count >= 2:
        return "high"
    if count == 1:
        return "medium"
    return "none"


def _verdict(active: list[dict[str, Any]], ready: list[dict[str, Any]]) -> str:
    if ready:
        return "bridge_paths_ready_for_current_state_review"
    if active:
        return "bridge_paths_detected_but_blocked"
    return "no_bridge_path_detected"


def _source_truth_evidence(source_truth: dict[str, Any]) -> dict[str, Any]:
    kinds = sorted({str(item.get("evidence_kind")) for item in source_truth.get("reviews") or [] if item.get("evidence_kind")})
    return {
        "status": source_truth.get("status"),
        "source_truth_verified_count": source_truth.get("source_truth_verified_count"),
        "evidence_kinds": kinds,
    }


def _read_json(store: ArtifactStore, target_id: str, phase_id: str, name: str) -> dict[str, Any]:
    payload = store.read_artifact(store.uri(target_id, phase_id, name))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _read_optional_json(store: ArtifactStore, target_id: str, phase_id: str, name: str) -> dict[str, Any]:
    try:
        return _read_json(store, target_id, phase_id, name)
    except Exception:
        return {}


def _source_text(source_manifest: dict[str, Any]) -> str:
    values = [str(value) for value in (source_manifest.get("source_files") or {}).values()]
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict):
                values.extend(str(value) for value in (item.get("source_files") or {}).values())
    return "\n".join(values)


def _effective_abi(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    abi = list(source_manifest.get("abi") or [])
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict):
                abi.extend(list(item.get("abi") or []))
    return abi


def _abi_names(abi: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("name") or "").lower() for item in abi if item.get("type") == "function"}
