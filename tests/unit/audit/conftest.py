"""Shared test fixtures for audit integration framework tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def sample_layout_detections_docling() -> list[dict[str, Any]]:
    """Raw Docling layout detections with lowercase labels."""
    return [
        {"class_name": "text", "confidence": 0.92, "bbox": [10, 20, 100, 50]},
        {"class_name": "table", "confidence": 0.88, "bbox": [10, 80, 200, 150]},
        {"class_name": "section_header", "confidence": 0.95, "bbox": [10, 5, 200, 20]},
        {"class_name": "picture", "confidence": 0.75, "bbox": [220, 80, 100, 100]},
        {"class_name": "formula", "confidence": 0.82, "bbox": [10, 200, 150, 30]},
        {"class_name": "code", "confidence": 0.90, "bbox": [10, 250, 180, 60]},
    ]


@pytest.fixture
def sample_layout_detections_standardized() -> list[dict[str, Any]]:
    """Layout detections already standardized to DocLayNet PascalCase."""
    return [
        {
            "class_name": "Text",
            "source_label": "text",
            "confidence": 0.92,
            "bbox": [10, 20, 100, 50],
        },
        {
            "class_name": "Table",
            "source_label": "table",
            "confidence": 0.88,
            "bbox": [10, 80, 200, 150],
        },
        {
            "class_name": "Section-Header",
            "source_label": "section_header",
            "confidence": 0.95,
            "bbox": [10, 5, 200, 20],
        },
        {
            "class_name": "Picture",
            "source_label": "picture",
            "confidence": 0.75,
            "bbox": [220, 80, 100, 100],
        },
    ]


@pytest.fixture
def sample_doclayout_yolo_detections() -> list[dict[str, Any]]:
    """Raw DocLayout-YOLO detections with its own label format."""
    return [
        {"class_name": "plain text", "confidence": 0.91},
        {"class_name": "table", "confidence": 0.87},
        {"class_name": "figure", "confidence": 0.78},
        {"class_name": "isolate_formula", "confidence": 0.80},
        {"class_name": "title", "confidence": 0.93},
    ]


@pytest.fixture
def sample_enrichment_data() -> dict[str, Any]:
    """Enrichment data dict with confidence fields for reliability testing."""
    return {
        "capture_method": "born_digital",
        "capture_confidence": 0.95,
        "domain_level1": "SCI",
        "domain_confidence": 0.72,
        "iso639_language": "en",
        "language_confidence": 0.88,
        "layout_detections": [],
        "layout_confidence": 0.85,
        "content_flags_confidence": 0.90,
    }


@pytest.fixture
def sample_enrichment_data_low_confidence() -> dict[str, Any]:
    """Enrichment data with low confidence scores for edge case testing."""
    return {
        "capture_method": "unknown",
        "capture_confidence": 0.3,
        "domain_level1": "UNK",
        "domain_confidence": 0.4,
        "iso639_language": "und",
        "language_confidence": 0.1,
        "layout_detections": [],
        "layout_confidence": 0.0,
        "content_flags_confidence": 0.45,
    }


@pytest.fixture
def vlm_table_true_positives() -> frozenset[str]:
    """VLM-confirmed table sample IDs."""
    return frozenset({"sample_001", "sample_015", "sample_042"})


@pytest.fixture
def vlm_figure_true_positives() -> frozenset[str]:
    """VLM-confirmed figure sample IDs."""
    return frozenset({"sample_003", "sample_028"})


@pytest.fixture
def vlm_formula_true_positives() -> frozenset[str]:
    """VLM-confirmed formula sample IDs."""
    return frozenset({"sample_005", "sample_007"})


@pytest.fixture
def vlm_handwriting_true_positives() -> frozenset[str]:
    """VLM-confirmed handwriting sample IDs."""
    return frozenset({"sample_010", "sample_033"})
