"""Pydantic models for front matter validation.

This module defines a discriminated union schema for validating YAML front matter
in Markdown documentation files. It supports multiple page types with strict
validation rules and autofix capabilities.

Schema Types:
    - common: General documentation pages (default)
    - script: Tool/script documentation pages
    - knowledge: Knowledge base entries
    - planning: Planning and strategy documents
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Regular expression for validating snake_case tags
TAG = re.compile(r"^[a-z0-9_]+$")


class Author(BaseModel):
    """Author information for documentation pages.

    Attributes:
        name: Full name of the author.
        orcid: Optional ORCID identifier (e.g., "0000-0000-0000-0000").
    """

    name: str
    orcid: str | None = None


class Metric(BaseModel):
    """Performance metric for model evaluation.

    Attributes:
        name: Name of the metric (e.g., "accuracy", "f1", "map").
        value: Numeric value of the metric.
        dataset: Optional dataset name where metric was measured.
        split: Optional dataset split (e.g., "test", "val").
    """

    name: str
    value: float
    dataset: str | None = None
    split: str | None = None


class ModelCard(BaseModel):
    """Model metadata for machine learning models.

    Attributes:
        id: Unique model identifier.
        task: Optional task description (e.g., "image-classification").
        license: Optional license identifier (e.g., "Apache-2.0").
        codeRepository: Optional URL to model code repository.
        metrics: Optional list of performance metrics.
    """

    id: str
    task: str | None = None
    license: str | None = None
    codeRepository: str | None = None  # noqa: N815 (Schema.org field name)
    metrics: list[Metric] | None = None


class DatasetCard(BaseModel):
    """Dataset metadata for training/evaluation data.

    Attributes:
        name: Dataset name.
        url: Optional URL to dataset.
        license: Optional license identifier (e.g., "CC-BY-4.0").
    """

    name: str
    url: str | None = None
    license: str | None = None


class CommonFM(BaseModel):
    """Common front matter schema for general documentation pages.

    This is the base schema and default type for most documentation pages.

    Attributes:
        schema_type: Discriminator field, always "common".
        title: Page title (renders as H1, no body H1 allowed).
        description: Optional short description.
        tags: List of snake_case tags (must be in allow-list).
        status: Publication status.
        owner: Owner key (must be in allow-list).
        review_cycle_days: Optional review cycle in days (1-365).
        authors: Optional list of authors with ORCID.
        purpose: One-sentence purpose with terminal punctuation.
        model: Optional model metadata.
        dataset: Optional dataset metadata.
    """

    model_config = ConfigDict(extra="forbid")

    schema_type: Literal["common"] = "common"
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: Literal["draft", "in-review", "published"]
    owner: str
    review_cycle_days: int | None = Field(default=None, ge=1, le=365)
    authors: list[Author] | None = None
    purpose: str
    model: ModelCard | None = None
    dataset: DatasetCard | None = None

    @field_validator("tags", mode="after")
    def _tags(cls, v: list[str]) -> list[str]:  # noqa: N805  # fmt: skip
        """Validate that all tags are snake_case lowercase."""
        bad = [t for t in v if not TAG.fullmatch(t)]
        if bad:
            raise ValueError(f"tags must be snake_case lowercase: {bad}")
        return v

    @field_validator("purpose")
    def _purpose_sentence(cls, v: str) -> str:  # noqa: N805  # fmt: skip
        """Validate that purpose ends with terminal punctuation."""
        if not v.strip().endswith((".", "!", "?")):
            raise ValueError("purpose must end with terminal punctuation")
        return v


class ScriptSpecFM(CommonFM):
    """Front matter schema for script/tool documentation pages.

    Extends CommonFM with script-specific metadata.

    Attributes:
        schema_type: Discriminator field, always "script".
        name: Script/tool name (e.g., "validate_front_matter.py").
        usage: Usage command line example.
        behavior: Description of script behavior.
        inputs: Optional description of inputs.
        outputs: Optional description of outputs.
        dependencies: Optional list of dependencies.
        category: Script category for organization.
    """

    schema_type: Literal["script"] = "script"  # type: ignore[assignment]
    name: str
    usage: str
    behavior: str
    inputs: str | None = None
    outputs: str | None = None
    dependencies: str | None = None
    category: Literal["validation", "data", "build", "docs", "release", "misc"]


class KnowledgeFM(CommonFM):
    """Front matter schema for knowledge base entries.

    Extends CommonFM with knowledge-specific metadata.

    Attributes:
        schema_type: Discriminator field, always "knowledge".
        agent_id: Agent identifier for AI-assisted workflows.
    """

    schema_type: Literal["knowledge"] = "knowledge"  # type: ignore[assignment]
    agent_id: str


class PlanningFM(CommonFM):
    """Front matter schema for planning and strategy documents.

    Extends CommonFM with planning-specific metadata.

    Attributes:
        schema_type: Discriminator field, always "planning".
        component: Planning component category.
        source: Source document or origin.
    """

    schema_type: Literal["planning"] = "planning"  # type: ignore[assignment]
    component: Literal[
        "Strategy",
        "Development-Tools",
        "Context",
        "Request",
        "Examples",
        "Augmentations",
        "Tone-Format",
        "Evaluation",
    ]
    source: str


# Discriminated union type for all front matter schemas
DiscriminatedFM = Annotated[
    ScriptSpecFM | KnowledgeFM | PlanningFM | CommonFM,
    Field(discriminator="schema_type"),
]
