"""Degradation severity classifier for document preprocessing routing.

Classifies documents as "simple" (classical CV corrections sufficient) or
"complex" (needs DocRes/VLM pipeline) based on capture method, quality score,
and degradation indicators. Pure Python logic - no CV dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Camera capture methods that always indicate complex degradation.
_CAMERA_CAPTURE_METHODS = frozenset(
    {
        "camera_professional",
        "camera_smartphone",
    }
)

# DQS threshold below which the document is considered severely degraded.
_DQS_SEVERE_THRESHOLD = 0.5


@dataclass(frozen=True)
class DegradationInput:
    """Input signals for degradation severity classification.

    Attributes:
        capture_method: How the document was digitised (CaptureMethod enum value).
        dqs_score: Document Quality Score in [0, 1], or None if unavailable.
        has_shadows: Whether shadow artefacts were detected.
        has_warping: Whether geometric warping was detected.
        has_handwriting: Whether handwriting regions were detected.
        has_bleed_through: Whether bleed-through artefacts were detected.
    """

    capture_method: str | None = None
    dqs_score: float | None = None
    has_shadows: bool = False
    has_warping: bool = False
    has_handwriting: bool = False
    has_bleed_through: bool = False


@dataclass(frozen=True)
class DegradationClassification:
    """Result of degradation severity classification.

    Attributes:
        severity: Overall severity label.
        reasons: Human-readable explanations for the classification.
        indicator_count: Number of severe indicators that were active.
        confidence: Classification confidence in [0, 1].
    """

    severity: Literal["simple", "complex"] = "simple"
    reasons: list[str] = field(default_factory=list)
    indicator_count: int = 0
    confidence: float = 1.0


class DegradationSeverityClassifier:
    """Classify degradation severity from document quality signals.

    The classifier uses a two-stage decision process:

    1. **Camera gate**: Any camera capture method immediately yields "complex"
       because camera-captured documents exhibit perspective distortion, uneven
       lighting, and variable focus that classical CV pipelines cannot fix.
    2. **Indicator count**: Four severe indicators are tallied (low DQS, shadows,
       warping, handwriting). Two or more triggers "complex"; fewer yields
       "simple". Bleed-through is tracked as a reason but is *not* counted as a
       severe indicator because classical binarisation handles it adequately.

    Confidence reflects how clear-cut the decision is: camera captures and high
    indicator counts yield high confidence; borderline cases (exactly 2
    indicators, or DQS near the threshold) yield lower confidence.
    """

    def classify(self, inp: DegradationInput) -> DegradationClassification:
        """Classify degradation severity for a single document.

        Args:
            inp: Aggregated quality signals for one document.

        Returns:
            Classification result with severity, reasons, count, and confidence.
        """
        reasons: list[str] = []
        indicator_count = 0

        # --- Stage 1: camera gate ---
        is_camera = (
            inp.capture_method is not None
            and inp.capture_method in _CAMERA_CAPTURE_METHODS
        )
        if is_camera:
            reasons.append(
                f"Camera capture method ({inp.capture_method}) implies "
                "perspective distortion and uneven lighting"
            )

        # --- Stage 2: severe indicator tally ---
        is_low_dqs = inp.dqs_score is not None and inp.dqs_score < _DQS_SEVERE_THRESHOLD
        if is_low_dqs:
            indicator_count += 1
            reasons.append(
                f"Low document quality score ({inp.dqs_score:.2f} < {_DQS_SEVERE_THRESHOLD})"
            )

        if inp.has_shadows:
            indicator_count += 1
            reasons.append("Shadow artefacts detected")

        if inp.has_warping:
            indicator_count += 1
            reasons.append("Geometric warping detected")

        if inp.has_handwriting:
            indicator_count += 1
            reasons.append("Handwriting regions detected")

        # Bleed-through is noted but not a severe indicator.
        if inp.has_bleed_through:
            reasons.append("Bleed-through artefacts detected (handled by binarisation)")

        # --- Decision ---
        is_complex = is_camera or indicator_count >= 2
        severity: Literal["simple", "complex"] = "complex" if is_complex else "simple"
        confidence = self._compute_confidence(
            is_camera=is_camera,
            indicator_count=indicator_count,
            dqs_score=inp.dqs_score,
        )

        if not reasons:
            reasons.append("No significant degradation indicators found")

        result = DegradationClassification(
            severity=severity,
            reasons=reasons,
            indicator_count=indicator_count,
            confidence=confidence,
        )

        logger.debug(
            "degradation_severity_classified",
            severity=result.severity,
            indicator_count=result.indicator_count,
            confidence=result.confidence,
        )

        return result

    @staticmethod
    def _compute_confidence(
        *,
        is_camera: bool,
        indicator_count: int,
        dqs_score: float | None,
    ) -> float:
        """Derive confidence from how clear-cut the decision is.

        High confidence cases:
        - Camera capture (always complex, unambiguous).
        - Zero indicators (clearly simple).
        - Three or more indicators (clearly complex).

        Lower confidence cases:
        - Exactly one indicator (simple, but not pristine).
        - Exactly two indicators (complex, but borderline).
        - DQS near the threshold boundary.

        Args:
            is_camera: Whether the document was camera-captured.
            indicator_count: Number of severe indicators active.
            dqs_score: Document quality score, if available.

        Returns:
            Confidence value in [0.5, 1.0].
        """
        if is_camera:
            # Camera gate is deterministic; still modulate slightly by indicator
            # count so a camera doc with extra problems shows even higher
            # confidence.
            return min(1.0, 0.90 + indicator_count * 0.025)

        if indicator_count == 0:
            return 0.95  # clearly simple

        if indicator_count == 1:
            return 0.80  # simple, but has one flag

        if indicator_count == 2:
            # Borderline complex -- lower confidence further when DQS is close
            # to the threshold.
            base = 0.70
            if dqs_score is not None:
                distance = abs(dqs_score - _DQS_SEVERE_THRESHOLD)
                # distance in [0, 0.5] maps to bonus in [0, 0.10]
                base += min(distance * 0.20, 0.10)
            return base

        # 3+ indicators -- clearly complex
        return min(1.0, 0.85 + (indicator_count - 3) * 0.05)


def classify_degradation_severity(
    inp: DegradationInput,
) -> DegradationClassification:
    """Module-level convenience wrapper around DegradationSeverityClassifier.

    Args:
        inp: Aggregated quality signals for one document.

    Returns:
        Classification result with severity, reasons, count, and confidence.
    """
    return DegradationSeverityClassifier().classify(inp)
