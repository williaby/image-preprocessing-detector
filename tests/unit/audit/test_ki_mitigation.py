"""Tests for KI mitigation mixin (KI-001 through KI-009)."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.audit.integration.mixins.ki_mitigation import KIMitigationMixin


@pytest.fixture
def mixin() -> KIMitigationMixin:
    """Create a KIMitigationMixin instance."""
    return KIMitigationMixin()


class TestKI001LayoutCasing:
    """Tests for KI-001: Docling layout label casing standardization."""

    def test_converts_lowercase_to_pascalcase(
        self,
        mixin: KIMitigationMixin,
        sample_layout_detections_docling: list[dict[str, Any]],
    ) -> None:
        result = mixin.apply_ki_001_layout_casing(sample_layout_detections_docling)
        class_names = [d["class_name"] for d in result]
        assert "Text" in class_names
        assert "Table" in class_names
        assert "Section-Header" in class_names
        assert "Picture" in class_names

    def test_preserves_source_label(
        self,
        mixin: KIMitigationMixin,
        sample_layout_detections_docling: list[dict[str, Any]],
    ) -> None:
        result = mixin.apply_ki_001_layout_casing(sample_layout_detections_docling)
        assert result[0]["source_label"] == "text"
        assert result[2]["source_label"] == "section_header"

    def test_passthrough_unknown_labels(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        detections = [{"class_name": "unknown_class", "confidence": 0.5}]
        result = mixin.apply_ki_001_layout_casing(detections)
        assert result[0]["class_name"] == "unknown_class"

    def test_custom_label_map(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        custom_map = {"foo": "Bar", "baz": "Qux"}
        detections = [
            {"class_name": "foo", "confidence": 0.9},
            {"class_name": "baz", "confidence": 0.8},
        ]
        result = mixin.apply_ki_001_layout_casing(detections, label_map=custom_map)
        assert result[0]["class_name"] == "Bar"
        assert result[1]["class_name"] == "Qux"

    def test_empty_detections(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        result = mixin.apply_ki_001_layout_casing([])
        assert result == []

    def test_does_not_mutate_input(
        self,
        mixin: KIMitigationMixin,
        sample_layout_detections_docling: list[dict[str, Any]],
    ) -> None:
        original_class = sample_layout_detections_docling[0]["class_name"]
        mixin.apply_ki_001_layout_casing(sample_layout_detections_docling)
        assert sample_layout_detections_docling[0]["class_name"] == original_class

    def test_preserves_existing_source_label(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        detections = [
            {"class_name": "text", "source_label": "original_text", "confidence": 0.9}
        ]
        result = mixin.apply_ki_001_layout_casing(detections)
        assert result[0]["source_label"] == "original_text"
        assert result[0]["class_name"] == "Text"


class TestKI001DocLayoutYolo:
    """Tests for KI-001 DocLayout-YOLO variant."""

    def test_converts_doclayout_yolo_labels(
        self,
        mixin: KIMitigationMixin,
        sample_doclayout_yolo_detections: list[dict[str, Any]],
    ) -> None:
        result = mixin.apply_ki_001_doclayout_yolo(sample_doclayout_yolo_detections)
        class_names = [d["class_name"] for d in result]
        assert "Text" in class_names
        assert "Table" in class_names
        assert "Picture" in class_names
        assert "Formula" in class_names
        assert "Title" in class_names


class TestKI002TableOverride:
    """Tests for KI-002: Table detection VLM override."""

    def test_true_positive_confirmed(
        self,
        mixin: KIMitigationMixin,
        vlm_table_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_002_table_override(
            "sample_001", True, vlm_table_true_positives
        )
        assert result is True

    def test_false_positive_overridden(
        self,
        mixin: KIMitigationMixin,
        vlm_table_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_002_table_override(
            "sample_999", True, vlm_table_true_positives
        )
        assert result is False

    def test_no_table_stays_false(
        self,
        mixin: KIMitigationMixin,
        vlm_table_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_002_table_override(
            "sample_001", False, vlm_table_true_positives
        )
        assert result is False


class TestKI003FigureOverride:
    """Tests for KI-003: Figure detection VLM override."""

    def test_true_positive_confirmed(
        self,
        mixin: KIMitigationMixin,
        vlm_figure_true_positives: frozenset[str],
    ) -> None:
        assert (
            mixin.apply_ki_003_figure_override(
                "sample_003", True, vlm_figure_true_positives
            )
            is True
        )

    def test_false_positive_overridden(
        self,
        mixin: KIMitigationMixin,
        vlm_figure_true_positives: frozenset[str],
    ) -> None:
        assert (
            mixin.apply_ki_003_figure_override(
                "sample_999", True, vlm_figure_true_positives
            )
            is False
        )


class TestKI004HandwritingOverride:
    """Tests for KI-004: Handwriting detection on synthetic datasets."""

    def test_synthetic_always_false(
        self,
        mixin: KIMitigationMixin,
        vlm_handwriting_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_004_handwriting_override(
            "sample_010", True, vlm_handwriting_true_positives
        )
        assert result is False

    def test_non_synthetic_vlm_confirmed(
        self,
        mixin: KIMitigationMixin,
        vlm_handwriting_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_004_handwriting_override(
            "sample_010", False, vlm_handwriting_true_positives
        )
        assert result is True

    def test_non_synthetic_not_confirmed(
        self,
        mixin: KIMitigationMixin,
        vlm_handwriting_true_positives: frozenset[str],
    ) -> None:
        result = mixin.apply_ki_004_handwriting_override(
            "sample_999", False, vlm_handwriting_true_positives
        )
        assert result is False


class TestKI005CaptureMethod:
    """Tests for KI-005: Synthetic capture method override."""

    def test_synthetic_override(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        result = mixin.apply_ki_005_capture_method(
            is_synthetic=True,
            known_capture_method=None,
            llm_capture="born_digital",
        )
        assert result == ("synthetic", 1.0, "dataset_documentation")

    def test_known_capture_method(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        result = mixin.apply_ki_005_capture_method(
            is_synthetic=False,
            known_capture_method="scanner_flatbed",
        )
        assert result == ("scanner_flatbed", 1.0, "dataset_documentation")

    def test_llm_fallback(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        result = mixin.apply_ki_005_capture_method(
            is_synthetic=False,
            known_capture_method=None,
            llm_capture="camera_smartphone",
            llm_confidence=0.6,
        )
        assert result == ("camera_smartphone", 0.6, "llm_vision")

    def test_no_source_fallback(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        result = mixin.apply_ki_005_capture_method(
            is_synthetic=False,
            known_capture_method=None,
        )
        assert result == ("unknown", 0.3, "none")


class TestKI006FormulaOverride:
    """Tests for KI-006: Formula detection VLM override."""

    def test_true_positive_confirmed(
        self,
        mixin: KIMitigationMixin,
        vlm_formula_true_positives: frozenset[str],
    ) -> None:
        assert (
            mixin.apply_ki_006_formula_override(
                "sample_005", True, vlm_formula_true_positives
            )
            is True
        )

    def test_false_positive_overridden(
        self,
        mixin: KIMitigationMixin,
        vlm_formula_true_positives: frozenset[str],
    ) -> None:
        assert (
            mixin.apply_ki_006_formula_override(
                "sample_999", True, vlm_formula_true_positives
            )
            is False
        )


class TestKI007DomainUNK:
    """Tests for KI-007: Accept UNK domain classification."""

    def test_unk_passthrough(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_007_domain_unk("UNK") == "UNK"

    def test_non_unk_passthrough(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_007_domain_unk("SCI") == "SCI"


class TestKI008ScriptFamily:
    """Tests for KI-008: Re-derive script_family from ISO 15924."""

    def test_derives_latin(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        def mock_fn(s):
            return {"Latn": "latin", "Hans": "cjk"}.get(s, "unknown")

        assert mixin.apply_ki_008_script_family("Latn", mock_fn) == "latin"

    def test_derives_cjk(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        def mock_fn(s):
            return {"Latn": "latin", "Hans": "cjk"}.get(s, "unknown")

        assert mixin.apply_ki_008_script_family("Hans", mock_fn) == "cjk"

    def test_unknown_script(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        def mock_fn(s):
            return "unknown"

        assert mixin.apply_ki_008_script_family("Zzzz", mock_fn) == "unknown"


class TestKI009LanguagePriority:
    """Tests for KI-009: Documentation language override check."""

    def test_override_needed(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_009_language_priority("en", "zh") is True

    def test_no_override_same_language(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_009_language_priority("en", "en") is False

    def test_no_override_llm_und(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_009_language_priority("en", "und") is False

    def test_no_override_doc_none(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_009_language_priority(None, "zh") is False

    def test_no_override_doc_und(
        self,
        mixin: KIMitigationMixin,
    ) -> None:
        assert mixin.apply_ki_009_language_priority("und", "zh") is False
