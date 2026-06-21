"""Corpus adapter interfaces and local design corpus implementation."""

from .adapter import CorpusAdapter, CorpusMatch, CorpusScanContext, CorpusScanResult, DesignCorpusAdapter, NullCorpusAdapter

__all__ = [
    "CorpusAdapter",
    "CorpusMatch",
    "CorpusScanContext",
    "CorpusScanResult",
    "DesignCorpusAdapter",
    "NullCorpusAdapter",
]
