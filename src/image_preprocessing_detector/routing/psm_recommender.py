"""PSM Recommender — Tesseract Page Segmentation Mode selection.

Maps document layout characteristics to Tesseract PSM values (0-13) using a
priority-ordered lookup table. Rules are evaluated top-to-bottom; the first
matching rule wins.

Priority order:
    1. Low orientation confidence → PSM 1 (auto + OSD)
    2. Sparse text with few elements → PSM 11 (sparse text)
    3. Tables present → PSM 6 (uniform block)
    4. Single-column layout → PSM 6
    5. Multi-column layout → PSM 3 (fully automatic)
    6. Handwriting present → PSM 6
    7. Default → PSM 3
"""

from __future__ import annotations

from dataclasses import dataclass

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Valid Tesseract PSM range
_PSM_MIN = 0
_PSM_MAX = 13

# Thresholds
_ORIENTATION_CONFIDENCE_THRESHOLD = 0.5
_SPARSE_ELEMENT_COUNT_THRESHOLD = 5


@dataclass(frozen=True)
class PSMInput:
    """Input characteristics for PSM recommendation.

    Attributes:
        layout_type (str | None): Coarse page layout classification (e.g. "single_column",
            "multi_column", "table_dominant", "figure_dominant", "mixed").
        has_tables (bool): Whether the page contains detected tables.
        is_sparse (bool): Whether the text layout is sparse / scattered.
        has_handwriting (bool): Whether handwriting was detected on the page.
        orientation_confidence (float): Confidence in the detected page orientation
            (0 = unknown, 1 = certain).
        element_count (int): Number of detected layout elements on the page.
    """

    layout_type: str | None = None
    has_tables: bool = False
    is_sparse: bool = False
    has_handwriting: bool = False
    orientation_confidence: float = 1.0
    element_count: int = 0


@dataclass(frozen=True)
class PSMRecommendation:
    """Recommended Tesseract Page Segmentation Mode.

    Attributes:
        psm (int): Tesseract PSM value (0-13).
        reason (str): Human-readable explanation of why this PSM was chosen.
        confidence (float): Confidence in the recommendation (0-1).
    """

    psm: int
    reason: str
    confidence: float


class PSMRecommender:
    """Recommend a Tesseract Page Segmentation Mode from layout features.

    Rules are evaluated in priority order. The first matching rule produces
    the recommendation; subsequent rules are skipped.

    Example:
        >>> recommender = PSMRecommender()
        >>> inp = PSMInput(layout_type="single_column", has_tables=False)
        >>> rec = recommender.recommend(inp)
        >>> rec.psm
        6
    """

    def recommend(self, inp: PSMInput) -> PSMRecommendation:
        """Select the best PSM for the given page characteristics.

        Args:
            inp (PSMInput): Layout characteristics for the page.

        Returns:
            PSMRecommendation: PSMRecommendation with the selected PSM, reason, and confidence.
        """
        # Rule 1: Low orientation confidence → PSM 1 (auto + OSD)
        if inp.orientation_confidence < _ORIENTATION_CONFIDENCE_THRESHOLD:
            rec = PSMRecommendation(
                psm=1,
                reason="Low orientation confidence; using automatic segmentation with OSD",
                confidence=0.7,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="low_orientation",
            )
            return rec

        # Rule 2: Sparse text with few elements → PSM 11
        if inp.is_sparse and inp.element_count < _SPARSE_ELEMENT_COUNT_THRESHOLD:
            rec = PSMRecommendation(
                psm=11,
                reason="Sparse text with few layout elements",
                confidence=0.8,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="sparse_text",
            )
            return rec

        # Rule 3: Tables present → PSM 6
        if inp.has_tables:
            rec = PSMRecommendation(
                psm=6,
                reason="Tables detected; using uniform block segmentation",
                confidence=0.85,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="has_tables",
            )
            return rec

        # Rule 4: Single-column layout → PSM 6
        if inp.layout_type == "single_column":
            rec = PSMRecommendation(
                psm=6,
                reason="Single-column layout; using uniform block segmentation",
                confidence=0.9,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="single_column",
            )
            return rec

        # Rule 5: Multi-column layout → PSM 3
        if inp.layout_type == "multi_column":
            rec = PSMRecommendation(
                psm=3,
                reason="Multi-column layout; using fully automatic segmentation",
                confidence=0.9,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="multi_column",
            )
            return rec

        # Rule 6: Handwriting present → PSM 6
        if inp.has_handwriting:
            rec = PSMRecommendation(
                psm=6,
                reason="Handwriting detected; using uniform block segmentation",
                confidence=0.75,
            )
            logger.debug(
                "psm_recommendation",
                psm=rec.psm,
                reason=rec.reason,
                rule="has_handwriting",
            )
            return rec

        # Rule 7: Default → PSM 3
        rec = PSMRecommendation(
            psm=3,
            reason="Default fully automatic page segmentation",
            confidence=0.6,
        )
        logger.debug(
            "psm_recommendation",
            psm=rec.psm,
            reason=rec.reason,
            rule="default",
        )
        return rec


# Module-level singleton
_default_recommender: PSMRecommender | None = None


def _get_default_recommender() -> PSMRecommender:
    """Return (and lazily create) the module-level PSMRecommender singleton."""
    global _default_recommender
    if _default_recommender is None:
        _default_recommender = PSMRecommender()
    return _default_recommender


def recommend_psm(inp: PSMInput) -> PSMRecommendation:
    """Convenience function — recommend a PSM using the default recommender.

    Args:
        inp (PSMInput): Layout characteristics for the page.

    Returns:
        PSMRecommendation: PSMRecommendation with the selected PSM, reason, and confidence.
    """
    return _get_default_recommender().recommend(inp)
