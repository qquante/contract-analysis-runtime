"""Explorer adapter contracts.

The runtime keeps Explorer calls behind this interface so phases can be tested
with fixture/local adapters before any chain API is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from vassago_contract_runtime.contracts import ContractTargetRef


@dataclass(frozen=True)
class ExplorerContractContext:
    status: str
    provider: str
    target: ContractTargetRef
    abi: list[dict[str, Any]] | None = None
    source_files: dict[str, str] = field(default_factory=dict)
    creation: dict[str, Any] = field(default_factory=dict)
    proxy_context: dict[str, Any] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target": self.target.to_json(),
            "abi": self.abi,
            "source_files": dict(self.source_files),
            "creation": dict(self.creation),
            "proxy_context": dict(self.proxy_context),
            "labels": list(self.labels),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


@dataclass(frozen=True)
class ExplorerLogsResult:
    status: str
    provider: str
    target: ContractTargetRef
    from_block: int
    to_block: int
    logs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target": self.target.to_json(),
            "from_block": self.from_block,
            "to_block": self.to_block,
            "logs": list(self.logs),
            "log_count": len(self.logs),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class ExplorerAdapter(Protocol):
    def get_contract_context(self, target: ContractTargetRef) -> ExplorerContractContext:
        """Return read-only Explorer context for one target."""

    def get_logs(
        self,
        target: ContractTargetRef,
        *,
        from_block: int,
        to_block: int,
        topics: dict[str, str] | None = None,
    ) -> ExplorerLogsResult:
        """Return read-only event logs for one target."""


class NullExplorerAdapter:
    """Offline Explorer adapter used until a provider implementation is wired."""

    def get_contract_context(self, target: ContractTargetRef) -> ExplorerContractContext:
        return ExplorerContractContext(
            status="unresolved",
            provider="null",
            target=target,
            metadata={
                "evidence_status": "static_only",
                "note": "No Explorer adapter configured. No network call was made.",
            },
            error={"code": "explorer_adapter_not_configured", "message": "No Explorer provider is configured."},
        )

    def get_logs(
        self,
        target: ContractTargetRef,
        *,
        from_block: int,
        to_block: int,
        topics: dict[str, str] | None = None,
    ) -> ExplorerLogsResult:
        return ExplorerLogsResult(
            status="unresolved",
            provider="null",
            target=target,
            from_block=from_block,
            to_block=to_block,
            metadata={
                "evidence_status": "static_only",
                "note": "No Explorer adapter configured. No network call was made.",
            },
            error={"code": "explorer_adapter_not_configured", "message": "No Explorer provider is configured."},
        )


class EtherscanV2ExplorerAdapter:
    """Read-only Etherscan V2 adapter with optional filesystem cache."""

    base_url = "https://api.etherscan.io/v2/api"

    def __init__(
        self,
        api_token: str | None = None,
        *,
        cache_dir: str | Path | None = None,
        min_interval_seconds: float = 0.2,
        transport: Any | None = None,
    ) -> None:
        self.api_token = api_token or os.environ.get("ETHERSCAN_API_KEY")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.min_interval_seconds = min_interval_seconds
        self.transport = transport or _default_transport
        self._last_request_at = 0.0

    def get_contract_context(self, target: ContractTargetRef) -> ExplorerContractContext:
        source = self._api(
            target,
            {
                "module": "contract",
                "action": "getsourcecode",
                "address": target.address,
            },
        )
        if source.get("status") != "1":
            return ExplorerContractContext(
                status="unresolved",
                provider="etherscan_v2",
                target=target,
                error={
                    "code": str(source.get("error_code") or "etherscan_getsourcecode_failed"),
                    "message": str(source.get("message") or source.get("result")),
                },
                metadata=_metadata(source),
            )
        record = _first_result(source)
        abi = _parse_abi(record.get("ABI"))
        if abi is None:
            abi_response = self._api(
                target,
                {
                    "module": "contract",
                    "action": "getabi",
                    "address": target.address,
                },
            )
            abi = _parse_abi(abi_response.get("result"))
        return ExplorerContractContext(
            status="resolved",
            provider="etherscan_v2",
            target=target,
            abi=abi,
            source_files=_parse_source_files(record),
            proxy_context={
                "proxy": str(record.get("Proxy") or "0"),
                "implementation": str(record.get("Implementation") or ""),
            },
            metadata={
                **_metadata(source),
                "contract_name": record.get("ContractName"),
                "compiler_version": record.get("CompilerVersion"),
                "evidence_status": "read_only_real",
            },
        )

    def get_logs(
        self,
        target: ContractTargetRef,
        *,
        from_block: int,
        to_block: int,
        topics: dict[str, str] | None = None,
    ) -> ExplorerLogsResult:
        params = {
            "module": "logs",
            "action": "getLogs",
            "address": target.address,
            "fromBlock": str(from_block),
            "toBlock": str(to_block),
        }
        if topics:
            params.update(topics)
        response = self._api(target, params)
        if response.get("status") != "1":
            return ExplorerLogsResult(
                status="unresolved",
                provider="etherscan_v2",
                target=target,
                from_block=from_block,
                to_block=to_block,
                error={
                    "code": str(response.get("error_code") or "etherscan_getlogs_failed"),
                    "message": str(response.get("message") or response.get("result")),
                },
                metadata=_metadata(response),
            )
        result = response.get("result") if isinstance(response.get("result"), list) else []
        return ExplorerLogsResult(
            status="resolved",
            provider="etherscan_v2",
            target=target,
            from_block=from_block,
            to_block=to_block,
            logs=result,
            metadata={**_metadata(response), "evidence_status": "read_only_real"},
        )

    def _api(self, target: ContractTargetRef, params: dict[str, str]) -> dict[str, Any]:
        chainid = _chain_id(target.chain)
        cache_params = {"chainid": chainid, **params}
        cache_key = _cache_key(cache_params)
        cached = self._cache_read(cache_key)
        if cached is not None:
            cached["cache"] = {"hit": True, "key": cache_key}
            return cached
        if not self.api_token:
            return {
                "status": "0",
                "message": "ETHERSCAN_API_KEY is not configured.",
                "result": "ETHERSCAN_API_KEY is not configured.",
                "error_code": "etherscan_api_key_missing",
                "cache": {"hit": False, "key": cache_key, "miss_reason": "not_found"},
            }
        self._throttle()
        request_params = {**cache_params, "apikey": self.api_token}
        url = f"{self.base_url}?{urlencode(request_params)}"
        payload = self.transport(url)
        payload["cache"] = {"hit": False, "key": cache_key}
        self._cache_write(cache_key, payload)
        return payload

    def _cache_read(self, key: str) -> dict[str, Any] | None:
        if not self.cache_dir:
            return None
        path = self.cache_dir / f"{key}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _cache_write(self, key: str, payload: dict[str, Any]) -> None:
        if not self.cache_dir:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / f"{key}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()


def _default_transport(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _chain_id(chain: str) -> str:
    return {
        "eth": "1",
        "ethereum": "1",
        "mainnet": "1",
        "bsc": "56",
        "bnb": "56",
        "binance": "56",
        "polygon": "137",
        "matic": "137",
        "arbitrum": "42161",
        "arbitrum-one": "42161",
        "optimism": "10",
        "op": "10",
        "base": "8453",
        "gnosis": "100",
        "xdai": "100",
        "moonriver": "1285",
    }.get(chain.lower(), chain)


def _cache_key(params: dict[str, str]) -> str:
    return sha256(json.dumps(params, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _first_result(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0]
    return {}


def _parse_abi(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or value in {"", "Contract source code not verified"}:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def _parse_source_files(record: dict[str, Any]) -> dict[str, str]:
    source = str(record.get("SourceCode") or "")
    filename = _flat_source_filename(record)
    if not source:
        return {}
    parsed = _parse_standard_json_source(source)
    if parsed:
        return parsed
    return {filename: source}


def _flat_source_filename(record: dict[str, Any]) -> str:
    filename = str(record.get("ContractFileName") or record.get("ContractName") or "Contract.sol").strip()
    if not filename:
        return "Contract.sol"
    return filename if filename.endswith(".sol") else f"{filename}.sol"


def _parse_standard_json_source(source: str) -> dict[str, str]:
    text = source.strip()
    if text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    sources = parsed.get("sources") if isinstance(parsed, dict) else None
    if not isinstance(sources, dict):
        return {}
    files: dict[str, str] = {}
    for name, item in sources.items():
        if isinstance(item, dict) and isinstance(item.get("content"), str):
            files[_normalize_source_unit_name(str(name))] = item["content"]
    return files


def _normalize_source_unit_name(name: str) -> str:
    text = name.replace("\\", "/").strip()
    if not text:
        return "Contract.sol"
    parts = [part for part in text.split("/") if part not in {"", ".", ".."}]
    if not parts:
        return Path(text).name or "Contract.sol"
    if text.startswith("/") and "contracts" in parts:
        index = parts.index("contracts")
        tail = parts[index + 1 :]
        if tail:
            return "/".join(tail)
    if len(parts) >= 2 and re_match_drive_root(parts[0]):
        return "/".join(parts[1:])
    return "/".join(parts)


def re_match_drive_root(value: str) -> bool:
    return len(value) == 2 and value[1] == ":"


def _metadata(response: dict[str, Any]) -> dict[str, Any]:
    cache = response.get("cache") if isinstance(response.get("cache"), dict) else {}
    return {
        "etherscan_status": response.get("status"),
        "etherscan_message": response.get("message"),
        "cache_hit": bool(cache.get("hit")),
        "cache_key": cache.get("key"),
    }
