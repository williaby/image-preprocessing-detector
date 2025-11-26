"""Drift detection module for monitoring feature distributions.

Sprint 6.3.1: Feature distribution monitoring with KL divergence and PSI.

This module provides:
- DistributionTracker: Tracks feature distributions over time
- DriftDetector: Computes KL divergence and PSI metrics
- ReferenceStore: Stores and rotates reference distributions

Key IQA features monitored:
- Quality scores (0-1 continuous)
- Blur scores
- Skew angles
- Contrast scores
- Noise levels
- Teacher escalation rates
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.utils.datetime_compat import ensure_aware, utc_now

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_NUM_BINS = 50
DEFAULT_EPSILON = 1e-10  # Smoothing for KL divergence
DEFAULT_SAMPLE_RATE = 0.1  # 10% sampling
DEFAULT_REFERENCE_ROTATION_DAYS = 30
MAX_SAMPLES_PER_FEATURE = 10000

# Drift thresholds
KL_WARNING_THRESHOLD = 0.15
KL_CRITICAL_THRESHOLD = 0.30
PSI_WARNING_THRESHOLD = 0.10
PSI_CRITICAL_THRESHOLD = 0.25


class DriftSeverity(Enum):
    """Severity levels for drift detection."""

    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


class FeatureType(Enum):
    """Types of features being monitored."""

    QUALITY_SCORE = "quality_score"
    BLUR_SCORE = "blur_score"
    SKEW_ANGLE = "skew_angle"
    CONTRAST_SCORE = "contrast_score"
    NOISE_LEVEL = "noise_level"
    BRIGHTNESS = "brightness"
    SHARPNESS = "sharpness"
    ESCALATION_RATE = "escalation_rate"
    PROCESSING_TIME = "processing_time"
    GATE_CONFIDENCE = "gate_confidence"


# Feature bounds for histogram binning
FEATURE_BOUNDS: dict[FeatureType, tuple[float, float]] = {
    FeatureType.QUALITY_SCORE: (0.0, 1.0),
    FeatureType.BLUR_SCORE: (0.0, 1.0),
    FeatureType.SKEW_ANGLE: (-45.0, 45.0),
    FeatureType.CONTRAST_SCORE: (0.0, 1.0),
    FeatureType.NOISE_LEVEL: (0.0, 1.0),
    FeatureType.BRIGHTNESS: (0.0, 255.0),
    FeatureType.SHARPNESS: (0.0, 1.0),
    FeatureType.ESCALATION_RATE: (0.0, 1.0),
    FeatureType.PROCESSING_TIME: (0.0, 10.0),  # seconds
    FeatureType.GATE_CONFIDENCE: (0.0, 1.0),
}


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class HistogramStats:
    """Statistics computed from a histogram."""

    mean: float
    std: float
    median: float
    min_val: float
    max_val: float
    p5: float
    p25: float
    p75: float
    p95: float
    count: int
    bins: list[float] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mean": self.mean,
            "std": self.std,
            "median": self.median,
            "min": self.min_val,
            "max": self.max_val,
            "p5": self.p5,
            "p25": self.p25,
            "p75": self.p75,
            "p95": self.p95,
            "count": self.count,
            "bins": self.bins,
            "counts": self.counts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistogramStats:
        """Create from dictionary."""
        return cls(
            mean=data["mean"],
            std=data["std"],
            median=data["median"],
            min_val=data["min"],
            max_val=data["max"],
            p5=data["p5"],
            p25=data["p25"],
            p75=data["p75"],
            p95=data["p95"],
            count=data["count"],
            bins=data.get("bins", []),
            counts=data.get("counts", []),
        )


@dataclass
class DriftResult:
    """Result of drift detection analysis."""

    feature: str
    kl_divergence: float
    psi: float
    severity: DriftSeverity
    reference_stats: HistogramStats | None
    current_stats: HistogramStats | None
    timestamp: datetime = field(default_factory=utc_now)
    sample_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature": self.feature,
            "kl_divergence": self.kl_divergence,
            "psi": self.psi,
            "severity": self.severity.value,
            "reference_stats": (
                self.reference_stats.to_dict() if self.reference_stats else None
            ),
            "current_stats": (
                self.current_stats.to_dict() if self.current_stats else None
            ),
            "timestamp": self.timestamp.isoformat(),
            "sample_ids": self.sample_ids[:10],  # Limit for payload size
        }


@dataclass
class ReferenceDistribution:
    """Reference distribution for a feature."""

    feature: str
    histogram: list[float]  # Normalized bin counts
    bin_edges: list[float]
    stats: HistogramStats
    created_at: datetime
    expires_at: datetime
    sample_count: int
    checksum: str  # For integrity verification

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature": self.feature,
            "histogram": self.histogram,
            "bin_edges": self.bin_edges,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "sample_count": self.sample_count,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReferenceDistribution:
        """Create from dictionary."""
        return cls(
            feature=data["feature"],
            histogram=data["histogram"],
            bin_edges=data["bin_edges"],
            stats=HistogramStats.from_dict(data["stats"]),
            created_at=ensure_aware(datetime.fromisoformat(data["created_at"])),
            expires_at=ensure_aware(datetime.fromisoformat(data["expires_at"])),
            sample_count=data["sample_count"],
            checksum=data["checksum"],
        )

    def is_expired(self) -> bool:
        """Check if reference distribution has expired."""
        return utc_now() > self.expires_at

    def verify_checksum(self) -> bool:
        """Verify the checksum of the distribution."""
        computed = compute_checksum(self.histogram, self.bin_edges)
        return computed == self.checksum


# ============================================================================
# Utility Functions
# ============================================================================


def compute_checksum(histogram: list[float], bin_edges: list[float]) -> str:
    """Compute checksum for distribution integrity verification."""
    data = json.dumps({"histogram": histogram, "bin_edges": bin_edges}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def compute_histogram(
    values: list[float],
    num_bins: int = DEFAULT_NUM_BINS,
    bounds: tuple[float, float] | None = None,
) -> tuple[list[float], list[float]]:
    """Compute normalized histogram from values.

    Args:
        values: List of feature values
        num_bins: Number of histogram bins
        bounds: Optional (min, max) bounds for binning

    Returns:
        Tuple of (normalized_counts, bin_edges)
    """
    if not values:
        return [], []

    arr = np.array(values, dtype=np.float64)

    # Handle bounds
    if bounds:
        min_val, max_val = bounds
        # Clip values to bounds
        arr = np.clip(arr, min_val, max_val)
    else:
        min_val, max_val = float(arr.min()), float(arr.max())

    # Add small buffer to max to include edge values
    if min_val == max_val:
        max_val = min_val + 1.0

    # Compute histogram
    counts, bin_edges = np.histogram(arr, bins=num_bins, range=(min_val, max_val))

    # Normalize to probability distribution
    total = counts.sum()
    normalized = (counts / total).tolist() if total > 0 else [0.0] * num_bins

    return normalized, bin_edges.tolist()


def compute_stats(values: list[float]) -> HistogramStats:
    """Compute statistical summary of values.

    Args:
        values: List of feature values

    Returns:
        HistogramStats with computed statistics
    """
    if not values:
        return HistogramStats(
            mean=0.0,
            std=0.0,
            median=0.0,
            min_val=0.0,
            max_val=0.0,
            p5=0.0,
            p25=0.0,
            p75=0.0,
            p95=0.0,
            count=0,
        )

    arr = np.array(values, dtype=np.float64)

    return HistogramStats(
        mean=float(np.mean(arr)),
        std=float(np.std(arr)),
        median=float(np.median(arr)),
        min_val=float(np.min(arr)),
        max_val=float(np.max(arr)),
        p5=float(np.percentile(arr, 5)),
        p25=float(np.percentile(arr, 25)),
        p75=float(np.percentile(arr, 75)),
        p95=float(np.percentile(arr, 95)),
        count=len(values),
    )


def kl_divergence(
    p: list[float], q: list[float], epsilon: float = DEFAULT_EPSILON
) -> float:
    """Compute KL divergence D_KL(P || Q).

    KL divergence measures how distribution P diverges from reference Q.
    - KL = 0 means distributions are identical
    - Higher values indicate greater divergence

    Args:
        p: Current distribution (normalized histogram)
        q: Reference distribution (normalized histogram)
        epsilon: Smoothing factor to avoid log(0)

    Returns:
        KL divergence value (non-negative float)
    """
    if len(p) != len(q):
        raise ValueError(f"Distribution lengths must match: {len(p)} != {len(q)}")

    if not p or not q:
        return 0.0

    kl = 0.0
    for pi, qi in zip(p, q, strict=True):
        # Add epsilon for numerical stability
        pi_safe = max(pi, epsilon)
        qi_safe = max(qi, epsilon)

        if pi_safe > epsilon:
            kl += pi_safe * math.log(pi_safe / qi_safe)

    return max(0.0, kl)  # Ensure non-negative


def psi(
    expected: list[float], actual: list[float], epsilon: float = DEFAULT_EPSILON
) -> float:
    """Compute Population Stability Index (PSI).

    PSI measures the shift between two distributions:
    - PSI < 0.1: No significant shift
    - PSI 0.1-0.25: Moderate shift
    - PSI > 0.25: Significant shift

    Args:
        expected: Reference distribution (normalized histogram)
        actual: Current distribution (normalized histogram)
        epsilon: Smoothing factor

    Returns:
        PSI value (non-negative float)
    """
    if len(expected) != len(actual):
        raise ValueError(
            f"Distribution lengths must match: {len(expected)} != {len(actual)}"
        )

    if not expected or not actual:
        return 0.0

    psi_value = 0.0
    for e, a in zip(expected, actual, strict=True):
        # Add epsilon for numerical stability
        e_safe = max(e, epsilon)
        a_safe = max(a, epsilon)

        psi_value += (a_safe - e_safe) * math.log(a_safe / e_safe)

    return max(0.0, psi_value)  # Ensure non-negative


def symmetric_kl(
    p: list[float], q: list[float], epsilon: float = DEFAULT_EPSILON
) -> float:
    """Compute symmetric KL divergence (Jensen-Shannon divergence approximation).

    Args:
        p: First distribution
        q: Second distribution
        epsilon: Smoothing factor

    Returns:
        Symmetric KL divergence value
    """
    return (kl_divergence(p, q, epsilon) + kl_divergence(q, p, epsilon)) / 2


# ============================================================================
# Distribution Tracker
# ============================================================================


class DistributionTracker:
    """Tracks feature distributions with reservoir sampling.

    Uses reservoir sampling to maintain a representative sample of
    feature values without storing all data points.
    """

    def __init__(
        self,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        max_samples: int = MAX_SAMPLES_PER_FEATURE,
    ):
        """Initialize distribution tracker.

        Args:
            sample_rate: Probability of including each sample (0-1)
            max_samples: Maximum samples to store per feature
        """
        self.sample_rate = sample_rate
        self.max_samples = max_samples
        self._samples: dict[str, list[tuple[float, str]]] = defaultdict(list)
        self._counts: dict[str, int] = defaultdict(int)
        self._rng = np.random.default_rng()

    def add_sample(
        self,
        feature: str | FeatureType,
        value: float,
        sample_id: str | None = None,
    ) -> bool:
        """Add a sample to the tracker.

        Uses reservoir sampling to maintain representative distribution.

        Args:
            feature: Feature name or type
            value: Feature value
            sample_id: Optional identifier for the sample

        Returns:
            True if sample was added, False if skipped
        """
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        sample_id = sample_id or f"sample_{self._counts[feature_name]}"

        self._counts[feature_name] += 1
        count = self._counts[feature_name]

        # Probabilistic sampling
        if self._rng.random() > self.sample_rate:
            return False

        samples = self._samples[feature_name]

        if len(samples) < self.max_samples:
            samples.append((value, sample_id))
            return True

        # Reservoir sampling: replace random element
        idx = self._rng.integers(0, count)
        if idx < self.max_samples:
            samples[idx] = (value, sample_id)
            return True

        return False

    def get_values(self, feature: str | FeatureType) -> list[float]:
        """Get all sampled values for a feature."""
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        return [v for v, _ in self._samples.get(feature_name, [])]

    def get_samples_with_ids(
        self, feature: str | FeatureType
    ) -> list[tuple[float, str]]:
        """Get all samples with their IDs."""
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        return list(self._samples.get(feature_name, []))

    def get_sample_count(self, feature: str | FeatureType) -> int:
        """Get total number of samples seen (not just stored)."""
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        return self._counts.get(feature_name, 0)

    def get_stored_count(self, feature: str | FeatureType) -> int:
        """Get number of samples currently stored."""
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        return len(self._samples.get(feature_name, []))

    def compute_histogram(
        self,
        feature: str | FeatureType,
        num_bins: int = DEFAULT_NUM_BINS,
    ) -> tuple[list[float], list[float]]:
        """Compute histogram for a feature."""
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        values = self.get_values(feature_name)

        # Get bounds if feature type is known
        bounds = None
        try:
            feature_type = FeatureType(feature_name)
            bounds = FEATURE_BOUNDS.get(feature_type)
        except ValueError:
            # Feature name is not a known FeatureType enum value; use unbounded histogram
            pass

        return compute_histogram(values, num_bins, bounds)

    def compute_stats(self, feature: str | FeatureType) -> HistogramStats:
        """Compute statistics for a feature."""
        values = self.get_values(feature)
        stats = compute_stats(values)

        # Add histogram data
        histogram, bin_edges = self.compute_histogram(feature)
        stats.bins = bin_edges
        stats.counts = [int(c * stats.count) for c in histogram]

        return stats

    def clear(self, feature: str | FeatureType | None = None) -> None:
        """Clear tracked samples.

        Args:
            feature: Specific feature to clear, or None to clear all
        """
        if feature is None:
            self._samples.clear()
            self._counts.clear()
        else:
            feature_name = (
                feature.value if isinstance(feature, FeatureType) else feature
            )
            self._samples.pop(feature_name, None)
            self._counts.pop(feature_name, None)

    def get_tracked_features(self) -> list[str]:
        """Get list of features being tracked."""
        return list(self._samples.keys())


# ============================================================================
# Reference Store
# ============================================================================


class ReferenceStore:
    """Stores and manages reference distributions.

    Reference distributions are used as baselines for drift detection.
    They are rotated monthly by default.
    """

    def __init__(
        self,
        storage_path: str | Path,
        rotation_days: int = DEFAULT_REFERENCE_ROTATION_DAYS,
    ):
        """Initialize reference store.

        Args:
            storage_path: Directory to store reference distributions
            rotation_days: Days before reference distributions expire
        """
        self.storage_path = Path(storage_path)
        self.rotation_days = rotation_days
        self._references: dict[str, ReferenceDistribution] = {}

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing references
        self._load_references()

    def _load_references(self) -> None:
        """Load reference distributions from storage."""
        for filepath in self.storage_path.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                ref = ReferenceDistribution.from_dict(data)

                # Skip expired references
                if ref.is_expired():
                    logger.info(f"Skipping expired reference: {ref.feature}")
                    continue

                # Verify integrity
                if not ref.verify_checksum():
                    logger.warning(f"Checksum mismatch for reference: {ref.feature}")
                    continue

                self._references[ref.feature] = ref
                logger.debug(f"Loaded reference distribution: {ref.feature}")

            except (json.JSONDecodeError, KeyError, ValueError):
                logger.exception(f"Error loading reference from {filepath}")

    def save_reference(
        self,
        feature: str | FeatureType,
        histogram: list[float],
        bin_edges: list[float],
        stats: HistogramStats,
        sample_count: int,
    ) -> ReferenceDistribution:
        """Save a new reference distribution.

        Args:
            feature: Feature name or type
            histogram: Normalized histogram counts
            bin_edges: Histogram bin edges
            stats: Statistical summary
            sample_count: Number of samples used

        Returns:
            Created ReferenceDistribution
        """
        feature_name = feature.value if isinstance(feature, FeatureType) else feature

        now = utc_now()
        ref = ReferenceDistribution(
            feature=feature_name,
            histogram=histogram,
            bin_edges=bin_edges,
            stats=stats,
            created_at=now,
            expires_at=now + timedelta(days=self.rotation_days),
            sample_count=sample_count,
            checksum=compute_checksum(histogram, bin_edges),
        )

        # Store in memory
        self._references[feature_name] = ref

        # Persist to disk
        filepath = self.storage_path / f"{feature_name}.json"
        with open(filepath, "w") as f:
            json.dump(ref.to_dict(), f, indent=2)

        logger.info(
            f"Saved reference distribution: {feature_name} "
            f"(expires: {ref.expires_at.isoformat()})"
        )

        return ref

    def get_reference(self, feature: str | FeatureType) -> ReferenceDistribution | None:
        """Get reference distribution for a feature.

        Args:
            feature: Feature name or type

        Returns:
            ReferenceDistribution or None if not found/expired
        """
        feature_name = feature.value if isinstance(feature, FeatureType) else feature
        ref = self._references.get(feature_name)

        if ref and ref.is_expired():
            logger.info(f"Reference expired for {feature_name}")
            return None

        return ref

    def has_reference(self, feature: str | FeatureType) -> bool:
        """Check if valid reference exists for feature."""
        return self.get_reference(feature) is not None

    def rotate_expired(self) -> list[str]:
        """Remove expired references.

        Returns:
            List of expired feature names that were removed
        """
        expired = []
        for feature_name, ref in list(self._references.items()):
            if ref.is_expired():
                expired.append(feature_name)
                del self._references[feature_name]

                # Remove file
                filepath = self.storage_path / f"{feature_name}.json"
                if filepath.exists():
                    filepath.unlink()

                logger.info(f"Rotated expired reference: {feature_name}")

        return expired

    def get_all_features(self) -> list[str]:
        """Get list of features with valid references."""
        return [f for f, r in self._references.items() if not r.is_expired()]

    def clear(self) -> None:
        """Clear all references."""
        self._references.clear()
        for filepath in self.storage_path.glob("*.json"):
            filepath.unlink()


# ============================================================================
# Drift Detector
# ============================================================================


class DriftDetector:
    """Detects distribution drift using KL divergence and PSI.

    Compares current feature distributions against stored references
    to detect drift that may indicate model degradation.
    """

    def __init__(
        self,
        reference_store: ReferenceStore,
        kl_warning: float = KL_WARNING_THRESHOLD,
        kl_critical: float = KL_CRITICAL_THRESHOLD,
        psi_warning: float = PSI_WARNING_THRESHOLD,
        psi_critical: float = PSI_CRITICAL_THRESHOLD,
    ):
        """Initialize drift detector.

        Args:
            reference_store: Store for reference distributions
            kl_warning: KL divergence threshold for warning
            kl_critical: KL divergence threshold for critical
            psi_warning: PSI threshold for warning
            psi_critical: PSI threshold for critical
        """
        self.reference_store = reference_store
        self.kl_warning = kl_warning
        self.kl_critical = kl_critical
        self.psi_warning = psi_warning
        self.psi_critical = psi_critical

    def detect_drift(
        self,
        feature: str | FeatureType,
        current_histogram: list[float],
        current_stats: HistogramStats | None = None,
        sample_ids: list[str] | None = None,
    ) -> DriftResult:
        """Detect drift for a single feature.

        Args:
            feature: Feature name or type
            current_histogram: Current normalized histogram
            current_stats: Optional current statistics
            sample_ids: Optional list of sample IDs for triage

        Returns:
            DriftResult with analysis
        """
        feature_name = feature.value if isinstance(feature, FeatureType) else feature

        # Get reference distribution
        ref = self.reference_store.get_reference(feature_name)

        if ref is None:
            logger.warning(f"No reference distribution for {feature_name}")
            return DriftResult(
                feature=feature_name,
                kl_divergence=0.0,
                psi=0.0,
                severity=DriftSeverity.NONE,
                reference_stats=None,
                current_stats=current_stats,
                sample_ids=sample_ids or [],
            )

        # Ensure histograms have same length
        if len(current_histogram) != len(ref.histogram):
            logger.warning(
                f"Histogram length mismatch for {feature_name}: "
                f"{len(current_histogram)} vs {len(ref.histogram)}"
            )
            # Resample to match reference bins
            current_histogram = self._resample_histogram(
                current_histogram, len(ref.histogram)
            )

        # Compute drift metrics
        kl = kl_divergence(current_histogram, ref.histogram)
        psi_value = psi(ref.histogram, current_histogram)

        # Determine severity
        severity = self._compute_severity(kl, psi_value)

        return DriftResult(
            feature=feature_name,
            kl_divergence=kl,
            psi=psi_value,
            severity=severity,
            reference_stats=ref.stats,
            current_stats=current_stats,
            sample_ids=sample_ids or [],
        )

    def detect_drift_from_tracker(
        self,
        tracker: DistributionTracker,
        features: list[str | FeatureType] | None = None,
    ) -> list[DriftResult]:
        """Detect drift for all tracked features.

        Args:
            tracker: Distribution tracker with current samples
            features: Optional list of specific features to check

        Returns:
            List of DriftResults for each feature
        """
        if features is None:
            features = [FeatureType(f) for f in tracker.get_tracked_features()]

        results = []
        for feature in features:
            feature_name = (
                feature.value if isinstance(feature, FeatureType) else feature
            )

            histogram, _ = tracker.compute_histogram(feature)
            stats = tracker.compute_stats(feature)
            samples = tracker.get_samples_with_ids(feature)
            sample_ids = [sid for _, sid in samples]

            result = self.detect_drift(
                feature_name,
                histogram,
                current_stats=stats,
                sample_ids=sample_ids,
            )
            results.append(result)

        return results

    def _compute_severity(self, kl: float, psi_value: float) -> DriftSeverity:
        """Compute drift severity from KL and PSI values."""
        # Critical if either metric exceeds critical threshold
        if kl >= self.kl_critical or psi_value >= self.psi_critical:
            return DriftSeverity.CRITICAL

        # Warning if either metric exceeds warning threshold
        if kl >= self.kl_warning or psi_value >= self.psi_warning:
            return DriftSeverity.WARNING

        return DriftSeverity.NONE

    def _resample_histogram(
        self, histogram: list[float], target_bins: int
    ) -> list[float]:
        """Resample histogram to target number of bins."""
        if not histogram:
            return [0.0] * target_bins

        # Simple linear interpolation
        arr = np.array(histogram)
        indices = np.linspace(0, len(arr) - 1, target_bins)
        resampled = np.interp(indices, np.arange(len(arr)), arr)

        # Renormalize
        total = resampled.sum()
        if total > 0:
            resampled = resampled / total

        return resampled.tolist()  # type: ignore[no-any-return]

    def create_reference_from_tracker(
        self,
        tracker: DistributionTracker,
        feature: str | FeatureType,
        min_samples: int = 100,
    ) -> ReferenceDistribution | None:
        """Create reference distribution from tracked samples.

        Args:
            tracker: Distribution tracker with samples
            feature: Feature to create reference for
            min_samples: Minimum samples required

        Returns:
            Created ReferenceDistribution or None if insufficient samples
        """
        stored_count = tracker.get_stored_count(feature)

        if stored_count < min_samples:
            logger.warning(
                f"Insufficient samples for {feature}: {stored_count} < {min_samples}"
            )
            return None

        histogram, bin_edges = tracker.compute_histogram(feature)
        stats = tracker.compute_stats(feature)

        return self.reference_store.save_reference(
            feature=feature,
            histogram=histogram,
            bin_edges=bin_edges,
            stats=stats,
            sample_count=stored_count,
        )


# ============================================================================
# Convenience Functions
# ============================================================================


def create_drift_detector(
    storage_path: str | Path = "data/drift_references",
    rotation_days: int = DEFAULT_REFERENCE_ROTATION_DAYS,
) -> DriftDetector:
    """Create a drift detector with default configuration.

    Args:
        storage_path: Path for reference distribution storage
        rotation_days: Days before references expire

    Returns:
        Configured DriftDetector instance
    """
    store = ReferenceStore(storage_path, rotation_days)
    return DriftDetector(store)


def create_tracker(
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    max_samples: int = MAX_SAMPLES_PER_FEATURE,
) -> DistributionTracker:
    """Create a distribution tracker with default configuration.

    Args:
        sample_rate: Sampling probability
        max_samples: Maximum samples per feature

    Returns:
        Configured DistributionTracker instance
    """
    return DistributionTracker(sample_rate, max_samples)


__all__ = [
    "DEFAULT_NUM_BINS",
    "DEFAULT_SAMPLE_RATE",
    "FEATURE_BOUNDS",
    "KL_CRITICAL_THRESHOLD",
    "KL_WARNING_THRESHOLD",
    "PSI_CRITICAL_THRESHOLD",
    "PSI_WARNING_THRESHOLD",
    "DistributionTracker",
    "DriftDetector",
    "DriftResult",
    "DriftSeverity",
    "FeatureType",
    "HistogramStats",
    "ReferenceDistribution",
    "ReferenceStore",
    "compute_histogram",
    "compute_stats",
    "create_drift_detector",
    "create_tracker",
    "kl_divergence",
    "psi",
    "symmetric_kl",
]
