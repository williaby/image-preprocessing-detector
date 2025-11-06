"""
Image correction operations with guardrails.

Implements corrections for detected image quality issues:
- Deskew (rotation correction)
- Contrast enhancement (CLAHE)
- Sharpening (unsharp mask)
- Denoising
"""

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import Severity
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass
class CorrectionResult:
    """
    Result of a correction operation.

    Attributes:
        corrected_image: The corrected image
        applied: Whether correction was actually applied
        parameters: Parameters used for the correction
        skipped_reason: Reason if correction was skipped (None if applied)
    """

    corrected_image: np.ndarray
    applied: bool
    parameters: dict[str, Any]
    skipped_reason: str | None = None


class DeskewCorrector:
    """
    Corrects image skew using rotation.

    Includes guardrails to prevent over-correction and quality degradation.
    """

    def __init__(
        self,
        min_angle: float = 0.5,
        max_angle: float = 45.0,
        border_value: int = 255,
    ) -> None:
        """
        Initialize deskew corrector.

        Args:
            min_angle: Minimum angle to correct (< 0.5° skipped)
            max_angle: Maximum angle to correct (> 45° too risky)
            border_value: Border fill value (0-255, default white)
        """
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.border_value = border_value

        logger.info(
            "Deskew corrector initialized",
            min_angle=min_angle,
            max_angle=max_angle,
        )

    def correct(
        self, image: np.ndarray, angle: float, confidence: float = 1.0
    ) -> CorrectionResult:
        """
        Apply deskew correction.

        Args:
            image: Input image (BGR format)
            angle: Detected skew angle in degrees
            confidence: Detection confidence (0.0-1.0)

        Returns:
            CorrectionResult with corrected image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        abs_angle = abs(angle)

        # Guardrail 1: Skip if angle is too small
        if abs_angle < self.min_angle:
            logger.debug(
                "Skipping deskew (angle too small)",
                angle=angle,
                min_angle=self.min_angle,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"angle": angle},
                skipped_reason=f"Angle {abs_angle:.2f}° below threshold {self.min_angle}°",
            )

        # Guardrail 2: Skip if angle is too large (likely false detection)
        if abs_angle > self.max_angle:
            logger.warning(
                "Skipping deskew (angle too large, likely false detection)",
                angle=angle,
                max_angle=self.max_angle,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"angle": angle},
                skipped_reason=f"Angle {abs_angle:.2f}° exceeds max {self.max_angle}°",
            )

        # Guardrail 3: Skip if confidence is too low
        if confidence < 0.3:
            logger.debug(
                "Skipping deskew (low confidence)",
                angle=angle,
                confidence=confidence,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"angle": angle, "confidence": confidence},
                skipped_reason=f"Confidence {confidence:.2f} too low",
            )

        # Apply rotation
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new dimensions to avoid cropping
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Adjust transformation matrix for new dimensions
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        corrected = cv2.warpAffine(
            image,
            M,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(self.border_value, self.border_value, self.border_value),
        )

        logger.info(
            "Deskew correction applied",
            angle=angle,
            original_size=(w, h),
            new_size=(new_w, new_h),
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "angle": angle,
                "confidence": confidence,
                "original_size": (w, h),
                "new_size": (new_w, new_h),
            },
        )


class ContrastEnhancer:
    """
    Enhances image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Includes guardrails to prevent over-enhancement.
    """

    def __init__(
        self,
        clip_limit: float = 2.0,
        tile_grid_size: tuple[int, int] = (8, 8),
        min_score: float = 0.4,
    ) -> None:
        """
        Initialize contrast enhancer.

        Args:
            clip_limit: CLAHE clip limit (higher = more contrast)
            tile_grid_size: Size of grid for histogram equalization
            min_score: Minimum contrast score to skip enhancement
        """
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self.min_score = min_score

        logger.info(
            "Contrast enhancer initialized",
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
        )

    def correct(
        self, image: np.ndarray, score: float, severity: Severity
    ) -> CorrectionResult:
        """
        Apply contrast enhancement.

        Args:
            image: Input image (BGR format)
            score: Detected contrast score (0.0-1.0)
            severity: Issue severity

        Returns:
            CorrectionResult with enhanced image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        # Guardrail: Skip if contrast is already good
        if score >= self.min_score:
            logger.debug(
                "Skipping contrast enhancement (contrast already good)",
                score=score,
                min_score=self.min_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"score": score},
                skipped_reason=f"Contrast score {score:.2f} above threshold {self.min_score}",
            )

        # Adjust clip limit based on severity
        clip_limit = self.clip_limit
        if severity == Severity.CRITICAL:
            clip_limit *= 2.0  # More aggressive for critical cases
        elif severity == Severity.LOW:
            clip_limit *= 0.5  # Gentler for mild cases

        # Convert to LAB color space (better for contrast enhancement)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=self.tile_grid_size)
        l_enhanced = clahe.apply(l_channel)

        # Merge channels and convert back to BGR
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        corrected = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        logger.info(
            "Contrast enhancement applied",
            original_score=score,
            severity=severity.value,
            clip_limit=clip_limit,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "score": score,
                "severity": severity.value,
                "clip_limit": clip_limit,
                "tile_grid_size": self.tile_grid_size,
            },
        )


class Sharpener:
    """
    Sharpens blurred images using unsharp mask.

    Includes guardrails to prevent over-sharpening and noise amplification.
    """

    def __init__(
        self,
        amount: float = 1.0,
        kernel_size: int = 5,
        sigma: float = 1.0,
        min_blur_score: float = 200.0,
    ) -> None:
        """
        Initialize sharpener.

        Args:
            amount: Sharpening strength (0.0-2.0)
            kernel_size: Gaussian blur kernel size (odd number)
            sigma: Gaussian blur sigma
            min_blur_score: Minimum blur score to skip sharpening
        """
        self.amount = amount
        self.kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        self.sigma = sigma
        self.min_blur_score = min_blur_score

        logger.info(
            "Sharpener initialized",
            amount=amount,
            kernel_size=self.kernel_size,
        )

    def correct(
        self, image: np.ndarray, blur_score: float, severity: Severity
    ) -> CorrectionResult:
        """
        Apply sharpening correction.

        Args:
            image: Input image (BGR format)
            blur_score: Detected blur score (Laplacian variance)
            severity: Issue severity

        Returns:
            CorrectionResult with sharpened image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        # Guardrail: Skip if image is already sharp
        if blur_score >= self.min_blur_score:
            logger.debug(
                "Skipping sharpening (image already sharp)",
                blur_score=blur_score,
                min_blur_score=self.min_blur_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"blur_score": blur_score},
                skipped_reason=f"Blur score {blur_score:.1f} above threshold {self.min_blur_score}",
            )

        # Adjust sharpening amount based on severity
        amount = self.amount
        if severity == Severity.CRITICAL:
            amount *= 1.5  # More aggressive
        elif severity == Severity.LOW:
            amount *= 0.5  # Gentler

        # Guardrail: Cap amount to prevent over-sharpening
        amount = min(amount, 2.0)

        # Create unsharp mask
        blurred = cv2.GaussianBlur(
            image, (self.kernel_size, self.kernel_size), self.sigma
        )
        corrected = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)

        logger.info(
            "Sharpening applied",
            blur_score=blur_score,
            severity=severity.value,
            amount=amount,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "blur_score": blur_score,
                "severity": severity.value,
                "amount": amount,
                "kernel_size": self.kernel_size,
                "sigma": self.sigma,
            },
        )


# Convenience functions
def correct_skew(
    image: np.ndarray, angle: float, confidence: float = 1.0
) -> CorrectionResult:
    """
    Convenience function for deskew correction.

    Args:
        image: Input image (BGR format)
        angle: Detected skew angle in degrees
        confidence: Detection confidence (0.0-1.0)

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("skewed.jpg")
        >>> result = correct_skew(img, angle=3.5, confidence=0.85)
        >>> if result.applied:
        ...     cv2.imwrite("corrected.jpg", result.corrected_image)
    """
    corrector = DeskewCorrector()
    return corrector.correct(image, angle, confidence)


def enhance_contrast(
    image: np.ndarray, score: float, severity: Severity
) -> CorrectionResult:
    """
    Convenience function for contrast enhancement.

    Args:
        image: Input image (BGR format)
        score: Detected contrast score (0.0-1.0)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("low_contrast.jpg")
        >>> result = enhance_contrast(img, score=0.25, severity=Severity.HIGH)
        >>> if result.applied:
        ...     cv2.imwrite("enhanced.jpg", result.corrected_image)
    """
    enhancer = ContrastEnhancer()
    return enhancer.correct(image, score, severity)


def sharpen_image(
    image: np.ndarray, blur_score: float, severity: Severity
) -> CorrectionResult:
    """
    Convenience function for sharpening.

    Args:
        image: Input image (BGR format)
        blur_score: Detected blur score (Laplacian variance)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("blurred.jpg")
        >>> result = sharpen_image(img, blur_score=80.0, severity=Severity.HIGH)
        >>> if result.applied:
        ...     cv2.imwrite("sharpened.jpg", result.corrected_image)
    """
    sharpener = Sharpener()
    return sharpener.correct(image, blur_score, severity)
