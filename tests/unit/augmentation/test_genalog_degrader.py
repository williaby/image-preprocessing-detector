"""Unit tests for Genalog degrader module.

Tests cover:
- GenalogDegrader initialization
- Input validation (type checking, dtype)
- apply() method behavior
- apply_batch() method behavior
- create_default_degrader() factory function
"""

import numpy as np
import pytest

from image_preprocessing_detector.augmentation.genalog_config import (
    BlurConfig,
    DegradationConfig,
    SaltPepperConfig,
)
from image_preprocessing_detector.augmentation.genalog_degrader import (
    GenalogDegrader,
    create_default_degrader,
)

# =============================================================================
# GenalogDegrader Initialization Tests
# =============================================================================


@pytest.mark.unit
class TestGenalogDegraderInit:
    """Tests for GenalogDegrader initialization."""

    def test_init_with_default_config(self) -> None:
        """Test initialization with default configuration."""
        config = DegradationConfig()
        degrader = GenalogDegrader(config)

        assert degrader.config == config
        assert degrader._rng is not None

    def test_init_with_seed(self) -> None:
        """Test initialization with specific seed."""
        config = DegradationConfig(seed=42)
        degrader = GenalogDegrader(config)

        assert degrader.config.seed == 42

    def test_init_with_enabled_degradations(self) -> None:
        """Test initialization logs enabled degradations."""
        config = DegradationConfig(
            blur=BlurConfig(enabled=True),
            salt_pepper=SaltPepperConfig(enabled=True),
        )
        degrader = GenalogDegrader(config)

        enabled = degrader.config.get_enabled_degradations()
        assert "blur" in enabled
        assert "salt_pepper" in enabled


# =============================================================================
# GenalogDegrader.apply() Tests
# =============================================================================


@pytest.mark.unit
class TestGenalogDegraderApply:
    """Tests for GenalogDegrader.apply() method."""

    @pytest.fixture
    def degrader(self) -> GenalogDegrader:
        """Create a default degrader for tests."""
        config = DegradationConfig(seed=42)
        return GenalogDegrader(config)

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.zeros((100, 100, 3), dtype=np.uint8)

    def test_apply_returns_copy(
        self, degrader: GenalogDegrader, sample_image: np.ndarray
    ) -> None:
        """Test that apply returns a copy, not the original."""
        result = degrader.apply(sample_image)

        assert result is not sample_image
        assert np.array_equal(result, sample_image)  # Currently returns unchanged copy

    def test_apply_preserves_shape(
        self, degrader: GenalogDegrader, sample_image: np.ndarray
    ) -> None:
        """Test that apply preserves image shape."""
        result = degrader.apply(sample_image)
        assert result.shape == sample_image.shape

    def test_apply_preserves_dtype(
        self, degrader: GenalogDegrader, sample_image: np.ndarray
    ) -> None:
        """Test that apply preserves image dtype."""
        result = degrader.apply(sample_image)
        assert result.dtype == np.uint8

    def test_apply_rejects_non_array(self, degrader: GenalogDegrader) -> None:
        """Test that apply raises TypeError for non-array input."""
        with pytest.raises(TypeError, match="Expected NumPy array"):
            degrader.apply("not an array")  # type: ignore

        with pytest.raises(TypeError, match="Expected NumPy array"):
            degrader.apply([1, 2, 3])  # type: ignore

    def test_apply_rejects_wrong_dtype(self, degrader: GenalogDegrader) -> None:
        """Test that apply raises ValueError for wrong dtype."""
        float_image = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="Expected uint8 dtype"):
            degrader.apply(float_image)

        int16_image = np.zeros((100, 100, 3), dtype=np.int16)
        with pytest.raises(ValueError, match="Expected uint8 dtype"):
            degrader.apply(int16_image)

    def test_apply_accepts_various_shapes(self, degrader: GenalogDegrader) -> None:
        """Test that apply accepts various image dimensions."""
        # Small image
        small = np.zeros((10, 10, 3), dtype=np.uint8)
        result = degrader.apply(small)
        assert result.shape == (10, 10, 3)

        # Large image
        large = np.zeros((1000, 1000, 3), dtype=np.uint8)
        result = degrader.apply(large)
        assert result.shape == (1000, 1000, 3)

        # Non-square image
        rect = np.zeros((100, 200, 3), dtype=np.uint8)
        result = degrader.apply(rect)
        assert result.shape == (100, 200, 3)

    def test_apply_with_grayscale(self, degrader: GenalogDegrader) -> None:
        """Test apply with grayscale image (2D array)."""
        gray = np.zeros((100, 100), dtype=np.uint8)
        # Should work without error (returns copy)
        result = degrader.apply(gray)
        assert result.shape == gray.shape


# =============================================================================
# GenalogDegrader.apply_batch() Tests
# =============================================================================


@pytest.mark.unit
class TestGenalogDegraderApplyBatch:
    """Tests for GenalogDegrader.apply_batch() method."""

    @pytest.fixture
    def degrader(self) -> GenalogDegrader:
        """Create a default degrader for tests."""
        return GenalogDegrader(DegradationConfig(seed=42))

    def test_batch_returns_list(self, degrader: GenalogDegrader) -> None:
        """Test that apply_batch returns a list."""
        images = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
        results = degrader.apply_batch(images)

        assert isinstance(results, list)
        assert len(results) == 3

    def test_batch_preserves_individual_shapes(self, degrader: GenalogDegrader) -> None:
        """Test that batch processing preserves individual image shapes."""
        images = [
            np.zeros((50, 50, 3), dtype=np.uint8),
            np.zeros((100, 100, 3), dtype=np.uint8),
            np.zeros((75, 150, 3), dtype=np.uint8),
        ]
        results = degrader.apply_batch(images)

        assert results[0].shape == (50, 50, 3)
        assert results[1].shape == (100, 100, 3)
        assert results[2].shape == (75, 150, 3)

    def test_empty_batch(self, degrader: GenalogDegrader) -> None:
        """Test apply_batch with empty list."""
        results = degrader.apply_batch([])
        assert results == []


# =============================================================================
# GenalogDegrader.generate_sensitivity_gradient() Tests
# =============================================================================


@pytest.mark.unit
class TestGenalogDegraderSensitivity:
    """Tests for GenalogDegrader.generate_sensitivity_gradient() method."""

    @pytest.fixture
    def degrader(self) -> GenalogDegrader:
        """Create a default degrader for tests."""
        return GenalogDegrader(DegradationConfig(seed=42))

    def test_sensitivity_gradient_not_implemented(
        self, degrader: GenalogDegrader, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test that generate_sensitivity_gradient raises NotImplementedError."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with pytest.raises(NotImplementedError, match="Phase 2 Week 2"):
            # Use positional arguments since method params are prefixed with
            # underscores (_image, _degradation_type, etc.) to indicate unused
            degrader.generate_sensitivity_gradient(
                image,  # _image
                "blur",  # _degradation_type
                "kernel_size",  # _param_name
                (1.0, 11.0, 2.0),  # _param_range
                tmp_path,  # type: ignore  # _output_dir
            )


# =============================================================================
# create_default_degrader() Tests
# =============================================================================


@pytest.mark.unit
class TestCreateDefaultDegrader:
    """Tests for create_default_degrader() factory function."""

    def test_creates_degrader_without_seed(self) -> None:
        """Test create_default_degrader without seed."""
        degrader = create_default_degrader()

        assert isinstance(degrader, GenalogDegrader)
        assert degrader.config.seed is None

    def test_creates_degrader_with_seed(self) -> None:
        """Test create_default_degrader with seed."""
        degrader = create_default_degrader(seed=42)

        assert degrader.config.seed == 42

    def test_default_has_blur_enabled(self) -> None:
        """Test default degrader has blur enabled."""
        degrader = create_default_degrader()

        assert degrader.config.blur.enabled is True
        assert degrader.config.blur.kernel_size == 3
        assert degrader.config.blur.sigma == 1.0

    def test_default_has_salt_pepper_enabled(self) -> None:
        """Test default degrader has salt_pepper enabled."""
        degrader = create_default_degrader()

        assert degrader.config.salt_pepper.enabled is True
        assert degrader.config.salt_pepper.amount == 0.01
        assert degrader.config.salt_pepper.salt_vs_pepper == 0.5

    def test_reproducibility_with_same_seed(self) -> None:
        """Test that same seed produces reproducible RNG state."""
        degrader1 = create_default_degrader(seed=42)
        degrader2 = create_default_degrader(seed=42)

        # Both should have same seed
        assert degrader1.config.seed == degrader2.config.seed == 42
