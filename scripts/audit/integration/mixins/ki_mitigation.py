"""Known Issue mitigation mixin (KI-001 through KI-009).

Provides reusable methods for applying cross-dataset known issue
mitigations during enrichment integration. Each method corresponds
to a documented issue in CROSS_DATASET_KNOWN_ISSUES.json.

Usage:
    class MyIntegration(KIMitigationMixin):
        ...
        layout = self.apply_ki_001_layout_casing(raw_detections)
"""

from __future__ import annotations

from typing import Any

from scripts.audit.integration.constants import (
    DOCLING_TO_DOCLAYNET,
    DOCLAYOUT_YOLO_TO_DOCLAYNET,
)


class KIMitigationMixin:
    """Mixin providing KI-001 through KI-009 mitigation methods.

    All methods are stateless and operate on data passed as arguments.
    Configuration (which KIs to apply, VLM true-positive sets) is
    passed per-call rather than stored as instance state, enabling
    reuse across datasets with different KI profiles.
    """

    def apply_ki_001_layout_casing(
        self,
        detections: list[dict[str, Any]],
        *,
        label_map: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """KI-001: Standardize layout label casing to DocLayNet PascalCase.

        Converts lowercase/snake_case Docling labels to PascalCase
        DocLayNet taxonomy. Preserves the original label in source_label.

        Args:
            detections: Raw layout detection dicts from enrichment.
            label_map: Custom label mapping. Defaults to
                DOCLING_TO_DOCLAYNET if None.

        Returns:
            New list of detection dicts with standardized class_name.
        """
        mapping = label_map or DOCLING_TO_DOCLAYNET
        standardized: list[dict[str, Any]] = []
        for det in detections:
            new_det = dict(det)
            original_class = det.get("class_name", "")
            new_det["class_name"] = mapping.get(original_class, original_class)
            if not new_det.get("source_label"):
                new_det["source_label"] = original_class
            standardized.append(new_det)
        return standardized

    def apply_ki_001_doclayout_yolo(
        self,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """KI-001 variant: Standardize DocLayout-YOLO labels to DocLayNet.

        Args:
            detections: Raw layout detection dicts from DocLayout-YOLO.

        Returns:
            New list of detection dicts with standardized class_name.
        """
        return self.apply_ki_001_layout_casing(
            detections, label_map=DOCLAYOUT_YOLO_TO_DOCLAYNET
        )

    def apply_ki_002_table_override(
        self,
        filename_stem: str,
        layout_has_table: bool,
        vlm_true_positives: frozenset[str],
    ) -> bool:
        """KI-002: Override table detection with VLM verification.

        Docling/DocLayout-YOLO classifies multi-column text as Table.
        Only trust has_table=True if the sample is in the VLM-verified
        true positive set.

        Args:
            filename_stem: Image filename stem (without extension).
            layout_has_table: Whether layout detected a table.
            vlm_true_positives: Frozenset of VLM-confirmed table sample IDs.

        Returns:
            True only if VLM confirmed this sample has a real table.
        """
        if not layout_has_table:
            return False
        return filename_stem in vlm_true_positives

    def apply_ki_003_figure_override(
        self,
        filename_stem: str,
        layout_has_figure: bool,
        vlm_true_positives: frozenset[str],
    ) -> bool:
        """KI-003: Override figure detection with VLM verification.

        Docling classifies dense text blocks as Picture. Only trust
        has_figure=True if VLM confirmed.

        Args:
            filename_stem: Image filename stem.
            layout_has_figure: Whether layout detected a figure.
            vlm_true_positives: Frozenset of VLM-confirmed figure sample IDs.

        Returns:
            True only if VLM confirmed this sample has a real figure.
        """
        if not layout_has_figure:
            return False
        return filename_stem in vlm_true_positives

    def apply_ki_004_handwriting_override(
        self,
        filename_stem: str,
        is_synthetic: bool,
        vlm_true_positives: frozenset[str],
    ) -> bool:
        """KI-004: Override handwriting detection on synthetic datasets.

        LLM cannot distinguish rendered text from handwriting on
        synthetic images. For synthetic datasets, always return False.
        For non-synthetic, require VLM confirmation.

        Args:
            filename_stem: Image filename stem.
            is_synthetic: Whether this is a synthetic dataset.
            vlm_true_positives: Frozenset of VLM-confirmed handwriting IDs.

        Returns:
            True only if non-synthetic AND VLM confirmed handwriting.
        """
        if is_synthetic:
            return False
        return filename_stem in vlm_true_positives

    def apply_ki_005_capture_method(
        self,
        is_synthetic: bool,
        known_capture_method: str | None,
        llm_capture: str | None = None,
        llm_confidence: float = 0.5,
    ) -> tuple[str, float, str]:
        """KI-005: Override capture method for synthetic datasets.

        LLM misclassifies synthetic images as born_digital or
        scanner_flatbed. For synthetic datasets, always use
        "synthetic". For known capture methods from documentation,
        use that. Otherwise fall back to LLM.

        Args:
            is_synthetic: Whether this is a synthetic dataset.
            known_capture_method: Known capture method from documentation.
            llm_capture: LLM-detected capture method.
            llm_confidence: LLM confidence for capture method.

        Returns:
            Tuple of (capture_method, confidence, detection_method).
        """
        if is_synthetic:
            return ("synthetic", 1.0, "dataset_documentation")

        if known_capture_method:
            return (known_capture_method, 1.0, "dataset_documentation")

        if llm_capture:
            return (llm_capture, llm_confidence, "llm_vision")

        return ("unknown", 0.3, "none")

    def apply_ki_006_formula_override(
        self,
        filename_stem: str,
        layout_has_formula: bool,
        vlm_true_positives: frozenset[str],
    ) -> bool:
        """KI-006: Override formula detection with VLM verification.

        LLM flags text discussing math/science as has_formula even
        when no rendered equations exist. Only trust has_formula=True
        if VLM confirmed.

        Args:
            filename_stem: Image filename stem.
            layout_has_formula: Whether layout detected a formula.
            vlm_true_positives: Frozenset of VLM-confirmed formula IDs.

        Returns:
            True only if VLM confirmed this sample has a real formula.
        """
        if not layout_has_formula:
            return False
        return filename_stem in vlm_true_positives

    def apply_ki_007_domain_unk(
        self,
        domain: str,
    ) -> str:
        """KI-007: Accept UNK domain classification.

        Generic/narrative/creative text legitimately doesn't fit domain
        categories. UNK is a valid classification, not a defect.

        Args:
            domain: Domain classification string.

        Returns:
            Domain string unchanged (passthrough for documentation).
        """
        return domain

    def apply_ki_008_script_family(
        self,
        iso15924_script: str,
        get_script_family_fn: Any,
    ) -> str:
        """KI-008: Re-derive script_family from ISO 15924 script code.

        Base metadata annotator populates script_family with
        directionality ('ltr', 'rtl') instead of family names
        ('latin', 'cjk', 'arabic'). Always re-derive from the
        script code.

        Args:
            iso15924_script: ISO 15924 script code (e.g., "Latn", "Hans").
            get_script_family_fn: Function that maps script code to family.

        Returns:
            Correct script family string (e.g., "latin", "cjk").
        """
        return get_script_family_fn(iso15924_script)

    def apply_ki_009_language_priority(
        self,
        doc_language: str | None,
        llm_language: str | None,
    ) -> bool:
        """KI-009: Check if documentation language should be overridden.

        Dataset documentation language claims are unreliable. When LLM
        enrichment provides a different language, LLM should take
        priority.

        Args:
            doc_language: Language from dataset documentation.
            llm_language: Language from LLM enrichment.

        Returns:
            True if LLM language differs from documentation (override needed).
        """
        if not doc_language or not llm_language:
            return False
        return (
            doc_language != llm_language
            and llm_language != "und"
            and doc_language != "und"
        )
