# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for multilingual/script parsers.

Tests all 10 multilingual parsers to ensure correct extraction of
language codes, script names, and metadata from directory structures
and annotation files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import mock_open, patch

from image_preprocessing_detector.annotation.parsers.multilingual import (
    ArabicDocsParser,
    CcOcrParser,
    CvsiParser,
    Mdiw13Parser,
    Mle2eParser,
    MultilingualScriptsParser,
    NepaliHandwrittenParser,
    Siw13Parser,
    TibhcrParser,
    YarmoukParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels


class TestMultilingualScriptsParser:
    """Tests for MultilingualScriptsParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = MultilingualScriptsParser()
        assert parser.dataset_names == ["multilingual_scripts"]

    def test_arabic_ocr_subdataset(self):
        """Test parsing Arabic OCR subdataset."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path("/data/multilingual_scripts/arabic_ocr/train/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Arabic"
        assert labels.language_code == "ar"
        assert labels.iso15924_script_code == "Arab"  # Standardized field
        assert labels.raw_labels["subdataset"] == "arabic_ocr"
        assert labels.raw_labels["has_ground_truth_labels"] is True

    def test_dzongkha_digits_subdataset(self):
        """Test parsing Dzongkha digits subdataset."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path("/data/multilingual_scripts/dzongkha_digits/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Tibetan"
        assert labels.language_code == "dz"
        assert labels.iso15924_script_code == "Tibt"  # Standardized field
        assert labels.raw_labels["subdataset"] == "dzongkha_digits"

    def test_jssoda_subdataset(self):
        """Test parsing JSSODA Japanese subdataset."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path("/data/multilingual_scripts/jssoda/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Japanese"
        assert labels.language_code == "ja"
        assert labels.iso15924_script_code == "Jpan"  # Standardized field

    def test_nepal_devanagari_book(self):
        """Test parsing Nepal Devanagari book subdataset."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path(
            "/data/multilingual_scripts/nepal_devanagari/nepal_book_001.jpg"
        )

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Devanagari"
        assert labels.language_code == "ne"
        assert labels.iso15924_script_code == "Deva"  # Standardized field
        assert labels.raw_labels["subdataset"] == "nepal_devanagari"
        assert labels.raw_labels["has_ground_truth_labels"] is False
        assert labels.raw_labels["document_type"] == "book"
        assert "Unlabeled" in labels.raw_labels["note"]

    def test_nepal_devanagari_newspaper(self):
        """Test parsing Nepal Devanagari newspaper subdataset."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path(
            "/data/multilingual_scripts/nepal_devanagari/nepal_newspaper_001.jpg"
        )

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["document_type"] == "newspaper"

    def test_mdiw13_reference(self):
        """Test MDIW-13 reference (separate parser)."""
        parser = MultilingualScriptsParser()
        dataset_path = Path("/data/multilingual_scripts")
        image_path = Path("/data/multilingual_scripts/mdiw13/Devanagari/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Indic"
        assert labels.raw_labels["subdataset"] == "mdiw13"
        assert "use MDIW13Parser" in labels.raw_labels["note"]


class TestMdiw13Parser:
    """Tests for Mdiw13Parser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = Mdiw13Parser()
        assert parser.dataset_names == ["mdiw13"]

    def test_devanagari_script(self):
        """Test parsing Devanagari script."""
        parser = Mdiw13Parser()
        dataset_path = Path("/data/mdiw13")
        image_path = Path("/data/mdiw13/Devanagari/Line/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Devanagari"
        assert labels.language_code == "hi"
        assert labels.iso15924_script_code == "Deva"  # Standardized field
        assert labels.raw_labels["segmentation_level"] == "line"

    def test_arabic_script_document_level(self):
        """Test parsing Arabic script at document level."""
        parser = Mdiw13Parser()
        dataset_path = Path("/data/mdiw13")
        image_path = Path("/data/mdiw13/Arabic/Document/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Arabic"
        assert labels.language_code == "ar"
        assert labels.iso15924_script_code == "Arab"  # Standardized field
        assert labels.raw_labels["segmentation_level"] == "document"

    def test_tamil_script_word_level(self):
        """Test parsing Tamil script at word level."""
        parser = Mdiw13Parser()
        dataset_path = Path("/data/mdiw13")
        image_path = Path("/data/mdiw13/Tamil/Word/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Tamil"
        assert labels.language_code == "ta"
        assert labels.iso15924_script_code == "Taml"  # Standardized field
        assert labels.raw_labels["segmentation_level"] == "word"

    def test_all_13_scripts(self):
        """Test all 13 scripts are correctly mapped."""
        parser = Mdiw13Parser()
        dataset_path = Path("/data/mdiw13")

        scripts = [
            ("Arabic", "ar", "Arab"),
            ("Bengali", "bn", "Beng"),
            ("Gujarati", "gu", "Gujr"),
            ("Gurmukhi", "pa", "Guru"),
            ("Devanagari", "hi", "Deva"),
            ("Japanese", "ja", "Jpan"),
            ("Kannada", "kn", "Knda"),
            ("Malayalam", "ml", "Mlym"),
            ("Oriya", "or", "Orya"),
            ("Roman", "en", "Latn"),
            ("Tamil", "ta", "Taml"),
            ("Telugu", "te", "Telu"),
            ("Thai", "th", "Thai"),
        ]

        for script_name, lang_code, iso15924 in scripts:
            image_path = Path(f"/data/mdiw13/{script_name}/Line/img001.png")
            labels = parser.parse(dataset_path, image_path, {})
            assert labels.script_name == script_name
            assert labels.language_code == lang_code
            assert labels.iso15924_script_code == iso15924  # Standardized field


class TestCcOcrParser:
    """Tests for CcOcrParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = CcOcrParser()
        assert parser.dataset_names == ["cc_ocr"]

    def test_default_chinese(self):
        """Test default Chinese language/script."""
        parser = CcOcrParser()
        dataset_path = Path("/data/cc-ocr")
        image_path = Path("/data/cc-ocr/multilingual_text/subset1/images/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "zh"
        assert labels.script_name == "Chinese"  # Human-readable name
        assert labels.iso15924_script_code == "Hans"  # ISO 15924 code

    def test_track_detection(self):
        """Test track detection from path."""
        parser = CcOcrParser()
        dataset_path = Path("/data/cc-ocr")
        image_path = Path("/data/cc-ocr/document_parsing/subset1/images/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert "document" in labels.raw_labels["track"].lower()

    def test_json_annotation_parsing(self):
        """Test parsing JSON annotations."""
        parser = CcOcrParser()
        dataset_path = Path("/data/cc-ocr")
        image_path = Path("/data/cc-ocr/multilingual_text/subset1/images/img001.png")

        json_content = '{"language": "ja", "text": "日本語"}'

        with patch("builtins.open", mock_open(read_data=json_content)):
            with patch("pathlib.Path.exists", return_value=True):
                labels = parser.parse(dataset_path, image_path, {})

                assert labels.language_code == "ja"
                assert labels.transcription == "日本語"
                assert "annotation" in labels.raw_labels


class TestTibhcrParser:
    """Tests for TibhcrParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = TibhcrParser()
        assert parser.dataset_names == ["tibhcr"]

    def test_fixed_tibetan_script(self):
        """Test fixed Tibetan script/language."""
        parser = TibhcrParser()
        dataset_path = Path("/data/tibhcr")
        image_path = Path("/data/tibhcr/train/ka/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.script_name == "Tibetan"
        assert labels.language_code == "bo"
        assert labels.iso15924_script_code == "Tibt"  # Standardized field

    def test_character_class_extraction(self):
        """Test character class extraction."""
        parser = TibhcrParser()
        dataset_path = Path("/data/tibhcr")
        image_path = Path("/data/tibhcr/train/ka/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.transcription == "ka"
        assert labels.raw_labels["character_class"] == "ka"
        assert labels.raw_labels["split"] == "train"

    def test_test_split(self):
        """Test test split extraction."""
        parser = TibhcrParser()
        dataset_path = Path("/data/tibhcr")
        image_path = Path("/data/tibhcr/test/ga/img001.png")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "test"
        assert labels.transcription == "ga"


class TestArabicDocsParser:
    """Tests for ArabicDocsParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = ArabicDocsParser()
        assert parser.dataset_names == ["arabic_docs_ocr"]

    def test_fixed_arabic_script(self):
        """Test fixed Arabic script/language."""
        parser = ArabicDocsParser()
        dataset_path = Path("/data/arabic_docs_ocr")
        image_path = Path("/data/arabic_docs_ocr/Documents/invoice/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "ar"
        assert labels.script_name == "Arabic"
        assert labels.iso15924_script_code == "Arab"  # Standardized field

    def test_category_extraction(self):
        """Test category extraction from path."""
        parser = ArabicDocsParser()
        dataset_path = Path("/data/arabic_docs_ocr")
        image_path = Path("/data/arabic_docs_ocr/Documents/invoice/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["category"] == "invoice"
        assert labels.raw_labels["document_type"] == "invoice"


class TestNepaliHandwrittenParser:
    """Tests for NepaliHandwrittenParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = NepaliHandwrittenParser()
        assert parser.dataset_names == ["nepali_handwritten"]

    def test_fixed_nepali_devanagari(self):
        """Test fixed Nepali/Devanagari script/language."""
        parser = NepaliHandwrittenParser()
        dataset_path = Path("/data/nepali_handwritten")
        image_path = Path("/data/nepali_handwritten/train/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "ne"
        assert labels.script_name == "Devanagari"
        assert labels.iso15924_script_code == "Deva"  # Standardized field

    def test_split_extraction(self):
        """Test split extraction."""
        parser = NepaliHandwrittenParser()
        dataset_path = Path("/data/nepali_handwritten")
        image_path = Path("/data/nepali_handwritten/test/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "test"


class TestYarmoukParser:
    """Tests for YarmoukParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = YarmoukParser()
        assert parser.dataset_names == ["yarmouk_ocr"]

    def test_fixed_arabic_script(self):
        """Test fixed Arabic script/language."""
        parser = YarmoukParser()
        dataset_path = Path("/data/yarmouk_ocr")
        image_path = Path("/data/yarmouk_ocr/Training/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "ar"
        assert labels.script_name == "Arabic"
        assert labels.iso15924_script_code == "Arab"  # Standardized field

    def test_training_split(self):
        """Test Training split extraction."""
        parser = YarmoukParser()
        dataset_path = Path("/data/yarmouk_ocr")
        image_path = Path("/data/yarmouk_ocr/Training/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "train"

    def test_testing_split(self):
        """Test Testing split extraction."""
        parser = YarmoukParser()
        dataset_path = Path("/data/yarmouk_ocr")
        image_path = Path("/data/yarmouk_ocr/Testing/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "test"

    def test_samples_split(self):
        """Test Samples split extraction."""
        parser = YarmoukParser()
        dataset_path = Path("/data/yarmouk_ocr")
        image_path = Path("/data/yarmouk_ocr/Samples/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "sample"


class TestCvsiParser:
    """Tests for CvsiParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = CvsiParser()
        assert parser.dataset_names == ["cvsi"]

    def test_hindi_script(self):
        """Test Hindi script detection."""
        parser = CvsiParser()
        dataset_path = Path("/data/cvsi")
        image_path = Path("/data/cvsi/Training/Hindi/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "hi"
        assert labels.script_name == "Hindi"  # Human-readable name
        assert labels.iso15924_script_code == "Deva"  # Standardized ISO 15924
        assert labels.raw_labels["script_class"] == "Hindi"
        assert labels.raw_labels["split"] == "training"

    def test_tamil_script(self):
        """Test Tamil script detection."""
        parser = CvsiParser()
        dataset_path = Path("/data/cvsi")
        image_path = Path("/data/cvsi/Testing/Tamil/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "ta"
        assert labels.script_name == "Tamil"  # Human-readable name
        assert labels.iso15924_script_code == "Taml"  # Standardized ISO 15924
        assert labels.raw_labels["split"] == "testing"

    def test_all_10_scripts(self):
        """Test all 10 CVSI scripts are correctly mapped."""
        parser = CvsiParser()
        dataset_path = Path("/data/cvsi")

        scripts = [
            ("Arabic", "ar", "Arab"),
            ("Bengali", "bn", "Beng"),
            ("English", "en", "Latn"),
            ("Gujrathi", "gu", "Gujr"),
            ("Hindi", "hi", "Deva"),
            ("Kannada", "kn", "Knda"),
            ("Oriya", "or", "Orya"),
            ("Punjabi", "pa", "Guru"),
            ("Tamil", "ta", "Taml"),
            ("Telegu", "te", "Telu"),
        ]

        for script_name, lang_code, iso15924 in scripts:
            image_path = Path(f"/data/cvsi/Training/{script_name}/img001.jpg")
            labels = parser.parse(dataset_path, image_path, {})
            assert labels.language_code == lang_code
            assert labels.script_name == script_name  # Human-readable name
            assert labels.iso15924_script_code == iso15924  # Standardized ISO 15924


class TestSiw13Parser:
    """Tests for Siw13Parser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = Siw13Parser()
        assert parser.dataset_names == ["siw13"]

    def test_chinese_script(self):
        """Test Chinese script detection."""
        parser = Siw13Parser()
        dataset_path = Path("/data/siw13")
        image_path = Path("/data/siw13/Training/Chinese/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "zh"
        assert labels.script_name == "Chinese"  # Human-readable name
        assert labels.iso15924_script_code == "Hans"  # Standardized ISO 15924
        assert labels.raw_labels["script_class"] == "Chinese"
        assert labels.raw_labels["split"] == "training"

    def test_tibetan_script(self):
        """Test Tibetan script detection."""
        parser = Siw13Parser()
        dataset_path = Path("/data/siw13")
        image_path = Path("/data/siw13/Testing/Tibetan/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.language_code == "bo"
        assert labels.script_name == "Tibetan"  # Human-readable name
        assert labels.iso15924_script_code == "Tibt"  # Standardized ISO 15924
        assert labels.raw_labels["split"] == "testing"

    def test_all_13_scripts(self):
        """Test all 13 SIW-13 scripts are correctly mapped."""
        parser = Siw13Parser()
        dataset_path = Path("/data/siw13")

        scripts = [
            ("Arabic", "ar", "Arab"),
            ("Cambodian", "km", "Khmr"),
            ("Chinese", "zh", "Hans"),
            ("English", "en", "Latn"),
            ("Greek", "el", "Grek"),
            ("Hebrew", "he", "Hebr"),
            ("Japanese", "ja", "Jpan"),
            ("Kannada", "kn", "Knda"),
            ("Korean", "ko", "Kore"),
            ("Mongolian", "mn", "Mong"),
            ("Russian", "ru", "Cyrl"),
            ("Thai", "th", "Thai"),
            ("Tibetan", "bo", "Tibt"),
        ]

        for script_name, lang_code, iso15924 in scripts:
            image_path = Path(f"/data/siw13/Training/{script_name}/img001.jpg")
            labels = parser.parse(dataset_path, image_path, {})
            assert labels.language_code == lang_code
            assert labels.script_name == script_name  # Human-readable name
            assert labels.iso15924_script_code == iso15924  # Standardized ISO 15924


class TestMle2eParser:
    """Tests for Mle2eParser."""

    def test_dataset_names(self):
        """Test dataset names property."""
        parser = Mle2eParser()
        assert parser.dataset_names == ["mle2e"]

    def test_split_extraction(self):
        """Test split extraction from path."""
        parser = Mle2eParser()
        dataset_path = Path("/data/mle2e")
        image_path = Path("/data/mle2e/Training/img001.jpg")

        labels = parser.parse(dataset_path, image_path, {})

        assert labels.raw_labels["split"] == "train"

    def test_annotation_parsing(self):
        """Test parsing text annotation files."""
        parser = Mle2eParser()
        dataset_path = Path("/data/mle2e")
        image_path = Path("/data/mle2e/Training/img001.jpg")

        txt_content = """100,200,300,400,chinese,你好
400,500,600,700,latin,Hello
700,800,900,1000,korean,안녕"""

        with patch("builtins.open", mock_open(read_data=txt_content)):
            with patch("pathlib.Path.exists", return_value=True):
                labels = parser.parse(dataset_path, image_path, {})

                assert "scripts" in labels.raw_labels
                assert "chinese" in labels.raw_labels["scripts"]
                assert "latin" in labels.raw_labels["scripts"]
                assert "korean" in labels.raw_labels["scripts"]

                # Primary script is set from one of the detected scripts
                # (order is implementation-dependent with multiple scripts)
                assert labels.language_code in {"zh", "en", "ko"}
                # Human-readable names now in script_name
                assert labels.script_name in {"Chinese", "Latin", "Korean"}
                # ISO 15924 codes in iso15924_script_code
                assert labels.iso15924_script_code in {"Hans", "Latn", "Hang"}

                # Text instances (first 5)
                assert labels.text_instances is not None
                assert len(labels.text_instances) == 3
                assert labels.text_instances[0]["script"] == "chinese"
                assert labels.text_instances[0]["text"] == "你好"

    def test_all_4_scripts(self):
        """Test all 4 MLE2E scripts are correctly mapped."""
        parser = Mle2eParser()

        # (script_label, lang_code, human_name, iso15924)
        scripts = [
            ("latin", "en", "Latin", "Latn"),
            ("chinese", "zh", "Chinese", "Hans"),
            ("kannada", "kn", "Kannada", "Knda"),
            ("korean", "ko", "Korean", "Hang"),
        ]

        for script_label, lang_code, human_name, iso15924 in scripts:
            txt_content = f"100,200,300,400,{script_label},sample"

            dataset_path = Path("/data/mle2e")
            image_path = Path("/data/mle2e/Training/img001.jpg")

            with patch("builtins.open", mock_open(read_data=txt_content)):
                with patch("pathlib.Path.exists", return_value=True):
                    labels = parser.parse(dataset_path, image_path, {})
                    assert labels.language_code == lang_code
                    assert labels.script_name == human_name  # Human-readable name
                    assert labels.iso15924_script_code == iso15924  # ISO 15924


class TestIntegration:
    """Integration tests for multilingual parsers."""

    def test_all_parsers_return_original_labels(self):
        """Test all parsers return OriginalLabels instances."""
        parsers = [
            MultilingualScriptsParser(),
            Mdiw13Parser(),
            CcOcrParser(),
            TibhcrParser(),
            ArabicDocsParser(),
            NepaliHandwrittenParser(),
            YarmoukParser(),
            CvsiParser(),
            Siw13Parser(),
            Mle2eParser(),
        ]

        dataset_path = Path("/data/test")
        image_path = Path("/data/test/img001.jpg")

        for parser in parsers:
            labels = parser.parse(dataset_path, image_path, {})
            assert isinstance(labels, OriginalLabels)
            assert labels.raw_labels is not None

    def test_all_parsers_have_dataset_names(self):
        """Test all parsers have non-empty dataset_names."""
        parsers = [
            MultilingualScriptsParser(),
            Mdiw13Parser(),
            CcOcrParser(),
            TibhcrParser(),
            ArabicDocsParser(),
            NepaliHandwrittenParser(),
            YarmoukParser(),
            CvsiParser(),
            Siw13Parser(),
            Mle2eParser(),
        ]

        for parser in parsers:
            assert len(parser.dataset_names) > 0
            assert all(isinstance(name, str) for name in parser.dataset_names)

    def test_all_parsers_set_language_or_script(self):
        """Test all parsers set language_code or script_name."""
        test_cases = [
            (
                MultilingualScriptsParser(),
                Path("/data/multilingual_scripts/arabic_ocr/img001.jpg"),
            ),
            (Mdiw13Parser(), Path("/data/mdiw13/Devanagari/Line/img001.png")),
            (CcOcrParser(), Path("/data/cc-ocr/multilingual_text/img001.png")),
            (TibhcrParser(), Path("/data/tibhcr/train/ka/img001.png")),
            (
                ArabicDocsParser(),
                Path("/data/arabic_docs_ocr/Documents/invoice/img001.jpg"),
            ),
            (
                NepaliHandwrittenParser(),
                Path("/data/nepali_handwritten/train/img001.jpg"),
            ),
            (YarmoukParser(), Path("/data/yarmouk_ocr/Training/img001.jpg")),
            (CvsiParser(), Path("/data/cvsi/Training/Hindi/img001.jpg")),
            (Siw13Parser(), Path("/data/siw13/Training/Chinese/img001.jpg")),
            (Mle2eParser(), Path("/data/mle2e/Training/img001.jpg")),
        ]

        for parser, image_path in test_cases:
            dataset_path = image_path.parent.parent
            labels = parser.parse(dataset_path, image_path, {})

            # Most parsers should set language_code or script_name
            # MLE2E is an exception - it determines language from per-image annotations
            # which don't exist in this mock test
            if parser.__class__.__name__ != "Mle2eParser":
                assert (
                    labels.language_code is not None or labels.script_name is not None
                ), f"{parser.__class__.__name__} did not set language or script"
