"""Dataset integration configuration (Pydantic v2).

Provides DatasetIntegrationConfig as a frozen Pydantic model that
replaces the per-script hardcoded constants. Configs can be loaded
from YAML files for declarative dataset setup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class KIMitigationConfig(BaseModel, frozen=True):
    """Configuration for which KI mitigations to apply.

    Attributes:
        apply_ki_001_layout_casing: Standardize Docling labels to PascalCase.
        layout_source: Which layout extractor was used ("docling" or "doclayout_yolo").
        apply_ki_002_table_override: Override table detection with VLM verification.
        apply_ki_003_figure_override: Override figure detection with VLM verification.
        apply_ki_004_handwriting_override: Override handwriting on synthetic datasets.
        apply_ki_005_capture_override: Override capture method from documentation.
        apply_ki_006_formula_override: Override formula detection with VLM verification.
        apply_ki_008_script_family: Re-derive script_family from ISO 15924.
    """

    apply_ki_001_layout_casing: bool = True
    layout_source: str = "docling"
    apply_ki_002_table_override: bool = True
    apply_ki_003_figure_override: bool = True
    apply_ki_004_handwriting_override: bool = True
    apply_ki_005_capture_override: bool = True
    apply_ki_006_formula_override: bool = True
    apply_ki_008_script_family: bool = True


class VLMCorrections(BaseModel, frozen=True):
    """VLM-verified true positive sample sets for content flag overrides.

    Attributes:
        table_true_positives: Sample IDs with VLM-confirmed real tables.
        figure_true_positives: Sample IDs with VLM-confirmed real figures.
        formula_true_positives: Sample IDs with VLM-confirmed real formulas.
        handwriting_true_positives: Sample IDs with VLM-confirmed handwriting.
    """

    table_true_positives: frozenset[str] = Field(default_factory=frozenset)
    figure_true_positives: frozenset[str] = Field(default_factory=frozenset)
    formula_true_positives: frozenset[str] = Field(default_factory=frozenset)
    handwriting_true_positives: frozenset[str] = Field(default_factory=frozenset)


class DatasetIntegrationConfig(BaseModel, frozen=True):
    """Complete configuration for a dataset integration script.

    Replaces the per-script hardcoded constants at the top of each
    integrate_*_enrichments.py script.

    Attributes:
        dataset_name: Canonical short name (e.g., "jssoda", "doclaynet").
        is_synthetic: Whether this is a synthetic/rendered dataset.
        known_capture_method: Known capture method from documentation.
        metadata_path: Relative path to metadata JSON (from registry root).
        llm_enrichment_path: Relative path to LLM enrichment JSON.
        language_enrichment_path: Relative path to language enrichment JSON.
        skew_labels_path: Path to skew labels JSON (optional).
        resolution_labels_path: Path to resolution labels JSON (optional).
        vlm_enrichment_path: Path to VLM enrichment JSON (optional).
        train_gt_path: Path to dataset-specific GT annotations (optional).
        vlm_text_labels_path: Path to VLM text labels JSON (optional).
        script_version: Version of the integration script.
        enrichment_version_tag: Tag for the enrichment version.
        enrichment_version_number: Numeric version for the enrichment.
        ki_config: KI mitigation toggle configuration.
        vlm_corrections: VLM-verified true positive sets.
        doc_language: Documentation-stated language (fallback).
        doc_script: Documentation-stated script (fallback).
        extra: Additional dataset-specific config values.
    """

    dataset_name: str
    is_synthetic: bool = False
    known_capture_method: str | None = None

    # Paths (relative to registry root unless absolute)
    metadata_path: str = ""
    llm_enrichment_path: str = ""
    language_enrichment_path: str = ""
    skew_labels_path: str | None = None
    resolution_labels_path: str | None = None
    vlm_enrichment_path: str | None = None
    train_gt_path: str | None = None
    vlm_text_labels_path: str | None = None

    # Versioning
    script_version: str = "1.1.0"
    enrichment_version_tag: str = "integrated_v2"
    enrichment_version_number: int = 2

    # KI mitigations and VLM corrections
    ki_config: KIMitigationConfig = Field(default_factory=KIMitigationConfig)
    vlm_corrections: VLMCorrections = Field(default_factory=VLMCorrections)

    # Documentation fallbacks
    doc_language: str | None = None
    doc_script: str | None = None

    # Extra dataset-specific config
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dataset_name")
    @classmethod
    def validate_dataset_name(cls, v: str) -> str:
        """Ensure dataset_name is non-empty and uses kebab-case."""
        if not v or not v.strip():
            msg = "dataset_name must be non-empty"
            raise ValueError(msg)
        return v.strip()

    def resolve_path(
        self,
        relative_path: str | None,
        registry_dir: Path,
    ) -> Path | None:
        """Resolve a relative path against the registry directory.

        Args:
            relative_path: Path string (relative or absolute).
            registry_dir: Base directory for relative paths.

        Returns:
            Resolved Path, or None if relative_path is None/empty.
        """
        if not relative_path:
            return None
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return registry_dir / p

    def get_metadata_path(self, registry_dir: Path) -> Path:
        """Get the full metadata path, using convention if not specified.

        Args:
            registry_dir: Base directory for relative paths.

        Returns:
            Full Path to the metadata JSON file.
        """
        if self.metadata_path:
            return self.resolve_path(self.metadata_path, registry_dir) or registry_dir
        return registry_dir / "json" / f"{self.dataset_name}_metadata.json"

    def get_llm_enrichment_path(self, registry_dir: Path) -> Path:
        """Get the full LLM enrichment path, using convention if not specified.

        Args:
            registry_dir: Base directory for relative paths.

        Returns:
            Full Path to the LLM enrichment JSON file.
        """
        if self.llm_enrichment_path:
            return (
                self.resolve_path(self.llm_enrichment_path, registry_dir)
                or registry_dir
            )
        return registry_dir / "json" / f"{self.dataset_name}_llm_enrichment.json"

    def get_language_enrichment_path(self, registry_dir: Path) -> Path:
        """Get the full language enrichment path.

        Args:
            registry_dir: Base directory for relative paths.

        Returns:
            Full Path to the language enrichment JSON file.
        """
        if self.language_enrichment_path:
            return (
                self.resolve_path(self.language_enrichment_path, registry_dir)
                or registry_dir
            )
        return registry_dir / "json" / f"{self.dataset_name}_language_enrichment.json"


def load_config_from_yaml(path: Path) -> DatasetIntegrationConfig:
    """Load a DatasetIntegrationConfig from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Validated DatasetIntegrationConfig instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        pydantic.ValidationError: If the YAML content is invalid.
    """
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Handle frozenset conversion for VLM corrections
    vlm = raw.get("vlm_corrections", {})
    for key in (
        "table_true_positives",
        "figure_true_positives",
        "formula_true_positives",
        "handwriting_true_positives",
    ):
        if key in vlm and isinstance(vlm[key], list):
            vlm[key] = frozenset(vlm[key])

    return DatasetIntegrationConfig(**raw)
