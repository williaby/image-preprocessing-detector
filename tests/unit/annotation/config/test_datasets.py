# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for datasets configuration module.

Tests:
    - DatasetConfig dataclass structure and immutability
    - DATASET_CONFIGS registry completeness (42 datasets)
    - Path resolution helpers
    - Parser name mapping
    - Validation logic
"""

from __future__ import annotations

from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.config import (
    DATASET_CONFIGS,
    AnnotationSettings,
    DatasetConfig,
    get_dataset_path,
    get_parser_module_name,
    is_benchmark_dataset,
    validate_dataset_configs,
)
from image_preprocessing_detector.annotation.schemas.enums import (
    CaptureMethod,
    DomainLevel1,
)


class TestDatasetConfig:
    """Tests for DatasetConfig dataclass."""

    def test_frozen_immutability(self) -> None:
        """Ensure DatasetConfig is immutable."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.UNKNOWN,
            domain=DomainLevel1.UNKNOWN,
        )

        with pytest.raises(AttributeError):
            config.name = "modified"  # type: ignore[misc]

    def test_required_fields_only(self) -> None:
        """Create config with only required fields."""
        config = DatasetConfig(
            name="minimal",
            path_suffix="01_base_data/minimal",
            pattern="*.jpg",
            capture_method=CaptureMethod.SCANNER_ADF,
            domain=DomainLevel1.ADMINISTRATIVE,
        )

        assert config.name == "minimal"
        assert config.is_benchmark is False
        assert config.has_human_mos is False
        assert config.has_table is None
        assert config.parser_name is None

    def test_all_optional_fields(self) -> None:
        """Create config with all optional fields populated."""
        config = DatasetConfig(
            name="complete",
            path_suffix="02_benchmark_only/complete",
            pattern="**/*.png",
            capture_method=CaptureMethod.BORN_DIGITAL,
            domain=DomainLevel1.SCIENTIFIC,
            is_benchmark=True,
            has_human_mos=True,
            has_table=True,
            has_formula=False,
            has_handwriting=None,
            has_signature=False,
            parser_name="complete",
            has_coco_annotations=True,
            arrow_format=False,
            has_paired_gt=True,
            iso639_language="en",
            iso15924_script="Latn",
            text_scope="page",
            paper_size="A4",
            mos_file="scores.csv",
        )

        assert config.name == "complete"
        assert config.is_benchmark is True
        assert config.has_table is True
        assert config.has_formula is False
        assert config.has_handwriting is None
        assert config.iso639_language == "en"


class TestDatasetConfigsRegistry:
    """Tests for DATASET_CONFIGS registry."""

    def test_registry_completeness(self) -> None:
        """Ensure all 38 datasets are present."""
        # Benchmark (4)
        assert "diqa-5000" in DATASET_CONFIGS
        assert "smartdoc-qa" in DATASET_CONFIGS
        assert "dibco" in DATASET_CONFIGS
        assert "omnidocbench" in DATASET_CONFIGS

        # Degraded (2)
        assert "tobacco800" in DATASET_CONFIGS
        assert "historical_degraded" in DATASET_CONFIGS

        # Documents (2)
        assert "rvl_cdip" in DATASET_CONFIGS
        assert "doclaynet" in DATASET_CONFIGS

        # Forms (5)
        assert "nist-sd2" in DATASET_CONFIGS
        assert "nist_sd6" in DATASET_CONFIGS
        assert "funsd" in DATASET_CONFIGS
        assert "funsd_plus" in DATASET_CONFIGS
        assert "sroie" in DATASET_CONFIGS

        # Tables (3)
        assert "tablebank" in DATASET_CONFIGS
        assert "pubtabnet" in DATASET_CONFIGS
        assert "fintabnet" in DATASET_CONFIGS

        # Handwriting (3)
        assert "nist_sd19" in DATASET_CONFIGS
        assert "signatr6k" in DATASET_CONFIGS
        assert "maths_handwriting" in DATASET_CONFIGS

        # Formulas (2)
        assert "im2latex" in DATASET_CONFIGS
        assert "mathverse" in DATASET_CONFIGS

        # Educational (1)
        assert "multimodal_textbook" in DATASET_CONFIGS

        # Camera-captured (1)
        assert "realdae" in DATASET_CONFIGS

        # OCR Quality (1)
        assert "ocr_quality" in DATASET_CONFIGS

        # Multilingual (13)
        assert "pucit_ohul" in DATASET_CONFIGS
        assert "multilingual_scripts" in DATASET_CONFIGS
        assert "midv500" in DATASET_CONFIGS
        assert "bhutan_financial" in DATASET_CONFIGS
        assert "mdiw13" in DATASET_CONFIGS
        assert "cc_ocr" in DATASET_CONFIGS
        assert "tibhcr" in DATASET_CONFIGS
        assert "mlt19" in DATASET_CONFIGS
        assert "arabic_docs_ocr" in DATASET_CONFIGS
        assert "hindi_ocr_synthetic" in DATASET_CONFIGS
        assert "nepali_handwritten" in DATASET_CONFIGS
        assert "yarmouk_ocr" in DATASET_CONFIGS

        # Script Identification (3)
        assert "cvsi" in DATASET_CONFIGS
        assert "siw13" in DATASET_CONFIGS
        assert "mle2e" in DATASET_CONFIGS

        # OHR-Bench (1)
        assert "ohr-bench" in DATASET_CONFIGS

        # Correction datasets (8)
        assert "docalign12k" in DATASET_CONFIGS
        assert "docreal" in DATASET_CONFIGS
        assert "drccbi" in DATASET_CONFIGS
        assert "staindoc" in DATASET_CONFIGS
        assert "wsrd" in DATASET_CONFIGS

        # Document datasets (2)
        assert "document-haystack" in DATASET_CONFIGS
        assert "markushgrapher" in DATASET_CONFIGS

        # Layout datasets (1)
        assert "indicdlp" in DATASET_CONFIGS

        # Quality datasets (1)
        assert "q-doc" in DATASET_CONFIGS

        # Total count (58 datasets: 46 existing + 12 new)
        assert len(DATASET_CONFIGS) == 58

    def test_all_keys_match_names(self) -> None:
        """Ensure registry keys match config names."""
        for key, config in DATASET_CONFIGS.items():
            assert key == config.name, f"Key '{key}' != config.name '{config.name}'"

    def test_benchmark_datasets_marked_correctly(self) -> None:
        """Check is_benchmark flag matches path_suffix."""
        valid_non_benchmark_prefixes = ("01_base_data", "03_training_datasets")
        for name, config in DATASET_CONFIGS.items():
            if config.is_benchmark:
                assert config.path_suffix.startswith("02_benchmark_only"), (
                    f"{name}: is_benchmark=True but path not in 02_benchmark_only/"
                )
            else:
                assert config.path_suffix.startswith(valid_non_benchmark_prefixes), (
                    f"{name}: is_benchmark=False but path not in {valid_non_benchmark_prefixes}"
                )

    def test_parser_names_lowercase_snake_case(self) -> None:
        """Ensure parser names follow naming convention."""
        for name, config in DATASET_CONFIGS.items():
            if config.parser_name:
                assert config.parser_name == config.parser_name.lower(), (
                    f"{name}: parser_name should be lowercase"
                )
                assert " " not in config.parser_name, (
                    f"{name}: parser_name should not contain spaces"
                )


class TestSpecificDatasets:
    """Tests for specific dataset configurations."""

    def test_diqa_5000_config(self) -> None:
        """Validate diqa-5000 benchmark configuration."""
        config = DATASET_CONFIGS["diqa-5000"]

        assert config.name == "diqa-5000"
        assert config.is_benchmark is True
        assert config.has_human_mos is True
        assert config.mos_file == "train/train.csv"
        assert config.parser_name == "diqa"
        assert config.capture_method == CaptureMethod.UNKNOWN
        assert config.domain == DomainLevel1.UNKNOWN

    def test_tablebank_tier_0_flags(self) -> None:
        """Validate tablebank Tier 0 exact flags."""
        config = DATASET_CONFIGS["tablebank"]

        # Tier 0: 100% tables by definition
        assert config.has_table is True
        assert config.has_formula is False
        assert config.has_handwriting is False
        assert config.has_signature is False
        assert config.has_coco_annotations is True

    def test_nist_sd2_multi_flags(self) -> None:
        """Validate nist-sd2 multiple content flags."""
        config = DATASET_CONFIGS["nist-sd2"]

        assert config.has_table is True
        assert config.has_handwriting is True
        assert config.has_signature is True
        assert config.domain == DomainLevel1.FINANCIAL

    def test_pucit_ohul_multilingual(self) -> None:
        """Validate pucit_ohul multilingual fields."""
        config = DATASET_CONFIGS["pucit_ohul"]

        assert config.iso639_language == "ur"  # Urdu
        assert config.iso15924_script == "Arab"  # Arabic script
        assert config.text_scope == "word"
        assert config.has_handwriting is True

    def test_bhutan_financial_generic_parser(self) -> None:
        """Validate bhutan_financial uses generic parser (real-world docs)."""
        config = DATASET_CONFIGS["bhutan_financial"]

        assert config.parser_name == "generic"
        assert config.has_table is True
        assert config.paper_size == "A4"


class TestPathResolution:
    """Tests for path resolution helpers."""

    def test_get_dataset_path_benchmark(self) -> None:
        """Resolve path for benchmark dataset."""
        settings = AnnotationSettings(e_drive_root=Path("/mnt/e/image_detection"))
        config = DATASET_CONFIGS["diqa-5000"]

        path = get_dataset_path(config, settings)

        assert path == Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")

    def test_get_dataset_path_base_data(self) -> None:
        """Resolve path for base_data dataset."""
        settings = AnnotationSettings(e_drive_root=Path("/mnt/e/image_detection"))
        config = DATASET_CONFIGS["tablebank"]

        path = get_dataset_path(config, settings)

        assert path == Path("/mnt/e/image_detection/01_base_data/tables/tablebank")

    def test_is_benchmark_dataset(self) -> None:
        """Check is_benchmark_dataset helper."""
        assert is_benchmark_dataset(DATASET_CONFIGS["diqa-5000"]) is True
        assert is_benchmark_dataset(DATASET_CONFIGS["omnidocbench"]) is True
        assert is_benchmark_dataset(DATASET_CONFIGS["tablebank"]) is False
        assert is_benchmark_dataset(DATASET_CONFIGS["tobacco800"]) is False


class TestParserMapping:
    """Tests for parser name to module name mapping."""

    def test_get_parser_module_name(self) -> None:
        """Map parser_name to module name."""
        config = DATASET_CONFIGS["diqa-5000"]
        module = get_parser_module_name(config)

        assert module == "diqa_parser"

    def test_get_parser_module_name_generic(self) -> None:
        """Handle dataset with generic parser."""
        config = DATASET_CONFIGS["bhutan_financial"]
        module = get_parser_module_name(config)

        assert module == "generic_parser"

    def test_parser_module_names_consistent(self) -> None:
        """Ensure all parser names map to valid module names."""
        for name, config in DATASET_CONFIGS.items():
            if config.parser_name:
                module = get_parser_module_name(config)
                assert module is not None
                assert module.endswith("_parser")
                assert "_" in module or len(module.split("_")) > 1


class TestValidation:
    """Tests for validate_dataset_configs function."""

    def test_validate_all_configs_pass(self) -> None:
        """Ensure all current configs pass validation."""
        issues = validate_dataset_configs()

        # Should have no issues
        assert len(issues) == 0, f"Validation issues found: {issues}"

    def test_validation_detects_key_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Detect when key doesn't match config.name."""
        bad_configs = {
            "wrong_key": DatasetConfig(
                name="correct_name",
                path_suffix="01_base_data/test",
                pattern="*.jpg",
                capture_method=CaptureMethod.UNKNOWN,
                domain=DomainLevel1.UNKNOWN,
            )
        }

        monkeypatch.setattr(
            "image_preprocessing_detector.annotation.config.datasets.DATASET_CONFIGS",
            bad_configs,
        )

        issues = validate_dataset_configs()
        assert len(issues) > 0
        assert any("does not match" in issue for issue in issues)

    def test_validation_detects_absolute_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Detect path_suffix starting with /."""
        bad_configs = {
            "bad_path": DatasetConfig(
                name="bad_path",
                path_suffix="/absolute/path",
                pattern="*.jpg",
                capture_method=CaptureMethod.UNKNOWN,
                domain=DomainLevel1.UNKNOWN,
            )
        }

        monkeypatch.setattr(
            "image_preprocessing_detector.annotation.config.datasets.DATASET_CONFIGS",
            bad_configs,
        )

        issues = validate_dataset_configs()
        assert len(issues) > 0
        assert any("should not start with /" in issue for issue in issues)

    def test_validation_detects_uppercase_parser(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Detect parser_name not in lowercase snake_case."""
        bad_configs = {
            "bad_parser": DatasetConfig(
                name="bad_parser",
                path_suffix="01_base_data/test",
                pattern="*.jpg",
                capture_method=CaptureMethod.UNKNOWN,
                domain=DomainLevel1.UNKNOWN,
                parser_name="BadParser",  # Should be lowercase
            )
        }

        monkeypatch.setattr(
            "image_preprocessing_detector.annotation.config.datasets.DATASET_CONFIGS",
            bad_configs,
        )

        issues = validate_dataset_configs()
        assert len(issues) > 0
        assert any("lowercase snake_case" in issue for issue in issues)


class TestTier0ContentFlags:
    """Tests for Tier 0 exact content flags in datasets."""

    def test_table_datasets_tier_0(self) -> None:
        """Validate all table datasets have exact Tier 0 flags."""
        table_datasets = ["tablebank", "pubtabnet", "fintabnet"]

        for name in table_datasets:
            config = DATASET_CONFIGS[name]
            assert config.has_table is True
            assert config.has_formula is False
            assert config.has_handwriting is False
            assert config.has_signature is False

    def test_formula_datasets_tier_0(self) -> None:
        """Validate formula datasets have exact Tier 0 flags."""
        formula_datasets = ["im2latex", "mathverse"]

        for name in formula_datasets:
            config = DATASET_CONFIGS[name]
            assert config.has_formula is True
            assert config.has_table is False
            assert config.has_handwriting is False
            assert config.has_signature is False

    def test_handwriting_datasets_tier_0(self) -> None:
        """Validate handwriting datasets have exact Tier 0 flags."""
        config_nist_sd19 = DATASET_CONFIGS["nist_sd19"]
        assert config_nist_sd19.has_handwriting is True
        assert config_nist_sd19.has_table is False
        assert config_nist_sd19.has_formula is False
        assert config_nist_sd19.has_signature is False

        config_signatr = DATASET_CONFIGS["signatr6k"]
        assert config_signatr.has_signature is True
        assert config_signatr.has_handwriting is True
        assert config_signatr.has_table is False
        assert config_signatr.has_formula is False

        config_maths = DATASET_CONFIGS["maths_handwriting"]
        assert config_maths.has_formula is True
        assert config_maths.has_handwriting is True
        assert config_maths.has_table is False
        assert config_maths.has_signature is False


class TestMultilingualDatasets:
    """Tests for multilingual/script detection datasets."""

    def test_multilingual_field_consistency(self) -> None:
        """Check multilingual fields are populated consistently."""
        multilingual_with_script = [
            "pucit_ohul",  # ur/Arab
            "tibhcr",  # Tibt
            "arabic_docs_ocr",  # ar/Arab
            "hindi_ocr_synthetic",  # hi/Deva
            "nepali_handwritten",  # ne/Deva
            "yarmouk_ocr",  # ar/Arab
        ]

        for name in multilingual_with_script:
            config = DATASET_CONFIGS[name]
            # If has language code, should have script code
            if config.iso639_language:
                assert config.iso15924_script is not None, (
                    f"{name} has language but no script"
                )

    def test_text_scope_populated(self) -> None:
        """Ensure text_scope is populated for multilingual datasets."""
        multilingual_datasets = [
            "pucit_ohul",
            "multilingual_scripts",
            "midv500",
            "bhutan_financial",
            "mdiw13",
            "cc_ocr",
            "tibhcr",
            "mlt19",
            "arabic_docs_ocr",
            "hindi_ocr_synthetic",
            "nepali_handwritten",
            "yarmouk_ocr",
            "cvsi",
            "siw13",
            "mle2e",
        ]

        for name in multilingual_datasets:
            config = DATASET_CONFIGS[name]
            assert config.text_scope is not None, (
                f"{name} should have text_scope populated"
            )


class TestArrowFormatDatasets:
    """Tests for datasets requiring Arrow format extraction."""

    def test_arrow_format_flag(self) -> None:
        """Check arrow_format flag for special datasets."""
        assert DATASET_CONFIGS["omnidocbench"].arrow_format is True
        assert DATASET_CONFIGS["ohr-bench"].arrow_format is True

    def test_arrow_datasets_are_benchmark(self) -> None:
        """Arrow format datasets should be benchmarks."""
        for name, config in DATASET_CONFIGS.items():
            if config.arrow_format:
                assert config.is_benchmark is True, (
                    f"{name} has arrow_format but is not benchmark"
                )
