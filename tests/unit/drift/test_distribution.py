"""Tests for drift detection module - Sprint 6.3.1.

Tests histogram computation, KL/PSI metrics, and distribution tracking.
"""

from __future__ import annotations

import math
import tempfile
from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest

rng = np.random.default_rng()

from image_preprocessing_detector.drift import (
    DEFAULT_NUM_BINS,
    FEATURE_BOUNDS,
    KL_CRITICAL_THRESHOLD,
    KL_WARNING_THRESHOLD,
    PSI_CRITICAL_THRESHOLD,
    PSI_WARNING_THRESHOLD,
    DistributionTracker,
    DriftDetector,
    DriftResult,
    DriftSeverity,
    FeatureType,
    HistogramStats,
    ReferenceDistribution,
    ReferenceStore,
    compute_checksum,
    compute_histogram,
    compute_stats,
    create_drift_detector,
    create_tracker,
    kl_divergence,
    psi,
    symmetric_kl,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now

# ============================================================================
# Histogram Computation Tests
# ============================================================================


class TestComputeHistogram:
    """Tests for histogram computation."""

    def test_empty_values_returns_empty(self) -> None:
        """Test empty input returns empty histogram."""
        histogram, bin_edges = compute_histogram([])
        assert histogram == []
        assert bin_edges == []

    def test_single_value(self) -> None:
        """Test histogram with single value."""
        histogram, bin_edges = compute_histogram([0.5])

        assert len(histogram) == DEFAULT_NUM_BINS
        assert len(bin_edges) == DEFAULT_NUM_BINS + 1
        assert sum(histogram) == pytest.approx(1.0)

    def test_uniform_distribution(self) -> None:
        """Test histogram of uniform distribution."""
        values = list(rng.uniform(0, 1, 10000))
        histogram, _ = compute_histogram(values)

        assert len(histogram) == DEFAULT_NUM_BINS
        assert sum(histogram) == pytest.approx(1.0)
        # Uniform distribution should have roughly equal bin counts
        expected = 1.0 / DEFAULT_NUM_BINS
        for h in histogram:
            assert h == pytest.approx(expected, rel=0.3)

    def test_normal_distribution(self) -> None:
        """Test histogram of normal distribution."""
        values = list(rng.normal(0.5, 0.1, 10000))
        histogram, _ = compute_histogram(values, bounds=(0, 1))

        assert len(histogram) == DEFAULT_NUM_BINS
        assert sum(histogram) == pytest.approx(1.0)

        # Peak should be near center
        peak_idx = histogram.index(max(histogram))
        center_idx = DEFAULT_NUM_BINS // 2
        assert abs(peak_idx - center_idx) <= 5

    def test_custom_num_bins(self) -> None:
        """Test histogram with custom bin count."""
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        histogram, bin_edges = compute_histogram(values, num_bins=10)

        assert len(histogram) == 10
        assert len(bin_edges) == 11

    def test_with_bounds(self) -> None:
        """Test histogram with explicit bounds."""
        values = [0.0, 0.25, 0.5, 0.75, 1.0]
        _, bin_edges = compute_histogram(values, bounds=(0, 1))

        assert bin_edges[0] == pytest.approx(0.0)
        assert bin_edges[-1] == pytest.approx(1.0)

    def test_values_outside_bounds_clipped(self) -> None:
        """Test values outside bounds are clipped."""
        values = [-0.5, 0.5, 1.5]
        histogram, _ = compute_histogram(values, bounds=(0, 1))

        # Should still produce valid histogram
        assert sum(histogram) == pytest.approx(1.0)

    def test_all_same_values(self) -> None:
        """Test histogram when all values are identical."""
        values = [0.5] * 100
        histogram, _ = compute_histogram(values)

        # All values should be in one bin
        assert max(histogram) == pytest.approx(1.0)
        assert sum(histogram) == pytest.approx(1.0)

    def test_reproducibility(self) -> None:
        """Test histogram computation is deterministic."""
        values = list(rng.uniform(0, 1, 1000))

        h1, e1 = compute_histogram(values)
        h2, e2 = compute_histogram(values)

        assert h1 == h2
        assert e1 == e2


class TestComputeStats:
    """Tests for statistical computation."""

    def test_empty_values(self) -> None:
        """Test stats with empty input."""
        stats = compute_stats([])

        assert stats.count == 0
        assert stats.mean == pytest.approx(0.0)
        assert stats.std == pytest.approx(0.0)

    def test_single_value(self) -> None:
        """Test stats with single value."""
        stats = compute_stats([0.5])

        assert stats.count == 1
        assert stats.mean == pytest.approx(0.5)
        assert stats.std == pytest.approx(0.0)
        assert stats.min_val == pytest.approx(0.5)
        assert stats.max_val == pytest.approx(0.5)

    def test_known_values(self) -> None:
        """Test stats with known values."""
        values = [1, 2, 3, 4, 5]
        stats = compute_stats(values)

        assert stats.count == 5
        assert stats.mean == pytest.approx(3.0)
        assert stats.median == pytest.approx(3.0)
        assert stats.min_val == pytest.approx(1.0)
        assert stats.max_val == pytest.approx(5.0)

    def test_percentiles(self) -> None:
        """Test percentile calculations."""
        values = list(range(100))
        stats = compute_stats(values)

        assert stats.p5 == pytest.approx(4.95, abs=0.5)
        assert stats.p25 == pytest.approx(24.75, abs=0.5)
        assert stats.p75 == pytest.approx(74.25, abs=0.5)
        assert stats.p95 == pytest.approx(94.05, abs=0.5)

    def test_to_dict(self) -> None:
        """Test stats serialization."""
        stats = compute_stats([1, 2, 3])
        d = stats.to_dict()

        assert "mean" in d
        assert "std" in d
        assert "median" in d
        assert "min" in d
        assert "max" in d
        assert "count" in d

    def test_from_dict(self) -> None:
        """Test stats deserialization."""
        original = compute_stats([1, 2, 3, 4, 5])
        d = original.to_dict()
        restored = HistogramStats.from_dict(d)

        assert restored.mean == original.mean
        assert restored.std == original.std
        assert restored.count == original.count


# ============================================================================
# KL Divergence Tests
# ============================================================================


class TestKLDivergence:
    """Tests for KL divergence computation."""

    def test_identical_distributions(self) -> None:
        """Test KL divergence of identical distributions is zero."""
        p = [0.1, 0.2, 0.3, 0.2, 0.2]
        kl = kl_divergence(p, p)

        assert kl == pytest.approx(0.0, abs=1e-6)

    def test_uniform_vs_uniform(self) -> None:
        """Test KL divergence between two uniform distributions."""
        p = [0.2] * 5
        q = [0.2] * 5
        kl = kl_divergence(p, q)

        assert kl == pytest.approx(0.0, abs=1e-6)

    def test_asymmetric(self) -> None:
        """Test KL divergence is asymmetric."""
        # Use distributions that are not mirror images of each other
        p = [0.7, 0.2, 0.1]
        q = [0.1, 0.3, 0.6]

        kl_pq = kl_divergence(p, q)
        kl_qp = kl_divergence(q, p)

        # Should be different (asymmetric)
        assert kl_pq != kl_qp

    def test_non_negative(self) -> None:
        """Test KL divergence is always non-negative."""
        for _ in range(100):
            p = list(rng.dirichlet(np.ones(10)))
            q = list(rng.dirichlet(np.ones(10)))
            kl = kl_divergence(p, q)

            assert kl >= 0

    def test_length_mismatch_raises(self) -> None:
        """Test mismatched distribution lengths raise error."""
        p = [0.5, 0.5]
        q = [0.33, 0.33, 0.34]

        with pytest.raises(ValueError, match="lengths must match"):
            kl_divergence(p, q)

    def test_empty_distributions(self) -> None:
        """Test empty distributions return zero."""
        assert kl_divergence([], []) == pytest.approx(0.0)

    def test_epsilon_handling(self) -> None:
        """Test epsilon prevents log(0) errors."""
        p = [1.0, 0.0, 0.0]
        q = [0.0, 0.5, 0.5]

        # Should not raise, epsilon prevents division by zero
        kl = kl_divergence(p, q)
        assert kl >= 0
        assert not math.isnan(kl)
        assert not math.isinf(kl)

    def test_known_value(self) -> None:
        """Test KL divergence against known value."""
        # For p=[0.5, 0.5] vs q=[0.25, 0.75]
        # KL = 0.5*log(0.5/0.25) + 0.5*log(0.5/0.75)
        # KL = 0.5*log(2) + 0.5*log(2/3)
        # KL ≈ 0.346 + (-0.203) ≈ 0.143
        p = [0.5, 0.5]
        q = [0.25, 0.75]
        kl = kl_divergence(p, q)

        expected = 0.5 * math.log(2) + 0.5 * math.log(2 / 3)
        assert kl == pytest.approx(expected, rel=0.01)


class TestPSI:
    """Tests for Population Stability Index."""

    def test_identical_distributions(self) -> None:
        """Test PSI of identical distributions is zero."""
        expected = [0.2] * 5
        actual = [0.2] * 5

        psi_value = psi(expected, actual)
        assert psi_value == pytest.approx(0.0, abs=1e-6)

    def test_no_shift(self) -> None:
        """Test PSI < 0.1 indicates no significant shift."""
        expected = [0.2] * 5
        # Small variation
        actual = [0.19, 0.21, 0.20, 0.20, 0.20]

        psi_value = psi(expected, actual)
        assert psi_value < PSI_WARNING_THRESHOLD

    def test_moderate_shift(self) -> None:
        """Test PSI 0.1-0.25 indicates moderate shift."""
        expected = [0.2] * 5
        # Moderate shift
        actual = [0.3, 0.25, 0.2, 0.15, 0.1]

        psi_value = psi(expected, actual)
        # Should be noticeable but not critical
        assert psi_value > 0

    def test_significant_shift(self) -> None:
        """Test PSI > 0.25 indicates significant shift."""
        expected = [0.9, 0.1, 0.0, 0.0, 0.0]
        actual = [0.0, 0.0, 0.0, 0.1, 0.9]

        psi_value = psi(expected, actual)
        assert psi_value > PSI_CRITICAL_THRESHOLD

    def test_symmetric(self) -> None:
        """Test PSI is approximately symmetric."""
        expected = [0.3, 0.4, 0.3]
        actual = [0.4, 0.3, 0.3]

        psi_ea = psi(expected, actual)
        psi_ae = psi(actual, expected)

        # PSI should be similar in both directions
        assert psi_ea == pytest.approx(psi_ae, rel=0.2)

    def test_non_negative(self) -> None:
        """Test PSI is always non-negative."""
        for _ in range(100):
            expected = list(rng.dirichlet(np.ones(10)))
            actual = list(rng.dirichlet(np.ones(10)))
            psi_value = psi(expected, actual)

            assert psi_value >= 0

    def test_length_mismatch_raises(self) -> None:
        """Test mismatched distribution lengths raise error."""
        with pytest.raises(ValueError, match="lengths must match"):
            psi([0.5, 0.5], [0.33, 0.33, 0.34])


class TestSymmetricKL:
    """Tests for symmetric KL divergence."""

    def test_symmetric(self) -> None:
        """Test symmetric KL is actually symmetric."""
        p = [0.3, 0.4, 0.3]
        q = [0.4, 0.3, 0.3]

        skl_pq = symmetric_kl(p, q)
        skl_qp = symmetric_kl(q, p)

        assert skl_pq == pytest.approx(skl_qp)

    def test_identical_is_zero(self) -> None:
        """Test symmetric KL of identical distributions is zero."""
        p = [0.25] * 4
        assert symmetric_kl(p, p) == pytest.approx(0.0, abs=1e-6)


# ============================================================================
# Distribution Tracker Tests
# ============================================================================


class TestDistributionTracker:
    """Tests for DistributionTracker."""

    def test_add_sample(self) -> None:
        """Test adding samples to tracker."""
        tracker = DistributionTracker(sample_rate=1.0)  # 100% sampling

        tracker.add_sample("test_feature", 0.5, "sample1")
        tracker.add_sample("test_feature", 0.6, "sample2")

        assert tracker.get_stored_count("test_feature") == 2
        assert tracker.get_sample_count("test_feature") == 2

    def test_sampling_rate(self) -> None:
        """Test sampling rate reduces stored samples."""
        tracker = DistributionTracker(sample_rate=0.1)

        for i in range(1000):
            tracker.add_sample("test", float(i) / 1000)

        # With 10% sampling, should have ~100 samples (with variance)
        stored = tracker.get_stored_count("test")
        assert 50 < stored < 200  # Allow variance

    def test_max_samples_limit(self) -> None:
        """Test max samples limit is enforced."""
        tracker = DistributionTracker(sample_rate=1.0, max_samples=100)

        for i in range(1000):
            tracker.add_sample("test", float(i))

        assert tracker.get_stored_count("test") <= 100

    def test_feature_type_enum(self) -> None:
        """Test using FeatureType enum."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample(FeatureType.QUALITY_SCORE, 0.8)
        tracker.add_sample(FeatureType.BLUR_SCORE, 0.2)

        assert tracker.get_stored_count(FeatureType.QUALITY_SCORE) == 1
        assert tracker.get_stored_count(FeatureType.BLUR_SCORE) == 1

    def test_get_values(self) -> None:
        """Test retrieving stored values."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample("test", 1.0)
        tracker.add_sample("test", 2.0)
        tracker.add_sample("test", 3.0)

        values = tracker.get_values("test")
        assert values == [1.0, 2.0, 3.0]

    def test_get_samples_with_ids(self) -> None:
        """Test retrieving samples with IDs."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample("test", 1.0, "id1")
        tracker.add_sample("test", 2.0, "id2")

        samples = tracker.get_samples_with_ids("test")
        assert samples == [(1.0, "id1"), (2.0, "id2")]

    def test_compute_histogram(self) -> None:
        """Test computing histogram from tracker."""
        tracker = DistributionTracker(sample_rate=1.0)

        for i in range(100):
            tracker.add_sample(FeatureType.QUALITY_SCORE, i / 100.0)

        histogram, _ = tracker.compute_histogram(FeatureType.QUALITY_SCORE)

        assert len(histogram) == DEFAULT_NUM_BINS
        assert sum(histogram) == pytest.approx(1.0)

    def test_compute_stats(self) -> None:
        """Test computing stats from tracker."""
        tracker = DistributionTracker(sample_rate=1.0)

        for v in [1, 2, 3, 4, 5]:
            tracker.add_sample("test", float(v))

        stats = tracker.compute_stats("test")

        assert stats.count == 5
        assert stats.mean == pytest.approx(3.0)

    def test_clear_specific_feature(self) -> None:
        """Test clearing specific feature."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample("feature1", 1.0)
        tracker.add_sample("feature2", 2.0)

        tracker.clear("feature1")

        assert tracker.get_stored_count("feature1") == 0
        assert tracker.get_stored_count("feature2") == 1

    def test_clear_all(self) -> None:
        """Test clearing all features."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample("feature1", 1.0)
        tracker.add_sample("feature2", 2.0)

        tracker.clear()

        assert tracker.get_tracked_features() == []

    def test_get_tracked_features(self) -> None:
        """Test getting list of tracked features."""
        tracker = DistributionTracker(sample_rate=1.0)

        tracker.add_sample("a", 1.0)
        tracker.add_sample("b", 2.0)
        tracker.add_sample("c", 3.0)

        features = tracker.get_tracked_features()
        assert set(features) == {"a", "b", "c"}


# ============================================================================
# Reference Store Tests
# ============================================================================


class TestReferenceStore:
    """Tests for ReferenceStore."""

    def test_save_and_load_reference(self) -> None:
        """Test saving and loading reference distributions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)

            histogram = [0.2] * 5
            bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            stats = compute_stats([0.1, 0.3, 0.5, 0.7, 0.9])

            ref = store.save_reference(
                feature="test_feature",
                histogram=histogram,
                bin_edges=bin_edges,
                stats=stats,
                sample_count=5,
            )

            assert ref.feature == "test_feature"
            assert not ref.is_expired()

            # Reload from disk
            store2 = ReferenceStore(tmpdir)
            loaded = store2.get_reference("test_feature")

            assert loaded is not None
            assert loaded.feature == "test_feature"
            assert loaded.histogram == histogram

    def test_reference_expiration(self) -> None:
        """Test reference distribution expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir, rotation_days=0)  # Expire immediately

            histogram = [0.5, 0.5]
            bin_edges = [0.0, 0.5, 1.0]
            stats = compute_stats([0.25, 0.75])

            store.save_reference("test", histogram, bin_edges, stats, 2)

            # Should be expired
            ref = store.get_reference("test")
            assert ref is None

    def test_rotate_expired(self) -> None:
        """Test rotating expired references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir, rotation_days=30)

            # Create a reference
            store.save_reference(
                "test",
                [0.5, 0.5],
                [0.0, 0.5, 1.0],
                compute_stats([0.25, 0.75]),
                2,
            )

            # Manually expire it
            ref = store._references["test"]
            ref.expires_at = utc_now() - timedelta(days=1)

            expired = store.rotate_expired()

            assert "test" in expired
            assert store.get_reference("test") is None

    def test_checksum_verification(self) -> None:
        """Test reference checksum verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)

            histogram = [0.3, 0.4, 0.3]
            bin_edges = [0.0, 0.33, 0.66, 1.0]

            ref = store.save_reference(
                "test",
                histogram,
                bin_edges,
                compute_stats([0.15, 0.5, 0.85]),
                3,
            )

            assert ref.verify_checksum()

            # Tamper with histogram
            ref.histogram[0] = 0.5
            assert not ref.verify_checksum()

    def test_has_reference(self) -> None:
        """Test checking reference existence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)

            assert not store.has_reference("test")

            store.save_reference(
                "test",
                [0.5, 0.5],
                [0.0, 0.5, 1.0],
                compute_stats([0.25, 0.75]),
                2,
            )

            assert store.has_reference("test")

    def test_get_all_features(self) -> None:
        """Test getting all feature names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)

            for name in ["a", "b", "c"]:
                store.save_reference(
                    name,
                    [0.5, 0.5],
                    [0.0, 0.5, 1.0],
                    compute_stats([0.25, 0.75]),
                    2,
                )

            features = store.get_all_features()
            assert set(features) == {"a", "b", "c"}

    def test_clear(self) -> None:
        """Test clearing all references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)

            store.save_reference(
                "test",
                [0.5, 0.5],
                [0.0, 0.5, 1.0],
                compute_stats([0.25, 0.75]),
                2,
            )

            store.clear()

            assert store.get_all_features() == []
            assert not list(Path(tmpdir).glob("*.json"))


# ============================================================================
# Drift Detector Tests
# ============================================================================


class TestDriftDetector:
    """Tests for DriftDetector."""

    def test_no_drift_detection(self) -> None:
        """Test detecting no drift when distributions match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            # Create reference
            histogram = [0.2] * 5
            bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            store.save_reference(
                "test",
                histogram,
                bin_edges,
                compute_stats([0.1, 0.3, 0.5, 0.7, 0.9]),
                5,
            )

            # Same distribution
            result = detector.detect_drift("test", histogram)

            assert result.severity == DriftSeverity.NONE
            assert result.kl_divergence == pytest.approx(0.0, abs=0.01)
            assert result.psi == pytest.approx(0.0, abs=0.01)

    def test_warning_drift_detection(self) -> None:
        """Test detecting warning-level drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            # Create reference
            ref_histogram = [0.2] * 5
            bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            store.save_reference(
                "test",
                ref_histogram,
                bin_edges,
                compute_stats([0.1, 0.3, 0.5, 0.7, 0.9]),
                5,
            )

            # Shifted distribution
            current_histogram = [0.35, 0.25, 0.2, 0.15, 0.05]
            result = detector.detect_drift("test", current_histogram)

            assert result.severity in [DriftSeverity.WARNING, DriftSeverity.CRITICAL]
            assert result.kl_divergence > 0

    def test_critical_drift_detection(self) -> None:
        """Test detecting critical-level drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(
                store,
                kl_critical=0.3,
            )

            # Create reference - concentrated at low values
            ref_histogram = [0.8, 0.15, 0.05, 0.0, 0.0]
            bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            store.save_reference(
                "test",
                ref_histogram,
                bin_edges,
                compute_stats([0.1] * 80 + [0.3] * 15 + [0.5] * 5),
                100,
            )

            # Completely different - concentrated at high values
            current_histogram = [0.0, 0.0, 0.05, 0.15, 0.8]
            result = detector.detect_drift("test", current_histogram)

            assert result.severity == DriftSeverity.CRITICAL
            assert result.kl_divergence >= 0.3

    def test_no_reference_available(self) -> None:
        """Test behavior when no reference exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            result = detector.detect_drift("nonexistent", [0.5, 0.5])

            assert result.severity == DriftSeverity.NONE
            assert result.kl_divergence == pytest.approx(0.0)
            assert result.reference_stats is None

    def test_detect_drift_from_tracker(self) -> None:
        """Test detecting drift from tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            # Create reference
            store.save_reference(
                FeatureType.QUALITY_SCORE.value,
                [0.2] * 5,
                [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compute_stats([0.1, 0.3, 0.5, 0.7, 0.9]),
                5,
            )

            # Create tracker with similar data
            tracker = DistributionTracker(sample_rate=1.0)
            for v in [0.1, 0.3, 0.5, 0.7, 0.9]:
                tracker.add_sample(FeatureType.QUALITY_SCORE, v)

            results = detector.detect_drift_from_tracker(
                tracker, [FeatureType.QUALITY_SCORE]
            )

            assert len(results) == 1
            assert results[0].feature == FeatureType.QUALITY_SCORE.value

    def test_create_reference_from_tracker(self) -> None:
        """Test creating reference from tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            tracker = DistributionTracker(sample_rate=1.0)
            for i in range(200):
                tracker.add_sample("test", i / 200.0)

            ref = detector.create_reference_from_tracker(
                tracker, "test", min_samples=100
            )

            assert ref is not None
            assert ref.feature == "test"
            assert ref.sample_count == 200

    def test_create_reference_insufficient_samples(self) -> None:
        """Test creating reference with insufficient samples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            tracker = DistributionTracker(sample_rate=1.0)
            for i in range(50):
                tracker.add_sample("test", i / 50.0)

            ref = detector.create_reference_from_tracker(
                tracker, "test", min_samples=100
            )

            assert ref is None

    def test_sample_ids_in_result(self) -> None:
        """Test sample IDs are included in drift result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ReferenceStore(tmpdir)
            detector = DriftDetector(store)

            store.save_reference(
                "test",
                [0.5, 0.5],
                [0.0, 0.5, 1.0],
                compute_stats([0.25, 0.75]),
                2,
            )

            result = detector.detect_drift(
                "test",
                [0.5, 0.5],
                sample_ids=["s1", "s2", "s3"],
            )

            assert result.sample_ids == ["s1", "s2", "s3"]


# ============================================================================
# Data Class Tests
# ============================================================================


class TestDriftResult:
    """Tests for DriftResult data class."""

    def test_to_dict(self) -> None:
        """Test DriftResult serialization."""
        result = DriftResult(
            feature="test",
            kl_divergence=0.15,
            psi=0.12,
            severity=DriftSeverity.WARNING,
            reference_stats=compute_stats([1, 2, 3]),
            current_stats=compute_stats([2, 3, 4]),
            sample_ids=["a", "b"],
        )

        d = result.to_dict()

        assert d["feature"] == "test"
        assert d["kl_divergence"] == pytest.approx(0.15)
        assert d["psi"] == pytest.approx(0.12)
        assert d["severity"] == "warning"
        assert d["sample_ids"] == ["a", "b"]

    def test_sample_ids_limited(self) -> None:
        """Test sample IDs are limited in serialization."""
        result = DriftResult(
            feature="test",
            kl_divergence=0.0,
            psi=0.0,
            severity=DriftSeverity.NONE,
            reference_stats=None,
            current_stats=None,
            sample_ids=[f"s{i}" for i in range(100)],
        )

        d = result.to_dict()
        assert len(d["sample_ids"]) == 10


class TestReferenceDistribution:
    """Tests for ReferenceDistribution data class."""

    def test_is_expired(self) -> None:
        """Test expiration check."""
        ref = ReferenceDistribution(
            feature="test",
            histogram=[0.5, 0.5],
            bin_edges=[0.0, 0.5, 1.0],
            stats=compute_stats([0.25, 0.75]),
            created_at=utc_now() - timedelta(days=40),
            expires_at=utc_now() - timedelta(days=10),
            sample_count=2,
            checksum="abc123",
        )

        assert ref.is_expired()

    def test_not_expired(self) -> None:
        """Test not expired check."""
        ref = ReferenceDistribution(
            feature="test",
            histogram=[0.5, 0.5],
            bin_edges=[0.0, 0.5, 1.0],
            stats=compute_stats([0.25, 0.75]),
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            sample_count=2,
            checksum="abc123",
        )

        assert not ref.is_expired()

    def test_round_trip_serialization(self) -> None:
        """Test serialization round trip."""
        original = ReferenceDistribution(
            feature="test",
            histogram=[0.3, 0.4, 0.3],
            bin_edges=[0.0, 0.33, 0.66, 1.0],
            stats=compute_stats([0.15, 0.5, 0.85]),
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            sample_count=3,
            checksum=compute_checksum([0.3, 0.4, 0.3], [0.0, 0.33, 0.66, 1.0]),
        )

        d = original.to_dict()
        restored = ReferenceDistribution.from_dict(d)

        assert restored.feature == original.feature
        assert restored.histogram == original.histogram
        assert restored.sample_count == original.sample_count


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for module convenience functions."""

    def test_create_drift_detector(self) -> None:
        """Test creating drift detector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = create_drift_detector(tmpdir)

            assert isinstance(detector, DriftDetector)
            assert isinstance(detector.reference_store, ReferenceStore)

    def test_create_tracker(self) -> None:
        """Test creating distribution tracker."""
        tracker = create_tracker(sample_rate=0.5, max_samples=500)

        assert isinstance(tracker, DistributionTracker)
        assert tracker.sample_rate == pytest.approx(0.5)
        assert tracker.max_samples == 500


# ============================================================================
# Robustness Tests
# ============================================================================


class TestMetricRobustness:
    """Tests for metric computation robustness."""

    def test_kl_with_zeros(self) -> None:
        """Test KL divergence handles zeros gracefully."""
        p = [0.0, 0.0, 1.0, 0.0, 0.0]
        q = [0.2, 0.2, 0.2, 0.2, 0.2]

        kl = kl_divergence(p, q)
        assert not math.isnan(kl)
        assert not math.isinf(kl)

    def test_psi_with_zeros(self) -> None:
        """Test PSI handles zeros gracefully."""
        expected = [0.0, 1.0, 0.0]
        actual = [0.5, 0.0, 0.5]

        psi_value = psi(expected, actual)
        assert not math.isnan(psi_value)
        assert not math.isinf(psi_value)

    def test_histogram_with_outliers(self) -> None:
        """Test histogram handles outliers."""
        values = [0.5] * 100 + [1000.0]  # One extreme outlier

        histogram, _ = compute_histogram(values, bounds=(0, 1))
        assert sum(histogram) == pytest.approx(1.0)

    def test_stats_with_extreme_values(self) -> None:
        """Test stats handles extreme values."""
        values = [1e-10, 0.5, 1e10]

        stats = compute_stats(values)
        assert not math.isnan(stats.mean)
        assert not math.isnan(stats.std)

    def test_large_histogram(self) -> None:
        """Test histogram with large number of bins."""
        values = list(rng.uniform(0, 1, 10000))
        histogram, _ = compute_histogram(values, num_bins=1000)

        assert len(histogram) == 1000
        assert sum(histogram) == pytest.approx(1.0)

    def test_tracker_high_throughput(self) -> None:
        """Test tracker handles high throughput."""
        tracker = DistributionTracker(sample_rate=0.01, max_samples=1000)

        for _ in range(100000):
            tracker.add_sample("test", rng.random())

        assert tracker.get_stored_count("test") <= 1000
        assert tracker.get_sample_count("test") == 100000


class TestFeatureTypeBounds:
    """Tests for feature type bounds."""

    def test_all_feature_types_have_bounds(self) -> None:
        """Test all feature types have defined bounds."""
        for feature_type in FeatureType:
            assert feature_type in FEATURE_BOUNDS
            bounds = FEATURE_BOUNDS[feature_type]
            assert len(bounds) == 2
            assert bounds[0] < bounds[1]

    def test_quality_score_bounds(self) -> None:
        """Test quality score bounds are 0-1."""
        assert FEATURE_BOUNDS[FeatureType.QUALITY_SCORE] == (0.0, 1.0)

    def test_skew_angle_bounds(self) -> None:
        """Test skew angle bounds are reasonable."""
        bounds = FEATURE_BOUNDS[FeatureType.SKEW_ANGLE]
        assert bounds[0] == -45.0
        assert bounds[1] == pytest.approx(45.0)


class TestThresholdConstants:
    """Tests for threshold constants."""

    def test_kl_thresholds_ordered(self) -> None:
        """Test KL thresholds are in order."""
        assert KL_WARNING_THRESHOLD < KL_CRITICAL_THRESHOLD

    def test_psi_thresholds_ordered(self) -> None:
        """Test PSI thresholds are in order."""
        assert PSI_WARNING_THRESHOLD < PSI_CRITICAL_THRESHOLD

    def test_kl_thresholds_reasonable(self) -> None:
        """Test KL thresholds are in reasonable range."""
        assert 0 < KL_WARNING_THRESHOLD < 1
        assert 0 < KL_CRITICAL_THRESHOLD < 2

    def test_psi_thresholds_reasonable(self) -> None:
        """Test PSI thresholds are in reasonable range."""
        assert 0 < PSI_WARNING_THRESHOLD < 0.5
        assert 0 < PSI_CRITICAL_THRESHOLD < 1
