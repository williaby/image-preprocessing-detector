"""Tests for dataset configuration validators.

Tests comprehensive validation of DatasetConfig objects with
clear error messages.
"""

from __future__ import annotations

from image_preprocessing_detector.annotation.config import (
    DATASET_CONFIGS,
    DatasetConfig,
)
from image_preprocessing_detector.annotation.config.validators import (
    BatchValidationReport,
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    quick_validate,
    validate_all_configs,
    validate_dataset_config,
)
from image_preprocessing_detector.annotation.schemas.enums import (
    CaptureMethod,
    DomainLevel1,
)


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_has_expected_values(self) -> None:
        """Test enum has ERROR, WARNING, INFO."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationMessage:
    """Tests for ValidationMessage dataclass."""

    def test_str_format_with_field(self) -> None:
        """Test string formatting with field name."""
        msg = ValidationMessage(
            severity=ValidationSeverity.ERROR,
            field="name",
            message="Name is required",
        )

        result = str(msg)

        assert "[ERROR]" in result
        assert "(name)" in result
        assert "Name is required" in result

    def test_str_format_without_field(self) -> None:
        """Test string formatting without field name."""
        msg = ValidationMessage(
            severity=ValidationSeverity.WARNING,
            field=None,
            message="General warning",
        )

        result = str(msg)

        assert "[WARNING]" in result
        assert "General warning" in result
        assert "()" not in result

    def test_str_format_with_suggestion(self) -> None:
        """Test string formatting with suggestion."""
        msg = ValidationMessage(
            severity=ValidationSeverity.ERROR,
            field="name",
            message="Name is required",
            suggestion="Provide a unique identifier",
        )

        result = str(msg)

        assert "-> Provide a unique identifier" in result


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_is_valid_no_errors(self) -> None:
        """Test is_valid when no errors."""
        result = ValidationResult(dataset_name="test")
        result.add_warning("Just a warning")

        assert result.is_valid is True

    def test_is_valid_with_errors(self) -> None:
        """Test is_valid when errors present."""
        result = ValidationResult(dataset_name="test")
        result.add_error("Critical error")

        assert result.is_valid is False

    def test_errors_property(self) -> None:
        """Test errors property filters correctly."""
        result = ValidationResult(dataset_name="test")
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.add_error("Error 2")
        result.add_info("Info 1")

        errors = result.errors

        assert len(errors) == 2
        assert all(e.severity == ValidationSeverity.ERROR for e in errors)

    def test_warnings_property(self) -> None:
        """Test warnings property filters correctly."""
        result = ValidationResult(dataset_name="test")
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")

        warnings = result.warnings

        assert len(warnings) == 2

    def test_format_output(self) -> None:
        """Test format produces readable output."""
        result = ValidationResult(dataset_name="test-dataset")
        result.add_error("Missing field", field="name")

        output = result.format()

        assert "test-dataset" in output
        assert "INVALID" in output
        assert "Missing field" in output


class TestBatchValidationReport:
    """Tests for BatchValidationReport dataclass."""

    def test_valid_count(self) -> None:
        """Test valid_count property."""
        report = BatchValidationReport()

        valid = ValidationResult(dataset_name="valid")
        invalid = ValidationResult(dataset_name="invalid")
        invalid.add_error("Error")

        report.results["valid"] = valid
        report.results["invalid"] = invalid

        assert report.valid_count == 1
        assert report.invalid_count == 1

    def test_total_errors(self) -> None:
        """Test total_errors property."""
        report = BatchValidationReport()

        r1 = ValidationResult(dataset_name="r1")
        r1.add_error("Error 1")
        r1.add_error("Error 2")

        r2 = ValidationResult(dataset_name="r2")
        r2.add_error("Error 3")

        report.results["r1"] = r1
        report.results["r2"] = r2

        assert report.total_errors == 3

    def test_summary_format(self) -> None:
        """Test summary produces readable report."""
        report = BatchValidationReport()

        valid = ValidationResult(dataset_name="valid")
        report.results["valid"] = valid

        summary = report.summary()

        assert "Validation Report" in summary
        assert "Total Datasets: 1" in summary
        assert "Valid:   1" in summary


class TestValidateDatasetConfig:
    """Tests for validate_dataset_config function."""

    def test_valid_config(self) -> None:
        """Test valid config passes validation."""
        config = DatasetConfig(
            name="test-dataset",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            parser_name="test",
        )

        result = validate_dataset_config(config)

        assert result.is_valid

    def test_missing_name(self) -> None:
        """Test missing name produces error."""
        config = DatasetConfig(
            name="",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("name is required" in str(e) for e in result.errors)

    def test_missing_path_suffix(self) -> None:
        """Test missing path_suffix produces error."""
        config = DatasetConfig(
            name="test",
            path_suffix="",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("Path suffix is required" in str(e) for e in result.errors)

    def test_missing_pattern(self) -> None:
        """Test missing pattern produces error."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("pattern is required" in str(e) for e in result.errors)

    def test_uppercase_name_warning(self) -> None:
        """Test uppercase name produces warning."""
        config = DatasetConfig(
            name="TEST-Dataset",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        # Should be valid but have warning
        assert result.is_valid
        assert any("uppercase" in str(w) for w in result.warnings)

    def test_space_in_name_error(self) -> None:
        """Test space in name produces error."""
        config = DatasetConfig(
            name="test dataset",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("spaces" in str(e) for e in result.errors)

    def test_pattern_without_extension_warning(self) -> None:
        """Test pattern without extension produces warning."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        result = validate_dataset_config(config)

        assert result.is_valid
        assert any("no file extension" in str(w) for w in result.warnings)

    def test_invalid_iso639_language(self) -> None:
        """Test invalid ISO 639 code produces error."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            iso639_language="INVALID",
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("ISO 639" in str(e) for e in result.errors)

    def test_invalid_iso15924_script(self) -> None:
        """Test invalid ISO 15924 code produces error."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            iso15924_script="invalid",
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("ISO 15924" in str(e) for e in result.errors)

    def test_valid_iso_codes(self) -> None:
        """Test valid ISO codes pass validation."""
        config = DatasetConfig(
            name="arabic-docs",
            path_suffix="01_base_data/multilingual/arabic",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            iso639_language="ar",
            iso15924_script="Arab",
        )

        result = validate_dataset_config(config)

        assert result.is_valid

    def test_invalid_text_scope(self) -> None:
        """Test invalid text_scope produces error."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            text_scope="invalid_scope",
        )

        result = validate_dataset_config(config)

        assert not result.is_valid
        assert any("text_scope" in str(e) for e in result.errors)

    def test_missing_parser_name_warning(self) -> None:
        """Test missing parser_name produces warning."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
            parser_name=None,
        )

        result = validate_dataset_config(config)

        assert result.is_valid
        assert any("parser_name" in str(w) for w in result.warnings)


class TestValidateAllConfigs:
    """Tests for validate_all_configs function."""

    def test_validates_multiple_configs(self) -> None:
        """Test validates multiple configs."""
        configs = {
            "valid": DatasetConfig(
                name="valid",
                path_suffix="01_base_data/valid",
                pattern="**/*.jpg",
                capture_method=CaptureMethod.SCANNER_FLATBED,
                domain=DomainLevel1.TAX,
            ),
            "invalid": DatasetConfig(
                name="",
                path_suffix="01_base_data/invalid",
                pattern="**/*.jpg",
                capture_method=CaptureMethod.SCANNER_FLATBED,
                domain=DomainLevel1.TAX,
            ),
        }

        report = validate_all_configs(configs)

        assert len(report.results) == 2
        assert report.valid_count == 1
        assert report.invalid_count == 1

    def test_detects_name_key_mismatch(self) -> None:
        """Test detects when config.name doesn't match dict key."""
        configs = {
            "key": DatasetConfig(
                name="different",
                path_suffix="01_base_data/test",
                pattern="**/*.jpg",
                capture_method=CaptureMethod.SCANNER_FLATBED,
                domain=DomainLevel1.TAX,
            ),
        }

        report = validate_all_configs(configs)

        assert report.invalid_count == 1
        assert any("doesn't match" in str(e) for e in report.results["key"].errors)


class TestQuickValidate:
    """Tests for quick_validate function."""

    def test_valid_config(self) -> None:
        """Test valid config returns True."""
        config = DatasetConfig(
            name="test",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        assert quick_validate(config) is True

    def test_missing_name(self) -> None:
        """Test missing name returns False."""
        config = DatasetConfig(
            name="",
            path_suffix="01_base_data/test",
            pattern="**/*.jpg",
            capture_method=CaptureMethod.SCANNER_FLATBED,
            domain=DomainLevel1.TAX,
        )

        assert quick_validate(config) is False

    def test_dict_input(self) -> None:
        """Test accepts dict input."""
        config_dict = {
            "name": "test",
            "path_suffix": "base_data/test",
            "pattern": "**/*.jpg",
        }

        assert quick_validate(config_dict) is True

    def test_dict_missing_field(self) -> None:
        """Test dict missing field returns False."""
        config_dict = {
            "name": "test",
            "pattern": "**/*.jpg",
        }

        assert quick_validate(config_dict) is False


class TestRealDatasetConfigs:
    """Tests that real DATASET_CONFIGS pass validation."""

    def test_all_configs_valid(self) -> None:
        """Test all registered configs pass validation."""
        report = validate_all_configs(DATASET_CONFIGS)

        # Should have no errors (warnings are OK)
        if report.invalid_count > 0:
            # Print helpful debug info
            for name, result in report.results.items():
                if not result.is_valid:
                    print(f"\n{result.format()}")

        assert report.invalid_count == 0, f"{report.invalid_count} invalid configs"

    def test_sample_configs_structure(self) -> None:
        """Test sample configs have expected structure."""
        # Check a few known configs
        known_configs = ["diqa-5000", "funsd", "tablebank"]

        for name in known_configs:
            if name in DATASET_CONFIGS:
                config = DATASET_CONFIGS[name]
                result = validate_dataset_config(config)
                assert result.is_valid, f"{name}: {result.format()}"
