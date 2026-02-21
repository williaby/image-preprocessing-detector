"""PyTorch Dataset for IQA Training.

Loads images and quality issue labels for training IQA models.

Supports both binary labels (Phase 2) and continuous labels (Phase 7).

Sprint 3.3.5: Final Training Dataset (Milestone 10.3)
Phase 7: Continuous Labels Support
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
import torch
from numpy.typing import NDArray
from torch.utils.data import DataLoader, Dataset

from image_preprocessing_detector.utils.path_security import validate_safe_path

# Quality issue types (from data/weak_supervision.py)
QUALITY_ISSUES = [
    "noise",
    "blur",
    "skew",
    "perspective",
    "low_contrast",
    "orientation",
]

# Phase 7: Standard continuous label dimensions
CONTINUOUS_DIMENSIONS = [
    "blur_severity",
    "noise_severity",
    "skew_severity",
    "contrast_severity",
    "compression_severity",
]

# Mapping from continuous dimensions to binary issue names
DIMENSION_TO_ISSUE = {
    "blur_severity": "blur",
    "noise_severity": "noise",
    "skew_severity": "skew",
    "contrast_severity": "illumination",
    "compression_severity": "artifacts",
}


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

        # Load image - validate path to prevent directory traversal
        image_path = validate_safe_path(sample["image_path"], must_exist=True)
        image = cv2.imread(str(image_path))

        if image is None:
            msg = f"Failed to load image at index {idx}: {image_path}"
            raise IndexError(msg)

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Load labels - validate path to prevent directory traversal
        label_path = validate_safe_path(sample["label_path"], must_exist=True)
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
                elif hasattr(self.transform.__call__, "__code__"):
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
            label_path = validate_safe_path(sample["label_path"], must_exist=True)
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


# =============================================================================
# Phase 7: Continuous Labels Dataset
# =============================================================================


class ContinuousIQADataset(Dataset):
    """PyTorch Dataset for Continuous IQA Training (Phase 7).

    Loads images with continuous severity labels [0,1] for regression training.
    Supports labels from DocCreator, Augraphy, and MLLM pseudo-labels.

    Args:
        data_dir: Directory containing images and labels
        split: Dataset split ("train", "val", or "test")
        transform: Optional image transforms
        label_type: "continuous" for [0,1] scores, "binary" for backward compat
        return_variance: If True, return label variance for GDBC loss
        binary_threshold: Threshold for converting to binary (default: 0.3)

    Example:
        >>> dataset = ContinuousIQADataset("data/phase7_dataset", split="train")
        >>> image, labels = dataset[0]
        >>> print(labels.shape)  # (5,) - continuous severity for 5 issues
    """

    def __init__(
        self,
        data_dir: str | Path,
        split: str = "train",
        transform: Any = None,
        label_type: Literal["continuous", "binary"] = "continuous",
        return_variance: bool = False,
        binary_threshold: float = 0.3,
    ) -> None:
        """Initialize continuous IQA dataset."""
        self.data_dir = Path(data_dir)
        self.split = split
        self.transform = transform
        self.label_type = label_type
        self.return_variance = return_variance
        self.binary_threshold = binary_threshold

        # Load split metadata
        split_file = self.data_dir / f"{split}_split.json"
        if not split_file.exists():
            msg = f"Split file not found: {split_file}"
            raise FileNotFoundError(msg)

        # Validate path to prevent directory traversal
        split_file = validate_safe_path(split_file, must_exist=True)
        with open(split_file) as f:
            self.split_metadata = json.load(f)

        self.samples = self.split_metadata["samples"]

    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self.samples)

    def __getitem__(
        self, idx: int
    ) -> (
        tuple[torch.Tensor, torch.Tensor]
        | tuple[torch.Tensor, torch.Tensor, torch.Tensor]
    ):
        """Get image and continuous labels for given index.

        Returns:
            If return_variance=False:
                Tuple of (image, labels)
                - image: Tensor of shape (C, H, W)
                - labels: Tensor of shape (5,) with continuous severities [0,1]

            If return_variance=True:
                Tuple of (image, labels, variances)
                - variances: Tensor of shape (5,) for GDBC weighting
        """
        sample = self.samples[idx]

        # Load image - validate path to prevent directory traversal
        image_path = validate_safe_path(sample["image_path"], must_exist=True)
        image = cv2.imread(str(image_path))

        if image is None:
            msg = f"Failed to load image at index {idx}: {image_path}"
            raise IndexError(msg)

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Load labels - validate path to prevent directory traversal
        label_path = validate_safe_path(sample["label_path"], must_exist=True)
        with open(label_path) as f:
            label_data = json.load(f)

        # Extract continuous labels
        labels, variances = self._extract_continuous_labels(label_data)

        # Apply transforms if provided
        if self.transform is not None:
            if hasattr(self.transform, "__call__"):
                # Try albumentations-style
                try:
                    transformed = self.transform(image=image)
                    image = transformed["image"]
                except (TypeError, KeyError):
                    image = self.transform(image)

        # Convert image to tensor if not already
        if not isinstance(image, torch.Tensor):
            image = self._to_tensor(image)

        # Convert labels to tensor
        if self.label_type == "binary":
            # Convert continuous to binary for backward compatibility
            labels = [1 if l >= self.binary_threshold else 0 for l in labels]

        labels_tensor = torch.tensor(labels, dtype=torch.float32)

        if self.return_variance:
            variance_tensor = torch.tensor(variances, dtype=torch.float32)
            return image, labels_tensor, variance_tensor

        return image, labels_tensor

    def _extract_continuous_labels(
        self, label_data: dict[str, Any]
    ) -> tuple[list[float], list[float]]:
        """Extract continuous severity labels.

        Handles multiple label formats:
        - Phase 7 continuous_labels format
        - MLLM pseudo-label format
        - Weak supervision format (with severity in metadata)

        Returns:
            Tuple of (labels, variances) as lists of floats
        """
        # Try each format in priority order
        if "continuous_labels" in label_data:
            return self._extract_phase7_format(label_data)

        if "blur_severity" in label_data:
            return self._extract_mllm_format(label_data)

        if "labels" in label_data:
            return self._extract_weak_supervision_format(label_data)

        if "quality_scores" in label_data:
            return self._extract_quality_scores_format(label_data)

        # Default: zeros
        return [0.0] * len(CONTINUOUS_DIMENSIONS), [0.0] * len(CONTINUOUS_DIMENSIONS)

    def _extract_phase7_format(
        self, label_data: dict[str, Any]
    ) -> tuple[list[float], list[float]]:
        """Extract Phase 7 continuous_labels format."""
        cont = label_data["continuous_labels"]
        variance = float(label_data.get("label_variance", 0.0))

        labels = [float(cont.get(dim, 0.0)) for dim in CONTINUOUS_DIMENSIONS]
        variances = [variance] * len(CONTINUOUS_DIMENSIONS)

        return labels, variances

    def _extract_mllm_format(
        self, label_data: dict[str, Any]
    ) -> tuple[list[float], list[float]]:
        """Extract MLLM/Augraphy direct severity format."""
        variance = float(label_data.get("label_variance", 0.0))

        labels = [float(label_data.get(dim, 0.0)) for dim in CONTINUOUS_DIMENSIONS]
        variances = [variance] * len(CONTINUOUS_DIMENSIONS)

        return labels, variances

    def _extract_weak_supervision_format(
        self, label_data: dict[str, Any]
    ) -> tuple[list[float], list[float]]:
        """Extract weak supervision format with nested labels."""
        labels = []
        nested_labels = label_data["labels"]

        for dim in CONTINUOUS_DIMENSIONS:
            issue_name = DIMENSION_TO_ISSUE.get(dim, dim.replace("_severity", ""))
            severity = self._get_nested_severity(nested_labels, issue_name)
            labels.append(severity)

        variances = [0.0] * len(labels)
        return labels, variances

    def _get_nested_severity(
        self, nested_labels: dict[str, Any], issue_name: str
    ) -> float:
        """Extract severity value from nested label structure."""
        # Direct match
        if issue_name in nested_labels:
            return self._parse_label_entry(nested_labels[issue_name])

        # Illumination -> contrast fallback
        if issue_name == "illumination" and "illumination" in nested_labels:
            return self._parse_label_entry(nested_labels["illumination"])

        return 0.0

    def _parse_label_entry(self, entry: dict | float | int) -> float:
        """Parse label entry to extract severity value."""
        if isinstance(entry, dict):
            return float(entry.get("severity", entry.get("value", 0)))
        return float(entry) * 0.7  # Convert binary to soft label

    def _extract_quality_scores_format(
        self, label_data: dict[str, Any]
    ) -> tuple[list[float], list[float]]:
        """Extract quality_scores format (fallback)."""
        scores = label_data["quality_scores"]
        labels = []

        for dim in CONTINUOUS_DIMENSIONS:
            key = dim.replace("_severity", "")
            val = self._get_quality_score(scores, key)
            labels.append(float(val))

        variances = [0.0] * len(labels)
        return labels, variances

    def _get_quality_score(self, scores: dict[str, Any], key: str) -> float:
        """Get quality score with key name variations."""
        if key == "contrast":
            return scores.get("contrast", scores.get("rms_contrast", 0.0))
        if key == "compression":
            return scores.get("compression", scores.get("blockiness", 0.0) / 10.0)
        return scores.get(key, 0.0)

    def _to_tensor(self, image: NDArray[np.uint8]) -> torch.Tensor:
        """Convert numpy image to PyTorch tensor."""
        image = image.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        return torch.from_numpy(image)

    def get_label_statistics(self) -> dict[str, Any]:
        """Calculate continuous label distribution statistics."""
        all_labels = []

        for sample in self.samples:
            # Validate path to prevent directory traversal
            label_path = validate_safe_path(sample["label_path"], must_exist=True)
            with open(label_path) as f:
                label_data = json.load(f)
            labels, _ = self._extract_continuous_labels(label_data)
            all_labels.append(labels)

        all_labels_np = np.array(all_labels)

        stats = {
            "total_samples": len(self.samples),
            "dimensions": CONTINUOUS_DIMENSIONS,
        }

        for i, dim in enumerate(CONTINUOUS_DIMENSIONS):
            dim_values = all_labels_np[:, i]
            stats[dim] = {
                "mean": float(dim_values.mean()),
                "std": float(dim_values.std()),
                "min": float(dim_values.min()),
                "max": float(dim_values.max()),
                "median": float(np.median(dim_values)),
                "above_threshold": int((dim_values >= self.binary_threshold).sum()),
            }

        return stats


def create_continuous_data_loaders(
    data_dir: str | Path,
    batch_size: int = 32,
    num_workers: int = 4,
    train_transform: Any = None,
    val_transform: Any = None,
    label_type: Literal["continuous", "binary"] = "continuous",
    return_variance: bool = False,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """Create DataLoaders for continuous label training (Phase 7).

    Args:
        data_dir: Directory containing dataset splits
        batch_size: Batch size for training
        num_workers: Number of worker processes
        train_transform: Transform for training data
        val_transform: Transform for validation/test data
        label_type: "continuous" for regression, "binary" for classification
        return_variance: Include variance tensor for GDBC loss

    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    train_dataset = ContinuousIQADataset(
        data_dir,
        split="train",
        transform=train_transform,
        label_type=label_type,
        return_variance=return_variance,
    )
    val_dataset = ContinuousIQADataset(
        data_dir,
        split="val",
        transform=val_transform,
        label_type=label_type,
        return_variance=return_variance,
    )
    test_dataset = ContinuousIQADataset(
        data_dir,
        split="test",
        transform=val_transform,
        label_type=label_type,
        return_variance=return_variance,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
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
        print("Usage: python data/dataset.py <data_dir>")
        sys.exit(1)

    data_dir = sys.argv[1]

    # Load datasets
    train_dataset = IQADataset(data_dir, split="train")
    val_dataset = IQADataset(data_dir, split="val")
    test_dataset = IQADataset(data_dir, split="test")

    print("\nDataset Statistics:")
    print(f"Train: {len(train_dataset)} samples")
    print(f"Val: {len(val_dataset)} samples")
    print(f"Test: {len(test_dataset)} samples")

    # Print label distribution
    print("\nTrain Label Distribution:")
    stats = train_dataset.get_label_statistics()
    for issue, percentage in stats["label_percentages"].items():
        count = stats["label_counts"][issue]
        print(f"  {issue}: {count} ({percentage:.1f}%)")

    print(f"\nAverage issues per image: {stats['average_issues_per_image']:.2f}")

    # Test loading a sample
    print("\nTesting data loading...")
    image, labels = train_dataset[0]
    print(f"Image shape: {image.shape}")
    print(f"Labels shape: {labels.shape}")
    print(f"Labels: {labels}")
