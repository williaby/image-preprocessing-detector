# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Checkpoint management for Google Colab training with session limits.

This module provides robust checkpoint saving/loading to handle Colab Pro's
12-hour session limit. Automatically saves checkpoints and resumes training
seamlessly across sessions.

Key Features:
- Auto-save every N epochs or M minutes
- Resume from last checkpoint
- Session time tracking (warn before 12hr limit)
- Model state, optimizer state, training metrics
- Google Drive integration
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.optim as optim


class CheckpointManager:
    """Manages training checkpoints with session time awareness."""

    def __init__(
        self,
        checkpoint_dir: str,
        save_interval_epochs: int = 5,
        save_interval_minutes: int = 30,
        max_session_hours: float = 11.5,  # Stop before 12hr limit
        keep_last_n: int = 3,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to save checkpoints (Google Drive path)
            save_interval_epochs: Save checkpoint every N epochs
            save_interval_minutes: Also save every M minutes (whichever comes first)
            max_session_hours: Max session duration before auto-stop (11.5 for safety)
            keep_last_n: Keep only last N checkpoints to save space
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.save_interval_epochs = save_interval_epochs
        self.save_interval_minutes = save_interval_minutes
        self.max_session_hours = max_session_hours
        self.keep_last_n = keep_last_n

        self.session_start_time = time.time()
        self.last_checkpoint_time = time.time()

        # Track best model for final export
        self.best_metric_value: float | None = None
        self.best_model_path: Path | None = None

    def should_save_checkpoint(self, epoch: int) -> bool:
        """Check if checkpoint should be saved based on time/epoch interval.

        Args:
            epoch: Current epoch number

        Returns:
            True if checkpoint should be saved
        """
        # Check epoch interval
        if epoch % self.save_interval_epochs == 0:
            return True

        # Check time interval
        minutes_since_last = (time.time() - self.last_checkpoint_time) / 60
        if minutes_since_last >= self.save_interval_minutes:
            return True

        return False

    def should_stop_training(self) -> bool:
        """Check if training should stop due to approaching session limit.

        Returns:
            True if approaching 12-hour limit
        """
        hours_elapsed = (time.time() - self.session_start_time) / 3600
        return hours_elapsed >= self.max_session_hours

    def get_session_status(self) -> dict[str, Any]:
        """Get current session timing information.

        Returns:
            Dictionary with session status details
        """
        hours_elapsed = (time.time() - self.session_start_time) / 3600
        hours_remaining = self.max_session_hours - hours_elapsed

        return {
            "hours_elapsed": round(hours_elapsed, 2),
            "hours_remaining": round(hours_remaining, 2),
            "minutes_since_last_checkpoint": round(
                (time.time() - self.last_checkpoint_time) / 60, 1
            ),
            "should_stop": self.should_stop_training(),
        }

    def save_checkpoint(
        self,
        model: nn.Module,
        optimizer: optim.Optimizer,
        epoch: int,
        metrics: dict[str, float],
        scheduler: Any | None = None,
        extra_state: dict[str, Any] | None = None,
    ) -> Path:
        """Save training checkpoint.

        Args:
            model: PyTorch model to save
            optimizer: Optimizer state
            epoch: Current epoch number
            metrics: Training metrics (loss, accuracy, etc.)
            scheduler: Optional learning rate scheduler
            extra_state: Additional state to save

        Returns:
            Path to saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = (
            self.checkpoint_dir / f"checkpoint_epoch{epoch:03d}_{timestamp}.pt"
        )

        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
            "session_info": self.get_session_status(),
            "timestamp": timestamp,
        }

        if scheduler is not None:
            checkpoint["scheduler_state_dict"] = scheduler.state_dict()

        if extra_state is not None:
            checkpoint["extra_state"] = extra_state

        # Save checkpoint
        # nosec B614 - torch.save uses pickle, but saving our own trusted model checkpoints
        torch.save(checkpoint, checkpoint_path)  # nosec
        self.last_checkpoint_time = time.time()

        # Also save as "latest" for easy resuming
        # nosec B614 - torch.save uses pickle, but saving our own trusted model checkpoints
        latest_path = self.checkpoint_dir / "checkpoint_latest.pt"
        torch.save(checkpoint, latest_path)  # nosec

        # Save metadata JSON for easy inspection
        metadata_path = (
            self.checkpoint_dir / f"checkpoint_epoch{epoch:03d}_{timestamp}.json"
        )
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "epoch": epoch,
                    "metrics": metrics,
                    "session_info": checkpoint["session_info"],
                    "timestamp": timestamp,
                },
                f,
                indent=2,
            )

        print(f"✅ Checkpoint saved: {checkpoint_path.name}")
        print(f"   Metrics: {metrics}")
        print(f"   Session status: {self.get_session_status()}")

        # Check if this is the best model (based on primary metric)
        if "val_loss" in metrics:
            metric_value = metrics["val_loss"]
            if self.best_metric_value is None or metric_value < self.best_metric_value:
                self.best_metric_value = metric_value
                self.best_model_path = checkpoint_path
                best_path = self.checkpoint_dir / "checkpoint_best.pt"
                # nosec B614 - torch.save uses pickle, but saving our own trusted model checkpoints
                torch.save(checkpoint, best_path)  # nosec
                print(f"   ⭐ New best model! Val loss: {metric_value:.4f}")

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints()

        return checkpoint_path

    def load_checkpoint(
        self,
        model: nn.Module,
        optimizer: optim.Optimizer | None = None,
        scheduler: Any | None = None,
        checkpoint_path: str | None = None,
    ) -> dict[str, Any]:
        """Load checkpoint and resume training.

        Args:
            model: PyTorch model to load weights into
            optimizer: Optional optimizer to load state into
            scheduler: Optional scheduler to load state into
            checkpoint_path: Specific checkpoint to load (default: latest)

        Returns:
            Dictionary with checkpoint information (epoch, metrics, etc.)

        Raises:
            FileNotFoundError: If no checkpoint exists
        """
        if checkpoint_path is None:
            checkpoint_path = self.checkpoint_dir / "checkpoint_latest.pt"
        else:
            checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"No checkpoint found at {checkpoint_path}")

        print(f"📂 Loading checkpoint: {checkpoint_path.name}")
        # nosec B614 - torch.load uses pickle, but loading our own trusted checkpoints from local filesystem
        # WARNING: Only load checkpoints from trusted sources (our own training runs)
        checkpoint = torch.load(checkpoint_path, map_location="cpu")  # nosec

        # Load model state
        model.load_state_dict(checkpoint["model_state_dict"])

        # Load optimizer state if provided
        if optimizer is not None and "optimizer_state_dict" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        # Load scheduler state if provided
        if scheduler is not None and "scheduler_state_dict" in checkpoint:
            scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

        resume_epoch = checkpoint["epoch"] + 1
        metrics = checkpoint.get("metrics", {})

        print(f"✅ Resumed from epoch {checkpoint['epoch']}")
        print(f"   Metrics: {metrics}")
        print(f"   Will resume training at epoch {resume_epoch}")

        return {
            "resume_epoch": resume_epoch,
            "metrics": metrics,
            "extra_state": checkpoint.get("extra_state", {}),
        }

    def has_checkpoint(self) -> bool:
        """Check if a resumable checkpoint exists.

        Returns:
            True if checkpoint_latest.pt exists
        """
        latest_path = self.checkpoint_dir / "checkpoint_latest.pt"
        return latest_path.exists()

    def get_best_checkpoint_path(self) -> Path | None:
        """Get path to best checkpoint (lowest validation loss).

        Returns:
            Path to best checkpoint or None if not found
        """
        best_path = self.checkpoint_dir / "checkpoint_best.pt"
        if best_path.exists():
            return best_path
        return self.best_model_path

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints, keeping only last N."""
        # Get all checkpoint files (exclude latest and best)
        checkpoints = sorted(
            [
                f
                for f in self.checkpoint_dir.glob("checkpoint_epoch*.pt")
                if "latest" not in f.name and "best" not in f.name
            ],
            key=lambda x: x.stat().st_mtime,
        )

        # Remove oldest checkpoints if exceeding limit
        if len(checkpoints) > self.keep_last_n:
            for old_checkpoint in checkpoints[: -self.keep_last_n]:
                old_checkpoint.unlink()
                # Also remove associated JSON metadata
                json_file = old_checkpoint.with_suffix(".json")
                if json_file.exists():
                    json_file.unlink()
                print(f"🗑️  Removed old checkpoint: {old_checkpoint.name}")

    def print_session_warning(self) -> None:
        """Print warning if approaching session limit."""
        status = self.get_session_status()
        if status["hours_remaining"] < 1.0:
            print("\n" + "=" * 60)
            print("⚠️  WARNING: Approaching 12-hour session limit!")
            print(f"   Time remaining: {status['hours_remaining']:.1f} hours")
            print("   Training will auto-stop to save checkpoint.")
            print("   You can resume in a new session by re-running the notebook.")
            print("=" * 60 + "\n")
        elif status["hours_remaining"] < 2.0:
            print(f"⏰ Session time remaining: {status['hours_remaining']:.1f} hours")


def train_with_checkpointing(
    model: nn.Module,
    train_loader: Any,
    val_loader: Any,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    checkpoint_manager: CheckpointManager,
    num_epochs: int,
    device: str = "cuda",
    scheduler: Any | None = None,
    start_epoch: int = 0,
) -> dict[str, Any]:
    """Training loop with automatic checkpointing.

    Args:
        model: PyTorch model to train
        train_loader: Training data loader
        val_loader: Validation data loader
        optimizer: Optimizer
        criterion: Loss function
        checkpoint_manager: CheckpointManager instance
        num_epochs: Total number of epochs
        device: Device to train on ('cuda' or 'cpu')
        scheduler: Optional learning rate scheduler
        start_epoch: Epoch to start from (for resuming)

    Returns:
        Dictionary with training history and final metrics
    """
    model = model.to(device)
    history: dict[str, list] = {"train_loss": [], "val_loss": [], "val_accuracy": []}

    for epoch in range(start_epoch, num_epochs):
        # Check session time before starting epoch
        checkpoint_manager.print_session_warning()
        if checkpoint_manager.should_stop_training():
            print("\n🛑 Stopping training to save checkpoint before session limit.")
            break

        # Training phase
        model.train()
        train_loss = 0.0
        for batch_idx, (inputs, targets) in enumerate(train_loader):
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)

        # Validation phase
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item()

                # Calculate accuracy (adjust based on your task)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

        avg_val_loss = val_loss / len(val_loader)
        val_accuracy = 100.0 * correct / total if total > 0 else 0.0

        # Update learning rate scheduler
        if scheduler is not None:
            scheduler.step(avg_val_loss)

        # Record metrics
        metrics = {
            "train_loss": avg_train_loss,
            "val_loss": avg_val_loss,
            "val_accuracy": val_accuracy,
        }
        history["train_loss"].append(avg_train_loss)
        history["val_loss"].append(avg_val_loss)
        history["val_accuracy"].append(val_accuracy)

        print(
            f"Epoch {epoch + 1}/{num_epochs}: "
            f"Train Loss: {avg_train_loss:.4f}, "
            f"Val Loss: {avg_val_loss:.4f}, "
            f"Val Acc: {val_accuracy:.2f}%"
        )

        # Save checkpoint if needed
        if checkpoint_manager.should_save_checkpoint(epoch):
            checkpoint_manager.save_checkpoint(
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                epoch=epoch,
                metrics=metrics,
                extra_state={"history": history},
            )

    # Final checkpoint at end of training
    print("\n✅ Training completed! Saving final checkpoint...")
    checkpoint_manager.save_checkpoint(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        epoch=epoch,
        metrics=metrics,
        extra_state={"history": history},
    )

    return {"history": history, "final_metrics": metrics}
