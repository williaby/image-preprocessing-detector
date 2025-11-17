"""Training loop for ResNet-50 Teacher Model.

This module implements the complete training pipeline for the teacher model:
- Training loop with batching and gradient accumulation
- Validation loop with metrics computation
- Early stopping based on validation loss
- Model checkpointing (save/load)
- Learning rate scheduling
- Gradient clipping
- Mixed precision training (AMP)
- TensorBoard logging

Usage:
    >>> from image_preprocessing_detector.training import TeacherTrainer
    >>> from image_preprocessing_detector.models import ResNetTeacher, MultiHeadIQALoss
    >>>
    >>> model = ResNetTeacher(num_heads=5, dropout=0.2)
    >>> loss_fn = MultiHeadIQALoss(head_names=model.ISSUE_TYPES)
    >>> trainer = TeacherTrainer(model, loss_fn, config)
    >>> trainer.train(train_loader, val_loader)
"""

import logging
import time
from pathlib import Path
from typing import Any, cast

import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

logger = logging.getLogger(__name__)


class TeacherTrainer:
    """Trainer for ResNet-50 Teacher Model.

    This class manages the complete training pipeline including:
    - Training and validation loops
    - Checkpointing and early stopping
    - Learning rate scheduling
    - Metrics logging and TensorBoard visualization

    Args:
        model: ResNet teacher model
        loss_fn: Loss function (MultiHeadIQALoss)
        config: Training configuration dictionary
        device: Device to train on (default: auto-detect)

    Attributes:
        model: The model being trained
        loss_fn: Loss function
        optimizer: Adam/AdamW optimizer
        scheduler: Learning rate scheduler
        scaler: Gradient scaler for mixed precision
        best_val_loss: Best validation loss seen
        patience_counter: Counter for early stopping
        epoch: Current epoch number
    """

    def __init__(
        self,
        model: nn.Module,
        loss_fn: nn.Module,
        config: dict[str, Any],
        device: str | None = None,
    ) -> None:
        self.config = config
        self.model = model

        # Device setup
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = self.model.to(self.device)
        self.loss_fn = loss_fn.to(self.device)

        # Training configuration
        self.batch_size = config.get("batch_size", 32)
        self.epochs = config.get("epochs", 50)
        self.gradient_clip_norm = config.get("gradient_clip_norm", 1.0)
        self.gradient_accumulation_steps = config.get("gradient_accumulation_steps", 1)

        # Mixed precision training
        self.use_amp = config.get("mixed_precision", {}).get("enabled", True)
        self.scaler = GradScaler() if self.use_amp else None

        # Optimizer
        optimizer_name = config.get("optimizer", "adamw").lower()
        lr = config.get("learning_rate", 1e-3)
        weight_decay = config.get("weight_decay", 0.01)

        self.optimizer: optim.Optimizer
        if optimizer_name == "adamw":
            self.optimizer = optim.AdamW(
                self.model.parameters(), lr=lr, weight_decay=weight_decay
            )
        elif optimizer_name == "adam":
            self.optimizer = optim.Adam(
                self.model.parameters(), lr=lr, weight_decay=weight_decay
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
                eta_min=scheduler_config.get("min_lr", 1e-5),
            )
        elif scheduler_type == "reduce_on_plateau":
            self.scheduler = ReduceLROnPlateau(
                self.optimizer,
                mode=scheduler_config.get("mode", "min"),
                factor=scheduler_config.get("factor", 0.5),
                patience=scheduler_config.get("patience", 5),
                min_lr=scheduler_config.get("min_lr", 1e-5),
            )
        else:
            self.scheduler = None

        # Early stopping
        self.early_stopping_patience = config.get("early_stopping_patience", 10)
        self.best_val_loss = float("inf")
        self.patience_counter = 0

        # Checkpointing
        checkpoint_dir = config.get("checkpoint_dir", "checkpoints")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.save_interval_epochs = config.get("save_interval_epochs", 5)
        self.keep_last_n = config.get("keep_last_n", 3)

        # Logging
        log_dir = config.get("log_dir", "logs")
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
            "learning_rate": [],
        }

    def train_epoch(self, train_loader: DataLoader) -> dict[str, float]:
        """Train for one epoch.

        Args:
            train_loader: DataLoader for training data

        Returns:
            Dictionary containing training metrics
        """
        self.model.train()
        epoch_loss = 0.0
        epoch_cls_loss = 0.0
        epoch_conf_loss = 0.0
        num_batches = 0

        start_time = time.time()

        # Get issue types from model (type-safe access with validation)
        if not hasattr(self.model, "ISSUE_TYPES"):
            raise AttributeError(
                f"Model of type {type(self.model).__name__} does not have required attribute 'ISSUE_TYPES'."
            )
        issue_types = cast(list[str], self.model.ISSUE_TYPES)

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

            # Forward pass with mixed precision
            if self.use_amp and self.scaler is not None:
                with autocast():
                    predictions = self.model(images)
                    loss_dict = self.loss_fn(predictions, targets)
                    loss = loss_dict["total_loss"]
                    loss = loss / self.gradient_accumulation_steps
            else:
                predictions = self.model(images)
                loss_dict = self.loss_fn(predictions, targets)
                loss = loss_dict["total_loss"]
                loss = loss / self.gradient_accumulation_steps

            # Backward pass
            if self.use_amp and self.scaler is not None:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()

            # Gradient accumulation and optimization step
            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                # Gradient clipping
                if self.use_amp and self.scaler is not None:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), self.gradient_clip_norm
                    )
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), self.gradient_clip_norm
                    )
                    self.optimizer.step()

                self.optimizer.zero_grad()
                self.global_step += 1

            # Accumulate losses
            epoch_loss += loss.item() * self.gradient_accumulation_steps
            epoch_cls_loss += loss_dict["classification_loss"].item()
            epoch_conf_loss += loss_dict["confidence_loss"].item()
            num_batches += 1

            # Logging
            if batch_idx % self.log_interval == 0:
                logger.info(
                    f"Epoch {self.epoch} [{batch_idx}/{len(train_loader)}] "
                    f"Loss: {loss.item() * self.gradient_accumulation_steps:.4f} "
                    f"Cls: {loss_dict['classification_loss'].item():.4f} "
                    f"Conf: {loss_dict['confidence_loss'].item():.4f}"
                )

                # TensorBoard logging
                self.writer.add_scalar(
                    "train/batch_loss", loss.item(), self.global_step
                )
                self.writer.add_scalar(
                    "train/classification_loss",
                    loss_dict["classification_loss"].item(),
                    self.global_step,
                )
                self.writer.add_scalar(
                    "train/confidence_loss",
                    loss_dict["confidence_loss"].item(),
                    self.global_step,
                )

        # Compute epoch metrics
        avg_loss = epoch_loss / num_batches
        avg_cls_loss = epoch_cls_loss / num_batches
        avg_conf_loss = epoch_conf_loss / num_batches
        epoch_time = time.time() - start_time

        return {
            "loss": avg_loss,
            "classification_loss": avg_cls_loss,
            "confidence_loss": avg_conf_loss,
            "time": epoch_time,
        }

    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> dict[str, Any]:
        """Validate the model.

        Args:
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing validation metrics
        """
        self.model.eval()
        val_loss = 0.0
        val_cls_loss = 0.0
        val_conf_loss = 0.0
        num_batches = 0

        # Get issue types from model (type-safe access)
        issue_types = getattr(self.model, "ISSUE_TYPES", [])

        # Per-head metrics
        per_head_metrics: dict[str, dict[str, float]] = {
            head: {"loss": 0.0} for head in issue_types
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

            # Forward pass
            if self.use_amp:
                with autocast():
                    predictions = self.model(images)
                    loss_dict = self.loss_fn(predictions, targets)
            else:
                predictions = self.model(images)
                loss_dict = self.loss_fn(predictions, targets)

            # Accumulate losses
            val_loss += loss_dict["total_loss"].item()
            val_cls_loss += loss_dict["classification_loss"].item()
            val_conf_loss += loss_dict["confidence_loss"].item()
            num_batches += 1

            # Per-head losses
            for head_name, head_loss in loss_dict["per_head_loss"].items():
                per_head_metrics[head_name]["loss"] += head_loss.item()

        # Compute average metrics
        avg_val_loss = val_loss / num_batches
        avg_cls_loss = val_cls_loss / num_batches
        avg_conf_loss = val_conf_loss / num_batches

        # Average per-head metrics
        for head_name in per_head_metrics:
            per_head_metrics[head_name]["loss"] /= num_batches

        return {
            "loss": avg_val_loss,
            "classification_loss": avg_cls_loss,
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
            "model_state_dict": self.model.state_dict(),
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
        checkpoint_path = self.checkpoint_dir / f"checkpoint_epoch_{epoch}.pt"
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"Saved checkpoint: {checkpoint_path}")

        # Save best model
        if is_best:
            best_path = self.checkpoint_dir / "best_model.pt"
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best model: {best_path}")

        # Clean up old checkpoints (keep only last N)
        self._cleanup_old_checkpoints()

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints, keeping only the last N."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_epoch_*.pt"),
            key=lambda p: p.stat().st_mtime,
        )

        # Keep only the last N checkpoints
        if len(checkpoints) > self.keep_last_n:
            for checkpoint in checkpoints[: -self.keep_last_n]:
                checkpoint.unlink()
                logger.debug(f"Removed old checkpoint: {checkpoint}")

    def load_checkpoint(self, checkpoint_path: str | Path) -> None:
        """Load model checkpoint.

        Args:
            checkpoint_path: Path to checkpoint file
        """
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        logger.info(f"Loading checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=self.device)

        # Restore model and optimizer state
        self.model.load_state_dict(checkpoint["model_state_dict"])
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

    def train(self, train_loader: DataLoader, val_loader: DataLoader) -> dict[str, Any]:
        """Main training loop.

        Args:
            train_loader: DataLoader for training data
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing training history and final metrics
        """
        logger.info("Starting training...")
        logger.info(f"Device: {self.device}")
        logger.info(f"Epochs: {self.epochs}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Mixed precision: {self.use_amp}")

        for epoch in range(self.epoch, self.epochs):
            self.epoch = epoch
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Epoch {epoch + 1}/{self.epochs}")
            logger.info(f"{'=' * 60}")

            # Train
            train_metrics = self.train_epoch(train_loader)
            logger.info(
                f"Train Loss: {train_metrics['loss']:.4f} "
                f"(Cls: {train_metrics['classification_loss']:.4f}, "
                f"Conf: {train_metrics['confidence_loss']:.4f}) "
                f"Time: {train_metrics['time']:.2f}s"
            )

            # Validate
            val_metrics = self.validate(val_loader)
            logger.info(
                f"Val Loss: {val_metrics['loss']:.4f} "
                f"(Cls: {val_metrics['classification_loss']:.4f}, "
                f"Conf: {val_metrics['confidence_loss']:.4f})"
            )

            # Log per-head metrics
            for head_name, metrics in val_metrics["per_head_metrics"].items():
                logger.info(f"  {head_name}: {metrics['loss']:.4f}")

            # Update learning rate
            if self.scheduler:
                if isinstance(self.scheduler, ReduceLROnPlateau):
                    self.scheduler.step(val_metrics["loss"])
                else:
                    self.scheduler.step()

            current_lr = self.optimizer.param_groups[0]["lr"]
            logger.info(f"Learning Rate: {current_lr:.6f}")

            # TensorBoard logging
            self.writer.add_scalar("train/epoch_loss", train_metrics["loss"], epoch)
            self.writer.add_scalar("val/epoch_loss", val_metrics["loss"], epoch)
            self.writer.add_scalar("train/learning_rate", current_lr, epoch)

            # Update training history
            self.training_history["train_loss"].append(train_metrics["loss"])
            self.training_history["val_loss"].append(val_metrics["loss"])
            self.training_history["learning_rate"].append(current_lr)

            # Early stopping check
            is_best = val_metrics["loss"] < self.best_val_loss
            if is_best:
                self.best_val_loss = val_metrics["loss"]
                self.patience_counter = 0
                logger.info(f"New best validation loss: {self.best_val_loss:.4f}")
            else:
                self.patience_counter += 1
                logger.info(
                    f"No improvement. Patience: {self.patience_counter}/"
                    f"{self.early_stopping_patience}"
                )

            # Save checkpoint
            if (epoch + 1) % self.save_interval_epochs == 0 or is_best:
                self.save_checkpoint(epoch, val_metrics["loss"], is_best)

            # Early stopping
            if self.patience_counter >= self.early_stopping_patience:
                logger.info(
                    f"Early stopping triggered after {epoch + 1} epochs. "
                    f"Best val loss: {self.best_val_loss:.4f}"
                )
                break

        # Close TensorBoard writer
        self.writer.close()

        logger.info("\nTraining complete!")
        logger.info(f"Best validation loss: {self.best_val_loss:.4f}")

        return {
            "best_val_loss": self.best_val_loss,
            "total_epochs": epoch + 1,
            "training_history": self.training_history,
        }
