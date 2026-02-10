# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for quality score parsers.

Tests cover:
    - DIQAParser: 3-dimension MOS scores from CSV
    - SmartDocParser: Filename encoding and OCR accuracy
    - DibcoParser: Directory structure parsing
    - OcrQualityParser: Parquet/JSON human scores
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.parsers.quality import (
    DibcoParser,
    DIQAParser,
    OcrQualityParser,
    SmartDocParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels

# ==============================================================================
# DIQAParser Tests
# ==============================================================================


class TestDIQAParser:
    """Test suite for DIQA-5000 parser."""

    @pytest.fixture
    def parser(self) -> DIQAParser:
        """Create DIQAParser instance."""
        return DIQAParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock DIQA-5000 dataset structure.

        CSV columns: res (restored filename), ori (original filename),
        overall, sharpness, color_fidelity.

        The parser matches by the column corresponding to the image's folder:
        - Image in ori/ folder -> matches against 'ori' column
        - Image in res/ folder -> matches against 'res' column
        So ori column values must match the image filenames used in tests.
        """
        dataset = tmp_path / "diqa-5000"
        dataset.mkdir()

        # Create train split CSV
        train_dir = dataset / "train"
        train_dir.mkdir()
        csv_path = train_dir / "train.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["res", "ori", "overall", "sharpness", "color_fidelity"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "res": "img001_res.jpg",
                    "ori": "img001.jpg",
                    "overall": "4.2",
                    "sharpness": "4.5",
                    "color_fidelity": "3.8",
                }
            )
            writer.writerow(
                {
                    "res": "img002_res.jpg",
                    "ori": "img002.jpg",
                    "overall": "3.1",
                    "sharpness": "3.0",
                    "color_fidelity": "3.2",
                }
            )

        # Create val split CSV
        val_dir = dataset / "val"
        val_dir.mkdir()
        csv_path = val_dir / "val.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["res", "ori", "overall", "sharpness", "color_fidelity"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "res": "val001_res.jpg",
                    "ori": "val001.jpg",
                    "overall": "4.8",
                    "sharpness": "4.9",
                    "color_fidelity": "4.7",
                }
            )

        return dataset

    def test_dataset_names(self, parser: DIQAParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["diqa-5000"]

    def test_parse_train_split(self, parser: DIQAParser, dataset_path: Path) -> None:
        """Test parsing from train split CSV."""
        image_path = dataset_path / "train" / "ori" / "img001.jpg"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.diqa_overall == 4.2
        assert labels.diqa_mos == 4.2  # Backward compatibility
        assert labels.diqa_sharpness == 4.5
        assert labels.diqa_color_fidelity == 3.8
        assert labels.diqa_original_image == "img001.jpg"

    def test_parse_val_split(self, parser: DIQAParser, dataset_path: Path) -> None:
        """Test parsing from val split CSV."""
        image_path = dataset_path / "val" / "ori" / "val001.jpg"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.diqa_overall == 4.8
        assert labels.diqa_mos == 4.8
        assert labels.diqa_sharpness == 4.9
        assert labels.diqa_color_fidelity == 4.7

    def test_parse_no_match(self, parser: DIQAParser, dataset_path: Path) -> None:
        """Test parsing when no matching entry found."""
        image_path = dataset_path / "train" / "ori" / "nonexistent.jpg"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.diqa_overall is None
        assert labels.diqa_mos is None
        assert labels.diqa_sharpness is None

    def test_parse_missing_csv(self, parser: DIQAParser, tmp_path: Path) -> None:
        """Test parsing when CSV files are missing."""
        dataset = tmp_path / "empty-dataset"
        dataset.mkdir()
        image_path = dataset / "train" / "ori" / "img001.jpg"
        labels = parser.parse(dataset, image_path, {})

        assert labels.diqa_overall is None

    def test_parse_malformed_csv(self, parser: DIQAParser, tmp_path: Path) -> None:
        """Test parsing with malformed CSV data."""
        dataset = tmp_path / "malformed"
        dataset.mkdir()
        train_dir = dataset / "train"
        train_dir.mkdir()
        csv_path = train_dir / "train.csv"
        with open(csv_path, "w") as f:
            f.write("invalid,csv,format\n")
            f.write("no,proper,headers\n")

        image_path = dataset / "train" / "ori" / "img001.jpg"
        labels = parser.parse(dataset, image_path, {})

        assert labels.diqa_overall is None


# ==============================================================================
# SmartDocParser Tests
# ==============================================================================


class TestSmartDocParser:
    """Test suite for SmartDoc-QA parser."""

    @pytest.fixture
    def parser(self) -> SmartDocParser:
        """Create SmartDocParser instance."""
        return SmartDocParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock SmartDoc-QA dataset structure."""
        dataset = tmp_path / "smartdoc-qa"
        dataset.mkdir()

        # Create phone folder structure
        phone_dir = dataset / "Captured_Images" / "Galaxy_S4"
        images_dir = phone_dir / "Images"
        images_dir.mkdir(parents=True)

        ocr_dir = phone_dir / "OCR_Accuracy_Finereader"
        ocr_dir.mkdir(parents=True)

        # Create OCR accuracy file
        cacc_path = ocr_dir / "S_Img_Android_D1_L1_r0_a0_b0.cacc.txt"
        with open(cacc_path, "w") as f:
            f.write("Character Recognition Report\n")
            f.write("   99.56%  Accuracy\n")
            f.write("Other data...\n")

        wacc_path = ocr_dir / "S_Img_Android_D1_L1_r0_a0_b0.wacc.txt"
        with open(wacc_path, "w") as f:
            f.write("Word Recognition Report\n")
            f.write("   98.23%  Accuracy\n")

        return dataset

    def test_dataset_names(self, parser: SmartDocParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["smartdoc-qa"]

    def test_parse_filename_encoding(
        self, parser: SmartDocParser, dataset_path: Path
    ) -> None:
        """Test parsing capture parameters from filename."""
        image_path = (
            dataset_path
            / "Captured_Images"
            / "Galaxy_S4"
            / "Images"
            / "S_Img_Android_D1_L1_r0_a0_b0.jpg"
        )
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.smartdoc_capture_device == "Galaxy_S4"
        assert labels.smartdoc_lighting == "normal"
        assert labels.raw_labels is not None
        assert labels.raw_labels["phone_id"] == "S"
        assert labels.raw_labels["os_type"] == "Android"
        assert labels.raw_labels["document_number"] == 1
        assert labels.raw_labels["lighting_code"] == "1"
        assert labels.raw_labels["rotation_degrees"] == 0
        assert labels.raw_labels["viewing_angle"] == 0
        assert labels.raw_labels["blur_level"] == 0

    def test_parse_ocr_accuracy(
        self, parser: SmartDocParser, dataset_path: Path
    ) -> None:
        """Test parsing OCR accuracy to MOS conversion."""
        image_path = (
            dataset_path
            / "Captured_Images"
            / "Galaxy_S4"
            / "Images"
            / "S_Img_Android_D1_L1_r0_a0_b0.jpg"
        )
        labels = parser.parse(dataset_path, image_path, {})

        # 99.56% accuracy should map to 5.0 MOS
        assert labels.smartdoc_mos == 5.0
        assert labels.raw_labels is not None
        assert labels.raw_labels["character_accuracy_percent"] == 99.56
        assert labels.raw_labels["word_accuracy_percent"] == 98.23

    def test_parse_motion_blur_variant(
        self, parser: SmartDocParser, tmp_path: Path
    ) -> None:
        """Test parsing filename with motion blur variant."""
        dataset = tmp_path / "smartdoc"
        phone_dir = dataset / "Captured_Images" / "TestPhone" / "Images"
        phone_dir.mkdir(parents=True)

        image_path = phone_dir / "M_Img_WP_D5_L2_r90_a30_b-3_Mb2.jpg"
        labels = parser.parse(dataset, image_path, {})

        assert labels.smartdoc_capture_device == "TestPhone"
        assert labels.smartdoc_lighting == "challenging"
        assert labels.raw_labels is not None
        assert labels.raw_labels["blur_type"] == "Mb"
        assert labels.raw_labels["blur_variant"] == 2

    def test_parse_no_ocr_accuracy(
        self, parser: SmartDocParser, tmp_path: Path
    ) -> None:
        """Test parsing when OCR accuracy files are missing."""
        dataset = tmp_path / "smartdoc"
        phone_dir = dataset / "Captured_Images" / "TestPhone" / "Images"
        phone_dir.mkdir(parents=True)

        image_path = phone_dir / "S_Img_Android_D1_L1_r0_a0_b0.jpg"
        labels = parser.parse(dataset, image_path, {})

        assert labels.smartdoc_mos is None

    def test_mos_scale_conversion(self, parser: SmartDocParser, tmp_path: Path) -> None:
        """Test various accuracy to MOS scale conversions."""
        test_cases = [
            (99.5, 5.0),
            (95.0, 4.5),
            (90.0, 4.0),
            (85.0, 3.5),
            (80.0, 3.0),
            (75.0, 2.5),
            (70.0, 2.0),
            (60.0, pytest.approx(1.857, rel=0.01)),
        ]

        for accuracy, expected_mos in test_cases:
            dataset = tmp_path / f"test_{accuracy}"
            phone_dir = dataset / "Captured_Images" / "TestPhone"
            images_dir = phone_dir / "Images"
            images_dir.mkdir(parents=True)
            ocr_dir = phone_dir / "OCR_Accuracy_Finereader"
            ocr_dir.mkdir(parents=True)

            cacc_path = ocr_dir / "S_Img_Android_D1_L1_r0_a0_b0.cacc.txt"
            with open(cacc_path, "w") as f:
                f.write(f"   {accuracy}%  Accuracy\n")

            image_path = images_dir / "S_Img_Android_D1_L1_r0_a0_b0.jpg"
            labels = parser.parse(dataset, image_path, {})

            assert labels.smartdoc_mos == expected_mos


# ==============================================================================
# DibcoParser Tests
# ==============================================================================


class TestDibcoParser:
    """Test suite for DIBCO parser."""

    @pytest.fixture
    def parser(self) -> DibcoParser:
        """Create DibcoParser instance."""
        return DibcoParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock DIBCO dataset structure."""
        dataset = tmp_path / "dibco"
        dataset.mkdir()

        # Create 2013 handwritten test images
        test_dir = dataset / "2013" / "DIBCO2013_Test_images-handwritten"
        test_dir.mkdir(parents=True)

        # Create corresponding GT
        gt_dir = dataset / "2013" / "DIBCO2013-GT-Test-images_handwritten"
        gt_dir.mkdir(parents=True)
        gt_image = gt_dir / "H01.png"
        gt_image.touch()

        # Create printed images
        printed_dir = dataset / "2013" / "DIBCO2013_Test_images-printed"
        printed_dir.mkdir(parents=True)

        return dataset

    def test_dataset_names(self, parser: DibcoParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["dibco"]

    def test_parse_handwritten(self, parser: DibcoParser, dataset_path: Path) -> None:
        """Test parsing handwritten document metadata."""
        image_path = (
            dataset_path / "2013" / "DIBCO2013_Test_images-handwritten" / "H01.png"
        )
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["dibco_year"] == 2013
        assert labels.raw_labels["document_type"] == "handwritten"
        assert labels.raw_labels["has_handwriting"] is True
        assert labels.raw_labels["has_ground_truth"] is True
        assert "ground_truth_path" in labels.raw_labels

    def test_parse_printed(self, parser: DibcoParser, dataset_path: Path) -> None:
        """Test parsing printed document metadata."""
        image_path = dataset_path / "2013" / "DIBCO2013_Test_images-printed" / "P01.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["dibco_year"] == 2013
        assert labels.raw_labels["document_type"] == "printed"
        assert labels.raw_labels["has_handwriting"] is False

    def test_parse_ground_truth_image(
        self, parser: DibcoParser, dataset_path: Path
    ) -> None:
        """Test parsing ground truth image metadata."""
        image_path = (
            dataset_path / "2013" / "DIBCO2013-GT-Test-images_handwritten" / "H01.png"
        )
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["dibco_year"] == 2013
        assert labels.raw_labels["is_ground_truth"] is True

    def test_parse_no_ground_truth(self, parser: DibcoParser, tmp_path: Path) -> None:
        """Test parsing when ground truth is not available."""
        dataset = tmp_path / "dibco"
        test_dir = dataset / "2015" / "DIBCO2015_Test_images-handwritten"
        test_dir.mkdir(parents=True)

        image_path = test_dir / "H01.png"
        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["dibco_year"] == 2015
        assert "has_ground_truth" not in labels.raw_labels

    def test_parse_multiple_years(self, parser: DibcoParser, tmp_path: Path) -> None:
        """Test parsing documents from different years."""
        for year in [2009, 2011, 2013, 2016, 2017]:
            dataset = tmp_path / f"dibco_{year}"
            test_dir = dataset / str(year) / f"DIBCO{year}_Test_images-handwritten"
            test_dir.mkdir(parents=True)

            image_path = test_dir / "H01.png"
            labels = parser.parse(dataset, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels["dibco_year"] == year


# ==============================================================================
# OcrQualityParser Tests
# ==============================================================================


class TestOcrQualityParser:
    """Test suite for OCR-Quality parser."""

    @pytest.fixture
    def parser(self) -> OcrQualityParser:
        """Create OcrQualityParser instance."""
        return OcrQualityParser()

    @pytest.fixture
    def dataset_path_json(self, tmp_path: Path) -> Path:
        """Create mock OCR-Quality dataset with JSON."""
        dataset = tmp_path / "ocr-quality-json"
        dataset.mkdir()

        json_path = dataset / "OCR-Quality.json"
        data = [
            {
                "image_path": "images/doc001.png",
                "human_score": 1,
                "source": "human_annotator_1",
                "ocr_text": "This is high quality text that should be readable." * 20,
            },
            {
                "image_path": "images/doc002.png",
                "human_score": 4,
                "source": "human_annotator_2",
                "ocr_text": "Poor quality degraded text.",
            },
        ]
        with open(json_path, "w") as f:
            json.dump(data, f)

        return dataset

    @pytest.fixture
    def dataset_path_parquet(self, tmp_path: Path) -> Path:
        """Create mock OCR-Quality dataset with Parquet."""
        pytest.importorskip("pyarrow")
        import pyarrow as pa
        import pyarrow.parquet as pq

        dataset = tmp_path / "ocr-quality-parquet"
        dataset.mkdir()

        parquet_path = dataset / "OCR-Quality.parquet"
        data = {
            "image_path": ["images/doc001.png", "images/doc002.png"],
            "human_score": [1, 4],
            "source": ["human_annotator_1", "human_annotator_2"],
            "ocr_text": [
                "This is high quality text that should be readable." * 20,
                "Poor quality degraded text.",
            ],
        }
        table = pa.Table.from_pydict(data)
        pq.write_table(table, parquet_path)

        return dataset

    def test_dataset_names(self, parser: OcrQualityParser) -> None:
        """Test dataset_names property."""
        assert parser.dataset_names == ["ocr_quality"]

    def test_parse_json(
        self, parser: OcrQualityParser, dataset_path_json: Path
    ) -> None:
        """Test parsing from JSON file."""
        image_path = dataset_path_json / "images" / "doc001.png"
        labels = parser.parse(dataset_path_json, image_path, {})

        assert labels.ocr_quality_score == 1
        assert labels.ocr_quality_source == "human_annotator_1"
        assert len(labels.ocr_quality_text or "") <= 500  # Truncated

    @pytest.mark.skipif(
        not pytest.importorskip("pyarrow", reason="pyarrow not available"),
        reason="pyarrow required",
    )
    def test_parse_parquet(
        self, parser: OcrQualityParser, dataset_path_parquet: Path
    ) -> None:
        """Test parsing from Parquet file (preferred)."""
        image_path = dataset_path_parquet / "images" / "doc001.png"
        labels = parser.parse(dataset_path_parquet, image_path, {})

        assert labels.ocr_quality_score == 1
        assert labels.ocr_quality_source == "human_annotator_1"
        assert len(labels.ocr_quality_text or "") <= 500  # Truncated

    def test_parse_no_match(
        self, parser: OcrQualityParser, dataset_path_json: Path
    ) -> None:
        """Test parsing when no matching entry found."""
        image_path = dataset_path_json / "images" / "nonexistent.png"
        labels = parser.parse(dataset_path_json, image_path, {})

        assert labels.ocr_quality_score is None
        assert labels.ocr_quality_source is None

    def test_parse_missing_files(
        self, parser: OcrQualityParser, tmp_path: Path
    ) -> None:
        """Test parsing when annotation files are missing."""
        dataset = tmp_path / "empty"
        dataset.mkdir()
        image_path = dataset / "images" / "doc001.png"
        labels = parser.parse(dataset, image_path, {})

        assert labels.ocr_quality_score is None

    def test_text_truncation(
        self, parser: OcrQualityParser, dataset_path_json: Path
    ) -> None:
        """Test that OCR text is truncated to 500 characters."""
        image_path = dataset_path_json / "images" / "doc001.png"
        labels = parser.parse(dataset_path_json, image_path, {})

        assert labels.ocr_quality_text is not None
        assert len(labels.ocr_quality_text) == 500


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_all_parsers_implement_base_protocol() -> None:
    """Verify all parsers implement the BaseParser protocol correctly."""
    parsers = [DIQAParser(), SmartDocParser(), DibcoParser(), OcrQualityParser()]

    for parser in parsers:
        # Must have dataset_names property
        assert hasattr(parser, "dataset_names")
        assert isinstance(parser.dataset_names, list)
        assert len(parser.dataset_names) > 0

        # Must have parse method
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

        # Must have supports_batch method
        assert hasattr(parser, "supports_batch")
        assert callable(parser.supports_batch)

        # Must have parse_batch method
        assert hasattr(parser, "parse_batch")
        assert callable(parser.parse_batch)


def test_parser_returns_original_labels() -> None:
    """Verify all parsers return OriginalLabels instances."""
    from pathlib import Path

    parsers = [DIQAParser(), SmartDocParser(), DibcoParser(), OcrQualityParser()]

    for parser in parsers:
        # Create minimal test environment
        fake_dataset_path = Path("/fake/dataset")
        fake_image_path = Path("/fake/image.jpg")

        result = parser.parse(fake_dataset_path, fake_image_path, {})

        # Must return OriginalLabels instance
        assert isinstance(result, OriginalLabels)
