"""Unit tests for annotation configuration system.

Tests AnnotationSettings, tier definitions, and configuration loading.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest
import yaml

from image_preprocessing_detector.annotation.config import (
    CONTENT_FLAG_KEYS,
    TIER_0_DATASETS,
    TIER_1_DATASETS,
    AnnotationSettings,
    get_tier_0_flags,
    get_tier_for_dataset,
    is_tier_0,
    is_tier_1,
)
from image_preprocessing_detector.annotation.schemas import EnrichmentTier


class TestAnnotationSettings:
    """Test AnnotationSettings dataclass."""

    def test_default_values(self) -> None:
        """Test that defaults are sensible."""
        settings = AnnotationSettings()

        assert settings.batch_size == 100
        assert settings.workers == 4
        assert settings.cache_size_limit == 10_000
        assert settings.checkpoint_interval == 100
        assert settings.hash_full_file is True  # P0-1 fix - always True
        assert settings.atomic_fsync is False
        assert settings.yolo_confidence_threshold == pytest.approx(0.25)
        assert settings.siglip_batch_size == 32

    def test_custom_values(self) -> None:
        """Test creating settings with custom values."""
        settings = AnnotationSettings(
            batch_size=200,
            workers=8,
            yolo_confidence_threshold=0.5,
        )

        assert settings.batch_size == 200
        assert settings.workers == 8
        assert settings.yolo_confidence_threshold == pytest.approx(0.5)

    def test_frozen_dataclass(self) -> None:
        """Test that settings are immutable."""
        settings = AnnotationSettings()

        with pytest.raises(AttributeError):
            settings.batch_size = 200  # type: ignore[misc]

    def test_hash_full_file_always_true(self) -> None:
        """Test that hash_full_file is always True (P0-1 fix)."""
        # Even if explicitly set to False, it should be True
        # This is enforced by the class design
        settings = AnnotationSettings(hash_full_file=False)

        # Note: In current implementation, user CAN set to False
        # but validation should catch it. Let's test the validator.
        issues = settings.validate()
        assert any("hash_full_file must be True" in issue for issue in issues)


class TestAnnotationSettingsFromEnv:
    """Test loading AnnotationSettings from environment variables."""

    def test_from_env_defaults(self) -> None:
        """Test loading from env with no vars set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = AnnotationSettings.from_env()

        assert settings.batch_size == 100
        assert settings.workers == 4
        assert settings.hash_full_file is True

    def test_from_env_custom_values(self) -> None:
        """Test loading custom values from env."""
        env = {
            "ANNOTATION_BATCH_SIZE": "200",
            "ANNOTATION_WORKERS": "8",
            "ANNOTATION_CACHE_SIZE": "5000",
            "ANNOTATION_YOLO_CONFIDENCE": "0.35",
            "ANNOTATION_ATOMIC_FSYNC": "true",
        }

        with mock.patch.dict(os.environ, env, clear=True):
            settings = AnnotationSettings.from_env()

        assert settings.batch_size == 200
        assert settings.workers == 8
        assert settings.cache_size_limit == 5000
        assert settings.yolo_confidence_threshold == pytest.approx(0.35)
        assert settings.atomic_fsync is True

    def test_from_env_paths(self) -> None:
        """Test loading path values from env."""
        env = {
            "ANNOTATION_E_DRIVE_ROOT": "/custom/data",
            "ANNOTATION_METADATA_ROOT": "/custom/metadata",
            "ANNOTATION_YOLO_MODEL_PATH": "/models/yolo.pt",
        }

        with mock.patch.dict(os.environ, env, clear=True):
            settings = AnnotationSettings.from_env()

        assert settings.e_drive_root == Path("/custom/data")
        assert settings.metadata_root == Path("/custom/metadata")
        assert settings.yolo_model_path == Path("/models/yolo.pt")

    def test_from_env_boolean_variations(self) -> None:
        """Test various boolean string formats."""
        for true_val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            env = {"ANNOTATION_ATOMIC_FSYNC": true_val}
            with mock.patch.dict(os.environ, env, clear=True):
                settings = AnnotationSettings.from_env()
                assert settings.atomic_fsync is True, f"Failed for {true_val}"

        for false_val in ["false", "False", "0", "no", "anything"]:
            env = {"ANNOTATION_ATOMIC_FSYNC": false_val}
            with mock.patch.dict(os.environ, env, clear=True):
                settings = AnnotationSettings.from_env()
                assert settings.atomic_fsync is False, f"Failed for {false_val}"


class TestAnnotationSettingsFromYaml:
    """Test loading AnnotationSettings from YAML files."""

    def test_from_yaml_flat_structure(self, tmp_path: Path) -> None:
        """Test loading from flat YAML structure."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "e_drive_root": "/custom/data",
                    "batch_size": 200,
                    "workers": 8,
                }
            )
        )

        settings = AnnotationSettings.from_yaml(config_file)

        assert settings.e_drive_root == Path("/custom/data")
        assert settings.batch_size == 200
        assert settings.workers == 8

    def test_from_yaml_nested_structure(self, tmp_path: Path) -> None:
        """Test loading from nested YAML structure."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "annotation": {
                        "batch_size": 150,
                        "workers": 6,
                        "yolo": {
                            "confidence_threshold": 0.4,
                            "model_path": "/models/yolo.pt",
                        },
                    }
                }
            )
        )

        settings = AnnotationSettings.from_yaml(config_file)

        assert settings.batch_size == 150
        assert settings.workers == 6
        assert settings.yolo_confidence_threshold == pytest.approx(0.4)
        assert settings.yolo_model_path == Path("/models/yolo.pt")

    def test_from_yaml_file_not_found(self, tmp_path: Path) -> None:
        """Test error when YAML file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            AnnotationSettings.from_yaml(config_file)

    def test_from_yaml_invalid_format(self, tmp_path: Path) -> None:
        """Test error when YAML has invalid format."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("- just\n- a\n- list")

        with pytest.raises(TypeError, match="must contain a mapping"):
            AnnotationSettings.from_yaml(config_file)


class TestAnnotationSettingsValidation:
    """Test AnnotationSettings validation."""

    def test_validate_valid_settings(self) -> None:
        """Test validation of valid settings."""
        settings = AnnotationSettings()
        issues = settings.validate()

        # Only warning should be about non-existent default paths
        config_errors = [i for i in issues if "must be" in i]
        assert len(config_errors) == 0

    def test_validate_invalid_batch_size(self) -> None:
        """Test validation catches invalid batch_size."""
        settings = AnnotationSettings(batch_size=0)
        issues = settings.validate()

        assert any("batch_size must be positive" in i for i in issues)

    def test_validate_invalid_workers(self) -> None:
        """Test validation catches invalid workers."""
        settings = AnnotationSettings(workers=-1)
        issues = settings.validate()

        assert any("workers must be positive" in i for i in issues)

    def test_validate_invalid_yolo_confidence(self) -> None:
        """Test validation catches invalid YOLO confidence."""
        settings = AnnotationSettings(yolo_confidence_threshold=1.5)
        issues = settings.validate()

        assert any("yolo_confidence_threshold must be" in i for i in issues)

    def test_to_dict(self) -> None:
        """Test converting settings to dictionary."""
        settings = AnnotationSettings(batch_size=200)
        result = settings.to_dict()

        assert isinstance(result, dict)
        assert result["batch_size"] == 200
        assert "e_drive_root" in result
        assert "yolo_confidence_threshold" in result


class TestTierDefinitions:
    """Test tier definitions and helper functions."""

    def test_tier_0_datasets_structure(self) -> None:
        """Test TIER_0_DATASETS has expected structure."""
        assert isinstance(TIER_0_DATASETS, dict)
        assert len(TIER_0_DATASETS) > 0

        for dataset, flags in TIER_0_DATASETS.items():
            assert isinstance(dataset, str)
            assert isinstance(flags, dict)
            # At least one content flag should be True
            assert any(flags.get(k, False) for k in CONTENT_FLAG_KEYS), (
                f"No content flag set for {dataset}"
            )

    def test_tier_1_datasets_structure(self) -> None:
        """Test TIER_1_DATASETS has expected structure."""
        assert isinstance(TIER_1_DATASETS, set)
        assert len(TIER_1_DATASETS) > 0

        for dataset in TIER_1_DATASETS:
            assert isinstance(dataset, str)

    def test_known_tier_0_datasets(self) -> None:
        """Test expected Tier 0 datasets are present."""
        expected = ["tablebank", "pubtabnet", "im2latex", "signatr6k"]

        for dataset in expected:
            assert dataset in TIER_0_DATASETS, f"Missing Tier 0 dataset: {dataset}"

    def test_known_tier_1_datasets(self) -> None:
        """Test expected Tier 1 datasets are present."""
        expected = ["doclaynet", "tablebank", "funsd"]

        for dataset in expected:
            assert dataset in TIER_1_DATASETS, f"Missing Tier 1 dataset: {dataset}"

    def test_content_flag_keys(self) -> None:
        """Test CONTENT_FLAG_KEYS has expected keys."""
        expected = [
            "has_table",
            "has_formula",
            "has_handwriting",
            "has_signature",
            "has_figure",
        ]

        for key in expected:
            assert key in CONTENT_FLAG_KEYS


class TestTierHelperFunctions:
    """Test tier helper functions."""

    def test_is_tier_0(self) -> None:
        """Test is_tier_0 function."""
        assert is_tier_0("tablebank") is True
        assert is_tier_0("pubtabnet") is True
        assert is_tier_0("unknown_dataset") is False

    def test_is_tier_1(self) -> None:
        """Test is_tier_1 function."""
        assert is_tier_1("doclaynet") is True
        assert is_tier_1("funsd") is True
        assert is_tier_1("unknown_dataset") is False

    def test_get_tier_for_dataset(self) -> None:
        """Test get_tier_for_dataset function."""
        # Tier 0 datasets
        assert get_tier_for_dataset("tablebank") == EnrichmentTier.TIER_0_EXACT
        assert get_tier_for_dataset("im2latex") == EnrichmentTier.TIER_0_EXACT

        # Tier 1 datasets (that aren't also Tier 0)
        assert get_tier_for_dataset("doclaynet") == EnrichmentTier.TIER_1_ANNOTATION
        assert get_tier_for_dataset("funsd") == EnrichmentTier.TIER_1_ANNOTATION

        # Unknown datasets default to Tier 2
        assert get_tier_for_dataset("random_dataset") == EnrichmentTier.TIER_2_MODEL

    def test_get_tier_0_flags(self) -> None:
        """Test get_tier_0_flags function."""
        # Tier 0 dataset should return flags
        flags = get_tier_0_flags("tablebank")
        assert flags is not None
        assert flags["has_table"] is True

        # Non-Tier 0 dataset should return None
        flags = get_tier_0_flags("unknown_dataset")
        assert flags is None

    def test_tier_0_overrides_tier_1(self) -> None:
        """Test that Tier 0 takes precedence for datasets in both."""
        # tablebank is in both TIER_0 and TIER_1
        assert "tablebank" in TIER_0_DATASETS
        assert "tablebank" in TIER_1_DATASETS

        # get_tier_for_dataset should return TIER_0
        assert get_tier_for_dataset("tablebank") == EnrichmentTier.TIER_0_EXACT
