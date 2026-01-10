# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""PyTorch Dataset for MUSIQ fine-tuning on DIQA-5000.

This module provides a PyTorch Dataset wrapper for DIQA-5000 that:
- Returns continuous quality scores (not binary thresholds)
- Applies augmentation pipelines for each training phase
- Handles proper tensor conversion and normalization

Reference: docs/planning/MUSIQ_FINETUNING_PLAN.md Section 6
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.utils.data import Dataset

if TYPE_CHECKING:
    import albumentations as alb

    from image_preprocessing_detector.labeling.arena.datasets.base import (
        DIQA5000Dataset,
    )


def get_phase1_transforms(target_size: int = 224) -> alb.Compose:
    """Get augmentation pipeline for Phase 1 (head warmup).

    Phase 1 uses minimal augmentation to focus on learning
    the mapping from features to quality scores.

    Note: PyIQA MUSIQ can handle arbitrary image sizes through its
    multi-scale patch extraction. We resize to a consistent size
    only for batching efficiency. Images are expected in [0, 1] range.

    Args:
        target_size: Target size for resizing (square output).

    Returns:
        Albumentations Compose pipeline.
    """
    import albumentations as alb
    from albumentations.pytorch import ToTensorV2

    return alb.Compose(
        [
            # Resize to consistent size for batching
            # MUSIQ can handle arbitrary sizes but consistent batching is easier
            alb.Resize(height=target_size, width=target_size),
            # Convert to tensor (ToTensorV2 outputs uint8, we normalize in __getitem__)
            ToTensorV2(),
        ]
    )


def get_phase2_transforms(target_size: int = 224) -> alb.Compose:
    """Get augmentation pipeline for Phase 2 (full fine-tuning).

    Phase 2 uses label-preserving augmentations to improve
    generalization while maintaining quality perception.

    Note: PyIQA MUSIQ can handle arbitrary image sizes through its
    multi-scale patch extraction. We resize to a consistent size
    only for batching efficiency. Images are expected in [0, 1] range.

    Args:
        target_size: Target size for resizing (square output).

    Returns:
        Albumentations Compose pipeline.
    """
    import albumentations as alb
    from albumentations.pytorch import ToTensorV2

    return alb.Compose(
        [
            # Resize to consistent size for batching
            alb.Resize(height=target_size, width=target_size),
            # Augmentations (applied before final resize for quality preservation)
            alb.HorizontalFlip(p=0.5),
            alb.Rotate(limit=5, p=0.3),  # Small rotation to preserve quality perception
            alb.ColorJitter(
                brightness=0.1,
                contrast=0.1,
                saturation=0.1,
                hue=0.05,
                p=0.3,
            ),
            # Convert to tensor (ToTensorV2 outputs uint8, we normalize in __getitem__)
            ToTensorV2(),
        ]
    )


def get_validation_transforms(target_size: int = 224) -> alb.Compose:
    """Get transform pipeline for validation (no augmentation).

    Note: PyIQA MUSIQ can handle arbitrary image sizes through its
    multi-scale patch extraction. We resize to a consistent size
    only for batching efficiency. Images are expected in [0, 1] range.

    Args:
        target_size: Target size for resizing (square output).

    Returns:
        Albumentations Compose pipeline.
    """
    import albumentations as alb
    from albumentations.pytorch import ToTensorV2

    return alb.Compose(
        [
            # Resize to consistent size for batching
            alb.Resize(height=target_size, width=target_size),
            # Convert to tensor (ToTensorV2 outputs uint8, we normalize in __getitem__)
            ToTensorV2(),
        ]
    )


class DIQA5000TrainingDataset(Dataset[tuple[torch.Tensor, dict[str, torch.Tensor]]]):
    """PyTorch Dataset for DIQA-5000 with continuous labels.

    Wraps the existing DIQA5000Dataset for training with:
    - On-the-fly augmentation
    - Proper tensor conversion
    - Label normalization to [0, 1]

    Example:
        >>> dataset = DIQA5000TrainingDataset(
        ...     root_dir="/path/to/diqa-5000",
        ...     split="train",
        ...     transform=get_phase1_transforms(),
        ... )
        >>> image, labels = dataset[0]
        >>> print(image.shape)  # [3, H, W]
        >>> print(labels["sharpness"])  # tensor(0.xxx)
    """

    def __init__(
        self,
        root_dir: str | Path,
        split: str = "train",
        transform: alb.Compose | None = None,
        target_size: tuple[int, int] | None = None,
    ) -> None:
        """Initialize DIQA-5000 training dataset.

        Args:
            root_dir: Path to DIQA-5000 dataset root.
            split: Dataset split ('train', 'val', 'test').
            transform: Albumentations transform pipeline.
            target_size: Optional (H, W) to resize images.
        """
        from image_preprocessing_detector.labeling.arena.datasets.base import (
            DIQA5000Dataset,
        )

        # Load base dataset (already normalizes MOS [1-5] -> [0-1])
        self.base_dataset: DIQA5000Dataset = DIQA5000Dataset(
            root_dir=root_dir,
            split=split,
            normalize_scores=True,
        )

        self.transform = transform
        self.target_size = target_size
        self.split = split

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self.base_dataset)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Get a sample.

        Args:
            idx: Sample index.

        Returns:
            Tuple of (image_tensor, labels_dict).
            - image_tensor: [3, H, W] float tensor
            - labels_dict: {'overall': tensor, 'sharpness': tensor, 'color': tensor}
        """
        sample = self.base_dataset[idx]

        # Get image as numpy array [H, W, C]
        image = sample.image

        # Resize if specified
        if self.target_size is not None:
            import cv2

            image = cv2.resize(
                image,
                (self.target_size[1], self.target_size[0]),
                interpolation=cv2.INTER_LINEAR,
            )

        # Apply augmentation
        if self.transform is not None:
            transformed = self.transform(image=image)
            image = transformed["image"]
            # ToTensorV2 outputs uint8 tensor - convert to float [0, 1]
            if image.dtype == torch.uint8:
                image = image.float() / 255.0
        else:
            # Default: just convert to tensor and normalize
            image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0

        # Convert labels to tensors
        labels = {
            "overall": torch.tensor(
                sample.ground_truth["overall"], dtype=torch.float32
            ),
            "sharpness": torch.tensor(
                sample.ground_truth["sharpness"], dtype=torch.float32
            ),
            "color": torch.tensor(sample.ground_truth["color"], dtype=torch.float32),
        }

        return image, labels


def create_dataloaders(
    root_dir: str | Path,
    batch_size: int = 32,
    num_workers: int = 4,
    phase: int = 1,
    target_size: tuple[int, int] | int | None = 224,
) -> tuple[torch.utils.data.DataLoader[Any], torch.utils.data.DataLoader[Any]]:
    """Create train and validation dataloaders.

    Args:
        root_dir: Path to DIQA-5000 dataset root.
        batch_size: Batch size for training.
        num_workers: Number of data loading workers.
        phase: Training phase (1 or 2) for augmentation selection.
        target_size: Image size for resizing (int for square, or (H, W) tuple).
            Default 224 matches MUSIQ's KonIQ-10k training resolution.

    Returns:
        Tuple of (train_loader, val_loader).
    """
    # Handle target_size - convert tuple to int (use max dimension)
    if isinstance(target_size, tuple):
        img_size = max(target_size)
    else:
        img_size = target_size if target_size is not None else 224

    # Select transforms based on phase (with resize)
    train_transform = (
        get_phase1_transforms(target_size=img_size)
        if phase == 1
        else get_phase2_transforms(target_size=img_size)
    )
    val_transform = get_validation_transforms(target_size=img_size)

    # Create datasets (no target_size needed - transforms handle it)
    train_dataset = DIQA5000TrainingDataset(
        root_dir=root_dir,
        split="train",
        transform=train_transform,
    )

    val_dataset = DIQA5000TrainingDataset(
        root_dir=root_dir,
        split="val",
        transform=val_transform,
    )

    # Create dataloaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader


def collate_diqa_batch(
    batch: list[tuple[torch.Tensor, dict[str, torch.Tensor]]],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Custom collate function for DIQA batches.

    Args:
        batch: List of (image, labels) tuples.

    Returns:
        Tuple of (batched_images, batched_labels).
    """
    images = torch.stack([item[0] for item in batch])
    labels = {
        dim: torch.stack([item[1][dim] for item in batch])
        for dim in ["overall", "sharpness", "color"]
    }
    return images, labels
