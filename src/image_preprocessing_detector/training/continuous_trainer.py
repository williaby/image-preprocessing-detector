# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Training loop for Phase 7 Continuous Label Models.

This module implements the training pipeline for models trained on
continuous severity labels [0, 1] instead of binary labels:

- ContinuousTeacherTrainer: Trains ResNet-50 teacher with BCE+MSE loss
- Supports GDBC variance weighting for multi-source labels
- Integrates ECE calibration metrics during validation
- Early stopping based on ECE (not just validation loss)

Usage:
    >>> from image_preprocessing_detector.training import ContinuousTeacherTrainer
    >>> from image_preprocessing_detector.models import (
    ...     ResNetTeacher,
    ...     ContinuousBCEMSELoss,
    ... )
    >>>
    >>> model = ResNetTeacher(num_heads=5)
    >>> loss_fn = ContinuousBCEMSELoss(alpha=0.6, beta=0.4)
    >>> trainer = ContinuousTeacherTrainer(model, loss_fn, config)
    >>> trainer.train(train_loader, val_loader)

Reference:
    Phase 7 Strategy: docs/planning/PROJECT_PLAN.md (Sprint 7.2.2)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from image_preprocessing_detector.metrics.calibration import (
    compute_multiclass_ece,
    compute_severity_metrics,
)
from image_preprocessing_detector.training.checkpoint_utils import (
    cleanup_old_checkpoints,
    load_checkpoint_safe,
)

logger = logging.getLogger(__name__)

# Standard severity dimensions for Phase 7
SEVERITY_DIMENSIONS = [
    "blur_severity",
    "noise_severity",
    "skew_severity",
    "contrast_severity",
    "compression_severity",
]


class ContinuousTeacherTrainer:
    """Trainer for ResNet-50 Teacher Model with Continuous Labels.

    This trainer extends the binary classification paradigm to support
    continuous severity regression while maintaining backward compatibility.

    Key differences from TeacherTrainer:
    1. Uses ContinuousBCEMSELoss instead of pure BCE
    2. Tracks severity MAE and ECE metrics
    3. Supports GDBC variance weighting
    4. Early stopping can be based on ECE (calibration)

    Args:
        model: ResNet teacher model with multi-head output
        loss_fn: Loss function (ContinuousBCEMSELoss or GDBCLoss)
        config: Training configuration dictionary
        device: Device to train on (default: auto-detect)

    Attributes:
        model: The model being trained
        loss_fn: Loss function
        optimizer: Adam/AdamW optimizer
        scheduler: Learning rate scheduler
        scaler: Gradient scaler for mixed precision
        best_val_loss: Best validation loss seen
        best_ece: Best Expected Calibration Error seen
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
        self.loss_fn = loss_fn

        # Training configuration
        self.batch_size = config.get("batch_size", 32)
        self.epochs = config.get("epochs", 50)
        self.gradient_clip_norm = config.get("gradient_clip_norm", 1.0)
        self.gradient_accumulation_steps = config.get("gradient_accumulation_steps", 1)

        # Phase 7: ECE-based early stopping
        self.use_ece_early_stopping = config.get("use_ece_early_stopping", True)
        self.target_ece = config.get("target_ece", 0.10)  # Phase 7 target

        # Mixed precision training
        self.use_amp = config.get("mixed_precision", {}).get("enabled", True)
        self.scaler = GradScaler() if self.use_amp else None

        # Optimizer
        optimizer_name = config.get("optimizer", "adamw").lower()
        lr = config.get("learning_rate", 1e-4)
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
        self.best_ece = float("inf")
        self.patience_counter = 0

        # Checkpointing
        checkpoint_dir = config.get("checkpoint_dir", "checkpoints/phase7")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.save_interval_epochs = config.get("save_interval_epochs", 5)
        self.keep_last_n = config.get("keep_last_n", 3)

        # Logging
        log_dir = config.get("log_dir", "logs/phase7")
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
            "val_ece": [],
            "severity_mae": [],
            "learning_rate": [],
        }

    def _forward_with_loss(
        self,
        images: torch.Tensor,
        targets: torch.Tensor,
        variances: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, Any]]:
        """Forward pass through model and compute loss.

        Args:
            images: Input batch of images (B, C, H, W)
            targets: Continuous severity targets (B, num_classes)
            variances: Optional label variances for GDBC (B, num_classes)

        Returns:
            Tuple of (scaled_loss, loss_dict)
        """
        if self.use_amp and self.scaler is not None:
            with autocast(device_type="cuda"):
                predictions = self.model(images)

                # Handle multi-head output format
                if isinstance(predictions, dict):
                    # Convert dict of heads to tensor
                    pred_tensor = self._dict_to_tensor(predictions)
                else:
                    pred_tensor = predictions

                # Compute loss
                if variances is not None and hasattr(self.loss_fn, "forward"):
                    # GDBC loss with variance
                    loss_dict = self.loss_fn(pred_tensor, targets, variances)
                else:
                    loss_dict = self.loss_fn(pred_tensor, targets)

                loss = loss_dict["total_loss"] / self.gradient_accumulation_steps
        else:
            predictions = self.model(images)

            if isinstance(predictions, dict):
                pred_tensor = self._dict_to_tensor(predictions)
            else:
                pred_tensor = predictions

            if variances is not None:
                loss_dict = self.loss_fn(pred_tensor, targets, variances)
            else:
                loss_dict = self.loss_fn(pred_tensor, targets)

            loss = loss_dict["total_loss"] / self.gradient_accumulation_steps

        return loss, loss_dict

    def _dict_to_tensor(self, predictions: dict[str, Any]) -> torch.Tensor:
        """Convert multi-head dict predictions to tensor.

        Args:
            predictions: Dict mapping head names to prediction dicts

        Returns:
            Tensor of shape (batch_size, num_heads)
        """
        # Assume predictions have format {head_name: {"logits": tensor}}
        head_names = list(predictions.keys())
        logits_list = []

        for head_name in sorted(head_names):
            head_pred = predictions[head_name]
            if isinstance(head_pred, dict):
                logits = head_pred.get("logits", head_pred.get("output"))
                if logits is None:
                    raise ValueError(
                        f"Missing logits/output in predictions for head '{head_name}'"
                    )
            else:
                logits = head_pred
            logits_list.append(logits.squeeze(-1))

        return torch.stack(logits_list, dim=1)

    def _optimizer_step(self, batch_idx: int, loss: torch.Tensor) -> None:
        """Perform backward pass and optimizer step.

        Args:
            batch_idx: Current batch index
            loss: Scaled loss value
        """
        if self.use_amp and self.scaler is not None:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

        if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
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

    def train_epoch(self, train_loader: DataLoader) -> dict[str, float]:
        """Train for one epoch with continuous labels.

        Args:
            train_loader: DataLoader yielding (images, labels) or
                         (images, labels, variances) tuples

        Returns:
            Dictionary containing training metrics
        """
        self.model.train()
        epoch_loss = 0.0
        epoch_bce_loss = 0.0
        epoch_mse_loss = 0.0
        epoch_severity_mae = 0.0
        num_batches = 0

        start_time = time.time()

        for batch_idx, batch in enumerate(train_loader):
            # Handle different batch formats
            if len(batch) == 3:
                images, targets, variances = batch
                variances = variances.to(self.device)
            else:
                images, targets = batch
                variances = None

            images = images.to(self.device)
            targets = targets.to(self.device)

            # Forward pass and compute loss
            loss, loss_dict = self._forward_with_loss(images, targets, variances)

            # Backward pass and optimizer step
            self._optimizer_step(batch_idx, loss)

            # Accumulate losses
            epoch_loss += loss.item() * self.gradient_accumulation_steps
            epoch_bce_loss += loss_dict.get("bce_loss", torch.tensor(0.0)).item()
            epoch_mse_loss += loss_dict.get("mse_loss", torch.tensor(0.0)).item()
            epoch_severity_mae += loss_dict.get(
                "severity_mae", torch.tensor(0.0)
            ).item()
            num_batches += 1

            # Logging
            if batch_idx % self.log_interval == 0:
                logger.info(
                    f"Epoch {self.epoch} [{batch_idx}/{len(train_loader)}] "
                    f"Loss: {loss.item() * self.gradient_accumulation_steps:.4f} "
                    f"BCE: {loss_dict.get('bce_loss', 0):.4f} "
                    f"MSE: {loss_dict.get('mse_loss', 0):.4f} "
                    f"MAE: {loss_dict.get('severity_mae', 0):.4f}"
                )

                self.writer.add_scalar(
                    "train/batch_loss", loss.item(), self.global_step
                )

        # Compute epoch metrics
        avg_loss = epoch_loss / num_batches if num_batches > 0 else 0.0
        avg_bce = epoch_bce_loss / num_batches if num_batches > 0 else 0.0
        avg_mse = epoch_mse_loss / num_batches if num_batches > 0 else 0.0
        avg_mae = epoch_severity_mae / num_batches if num_batches > 0 else 0.0
        epoch_time = time.time() - start_time

        return {
            "loss": avg_loss,
            "bce_loss": avg_bce,
            "mse_loss": avg_mse,
            "severity_mae": avg_mae,
            "time": epoch_time,
        }

    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> dict[str, Any]:
        """Validate the model with calibration metrics.

        Args:
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing validation metrics including ECE
        """
        self.model.eval()
        val_loss = 0.0
        val_bce_loss = 0.0
        val_mse_loss = 0.0
        num_batches = 0

        all_predictions: list[np.ndarray] = []
        all_targets: list[np.ndarray] = []

        for batch in val_loader:
            if len(batch) == 3:
                images, targets, _variances = batch  # Variances not used in validation
            else:
                images, targets = batch

            images = images.to(self.device)
            targets = targets.to(self.device)

            # Forward pass
            if self.use_amp:
                with autocast(device_type="cuda"):
                    predictions = self.model(images)
                    if isinstance(predictions, dict):
                        pred_tensor = self._dict_to_tensor(predictions)
                    else:
                        pred_tensor = predictions
                    loss_dict = self.loss_fn(pred_tensor, targets)
            else:
                predictions = self.model(images)
                if isinstance(predictions, dict):
                    pred_tensor = self._dict_to_tensor(predictions)
                else:
                    pred_tensor = predictions
                loss_dict = self.loss_fn(pred_tensor, targets)

            # Accumulate losses
            val_loss += loss_dict["total_loss"].item()
            val_bce_loss += loss_dict.get("bce_loss", torch.tensor(0.0)).item()
            val_mse_loss += loss_dict.get("mse_loss", torch.tensor(0.0)).item()
            num_batches += 1

            # Collect predictions for ECE computation
            pred_probs = torch.sigmoid(pred_tensor).cpu().numpy()
            target_np = targets.cpu().numpy()
            all_predictions.append(pred_probs)
            all_targets.append(target_np)

        # Compute average metrics
        avg_val_loss = val_loss / num_batches if num_batches > 0 else 0.0
        avg_bce = val_bce_loss / num_batches if num_batches > 0 else 0.0
        avg_mse = val_mse_loss / num_batches if num_batches > 0 else 0.0

        # Compute ECE and severity metrics
        all_preds = np.concatenate(all_predictions, axis=0)
        all_tgts = np.concatenate(all_targets, axis=0)

        ece_result = compute_multiclass_ece(
            all_preds, all_tgts, class_names=SEVERITY_DIMENSIONS[: all_preds.shape[1]]
        )
        severity_metrics = compute_severity_metrics(all_preds, all_tgts)

        return {
            "loss": avg_val_loss,
            "bce_loss": avg_bce,
            "mse_loss": avg_mse,
            "ece": ece_result.ece,
            "mce": ece_result.mce,
            "per_class_ece": ece_result.per_class_ece,
            "severity_mae": severity_metrics["severity_mae"],
            "severity_correlation": severity_metrics["severity_correlation"],
        }

    def save_checkpoint(
        self, epoch: int, val_loss: float, ece: float, is_best: bool = False
    ) -> None:
        """Save model checkpoint.

        Args:
            epoch: Current epoch number
            val_loss: Validation loss
            ece: Expected Calibration Error
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
            "ece": ece,
            "best_val_loss": self.best_val_loss,
            "best_ece": self.best_ece,
            "config": self.config,
            "training_history": self.training_history,
            "model_version": "continuous_v2.0",
        }

        # Save regular checkpoint
        checkpoint_path = self.checkpoint_dir / f"checkpoint_epoch_{epoch}.pt"
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"Saved checkpoint: {checkpoint_path}")

        # Save best model
        if is_best:
            best_path = self.checkpoint_dir / "best_model_continuous.pt"
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best model: {best_path} (ECE: {ece:.4f})")

        # Clean up old checkpoints
        cleanup_old_checkpoints(
            self.checkpoint_dir,
            pattern="checkpoint_epoch_*.pt",
            keep_last_n=self.keep_last_n,
        )

    def load_checkpoint(self, checkpoint_path: str | Path) -> None:
        """Load model checkpoint.

        Args:
            checkpoint_path: Path to checkpoint file
        """
        checkpoint = load_checkpoint_safe(checkpoint_path, device=self.device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if self.scheduler and checkpoint.get("scheduler_state_dict"):
            self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

        if self.scaler and checkpoint.get("scaler_state_dict"):
            self.scaler.load_state_dict(checkpoint["scaler_state_dict"])

        self.epoch = checkpoint["epoch"]
        self.best_val_loss = checkpoint.get("best_val_loss", float("inf"))
        self.best_ece = checkpoint.get("best_ece", float("inf"))
        self.training_history = checkpoint.get("training_history", {})

        logger.info(f"Resumed from epoch {self.epoch}, best ECE: {self.best_ece:.4f}")

    def _check_early_stopping(self, val_loss: float, ece: float) -> bool:
        """Check for improvement and update early stopping state.

        Args:
            val_loss: Current validation loss
            ece: Current Expected Calibration Error

        Returns:
            True if this is the best model so far
        """
        # Phase 7: Use ECE as primary metric if enabled
        if self.use_ece_early_stopping:
            metric = ece
            best_metric = self.best_ece
            metric_name = "ECE"
        else:
            metric = val_loss
            best_metric = self.best_val_loss
            metric_name = "loss"

        is_best = metric < best_metric

        if is_best:
            if self.use_ece_early_stopping:
                self.best_ece = ece
            self.best_val_loss = val_loss
            self.patience_counter = 0
            logger.info(f"New best {metric_name}: {metric:.4f}")
        else:
            self.patience_counter += 1
            logger.info(
                f"No improvement. Patience: {self.patience_counter}/"
                f"{self.early_stopping_patience}"
            )

        return is_best

    def train(self, train_loader: DataLoader, val_loader: DataLoader) -> dict[str, Any]:
        """Main training loop for continuous labels.

        Args:
            train_loader: DataLoader for training data
            val_loader: DataLoader for validation data

        Returns:
            Dictionary containing training history and final metrics
        """
        logger.info("Starting Phase 7 continuous label training...")
        logger.info(f"Device: {self.device}")
        logger.info(f"Epochs: {self.epochs}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Mixed precision: {self.use_amp}")
        logger.info(f"ECE early stopping: {self.use_ece_early_stopping}")
        logger.info(f"Target ECE: {self.target_ece}")

        last_epoch = self.epoch - 1

        for epoch in range(self.epoch, self.epochs):
            last_epoch = epoch
            self.epoch = epoch
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Epoch {epoch + 1}/{self.epochs}")
            logger.info(f"{'=' * 60}")

            # Train
            train_metrics = self.train_epoch(train_loader)
            logger.info(
                f"Train - Loss: {train_metrics['loss']:.4f} "
                f"BCE: {train_metrics['bce_loss']:.4f} "
                f"MSE: {train_metrics['mse_loss']:.4f} "
                f"MAE: {train_metrics['severity_mae']:.4f} "
                f"Time: {train_metrics['time']:.2f}s"
            )

            # Validate
            val_metrics = self.validate(val_loader)
            logger.info(
                f"Val - Loss: {val_metrics['loss']:.4f} "
                f"ECE: {val_metrics['ece']:.4f} "
                f"MAE: {val_metrics['severity_mae']:.4f} "
                f"Corr: {val_metrics['severity_correlation']:.4f}"
            )

            # Log per-class ECE
            for class_name, class_ece in val_metrics["per_class_ece"].items():
                logger.info(f"  {class_name} ECE: {class_ece:.4f}")

            # Update learning rate
            if self.scheduler:
                if isinstance(self.scheduler, ReduceLROnPlateau):
                    metric = (
                        val_metrics["ece"]
                        if self.use_ece_early_stopping
                        else val_metrics["loss"]
                    )
                    self.scheduler.step(metric)
                else:
                    self.scheduler.step()

            current_lr = self.optimizer.param_groups[0]["lr"]
            logger.info(f"Learning Rate: {current_lr:.6f}")

            # TensorBoard logging
            self.writer.add_scalar("train/epoch_loss", train_metrics["loss"], epoch)
            self.writer.add_scalar("val/epoch_loss", val_metrics["loss"], epoch)
            self.writer.add_scalar("val/ece", val_metrics["ece"], epoch)
            self.writer.add_scalar(
                "val/severity_mae", val_metrics["severity_mae"], epoch
            )
            self.writer.add_scalar("train/learning_rate", current_lr, epoch)

            # Update training history
            self.training_history["train_loss"].append(train_metrics["loss"])
            self.training_history["val_loss"].append(val_metrics["loss"])
            self.training_history["val_ece"].append(val_metrics["ece"])
            self.training_history["severity_mae"].append(val_metrics["severity_mae"])
            self.training_history["learning_rate"].append(current_lr)

            # Early stopping check
            is_best = self._check_early_stopping(
                val_metrics["loss"], val_metrics["ece"]
            )

            # Check if we've hit target ECE
            if val_metrics["ece"] <= self.target_ece:
                logger.info(f"Target ECE {self.target_ece} achieved!")

            # Save checkpoint
            if (epoch + 1) % self.save_interval_epochs == 0 or is_best:
                self.save_checkpoint(
                    epoch, val_metrics["loss"], val_metrics["ece"], is_best
                )

            # Early stopping
            if self.patience_counter >= self.early_stopping_patience:
                logger.info(
                    f"Early stopping triggered after {epoch + 1} epochs. "
                    f"Best ECE: {self.best_ece:.4f}"
                )
                break

        # Close TensorBoard writer
        self.writer.close()

        logger.info("\nPhase 7 training complete!")
        logger.info(f"Best validation loss: {self.best_val_loss:.4f}")
        logger.info(f"Best ECE: {self.best_ece:.4f}")

        return {
            "best_val_loss": self.best_val_loss,
            "best_ece": self.best_ece,
            "total_epochs": last_epoch + 1,
            "training_history": self.training_history,
            "target_ece_achieved": self.best_ece <= self.target_ece,
        }
