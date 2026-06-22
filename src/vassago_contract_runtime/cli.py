"""Command line interface for the contract runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .design_runtime.design_loader import DesignLoadError
from .design_runtime.models import ModelValidationError
from .historical_corpus import build_historical_corpus_report, write_historical_blind_targets
from .historical_scoring import write_historical_score
from .mcp import run_stdio
from .quality import run_checks
from .runtime_api import read_artifact_from_payload, resume_design_from_payload, run_design_from_payload
from .sc01_bridge_review import write_sc01_bridge_current_review
from .sc01_current_state import write_sc01_current_state_review
from .sc01_impact import write_sc01_impact_review


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
        "--source-cache-dir",
        help="Filesystem cache directory for read-only Explorer source context. Defaults to <output>/_cache/etherscan-v2.",
    )
    run.add_argument(
        "--runtime-authorized",
        action="store_true",
        help="Allow local Foundry runtime when the design runtime gate is satisfied.",
    )
    run.add_argument(
        "--allow-solc-install",
        action="store_true",
        help="Allow solc-select to install missing solc versions for Slither. Default is no install.",
    )
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
        "--source-cache-dir",
        help="Filesystem cache directory for read-only Explorer source context. Defaults to <run>/_cache/etherscan-v2.",
    )
    resume.add_argument(
        "--runtime-authorized",
        action="store_true",
        help="Allow local Foundry runtime when the design runtime gate is satisfied.",
    )
    resume.add_argument(
        "--allow-solc-install",
        action="store_true",
        help="Allow solc-select to install missing solc versions for Slither. Default is no install.",
    )
    resume.add_argument(
        "--bootstrap-adapters",
        action="store_true",
        help="Use implemented bootstrap adapters and dry-run the rest.",
    )

    artifact_read = sub.add_parser("artifact-read", help="Read an artifact by vassago:// URI.")
    artifact_read.add_argument("--run", required=True, help="Run directory.")
    artifact_read.add_argument("--uri", required=True, help="Artifact URI.")

    impact_review = sub.add_parser("impact-review", help="Write an SC01 impact review sidecar for one target.")
    impact_review.add_argument("--run", required=True, help="Run directory.")
    impact_review.add_argument("--target-id", required=True, help="Target id inside the run.")

    current_state = sub.add_parser(
        "current-state-review",
        help="Write a read-only SC01 current-state review sidecar for one target.",
    )
    current_state.add_argument("--run", required=True, help="Run directory.")
    current_state.add_argument("--target-id", required=True, help="Target id inside the run.")
    current_state.add_argument("--rpc-url", help="Read-only RPC URL. Defaults to VASSAGO_CURRENT_STATE_RPC_URL/fallback env.")

    bridge_review = sub.add_parser(
        "bridge-current-review",
        help="Write a static/read-only SC01 bridge current-path review sidecar for one target.",
    )
    bridge_review.add_argument("--run", required=True, help="Run directory.")
    bridge_review.add_argument("--target-id", required=True, help="Target id inside the run.")

    historical_corpus = sub.add_parser("historical-corpus-report", help="Validate and summarize a historical corpus.")
    historical_corpus.add_argument(
        "--manifest",
        default="designs/historical-exploits/manifest.json",
        help="Historical corpus manifest.",
    )
    historical_corpus.add_argument("--family", help="Optional family filter.")
    historical_corpus.add_argument("--limit", type=int, help="Optional maximum case count.")
    historical_corpus.add_argument("--targets-output", help="Optional path to write blind target list JSON.")

    historical_score = sub.add_parser("historical-corpus-score", help="Score a completed run against a historical corpus.")
    historical_score.add_argument("--run", required=True, help="Run directory to score.")
    historical_score.add_argument(
        "--manifest",
        default="designs/historical-exploits/manifest.json",
        help="Historical corpus manifest.",
    )
    historical_score.add_argument("--family", help="Optional family filter.")
    historical_score.add_argument("--benchmark-id", help="Optional benchmark id filter, for example HEC-031.")
    historical_score.add_argument("--limit", type=int, help="Optional maximum case count.")
    historical_score.add_argument("--output-dir", help="Output directory. Defaults to <run>/historical-corpus-score.")

    mcp = sub.add_parser("mcp", help="Run the local MCP server.")
    mcp.add_argument("--stdio", action="store_true", help="Use stdio transport.")

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
        if args.command == "impact-review":
            return _impact_review_command(args)
        if args.command == "current-state-review":
            return _current_state_review_command(args)
        if args.command == "bridge-current-review":
            return _bridge_current_review_command(args)
        if args.command == "historical-corpus-report":
            return _historical_corpus_report_command(args)
        if args.command == "historical-corpus-score":
            return _historical_corpus_score_command(args)
        if args.command == "mcp":
            if not args.stdio:
                raise ValueError("Only local stdio MCP is supported. Pass --stdio.")
            return run_stdio()
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
            "source_cache_dir": args.source_cache_dir,
            "runtime_authorized": args.runtime_authorized,
            "allow_solc_install": args.allow_solc_install,
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
            "source_cache_dir": args.source_cache_dir,
            "runtime_authorized": args.runtime_authorized,
            "allow_solc_install": args.allow_solc_install,
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


def _impact_review_command(args: argparse.Namespace) -> int:
    payload = write_sc01_impact_review(args.run, args.target_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "completed" else 1


def _current_state_review_command(args: argparse.Namespace) -> int:
    payload = write_sc01_current_state_review(args.run, args.target_id, rpc_url=args.rpc_url)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "completed" else 1


def _bridge_current_review_command(args: argparse.Namespace) -> int:
    payload = write_sc01_bridge_current_review(args.run, args.target_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "completed" else 1


def _historical_corpus_report_command(args: argparse.Namespace) -> int:
    payload = build_historical_corpus_report(args.manifest, family=args.family, limit=args.limit)
    if args.targets_output:
        payload["target_export"] = write_historical_blind_targets(
            args.targets_output,
            args.manifest,
            family=args.family,
            limit=args.limit,
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "completed" else 1


def _historical_corpus_score_command(args: argparse.Namespace) -> int:
    payload = write_historical_score(
        args.run,
        args.manifest,
        output_dir=args.output_dir,
        family=args.family,
        benchmark_id=args.benchmark_id,
        limit=args.limit,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
