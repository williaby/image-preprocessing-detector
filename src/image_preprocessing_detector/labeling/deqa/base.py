"""Base classes for DeQA-Doc inference.

This module defines the abstract base class and common data structures
used across all inference modes.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.labeling.deqa.config import (
    QUALITY_LEVELS,
    QUALITY_SCORES,
    DeQAConfig,
    QualityDimension,
)
from image_preprocessing_detector.utils.datetime_compat import UTC

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class DeQAScore:
    """Quality score output from a DeQA model.

    Attributes:
        dimension: Quality dimension (overall, sharpness, color).
        score: Final weighted quality score (1-5 scale).
        logits: Raw logits for each quality level.
        probs: Probability distribution over quality levels.
        model_id: Model that produced this score.
    """

    dimension: QualityDimension
    score: float
    logits: dict[str, float] = field(default_factory=dict)
    probs: dict[str, float] = field(default_factory=dict)
    model_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "logits": self.logits,
            "probs": self.probs,
            "model_id": self.model_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeQAScore:
        """Deserialize from dictionary."""
        return cls(
            dimension=QualityDimension(data["dimension"]),
            score=data["score"],
            logits=data.get("logits", {}),
            probs=data.get("probs", {}),
            model_id=data.get("model_id", ""),
        )


@dataclass
class LabelResult:
    """Complete labeling result for a single image.

    Attributes:
        image_path: Path to the image file.
        dataset: Dataset name.
        mode: Inference mode used.
        scores: Final scores per dimension.
        per_model_scores: Scores from each model (for ensemble mode).
        model_config: Configuration of models used.
        timestamp: When inference was performed.
    """

    image_path: str
    dataset: str
    mode: str
    scores: dict[str, float]  # dimension -> score
    per_model_scores: dict[str, dict[str, float]] | None = None  # dim -> model -> score
    probs: dict[str, dict[str, float]] | None = None  # dimension -> level -> prob
    model_config: dict[str, Any] | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSONL output."""
        return {
            "image": self.image_path,
            "dataset": self.dataset,
            "mode": self.mode,
            "scores": self.scores,
            "per_model_scores": self.per_model_scores,
            "probs": self.probs,
            "model_config": self.model_config,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LabelResult:
        """Deserialize from dictionary."""
        return cls(
            image_path=data["image"],
            dataset=data["dataset"],
            mode=data["mode"],
            scores=data["scores"],
            per_model_scores=data.get("per_model_scores"),
            probs=data.get("probs"),
            model_config=data.get("model_config"),
            timestamp=data.get("timestamp", ""),
        )


class DeQAInference(ABC):
    """Abstract base class for DeQA-Doc inference engines.

    All inference modes (specialist, ensemble, vl) inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: DeQAConfig) -> None:
        """Initialize the inference engine.

        Args:
            config: Configuration for inference.
        """
        self.config = config
        self.models: dict[str | QualityDimension, Any] = {}
        self.tokenizers: dict[str | QualityDimension, Any] = {}
        self.processors: dict[str | QualityDimension, Any] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if models are loaded."""
        return self._loaded

    @abstractmethod
    def load_models(self, device: str | None = None) -> None:
        """Load model weights to the specified device.

        Args:
            device: Device to load models on. Defaults to config.device.
        """
        ...

    @abstractmethod
    def unload_models(self) -> None:
        """Unload models and free GPU memory."""
        ...

    @abstractmethod
    def predict(self, image: Image.Image) -> dict[str, DeQAScore]:
        """Generate quality scores for an image.

        Args:
            image: PIL Image to assess.

        Returns:
            Dictionary mapping dimension to DeQAScore.
        """
        ...

    def predict_batch(
        self,
        images: list[Image.Image],
    ) -> list[dict[str, DeQAScore]]:
        """Generate quality scores for a batch of images.

        Default implementation processes images sequentially.
        Subclasses can override for batch optimization.

        Args:
            images: List of PIL Images to assess.

        Returns:
            List of dictionaries mapping dimension to DeQAScore.
        """
        return [self.predict(img) for img in images]

    def generate_label_result(
        self,
        image_path: str,
        dataset: str,
        scores: dict[str, DeQAScore],
        per_model_scores: dict[str, dict[str, float]] | None = None,
    ) -> LabelResult:
        """Create a LabelResult from prediction scores.

        Args:
            image_path: Path to the image file.
            dataset: Dataset name.
            scores: Dictionary of DeQAScore per dimension.
            per_model_scores: Optional per-model scores for ensemble mode.

        Returns:
            LabelResult instance.
        """
        return LabelResult(
            image_path=image_path,
            dataset=dataset,
            mode=self.config.mode.value,
            scores={dim: score.score for dim, score in scores.items()},
            per_model_scores=per_model_scores,
            probs={dim: score.probs for dim, score in scores.items()},
            model_config={
                "models": [m.model_id for m in self.config.get_model_configs()],
                "quantization": self.config.quantization,
            },
        )

    @staticmethod
    def compute_score_from_probs(probs: dict[str, float]) -> float:
        """Compute weighted quality score from probability distribution.

        Args:
            probs: Dictionary mapping level name to probability.

        Returns:
            Weighted quality score (1-5 scale).
        """
        score = 0.0
        for level, level_score in zip(QUALITY_LEVELS, QUALITY_SCORES, strict=True):
            score += probs.get(level, 0.0) * level_score
        return score

    @staticmethod
    def normalize_logits_to_probs(logits: dict[str, float]) -> dict[str, float]:
        """Normalize logits to probability distribution using softmax.

        Args:
            logits: Dictionary mapping level name to logit value.

        Returns:
            Dictionary mapping level name to probability.
        """
        import math

        max_logit = max(logits.values())
        exp_logits = {k: math.exp(v - max_logit) for k, v in logits.items()}
        total = sum(exp_logits.values())
        return {k: v / total for k, v in exp_logits.items()}


class CheckpointManager:
    """Manages checkpointing for long-running inference jobs."""

    def __init__(
        self,
        output_path: Path,
        checkpoint_interval: int = 500,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            output_path: Path for output JSONL file.
            checkpoint_interval: Save checkpoint every N images.

        Raises:
            ValueError: If output_path contains path traversal.
        """
        # Validate path to prevent traversal attacks
        self._output_path = self._validate_path(output_path)
        self.checkpoint_interval = checkpoint_interval
        self._checkpoint_path = self._output_path.with_suffix(".checkpoint.json")
        self.results: list[LabelResult] = []
        self.processed_ids: set[str] = set()

    @staticmethod
    def _validate_path(path: Path) -> Path:
        """Validate and resolve a path, preventing traversal attacks.

        Args:
            path: Path to validate.

        Returns:
            Resolved absolute path.

        Raises:
            ValueError: If path contains traversal attempts.
        """
        if ".." in str(path):
            msg = f"Path traversal not allowed: {path}"
            raise ValueError(msg)
        return path.resolve()

    @property
    def output_path(self) -> Path:
        """Get validated output path."""
        return self._output_path

    @property
    def checkpoint_path(self) -> Path:
        """Get validated checkpoint path."""
        return self._checkpoint_path

    def load_checkpoint(self) -> int:
        """Load existing checkpoint if available.

        Returns:
            Number of previously processed images.
        """
        if not self.checkpoint_path.exists():
            return 0

        try:
            # Path validated in __init__ via _validate_path
            with open(self.checkpoint_path) as f:  # nosemgrep: cli-path-traversal-open
                data = json.load(f)
            self.processed_ids = set(data.get("processed_ids", []))
            logger.info(
                "Loaded checkpoint with %d processed images", len(self.processed_ids)
            )
            return len(self.processed_ids)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load checkpoint: %s", e)
            return 0

    def save_checkpoint(self) -> None:
        """Save current progress to checkpoint file."""
        # Path validated in __init__ via _validate_path
        with open(self.checkpoint_path, "w") as f:  # nosemgrep: cli-path-traversal-open
            json.dump(
                {
                    "processed_ids": list(self.processed_ids),
                    "count": len(self.processed_ids),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                f,
            )

    def add_result(self, result: LabelResult) -> None:
        """Add a result and checkpoint if needed.

        Args:
            result: LabelResult to add.
        """
        self.results.append(result)
        self.processed_ids.add(result.image_path)

        if len(self.results) % self.checkpoint_interval == 0:
            self.save_results()
            self.save_checkpoint()
            logger.info("Checkpoint saved at %d results", len(self.results))

    def save_results(self) -> None:
        """Save all results to output file."""
        # Path validated in __init__ via _validate_path
        with open(self.output_path, "w") as f:  # nosemgrep: cli-path-traversal-open
            f.writelines(result.to_json() + "\n" for result in self.results)

    def is_processed(self, image_path: str) -> bool:
        """Check if an image has already been processed.

        Args:
            image_path: Path to check.

        Returns:
            True if already processed.
        """
        return image_path in self.processed_ids

    def finalize(self) -> None:
        """Save final results and clean up checkpoint."""
        self.save_results()
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()
        logger.info("Finalized %d results to %s", len(self.results), self.output_path)
