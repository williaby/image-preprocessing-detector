# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Dataset loader for DIQA-5000 with high-resolution support.

Implements:
- 1600x1600 high-resolution loading (DocIQ protocol)
- Soft label generation (DeQA-Doc method)
- Safe quality-preserving augmentations
- CSV-based DIQA-5000 format support
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from image_preprocessing_detector.labeling.hyperiqa_plus_plus.utils import (
    apply_safe_augmentations,
    create_soft_labels,
    normalize_mos_to_01,
)

if TYPE_CHECKING:
    from torch import Tensor

logger = logging.getLogger(__name__)


class DIQA5000HighResDataset(Dataset):
    """DIQA-5000 dataset with 1600x1600 resolution and soft labels.

    Features:
        - High-resolution 1600x1600 input (DocIQ protocol)
        - Soft label distribution generation
        - Quality-preserving augmentations only
        - Three-dimensional MOS (overall, sharpness, color)

    Dataset Structure:
        root_dir/
        ├── train/
        │   ├── res/              # Distorted images
        │   └── train.csv         # Annotations
        ├── val/
        │   ├── res/
        │   └── val.csv
        └── test/
            ├── res/
            └── test.csv

    CSV Format: res,ori,overall,sharpness,color_fidelity
    """

    def __init__(
        self,
        root_dir: str | Path,
        split: str = "train",
        image_size: tuple[int, int] = (1600, 1600),
        num_bins: int = 10,
        augment: bool = True,
    ) -> None:
        """Initialize DIQA-5000 dataset.

        Args:
            root_dir: Path to DIQA-5000 root directory
            split: Dataset split ('train', 'val', or 'test')
            image_size: Target image size (default 1600x1600 per DocIQ)
            num_bins: Number of quality bins for soft labels
            augment: Whether to apply augmentations (train split only)
        """
        self.root_dir = Path(root_dir)
        self.split = split
        self.image_size = image_size
        self.num_bins = num_bins
        self.augment = augment and split == "train"

        # Load CSV annotations
        csv_path = self.root_dir / split / f"{split}.csv"
        if not csv_path.exists():
            msg = f"Annotations not found: {csv_path}"
            raise FileNotFoundError(msg)

        self.samples = self._load_annotations(csv_path)

        # Image directory
        self.images_dir = self.root_dir / split / "res"

        # Image preprocessing
        self.transform = self._create_transform()

        logger.info(
            f"Loaded {len(self.samples)} samples from DIQA-5000 {split} split "
            f"(resolution: {image_size[0]}x{image_size[1]})"
        )

    def _load_annotations(self, csv_path: Path) -> list[dict]:
        """Load annotations from DIQA-5000 CSV.

        CSV Format: res,ori,overall,sharpness,color_fidelity

        Args:
            csv_path: Path to CSV file

        Returns:
            List of annotation dictionaries
        """
        samples: list[dict[str, str | float]] = []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            samples.extend(
                {
                    "image_name": row["res"],
                    "mos_overall": float(row["overall"]),
                    "mos_sharpness": float(row["sharpness"]),
                    "mos_color": float(row["color_fidelity"]),
                }
                for row in reader
            )
        return samples

    def _create_transform(self) -> transforms.Compose:
        """Create transform pipeline for high-resolution input.

        Returns:
            Torchvision transform pipeline
        """
        return transforms.Compose(
            [
                transforms.Resize(self.image_size, antialias=True),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

    def __len__(self) -> int:
        """Get dataset size."""
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, Tensor | dict]:
        """Get dataset item with soft labels.

        Args:
            idx: Sample index

        Returns:
            Dictionary with:
                'pixel_values': Image tensor [3, H, W]
                'targets': {
                    'overall': {'mos', 'mos_normalized', 'soft_labels'},
                    'sharpness': {'mos', 'mos_normalized', 'soft_labels'},
                    'color': {'mos', 'mos_normalized', 'soft_labels'},
                }
                'image_name': Filename for debugging
        """
        sample = self.samples[idx]

        # Load image with path validation (security: prevent path traversal)
        img_path = (self.images_dir / sample["image_name"]).resolve()

        # Ensure path is within images directory
        if not img_path.is_relative_to(self.images_dir.resolve()):
            msg = f"Path traversal detected: {img_path}"
            raise ValueError(msg)

        # Ensure file exists
        if not img_path.exists():
            msg = f"Image not found: {img_path}"
            raise FileNotFoundError(msg)

        image = Image.open(img_path).convert("RGB")

        # Apply safe augmentations (train split only)
        if self.augment:
            image = apply_safe_augmentations(image)

        # Transform to tensor
        image_tensor = self.transform(image)

        # Create soft labels for each dimension
        soft_labels_overall = create_soft_labels(sample["mos_overall"], self.num_bins)
        soft_labels_sharpness = create_soft_labels(
            sample["mos_sharpness"], self.num_bins
        )
        soft_labels_color = create_soft_labels(sample["mos_color"], self.num_bins)

        # Normalize MOS to [0, 1] for loss computation
        mos_overall_norm = normalize_mos_to_01(sample["mos_overall"])
        mos_sharpness_norm = normalize_mos_to_01(sample["mos_sharpness"])
        mos_color_norm = normalize_mos_to_01(sample["mos_color"])

        return {
            "pixel_values": image_tensor,
            "targets": {
                "overall": {
                    "mos": torch.tensor(mos_overall_norm, dtype=torch.float32),
                    "soft_labels": soft_labels_overall,
                },
                "sharpness": {
                    "mos": torch.tensor(mos_sharpness_norm, dtype=torch.float32),
                    "soft_labels": soft_labels_sharpness,
                },
                "color": {
                    "mos": torch.tensor(mos_color_norm, dtype=torch.float32),
                    "soft_labels": soft_labels_color,
                },
            },
            "image_name": sample["image_name"],
        }
