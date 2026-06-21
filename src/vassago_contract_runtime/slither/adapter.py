"""Slither adapter contract.

Slither is intentionally hidden behind this interface so the design runtime can
fall back cleanly when compilation context is incomplete or Slither is not
installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Protocol

from .solc_manager import SolcSelectManager, SolcVersionManager


@dataclass(frozen=True)
class SlitherInput:
    target_id: str
    source_files: dict[str, str]
    compile_context: dict[str, Any] = field(default_factory=dict)
    target_contract: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "source_file_count": len(self.source_files),
            "compile_context": dict(self.compile_context),
            "target_contract": self.target_contract,
        }


@dataclass(frozen=True)
class SlitherAnalysisResult:
    status: str
    provider: str
    target_id: str
    detectors: list[dict[str, Any]] = field(default_factory=list)
    ir: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target_id": self.target_id,
            "detectors": list(self.detectors),
            "ir": dict(self.ir),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class SlitherAdapter(Protocol):
    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        """Analyze a source bundle and return detector/IR context."""


class NullSlitherAdapter:
    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        return SlitherAnalysisResult(
            status="unavailable",
            provider="null",
            target_id=item.target_id,
            metadata={
                "evidence_status": "static_only",
                "note": "No Slither adapter configured. No compiler or Slither process was run.",
            },
            error={"code": "slither_adapter_not_configured", "message": "No Slither adapter is configured."},
        )


class PythonSlitherAdapter:
    """Extract normalized IR with Slither's Python API when available."""

    def __init__(
        self,
        slither_factory: Any | None = None,
        *,
        solc_manager: SolcVersionManager | None = None,
        allow_solc_install: bool = False,
    ) -> None:
        self.slither_factory = slither_factory
        self.solc_manager = solc_manager or SolcSelectManager()
        self.allow_solc_install = allow_solc_install

    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        if not item.source_files:
            return SlitherAnalysisResult(
                status="failed",
                provider="slither_python",
                target_id=item.target_id,
                error={"code": "slither_missing_source_files", "message": "No source files supplied."},
            )
        factory = self.slither_factory
        if factory is None:
            try:
                from slither.slither import Slither  # type: ignore
            except ImportError as exc:
                return SlitherAnalysisResult(
                    status="unavailable",
                    provider="slither_python",
                    target_id=item.target_id,
                    error={"code": "slither_python_api_not_installed", "message": str(exc)},
                )
            factory = Slither
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source_paths = _write_sources(workspace, item.source_files)
            target_source = _select_target_source(source_paths, item)
            compiler_selection = _compiler_selection(item.compile_context)
            provisioning = self.solc_manager.prepare(
                str(compiler_selection.get("requested_version") or ""),
                allow_install=self.allow_solc_install,
            ).to_json()
            compiler_selection["provisioning"] = provisioning
            if _should_skip_for_missing_compiler(compiler_selection):
                return SlitherAnalysisResult(
                    status="failed",
                    provider="slither_python",
                    target_id=item.target_id,
                    metadata={
                        "source_file_count": len(source_paths),
                        "target_source": str(target_source),
                        "compiler_selection": compiler_selection,
                    },
                    error={
                        "code": "solc_version_cache_missing",
                        "message": f"Requested solc {compiler_selection.get('requested_version')} is not available locally.",
                    },
                )
            try:
                slither = _build_python_slither(
                    factory,
                    workspace,
                    target_source,
                    item.compile_context,
                    compiler_selection,
                )
            except Exception as exc:
                return SlitherAnalysisResult(
                    status="failed",
                    provider="slither_python",
                    target_id=item.target_id,
                    metadata={
                        "source_file_count": len(source_paths),
                        "target_source": str(target_source),
                        "compiler_selection": compiler_selection,
                    },
                    error={"code": "slither_python_analysis_failed", "message": str(exc)},
                )
            ir = _normalize_python_slither(slither, item)
            return SlitherAnalysisResult(
                status="completed",
                provider="slither_python",
                target_id=item.target_id,
                ir=ir,
                metadata={
                    "evidence_status": "static_only",
                    "source_file_count": len(source_paths),
                    "target_source": str(target_source),
                    "contract_count": len(ir.get("contracts") or []),
                    "function_count": len(ir.get("functions") or []),
                    "compiler_selection": compiler_selection,
                },
            )


class SubprocessSlitherAdapter:
    """Run Slither through its CLI and parse JSON output."""

    def __init__(self, executable: str = "slither", *, timeout_seconds: int = 120, runner: Any | None = None) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.runner = runner or _run_subprocess

    def analyze(self, item: SlitherInput) -> SlitherAnalysisResult:
        if not item.source_files:
            return SlitherAnalysisResult(
                status="failed",
                provider="slither_subprocess",
                target_id=item.target_id,
                error={"code": "slither_missing_source_files", "message": "No source files supplied."},
            )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source_paths = _write_sources(workspace, item.source_files)
            target_source = _select_target_source(source_paths, item)
            output_path = workspace / "slither-output.json"
            command = [self.executable, str(target_source), "--json", str(output_path)]
            try:
                completed = self.runner(command, workspace, self.timeout_seconds)
            except FileNotFoundError:
                return SlitherAnalysisResult(
                    status="unavailable",
                    provider="slither_subprocess",
                    target_id=item.target_id,
                    error={"code": "slither_executable_not_found", "message": f"Executable not found: {self.executable}"},
                )
            except subprocess.TimeoutExpired:
                return SlitherAnalysisResult(
                    status="failed",
                    provider="slither_subprocess",
                    target_id=item.target_id,
                    error={"code": "slither_timeout", "message": f"Timed out after {self.timeout_seconds}s."},
                )
            payload = _read_json(output_path)
            success = bool(payload.get("success")) if payload else completed.returncode == 0
            detectors = _detectors(payload)
            return SlitherAnalysisResult(
                status="completed" if success else "failed",
                provider="slither_subprocess",
                target_id=item.target_id,
                detectors=detectors,
                ir={"status": "not_extracted", "reason": "subprocess_json_detector_output_only"},
                metadata={
                    "evidence_status": "static_only",
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-4000:] if isinstance(completed.stdout, str) else "",
                    "stderr": completed.stderr[-4000:] if isinstance(completed.stderr, str) else "",
                    "source_file_count": len(source_paths),
                },
                error=None if success else {"code": "slither_failed", "message": str(payload.get("error") or completed.stderr)},
            )


def _run_subprocess(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        timeout=timeout_seconds,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_sources(workspace: Path, source_files: dict[str, str]) -> dict[str, Path]:
    paths = {}
    for name, content in source_files.items():
        safe_name = _safe_source_name(name)
        path = workspace / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        paths[name] = path
    return paths


def _safe_source_name(name: str) -> str:
    path = Path(name)
    parts = [part for part in path.parts if part not in {"", ".", ".."}]
    cleaned = Path(*parts).as_posix() if parts else "Contract.sol"
    if cleaned.startswith("/") or "\\" in cleaned:
        return Path(cleaned).name or "Contract.sol"
    return cleaned


def _select_target_source(source_paths: dict[str, Path], item: SlitherInput) -> Path:
    selected = item.compile_context.get("selected_source_file")
    if selected in source_paths:
        return source_paths[selected]
    return source_paths[sorted(source_paths)[0]]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _detectors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") if isinstance(payload, dict) else None
    detectors = results.get("detectors") if isinstance(results, dict) else None
    return detectors if isinstance(detectors, list) else []


def _build_python_slither(
    factory: Any,
    workspace: Path,
    target_source: Path,
    compile_context: dict[str, Any],
    compiler_selection: dict[str, Any],
) -> Any:
    kwargs = _slither_constructor_kwargs(compile_context)
    try:
        target_arg = target_source.relative_to(workspace).as_posix()
    except ValueError:
        target_arg = str(target_source)
    cwd = Path.cwd()
    old_solc_version = os.environ.get("SOLC_VERSION")
    requested_version = str(compiler_selection.get("requested_version") or "")
    if requested_version:
        os.environ["SOLC_VERSION"] = requested_version
    os.chdir(workspace)
    try:
        if kwargs:
            try:
                return factory(target_arg, **kwargs)
            except TypeError:
                return factory(target_arg)
        else:
            return factory(target_arg)
    finally:
        os.chdir(cwd)
        _restore_env("SOLC_VERSION", old_solc_version)


def _slither_constructor_kwargs(compile_context: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    solc_args = compile_context.get("solc_args")
    if isinstance(solc_args, str) and solc_args.strip():
        kwargs["solc_args"] = solc_args
    remappings = compile_context.get("solc_remaps") or compile_context.get("remappings")
    if isinstance(remappings, list) and remappings:
        kwargs["solc_remaps"] = [str(item) for item in remappings]
    elif isinstance(remappings, str) and remappings.strip():
        kwargs["solc_remaps"] = remappings
    return kwargs


def _restore_env(name: str, old_value: str | None) -> None:
    if old_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = old_value


def _compiler_selection(compile_context: dict[str, Any]) -> dict[str, Any]:
    selection = compile_context.get("solc_version_selection")
    requested = ""
    source = "unknown"
    if isinstance(selection, dict):
        requested = str(selection.get("requested_version") or "")
        source = str(selection.get("source") or source)
    requested = requested or _normalize_solc_version(compile_context.get("compiler_version"))
    compiler = compile_context.get("compiler")
    if not requested and isinstance(compiler, dict):
        requested = _normalize_solc_version(compiler.get("version"))
        source = "compiler_metadata" if requested else source
    current = _current_solc_version()
    if not requested:
        status = "not_selected"
    elif current == requested:
        status = "current_matches_requested"
    elif current:
        status = "requested_via_solc_select_env"
    else:
        status = "requested_without_detected_solc"
    return {
        "requested_version": requested,
        "source": source,
        "current_solc_version": current,
        "env_var": "SOLC_VERSION" if requested else None,
        "status": status,
    }


def _should_skip_for_missing_compiler(compiler_selection: dict[str, Any]) -> bool:
    requested = str(compiler_selection.get("requested_version") or "")
    current = str(compiler_selection.get("current_solc_version") or "")
    provisioning = compiler_selection.get("provisioning")
    provision_status = provisioning.get("status") if isinstance(provisioning, dict) else ""
    if not requested or requested == current:
        return False
    return provision_status in {"compiler_cache_missing", "manager_unavailable", "install_failed", "manager_failed"}


def _current_solc_version() -> str:
    try:
        completed = subprocess.run(
            ["solc", "--version"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return _normalize_solc_version((completed.stdout or "") + "\n" + (completed.stderr or ""))


def _normalize_solc_version(value: object) -> str:
    match = re.search(r"v?(0\.\d+\.\d+)", str(value or ""))
    return match.group(1) if match else ""


def _normalize_python_slither(slither: Any, item: SlitherInput) -> dict[str, Any]:
    contracts = []
    flat_functions = []
    for contract in list(getattr(slither, "contracts", []) or []):
        functions = [_normalize_function(contract, function) for function in _contract_functions(contract)]
        if item.target_contract and str(getattr(contract, "name", "")) != item.target_contract:
            contract_status = "context_only"
        else:
            contract_status = "selected" if item.target_contract else "selected_or_context"
        contract_payload = {
            "name": str(getattr(contract, "name", "")),
            "status": contract_status,
            "inheritance": _name_list(getattr(contract, "inheritance", []) or []),
            "functions": functions,
        }
        contracts.append(contract_payload)
        flat_functions.extend(functions)
    return {
        "status": "completed",
        "provider": "slither_python",
        "target_contract": item.target_contract,
        "contracts": contracts,
        "functions": flat_functions,
    }


def _contract_functions(contract: Any) -> list[Any]:
    values = getattr(contract, "functions", None)
    if values is None:
        values = getattr(contract, "functions_declared", None)
    return list(values or [])


def _normalize_function(contract: Any, function: Any) -> dict[str, Any]:
    name = str(getattr(function, "name", "") or "")
    signature = _function_signature(function, name)
    nodes = list(getattr(function, "nodes", []) or [])
    conditions = _condition_expressions(nodes)
    return {
        "contract": str(getattr(contract, "name", "") or ""),
        "name": name,
        "signature": signature,
        "full_name": str(getattr(function, "full_name", "") or signature),
        "visibility": str(getattr(function, "visibility", "") or ""),
        "stateMutability": str(getattr(function, "state_mutability", "") or ""),
        "modifiers": _name_list(getattr(function, "modifiers", []) or []),
        "state_reads": _variable_name_list(getattr(function, "state_variables_read", []) or []),
        "state_writes": _variable_name_list(getattr(function, "state_variables_written", []) or []),
        "variables_read": _variable_name_list(getattr(function, "variables_read", []) or []),
        "variables_written": _variable_name_list(getattr(function, "variables_written", []) or []),
        "internal_calls": _call_list(getattr(function, "internal_calls", []) or []),
        "external_calls": _external_calls(function),
        "conditions": conditions,
        "source_excerpt": _source_excerpt(getattr(function, "source_mapping", None)),
        "source_mapping": _source_mapping(getattr(function, "source_mapping", None)),
        "slithir_operations": _slithir_operations(nodes),
        "evidence_refs": [
            f"slither:{str(getattr(contract, 'name', '') or '')}.{signature}",
            "slither:state_variables_written",
            "slither:modifiers",
        ],
    }


def _function_signature(function: Any, fallback_name: str) -> str:
    for attr in ("full_name", "signature_str", "canonical_name"):
        value = getattr(function, attr, None)
        if isinstance(value, str) and "(" in value and ")" in value:
            return value.split(".")[-1]
    parameters = getattr(function, "parameters", None)
    if parameters is not None:
        types = []
        for parameter in list(parameters or []):
            type_value = getattr(parameter, "type", None)
            types.append(str(type_value or ""))
        return f"{fallback_name}({','.join(types)})"
    return fallback_name


def _name_list(values: list[Any]) -> list[str]:
    names = []
    for value in values:
        names.append(_name(value))
    return sorted({name for name in names if name})


def _variable_name_list(values: list[Any]) -> list[str]:
    names = []
    for value in values:
        name = _name(value)
        if "(" in name:
            name = name.split("(", 1)[0]
        if "." in name:
            name = name.split(".")[-1]
        names.append(name)
    return sorted({name for name in names if name})


def _call_list(values: list[Any]) -> list[str]:
    names = []
    for value in values:
        if isinstance(value, tuple):
            names.extend(_name(item) for item in value)
        else:
            names.append(_name(value))
    return sorted({name for name in names if name})


def _external_calls(function: Any) -> list[str]:
    calls = []
    for attr in ("high_level_calls", "low_level_calls", "library_calls", "external_calls_as_expressions"):
        calls.extend(_call_list(list(getattr(function, attr, []) or [])))
    return sorted({call for call in calls if call})


def _name(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    for attr in ("full_name", "canonical_name", "name"):
        text = getattr(value, attr, None)
        if text:
            return str(text)
    return str(value)


def _condition_expressions(nodes: list[Any]) -> list[str]:
    expressions = []
    for node in nodes:
        expression = getattr(node, "expression", None)
        text = str(expression or "")
        node_type = str(getattr(node, "type", "") or "")
        if not text:
            continue
        lowered = text.lower()
        if "require" in lowered or "assert" in lowered or "revert" in lowered or "if" in node_type.lower():
            expressions.append(text)
    return sorted({expression for expression in expressions if expression})


def _slithir_operations(nodes: list[Any]) -> list[str]:
    operations = []
    for node in nodes:
        for ir in list(getattr(node, "irs", []) or []):
            operations.append(str(ir))
            if len(operations) >= 80:
                return operations
    return operations


def _source_excerpt(source_mapping: Any) -> str:
    content = getattr(source_mapping, "content", None)
    return str(content or "")[:2000]


def _source_mapping(source_mapping: Any) -> dict[str, Any]:
    if source_mapping is None:
        return {}
    filename = getattr(source_mapping, "filename", None)
    return {
        "filename": str(getattr(filename, "relative", None) or getattr(filename, "absolute", None) or filename or ""),
        "start": getattr(source_mapping, "start", None),
        "length": getattr(source_mapping, "length", None),
        "lines": list(getattr(source_mapping, "lines", []) or []),
    }
