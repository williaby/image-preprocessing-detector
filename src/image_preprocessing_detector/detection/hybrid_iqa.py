"""Hybrid IQA integration for per-element quality assessment.

FR-3.14: Hybrid IQA performs quality assessment on individual document elements
(images, tables, figures) rather than the full page.

This module bridges the detection pipeline with the DocumentElement schema,
populating quality_issues for elements that require separate assessment.
"""

from typing import TYPE_CHECKING

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    Severity,
    detect_blur,
    detect_contrast,
    detect_lighting,
    detect_noise,
)
from image_preprocessing_detector.schema import (
    ActionType,
    DetectedIssue,
    DocumentElement,
    ElementCategory,
    IssueType,
)
from image_preprocessing_detector.utils import get_logger

if TYPE_CHECKING:
    from image_preprocessing_detector.detection.iqa_ml import (
        MLIQADetector,
    )

logger = get_logger(__name__)


def extract_element_region(
    page_image: np.ndarray,
    element: DocumentElement,
) -> np.ndarray | None:
    """Extract element region from page image using bounding box.

    Args:
        page_image (np.ndarray): Full page image (BGR format)
        element (DocumentElement): Document element with COCO-format bbox [x, y, width, height]

    Returns:
        np.ndarray | None: Cropped element image or None if bbox is invalid"""
    if not element.bbox or len(element.bbox) < 4:
        logger.warning("Invalid bbox for element", element_id=element.id)
        return None

    x, y, w, h = element.bbox
    h_page, w_page = page_image.shape[:2]

    # Validate bounds
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        logger.warning(
            "Negative bbox dimensions", element_id=element.id, bbox=element.bbox
        )
        return None

    # Clip to page bounds
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w_page, x + w)
    y2 = min(h_page, y + h)

    if x2 <= x1 or y2 <= y1:
        logger.warning("Empty region after clipping", element_id=element.id)
        return None

    return page_image[y1:y2, x1:x2].copy()


def assess_element_quality_classical(
    element_image: np.ndarray,
    element: DocumentElement,
) -> list[DetectedIssue]:
    """Assess element quality using classical IQA detectors.

    Args:
        element_image (np.ndarray): Cropped element image (BGR format)
        element (DocumentElement): Document element metadata

    Returns:
        list[DetectedIssue]: List of detected quality issues"""
    issues: list[DetectedIssue] = []

    # Blur detection
    blur_result = detect_blur(element_image)
    if blur_result.is_blurred:
        issues.append(
            DetectedIssue(
                issue_type=IssueType.BLUR,
                severity=blur_result.severity,
                confidence=min(1.0, blur_result.blur_score / 100.0),
                description=f"Element blur detected (score: {blur_result.blur_score:.1f})",
                bbox=element.bbox,
                metrics={"blur_score": blur_result.blur_score},
                recommended_action=ActionType.SHARPEN,
            )
        )

    # Contrast detection
    contrast_result = detect_contrast(element_image)
    if contrast_result.is_low_contrast:
        issues.append(
            DetectedIssue(
                issue_type=IssueType.LOW_CONTRAST,
                severity=contrast_result.severity,
                confidence=1.0 - contrast_result.score,
                description=f"Low contrast in element (score: {contrast_result.score:.2f})",
                bbox=element.bbox,
                metrics={"contrast_score": contrast_result.score},
                recommended_action=ActionType.ENHANCE_CONTRAST,
            )
        )

    # Lighting/illumination detection
    try:
        lighting_result = detect_lighting(element_image)
        if lighting_result.has_issues:
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.LIGHTING,
                    severity=lighting_result.severity,
                    confidence=1.0 - lighting_result.uniformity_score,
                    description=f"Uneven illumination in element (uniformity: {lighting_result.uniformity_score:.2f})",
                    bbox=element.bbox,
                    metrics={"uniformity_score": lighting_result.uniformity_score},
                    recommended_action=ActionType.ENHANCE_CONTRAST,
                )
            )
    except Exception as e:
        logger.debug("Lighting detection skipped", error=str(e))

    # Noise detection
    try:
        noise_result = detect_noise(element_image)
        if noise_result.is_noisy:
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.NOISE,
                    severity=noise_result.severity,
                    confidence=1.0 - noise_result.noise_score,
                    description=f"Noise detected in element (score: {noise_result.noise_score:.2f})",
                    bbox=element.bbox,
                    metrics={"noise_score": noise_result.noise_score},
                    recommended_action=ActionType.DENOISE,
                )
            )
    except Exception as e:
        logger.debug("Noise detection skipped", error=str(e))

    return issues


def assess_element_quality_ml(
    element_image: np.ndarray,
    element: DocumentElement,
    ml_detector: "MLIQADetector",
) -> list[DetectedIssue]:
    """Assess element quality using ML IQA detector.

    Args:
        element_image (np.ndarray): Cropped element image (BGR format)
        element (DocumentElement): Document element metadata
        ml_detector ('MLIQADetector'): ML IQA detector instance

    Returns:
        list[DetectedIssue]: List of detected quality issues from ML model"""
    issues: list[DetectedIssue] = []

    try:
        # Run ML inference on element
        scores = ml_detector.run_student_inference(element_image)

        # Map ML scores to detected issues
        score_mappings = [
            (scores.blur_score, IssueType.BLUR, ActionType.SHARPEN, "ML blur"),
            (scores.noise_score, IssueType.NOISE, ActionType.DENOISE, "ML noise"),
            (
                scores.contrast_score,
                IssueType.LOW_CONTRAST,
                ActionType.ENHANCE_CONTRAST,
                "ML contrast",
            ),
            (
                scores.compression_score,
                IssueType.COMPRESSION_ARTIFACTS,
                None,
                "ML compression",
            ),
        ]

        for score, issue_type, action, name in score_mappings:
            # ML scores: 0=bad, 1=good; threshold at 0.5
            if score < 0.5:
                if score < 0.3:
                    severity = Severity.CRITICAL
                elif score < 0.4:
                    severity = Severity.HIGH
                else:
                    severity = Severity.MEDIUM
                issues.append(
                    DetectedIssue(
                        issue_type=issue_type,
                        severity=severity,
                        confidence=1.0 - score,
                        description=f"{name} issue detected (score: {score:.2f})",
                        bbox=element.bbox,
                        metrics={f"{name.lower().replace(' ', '_')}_score": score},
                        recommended_action=action,
                    )
                )

    except Exception as e:
        logger.warning("ML IQA failed for element", element_id=element.id, error=str(e))

    return issues


def assess_element_iqa(
    page_image: np.ndarray,
    element: DocumentElement,
    ml_detector: "MLIQADetector | None" = None,
    use_ml: bool = True,
) -> DocumentElement:
    """Assess quality for a single document element.

    Performs hybrid IQA: classical detectors + optional ML inference.

    Args:
        page_image (np.ndarray): Full page image (BGR format)
        element (DocumentElement): Document element to assess
        ml_detector ('MLIQADetector | None'): Optional ML IQA detector
        use_ml (bool): Whether to use ML IQA (if detector available)

    Returns:
        DocumentElement: Updated DocumentElement with quality_issues populated"""
    # Only assess quality for elements that benefit from it
    assessable_categories = {
        ElementCategory.IMAGE,
        ElementCategory.TABLE,
        ElementCategory.FIGURE,
        ElementCategory.HANDWRITING,
    }

    if element.category not in assessable_categories:
        logger.debug(
            "Skipping IQA for element category",
            element_id=element.id,
            category=element.category.value,
        )
        return element

    # Extract element region
    element_image = extract_element_region(page_image, element)
    if element_image is None:
        logger.warning("Could not extract element region", element_id=element.id)
        return element

    # Skip very small elements
    if element_image.shape[0] < 32 or element_image.shape[1] < 32:
        logger.debug(
            "Skipping IQA for small element",
            element_id=element.id,
            shape=element_image.shape,
        )
        return element

    # Run classical IQA
    classical_issues = assess_element_quality_classical(element_image, element)

    # Run ML IQA if available and enabled
    ml_issues: list[DetectedIssue] = []
    if use_ml and ml_detector is not None:
        ml_issues = assess_element_quality_ml(element_image, element, ml_detector)

    # Combine issues, preferring ML results when both detect same issue type
    all_issues = classical_issues.copy()
    classical_types = {issue.issue_type for issue in classical_issues}

    for ml_issue in ml_issues:
        if ml_issue.issue_type not in classical_types:
            all_issues.append(ml_issue)

    # Update element
    element.quality_issues = all_issues
    element.needs_correction = len(all_issues) > 0

    logger.debug(
        "Element IQA complete",
        element_id=element.id,
        issues_found=len(all_issues),
    )

    return element


def assess_page_elements_iqa(
    page_image: np.ndarray,
    elements: list[DocumentElement],
    ml_detector: "MLIQADetector | None" = None,
    use_ml: bool = True,
) -> list[DocumentElement]:
    """Assess quality for all elements on a page.

    Args:
        page_image (np.ndarray): Full page image (BGR format)
        elements (list[DocumentElement]): List of document elements to assess
        ml_detector ('MLIQADetector | None'): Optional ML IQA detector
        use_ml (bool): Whether to use ML IQA (if detector available)

    Returns:
        list[DocumentElement]: List of updated DocumentElements with quality_issues populated"""
    assessed_elements = []

    for element in elements:
        assessed_element = assess_element_iqa(
            page_image=page_image,
            element=element,
            ml_detector=ml_detector,
            use_ml=use_ml,
        )
        assessed_elements.append(assessed_element)

    # Log summary
    total_issues = sum(len(e.quality_issues) for e in assessed_elements)
    elements_with_issues = sum(1 for e in assessed_elements if e.needs_correction)

    logger.info(
        "Page element IQA complete",
        total_elements=len(elements),
        elements_with_issues=elements_with_issues,
        total_issues=total_issues,
    )

    return assessed_elements
