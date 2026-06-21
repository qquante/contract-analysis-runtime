"""Command line interface for the contract runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .design_runtime.design_loader import DesignLoadError
from .design_runtime.models import ModelValidationError
from .quality import run_checks
from .runtime_api import read_artifact_from_payload, resume_design_from_payload, run_design_from_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vassago-contract-runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate repository runtime metadata.")
    check.add_argument("--root", default=".", help="Repository root.")

    run = sub.add_parser("run-design", help="Run a design against target contracts.")
    run.add_argument("--design", required=True, help="Design id or path to design.yaml.")
    run.add_argument("--targets", required=True, help="JSON target list.")
    run.add_argument("--output", required=True, help="Run output directory.")
    run.add_argument("--dry-run", action="store_true", help="Write manifests and dry-run artifacts only.")
    run.add_argument("--source-fixture", help="Local JSON source fixture for phase 01 dossier.")
    run.add_argument(
        "--bootstrap-adapters",
        action="store_true",
        help="Run implemented bootstrap adapters and dry-run the rest.",
    )
    run.add_argument("--no-resume", action="store_true", help="Do not resume an existing run directory.")

    resume = sub.add_parser("resume", help="Resume an existing run.")
    resume.add_argument("--run", required=True, help="Run directory.")
    resume.add_argument("--dry-run", action="store_true", help="Use dry-run adapters.")
    resume.add_argument("--source-fixture", help="Local JSON source fixture for phase 01 dossier.")
    resume.add_argument(
        "--bootstrap-adapters",
        action="store_true",
        help="Use implemented bootstrap adapters and dry-run the rest.",
    )

    artifact_read = sub.add_parser("artifact-read", help="Read an artifact by vassago:// URI.")
    artifact_read.add_argument("--run", required=True, help="Run directory.")
    artifact_read.add_argument("--uri", required=True, help="Artifact URI.")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = run_checks(Path(args.root))
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.command == "run-design":
            return _run_design_command(args)
        if args.command == "resume":
            return _resume_command(args)
        if args.command == "artifact-read":
            return _artifact_read_command(args)
    except (DesignLoadError, ModelValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


def _run_design_command(args: argparse.Namespace) -> int:
    payload = run_design_from_payload(
        {
            "design": args.design,
            "targets_path": args.targets,
            "output": args.output,
            "dry_run": args.dry_run,
            "bootstrap_adapters": args.bootstrap_adapters,
            "source_fixture": args.source_fixture,
            "resume": not args.no_resume,
        }
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["failed_count"] == 0 else 1


def _resume_command(args: argparse.Namespace) -> int:
    payload = resume_design_from_payload(
        {
            "run": args.run,
            "dry_run": args.dry_run,
            "bootstrap_adapters": args.bootstrap_adapters,
            "source_fixture": args.source_fixture,
        }
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["failed_count"] == 0 else 1


def _artifact_read_command(args: argparse.Namespace) -> int:
    payload = read_artifact_from_payload({"run": args.run, "uri": args.uri})["artifact"]
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
