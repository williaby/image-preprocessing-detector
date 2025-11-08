"""Front matter contract module for MkDocs documentation validation.

This module provides Pydantic models for validating YAML front matter in Markdown
documentation files. It enforces a discriminated union schema supporting multiple
page types: common, script, knowledge, and planning.
"""

from .models import (
    Author,
    CommonFM,
    DatasetCard,
    DiscriminatedFM,
    KnowledgeFM,
    Metric,
    ModelCard,
    PlanningFM,
    ScriptSpecFM,
)

__all__ = [
    "Author",
    "CommonFM",
    "DatasetCard",
    "DiscriminatedFM",
    "KnowledgeFM",
    "Metric",
    "ModelCard",
    "PlanningFM",
    "ScriptSpecFM",
]
