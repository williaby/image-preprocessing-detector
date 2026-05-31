"""DocLayout-YOLO provider for layout detection.

This module provides a YOLO-based enrichment provider for document layout
detection using the DocLayout-YOLO model. Supports batch inference for
GPU efficiency.

Classes:
    YOLOProvider: DocLayout-YOLO layout detection with batch processing

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.yolo import (
    ...     YOLOProvider,
    ... )
    >>>
    >>> provider = YOLOProvider(
    ...     model_path="checkpoints/doclayout_yolo.pt",
    ...     confidence_threshold=0.25,
    ...     batch_size=8,
    ... )
    >>>
    >>> if provider.is_available():
    ...     enrichment = provider.enrich(Path("document.jpg"))
    ...     print(f"Found {len(enrichment.layout_detections)} elements")
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "provider"
__l4_task__ = "layout"
__l4_workstream__ = "WS3"
__l4_provides__ = "yolo_layout_boxes"


import logging
from pathlib import Path
from typing import Any

from ...schemas.enrichment import EnrichmentData
from ..errors import InferenceError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class YOLOProvider:
    """DocLayout-YOLO provider for layout detection.

    Wraps DocLayout-YOLO inference for document layout detection.
    Provides batch processing for GPU efficiency and availability
    checking for robust operation.

    Attributes:
        model_path: Path to YOLO model checkpoint
        confidence_threshold: Minimum confidence for detections (0.0-1.0)
        batch_size: Batch size for inference
        device: Device to use ("cuda", "cpu", or None for auto-detect)
    """

    def __init__(
        self,
        model_path: Path | str | None = None,
        confidence_threshold: float = 0.25,
        batch_size: int = 8,
        device: str | None = None,
    ):
        """Initialize YOLOProvider.

        Args:
            model_path (Path | str | None): Path to YOLO checkpoint (e.g., "doclayout_yolo.pt")
            confidence_threshold (float): Minimum detection confidence (default: 0.25)
            batch_size (int): Batch size for inference (default: 8)
            device (str | None): Device to use (None for auto-detect, "cuda" or "cpu")"""
        self.model_path = Path(model_path) if model_path else None
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        self._device = device
        self._model: Any | None = None

        # Cache device detection result
        self._device_available: bool | None = None

    @property
    def name(self) -> str:
        """Provider name for logging and provenance."""
        return "doclayout_yolo"

    @property
    def tier(self) -> str:
        """Enrichment tier (tier_2_model for ML inference)."""
        return "tier_2_model"

    @property
    def device(self) -> str:
        """Get device for inference (auto-detect if not specified)."""
        if self._device is not None:
            return self._device

        # Auto-detect device
        try:
            import torch

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self._device = "cpu"

        return self._device

    def is_available(self) -> bool:
        """Check if YOLO model is available.

        Checks:
        - Model checkpoint exists
        - Required dependencies installed (ultralytics)
        - GPU available if device is "cuda"

        Returns:
            bool: True if provider can be used"""
        if self._device_available is not None:
            return self._device_available

        # Check model path
        if self.model_path is None or not self.model_path.exists():
            logger.debug(f"YOLO model not found at {self.model_path}")
            self._device_available = False
            return False

        # Check dependencies
        try:
            import ultralytics  # noqa: F401
        except ImportError:
            logger.debug("ultralytics not installed")
            self._device_available = False
            return False

        # Check GPU if required
        if self.device == "cuda":
            try:
                import torch

                if not torch.cuda.is_available():
                    logger.debug("CUDA requested but not available")
                    self._device_available = False
                    return False
            except ImportError:
                logger.debug("torch not installed")
                self._device_available = False
                return False

        self._device_available = True
        return True

    def supports(self, _image_path: Path) -> bool:
        """Check if this image should be processed.

        Currently processes all images. Could be extended to skip
        images that already have layout annotations.

        Args:
            _image_path (Path): Path to image file (unused)

        Returns:
            bool: True (processes all images by default)"""
        return True

    def _ensure_loaded(self) -> None:
        """Lazy-load YOLO model on first use.

        Raises:
            ProviderUnavailableError: If model cannot be loaded
        """
        if self._model is not None:
            return

        if not self.is_available():
            raise ProviderUnavailableError(
                self.name, f"Model not found at {self.model_path}"
            )

        try:
            from ultralytics import YOLO

            logger.info(f"Loading YOLO model from {self.model_path}")
            self._model = YOLO(str(self.model_path))

            # Set device
            if hasattr(self._model, "to"):
                self._model.to(self.device)

            logger.info(f"YOLO model loaded on {self.device}")

        except Exception as e:
            raise ProviderUnavailableError(
                self.name, f"Model loading failed: {e}"
            ) from e

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image with layout detection.

        Args:
            image_path (Path): Path to image file

        Returns:
            EnrichmentData: EnrichmentData with layout_detections populated

        Raises:
            InferenceError: If inference fails
            ProviderUnavailableError: If provider is not available
        """
        return self.enrich_batch([image_path])[0]

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images with batch inference.

        Batch processing provides significant performance benefits:
        - GPU batch inference is much faster than sequential
        - Model loading overhead is amortized across batch
        - Memory usage is more efficient

        Args:
            image_paths (list[Path]): List of image file paths

        Returns:
            list[EnrichmentData]: List of EnrichmentData in same order as image_paths

        Raises:
            InferenceError: If batch inference fails
            ProviderUnavailableError: If provider is not available
        """
        # Short-circuit before loading model for empty batches
        if not image_paths:
            return []

        self._ensure_loaded()

        results: list[EnrichmentData] = []

        # Process in batches
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i : i + self.batch_size]

            try:
                batch_results = self._process_batch(batch_paths)
                results.extend(batch_results)
            except Exception as e:
                # On batch failure, re-raise as InferenceError
                logger.exception("YOLO batch inference failed")
                raise InferenceError(self.name, len(batch_paths), e) from e

        return results

    def _process_batch(self, paths: list[Path]) -> list[EnrichmentData]:
        """Process a single batch through YOLO.

        Args:
            paths (list[Path]): List of image paths in this batch

        Returns:
            list[EnrichmentData]: List of EnrichmentData with layout detections"""
        # Convert paths to strings for YOLO
        image_paths = [str(p) for p in paths]

        # Run inference (model is guaranteed loaded via _ensure_loaded)
        assert self._model is not None
        predictions = self._model.predict(
            image_paths,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )

        # Convert predictions to EnrichmentData
        results = []
        for _path, pred in zip(paths, predictions, strict=True):
            enrichment = EnrichmentData()
            enrichment.layout_detections = self._convert_predictions(pred)
            results.append(enrichment)

        return results

    def _convert_predictions(self, prediction: Any) -> list[dict[str, Any]]:
        """Convert YOLO prediction to LayoutDetection dicts.

        Args:
            prediction (Any): YOLO prediction object

        Returns:
            list[dict[str, Any]]: List of LayoutDetection dictionaries"""
        detections: list[dict[str, Any]] = []

        # Extract boxes, classes, and confidences
        if not hasattr(prediction, "boxes"):
            return detections

        boxes = prediction.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        # Get class names
        names = prediction.names if hasattr(prediction, "names") else {}

        # Convert each detection
        for box in boxes:
            # Get box coordinates (xyxy format)
            xyxy = box.xyxy[0].cpu().numpy() if hasattr(box, "xyxy") else None
            if xyxy is None or len(xyxy) != 4:
                continue

            # Convert to COCO format [x, y, width, height]
            x1, y1, x2, y2 = xyxy
            bbox = [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]

            # Get class and confidence
            cls_id = int(box.cls[0].item()) if hasattr(box, "cls") else 0
            conf = float(box.conf[0].item()) if hasattr(box, "conf") else 0.0

            # Get class name
            class_name = names.get(cls_id, f"class_{cls_id}")

            # Create detection dict (not LayoutDetection dataclass for now)
            detection = {
                "class_name": class_name,
                "bbox": bbox,
                "confidence": conf,
                "source": self.name,
            }
            detections.append(detection)

        return detections


__all__ = ["YOLOProvider"]
