# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Import validation tests for the annotation package.

These tests verify that all public APIs are importable and that
the package structure is correct.
"""

from __future__ import annotations


class TestPackageImports:
    """Test that all annotation package imports work correctly."""

    def test_top_level_import(self) -> None:
        """Test importing the main annotation package."""
        from image_preprocessing_detector import annotation

        assert hasattr(annotation, "__version__")
        assert hasattr(annotation, "SCHEMA_VERSION")
        assert hasattr(annotation, "create_orchestrator")
        assert hasattr(annotation, "AnnotationOrchestrator")

    def test_create_orchestrator_import(self) -> None:
        """Test importing create_orchestrator factory function."""
        from image_preprocessing_detector.annotation import create_orchestrator

        assert callable(create_orchestrator)

    def test_version_attributes(self) -> None:
        """Test version attributes are present and valid."""
        from image_preprocessing_detector.annotation import SCHEMA_VERSION, __version__

        assert isinstance(__version__, str)
        assert isinstance(SCHEMA_VERSION, str)
        assert __version__ == "0.1.0"
        assert SCHEMA_VERSION == "2.1"


class TestSchemasImports:
    """Test that all schema imports work correctly."""

    def test_enums_import(self) -> None:
        """Test importing enum classes."""
        from image_preprocessing_detector.annotation.schemas import (
            CaptureMethod,
            DomainLevel1,
            EnrichmentTier,
            ResolutionCategory,
        )

        # Verify they are enums with expected values
        assert CaptureMethod.BORN_DIGITAL.value == "born_digital"
        assert DomainLevel1.TAX.value == "TAX"
        assert EnrichmentTier.TIER_0_EXACT.value == "tier_0_exact"
        assert ResolutionCategory.STANDARD.value == "standard_300"

    def test_immutable_import(self) -> None:
        """Test importing immutable layer schemas."""
        from image_preprocessing_detector.annotation.schemas import (
            OriginalFileMetadata,
            OriginalLabels,
        )

        # Verify they are dataclasses
        assert hasattr(OriginalFileMetadata, "__dataclass_fields__")
        assert hasattr(OriginalLabels, "__dataclass_fields__")

    def test_enrichment_import(self) -> None:
        """Test importing enrichment layer schemas."""
        from image_preprocessing_detector.annotation.schemas import (
            EnrichmentData,
            EnrichmentVersion,
            LayoutDetection,
        )

        # Verify they are dataclasses
        assert hasattr(LayoutDetection, "__dataclass_fields__")
        assert hasattr(EnrichmentData, "__dataclass_fields__")
        assert hasattr(EnrichmentVersion, "__dataclass_fields__")

    def test_sample_import(self) -> None:
        """Test importing sample aggregate schema."""
        from image_preprocessing_detector.annotation.schemas import (
            SCHEMA_VERSION,
            SCRIPT_VERSION,
            SampleMetadata,
        )

        assert hasattr(SampleMetadata, "__dataclass_fields__")
        assert isinstance(SCHEMA_VERSION, str)
        assert isinstance(SCRIPT_VERSION, str)

    def test_migrations_import(self) -> None:
        """Test importing migration utilities."""
        from image_preprocessing_detector.annotation.schemas import (
            CURRENT_VERSION,
            MIN_SUPPORTED_VERSION,
            get_migration_path,
            migrate_sample,
            register_migration,
            rollback_sample,
        )

        assert CURRENT_VERSION == "2.1"
        assert MIN_SUPPORTED_VERSION == "1.0"
        assert callable(migrate_sample)
        assert callable(rollback_sample)
        assert callable(get_migration_path)
        assert callable(register_migration)


class TestIntegrityImports:
    """Test that all integrity imports work correctly."""

    def test_hashing_import(self) -> None:
        """Test importing hashing utilities."""
        from image_preprocessing_detector.annotation.integrity import (
            DEFAULT_CHUNK_SIZE,
            compute_content_hash,
            compute_full_sha256,
            compute_sample_id,
            compute_string_hash,
            verify_file_hash,
        )

        assert DEFAULT_CHUNK_SIZE == 65536
        assert callable(compute_full_sha256)
        assert callable(compute_sample_id)
        assert callable(compute_content_hash)
        assert callable(compute_string_hash)
        assert callable(verify_file_hash)

    def test_atomic_import(self) -> None:
        """Test importing atomic file utilities."""
        from image_preprocessing_detector.annotation.integrity import (
            atomic_json_write,
            atomic_write,
            safe_write_bytes,
            safe_write_text,
        )

        # atomic_write is a context manager
        assert callable(atomic_write)
        assert callable(safe_write_text)
        assert callable(safe_write_bytes)
        assert callable(atomic_json_write)


class TestConfigImports:
    """Test that all config imports work correctly."""

    def test_settings_import(self) -> None:
        """Test importing AnnotationSettings."""
        from image_preprocessing_detector.annotation.config import AnnotationSettings

        assert hasattr(AnnotationSettings, "__dataclass_fields__")
        assert hasattr(AnnotationSettings, "from_env")
        assert hasattr(AnnotationSettings, "from_yaml")
        assert hasattr(AnnotationSettings, "validate")

    def test_tiers_import(self) -> None:
        """Test importing tier definitions."""
        from image_preprocessing_detector.annotation.config import (
            CONTENT_FLAG_KEYS,
            TIER_0_DATASETS,
            TIER_1_DATASETS,
            get_tier_0_flags,
            get_tier_for_dataset,
            is_tier_0,
            is_tier_1,
        )

        assert isinstance(TIER_0_DATASETS, dict)
        assert isinstance(TIER_1_DATASETS, set)
        assert isinstance(CONTENT_FLAG_KEYS, list)
        assert callable(get_tier_for_dataset)
        assert callable(get_tier_0_flags)
        assert callable(is_tier_0)
        assert callable(is_tier_1)

    def test_tier_0_datasets_content(self) -> None:
        """Test that TIER_0_DATASETS has expected entries."""
        from image_preprocessing_detector.annotation.config import TIER_0_DATASETS

        # Check some known Tier 0 datasets
        assert "tablebank" in TIER_0_DATASETS
        assert "pubtabnet" in TIER_0_DATASETS
        assert "im2latex" in TIER_0_DATASETS
        assert "signatr6k" in TIER_0_DATASETS

        # Check content flags
        assert TIER_0_DATASETS["tablebank"]["has_table"] is True
        assert TIER_0_DATASETS["im2latex"]["has_formula"] is True
        assert TIER_0_DATASETS["signatr6k"]["has_signature"] is True
