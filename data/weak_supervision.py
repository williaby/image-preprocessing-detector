"""Weak supervision labeling system for IQA training.

Automatically generates quality issue labels using reference-free image quality metrics:
- BRISQUE: Blind/Referenceless Image Spatial Quality Evaluator (PLACEHOLDER)
- NIQE: Natural Image Quality Evaluator (PLACEHOLDER)
- Laplacian Variance: Blur detection
- RMS Contrast: Low contrast detection
- Hough Transform: Skew detection
- Edge straightness: Perspective distortion

Phase 2 - Week 1: Data Collection & Augmentation

Known Limitations:
    - BRISQUE: Currently uses simplified noise estimation placeholder.
      Full implementation requires cv2.quality.QualityBRISQUE module.
    - NIQE: Currently uses simplified gradient statistics placeholder.
      Full implementation requires cv2.quality.QualityNIQE module.

    These placeholders are functional for initial weak supervision but may impact
    label quality. Consider upgrading to full cv2.quality implementations when
    OpenCV version supports them (OpenCV 4.6+ with contrib modules).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass
class QualityLabel:
    """Quality issue label with confidence.

    Args:
        value: Binary label (0 = no issue, 1 = issue present)
        confidence: Confidence score [0, 1]
        source: Labeling function name
        metadata: Additional metrics or parameters
    """

    value: int
    confidence: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            **self.metadata,
        }


@dataclass
class ImageQualityLabels:
    """Complete quality assessment labels for an image.

    Args:
        image_path: Path to image
        labels: Dictionary mapping issue type to QualityLabel
        quality_scores: Raw quality metric scores (BRISQUE, NIQE, etc.)
    """

    image_path: str
    labels: dict[str, QualityLabel]
    quality_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "image_path": self.image_path,
            "labels": {k: v.to_dict() for k, v in self.labels.items()},
            "quality_scores": self.quality_scores,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImageQualityLabels:
        """Create from dictionary."""
        labels = {
            k: QualityLabel(
                value=v["value"],
                confidence=v["confidence"],
                source=v["source"],
                metadata={
                    kk: vv
                    for kk, vv in v.items()
                    if kk not in ["value", "confidence", "source"]
                },
            )
            for k, v in data["labels"].items()
        }
        return cls(
            image_path=data["image_path"],
            labels=labels,
            quality_scores=data.get("quality_scores", {}),
        )


class WeakSupervisionLabeler:
    """Weak supervision labeling system using image quality metrics.

    Generates labels for 5 quality issue types (aligned with ResNetTeacher model):
    1. Blur
    2. Noise
    3. Skew
    4. Illumination (poor lighting/low contrast)
    5. Artifacts (compression artifacts, distortions)

    Example:
        >>> labeler = WeakSupervisionLabeler()
        >>> image = cv2.imread("document.png")
        >>> labels = labeler.label_image(image, "document.png")
        >>> print(labels.labels["blur"].value)  # 0 or 1
        >>> print(labels.labels["blur"].confidence)  # 0.0-1.0
    """

    def __init__(self) -> None:
        """Initialize weak supervision labeler."""
        # Thresholds tuned for document images (will be refined during validation)
        self.thresholds = {
            "brisque": {"good": 30, "poor": 50},  # Lower is better
            "niqe": {"excellent": 5, "good": 10},  # Lower is better
            "laplacian": {"sharp": 200, "moderate": 100, "blurry": 50},
            "rms_contrast": {"good": 0.4, "low": 0.3, "very_low": 0.2},
            "skew_angle": {"acceptable": 2.0, "skewed": 5.0},  # degrees
            "blockiness": {
                "clean": 2.0,
                "moderate": 5.0,
                "severe": 10.0,
            },  # JPEG artifacts
        }

    def label_image(
        self,
        image: NDArray[np.uint8],
        image_path: str,
    ) -> ImageQualityLabels:
        """Generate quality labels for image using weak supervision.

        Args:
            image: Input image (H, W, C) in BGR format
            image_path: Path to image (for metadata)

        Returns:
            ImageQualityLabels with binary labels and confidence scores
        """
        labels = {}

        # 1. Blur detection (using Laplacian variance)
        laplacian_var = self._compute_laplacian_variance(image)
        labels["blur"] = self._label_blur(laplacian_var)

        # 2. Noise detection (using BRISQUE)
        brisque_score = self._compute_brisque(image)
        labels["noise"] = self._label_noise(brisque_score)

        # 3. Skew detection (using Hough transform)
        skew_angle = self._detect_skew(image)
        labels["skew"] = self._label_skew(skew_angle)

        # 4. Illumination/low contrast (using RMS contrast)
        rms_contrast = self._compute_rms_contrast(image)
        labels["illumination"] = self._label_illumination(rms_contrast)

        # 5. Artifacts (using blockiness detection for JPEG artifacts)
        blockiness = self._detect_blockiness(image)
        labels["artifacts"] = self._label_artifacts(blockiness)

        # Compute quality scores
        quality_scores = {
            "brisque": float(brisque_score),
            "niqe": float(self._compute_niqe(image)),
            "laplacian_variance": float(laplacian_var),
            "rms_contrast": float(rms_contrast),
            "skew_angle_degrees": float(skew_angle),
            "blockiness": float(blockiness),
        }

        return ImageQualityLabels(
            image_path=image_path,
            labels=labels,
            quality_scores=quality_scores,
        )

    def _compute_brisque(self, image: NDArray[np.uint8]) -> float:
        """Compute BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator).

        BRISQUE measures image quality without a reference. Lower scores = better quality.
        Range: typically 0-100, but can exceed for very poor images.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            BRISQUE score (lower is better)

        Note:
            This is a placeholder implementation using simplified noise estimation.
            See module docstring "Known Limitations" for details on upgrading to
            cv2.quality.QualityBRISQUE.
        """
        # TODO: Implement BRISQUE using cv2.quality.QualityBRISQUE module
        # Current placeholder uses simplified noise estimation (see module docstring)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Estimate noise using Laplacian of Gaussian
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.Laplacian(blurred, cv2.CV_64F).var()

        # Normalize to approximate BRISQUE range [0-100]
        return min(100.0, max(0.0, (100 - noise / 10)))

    def _compute_niqe(self, image: NDArray[np.uint8]) -> float:
        """Compute NIQE (Natural Image Quality Evaluator).

        NIQE measures deviation from natural image statistics. Lower scores = better quality.
        Range: typically 0-100.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            NIQE score (lower is better)

        Note:
            This is a placeholder implementation using simplified gradient statistics.
            See module docstring "Known Limitations" for details on upgrading to
            cv2.quality.QualityNIQE.
        """
        # TODO: Implement NIQE using cv2.quality.QualityNIQE module (requires OpenCV 4.6+ contrib)
        # Current placeholder uses simplified gradient statistics (see module docstring)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute gradient magnitude
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(gx**2 + gy**2)

        # NIQE approximation based on gradient statistics
        mean_grad = gradient_mag.mean()
        std_grad = gradient_mag.std()
        # Guard against division by zero for blank or near-uniform images
        if mean_grad < 1e-8:
            return 100.0
        return min(100.0, max(0.0, 50 - (std_grad / mean_grad) * 10))

    def _compute_laplacian_variance(self, image: NDArray[np.uint8]) -> float:
        """Compute Laplacian variance for blur detection.

        Higher variance = sharper image. Lower variance = more blur.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            Laplacian variance
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)

    def _compute_rms_contrast(self, image: NDArray[np.uint8]) -> float:
        """Compute RMS (Root Mean Square) contrast.

        Measures overall contrast in image. Higher values = better contrast.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            RMS contrast [0, 1]
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Normalize to [0, 1]
        normalized = gray.astype(np.float64) / 255.0
        # Compute RMS contrast
        mean = normalized.mean()
        rms = np.sqrt(((normalized - mean) ** 2).mean())
        return float(rms)

    def _detect_skew(self, image: NDArray[np.uint8]) -> float:
        """Detect skew angle using Hough transform.

        Detects text line angles and computes deviation from horizontal.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            Skew angle in degrees (0 = no skew)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Hough line transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            return 0.0

        # Extract angles and find dominant angle
        angles = []
        for line in lines:
            _rho, theta = line[0]
            angle = np.degrees(theta) - 90  # Convert to degrees from horizontal
            # Filter near-horizontal lines (±30°)
            if abs(angle) < 30:
                angles.append(angle)

        if not angles:
            return 0.0

        # Compute median angle as skew estimate
        skew_angle = float(np.median(angles))
        return abs(skew_angle)

    def _detect_perspective(self, image: NDArray[np.uint8]) -> float:
        """Detect perspective distortion using edge straightness.

        Measures deviation of edges from straight lines.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            Edge deviation in degrees (0 = no distortion)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Analyze straightness of major contours
        deviations = []
        for contour in contours:
            if len(contour) < 10:
                continue

            # Fit line to contour
            [vx, vy, x, y] = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)

            # Compute perpendicular distance from points to fitted line
            distances = []
            for point in contour:
                px, py = point[0]
                # Distance from point to line
                dist = abs((vy * (px - x)) - (vx * (py - y)))
                distances.append(dist)

            if distances:
                mean_dev = np.mean(distances)
                deviations.append(mean_dev)

        if not deviations:
            return 0.0

        # Return median deviation as perspective estimate
        # Convert pixel deviation to approximate degrees (rough heuristic)
        median_dev = float(np.median(deviations))
        # Normalize by image diagonal
        diag = np.sqrt(image.shape[0] ** 2 + image.shape[1] ** 2)
        normalized_dev = (median_dev / diag) * 100  # Scale to degrees-like range

        return min(50.0, normalized_dev)

    def _label_noise(self, brisque_score: float) -> QualityLabel:
        """Label noise based on BRISQUE score."""
        thresholds = self.thresholds["brisque"]

        if brisque_score < thresholds["good"]:
            # Clean image
            return QualityLabel(
                value=0,
                confidence=0.85,
                source="brisque",
                metadata={"brisque_score": brisque_score},
            )
        if brisque_score < thresholds["poor"]:
            # Moderate noise
            return QualityLabel(
                value=1,
                confidence=0.70,
                source="brisque",
                metadata={"brisque_score": brisque_score},
            )
        # Significant noise
        return QualityLabel(
            value=1,
            confidence=0.90,
            source="brisque",
            metadata={"brisque_score": brisque_score},
        )

    def _label_blur(self, laplacian_var: float) -> QualityLabel:
        """Label blur based on Laplacian variance."""
        thresholds = self.thresholds["laplacian"]

        if laplacian_var > thresholds["sharp"]:
            # Sharp image
            return QualityLabel(
                value=0,
                confidence=0.92,
                source="laplacian",
                metadata={"laplacian_variance": laplacian_var},
            )
        if laplacian_var > thresholds["moderate"]:
            # Moderate blur
            return QualityLabel(
                value=1,
                confidence=0.75,
                source="laplacian",
                metadata={"laplacian_variance": laplacian_var},
            )
        # Significant blur
        return QualityLabel(
            value=1,
            confidence=0.95,
            source="laplacian",
            metadata={"laplacian_variance": laplacian_var},
        )

    def _label_skew(self, skew_angle: float) -> QualityLabel:
        """Label skew based on detected angle."""
        thresholds = self.thresholds["skew_angle"]

        if skew_angle < thresholds["acceptable"]:
            # No significant skew
            return QualityLabel(
                value=0,
                confidence=0.88,
                source="hough_transform",
                metadata={"skew_angle_degrees": skew_angle},
            )
        if skew_angle < thresholds["skewed"]:
            # Moderate skew
            return QualityLabel(
                value=1,
                confidence=0.75,
                source="hough_transform",
                metadata={"skew_angle_degrees": skew_angle},
            )
        # Significant skew
        return QualityLabel(
            value=1,
            confidence=0.92,
            source="hough_transform",
            metadata={"skew_angle_degrees": skew_angle},
        )

    def _label_perspective(self, edge_deviation: float) -> QualityLabel:
        """Label perspective distortion based on edge straightness."""
        thresholds = self.thresholds["edge_straightness"]

        if edge_deviation < thresholds["straight"]:
            # No distortion
            return QualityLabel(
                value=0,
                confidence=0.75,
                source="edge_straightness",
                metadata={"edge_deviation_degrees": edge_deviation},
            )
        if edge_deviation < thresholds["distorted"]:
            # Moderate distortion
            return QualityLabel(
                value=1,
                confidence=0.65,
                source="edge_straightness",
                metadata={"edge_deviation_degrees": edge_deviation},
            )
        # Significant distortion
        return QualityLabel(
            value=1,
            confidence=0.80,
            source="edge_straightness",
            metadata={"edge_deviation_degrees": edge_deviation},
        )

    def _detect_blockiness(self, image: NDArray[np.uint8]) -> float:
        """Detect blockiness artifacts (JPEG compression).

        Measures discontinuities at 8x8 block boundaries, typical of JPEG compression.

        Args:
            image: Input image (H, W, C) in BGR format

        Returns:
            Blockiness score (higher = more artifacts)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute horizontal and vertical differences at 8-pixel boundaries
        h, w = gray.shape
        blockiness_scores = []

        # Horizontal blockiness (check vertical edges at x = 8, 16, 24, ...)
        for x in range(8, w - 8, 8):
            # Difference across block boundary
            left = gray[:, x - 1].astype(np.float64)
            right = gray[:, x].astype(np.float64)
            diff = np.abs(left - right).mean()
            blockiness_scores.append(diff)

        # Vertical blockiness (check horizontal edges at y = 8, 16, 24, ...)
        for y in range(8, h - 8, 8):
            # Difference across block boundary
            top = gray[y - 1, :].astype(np.float64)
            bottom = gray[y, :].astype(np.float64)
            diff = np.abs(top - bottom).mean()
            blockiness_scores.append(diff)

        if not blockiness_scores:
            return 0.0

        # Return mean blockiness across all boundaries
        return float(np.mean(blockiness_scores))

    def _label_artifacts(self, blockiness: float) -> QualityLabel:
        """Label compression artifacts based on blockiness."""
        thresholds = self.thresholds["blockiness"]

        if blockiness < thresholds["clean"]:
            # No significant artifacts
            return QualityLabel(
                value=0,
                confidence=0.85,
                source="blockiness",
                metadata={"blockiness": blockiness},
            )
        if blockiness < thresholds["moderate"]:
            # Moderate artifacts
            return QualityLabel(
                value=1,
                confidence=0.70,
                source="blockiness",
                metadata={"blockiness": blockiness},
            )
        # Severe artifacts
        return QualityLabel(
            value=1,
            confidence=0.90,
            source="blockiness",
            metadata={"blockiness": blockiness},
        )

    def _label_illumination(self, rms_contrast: float) -> QualityLabel:
        """Label illumination issues (poor lighting/low contrast) based on RMS contrast."""
        thresholds = self.thresholds["rms_contrast"]

        if rms_contrast > thresholds["good"]:
            # Good contrast/illumination
            return QualityLabel(
                value=0,
                confidence=0.88,
                source="rms_contrast",
                metadata={"rms_contrast": rms_contrast},
            )
        if rms_contrast > thresholds["low"]:
            # Poor illumination/low contrast
            return QualityLabel(
                value=1,
                confidence=0.75,
                source="rms_contrast",
                metadata={"rms_contrast": rms_contrast},
            )
        # Very poor illumination/very low contrast
        return QualityLabel(
            value=1,
            confidence=0.90,
            source="rms_contrast",
            metadata={"rms_contrast": rms_contrast},
        )

    def label_batch(
        self,
        image_paths: list[str | Path],
        output_dir: str | Path,
    ) -> list[ImageQualityLabels]:
        """Label batch of images and save to JSON files.

        Args:
            image_paths: List of image paths
            output_dir: Directory to save JSON labels

        Returns:
            List of ImageQualityLabels for all images
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_labels = []
        for image_path in image_paths:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                continue

            # Generate labels
            labels = self.label_image(image, str(image_path))
            all_labels.append(labels)

            # Save to JSON
            output_path = output_dir / f"{Path(image_path).stem}_labels.json"
            with open(output_path, "w") as f:
                json.dump(labels.to_dict(), f, indent=2)

        return all_labels


class ContinuousWeakSupervisionLabeler:
    """Phase 7 weak supervision labeler with continuous severity scores.

    Generates continuous [0, 1] severity labels instead of binary labels.
    Preserves severity gradation for better model calibration.

    Features:
    - Normalized severity scores in [0, 1] range
    - Label smoothing to reduce overconfidence
    - Outlier filtering for extreme detector disagreement
    - Integration with ContinuousQualityLabel schema

    Example:
        >>> labeler = ContinuousWeakSupervisionLabeler()
        >>> image = cv2.imread("document.png")
        >>> label = labeler.label_image(image, "document.png")
        >>> print(f"Blur severity: {label['blur_severity']:.2f}")
    """

    # Confidence assigned to labels when all detectors agree closely.
    # Range [0, 1]; higher means more certain the label is accurate.
    NORMAL_LABEL_CONFIDENCE: float = 0.7

    # Confidence assigned to outlier labels where detectors disagree significantly.
    # Reduced from NORMAL_LABEL_CONFIDENCE to signal lower reliability to downstream
    # training code (e.g., GDBC uncertainty weighting).
    OUTLIER_LABEL_CONFIDENCE: float = 0.4

    def __init__(
        self,
        label_smoothing: float = 0.0,
        smooth_clip_min: float = 0.0,
        smooth_clip_max: float = 1.0,
        outlier_threshold: float = 0.5,
    ) -> None:
        """Initialize continuous labeler.

        Args:
            label_smoothing: Smoothing factor (0=none, clips to [min, max])
            smooth_clip_min: Minimum value after smoothing (default: 0.0)
            smooth_clip_max: Maximum value after smoothing (default: 1.0)
            outlier_threshold: Max allowed variance between detectors
        """
        self.label_smoothing = label_smoothing
        self.smooth_clip_min = smooth_clip_min
        self.smooth_clip_max = smooth_clip_max
        self.outlier_threshold = outlier_threshold

        # Reuse binary labeler instance for efficiency
        self._binary_labeler = WeakSupervisionLabeler()

        # Normalization parameters for each metric
        # These map raw metric values to [0, 1] severity
        self.normalization: dict[str, dict[str, Any]] = {
            # Laplacian variance: high = sharp (good), low = blurry (bad)
            # severity = 1 - normalized_sharpness
            "laplacian": {"min": 50, "max": 500, "invert": True},
            # BRISQUE: lower is better (0-100 scale)
            "brisque": {"min": 0, "max": 100, "invert": False},
            # Skew angle: 0 = no skew, higher = more skew
            "skew": {"min": 0, "max": 15, "invert": False},  # degrees
            # RMS contrast: higher is better (0-0.5 typical range)
            "rms_contrast": {"min": 0.1, "max": 0.5, "invert": True},
            # Blockiness: higher = more JPEG artifacts
            "blockiness": {"min": 0, "max": 15, "invert": False},
        }

    def _normalize_metric(
        self,
        value: float,
        metric_name: str,
    ) -> float:
        """Normalize a raw metric value to [0, 1] severity.

        Args:
            value: Raw metric value
            metric_name: Name of the metric for normalization params

        Returns:
            Normalized severity in [0, 1] (0=good, 1=bad)
        """
        params = self.normalization.get(metric_name, {"min": 0, "max": 1, "invert": False})

        min_val = params["min"]
        max_val = params["max"]
        invert = params["invert"]

        # Clip to valid range
        value = max(min_val, min(max_val, value))

        # Normalize to [0, 1]
        normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.0

        # Invert if needed (for metrics where higher = better)
        if invert:
            normalized = 1.0 - normalized

        # Apply label smoothing
        if self.label_smoothing > 0:
            normalized = float(np.clip(
                normalized,
                self.smooth_clip_min,
                self.smooth_clip_max,
            ))

        return float(normalized)

    def label_image(
        self,
        image: NDArray[np.uint8],
        image_path: str = "",
    ) -> dict[str, Any]:
        """Generate continuous severity labels for image.

        Args:
            image: Input image (H, W, C) in BGR format
            image_path: Path to image (for metadata)

        Returns:
            Dictionary with continuous severity scores compatible with
            ContinuousQualityLabel schema
        """
        # Use the binary labeler's detection methods (reuse instance)
        # Compute raw metrics
        laplacian_var = self._binary_labeler._compute_laplacian_variance(image)
        brisque_score = self._binary_labeler._compute_brisque(image)
        skew_angle = self._binary_labeler._detect_skew(image)
        rms_contrast = self._binary_labeler._compute_rms_contrast(image)
        blockiness = self._binary_labeler._detect_blockiness(image)

        # Convert to continuous severity scores
        blur_severity = self._normalize_metric(laplacian_var, "laplacian")
        noise_severity = self._normalize_metric(brisque_score, "brisque")
        skew_severity = self._normalize_metric(skew_angle, "skew")
        contrast_severity = self._normalize_metric(rms_contrast, "rms_contrast")
        compression_severity = self._normalize_metric(blockiness, "blockiness")

        # Compute overall quality using 75th percentile of severities
        # This is more robust than max for documents with multiple moderate defects
        severities = [blur_severity, noise_severity, skew_severity, contrast_severity, compression_severity]
        severity_75th = float(np.percentile(severities, 75))
        overall_quality = 1.0 - severity_75th

        # Check for outliers (high disagreement between detectors)
        severity_variance = float(np.var(severities))
        is_outlier = severity_variance > self.outlier_threshold

        # Build result in ContinuousQualityLabel format
        return {
            # Continuous severity scores
            "blur_severity": blur_severity,
            "noise_severity": noise_severity,
            "skew_severity": skew_severity,
            "contrast_severity": contrast_severity,
            "compression_severity": compression_severity,
            "overall_quality": overall_quality,
            # Document-specific degradations not currently measured by weak supervision
            # detectors. Kept at 0.0 for schema compatibility. These would require
            # specialized detectors (e.g., spectral analysis for ink, page-pair
            # comparison for bleed-through) to compute accurately.
            "ink_degradation": 0.0,
            "paper_degradation": 0.0,
            "bleed_through": 0.0,
            # Metadata
            "label_source": "weak_supervision",
            "label_confidence": self.NORMAL_LABEL_CONFIDENCE if not is_outlier else self.OUTLIER_LABEL_CONFIDENCE,
            "label_variance": severity_variance,
            "image_path": image_path,
            "is_outlier": is_outlier,
            # Raw quality scores for debugging
            "quality_scores": {
                "laplacian_variance": laplacian_var,
                "brisque": brisque_score,
                "skew_angle_degrees": skew_angle,
                "rms_contrast": rms_contrast,
                "blockiness": blockiness,
            },
            # Backward-compatible binary labels
            "labels": {
                "blur": {
                    "value": int(blur_severity >= 0.3),
                    "confidence": 0.7,
                    "source": "laplacian",
                    "severity": blur_severity,
                },
                "noise": {
                    "value": int(noise_severity >= 0.3),
                    "confidence": 0.7,
                    "source": "brisque",
                    "severity": noise_severity,
                },
                "skew": {
                    "value": int(skew_severity >= 0.3),
                    "confidence": 0.7,
                    "source": "hough_transform",
                    "severity": skew_severity,
                },
                "illumination": {
                    "value": int(contrast_severity >= 0.3),
                    "confidence": 0.7,
                    "source": "rms_contrast",
                    "severity": contrast_severity,
                },
                "artifacts": {
                    "value": int(compression_severity >= 0.3),
                    "confidence": 0.7,
                    "source": "blockiness",
                    "severity": compression_severity,
                },
            },
        }

    def label_batch(
        self,
        image_paths: list[str | Path],
        output_dir: str | Path,
        filter_outliers: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Label batch of images with continuous scores.

        Args:
            image_paths: List of image paths
            output_dir: Directory to save JSON labels
            filter_outliers: If True, separate outliers from main dataset

        Returns:
            Tuple of (valid_labels, outlier_labels)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        valid_labels: list[dict[str, Any]] = []
        outlier_labels: list[dict[str, Any]] = []

        for image_path in image_paths:
            image = cv2.imread(str(image_path))
            if image is None:
                continue

            label = self.label_image(image, str(image_path))

            # Separate outliers
            if filter_outliers and label.get("is_outlier", False):
                outlier_labels.append(label)
                continue

            valid_labels.append(label)

            # Save to JSON
            output_path = output_dir / f"{Path(image_path).stem}_continuous_labels.json"
            with open(output_path, "w") as f:
                json.dump(label, f, indent=2)

        return valid_labels, outlier_labels

    def get_severity_vector(self, label: dict[str, Any]) -> list[float]:
        """Extract severity vector from label dict.

        Args:
            label: Label dictionary from label_image

        Returns:
            List of 5 severity values [blur, noise, skew, contrast, compression]
        """
        return [
            label["blur_severity"],
            label["noise_severity"],
            label["skew_severity"],
            label["contrast_severity"],
            label["compression_severity"],
        ]


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 3:
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Load image
    image = cv2.imread(input_path)
    if image is None:
        sys.exit(1)

    # Check for continuous mode flag
    continuous_mode = "--continuous" in sys.argv

    if continuous_mode:
        # Phase 7: Continuous labels
        cont_labeler = ContinuousWeakSupervisionLabeler()
        labels = cont_labeler.label_image(image, input_path)
    else:
        # Original: Binary labels
        labeler = WeakSupervisionLabeler()
        labels = labeler.label_image(image, input_path).to_dict()

    # Save to JSON
    with open(output_path, "w") as f:
        json.dump(labels, f, indent=2)
