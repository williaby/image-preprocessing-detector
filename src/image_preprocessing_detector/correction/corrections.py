"""Image correction operations with guardrails.

Implements corrections for detected image quality issues:
- Deskew (rotation correction)
- Contrast enhancement (CLAHE)
- Sharpening (unsharp mask)
- Denoising (NLMeans)
- Binarization correction (adaptive thresholding)
- Illumination normalization (morphological)
- Bleed-through suppression (cross-channel filtering)
- Orientation correction (90°, 180°, 270° rotation - Phase 8)

All correctors include guardrails to prevent quality degradation.
"""

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import Severity
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Error message constant to avoid duplication
_INVALID_IMAGE_ERROR = "Invalid or empty image provided"


@dataclass
class CorrectionResult:
    """Result of a correction operation.

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
    """Corrects image skew using rotation.

    Includes guardrails to prevent over-correction and quality degradation.
    """

    def __init__(
        self,
        min_angle: float = 0.5,
        max_angle: float = 45.0,
        border_value: int = 255,
    ) -> None:
        """Initialize deskew corrector.

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
        """Apply deskew correction.

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
            raise ValueError(_INVALID_IMAGE_ERROR)

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
        M = cv2.getRotationMatrix2D(center, angle, 1.0)  # noqa: N806  # fmt: skip

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
    """Enhances image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Includes guardrails to prevent over-enhancement.
    """

    def __init__(
        self,
        clip_limit: float = 2.0,
        tile_grid_size: tuple[int, int] = (8, 8),
        min_score: float = 0.4,
    ) -> None:
        """Initialize contrast enhancer.

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
        """Apply contrast enhancement.

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
            raise ValueError(_INVALID_IMAGE_ERROR)

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
    """Sharpens blurred images using unsharp mask.

    Includes guardrails to prevent over-sharpening and noise amplification.
    """

    def __init__(
        self,
        amount: float = 1.0,
        kernel_size: int = 5,
        sigma: float = 1.0,
        min_blur_score: float = 200.0,
    ) -> None:
        """Initialize sharpener.

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
        """Apply sharpening correction.

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
            raise ValueError(_INVALID_IMAGE_ERROR)

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


class Denoiser:
    """Reduces image noise using Non-Local Means (NLMeans) denoising.

    NLMeans is effective for Gaussian noise while preserving edges.
    Includes guardrails to prevent over-smoothing.
    """

    def __init__(
        self,
        h_luminance: float = 10.0,
        h_color: float = 10.0,
        template_window_size: int = 7,
        search_window_size: int = 21,
        min_noise_score: float = 0.7,
    ) -> None:
        """Initialize denoiser.

        Args:
            h_luminance: Filter strength for luminance (higher = more smoothing)
            h_color: Filter strength for color components
            template_window_size: Size of template patch (odd number)
            search_window_size: Size of search window (odd number)
            min_noise_score: Minimum noise score to skip denoising (0-1, higher = cleaner)
        """
        self.h_luminance = h_luminance
        self.h_color = h_color
        self.template_window_size = template_window_size
        self.search_window_size = search_window_size
        self.min_noise_score = min_noise_score

        logger.info(
            "Denoiser initialized",
            h_luminance=h_luminance,
            h_color=h_color,
            template_window_size=template_window_size,
        )

    def correct(
        self, image: np.ndarray, noise_score: float, severity: Severity
    ) -> CorrectionResult:
        """Apply noise reduction.

        Args:
            image: Input image (BGR format)
            noise_score: Detected noise score (0-1, 0=noisy, 1=clean)
            severity: Issue severity

        Returns:
            CorrectionResult with denoised image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        # Guardrail: Skip if image is already clean
        if noise_score >= self.min_noise_score:
            logger.debug(
                "Skipping denoising (image already clean)",
                noise_score=noise_score,
                min_noise_score=self.min_noise_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"noise_score": noise_score},
                skipped_reason=f"Noise score {noise_score:.2f} above threshold {self.min_noise_score}",
            )

        # Adjust filter strength based on severity
        h_lum = self.h_luminance
        h_col = self.h_color
        if severity == Severity.CRITICAL:
            h_lum *= 1.5
            h_col *= 1.5
        elif severity == Severity.LOW:
            h_lum *= 0.5
            h_col *= 0.5

        # Guardrail: Cap filter strength to prevent over-smoothing
        h_lum = min(h_lum, 20.0)
        h_col = min(h_col, 20.0)

        # Apply NLMeans denoising
        corrected = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h_lum,
            h_col,
            self.template_window_size,
            self.search_window_size,
        )

        logger.info(
            "Denoising applied",
            noise_score=noise_score,
            severity=severity.value,
            h_luminance=h_lum,
            h_color=h_col,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "noise_score": noise_score,
                "severity": severity.value,
                "h_luminance": h_lum,
                "h_color": h_col,
                "template_window_size": self.template_window_size,
                "search_window_size": self.search_window_size,
            },
        )


class BinarizationCorrector:
    """Corrects poor binarization quality using adaptive thresholding.

    Useful for scanned documents with uneven lighting or faded text.
    Includes guardrails to prevent destroying color information.
    """

    def __init__(
        self,
        block_size: int = 11,
        c_offset: int = 2,
        min_binarization_score: float = 0.7,
        apply_morphology: bool = True,
    ) -> None:
        """Initialize binarization corrector.

        Args:
            block_size: Size of adaptive threshold neighborhood (odd number)
            c_offset: Constant subtracted from mean/weighted mean
            min_binarization_score: Minimum score to skip correction (0-1)
            apply_morphology: Apply morphological opening to clean up
        """
        self.block_size = block_size if block_size % 2 == 1 else block_size + 1
        self.c_offset = c_offset
        self.min_binarization_score = min_binarization_score
        self.apply_morphology = apply_morphology

        logger.info(
            "Binarization corrector initialized",
            block_size=self.block_size,
            c_offset=c_offset,
            apply_morphology=apply_morphology,
        )

    def correct(
        self, image: np.ndarray, binarization_score: float, severity: Severity
    ) -> CorrectionResult:
        """Apply binarization correction.

        Args:
            image: Input image (BGR format)
            binarization_score: Detected binarization quality (0-1, 0=poor, 1=good)
            severity: Issue severity

        Returns:
            CorrectionResult with corrected image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        # Guardrail: Skip if binarization quality is already good
        if binarization_score >= self.min_binarization_score:
            logger.debug(
                "Skipping binarization correction (quality already good)",
                binarization_score=binarization_score,
                min_score=self.min_binarization_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"binarization_score": binarization_score},
                skipped_reason=f"Binarization score {binarization_score:.2f} above threshold {self.min_binarization_score}",
            )

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Adjust parameters based on severity
        block_size = self.block_size
        c_offset = self.c_offset
        if severity == Severity.CRITICAL:
            block_size = min(block_size + 4, 31)
            c_offset = max(c_offset - 1, 0)
        elif severity == Severity.LOW:
            c_offset = c_offset + 1

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c_offset,
        )

        # Optional morphological cleanup
        if self.apply_morphology:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Convert back to BGR for consistency
        corrected = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        logger.info(
            "Binarization correction applied",
            binarization_score=binarization_score,
            severity=severity.value,
            block_size=block_size,
            c_offset=c_offset,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "binarization_score": binarization_score,
                "severity": severity.value,
                "block_size": block_size,
                "c_offset": c_offset,
                "apply_morphology": self.apply_morphology,
            },
        )


class IlluminationNormalizer:
    """Normalizes uneven illumination using morphological operations.

    Effective for documents with shadows, uneven lighting, or scanner artifacts.
    Includes guardrails to preserve document content.
    """

    def __init__(
        self,
        kernel_size: int = 51,
        min_illumination_score: float = 0.7,
        blend_alpha: float = 0.8,
    ) -> None:
        """Initialize illumination normalizer.

        Args:
            kernel_size: Size of morphological kernel (odd number, larger = more smoothing)
            min_illumination_score: Minimum score to skip normalization (0-1)
            blend_alpha: Blending factor with original (0-1, higher = more correction)
        """
        self.kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        self.min_illumination_score = min_illumination_score
        self.blend_alpha = blend_alpha

        logger.info(
            "Illumination normalizer initialized",
            kernel_size=self.kernel_size,
            blend_alpha=blend_alpha,
        )

    def correct(
        self, image: np.ndarray, illumination_score: float, severity: Severity
    ) -> CorrectionResult:
        """Apply illumination normalization.

        Args:
            image: Input image (BGR format)
            illumination_score: Detected illumination uniformity (0-1, 0=uneven, 1=uniform)
            severity: Issue severity

        Returns:
            CorrectionResult with normalized image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        # Guardrail: Skip if illumination is already uniform
        if illumination_score >= self.min_illumination_score:
            logger.debug(
                "Skipping illumination normalization (already uniform)",
                illumination_score=illumination_score,
                min_score=self.min_illumination_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"illumination_score": illumination_score},
                skipped_reason=f"Illumination score {illumination_score:.2f} above threshold {self.min_illumination_score}",
            )

        # Adjust parameters based on severity
        kernel_size = self.kernel_size
        alpha = self.blend_alpha
        if severity == Severity.CRITICAL:
            kernel_size = min(kernel_size + 20, 101)
            alpha = min(alpha + 0.1, 1.0)
        elif severity == Severity.LOW:
            kernel_size = max(kernel_size - 10, 21)
            alpha = max(alpha - 0.1, 0.5)

        # Convert to grayscale for background estimation
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Estimate background using morphological closing
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        # Normalize by dividing by background
        # Add small epsilon to prevent division by zero
        normalized = np.clip(
            gray.astype(np.float32) / (background.astype(np.float32) + 1e-6) * 255,
            0,
            255,
        ).astype(np.uint8)

        # Blend with original to preserve some texture
        blended_gray = cv2.addWeighted(normalized, alpha, gray, 1 - alpha, 0)

        # Convert back to BGR
        if len(image.shape) == 3:
            # Apply normalization to L channel in LAB space for color images
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)

            # Normalize L channel
            l_bg = cv2.morphologyEx(l_channel, cv2.MORPH_CLOSE, kernel)
            l_normalized = np.clip(
                l_channel.astype(np.float32) / (l_bg.astype(np.float32) + 1e-6) * 128,
                0,
                255,
            ).astype(np.uint8)
            l_blended = cv2.addWeighted(l_normalized, alpha, l_channel, 1 - alpha, 0)

            # Merge and convert back
            corrected_lab = cv2.merge([l_blended, a, b])
            corrected = cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)
        else:
            corrected = cv2.cvtColor(blended_gray, cv2.COLOR_GRAY2BGR)

        logger.info(
            "Illumination normalization applied",
            illumination_score=illumination_score,
            severity=severity.value,
            kernel_size=kernel_size,
            blend_alpha=alpha,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "illumination_score": illumination_score,
                "severity": severity.value,
                "kernel_size": kernel_size,
                "blend_alpha": alpha,
            },
        )


class BleedThroughSuppressor:
    """Suppresses bleed-through from reverse side of scanned documents.

    Uses cross-channel analysis and morphological filtering to remove
    faint text showing through from the other side.
    Includes guardrails to prevent removing legitimate content.
    """

    def __init__(
        self,
        kernel_size: int = 3,
        min_bleed_score: float = 0.7,
        intensity_threshold: int = 200,
        blend_alpha: float = 0.7,
    ) -> None:
        """Initialize bleed-through suppressor.

        Args:
            kernel_size: Size of morphological kernel
            min_bleed_score: Minimum score to skip suppression (0-1, 0=severe bleed, 1=none)
            intensity_threshold: Threshold for detecting bleed-through regions
            blend_alpha: Blending factor for correction
        """
        self.kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        self.min_bleed_score = min_bleed_score
        self.intensity_threshold = intensity_threshold
        self.blend_alpha = blend_alpha

        logger.info(
            "Bleed-through suppressor initialized",
            kernel_size=self.kernel_size,
            intensity_threshold=intensity_threshold,
        )

    def correct(
        self, image: np.ndarray, bleed_score: float, severity: Severity
    ) -> CorrectionResult:
        """Apply bleed-through suppression.

        Args:
            image: Input image (BGR format)
            bleed_score: Detected bleed-through score (0-1, 0=severe, 1=none)
            severity: Issue severity

        Returns:
            CorrectionResult with suppressed image and metadata

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        # Guardrail: Skip if no significant bleed-through
        if bleed_score >= self.min_bleed_score:
            logger.debug(
                "Skipping bleed-through suppression (no significant bleed-through)",
                bleed_score=bleed_score,
                min_score=self.min_bleed_score,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"bleed_score": bleed_score},
                skipped_reason=f"Bleed-through score {bleed_score:.2f} above threshold {self.min_bleed_score}",
            )

        # Adjust parameters based on severity
        threshold = self.intensity_threshold
        alpha = self.blend_alpha
        if severity == Severity.CRITICAL:
            threshold = max(threshold - 20, 150)
            alpha = min(alpha + 0.2, 1.0)
        elif severity == Severity.LOW:
            threshold = min(threshold + 20, 230)
            alpha = max(alpha - 0.1, 0.5)

        # Convert to grayscale for processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Detect bleed-through regions (faint, low-contrast marks)
        # Use morphological top-hat to find light features on background
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (self.kernel_size, self.kernel_size)
        )

        # Black top-hat detects dark regions on light background
        black_hat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)

        # Create mask for bleed-through regions
        # Bleed-through tends to be faint, so we look for low-intensity features
        _, bleed_mask = cv2.threshold(black_hat, 20, 255, cv2.THRESH_BINARY)

        # Dilate mask slightly to cover bleed-through edges
        bleed_mask = cv2.dilate(bleed_mask, kernel, iterations=1)

        # Suppress bleed-through by filling with local background
        # Use morphological closing to estimate local background
        closing_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, closing_kernel)

        # Replace bleed-through regions with background
        suppressed_gray = gray.copy()
        suppressed_gray[bleed_mask > 0] = background[bleed_mask > 0]

        # Blend with original to prevent artifacts
        blended = cv2.addWeighted(suppressed_gray, alpha, gray, 1 - alpha, 0)

        # Convert back to BGR
        if len(image.shape) == 3:
            # Apply suppression to L channel
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)

            l_background = cv2.morphologyEx(l_channel, cv2.MORPH_CLOSE, closing_kernel)
            l_suppressed = l_channel.copy()
            l_suppressed[bleed_mask > 0] = l_background[bleed_mask > 0]
            l_blended = cv2.addWeighted(l_suppressed, alpha, l_channel, 1 - alpha, 0)

            corrected_lab = cv2.merge([l_blended, a, b])
            corrected = cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)
        else:
            corrected = cv2.cvtColor(blended, cv2.COLOR_GRAY2BGR)

        logger.info(
            "Bleed-through suppression applied",
            bleed_score=bleed_score,
            severity=severity.value,
            intensity_threshold=threshold,
            blend_alpha=alpha,
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "bleed_score": bleed_score,
                "severity": severity.value,
                "kernel_size": self.kernel_size,
                "intensity_threshold": threshold,
                "blend_alpha": alpha,
            },
        )


class OrientationCorrector:
    """Corrects document orientation (90°, 180°, 270° rotation).

    Phase 8 implementation for handling rotated scans/photos.
    Includes guardrails based on confidence thresholds.
    """

    def __init__(
        self,
        min_confidence: float = 0.7,
        auto_correct_threshold: float = 0.85,
    ) -> None:
        """Initialize orientation corrector.

        Args:
            min_confidence: Minimum confidence to apply correction
            auto_correct_threshold: Confidence threshold for auto-correction
        """
        self.min_confidence = min_confidence
        self.auto_correct_threshold = auto_correct_threshold

        logger.info(
            "Orientation corrector initialized",
            min_confidence=min_confidence,
            auto_correct_threshold=auto_correct_threshold,
        )

    def correct(
        self,
        image: np.ndarray,
        angle: int,
        confidence: float,
        force: bool = False,
    ) -> CorrectionResult:
        """Apply orientation correction.

        Args:
            image: Input image (BGR format)
            angle: Detected orientation angle (0, 90, 180, 270)
            confidence: Detection confidence (0.0-1.0)
            force: Force correction even if confidence is low

        Returns:
            CorrectionResult with corrected image and metadata

        Raises:
            ValueError: If image is invalid, empty, or angle is invalid
        """
        if image is None or image.size == 0:
            raise ValueError(_INVALID_IMAGE_ERROR)

        if angle not in (0, 90, 180, 270):
            raise ValueError(
                f"Invalid orientation angle: {angle}. Must be 0, 90, 180, or 270."
            )

        # No correction needed for upright images
        if angle == 0:
            logger.debug("Skipping orientation correction (already upright)")
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"angle": angle, "confidence": confidence},
                skipped_reason="Image already upright (0°)",
            )

        # Guardrail: Check confidence threshold (unless forced)
        if not force and confidence < self.min_confidence:
            logger.warning(
                "Skipping orientation correction (low confidence)",
                angle=angle,
                confidence=confidence,
                min_confidence=self.min_confidence,
            )
            return CorrectionResult(
                corrected_image=image.copy(),
                applied=False,
                parameters={"angle": angle, "confidence": confidence},
                skipped_reason=f"Confidence {confidence:.2f} below threshold {self.min_confidence}",
            )

        # Apply rotation (counter-clockwise to correct)
        rotation_map = {
            90: cv2.ROTATE_90_COUNTERCLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_CLOCKWISE,
        }

        corrected = cv2.rotate(image, rotation_map[angle])

        original_h, original_w = image.shape[:2]
        new_h, new_w = corrected.shape[:2]

        logger.info(
            "Orientation correction applied",
            detected_angle=angle,
            correction_applied=f"-{angle}°",
            confidence=confidence,
            original_size=(original_w, original_h),
            new_size=(new_w, new_h),
        )

        return CorrectionResult(
            corrected_image=corrected,
            applied=True,
            parameters={
                "detected_angle": angle,
                "correction_applied": -angle,
                "confidence": confidence,
                "original_size": (original_w, original_h),
                "new_size": (new_w, new_h),
            },
        )


# Convenience functions
def correct_skew(
    image: np.ndarray, angle: float, confidence: float = 1.0
) -> CorrectionResult:
    """Convenience function for deskew correction.

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
    """Convenience function for contrast enhancement.

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
    """Convenience function for sharpening.

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


def denoise_image(
    image: np.ndarray, noise_score: float, severity: Severity
) -> CorrectionResult:
    """Convenience function for denoising.

    Args:
        image: Input image (BGR format)
        noise_score: Detected noise score (0-1, 0=noisy, 1=clean)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("noisy.jpg")
        >>> result = denoise_image(img, noise_score=0.3, severity=Severity.HIGH)
        >>> if result.applied:
        ...     cv2.imwrite("denoised.jpg", result.corrected_image)
    """
    denoiser = Denoiser()
    return denoiser.correct(image, noise_score, severity)


def correct_binarization(
    image: np.ndarray, binarization_score: float, severity: Severity
) -> CorrectionResult:
    """Convenience function for binarization correction.

    Args:
        image: Input image (BGR format)
        binarization_score: Detected binarization quality (0-1)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("faded_document.jpg")
        >>> result = correct_binarization(
        ...     img, binarization_score=0.3, severity=Severity.HIGH
        ... )
        >>> if result.applied:
        ...     cv2.imwrite("binarized.jpg", result.corrected_image)
    """
    corrector = BinarizationCorrector()
    return corrector.correct(image, binarization_score, severity)


def normalize_illumination(
    image: np.ndarray, illumination_score: float, severity: Severity
) -> CorrectionResult:
    """Convenience function for illumination normalization.

    Args:
        image: Input image (BGR format)
        illumination_score: Detected illumination uniformity (0-1)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("uneven_lighting.jpg")
        >>> result = normalize_illumination(
        ...     img, illumination_score=0.4, severity=Severity.MEDIUM
        ... )
        >>> if result.applied:
        ...     cv2.imwrite("normalized.jpg", result.corrected_image)
    """
    normalizer = IlluminationNormalizer()
    return normalizer.correct(image, illumination_score, severity)


def suppress_bleed_through(
    image: np.ndarray, bleed_score: float, severity: Severity
) -> CorrectionResult:
    """Convenience function for bleed-through suppression.

    Args:
        image: Input image (BGR format)
        bleed_score: Detected bleed-through score (0-1, 0=severe, 1=none)
        severity: Issue severity

    Returns:
        CorrectionResult

    Example:
        >>> img = cv2.imread("bleed_through_scan.jpg")
        >>> result = suppress_bleed_through(
        ...     img, bleed_score=0.3, severity=Severity.MEDIUM
        ... )
        >>> if result.applied:
        ...     cv2.imwrite("cleaned.jpg", result.corrected_image)
    """
    suppressor = BleedThroughSuppressor()
    return suppressor.correct(image, bleed_score, severity)


def correct_orientation(
    image: np.ndarray,
    angle: int,
    confidence: float,
    force: bool = False,
) -> CorrectionResult:
    """Convenience function for orientation correction.

    Corrects document orientation when pages are rotated 90°, 180°, or 270°.
    Common in scanned/photographed documents.

    Args:
        image: Input image (BGR format)
        angle: Detected orientation angle (0, 90, 180, 270 degrees)
        confidence: Detection confidence (0.0-1.0)
        force: Force correction even if confidence is low

    Returns:
        CorrectionResult with corrected image and metadata

    Example:
        >>> img = cv2.imread("rotated_scan.jpg")
        >>> result = correct_orientation(img, angle=90, confidence=0.92)
        >>> if result.applied:
        ...     cv2.imwrite("corrected.jpg", result.corrected_image)
    """
    corrector = OrientationCorrector()
    return corrector.correct(image, angle, confidence, force)
