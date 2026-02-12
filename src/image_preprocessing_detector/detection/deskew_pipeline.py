"""Deskew pipeline orchestrator: ML-first with classical fallback.

Orchestrates the full deskew correction flow:
    1. Run ONNX SkewNet inference (orientation + skew in one pass)
    2. Apply 90-degree orientation correction if needed
    3. Apply fine skew correction via OpenCV warpAffine
    4. Fall back to classical Hough+Projection if confidence is low

This module is the primary entry point for deskew in the preprocessing
pipeline, replacing direct use of SkewDetector + DeskewCorrector.

Config: config/skew_estimation.yaml
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeskewConfig:
    """Configuration for the deskew pipeline.

    Attributes:
        model_path: Path to the ONNX SkewNet model.
        orientation_confidence_threshold: Min confidence to apply orientation.
        orientation_fallback_threshold: Below this, fall back to classical.
        skew_confidence_threshold: Min bin probability to trust skew prediction.
        min_correction_angle: Skip correction below this angle.
        max_correction_angle: Flag for review above this angle.
        uncertainty_gate: Skip correction if uncertainty > |angle|.
        fallback_enabled: Whether to allow classical fallback.
        border_value: Pixel value for rotation borders (255 = white).
    """

    model_path: Path | None = None
    orientation_confidence_threshold: float = 0.85
    orientation_fallback_threshold: float = 0.5
    skew_confidence_threshold: float = 0.3
    min_correction_angle: float = 0.3
    max_correction_angle: float = 45.0
    uncertainty_gate: bool = True
    fallback_enabled: bool = True
    border_value: int = 255

    @staticmethod
    def from_yaml(config_path: str | Path | None = None) -> DeskewConfig:
        """Load pipeline config from skew_estimation.yaml.

        Args:
            config_path: Path to config YAML. None uses default.

        Returns:
            Populated DeskewConfig.
        """
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parents[3] / "config" / "skew_estimation.yaml"
            )
        else:
            config_path = Path(config_path)

        with config_path.open() as f:
            cfg = yaml.safe_load(f)

        model_cfg = cfg.get("model", {})
        orient_cfg = cfg.get("orientation", {})
        skew_cfg = cfg.get("skew", {})
        correction_cfg = skew_cfg.get("correction", {})
        fallback_cfg = cfg.get("fallback", {})

        # Resolve model path relative to project root
        onnx_path = model_cfg.get("onnx_int8_path") or model_cfg.get("onnx_fp32_path")
        model_path = None
        if onnx_path:
            candidate = config_path.parent.parent / onnx_path
            if candidate.exists():
                model_path = candidate

        return DeskewConfig(
            model_path=model_path,
            orientation_confidence_threshold=orient_cfg.get(
                "confidence_threshold", 0.85
            ),
            orientation_fallback_threshold=orient_cfg.get("fallback_threshold", 0.5),
            skew_confidence_threshold=fallback_cfg.get(
                "skew_confidence_threshold", 0.3
            ),
            min_correction_angle=correction_cfg.get("min_angle", 0.3),
            max_correction_angle=correction_cfg.get("max_angle", 45.0),
            uncertainty_gate=correction_cfg.get("uncertainty_gate", True),
            fallback_enabled=fallback_cfg.get("enabled", True),
            border_value=255,
        )


@dataclass(frozen=True)
class DeskewResult:
    """Result of the full deskew pipeline.

    Attributes:
        corrected_image: The deskewed image (may be same as input if skipped).
        orientation_applied: Whether orientation correction was applied.
        orientation_angle: Detected orientation (0, 90, 180, 270).
        orientation_confidence: Confidence of orientation prediction.
        skew_angle: Detected fine skew angle in degrees.
        skew_confidence: Confidence of skew prediction.
        skew_uncertainty: Predicted uncertainty from regression head.
        correction_applied: Whether skew correction was applied.
        skipped_reason: Reason if correction was skipped.
        method: Detection method used (ml, classical, ml+fallback).
        latency_ms: Total pipeline latency in milliseconds.
    """

    corrected_image: np.ndarray
    orientation_applied: bool = False
    orientation_angle: int = 0
    orientation_confidence: float = 0.0
    skew_angle: float = 0.0
    skew_confidence: float = 0.0
    skew_uncertainty: float = 0.0
    correction_applied: bool = False
    skipped_reason: str | None = None
    method: str = "ml"
    latency_ms: float = 0.0


class DeskewPipeline:
    """ML-first deskew pipeline with classical fallback.

    Usage:
        pipeline = DeskewPipeline.from_config()
        result = pipeline.process(image)
        if result.correction_applied:
            corrected = result.corrected_image
    """

    def __init__(self, config: DeskewConfig | None = None) -> None:
        """Initialize deskew pipeline.

        Args:
            config: Pipeline configuration. None loads from YAML.
        """
        self.config = config or DeskewConfig.from_yaml()
        self._ml_estimator: Any | None = None
        self._classical_detector: Any | None = None

        logger.info(
            "DeskewPipeline initialized",
            extra={
                "model_path": str(self.config.model_path),
                "fallback_enabled": self.config.fallback_enabled,
            },
        )

    @classmethod
    def from_config(cls, config_path: str | Path | None = None) -> DeskewPipeline:
        """Create pipeline from YAML config file.

        Args:
            config_path: Path to skew_estimation.yaml.

        Returns:
            Configured DeskewPipeline instance.
        """
        config = DeskewConfig.from_yaml(config_path)
        return cls(config=config)

    def process(self, image: np.ndarray) -> DeskewResult:
        """Run the full deskew pipeline on an image.

        Args:
            image: Input image (BGR uint8, from OpenCV).

        Returns:
            DeskewResult with corrected image and metadata.

        Raises:
            ValueError: If image is invalid or empty.
        """
        import time

        if image is None or image.size == 0:
            msg = "Invalid or empty image provided"
            raise ValueError(msg)

        start = time.perf_counter()

        # Try ML-based detection first
        if self.config.model_path and self.config.model_path.exists():
            result = self._process_ml(image)
        elif self.config.fallback_enabled:
            result = self._process_classical(image)
        else:
            result = DeskewResult(
                corrected_image=image.copy(),
                skipped_reason="No model available and fallback disabled",
                method="none",
            )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Return with timing
        return DeskewResult(
            corrected_image=result.corrected_image,
            orientation_applied=result.orientation_applied,
            orientation_angle=result.orientation_angle,
            orientation_confidence=result.orientation_confidence,
            skew_angle=result.skew_angle,
            skew_confidence=result.skew_confidence,
            skew_uncertainty=result.skew_uncertainty,
            correction_applied=result.correction_applied,
            skipped_reason=result.skipped_reason,
            method=result.method,
            latency_ms=round(elapsed_ms, 2),
        )

    def _process_ml(self, image: np.ndarray) -> DeskewResult:
        """Run ML-based deskew with optional classical fallback.

        Args:
            image: Input BGR image.

        Returns:
            DeskewResult from ML inference.
        """
        from image_preprocessing_detector.models.skew_estimator import (
            SkewEstimatorInference,
        )

        if self._ml_estimator is None:
            self._ml_estimator = SkewEstimatorInference(
                model_path=self.config.model_path,  # type: ignore[arg-type]
            )

        estimation = self._ml_estimator.predict(image)

        # Step 1: Orientation correction
        working_image = image.copy()
        orientation_applied = False

        if estimation.orientation_class != 0:
            if (
                estimation.orientation_confidence
                >= self.config.orientation_confidence_threshold
            ):
                working_image = _rotate_90(working_image, estimation.orientation_class)
                orientation_applied = True
                logger.debug(
                    "Applied orientation correction",
                    extra={
                        "angle": estimation.orientation_class,
                        "confidence": estimation.orientation_confidence,
                    },
                )
            elif (
                estimation.orientation_confidence
                < self.config.orientation_fallback_threshold
                and self.config.fallback_enabled
            ):
                # Low confidence: fall back to classical for the whole thing
                logger.debug(
                    "Orientation confidence too low, falling back to classical"
                )
                classical_result = self._process_classical(working_image)
                return DeskewResult(
                    corrected_image=classical_result.corrected_image,
                    orientation_applied=classical_result.orientation_applied,
                    orientation_angle=classical_result.orientation_angle,
                    orientation_confidence=estimation.orientation_confidence,
                    skew_angle=classical_result.skew_angle,
                    skew_confidence=classical_result.skew_confidence,
                    correction_applied=classical_result.correction_applied,
                    skipped_reason=classical_result.skipped_reason,
                    method="ml+fallback",
                )

        # Step 2: Fine skew correction
        skew_angle = estimation.final_angle
        abs_angle = abs(skew_angle)

        # Check confidence
        if estimation.skew_bin_confidence < self.config.skew_confidence_threshold:
            if self.config.fallback_enabled:
                classical_result = self._process_classical(working_image)
                return DeskewResult(
                    corrected_image=classical_result.corrected_image,
                    orientation_applied=orientation_applied,
                    orientation_angle=estimation.orientation_class,
                    orientation_confidence=estimation.orientation_confidence,
                    skew_angle=classical_result.skew_angle,
                    skew_confidence=estimation.skew_bin_confidence,
                    skew_uncertainty=estimation.skew_uncertainty,
                    correction_applied=classical_result.correction_applied,
                    skipped_reason=classical_result.skipped_reason,
                    method="ml+fallback",
                )
            return DeskewResult(
                corrected_image=working_image,
                orientation_applied=orientation_applied,
                orientation_angle=estimation.orientation_class,
                orientation_confidence=estimation.orientation_confidence,
                skew_angle=skew_angle,
                skew_confidence=estimation.skew_bin_confidence,
                skew_uncertainty=estimation.skew_uncertainty,
                skipped_reason="Low skew bin confidence",
                method="ml",
            )

        # Uncertainty gate: skip if uncertainty > |angle|
        if self.config.uncertainty_gate and estimation.skew_uncertainty > abs_angle:
            return DeskewResult(
                corrected_image=working_image,
                orientation_applied=orientation_applied,
                orientation_angle=estimation.orientation_class,
                orientation_confidence=estimation.orientation_confidence,
                skew_angle=skew_angle,
                skew_confidence=estimation.skew_bin_confidence,
                skew_uncertainty=estimation.skew_uncertainty,
                skipped_reason="Uncertainty exceeds angle magnitude",
                method="ml",
            )

        # Min angle gate
        if abs_angle < self.config.min_correction_angle:
            return DeskewResult(
                corrected_image=working_image,
                orientation_applied=orientation_applied,
                orientation_angle=estimation.orientation_class,
                orientation_confidence=estimation.orientation_confidence,
                skew_angle=skew_angle,
                skew_confidence=estimation.skew_bin_confidence,
                skew_uncertainty=estimation.skew_uncertainty,
                skipped_reason=f"Angle {abs_angle:.2f} below min {self.config.min_correction_angle}",
                method="ml",
            )

        # Max angle gate
        if abs_angle > self.config.max_correction_angle:
            return DeskewResult(
                corrected_image=working_image,
                orientation_applied=orientation_applied,
                orientation_angle=estimation.orientation_class,
                orientation_confidence=estimation.orientation_confidence,
                skew_angle=skew_angle,
                skew_confidence=estimation.skew_bin_confidence,
                skew_uncertainty=estimation.skew_uncertainty,
                skipped_reason=f"Angle {abs_angle:.2f} exceeds max {self.config.max_correction_angle}",
                method="ml",
            )

        # Apply skew correction
        corrected = _apply_skew_correction(
            working_image, skew_angle, self.config.border_value
        )

        return DeskewResult(
            corrected_image=corrected,
            orientation_applied=orientation_applied,
            orientation_angle=estimation.orientation_class,
            orientation_confidence=estimation.orientation_confidence,
            skew_angle=skew_angle,
            skew_confidence=estimation.skew_bin_confidence,
            skew_uncertainty=estimation.skew_uncertainty,
            correction_applied=True,
            method="ml",
        )

    def _process_classical(self, image: np.ndarray) -> DeskewResult:
        """Run classical Hough+Projection skew detection and correction.

        Args:
            image: Input BGR image.

        Returns:
            DeskewResult from classical detection.
        """
        from image_preprocessing_detector.detection.iqa_classical import SkewDetector

        if self._classical_detector is None:
            self._classical_detector = SkewDetector()

        result = self._classical_detector.detect(image)

        abs_angle = abs(result.angle)

        if abs_angle < self.config.min_correction_angle:
            return DeskewResult(
                corrected_image=image.copy(),
                skew_angle=result.angle,
                skew_confidence=result.confidence,
                skipped_reason=f"Classical: angle {abs_angle:.2f} below min",
                method="classical",
            )

        if abs_angle > self.config.max_correction_angle:
            return DeskewResult(
                corrected_image=image.copy(),
                skew_angle=result.angle,
                skew_confidence=result.confidence,
                skipped_reason=f"Classical: angle {abs_angle:.2f} exceeds max",
                method="classical",
            )

        corrected = _apply_skew_correction(
            image, result.angle, self.config.border_value
        )

        return DeskewResult(
            corrected_image=corrected,
            skew_angle=result.angle,
            skew_confidence=result.confidence,
            correction_applied=True,
            method="classical",
        )

    def close(self) -> None:
        """Release resources."""
        if self._ml_estimator is not None:
            self._ml_estimator.close()
            self._ml_estimator = None


# ---------------------------------------------------------------------------
# Image correction utilities
# ---------------------------------------------------------------------------


def _rotate_90(image: np.ndarray, angle: int) -> np.ndarray:
    """Rotate image by 90/180/270 degrees.

    Args:
        image: Input BGR image.
        angle: Rotation angle (0, 90, 180, 270).

    Returns:
        Rotated image.
    """
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image.copy()


def _apply_skew_correction(
    image: np.ndarray,
    angle: float,
    border_value: int = 255,
) -> np.ndarray:
    """Apply fine skew correction using OpenCV warpAffine.

    Args:
        image: Input BGR image.
        angle: Skew angle in degrees (positive = clockwise).
        border_value: Fill value for borders after rotation.

    Returns:
        Deskewed image.
    """
    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)

    rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)

    return cv2.warpAffine(
        image,
        rotation_matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(border_value, border_value, border_value),
    )
