"""Generate and save teacher soft labels for student training.

This module runs teacher model inference on the training dataset and saves
the resulting soft labels (logits) to disk. This avoids recomputing teacher
predictions during student training, significantly reducing training time.

The soft labels are saved in PyTorch tensor format (.pt) for efficient loading.

Usage:
    >>> from generate_soft_labels import SoftLabelGenerator
    >>> generator = SoftLabelGenerator(teacher_model, device="cuda")
    >>> soft_labels = generator.generate(train_loader)
    >>> generator.save(soft_labels, output_path="soft_labels.pt")

Storage Format:
    - Dictionary mapping sample IDs to teacher logits
    - Structure: {sample_id: tensor(num_classes)}
    - File format: PyTorch tensor (.pt)
    - Typical size: ~50MB for standard training set
"""

# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class SoftLabelGenerator:
    """Generator for creating teacher soft labels.

    This class runs teacher model inference on a dataset and saves
    the resulting logits for use in knowledge distillation training.

    Attributes:
        teacher_model: Pre-trained teacher model
        device: Device for inference ('cuda' or 'cpu')
        batch_size: Batch size for inference
    """

    def __init__(
        self,
        teacher_model: nn.Module,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Initialize the soft label generator.

        Args:
            teacher_model: Pre-trained teacher model
            device: Device for inference (default: auto-detect)
            batch_size: Batch size for inference (default: use DataLoader batch size)
        """
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.teacher_model = teacher_model.to(self.device)
        self.teacher_model.eval()
        self.batch_size = batch_size

        # Freeze teacher model
        for param in self.teacher_model.parameters():
            param.requires_grad = False

        logger.info(
            "SoftLabelGenerator initialized",
            device=str(self.device),
            batch_size=batch_size,
        )

    def _extract_images_from_batch(
        self, batch: list | tuple | torch.Tensor
    ) -> torch.Tensor:
        """Extract images tensor from a batch."""
        if isinstance(batch, list | tuple) and len(batch) == 2:
            images, _ = batch
        else:
            images = batch

        if not isinstance(images, torch.Tensor):
            images = torch.stack(images)  # pyright: ignore[reportUnknownArgumentType]

        return images.to(self.device)  # pyright: ignore[reportAttributeAccessIssue]

    def _get_teacher_logits(self, teacher_outputs: dict | torch.Tensor) -> torch.Tensor:
        """Extract logits from teacher model output."""
        if isinstance(teacher_outputs, dict):
            logits: torch.Tensor = teacher_outputs["all"]
            return logits
        return teacher_outputs

    def generate(
        self,
        data_loader: DataLoader,
        show_progress: bool = True,
    ) -> dict[int, torch.Tensor]:
        """Generate soft labels for a dataset.

        Args:
            data_loader: DataLoader for the dataset
            show_progress: Whether to show progress bar

        Returns:
            Dictionary mapping sample indices to teacher logits
            {sample_id: tensor(num_classes)}
        """
        soft_labels: dict[int, torch.Tensor] = {}
        sample_id = 0

        dataset = data_loader.dataset
        total = len(dataset) if hasattr(dataset, "__len__") else 0
        logger.info("Generating soft labels", total_samples=total)

        # Create progress bar if requested
        iterator = (
            tqdm(data_loader, desc="Generating soft labels")
            if show_progress
            else data_loader
        )

        with torch.no_grad():
            for batch_idx, batch in enumerate(iterator):
                # Extract and process images
                images = self._extract_images_from_batch(batch)
                batch_size = images.size(0)

                # Get teacher predictions and extract logits
                teacher_outputs = self.teacher_model(images)
                teacher_logits = self._get_teacher_logits(teacher_outputs)
                teacher_logits_cpu = teacher_logits.cpu()

                # Store each sample's logits
                for i in range(batch_size):
                    soft_labels[sample_id] = teacher_logits_cpu[i]
                    sample_id += 1

                # Log progress periodically
                if (batch_idx + 1) % 100 == 0:
                    logger.debug(
                        "Soft label generation progress",
                        batch=batch_idx + 1,
                        total_batches=len(data_loader),
                        samples_processed=sample_id,
                    )

        logger.info("Soft label generation complete", total_samples=sample_id)

        return soft_labels

    def save(
        self,
        soft_labels: dict[int, torch.Tensor],
        output_path: Path | str,
    ) -> None:
        """Save soft labels to disk.

        Args:
            soft_labels: Dictionary of soft labels
            output_path: Path to save file (.pt format)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Verify soft labels
        self._verify_soft_labels(soft_labels)

        # Save to disk
        # nosemgrep: pickles-in-pytorch
        # Security: torch.save is standard for ML soft labels; we only load our own data
        torch.save(soft_labels, output_path)

        # Log file size
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        logger.info(
            "Soft labels saved",
            path=str(output_path),
            num_samples=len(soft_labels),
            file_size_mb=f"{file_size_mb:.2f} MB",
        )

    def load(self, input_path: Path | str) -> dict[int, torch.Tensor]:
        """Load soft labels from disk.

        Args:
            input_path: Path to soft labels file (.pt format)

        Returns:
            Dictionary of soft labels
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Soft labels file not found: {input_path}")

        logger.info("Loading soft labels", path=str(input_path))

        # Security: Use weights_only=True to prevent arbitrary code execution
        # Only loads tensors, dicts, lists, and primitive types
        soft_labels: dict[int, torch.Tensor] = torch.load(input_path, weights_only=True)

        # Verify loaded soft labels
        self._verify_soft_labels(soft_labels)

        logger.info("Soft labels loaded", num_samples=len(soft_labels))

        return soft_labels

    def _verify_soft_labels(self, soft_labels: dict[int, torch.Tensor]) -> None:
        """Verify soft labels integrity.

        Args:
            soft_labels: Dictionary of soft labels to verify

        Raises:
            ValueError: If soft labels contain invalid data
        """
        if not soft_labels:
            raise ValueError("Soft labels dictionary is empty")

        # Check first sample for shape and validity
        first_id = next(iter(soft_labels))
        first_logits = soft_labels[first_id]

        # Check for NaNs or Infs
        if torch.isnan(first_logits).any():
            raise ValueError("Soft labels contain NaN values")
        if torch.isinf(first_logits).any():
            raise ValueError("Soft labels contain Inf values")

        # Check shape consistency
        expected_shape = first_logits.shape
        for sample_id, logits in soft_labels.items():
            if logits.shape != expected_shape:
                raise ValueError(
                    f"Inconsistent soft label shapes: sample {sample_id} has "
                    f"shape {logits.shape}, expected {expected_shape}"
                )

            # Check for NaNs/Infs
            if torch.isnan(logits).any() or torch.isinf(logits).any():
                raise ValueError(f"Sample {sample_id} contains NaN or Inf values")

        logger.debug(
            "Soft labels verified",
            num_samples=len(soft_labels),
            logit_shape=tuple(expected_shape),
        )


def generate_and_save_soft_labels(
    teacher_model: nn.Module,
    data_loader: DataLoader,
    output_path: Path | str,
    device: str | None = None,
    show_progress: bool = True,
) -> dict[int, torch.Tensor]:
    """Generate and save teacher soft labels in one call.

    This is a convenience function that creates a SoftLabelGenerator,
    generates soft labels, and saves them to disk.

    Args:
        teacher_model: Pre-trained teacher model
        data_loader: DataLoader for the dataset
        output_path: Path to save soft labels
        device: Device for inference (default: auto-detect)
        show_progress: Whether to show progress bar

    Returns:
        Dictionary of soft labels

    Example:
        >>> soft_labels = generate_and_save_soft_labels(
        ...     teacher_model, train_loader, "soft_labels/train_soft_labels.pt"
        ... )
    """
    generator = SoftLabelGenerator(teacher_model, device=device)
    soft_labels = generator.generate(data_loader, show_progress=show_progress)
    generator.save(soft_labels, output_path)
    return soft_labels


def load_soft_labels(input_path: Path | str) -> dict[int, torch.Tensor]:
    """Load soft labels from disk.

    This is a convenience function for loading soft labels without
    creating a SoftLabelGenerator instance.

    Args:
        input_path: Path to soft labels file

    Returns:
        Dictionary of soft labels

    Example:
        >>> soft_labels = load_soft_labels("soft_labels/train_soft_labels.pt")
    """
    # Create temporary generator just for loading
    # We use a dummy model since we only need the load functionality
    generator = SoftLabelGenerator(nn.Identity())
    return generator.load(input_path)
