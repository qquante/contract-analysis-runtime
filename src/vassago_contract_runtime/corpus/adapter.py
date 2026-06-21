"""SC01 corpus motif adapter interface and local implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from vassago_contract_runtime.design_runtime.design_loader import parse_simple_yaml


@dataclass(frozen=True)
class CorpusScanContext:
    design_id: str
    target_id: str
    chain: str
    address: str
    function_index: dict[str, Any]
    source_manifest: dict[str, Any]
    protocol_fingerprint: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorpusMatch:
    corpus_id: str
    thesis_id: str
    bug_family: str
    matched_motifs: list[str]
    matched_functions: list[str]
    evidence_refs: list[str]
    confidence: str = "candidate"

    def to_json(self) -> dict[str, Any]:
        return {
            "corpus_id": self.corpus_id,
            "thesis_id": self.thesis_id,
            "bug_family": self.bug_family,
            "matched_motifs": list(self.matched_motifs),
            "matched_functions": list(self.matched_functions),
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class CorpusScanResult:
    status: str
    matches: list[CorpusMatch]
    motif_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "motif_count": self.motif_count,
            "match_count": len(self.matches),
            "matches": [match.to_json() for match in self.matches],
            "metadata": dict(self.metadata),
        }


class CorpusAdapter(Protocol):
    def scan(self, context: CorpusScanContext) -> CorpusScanResult:
        """Scan one target against a local corpus."""


class NullCorpusAdapter:
    def scan(self, context: CorpusScanContext) -> CorpusScanResult:
        return CorpusScanResult(
            status="unconfigured",
            matches=[],
            motif_count=0,
            metadata={"evidence_status": "static_only", "note": "No corpus adapter configured."},
        )


class DesignCorpusAdapter:
    """Load thesis motifs from designs/<design>/corpus/*.yaml."""

    def __init__(self, motifs: list[dict[str, Any]]) -> None:
        self.motifs = motifs

    @classmethod
    def from_dir(cls, corpus_dir: str | Path) -> "DesignCorpusAdapter":
        path = Path(corpus_dir)
        motifs: list[dict[str, Any]] = []
        if path.is_dir():
            for item in sorted(path.glob("*.yaml")):
                payload = parse_simple_yaml(item.read_text(encoding="utf-8"))
                payload["_corpus_file"] = item.name
                motifs.append(payload)
        return cls(motifs)

    def scan(self, context: CorpusScanContext) -> CorpusScanResult:
        haystack = _haystack(context)
        functions = _functions(context)
        matches: list[CorpusMatch] = []
        for motif in self.motifs:
            search_motifs = [str(item) for item in motif.get("search_motifs", []) if str(item).strip()]
            matched = [item for item in search_motifs if item.lower() in haystack]
            matched_functions = [
                function["name"]
                for function in functions
                if any(item.lower() in str(function.get("name") or "").lower() for item in matched)
            ]
            if not matched:
                continue
            matches.append(
                CorpusMatch(
                    corpus_id=str(motif.get("id") or motif.get("_corpus_file") or "unknown"),
                    thesis_id=str(motif.get("thesis_id") or motif.get("id") or "unknown"),
                    bug_family=str(motif.get("bug_family") or "unknown"),
                    matched_motifs=matched,
                    matched_functions=matched_functions,
                    evidence_refs=_evidence_refs(matched, context),
                    confidence="candidate",
                )
            )
        return CorpusScanResult(
            status="completed",
            matches=matches,
            motif_count=len(self.motifs),
            metadata={
                "evidence_status": "static_only",
                "source": "design_corpus",
                "corpus_files": [str(item.get("_corpus_file")) for item in self.motifs],
            },
        )


def _haystack(context: CorpusScanContext) -> str:
    function_text = " ".join(str(item.get("name") or "") for item in _functions(context))
    source_text = " ".join(str(value) for value in (context.source_manifest.get("source_files") or {}).values())
    return f"{function_text} {source_text}".lower()


def _functions(context: CorpusScanContext) -> list[dict[str, Any]]:
    return [item for item in context.function_index.get("functions", []) if isinstance(item, dict)]


def _evidence_refs(matched: list[str], context: CorpusScanContext) -> list[str]:
    refs = []
    function_names = [str(item.get("name") or "") for item in _functions(context)]
    for motif in matched:
        if any(motif.lower() in name.lower() for name in function_names):
            refs.append(f"function-index:{motif}")
        if motif.lower() in " ".join((context.source_manifest.get("source_files") or {}).values()).lower():
            refs.append(f"source-manifest:{motif}")
    return sorted(set(refs))
