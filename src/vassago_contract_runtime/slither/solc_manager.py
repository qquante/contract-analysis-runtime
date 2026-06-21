"""Controlled solc version cache/provisioning for Slither.

The manager never calls ``solc-select use``. Slither execution sets
``SOLC_VERSION`` per process invocation, so global compiler state is not
mutated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import subprocess
from typing import Any, Protocol


@dataclass(frozen=True)
class SolcProvisionResult:
    status: str
    requested_version: str
    current_solc_version: str = ""
    installed_versions: list[str] = field(default_factory=list)
    manager: str = "solc-select"
    install_attempted: bool = False
    install_allowed: bool = False
    error: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "requested_version": self.requested_version,
            "current_solc_version": self.current_solc_version,
            "installed_versions": list(self.installed_versions),
            "manager": self.manager,
            "install_attempted": self.install_attempted,
            "install_allowed": self.install_allowed,
            "error": self.error,
        }


class SolcVersionManager(Protocol):
    def prepare(self, requested_version: str, *, allow_install: bool = False) -> SolcProvisionResult:
        """Ensure a requested solc version is usable or report why not."""


class SolcSelectManager:
    """Use solc-select as an optional local compiler cache."""

    def __init__(
        self,
        executable: str = "solc-select",
        *,
        runner: Any | None = None,
        current_version_getter: Any | None = None,
    ) -> None:
        self.executable = executable
        self.runner = runner or _run_subprocess
        self.current_version_getter = current_version_getter or _current_solc_version

    def prepare(self, requested_version: str, *, allow_install: bool = False) -> SolcProvisionResult:
        version = _normalize_solc_version(requested_version)
        current = str(self.current_version_getter() or "")
        if not version:
            return SolcProvisionResult(status="not_requested", requested_version="", current_solc_version=current)
        installed_result = self._installed_versions()
        if installed_result.error:
            if current == version:
                return SolcProvisionResult(
                    status="current_matches_requested",
                    requested_version=version,
                    current_solc_version=current,
                    manager=self.executable,
                    error=installed_result.error,
                )
            return SolcProvisionResult(
                status="manager_unavailable",
                requested_version=version,
                current_solc_version=current,
                manager=self.executable,
                error=installed_result.error,
            )
        installed = installed_result.installed_versions
        if current == version:
            return SolcProvisionResult(
                status="current_matches_requested",
                requested_version=version,
                current_solc_version=current,
                installed_versions=installed,
                manager=self.executable,
            )
        if version in installed:
            return SolcProvisionResult(
                status="cache_hit",
                requested_version=version,
                current_solc_version=current,
                installed_versions=installed,
                manager=self.executable,
            )
        if not allow_install:
            return SolcProvisionResult(
                status="compiler_cache_missing",
                requested_version=version,
                current_solc_version=current,
                installed_versions=installed,
                manager=self.executable,
                install_allowed=False,
            )
        install = self._install(version)
        installed_after = self._installed_versions()
        installed_versions = installed_after.installed_versions or installed
        status = "installed" if not install.error and version in installed_versions else "install_failed"
        return SolcProvisionResult(
            status=status,
            requested_version=version,
            current_solc_version=str(self.current_version_getter() or ""),
            installed_versions=installed_versions,
            manager=self.executable,
            install_attempted=True,
            install_allowed=True,
            error=install.error or installed_after.error,
        )

    def _installed_versions(self) -> SolcProvisionResult:
        try:
            completed = self.runner([self.executable, "versions"], timeout_seconds=30)
        except FileNotFoundError:
            return SolcProvisionResult(
                status="manager_unavailable",
                requested_version="",
                error={"code": "solc_select_not_found", "message": f"Executable not found: {self.executable}"},
            )
        except subprocess.TimeoutExpired:
            return SolcProvisionResult(
                status="manager_timeout",
                requested_version="",
                error={"code": "solc_select_timeout", "message": "solc-select versions timed out."},
            )
        output = "\n".join([completed.stdout or "", completed.stderr or ""])
        if completed.returncode != 0:
            return SolcProvisionResult(
                status="manager_failed",
                requested_version="",
                error={"code": "solc_select_versions_failed", "message": output[-2000:]},
            )
        return SolcProvisionResult(status="listed", requested_version="", installed_versions=_parse_versions(output))

    def _install(self, version: str) -> SolcProvisionResult:
        try:
            completed = self.runner([self.executable, "install", version], timeout_seconds=300)
        except FileNotFoundError:
            return SolcProvisionResult(
                status="manager_unavailable",
                requested_version=version,
                install_attempted=True,
                install_allowed=True,
                error={"code": "solc_select_not_found", "message": f"Executable not found: {self.executable}"},
            )
        except subprocess.TimeoutExpired:
            return SolcProvisionResult(
                status="install_timeout",
                requested_version=version,
                install_attempted=True,
                install_allowed=True,
                error={"code": "solc_select_install_timeout", "message": f"Install timed out for solc {version}."},
            )
        output = "\n".join([completed.stdout or "", completed.stderr or ""])
        return SolcProvisionResult(
            status="install_command_completed" if completed.returncode == 0 else "install_failed",
            requested_version=version,
            install_attempted=True,
            install_allowed=True,
            error=None
            if completed.returncode == 0
            else {"code": "solc_select_install_failed", "message": output[-2000:]},
        )


def _run_subprocess(command: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess:
    return subprocess.run(command, timeout=timeout_seconds, text=True, capture_output=True, check=False)


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


def _parse_versions(output: str) -> list[str]:
    return sorted(set(re.findall(r"\b0\.\d+\.\d+\b", output)))
