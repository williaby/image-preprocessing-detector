# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for handwriting and signature parsers.

Tests cover:
    - SignaTRParser: Signature segmentation dataset
    - PucitOhulParser: Urdu handwriting with Excel labels
    - NistSd19Parser: Handwritten characters from directory structure
    - NistDb2Parser: Tax forms with .fmt field annotations
    - MathsHandwritingParser: Mathematical handwriting stub
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.parsers.handwriting import (
    MathsHandwritingParser,
    NistDb2Parser,
    NistSd19Parser,
    PucitOhulParser,
    SignaTRParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels

# Check if openpyxl is available
HAS_OPENPYXL = importlib.util.find_spec("openpyxl") is not None


# ==============================================================================
# SignaTRParser Tests
# ==============================================================================


class TestSignaTRParser:
    """Test suite for SignaTR6K signature parser."""

    @pytest.fixture
    def parser(self) -> SignaTRParser:
        """Create SignaTRParser instance."""
        return SignaTRParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock SignaTR6K dataset structure."""
        dataset = tmp_path / "SignaTR6K"
        dataset.mkdir()

        # Create train split with crop and label directories
        train_crop_dir = dataset / "train" / "crop"
        train_crop_dir.mkdir(parents=True)
        train_label_dir = dataset / "train" / "label"
        train_label_dir.mkdir(parents=True)

        # Create sample images and labels
        (train_crop_dir / "12345.png").touch()
        (train_label_dir / "12345.png").touch()
        (train_crop_dir / "12346.png").touch()  # No corresponding label

        # Create test split
        test_crop_dir = dataset / "test" / "crop"
        test_crop_dir.mkdir(parents=True)
        (test_crop_dir / "99999.png").touch()

        # Create validation split
        val_label_dir = dataset / "validation" / "label"
        val_label_dir.mkdir(parents=True)
        (val_label_dir / "55555.png").touch()

        return dataset

    def test_dataset_names(self, parser: SignaTRParser) -> None:
        """Test dataset_names property."""
        assert "signatr6k" in parser.dataset_names
        assert "signatr" in parser.dataset_names

    def test_parse_train_crop_with_mask(
        self, parser: SignaTRParser, dataset_path: Path
    ) -> None:
        """Test parsing crop image with corresponding mask."""
        image_path = dataset_path / "train" / "crop" / "12345.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "train"
        assert labels.raw_labels["image_type"] == "signature"
        assert labels.raw_labels["signature_id"] == 12345
        assert labels.raw_labels["has_mask"] is True
        assert "mask_path" in labels.raw_labels

    def test_parse_crop_without_mask(
        self, parser: SignaTRParser, dataset_path: Path
    ) -> None:
        """Test parsing crop image without corresponding mask."""
        image_path = dataset_path / "train" / "crop" / "12346.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["image_type"] == "signature"
        assert labels.raw_labels["signature_id"] == 12346
        assert labels.raw_labels["has_mask"] is False

    def test_parse_label_image(self, parser: SignaTRParser, dataset_path: Path) -> None:
        """Test parsing label/mask image."""
        image_path = dataset_path / "validation" / "label" / "55555.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "validation"
        assert labels.raw_labels["image_type"] == "mask"
        assert labels.raw_labels["signature_id"] == 55555

    def test_parse_test_split(self, parser: SignaTRParser, dataset_path: Path) -> None:
        """Test parsing test split."""
        image_path = dataset_path / "test" / "crop" / "99999.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "test"

    def test_parse_non_numeric_id(self, parser: SignaTRParser, tmp_path: Path) -> None:
        """Test parsing filename with non-numeric ID."""
        dataset = tmp_path / "signatr"
        crop_dir = dataset / "train" / "crop"
        crop_dir.mkdir(parents=True)
        image_path = crop_dir / "signature_abc.png"

        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["signature_id"] == "signature_abc"


# ==============================================================================
# PucitOhulParser Tests
# ==============================================================================


class TestPucitOhulParser:
    """Test suite for PUCIT-OHUL Urdu handwriting parser."""

    @pytest.fixture
    def parser(self) -> PucitOhulParser:
        """Create PucitOhulParser instance."""
        return PucitOhulParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock PUCIT-OHUL dataset structure."""
        dataset = tmp_path / "Pucit"
        dataset.mkdir()

        # Create train and test directories
        train_dir = dataset / "train_lines"
        train_dir.mkdir(parents=True)
        test_dir = dataset / "test_lines"
        test_dir.mkdir(parents=True)

        (train_dir / "img001.png").touch()
        (test_dir / "img002.png").touch()

        return dataset

    @pytest.fixture
    def dataset_path_with_excel(self, tmp_path: Path) -> Path:
        """Create mock dataset with Excel labels."""
        pytest.importorskip("openpyxl")
        import openpyxl

        dataset = tmp_path / "Pucit"
        dataset.mkdir()

        train_dir = dataset / "train_lines"
        train_dir.mkdir(parents=True)
        (train_dir / "img001.png").touch()

        # Create Excel file
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["image_name", "transcription", "writer_id"])
        ws.append(["img001", "یہ اردو متن ہے", "writer_123"])
        wb.save(dataset / "train_labels_v2.xlsx")
        wb.close()

        return dataset

    def test_dataset_names(self, parser: PucitOhulParser) -> None:
        """Test dataset_names property."""
        assert "pucit-ohul" in parser.dataset_names
        assert "pucit_ohul" in parser.dataset_names
        assert "pucit" in parser.dataset_names

    def test_parse_language_and_script(
        self, parser: PucitOhulParser, dataset_path: Path
    ) -> None:
        """Test language and script are set correctly."""
        image_path = dataset_path / "train_lines" / "img001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "ur"
        assert labels.script_name == "Arabic"

    def test_parse_train_split(
        self, parser: PucitOhulParser, dataset_path: Path
    ) -> None:
        """Test parsing train split."""
        image_path = dataset_path / "train_lines" / "img001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "train"

    def test_parse_test_split(
        self, parser: PucitOhulParser, dataset_path: Path
    ) -> None:
        """Test parsing test split."""
        image_path = dataset_path / "test_lines" / "img002.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "test"

    @pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not available")
    def test_parse_excel_labels(
        self, parser: PucitOhulParser, dataset_path_with_excel: Path
    ) -> None:
        """Test parsing transcriptions from Excel file."""
        image_path = dataset_path_with_excel / "train_lines" / "img001.png"
        labels = parser.parse(dataset_path_with_excel, image_path, {})

        assert labels.transcription == "یہ اردو متن ہے"
        assert labels.writer_id == "writer_123"

    def test_parse_no_excel(self, parser: PucitOhulParser, dataset_path: Path) -> None:
        """Test parsing when Excel file is missing."""
        image_path = dataset_path / "train_lines" / "img001.png"
        labels = parser.parse(dataset_path, image_path, {})

        # Should still set language/script
        assert labels.language_code == "ur"
        assert labels.script_name == "Arabic"
        # But no transcription
        assert labels.transcription is None


# ==============================================================================
# NistSd19Parser Tests
# ==============================================================================


class TestNistSd19Parser:
    """Test suite for NIST SD-19 handwriting parser."""

    @pytest.fixture
    def parser(self) -> NistSd19Parser:
        """Create NistSd19Parser instance."""
        return NistSd19Parser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock NIST SD-19 dataset structure."""
        dataset = tmp_path / "nist-sd19"
        dataset.mkdir()

        # Create by_class structure
        class_dir = dataset / "by_class" / "30" / "hsf_0"
        class_dir.mkdir(parents=True)
        (class_dir / "a_0001.png").touch()
        (class_dir / "b_0042.png").touch()

        # Create by_write structure
        write_dir = dataset / "by_write" / "hsf_4"
        write_dir.mkdir(parents=True)
        (write_dir / "5_0123.png").touch()

        return dataset

    def test_dataset_names(self, parser: NistSd19Parser) -> None:
        """Test dataset_names property."""
        assert "nist-sd19" in parser.dataset_names
        assert "nist_sd19" in parser.dataset_names
        assert "sd19" in parser.dataset_names

    def test_parse_by_class_structure(
        self, parser: NistSd19Parser, dataset_path: Path
    ) -> None:
        """Test parsing from by_class directory structure."""
        image_path = dataset_path / "by_class" / "30" / "hsf_0" / "a_0001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.writer_id == "hsf_0"
        assert labels.transcription == "A"
        assert labels.raw_labels is not None
        assert labels.raw_labels["class_id"] == "30"
        assert labels.raw_labels["sample_id"] == "0001"

    def test_parse_by_write_structure(
        self, parser: NistSd19Parser, dataset_path: Path
    ) -> None:
        """Test parsing from by_write directory structure."""
        image_path = dataset_path / "by_write" / "hsf_4" / "5_0123.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.writer_id == "hsf_4"
        assert labels.transcription == "5"
        assert labels.raw_labels is not None
        assert labels.raw_labels["sample_id"] == "0123"

    def test_parse_digit_class(self, parser: NistSd19Parser, tmp_path: Path) -> None:
        """Test parsing digit character class."""
        dataset = tmp_path / "nist"
        class_dir = dataset / "by_class" / "5" / "hsf_1"
        class_dir.mkdir(parents=True)
        image_path = class_dir / "sample.png"

        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["class_id"] == "5"
        assert labels.transcription == "5"

    def test_parse_multiple_writers(
        self, parser: NistSd19Parser, dataset_path: Path
    ) -> None:
        """Test parsing multiple writer groups."""
        for writer in ["hsf_0", "hsf_4"]:
            writer_dir = dataset_path / "by_write" / writer
            writer_dir.mkdir(parents=True, exist_ok=True)
            image_path = writer_dir / "a_0001.png"
            image_path.touch()

            labels = parser.parse(dataset_path, image_path, {})
            assert labels.writer_id == writer


# ==============================================================================
# NistDb2Parser Tests
# ==============================================================================


class TestNistDb2Parser:
    """Test suite for NIST DB2 tax form parser."""

    @pytest.fixture
    def parser(self) -> NistDb2Parser:
        """Create NistDb2Parser instance."""
        return NistDb2Parser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock NIST DB2 dataset structure."""
        dataset = tmp_path / "NIST_SD2"
        dataset.mkdir()

        # Create form image
        image_path = dataset / "form_0001.png"
        image_path.touch()

        # Create companion .fmt file
        fmt_path = dataset / "form_0001.fmt"
        with open(fmt_path, "w") as f:
            f.write("FORM_ID_12345\n")
            f.write("FIELD_01 John\n")
            f.write("FIELD_02 Doe\n")
            f.write("FIELD_03 _ICON_\n")
            f.write("FIELD_04 555-1234\n")
            f.write("FIELD_05 123 Main St\n")
            f.write("FIELD_06 Some Value\n")

        return dataset

    def test_dataset_names(self, parser: NistDb2Parser) -> None:
        """Test dataset_names property."""
        assert "nist-db2" in parser.dataset_names
        assert "nist-sd2" in parser.dataset_names
        assert "sd2" in parser.dataset_names

    def test_parse_language_and_script(
        self, parser: NistDb2Parser, dataset_path: Path
    ) -> None:
        """Test language and script are set for US tax forms."""
        image_path = dataset_path / "form_0001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "en"
        assert labels.script_name == "Latin"

    def test_parse_form_metadata(
        self, parser: NistDb2Parser, dataset_path: Path
    ) -> None:
        """Test parsing form type and document type."""
        image_path = dataset_path / "form_0001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["form_type"] == "1040"
        assert labels.raw_labels["document_type"] == "tax_form"

    def test_parse_fmt_file(self, parser: NistDb2Parser, dataset_path: Path) -> None:
        """Test parsing .fmt field annotations."""
        image_path = dataset_path / "form_0001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["form_id"] == "FORM_ID_12345"
        assert labels.raw_labels["field_count"] == 6
        assert labels.raw_labels["has_handwritten_content"] is True
        assert len(labels.raw_labels["sample_fields"]) == 5
        assert "John" in labels.raw_labels["sample_fields"]
        assert "_ICON_" not in labels.raw_labels["sample_fields"]

    def test_parse_no_fmt_file(self, parser: NistDb2Parser, tmp_path: Path) -> None:
        """Test parsing when .fmt file is missing."""
        dataset = tmp_path / "nist"
        dataset.mkdir()
        image_path = dataset / "form_0001.png"
        image_path.touch()

        labels = parser.parse(dataset, image_path, {})

        # Should still set form metadata
        assert labels.raw_labels is not None
        assert labels.raw_labels["form_type"] == "1040"
        # But no field data
        assert "form_id" not in labels.raw_labels

    def test_parse_empty_fmt_file(self, parser: NistDb2Parser, tmp_path: Path) -> None:
        """Test parsing empty .fmt file."""
        dataset = tmp_path / "nist"
        dataset.mkdir()
        image_path = dataset / "form_0001.png"
        image_path.touch()
        fmt_path = dataset / "form_0001.fmt"
        fmt_path.touch()

        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["form_type"] == "1040"


# ==============================================================================
# MathsHandwritingParser Tests
# ==============================================================================


class TestMathsHandwritingParser:
    """Test suite for mathematical handwriting stub parser."""

    @pytest.fixture
    def parser(self) -> MathsHandwritingParser:
        """Create MathsHandwritingParser instance."""
        return MathsHandwritingParser()

    @pytest.fixture
    def dataset_path(self, tmp_path: Path) -> Path:
        """Create mock maths handwriting dataset structure."""
        dataset = tmp_path / "maths_handwriting"
        dataset.mkdir()

        train_dir = dataset / "train"
        train_dir.mkdir()
        (train_dir / "equation_001.png").touch()

        test_dir = dataset / "test"
        test_dir.mkdir()
        (test_dir / "equation_002.png").touch()

        return dataset

    def test_dataset_names(self, parser: MathsHandwritingParser) -> None:
        """Test dataset_names property."""
        assert "maths-handwriting" in parser.dataset_names
        assert "maths_handwriting" in parser.dataset_names
        assert "math_handwriting" in parser.dataset_names

    def test_parse_train_split(
        self, parser: MathsHandwritingParser, dataset_path: Path
    ) -> None:
        """Test parsing train split."""
        image_path = dataset_path / "train" / "equation_001.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "train"
        assert labels.raw_labels["content_type"] == "mathematical"

    def test_parse_test_split(
        self, parser: MathsHandwritingParser, dataset_path: Path
    ) -> None:
        """Test parsing test split."""
        image_path = dataset_path / "test" / "equation_002.png"
        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "test"

    def test_parse_validation_split(
        self, parser: MathsHandwritingParser, tmp_path: Path
    ) -> None:
        """Test parsing validation split."""
        dataset = tmp_path / "maths"
        val_dir = dataset / "validation"
        val_dir.mkdir(parents=True)
        image_path = val_dir / "eq.png"

        labels = parser.parse(dataset, image_path, {})

        assert labels.raw_labels is not None
        assert labels.raw_labels["split"] == "validation"

    def test_parse_no_split(
        self, parser: MathsHandwritingParser, tmp_path: Path
    ) -> None:
        """Test parsing when no split directory exists."""
        dataset = tmp_path / "maths"
        dataset.mkdir()
        image_path = dataset / "equation.png"

        labels = parser.parse(dataset, image_path, {})

        # Should still mark as mathematical
        assert labels.raw_labels is not None
        assert labels.raw_labels["content_type"] == "mathematical"
        assert "split" not in labels.raw_labels


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_all_parsers_implement_base_protocol() -> None:
    """Verify all parsers implement the BaseParser protocol correctly."""
    parsers = [
        SignaTRParser(),
        PucitOhulParser(),
        NistSd19Parser(),
        NistDb2Parser(),
        MathsHandwritingParser(),
    ]

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
    parsers = [
        SignaTRParser(),
        PucitOhulParser(),
        NistSd19Parser(),
        NistDb2Parser(),
        MathsHandwritingParser(),
    ]

    for parser in parsers:
        # Create minimal test environment
        fake_dataset_path = Path("/fake/dataset")
        fake_image_path = Path("/fake/image.jpg")

        result = parser.parse(fake_dataset_path, fake_image_path, {})

        # Must return OriginalLabels instance
        assert isinstance(result, OriginalLabels)


def test_parsers_handle_missing_data_gracefully() -> None:
    """Verify all parsers handle missing data without raising exceptions."""
    parsers = [
        SignaTRParser(),
        PucitOhulParser(),
        NistSd19Parser(),
        NistDb2Parser(),
        MathsHandwritingParser(),
    ]

    fake_dataset_path = Path("/nonexistent/dataset")
    fake_image_path = Path("/nonexistent/image.jpg")

    for parser in parsers:
        # Should not raise exceptions
        labels = parser.parse(fake_dataset_path, fake_image_path, {})
        assert isinstance(labels, OriginalLabels)
