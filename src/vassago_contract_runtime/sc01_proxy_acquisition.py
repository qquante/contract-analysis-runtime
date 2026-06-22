"""Source-backed proxy/upgrade thesis acquisition.

This module creates routing candidates from ABI/source/proxy context only. It
does not verify any vulnerability and does not use historical labels, case ids
or addresses.
"""

from __future__ import annotations

import re
from typing import Any


def build_proxy_upgrade_candidates(
    *,
    target_id: str,
    chain: str,
    address: str,
    function_index: dict[str, Any],
    source_manifest: dict[str, Any],
    access_surface: dict[str, Any],
) -> list[dict[str, Any]]:
    signals = _signals(function_index, source_manifest, access_surface)
    candidates = []
    if _should_queue_initializer(signals):
        candidates.append(
            _candidate(
                target_id=target_id,
                chain=chain,
                address=address,
                thesis_id="uninitialized_implementation_proxy",
                matched_motifs=signals["initializer_motifs"],
                matched_functions=signals["initializer_functions"],
                evidence_refs=signals["initializer_refs"],
            )
        )
    if _should_queue_uups(signals):
        candidates.append(
            _candidate(
                target_id=target_id,
                chain=chain,
                address=address,
                thesis_id="uups_weak_auth",
                matched_motifs=signals["upgrade_motifs"],
                matched_functions=signals["upgrade_functions"],
                evidence_refs=signals["upgrade_refs"],
            )
        )
    if _should_queue_role_admin(signals):
        candidates.append(
            _candidate(
                target_id=target_id,
                chain=chain,
                address=address,
                thesis_id="role_admin_escalation",
                matched_motifs=signals["role_motifs"],
                matched_functions=signals["role_functions"],
                evidence_refs=signals["role_refs"],
            )
        )
    return candidates


def _candidate(
    *,
    target_id: str,
    chain: str,
    address: str,
    thesis_id: str,
    matched_motifs: list[str],
    matched_functions: list[str],
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "candidate_id": f"TC-{target_id[3:]}-{thesis_id}",
        "target_id": target_id,
        "chain": chain,
        "address": address,
        "thesis_id": thesis_id,
        "corpus_id": f"sc01-dynamic-{thesis_id}",
        "bug_family": "access_control",
        "status": "candidate_only",
        "matched_motifs": sorted(set(matched_motifs)),
        "matched_functions": sorted(set(matched_functions)),
        "evidence_refs": sorted(set(evidence_refs)),
        "blockers": ["source_truth_not_run", "onchain_state_not_read", "proof_pieces_not_built"],
        "acquisition_source": "source_abi_proxy_context",
        "warning": "Routing hint only. Source-truth must validate or reject this candidate.",
    }


def _signals(
    function_index: dict[str, Any],
    source_manifest: dict[str, Any],
    access_surface: dict[str, Any],
) -> dict[str, list[str] | bool]:
    functions = _functions(function_index)
    source = _source_text(source_manifest)
    proxy_context = dict(source_manifest.get("proxy_context") or {})
    is_proxy = _is_proxy_context(proxy_context, source)
    has_related_impl = _has_related_implementation(source_manifest)
    initializer_functions = _matching_functions(functions, _is_initializer_name)
    upgrade_functions = _matching_functions(functions, _is_upgrade_name)
    role_functions = _matching_functions(functions, _is_role_admin_name)
    source_lower = source.lower()
    proxy_refs = _proxy_refs(proxy_context, source)
    initializer_refs = _refs_for_functions(access_surface, initializer_functions)
    upgrade_refs = _refs_for_functions(access_surface, upgrade_functions)
    role_refs = _refs_for_functions(access_surface, role_functions)
    if has_related_impl:
        proxy_refs.append("source-manifest:related implementation source")
    if is_proxy:
        proxy_refs.append("source-manifest:proxy context")
    if "_authorizeupgrade" in source_lower:
        upgrade_refs.append("source-manifest:_authorizeUpgrade")
    if "eip1967" in source_lower or "implementation_slot" in source_lower:
        upgrade_refs.append("source-manifest:EIP-1967 implementation slot")
    if "transparentupgradeableproxy" in source_lower or "ifadmin" in source_lower:
        upgrade_refs.append("source-manifest:transparent proxy admin path")
    if "getroleadmin" in source_lower:
        role_refs.append("source-manifest:getRoleAdmin")
    if "hasrole" in source_lower:
        role_refs.append("source-manifest:hasRole")
    return {
        "is_proxy": is_proxy,
        "has_related_impl": has_related_impl,
        "initializer_functions": initializer_functions,
        "initializer_motifs": _initializer_motifs(source_lower, initializer_functions, is_proxy, has_related_impl),
        "initializer_refs": sorted(set(initializer_refs + proxy_refs)),
        "upgrade_functions": upgrade_functions,
        "upgrade_motifs": _upgrade_motifs(source_lower, upgrade_functions, is_proxy),
        "upgrade_refs": sorted(set(upgrade_refs + proxy_refs)),
        "role_functions": role_functions,
        "role_motifs": _role_motifs(source_lower, role_functions),
        "role_refs": sorted(set(role_refs)),
    }


def _should_queue_initializer(signals: dict[str, Any]) -> bool:
    return bool(signals["initializer_functions"]) and (bool(signals["is_proxy"]) or bool(signals["has_related_impl"]))


def _should_queue_uups(signals: dict[str, Any]) -> bool:
    if not signals["upgrade_functions"]:
        return False
    motifs = set(signals["upgrade_motifs"])
    return bool({"upgradeTo", "upgradeToAndCall"} & motifs) and bool(
        {"_authorizeUpgrade", "EIP-1967", "TransparentUpgradeableProxy", "proxy_context"} & motifs
    )


def _should_queue_role_admin(signals: dict[str, Any]) -> bool:
    motifs = set(signals["role_motifs"])
    return bool(signals["role_functions"]) and bool({"hasRole", "getRoleAdmin", "grantRole"} & motifs)


def _functions(function_index: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in function_index.get("functions", []) if isinstance(item, dict)]


def _matching_functions(functions: list[dict[str, Any]], predicate: object) -> list[str]:
    matches = []
    for function in functions:
        name = str(function.get("name") or "")
        if callable(predicate) and predicate(name):
            matches.append(_signature(function))
    return sorted({item for item in matches if item})


def _signature(function: dict[str, Any]) -> str:
    name = str(function.get("name") or "")
    inputs = ",".join(str(item.get("type") or "") for item in function.get("inputs") or [])
    return f"{name}({inputs})"


def _is_initializer_name(name: str) -> bool:
    lowered = name.lower()
    return lowered == "initialize" or lowered.startswith("reinitialize") or lowered == "proxyinitialize"


def _is_upgrade_name(name: str) -> bool:
    return name in {"upgradeTo", "upgradeToAndCall"} or "upgrade" in name.lower()


def _is_role_admin_name(name: str) -> bool:
    return name in {"grantRole", "revokeRole", "renounceRole", "hasRole", "getRoleAdmin"} or name == "_setRoleAdmin"


def _source_text(source_manifest: dict[str, Any]) -> str:
    values = [str(value) for value in (source_manifest.get("source_files") or {}).values()]
    related = source_manifest.get("related_sources")
    if isinstance(related, dict):
        for item in related.values():
            if isinstance(item, dict):
                values.extend(str(value) for value in (item.get("source_files") or {}).values())
    return "\n".join(values)


def _has_related_implementation(source_manifest: dict[str, Any]) -> bool:
    related = source_manifest.get("related_sources")
    if not isinstance(related, dict):
        return False
    implementation = related.get("implementation")
    return isinstance(implementation, dict) and implementation.get("status") == "resolved"


def _is_proxy_context(proxy_context: dict[str, Any], source: str) -> bool:
    implementation = str(proxy_context.get("implementation") or "").lower()
    proxy_flag = str(proxy_context.get("proxy") or "").lower()
    return (
        proxy_flag in {"1", "true", "yes"}
        or implementation not in {"", "0x", "0x0000000000000000000000000000000000000000"}
        or "delegatecall" in source
        or "IMPLEMENTATION_SLOT" in source
        or "TransparentUpgradeableProxy" in source
    )


def _proxy_refs(proxy_context: dict[str, Any], source: str) -> list[str]:
    refs = []
    if proxy_context:
        refs.append("source-manifest:proxy_context")
    if "TransparentUpgradeableProxy" in source:
        refs.append("source-manifest:TransparentUpgradeableProxy")
    if "IMPLEMENTATION_SLOT" in source or "eip1967" in source.lower():
        refs.append("source-manifest:EIP-1967")
    if "delegatecall" in source:
        refs.append("source-manifest:delegatecall")
    return refs


def _refs_for_functions(access_surface: dict[str, Any], signatures: list[str]) -> list[str]:
    wanted = {str(item) for item in signatures}
    refs = []
    for function in access_surface.get("functions", []):
        signature = str(function.get("signature") or "")
        if signature not in wanted:
            continue
        source = str(function.get("extraction_source") or "abi")
        refs.append(f"access-surface:{signature}:{source}")
        if function.get("source_status") == "found":
            refs.append(f"access-surface:{signature}:source_found")
    return refs


def _initializer_motifs(source_lower: str, functions: list[str], is_proxy: bool, has_related_impl: bool) -> list[str]:
    motifs = [str(item).split("(")[0] for item in functions]
    if "initializer" in source_lower:
        motifs.append("initializer")
    if "_disableinitializers" in source_lower:
        motifs.append("_disableInitializers")
    if is_proxy:
        motifs.append("proxy_context")
    if has_related_impl:
        motifs.append("related_implementation")
    return sorted(set(motifs))


def _upgrade_motifs(source_lower: str, functions: list[str], is_proxy: bool) -> list[str]:
    motifs = [str(item).split("(")[0] for item in functions]
    if "_authorizeupgrade" in source_lower:
        motifs.append("_authorizeUpgrade")
    if "onlyproxy" in source_lower:
        motifs.append("onlyProxy")
    if "eip1967" in source_lower or "implementation_slot" in source_lower:
        motifs.append("EIP-1967")
    if "transparentupgradeableproxy" in source_lower or "ifadmin" in source_lower:
        motifs.append("TransparentUpgradeableProxy")
    if is_proxy:
        motifs.append("proxy_context")
    return sorted(set(motifs))


def _role_motifs(source_lower: str, functions: list[str]) -> list[str]:
    motifs = [str(item).split("(")[0] for item in functions]
    for marker in ("hasRole", "getRoleAdmin", "grantRole", "revokeRole", "DEFAULT_ADMIN_ROLE"):
        if marker.lower() in source_lower:
            motifs.append(marker)
    if re.search(r"\b_setRoleAdmin\s*\(", source_lower, flags=re.IGNORECASE):
        motifs.append("_setRoleAdmin")
    return sorted(set(motifs))
