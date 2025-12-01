"""Phase 7 Continuous Labels Schema and Utilities.

Pydantic models for continuous quality labels with backward compatibility
for binary label training pipelines.

This module provides:
1. ContinuousQualityLabel - Main Pydantic model for [0,1] severity scores
2. Conversion utilities between continuous and binary labels
3. Label aggregation for multi-source datasets
4. Validation and normalization functions

Reference:
    - Phase 7 Strategy: docs/development/phase-7-continuous-labels-strategy.md
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from image_preprocessing_detector.utils.datetime_compat import utc_now
from image_preprocessing_detector.utils.path_security import validate_safe_path


class LabelSource(str, Enum):
    """Source of quality labels."""

    DOCCREATOR = "doccreator"
    AUGRAPHY = "augraphy"
    MLLM_PSEUDO = "mllm_pseudo"
    WEAK_SUPERVISION = "weak_supervision"
    MOS_CROWDSOURCED = "mos_crowdsourced"
    MOS_EXPERT = "mos_expert"
    MANUAL = "manual"


class BinaryLabel(BaseModel):
    """Binary label with confidence and severity for backward compatibility.

    Used in the `labels` field of ContinuousQualityLabel to maintain
    compatibility with existing binary training pipelines.
    """

    value: int = Field(ge=0, le=1, description="Binary label (0 or 1)")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source: str = "continuous"
    severity: float = Field(ge=0.0, le=1.0, default=0.0)

    @field_validator("value")
    @classmethod
    def validate_binary(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("Binary label must be 0 or 1")
        return v


class QualityScores(BaseModel):
    """Raw quality scores for backward compatibility."""

    blur: float = Field(ge=0.0, le=1.0, default=0.0)
    noise: float = Field(ge=0.0, le=1.0, default=0.0)
    skew: float = Field(ge=0.0, le=1.0, default=0.0)
    contrast: float = Field(ge=0.0, le=1.0, default=0.0)
    compression: float = Field(ge=0.0, le=1.0, default=0.0)
    overall: float = Field(ge=0.0, le=1.0, default=1.0)


class ContinuousQualityLabel(BaseModel):
    """Continuous quality labels for Phase 7 training.

    All severity scores are in range [0, 1]:
    - 0.0 = no degradation, perfect quality
    - 1.0 = maximum degradation, unreadable

    This schema provides:
    1. Primary continuous severity scores for regression training
    2. Backward-compatible binary labels for classification
    3. Metadata for label provenance and GDBC weighting

    Example:
        >>> label = ContinuousQualityLabel(
        ...     blur_severity=0.3,
        ...     noise_severity=0.2,
        ...     overall_quality=0.8,
        ...     label_source="augraphy",
        ... )
        >>> print(label.get_binary_labels())
        {'blur': 1, 'noise': 0, 'skew': 0, 'illumination': 0, 'artifacts': 0}
    """

    # =========================================================================
    # Primary Continuous Severity Scores [0, 1]
    # =========================================================================

    blur_severity: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Blur severity from Gaussian, motion, defocus blur",
    )
    noise_severity: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Noise severity from Gaussian, salt-pepper, scanner noise",
    )
    skew_severity: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Rotation/skew severity (angle normalized to [0,1])",
    )
    contrast_severity: float = Field(
        ge=0.0, le=1.0, default=0.0, description="Poor contrast/illumination severity"
    )
    compression_severity: float = Field(
        ge=0.0, le=1.0, default=0.0, description="JPEG/compression artifact severity"
    )

    # =========================================================================
    # Document-Specific Degradations
    # =========================================================================

    ink_degradation: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Ink fading, bleeding, broken characters",
    )
    paper_degradation: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Paper aging, stains, watermarks, dirty drum",
    )
    bleed_through: float = Field(
        ge=0.0, le=1.0, default=0.0, description="Show-through from reverse side"
    )

    # =========================================================================
    # Aggregated Scores
    # =========================================================================

    overall_quality: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Overall quality (1.0 = best, 0.0 = worst)",
    )
    dmos: float = Field(
        ge=0.0,
        le=100.0,
        default=0.0,
        description="Differential MOS score (for MOS datasets)",
    )

    # =========================================================================
    # Label Provenance and GDBC
    # =========================================================================

    label_source: Literal[
        "doccreator",
        "augraphy",
        "mllm_pseudo",
        "weak_supervision",
        "mos_crowdsourced",
        "mos_expert",
        "manual",
    ] = Field(default="augraphy")

    label_confidence: float = Field(
        ge=0.0, le=1.0, default=1.0, description="Confidence in label accuracy"
    )
    label_variance: float = Field(
        ge=0.0,
        default=0.0,
        description="Annotation variance for GDBC (from MOS datasets)",
    )

    # =========================================================================
    # Metadata
    # =========================================================================

    image_path: str = Field(default="", description="Path to source image")
    generation_timestamp: str = Field(
        default_factory=lambda: utc_now().isoformat()
    )
    augmentation_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw augmentation parameters for reproducibility",
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def compute_overall_if_missing(self) -> ContinuousQualityLabel:
        """Compute overall_quality if not explicitly set."""
        # If overall_quality is default and we have severity scores, compute it
        if self.overall_quality == 1.0:
            max_severity = max(
                self.blur_severity,
                self.noise_severity,
                self.skew_severity,
                self.contrast_severity,
                self.compression_severity,
                self.ink_degradation,
                self.paper_degradation,
                self.bleed_through,
            )
            if max_severity > 0:
                self.overall_quality = 1.0 - max_severity
        return self

    # =========================================================================
    # Conversion Methods
    # =========================================================================

    def get_binary_labels(self, threshold: float = 0.3) -> dict[str, int]:
        """Convert continuous labels to binary for backward compatibility.

        Args:
            threshold: Severity threshold for positive label (default: 0.3)

        Returns:
            Dict mapping issue names to binary labels (0 or 1)
        """
        return {
            "blur": int(self.blur_severity >= threshold),
            "noise": int(self.noise_severity >= threshold),
            "skew": int(self.skew_severity >= threshold),
            "illumination": int(self.contrast_severity >= threshold),
            "artifacts": int(self.compression_severity >= threshold),
        }

    def get_severity_vector(self) -> list[float]:
        """Get severity scores as a vector for model training.

        Returns:
            List of 5 severity scores in order:
            [blur, noise, skew, contrast, compression]
        """
        return [
            self.blur_severity,
            self.noise_severity,
            self.skew_severity,
            self.contrast_severity,
            self.compression_severity,
        ]

    def get_extended_severity_vector(self) -> list[float]:
        """Get extended severity vector including document-specific degradations.

        Returns:
            List of 8 severity scores in order:
            [blur, noise, skew, contrast, compression, ink, paper, bleed]
        """
        return [
            self.blur_severity,
            self.noise_severity,
            self.skew_severity,
            self.contrast_severity,
            self.compression_severity,
            self.ink_degradation,
            self.paper_degradation,
            self.bleed_through,
        ]

    def to_training_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for training dataset.

        Returns format compatible with existing IQADataset and weak supervision.
        """
        binary = self.get_binary_labels()

        return {
            # Continuous scores (primary for Phase 7)
            "continuous_labels": {
                "blur_severity": self.blur_severity,
                "noise_severity": self.noise_severity,
                "skew_severity": self.skew_severity,
                "contrast_severity": self.contrast_severity,
                "compression_severity": self.compression_severity,
                "ink_degradation": self.ink_degradation,
                "paper_degradation": self.paper_degradation,
                "bleed_through": self.bleed_through,
                "overall_quality": self.overall_quality,
            },
            # Backward-compatible quality_scores
            "quality_scores": {
                "blur": self.blur_severity,
                "noise": self.noise_severity,
                "skew": self.skew_severity,
                "contrast": self.contrast_severity,
                "compression": self.compression_severity,
                "overall": self.overall_quality,
            },
            # Backward-compatible binary labels
            "labels": {
                "blur": {
                    "value": binary["blur"],
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.blur_severity,
                },
                "noise": {
                    "value": binary["noise"],
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.noise_severity,
                },
                "skew": {
                    "value": binary["skew"],
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.skew_severity,
                },
                "illumination": {
                    "value": binary["illumination"],
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.contrast_severity,
                },
                "artifacts": {
                    "value": binary["artifacts"],
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.compression_severity,
                },
            },
            # Metadata
            "label_source": self.label_source,
            "label_confidence": self.label_confidence,
            "label_variance": self.label_variance,
            "image_path": self.image_path,
            "augmentation_params": self.augmentation_params,
        }


# =============================================================================
# Conversion Functions
# =============================================================================


def binary_to_continuous(
    binary_labels: dict[str, Any],
    confidence: float = 0.7,
    source: str = "weak_supervision",
) -> ContinuousQualityLabel:
    """Convert binary labels to soft continuous labels.

    Existing binary labels are converted to continuous by using the
    confidence as the severity when label=1.

    Args:
        binary_labels: Dict with issue names and values (0/1 or dicts with 'value')
        confidence: Confidence/severity to assign for positive labels
        source: Label source identifier

    Returns:
        ContinuousQualityLabel with soft severity values
    """

    # Handle both simple dict and nested dict formats
    def get_value(v: Any) -> int:
        if isinstance(v, dict):
            return int(v.get("value", 0))
        return int(v)

    # Map binary values to severity
    blur = get_value(binary_labels.get("blur", 0)) * confidence
    noise = get_value(binary_labels.get("noise", 0)) * confidence
    skew = get_value(binary_labels.get("skew", 0)) * confidence
    illumination = get_value(binary_labels.get("illumination", 0)) * confidence
    artifacts = get_value(binary_labels.get("artifacts", 0)) * confidence

    return ContinuousQualityLabel(
        blur_severity=blur,
        noise_severity=noise,
        skew_severity=skew,
        contrast_severity=illumination,
        compression_severity=artifacts,
        label_source=source,  # type: ignore
        label_confidence=confidence,
    )


def aggregate_labels(
    labels: list[ContinuousQualityLabel],
    method: Literal["mean", "median", "max", "weighted"] = "weighted",
) -> ContinuousQualityLabel:
    """Aggregate multiple labels (e.g., from ensemble models).

    Args:
        labels: List of ContinuousQualityLabel instances
        method: Aggregation method
            - "mean": Simple average
            - "median": Median value
            - "max": Maximum severity (conservative)
            - "weighted": Weighted by label_confidence

    Returns:
        Aggregated ContinuousQualityLabel
    """
    if not labels:
        return ContinuousQualityLabel()

    if len(labels) == 1:
        return labels[0]

    import numpy as np

    # Extract severity vectors
    vectors = np.array([l.get_extended_severity_vector() for l in labels])
    confidences = np.array([l.label_confidence for l in labels])

    if method == "mean":
        aggregated = vectors.mean(axis=0)
    elif method == "median":
        aggregated = np.median(vectors, axis=0)
    elif method == "max":
        aggregated = vectors.max(axis=0)
    elif method == "weighted":
        weights = confidences / confidences.sum()
        aggregated = np.average(vectors, axis=0, weights=weights)
    else:
        raise ValueError(f"Unknown aggregation method: {method}")

    # Compute variance for GDBC
    variance = vectors.var(axis=0).mean()

    return ContinuousQualityLabel(
        blur_severity=float(aggregated[0]),
        noise_severity=float(aggregated[1]),
        skew_severity=float(aggregated[2]),
        contrast_severity=float(aggregated[3]),
        compression_severity=float(aggregated[4]),
        ink_degradation=float(aggregated[5]),
        paper_degradation=float(aggregated[6]),
        bleed_through=float(aggregated[7]),
        label_source="mllm_pseudo",
        label_confidence=float(confidences.mean()),
        label_variance=float(variance),
    )


def load_label_file(path: str | Path) -> ContinuousQualityLabel:
    """Load a label file and convert to ContinuousQualityLabel.

    Handles multiple formats:
    - Phase 7 continuous labels (direct load)
    - Weak supervision labels (convert from binary)
    - MLLM pseudo-labels

    Args:
        path: Path to JSON label file

    Returns:
        ContinuousQualityLabel instance
    """
    import json

    # Validate path to prevent directory traversal
    path = validate_safe_path(path, must_exist=True)
    with open(path) as f:
        data = json.load(f)

    # Check for continuous label format
    if "blur_severity" in data or "continuous_labels" in data:
        # Phase 7 format or MLLM pseudo-label format
        if "continuous_labels" in data:
            data = {**data, **data["continuous_labels"]}
        return ContinuousQualityLabel(
            **{
                k: v
                for k, v in data.items()
                if k in ContinuousQualityLabel.model_fields
            }
        )

    # Weak supervision format (binary labels with quality_scores)
    if "labels" in data:
        # Try to extract severity from quality_scores or metadata
        quality_scores = data.get("quality_scores", {})

        return ContinuousQualityLabel(
            blur_severity=quality_scores.get("blur", 0.0)
            if isinstance(quality_scores.get("blur"), float)
            else float(data["labels"].get("blur", {}).get("severity", 0.0)),
            noise_severity=quality_scores.get("noise", 0.0)
            if isinstance(quality_scores.get("noise"), float)
            else float(data["labels"].get("noise", {}).get("severity", 0.0)),
            skew_severity=quality_scores.get("skew", 0.0)
            if isinstance(quality_scores.get("skew"), float)
            else float(data["labels"].get("skew", {}).get("severity", 0.0)),
            contrast_severity=quality_scores.get(
                "contrast", quality_scores.get("rms_contrast", 0.0)
            ),
            compression_severity=quality_scores.get("blockiness", 0.0)
            / 10.0,  # Normalize
            overall_quality=quality_scores.get("overall", 1.0),
            label_source="weak_supervision",
            image_path=data.get("image_path", ""),
        )

    # Fallback: convert from binary
    return binary_to_continuous(data)


def save_label_file(
    label: ContinuousQualityLabel,
    path: str | Path,
) -> Path:
    """Save ContinuousQualityLabel to JSON file.

    Args:
        label: Label to save
        path: Output path

    Returns:
        Path to saved file
    """
    import json

    # Validate path to prevent directory traversal
    path = validate_safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(label.to_training_dict(), f, indent=2)

    return path


if __name__ == "__main__":
    # Example usage
    label = ContinuousQualityLabel(
        blur_severity=0.35,
        noise_severity=0.20,
        skew_severity=0.10,
        contrast_severity=0.15,
        compression_severity=0.25,
        label_source="augraphy",
    )

    print("Continuous Label:")
    print(f"  Blur: {label.blur_severity:.2f}")
    print(f"  Overall Quality: {label.overall_quality:.2f}")
    print(f"\nBinary Labels: {label.get_binary_labels()}")
    print(f"\nSeverity Vector: {label.get_severity_vector()}")
