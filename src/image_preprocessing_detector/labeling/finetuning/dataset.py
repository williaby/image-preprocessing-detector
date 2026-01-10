# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Training dataset adapter for DIQA regression fine-tuning.

This module provides PyTorch Dataset classes for loading DIQA-5000
and other datasets for regression head training.

Enforces strict train/val/test split discipline:
- Training split: Used for model learning only
- Validation split: Used for early stopping and hyperparameter tuning
- Test split: NEVER used during training (reserved for Project A evaluation)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import structlog
import torch
from torch.utils.data import Dataset

logger = structlog.get_logger(__name__)


@dataclass
class DIQASample:
    """Single sample for DIQA training.

    Attributes:
        image_id: Unique identifier for the sample
        image_path: Path to the image file
        overall: Overall quality score [0, 1]
        sharpness: Sharpness score [0, 1]
        color: Color fidelity score [0, 1]
        metadata: Additional metadata
    """

    image_id: str
    image_path: str
    overall: float
    sharpness: float
    color: float
    metadata: dict[str, Any] | None = None

    def to_target_tensor(self) -> torch.Tensor:
        """Convert scores to target tensor.

        Returns:
            Tensor of shape [3] with [overall, sharpness, color]
        """
        return torch.tensor(
            [self.overall, self.sharpness, self.color], dtype=torch.float32
        )


class DIQATrainingDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """PyTorch Dataset for DIQA regression training.

    Loads images and targets from DIQA-5000 or compatible datasets.
    Applies data augmentation for training and supports various
    image preprocessing pipelines.

    IMPORTANT: This dataset enforces split discipline.
    The test split is blocked from training to preserve evaluation integrity.

    Example:
        >>> from torchvision import transforms
        >>> transform = transforms.Compose(
        ...     [
        ...         transforms.Resize((224, 224)),
        ...         transforms.ToTensor(),
        ...     ]
        ... )
        >>> dataset = DIQATrainingDataset(
        ...     data_dir="/data/diqa5000",
        ...     split="train",
        ...     transform=transform,
        ... )
        >>> image, target = dataset[0]
    """

    # Block test split to prevent accidental data leakage
    BLOCKED_SPLITS: ClassVar[set[str]] = {"test"}
    ALLOWED_SPLITS: ClassVar[set[str]] = {"train", "val", "validation"}

    def __init__(
        self,
        data_dir: str | Path,
        split: str = "train",
        transform: Callable[[Any], torch.Tensor] | None = None,
        target_transform: Callable[[torch.Tensor], torch.Tensor] | None = None,
        max_samples: int | None = None,
        synthetic_fallback: bool = True,
    ) -> None:
        """Initialize the training dataset.

        Args:
            data_dir: Root directory of the dataset.
            split: Data split ("train" or "val"). Test is blocked.
            transform: Image transform pipeline.
            target_transform: Target transform (optional).
            max_samples: Maximum number of samples to load.
            synthetic_fallback: Generate synthetic data if real data not found.

        Raises:
            ValueError: If attempting to load test split.
        """
        self.data_dir = Path(data_dir)
        self.split = split.lower()
        self.transform = transform
        self.target_transform = target_transform
        self.max_samples = max_samples

        # Block test split
        if self.split in self.BLOCKED_SPLITS:
            msg = (
                "Test split is blocked for training datasets to preserve "
                "evaluation integrity. Use 'train' or 'val' splits only."
            )
            raise ValueError(msg)

        if self.split not in self.ALLOWED_SPLITS:
            msg = f"Unknown split: {split}. Must be one of {self.ALLOWED_SPLITS}"
            raise ValueError(msg)

        # Normalize split name
        if self.split == "validation":
            self.split = "val"

        # Load samples
        self.samples = self._load_samples(synthetic_fallback)

        logger.info(
            "diqa_training_dataset_loaded",
            data_dir=str(self.data_dir),
            split=self.split,
            num_samples=len(self.samples),
        )

    def _load_samples(self, synthetic_fallback: bool) -> list[DIQASample]:
        """Load samples from disk or generate synthetic data.

        Args:
            synthetic_fallback: Generate synthetic data if needed.

        Returns:
            List of DIQASample objects.
        """
        samples = []

        # Try to load real annotations
        annotations_path = self._find_annotations_file()

        if annotations_path is not None:
            samples = self._load_from_annotations(annotations_path)
        elif synthetic_fallback:
            logger.warning(
                "annotations_not_found",
                message="Generating synthetic training data for development",
            )
            samples = self._generate_synthetic_samples()
        else:
            msg = f"No annotations found for split '{self.split}' in {self.data_dir}"
            raise FileNotFoundError(msg)

        # Limit samples if requested
        if self.max_samples is not None and len(samples) > self.max_samples:
            samples = samples[: self.max_samples]

        return samples

    def _find_annotations_file(self) -> Path | None:
        """Find the annotations file for the current split.

        Returns:
            Path to annotations file or None if not found.
        """
        # Common locations for annotations
        search_paths = [
            self.data_dir / "annotations" / f"{self.split}.csv",
            self.data_dir / f"{self.split}.csv",
            self.data_dir / "annotations" / f"{self.split}_annotations.csv",
            self.data_dir / f"{self.split}_labels.csv",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_from_annotations(self, annotations_path: Path) -> list[DIQASample]:
        """Load samples from annotations CSV file.

        Expected CSV format:
            image_id,image_path,overall,sharpness,color

        Args:
            annotations_path: Path to annotations CSV.

        Returns:
            List of DIQASample objects.
        """
        import csv

        samples = []

        with open(annotations_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Handle relative paths
                image_path = row.get("image_path", row.get("path", ""))
                if not Path(image_path).is_absolute():
                    image_path = str(self.data_dir / image_path)

                sample = DIQASample(
                    image_id=row.get("image_id", row.get("id", "")),
                    image_path=image_path,
                    overall=float(row.get("overall", row.get("quality", 0.5))),
                    sharpness=float(row.get("sharpness", row.get("sharp", 0.5))),
                    color=float(row.get("color", row.get("colour", 0.5))),
                )
                samples.append(sample)

        logger.info(
            "annotations_loaded",
            path=str(annotations_path),
            num_samples=len(samples),
        )

        return samples

    def _generate_synthetic_samples(self, num_samples: int = 500) -> list[DIQASample]:
        """Generate synthetic samples for development/testing.

        Creates synthetic data with correlated scores that mimic
        real DIQA-5000 distributions.

        Args:
            num_samples: Number of synthetic samples to generate.

        Returns:
            List of synthetic DIQASample objects.
        """
        np.random.seed(42 if self.split == "train" else 43)

        samples = []
        for i in range(num_samples):
            # Generate correlated scores
            base_quality = np.random.beta(2, 2)  # Centered around 0.5
            noise = np.random.normal(0, 0.1, 3)

            overall = np.clip(base_quality + noise[0], 0.0, 1.0)
            sharpness = np.clip(base_quality + noise[1] - 0.05, 0.0, 1.0)
            color = np.clip(base_quality + noise[2] + 0.05, 0.0, 1.0)

            sample = DIQASample(
                image_id=f"synthetic_{self.split}_{i:04d}",
                image_path="",  # No real image
                overall=float(overall),
                sharpness=float(sharpness),
                color=float(color),
            )
            samples.append(sample)

        return samples

    def __len__(self) -> int:
        """Get number of samples in dataset."""
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Get a single sample.

        Args:
            idx: Sample index.

        Returns:
            Tuple of (image_tensor, target_tensor)
        """
        sample = self.samples[idx]

        # Load image
        image = self._load_image(sample)

        # Apply transform
        if self.transform is not None:
            image = self.transform(image)

        # Get target
        target = sample.to_target_tensor()

        if self.target_transform is not None:
            target = self.target_transform(target)

        return image, target

    def _load_image(self, sample: DIQASample) -> Any:
        """Load image from disk or generate synthetic.

        Args:
            sample: Sample to load image for.

        Returns:
            PIL Image or numpy array.
        """
        from PIL import Image

        if sample.image_path and Path(sample.image_path).exists():
            return Image.open(sample.image_path).convert("RGB")

        # Generate synthetic image based on quality scores
        return self._generate_synthetic_image(sample)

    def _generate_synthetic_image(self, sample: DIQASample) -> Any:
        """Generate a synthetic image for training.

        Creates an image with visual characteristics that correlate
        with the target quality scores.

        Args:
            sample: Sample with target scores.

        Returns:
            PIL Image.
        """
        from PIL import Image

        # Create base image
        size = (224, 224)
        np.random.seed(hash(sample.image_id) % (2**32))

        # Base texture with quality-dependent noise
        noise_level = (1.0 - sample.overall) * 50
        img = np.random.randint(100, 156, (*size, 3), dtype=np.uint8)
        noise = np.random.normal(0, noise_level, (*size, 3))
        img = np.clip(img + noise, 0, 255).astype(np.uint8)

        # Add structure based on sharpness
        if sample.sharpness > 0.5:
            # Add edge-like features
            for _ in range(int(sample.sharpness * 10)):
                x1, y1 = np.random.randint(0, size[0], 2)
                x2, y2 = np.random.randint(0, size[0], 2)
                # Simple line drawing
                img[x1:x2, y1:y2, :] = np.clip(
                    img[x1:x2, y1:y2, :] + 30, 0, 255
                ).astype(np.uint8)

        # Adjust color based on color score
        if sample.color > 0.5:
            # Enhance color variation
            img_float = img.astype(np.float32)
            color_factor = float(1.0 + (sample.color - 0.5) * 0.2)
            img_float[:, :, 0] = img_float[:, :, 0] * color_factor  # R
            img_float[:, :, 2] = img_float[:, :, 2] * color_factor  # B
            img = np.clip(img_float, 0, 255).astype(np.uint8)

        return Image.fromarray(img)

    def get_sample_info(self, idx: int) -> DIQASample:
        """Get sample information without loading image.

        Args:
            idx: Sample index.

        Returns:
            DIQASample object.
        """
        return self.samples[idx]


def get_default_transforms(
    is_training: bool = True,
    image_size: int = 224,
) -> Callable[[Any], Any]:
    """Get default image transforms for DIQA training.

    Args:
        is_training: Whether to include training augmentations.
        image_size: Target image size.

    Returns:
        Transform pipeline.
    """
    from torchvision import transforms

    if is_training:
        return transforms.Compose(  # type: ignore[no-any-return]
            [
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
    return transforms.Compose(  # type: ignore[no-any-return]
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def create_data_loaders(
    data_dir: str | Path,
    batch_size: int = 16,
    num_workers: int = 4,
    image_size: int = 224,
    max_train_samples: int | None = None,
    max_val_samples: int | None = None,
) -> tuple[Any, Any]:
    """Create training and validation data loaders.

    Args:
        data_dir: Root directory of the dataset.
        batch_size: Batch size for training.
        num_workers: Number of data loading workers.
        image_size: Target image size.
        max_train_samples: Maximum training samples (for debugging).
        max_val_samples: Maximum validation samples.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    from torch.utils.data import DataLoader

    train_dataset = DIQATrainingDataset(
        data_dir=data_dir,
        split="train",
        transform=get_default_transforms(is_training=True, image_size=image_size),
        max_samples=max_train_samples,
    )

    val_dataset = DIQATrainingDataset(
        data_dir=data_dir,
        split="val",
        transform=get_default_transforms(is_training=False, image_size=image_size),
        max_samples=max_val_samples,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader
