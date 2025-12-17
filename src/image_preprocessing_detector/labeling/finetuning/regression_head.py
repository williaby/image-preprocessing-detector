# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Regression head model for DIQA score prediction.

This module implements the regression head architecture for Project C,
which transforms vision encoder outputs into 3 continuous DIQA scores:
- Overall quality
- Sharpness
- Color fidelity

Architecture:
    Vision Encoder → Pooled Embedding → MLP Regression Head → [3 scores]

The regression head is designed to be attached to any HuggingFace
vision encoder that exposes hidden states.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
import torch
import torch.nn as nn
from torch import Tensor

logger = structlog.get_logger(__name__)


@dataclass
class RegressionHeadConfig:
    """Configuration for the DIQA regression head.

    Attributes:
        hidden_size: Size of the input hidden states from vision encoder
        intermediate_size: Size of the intermediate MLP layer
        num_outputs: Number of output scores (default: 3 for DIQA)
        dropout: Dropout probability
        activation: Activation function ("gelu", "relu", "silu")
        use_layer_norm: Whether to use layer normalization
        pooling_strategy: How to pool encoder outputs ("mean", "cls", "max")
    """

    hidden_size: int = 768
    intermediate_size: int = 256
    num_outputs: int = 3
    dropout: float = 0.1
    activation: str = "gelu"
    use_layer_norm: bool = True
    pooling_strategy: str = "mean"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "hidden_size": self.hidden_size,
            "intermediate_size": self.intermediate_size,
            "num_outputs": self.num_outputs,
            "dropout": self.dropout,
            "activation": self.activation,
            "use_layer_norm": self.use_layer_norm,
            "pooling_strategy": self.pooling_strategy,
        }


class DIQARegressionHead(nn.Module):
    """MLP regression head for DIQA score prediction.

    This head is designed to be attached to the output of a vision encoder.
    It pools the hidden states and passes them through an MLP to produce
    3 continuous scores for overall, sharpness, and color.

    Example:
        >>> config = RegressionHeadConfig(hidden_size=768)
        >>> head = DIQARegressionHead(config)
        >>> hidden_states = torch.randn(4, 197, 768)  # [batch, seq, hidden]
        >>> scores = head(hidden_states)
        >>> print(scores.shape)  # [4, 3]
    """

    def __init__(self, config: RegressionHeadConfig) -> None:
        """Initialize the regression head.

        Args:
            config: Regression head configuration.
        """
        super().__init__()
        self.config = config

        # Layer normalization (optional)
        self.layer_norm = (
            nn.LayerNorm(config.hidden_size) if config.use_layer_norm else nn.Identity()
        )

        # Activation function
        activations = {
            "gelu": nn.GELU(),
            "relu": nn.ReLU(),
            "silu": nn.SiLU(),
        }
        self.activation = activations.get(config.activation, nn.GELU())

        # MLP layers
        self.fc1 = nn.Linear(config.hidden_size, config.intermediate_size)
        self.dropout = nn.Dropout(config.dropout)
        self.fc2 = nn.Linear(config.intermediate_size, config.num_outputs)

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights with small values for stable training."""
        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def _pool_hidden_states(self, hidden_states: Tensor) -> Tensor:
        """Pool hidden states according to pooling strategy.

        Args:
            hidden_states: Tensor of shape [batch, seq_len, hidden_size]

        Returns:
            Pooled tensor of shape [batch, hidden_size]
        """
        if self.config.pooling_strategy == "cls":
            # Use CLS token (first token)
            return hidden_states[:, 0, :]
        elif self.config.pooling_strategy == "max":
            # Max pooling over sequence
            return hidden_states.max(dim=1).values
        else:  # mean
            # Mean pooling over sequence
            return hidden_states.mean(dim=1)

    def forward(self, hidden_states: Tensor) -> Tensor:
        """Forward pass through the regression head.

        Args:
            hidden_states: Tensor of shape [batch, seq_len, hidden_size]
                          or [batch, hidden_size] if already pooled.

        Returns:
            Scores tensor of shape [batch, num_outputs]
        """
        # Pool if needed
        if hidden_states.dim() == 3:
            x = self._pool_hidden_states(hidden_states)
        else:
            x = hidden_states

        # MLP
        x = self.layer_norm(x)
        x = self.fc1(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = self.fc2(x)

        # Sigmoid to constrain to [0, 1]
        x = torch.sigmoid(x)

        return x


class DIQARegressionModel(nn.Module):
    """Complete DIQA regression model with vision encoder + regression head.

    This model combines a pre-trained vision encoder with a regression head
    for end-to-end DIQA score prediction.

    Supports:
    - Various HuggingFace vision encoders
    - LoRA/PEFT adapter integration
    - Frozen encoder with trainable head
    - Full fine-tuning

    Example:
        >>> model = DIQARegressionModel(base_model_id="HuggingFaceTB/SmolVLM-256M-Instruct")
        >>> images = processor(images=[img], return_tensors="pt")
        >>> scores = model(**images)
        >>> print(scores.overall, scores.sharpness, scores.color)
    """

    def __init__(
        self,
        base_model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct",
        head_config: RegressionHeadConfig | None = None,
        freeze_encoder: bool = False,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        device_map: str | None = "auto",
    ) -> None:
        """Initialize the DIQA regression model.

        Args:
            base_model_id: HuggingFace model ID for the vision encoder.
            head_config: Configuration for regression head. If None, uses defaults.
            freeze_encoder: Whether to freeze the encoder weights.
            load_in_4bit: Load encoder in 4-bit quantization.
            load_in_8bit: Load encoder in 8-bit quantization.
            device_map: Device map for model loading.
        """
        super().__init__()

        self.base_model_id = base_model_id
        self.freeze_encoder = freeze_encoder

        # Load vision encoder
        self.encoder = self._load_encoder(
            base_model_id,
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            device_map=device_map,
        )

        # Get hidden size from encoder config
        hidden_size = self._get_hidden_size()

        # Create regression head config
        if head_config is None:
            head_config = RegressionHeadConfig(hidden_size=hidden_size)
        else:
            head_config.hidden_size = hidden_size

        self.head_config = head_config
        self.head = DIQARegressionHead(head_config)

        # Freeze encoder if requested
        if freeze_encoder:
            self._freeze_encoder()

        logger.info(
            "diqa_regression_model_initialized",
            base_model=base_model_id,
            hidden_size=hidden_size,
            freeze_encoder=freeze_encoder,
        )

    def _load_encoder(
        self,
        model_id: str,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        device_map: str | None = "auto",
    ) -> nn.Module:
        """Load the vision encoder from HuggingFace.

        Args:
            model_id: HuggingFace model ID.
            load_in_4bit: Use 4-bit quantization.
            load_in_8bit: Use 8-bit quantization.
            device_map: Device mapping strategy.

        Returns:
            Loaded encoder model.
        """
        from transformers import AutoModel

        load_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
        }

        if device_map:
            load_kwargs["device_map"] = device_map

        # Handle quantization
        if load_in_4bit or load_in_8bit:
            try:
                from transformers import BitsAndBytesConfig

                if load_in_4bit:
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                else:
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_8bit=True
                    )
            except ImportError:
                logger.warning("bitsandbytes_not_available", falling_back="fp16")
                load_kwargs["torch_dtype"] = torch.float16

        encoder = AutoModel.from_pretrained(model_id, **load_kwargs)
        return encoder

    def _get_hidden_size(self) -> int:
        """Get the hidden size from the encoder config."""
        config = self.encoder.config

        # Try various attribute names
        for attr in ["hidden_size", "d_model", "n_embd", "embed_dim"]:
            if hasattr(config, attr):
                return getattr(config, attr)

        # Fallback: try to infer from a forward pass
        logger.warning("could_not_determine_hidden_size", fallback=768)
        return 768

    def _freeze_encoder(self) -> None:
        """Freeze all encoder parameters."""
        for param in self.encoder.parameters():
            param.requires_grad = False

        logger.info("encoder_frozen", trainable_params=0)

    def unfreeze_encoder(self) -> None:
        """Unfreeze encoder parameters for full fine-tuning."""
        for param in self.encoder.parameters():
            param.requires_grad = True

        self.freeze_encoder = False
        logger.info("encoder_unfrozen")

    def forward(
        self,
        pixel_values: Tensor | None = None,
        **kwargs: Any,
    ) -> Tensor:
        """Forward pass through encoder and regression head.

        Args:
            pixel_values: Image tensor of shape [batch, channels, height, width]
            **kwargs: Additional arguments passed to encoder.

        Returns:
            Scores tensor of shape [batch, 3] with values in [0, 1]
        """
        # Get encoder outputs
        encoder_outputs = self.encoder(pixel_values=pixel_values, **kwargs)

        # Extract hidden states
        if hasattr(encoder_outputs, "last_hidden_state"):
            hidden_states = encoder_outputs.last_hidden_state
        elif hasattr(encoder_outputs, "hidden_states"):
            hidden_states = encoder_outputs.hidden_states[-1]
        elif isinstance(encoder_outputs, tuple):
            hidden_states = encoder_outputs[0]
        else:
            hidden_states = encoder_outputs

        # Pass through regression head
        scores = self.head(hidden_states)

        return scores

    def get_trainable_parameters(self) -> int:
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_total_parameters(self) -> int:
        """Get total number of parameters."""
        return sum(p.numel() for p in self.parameters())

    def save_pretrained(self, save_directory: str) -> None:
        """Save the model to a directory.

        Args:
            save_directory: Directory to save model to.
        """
        import json
        from pathlib import Path

        save_path = Path(save_directory)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save state dict
        torch.save(self.state_dict(), save_path / "pytorch_model.bin")

        # Save config
        config = {
            "base_model_id": self.base_model_id,
            "head_config": self.head_config.to_dict(),
            "freeze_encoder": self.freeze_encoder,
        }
        (save_path / "config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        logger.info("model_saved", path=str(save_path))

    @classmethod
    def from_pretrained(cls, load_directory: str) -> DIQARegressionModel:
        """Load model from a saved directory.

        Args:
            load_directory: Directory containing saved model.

        Returns:
            Loaded DIQARegressionModel.
        """
        import json
        from pathlib import Path

        load_path = Path(load_directory)

        # Load config
        config = json.loads((load_path / "config.json").read_text(encoding="utf-8"))

        # Create model
        head_config = RegressionHeadConfig(**config["head_config"])
        model = cls(
            base_model_id=config["base_model_id"],
            head_config=head_config,
            freeze_encoder=config.get("freeze_encoder", False),
        )

        # Load state dict
        state_dict = torch.load(
            load_path / "pytorch_model.bin",
            map_location="cpu",
        )
        model.load_state_dict(state_dict)

        logger.info("model_loaded", path=str(load_path))
        return model


@dataclass
class DIQAOutput:
    """Output from DIQA regression model.

    Attributes:
        overall: Overall quality score [0, 1]
        sharpness: Sharpness score [0, 1]
        color: Color fidelity score [0, 1]
        scores: Raw tensor of all scores
        hidden_states: Encoder hidden states (optional)
    """

    overall: float
    sharpness: float
    color: float
    scores: Tensor | None = None
    hidden_states: Tensor | None = None

    @classmethod
    def from_tensor(cls, scores: Tensor) -> DIQAOutput:
        """Create output from scores tensor.

        Args:
            scores: Tensor of shape [3] or [1, 3]

        Returns:
            DIQAOutput instance.
        """
        if scores.dim() == 2:
            scores = scores.squeeze(0)

        return cls(
            overall=float(scores[0].item()),
            sharpness=float(scores[1].item()),
            color=float(scores[2].item()),
            scores=scores,
        )
