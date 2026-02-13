# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for RVL-CDIP document classification parser.

Tests cover:
    - Filename-based document class extraction (16 classes)
    - Layout annotation extraction from COCO JSON files
    - OCR text extraction from JSONL files
    - Text statistics calculation
    - Error handling and missing data scenarios
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.parsers.document.rvl_cdip import (
    RvlCdipParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels


class TestRvlCdipParser:
    """Test suite for RVL-CDIP parser."""

    @pytest.fixture
    def parser(self) -> RvlCdipParser:
        """Create RvlCdipParser instance."""
        return RvlCdipParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock RVL-CDIP dataset structure with annotations."""
        dataset = tmp_path / "rvl_cdip"
        dataset.mkdir()

        # Create images directory
        images_dir = dataset / "images"
        images_dir.mkdir()

        # Create annotations directory structure
        annotations_dir = dataset / "annotations" / "rvl-cdip"
        annotations_dir.mkdir(parents=True)

        # Create layout annotations directory with COCO format
        layout_dir = annotations_dir / "layout"
        layout_dir.mkdir()

        # Sample COCO layout annotations (DocLayNet format)
        layout_data = {
            "info": {
                "description": "RVL-CDIP Layout Annotations",
                "version": "1.0",
            },
            "categories": [
                {"id": 0, "name": "Caption"},
                {"id": 1, "name": "Footnote"},
                {"id": 2, "name": "Formula"},
                {"id": 8, "name": "Table"},
                {"id": 9, "name": "Text"},
            ],
            "images": [
                {
                    "id": 0,
                    "file_name": "rvl_advertisement_0000.jpg",
                    "gcs_path": "image-preprocessing-detector/datasets/rvl_cdip/rvl_cdip/images/rvl_advertisement_0000.jpg",
                },
                {
                    "id": 1,
                    "file_name": "rvl_invoice_1234.jpg",
                    "gcs_path": "image-preprocessing-detector/datasets/rvl_cdip/rvl_cdip/images/rvl_invoice_1234.jpg",
                },
            ],
            "annotations": [
                {
                    "id": 0,
                    "bbox": [100.0, 200.0, 300.0, 50.0],
                    "category_id": 9,
                    "category_name": "Text",
                    "confidence": 0.95,
                    "area": 15000.0,
                    "image_id": 0,
                },
                {
                    "id": 1,
                    "bbox": [100.0, 300.0, 400.0, 200.0],
                    "category_id": 8,
                    "category_name": "Table",
                    "confidence": 0.88,
                    "area": 80000.0,
                    "image_id": 0,
                },
                {
                    "id": 2,
                    "bbox": [50.0, 100.0, 200.0, 30.0],
                    "category_id": 2,
                    "category_name": "Formula",
                    "confidence": 0.92,
                    "area": 6000.0,
                    "image_id": 1,
                },
            ],
        }

        layout_file = layout_dir / "layout_batch_0.json"
        with open(layout_file, "w") as f:
            json.dump(layout_data, f)

        # Create OCR annotations directory with JSONL format
        ocr_dir = annotations_dir / "ocr"
        ocr_dir.mkdir()

        # Sample OCR entries
        ocr_entries = [
            {
                "source": "image-preprocessing-detector/datasets/rvl_cdip/rvl_cdip/images/rvl_advertisement_0000.jpg",
                "text": "ACME Corporation\n\nSpecial Offer!\n\nGet 50% off all products this month.\nVisit www.acme.com for details.",
                "confidence": 1.0,
                "tables_found": 0,
                "processing_time_ms": 1234.56,
                "success": True,
                "error": None,
            },
            {
                "source": "image-preprocessing-detector/datasets/rvl_cdip/rvl_cdip/images/rvl_invoice_1234.jpg",
                "text": "INVOICE #12345\n\nDate: 2024-01-15\nCustomer: John Doe\n\nItem       Qty    Price    Total\nWidget A   10     $5.00    $50.00\nWidget B   5      $10.00   $50.00\n\nSubtotal: $100.00\nTax: $10.00\nTotal: $110.00",
                "confidence": 1.0,
                "tables_found": 1,
                "processing_time_ms": 2345.67,
                "success": True,
                "error": None,
            },
        ]

        ocr_file = ocr_dir / "ocr_batch_0.jsonl"
        with open(ocr_file, "w") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in ocr_entries)

        return dataset

    def test_dataset_names(self, parser: RvlCdipParser) -> None:
        """Test that parser declares correct dataset names."""
        assert parser.dataset_names == ["rvl_cdip"]

    def test_parse_filename_advertisement(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test parsing advertisement class from filename."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": False, "extract_ocr": False},
        )

        assert isinstance(labels, OriginalLabels)
        assert labels.raw_labels is not None
        assert labels.raw_labels["document_class"] == "advertisement"
        assert labels.raw_labels["document_class_id"] == 0
        assert labels.raw_labels["image_number"] == "0000"
        assert labels.raw_labels["document_type"] == "Advertisement"

    def test_parse_filename_scientific_publication(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test parsing multi-word class (scientific_publication)."""
        image_path = dataset_path / "images" / "rvl_scientific_publication_5678.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": False, "extract_ocr": False},
        )

        assert labels.raw_labels is not None
        assert labels.raw_labels["document_class"] == "scientific_publication"
        assert labels.raw_labels["document_class_id"] == 13
        assert labels.raw_labels["image_number"] == "5678"
        assert labels.raw_labels["document_type"] == "Scientific Publication"

    def test_parse_all_16_classes(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test parsing all 16 RVL-CDIP document classes."""
        expected_classes = [
            ("advertisement", 0),
            ("budget", 1),
            ("email", 2),
            ("file_folder", 3),
            ("form", 4),
            ("handwritten", 5),
            ("invoice", 6),
            ("letter", 7),
            ("memo", 8),
            ("news_article", 9),
            ("presentation", 10),
            ("questionnaire", 11),
            ("resume", 12),
            ("scientific_publication", 13),
            ("scientific_report", 14),
            ("specification", 15),
        ]

        for class_name, class_id in expected_classes:
            image_path = dataset_path / "images" / f"rvl_{class_name}_0001.jpg"
            labels = parser.parse(
                dataset_path=dataset_path,
                image_path=image_path,
                config={"extract_layout": False, "extract_ocr": False},
            )

            assert labels.raw_labels is not None
            assert labels.raw_labels["document_class"] == class_name
            assert labels.raw_labels["document_class_id"] == class_id

    def test_parse_invalid_filename(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test parsing with invalid filename format."""
        image_path = dataset_path / "images" / "invalid_filename.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={},
        )

        assert labels.raw_labels is not None
        # No class extracted, but raw_labels dict exists
        assert "document_class" not in labels.raw_labels

    def test_parse_layout_annotations(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test extraction of layout annotations from COCO JSON."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": True, "extract_ocr": False},
        )

        assert labels.raw_labels is not None
        assert "layout_detections" in labels.raw_labels

        detections = labels.raw_labels["layout_detections"]
        assert isinstance(detections, list)
        assert len(detections) == 2  # 2 annotations for advertisement_0000

        # Check first detection (Text element)
        text_detection = detections[0]
        assert text_detection["bbox"] == [100.0, 200.0, 300.0, 50.0]
        assert text_detection["category_id"] == 9
        assert text_detection["category_name"] == "Text"
        assert text_detection["confidence"] == pytest.approx(0.95)
        assert text_detection["area"] == pytest.approx(15000.0)
        assert text_detection["source"] == "doclayout_yolo"

        # Check second detection (Table element)
        table_detection = detections[1]
        assert table_detection["category_name"] == "Table"
        assert table_detection["confidence"] == pytest.approx(0.88)

    def test_parse_layout_multiple_images(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test that layout extraction correctly matches image_id."""
        # Test invoice image (should have 1 detection)
        invoice_path = dataset_path / "images" / "rvl_invoice_1234.jpg"
        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=invoice_path,
            config={"extract_layout": True, "extract_ocr": False},
        )

        assert labels.raw_labels is not None
        detections = labels.raw_labels["layout_detections"]
        assert len(detections) == 1
        assert detections[0]["category_name"] == "Formula"

    def test_parse_layout_missing(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test handling of image with no layout annotations."""
        image_path = dataset_path / "images" / "rvl_letter_9999.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": True, "extract_ocr": False},
        )

        assert labels.raw_labels is not None
        # No layout_detections key when no annotations found
        assert "layout_detections" not in labels.raw_labels

    def test_parse_ocr_text(self, parser: RvlCdipParser, dataset_path: Path) -> None:
        """Test extraction of OCR text from JSONL files."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": False, "extract_ocr": True},
        )

        assert labels.raw_labels is not None
        assert "text_content" in labels.raw_labels

        text_content = labels.raw_labels["text_content"]
        assert isinstance(text_content, dict)

        # Check text extraction
        assert "ACME Corporation" in text_content["full_text"]
        assert "Special Offer" in text_content["full_text"]

        # Check metadata
        assert text_content["source_type"] == "ocr_tesseract"
        assert text_content["confidence"] == pytest.approx(1.0)
        assert text_content["tables_found"] == 0
        assert text_content["processing_time_ms"] == pytest.approx(1234.56)

        # Check text statistics
        assert text_content["character_count"] > 0
        assert text_content["word_count"] > 0

    def test_parse_ocr_with_table(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test OCR extraction for document with table."""
        invoice_path = dataset_path / "images" / "rvl_invoice_1234.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=invoice_path,
            config={"extract_layout": False, "extract_ocr": True},
        )

        assert labels.raw_labels is not None
        text_content = labels.raw_labels["text_content"]

        assert "INVOICE #12345" in text_content["full_text"]
        assert text_content["tables_found"] == 1
        assert text_content["word_count"] > 20  # Invoice has substantial text

    def test_parse_ocr_missing(self, parser: RvlCdipParser, dataset_path: Path) -> None:
        """Test handling of image with no OCR data."""
        image_path = dataset_path / "images" / "rvl_letter_9999.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": False, "extract_ocr": True},
        )

        assert labels.raw_labels is not None
        # No text_content key when no OCR found
        assert "text_content" not in labels.raw_labels

    def test_parse_full_integration(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test full parsing with class, layout, and OCR extraction."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={},  # Default: extract_layout=True, extract_ocr=True
        )

        assert labels.raw_labels is not None

        # Check document class
        assert labels.raw_labels["document_class"] == "advertisement"
        assert labels.raw_labels["document_class_id"] == 0

        # Check layout annotations
        assert "layout_detections" in labels.raw_labels
        assert len(labels.raw_labels["layout_detections"]) == 2

        # Check OCR text
        assert "text_content" in labels.raw_labels
        assert "ACME Corporation" in labels.raw_labels["text_content"]["full_text"]

    def test_config_disable_layout(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test disabling layout extraction via config."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": False, "extract_ocr": True},
        )

        assert labels.raw_labels is not None
        assert "layout_detections" not in labels.raw_labels
        assert "text_content" in labels.raw_labels

    def test_config_disable_ocr(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test disabling OCR extraction via config."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_layout": True, "extract_ocr": False},
        )

        assert labels.raw_labels is not None
        assert "layout_detections" in labels.raw_labels
        assert "text_content" not in labels.raw_labels

    def test_caching_optimization(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test that batch files are cached for performance."""
        # Clear cache
        parser._layout_cache.clear()
        parser._ocr_cache.clear()

        # Parse first image (should load batch files)
        image1_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"
        parser.parse(
            dataset_path=dataset_path,
            image_path=image1_path,
            config={},
        )

        # Cache should be populated
        assert len(parser._layout_cache) > 0
        assert len(parser._ocr_cache) > 0

        # Parse second image (should use cache)
        image2_path = dataset_path / "images" / "rvl_invoice_1234.jpg"
        parser.parse(
            dataset_path=dataset_path,
            image_path=image2_path,
            config={},
        )

        # Cache size should remain same (reused)
        assert len(parser._layout_cache) == 1  # Only 1 batch file
        assert len(parser._ocr_cache) == 1

    def test_text_statistics_calculation(
        self, parser: RvlCdipParser, dataset_path: Path
    ) -> None:
        """Test that text statistics are correctly calculated."""
        image_path = dataset_path / "images" / "rvl_advertisement_0000.jpg"

        labels = parser.parse(
            dataset_path=dataset_path,
            image_path=image_path,
            config={"extract_ocr": True},
        )

        assert labels.raw_labels is not None
        text_content = labels.raw_labels["text_content"]

        # Verify statistics match actual text
        full_text = text_content["full_text"]
        assert text_content["character_count"] == len(full_text)
        assert text_content["word_count"] == len(full_text.split())

    def test_doclaynet_class_mapping(self, parser: RvlCdipParser) -> None:
        """Test that DocLayNet class IDs are correctly defined."""
        expected_classes = {
            0: "Caption",
            1: "Footnote",
            2: "Formula",
            3: "List-Item",
            4: "Page-Footer",
            5: "Page-Header",
            6: "Picture",
            7: "Section-Header",
            8: "Table",
            9: "Text",
            10: "Title",
        }

        assert expected_classes == parser.DOCLAYNET_CLASSES


__all__ = ["TestRvlCdipParser"]
