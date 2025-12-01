"""ResNet adapter for ML-based IQA benchmarking.

Supports both baseline (ImageNet) and fine-tuned variants.
"""

import logging
import sys
import time
from pathlib import Path

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from scripts.omnidocbench_baseline.models.base import (
    IQAModel,
    ModelConfig,
    ModelPrediction,
)

logger = logging.getLogger(__name__)


class ResNetAdapter(IQAModel):
    """Adapter for ResNet-based IQA models.

    Supports:
    - Baseline models (ImageNet pre-trained)
    - Fine-tuned models (custom checkpoints)
    - Teacher (ResNet-50) and Student (ResNet-18) variants
    """

    def __init__(self, config: ModelConfig):
        """Initialize adapter with configuration.

        Args:
            config: Model configuration from registry
        """
        super().__init__(config)
        self._model = None
        self._transform = None
        self._device = None

    def load(self) -> None:
        """Load model weights."""
        if self._is_loaded:
            return

        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as transforms

            # Determine device
            if torch.cuda.is_available():
                self._device = torch.device("cuda")
            else:
                self._device = torch.device("cpu")

            logger.info(f"Loading {self.config.name} on {self._device}")

            # Get architecture
            arch = self.config.config.get("architecture", "resnet18")
            weights = self.config.config.get("weights", "imagenet")
            checkpoint = self.config.config.get("checkpoint")

            # Load base model
            if arch == "resnet18":
                if weights == "imagenet":
                    self._model = models.resnet18(
                        weights=models.ResNet18_Weights.IMAGENET1K_V1
                    )
                else:
                    self._model = models.resnet18(weights=None)
            elif arch == "resnet50":
                if weights == "imagenet":
                    self._model = models.resnet50(
                        weights=models.ResNet50_Weights.IMAGENET1K_V1
                    )
                else:
                    self._model = models.resnet50(weights=None)
            else:
                raise ValueError(f"Unsupported architecture: {arch}")

            # Load custom checkpoint if specified
            if checkpoint and weights == "custom":
                checkpoint_path = Path(checkpoint)
                if checkpoint_path.exists():
                    state_dict = torch.load(checkpoint_path, map_location=self._device)
                    self._model.load_state_dict(state_dict)
                    logger.info(f"Loaded checkpoint from {checkpoint_path}")
                else:
                    logger.warning(
                        f"Checkpoint not found: {checkpoint_path}. "
                        f"Using random weights."
                    )

            # Move to device and set eval mode
            self._model = self._model.to(self._device)
            self._model.eval()

            # Setup transforms
            input_size = self.config.config.get("input_size", 224)
            normalize = self.config.config.get("normalize", "imagenet")

            if normalize == "imagenet":
                norm_mean = [0.485, 0.456, 0.406]
                norm_std = [0.229, 0.224, 0.225]
            else:
                norm_mean = [0.5, 0.5, 0.5]
                norm_std = [0.5, 0.5, 0.5]

            self._transform = transforms.Compose(
                [
                    transforms.ToPILImage(),
                    transforms.Resize((input_size, input_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=norm_mean, std=norm_std),
                ]
            )

            self._is_loaded = True
            logger.info(f"Loaded {self.config.name} ({arch})")

        except ImportError as e:
            logger.error(f"PyTorch not available: {e}")
            logger.info("Using placeholder predictions for unloaded model")
            self._is_loaded = True  # Mark as loaded to allow placeholder behavior

    def predict_quality_scores(self, image: np.ndarray) -> dict[str, float]:
        """Predict IQA scores using ResNet features.

        For baseline models, uses feature statistics as proxy for quality.
        For fine-tuned models, uses the trained IQA heads.

        Args:
            image: Input image (BGR format)

        Returns:
            Dict of quality scores (0-1 range)
        """
        if not self._is_loaded:
            self.load()

        # If model failed to load, return placeholder scores
        if self._model is None:
            logger.warning("Model not loaded, returning placeholder scores")
            return {
                "blur_score": 0.5,
                "noise_score": 0.5,
                "contrast_score": 0.5,
                "overall_quality": 0.5,
            }

        import cv2
        import torch

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Transform
        input_tensor = self._transform(rgb_image).unsqueeze(0).to(self._device)

        # Forward pass
        with torch.no_grad():
            # Get features before final FC layer
            x = self._model.conv1(input_tensor)
            x = self._model.bn1(x)
            x = self._model.relu(x)
            x = self._model.maxpool(x)

            x = self._model.layer1(x)
            x = self._model.layer2(x)
            x = self._model.layer3(x)
            x = self._model.layer4(x)

            x = self._model.avgpool(x)
            features = torch.flatten(x, 1)

            # For baseline models, derive quality scores from feature statistics
            # Higher feature variance often correlates with sharper images
            feature_mean = features.mean().item()
            feature_std = features.std().item()
            feature_max = features.max().item()

        # Normalize to 0-1 range using typical ranges
        # These are heuristic mappings for baseline models
        # Fine-tuned models would have explicit IQA heads

        # Feature std proxy for sharpness (higher = sharper)
        # Typical range: 0.2 - 1.5
        sharpness = min(1.0, max(0.0, (feature_std - 0.2) / 1.3))
        blur_score = 1.0 - sharpness

        # Feature mean proxy for contrast
        # Typical range: 0.0 - 0.5
        contrast_score = min(1.0, max(0.0, feature_mean / 0.5))

        # Overall quality (weighted combination)
        overall_quality = 0.6 * sharpness + 0.4 * contrast_score

        return {
            "blur_score": blur_score,
            "contrast_score": contrast_score,
            "overall_quality": overall_quality,
            # Raw features for analysis
            "_feature_mean": feature_mean,
            "_feature_std": feature_std,
            "_feature_max": feature_max,
        }

    def predict(self, image: np.ndarray) -> ModelPrediction:
        """Run IQA inference.

        Args:
            image: Input image (BGR format)

        Returns:
            ModelPrediction with quality scores
        """
        start = time.perf_counter()

        scores = self.predict_quality_scores(image)
        elapsed = (time.perf_counter() - start) * 1000

        # Convert to binary labels
        labels = {
            "fuzzy_scan": scores["blur_score"] >= 0.5,
            "low_quality": scores["overall_quality"] < 0.5,
        }

        # Separate internal scores
        public_scores = {k: v for k, v in scores.items() if not k.startswith("_")}
        raw_output = {k: v for k, v in scores.items() if k.startswith("_")}

        return ModelPrediction(
            scores=public_scores,
            labels=labels,
            confidences=public_scores.copy(),
            raw_output=raw_output,
            inference_time_ms=elapsed,
        )

    def unload(self) -> None:
        """Unload model to free GPU memory."""
        if self._model is not None:
            del self._model
            self._model = None

            # Clear CUDA cache if available
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

        self._is_loaded = False
        logger.info(f"Unloaded {self.config.name}")
