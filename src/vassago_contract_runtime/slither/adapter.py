"""Slither adapter contract.

Slither is intentionally hidden behind this interface so the design runtime can
fall back cleanly when compilation context is incomplete or Slither is not
installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Protocol


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
