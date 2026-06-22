"""Foundry adapter contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Protocol


@dataclass(frozen=True)
class FoundryHarnessInput:
    target_id: str
    harness_name: str
    source_files: dict[str, str]
    test_files: dict[str, str]
    foundry_toml: str | None = None
    fork: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "harness_name": self.harness_name,
            "source_file_count": len(self.source_files),
            "test_file_count": len(self.test_files),
            "has_foundry_toml": self.foundry_toml is not None,
            "fork": dict(self.fork),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class FoundryRunResult:
    status: str
    provider: str
    target_id: str
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "target_id": self.target_id,
            "command": _redacted_command(self.command),
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class FoundryAdapter(Protocol):
    def compile_harness(self, item: FoundryHarnessInput) -> FoundryRunResult:
        """Compile a harness without runtime execution."""

    def run_local_fork(self, item: FoundryHarnessInput) -> FoundryRunResult:
        """Run local/fork tests only when runtime gate is satisfied."""


class NullFoundryAdapter:
    def compile_harness(self, item: FoundryHarnessInput) -> FoundryRunResult:
        return FoundryRunResult(
            status="unavailable",
            provider="null",
            target_id=item.target_id,
            metadata={"evidence_status": "static_only", "note": "No Foundry adapter configured."},
            error={"code": "foundry_adapter_not_configured", "message": "No Foundry adapter is configured."},
        )

    def run_local_fork(self, item: FoundryHarnessInput) -> FoundryRunResult:
        return FoundryRunResult(
            status="blocked",
            provider="null",
            target_id=item.target_id,
            metadata={
                "evidence_status": "static_only",
                "note": "Runtime execution requires an explicit Foundry adapter and runtime-ready gate.",
            },
            error={"code": "foundry_runtime_not_configured", "message": "No Foundry runtime adapter is configured."},
        )


class SubprocessFoundryAdapter:
    """Run Foundry locally through `forge`.

    `compile_harness` uses `forge build` and never runs tests.
    `run_local_fork` uses `forge test`, but only when the caller passes an
    explicit runtime-ready authorization in metadata.
    """

    def __init__(self, executable: str = "forge", *, timeout_seconds: int = 180, runner: Any | None = None) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.runner = runner or _run_subprocess

    def compile_harness(self, item: FoundryHarnessInput) -> FoundryRunResult:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            _write_workspace(workspace, item)
            command = [self.executable, "build"]
            return _run_foundry(
                item,
                provider="foundry_subprocess",
                command=command,
                workspace=workspace,
                runner=self.runner,
                timeout_seconds=self.timeout_seconds,
                success_status="compile_only_passed",
                failure_status="compile_failed",
            )

    def run_local_fork(self, item: FoundryHarnessInput) -> FoundryRunResult:
        if item.metadata.get("runtime_ready") is not True or item.metadata.get("runtime_authorized") is not True:
            return FoundryRunResult(
                status="blocked",
                provider="foundry_subprocess",
                target_id=item.target_id,
                metadata={
                    "evidence_status": "static_only",
                    "runtime_ready": bool(item.metadata.get("runtime_ready")),
                    "runtime_authorized": bool(item.metadata.get("runtime_authorized")),
                    "note": "Runtime Foundry requires explicit runtime_ready and runtime_authorized metadata.",
                },
                error={"code": "foundry_runtime_gate_not_satisfied", "message": "Runtime gate is not satisfied."},
            )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            _write_workspace(workspace, item)
            command = [self.executable, "test", "--match-contract", item.harness_name]
            fork_url = item.fork.get("rpc_url")
            fork_block = item.fork.get("block_number")
            if fork_url:
                command.extend(["--fork-url", str(fork_url)])
            if fork_block:
                command.extend(["--fork-block-number", str(fork_block)])
            return _run_foundry(
                item,
                provider="foundry_subprocess",
                command=command,
                workspace=workspace,
                runner=self.runner,
                timeout_seconds=self.timeout_seconds,
                success_status="runtime_completed",
                failure_status="runtime_failed",
            )


def _run_subprocess(command: list[str], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        timeout=timeout_seconds,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _run_foundry(
    item: FoundryHarnessInput,
    *,
    provider: str,
    command: list[str],
    workspace: Path,
    runner: Any,
    timeout_seconds: int,
    success_status: str,
    failure_status: str,
) -> FoundryRunResult:
    try:
        completed = runner(command, workspace, timeout_seconds)
    except FileNotFoundError:
        return FoundryRunResult(
            status="unavailable",
            provider=provider,
            target_id=item.target_id,
            command=command,
            error={"code": "forge_executable_not_found", "message": f"Executable not found: {command[0]}"},
        )
    except subprocess.TimeoutExpired:
        return FoundryRunResult(
            status=failure_status,
            provider=provider,
            target_id=item.target_id,
            command=command,
            error={"code": "forge_timeout", "message": f"Timed out after {timeout_seconds}s."},
        )
    status = success_status if completed.returncode == 0 else failure_status
    return FoundryRunResult(
        status=status,
        provider=provider,
        target_id=item.target_id,
        command=command,
        stdout=completed.stdout if isinstance(completed.stdout, str) else "",
        stderr=completed.stderr if isinstance(completed.stderr, str) else "",
        metadata={
            "evidence_status": "compile_only" if success_status == "compile_only_passed" else "runtime_local",
            "returncode": completed.returncode,
            "workspace_ephemeral": True,
            "no_broadcast_command": "--broadcast" not in command,
        },
        error=None if completed.returncode == 0 else {"code": "forge_failed", "message": completed.stderr},
    )


def _redacted_command(command: list[str]) -> list[str]:
    redacted = []
    redact_next = False
    for item in command:
        if redact_next:
            redacted.append("<redacted-rpc-url>")
            redact_next = False
            continue
        redacted.append(item)
        if item == "--fork-url":
            redact_next = True
    return redacted


def _write_workspace(workspace: Path, item: FoundryHarnessInput) -> None:
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "test").mkdir(parents=True, exist_ok=True)
    (workspace / "foundry.toml").write_text(item.foundry_toml or _default_foundry_toml(), encoding="utf-8")
    for name, content in item.source_files.items():
        _write_local_file(workspace / "src", name, content)
    for name, content in item.test_files.items():
        _write_local_file(workspace / "test", name, content)


def _write_local_file(root: Path, name: str, content: str) -> None:
    parts = [part for part in Path(name).parts if part not in {"", ".", ".."}]
    path = root / (Path(*parts) if parts else Path("Contract.sol"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _default_foundry_toml() -> str:
    return "\n".join(
        [
            "[profile.default]",
            'src = "src"',
            'test = "test"',
            'out = "out"',
            'libs = ["lib"]',
            "auto_detect_solc = true",
            "",
        ]
    )
