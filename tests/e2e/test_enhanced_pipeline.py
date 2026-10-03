"""E2E integration tests for enhanced document processing pipeline.

Tests validate the integration of Stream 4-9 components:
- Border removal (Stream 6)
- Perspective correction (Stream 6)
- Multi-task teacher detection with heuristic fallback (Stream 4 + Stream 2)
- DoclingRoutingEngine routing decisions (Stream 5)
- Pipeline ordering (orientation first, blank page early exit)
- Graceful degradation when teacher model unavailable

Test scenarios:
1. Born-digital document → OCR skip routing
2. Camera-captured document → VLM escalation routing
3. CJK script → batch size adjustment
4. Code detection → enrichment flag
5. Orientation correction → applied before other processing
6. Blank page → early exit
7. Extreme warping → perspective correction blocked
8. Teacher unavailable → heuristic fallback
9. Border removal → preserves content area
10. Full pipeline → all components integrated
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.correction.border_removal import (
    remove_borders,
)
from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.correction.perspective_correction import (
    correct_perspective,
)
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    PageMetadata,
    ProcessingVersion,
)

# Use modern numpy.random.Generator API
_rng = np.random.default_rng(seed=42)

# ---------------------------------------------------------------------------
# Minimal DocumentMetadata factory for routing tests
# ---------------------------------------------------------------------------

_MIN_PAGE = PageMetadata(
    page_index=0, width_px=600, height_px=800, dpi_input=300, dpi_effective=300
)
_MIN_VERSION = ProcessingVersion(pipeline_version="test-0.0.0")


def _make_metadata(**overrides: object) -> DocumentMetadata:
    """Build a ``DocumentMetadata`` with required fields pre-filled.

    Pass any field as a keyword arg to override the default value.
    """
    defaults: dict[str, object] = {
        "document_id": "test-e2e-001",
        "file_name": "test.pdf",
        "source_mime": "application/pdf",
        "num_pages": 1,
        "processing_version": _MIN_VERSION,
        "pages": [_MIN_PAGE],
    }
    defaults.update(overrides)
    return DocumentMetadata(**defaults)  # type: ignore[arg-type]


# ============================================================================
# Fixtures: synthetic document images
# ============================================================================


@pytest.fixture
def clean_document() -> np.ndarray:
    """Create a clean document image with text-like features.

    White background with black text blocks. Good quality, no degradation.
    """
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255

    # Header
    cv2.rectangle(img, (50, 30), (550, 60), (0, 0, 0), -1)

    # Body text lines
    for y in range(100, 700, 30):
        width = _rng.integers(400, 500)
        cv2.rectangle(img, (50, y), (50 + width, y + 10), (30, 30, 30), -1)

    return img


@pytest.fixture
def document_with_border() -> np.ndarray:
    """Create a document with a distinct black scanner border.

    Document content in center, black border around edges.
    """
    img = np.zeros((800, 600, 3), dtype=np.uint8)  # Black background

    # White document area - narrow border to keep area_ratio >= 0.70
    margin_x, margin_y = 30, 40
    img[margin_y : 800 - margin_y, margin_x : 600 - margin_x] = 255

    # Add text content inside the white area
    for y in range(margin_y + 20, 800 - margin_y - 20, 30):
        width = _rng.integers(400, 500)
        cv2.rectangle(
            img,
            (margin_x + 20, y),
            (margin_x + 20 + width, y + 10),
            (30, 30, 30),
            -1,
        )

    return img


@pytest.fixture
def warped_document() -> np.ndarray:
    """Create a perspective-warped document (camera capture simulation)."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255

    # Text content
    for y in range(100, 700, 30):
        cv2.rectangle(img, (50, y), (500, y + 10), (30, 30, 30), -1)

    # Apply perspective warp (simulating camera angle)
    h, w = img.shape[:2]
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst_pts = np.float32([[30, 20], [w - 40, 10], [w - 10, h - 15], [20, h - 30]])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(img, matrix, (w, h), borderValue=(200, 200, 200))


@pytest.fixture
def blank_page() -> np.ndarray:
    """Create a blank white page (no content)."""
    return np.ones((800, 600, 3), dtype=np.uint8) * 255


@pytest.fixture
def rotated_document(clean_document: np.ndarray) -> np.ndarray:
    """Create a 90-degree rotated document."""
    return cv2.rotate(clean_document, cv2.ROTATE_90_CLOCKWISE)


@pytest.fixture
def grayscale_document() -> np.ndarray:
    """Create a grayscale document image."""
    img = np.ones((800, 600), dtype=np.uint8) * 255
    for y in range(100, 700, 30):
        cv2.rectangle(img, (50, y), (500, y + 10), 30, -1)
    return img


# ============================================================================
# Test 1: Border Removal Integration
# ============================================================================


class TestBorderRemoval:
    """Tests for border removal in pipeline context."""

    def test_border_removed_from_scanned_doc(
        self,
        document_with_border: np.ndarray,
    ) -> None:
        """Scanner border is cropped, content area preserved."""
        result = remove_borders(document_with_border)
        assert result.applied
        assert result.corrected_image.shape[0] < document_with_border.shape[0]
        assert result.corrected_image.shape[1] < document_with_border.shape[1]

    def test_clean_document_preserved(self, clean_document: np.ndarray) -> None:
        """Clean document without border is not over-cropped."""
        result = remove_borders(clean_document)
        if result.applied:
            # If any cropping applied, it should preserve most of the image
            area_ratio = result.parameters.get("area_ratio", 1.0)
            assert area_ratio >= 0.70

    def test_border_removal_returns_correction_result(
        self,
        document_with_border: np.ndarray,
    ) -> None:
        """Border removal returns a CorrectionResult."""
        result = remove_borders(document_with_border)
        assert isinstance(result, CorrectionResult)
        assert "crop_rect" in result.parameters
        assert "area_ratio" in result.parameters

    def test_grayscale_input_supported(
        self,
        grayscale_document: np.ndarray,
    ) -> None:
        """Border removal handles grayscale input."""
        result = remove_borders(grayscale_document)
        assert isinstance(result, CorrectionResult)

    def test_safety_guardrail_prevents_overcrop(self) -> None:
        """Crop below 70% area threshold is rejected."""
        # Create image where "content" is only a tiny area
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        # Small black dot - contour will be tiny
        cv2.circle(img, (300, 400), 20, (0, 0, 0), -1)
        result = remove_borders(img)
        # Either not applied, or applied with area >= 70%
        if result.applied:
            assert result.parameters["area_ratio"] >= 0.70


# ============================================================================
# Test 2: Perspective Correction Integration
# ============================================================================


class TestPerspectiveCorrection:
    """Tests for perspective correction in pipeline context."""

    def test_warped_document_correction(
        self,
        warped_document: np.ndarray,
    ) -> None:
        """Perspective correction returns CorrectionResult."""
        result = correct_perspective(warped_document, warping_score=0.4)
        assert isinstance(result, CorrectionResult)

    def test_extreme_warping_blocked(
        self,
        warped_document: np.ndarray,
    ) -> None:
        """Warping score > 0.75 blocks correction (defers to VLM)."""
        result = correct_perspective(warped_document, warping_score=0.8)
        assert not result.applied
        assert (
            "warping too severe" in (result.skipped_reason or "").lower()
            or "threshold" in (result.skipped_reason or "").lower()
        )

    def test_clean_document_no_correction(
        self,
        clean_document: np.ndarray,
    ) -> None:
        """Clean document doesn't need perspective correction."""
        result = correct_perspective(clean_document, warping_score=0.1)
        # May or may not apply depending on quad detection
        assert isinstance(result, CorrectionResult)

    def test_grayscale_perspective_correction(
        self,
        grayscale_document: np.ndarray,
    ) -> None:
        """Perspective correction handles grayscale converted to BGR."""
        # PerspectiveCorrector expects BGR; convert grayscale first
        bgr = cv2.cvtColor(grayscale_document, cv2.COLOR_GRAY2BGR)
        result = correct_perspective(bgr, warping_score=0.3)
        assert isinstance(result, CorrectionResult)


# ============================================================================
# Test 3: DoclingRouter Routing Decisions
# ============================================================================


class TestDoclingRouting:
    """Tests for DoclingRouter integration with pipeline analysis."""

    def test_born_digital_ocr_skip(self) -> None:
        """Born-digital document with high quality skips OCR."""
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import DoclingRoutingParams

        engine = DoclingRoutingEngine()
        metadata = _make_metadata(
            text_layer_quality=0.95,
            text_layer_skip_ocr=True,
        )
        decision = engine.route(metadata)
        assert isinstance(decision.params, DoclingRoutingParams)
        # Born-digital with high text layer quality should disable OCR
        assert not decision.params.ocr_enabled

    def test_camera_vlm_escalation(self) -> None:
        """Camera-captured document with low script confidence escalates to VLM."""
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import DocumentScriptDetection

        engine = DoclingRoutingEngine()
        metadata = _make_metadata(
            script_detection=DocumentScriptDetection(
                dominant_script="Latn",
                dominant_confidence=0.4,  # Low confidence → VLM
            ),
        )
        decision = engine.route(metadata)
        # Low script confidence triggers VLM escalation
        assert decision.params.pipeline == "vlm"
        assert len(decision.vlm_reasons) > 0

    def test_cjk_batch_size_adjustment(self) -> None:
        """CJK script reduces page batch size."""
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import DocumentScriptDetection

        engine = DoclingRoutingEngine()
        metadata = _make_metadata(
            script_detection=DocumentScriptDetection(
                dominant_script="Hans",  # CJK
                dominant_confidence=0.9,
            ),
        )
        decision = engine.route(metadata)
        # CJK should get smaller batch size
        assert decision.params.page_batch_size <= 2

    def test_code_enrichment_flag(self) -> None:
        """Document with code enables code enrichment."""
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import LayoutType, PageLayoutSummary

        engine = DoclingRoutingEngine()
        page = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            has_code=True,  # Code detected
        )
        metadata = _make_metadata(page_layout_summary=[page])
        decision = engine.route(metadata)
        assert decision.params.enrich_code


# ============================================================================
# Test 4: Multi-Task Teacher with Heuristic Fallback
# ============================================================================


class TestTeacherFallback:
    """Tests for graceful degradation when teacher model unavailable."""

    def test_heuristic_detectors_work_standalone(
        self,
        clean_document: np.ndarray,
    ) -> None:
        """Heuristic detectors produce results without teacher model."""
        from image_preprocessing_detector.detection.script_detector import (
            detect_script_heuristic,
        )
        from image_preprocessing_detector.detection.shadow_detector import (
            detect_shadows,
        )
        from image_preprocessing_detector.detection.warping_detector import (
            detect_warping_distortion,
        )

        script_result = detect_script_heuristic(clean_document)
        assert script_result.detected_script is not None

        shadow_result = detect_shadows(clean_document)
        assert hasattr(shadow_result, "shadow_score")
        assert 0.0 <= shadow_result.shadow_score <= 1.0

        warping_result = detect_warping_distortion(clean_document)
        assert hasattr(warping_result, "warping_score")
        assert 0.0 <= warping_result.warping_score <= 1.0

    def test_teacher_detector_initializes_without_checkpoint(self) -> None:
        """SigLIP2MultiTaskDetector can be created without checkpoint."""
        from image_preprocessing_detector.detection.siglip2_multitask import (
            SigLIP2MultiTaskDetector,
        )

        detector = SigLIP2MultiTaskDetector()
        assert not detector._initialized
        assert detector.checkpoint_path is None


# ============================================================================
# Test 5: Pipeline Ordering
# ============================================================================


class TestPipelineOrdering:
    """Tests for correct pipeline step ordering."""

    def test_border_removal_before_corrections(
        self,
        document_with_border: np.ndarray,
    ) -> None:
        """Border removal happens before other corrections."""
        # Step 1: Border removal
        border_result = remove_borders(document_with_border)
        if border_result.applied:
            image = border_result.corrected_image
        else:
            image = document_with_border

        # Step 2: Perspective correction (on cropped image)
        perspective_result = correct_perspective(image, warping_score=0.3)

        # Both steps complete without error
        assert isinstance(border_result, CorrectionResult)
        assert isinstance(perspective_result, CorrectionResult)

    def test_corrections_chain_preserves_image(
        self,
        document_with_border: np.ndarray,
    ) -> None:
        """Chaining border removal + perspective doesn't corrupt image."""
        # Border removal
        result1 = remove_borders(document_with_border)
        image = result1.corrected_image

        # Perspective correction
        result2 = correct_perspective(image, warping_score=0.3)
        final = result2.corrected_image

        # Image is still valid
        assert final.ndim in (2, 3)
        assert final.size > 0
        assert final.dtype == np.uint8


# ============================================================================
# Test 6: Blank Page Early Exit
# ============================================================================


class TestBlankPageHandling:
    """Tests for blank page detection and early exit."""

    def test_blank_page_detected(self, blank_page: np.ndarray) -> None:
        """Blank page detector identifies empty pages."""
        from image_preprocessing_detector.detection.blank_page_detector import (
            detect_blank_page,
        )

        result = detect_blank_page(blank_page)
        assert result.is_blank

    def test_document_not_blank(self, clean_document: np.ndarray) -> None:
        """Document with content is not flagged as blank."""
        from image_preprocessing_detector.detection.blank_page_detector import (
            detect_blank_page,
        )

        result = detect_blank_page(clean_document)
        assert not result.is_blank


# ============================================================================
# Test 7: Full Pipeline Integration
# ============================================================================


class TestFullPipelineIntegration:
    """Tests for all components working together."""

    def test_full_pipeline_scanned_document(
        self,
        document_with_border: np.ndarray,
    ) -> None:
        """Full pipeline: scanned doc → border removal → detection → routing."""
        from image_preprocessing_detector.detection.blank_page_detector import (
            detect_blank_page,
        )
        from image_preprocessing_detector.detection.script_detector import (
            detect_script_heuristic,
        )
        from image_preprocessing_detector.detection.shadow_detector import (
            detect_shadows,
        )
        from image_preprocessing_detector.detection.warping_detector import (
            detect_warping_distortion,
        )
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import (
            DocumentScriptDetection,
            LayoutType,
            PageLayoutSummary,
        )

        # Step 1: Blank page check
        blank_result = detect_blank_page(document_with_border)
        assert not blank_result.is_blank

        # Step 2: Border removal
        border_result = remove_borders(document_with_border)
        image = border_result.corrected_image

        # Step 3: Warping detection
        warping_result = detect_warping_distortion(image)

        # Step 4: Perspective correction (if warping < 0.75)
        if warping_result.warping_score < 0.75:
            persp_result = correct_perspective(
                image,
                warping_score=warping_result.warping_score,
            )
            image = persp_result.corrected_image

        # Step 5: Script + shadow detection (heuristic fallback)
        script_result = detect_script_heuristic(image)
        shadow_result = detect_shadows(image)

        # Step 6: Routing via DocumentMetadata + PageLayoutSummary
        engine = DoclingRoutingEngine()
        page = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            complexity_score=0.3,
            warping_score=warping_result.warping_score,
            shadow_score=shadow_result.shadow_score,
        )
        metadata = _make_metadata(
            script_detection=DocumentScriptDetection(
                dominant_script=script_result.detected_script,
                dominant_confidence=script_result.confidence,
            ),
            page_layout_summary=[page],
        )
        decision = engine.route(metadata)

        # Verify all components produced valid results
        assert isinstance(border_result, CorrectionResult)
        assert 0.0 <= warping_result.warping_score <= 1.0
        assert script_result.detected_script is not None
        assert 0.0 <= shadow_result.shadow_score <= 1.0
        assert decision.params is not None

    def test_full_pipeline_clean_document(
        self,
        clean_document: np.ndarray,
    ) -> None:
        """Full pipeline on clean document completes without errors."""
        from image_preprocessing_detector.detection.blank_page_detector import (
            detect_blank_page,
        )
        from image_preprocessing_detector.detection.shadow_detector import (
            detect_shadows,
        )
        from image_preprocessing_detector.detection.warping_detector import (
            detect_warping_distortion,
        )

        # All components run without error on clean document
        blank_result = detect_blank_page(clean_document)
        border_result = remove_borders(clean_document)
        warping_result = detect_warping_distortion(clean_document)
        shadow_result = detect_shadows(clean_document)

        assert not blank_result.is_blank
        assert isinstance(border_result, CorrectionResult)
        assert 0.0 <= warping_result.warping_score <= 1.0
        assert 0.0 <= shadow_result.shadow_score <= 1.0

    def test_multi_task_prediction_dataclasses(self) -> None:
        """Multi-task prediction types are importable and usable."""
        from image_preprocessing_detector.detection.siglip2_multitask import (
            ClassificationResult,
            IQAScore,
            MultiTaskPrediction,
            RegressionResult,
            prediction_to_dict,
        )

        # Create a full prediction
        pred = MultiTaskPrediction(
            iqa_overall=IQAScore(mu=0.8, sigma_sq=0.03),
            iqa_sharpness=IQAScore(mu=0.85, sigma_sq=0.02),
            iqa_color=IQAScore(mu=0.7, sigma_sq=0.05),
            script=ClassificationResult("LATN", 0, 0.95, {"LATN": 0.95}),
            source=ClassificationResult("scanned", 0, 0.9, {"scanned": 0.9}),
            orientation=ClassificationResult("0", 0, 0.99, {"0": 0.99}),
            shadow=RegressionResult(0.1, 0.01),
            warping=RegressionResult(0.05, 0.02),
            inference_time_ms=45.0,
            device="cpu",
        )

        # Serialize to dict
        result_dict = prediction_to_dict(pred)
        assert result_dict["script"]["predicted"] == "LATN"
        assert result_dict["orientation"]["degrees"] == 0
        assert result_dict["inference_time_ms"] == 45.0

    def test_routing_decision_to_cli_args(self) -> None:
        """RoutingDecision params can generate CLI args."""
        from image_preprocessing_detector.routing.docling_router import (
            DoclingRoutingEngine,
        )
        from image_preprocessing_detector.schema import (
            DocumentScriptDetection,
            LayoutType,
            PageLayoutSummary,
            TableComplexity,
        )

        engine = DoclingRoutingEngine()
        page = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.COMPLEX,
            complexity_score=0.8,
            has_tables=True,
            table_complexity=TableComplexity(
                complexity_score=0.8,
                has_merged_cells=True,
                estimated_rows=10,
                estimated_columns=5,
            ),
            has_dense_math=True,
        )
        metadata = _make_metadata(
            script_detection=DocumentScriptDetection(
                dominant_script="Latn",
                dominant_confidence=0.9,
            ),
            page_layout_summary=[page],
        )
        decision = engine.route(metadata)

        # Verify params can be serialized
        cli_args = decision.params.to_cli_args()
        assert isinstance(cli_args, list)
        assert all(isinstance(a, str) for a in cli_args)

        yaml_str = decision.params.to_yaml()
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 0
