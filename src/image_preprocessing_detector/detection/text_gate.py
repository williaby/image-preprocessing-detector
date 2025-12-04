"""Text detection gate for routing documents in the preprocessing pipeline.

Uses an ensemble of fast heuristics to determine if a document contains text:
- Morphological stroke density
- Connected components analysis
- Edge density patterns
"""

from dataclasses import dataclass

import cv2
import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Detection thresholds and constants
DEFAULT_STROKE_THRESHOLD = 0.05  # Minimum stroke density for text
DEFAULT_MIN_TEXT_COMPONENTS = 10  # Minimum text-like components
DEFAULT_EDGE_THRESHOLD_LOW = 50  # Canny low threshold
DEFAULT_EDGE_THRESHOLD_HIGH = 150  # Canny high threshold
DEFAULT_MIN_COMPONENT_AREA = 20  # Minimum component area in pixels
DEFAULT_MAX_COMPONENT_AREA = 5000  # Maximum component area in pixels
DEFAULT_MIN_ASPECT_RATIO = 0.1  # Minimum aspect ratio for text
DEFAULT_MAX_ASPECT_RATIO = 10.0  # Maximum aspect ratio for text

# Morphological gradient constants
MORPH_GRADIENT_THRESHOLD = 30  # Moderate threshold for edge detection
MORPH_KERNEL_SIZE = (3, 3)  # Kernel size for morphological operations
COMPONENT_SCORE_MULTIPLIER = 2  # Multiplier for normalizing component score

# Confidence weights for ensemble
WEIGHT_STROKE = 0.4  # Weight for stroke density in confidence calculation
WEIGHT_COMPONENT = 0.4  # Weight for component analysis in confidence calculation
WEIGHT_EDGE = 0.2  # Weight for edge density in confidence calculation


@dataclass
class TextDetectionResult:
    """Result of text detection analysis.

    Attributes:
        has_text: Whether text is detected in the image
        confidence: Overall confidence score (0.0-1.0)
        stroke_density: Morphological stroke density score
        component_score: Connected components text score
        edge_score: Edge density text score
    """

    has_text: bool
    confidence: float
    stroke_density: float
    component_score: float
    edge_score: float


class TextGate:
    """Text detection gate for document routing.

    Uses ensemble of fast classical CV methods to detect text presence.
    Optimized for speed (< 50ms per page on CPU).
    """

    def __init__(
        self,
        stroke_threshold: float = DEFAULT_STROKE_THRESHOLD,
        min_text_components: int = DEFAULT_MIN_TEXT_COMPONENTS,
        edge_threshold_low: int = DEFAULT_EDGE_THRESHOLD_LOW,
        edge_threshold_high: int = DEFAULT_EDGE_THRESHOLD_HIGH,
        min_component_area: int = DEFAULT_MIN_COMPONENT_AREA,
        max_component_area: int = DEFAULT_MAX_COMPONENT_AREA,
        min_aspect_ratio: float = DEFAULT_MIN_ASPECT_RATIO,
        max_aspect_ratio: float = DEFAULT_MAX_ASPECT_RATIO,
    ) -> None:
        """Initialize text detection gate.

        Args:
            stroke_threshold: Minimum stroke density for text (default: 0.05)
            min_text_components: Minimum text-like components (default: 10)
            edge_threshold_low: Canny low threshold (default: 50)
            edge_threshold_high: Canny high threshold (default: 150)
            min_component_area: Minimum component area in pixels (default: 20)
            max_component_area: Maximum component area in pixels (default: 5000)
            min_aspect_ratio: Minimum aspect ratio for text (default: 0.1)
            max_aspect_ratio: Maximum aspect ratio for text (default: 10.0)
        """
        self.stroke_threshold = stroke_threshold
        self.min_text_components = min_text_components
        self.edge_threshold_low = edge_threshold_low
        self.edge_threshold_high = edge_threshold_high
        self.min_component_area = min_component_area
        self.max_component_area = max_component_area
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio

        logger.info(
            "Text gate initialized",
            stroke_threshold=stroke_threshold,
            min_text_components=min_text_components,
        )

    def detect(self, image: np.ndarray) -> TextDetectionResult:
        """Detect text presence in an image.

        Args:
            image: Input image (BGR format, from OpenCV)

        Returns:
            TextDetectionResult with detection decision and confidence scores

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError(
                f"Expected BGR image with shape (H, W, 3), got {image.shape}"
            )

        logger.debug("Running text detection", image_shape=image.shape)

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Run all detection methods
        stroke_density = self._compute_stroke_density(gray)
        component_score = self._analyze_connected_components(gray)
        edge_score = self._compute_edge_density(gray)

        # Ensemble decision with weighted average
        confidence = self._compute_confidence(
            stroke_density, component_score, edge_score
        )

        # Decision logic: text detected if stroke density OR component count is high
        has_text = (stroke_density > self.stroke_threshold) or (
            component_score > 0.5
        )  # component_score > 0.5 means >= min_text_components

        logger.debug(
            "Text detection complete",
            has_text=has_text,
            confidence=confidence,
            stroke_density=stroke_density,
            component_score=component_score,
            edge_score=edge_score,
        )

        return TextDetectionResult(
            has_text=has_text,
            confidence=confidence,
            stroke_density=stroke_density,
            component_score=component_score,
            edge_score=edge_score,
        )

    def _compute_stroke_density(self, gray: np.ndarray) -> float:
        """Compute morphological stroke density.

        Text has high stroke density due to character edges and strokes.

        Args:
            gray: Grayscale image

        Returns:
            Stroke density score (0.0-1.0)
        """
        # Apply morphological gradient to detect edges/strokes
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_SIZE)
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

        # Threshold and count pixels
        stroke_pixels = np.count_nonzero(gradient > MORPH_GRADIENT_THRESHOLD)
        total_pixels = gradient.size

        return float(stroke_pixels / total_pixels) if total_pixels > 0 else 0.0

    def _analyze_connected_components(self, gray: np.ndarray) -> float:
        """Analyze connected components for text-like structures.

        Text typically consists of many small components with specific aspect ratios.

        Args:
            gray: Grayscale image

        Returns:
            Component score (0.0-1.0) based on text-like component count
        """
        # Binarize image with Otsu's method
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find connected components
        num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        text_component_count = 0

        # Analyze each component (skip background label 0)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]

            # Filter by area
            if area < self.min_component_area or area > self.max_component_area:
                continue

            # Calculate aspect ratio
            if height == 0 or width == 0:
                continue

            aspect_ratio = max(width, height) / min(width, height)

            # Text-like components have aspect ratios between 1:2 and 10:1
            if self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio:
                text_component_count += 1

        # Normalize score: sigmoid-like function
        # Score approaches 1.0 as component count exceeds min_text_components
        return min(
            1.0,
            text_component_count
            / (self.min_text_components * COMPONENT_SCORE_MULTIPLIER),
        )

    def _compute_edge_density(self, gray: np.ndarray) -> float:
        """Compute edge density using Canny edge detection.

        Text regions have consistent edge patterns due to character boundaries.

        Args:
            gray: Grayscale image

        Returns:
            Edge density score (0.0-1.0)
        """
        # Apply Canny edge detection
        edges = cv2.Canny(gray, self.edge_threshold_low, self.edge_threshold_high)

        # Calculate edge density
        edge_pixels = np.count_nonzero(edges)
        total_pixels = edges.size

        return float(edge_pixels / total_pixels) if total_pixels > 0 else 0.0

    def _compute_confidence(
        self, stroke_density: float, component_score: float, edge_score: float
    ) -> float:
        """Compute overall confidence using weighted average.

        Weights prioritize stroke density and component analysis over edge density.

        Args:
            stroke_density: Stroke density score
            component_score: Component analysis score
            edge_score: Edge density score

        Returns:
            Weighted confidence score (0.0-1.0)
        """
        # Weighted average: stroke and components are more reliable
        confidence = (
            WEIGHT_STROKE * stroke_density
            + WEIGHT_COMPONENT * component_score
            + WEIGHT_EDGE * edge_score
        )

        return min(1.0, max(0.0, confidence))


def detect_text(
    image: np.ndarray,
    stroke_threshold: float = DEFAULT_STROKE_THRESHOLD,
    min_text_components: int = DEFAULT_MIN_TEXT_COMPONENTS,
) -> TextDetectionResult:
    """Convenience function for text detection.

    Args:
        image: Input image (BGR format)
        stroke_threshold: Minimum stroke density for text (default: 0.05)
        min_text_components: Minimum text-like components (default: 10)

    Returns:
        TextDetectionResult with detection decision and scores

    Example:
        >>> import cv2
        >>> img = cv2.imread("document.jpg")
        >>> result = detect_text(img)
        >>> if result.has_text:
        ...     print(f"Text detected with {result.confidence:.2%} confidence")
    """
    gate = TextGate(
        stroke_threshold=stroke_threshold,
        min_text_components=min_text_components,
    )
    return gate.detect(image)


# Example usage
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python text_gate.py <image_path>")
        sys.exit(1)

    from image_preprocessing_detector.utils import setup_logging

    setup_logging(level="DEBUG", json_logs=False)

    image_path = sys.argv[1]
    img = cv2.imread(image_path)

    if img is None:
        logger.error("Failed to load image", path=image_path)
        sys.exit(1)

    gate = TextGate()
    result = gate.detect(img)

    print(f"\n{'=' * 60}")
    print(f"Text Detection Results for: {image_path}")
    print(f"{'=' * 60}")
    print(f"Has Text:         {'YES' if result.has_text else 'NO'}")
    print(f"Confidence:       {result.confidence:.2%}")
    print(f"Stroke Density:   {result.stroke_density:.4f}")
    print(f"Component Score:  {result.component_score:.4f}")
    print(f"Edge Score:       {result.edge_score:.4f}")
    print(f"{'=' * 60}\n")
