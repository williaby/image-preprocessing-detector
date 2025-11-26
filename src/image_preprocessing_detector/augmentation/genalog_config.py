"""Genalog degradation configuration schemas.

This module defines Pydantic configuration models for controlling
synthetic document degradations using Microsoft's Genalog library.

Supports degradation types:
- Blur (Gaussian blur to simulate defocus/motion blur)
- Bleed-through (double-sided printing artifact)
- Salt & Pepper noise (ink degradation)
- Morphological operations (erode, dilate, open, close)

References:
- Genalog documentation: https://microsoft.github.io/genalog/
- Phase 2 Week 1 requirements: PROJECT_PLAN.md lines 937-968
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MorphologicalOperation(str, Enum):
    """Morphological operations for document degradation.

    Operations:
        ERODE: Shrinks foreground objects (simulates ink overflow)
        DILATE: Expands foreground objects (simulates ink spreading)
        OPEN: Erosion followed by dilation (removes small bright spots)
        CLOSE: Dilation followed by erosion (fills small holes)
    """

    ERODE = "erode"
    DILATE = "dilate"
    OPEN = "open"
    CLOSE = "close"


class BlurConfig(BaseModel):
    """Configuration for Gaussian blur degradation.

    Simulates defocus blur, motion blur, or low-quality scanning.

    Attributes:
        enabled: Whether to apply blur degradation
        kernel_size: Blur kernel size in pixels (must be odd, >= 1)
        sigma: Gaussian kernel standard deviation (0 = auto-calculate from kernel_size)

    Example:
        >>> config = BlurConfig(enabled=True, kernel_size=5, sigma=1.5)
        >>> # Creates moderate blur with 5x5 kernel
    """

    enabled: bool = Field(default=True, description="Enable blur degradation")
    kernel_size: int = Field(
        default=3,
        ge=1,
        description="Blur kernel size in pixels (must be odd)",
    )
    sigma: float = Field(
        default=0.0,
        ge=0.0,
        description="Gaussian kernel standard deviation (0 = auto)",
    )

    @field_validator("kernel_size")
    @classmethod
    def validate_odd_kernel(cls, v: int) -> int:
        """Ensure kernel size is odd."""
        if v % 2 == 0:
            msg = f"kernel_size must be odd, got {v}"
            raise ValueError(msg)
        return v


class BleedThroughConfig(BaseModel):
    """Configuration for bleed-through degradation.

    Simulates double-sided printing where text from the reverse side
    shows through the paper.

    Attributes:
        enabled: Whether to apply bleed-through degradation
        alpha: Blending strength (0.0 = no effect, 1.0 = full bleed-through)
        offset_x: Horizontal offset in pixels for reverse side alignment
        offset_y: Vertical offset in pixels for reverse side alignment

    Example:
        >>> config = BleedThroughConfig(
        ...     enabled=True, alpha=0.3, offset_x=2, offset_y=-1
        ... )
        >>> # Simulates mild bleed-through with slight misalignment
    """

    enabled: bool = Field(default=False, description="Enable bleed-through degradation")
    alpha: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Blending strength (0-1)",
    )
    offset_x: int = Field(
        default=0,
        description="Horizontal offset in pixels",
    )
    offset_y: int = Field(
        default=0,
        description="Vertical offset in pixels",
    )


class SaltPepperConfig(BaseModel):
    """Configuration for salt & pepper noise degradation.

    Simulates ink degradation, scanner noise, or photocopy artifacts.

    Attributes:
        enabled: Whether to apply salt & pepper noise
        amount: Proportion of pixels to corrupt (0.0 to 1.0)
        salt_vs_pepper: Ratio of salt (white) to pepper (black) noise

    Example:
        >>> config = SaltPepperConfig(enabled=True, amount=0.01, salt_vs_pepper=0.5)
        >>> # Adds 1% noise with equal salt/pepper distribution
    """

    enabled: bool = Field(
        default=False,
        description="Enable salt & pepper noise degradation",
    )
    amount: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Proportion of pixels to corrupt (0-1)",
    )
    salt_vs_pepper: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Ratio of salt to pepper noise (0-1)",
    )


class MorphologicalConfig(BaseModel):
    """Configuration for morphological operation degradation.

    Simulates ink spreading, overflow, or degraded printing quality.

    Attributes:
        enabled: Whether to apply morphological operations
        operation: Type of morphological operation to apply
        kernel_size: Size of the morphological kernel (must be odd)
        iterations: Number of times to apply the operation

    Example:
        >>> config = MorphologicalConfig(
        ...     enabled=True,
        ...     operation=MorphologicalOperation.ERODE,
        ...     kernel_size=3,
        ...     iterations=1,
        ... )
        >>> # Simulates slight ink overflow with single erosion pass
    """

    enabled: bool = Field(
        default=False,
        description="Enable morphological degradation",
    )
    operation: MorphologicalOperation = Field(
        default=MorphologicalOperation.ERODE,
        description="Morphological operation type",
    )
    kernel_size: int = Field(
        default=3,
        ge=1,
        description="Morphological kernel size (must be odd)",
    )
    iterations: int = Field(
        default=1,
        ge=1,
        description="Number of times to apply operation",
    )

    @field_validator("kernel_size")
    @classmethod
    def validate_odd_kernel(cls, v: int) -> int:
        """Ensure kernel size is odd."""
        if v % 2 == 0:
            msg = f"kernel_size must be odd, got {v}"
            raise ValueError(msg)
        return v


class DegradationConfig(BaseModel):
    """Top-level configuration for all Genalog degradations.

    Combines multiple degradation types that can be applied sequentially
    to generate synthetic training data for IQA models.

    Attributes:
        blur: Gaussian blur configuration
        bleed_through: Bleed-through configuration
        salt_pepper: Salt & pepper noise configuration
        morphological: Morphological operations configuration
        seed: Random seed for reproducibility (None = random)

    Example:
        >>> config = DegradationConfig(
        ...     blur=BlurConfig(enabled=True, kernel_size=5),
        ...     salt_pepper=SaltPepperConfig(enabled=True, amount=0.02),
        ...     seed=42,
        ... )
        >>> # Applies blur + noise with reproducible results

    References:
        - image_reference_sets.md Section IV: Synthetic Generation
        - PROJECT_PLAN.md Phase 2 Week 1: Data Collection & Augmentation
    """

    blur: BlurConfig = Field(
        default_factory=BlurConfig,
        description="Blur degradation configuration",
    )
    bleed_through: BleedThroughConfig = Field(
        default_factory=BleedThroughConfig,
        description="Bleed-through degradation configuration",
    )
    salt_pepper: SaltPepperConfig = Field(
        default_factory=SaltPepperConfig,
        description="Salt & pepper noise configuration",
    )
    morphological: MorphologicalConfig = Field(
        default_factory=MorphologicalConfig,
        description="Morphological operations configuration",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility (None = random)",
    )

    def get_enabled_degradations(self) -> list[str]:
        """Get list of enabled degradation types.

        Returns:
            List of degradation names that are currently enabled.

        Example:
            >>> config = DegradationConfig(
            ...     blur=BlurConfig(enabled=True),
            ...     salt_pepper=SaltPepperConfig(enabled=True),
            ... )
            >>> config.get_enabled_degradations()
            ['blur', 'salt_pepper']
        """
        enabled = []
        if self.blur.enabled:
            enabled.append("blur")
        if self.bleed_through.enabled:
            enabled.append("bleed_through")
        if self.salt_pepper.enabled:
            enabled.append("salt_pepper")
        if self.morphological.enabled:
            enabled.append("morphological")
        return enabled

    def to_genalog_params(self) -> dict[str, Any]:
        """Convert configuration to Genalog-compatible parameters.

        Returns:
            Dictionary of parameters suitable for Genalog degradation functions.

        Note:
            This is a placeholder for Phase 2 implementation.
            Actual parameter mapping depends on Genalog API specifics.
        """
        # NOTE: This will be implemented in genalog_degrader.py
        # Placeholder for now - returns dict representation
        return {
            "blur": self.blur.model_dump() if self.blur.enabled else None,
            "bleed_through": (
                self.bleed_through.model_dump() if self.bleed_through.enabled else None
            ),
            "salt_pepper": (
                self.salt_pepper.model_dump() if self.salt_pepper.enabled else None
            ),
            "morphological": (
                self.morphological.model_dump() if self.morphological.enabled else None
            ),
            "seed": self.seed,
        }

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
