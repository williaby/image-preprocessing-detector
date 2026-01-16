# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Utility functions for HyperIQA++ training.

Includes soft label construction, data augmentation, and helper functions.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import numpy as np
import torch
from PIL import Image, ImageOps

if TYPE_CHECKING:
    pass


def create_soft_labels(mos_score: float, num_bins: int = 10) -> torch.Tensor:
    """Convert MOS to soft probability distribution using linear interpolation.

    DeQA-Doc Method 2: For MOS value between integers c and c+1,
    assign probability p_c = c+1 - μ and p_{c+1} = μ - c.

    Args:
        mos_score: Mean opinion score in [1, 5] range
        num_bins: Number of quality bins (default 10)

    Returns:
        Soft label distribution tensor [num_bins] with sum=1.0

    Raises:
        ValueError: If soft labels do not sum to 1.0 (validation failure)

    Example:
        >>> labels = create_soft_labels(3.7, num_bins=10)
        >>> # MOS 3.7 → bins 3,4 → soft_labels[6]=0.3, soft_labels[7]=0.7
        >>> labels = create_soft_labels(3.0, num_bins=10)
        >>> # MOS 3.0 → bin 3 → soft_labels[5]=1.0
    """
    min_score, max_score = 1.0, 5.0

    # Clamp to valid range
    mos_score = float(np.clip(mos_score, min_score, max_score))

    # Find adjacent bins (1-indexed in DIQA-5000)
    lower_bin = int(np.floor(mos_score))
    upper_bin = int(np.ceil(mos_score))

    # Linear interpolation weights
    upper_weight = mos_score - lower_bin
    lower_weight = 1.0 - upper_weight

    # Create soft label distribution (0-indexed array)
    soft_labels = np.zeros(num_bins, dtype=np.float32)

    # Map 1-5 bins to evenly spaced positions in 10-bin array
    # Bins [1, 2, 3, 4, 5] → indices [0, 2, 5, 7, 9] approximately
    def bin_to_idx(b: int) -> int:
        # Ensure integer index with proper rounding
        return round((b - 1) * (num_bins - 1) / 4.0)

    lower_idx = bin_to_idx(lower_bin)
    upper_idx = bin_to_idx(upper_bin)

    # Ensure indices are within bounds
    lower_idx = min(lower_idx, num_bins - 1)
    upper_idx = min(upper_idx, num_bins - 1)

    # Assign weights - use += to handle case where lower_idx == upper_idx
    soft_labels[lower_idx] += lower_weight
    if upper_idx != lower_idx and upper_bin <= 5 and upper_idx < num_bins:
        soft_labels[upper_idx] += upper_weight

    # Validation: ensure sum=1.0 (within floating point tolerance)
    label_sum = soft_labels.sum()
    if not np.isclose(label_sum, 1.0, atol=1e-6):
        msg = (
            f"Soft labels do not sum to 1.0 (got {label_sum:.6f}). "
            f"MOS={mos_score}, lower_bin={lower_bin}, upper_bin={upper_bin}, "
            f"lower_idx={lower_idx}, upper_idx={upper_idx}"
        )
        raise ValueError(msg)

    return torch.tensor(soft_labels, dtype=torch.float32)


def apply_safe_augmentations(image: Image.Image) -> Image.Image:
    """Apply augmentations that preserve quality labels.

    These augmentations change the image view but NOT its quality:
    - Horizontal flip: Document quality is the same when mirrored
    - Random crop + resize: Multi-scale learning without quality change

    FORBIDDEN augmentations (change quality labels):
    - Blur (changes sharpness label)
    - Noise injection (changes technical quality)
    - Color jitter (changes color fidelity label)
    - JPEG compression (changes technical quality)

    Args:
        image: PIL Image to augment

    Returns:
        Augmented PIL Image
    """
    # Horizontal flip (50% chance)
    if random.random() < 0.5:  # noqa: S311  # Data augmentation, not cryptographic
        image = ImageOps.mirror(image)

    # Random crop and resize (30% chance) for multi-scale learning
    if random.random() < 0.3:  # noqa: S311  # Data augmentation, not cryptographic
        w, h = image.size
        crop_scale = random.choice([0.8, 0.9, 1.0])  # noqa: S311
        new_w, new_h = int(w * crop_scale), int(h * crop_scale)
        left = random.randint(0, max(1, w - new_w))  # noqa: S311
        top = random.randint(0, max(1, h - new_h))  # noqa: S311
        image = image.crop((left, top, left + new_w, top + new_h))
        # Resize back to original dimensions
        image = image.resize((w, h), Image.Resampling.BILINEAR)

    return image


def compute_vquala_score(
    srcc_overall: float,
    srcc_sharpness: float,
    srcc_color: float,
) -> float:
    """Compute VQualA 2025 final score.

    VQualA Score = 0.5xOverall + 0.25xSharpness + 0.25xColor

    Args:
        srcc_overall: Spearman correlation for overall quality
        srcc_sharpness: Spearman correlation for sharpness
        srcc_color: Spearman correlation for color fidelity

    Returns:
        VQualA final score
    """
    return 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color


def normalize_mos_to_01(mos: float) -> float:
    """Normalize MOS from [1, 5] scale to [0, 1] scale.

    Args:
        mos: Mean Opinion Score in [1, 5] range

    Returns:
        Normalized score in [0, 1] range
    """
    return (mos - 1.0) / 4.0


def denormalize_score_to_mos(score: float) -> float:
    """Convert normalized [0, 1] score back to [1, 5] MOS scale.

    Args:
        score: Normalized score in [0, 1] range

    Returns:
        MOS score in [1, 5] range
    """
    return score * 4.0 + 1.0
