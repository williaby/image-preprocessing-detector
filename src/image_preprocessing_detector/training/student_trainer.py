"""Training loop for ResNet-18 Student Model via Knowledge Distillation.

This module implements the complete training pipeline for the student model:
- Knowledge distillation from frozen teacher model
- Training loop with soft and hard target losses
- Validation loop with metrics computation
- Early stopping based on validation loss
- Model checkpointing (save/load)
- Learning rate scheduling
- Mixed precision training (AMP)
- TensorBoard logging

Usage:
    >>> from image_preprocessing_detector.training import StudentTrainer
    >>> from image_preprocessing_detector.models import (
    ...     ResNetStudent,
    ...     ResNetTeacher,
    ...     DistillationLoss,
    ... )
    >>>
    >>> teacher = ResNetTeacher(num_heads=5)
    >>> teacher.load_state_dict(
    ...     torch.load("teacher_checkpoint.pth")["model_state_dict"]
    ... )
    >>> student = ResNetStudent(num_heads=5)
    >>> loss_fn = DistillationLoss(head_names=student.ISSUE_TYPES, temperature=4.0)
    >>> trainer = StudentTrainer(student, teacher, loss_fn, config)
    >>> trainer.train(train_loader, val_loader)
"""

import logging
import time
from pathlib import Path
from typing import Any, cast

import torch
import torch.nn as nn
import torch.optim as optim
from torch.amp import GradScaler, autocast
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from image_preprocessing_detector.training.checkpoint_utils import (
    cleanup_old_checkpoints,
    load_checkpoint_safe,
)

logger = logging.getLogger(__name__)


class StudentTrainer:
    """Trainer for ResNet-18 Student Model via Knowledge Distillation.

    This class manages the complete distillation training pipeline including:
    - Frozen teacher model for generating soft targets
    - Training and validation loops with distillation loss
    - Checkpointing and early stopping
    - Learning rate scheduling
    - Metrics logging and TensorBoard visualization

    Args:
        student_model: ResNet-18 student model to train
        teacher_model: Frozen ResNet-50 teacher model for soft targets
        loss_fn: DistillationLoss function
        config: Training configuration dictionary
        device: Device to train on (default: auto-detect)

    Attributes:
        student: The student model being trained
        teacher: The frozen teacher model
        loss_fn: Distillation loss function
        optimizer: Adam/AdamW optimizer
        scheduler: Learning rate scheduler
        scaler: Gradient scaler for mixed precision
        best_val_loss: Best validation loss seen
        patience_counter: Counter for early stopping
        epoch: Current epoch number
    """

    def __init__(
        self,
        student_model: nn.Module,
        teacher_model: nn.Module,
        loss_fn: nn.Module,
        config: dict[str, Any],
        device: str | None = None,
    ) -> None:
        self.config = config

        # Device setup
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Student model (trainable)
        self.student = student_model.to(self.device)

        # Teacher model (frozen)
        self.teacher = teacher_model.to(self.device)
        self.teacher.eval()
        for param in self.teacher.parameters():
            param.requires_grad = False

        self.loss_fn = loss_fn.to(self.device)

        # Training configuration
        self.batch_size = config.get("batch_size", 32)
        self.epochs = config.get("epochs", 30)
        self.gradient_clip_norm = config.get("gradient_clip_norm", 1.0)
        self.gradient_accumulation_steps = config.get("gradient_accumulation_steps", 1)

        # Mixed precision training
        self.use_amp = config.get("mixed_precision", {}).get("enabled", True)
        self.scaler = (
            GradScaler("cuda") if self.use_amp and self.device.type == "cuda" else None
        )

        # Optimizer
        optimizer_name = config.get("optimizer", "adamw").lower()
        lr = config.get("learning_rate", 1e-3)
        weight_decay = config.get("weight_decay", 0.01)

        self.optimizer: optim.Optimizer
        if optimizer_name == "adamw":
            self.optimizer = optim.AdamW(
                self.student.parameters(), lr=lr, weight_decay=weight_decay
            )
        elif optimizer_name == "adam":
            self.optimizer = optim.Adam(
                self.student.parameters(), lr=lr, weight_decay=weight_decay
            )
        else:
            raise ValueError(f"Unsupported optimizer: {optimizer_name}")

        # Learning rate scheduler
        scheduler_config = config.get("scheduler", {})
        scheduler_type = scheduler_config.get("type", "cosine")

        self.scheduler: CosineAnnealingLR | ReduceLROnPlateau | None
        if scheduler_type == "cosine":
            self.scheduler = CosineAnnealingLR(
                self.optimizer,
                T_max=self.epochs,
                eta_min=scheduler_config.get("min_lr", 1e-6),
            )
        elif scheduler_type == "reduce_on_plateau":
            self.scheduler = ReduceLROnPlateau(
                self.optimizer,
                mode=scheduler_config.get("mode", "min"),
                factor=scheduler_config.get("factor", 0.5),
                patience=scheduler_config.get("patience", 5),
                min_lr=scheduler_config.get("min_lr", 1e-6),
            )
        else:
            self.scheduler = None

        # Early stopping
        self.early_stopping_patience = config.get("early_stopping_patience", 10)
        self.best_val_loss = float("inf")
        self.patience_counter = 0

        # Checkpointing
        checkpoint_dir = config.get("checkpoint_dir", "checkpoints/student")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.save_interval_epochs = config.get("save_interval_epochs", 5)
        self.keep_last_n = config.get("keep_last_n", 3)

        # Logging
        log_dir = config.get("log_dir", "logs/student")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.writer = SummaryWriter(log_dir=str(self.log_dir))
        self.log_interval = config.get("log_interval", 50)

        # Training state
        self.epoch = 0
        self.global_step = 0
        self.training_history: dict[str, list[float]] = {
            "train_loss": [],
            "val_loss": [],
            "soft_loss": [],
            "hard_loss": [],
            "learning_rate": [],
        }

    def _get_teacher_predictions(self, images: torch.Tensor) -> dict[str, Any]:
        """Get predictions from frozen teacher model.

        Args:
            images: Input batch of images

        Returns:
            Teacher model predictions
        """
        with torch.no_grad():
            if self.use_amp and self.device.type == "cuda":
                with autocast("cuda"):
                    return cast(dict[str, Any], self.teacher(images))
            return cast(dict[str, Any], self.teacher(images))

    def _forward_student_with_loss(
        self,
        images: torch.Tensor,
        targets: dict[str, dict[str, torch.Tensor]],
        teacher_preds: dict[str, Any],
    ) -> tuple[torch.Tensor, dict[str, Any]]:
        """Forward pass through student and compute loss.

        Args:
            images: Input batch of images
            targets: Ground truth targets
            teacher_preds: Teacher model predictions

        Returns:
            Tuple of (scaled_loss, loss_dict)
        """
        if self.use_amp and self.scaler is not None:
            with autocast("cuda"):
                student_preds = self.student(images)
                loss_dict = self.loss_fn(student_preds, teacher_preds, targets)
                loss = loss_dict["total_loss"] / self.gradient_accumulation_steps
        else:
            student_preds = self.student(images)
            loss_dict = self.loss_fn(student_preds, teacher_preds, targets)
            loss = loss_dict["total_loss"] / self.gradient_accumulation_steps
        return loss, loss_dict

    def _optimizer_step(self, batch_idx: int, loss: torch.Tensor) -> None:
        """Perform backward pass and optimizer step with gradient accumulation.

        Args:
            batch_idx: Current batch index
            loss: Scaled loss value
        """
        # Backward pass
        if self.use_amp and self.scaler is not None:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

        # Gradient accumulation and optimization step
        if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
            if self.use_amp and self.scaler is not None:
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.student.parameters(), self.gradient_clip_norm
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(
                    self.student.parameters(), self.gradient_clip_norm
                )
                self.optimizer.step()

            self.optimizer.zero_grad()
            self.global_step += 1

    def train_epoch(self, train_loader: DataLoader) -> dict[str, float]:
        """Train for one epoch using knowledge distillation.

        Args:
            train_loader: DataLoader for training data

        Returns:
            Dictionary containing training metrics
        """
        self.student.train()
        self.teacher.eval()  # Ensure teacher stays in eval mode

        epoch_loss = 0.0
        epoch_soft_loss = 0.0
        epoch_hard_loss = 0.0
        epoch_conf_loss = 0.0
        num_batches = 0

        start_time = time.time()

        # Get issue types from student model
        if not hasattr(self.student, "ISSUE_TYPES"):
            raise AttributeError(
                f"Student model of type {type(self.student).__name__} "
                "does not have required attribute 'ISSUE_TYPES'."
            )
        issue_types = cast(list[str], self.student.ISSUE_TYPES)

        for batch_idx, batch in enumerate(train_loader):
            # Move data to device
            images = batch["image"].to(self.device)
            targets = {
                head_name: {
                    "labels": batch["labels"][head_name].to(self.device),
                    "confidence": batch["confidence"][head_name].to(self.device),
                }
                for head_name in issue_types
            }

            # Get teacher predictions and compute student loss
            teacher_preds = self._get_teacher_predictions(images)
            loss, loss_dict = self._forward_student_with_loss(
                images, targets, teacher_preds
            )

            # Backward pass and optimizer step
            self._optimizer_step(batch_idx, loss)

            # Accumulate losses
            epoch_loss += loss.item() * self.gradient_accumulation_steps
            epoch_soft_loss += loss_dict["soft_loss"].item()
            epoch_hard_loss += loss_dict["hard_loss"].item()
            epoch_conf_loss += loss_dict["confidence_loss"].item()
            num_batches += 1

            # Logging
            if batch_idx % self.log_interval == 0:
                logger.info(
                    f"Epoch {self.epoch} [{batch_idx}/{len(train_loader)}] "
                    f"Loss: {loss.item() * self.gradient_accumulation_steps:.4f} "
                    f"Soft: {loss_dict['soft_loss'].item():.4f} "
                    f"Hard: {loss_dict['hard_loss'].item():.4f}"
                )

                # TensorBoard logging
                self.writer.add_scalar(
                    "train/batch_loss", loss.item(), self.global_step
                )
                self.writer.add_scalar(
                    "train/soft_loss",
                    loss_dict["soft_loss"].item(),
                    self.global_step,
                )
                self.writer.add_scalar(
                    "train/hard_loss",
                    loss_dict["hard_loss"].item(),
                    self.global_step,
                )

        # Compute epoch metrics
        avg_loss = epoch_loss / num_batches
        avg_soft_loss = epoch_soft_loss / num_batches
        avg_hard_loss = epoch_hard_loss / num_batches
        avg_conf_loss = epoch_conf_loss / num_batches
        epoch_time = time.time() - start_time

        return {
            "loss": avg_loss,
            "soft_loss": avg_soft_loss,
            "hard_loss": avg_hard_loss,
            "confidence_loss": avg_conf_loss,
            "time": epoch_time,
        }

    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> dict[str, Any]:
        """Validate the student model.

        Args:
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing validation metrics
        """
        self.student.eval()
        self.teacher.eval()

        val_loss = 0.0
        val_soft_loss = 0.0
        val_hard_loss = 0.0
        val_conf_loss = 0.0
        num_batches = 0

        # Get issue types from student model
        if not hasattr(self.student, "ISSUE_TYPES"):
            raise AttributeError(
                f"Student model of type {type(self.student).__name__} "
                "does not have required attribute 'ISSUE_TYPES'."
            )
        issue_types = cast(list[str], self.student.ISSUE_TYPES)

        # Per-head metrics
        per_head_metrics: dict[str, dict[str, float]] = {
            head: {"soft_loss": 0.0, "hard_loss": 0.0} for head in issue_types
        }

        for batch in val_loader:
            images = batch["image"].to(self.device)
            targets = {
                head_name: {
                    "labels": batch["labels"][head_name].to(self.device),
                    "confidence": batch["confidence"][head_name].to(self.device),
                }
                for head_name in issue_types
            }

            # Get predictions from both models
            if self.use_amp and self.device.type == "cuda":
                with autocast("cuda"):
                    teacher_preds = self.teacher(images)
                    student_preds = self.student(images)
                    loss_dict = self.loss_fn(student_preds, teacher_preds, targets)
            else:
                teacher_preds = self.teacher(images)
                student_preds = self.student(images)
                loss_dict = self.loss_fn(student_preds, teacher_preds, targets)

            # Accumulate losses
            val_loss += loss_dict["total_loss"].item()
            val_soft_loss += loss_dict["soft_loss"].item()
            val_hard_loss += loss_dict["hard_loss"].item()
            val_conf_loss += loss_dict["confidence_loss"].item()
            num_batches += 1

            # Per-head losses
            for head_name, head_losses in loss_dict["per_head_loss"].items():
                per_head_metrics[head_name]["soft_loss"] += head_losses[
                    "soft_loss"
                ].item()
                per_head_metrics[head_name]["hard_loss"] += head_losses[
                    "hard_loss"
                ].item()

        # Compute average metrics
        avg_val_loss = val_loss / num_batches
        avg_soft_loss = val_soft_loss / num_batches
        avg_hard_loss = val_hard_loss / num_batches
        avg_conf_loss = val_conf_loss / num_batches

        # Average per-head metrics
        for head_name in per_head_metrics:
            per_head_metrics[head_name]["soft_loss"] /= num_batches
            per_head_metrics[head_name]["hard_loss"] /= num_batches

        return {
            "loss": avg_val_loss,
            "soft_loss": avg_soft_loss,
            "hard_loss": avg_hard_loss,
            "confidence_loss": avg_conf_loss,
            "per_head_metrics": per_head_metrics,
        }

    def save_checkpoint(
        self, epoch: int, val_loss: float, is_best: bool = False
    ) -> None:
        """Save model checkpoint.

        Args:
            epoch: Current epoch number
            val_loss: Validation loss
            is_best: Whether this is the best model so far
        """
        checkpoint = {
            "epoch": epoch,
            "student_state_dict": self.student.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": (
                self.scheduler.state_dict() if self.scheduler else None
            ),
            "scaler_state_dict": (self.scaler.state_dict() if self.scaler else None),
            "val_loss": val_loss,
            "best_val_loss": self.best_val_loss,
            "config": self.config,
            "training_history": self.training_history,
        }

        # Save regular checkpoint
        checkpoint_path = self.checkpoint_dir / f"student_checkpoint_epoch_{epoch}.pt"
        # nosemgrep: pickles-in-pytorch
        # Security: torch.save is standard for ML checkpoints; we only load our own checkpoints
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"Saved checkpoint: {checkpoint_path}")

        # Save best model
        if is_best:
            best_path = self.checkpoint_dir / "student_best_model.pt"
            # nosemgrep: pickles-in-pytorch
            # Security: torch.save is standard for ML checkpoints; we only load our own checkpoints
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best model: {best_path}")

        # Clean up old checkpoints
        self._cleanup_old_checkpoints()

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints, keeping only the last N."""
        cleanup_old_checkpoints(
            self.checkpoint_dir,
            pattern="student_checkpoint_epoch_*.pt",
            keep_last_n=self.keep_last_n,
        )

    def load_checkpoint(self, checkpoint_path: str | Path) -> None:
        """Load model checkpoint.

        Args:
            checkpoint_path: Path to checkpoint file
        """
        checkpoint = load_checkpoint_safe(checkpoint_path, device=self.device)

        # Restore student model and optimizer state
        self.student.load_state_dict(checkpoint["student_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if self.scheduler and checkpoint["scheduler_state_dict"]:
            self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

        if self.scaler and checkpoint["scaler_state_dict"]:
            self.scaler.load_state_dict(checkpoint["scaler_state_dict"])

        # Restore training state
        self.epoch = checkpoint["epoch"]
        self.best_val_loss = checkpoint["best_val_loss"]
        self.training_history = checkpoint.get("training_history", {})

        logger.info(
            f"Resumed from epoch {self.epoch}, best val loss: {self.best_val_loss:.4f}"
        )

    def _log_per_head_metrics(
        self, per_head_metrics: dict[str, dict[str, float]]
    ) -> None:
        """Log per-head validation metrics.

        Args:
            per_head_metrics: Dictionary of per-head soft/hard losses
        """
        for head_name, metrics in per_head_metrics.items():
            logger.info(
                f"  {head_name}: soft={metrics['soft_loss']:.4f}, "
                f"hard={metrics['hard_loss']:.4f}"
            )

    def _update_scheduler(self, val_loss: float) -> None:
        """Update learning rate scheduler.

        Args:
            val_loss: Validation loss for ReduceLROnPlateau
        """
        if not self.scheduler:
            return
        if isinstance(self.scheduler, ReduceLROnPlateau):
            self.scheduler.step(val_loss)
        else:
            self.scheduler.step()

    def _check_early_stopping(self, val_loss: float) -> bool:
        """Check for improvement and update early stopping state.

        Args:
            val_loss: Current validation loss

        Returns:
            True if this is the best model so far
        """
        is_best = val_loss < self.best_val_loss
        if is_best:
            self.best_val_loss = val_loss
            self.patience_counter = 0
            logger.info(f"New best validation loss: {self.best_val_loss:.4f}")
        else:
            self.patience_counter += 1
            logger.info(
                f"No improvement. Patience: {self.patience_counter}/"
                f"{self.early_stopping_patience}"
            )
        return is_best

    def train(self, train_loader: DataLoader, val_loader: DataLoader) -> dict[str, Any]:
        """Main training loop for knowledge distillation.

        Args:
            train_loader: DataLoader for training data
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing training history and final metrics
        """
        logger.info("Starting student training via knowledge distillation...")
        logger.info(f"Device: {self.device}")
        logger.info(f"Epochs: {self.epochs}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Mixed precision: {self.use_amp}")
        logger.info(f"Temperature: {self.loss_fn.temperature}")
        logger.info(f"Alpha (soft/hard balance): {self.loss_fn.alpha}")

        epochs_run = 0
        for epoch in range(self.epoch, self.epochs):
            self.epoch = epoch
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Epoch {epoch + 1}/{self.epochs}")
            logger.info(f"{'=' * 60}")

            # Train
            train_metrics = self.train_epoch(train_loader)
            logger.info(
                f"Train Loss: {train_metrics['loss']:.4f} "
                f"(Soft: {train_metrics['soft_loss']:.4f}, "
                f"Hard: {train_metrics['hard_loss']:.4f}) "
                f"Time: {train_metrics['time']:.2f}s"
            )

            # Validate
            val_metrics = self.validate(val_loader)
            logger.info(
                f"Val Loss: {val_metrics['loss']:.4f} "
                f"(Soft: {val_metrics['soft_loss']:.4f}, "
                f"Hard: {val_metrics['hard_loss']:.4f})"
            )

            # Log per-head metrics
            self._log_per_head_metrics(val_metrics["per_head_metrics"])

            # Update learning rate
            self._update_scheduler(val_metrics["loss"])

            current_lr = self.optimizer.param_groups[0]["lr"]
            logger.info(f"Learning Rate: {current_lr:.6f}")

            # TensorBoard logging
            self.writer.add_scalar("train/epoch_loss", train_metrics["loss"], epoch)
            self.writer.add_scalar("val/epoch_loss", val_metrics["loss"], epoch)
            self.writer.add_scalar("val/soft_loss", val_metrics["soft_loss"], epoch)
            self.writer.add_scalar("val/hard_loss", val_metrics["hard_loss"], epoch)
            self.writer.add_scalar("train/learning_rate", current_lr, epoch)

            # Update training history
            self.training_history["train_loss"].append(train_metrics["loss"])
            self.training_history["val_loss"].append(val_metrics["loss"])
            self.training_history["soft_loss"].append(val_metrics["soft_loss"])
            self.training_history["hard_loss"].append(val_metrics["hard_loss"])
            self.training_history["learning_rate"].append(current_lr)

            # Early stopping check
            is_best = self._check_early_stopping(val_metrics["loss"])

            # Save checkpoint
            if (epoch + 1) % self.save_interval_epochs == 0 or is_best:
                self.save_checkpoint(epoch, val_metrics["loss"], is_best)

            epochs_run = epoch + 1

            # Early stopping
            if self.patience_counter >= self.early_stopping_patience:
                logger.info(
                    f"Early stopping triggered after {epoch + 1} epochs. "
                    f"Best val loss: {self.best_val_loss:.4f}"
                )
                break

        # Close TensorBoard writer
        self.writer.close()

        logger.info("\nStudent training complete!")
        logger.info(f"Best validation loss: {self.best_val_loss:.4f}")

        return {
            "best_val_loss": self.best_val_loss,
            "total_epochs": epochs_run,
            "training_history": self.training_history,
        }
