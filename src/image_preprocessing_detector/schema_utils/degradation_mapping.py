"""Degradation-to-Issue Mapping Module.

Maps the 45-dimensional degradation taxonomy (Layer 2 training) to the
7 runtime issue types (Project B output schema).

This module provides:
1. DEGRADATION_INDEX: Complete 45-type taxonomy with group/index mapping
2. DEGRADATION_TO_ISSUE: Maps each degradation type to runtime issue type
3. Utility functions for converting between representations

References:
- Layer 2 Schema: docs/schema/layer2_enrichment.schema.json
- Output Schema: docs/schema/document_metadata.schema.json
- Detection Taxonomy: docs/reference/detection-taxonomy.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class RuntimeIssueType(str, Enum):
    """Runtime issue types from document_metadata.schema.json."""

    NOISE = "noise"
    BLUR = "blur"
    SKEW = "skew"
    PERSPECTIVE = "perspective"
    LOW_CONTRAST = "low_contrast"
    ORIENTATION = "orientation"
    LOW_DPI = "low_dpi"


class SeverityLevel(str, Enum):
    """Severity levels for detected issues."""

    NONE = "none"
    MILD = "mild"
    LOW = "low"
    MODERATE = "moderate"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"
    CRITICAL = "critical"


class DegradationGroup(str, Enum):
    """Degradation groups from the 45-type taxonomy."""

    BLUR_FOCUS = "blur_focus"
    NOISE = "noise"
    GEOMETRIC = "geometric"
    ILLUMINATION = "illumination"
    COMPRESSION = "compression"
    PHYSICAL = "physical"
    TEXT_CONTENT = "text_content"
    SCANNER = "scanner"


@dataclass(frozen=True)
class DegradationType:
    """Single degradation type definition."""

    name: str
    index: int
    group: DegradationGroup
    runtime_issue: RuntimeIssueType
    description: str


# Complete 45-dimensional degradation index
# Maps to Layer 2 iqa_vector indices
DEGRADATION_INDEX: dict[int, DegradationType] = {
    # === Blur/Focus Group (indices 0-5) ===
    0: DegradationType(
        name="motion_blur",
        index=0,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Motion blur from camera shake during capture",
    ),
    1: DegradationType(
        name="defocus_blur",
        index=1,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Out-of-focus blur from incorrect focal distance",
    ),
    2: DegradationType(
        name="gaussian_blur",
        index=2,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="General Gaussian blur degradation",
    ),
    3: DegradationType(
        name="lens_aberration",
        index=3,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Optical lens aberration causing edge softness",
    ),
    4: DegradationType(
        name="depth_of_field",
        index=4,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Shallow depth of field causing partial blur",
    ),
    5: DegradationType(
        name="camera_shake",
        index=5,
        group=DegradationGroup.BLUR_FOCUS,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Blur from camera movement during exposure",
    ),
    # === Noise Group (indices 6-12) ===
    6: DegradationType(
        name="gaussian_noise",
        index=6,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Random Gaussian noise across image",
    ),
    7: DegradationType(
        name="salt_pepper_noise",
        index=7,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Salt and pepper impulse noise",
    ),
    8: DegradationType(
        name="speckle_noise",
        index=8,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Multiplicative speckle noise pattern",
    ),
    9: DegradationType(
        name="film_grain",
        index=9,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Film grain texture from analog capture",
    ),
    10: DegradationType(
        name="sensor_noise",
        index=10,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Digital sensor noise (high ISO)",
    ),
    11: DegradationType(
        name="quantization_noise",
        index=11,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Quantization artifacts from bit depth reduction",
    ),
    12: DegradationType(
        name="banding",
        index=12,
        group=DegradationGroup.NOISE,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Horizontal or vertical banding artifacts",
    ),
    # === Geometric Group (indices 13-18) ===
    13: DegradationType(
        name="skew",
        index=13,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.SKEW,
        description="Document rotation/skew from scanning",
    ),
    14: DegradationType(
        name="rotation",
        index=14,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.ORIENTATION,
        description="Significant rotation (90/180/270 degrees)",
    ),
    15: DegradationType(
        name="perspective",
        index=15,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.PERSPECTIVE,
        description="Perspective distortion from camera angle",
    ),
    16: DegradationType(
        name="barrel_distortion",
        index=16,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.PERSPECTIVE,
        description="Barrel lens distortion",
    ),
    17: DegradationType(
        name="pincushion_distortion",
        index=17,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.PERSPECTIVE,
        description="Pincushion lens distortion",
    ),
    18: DegradationType(
        name="page_curl",
        index=18,
        group=DegradationGroup.GEOMETRIC,
        runtime_issue=RuntimeIssueType.PERSPECTIVE,
        description="Page curl near binding",
    ),
    # === Illumination Group (indices 19-25) ===
    19: DegradationType(
        name="underexposure",
        index=19,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Image too dark from underexposure",
    ),
    20: DegradationType(
        name="overexposure",
        index=20,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Image washed out from overexposure",
    ),
    21: DegradationType(
        name="uneven_lighting",
        index=21,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Non-uniform lighting across document",
    ),
    22: DegradationType(
        name="shadow",
        index=22,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Shadows obscuring content",
    ),
    23: DegradationType(
        name="glare",
        index=23,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Specular glare/reflection",
    ),
    24: DegradationType(
        name="vignetting",
        index=24,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Darkening at image corners",
    ),
    25: DegradationType(
        name="color_cast",
        index=25,
        group=DegradationGroup.ILLUMINATION,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Incorrect white balance/color cast",
    ),
    # === Compression Group (indices 26-29) ===
    26: DegradationType(
        name="jpeg_artifacts",
        index=26,
        group=DegradationGroup.COMPRESSION,
        runtime_issue=RuntimeIssueType.NOISE,
        description="JPEG block artifacts",
    ),
    27: DegradationType(
        name="jpeg2000_artifacts",
        index=27,
        group=DegradationGroup.COMPRESSION,
        runtime_issue=RuntimeIssueType.NOISE,
        description="JPEG2000 wavelet artifacts",
    ),
    28: DegradationType(
        name="webp_artifacts",
        index=28,
        group=DegradationGroup.COMPRESSION,
        runtime_issue=RuntimeIssueType.NOISE,
        description="WebP compression artifacts",
    ),
    29: DegradationType(
        name="low_bitrate",
        index=29,
        group=DegradationGroup.COMPRESSION,
        runtime_issue=RuntimeIssueType.LOW_DPI,
        description="Low bitrate causing quality loss",
    ),
    # === Physical Group (indices 30-36) ===
    30: DegradationType(
        name="paper_yellowing",
        index=30,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Aged paper yellowing",
    ),
    31: DegradationType(
        name="foxing",
        index=31,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Brown spots from fungal growth",
    ),
    32: DegradationType(
        name="staining",
        index=32,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Coffee/water stains on document",
    ),
    33: DegradationType(
        name="bleed_through",
        index=33,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Ink bleed-through from reverse side",
    ),
    34: DegradationType(
        name="fading",
        index=34,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Faded ink or print",
    ),
    35: DegradationType(
        name="creasing",
        index=35,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.PERSPECTIVE,
        description="Paper creases affecting flatness",
    ),
    36: DegradationType(
        name="roller_marks",
        index=36,
        group=DegradationGroup.PHYSICAL,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Scanner roller marks",
    ),
    # === Text/Content Group (indices 37-41) ===
    37: DegradationType(
        name="faint_text",
        index=37,
        group=DegradationGroup.TEXT_CONTENT,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Light or faint text",
    ),
    38: DegradationType(
        name="broken_characters",
        index=38,
        group=DegradationGroup.TEXT_CONTENT,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Broken or incomplete characters",
    ),
    39: DegradationType(
        name="merged_characters",
        index=39,
        group=DegradationGroup.TEXT_CONTENT,
        runtime_issue=RuntimeIssueType.BLUR,
        description="Characters merged together",
    ),
    40: DegradationType(
        name="halftone_interference",
        index=40,
        group=DegradationGroup.TEXT_CONTENT,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Halftone/moire interference pattern",
    ),
    41: DegradationType(
        name="moire_pattern",
        index=41,
        group=DegradationGroup.TEXT_CONTENT,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Moire pattern from rescanning",
    ),
    # === Scanner Group (indices 42-44) ===
    42: DegradationType(
        name="dust_scratches",
        index=42,
        group=DegradationGroup.SCANNER,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Dust and scratches on scanner glass",
    ),
    43: DegradationType(
        name="scan_lines",
        index=43,
        group=DegradationGroup.SCANNER,
        runtime_issue=RuntimeIssueType.NOISE,
        description="Horizontal scan lines",
    ),
    44: DegradationType(
        name="edge_shadow",
        index=44,
        group=DegradationGroup.SCANNER,
        runtime_issue=RuntimeIssueType.LOW_CONTRAST,
        description="Shadows at document edges",
    ),
}

# Quick lookup by name
DEGRADATION_BY_NAME: dict[str, DegradationType] = {
    d.name: d for d in DEGRADATION_INDEX.values()
}

# Mapping from degradation name to runtime issue type (simplified lookup)
DEGRADATION_TO_ISSUE: dict[str, str] = {
    d.name: d.runtime_issue.value for d in DEGRADATION_INDEX.values()
}

# Group boundaries for vector slicing
GROUP_RANGES: dict[DegradationGroup, tuple[int, int]] = {
    DegradationGroup.BLUR_FOCUS: (0, 6),
    DegradationGroup.NOISE: (6, 13),
    DegradationGroup.GEOMETRIC: (13, 19),
    DegradationGroup.ILLUMINATION: (19, 26),
    DegradationGroup.COMPRESSION: (26, 30),
    DegradationGroup.PHYSICAL: (30, 37),
    DegradationGroup.TEXT_CONTENT: (37, 42),
    DegradationGroup.SCANNER: (42, 45),
}


class RuntimeIssue(TypedDict):
    """Runtime issue structure matching document_metadata.schema.json."""

    type: str
    confidence: float
    severity: str
    metrics: dict


def iqa_vector_to_runtime_issues(
    iqa_vector: list[float],
    threshold: float = 0.3,
    min_confidence: float = 0.5,
) -> list[RuntimeIssue]:
    """Convert 45-dim iqa_vector to runtime DetectedIssue list.

    Aggregates multiple degradations into their corresponding runtime
    issue types, taking the maximum severity for each issue type.

    Args:
        iqa_vector (list[float]): 45-dimensional severity vector (0.0-1.0 per degradation)
        threshold (float): Minimum severity to consider as "detected"
        min_confidence (float): Minimum confidence to report

    Returns:
        list[RuntimeIssue]: List of RuntimeIssue dicts matching document_metadata.schema.json

    Raises:
        ValueError: If iqa_vector does not have exactly 45 dimensions.

    Example:
        >>> vector = [0.0] * 45
        >>> vector[0] = 0.65  # motion_blur
        >>> vector[13] = 0.42  # skew
        >>> issues = iqa_vector_to_runtime_issues(vector)
        >>> print(issues)
        [
            {"type": "blur", "confidence": 0.65, "severity": "medium", ...},
            {"type": "skew", "confidence": 0.42, "severity": "low", ...}
        ]
    """
    if len(iqa_vector) != 45:
        raise ValueError(f"Expected 45-dim vector, got {len(iqa_vector)}")

    # Aggregate by runtime issue type
    issue_scores: dict[str, list[tuple[float, str]]] = {}

    for idx, severity in enumerate(iqa_vector):
        if severity < threshold:
            continue

        degradation = DEGRADATION_INDEX[idx]
        issue_type = degradation.runtime_issue.value

        if issue_type not in issue_scores:
            issue_scores[issue_type] = []

        issue_scores[issue_type].append((severity, degradation.name))

    # Build runtime issues
    issues: list[RuntimeIssue] = []

    for issue_type, scores in issue_scores.items():
        # Take maximum severity across all degradations mapping to this issue
        max_severity = max(s[0] for s in scores)
        contributing = [s[1] for s in scores]

        if max_severity < min_confidence:
            continue

        # Map numeric severity to categorical
        if max_severity >= 0.8:
            severity_label = "critical"
        elif max_severity >= 0.6:
            severity_label = "high"
        elif max_severity >= 0.4:
            severity_label = "medium"
        else:
            severity_label = "low"

        issues.append(
            RuntimeIssue(
                type=issue_type,
                confidence=round(max_severity, 3),
                severity=severity_label,
                metrics={
                    "contributing_degradations": contributing,
                    "max_severity_numeric": round(max_severity, 3),
                },
            )
        )

    # Sort by severity (highest first)
    issues.sort(key=lambda x: x["confidence"], reverse=True)

    return issues


def runtime_issues_to_iqa_vector(
    issues: list[RuntimeIssue],
) -> list[float]:
    """Convert runtime issues back to 45-dim iqa_vector.

    This is a lossy conversion since multiple degradation types map
    to the same runtime issue. Uses the first degradation in each group.

    Args:
        issues (list[RuntimeIssue]): List of RuntimeIssue dicts

    Returns:
        list[float]: 45-dimensional severity vector"""
    vector = [0.0] * 45

    # Map issue type to first degradation index in that group
    issue_to_primary_index: dict[str, int] = {
        "blur": 0,  # motion_blur
        "noise": 6,  # gaussian_noise
        "skew": 13,  # skew
        "perspective": 15,  # perspective
        "low_contrast": 19,  # underexposure
        "orientation": 14,  # rotation
        "low_dpi": 29,  # low_bitrate
    }

    for issue in issues:
        issue_type = issue["type"]
        confidence = issue["confidence"]

        if issue_type in issue_to_primary_index:
            idx = issue_to_primary_index[issue_type]
            vector[idx] = max(vector[idx], confidence)

    return vector


def get_degradation_group(index: int) -> DegradationGroup:
    """Get the degradation group for a given index."""
    if 0 <= index < 6:
        return DegradationGroup.BLUR_FOCUS
    if 6 <= index < 13:
        return DegradationGroup.NOISE
    if 13 <= index < 19:
        return DegradationGroup.GEOMETRIC
    if 19 <= index < 26:
        return DegradationGroup.ILLUMINATION
    if 26 <= index < 30:
        return DegradationGroup.COMPRESSION
    if 30 <= index < 37:
        return DegradationGroup.PHYSICAL
    if 37 <= index < 42:
        return DegradationGroup.TEXT_CONTENT
    if 42 <= index < 45:
        return DegradationGroup.SCANNER
    raise ValueError(f"Index {index} out of range [0, 44]")


def aggregate_group_scores(
    iqa_vector: list[float],
) -> dict[str, float]:
    """Aggregate iqa_vector into group-level scores.

    Uses max-pooling within each group.

    Args:
        iqa_vector (list[float]): 45-dimensional severity vector

    Returns:
        dict[str, float]: Dict mapping group name to maximum severity in that group

    Raises:
        ValueError: If iqa_vector does not have exactly 45 dimensions.
    """
    if len(iqa_vector) != 45:
        raise ValueError(f"Expected 45-dim vector, got {len(iqa_vector)}")

    result = {}
    for group, (start, end) in GROUP_RANGES.items():
        group_scores = iqa_vector[start:end]
        result[group.value] = max(group_scores) if group_scores else 0.0

    return result
