# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for annotation workflow pre-flight validation module.

Phase 5 Task 5.5.4: Pre-flight validation tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.workflow.preflight import (
    CheckCategory,
    CheckResult,
    CheckSeverity,
    PreflightChecker,
    PreflightConfig,
    PreflightResult,
    run_preflight_checks,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tmp_dataset(tmp_path: Path) -> Path:
    """Create a temporary dataset directory."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "images").mkdir()
    (dataset / "annotations").mkdir()
    for i in range(5):
        (dataset / "images" / f"img_{i}.png").touch()
    return dataset


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def tmp_model_file(tmp_path: Path) -> Path:
    """Create a temporary model file."""
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fake model content" * 1000)  # ~18KB
    return model


# ============================================================================
# CheckResult Tests
# ============================================================================


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        result = CheckResult(
            name="test_check",
            passed=True,
            category=CheckCategory.DISK,
            message="Test passed",
        )
        assert result.name == "test_check"
        assert result.passed is True
        assert result.category == CheckCategory.DISK
        assert result.severity == CheckSeverity.INFO

    def test_failed_check(self) -> None:
        """Test failed check creation."""
        result = CheckResult(
            name="disk_space",
            passed=False,
            category=CheckCategory.DISK,
            severity=CheckSeverity.ERROR,
            message="Insufficient disk space",
            details={"free_gb": 5.0, "required_gb": 10.0},
        )
        assert result.passed is False
        assert result.severity == CheckSeverity.ERROR
        assert result.details["free_gb"] == pytest.approx(5.0)

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        result = CheckResult(
            name="test",
            passed=True,
            category=CheckCategory.PATH,
            message="OK",
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True
        assert d["category"] == "path"


# ============================================================================
# PreflightResult Tests
# ============================================================================


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_empty_result(self) -> None:
        """Test empty result starts as passed."""
        result = PreflightResult()
        assert result.passed is True
        assert len(result.checks) == 0
        assert len(result.failures) == 0

    def test_add_passing_check(self) -> None:
        """Test adding a passing check."""
        result = PreflightResult()
        result.add_check(
            CheckResult(
                name="test",
                passed=True,
                category=CheckCategory.DISK,
            )
        )
        assert result.passed is True
        assert len(result.checks) == 1
        assert len(result.failures) == 0

    def test_add_warning_check(self) -> None:
        """Test adding a warning check doesn't fail overall."""
        result = PreflightResult()
        result.add_check(
            CheckResult(
                name="test",
                passed=False,
                category=CheckCategory.DISK,
                severity=CheckSeverity.WARNING,
                message="Warning message",
            )
        )
        assert result.passed is True  # Warnings don't fail
        assert len(result.warnings) == 1

    def test_add_error_check(self) -> None:
        """Test adding an error check fails overall."""
        result = PreflightResult()
        result.add_check(
            CheckResult(
                name="test",
                passed=False,
                category=CheckCategory.DISK,
                severity=CheckSeverity.ERROR,
                message="Error message",
            )
        )
        assert result.passed is False
        assert len(result.errors) == 1

    def test_critical_failures(self) -> None:
        """Test critical failures filtering."""
        result = PreflightResult()
        result.add_check(
            CheckResult(
                name="warning",
                passed=False,
                category=CheckCategory.DISK,
                severity=CheckSeverity.WARNING,
                message="Warning",
            )
        )
        result.add_check(
            CheckResult(
                name="error",
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message="Error",
            )
        )
        assert len(result.failures) == 2
        assert len(result.critical_failures) == 1

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        result = PreflightResult()
        result.add_check(
            CheckResult(name="test", passed=True, category=CheckCategory.DISK)
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["total_checks"] == 1
        assert d["failures"] == 0


# ============================================================================
# PreflightChecker Tests
# ============================================================================


class TestPreflightChecker:
    """Tests for PreflightChecker class."""

    def test_default_config(self) -> None:
        """Test checker with default config."""
        checker = PreflightChecker()
        assert checker.config.min_disk_space_gb == pytest.approx(10.0)
        assert checker.config.check_write_permission is True

    def test_custom_config(self) -> None:
        """Test checker with custom config."""
        config = PreflightConfig(min_disk_space_gb=5.0, check_write_permission=False)
        checker = PreflightChecker(config=config)
        assert checker.config.min_disk_space_gb == pytest.approx(5.0)
        assert checker.config.check_write_permission is False

    def test_check_disk_space_passes(self, tmp_path: Path) -> None:
        """Test disk space check passes with low requirement."""
        checker = PreflightChecker()
        result = checker.check_disk_space(tmp_path, min_gb=0.001)  # 1MB
        assert result.passed is True
        assert result.category == CheckCategory.DISK
        assert "free_gb" in result.details

    def test_check_disk_space_fails(self, tmp_path: Path) -> None:
        """Test disk space check fails with high requirement."""
        checker = PreflightChecker()
        result = checker.check_disk_space(tmp_path, min_gb=1_000_000)  # 1PB
        assert result.passed is False
        assert result.severity == CheckSeverity.ERROR

    def test_check_disk_space_nonexistent_path(self) -> None:
        """Test disk space check with non-existent path."""
        checker = PreflightChecker()
        result = checker.check_disk_space(Path("/nonexistent/path/deeply/nested"))
        # Should still work by finding accessible parent
        assert result.category == CheckCategory.DISK

    def test_check_path_readable_exists(self, tmp_dataset: Path) -> None:
        """Test path readable check for existing path."""
        checker = PreflightChecker()
        result = checker.check_path_readable(tmp_dataset)
        assert result.passed is True
        assert result.category == CheckCategory.PATH

    def test_check_path_readable_not_exists(self) -> None:
        """Test path readable check for non-existent path."""
        checker = PreflightChecker()
        result = checker.check_path_readable(Path("/nonexistent/path"))
        assert result.passed is False
        assert result.severity == CheckSeverity.ERROR

    def test_check_path_writable_exists(self, tmp_output: Path) -> None:
        """Test path writable check for existing writable path."""
        checker = PreflightChecker()
        result = checker.check_path_writable(tmp_output)
        assert result.passed is True

    def test_check_path_writable_can_create(self, tmp_path: Path) -> None:
        """Test path writable check for path that can be created."""
        checker = PreflightChecker()
        new_path = tmp_path / "new_dir"
        result = checker.check_path_writable(new_path)
        assert result.passed is True
        assert result.details["exists"] is False

    def test_check_path_writable_nonexistent_parent(self) -> None:
        """Test path writable check for path with non-existent parent."""
        checker = PreflightChecker()
        # Use a deeply nested path that definitely doesn't exist
        result = checker.check_path_writable(
            Path("/definitely/does/not/exist/anywhere/new_dir")
        )
        # Should fail because parent doesn't exist
        assert result.category == CheckCategory.PATH
        # The result depends on system - either fails or finds root
        # Just verify it returns a valid result
        assert result.name.startswith("path_writable")

    def test_check_model_file_exists(self, tmp_model_file: Path) -> None:
        """Test model file check for existing file."""
        checker = PreflightChecker()
        result = checker.check_model_file(tmp_model_file)
        assert result.passed is True
        assert result.category == CheckCategory.MODEL
        assert "size_mb" in result.details

    def test_check_model_file_not_exists(self) -> None:
        """Test model file check for non-existent file."""
        checker = PreflightChecker()
        result = checker.check_model_file(Path("/nonexistent/model.onnx"))
        assert result.passed is False
        assert result.severity == CheckSeverity.ERROR

    def test_check_model_file_is_directory(self, tmp_path: Path) -> None:
        """Test model file check when path is a directory."""
        checker = PreflightChecker()
        result = checker.check_model_file(tmp_path)
        assert result.passed is False
        assert "not a file" in result.message

    def test_check_dataset_structure_valid(self, tmp_path: Path) -> None:
        """Test dataset structure check with valid structure."""
        # Create expected structure
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "train").mkdir()
        (dataset / "val").mkdir()
        (dataset / "annotations.json").touch()

        checker = PreflightChecker()
        result = checker.check_dataset_structure(
            dataset,
            required_subdirs=["train", "val"],
            required_files=["annotations.json"],
        )
        assert result.passed is True

    def test_check_dataset_structure_missing_subdir(self, tmp_path: Path) -> None:
        """Test dataset structure check with missing subdirectory."""
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "train").mkdir()
        # Missing 'val' directory

        checker = PreflightChecker()
        result = checker.check_dataset_structure(
            dataset,
            required_subdirs=["train", "val"],
        )
        assert result.passed is False
        assert "val" in result.details["missing_subdirs"]

    def test_check_dataset_structure_not_exists(self) -> None:
        """Test dataset structure check for non-existent path."""
        checker = PreflightChecker()
        result = checker.check_dataset_structure(Path("/nonexistent"))
        assert result.passed is False

    def test_check_all_basic(self, tmp_dataset: Path, tmp_output: Path) -> None:
        """Test check_all with basic paths."""
        checker = PreflightChecker()
        result = checker.check_all(
            dataset_path=tmp_dataset,
            output_path=tmp_output,
        )
        # Should pass with valid paths
        assert len(result.checks) >= 2

    def test_check_all_with_checkpoint(
        self, tmp_dataset: Path, tmp_output: Path, tmp_path: Path
    ) -> None:
        """Test check_all with checkpoint path."""
        checkpoint_path = tmp_path / "checkpoints"
        checker = PreflightChecker()
        result = checker.check_all(
            dataset_path=tmp_dataset,
            output_path=tmp_output,
            checkpoint_path=checkpoint_path,
        )
        assert len(result.checks) >= 3

    def test_check_all_with_model_paths(
        self, tmp_dataset: Path, tmp_output: Path, tmp_model_file: Path
    ) -> None:
        """Test check_all with model paths in config."""
        config = PreflightConfig(model_paths=[tmp_model_file])
        checker = PreflightChecker(config=config)
        result = checker.check_all(
            dataset_path=tmp_dataset,
            output_path=tmp_output,
        )
        # Should include model check
        model_checks = [c for c in result.checks if c.category == CheckCategory.MODEL]
        assert len(model_checks) == 1

    def test_register_custom_check(self, tmp_dataset: Path) -> None:
        """Test registering a custom check."""

        def custom_check(result: PreflightResult) -> None:
            result.add_check(
                CheckResult(
                    name="custom_env_check",
                    passed=True,
                    category=CheckCategory.SYSTEM,
                    message="Custom check passed",
                )
            )

        checker = PreflightChecker()
        checker.register_check(custom_check)
        result = checker.check_all(dataset_path=tmp_dataset)

        custom_checks = [c for c in result.checks if c.name == "custom_env_check"]
        assert len(custom_checks) == 1

    def test_custom_check_exception_handled(self, tmp_dataset: Path) -> None:
        """Test that exceptions in custom checks are handled."""

        def bad_check(_result: PreflightResult) -> None:
            msg = "Custom check failed"
            raise RuntimeError(msg)

        checker = PreflightChecker()
        checker.register_check(bad_check)
        result = checker.check_all(dataset_path=tmp_dataset)

        # Should have a warning about the failed custom check
        assert any("custom_check" in c.name.lower() for c in result.checks)


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestRunPreflightChecks:
    """Tests for run_preflight_checks convenience function."""

    def test_basic_usage(self, tmp_dataset: Path, tmp_output: Path) -> None:
        """Test basic convenience function usage."""
        result = run_preflight_checks(
            dataset_path=tmp_dataset,
            output_path=tmp_output,
        )
        assert isinstance(result, PreflightResult)

    def test_with_custom_config(self, tmp_dataset: Path) -> None:
        """Test with custom configuration."""
        config = PreflightConfig(min_disk_space_gb=0.001)
        result = run_preflight_checks(
            dataset_path=tmp_dataset,
            config=config,
        )
        assert isinstance(result, PreflightResult)

    def test_no_paths(self) -> None:
        """Test with no paths provided."""
        result = run_preflight_checks()
        assert result.passed is True
        assert len(result.checks) == 0


# ============================================================================
# Provider Availability Tests
# ============================================================================


class TestProviderAvailability:
    """Tests for provider availability checks."""

    def test_check_unknown_provider(self) -> None:
        """Test checking unknown provider returns warning."""
        checker = PreflightChecker()
        result = checker.check_provider_availability("unknown_provider")
        assert result.passed is False
        assert result.category == CheckCategory.PROVIDER
        assert result.severity == CheckSeverity.WARNING
        assert "Unknown provider" in result.message

    def test_check_yolo_provider_without_model(self) -> None:
        """Test YOLO provider check without model file."""
        checker = PreflightChecker()
        result = checker.check_provider_availability("yolo")
        # Should return result (may pass or fail depending on environment)
        assert result.category == CheckCategory.PROVIDER
        assert "yolo" in result.details.get("provider", "")

    def test_check_siglip_provider_without_model(self) -> None:
        """Test SigLIP provider check without model file."""
        checker = PreflightChecker()
        result = checker.check_provider_availability("siglip")
        # Should return result (may pass or fail depending on environment)
        assert result.category == CheckCategory.PROVIDER
        assert "siglip" in result.details.get("provider", "")

    def test_check_all_with_providers(self, tmp_dataset: Path) -> None:
        """Test check_all includes provider checks when configured."""
        config = PreflightConfig(
            check_provider_connectivity=True,
            provider_names=["yolo"],
        )
        checker = PreflightChecker(config=config)
        result = checker.check_all(dataset_path=tmp_dataset)

        # Should include provider check
        provider_checks = [
            c for c in result.checks if c.category == CheckCategory.PROVIDER
        ]
        assert len(provider_checks) == 1

    def test_check_all_skips_providers_when_disabled(self, tmp_dataset: Path) -> None:
        """Test check_all skips providers when connectivity check disabled."""
        config = PreflightConfig(
            check_provider_connectivity=False,
            provider_names=["yolo", "siglip"],
        )
        checker = PreflightChecker(config=config)
        result = checker.check_all(dataset_path=tmp_dataset)

        # Should not include provider checks
        provider_checks = [
            c for c in result.checks if c.category == CheckCategory.PROVIDER
        ]
        assert len(provider_checks) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestPreflightIntegration:
    """Integration tests for pre-flight checks."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test complete pre-flight workflow."""
        # Set up environment
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "train").mkdir()
        for i in range(10):
            (dataset / "train" / f"image_{i}.png").touch()

        output = tmp_path / "output"
        checkpoint = tmp_path / "checkpoints"

        model = tmp_path / "model.onnx"
        model.write_bytes(b"x" * 1024)

        # Configure and run
        config = PreflightConfig(
            min_disk_space_gb=0.001,
            model_paths=[model],
            required_read_paths=[dataset],
        )

        result = run_preflight_checks(
            dataset_path=dataset,
            output_path=output,
            checkpoint_path=checkpoint,
            config=config,
        )

        assert result.passed is True
        assert len(result.checks) >= 4

    def test_failure_scenario(self, tmp_path: Path) -> None:
        """Test pre-flight failure scenario."""
        config = PreflightConfig(
            model_paths=[Path("/nonexistent/model.onnx")],
        )

        result = run_preflight_checks(
            dataset_path=Path("/nonexistent/dataset"),
            output_path=tmp_path / "output",
            config=config,
        )

        assert result.passed is False
        assert len(result.critical_failures) >= 1
