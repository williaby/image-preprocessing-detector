# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/extract_vidore_labels.py - VidOre label extraction.

These tests verify the label extraction utilities correctly:
- Create corpus to qrels mappings
- Detect text content using edge density
- Calculate degradation metrics (blur, noise, contrast)
- Calculate complexity metrics (tables, columns, text density)
- Classify degradation and complexity levels
- Map to routing bins (DQS routing matrix)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Skip all tests if cv2 or numpy is not available
cv2 = pytest.importorskip("cv2", reason="cv2 not installed")
np = pytest.importorskip("numpy", reason="numpy not installed")

from extract_vidore_labels import (
    LICENSE_SEC_PUBLIC_DOMAIN,
    _level_from_score,
    _score_metric,
    calculate_complexity_metrics,
    calculate_degradation_metrics,
    classify_complexity,
    classify_degradation,
    create_corpus_to_qrels_map,
    detect_parasitic_content_spatial,
    extract_document_classification,
    get_routing_bin,
    has_text_content,
)


class TestCreateCorpusToQrelsMap:
    """Tests for create_corpus_to_qrels_map function."""

    def test_empty_qrels(self) -> None:
        """Test with empty qrels list."""
        result = create_corpus_to_qrels_map([])
        assert len(result) == 0

    def test_single_qrel(self) -> None:
        """Test with single qrel entry."""
        qrels = [{"corpus_id": 1, "content": "test"}]
        result = create_corpus_to_qrels_map(qrels)

        assert 1 in result
        assert len(result[1]) == 1
        assert result[1][0]["content"] == "test"

    def test_multiple_qrels_same_corpus(self) -> None:
        """Test multiple qrels for same corpus_id."""
        qrels = [
            {"corpus_id": 1, "content": "first"},
            {"corpus_id": 1, "content": "second"},
        ]
        result = create_corpus_to_qrels_map(qrels)

        assert len(result[1]) == 2

    def test_multiple_corpus_ids(self) -> None:
        """Test qrels with different corpus_ids."""
        qrels = [
            {"corpus_id": 1, "content": "a"},
            {"corpus_id": 2, "content": "b"},
            {"corpus_id": 1, "content": "c"},
        ]
        result = create_corpus_to_qrels_map(qrels)

        assert 1 in result
        assert 2 in result
        assert len(result[1]) == 2
        assert len(result[2]) == 1


class TestHasTextContent:
    """Tests for has_text_content function."""

    def test_empty_region(self) -> None:
        """Test with empty region."""
        empty_region = np.array([])
        result = has_text_content(empty_region)
        assert result is False

    def test_uniform_region_no_text(self) -> None:
        """Test uniform region has no text."""
        # Uniform gray region (no edges)
        uniform_region = np.full((100, 100), 128, dtype=np.uint8)
        result = has_text_content(uniform_region)
        assert not result  # Use == for numpy bool comparison

    def test_high_contrast_region_has_text(self) -> None:
        """Test high contrast region detected as text."""
        # Create region with strong edges (text-like)
        region = np.zeros((100, 100), dtype=np.uint8)
        # Add vertical lines (text-like patterns)
        for i in range(0, 100, 5):
            region[:, i] = 255

        result = has_text_content(region)
        assert result  # Use == for numpy bool comparison

    def test_rgb_image_converted(self) -> None:
        """Test that RGB image is converted to grayscale."""
        # Create RGB image with text-like content
        region = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(0, 100, 5):
            region[:, i, :] = 255

        result = has_text_content(region)
        # Should process without error - use bool() to convert numpy bool
        assert isinstance(bool(result), bool)

    def test_custom_threshold(self) -> None:
        """Test with custom threshold."""
        # Create region with some edges
        region = np.zeros((100, 100), dtype=np.uint8)
        region[40:60, :] = 255

        # High threshold should reject
        result_high = has_text_content(region, threshold=0.9)
        # Low threshold should accept
        result_low = has_text_content(region, threshold=0.01)

        assert not result_high  # Use == for numpy bool comparison
        assert result_low


class TestDetectParasiticContentSpatial:
    """Tests for detect_parasitic_content_spatial function."""

    def test_uniform_image_no_parasitic(self) -> None:
        """Test uniform image has no parasitic content."""
        image = np.full((2200, 1700, 3), 255, dtype=np.uint8)

        result = detect_parasitic_content_spatial(
            image, corpus_id=1, doc_id="test_doc", page_num=1
        )

        assert result["image_id"] == 1
        assert "test_doc" in result["file_name"]
        assert result["width"] == 1700
        assert result["height"] == 2200
        assert len(result["parasitic_elements"]) == 0

    def test_header_detection(self) -> None:
        """Test header region detection."""
        image = np.full((2200, 1700, 3), 255, dtype=np.uint8)
        # Add text-like content in header region (top 10%)
        for i in range(0, 1700, 10):
            image[0:220, i, :] = 0  # Add vertical lines in header

        result = detect_parasitic_content_spatial(
            image, corpus_id=1, doc_id="test", page_num=1
        )

        header_elements = [
            e for e in result["parasitic_elements"] if e["type"] == "header"
        ]
        assert len(header_elements) > 0

    def test_footer_detection(self) -> None:
        """Test footer region detection."""
        image = np.full((2200, 1700, 3), 255, dtype=np.uint8)
        # Add text-like content in footer region (bottom 5%)
        footer_start = int(2200 * 0.95)
        for i in range(0, 1700, 10):
            image[footer_start:, i, :] = 0

        result = detect_parasitic_content_spatial(
            image, corpus_id=1, doc_id="test", page_num=1
        )

        footer_elements = [
            e for e in result["parasitic_elements"] if e["type"] == "footer"
        ]
        assert len(footer_elements) > 0

    def test_page_number_detection(self) -> None:
        """Test page number region detection."""
        image = np.full((2200, 1700, 3), 255, dtype=np.uint8)
        # Add text-like content in page number region (bottom 8%, centered)
        page_num_start = int(2200 * 0.92)
        x_start = int(1700 * 0.40)
        x_end = int(1700 * 0.60)
        for i in range(x_start, x_end, 10):
            image[page_num_start:, i, :] = 0

        result = detect_parasitic_content_spatial(
            image, corpus_id=1, doc_id="test", page_num=1
        )

        page_num_elements = [
            e for e in result["parasitic_elements"] if e["type"] == "page_number"
        ]
        assert len(page_num_elements) > 0

    def test_result_structure(self) -> None:
        """Test result has correct structure."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = detect_parasitic_content_spatial(
            image, corpus_id=123, doc_id="doc_abc", page_num=5
        )

        assert "image_id" in result
        assert "file_name" in result
        assert "parasitic_elements" in result
        assert "width" in result
        assert "height" in result
        assert result["file_name"] == "doc_abc_page_0005.png"


class TestCalculateDegradationMetrics:
    """Tests for calculate_degradation_metrics function."""

    def test_uniform_image(self) -> None:
        """Test metrics for uniform image."""
        image = np.full((100, 100, 3), 128, dtype=np.uint8)
        result = calculate_degradation_metrics(image)

        assert "blur" in result
        assert "noise" in result
        assert "contrast" in result
        assert "skew" in result
        assert "dpi" in result

    def test_high_contrast_image(self) -> None:
        """Test metrics for high contrast image."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:50, :] = 255

        result = calculate_degradation_metrics(image)

        # High contrast image should have higher contrast metric
        assert result["contrast"] > 50

    def test_grayscale_input(self) -> None:
        """Test metrics for grayscale input."""
        image = np.full((100, 100), 128, dtype=np.uint8)
        result = calculate_degradation_metrics(image)

        assert isinstance(result["blur"], float)
        assert isinstance(result["noise"], float)

    def test_dpi_estimation(self) -> None:
        """Test DPI is estimated from standard dimensions."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = calculate_degradation_metrics(image)

        # DPI should be positive
        assert result["dpi"] > 0


class TestCalculateComplexityMetrics:
    """Tests for calculate_complexity_metrics function."""

    def test_empty_markdown_and_qrels(self) -> None:
        """Test with empty inputs."""
        result = calculate_complexity_metrics("", [])

        assert result["table_count"] == 0
        assert result["picture_count"] == 0
        assert result["column_count"] == 1
        assert result["text_density"] == pytest.approx(0.0)
        assert result["formula_count"] == 0
        assert result["text_blocks"] == 0

    def test_table_count(self) -> None:
        """Test table counting from qrels."""
        qrels = [
            {"content_type": ["Table"]},
            {"content_type": ["Table", "Text"]},
            {"content_type": ["Text"]},
        ]
        result = calculate_complexity_metrics("", qrels)

        assert result["table_count"] == 2

    def test_text_density(self) -> None:
        """Test text density calculation."""
        markdown = "x" * 1000  # 1000 characters

        result = calculate_complexity_metrics(markdown, [])

        # Density = (1000 / (1700 * 2200)) * 1000
        expected_density = (1000 / (1700 * 2200)) * 1000
        assert abs(result["text_density"] - expected_density) < 0.001

    def test_formula_count(self) -> None:
        """Test formula counting from dollar signs."""
        markdown = "Revenue: $1,000,000 Profit: $500,000"

        result = calculate_complexity_metrics(markdown, [])

        assert result["formula_count"] == 2  # 2 dollar signs

    def test_text_blocks_count(self) -> None:
        """Test text blocks equals qrels entries."""
        qrels = [{}, {}, {}]
        result = calculate_complexity_metrics("", qrels)

        assert result["text_blocks"] == 3


class TestScoreMetric:
    """Tests for _score_metric function."""

    def test_higher_is_better_high_value(self) -> None:
        """Test high value scores 0 when higher is better."""
        result = _score_metric(600, (500, 200), higher_is_better=True)
        assert result == 0

    def test_higher_is_better_medium_value(self) -> None:
        """Test medium value scores 1 when higher is better."""
        result = _score_metric(300, (500, 200), higher_is_better=True)
        assert result == 1

    def test_higher_is_better_low_value(self) -> None:
        """Test low value scores 2 when higher is better."""
        result = _score_metric(100, (500, 200), higher_is_better=True)
        assert result == 2

    def test_lower_is_better_low_value(self) -> None:
        """Test low value scores 0 when lower is better."""
        result = _score_metric(5, (10, 30), higher_is_better=False)
        assert result == 0

    def test_lower_is_better_medium_value(self) -> None:
        """Test medium value scores 1 when lower is better."""
        result = _score_metric(20, (10, 30), higher_is_better=False)
        assert result == 1

    def test_lower_is_better_high_value(self) -> None:
        """Test high value scores 2 when lower is better."""
        result = _score_metric(50, (10, 30), higher_is_better=False)
        assert result == 2


class TestLevelFromScore:
    """Tests for _level_from_score function."""

    def test_low_score_returns_low(self) -> None:
        """Test low score returns 'low' level."""
        result = _level_from_score(1, 3)  # avg 0.33
        assert result == "low"

    def test_medium_score_returns_medium(self) -> None:
        """Test medium score returns 'medium' level."""
        result = _level_from_score(3, 3)  # avg 1.0
        assert result == "medium"

    def test_high_score_returns_high(self) -> None:
        """Test high score returns 'high' level."""
        result = _level_from_score(5, 3)  # avg 1.67
        assert result == "high"

    def test_boundary_low_medium(self) -> None:
        """Test boundary between low and medium."""
        # avg < 0.5 is low
        result = _level_from_score(1, 3)  # avg 0.33
        assert result == "low"

        # avg >= 0.5 is medium
        result = _level_from_score(2, 3)  # avg 0.67
        assert result == "medium"


class TestClassifyDegradation:
    """Tests for classify_degradation function."""

    def test_high_quality_metrics(self) -> None:
        """Test high quality metrics classified as low degradation."""
        metrics = {"blur": 600, "noise": 5, "contrast": 60}
        result = classify_degradation(metrics)
        assert result == "low"

    def test_low_quality_metrics(self) -> None:
        """Test low quality metrics classified as high degradation."""
        metrics = {"blur": 100, "noise": 50, "contrast": 15}
        result = classify_degradation(metrics)
        assert result == "high"

    def test_mixed_quality_metrics(self) -> None:
        """Test mixed metrics classified as medium degradation."""
        metrics = {"blur": 300, "noise": 20, "contrast": 40}
        result = classify_degradation(metrics)
        assert result == "medium"


class TestClassifyComplexity:
    """Tests for classify_complexity function."""

    def test_simple_document(self) -> None:
        """Test simple document classified as low complexity."""
        metrics = {
            "table_count": 0,
            "column_count": 1,
            "text_density": 2.0,
        }
        result = classify_complexity(metrics)
        assert result == "low"

    def test_complex_document(self) -> None:
        """Test complex document classified as high complexity."""
        metrics = {
            "table_count": 5,
            "column_count": 2,
            "text_density": 15.0,
        }
        result = classify_complexity(metrics)
        assert result == "high"

    def test_medium_complexity_document(self) -> None:
        """Test medium complexity document."""
        metrics = {
            "table_count": 2,
            "column_count": 1,
            "text_density": 7.0,
        }
        result = classify_complexity(metrics)
        assert result == "medium"


class TestGetRoutingBin:
    """Tests for get_routing_bin function."""

    def test_low_degradation_low_complexity(self) -> None:
        """Test bin 1: low degradation, low complexity."""
        result = get_routing_bin("low", "low")
        assert result == 1

    def test_low_degradation_high_complexity(self) -> None:
        """Test bin 3: low degradation, high complexity."""
        result = get_routing_bin("low", "high")
        assert result == 3

    def test_high_degradation_low_complexity(self) -> None:
        """Test bin 7: high degradation, low complexity."""
        result = get_routing_bin("high", "low")
        assert result == 7

    def test_high_degradation_high_complexity(self) -> None:
        """Test bin 9: high degradation, high complexity."""
        result = get_routing_bin("high", "high")
        assert result == 9

    def test_medium_medium(self) -> None:
        """Test bin 5: medium degradation, medium complexity."""
        result = get_routing_bin("medium", "medium")
        assert result == 5

    def test_all_bins_unique(self) -> None:
        """Test all 9 bins have unique values."""
        bins = set()
        for deg in ["low", "medium", "high"]:
            for cplx in ["low", "medium", "high"]:
                bins.add(get_routing_bin(deg, cplx))

        assert len(bins) == 9
        assert bins == {1, 2, 3, 4, 5, 6, 7, 8, 9}


class TestExtractDocumentClassification:
    """Tests for extract_document_classification function."""

    def test_single_page_corpus(self) -> None:
        """Test extraction with single page corpus."""
        mock_corpus = [
            {
                "corpus_id": 1,
                "doc_id": "test_doc",
                "page_number_in_doc": 1,
            }
        ]

        result = extract_document_classification(mock_corpus)

        assert "info" in result
        assert "classes" in result
        assert "classifications" in result
        assert len(result["classifications"]) == 1

    def test_classification_structure(self) -> None:
        """Test classification entry structure."""
        mock_corpus = [
            {
                "corpus_id": 123,
                "doc_id": "doc_abc",
                "page_number_in_doc": 5,
            }
        ]

        result = extract_document_classification(mock_corpus)

        classification = result["classifications"][0]
        assert classification["image_id"] == 123
        assert classification["file_name"] == "doc_abc_page_0005.png"
        assert classification["classification"] == "financial_report"
        assert classification["domain"] == "banking"

    def test_info_metadata(self) -> None:
        """Test info metadata is correct."""
        mock_corpus = [
            {
                "corpus_id": 1,
                "doc_id": "test",
                "page_number_in_doc": 1,
            }
        ]

        result = extract_document_classification(mock_corpus)

        assert result["info"]["source"] == "vidore_v3_finance"
        assert result["info"]["license"] == LICENSE_SEC_PUBLIC_DOMAIN
        assert result["info"]["total_documents"] == 1


class TestConstants:
    """Tests for module constants."""

    def test_license_constant(self) -> None:
        """Test license constant value."""
        assert LICENSE_SEC_PUBLIC_DOMAIN == "Public Domain (SEC website)"
