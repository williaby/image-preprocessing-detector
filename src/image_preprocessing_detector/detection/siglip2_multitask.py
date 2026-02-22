# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""SigLIP 2 Multi-Task Teacher inference wrapper for production use.

Provides lazy-loaded, device-aware inference for the multi-task teacher model
that predicts 8 document analysis tasks simultaneously:
- IQA regression: overall, sharpness, color (with uncertainty)
- Classification: script (19-class), document source (3-class), orientation (4-class)
- Severity regression: shadow, warping (with uncertainty)

Usage:
    >>> detector = SigLIP2MultiTaskDetector(checkpoint_path="best_model.pt")
    >>> result = detector.predict(image)
    >>> print(result.script_prediction, result.orientation_degrees)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# ============================================================================
# Constants (must match modal/train_siglip2_multitask.py)
# ============================================================================

SCRIPT_ML_CLASSES: tuple[str, ...] = (
    "LATN",
    "CYRL",
    "GREK",
    "ARAB",
    "HEBR",
    "DEVA",
    "BENG",
    "TAML",
    "TELU",
    "HANS",
    "HANT",
    "JPAN",
    "KORE",
    "THAI",
    "TIBT",
    "INDIC_OTHER",
    "SE_ASIAN_OTHER",
    "OTHER",
    "UNKNOWN",
)

SOURCE_CLASSES: tuple[str, ...] = ("scanned", "camera", "born_digital")

ORIENTATION_CLASSES: tuple[int, ...] = (0, 90, 180, 270)

IQA_TASKS: tuple[str, ...] = ("overall", "sharpness", "color")
CLASSIFICATION_TASKS: tuple[str, ...] = ("script", "source", "orientation")
REGRESSION_TASKS: tuple[str, ...] = ("shadow", "warping")
ALL_TASKS: tuple[str, ...] = IQA_TASKS + CLASSIFICATION_TASKS + REGRESSION_TASKS


# ============================================================================
# Result dataclasses
# ============================================================================


@dataclass(frozen=True)
class IQAScore:
    """Single IQA dimension score with uncertainty."""

    mu: float
    sigma_sq: float

    @property
    def confidence(self) -> float:
        """Higher confidence = lower uncertainty (inverse sigma_sq)."""
        return 1.0 / (1.0 + self.sigma_sq)


@dataclass(frozen=True)
class ClassificationResult:
    """Classification prediction with full softmax distribution."""

    predicted_class: str
    predicted_idx: int
    confidence: float
    distribution: dict[str, float]


@dataclass(frozen=True)
class RegressionResult:
    """Severity regression with uncertainty."""

    value: float
    sigma_sq: float

    @property
    def confidence(self) -> float:
        """Higher confidence = lower uncertainty."""
        return 1.0 / (1.0 + self.sigma_sq)


@dataclass(frozen=True)
class MultiTaskPrediction:
    """Complete multi-task prediction from SigLIP 2 teacher.

    Attributes:
        iqa_overall: Overall image quality score.
        iqa_sharpness: Sharpness quality score.
        iqa_color: Color quality score.
        script: Script detection result with full distribution.
        source: Document source classification.
        orientation: Orientation detection.
        shadow: Shadow severity (0=none, 1=severe).
        warping: Warping severity (0=none, 1=severe).
        inference_time_ms: Inference time in milliseconds.
        device: Device used for inference.
    """

    iqa_overall: IQAScore
    iqa_sharpness: IQAScore
    iqa_color: IQAScore
    script: ClassificationResult
    source: ClassificationResult
    orientation: ClassificationResult
    shadow: RegressionResult
    warping: RegressionResult
    inference_time_ms: float = 0.0
    device: str = "cpu"

    @property
    def script_prediction(self) -> str:
        """Primary script class (e.g. 'LATN', 'HANS')."""
        return self.script.predicted_class

    @property
    def orientation_degrees(self) -> int:
        """Predicted orientation in degrees (0, 90, 180, 270)."""
        return int(self.orientation.predicted_class)

    @property
    def source_type(self) -> str:
        """Document source type (scanned, camera, born_digital)."""
        return self.source.predicted_class

    @property
    def overall_quality(self) -> float:
        """Overall IQA score (0-1, higher is better)."""
        return self.iqa_overall.mu


@dataclass
class SigLIP2MultiTaskConfig:
    """Configuration for SigLIP2 multi-task inference.

    Attributes:
        model_id: HuggingFace model ID for backbone + processor.
        max_num_patches: Maximum NaFlex patches.
        device: Device override (None = auto-detect).
        use_fp16: Use half-precision for inference.
    """

    model_id: str = "google/siglip2-base-patch16-naflex"
    max_num_patches: int = 784
    device: str | None = None
    use_fp16: bool = False


# ============================================================================
# Detector class
# ============================================================================


class SigLIP2MultiTaskDetector:
    """Production inference wrapper for SigLIP 2 multi-task teacher.

    Lazy-loads the model on first prediction. Caches per device.

    Args:
        checkpoint_path: Path to trained model checkpoint (.pt file).
        config: Optional configuration overrides.

    Example:
        >>> detector = SigLIP2MultiTaskDetector("best_model.pt")
        >>> result = detector.predict(image_bgr)
        >>> print(result.script_prediction)  # "LATN"
        >>> print(result.orientation_degrees)  # 0
        >>> print(result.overall_quality)  # 0.85
    """

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        config: SigLIP2MultiTaskConfig | None = None,
    ) -> None:
        self.config = config or SigLIP2MultiTaskConfig()
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self._model: Any | None = None
        self._processor: Any | None = None
        self._device: Any | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy-load model and processor on first use."""
        if self._initialized:
            return

        import torch
        from transformers import AutoProcessor

        # Device selection
        if self.config.device:
            self._device = torch.device(self.config.device)
        elif torch.cuda.is_available():
            self._device = torch.device("cuda")
        else:
            self._device = torch.device("cpu")

        logger.info(
            "siglip2_multitask_init",
            device=str(self._device),
            model_id=self.config.model_id,
        )

        # Load processor
        self._processor = AutoProcessor.from_pretrained(self.config.model_id)

        # Build model architecture
        self._model = self._build_model(self.config.model_id)

        # Load checkpoint if provided
        if self.checkpoint_path and self.checkpoint_path.exists():
            ckpt = torch.load(
                self.checkpoint_path,
                map_location=self._device,
                weights_only=False,
            )
            state_dict = ckpt.get("model_state_dict", ckpt)
            missing, unexpected = self._model.load_state_dict(
                state_dict,
                strict=False,
            )
            logger.info(
                "checkpoint_loaded",
                path=str(self.checkpoint_path),
                missing_keys=len(missing),
                unexpected_keys=len(unexpected),
            )
        elif self.checkpoint_path:
            logger.warning(
                "checkpoint_not_found",
                path=str(self.checkpoint_path),
            )

        self._model = self._model.to(self._device)
        self._model.eval()

        if self.config.use_fp16 and self._device.type == "cuda":
            self._model = self._model.half()

        total_params = sum(p.numel() for p in self._model.parameters())
        logger.info("model_ready", total_params=total_params)
        self._initialized = True

    @staticmethod
    def _build_model(model_id: str) -> Any:
        """Build the multi-task model architecture.

        Mirrors SigLIP2MultiTaskTeacher from train_siglip2_multitask.py
        but without Modal dependencies.
        """
        import torch
        import torch.nn as nn
        from transformers import AutoModel

        # Head configurations (must match training)
        head_configs: dict[str, dict[str, Any]] = {
            "overall": {
                "hidden_dim": 256,
                "output_dim": 2,
                "dropout": 0.3,
                "type": "regression_uncertainty",
            },
            "sharpness": {
                "hidden_dim": 256,
                "output_dim": 2,
                "dropout": 0.3,
                "type": "regression_uncertainty",
            },
            "color": {
                "hidden_dim": 256,
                "output_dim": 2,
                "dropout": 0.3,
                "type": "regression_uncertainty",
            },
            "script": {
                "hidden_dim": 256,
                "output_dim": len(SCRIPT_ML_CLASSES),
                "dropout": 0.3,
                "type": "classification",
            },
            "source": {
                "hidden_dim": 64,
                "output_dim": len(SOURCE_CLASSES),
                "dropout": 0.0,
                "type": "classification",
            },
            "orientation": {
                "hidden_dim": 64,
                "output_dim": len(ORIENTATION_CLASSES),
                "dropout": 0.0,
                "type": "classification",
            },
            "shadow": {
                "hidden_dim": 64,
                "output_dim": 2,
                "dropout": 0.0,
                "type": "regression_uncertainty",
            },
            "warping": {
                "hidden_dim": 64,
                "output_dim": 2,
                "dropout": 0.0,
                "type": "regression_uncertainty",
            },
        }

        backbone = AutoModel.from_pretrained(model_id)
        embed_dim = backbone.config.vision_config.hidden_size

        heads = nn.ModuleDict()
        head_types: dict[str, str] = {}

        for name, cfg in head_configs.items():
            layers: list[nn.Module] = [
                nn.Linear(embed_dim, cfg["hidden_dim"]),
                nn.ReLU(),
            ]
            if cfg.get("dropout", 0) > 0:
                layers.append(nn.Dropout(cfg["dropout"]))
            layers.append(nn.Linear(cfg["hidden_dim"], cfg["output_dim"]))
            heads[name] = nn.Sequential(*layers)
            head_types[name] = cfg["type"]

        class _MultiTaskModel(nn.Module):
            """Inference-only multi-task model."""

            def __init__(
                self,
                bb: Any,
                hds: nn.ModuleDict,
                htypes: dict[str, str],
            ) -> None:
                super().__init__()
                self.backbone = bb
                self.heads = hds
                self._head_types = htypes
                for hname, hcfg in head_configs.items():
                    if hcfg["type"] == "regression_uncertainty":
                        self.register_buffer(
                            f"temp_{hname}",
                            torch.tensor(1.0),
                        )

            def forward(
                self,
                pixel_values: torch.Tensor,
                spatial_shapes: torch.Tensor | None = None,
                tasks: list[str] | None = None,
            ) -> dict[str, dict[str, torch.Tensor] | torch.Tensor]:
                features = self.backbone.get_image_features(
                    pixel_values=pixel_values,
                    spatial_shapes=spatial_shapes,
                )
                active = list(self.heads.keys()) if tasks is None else tasks
                results: dict[str, Any] = {}
                for task_name in active:
                    if task_name not in self.heads:
                        continue
                    out = self.heads[task_name](features)
                    htype = self._head_types.get(task_name, "classification")
                    if htype == "regression_uncertainty":
                        mu = out[:, 0]
                        log_sigma_sq = out[:, 1]
                        sigma_sq = torch.exp(log_sigma_sq)
                        temp = getattr(self, f"temp_{task_name}")
                        results[task_name] = {
                            "mu": mu,
                            "sigma_sq": temp * sigma_sq,
                            "logits": out,
                        }
                    else:
                        results[task_name] = out
                return results

        return _MultiTaskModel(backbone, heads, head_types)

    def _preprocess(
        self,
        image: np.ndarray,
    ) -> dict[str, Any]:
        """Convert BGR/grayscale numpy image to model inputs.

        Args:
            image: Input image (BGR uint8 or grayscale).

        Returns:
            Dict with pixel_values and spatial_shapes tensors.
        """
        import cv2
        from PIL import Image

        # Convert to RGB PIL
        if len(image.shape) == 2:
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)

        assert self._processor is not None
        inputs = self._processor(
            images=pil_image,
            return_tensors="pt",
            max_num_patches=self.config.max_num_patches,
            padding="max_length",
        )
        return {
            "pixel_values": inputs["pixel_values"].to(self._device),
            "spatial_shapes": inputs["spatial_shapes"].to(self._device),
        }

    def _postprocess(
        self,
        outputs: dict[str, Any],
    ) -> MultiTaskPrediction:
        """Convert raw model outputs to structured prediction.

        Args:
            outputs: Raw model forward pass outputs.

        Returns:
            MultiTaskPrediction with all task results.
        """
        import torch

        def _cls_result(
            logits: torch.Tensor,
            classes: tuple[str, ...] | tuple[int, ...],
        ) -> ClassificationResult:
            probs = torch.softmax(logits[0], dim=-1)
            idx = int(probs.argmax().item())
            dist = {str(c): p.item() for c, p in zip(classes, probs, strict=True)}
            return ClassificationResult(
                predicted_class=str(classes[idx]),
                predicted_idx=int(idx),
                confidence=probs[idx].item(),
                distribution=dist,
            )

        def _iqa_result(task_out: dict[str, torch.Tensor]) -> IQAScore:
            return IQAScore(
                mu=task_out["mu"][0].item(),
                sigma_sq=task_out["sigma_sq"][0].item(),
            )

        def _reg_result(task_out: dict[str, torch.Tensor]) -> RegressionResult:
            return RegressionResult(
                value=task_out["mu"][0].item(),
                sigma_sq=task_out["sigma_sq"][0].item(),
            )

        return MultiTaskPrediction(
            iqa_overall=_iqa_result(outputs["overall"]),
            iqa_sharpness=_iqa_result(outputs["sharpness"]),
            iqa_color=_iqa_result(outputs["color"]),
            script=_cls_result(outputs["script"], SCRIPT_ML_CLASSES),
            source=_cls_result(outputs["source"], SOURCE_CLASSES),
            orientation=_cls_result(
                outputs["orientation"],
                tuple(str(d) for d in ORIENTATION_CLASSES),
            ),
            shadow=_reg_result(outputs["shadow"]),
            warping=_reg_result(outputs["warping"]),
            device=str(self._device),
        )

    def predict(self, image: np.ndarray) -> MultiTaskPrediction:
        """Run multi-task inference on a single image.

        Args:
            image: Input image (BGR uint8 or grayscale numpy array).

        Returns:
            MultiTaskPrediction with all 8 task predictions.

        Raises:
            ValueError: If image is invalid or empty.
        """
        import time

        import torch

        if image is None or image.size == 0:
            msg = "Invalid or empty image provided"
            raise ValueError(msg)

        self._ensure_initialized()
        assert self._device is not None
        assert self._model is not None
        start = time.perf_counter()

        inputs = self._preprocess(image)

        with (
            torch.no_grad(),
            torch.amp.autocast(
                device_type=self._device.type,
                enabled=self.config.use_fp16,
            ),
        ):
            outputs = self._model(**inputs)

        elapsed_ms = (time.perf_counter() - start) * 1000
        result = self._postprocess(outputs)

        # Replace with timing info
        result = MultiTaskPrediction(
            iqa_overall=result.iqa_overall,
            iqa_sharpness=result.iqa_sharpness,
            iqa_color=result.iqa_color,
            script=result.script,
            source=result.source,
            orientation=result.orientation,
            shadow=result.shadow,
            warping=result.warping,
            inference_time_ms=elapsed_ms,
            device=str(self._device),
        )

        logger.debug(
            "siglip2_multitask_predict",
            script=result.script_prediction,
            orientation=result.orientation_degrees,
            quality=f"{result.overall_quality:.3f}",
            time_ms=f"{elapsed_ms:.1f}",
        )

        return result

    def predict_batch(
        self,
        images: list[np.ndarray],
    ) -> list[MultiTaskPrediction]:
        """Run inference on a batch of images.

        Currently processes sequentially. Batch GPU processing
        can be added when NaFlex padding is standardized.

        Args:
            images: List of input images (BGR uint8).

        Returns:
            List of MultiTaskPrediction results.
        """
        return [self.predict(img) for img in images]


# ============================================================================
# Convenience functions
# ============================================================================

# Module-level singleton for pipeline use
_default_detector: SigLIP2MultiTaskDetector | None = None


def get_multitask_detector(
    checkpoint_path: str | Path | None = None,
    config: SigLIP2MultiTaskConfig | None = None,
) -> SigLIP2MultiTaskDetector:
    """Get or create the default multi-task detector singleton.

    Args:
        checkpoint_path: Path to model checkpoint.
        config: Optional configuration.

    Returns:
        Cached SigLIP2MultiTaskDetector instance.
    """
    global _default_detector
    if _default_detector is None:
        _default_detector = SigLIP2MultiTaskDetector(
            checkpoint_path=checkpoint_path,
            config=config,
        )
    return _default_detector


def predict_multitask(
    image: np.ndarray,
    checkpoint_path: str | Path | None = None,
) -> MultiTaskPrediction:
    """Convenience function for single-image prediction.

    Args:
        image: Input image (BGR uint8 or grayscale).
        checkpoint_path: Path to model checkpoint.

    Returns:
        MultiTaskPrediction with all task results.
    """
    detector = get_multitask_detector(checkpoint_path=checkpoint_path)
    return detector.predict(image)


def prediction_to_dict(prediction: MultiTaskPrediction) -> dict[str, Any]:
    """Convert MultiTaskPrediction to JSON-serializable dict.

    Args:
        prediction: Multi-task prediction result.

    Returns:
        Nested dict with all prediction data.
    """
    return {
        "iqa": {
            "overall": {
                "mu": prediction.iqa_overall.mu,
                "sigma_sq": prediction.iqa_overall.sigma_sq,
            },
            "sharpness": {
                "mu": prediction.iqa_sharpness.mu,
                "sigma_sq": prediction.iqa_sharpness.sigma_sq,
            },
            "color": {
                "mu": prediction.iqa_color.mu,
                "sigma_sq": prediction.iqa_color.sigma_sq,
            },
        },
        "script": {
            "predicted": prediction.script.predicted_class,
            "confidence": prediction.script.confidence,
            "distribution": prediction.script.distribution,
        },
        "source": {
            "predicted": prediction.source.predicted_class,
            "confidence": prediction.source.confidence,
        },
        "orientation": {
            "degrees": prediction.orientation_degrees,
            "confidence": prediction.orientation.confidence,
        },
        "shadow": {
            "severity": prediction.shadow.value,
            "sigma_sq": prediction.shadow.sigma_sq,
        },
        "warping": {
            "severity": prediction.warping.value,
            "sigma_sq": prediction.warping.sigma_sq,
        },
        "inference_time_ms": prediction.inference_time_ms,
        "device": prediction.device,
    }


__all__ = [
    "ALL_TASKS",
    "CLASSIFICATION_TASKS",
    "IQA_TASKS",
    "ORIENTATION_CLASSES",
    "REGRESSION_TASKS",
    "SCRIPT_ML_CLASSES",
    "SOURCE_CLASSES",
    "ClassificationResult",
    "IQAScore",
    "MultiTaskPrediction",
    "RegressionResult",
    "SigLIP2MultiTaskConfig",
    "SigLIP2MultiTaskDetector",
    "get_multitask_detector",
    "predict_multitask",
    "prediction_to_dict",
]
