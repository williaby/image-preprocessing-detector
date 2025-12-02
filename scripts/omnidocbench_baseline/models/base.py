"""Abstract base classes for benchmark models.

Defines the interface that all model adapters must implement for
consistent benchmarking across different model types and versions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ModelPrediction:
    """Standardized prediction output from any model.

    Attributes:
        scores: Dict of score names to values (e.g., {"blur": 0.8, "noise": 0.3})
        labels: Dict of binary predictions (e.g., {"fuzzy_scan": True})
        confidences: Dict of confidence scores for each prediction
        raw_output: Original model output for debugging
        inference_time_ms: Time taken for inference in milliseconds
    """

    scores: dict[str, float] = field(default_factory=dict)
    labels: dict[str, bool] = field(default_factory=dict)
    confidences: dict[str, float] = field(default_factory=dict)
    raw_output: Any = None
    inference_time_ms: float = 0.0

    def get_binary_prediction(self, attribute: str, threshold: float = 0.5) -> bool:
        """Get binary prediction for an attribute.

        Args:
            attribute: Attribute name (e.g., "fuzzy_scan")
            threshold: Threshold for converting score to binary

        Returns:
            Binary prediction
        """
        # Check if already a binary label
        if attribute in self.labels:
            return self.labels[attribute]

        # Convert score to binary
        if attribute in self.scores:
            return self.scores[attribute] >= threshold

        return False

    def get_score(self, attribute: str, default: float = 0.0) -> float:
        """Get continuous score for an attribute.

        Args:
            attribute: Attribute name
            default: Default value if not found

        Returns:
            Score value
        """
        return self.scores.get(attribute, default)


@dataclass
class ModelConfig:
    """Configuration for a model variant.

    Attributes:
        model_id: Unique identifier (e.g., "resnet18_student_v1")
        name: Human-readable name
        version: Semantic version string
        model_type: Type category (e.g., "resnet", "classical_cv", "yolo")
        description: Description of this variant
        config: Model-specific configuration dict
        benchmarkable_attributes: List of attributes this model can predict
        status: "active", "planned", or "deprecated"
    """

    model_id: str
    name: str
    version: str
    model_type: str
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    benchmarkable_attributes: list[str] = field(default_factory=list)
    status: str = "active"

    @property
    def full_name(self) -> str:
        """Full name with version."""
        return f"{self.name} (v{self.version})"


class BaseModel(ABC):
    """Abstract base class for all benchmark models.

    All model adapters must inherit from this class and implement
    the required methods.
    """

    def __init__(self, config: ModelConfig):
        """Initialize model with configuration.

        Args:
            config: Model configuration
        """
        self.config = config
        self._is_loaded = False

    @property
    def model_id(self) -> str:
        """Unique model identifier."""
        return self.config.model_id

    @property
    def version(self) -> str:
        """Model version."""
        return self.config.version

    @property
    def benchmarkable_attributes(self) -> list[str]:
        """List of attributes this model can predict."""
        return self.config.benchmarkable_attributes

    @abstractmethod
    def load(self) -> None:
        """Load model weights/resources.

        Called once before inference. Should set self._is_loaded = True.
        """

    @abstractmethod
    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run inference on a single image.

        Args:
            image: Input image (BGR format, from OpenCV)

        Returns:
            ModelPrediction with scores/labels
        """

    def predict_batch(self, images: list[np.ndarray]) -> list[ModelPrediction]:
        """Run inference on a batch of images.

        Default implementation calls predict() sequentially.
        Override for batch-optimized inference.

        Args:
            images: List of input images

        Returns:
            List of ModelPrediction objects
        """
        return [self.predict(img) for img in images]

    def unload(self) -> None:
        """Unload model to free resources.

        Override if model needs explicit cleanup.
        """
        self._is_loaded = False

    def __enter__(self) -> "BaseModel":
        """Context manager entry."""
        self.load()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.unload()


class IQAModel(BaseModel):
    """Base class for Image Quality Assessment models.

    IQA models predict quality-related attributes:
    - fuzzy_scan: Image is blurry/low-quality scan
    - noise_level: Amount of noise (0-1)
    - blur_score: Blur severity (0-1)
    - contrast_score: Contrast quality (0-1)
    """

    # Standard IQA attributes
    STANDARD_ATTRIBUTES = [
        "fuzzy_scan",
        "blur_score",
        "noise_score",
        "contrast_score",
        "overall_quality",
    ]

    @abstractmethod
    def predict_quality_scores(self, image: np.ndarray) -> dict[str, float]:
        """Predict quality scores for an image.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict of quality scores (0-1 range)
        """

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run IQA inference.

        Converts quality scores to standardized prediction format.
        """
        import time

        start = time.perf_counter()
        scores = self.predict_quality_scores(image)
        elapsed = (time.perf_counter() - start) * 1000

        # Convert scores to binary labels using default thresholds
        labels = {}
        if "blur_score" in scores:
            # High blur score = fuzzy scan
            labels["fuzzy_scan"] = scores["blur_score"] >= 0.5
        if "overall_quality" in scores:
            labels["low_quality"] = scores["overall_quality"] < 0.5

        return ModelPrediction(
            scores=scores,
            labels=labels,
            confidences=scores.copy(),  # Use scores as confidence
            inference_time_ms=elapsed,
        )


class LayoutModel(BaseModel):
    """Base class for layout detection models.

    Layout models predict structural attributes:
    - layout_type: single_column, multi_column, etc.
    - has_tables: Page contains tables
    - has_figures: Page contains figures
    - has_dense_math: Page has many formulas
    """

    # Standard layout attributes
    STANDARD_ATTRIBUTES = [
        "layout_type",
        "has_tables",
        "has_figures",
        "has_dense_math",
        "has_handwriting",
    ]

    @abstractmethod
    def predict_layout(self, image: np.ndarray) -> dict[str, Any]:
        """Predict layout attributes for an image.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict with layout_type (str) and presence flags (bool)
        """

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run layout inference.

        Converts layout predictions to standardized format.
        """
        import time

        start = time.perf_counter()
        layout = self.predict_layout(image)
        elapsed = (time.perf_counter() - start) * 1000

        # Separate scores and labels
        scores = {}
        labels = {}

        for key, value in layout.items():
            if isinstance(value, bool):
                labels[key] = value
            elif isinstance(value, (int, float)):
                scores[key] = float(value)
            elif key == "layout_type":
                labels[key] = value  # Keep string value

        return ModelPrediction(
            scores=scores,
            labels=labels,
            raw_output=layout,
            inference_time_ms=elapsed,
        )


class PageAttributeModel(BaseModel):
    """Base class for page attribute detection models.

    Detects page-level attributes:
    - watermark: Page has watermark
    - colorful_background: Page has colorful/patterned background
    - fuzzy_scan: Page is a low-quality scan
    """

    STANDARD_ATTRIBUTES = [
        "watermark",
        "colorful_background",
        "fuzzy_scan",
    ]

    @abstractmethod
    def predict_attributes(self, image: np.ndarray) -> dict[str, bool]:
        """Predict page attributes for an image.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict of attribute names to boolean values
        """

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run attribute detection.

        Converts to standardized prediction format.
        """
        import time

        start = time.perf_counter()
        attributes = self.predict_attributes(image)
        elapsed = (time.perf_counter() - start) * 1000

        return ModelPrediction(
            labels=attributes,
            inference_time_ms=elapsed,
        )
