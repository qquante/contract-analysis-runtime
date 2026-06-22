"""Read-only SC01 current-state reviews.

Current-state review is deliberately separate from historical reproduction.
It can reject or flag live-risk prerequisites, but it does not execute
transactions and it does not promote historical fork evidence.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.request import Request, urlopen

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.design_runtime.manifest import load_run_manifest
from vassago_contract_runtime.design_runtime.models import short_hash
from vassago_contract_runtime.sc01_nomad import NOMAD_REPLICA_PROXY


CURRENT_STATE_PHASE_ID = "12_current_state_review"
CURRENT_STATE_JSON = "sc01-current-state-review.json"
CURRENT_STATE_MD = "sc01-current-state-review.md"

LOCAL_DOMAIN_SELECTOR = "8d3638f4"
ACCEPTABLE_ROOT_SELECTOR = "a3f81d68"
CONFIRM_AT_SELECTOR = "71bfb7b8"
MESSAGES_SELECTOR = "2bbd59ca"
ZERO32_HEX = "0x" + "00" * 32


class RpcLike(Protocol):
    def request(self, method: str, params: list[Any]) -> Any:
        """Perform one read-only JSON-RPC request."""


class JsonRpcClient:
    def __init__(self, rpc_url: str, *, timeout_seconds: int = 20) -> None:
        self.rpc_url = rpc_url
        self.timeout_seconds = timeout_seconds
        self._request_id = 0

    def request(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        request = Request(
            self.rpc_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        decoded = json.loads(raw)
        if decoded.get("error"):
            raise ValueError(f"RPC {method} failed: {decoded['error']}")
        return decoded.get("result")


def write_sc01_current_state_review(
    run_dir: str | Path,
    target_id: str,
    *,
    rpc_url: str | None = None,
) -> dict[str, Any]:
    manifest = load_run_manifest(run_dir)
    store = ArtifactStore(run_dir, manifest["run_id"])
    source_manifest = _read_json(store, target_id, "01_dossier", "source-manifest.json")
    source_truth = _read_json(store, target_id, "05_source_truth", "sc01-source-truth.json")
    review = build_nomad_current_state_review(
        source_manifest,
        source_truth=source_truth,
        rpc=JsonRpcClient(_rpc_url(rpc_url)),
        run_id=str(manifest["run_id"]),
        target_id=target_id,
    )
    json_artifact = store.write_json_artifact(target_id, CURRENT_STATE_PHASE_ID, CURRENT_STATE_JSON, review)
    md_artifact = store.write_text_artifact(target_id, CURRENT_STATE_PHASE_ID, CURRENT_STATE_MD, render_current_state_markdown(review))
    return {
        "status": review["status"],
        "run_id": manifest["run_id"],
        "target_id": target_id,
        "review_id": review["review_id"],
        "artifacts": [json_artifact, md_artifact],
        "summary": review["summary"],
    }


def build_nomad_current_state_review(
    source_manifest: dict[str, Any],
    *,
    source_truth: dict[str, Any] | None = None,
    rpc: RpcLike,
    run_id: str = "RUN-current-state",
    target_id: str = "CT-current-state",
) -> dict[str, Any]:
    target = dict(source_manifest.get("target") or {})
    proxy_address = str(target.get("address") or NOMAD_REPLICA_PROXY).lower()
    implementation = _implementation_address(source_manifest)
    source_review = _nomad_source_review(source_manifest)
    block_number = int(str(rpc.request("eth_blockNumber", [])), 16)
    proxy_code = str(rpc.request("eth_getCode", [proxy_address, "latest"]))
    implementation_code = str(rpc.request("eth_getCode", [implementation, "latest"])) if implementation else "0x"
    local_domain = _uint256(_eth_call(rpc, proxy_address, LOCAL_DOMAIN_SELECTOR))
    acceptable_zero = bool(_uint256(_eth_call(rpc, proxy_address, ACCEPTABLE_ROOT_SELECTOR, _word(ZERO32_HEX))))
    confirm_zero = _uint256(_eth_call(rpc, proxy_address, CONFIRM_AT_SELECTOR, _word(ZERO32_HEX)))
    message = _nomad_probe_message(local_domain)
    forged_hash = _keccak_hex(message)
    message_root = _word(_eth_call(rpc, proxy_address, MESSAGES_SELECTOR, _word(forged_hash)))
    gate = _live_gate(acceptable_zero, message_root, source_review)
    return {
        "status": "completed",
        "review_id": f"CSR-{short_hash(f'{run_id}|{target_id}|{proxy_address}|nomad')}",
        "run_id": run_id,
        "target_id": target_id,
        "chain": str(target.get("chain") or "eth"),
        "address": proxy_address,
        "protocol": "nomad_replica",
        "source_truth_evidence": _source_truth_evidence(source_truth or {}),
        "current_block_number": block_number,
        "current_implementation": {
            "source": "explorer_proxy_context",
            "address": implementation,
            "code_present": implementation_code != "0x",
            "code_sha256": _sha256_hex(implementation_code),
        },
        "proxy_code": {
            "code_present": proxy_code != "0x",
            "code_sha256": _sha256_hex(proxy_code),
        },
        "source_review": source_review,
        "read_only_calls": {
            "localDomain()": local_domain,
            "acceptableRoot(bytes32(0))": acceptable_zero,
            "confirmAt(bytes32(0))": confirm_zero,
            "forged_message_hash": forged_hash,
            "messages(forged_message_hash)": message_root,
        },
        "asset_moving_recipient_review": {
            "status": "not_required_after_root_gate_rejection" if gate["default_root_path_rejected"] else "not_performed",
            "reason": (
                "The current default-root gate rejects the forged unproven message before recipient execution."
                if gate["default_root_path_rejected"]
                else "A live asset-moving recipient proof would require a separate scoped bridge recipient review."
            ),
        },
        "summary": {
            "verdict": gate["verdict"],
            "current_live_risk": gate["current_live_risk"],
            "reasoning": gate["reasoning"],
        },
        "policy": {
            "read_only": True,
            "no_broadcast": True,
            "no_private_key": True,
            "historical_reproduction_not_promoted": True,
        },
        "rpc": {"url": "<redacted>"},
    }


def render_current_state_markdown(review: dict[str, Any]) -> str:
    summary = dict(review.get("summary") or {})
    calls = dict(review.get("read_only_calls") or {})
    implementation = dict(review.get("current_implementation") or {})
    lines = [
        "# SC01 Current-State Review",
        "",
        f"- Protocol: `{review.get('protocol')}`",
        f"- Target: `{review.get('chain')}:{review.get('address')}`",
        f"- Block: `{review.get('current_block_number')}`",
        f"- Implementation: `{implementation.get('address')}`",
        f"- Verdict: `{summary.get('verdict')}`",
        f"- Current live risk: `{summary.get('current_live_risk')}`",
        "",
        "## Read-Only Calls",
        "",
    ]
    for key, value in calls.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Reasoning",
            "",
            str(summary.get("reasoning") or ""),
            "",
            "This review is read-only. It does not broadcast, sign, or promote historical reproduction.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(store: ArtifactStore, target_id: str, phase_id: str, name: str) -> dict[str, Any]:
    payload = store.read_artifact(store.uri(target_id, phase_id, name))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON artifact for {phase_id}/{name}")
    return payload


def _rpc_url(value: str | None) -> str:
    rpc = (
        value
        or os.environ.get("VASSAGO_CURRENT_STATE_RPC_URL")
        or os.environ.get("ETH_MAINNET_RPC_URL")
        or os.environ.get("ALCHEMY_ETH_MAINNET_URL")
        or os.environ.get("VASSAGO_FORK_RPC_URL")
        or os.environ.get("VASSAGO_FORK_RPC_FALLBACK_ETH_URL")
    )
    if not rpc:
        raise ValueError("RPC URL missing. Set VASSAGO_CURRENT_STATE_RPC_URL or VASSAGO_FORK_RPC_FALLBACK_ETH_URL.")
    return rpc


def _eth_call(rpc: RpcLike, to: str, selector: str, encoded_args: str = "") -> str:
    result = str(rpc.request("eth_call", [{"to": to, "data": "0x" + selector + encoded_args.removeprefix("0x")}, "latest"]))
    if not result.startswith("0x"):
        raise ValueError(f"Invalid eth_call result: {result!r}")
    return result


def _word(value: str) -> str:
    return "0x" + value.removeprefix("0x").rjust(64, "0")[-64:]


def _uint256(value: str) -> int:
    return int(value.removeprefix("0x")[-64:] or "0", 16)


def _implementation_address(source_manifest: dict[str, Any]) -> str:
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    implementation = str(proxy_context.get("implementation") or "").strip().lower()
    if implementation.startswith("0x") and len(implementation) == 42:
        return implementation
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        item = related.get("implementation")
        if isinstance(item, dict):
            target = dict(item.get("target") or {})
            address = str(target.get("address") or "").strip().lower()
            if address.startswith("0x") and len(address) == 42:
                return address
    return ""


def _nomad_source_review(source_manifest: dict[str, Any]) -> dict[str, Any]:
    text = _source_text(source_manifest)
    process_uses_default_root_path = "acceptableRoot(messages[_messageHash])" in text or "acceptableRoot(messages[messageHash])" in text
    acceptable_root_rejects_none = "LEGACY_STATUS_NONE" in text and "return false" in _function_window(text, "function acceptableRoot")
    return {
        "process_uses_acceptable_root_messages": process_uses_default_root_path,
        "acceptable_root_rejects_legacy_status_none": acceptable_root_rejects_none,
        "current_source_fixed_signal": bool(process_uses_default_root_path and acceptable_root_rejects_none),
    }


def _source_text(source_manifest: dict[str, Any]) -> str:
    values = [str(value) for value in (source_manifest.get("source_files") or {}).values()]
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict):
                values.extend(str(value) for value in (item.get("source_files") or {}).values())
    return "\n".join(values)


def _function_window(text: str, marker: str) -> str:
    idx = text.find(marker)
    if idx < 0:
        return ""
    return text[idx : idx + 1200]


def _source_truth_evidence(source_truth: dict[str, Any]) -> dict[str, Any]:
    kinds = sorted({str(item.get("evidence_kind")) for item in source_truth.get("reviews") or [] if item.get("evidence_kind")})
    return {
        "status": source_truth.get("status"),
        "source_truth_verified_count": source_truth.get("source_truth_verified_count"),
        "evidence_kinds": kinds,
    }


def _live_gate(acceptable_zero: bool, message_root: str, source_review: dict[str, Any]) -> dict[str, Any]:
    default_message = int(message_root, 16) == 0
    current_fixed = bool(source_review.get("current_source_fixed_signal"))
    if default_message and not acceptable_zero:
        return {
            "default_root_path_rejected": True,
            "verdict": "current_default_root_path_rejected",
            "current_live_risk": "not_indicated_by_current_default_root_probe",
            "reasoning": (
                "Current source still routes process(bytes) through acceptableRoot(messages[messageHash]), but "
                "acceptableRoot(bytes32(0)) returns false for the current deployment. The forged unproven message "
                "therefore cannot pass the historical default-root path in this read-only probe."
            ),
        }
    if default_message and acceptable_zero and not current_fixed:
        return {
            "default_root_path_rejected": False,
            "verdict": "current_default_root_path_potentially_open",
            "current_live_risk": "needs_asset_recipient_runtime_review",
            "reasoning": (
                "The current default root was acceptable for an unproven forged message. This is not a final live "
                "claim; it requires an asset-moving recipient review and local fork runtime."
            ),
        }
    return {
        "default_root_path_rejected": False,
        "verdict": "current_state_inconclusive",
        "current_live_risk": "not_claimed",
        "reasoning": "The default-root probe did not produce a complete live exploitability proof.",
    }


def _nomad_probe_message(local_domain: int) -> bytes:
    body = b"vassago.nomad.current-state.probe"
    return b"".join(
        [
            int(1000).to_bytes(4, "big"),
            int("22" * 20, 16).to_bytes(32, "big"),
            int(7).to_bytes(4, "big"),
            int(local_domain).to_bytes(4, "big"),
            int("11" * 20, 16).to_bytes(32, "big"),
            body,
        ]
    )


def _keccak_hex(payload: bytes) -> str:
    try:
        from Crypto.Hash import keccak  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        raise ValueError("Keccak support is required for Nomad current-state review.") from exc
    digest = keccak.new(digest_bits=256)
    digest.update(payload)
    return "0x" + digest.hexdigest()


def _sha256_hex(value: str) -> str:
    raw = value.removeprefix("0x")
    try:
        return sha256(bytes.fromhex(raw)).hexdigest()
    except ValueError:
        return sha256(value.encode("utf-8")).hexdigest()
