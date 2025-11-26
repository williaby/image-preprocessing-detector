"""Unit tests for Genalog configuration schemas.

Tests cover:
- BlurConfig validation (odd kernel sizes)
- BleedThroughConfig parameter bounds
- SaltPepperConfig parameter bounds
- MorphologicalConfig validation
- DegradationConfig enabled degradations tracking
"""

import pytest
from pydantic import ValidationError

from image_preprocessing_detector.augmentation.genalog_config import (
    BleedThroughConfig,
    BlurConfig,
    DegradationConfig,
    MorphologicalConfig,
    MorphologicalOperation,
    SaltPepperConfig,
)

# =============================================================================
# BlurConfig Tests
# =============================================================================


@pytest.mark.unit
class TestBlurConfig:
    """Tests for BlurConfig validation."""

    def test_default_values(self) -> None:
        """Test BlurConfig has correct defaults."""
        config = BlurConfig()
        assert config.enabled is True
        assert config.kernel_size == 3
        assert config.sigma == pytest.approx(0.0)

    def test_valid_odd_kernel_sizes(self) -> None:
        """Test that odd kernel sizes are accepted."""
        for size in [1, 3, 5, 7, 9, 11]:
            config = BlurConfig(kernel_size=size)
            assert config.kernel_size == size

    def test_even_kernel_raises_error(self) -> None:
        """Test that even kernel sizes raise ValidationError."""
        with pytest.raises(ValidationError, match="kernel_size must be odd"):
            BlurConfig(kernel_size=2)

        with pytest.raises(ValidationError, match="kernel_size must be odd"):
            BlurConfig(kernel_size=4)

    def test_zero_kernel_raises_error(self) -> None:
        """Test that zero kernel size raises ValidationError."""
        with pytest.raises(ValidationError):
            BlurConfig(kernel_size=0)

    def test_negative_kernel_raises_error(self) -> None:
        """Test that negative kernel size raises ValidationError."""
        with pytest.raises(ValidationError):
            BlurConfig(kernel_size=-1)

    def test_negative_sigma_raises_error(self) -> None:
        """Test that negative sigma raises ValidationError."""
        with pytest.raises(ValidationError):
            BlurConfig(sigma=-1.0)

    def test_custom_sigma(self) -> None:
        """Test custom sigma values are accepted."""
        config = BlurConfig(sigma=2.5)
        assert config.sigma == pytest.approx(2.5)


# =============================================================================
# BleedThroughConfig Tests
# =============================================================================


@pytest.mark.unit
class TestBleedThroughConfig:
    """Tests for BleedThroughConfig validation."""

    def test_default_values(self) -> None:
        """Test BleedThroughConfig has correct defaults."""
        config = BleedThroughConfig()
        assert config.enabled is False
        assert config.alpha == pytest.approx(0.3)
        assert config.offset_x == 0
        assert config.offset_y == 0

    def test_alpha_bounds(self) -> None:
        """Test alpha must be between 0 and 1."""
        # Valid values
        BleedThroughConfig(alpha=0.0)
        BleedThroughConfig(alpha=0.5)
        BleedThroughConfig(alpha=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            BleedThroughConfig(alpha=-0.1)

        with pytest.raises(ValidationError):
            BleedThroughConfig(alpha=1.1)

    def test_offsets(self) -> None:
        """Test offset values can be positive, negative, or zero."""
        config = BleedThroughConfig(offset_x=10, offset_y=-5)
        assert config.offset_x == 10
        assert config.offset_y == -5


# =============================================================================
# SaltPepperConfig Tests
# =============================================================================


@pytest.mark.unit
class TestSaltPepperConfig:
    """Tests for SaltPepperConfig validation."""

    def test_default_values(self) -> None:
        """Test SaltPepperConfig has correct defaults."""
        config = SaltPepperConfig()
        assert config.enabled is False
        assert config.amount == pytest.approx(0.01)
        assert config.salt_vs_pepper == pytest.approx(0.5)

    def test_amount_bounds(self) -> None:
        """Test amount must be between 0 and 1."""
        SaltPepperConfig(amount=0.0)
        SaltPepperConfig(amount=0.5)
        SaltPepperConfig(amount=1.0)

        with pytest.raises(ValidationError):
            SaltPepperConfig(amount=-0.01)

        with pytest.raises(ValidationError):
            SaltPepperConfig(amount=1.01)

    def test_salt_vs_pepper_bounds(self) -> None:
        """Test salt_vs_pepper must be between 0 and 1."""
        SaltPepperConfig(salt_vs_pepper=0.0)  # All pepper
        SaltPepperConfig(salt_vs_pepper=1.0)  # All salt

        with pytest.raises(ValidationError):
            SaltPepperConfig(salt_vs_pepper=-0.1)

        with pytest.raises(ValidationError):
            SaltPepperConfig(salt_vs_pepper=1.1)


# =============================================================================
# MorphologicalConfig Tests
# =============================================================================


@pytest.mark.unit
class TestMorphologicalConfig:
    """Tests for MorphologicalConfig validation."""

    def test_default_values(self) -> None:
        """Test MorphologicalConfig has correct defaults."""
        config = MorphologicalConfig()
        assert config.enabled is False
        assert config.operation == MorphologicalOperation.ERODE
        assert config.kernel_size == 3
        assert config.iterations == 1

    def test_valid_operations(self) -> None:
        """Test all morphological operations are valid."""
        for op in MorphologicalOperation:
            config = MorphologicalConfig(operation=op)
            assert config.operation == op

    def test_odd_kernel_validation(self) -> None:
        """Test kernel size must be odd."""
        MorphologicalConfig(kernel_size=1)
        MorphologicalConfig(kernel_size=5)

        with pytest.raises(ValidationError, match="kernel_size must be odd"):
            MorphologicalConfig(kernel_size=2)

    def test_iterations_must_be_positive(self) -> None:
        """Test iterations must be at least 1."""
        MorphologicalConfig(iterations=1)
        MorphologicalConfig(iterations=10)

        with pytest.raises(ValidationError):
            MorphologicalConfig(iterations=0)


# =============================================================================
# DegradationConfig Tests
# =============================================================================


@pytest.mark.unit
class TestDegradationConfig:
    """Tests for DegradationConfig validation and methods."""

    def test_default_values(self) -> None:
        """Test DegradationConfig has correct defaults."""
        config = DegradationConfig()
        assert config.seed is None
        assert isinstance(config.blur, BlurConfig)
        assert isinstance(config.bleed_through, BleedThroughConfig)
        assert isinstance(config.salt_pepper, SaltPepperConfig)
        assert isinstance(config.morphological, MorphologicalConfig)

    def test_get_enabled_degradations_none(self) -> None:
        """Test get_enabled_degradations when none enabled."""
        config = DegradationConfig(
            blur=BlurConfig(enabled=False),
            bleed_through=BleedThroughConfig(enabled=False),
            salt_pepper=SaltPepperConfig(enabled=False),
            morphological=MorphologicalConfig(enabled=False),
        )
        enabled = config.get_enabled_degradations()
        assert enabled == []

    def test_get_enabled_degradations_all(self) -> None:
        """Test get_enabled_degradations when all enabled."""
        config = DegradationConfig(
            blur=BlurConfig(enabled=True),
            bleed_through=BleedThroughConfig(enabled=True),
            salt_pepper=SaltPepperConfig(enabled=True),
            morphological=MorphologicalConfig(enabled=True),
        )
        enabled = config.get_enabled_degradations()
        assert set(enabled) == {"blur", "bleed_through", "salt_pepper", "morphological"}

    def test_get_enabled_degradations_partial(self) -> None:
        """Test get_enabled_degradations with partial enablement."""
        config = DegradationConfig(
            blur=BlurConfig(enabled=True),
            salt_pepper=SaltPepperConfig(enabled=True),
        )
        enabled = config.get_enabled_degradations()
        assert "blur" in enabled
        assert "salt_pepper" in enabled
        assert "bleed_through" not in enabled
        assert "morphological" not in enabled

    def test_to_genalog_params(self) -> None:
        """Test to_genalog_params returns correct structure."""
        config = DegradationConfig(
            blur=BlurConfig(enabled=True, kernel_size=5),
            salt_pepper=SaltPepperConfig(enabled=True, amount=0.02),
            seed=42,
        )
        params = config.to_genalog_params()

        assert params["seed"] == 42
        assert params["blur"] is not None
        assert params["blur"]["kernel_size"] == 5
        assert params["salt_pepper"] is not None
        assert params["salt_pepper"]["amount"] == pytest.approx(0.02)
        assert params["bleed_through"] is None  # Not enabled
        assert params["morphological"] is None  # Not enabled

    def test_seed_reproducibility(self) -> None:
        """Test that seed can be set for reproducibility."""
        config = DegradationConfig(seed=12345)
        assert config.seed == 12345


# =============================================================================
# MorphologicalOperation Enum Tests
# =============================================================================


@pytest.mark.unit
class TestMorphologicalOperation:
    """Tests for MorphologicalOperation enum."""

    def test_all_operations_defined(self) -> None:
        """Test all expected operations are defined."""
        operations = [op.value for op in MorphologicalOperation]
        assert "erode" in operations
        assert "dilate" in operations
        assert "open" in operations
        assert "close" in operations

    def test_string_values(self) -> None:
        """Test operation string values."""
        assert MorphologicalOperation.ERODE.value == "erode"
        assert MorphologicalOperation.DILATE.value == "dilate"
        assert MorphologicalOperation.OPEN.value == "open"
        assert MorphologicalOperation.CLOSE.value == "close"
