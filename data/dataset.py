"""PyTorch Dataset for IQA Training.

Loads images and quality issue labels for training IQA models.

Sprint 3.3.5: Final Training Dataset (Milestone 10.3)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from numpy.typing import NDArray
from torch.utils.data import DataLoader, Dataset

# Quality issue types (from data/weak_supervision.py)
QUALITY_ISSUES = [
    "noise",
    "blur",
    "skew",
    "perspective",
    "low_contrast",
    "orientation",
]


class IQADataset(Dataset):
    """PyTorch Dataset for Image Quality Assessment.

    Loads images and multi-label quality issue annotations for training.

    Args:
        data_dir: Directory containing images and labels
        split: Dataset split ("train", "val", or "test")
        transform: Optional image transforms (albumentations or torchvision)
        return_quality_scores: If True, return raw quality scores in addition to labels

    Example:
        >>> dataset = IQADataset("data/final_training_dataset", split="train")
        >>> image, labels = dataset[0]
        >>> print(image.shape)  # (C, H, W)
        >>> print(labels.shape)  # (6,) - binary labels for 6 issues
    """

    def __init__(
        self,
        data_dir: str | Path,
        split: str = "train",
        transform: Any = None,
        return_quality_scores: bool = False,
    ) -> None:
        """Initialize IQA dataset."""
        self.data_dir = Path(data_dir)
        self.split = split
        self.transform = transform
        self.return_quality_scores = return_quality_scores

        # Load split metadata
        split_file = self.data_dir / f"{split}_split.json"
        if not split_file.exists():
            msg = f"Split file not found: {split_file}"
            raise FileNotFoundError(msg)

        with open(split_file) as f:
            self.split_metadata = json.load(f)

        self.samples = self.split_metadata["samples"]

        # Verify samples exist
        self._verify_samples()

    def _verify_samples(self) -> None:
        """Verify that all samples exist on disk."""
        missing_images = []
        missing_labels = []

        for sample in self.samples:
            image_path = Path(sample["image_path"])
            label_path = Path(sample["label_path"])

            if not image_path.exists():
                missing_images.append(str(image_path))

            if not label_path.exists():
                missing_labels.append(str(label_path))

        if missing_images or missing_labels:
            error_msg = "Dataset integrity check failed:\n"
            if missing_images:
                error_msg += f"Missing {len(missing_images)} images\n"
            if missing_labels:
                error_msg += f"Missing {len(missing_labels)} labels\n"
            raise FileNotFoundError(error_msg)

    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self.samples)

    def __getitem__(
        self, idx: int
    ) -> tuple[torch.Tensor, torch.Tensor] | tuple[torch.Tensor, torch.Tensor, dict]:
        """Get image and labels for given index.

        Args:
            idx: Sample index

        Returns:
            If return_quality_scores=False:
                Tuple of (image, labels)
                - image: Tensor of shape (C, H, W)
                - labels: Tensor of shape (6,) with binary labels

            If return_quality_scores=True:
                Tuple of (image, labels, metadata)
                - image: Tensor of shape (C, H, W)
                - labels: Tensor of shape (6,) with binary labels
                - metadata: Dictionary with quality_scores and other info
        """
        sample = self.samples[idx]

        # Load image
        image_path = Path(sample["image_path"])
        image = cv2.imread(str(image_path))

        if image is None:
            msg = f"Failed to load image at index {idx}: {image_path}"
            raise IndexError(msg)

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Load labels
        label_path = Path(sample["label_path"])
        with open(label_path) as f:
            label_data = json.load(f)

        # Extract binary labels in consistent order
        labels = self._extract_labels(label_data)

        # Apply transforms if provided
        if self.transform is not None:
            # Handle albumentations transforms
            is_albumentations = False
            if callable(self.transform):
                if hasattr(self.transform, "__code__"):
                    is_albumentations = "image" in self.transform.__code__.co_varnames
                elif hasattr(self.transform, "__call__") and hasattr(
                    self.transform.__call__, "__code__"
                ):
                    is_albumentations = (
                        "image" in self.transform.__call__.__code__.co_varnames
                    )

            if is_albumentations:
                transformed = self.transform(image=image)
                image = transformed["image"]
            else:
                # Handle torchvision transforms
                image = self.transform(image)

        # Convert image to tensor if not already
        if not isinstance(image, torch.Tensor):
            image = self._to_tensor(image)

        # Convert labels to tensor
        labels_tensor = torch.tensor(labels, dtype=torch.float32)

        if self.return_quality_scores:
            metadata = {
                "quality_scores": label_data.get("quality_scores", {}),
                "image_path": str(image_path),
                "label_source": label_data.get("annotation_source", "unknown"),
            }
            return image, labels_tensor, metadata

        return image, labels_tensor

    def _extract_labels(self, label_data: dict[str, Any]) -> list[int]:
        """Extract binary labels in consistent order.

        Args:
            label_data: Label dictionary (from corrected or weak supervision labels)

        Returns:
            List of 6 binary labels (0 or 1) in QUALITY_ISSUES order
        """
        # Check if this is a corrected label (has "corrected_labels" field)
        if "corrected_labels" in label_data:
            label_dict = label_data["corrected_labels"]
        else:
            # Weak supervision format (has "labels" field with confidence)
            label_dict = {
                issue: label_data["labels"][issue]["value"]
                for issue in QUALITY_ISSUES
                if issue in label_data.get("labels", {})
            }

        # Extract labels in consistent order
        labels = []
        for issue in QUALITY_ISSUES:
            label = label_dict.get(issue, 0)  # Default to 0 if missing
            labels.append(int(label))

        return labels

    def _to_tensor(self, image: NDArray[np.uint8]) -> torch.Tensor:
        """Convert numpy image to PyTorch tensor.

        Args:
            image: Numpy array of shape (H, W, C) with uint8 values [0, 255]

        Returns:
            Tensor of shape (C, H, W) with float32 values [0, 1]
        """
        # Normalize to [0, 1]
        image = image.astype(np.float32) / 255.0

        # Convert HWC to CHW
        image = np.transpose(image, (2, 0, 1))

        # Convert to tensor
        return torch.from_numpy(image)

    def get_label_statistics(self) -> dict[str, Any]:
        """Calculate label distribution statistics.

        Returns:
            Dictionary with label counts and percentages
        """
        label_counts = dict.fromkeys(QUALITY_ISSUES, 0)
        total_samples = len(self.samples)

        for sample in self.samples:
            label_path = Path(sample["label_path"])
            with open(label_path) as f:
                label_data = json.load(f)

            labels = self._extract_labels(label_data)
            for issue, value in zip(QUALITY_ISSUES, labels, strict=False):
                label_counts[issue] += value

        return {
            "total_samples": total_samples,
            "label_counts": label_counts,
            "label_percentages": {
                issue: (count / total_samples) * 100 if total_samples else 0.0
                for issue, count in label_counts.items()
            },
            "average_issues_per_image": (
                sum(label_counts.values()) / total_samples if total_samples else 0.0
            ),
        }


def create_data_loaders(
    data_dir: str | Path,
    batch_size: int = 32,
    num_workers: int = 4,
    train_transform: Any = None,
    val_transform: Any = None,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """Create DataLoaders for train, val, and test splits.

    Args:
        data_dir: Directory containing dataset splits
        batch_size: Batch size for training (default: 32)
        num_workers: Number of worker processes for data loading (default: 4)
        train_transform: Transform for training data (default: None)
        val_transform: Transform for validation/test data (default: None)

    Returns:
        Tuple of (train_loader, val_loader, test_loader)

    Example:
        >>> train_loader, val_loader, test_loader = create_data_loaders(
        ...     "data/final_training_dataset",
        ...     batch_size=32,
        ... )
        >>> for images, labels in train_loader:
        ...     print(images.shape, labels.shape)
        ...     break
    """
    # Create datasets
    train_dataset = IQADataset(data_dir, split="train", transform=train_transform)
    val_dataset = IQADataset(data_dir, split="val", transform=val_transform)
    test_dataset = IQADataset(data_dir, split="test", transform=val_transform)

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,  # Faster GPU transfer
        drop_last=True,  # Drop incomplete batch
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    # Example usage - CLI testing output
    import sys

    if len(sys.argv) < 2:
        print("Usage: python data/dataset.py <data_dir>")  # noqa: T201
        sys.exit(1)

    data_dir = sys.argv[1]

    # Load datasets
    train_dataset = IQADataset(data_dir, split="train")
    val_dataset = IQADataset(data_dir, split="val")
    test_dataset = IQADataset(data_dir, split="test")

    print("\nDataset Statistics:")  # noqa: T201
    print(f"Train: {len(train_dataset)} samples")  # noqa: T201
    print(f"Val: {len(val_dataset)} samples")  # noqa: T201
    print(f"Test: {len(test_dataset)} samples")  # noqa: T201

    # Print label distribution
    print("\nTrain Label Distribution:")  # noqa: T201
    stats = train_dataset.get_label_statistics()
    for issue, percentage in stats["label_percentages"].items():
        count = stats["label_counts"][issue]
        print(f"  {issue}: {count} ({percentage:.1f}%)")  # noqa: T201

    print(f"\nAverage issues per image: {stats['average_issues_per_image']:.2f}")  # noqa: T201

    # Test loading a sample
    print("\nTesting data loading...")  # noqa: T201
    image, labels = train_dataset[0]
    print(f"Image shape: {image.shape}")  # noqa: T201
    print(f"Labels shape: {labels.shape}")  # noqa: T201
    print(f"Labels: {labels}")  # noqa: T201
