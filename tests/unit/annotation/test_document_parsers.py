# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for document dataset parsers.

Tests all document parsers in the annotation.parsers.document package:
- RVL-CDIP: Document classification (16 classes)
- MIDV-500: ID documents (50 countries)
- OHR-Bench: OCR hallucination benchmark
- OmniDocBench: Arrow format benchmark
- Tobacco800: Degraded scanned documents
- RealDAE: Camera-captured documents
- Multimodal Textbook: Educational textbook images
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # No type-only imports needed yet; guard kept for future additions

# Import all parsers
from image_preprocessing_detector.annotation.parsers.document.midv500 import (
    Midv500Parser,
)
from image_preprocessing_detector.annotation.parsers.document.multimodal_textbook import (
    MultimodalTextbookParser,
)
from image_preprocessing_detector.annotation.parsers.document.ohr_bench import (
    OhrBenchParser,
)
from image_preprocessing_detector.annotation.parsers.document.omnidocbench import (
    OmnidocbenchParser,
)
from image_preprocessing_detector.annotation.parsers.document.realdae import (
    RealdaeParser,
)
from image_preprocessing_detector.annotation.parsers.document.rvl_cdip import (
    RvlCdipParser,
)
from image_preprocessing_detector.annotation.parsers.document.tobacco800 import (
    Tobacco800Parser,
)

# =============================================================================
# RVL-CDIP Parser Tests
# =============================================================================


class TestRvlCdipParser:
    """Tests for RVL-CDIP document classification parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = RvlCdipParser()
        assert parser.dataset_names == ["rvl_cdip"]

    def test_parse_single_word_class(self) -> None:
        """Test parsing single-word document class."""
        parser = RvlCdipParser()
        dataset_path = Path("/data/rvl_cdip")
        image_path = Path("/data/rvl_cdip/images/rvl_advertisement_0000.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["document_class"] == "advertisement"
        assert labels.raw_labels["document_class_id"] == 0
        assert labels.raw_labels["image_number"] == "0000"
        assert labels.raw_labels["document_type"] == "Advertisement"

    def test_parse_multi_word_class(self) -> None:
        """Test parsing multi-word document class with underscores."""
        parser = RvlCdipParser()
        dataset_path = Path("/data/rvl_cdip")
        image_path = Path("/data/rvl_cdip/images/rvl_scientific_publication_1234.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["document_class"] == "scientific_publication"
        assert labels.raw_labels["document_class_id"] == 13
        assert labels.raw_labels["image_number"] == "1234"
        assert labels.raw_labels["document_type"] == "Scientific Publication"

    def test_parse_all_16_classes(self) -> None:
        """Test all 16 RVL-CDIP document classes are recognized."""
        parser = RvlCdipParser()
        dataset_path = Path("/data/rvl_cdip")

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
            image_path = Path(f"/data/rvl_cdip/images/rvl_{class_name}_0001.jpg")
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels["document_class"] == class_name
            assert labels.raw_labels["document_class_id"] == class_id

    def test_parse_invalid_filename(self) -> None:
        """Test parsing handles invalid filename gracefully."""
        parser = RvlCdipParser()
        dataset_path = Path("/data/rvl_cdip")
        image_path = Path("/data/rvl_cdip/images/invalid_filename.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        # Should return empty labels without error
        assert labels.raw_labels is not None
        assert "document_class" not in labels.raw_labels

    def test_parse_missing_rvl_prefix(self) -> None:
        """Test parsing handles missing rvl_ prefix."""
        parser = RvlCdipParser()
        dataset_path = Path("/data/rvl_cdip")
        image_path = Path("/data/rvl_cdip/images/advertisement_0000.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        # Should return empty labels without error
        assert labels.raw_labels is not None
        assert "document_class" not in labels.raw_labels


# =============================================================================
# MIDV-500 Parser Tests
# =============================================================================


class TestMidv500Parser:
    """Tests for MIDV-500 ID document parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = Midv500Parser()
        assert parser.dataset_names == ["midv500"]

    def test_parse_russian_id(self) -> None:
        """Test parsing Russian ID document (Cyrillic script).

        MIDV-500 path format: {number}_{country}_{doctype}/images/{filename}
        Parser extracts country_code and document_type from doc_id.
        """
        parser = Midv500Parser()
        dataset_path = Path("/data/midv500")
        image_path = Path("/data/midv500/01_ru_id/images/01_ru_id.tif")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["country_code"] == "RU"
        assert labels.raw_labels["document_type"] == "id"
        assert labels.script_name == "Cyrillic"

    def test_parse_usa_passport(self) -> None:
        """Test parsing USA passport (3-letter country code).

        MIDV-500 path format: {number}_{country}_{doctype}/images/{filename}
        """
        parser = Midv500Parser()
        dataset_path = Path("/data/midv500")
        image_path = Path("/data/midv500/02_usa_passport/images/02_usa_passport.tif")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["country_code"] == "USA"
        assert labels.raw_labels["document_type"] == "passport"
        assert labels.script_name is None  # Not Cyrillic

    def test_parse_driver_license_variants(self) -> None:
        """Test parsing various driver's license naming variants.

        Parser normalizes drvlic, driverlicense, driving_licence, dl
        to 'driver_license'.
        """
        parser = Midv500Parser()
        dataset_path = Path("/data/midv500")

        variants = ["drvlic", "driverlicense", "dl"]
        for i, variant in enumerate(variants):
            image_path = Path(
                f"/data/midv500/0{i}_deu_{variant}/images/0{i}_deu_{variant}.tif"
            )
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels["document_type_normalized"] == "driver_license", (
                f"Failed for variant {variant}"
            )

    def test_parse_cyrillic_countries(self) -> None:
        """Test all Cyrillic countries are detected.

        MIDV-500 path format: {number}_{country}_{doctype}/images/{filename}
        """
        parser = Midv500Parser()
        dataset_path = Path("/data/midv500")

        cyrillic_countries = ["RU", "UA", "BY", "BG", "RS", "KZ"]
        for i, country in enumerate(cyrillic_countries):
            cc_lower = country.lower()
            image_path = Path(
                f"/data/midv500/0{i}_{cc_lower}_id/images/0{i}_{cc_lower}_id.tif"
            )
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.script_name == "Cyrillic", f"Failed for {country}"

    def test_parse_no_country_code(self) -> None:
        """Test parsing handles missing country code gracefully."""
        parser = Midv500Parser()
        dataset_path = Path("/data/midv500")
        image_path = Path("/data/midv500/unknown/card_001.tif")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "country_code" not in labels.raw_labels


# =============================================================================
# OHR-Bench Parser Tests
# =============================================================================


class TestOhrBenchParser:
    """Tests for OHR-Bench OCR hallucination benchmark parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = OhrBenchParser()
        assert set(parser.dataset_names) == {"ohr-bench", "ohr_bench"}

    def test_parse_category_from_parent(self) -> None:
        """Test extracting category from parent directory."""
        parser = OhrBenchParser()
        dataset_path = Path("/data/ohr_bench")
        image_path = Path("/data/ohr_bench/finance/report_001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["category"] == "finance"
        assert labels.raw_labels["document_type"] == "Finance"

    def test_parse_category_from_filename(self) -> None:
        """Test extracting category from filename."""
        parser = OhrBenchParser()
        dataset_path = Path("/data/ohr_bench")
        image_path = Path("/data/ohr_bench/mixed/medical_report_001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["category"] == "medical"

    def test_parse_all_16_categories(self) -> None:
        """Test all 16 OHR-Bench categories are recognized."""
        parser = OhrBenchParser()
        dataset_path = Path("/data/ohr_bench")

        categories = [
            "academic",
            "book",
            "exam",
            "finance",
            "form",
            "handwritten",
            "legal",
            "magazine",
            "medical",
            "newspaper",
            "note",
            "poster",
            "receipt",
            "research",
            "resume",
            "slide",
        ]

        for category in categories:
            image_path = Path(f"/data/ohr_bench/{category}/doc_001.jpg")
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels["category"] == category

    def test_parse_no_category_match(self) -> None:
        """Test parsing handles unknown category gracefully."""
        parser = OhrBenchParser()
        dataset_path = Path("/data/ohr_bench")
        image_path = Path("/data/ohr_bench/unknown/doc_001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "category" not in labels.raw_labels


# =============================================================================
# OmniDocBench Parser Tests
# =============================================================================


class TestOmnidocbenchParser:
    """Tests for OmniDocBench Arrow format benchmark parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = OmnidocbenchParser()
        assert parser.dataset_names == ["omnidocbench"]

    def test_parse_extracted_image(self) -> None:
        """Test parsing extracted image from Arrow format."""
        parser = OmnidocbenchParser()
        dataset_path = Path("/data/omnidocbench")
        image_path = Path("/data/omnidocbench/extracted_images/doc_001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["source"] == "omnidocbench"
        assert labels.raw_labels["format"] == "arrow_extracted"
        assert labels.raw_labels["original_filename"] == "doc_001.png"

    def test_validate_config_missing_extraction(self, tmp_path: Path) -> None:
        """Test validation fails when extraction hasn't been run."""
        parser = OmnidocbenchParser()
        config = {"path": str(tmp_path)}

        errors = parser.validate_config(config)

        assert len(errors) > 0
        assert "extraction" in errors[0].lower()

    def test_validate_config_empty_extraction(self, tmp_path: Path) -> None:
        """Test validation fails when extracted_images is empty."""
        parser = OmnidocbenchParser()
        extracted_dir = tmp_path / "extracted_images"
        extracted_dir.mkdir()
        config = {"path": str(tmp_path)}

        errors = parser.validate_config(config)

        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_validate_config_success(self, tmp_path: Path) -> None:
        """Test validation succeeds when extraction is complete."""
        parser = OmnidocbenchParser()
        extracted_dir = tmp_path / "extracted_images"
        extracted_dir.mkdir()
        (extracted_dir / "test.png").touch()
        config = {"path": str(tmp_path)}

        errors = parser.validate_config(config)

        assert len(errors) == 0


# =============================================================================
# Tobacco800 Parser Tests
# =============================================================================


class TestTobacco800Parser:
    """Tests for Tobacco800 degraded document parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = Tobacco800Parser()
        assert parser.dataset_names == ["tobacco800"]

    def test_parse_basic_metadata(self) -> None:
        """Test parsing extracts basic metadata."""
        parser = Tobacco800Parser()
        dataset_path = Path("/data/tobacco800")
        image_path = Path("/data/tobacco800/images/doc_001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["source"] == "tobacco800"
        assert labels.raw_labels["domain"] == "administrative"
        assert labels.raw_labels["capture_method"] == "scanner_adf"
        assert labels.raw_labels["is_degraded"] is True

    def test_parse_with_class_prefix(self) -> None:
        """Test parsing extracts potential class from filename."""
        parser = Tobacco800Parser()
        dataset_path = Path("/data/tobacco800")
        image_path = Path("/data/tobacco800/images/memo_001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["potential_class"] == "memo"

    def test_parse_simple_filename(self) -> None:
        """Test parsing handles simple filename without class."""
        parser = Tobacco800Parser()
        dataset_path = Path("/data/tobacco800")
        image_path = Path("/data/tobacco800/images/001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "potential_class" not in labels.raw_labels


# =============================================================================
# RealDAE Parser Tests
# =============================================================================


class TestRealdaeParser:
    """Tests for RealDAE camera-captured document parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = RealdaeParser()
        assert parser.dataset_names == ["realdae"]

    def test_parse_input_image(self) -> None:
        """Test parsing input degraded image."""
        parser = RealdaeParser()
        dataset_path = Path("/data/realdae")
        image_path = Path("/data/realdae/train/doc_001_in.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["source"] == "realdae"
        assert labels.raw_labels["capture_method"] == "camera_smartphone"
        assert labels.raw_labels["is_degraded"] is True
        assert labels.raw_labels["image_type"] == "input_degraded"
        assert labels.raw_labels["base_name"] == "doc_001"
        assert "expected_degradations" in labels.raw_labels

    def test_parse_ground_truth_image(self) -> None:
        """Test parsing ground truth image."""
        parser = RealdaeParser()
        dataset_path = Path("/data/realdae")
        image_path = Path("/data/realdae/train/doc_001_gt.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["image_type"] == "ground_truth"
        assert labels.raw_labels["base_name"] == "doc_001"

    def test_parse_with_ground_truth_pair(self, tmp_path: Path) -> None:
        """Test parsing detects ground truth pair."""
        parser = RealdaeParser()
        dataset_path = tmp_path
        train_dir = tmp_path / "train"
        train_dir.mkdir()

        # Create both input and GT files
        in_path = train_dir / "doc_001_in.jpg"
        gt_path = train_dir / "doc_001_gt.jpg"
        in_path.touch()
        gt_path.touch()

        labels = parser.parse(dataset_path, in_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["has_ground_truth"] is True
        assert str(gt_path) in labels.raw_labels["ground_truth_path"]

    def test_parse_without_ground_truth_pair(self, tmp_path: Path) -> None:
        """Test parsing handles missing ground truth."""
        parser = RealdaeParser()
        dataset_path = tmp_path
        train_dir = tmp_path / "train"
        train_dir.mkdir()

        in_path = train_dir / "doc_001_in.jpg"
        in_path.touch()

        labels = parser.parse(dataset_path, in_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["has_ground_truth"] is False

    def test_parse_subset_extraction(self) -> None:
        """Test extracting train/val/test subset."""
        parser = RealdaeParser()
        dataset_path = Path("/data/realdae")

        for subset in ["train", "val", "test", "validation"]:
            image_path = Path(f"/data/realdae/{subset}/doc_001_in.jpg")
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            expected_subset = subset if subset != "validation" else "validation"
            assert labels.raw_labels["subset"] == expected_subset.lower()


# =============================================================================
# Multimodal Textbook Parser Tests
# =============================================================================


class TestMultimodalTextbookParser:
    """Tests for Multimodal Textbook dataset parser."""

    def test_dataset_names(self) -> None:
        """Test parser reports correct dataset names."""
        parser = MultimodalTextbookParser()
        assert set(parser.dataset_names) == {
            "multimodal_textbook",
            "multimodal-textbook",
        }

    def test_parse_basic_metadata(self) -> None:
        """Test parsing extracts basic metadata."""
        parser = MultimodalTextbookParser()
        dataset_path = Path("/data/multimodal_textbook")
        image_path = Path(
            "/data/multimodal_textbook/example_data/sample_100_images/page_001.jpg"
        )

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["source"] == "multimodal_textbook"
        assert labels.raw_labels["domain"] == "educational"
        assert labels.raw_labels["capture_method"] == "born_digital"
        assert labels.raw_labels["document_type"] == "textbook"
        assert "expected_content" in labels.raw_labels

    def test_parse_page_number(self) -> None:
        """Test extracting page number from filename."""
        parser = MultimodalTextbookParser()
        dataset_path = Path("/data/multimodal_textbook")

        test_cases = [
            ("page_042.jpg", 42),
            ("Page_005.jpg", 5),
            ("p_123.jpg", 123),
            ("P123.jpg", 123),
        ]

        for filename, expected_page in test_cases:
            image_path = Path(f"/data/multimodal_textbook/images/{filename}")
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels.get("page_number") == expected_page

    def test_parse_chapter_number(self) -> None:
        """Test extracting chapter number from filename."""
        parser = MultimodalTextbookParser()
        dataset_path = Path("/data/multimodal_textbook")

        test_cases = [
            ("ch1_page5.jpg", 1),
            ("chapter_03.jpg", 3),
            ("Ch12.jpg", 12),
        ]

        for filename, expected_chapter in test_cases:
            image_path = Path(f"/data/multimodal_textbook/images/{filename}")
            labels = parser.parse(dataset_path, image_path, {})

            assert labels.raw_labels is not None
            assert labels.raw_labels.get("chapter") == expected_chapter

    def test_parse_no_metadata_in_filename(self) -> None:
        """Test parsing handles filename without page/chapter info."""
        parser = MultimodalTextbookParser()
        dataset_path = Path("/data/multimodal_textbook")
        image_path = Path("/data/multimodal_textbook/images/image001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert "page_number" not in labels.raw_labels
        assert "chapter" not in labels.raw_labels
        # But basic metadata should still be present
        assert labels.raw_labels["source"] == "multimodal_textbook"
