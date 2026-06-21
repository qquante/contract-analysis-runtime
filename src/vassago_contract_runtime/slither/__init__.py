"""Slither adapter interfaces."""

from .adapter import NullSlitherAdapter, SlitherAdapter, SlitherAnalysisResult, SlitherInput, SubprocessSlitherAdapter

__all__ = [
    "NullSlitherAdapter",
    "SlitherAdapter",
    "SlitherAnalysisResult",
    "SlitherInput",
    "SubprocessSlitherAdapter",
]
