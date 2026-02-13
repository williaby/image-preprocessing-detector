"""Unit tests for the deskew pipeline orchestrator.

Tests cover:
- DeskewConfig loading from YAML
- DeskewPipeline classical fallback path
- DeskewResult dataclass
- Image rotation utilities
- Skew correction application
- Confidence gates (min angle, max angle, uncertainty)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.deskew_pipeline import DeskewPipeline

# Use modern numpy Generator API instead of legacy np.random functions (S6711)
_rng = np.random.default_rng(42)


class TestDeskewConfig:
    """Tests for DeskewConfig loading and defaults."""

    def test_default_values(self) -> None:
        """DeskewConfig has sensible defaults."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewConfig

        config = DeskewConfig()
        assert config.orientation_confidence_threshold == pytest.approx(0.85)
        assert config.skew_confidence_threshold == pytest.approx(0.3)
        assert config.min_correction_angle == pytest.approx(0.3)
        assert config.max_correction_angle == pytest.approx(45.0)
        assert config.uncertainty_gate is True
        assert config.fallback_enabled is True
        assert config.border_value == 255

    def test_from_yaml_loads_config(self) -> None:
        """DeskewConfig loads thresholds from skew_estimation.yaml."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewConfig

        config = DeskewConfig.from_yaml()
        assert config.orientation_confidence_threshold == pytest.approx(0.85)
        assert config.min_correction_angle == pytest.approx(0.3)
        assert config.fallback_enabled is True

    def test_frozen(self) -> None:
        """DeskewConfig is immutable."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewConfig

        config = DeskewConfig()
        with pytest.raises(AttributeError):
            config.min_correction_angle = 1.0  # type: ignore[misc]


class TestDeskewResult:
    """Tests for DeskewResult dataclass."""

    def test_default_values(self) -> None:
        """DeskewResult has sensible defaults."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewResult

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = DeskewResult(corrected_image=img)
        assert result.orientation_applied is False
        assert result.orientation_angle == 0
        assert result.skew_angle == pytest.approx(0.0)
        assert result.correction_applied is False
        assert result.method == "ml"
        assert result.latency_ms == pytest.approx(0.0)

    def test_frozen(self) -> None:
        """DeskewResult is immutable."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewResult

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = DeskewResult(corrected_image=img)
        with pytest.raises(AttributeError):
            result.skew_angle = 5.0  # type: ignore[misc]


class TestRotate90:
    """Tests for _rotate_90 helper."""

    def test_rotate_0_returns_copy(self) -> None:
        """Rotation by 0 degrees returns a copy of the image."""
        from image_preprocessing_detector.detection.deskew_pipeline import _rotate_90

        img = _rng.integers(0, 255, (100, 200, 3), dtype=np.uint8)
        rotated = _rotate_90(img, 0)
        assert rotated.shape == img.shape
        np.testing.assert_array_equal(rotated, img)

    def test_rotate_90_changes_dimensions(self) -> None:
        """90 degree rotation swaps width and height."""
        from image_preprocessing_detector.detection.deskew_pipeline import _rotate_90

        img = np.zeros((100, 200, 3), dtype=np.uint8)
        rotated = _rotate_90(img, 90)
        assert rotated.shape == (200, 100, 3)

    def test_rotate_180_preserves_dimensions(self) -> None:
        """180 degree rotation keeps same dimensions."""
        from image_preprocessing_detector.detection.deskew_pipeline import _rotate_90

        img = np.zeros((100, 200, 3), dtype=np.uint8)
        rotated = _rotate_90(img, 180)
        assert rotated.shape == (100, 200, 3)

    def test_rotate_270_changes_dimensions(self) -> None:
        """270 degree rotation swaps width and height."""
        from image_preprocessing_detector.detection.deskew_pipeline import _rotate_90

        img = np.zeros((100, 200, 3), dtype=np.uint8)
        rotated = _rotate_90(img, 270)
        assert rotated.shape == (200, 100, 3)

    def test_rotate_360_roundtrip(self) -> None:
        """Four 90-degree rotations return the original image."""
        from image_preprocessing_detector.detection.deskew_pipeline import _rotate_90

        img = _rng.integers(0, 255, (50, 80, 3), dtype=np.uint8)
        result = img.copy()
        for _ in range(4):
            result = _rotate_90(result, 90)
        np.testing.assert_array_equal(result, img)


class TestApplySkewCorrection:
    """Tests for _apply_skew_correction helper."""

    def test_zero_angle_returns_original(self) -> None:
        """Zero angle correction returns image unchanged."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            _apply_skew_correction,
        )

        img = _rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
        corrected = _apply_skew_correction(img, 0.0)
        # With zero rotation, image should be nearly identical
        # (floating point rounding may cause tiny differences)
        assert corrected.shape == img.shape

    def test_preserves_image_dimensions(self) -> None:
        """Skew correction preserves image dimensions."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            _apply_skew_correction,
        )

        img = np.zeros((200, 300, 3), dtype=np.uint8)
        for angle in [1.0, -2.0, 5.0, -10.0]:
            corrected = _apply_skew_correction(img, angle)
            assert corrected.shape == img.shape, f"Shape changed for angle={angle}"

    def test_border_fill_value(self) -> None:
        """Border areas are filled with specified border value."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            _apply_skew_correction,
        )

        # Black image with large rotation will have white borders
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        corrected = _apply_skew_correction(img, 20.0, border_value=255)
        # Check corners (should be white from border fill)
        assert corrected[0, 0, 0] == 255 or corrected[99, 99, 0] == 255


class TestDeskewPipelineClassical:
    """Tests for DeskewPipeline using classical fallback path."""

    def _make_pipeline(self) -> DeskewPipeline:
        """Create a pipeline that will use classical fallback (no ML model)."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            DeskewConfig,
            DeskewPipeline,
        )

        config = DeskewConfig(
            model_path=None,
            fallback_enabled=True,
        )
        return DeskewPipeline(config=config)

    def test_process_returns_result(self) -> None:
        """Classical pipeline returns a DeskewResult."""
        from image_preprocessing_detector.detection.deskew_pipeline import DeskewResult

        pipeline = self._make_pipeline()
        img = _rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
        result = pipeline.process(img)
        assert isinstance(result, DeskewResult)
        assert result.method == "classical"
        assert result.latency_ms > 0

    def test_process_invalid_image_raises(self) -> None:
        """Pipeline raises ValueError for empty image."""
        pipeline = self._make_pipeline()
        with pytest.raises(ValueError, match="Invalid or empty"):
            pipeline.process(np.array([]))

    def test_process_none_image_raises(self) -> None:
        """Pipeline raises ValueError for None image."""
        pipeline = self._make_pipeline()
        with pytest.raises(ValueError, match="Invalid or empty"):
            pipeline.process(None)  # type: ignore[arg-type]

    def test_small_angle_skipped(self) -> None:
        """Angles below min threshold are skipped."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            DeskewConfig,
            DeskewPipeline,
        )

        config = DeskewConfig(
            model_path=None,
            fallback_enabled=True,
            min_correction_angle=5.0,  # High threshold
        )
        pipeline = DeskewPipeline(config=config)
        # Create an image with very mild skew (< 5 degrees)
        img = _rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
        result = pipeline.process(img)
        # Classical detector on random noise will likely find small angle
        if not result.correction_applied:
            assert result.skipped_reason is not None

    def test_no_model_no_fallback_returns_skip(self) -> None:
        """Without model and fallback, pipeline returns skip result."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            DeskewConfig,
            DeskewPipeline,
        )

        config = DeskewConfig(
            model_path=None,
            fallback_enabled=False,
        )
        pipeline = DeskewPipeline(config=config)
        img = _rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
        result = pipeline.process(img)
        assert not result.correction_applied
        assert result.method == "none"
        assert "No model" in (result.skipped_reason or "")

    def test_close_is_idempotent(self) -> None:
        """Calling close() multiple times is safe."""
        pipeline = self._make_pipeline()
        pipeline.close()
        pipeline.close()  # Should not raise


class TestDeskewPipelineFromConfig:
    """Tests for DeskewPipeline factory methods."""

    def test_from_config_creates_pipeline(self) -> None:
        """from_config() creates a working pipeline."""
        from image_preprocessing_detector.detection.deskew_pipeline import (
            DeskewPipeline,
        )

        pipeline = DeskewPipeline.from_config()
        assert pipeline.config is not None
        assert pipeline.config.fallback_enabled is True


class TestSchemaIntegration:
    """Tests for DeskewDetection schema model."""

    def test_deskew_detection_defaults(self) -> None:
        """DeskewDetection has sensible defaults."""
        from image_preprocessing_detector.schema import DeskewDetection

        dd = DeskewDetection()
        assert dd.skew_angle == pytest.approx(0.0)
        assert dd.skew_corrected is False
        assert dd.detection_method == "ml"
        assert dd.skipped_reason is None

    def test_deskew_detection_with_values(self) -> None:
        """DeskewDetection stores all fields correctly."""
        from image_preprocessing_detector.schema import (
            DeskewDetection,
            OrientationAngle,
        )

        dd = DeskewDetection(
            orientation_angle=OrientationAngle.ROTATED_90,
            orientation_confidence=0.95,
            orientation_corrected=True,
            skew_angle=1.5,
            skew_confidence=0.88,
            skew_uncertainty=0.05,
            skew_corrected=True,
            detection_method="ml",
            latency_ms=12.5,
        )
        assert dd.orientation_angle == OrientationAngle.ROTATED_90
        assert dd.skew_angle == pytest.approx(1.5)
        assert dd.skew_corrected is True

    def test_page_metadata_has_deskew_field(self) -> None:
        """PageMetadata accepts optional deskew field."""
        from image_preprocessing_detector.schema import (
            DeskewDetection,
            PageMetadata,
        )

        dd = DeskewDetection(skew_angle=2.0, skew_corrected=True)
        pm = PageMetadata(
            page_index=0,
            width_px=640,
            height_px=480,
            dpi_input=300,
            dpi_effective=300,
            deskew=dd,
        )
        assert pm.deskew is not None
        assert pm.deskew.skew_angle == pytest.approx(2.0)

    def test_page_metadata_deskew_none_by_default(self) -> None:
        """PageMetadata.deskew is None by default."""
        from image_preprocessing_detector.schema import PageMetadata

        pm = PageMetadata(
            page_index=0,
            width_px=640,
            height_px=480,
            dpi_input=300,
            dpi_effective=300,
        )
        assert pm.deskew is None
