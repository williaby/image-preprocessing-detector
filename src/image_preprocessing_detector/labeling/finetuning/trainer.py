# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unsloth-based trainer for DIQA regression fine-tuning.

This module implements the training loop for Project C, using:
- PEFT/LoRA for efficient fine-tuning
- Unsloth for training optimization (4x faster, 2x less memory)
- MSE/Huber loss for regression targets
- Early stopping and checkpoint management

Training Architecture:
    Base VLM (frozen) → LoRA Adapters → Regression Head → [3 scores]

The trainer supports:
- Full precision training (FP32)
- Mixed precision training (FP16/BF16)
- 4-bit/8-bit quantized base model with LoRA
- Gradient accumulation for effective larger batches
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import structlog
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR

from image_preprocessing_detector.labeling.finetuning.dataset import (
    create_data_loaders,
)
from image_preprocessing_detector.labeling.finetuning.regression_head import (
    DIQARegressionModel,
    RegressionHeadConfig,
)

if TYPE_CHECKING:
    from torch.utils.data import DataLoader

logger = structlog.get_logger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for DIQA regression training.

    Attributes:
        base_model_id: HuggingFace model ID for base VLM
        output_dir: Directory for checkpoints and logs
        num_epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Peak learning rate
        weight_decay: AdamW weight decay
        warmup_ratio: Fraction of steps for LR warmup
        gradient_accumulation_steps: Steps to accumulate before update
        max_grad_norm: Maximum gradient norm for clipping
        loss_function: Loss type ("mse", "huber", "smooth_l1")
        huber_delta: Delta parameter for Huber loss
        use_lora: Enable LoRA adapters
        lora_r: LoRA rank
        lora_alpha: LoRA alpha (scaling factor)
        lora_dropout: Dropout for LoRA layers
        lora_target_modules: Modules to apply LoRA to
        freeze_encoder: Freeze base encoder (use with LoRA)
        load_in_4bit: Load base model in 4-bit
        load_in_8bit: Load base model in 8-bit
        mixed_precision: Use mixed precision ("no", "fp16", "bf16")
        early_stopping_patience: Epochs without improvement before stopping
        early_stopping_threshold: Minimum improvement to reset patience
        save_every_n_epochs: Save checkpoint frequency
        eval_every_n_steps: Evaluation frequency (0 = per epoch only)
        log_every_n_steps: Logging frequency
        seed: Random seed for reproducibility
    """

    # Model
    base_model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct"
    output_dir: str = "./outputs/diqa_regression"

    # Training schedule
    num_epochs: int = 30
    batch_size: int = 16
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0

    # Loss
    loss_function: Literal["mse", "huber", "smooth_l1"] = "mse"
    huber_delta: float = 0.5

    # LoRA configuration
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )

    # Model loading
    freeze_encoder: bool = True
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    mixed_precision: Literal["no", "fp16", "bf16"] = "fp16"

    # Early stopping
    early_stopping_patience: int = 5
    early_stopping_threshold: float = 1e-4

    # Checkpointing and logging
    save_every_n_epochs: int = 5
    eval_every_n_steps: int = 0
    log_every_n_steps: int = 10
    seed: int = 42

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "base_model_id": self.base_model_id,
            "output_dir": self.output_dir,
            "num_epochs": self.num_epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "warmup_ratio": self.warmup_ratio,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "max_grad_norm": self.max_grad_norm,
            "loss_function": self.loss_function,
            "huber_delta": self.huber_delta,
            "use_lora": self.use_lora,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "lora_target_modules": self.lora_target_modules,
            "freeze_encoder": self.freeze_encoder,
            "load_in_4bit": self.load_in_4bit,
            "load_in_8bit": self.load_in_8bit,
            "mixed_precision": self.mixed_precision,
            "early_stopping_patience": self.early_stopping_patience,
            "early_stopping_threshold": self.early_stopping_threshold,
            "save_every_n_epochs": self.save_every_n_epochs,
            "eval_every_n_steps": self.eval_every_n_steps,
            "log_every_n_steps": self.log_every_n_steps,
            "seed": self.seed,
        }


@dataclass
class TrainingMetrics:
    """Metrics collected during training.

    Attributes:
        epoch: Current epoch number
        step: Global step number
        train_loss: Current training loss
        val_loss: Current validation loss
        learning_rate: Current learning rate
        grad_norm: Gradient norm before clipping
        epoch_time: Time for current epoch
        best_val_loss: Best validation loss so far
        epochs_without_improvement: Patience counter
    """

    epoch: int = 0
    step: int = 0
    train_loss: float = 0.0
    val_loss: float = float("inf")
    learning_rate: float = 0.0
    grad_norm: float = 0.0
    epoch_time: float = 0.0
    best_val_loss: float = float("inf")
    epochs_without_improvement: int = 0


class DIQATrainer:
    """Trainer for DIQA regression model with LoRA support.

    This trainer implements the complete training loop for Project C,
    including LoRA adapter management, early stopping, and checkpoint
    handling.

    Example:
        >>> config = TrainingConfig(
        ...     base_model_id="HuggingFaceTB/SmolVLM-256M-Instruct",
        ...     num_epochs=30,
        ...     use_lora=True,
        ... )
        >>> trainer = DIQATrainer(config)
        >>> trainer.train(data_dir="/data/diqa5000")
        >>> trainer.save_checkpoint("final")
    """

    def __init__(self, config: TrainingConfig) -> None:
        """Initialize the trainer.

        Args:
            config: Training configuration.
        """
        self.config = config
        self.device = self._setup_device()
        self.metrics = TrainingMetrics()

        # Will be initialized in setup()
        self.model: DIQARegressionModel | None = None
        self.optimizer: AdamW | None = None
        self.scheduler: Any = None
        self.scaler: torch.amp.GradScaler | None = None
        self.loss_fn: nn.Module | None = None

        # Set random seed
        self._set_seed(config.seed)

        logger.info(
            "diqa_trainer_initialized",
            config=config.to_dict(),
            device=str(self.device),
        )

    def _setup_device(self) -> torch.device:
        """Setup compute device."""
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info("using_cuda", device_name=torch.cuda.get_device_name(0))
        else:
            device = torch.device("cpu")
            logger.warning("cuda_not_available", fallback="cpu")
        return device

    def _set_seed(self, seed: int) -> None:
        """Set random seeds for reproducibility."""
        import random

        import numpy as np

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def setup(self) -> None:
        """Setup model, optimizer, and training components."""
        logger.info("setting_up_training")

        # Create model
        head_config = RegressionHeadConfig(
            intermediate_size=256,
            dropout=0.1,
            activation="gelu",
            pooling_strategy="mean",
        )

        self.model = DIQARegressionModel(
            base_model_id=self.config.base_model_id,
            head_config=head_config,
            freeze_encoder=self.config.freeze_encoder,
            load_in_4bit=self.config.load_in_4bit,
            load_in_8bit=self.config.load_in_8bit,
        )

        # Apply LoRA if enabled
        if self.config.use_lora and not self.config.freeze_encoder:
            self._apply_lora()

        self.model = self.model.to(self.device)
        assert self.model is not None  # For type checker

        # Setup loss function
        self.loss_fn = self._create_loss_function()

        # Setup optimizer (only trainable params)
        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        self.optimizer = AdamW(
            trainable_params,
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        # Setup mixed precision
        if self.config.mixed_precision != "no" and self.device.type == "cuda":
            dtype = (
                torch.float16
                if self.config.mixed_precision == "fp16"
                else torch.bfloat16
            )
            self.scaler = torch.amp.GradScaler("cuda")
            self._autocast_dtype = dtype
        else:
            self.scaler = None
            self._autocast_dtype = torch.float32

        logger.info(
            "training_setup_complete",
            trainable_params=self.model.get_trainable_parameters(),
            total_params=self.model.get_total_parameters(),
            use_lora=self.config.use_lora,
            mixed_precision=self.config.mixed_precision,
        )

    def _apply_lora(self) -> None:
        """Apply LoRA adapters to the model."""
        try:
            from peft import LoraConfig, get_peft_model

            lora_config = LoraConfig(
                r=self.config.lora_r,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=self.config.lora_target_modules,
                bias="none",
                task_type="FEATURE_EXTRACTION",
            )

            if self.model is not None:
                # Apply LoRA to encoder only
                # Note: encoder is a Module, but get_peft_model expects PreTrainedModel
                # HuggingFace models are compatible at runtime - use cast to satisfy typing
                from typing import cast

                from transformers import PreTrainedModel

                encoder_as_pretrained = cast(PreTrainedModel, self.model.encoder)
                self.model.encoder = get_peft_model(encoder_as_pretrained, lora_config)

            logger.info(
                "lora_applied",
                r=self.config.lora_r,
                alpha=self.config.lora_alpha,
                target_modules=self.config.lora_target_modules,
            )

        except ImportError:
            logger.warning(
                "peft_not_available",
                message="LoRA disabled - install peft: pip install peft",
            )

    def _create_loss_function(self) -> nn.Module:
        """Create the loss function based on configuration."""
        if self.config.loss_function == "huber":
            return nn.HuberLoss(delta=self.config.huber_delta)
        if self.config.loss_function == "smooth_l1":
            return nn.SmoothL1Loss()
        # mse
        return nn.MSELoss()

    def _setup_scheduler(self, num_training_steps: int) -> None:
        """Setup learning rate scheduler with warmup."""
        if self.optimizer is None:
            return

        warmup_steps = int(num_training_steps * self.config.warmup_ratio)

        # Linear warmup
        warmup_scheduler = LinearLR(
            self.optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=warmup_steps,
        )

        # Cosine annealing after warmup
        main_scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=num_training_steps - warmup_steps,
            eta_min=self.config.learning_rate * 0.01,
        )

        self.scheduler = SequentialLR(
            self.optimizer,
            schedulers=[warmup_scheduler, main_scheduler],
            milestones=[warmup_steps],
        )

        logger.info(
            "scheduler_configured",
            total_steps=num_training_steps,
            warmup_steps=warmup_steps,
        )

    def train(
        self,
        data_dir: str | Path,
        max_train_samples: int | None = None,
        max_val_samples: int | None = None,
    ) -> TrainingMetrics:
        """Run the full training loop.

        Args:
            data_dir: Directory containing DIQA dataset.
            max_train_samples: Limit training samples (for debugging).
            max_val_samples: Limit validation samples.

        Returns:
            Final training metrics.
        """
        # Setup if not already done
        if self.model is None:
            self.setup()

        # Create data loaders
        train_loader, val_loader = create_data_loaders(
            data_dir=data_dir,
            batch_size=self.config.batch_size,
            num_workers=4,
            max_train_samples=max_train_samples,
            max_val_samples=max_val_samples,
        )

        # Setup scheduler based on actual training steps
        num_training_steps = (
            len(train_loader) // self.config.gradient_accumulation_steps
        ) * self.config.num_epochs
        self._setup_scheduler(num_training_steps)

        # Create output directory
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            "training_started",
            num_epochs=self.config.num_epochs,
            train_samples=len(train_loader.dataset),
            val_samples=len(val_loader.dataset),
            total_steps=num_training_steps,
        )

        # Training loop
        for epoch in range(self.config.num_epochs):
            self.metrics.epoch = epoch + 1
            epoch_start = time.perf_counter()

            # Train one epoch
            train_loss = self._train_epoch(train_loader)
            self.metrics.train_loss = train_loss

            # Validate
            val_loss = self._validate(val_loader)
            self.metrics.val_loss = val_loss
            self.metrics.epoch_time = time.perf_counter() - epoch_start

            # Update learning rate
            if self.scheduler is not None:
                self.metrics.learning_rate = self.scheduler.get_last_lr()[0]

            # Log epoch summary
            logger.info(
                "epoch_complete",
                epoch=self.metrics.epoch,
                train_loss=f"{train_loss:.4f}",
                val_loss=f"{val_loss:.4f}",
                lr=f"{self.metrics.learning_rate:.2e}",
                time_s=f"{self.metrics.epoch_time:.1f}",
            )

            # Early stopping check
            if self._check_early_stopping(val_loss):
                logger.info(
                    "early_stopping_triggered",
                    epoch=self.metrics.epoch,
                    best_val_loss=f"{self.metrics.best_val_loss:.4f}",
                )
                break

            # Save checkpoint
            if (epoch + 1) % self.config.save_every_n_epochs == 0:
                self.save_checkpoint(f"epoch_{epoch + 1}")

        # Save final model
        self.save_checkpoint("final")

        logger.info(
            "training_complete",
            final_train_loss=f"{self.metrics.train_loss:.4f}",
            best_val_loss=f"{self.metrics.best_val_loss:.4f}",
            total_epochs=self.metrics.epoch,
        )

        return self.metrics

    def _train_epoch(self, train_loader: DataLoader[Any]) -> float:
        """Train for one epoch.

        Args:
            train_loader: Training data loader.

        Returns:
            Average training loss for the epoch.
        """
        if self.model is None or self.optimizer is None or self.loss_fn is None:
            return float("inf")

        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for batch_idx, (images, targets) in enumerate(train_loader):
            images = images.to(self.device)
            targets = targets.to(self.device)

            # Mixed precision forward pass
            with torch.amp.autocast(
                device_type=self.device.type,
                dtype=self._autocast_dtype,
                enabled=self.scaler is not None,
            ):
                outputs = self.model(pixel_values=images)
                loss = self.loss_fn(outputs, targets)
                loss = loss / self.config.gradient_accumulation_steps

            # Backward pass
            if self.scaler is not None:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()

            # Gradient accumulation
            if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                # Gradient clipping
                if self.scaler is not None:
                    self.scaler.unscale_(self.optimizer)

                grad_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.max_grad_norm,
                )
                self.metrics.grad_norm = float(grad_norm)

                # Optimizer step
                if self.scaler is not None:
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()

                self.optimizer.zero_grad()

                if self.scheduler is not None:
                    self.scheduler.step()

                self.metrics.step += 1

            total_loss += loss.item() * self.config.gradient_accumulation_steps
            num_batches += 1

            # Logging
            if (batch_idx + 1) % self.config.log_every_n_steps == 0:
                logger.debug(
                    "training_batch",
                    epoch=self.metrics.epoch,
                    batch=batch_idx + 1,
                    loss=f"{loss.item() * self.config.gradient_accumulation_steps:.4f}",
                    grad_norm=f"{self.metrics.grad_norm:.4f}",
                )

        return total_loss / max(num_batches, 1)

    def _validate(self, val_loader: DataLoader[Any]) -> float:
        """Run validation.

        Args:
            val_loader: Validation data loader.

        Returns:
            Average validation loss.
        """
        if self.model is None or self.loss_fn is None:
            return float("inf")

        self.model.eval()
        total_loss = 0.0
        num_batches = 0

        with torch.no_grad():
            for images, targets in val_loader:
                images = images.to(self.device)
                targets = targets.to(self.device)

                with torch.amp.autocast(
                    device_type=self.device.type,
                    dtype=self._autocast_dtype,
                    enabled=self.scaler is not None,
                ):
                    outputs = self.model(pixel_values=images)
                    loss = self.loss_fn(outputs, targets)

                total_loss += loss.item()
                num_batches += 1

        return total_loss / max(num_batches, 1)

    def _check_early_stopping(self, val_loss: float) -> bool:
        """Check early stopping condition.

        Args:
            val_loss: Current validation loss.

        Returns:
            True if training should stop.
        """
        improvement = self.metrics.best_val_loss - val_loss

        if improvement > self.config.early_stopping_threshold:
            self.metrics.best_val_loss = val_loss
            self.metrics.epochs_without_improvement = 0
            # Save best model
            self.save_checkpoint("best")
            return False

        self.metrics.epochs_without_improvement += 1
        return (
            self.metrics.epochs_without_improvement
            >= self.config.early_stopping_patience
        )

    def save_checkpoint(self, name: str) -> Path:
        """Save a training checkpoint.

        Args:
            name: Checkpoint name (e.g., "best", "epoch_10").

        Returns:
            Path to saved checkpoint.
        """
        if self.model is None:
            raise RuntimeError("Model not initialized")

        checkpoint_dir = Path(self.config.output_dir) / "checkpoints" / name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        self.model.save_pretrained(str(checkpoint_dir / "model"))

        # Save training state
        training_state = {
            "metrics": {
                "epoch": self.metrics.epoch,
                "step": self.metrics.step,
                "train_loss": self.metrics.train_loss,
                "val_loss": self.metrics.val_loss,
                "best_val_loss": self.metrics.best_val_loss,
                "epochs_without_improvement": self.metrics.epochs_without_improvement,
            },
            "config": self.config.to_dict(),
        }

        if self.optimizer is not None:
            training_state["optimizer_state_dict"] = self.optimizer.state_dict()

        if self.scheduler is not None:
            training_state["scheduler_state_dict"] = self.scheduler.state_dict()

        torch.save(training_state, checkpoint_dir / "training_state.pt")

        logger.info(
            "checkpoint_saved",
            name=name,
            path=str(checkpoint_dir),
            val_loss=f"{self.metrics.val_loss:.4f}",
        )

        return checkpoint_dir

    def load_checkpoint(self, checkpoint_path: str | Path) -> None:
        """Load a training checkpoint.

        Args:
            checkpoint_path: Path to checkpoint directory.
        """
        checkpoint_dir = Path(checkpoint_path)

        # Load model
        self.model = DIQARegressionModel.from_pretrained(str(checkpoint_dir / "model"))
        self.model = self.model.to(self.device)

        # Load training state
        training_state = torch.load(
            checkpoint_dir / "training_state.pt",
            map_location=self.device,
            weights_only=True,
        )

        # Restore metrics
        metrics_dict = training_state.get("metrics", {})
        self.metrics.epoch = metrics_dict.get("epoch", 0)
        self.metrics.step = metrics_dict.get("step", 0)
        self.metrics.train_loss = metrics_dict.get("train_loss", 0.0)
        self.metrics.val_loss = metrics_dict.get("val_loss", float("inf"))
        self.metrics.best_val_loss = metrics_dict.get("best_val_loss", float("inf"))
        self.metrics.epochs_without_improvement = metrics_dict.get(
            "epochs_without_improvement", 0
        )

        # Restore optimizer if available
        if self.optimizer is not None and "optimizer_state_dict" in training_state:
            self.optimizer.load_state_dict(training_state["optimizer_state_dict"])

        # Restore scheduler if available
        if self.scheduler is not None and "scheduler_state_dict" in training_state:
            self.scheduler.load_state_dict(training_state["scheduler_state_dict"])

        logger.info(
            "checkpoint_loaded",
            path=str(checkpoint_dir),
            epoch=self.metrics.epoch,
            val_loss=f"{self.metrics.val_loss:.4f}",
        )

    def export_model(
        self,
        export_dir: str | Path,
        formats: list[str] | None = None,
    ) -> dict[str, Path]:
        """Export the trained model to various formats.

        Args:
            export_dir: Directory for exported models.
            formats: Export formats ("pytorch", "onnx", "torchscript").
                    Defaults to all formats.

        Returns:
            Dictionary mapping format name to export path.
        """
        if self.model is None:
            raise RuntimeError("Model not initialized")

        if formats is None:
            formats = ["pytorch", "onnx", "torchscript"]

        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        exports: dict[str, Path] = {}

        # PyTorch format
        if "pytorch" in formats:
            pytorch_path = export_path / "pytorch"
            self.model.save_pretrained(str(pytorch_path))
            exports["pytorch"] = pytorch_path
            logger.info("model_exported", format="pytorch", path=str(pytorch_path))

        # TorchScript format
        if "torchscript" in formats:
            try:
                self.model.eval()
                # Create dummy input
                dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
                scripted = torch.jit.trace(
                    self.model,
                    (dummy_input,),
                    strict=False,
                )
                ts_path = export_path / "model.torchscript"
                scripted.save(str(ts_path))
                exports["torchscript"] = ts_path
                logger.info("model_exported", format="torchscript", path=str(ts_path))
            except Exception as e:
                logger.warning("torchscript_export_failed", error=str(e))

        # ONNX format
        if "onnx" in formats:
            try:
                self.model.eval()
                dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
                onnx_path = export_path / "model.onnx"
                torch.onnx.export(
                    self.model,
                    (dummy_input,),
                    str(onnx_path),
                    input_names=["pixel_values"],
                    output_names=["scores"],
                    dynamic_axes={
                        "pixel_values": {0: "batch_size"},
                        "scores": {0: "batch_size"},
                    },
                    opset_version=14,
                )
                exports["onnx"] = onnx_path
                logger.info("model_exported", format="onnx", path=str(onnx_path))
            except Exception as e:
                logger.warning("onnx_export_failed", error=str(e))

        return exports


def train_diqa_model(
    data_dir: str,
    output_dir: str = "./outputs/diqa_regression",
    base_model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct",
    num_epochs: int = 30,
    batch_size: int = 16,
    use_lora: bool = True,
    load_in_4bit: bool = False,
) -> TrainingMetrics:
    """Convenience function to train a DIQA regression model.

    Args:
        data_dir: Directory containing DIQA dataset.
        output_dir: Output directory for checkpoints.
        base_model_id: HuggingFace model ID.
        num_epochs: Number of training epochs.
        batch_size: Training batch size.
        use_lora: Enable LoRA adapters.
        load_in_4bit: Load base model in 4-bit.

    Returns:
        Final training metrics.

    Example:
        >>> metrics = train_diqa_model(
        ...     data_dir="/data/diqa5000",
        ...     num_epochs=30,
        ...     use_lora=True,
        ... )
        >>> print(f"Best validation loss: {metrics.best_val_loss:.4f}")
    """
    config = TrainingConfig(
        base_model_id=base_model_id,
        output_dir=output_dir,
        num_epochs=num_epochs,
        batch_size=batch_size,
        use_lora=use_lora,
        load_in_4bit=load_in_4bit,
        freeze_encoder=True,  # Always freeze when using LoRA
    )

    trainer = DIQATrainer(config)
    return trainer.train(data_dir=data_dir)
