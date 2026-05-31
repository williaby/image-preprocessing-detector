"""Document Orientation Detection Module.

Detects document orientation (0°, 90°, 180°, 270°) for rotated scans/photos.
Uses a multi-method ensemble approach with consensus voting.

Phase 8 Implementation - Addresses common scanning/photography issues where
documents are captured at incorrect orientations.
"""

from dataclasses import dataclass
from enum import IntEnum

import cv2
import numpy as np

from image_preprocessing_detector.schema import OrientationAngle, OrientationDetection
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class DetectionMethod(IntEnum):
    """Detection methods used in the ensemble."""

    TEXT_LINE_ANALYSIS = 1
    EDGE_HISTOGRAM = 2
    COMPONENT_RATIO = 3


@dataclass
class OrientationVote:
    """Vote from a single detection method."""

    method: str
    angle: int  # 0, 90, 180, 270
    confidence: float
    details: dict


@dataclass
class OrientationConfig:
    """Configuration for orientation detection.

    Attributes:
        consensus_required (int): Number of methods that must agree (default: 2 of 3)
        min_confidence (float): Minimum confidence to accept detection (default: 0.6)
        auto_correct_threshold (float): Confidence threshold for auto-correction (default: 0.8)
        hough_threshold (int): Threshold for Hough line detection
        min_line_length (int): Minimum line length for Hough transform
        max_line_gap (int): Maximum gap between line segments
        edge_canny_low (int): Canny edge detection low threshold
        edge_canny_high (int): Canny edge detection high threshold
        min_component_area (int): Minimum area for connected component analysis
    """

    consensus_required: int = 2
    min_confidence: float = 0.6
    auto_correct_threshold: float = 0.8
    hough_threshold: int = 50
    min_line_length: int = 50
    max_line_gap: int = 10
    edge_canny_low: int = 50
    edge_canny_high: int = 150
    min_component_area: int = 20


class OrientationDetector:
    """Multi-method ensemble detector for document orientation.

    Uses three complementary methods to detect if a document is rotated:
    1. Text Line Analysis: Detects dominant text line angles using Hough transform
    2. Edge Histogram: Analyzes edge orientation distribution
    3. Component Ratio: Analyzes aspect ratios of text-like connected components

    Requires consensus (default 2/3) for reliable detection.

    Args:
        config (OrientationConfig | None): Configuration options. Uses defaults if not provided.

    Example:
        >>> detector = OrientationDetector()
        >>> image = cv2.imread("rotated_scan.jpg")
        >>> result = detector.detect(image)
        >>> if result.needs_correction:
        ...     print(f"Document rotated {result.detected_angle}°")
    """

    def __init__(self, config: OrientationConfig | None = None) -> None:
        self.config = config or OrientationConfig()

    def detect(self, image: np.ndarray) -> OrientationDetection:
        """Detect document orientation using ensemble of methods.

        Args:
            image: Input image as numpy array (BGR or grayscale)

        Returns:
            OrientationDetection with detected angle, confidence, and method details
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Get votes from all methods
        votes = []

        # Method 1: Text line analysis
        text_vote = self._detect_via_text_lines(gray)
        if text_vote is not None:
            votes.append(text_vote)

        # Method 2: Edge histogram
        edge_vote = self._detect_via_edge_histogram(gray)
        if edge_vote is not None:
            votes.append(edge_vote)

        # Method 3: Component aspect ratio
        component_vote = self._detect_via_component_ratio(gray)
        if component_vote is not None:
            votes.append(component_vote)

        # Aggregate votes
        return self._aggregate_votes(votes)

    def _detect_via_text_lines(self, gray: np.ndarray) -> OrientationVote | None:
        """Detect orientation using text line angle analysis.

        Uses Hough transform to detect lines and analyzes their dominant angle.
        Text typically runs horizontal; 90°/270° rotation shows vertical lines.

        Args:
            gray: Grayscale image

        Returns:
            OrientationVote or None if detection fails
        """
        # Edge detection
        edges = cv2.Canny(gray, self.config.edge_canny_low, self.config.edge_canny_high)

        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.config.hough_threshold,
            minLineLength=self.config.min_line_length,
            maxLineGap=self.config.max_line_gap,
        )

        if lines is None or len(lines) < 5:
            logger.debug("Text line analysis: insufficient lines detected")
            return None

        # Calculate angles of all lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Calculate angle in degrees (-90 to 90)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)

        angles = np.array(angles)

        # Classify angles into orientation bins
        # Horizontal lines (0°) → upright document
        # Vertical lines (±90°) → 90°/270° rotated
        horizontal_count = np.sum(np.abs(angles) < 30)
        vertical_count = np.sum((np.abs(angles) > 60) & (np.abs(angles) < 120))

        total_lines = len(angles)

        # Determine dominant orientation
        if horizontal_count > vertical_count:
            # Document appears upright or 180° rotated
            # Use text baseline analysis for 180° detection
            orientation_180 = self._detect_180_rotation(gray)
            if orientation_180:
                detected_angle = 180
                confidence = 0.7  # 180° is harder to detect reliably
            else:
                detected_angle = 0
                confidence = horizontal_count / total_lines
        else:
            # Document appears 90° or 270° rotated
            # Analyze which direction based on text flow
            mean_angle = np.mean(angles[np.abs(angles) > 45])
            detected_angle = 90 if mean_angle > 0 else 270
            confidence = vertical_count / total_lines

        logger.debug(
            "Text line analysis result",
            detected_angle=detected_angle,
            confidence=confidence,
            horizontal_count=horizontal_count,
            vertical_count=vertical_count,
            total_lines=total_lines,
        )

        return OrientationVote(
            method="text_line_analysis",
            angle=detected_angle,
            confidence=min(1.0, confidence),
            details={
                "horizontal_count": int(horizontal_count),
                "vertical_count": int(vertical_count),
                "total_lines": total_lines,
            },
        )

    def _detect_180_rotation(self, gray: np.ndarray) -> bool:
        """Detect 180° rotation by analyzing text baseline position.

        In upright text, descenders (g, y, p) go below baseline.
        In 180° rotated text, they appear above the baseline.

        Args:
            gray: Grayscale image

        Returns:
            True if 180° rotation is detected
        """
        # This is a simplified heuristic - could be enhanced with ML
        # For now, use intensity distribution analysis

        # Divide image into top and bottom halves
        h, _w = gray.shape
        top_half = gray[: h // 2, :]
        bottom_half = gray[h // 2 :, :]

        # In upright documents, top often has headers/titles (less dense)
        # and bottom has body text (more dense with descenders)
        top_intensity = np.mean(top_half)
        bottom_intensity = np.mean(bottom_half)

        # If bottom is significantly darker (more ink), likely upright
        # If top is significantly darker, might be 180° rotated
        # This is a weak signal, so we use a small confidence boost
        intensity_diff = top_intensity - bottom_intensity

        # Threshold for detecting 180° rotation (positive diff = darker bottom = upright)
        return intensity_diff < -10  # Darker top suggests 180° rotation

    def _detect_via_edge_histogram(self, gray: np.ndarray) -> OrientationVote | None:
        """Detect orientation using edge orientation histogram.

        Analyzes the distribution of edge orientations. Document edges should be
        predominantly horizontal/vertical. 90° rotation swaps H/V distributions.

        Args:
            gray: Grayscale image

        Returns:
            OrientationVote or None if detection fails
        """
        # Compute gradients
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        # Calculate edge orientations
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        orientation = np.arctan2(sobel_y, sobel_x) * 180 / np.pi

        # Filter by magnitude (only strong edges)
        threshold = np.percentile(magnitude, 75)
        strong_edges_mask = magnitude > threshold
        strong_orientations = orientation[strong_edges_mask]

        if len(strong_orientations) < 100:
            logger.debug("Edge histogram: insufficient strong edges")
            return None

        # Build histogram of orientations
        hist, _bin_edges = np.histogram(strong_orientations, bins=36, range=(-180, 180))

        # Find dominant orientations (peaks in histogram)
        # Horizontal edges: around 0° or ±180°
        # Vertical edges: around ±90°

        horizontal_bins = list(range(3)) + list(range(33, 36))  # -10° to 10°
        vertical_bins = list(range(7, 11)) + list(range(25, 29))  # 70°-110°, -110°--70°

        horizontal_strength = sum(hist[i] for i in horizontal_bins)
        vertical_strength = sum(hist[i] for i in vertical_bins)

        total_strength = horizontal_strength + vertical_strength
        if total_strength == 0:
            logger.debug("Edge histogram: no dominant orientations")
            return None

        # Determine orientation
        if horizontal_strength > vertical_strength * 1.5:
            # Strong horizontal dominance → upright or 180°
            detected_angle = 0  # Assume upright (180° requires additional analysis)
            confidence = horizontal_strength / total_strength
        elif vertical_strength > horizontal_strength * 1.5:
            # Strong vertical dominance → 90° or 270°
            # Determine direction based on gradient direction distribution
            vertical_orientations = strong_orientations[
                (np.abs(strong_orientations) > 60) & (np.abs(strong_orientations) < 120)
            ]
            mean_vertical = (
                np.mean(vertical_orientations) if len(vertical_orientations) > 0 else 90
            )
            detected_angle = 90 if mean_vertical > 0 else 270
            confidence = vertical_strength / total_strength
        else:
            # Mixed - no clear orientation
            detected_angle = 0
            confidence = 0.5

        logger.debug(
            "Edge histogram result",
            detected_angle=detected_angle,
            confidence=confidence,
            horizontal_strength=horizontal_strength,
            vertical_strength=vertical_strength,
        )

        return OrientationVote(
            method="edge_histogram",
            angle=detected_angle,
            confidence=min(1.0, confidence),
            details={
                "horizontal_strength": int(horizontal_strength),
                "vertical_strength": int(vertical_strength),
            },
        )

    def _detect_via_component_ratio(self, gray: np.ndarray) -> OrientationVote | None:
        """Detect orientation using connected component aspect ratios.

        Text characters in Latin scripts are typically taller than wide.
        If most components are wider than tall, document may be 90°/270° rotated.

        Args:
            gray: Grayscale image

        Returns:
            OrientationVote or None if detection fails
        """
        # Binarize
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find connected components
        num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        if num_labels < 10:
            logger.debug("Component ratio: insufficient components")
            return None

        # Analyze aspect ratios of text-sized components
        aspect_ratios = []
        min_area = self.config.min_component_area
        max_area = (gray.shape[0] * gray.shape[1]) / 10  # Max 10% of image

        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]

            if min_area < area < max_area and width > 0 and height > 0:
                # Aspect ratio: height / width
                # > 1 means taller than wide (normal upright text)
                # < 1 means wider than tall (rotated text)
                ratio = height / width
                aspect_ratios.append(ratio)

        if len(aspect_ratios) < 20:
            logger.debug("Component ratio: insufficient text-sized components")
            return None

        # Calculate statistics
        aspect_ratios = np.array(aspect_ratios)
        median_ratio = np.median(aspect_ratios)
        tall_count = np.sum(aspect_ratios > 1.0)
        wide_count = np.sum(aspect_ratios < 1.0)

        total = len(aspect_ratios)

        # Determine orientation
        if tall_count > wide_count * 1.3:
            # More tall components → upright or 180°
            detected_angle = 0
            confidence = tall_count / total
        elif wide_count > tall_count * 1.3:
            # More wide components → 90° or 270° rotated
            detected_angle = (
                90  # Default to 90°, combine with other methods for direction
            )
            confidence = wide_count / total
        else:
            # Mixed - no clear orientation
            detected_angle = 0
            confidence = 0.5

        logger.debug(
            "Component ratio result",
            detected_angle=detected_angle,
            confidence=confidence,
            median_ratio=median_ratio,
            tall_count=tall_count,
            wide_count=wide_count,
        )

        return OrientationVote(
            method="component_ratio",
            angle=detected_angle,
            confidence=min(1.0, confidence),
            details={
                "median_ratio": float(median_ratio),
                "tall_count": int(tall_count),
                "wide_count": int(wide_count),
                "total_components": total,
            },
        )

    def _aggregate_votes(self, votes: list[OrientationVote]) -> OrientationDetection:
        """Aggregate votes from multiple methods using consensus.

        Args:
            votes: List of votes from detection methods

        Returns:
            Final OrientationDetection result
        """
        if not votes:
            logger.warning("No orientation votes received, defaulting to upright")
            return OrientationDetection(
                detected_angle=OrientationAngle.UPRIGHT,
                confidence=0.0,
                detection_method="none",
                auto_corrected=False,
                needs_correction=False,
                method_votes={},
            )

        # Count votes per angle
        angle_votes: dict[int, list[OrientationVote]] = {
            0: [],
            90: [],
            180: [],
            270: [],
        }
        for vote in votes:
            # Normalize angles to valid values
            normalized_angle = self._normalize_angle(vote.angle)
            angle_votes[normalized_angle].append(vote)

        # Find angle with most votes
        best_angle = max(angle_votes.keys(), key=lambda a: len(angle_votes[a]))
        best_votes = angle_votes[best_angle]

        # Check consensus
        consensus_met = len(best_votes) >= self.config.consensus_required

        # Calculate combined confidence
        if best_votes:
            # Weight by individual confidences
            confidences = [v.confidence for v in best_votes]
            combined_confidence = np.mean(confidences) * (len(best_votes) / len(votes))
        else:
            combined_confidence = 0.0

        # Determine if correction is needed
        needs_correction = best_angle != 0

        # Determine if auto-correction should be applied
        auto_correct = (
            consensus_met
            and needs_correction
            and combined_confidence >= self.config.auto_correct_threshold
        )

        # Build method votes dict
        method_votes_dict = {vote.method: vote.angle for vote in votes}

        # Determine detection method string
        if len(best_votes) == len(votes):
            detection_method = "ensemble_unanimous"
        elif consensus_met:
            detection_method = "ensemble_consensus"
        elif best_votes:
            detection_method = best_votes[0].method
        else:
            detection_method = "none"

        # Map to OrientationAngle enum
        angle_enum = self._angle_to_enum(best_angle if consensus_met else 0)

        logger.info(
            "Orientation detection complete",
            detected_angle=angle_enum.value,
            confidence=combined_confidence,
            consensus_met=consensus_met,
            needs_correction=needs_correction,
            auto_correct=auto_correct,
            method_votes=method_votes_dict,
        )

        return OrientationDetection(
            detected_angle=angle_enum,
            confidence=round(combined_confidence, 3),
            detection_method=detection_method,
            auto_corrected=False,  # Will be set to True if correction is applied
            needs_correction=needs_correction and consensus_met,
            method_votes=method_votes_dict,
        )

    def _normalize_angle(self, angle: int) -> int:
        """Normalize angle to nearest valid orientation (0, 90, 180, 270)."""
        angle = angle % 360
        if angle < 45:
            return 0
        if angle < 135:
            return 90
        if angle < 225:
            return 180
        if angle < 315:
            return 270
        return 0

    def _angle_to_enum(self, angle: int) -> OrientationAngle:
        """Convert integer angle to OrientationAngle enum."""
        mapping = {
            0: OrientationAngle.UPRIGHT,
            90: OrientationAngle.ROTATED_90,
            180: OrientationAngle.ROTATED_180,
            270: OrientationAngle.ROTATED_270,
        }
        return mapping.get(angle, OrientationAngle.UPRIGHT)


def detect_orientation(
    image: np.ndarray,
    config: OrientationConfig | None = None,
) -> OrientationDetection:
    """Convenience function to detect document orientation.

    Args:
        image: Input image as numpy array (BGR or grayscale)
        config: Configuration options. Uses defaults if not provided.

    Returns:
        OrientationDetection with detected angle and confidence

    Example:
        >>> import cv2
        >>> from image_preprocessing_detector.detection.orientation_detector import (
        ...     detect_orientation,
        ... )
        >>> image = cv2.imread("document.jpg")
        >>> result = detect_orientation(image)
        >>> print(
        ...     f"Orientation: {result.detected_angle}°, Confidence: {result.confidence}"
        ... )
    """
    detector = OrientationDetector(config)
    return detector.detect(image)


def correct_orientation(
    image: np.ndarray,
    detection: OrientationDetection,
) -> tuple[np.ndarray, bool]:
    """Apply orientation correction to image if needed.

    Args:
        image: Input image as numpy array
        detection: OrientationDetection result from detect_orientation

    Returns:
        Tuple of (corrected_image, was_corrected)

    Example:
        >>> detection = detect_orientation(image)
        >>> corrected, was_corrected = correct_orientation(image, detection)
        >>> if was_corrected:
        ...     print(f"Rotated image by -{detection.detected_angle}°")
    """
    if not detection.needs_correction:
        return image, False

    angle = detection.detected_angle.value
    if angle == 0:
        return image, False

    # Rotate counter-clockwise to correct
    rotation_code = {
        90: cv2.ROTATE_90_COUNTERCLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_CLOCKWISE,
    }

    rotated = cv2.rotate(image, rotation_code[angle])

    logger.info(
        "Applied orientation correction",
        original_angle=angle,
        rotation_applied=f"-{angle}°",
    )

    return rotated, True
