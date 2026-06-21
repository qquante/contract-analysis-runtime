"""Contract target models and adapters."""

from .source_resolver import NullSourceResolver, SourceResolution, SourceResolver
from .target import ContractTargetRef

__all__ = ["ContractTargetRef", "NullSourceResolver", "SourceResolution", "SourceResolver"]
