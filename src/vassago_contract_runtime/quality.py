"""Repository quality checks for the bootstrap runtime."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from .artifacts.store import ArtifactStore, ArtifactStoreError
from .design_runtime.design_loader import DesignLoadError, load_design


MAX_PRODUCTION_PY_LINES = 800


def run_checks(root: str | Path = ".") -> dict[str, Any]:
    root = Path(root)
    checks: list[dict[str, Any]] = []
    checks.append(_check_design(root / "designs" / "sc01-access" / "design.yaml"))
    checks.append(_check_line_limit(root / "src"))
    checks.append(_check_forbidden_evidence_strings(root / "src"))
    checks.append(_check_secret_patterns(root))
    checks.append(_check_artifact_path_traversal())
    failed = [item for item in checks if item["status"] != "passed"]
    return {
        "status": "failed" if failed else "passed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "checks": checks,
    }


def _check_design(path: Path) -> dict[str, Any]:
    try:
        design = load_design(path)
    except DesignLoadError as exc:
        return {"name": "design:sc01-access", "status": "failed", "error": {"code": exc.code, "message": exc.message}}
    return {
        "name": "design:sc01-access",
        "status": "passed",
        "phase_count": len(design.phases),
        "design_id": design.design_id,
    }


def _check_line_limit(src_root: Path) -> dict[str, Any]:
    offenders = []
    for path in sorted(src_root.rglob("*.py")):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_PRODUCTION_PY_LINES:
            offenders.append({"path": str(path), "line_count": line_count})
    return {
        "name": "python-line-limit",
        "status": "failed" if offenders else "passed",
        "max_lines": MAX_PRODUCTION_PY_LINES,
        "offenders": offenders,
    }


def _check_forbidden_evidence_strings(src_root: Path) -> dict[str, Any]:
    offenders = []
    forbidden = "reproduced_runtime"
    allowed = {"models.py", "quality.py"}
    for path in sorted(src_root.rglob("*.py")):
        if path.name in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if forbidden in text:
            offenders.append(str(path))
    return {
        "name": "evidence-promotion-string",
        "status": "failed" if offenders else "passed",
        "forbidden": forbidden,
        "offenders": offenders,
    }


def _check_secret_patterns(root: Path) -> dict[str, Any]:
    patterns = (
        "PRIVATE" + "_KEY" + "=",
        "MNEM" + "ONIC" + "=",
        "SECRET" + "_KEY" + "=",
        "ETHERSCAN" + "_API_KEY" + "=",
        "OPENROUTER" + "_API_KEY" + "=",
        "AL" + "CHEMY" + "_API_KEY" + "=",
    )
    offenders = []
    for pattern in ("*.md", "*.yaml", "*.toml", "*.json", "*.py"):
        for path in sorted(root.rglob(pattern)):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.name == "quality.py":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for secret_pattern in patterns:
                if secret_pattern in text:
                    offenders.append({"path": str(path), "pattern": secret_pattern})
    return {
        "name": "secret-patterns",
        "status": "failed" if offenders else "passed",
        "offenders": offenders,
    }


def _check_artifact_path_traversal() -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp), "RUN-check")
            store.write_text_artifact("CT-check", "00_intake", "../escape.txt", "bad")
    except ArtifactStoreError:
        return {"name": "artifact-path-traversal", "status": "passed"}
    return {"name": "artifact-path-traversal", "status": "failed", "error": "path traversal was not rejected"}
