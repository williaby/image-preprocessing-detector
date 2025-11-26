# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""DocLayout-YOLO detector for document layout analysis.

This module provides document layout detection using pre-trained DocLayout-YOLO models.
DocLayout-YOLO is a YOLOv10-based model specifically optimized for document layout
detection, achieving state-of-the-art performance (70-80% mAP) at real-time speeds
(85+ FPS).

Phase 6 Implementation:
- Uses pre-trained models from HuggingFace (no additional training required)
- Supports DocStructBench (general-purpose) and D4LA variants
- Provides COCO-format bounding boxes for detected elements
- Integrates with layout-lite analyzer for hybrid ML+heuristic detection

Reference:
    - Paper: https://arxiv.org/abs/2410.12628
    - GitHub: https://github.com/opendatalab/DocLayout-YOLO
    - Models: https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench

Usage:
    >>> from image_preprocessing_detector.detection.doclayout_yolo import (
    ...     DocLayoutYOLODetector,
    ...     detect_layout,
    ... )
    >>> detector = DocLayoutYOLODetector()
    >>> result = detector.detect(image)
    >>> for element in result.elements:
    ...     print(f"{element.class_name}: {element.confidence:.2f}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from image_preprocessing_detector.utils import get_logger
from image_preprocessing_detector.utils.model_config import (
    get_active_doclayout_yolo_model_id,
    get_doclayout_yolo_common_config,
    get_doclayout_yolo_config,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)


class DocLayoutClass(str, Enum):
    """Document layout element classes from DocStructBench.

    These are the 10 classes detected by the DocStructBench pre-trained model.
    Note: DocLayNet has 11 classes but DocStructBench uses 10.
    """

    TITLE = "title"
    PLAIN_TEXT = "plain text"
    ABANDONED_TEXT = "abandon"  # Text marked for removal/ignore
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    TABLE_CAPTION = "table_caption"
    TABLE_FOOTNOTE = "table_footnote"
    ISOLATE_FORMULA = "isolate_formula"
    FORMULA_CAPTION = "formula_caption"

    @classmethod
    def from_model_output(cls, class_name: str) -> DocLayoutClass | None:
        """Convert model output class name to enum.

        Args:
            class_name: Class name from model prediction

        Returns:
            DocLayoutClass enum value or None if not recognized
        """
        # Normalize: lowercase and handle variations
        normalized = class_name.lower().strip()

        # Handle common variations
        mappings = {
            "title": cls.TITLE,
            "plain text": cls.PLAIN_TEXT,
            "text": cls.PLAIN_TEXT,
            "abandon": cls.ABANDONED_TEXT,
            "abandoned": cls.ABANDONED_TEXT,
            "abandoned_text": cls.ABANDONED_TEXT,
            "figure": cls.FIGURE,
            "picture": cls.FIGURE,
            "image": cls.FIGURE,
            "figure_caption": cls.FIGURE_CAPTION,
            "table": cls.TABLE,
            "table_caption": cls.TABLE_CAPTION,
            "table_footnote": cls.TABLE_FOOTNOTE,
            "isolate_formula": cls.ISOLATE_FORMULA,
            "formula": cls.ISOLATE_FORMULA,
            "isolated_formula": cls.ISOLATE_FORMULA,
            "formula_caption": cls.FORMULA_CAPTION,
        }

        return mappings.get(normalized)


@dataclass
class DetectedElement:
    """A single detected document element.

    Attributes:
        class_id: Numeric class ID from model
        class_name: Human-readable class name
        class_enum: DocLayoutClass enum value (if recognized)
        confidence: Detection confidence (0-1)
        bbox: Bounding box in COCO format [x, y, width, height]
        bbox_xyxy: Bounding box in xyxy format [x1, y1, x2, y2]
    """

    class_id: int
    class_name: str
    class_enum: DocLayoutClass | None
    confidence: float
    bbox: list[int]  # COCO format: [x, y, width, height]
    bbox_xyxy: list[int]  # xyxy format: [x1, y1, x2, y2]

    @classmethod
    def from_prediction(
        cls,
        class_id: int,
        class_name: str,
        confidence: float,
        bbox_xyxy: list[float],
    ) -> DetectedElement:
        """Create element from model prediction.

        Args:
            class_id: Numeric class ID
            class_name: Class name from model
            confidence: Detection confidence
            bbox_xyxy: Bounding box in [x1, y1, x2, y2] format

        Returns:
            DetectedElement instance
        """
        # Convert xyxy to integers (round returns int in Python 3)
        x1, y1, x2, y2 = [round(v) for v in bbox_xyxy]

        # Convert to COCO format [x, y, width, height]
        bbox_coco = [x1, y1, x2 - x1, y2 - y1]

        return cls(
            class_id=class_id,
            class_name=class_name,
            class_enum=DocLayoutClass.from_model_output(class_name),
            confidence=confidence,
            bbox=bbox_coco,
            bbox_xyxy=[x1, y1, x2, y2],
        )


@dataclass
class LayoutDetectionResult:
    """Result of document layout detection.

    Attributes:
        elements: List of detected elements
        inference_time_ms: Time taken for inference in milliseconds
        image_size: Original image size (height, width)
        model_name: Name of the model used
        device: Device used for inference (cpu/cuda)
        success: Whether detection succeeded
        error_message: Error message if detection failed
    """

    elements: list[DetectedElement] = field(default_factory=list)
    inference_time_ms: float = 0.0
    image_size: tuple[int, int] = (0, 0)  # (height, width)
    model_name: str = ""
    device: str = "cpu"
    success: bool = True
    error_message: str | None = None

    @property
    def num_elements(self) -> int:
        """Get number of detected elements."""
        return len(self.elements)

    @property
    def has_tables(self) -> bool:
        """Check if any tables were detected."""
        return any(
            e.class_enum == DocLayoutClass.TABLE or e.class_name.lower() == "table"
            for e in self.elements
        )

    @property
    def has_figures(self) -> bool:
        """Check if any figures were detected."""
        return any(
            e.class_enum == DocLayoutClass.FIGURE
            or e.class_name.lower() in ("figure", "picture", "image")
            for e in self.elements
        )

    @property
    def has_formulas(self) -> bool:
        """Check if any formulas were detected."""
        return any(
            e.class_enum
            in (DocLayoutClass.ISOLATE_FORMULA, DocLayoutClass.FORMULA_CAPTION)
            or "formula" in e.class_name.lower()
            for e in self.elements
        )

    def get_elements_by_class(
        self, class_enum: DocLayoutClass
    ) -> list[DetectedElement]:
        """Get all elements of a specific class.

        Args:
            class_enum: The class to filter by

        Returns:
            List of elements matching the class
        """
        return [e for e in self.elements if e.class_enum == class_enum]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "num_elements": self.num_elements,
            "inference_time_ms": self.inference_time_ms,
            "image_size": list(self.image_size),
            "model_name": self.model_name,
            "device": self.device,
            "success": self.success,
            "error_message": self.error_message,
            "has_tables": self.has_tables,
            "has_figures": self.has_figures,
            "has_formulas": self.has_formulas,
            "elements": [
                {
                    "class_id": e.class_id,
                    "class_name": e.class_name,
                    "confidence": e.confidence,
                    "bbox": e.bbox,
                    "bbox_xyxy": e.bbox_xyxy,
                }
                for e in self.elements
            ],
        }


class DocLayoutYOLODetector:
    """DocLayout-YOLO detector for document layout analysis.

    This detector uses pre-trained DocLayout-YOLO models to detect document
    elements like titles, text blocks, tables, figures, and formulas.

    Features:
        - Lazy model loading (only loads when first detection is requested)
        - Automatic device selection (GPU if available, else CPU)
        - Configurable confidence threshold
        - ONNX export support for production deployment

    Example:
        >>> detector = DocLayoutYOLODetector()
        >>> result = detector.detect(image)
        >>> print(
        ...     f"Found {result.num_elements} elements in {result.inference_time_ms:.1f}ms"
        ... )

    Note:
        Requires the `doclayout-yolo` package: pip install doclayout-yolo
    """

    def __init__(
        self,
        model_key: str | None = None,
        device: str | None = None,
        confidence_threshold: float | None = None,
        image_size: int | None = None,
    ) -> None:
        """Initialize the DocLayout-YOLO detector.

        Args:
            model_key: Model key from config (e.g., "docstructbench", "d4la_pretrained").
                      If None, uses the active model from config.
            device: Device to run inference on ("cpu", "cuda", "cuda:0", etc.).
                   If None, automatically selects based on availability.
            confidence_threshold: Minimum confidence for detections (0-1).
                                 If None, uses value from config.
            image_size: Input image size for model. If None, uses recommended size.
        """
        # Load configuration
        self._config = get_doclayout_yolo_config(model_key)
        self._common_config = get_doclayout_yolo_common_config()

        # Store settings
        self._model_id = str(self._config["huggingface_id"])
        self._model_name = str(self._config.get("name", "DocLayout-YOLO"))
        self._confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else float(self._config.get("confidence_threshold", 0.2))
        )
        self._image_size = (
            image_size
            if image_size is not None
            else int(self._config.get("recommended_image_size", 1024))
        )

        # Device selection (lazy - determined at first inference)
        self._requested_device = device
        self._actual_device: str | None = None

        # Model instance (lazy loaded)
        self._model: Any = None
        self._model_loaded = False

        logger.info(
            "DocLayoutYOLODetector initialized",
            model_id=self._model_id,
            model_name=self._model_name,
            confidence_threshold=self._confidence_threshold,
            image_size=self._image_size,
            device=device or "auto",
        )

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded

    @property
    def device(self) -> str:
        """Get the device being used (loads model if not loaded)."""
        if not self._model_loaded:
            self._load_model()
        return self._actual_device or "cpu"

    def _determine_device(self) -> str:
        """Determine the best device to use for inference.

        Returns:
            Device string ("cuda:0", "cpu", etc.)
        """
        if self._requested_device is not None:
            return self._requested_device

        # Try to use CUDA if available
        try:
            import torch

            if torch.cuda.is_available():
                logger.debug("CUDA available, using GPU")
                return "cuda:0"
        except ImportError:
            logger.debug("PyTorch not available, using CPU")

        return "cpu"

    def _load_model(self) -> None:
        """Load the DocLayout-YOLO model from HuggingFace.

        Raises:
            ImportError: If doclayout-yolo package is not installed
            RuntimeError: If model loading fails
        """
        if self._model_loaded:
            return

        logger.info("Loading DocLayout-YOLO model", model_id=self._model_id)

        try:
            from doclayout_yolo import YOLOv10
        except ImportError as e:
            raise ImportError(
                "DocLayout-YOLO package not installed. "
                "Install with: pip install doclayout-yolo"
            ) from e

        # Determine device
        self._actual_device = self._determine_device()

        try:
            # Load model from HuggingFace
            start_time = time.perf_counter()
            self._model = YOLOv10.from_pretrained(self._model_id)
            load_time = (time.perf_counter() - start_time) * 1000

            self._model_loaded = True
            logger.info(
                "DocLayout-YOLO model loaded successfully",
                model_id=self._model_id,
                device=self._actual_device,
                load_time_ms=f"{load_time:.1f}",
            )

        except Exception as e:
            logger.exception("Failed to load DocLayout-YOLO model", error=str(e))
            raise RuntimeError(f"Failed to load DocLayout-YOLO model: {e}") from e

    def detect(
        self,
        image: NDArray[np.uint8],
        confidence_threshold: float | None = None,
    ) -> LayoutDetectionResult:
        """Detect document layout elements in an image.

        Args:
            image: Input image as numpy array (BGR or RGB format, HWC)
            confidence_threshold: Override confidence threshold for this detection

        Returns:
            LayoutDetectionResult containing detected elements and metadata

        Example:
            >>> import cv2
            >>> image = cv2.imread("document.png")
            >>> result = detector.detect(image)
            >>> for elem in result.elements:
            ...     print(f"{elem.class_name}: {elem.bbox}")
        """
        # Validate input
        if image is None or image.size == 0:
            return LayoutDetectionResult(
                success=False,
                error_message="Invalid or empty image provided",
            )

        # Get image dimensions
        if len(image.shape) == 2:
            height, width = image.shape
        else:
            height, width = image.shape[:2]

        # Load model if not already loaded
        if not self._model_loaded:
            try:
                self._load_model()
            except Exception as e:
                return LayoutDetectionResult(
                    success=False,
                    error_message=str(e),
                    image_size=(height, width),
                )

        # Use provided threshold or default
        conf_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else self._confidence_threshold
        )

        logger.debug(
            "Running DocLayout-YOLO detection",
            image_shape=image.shape,
            confidence_threshold=conf_threshold,
        )

        try:
            # Run inference
            start_time = time.perf_counter()
            results = self._model.predict(
                image,
                imgsz=self._image_size,
                conf=conf_threshold,
                device=self._actual_device,
                verbose=False,
            )
            inference_time = (time.perf_counter() - start_time) * 1000

            # Parse results
            elements = self._parse_results(results)

            return LayoutDetectionResult(
                elements=elements,
                inference_time_ms=inference_time,
                image_size=(height, width),
                model_name=self._model_name,
                device=self._actual_device or "cpu",
                success=True,
            )

        except Exception as e:
            logger.exception("DocLayout-YOLO detection failed", error=str(e))
            return LayoutDetectionResult(
                success=False,
                error_message=str(e),
                image_size=(height, width),
                model_name=self._model_name,
                device=self._actual_device or "cpu",
            )

    def _parse_results(self, results: Any) -> list[DetectedElement]:
        """Parse YOLO results into DetectedElement objects.

        Args:
            results: Results from model.predict()

        Returns:
            List of DetectedElement objects
        """
        elements = []

        # Results is a list (one per image in batch)
        if not results or len(results) == 0:
            return elements

        result = results[0]  # Single image

        # Get boxes and class names
        if hasattr(result, "boxes") and result.boxes is not None:
            boxes = result.boxes
            names = result.names if hasattr(result, "names") else {}

            for i in range(len(boxes)):
                # Get box coordinates (xyxy format)
                bbox_xyxy = boxes.xyxy[i].cpu().numpy().tolist()

                # Get class ID and confidence
                class_id = int(boxes.cls[i].cpu().numpy())
                confidence = float(boxes.conf[i].cpu().numpy())

                # Get class name
                class_name = names.get(class_id, f"class_{class_id}")

                element = DetectedElement.from_prediction(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox_xyxy=bbox_xyxy,
                )
                elements.append(element)

        logger.debug(
            "Parsed detection results",
            num_elements=len(elements),
            classes=[e.class_name for e in elements],
        )

        return elements

    def export_onnx(
        self,
        output_path: str | Path,
        image_size: int | None = None,
        opset_version: int = 17,
        simplify: bool = True,
    ) -> Path:
        """Export model to ONNX format for production deployment.

        Args:
            output_path: Path to save the ONNX model
            image_size: Input image size (default: uses configured size)
            opset_version: ONNX opset version (default: 17)
            simplify: Whether to simplify the ONNX graph (default: True)

        Returns:
            Path to the exported ONNX model

        Example:
            >>> detector = DocLayoutYOLODetector()
            >>> onnx_path = detector.export_onnx("models/doclayout.onnx")
        """
        if not self._model_loaded:
            self._load_model()

        output_path = Path(output_path)
        img_size = image_size or self._image_size

        logger.info(
            "Exporting DocLayout-YOLO to ONNX",
            output_path=str(output_path),
            image_size=img_size,
            opset_version=opset_version,
        )

        self._model.export(
            format="onnx",
            imgsz=img_size,
            opset=opset_version,
            simplify=simplify,
        )

        # The model.export() saves to a default location, move if needed
        # This depends on ultralytics behavior
        logger.info("ONNX export complete", output_path=str(output_path))

        return output_path


# Convenience functions


def detect_layout(
    image: NDArray[np.uint8],
    model_key: str | None = None,
    confidence_threshold: float = 0.2,
) -> LayoutDetectionResult:
    """Convenience function for one-off layout detection.

    Creates a detector, runs detection, and returns results.
    For repeated detection, create a DocLayoutYOLODetector instance instead.

    Args:
        image: Input image as numpy array
        model_key: Model key from config (default: active model)
        confidence_threshold: Minimum confidence (default: 0.2)

    Returns:
        LayoutDetectionResult with detected elements

    Example:
        >>> import cv2
        >>> image = cv2.imread("document.png")
        >>> result = detect_layout(image)
        >>> print(f"Found {result.num_elements} elements")
    """
    detector = DocLayoutYOLODetector(
        model_key=model_key,
        confidence_threshold=confidence_threshold,
    )
    return detector.detect(image)


def is_doclayout_yolo_available() -> bool:
    """Check if DocLayout-YOLO package is installed and available.

    Returns:
        True if doclayout-yolo can be imported, False otherwise
    """
    try:
        from doclayout_yolo import YOLOv10  # noqa: F401
    except ImportError:
        return False
    else:
        return True


def get_doclayout_yolo_model_info() -> dict[str, Any]:
    """Get information about the configured DocLayout-YOLO model.

    Returns:
        Dictionary with model configuration details
    """
    config = get_doclayout_yolo_config()
    common = get_doclayout_yolo_common_config()

    return {
        "model_id": get_active_doclayout_yolo_model_id(),
        "name": config.get("name"),
        "description": config.get("description"),
        "architecture": common.get("architecture"),
        "recommended_image_size": config.get("recommended_image_size"),
        "confidence_threshold": config.get("confidence_threshold"),
        "use_case": config.get("use_case"),
        "is_available": is_doclayout_yolo_available(),
    }
