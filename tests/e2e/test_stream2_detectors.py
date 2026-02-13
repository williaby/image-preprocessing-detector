# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""End-to-end integration tests for Stream 2 heuristic detectors.

Verifies that all Stream 2 detectors produce valid output types
that match schema fields, and that the full detector chain works
on synthetic document images.
"""

from __future__ import annotations

from typing import Literal
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.classification.degradation_classifier import (
    DegradationClassification,
    DegradationInput,
    classify_degradation_severity,
)
from image_preprocessing_detector.classification.document_source_classifier import (
    DocumentSourceResult,
    classify_document_source,
)
from image_preprocessing_detector.classification.text_layer_analyzer import (
    TextLayerAnalysisResult,
    TextLayerAnalyzer,
)
from image_preprocessing_detector.detection.blank_page_detector import (
    BlankPageResult,
    detect_blank_page,
)
from image_preprocessing_detector.detection.code_detector import (
    CodeDetectionResult,
    detect_code,
)
from image_preprocessing_detector.detection.handwriting_detector import (
    HandwritingDetectionResult,
    detect_handwriting,
)
from image_preprocessing_detector.detection.script_detector import (
    detect_script_heuristic,
)
from image_preprocessing_detector.detection.shadow_detector import (
    ShadowDetectionResult,
    detect_shadows,
)
from image_preprocessing_detector.detection.table_complexity import (
    analyze_table_complexity,
)
from image_preprocessing_detector.detection.warping_detector import (
    WarpingDetectionResult,
    detect_warping_distortion,
)
from image_preprocessing_detector.routing.psm_recommender import (
    PSMInput,
    PSMRecommendation,
    recommend_psm,
)
from image_preprocessing_detector.schema import (
    HandwritingAssessment,
    HandwritingPresence,
    ScriptDetectionResult,
    TableComplexity,
)

# ============================================================================
# Fixtures: Synthetic document images
# ============================================================================


@pytest.fixture
def white_page() -> np.ndarray:
    """Pure white page (blank document)."""
    return np.ones((600, 400, 3), dtype=np.uint8) * 255


@pytest.fixture
def document_image() -> np.ndarray:
    """Synthetic document with text-like content."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 245
    rng = np.random.default_rng(42)
    # Draw text-like horizontal bars
    for row in range(10):
        y = 80 + row * 60
        x_start = 50
        num_words = rng.integers(3, 8)
        x = x_start
        for _ in range(num_words):
            word_w = rng.integers(30, 80)
            word_h = rng.integers(12, 18)
            cv2.rectangle(img, (x, y), (x + word_w, y + word_h), (30, 30, 30), -1)
            x += word_w + rng.integers(8, 15)
    return img


@pytest.fixture
def table_image() -> np.ndarray:
    """Synthetic image with a simple table grid."""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    # Draw a 4x3 grid
    for row in range(5):
        y = 50 + row * 75
        cv2.line(img, (50, y), (350, y), (0, 0, 0), 2)
    for col in range(4):
        x = 50 + col * 100
        cv2.line(img, (x, 50), (x, 350), (0, 0, 0), 2)
    return img


# ============================================================================
# Test 1: Blank page detector triggers early exit
# ============================================================================


class TestBlankPageEarlyExit:
    """Blank page detector correctly identifies blank pages."""

    def test_white_page_is_blank(self, white_page: np.ndarray) -> None:
        """White image is detected as blank."""
        result = detect_blank_page(white_page)
        assert isinstance(result, BlankPageResult)
        assert result.is_blank is True
        assert result.blankness_score > 0.5

    def test_document_is_not_blank(self, document_image: np.ndarray) -> None:
        """Document with content is not blank."""
        result = detect_blank_page(document_image)
        assert isinstance(result, BlankPageResult)
        assert result.is_blank is False

    def test_blank_page_skips_further_processing(self, white_page: np.ndarray) -> None:
        """Simulate pipeline early exit on blank detection."""
        blank_result = detect_blank_page(white_page)
        assert blank_result.is_blank

        # In a real pipeline, we'd skip all other detectors
        # Here we verify the result has all fields needed for the decision
        assert 0.0 <= blank_result.confidence <= 1.0
        assert 0.0 <= blank_result.blankness_score <= 1.0


# ============================================================================
# Test 2: Handwriting detector → HandwritingAssessment schema
# ============================================================================


class TestHandwritingToAssessment:
    """Handwriting detector result converts to HandwritingAssessment correctly."""

    def test_no_handwriting_assessment(self, document_image: np.ndarray) -> None:
        """Document with printed-like text produces appropriate assessment."""
        result = detect_handwriting(document_image)
        assert isinstance(result, HandwritingDetectionResult)

        assessment = result.to_assessment()
        assert isinstance(assessment, HandwritingAssessment)
        assert assessment.detection_method == "heuristic"
        assert 0.0 <= assessment.presence_score <= 1.0
        assert assessment.presence_confidence >= 0.0

    def test_assessment_presence_enum_valid(self, document_image: np.ndarray) -> None:
        """HandwritingPresence enum is always valid."""
        result = detect_handwriting(document_image)
        assessment = result.to_assessment()

        # Presence should be a valid HandwritingPresence member
        assert isinstance(assessment.presence, int)
        valid_values = {p.value for p in HandwritingPresence}
        assert assessment.presence in valid_values

    def test_assessment_scores_bounded(self, white_page: np.ndarray) -> None:
        """All assessment scores are in [0, 1]."""
        result = detect_handwriting(white_page)
        assessment = result.to_assessment()

        assert 0.0 <= assessment.presence_score <= 1.0
        assert 0.0 <= assessment.legibility_score <= 1.0
        assert 0.0 <= assessment.presence_confidence <= 1.0
        assert 0.0 <= assessment.legibility_confidence <= 1.0
        assert 0.0 <= assessment.content_type_confidence <= 1.0


# ============================================================================
# Test 3: Full detector chain on synthetic document
# ============================================================================


class TestFullDetectorChain:
    """All detectors produce valid output types matching schema fields."""

    def test_all_detection_detectors(self, document_image: np.ndarray) -> None:
        """Run all detection-module detectors on a document image."""
        # Blank page
        blank = detect_blank_page(document_image)
        assert isinstance(blank, BlankPageResult)
        assert blank.is_blank is False

        # Shadows
        shadows = detect_shadows(document_image)
        assert isinstance(shadows, ShadowDetectionResult)
        assert 0.0 <= shadows.shadow_score <= 1.0
        assert shadows.shadow_severity in ("none", "mild", "moderate", "severe")

        # Warping
        warping = detect_warping_distortion(document_image)
        assert isinstance(warping, WarpingDetectionResult)
        assert 0.0 <= warping.warping_score <= 1.0

        # Code
        code = detect_code(document_image)
        assert isinstance(code, CodeDetectionResult)
        assert 0.0 <= code.code_confidence <= 1.0

        # Handwriting
        hw = detect_handwriting(document_image)
        assert isinstance(hw, HandwritingDetectionResult)
        assert 0.0 <= hw.handwriting_score <= 1.0

        # Script
        script = detect_script_heuristic(document_image)
        assert isinstance(script, ScriptDetectionResult)
        assert len(script.detected_script) == 4

    def test_all_classification_modules(self, document_image: np.ndarray) -> None:
        """Run all classification-module classifiers."""
        # Document source
        source = classify_document_source(document_image)
        assert isinstance(source, DocumentSourceResult)
        assert 0.0 <= source.scanner_score <= 1.0

        # Degradation severity
        degradation_input = DegradationInput(
            capture_method=source.capture_method,
            dqs_score=0.7,
            has_shadows=False,
            has_warping=False,
            has_handwriting=False,
            has_bleed_through=False,
        )
        degradation = classify_degradation_severity(degradation_input)
        assert isinstance(degradation, DegradationClassification)
        assert degradation.severity in ("simple", "complex")

    def test_routing_modules(self) -> None:
        """Run routing module with typical inputs."""
        psm_input = PSMInput(
            layout_type="single_column",
            has_tables=False,
            is_sparse=False,
            has_handwriting=False,
            orientation_confidence=0.9,
            element_count=10,
        )
        rec = recommend_psm(psm_input)
        assert isinstance(rec, PSMRecommendation)
        assert 0 <= rec.psm <= 13

    def test_table_complexity_analyzer(self, table_image: np.ndarray) -> None:
        """Table complexity analyzer produces valid TableComplexity."""
        result = analyze_table_complexity(table_image)
        assert isinstance(result, TableComplexity)
        assert 0.0 <= result.complexity_score <= 1.0
        assert result.estimated_rows >= 0
        assert result.estimated_columns >= 0


# ============================================================================
# Test 4: Script detector returns valid ISO 15924 codes
# ============================================================================


class TestScriptDetectorISO15924:
    """ScriptDetectorHeuristic returns valid ISO codes with distribution."""

    def test_returns_valid_iso_code(self, document_image: np.ndarray) -> None:
        """Detected script is always a 4-character ISO 15924 code."""
        result = detect_script_heuristic(document_image)
        assert isinstance(result, ScriptDetectionResult)
        assert len(result.detected_script) == 4
        assert result.detected_script[0].isupper()

    def test_probability_distribution_sums_to_one(
        self, document_image: np.ndarray
    ) -> None:
        """Script probabilities sum approximately to 1.0."""
        result = detect_script_heuristic(document_image)
        if result.script_probabilities:
            total = sum(result.script_probabilities.values())
            assert abs(total - 1.0) < 0.05, f"Probabilities sum to {total}"
            # All probabilities are non-negative
            assert all(p >= 0.0 for p in result.script_probabilities.values())

    def test_unknown_for_blank_page(self, white_page: np.ndarray) -> None:
        """Blank page returns unknown script."""
        result = detect_script_heuristic(white_page)
        assert result.detected_script == "Zzzz"
        assert result.is_unknown is True

    def test_detection_method_is_heuristic(self, document_image: np.ndarray) -> None:
        """Detection method is always 'heuristic'."""
        result = detect_script_heuristic(document_image)
        assert result.detection_method == "heuristic"


# ============================================================================
# Test 5: Detector outputs map to schema fields
# ============================================================================


class TestSchemaFieldMapping:
    """Verify detector outputs match the types expected by schema fields."""

    def test_shadow_maps_to_page_layout_summary(
        self, document_image: np.ndarray
    ) -> None:
        """Shadow detector output types match PageLayoutSummary fields."""
        result = detect_shadows(document_image)
        # These fields exist on PageLayoutSummary
        _: bool = result.has_shadows
        _score: float = result.shadow_score
        _severity: Literal["none", "mild", "moderate", "severe"] = (
            result.shadow_severity
        )

    def test_warping_maps_to_page_layout_summary(
        self, document_image: np.ndarray
    ) -> None:
        """Warping detector output types match PageLayoutSummary fields."""
        result = detect_warping_distortion(document_image)
        _: bool = result.has_warping
        _score: float = result.warping_score
        _type: str | None = result.warping_type

    def test_code_maps_to_page_layout_summary(self, document_image: np.ndarray) -> None:
        """Code detector output types match PageLayoutSummary fields."""
        result = detect_code(document_image)
        _: bool = result.has_code
        _conf: float = result.code_confidence

    def test_degradation_maps_to_document_metadata(self) -> None:
        """Degradation classifier output matches DocumentMetadata field."""
        result = classify_degradation_severity(DegradationInput())
        # DocumentMetadata.degradation_severity is Literal["simple", "complex"]
        assert result.severity in ("simple", "complex")

    def test_psm_maps_to_document_metadata(self) -> None:
        """PSM recommender output matches DocumentMetadata field."""
        rec = recommend_psm(PSMInput())
        # DocumentMetadata.recommended_psm is int | None, ge=0, le=13
        assert isinstance(rec.psm, int)
        assert 0 <= rec.psm <= 13


# ============================================================================
# Test 6: Text layer analyzer with mocked PyMuPDF
# ============================================================================


class TestTextLayerAnalyzerE2E:
    """Text layer analyzer integration with mocked fitz."""

    def test_high_quality_pdf_skip_ocr(self) -> None:
        """High-quality PDF text layer enables OCR skip."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Clean text content with many words " * 50
        mock_page.get_text_words.return_value = [
            (100.5, 200.3, 150.7, 220.1, "word", 0, 0, i) for i in range(50)
        ]
        mock_page.get_fonts.return_value = [
            (0, "TrueType", "Type1", "Helvetica", "Helv", 1),
        ]

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.page_count = 1

        with patch(
            "image_preprocessing_detector.classification.text_layer_analyzer.fitz"
        ) as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            analyzer = TextLayerAnalyzer()
            result = analyzer.analyze("test.pdf")

        assert isinstance(result, TextLayerAnalysisResult)
        assert result.text_layer_quality > 0.5
        assert result.text_layer_skip_ocr is True
        assert 0.0 <= result.confidence <= 1.0

    def test_no_text_pdf_requires_ocr(self) -> None:
        """PDF with no text layer requires OCR."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_page.get_text_words.return_value = []
        mock_page.get_fonts.return_value = []

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.page_count = 1

        with patch(
            "image_preprocessing_detector.classification.text_layer_analyzer.fitz"
        ) as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            analyzer = TextLayerAnalyzer()
            result = analyzer.analyze("test.pdf")

        assert isinstance(result, TextLayerAnalysisResult)
        assert result.text_layer_skip_ocr is False
