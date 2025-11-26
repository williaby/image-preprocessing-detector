"""Tests for active learning module - Sprint 6.3.4.

Tests for sample harvesting, manifest generation, and privacy checks.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from image_preprocessing_detector.utils.datetime_compat import utc_now

from image_preprocessing_detector.drift.active_learning import (
    DEFAULT_AGREEMENT_THRESHOLD,
    DEFAULT_ENTROPY_THRESHOLD,
    DEFAULT_MAX_SAMPLES_PER_BATCH,
    DEFAULT_OUTPUT_DIR,
    PRIVACY_REVIEW_CHECKLIST,
    HarvestedSample,
    HarvesterConfig,
    HarvestManifest,
    HarvestReason,
    ManifestGenerator,
    PrivacyChecker,
    PrivacyStatus,
    SampleHarvester,
    create_harvester,
    get_privacy_checklist,
    harvest_and_manifest,
    save_privacy_checklist,
)


# ============================================================================
# HarvestedSample Tests
# ============================================================================


class TestHarvestedSample:
    """Tests for HarvestedSample data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/test.png",
            harvest_time=datetime(2025, 1, 15, 12, 0, 0),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            entropy=0.85,
            agreement_score=0.4,
            model_predictions={"student": 0.7, "teacher": 0.8},
            quality_scores={"blur": 0.2, "contrast": 0.9},
            metadata={"source": "test"},
            privacy_status=PrivacyStatus.APPROVED,
            checksum="abc123",
        )

        d = sample.to_dict()

        assert d["sample_id"] == "sample_001"
        assert d["harvest_reason"] == "high_entropy"
        assert d["entropy"] == 0.85
        assert d["privacy_status"] == "approved"

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "sample_id": "sample_001",
            "source_path": "/data/test.png",
            "harvest_time": "2025-01-15T12:00:00",
            "harvest_reason": "high_entropy",
            "entropy": 0.85,
            "agreement_score": 0.4,
        }

        sample = HarvestedSample.from_dict(data)

        assert sample.sample_id == "sample_001"
        assert sample.harvest_reason == HarvestReason.HIGH_ENTROPY


# ============================================================================
# HarvestManifest Tests
# ============================================================================


class TestHarvestManifest:
    """Tests for HarvestManifest data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        samples = [
            HarvestedSample(
                sample_id=f"sample_{i}",
                source_path=f"/data/test{i}.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
            )
            for i in range(3)
        ]

        manifest = HarvestManifest(
            manifest_id="manifest_001",
            created_at=datetime(2025, 1, 15, 12, 0, 0),
            samples=samples,
            total_count=3,
        )

        d = manifest.to_dict()

        assert d["manifest_id"] == "manifest_001"
        assert d["total_count"] == 3
        assert len(d["samples"]) == 3

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "manifest_id": "manifest_001",
            "created_at": "2025-01-15T12:00:00",
            "samples": [
                {
                    "sample_id": "sample_001",
                    "source_path": "/data/test.png",
                    "harvest_time": "2025-01-15T12:00:00",
                    "harvest_reason": "high_entropy",
                }
            ],
            "total_count": 1,
        }

        manifest = HarvestManifest.from_dict(data)

        assert manifest.manifest_id == "manifest_001"
        assert len(manifest.samples) == 1

    def test_update_counts(self) -> None:
        """Test updating status counts."""
        samples = [
            HarvestedSample(
                sample_id="s1",
                source_path="/data/t1.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
                privacy_status=PrivacyStatus.APPROVED,
            ),
            HarvestedSample(
                sample_id="s2",
                source_path="/data/t2.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
                privacy_status=PrivacyStatus.REJECTED,
            ),
            HarvestedSample(
                sample_id="s3",
                source_path="/data/t3.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
                privacy_status=PrivacyStatus.PENDING,
            ),
        ]

        manifest = HarvestManifest(
            manifest_id="test",
            created_at=utc_now(),
            samples=samples,
            total_count=0,
        )

        manifest.update_counts()

        assert manifest.total_count == 3
        assert manifest.approved_count == 1
        assert manifest.rejected_count == 1
        assert manifest.pending_count == 1


# ============================================================================
# HarvesterConfig Tests
# ============================================================================


class TestHarvesterConfig:
    """Tests for HarvesterConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = HarvesterConfig()

        assert config.output_dir == DEFAULT_OUTPUT_DIR
        assert config.entropy_threshold == DEFAULT_ENTROPY_THRESHOLD
        assert config.agreement_threshold == DEFAULT_AGREEMENT_THRESHOLD
        assert config.max_samples_per_batch == DEFAULT_MAX_SAMPLES_PER_BATCH

    def test_to_dict(self) -> None:
        """Test serialization."""
        config = HarvesterConfig(
            output_dir="/custom/path",
            entropy_threshold=0.8,
        )

        d = config.to_dict()

        assert d["output_dir"] == "/custom/path"
        assert d["entropy_threshold"] == 0.8


# ============================================================================
# PrivacyChecker Tests
# ============================================================================


class TestPrivacyChecker:
    """Tests for PrivacyChecker."""

    def test_check_clean_sample(self) -> None:
        """Test checking a clean sample."""
        checker = PrivacyChecker()

        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/documents/test.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            metadata={"quality": 0.85},
        )

        status, notes = checker.check_sample(sample)

        assert status == PrivacyStatus.APPROVED

    def test_check_sensitive_path(self) -> None:
        """Test checking sample with sensitive path."""
        checker = PrivacyChecker()

        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/personal/private_doc.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
        )

        status, notes = checker.check_sample(sample)

        assert status == PrivacyStatus.REQUIRES_REVIEW
        assert "sensitive pattern" in notes.lower() or "personal" in notes.lower()

    def test_check_pii_in_metadata(self) -> None:
        """Test checking sample with PII in metadata."""
        checker = PrivacyChecker()

        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/test.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            metadata={"ssn": "123-45-6789"},  # PII indicator
        )

        status, notes = checker.check_sample(sample)

        assert status == PrivacyStatus.REQUIRES_REVIEW
        assert "ssn" in notes.lower()

    def test_custom_rule(self) -> None:
        """Test custom privacy rule."""
        # Rule that rejects samples with certain entropy
        def custom_rule(sample: HarvestedSample) -> bool:
            return sample.entropy is None or sample.entropy < 0.99

        checker = PrivacyChecker(custom_rules=[custom_rule])

        # Sample that fails custom rule
        sample = HarvestedSample(
            sample_id="sample_001",
            source_path="/data/test.png",
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            entropy=0.995,  # Above 0.99
        )

        status, notes = checker.check_sample(sample)

        assert status == PrivacyStatus.REQUIRES_REVIEW

    def test_check_batch(self) -> None:
        """Test checking multiple samples."""
        checker = PrivacyChecker()

        samples = [
            HarvestedSample(
                sample_id="s1",
                source_path="/data/clean.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
            ),
            HarvestedSample(
                sample_id="s2",
                source_path="/data/personal/sensitive.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
            ),
        ]

        results = checker.check_batch(samples)

        assert len(results) == 2
        assert results["s1"][0] == PrivacyStatus.APPROVED
        assert results["s2"][0] == PrivacyStatus.REQUIRES_REVIEW


# ============================================================================
# SampleHarvester Tests
# ============================================================================


class TestSampleHarvester:
    """Tests for SampleHarvester."""

    def test_should_harvest_high_entropy(self) -> None:
        """Test harvesting decision for high entropy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(output_dir=tmpdir, entropy_threshold=0.7)
            harvester = SampleHarvester(config)

            should, reason = harvester.should_harvest(entropy=0.85)

            assert should is True
            assert reason == HarvestReason.HIGH_ENTROPY

    def test_should_harvest_low_agreement(self) -> None:
        """Test harvesting decision for low agreement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(output_dir=tmpdir, agreement_threshold=0.5)
            harvester = SampleHarvester(config)

            should, reason = harvester.should_harvest(agreement=0.3)

            assert should is True
            assert reason == HarvestReason.LOW_AGREEMENT

    def test_should_harvest_teacher_escalation(self) -> None:
        """Test harvesting decision for teacher escalation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(output_dir=tmpdir)
            harvester = SampleHarvester(config)

            should, reason = harvester.should_harvest(is_teacher_escalation=True)

            assert should is True
            assert reason == HarvestReason.TEACHER_ESCALATION

    def test_should_harvest_quality_outlier(self) -> None:
        """Test harvesting decision for quality outlier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(output_dir=tmpdir)
            harvester = SampleHarvester(config)

            should, reason = harvester.should_harvest(
                quality_scores={"blur": 0.05}  # Extreme value
            )

            assert should is True
            assert reason == HarvestReason.QUALITY_OUTLIER

    def test_should_not_harvest_normal(self) -> None:
        """Test no harvest for normal values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(output_dir=tmpdir)
            harvester = SampleHarvester(config)

            should, reason = harvester.should_harvest(
                entropy=0.5, agreement=0.8, quality_scores={"blur": 0.5}
            )

            assert should is False
            assert reason is None

    def test_harvest_sample(self) -> None:
        """Test harvesting a sample."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "input" / "test.png"
            test_file.parent.mkdir(parents=True)
            test_file.write_bytes(b"test content")

            config = HarvesterConfig(
                output_dir=str(Path(tmpdir) / "output"),
                copy_sample_files=True,
                compute_checksums=True,
            )
            harvester = SampleHarvester(config)

            sample = harvester.harvest_sample(
                source_path=str(test_file),
                reason=HarvestReason.HIGH_ENTROPY,
                entropy=0.85,
                model_predictions={"student": 0.7},
            )

            assert sample.sample_id.startswith("sample_")
            assert sample.entropy == 0.85
            assert sample.harvest_reason == HarvestReason.HIGH_ENTROPY
            assert sample.checksum  # Should have checksum

    def test_batch_tracking(self) -> None:
        """Test batch tracking functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(
                output_dir=tmpdir,
                copy_sample_files=False,
            )
            harvester = SampleHarvester(config)

            # Harvest some samples
            for i in range(3):
                harvester.harvest_sample(
                    source_path=f"/data/test{i}.png",
                    reason=HarvestReason.HIGH_ENTROPY,
                )

            assert harvester.get_batch_size() == 3

            batch = harvester.get_current_batch()
            assert len(batch) == 3

            harvester.clear_batch()
            assert harvester.get_batch_size() == 0

    def test_batch_full_check(self) -> None:
        """Test batch full detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(
                output_dir=tmpdir,
                max_samples_per_batch=5,
                copy_sample_files=False,
            )
            harvester = SampleHarvester(config)

            assert not harvester.is_batch_full()

            for i in range(5):
                harvester.harvest_sample(
                    source_path=f"/data/test{i}.png",
                    reason=HarvestReason.HIGH_ENTROPY,
                )

            assert harvester.is_batch_full()


# ============================================================================
# ManifestGenerator Tests
# ============================================================================


class TestManifestGenerator:
    """Tests for ManifestGenerator."""

    def test_create_manifest(self) -> None:
        """Test creating a manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ManifestGenerator(tmpdir)

            samples = [
                HarvestedSample(
                    sample_id=f"sample_{i}",
                    source_path=f"/data/test{i}.png",
                    harvest_time=utc_now(),
                    harvest_reason=HarvestReason.HIGH_ENTROPY,
                )
                for i in range(3)
            ]

            manifest = generator.create_manifest(samples)

            assert manifest.manifest_id.startswith("manifest_")
            assert manifest.total_count == 3

    def test_save_and_load_manifest(self) -> None:
        """Test saving and loading manifests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ManifestGenerator(tmpdir)

            samples = [
                HarvestedSample(
                    sample_id="sample_001",
                    source_path="/data/test.png",
                    harvest_time=utc_now(),
                    harvest_reason=HarvestReason.HIGH_ENTROPY,
                )
            ]

            manifest = generator.create_manifest(samples)
            path = generator.save_manifest(manifest)

            # Verify file exists
            assert path.exists()

            # Load and verify
            loaded = generator.load_manifest(path)
            assert loaded.manifest_id == manifest.manifest_id
            assert loaded.total_count == 1

    def test_get_latest_manifest(self) -> None:
        """Test getting latest manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ManifestGenerator(tmpdir)

            # No manifests yet
            assert generator.get_latest_manifest() is None

            # Create and save a manifest
            samples = [
                HarvestedSample(
                    sample_id="sample_001",
                    source_path="/data/test.png",
                    harvest_time=utc_now(),
                    harvest_reason=HarvestReason.HIGH_ENTROPY,
                )
            ]

            manifest = generator.create_manifest(samples)
            generator.save_manifest(manifest)

            # Should find latest
            latest = generator.get_latest_manifest()
            assert latest is not None
            assert latest.manifest_id == manifest.manifest_id

    def test_generate_training_split(self) -> None:
        """Test generating training split."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ManifestGenerator(tmpdir)

            # Create manifest with approved and non-approved samples
            samples = [
                HarvestedSample(
                    sample_id=f"sample_{i}",
                    source_path=f"/data/test{i}.png",
                    harvest_time=utc_now(),
                    harvest_reason=HarvestReason.HIGH_ENTROPY,
                    privacy_status=(
                        PrivacyStatus.APPROVED if i < 8 else PrivacyStatus.PENDING
                    ),
                )
                for i in range(10)
            ]

            manifest = generator.create_manifest(samples)
            split = generator.generate_training_split(manifest)

            # Only approved samples (8) should be split
            total_in_split = len(split["train"]) + len(split["val"]) + len(split["test"])
            assert total_in_split == 8

    def test_list_manifests(self) -> None:
        """Test listing manifests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ManifestGenerator(tmpdir)

            # Create multiple manifests
            for _ in range(3):
                samples = [
                    HarvestedSample(
                        sample_id="sample_001",
                        source_path="/data/test.png",
                        harvest_time=utc_now(),
                        harvest_reason=HarvestReason.HIGH_ENTROPY,
                    )
                ]
                manifest = generator.create_manifest(samples)
                generator.save_manifest(manifest)

            manifests = generator.list_manifests()
            assert len(manifests) == 3


# ============================================================================
# Privacy Checklist Tests
# ============================================================================


class TestPrivacyChecklist:
    """Tests for privacy checklist functions."""

    def test_get_privacy_checklist(self) -> None:
        """Test getting privacy checklist."""
        checklist = get_privacy_checklist()

        assert "Privacy Review Checklist" in checklist
        assert "PII Detection" in checklist
        assert "Consent Verification" in checklist

    def test_save_privacy_checklist(self) -> None:
        """Test saving privacy checklist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "checklist.md"

            save_privacy_checklist(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "Privacy Review Checklist" in content


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_harvester(self) -> None:
        """Test creating harvester with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harvester = create_harvester(
                output_dir=tmpdir,
                entropy_threshold=0.8,
            )

            assert harvester is not None
            assert harvester.config.entropy_threshold == 0.8

    def test_harvest_and_manifest(self) -> None:
        """Test combined harvest and manifest generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HarvesterConfig(
                output_dir=str(Path(tmpdir) / "samples"),
                copy_sample_files=False,
            )
            harvester = SampleHarvester(config)
            generator = ManifestGenerator(str(Path(tmpdir) / "manifests"))

            samples_to_harvest = [
                {
                    "source_path": "/data/test1.png",
                    "entropy": 0.85,  # Above threshold
                },
                {
                    "source_path": "/data/test2.png",
                    "entropy": 0.5,  # Below threshold
                },
                {
                    "source_path": "/data/test3.png",
                    "agreement": 0.3,  # Low agreement
                },
            ]

            manifest = harvest_and_manifest(harvester, generator, samples_to_harvest)

            # Should have manifest with 2 samples (entropy and agreement triggers)
            assert manifest is not None
            assert manifest.total_count == 2


# ============================================================================
# Enum Tests
# ============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_harvest_reason_values(self) -> None:
        """Test HarvestReason enum values."""
        assert HarvestReason.HIGH_ENTROPY.value == "high_entropy"
        assert HarvestReason.LOW_AGREEMENT.value == "low_agreement"
        assert HarvestReason.TEACHER_ESCALATION.value == "teacher_escalation"
        assert HarvestReason.QUALITY_OUTLIER.value == "quality_outlier"
        assert HarvestReason.DRIFT_DETECTED.value == "drift_detected"

    def test_privacy_status_values(self) -> None:
        """Test PrivacyStatus enum values."""
        assert PrivacyStatus.PENDING.value == "pending"
        assert PrivacyStatus.APPROVED.value == "approved"
        assert PrivacyStatus.REJECTED.value == "rejected"
        assert PrivacyStatus.REQUIRES_REVIEW.value == "requires_review"


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_threshold_values(self) -> None:
        """Test threshold constant values are reasonable."""
        assert 0 < DEFAULT_ENTROPY_THRESHOLD < 1
        assert 0 < DEFAULT_AGREEMENT_THRESHOLD < 1

    def test_max_samples_reasonable(self) -> None:
        """Test max samples is reasonable."""
        assert DEFAULT_MAX_SAMPLES_PER_BATCH >= 10
        assert DEFAULT_MAX_SAMPLES_PER_BATCH <= 1000

    def test_checklist_not_empty(self) -> None:
        """Test checklist constant is not empty."""
        assert len(PRIVACY_REVIEW_CHECKLIST) > 100
        assert "checklist" in PRIVACY_REVIEW_CHECKLIST.lower()
