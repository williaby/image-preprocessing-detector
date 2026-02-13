"""Unit tests for the SkewNet model architecture and bin configuration.

Tests cover:
- Non-uniform bin configuration (BinConfig)
- Bin center computation
- Angle-to-bin and bin-to-angle mapping
- SkewEstimation dataclass
- Softmax utility
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

# Use modern numpy Generator API instead of legacy np.random functions (S6711)
_rng = np.random.default_rng(42)


class TestBinConfig:
    """Tests for BinConfig non-uniform bin layout."""

    def test_from_yaml_loads_default_config(self) -> None:
        """BinConfig loads 42 bins from default skew_estimation.yaml."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        assert config.total_bins == 42
        assert len(config.centers) == 42
        assert config.max_residual == pytest.approx(0.25)

    def test_from_yaml_with_explicit_path(self) -> None:
        """BinConfig loads from explicitly provided config path."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config_path = (
            Path(__file__).resolve().parents[2] / "config" / "skew_estimation.yaml"
        )
        config = BinConfig.from_yaml(config_path)
        assert config.total_bins == 42

    def test_zones_ordered_negative_to_positive(self) -> None:
        """Bin zones are ordered from most negative to most positive."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        zone_starts = [z.start for z in config.zones]
        assert zone_starts == sorted(zone_starts), "Zones must be sorted by start angle"

    def test_centers_are_monotonically_increasing(self) -> None:
        """Bin centers increase from negative to positive angles."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        for i in range(1, len(config.centers)):
            assert config.centers[i] > config.centers[i - 1], (
                f"Center {i} ({config.centers[i]}) not greater than "
                f"center {i - 1} ({config.centers[i - 1]})"
            )

    def test_centers_cover_full_range(self) -> None:
        """Bin centers span from approximately -45 to +45 degrees."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        assert config.centers[0] < -40, "First center should be near -45"
        assert config.centers[-1] > 40, "Last center should be near +45"

    def test_critical_zone_has_fine_bins(self) -> None:
        """Critical zone (-5 to +5) should have 0.5 deg bins."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        critical_zone = next(z for z in config.zones if z.name == "critical")
        assert critical_zone.width == pytest.approx(0.5)
        assert critical_zone.count == 20
        assert critical_zone.start == pytest.approx(-5.0)
        assert critical_zone.end == pytest.approx(5.0)

    def test_zone_bin_counts_sum_to_total(self) -> None:
        """Sum of all zone bin counts equals total_bins."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        total = sum(z.count for z in config.zones)
        assert total == config.total_bins

    def test_angle_to_bin_zero_angle(self) -> None:
        """Zero angle maps to a bin near center of critical zone."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        bin_idx = config.angle_to_bin(0.0)
        center = config.centers[bin_idx]
        assert abs(center) < 0.5, f"Zero angle mapped to bin with center {center}"

    def test_angle_to_bin_extreme_positive(self) -> None:
        """Large positive angle maps to a bin near +45."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        bin_idx = config.angle_to_bin(40.0)
        center = config.centers[bin_idx]
        assert center > 35, f"40 deg mapped to bin with center {center}"

    def test_angle_to_bin_extreme_negative(self) -> None:
        """Large negative angle maps to a bin near -45."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        bin_idx = config.angle_to_bin(-40.0)
        center = config.centers[bin_idx]
        assert center < -35, f"-40 deg mapped to bin with center {center}"

    def test_bin_to_angle_without_residual(self) -> None:
        """bin_to_angle returns bin center when residual is 0."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        for i in range(config.total_bins):
            angle = config.bin_to_angle(i, 0.0)
            assert angle == config.centers[i]

    def test_bin_to_angle_with_residual(self) -> None:
        """bin_to_angle adds residual to bin center."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        center = config.centers[20]  # Middle bin
        angle = config.bin_to_angle(20, 0.1)
        assert abs(angle - (center + 0.1)) < 1e-6

    def test_bin_to_angle_clamps_residual(self) -> None:
        """Residual is clamped to ±max_residual."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()
        center = config.centers[20]

        # Excessive positive residual
        angle_pos = config.bin_to_angle(20, 10.0)
        assert abs(angle_pos - (center + config.max_residual)) < 1e-6

        # Excessive negative residual
        angle_neg = config.bin_to_angle(20, -10.0)
        assert abs(angle_neg - (center - config.max_residual)) < 1e-6

    def test_roundtrip_angle_to_bin_to_angle(self) -> None:
        """Angle -> bin -> angle roundtrip stays within one bin width."""
        from image_preprocessing_detector.models.skew_estimator import BinConfig

        config = BinConfig.from_yaml()

        test_angles = [0.0, 1.0, -1.0, 5.5, -5.5, 20.0, -30.0]
        for angle in test_angles:
            bin_idx = config.angle_to_bin(angle)
            recovered = config.bin_to_angle(bin_idx, 0.0)
            # Error should be at most half a bin width
            error = abs(recovered - angle)
            # Find which zone this bin is in
            bin_center = config.centers[bin_idx]
            for zone in config.zones:
                if zone.start <= bin_center < zone.end:
                    max_error = zone.width / 2 + 0.01  # Small epsilon
                    assert error <= max_error, (
                        f"Angle {angle}: error {error:.3f} exceeds "
                        f"half bin width {max_error:.3f}"
                    )
                    break


class TestBinZone:
    """Tests for BinZone dataclass."""

    def test_frozen(self) -> None:
        """BinZone is immutable."""
        from image_preprocessing_detector.models.skew_estimator import BinZone

        zone = BinZone(name="test", start=0.0, end=5.0, width=1.0, count=5)
        with pytest.raises(AttributeError):
            zone.name = "changed"  # type: ignore[misc]


class TestSkewEstimation:
    """Tests for SkewEstimation output dataclass."""

    def test_frozen(self) -> None:
        """SkewEstimation is immutable."""
        from image_preprocessing_detector.models.skew_estimator import SkewEstimation

        est = SkewEstimation(
            orientation_class=0,
            orientation_confidence=0.95,
            skew_bin=20,
            skew_bin_confidence=0.8,
            skew_residual=0.1,
            skew_uncertainty=0.05,
            final_angle=0.35,
        )
        with pytest.raises(AttributeError):
            est.final_angle = 1.0  # type: ignore[misc]

    def test_attributes(self) -> None:
        """SkewEstimation stores all fields correctly."""
        from image_preprocessing_detector.models.skew_estimator import SkewEstimation

        est = SkewEstimation(
            orientation_class=90,
            orientation_confidence=0.99,
            skew_bin=5,
            skew_bin_confidence=0.75,
            skew_residual=-0.1,
            skew_uncertainty=0.02,
            final_angle=-12.6,
        )
        assert est.orientation_class == 90
        assert est.orientation_confidence == pytest.approx(0.99)
        assert est.skew_bin == 5
        assert est.final_angle == pytest.approx(-12.6)


class TestSoftmax:
    """Tests for the _softmax utility function."""

    def test_output_sums_to_one(self) -> None:
        """Softmax output sums to 1.0."""
        from image_preprocessing_detector.models.skew_estimator import _softmax

        logits = np.array([1.0, 2.0, 3.0, 4.0])
        probs = _softmax(logits)
        assert abs(np.sum(probs) - 1.0) < 1e-6

    def test_preserves_ordering(self) -> None:
        """Largest logit gets highest probability."""
        from image_preprocessing_detector.models.skew_estimator import _softmax

        logits = np.array([1.0, 5.0, 2.0])
        probs = _softmax(logits)
        assert np.argmax(probs) == 1

    def test_handles_large_values(self) -> None:
        """Numerically stable for large logits."""
        from image_preprocessing_detector.models.skew_estimator import _softmax

        logits = np.array([1000.0, 1001.0, 1002.0])
        probs = _softmax(logits)
        assert abs(np.sum(probs) - 1.0) < 1e-6
        assert np.argmax(probs) == 2

    def test_uniform_input(self) -> None:
        """Equal logits produce uniform distribution."""
        from image_preprocessing_detector.models.skew_estimator import _softmax

        logits = np.array([1.0, 1.0, 1.0, 1.0])
        probs = _softmax(logits)
        expected = 0.25
        for p in probs:
            assert abs(p - expected) < 1e-6


class TestSkewEstimatorInference:
    """Tests for the ONNX inference wrapper (mocked ONNX session)."""

    def test_preprocess_output_shape(self) -> None:
        """Preprocessing produces [1, 3, 384, 384] float32 tensor."""
        from image_preprocessing_detector.models.skew_estimator import (
            SkewEstimatorInference,
        )

        estimator = SkewEstimatorInference(
            model_path=Path("/fake/model.onnx"),
        )
        # Create a dummy BGR image
        image = _rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
        tensor = estimator._preprocess(image)

        assert tensor.shape == (1, 3, 384, 384)
        assert tensor.dtype == np.float32

    def test_preprocess_normalizes_values(self) -> None:
        """Preprocessing normalizes with ImageNet mean/std."""
        from image_preprocessing_detector.models.skew_estimator import (
            SkewEstimatorInference,
        )

        estimator = SkewEstimatorInference(
            model_path=Path("/fake/model.onnx"),
        )
        # All-black image should produce values near -mean/std
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        tensor = estimator._preprocess(image)

        # After normalization of 0.0: (0 - mean) / std
        # For channel 0 (R): (0 - 0.485) / 0.229 ≈ -2.117
        assert tensor[0, 0, 0, 0] < 0, "Normalized black should be negative"
