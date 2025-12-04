# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#

"""PDF pre-flight analysis for intelligent routing and optimization."""

import logging
import tempfile
from pathlib import Path
from typing import Any

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.ingestion.pdf_resolution import PDFResolutionAnalyzer
from image_preprocessing_detector.ingestion.pdf_upscaler import (
    PDFUpscaler,
    UpscaleAlgorithm,
)

logger = logging.getLogger(__name__)


class PDFPreflightResult:
    """Results from PDF pre-flight analysis."""

    def __init__(
        self,
        needs_upscaling: bool,
        resolution_analysis: dict[str, Any],
        upscaled_path: str | None = None,
        upscaling_result: dict[str, Any] | None = None,
        processing_time: float = 0.0,
    ) -> None:
        """Initialize preflight result.

        Args:
            needs_upscaling: Whether upscaling is needed
            resolution_analysis: Resolution analysis results
            upscaled_path: Path to upscaled PDF (if created)
            upscaling_result: Upscaling results (if performed)
            processing_time: Total processing time
        """
        self.needs_upscaling = needs_upscaling
        self.resolution_analysis = resolution_analysis
        self.upscaled_path = upscaled_path
        self.upscaling_result = upscaling_result or {}
        self.processing_time = processing_time

    @property
    def should_use_upscaled(self) -> bool:
        """Determine if upscaled version should be used.

        Returns:
            True if upscaling succeeded and should be used
        """
        return self.upscaled_path is not None and self.upscaling_result.get(
            "success", False
        )

    @property
    def recommended_path(self) -> str | None:
        """Get recommended PDF path (upscaled or original).

        Returns:
            Path to recommended PDF for processing
        """
        return self.upscaled_path if self.should_use_upscaled else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "needs_upscaling": self.needs_upscaling,
            "resolution_analysis": self.resolution_analysis,
            "upscaled_path": self.upscaled_path,
            "upscaling_result": self.upscaling_result,
            "processing_time": self.processing_time,
            "should_use_upscaled": self.should_use_upscaled,
            "recommended_path": self.recommended_path,
        }


class PDFDocumentAnalyzer:
    """Analyzes PDFs for resolution and determines if pre-processing is needed.

    This analyzer performs pre-flight checks on PDFs to determine:
    1. If resolution is sufficient for OCR
    2. If upscaling would improve quality
    3. Which version of the PDF should be used for processing
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize PDF document analyzer.

        Args:
            settings: Optional settings instance
        """
        self.settings = settings or Settings()

        # Initialize components
        self.resolution_analyzer = PDFResolutionAnalyzer(
            min_dpi_threshold=self.settings.pdf_min_dpi
        )

        # Map algorithm string to enum
        algorithm_map = {
            "lanczos": UpscaleAlgorithm.LANCZOS,
            "bicubic": UpscaleAlgorithm.BICUBIC,
            "inter_cubic": UpscaleAlgorithm.INTER_CUBIC,
            "inter_linear": UpscaleAlgorithm.INTER_LINEAR,
            "inter_area": UpscaleAlgorithm.INTER_AREA,
        }
        algorithm = algorithm_map.get(
            self.settings.pdf_upscale_algorithm.lower(),
            UpscaleAlgorithm.LANCZOS,
        )

        self.upscaler = PDFUpscaler(
            target_dpi=self.settings.pdf_target_dpi,
            algorithm=algorithm,
            preserve_original=self.settings.pdf_preserve_original_on_error,
        )

    def analyze(
        self,
        pdf_path: str | Path,
        perform_upscaling: bool | None = None,
    ) -> PDFPreflightResult:
        """Analyze PDF and optionally upscale if needed.

        # CRITICAL: File Operations: May create temporary files that need cleanup
        # #VERIFY: Implement proper cleanup and error handling

        Args:
            pdf_path: Path to PDF file
            perform_upscaling: Override upscaling decision (None = use config)

        Returns:
            PDFPreflightResult with analysis and upscaling results

        Raises:
            FileNotFoundError: If PDF doesn't exist
        """
        import time

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            msg = f"PDF file not found: {pdf_path}"
            raise FileNotFoundError(msg)

        start_time = time.time()

        logger.info(f"Starting PDF pre-flight analysis: {pdf_path.name}")

        # Perform resolution analysis
        # CRITICAL: Analysis Time: Must complete quickly for pre-flight (<100ms target)
        # #VERIFY: Monitor analysis time and optimize if needed
        try:
            resolution_analysis = self.resolution_analyzer.analyze_pdf_resolution(
                pdf_path
            )
        except Exception as e:
            logger.exception("Resolution analysis failed")
            # Return result indicating analysis failure
            return PDFPreflightResult(
                needs_upscaling=False,
                resolution_analysis={"error": str(e)},
                processing_time=time.time() - start_time,
            )

        needs_upscaling = resolution_analysis.get("needs_upscaling", False)

        # Determine if we should perform upscaling
        should_upscale = (
            perform_upscaling
            if perform_upscaling is not None
            else (self.settings.enable_pdf_upscaling and needs_upscaling)
        )

        upscaled_path = None
        upscaling_result = None

        if should_upscale:
            logger.info(
                f"PDF resolution below {self.settings.pdf_min_dpi} DPI "
                f"(min: {resolution_analysis.get('min_dpi')}, avg: {resolution_analysis.get('avg_dpi')})"
            )

            try:
                # Create temporary file for upscaled version
                # ASSUME: Temporary Files: System temp directory has sufficient space
                # #VERIFY: Check disk space before upscaling large files
                temp_dir = Path(tempfile.gettempdir()) / "data_ingestor_upscaled"
                temp_dir.mkdir(parents=True, exist_ok=True)

                upscaled_path = (
                    temp_dir / f"{pdf_path.stem}_upscaled_{int(time.time())}.pdf"
                )

                # Perform upscaling
                upscaling_result = self.upscaler.upscale_pdf(
                    input_path=pdf_path,
                    output_path=upscaled_path,
                )

                if not upscaling_result.get("success", False):
                    logger.warning(
                        f"Upscaling failed: {upscaling_result.get('error_message')}, "
                        "will use original PDF"
                    )
                    upscaled_path = None

            except Exception as e:
                logger.exception("Upscaling error, will use original PDF")
                upscaling_result = {"success": False, "error_message": str(e)}
                upscaled_path = None

        processing_time = time.time() - start_time

        result = PDFPreflightResult(
            needs_upscaling=needs_upscaling,
            resolution_analysis=resolution_analysis,
            upscaled_path=str(upscaled_path) if upscaled_path else None,
            upscaling_result=upscaling_result,
            processing_time=processing_time,
        )

        logger.info(
            f"PDF pre-flight analysis complete: {pdf_path.name} "
            f"(analysis_time: {processing_time:.2f}s, "
            f"upscaling_performed: {should_upscale}, "
            f"recommended: {'upscaled' if result.should_use_upscaled else 'original'})"
        )

        return result

    def quick_check(self, pdf_path: str | Path) -> bool:
        """Quick resolution check without upscaling.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if upscaling is recommended
        """
        try:
            resolution_analysis = self.resolution_analyzer.analyze_pdf_resolution(
                pdf_path
            )
            return bool(resolution_analysis.get("needs_upscaling", False))
        except (OSError, RuntimeError, ValueError):
            # OSError: file access errors, RuntimeError: PDF parsing errors
            logger.exception("Quick resolution check failed for %s", pdf_path)
            return False
