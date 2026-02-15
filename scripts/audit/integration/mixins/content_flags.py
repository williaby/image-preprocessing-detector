"""Content flag derivation mixin with VLM override support.

Derives boolean content flags (has_table, has_formula, has_figure,
has_code) from canonical layout classes, then applies VLM-verified
overrides per KI-002 through KI-006.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.audit.integration.constants import (
    CODE_CLASSES,
    FIGURE_CLASSES,
    FORMULA_CLASSES,
    TABLE_CLASSES,
)


@dataclass(frozen=True)
class ContentFlags:
    """Boolean content flags derived from layout detections and VLM overrides.

    Attributes:
        has_table: Whether sample contains a real table.
        has_formula: Whether sample contains rendered math expressions.
        has_figure: Whether sample contains figures/pictures/charts.
        has_code: Whether sample contains code blocks.
        has_handwriting: Whether sample contains handwriting.
        has_signature: Whether sample contains signatures.
        source: Provenance string describing how flags were derived.
        confidence: Confidence in the content flag assessments.
    """

    has_table: bool = False
    has_formula: bool = False
    has_figure: bool = False
    has_code: bool = False
    has_handwriting: bool = False
    has_signature: bool = False
    source: str = "layout_derived"
    confidence: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        """Export content flags as a dict for enrichment data.

        Returns:
            Dict with all flag fields and metadata.
        """
        return {
            "has_table": self.has_table,
            "has_formula": self.has_formula,
            "has_figure": self.has_figure,
            "has_code": self.has_code,
            "has_handwriting": self.has_handwriting,
            "has_signature": self.has_signature,
            "content_flags_source": self.source,
            "content_flags_confidence": self.confidence,
            "content_flags_tier": "tier_2_model",
            "handwriting_present": self.has_handwriting,
        }


class ContentFlagsMixin:
    """Mixin for deriving content flags from layout detections.

    Provides methods to:
    1. Derive raw flags from canonical layout class sets
    2. Apply VLM true-positive overrides (KI-002 through KI-006)
    3. Apply synthetic dataset overrides (KI-004)
    """

    def derive_content_flags(
        self,
        detections: list[dict[str, Any]],
        *,
        table_classes: frozenset[str] | None = None,
        formula_classes: frozenset[str] | None = None,
        figure_classes: frozenset[str] | None = None,
        code_classes: frozenset[str] | None = None,
    ) -> dict[str, bool]:
        """Derive content flags from canonical layout classes.

        Scans all layout detections and checks canonical_class against
        known class sets for table, formula, figure, and code.

        Args:
            detections: List of layout detection dicts, each containing
                at minimum a "canonical_class" or "class_name" key.
            table_classes: Override table class set.
            formula_classes: Override formula class set.
            figure_classes: Override figure class set.
            code_classes: Override code class set.

        Returns:
            Dict with boolean flags: has_table, has_formula, has_figure,
            has_code.
        """
        _table = table_classes or TABLE_CLASSES
        _formula = formula_classes or FORMULA_CLASSES
        _figure = figure_classes or FIGURE_CLASSES
        _code = code_classes or CODE_CLASSES

        canonical_classes: set[str] = set()
        for det in detections:
            class_name = det.get("canonical_class") or det.get("class_name", "")
            if class_name:
                canonical_classes.add(class_name.upper())

        return {
            "has_table": bool(canonical_classes & _table),
            "has_formula": bool(canonical_classes & _formula),
            "has_figure": bool(canonical_classes & _figure),
            "has_code": bool(canonical_classes & _code),
        }

    def apply_vlm_content_flag_overrides(
        self,
        filename_stem: str,
        layout_flags: dict[str, bool],
        *,
        is_synthetic: bool = False,
        vlm_table_tp: frozenset[str] | None = None,
        vlm_figure_tp: frozenset[str] | None = None,
        vlm_formula_tp: frozenset[str] | None = None,
        vlm_handwriting_tp: frozenset[str] | None = None,
    ) -> ContentFlags:
        """Apply VLM overrides to layout-derived content flags.

        For each content flag, if VLM true-positive sets are provided,
        only trust the flag if the sample is in the VLM-verified set.
        Applies KI-002, KI-003, KI-004, KI-006 overrides.

        Args:
            filename_stem: Image filename stem (without extension).
            layout_flags: Raw flags from derive_content_flags().
            is_synthetic: Whether this is a synthetic dataset.
            vlm_table_tp: VLM-confirmed table sample IDs (KI-002).
            vlm_figure_tp: VLM-confirmed figure sample IDs (KI-003).
            vlm_formula_tp: VLM-confirmed formula sample IDs (KI-006).
            vlm_handwriting_tp: VLM-confirmed handwriting IDs (KI-004).

        Returns:
            ContentFlags with VLM-verified values.
        """
        # KI-002: Table override
        has_table = layout_flags.get("has_table", False)
        if vlm_table_tp is not None:
            has_table = filename_stem in vlm_table_tp

        # KI-003: Figure override
        has_figure = layout_flags.get("has_figure", False)
        if vlm_figure_tp is not None:
            has_figure = filename_stem in vlm_figure_tp

        # KI-006: Formula override
        has_formula = layout_flags.get("has_formula", False)
        if vlm_formula_tp is not None:
            has_formula = filename_stem in vlm_formula_tp

        # KI-004: Handwriting override for synthetic
        has_handwriting = False
        if is_synthetic:
            has_handwriting = False
        elif vlm_handwriting_tp is not None:
            has_handwriting = filename_stem in vlm_handwriting_tp

        source = "vlm_corrected+docling_gpu+llm_vision"
        confidence = 0.95

        return ContentFlags(
            has_table=has_table,
            has_formula=has_formula,
            has_figure=has_figure,
            has_code=layout_flags.get("has_code", False),
            has_handwriting=has_handwriting,
            has_signature=False,
            source=source,
            confidence=confidence,
        )

    def apply_synthetic_overrides(
        self,
        flags: ContentFlags,
    ) -> ContentFlags:
        """Apply synthetic dataset overrides to content flags.

        For synthetic datasets, handwriting is always False (KI-004).
        This is a convenience method when VLM true-positive sets are
        not available.

        Args:
            flags: Content flags to override.

        Returns:
            New ContentFlags with synthetic overrides applied.
        """
        return ContentFlags(
            has_table=flags.has_table,
            has_formula=flags.has_formula,
            has_figure=flags.has_figure,
            has_code=flags.has_code,
            has_handwriting=False,
            has_signature=flags.has_signature,
            source=flags.source,
            confidence=flags.confidence,
        )
