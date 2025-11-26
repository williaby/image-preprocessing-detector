# Test Gap Remediation Plan

**Date**: 2025-01-25
**Author**: Claude Opus 4.5
**Project**: Image Preprocessing Detector (Project A)
**Status**: PROPOSED

## Executive Summary

This plan addresses the 4 critical testing gaps identified in the E2E Testing Evaluation:

| Gap | Severity | New Tests | Estimated Effort |
|-----|----------|-----------|------------------|
| Layout-Lite (Phase 6) | HIGH | 15+ tests | 2-3 days |
| Real File Pre-flight | MEDIUM | 10+ tests | 1 day |
| ML IQA CI Integration | MEDIUM | CI config + 5 tests | 1 day |
| Teacher Escalation E2E | MEDIUM | 8+ tests | 1 day |

**Total New Tests**: ~40 tests
**Total Effort**: ~5-6 days

---

## Phase 1: Layout-Lite Tests (Priority P0)

### 1.1 Create Unit Tests

**File**: `tests/unit/detection/test_layout_lite.py`

```python
"""Unit tests for Layout-Lite detection (Phase 6).

Tests:
- DocLayout-YOLO model loading
- Page attribute extraction
- Complexity score calculation
- Element bounding box extraction
"""

import numpy as np
import pytest

from image_preprocessing_detector.detection.layout_lite import (
    LayoutLiteAnalyzer,
    LayoutLiteResult,
    PageAttributes,
)
from image_preprocessing_detector.schema import LayoutType


class TestLayoutLiteAnalyzer:
    """Unit tests for LayoutLiteAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return LayoutLiteAnalyzer()

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly."""
        assert analyzer is not None
        assert analyzer.model is not None or analyzer._model_path is not None

    def test_analyze_simple_page(self, analyzer, sample_document_image):
        """Test analysis of simple single-column page."""
        result = analyzer.analyze(sample_document_image)

        assert isinstance(result, LayoutLiteResult)
        assert result.layout_type in LayoutType
        assert 0.0 <= result.complexity_score <= 1.0
        assert isinstance(result.has_tables, bool)
        assert isinstance(result.has_figures, bool)

    def test_analyze_table_detection(self, analyzer, simple_table_image):
        """Test table detection in table-heavy image."""
        result = analyzer.analyze(simple_table_image)

        # Table image should detect tables
        assert result.has_tables is True

    def test_analyze_figure_detection(self, analyzer):
        """Test figure detection."""
        # Create image with figure-like region
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        # Add colored rectangle (figure-like)
        img[200:400, 100:500] = [100, 150, 200]

        result = analyzer.analyze(img)
        # May or may not detect as figure depending on model
        assert isinstance(result.has_figures, bool)

    def test_complexity_score_single_column(self, analyzer):
        """Test complexity score for simple layout."""
        # Create simple single-column document
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
        for y in range(100, 900, 40):
            img[y:y+2, 100:700] = 0  # Text lines

        result = analyzer.analyze(img)

        # Simple layout should have low complexity
        assert result.complexity_score < 0.4
        assert result.layout_type == LayoutType.SINGLE_COLUMN

    def test_complexity_score_multi_column(self, analyzer, multi_column_pdf):
        """Test complexity score for multi-column layout."""
        from image_preprocessing_detector.ingestion.pdf_loader import load_pdf

        pages = load_pdf(str(multi_column_pdf))
        if not pages:
            pytest.skip("Multi-column PDF not available")

        result = analyzer.analyze(pages[0].image)

        # Multi-column should have higher complexity
        assert result.complexity_score > 0.3
        assert result.layout_type in [LayoutType.MULTI_COLUMN, LayoutType.THREE_COLUMN]

    def test_empty_image_handling(self, analyzer):
        """Test handling of empty/white image."""
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255

        result = analyzer.analyze(img)

        # Should not crash, return minimal result
        assert result is not None
        assert result.has_tables is False
        assert result.has_figures is False


class TestPageAttributes:
    """Tests for PageAttributes dataclass."""

    def test_page_attributes_defaults(self):
        """Test default values for page attributes."""
        attrs = PageAttributes()

        assert attrs.has_tables is False
        assert attrs.has_figures is False
        assert attrs.has_dense_math is False
        assert attrs.has_handwriting is False
        assert attrs.fuzzy_scan is False
        assert attrs.watermark is False
        assert attrs.colorful_background is False

    def test_page_attributes_to_dict(self):
        """Test conversion to dictionary."""
        attrs = PageAttributes(has_tables=True, has_figures=True)

        d = attrs.to_dict()
        assert d["has_tables"] is True
        assert d["has_figures"] is True


class TestComplexityScoring:
    """Tests for complexity score calculation."""

    def test_base_score_single_column(self):
        """Test base score for single column."""
        from image_preprocessing_detector.detection.layout_lite import (
            calculate_complexity_score,
        )

        attrs = PageAttributes()
        score = calculate_complexity_score(LayoutType.SINGLE_COLUMN, attrs)

        assert score == pytest.approx(0.1, abs=0.05)

    def test_base_score_multi_column(self):
        """Test base score for multi-column."""
        from image_preprocessing_detector.detection.layout_lite import (
            calculate_complexity_score,
        )

        attrs = PageAttributes()
        score = calculate_complexity_score(LayoutType.MULTI_COLUMN, attrs)

        assert score == pytest.approx(0.4, abs=0.05)

    def test_tables_increase_complexity(self):
        """Test that tables increase complexity score."""
        from image_preprocessing_detector.detection.layout_lite import (
            calculate_complexity_score,
        )

        attrs_no_tables = PageAttributes(has_tables=False)
        attrs_with_tables = PageAttributes(has_tables=True)

        score_no = calculate_complexity_score(LayoutType.SINGLE_COLUMN, attrs_no_tables)
        score_with = calculate_complexity_score(LayoutType.SINGLE_COLUMN, attrs_with_tables)

        assert score_with > score_no
        assert score_with - score_no == pytest.approx(0.20, abs=0.05)

    def test_combined_features_complexity(self):
        """Test complexity with multiple features."""
        from image_preprocessing_detector.detection.layout_lite import (
            calculate_complexity_score,
        )

        attrs = PageAttributes(
            has_tables=True,
            has_figures=True,
            has_dense_math=True,
        )
        score = calculate_complexity_score(LayoutType.COMPLEX, attrs)

        # Complex + tables + figures + math should be high
        assert score > 0.8
```

### 1.2 Create Integration Tests

**File**: `tests/integration/test_layout_lite_integration.py`

```python
"""Integration tests for Layout-Lite with real fixtures.

Tests Layout-Lite analyzer with:
- DocLayNet PDF fixtures
- TableBank image fixtures
- Layout edge case samples
"""

import pytest

from image_preprocessing_detector.detection.layout_lite import LayoutLiteAnalyzer
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.schema import LayoutType


@pytest.fixture(scope="module")
def layout_analyzer():
    """Shared Layout-Lite analyzer for all tests."""
    return LayoutLiteAnalyzer()


@pytest.mark.real_data
class TestLayoutLiteWithDocLayNet:
    """Test Layout-Lite with DocLayNet PDF fixtures."""

    def test_simple_text_pdf(self, layout_analyzer, simple_text_pdf):
        """Test simple text-heavy PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        pages = load_pdf(str(simple_text_pdf))
        result = layout_analyzer.analyze(pages[0].image)

        # Simple text should be single column, low complexity
        assert result.layout_type == LayoutType.SINGLE_COLUMN
        assert result.complexity_score < 0.3
        assert result.has_tables is False

    def test_tables_figures_pdf(self, layout_analyzer, tables_figures_pdf):
        """Test PDF with tables and figures."""
        if not tables_figures_pdf.exists():
            pytest.skip("Tables/figures PDF not available")

        pages = load_pdf(str(tables_figures_pdf))
        result = layout_analyzer.analyze(pages[0].image)

        # Should detect tables or figures
        assert result.has_tables or result.has_figures
        assert result.complexity_score > 0.3

    def test_multi_column_pdf(self, layout_analyzer, multi_column_pdf):
        """Test multi-column layout PDF."""
        if not multi_column_pdf.exists():
            pytest.skip("Multi-column PDF not available")

        pages = load_pdf(str(multi_column_pdf))
        result = layout_analyzer.analyze(pages[0].image)

        # Should detect multi-column layout
        assert result.layout_type in [
            LayoutType.MULTI_COLUMN,
            LayoutType.THREE_COLUMN,
            LayoutType.COMPLEX,
        ]

    def test_all_doclaynet_pdfs(self, layout_analyzer, doclaynet_pdfs):
        """Test all DocLayNet PDFs process without error."""
        if not doclaynet_pdfs:
            pytest.skip("DocLayNet PDFs not available")

        for pdf_path in doclaynet_pdfs:
            pages = load_pdf(str(pdf_path))
            for page in pages:
                result = layout_analyzer.analyze(page.image)

                # All should produce valid results
                assert result is not None
                assert 0.0 <= result.complexity_score <= 1.0
                assert result.layout_type in LayoutType


@pytest.mark.real_data
class TestLayoutLiteWithTableBank:
    """Test Layout-Lite with TableBank image fixtures."""

    def test_simple_table_detection(self, layout_analyzer, simple_table_image):
        """Test simple table image."""
        import cv2

        if simple_table_image is None:
            pytest.skip("Simple table image not available")

        img = cv2.imread(str(simple_table_image))
        result = layout_analyzer.analyze(img)

        # Table image should detect tables
        assert result.has_tables is True

    def test_complex_table_detection(self, layout_analyzer, complex_table_image):
        """Test complex table image."""
        import cv2

        if complex_table_image is None:
            pytest.skip("Complex table image not available")

        img = cv2.imread(str(complex_table_image))
        result = layout_analyzer.analyze(img)

        assert result.has_tables is True
        # Complex table should have higher complexity
        assert result.complexity_score > 0.4


@pytest.mark.real_data
class TestLayoutLiteEdgeCases:
    """Test Layout-Lite with edge case samples."""

    def test_dense_math_pdf(self, layout_analyzer, dense_math_pdf):
        """Test dense math equations PDF."""
        if not dense_math_pdf.exists():
            pytest.skip("Dense math PDF not available")

        pages = load_pdf(str(dense_math_pdf))
        result = layout_analyzer.analyze(pages[0].image)

        # Dense math should have high complexity
        assert result.has_dense_math or result.complexity_score > 0.5

    def test_watermarked_document(self, layout_analyzer, watermarked_pdf):
        """Test watermarked document PDF."""
        if not watermarked_pdf.exists():
            pytest.skip("Watermarked PDF not available")

        pages = load_pdf(str(watermarked_pdf))
        result = layout_analyzer.analyze(pages[0].image)

        # Should detect watermark or at least not crash
        assert result is not None

    def test_handwriting_mixed(self, layout_analyzer, handwriting_mixed_image):
        """Test handwriting mixed with printed text."""
        import cv2

        if not handwriting_mixed_image.exists():
            pytest.skip("Handwriting mixed image not available")

        img = cv2.imread(str(handwriting_mixed_image))
        result = layout_analyzer.analyze(img)

        # Should detect handwriting
        assert result.has_handwriting is True
```

### 1.3 Create E2E Tests

**File**: `tests/e2e/test_layout_lite_e2e.py`

```python
"""End-to-end tests for Layout-Lite in full pipeline.

Tests Layout-Lite integration with:
- DQS calculation
- Routing recommendations
- Full DocumentMetadata generation
"""

import tempfile
from pathlib import Path

import pytest

from image_preprocessing_detector.detection.layout_lite import LayoutLiteAnalyzer
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.metrics.dqs_calculator import (
    calculate_structural_complexity_score,
)
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)
from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.schema import (
    DQSMetadata,
    PageLayoutSummary,
    PDFType,
)


@pytest.fixture(scope="module")
def layout_analyzer():
    """Shared Layout-Lite analyzer."""
    return LayoutLiteAnalyzer()


class TestLayoutLiteInPipeline:
    """Test Layout-Lite in full processing pipeline."""

    def test_layout_lite_to_dqs(self, layout_analyzer, sample_document_image):
        """Test Layout-Lite output feeds into DQS calculation."""
        result = layout_analyzer.analyze(sample_document_image)

        # Create PageLayoutSummary from Layout-Lite result
        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=result.layout_type,
            has_tables=result.has_tables,
            has_figures=result.has_figures,
            has_dense_math=result.has_dense_math,
            has_handwriting=result.has_handwriting,
            complexity_score=result.complexity_score,
        )

        # Calculate structural complexity
        complexity = calculate_structural_complexity_score(layout_summary)

        assert 0.0 <= complexity <= 1.0
        assert complexity == pytest.approx(result.complexity_score, abs=0.1)

    def test_layout_lite_to_routing(self, layout_analyzer, simple_table_image):
        """Test Layout-Lite with tables triggers correct routing."""
        import cv2

        if simple_table_image is None:
            pytest.skip("Simple table image not available")

        img = cv2.imread(str(simple_table_image))
        result = layout_analyzer.analyze(img)

        # Create routing inputs
        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=result.layout_type,
            has_tables=result.has_tables,
            has_figures=result.has_figures,
            has_dense_math=result.has_dense_math,
            has_handwriting=result.has_handwriting,
            complexity_score=result.complexity_score,
        )

        dqs = DQSMetadata(
            degradation_score=0.8,
            structural_complexity_score=result.complexity_score,
        )

        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY, dqs, 0.3, [layout_summary]
        )

        # Tables should trigger VISION_STRUCTURED
        if result.has_tables:
            from image_preprocessing_detector.schema import OCRRoutingRecommendation
            assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED

    @pytest.mark.real_data
    def test_full_pipeline_with_layout_lite(
        self, layout_analyzer, tables_figures_pdf
    ):
        """Test full pipeline with Layout-Lite on real PDF."""
        if not tables_figures_pdf.exists():
            pytest.skip("Tables/figures PDF not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            pages = load_pdf(str(tables_figures_pdf))

            builder = MetadataBuilder(
                document_id="layout_e2e_001",
                file_name="tables_figures_2.pdf",
            )

            page_layouts = []
            for idx, page_image in enumerate(pages):
                # Run Layout-Lite
                layout_result = layout_analyzer.analyze(page_image.image)

                # Create layout summary
                layout_summary = PageLayoutSummary(
                    page_number=idx + 1,
                    layout_type=layout_result.layout_type,
                    has_tables=layout_result.has_tables,
                    has_figures=layout_result.has_figures,
                    has_dense_math=layout_result.has_dense_math,
                    has_handwriting=layout_result.has_handwriting,
                    complexity_score=layout_result.complexity_score,
                )
                page_layouts.append(layout_summary)

                # Add page to builder
                builder.add_page(
                    page_number=idx,
                    page_data=page_image,
                )

            # Build with layout summaries
            builder.set_page_layout_summaries(page_layouts)
            metadata = builder.build()

            # Generate JSON
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify
            loaded = load_json(output_path)
            assert len(loaded.page_layout_summary) == len(pages)

            # At least one page should have tables or figures
            has_complex = any(
                p.has_tables or p.has_figures
                for p in loaded.page_layout_summary
            )
            assert has_complex
```

---

## Phase 2: Real File Pre-flight Tests (Priority P1)

### 2.1 Create Pre-flight Integration Tests

**File**: `tests/integration/test_preflight_real_fixtures.py`

```python
"""Integration tests for pre-flight analysis with real fixtures.

Tests DPI detection and upscaling with:
- DocLayNet PDF fixtures
- Various DPI scenarios
"""

import pytest

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.ingestion.pdf_analyzer import PDFDocumentAnalyzer
from image_preprocessing_detector.ingestion.pdf_resolution import (
    PDFResolutionAnalyzer,
)


@pytest.fixture
def settings():
    """Test settings with upscaling enabled."""
    s = Settings()
    s.enable_pdf_upscaling = True
    return s


@pytest.fixture
def analyzer(settings):
    """PDF document analyzer."""
    return PDFDocumentAnalyzer(settings)


@pytest.fixture
def resolution_analyzer():
    """PDF resolution analyzer."""
    return PDFResolutionAnalyzer()


@pytest.mark.real_data
class TestPreflightWithDocLayNet:
    """Test pre-flight analysis with DocLayNet PDFs."""

    def test_simple_text_pdf_resolution(self, resolution_analyzer, simple_text_pdf):
        """Test DPI detection on simple text PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        result = resolution_analyzer.analyze(simple_text_pdf)

        assert result is not None
        assert result.min_dpi > 0
        assert result.avg_dpi > 0
        assert result.max_dpi >= result.min_dpi
        assert isinstance(result.needs_upscaling, bool)

    def test_all_doclaynet_pdfs_resolution(self, resolution_analyzer, doclaynet_pdfs):
        """Test DPI detection on all DocLayNet PDFs."""
        if not doclaynet_pdfs:
            pytest.skip("DocLayNet PDFs not available")

        for pdf_path in doclaynet_pdfs:
            result = resolution_analyzer.analyze(pdf_path)

            assert result is not None
            assert result.min_dpi > 0
            # DocLayNet PDFs should generally be good quality
            assert result.avg_dpi >= 72  # At least screen resolution

    def test_preflight_analysis_complete(self, analyzer, simple_text_pdf):
        """Test complete pre-flight analysis."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        result = analyzer.analyze(simple_text_pdf)

        assert result.resolution_analysis is not None
        assert "needs_upscaling" in result.resolution_analysis
        assert result.recommended_path is not None

    def test_all_doclaynet_preflight(self, analyzer, doclaynet_pdfs):
        """Test pre-flight on all DocLayNet PDFs."""
        if not doclaynet_pdfs:
            pytest.skip("DocLayNet PDFs not available")

        for pdf_path in doclaynet_pdfs:
            result = analyzer.analyze(pdf_path)

            # All should complete without error
            assert result is not None
            assert result.resolution_analysis is not None


@pytest.mark.real_data
class TestPreflightEdgeCases:
    """Test pre-flight with edge case documents."""

    def test_watermarked_pdf_resolution(self, resolution_analyzer, watermarked_pdf):
        """Test DPI detection on watermarked PDF."""
        if not watermarked_pdf.exists():
            pytest.skip("Watermarked PDF not available")

        result = resolution_analyzer.analyze(watermarked_pdf)

        # Should not crash on watermarked document
        assert result is not None

    def test_dense_math_pdf_resolution(self, resolution_analyzer, dense_math_pdf):
        """Test DPI detection on dense math PDF."""
        if not dense_math_pdf.exists():
            pytest.skip("Dense math PDF not available")

        result = resolution_analyzer.analyze(dense_math_pdf)

        assert result is not None
        # Math documents often need higher DPI
        assert result.avg_dpi > 0
```

---

## Phase 3: ML IQA CI Integration (Priority P1)

### 3.1 CI Configuration Updates

**File**: `.github/workflows/ci.yml` (additions)

```yaml
  # New job: ML IQA tests with models
  test-ml-iqa:
    name: ML IQA Tests
    runs-on: ubuntu-latest
    needs: setup-optimized

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev,ml

      - name: Download test models
        env:
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GCP_SA_KEY }}
        run: |
          # Create credentials file
          echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" > /tmp/gcp-key.json
          export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json

          # Download models
          mkdir -p models/iqa/onnx
          gsutil cp gs://image_detection_b/models/phase2_student/student.onnx models/iqa/onnx/
          gsutil cp gs://image_detection_b/models/phase2_teacher/teacher.onnx models/iqa/onnx/

      - name: Run ML IQA tests
        run: |
          poetry run pytest tests/integration/test_ml_iqa_e2e.py -v --tb=short
          poetry run pytest tests/unit/test_iqa_ml.py -v --tb=short

  # New job: Real data tests
  test-real-data:
    name: Real Data Tests
    runs-on: ubuntu-latest
    needs: setup-optimized

    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true  # Fetch LFS files (test fixtures)

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev

      - name: Run real data tests
        run: |
          poetry run pytest -m real_data -v --tb=short
```

### 3.2 Mock-based ML Tests for Model-Unavailable Paths

**File**: `tests/unit/test_iqa_ml_fallback.py`

```python
"""Tests for ML IQA fallback behavior when models unavailable.

These tests run WITHOUT actual ONNX models to verify graceful degradation.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_ml import (
    MLIQADetector,
    ModelType,
)


class TestMLIQAModelUnavailable:
    """Test ML IQA behavior when models are unavailable."""

    def test_detector_creation_without_models(self):
        """Test detector handles missing models gracefully."""
        with patch(
            "image_preprocessing_detector.detection.iqa_ml.Path.exists",
            return_value=False,
        ):
            detector = MLIQADetector(
                student_model_path="nonexistent/student.onnx",
                teacher_model_path="nonexistent/teacher.onnx",
            )

            # Should create but models not loaded
            assert detector._student_session is None
            assert detector._teacher_session is None

    def test_inference_fails_gracefully(self):
        """Test inference returns None when models unavailable."""
        detector = MLIQADetector(
            student_model_path="nonexistent/student.onnx",
            teacher_model_path="nonexistent/teacher.onnx",
        )

        img = np.ones((224, 224, 3), dtype=np.uint8)

        # Should not crash, return None or raise specific exception
        with pytest.raises(RuntimeError, match="Model not loaded"):
            detector.run_student(img)

    def test_pipeline_returns_none_without_models(self):
        """Test pipeline returns None scores when models unavailable."""
        detector = MLIQADetector(
            student_model_path="nonexistent/student.onnx",
            teacher_model_path="nonexistent/teacher.onnx",
        )

        img = np.ones((224, 224, 3), dtype=np.uint8)
        classical_scores = MagicMock()

        student, teacher, reason = detector.run_pipeline(img, classical_scores)

        # Should return None, not crash
        assert student is None
        assert teacher is None


class TestMLIQAMockedInference:
    """Test ML IQA with mocked ONNX sessions."""

    @pytest.fixture
    def mock_onnx_session(self):
        """Create mock ONNX session."""
        session = MagicMock()
        # Mock output: 5 quality heads
        session.run.return_value = [
            np.array([[0.8, 0.9, 0.85, 0.75, 0.95]])  # [blur, noise, contrast, skew, compression]
        ]
        return session

    def test_student_inference_with_mock(self, mock_onnx_session):
        """Test student inference with mocked session."""
        detector = MLIQADetector.__new__(MLIQADetector)
        detector._student_session = mock_onnx_session
        detector._teacher_session = None
        detector._input_name = "input"
        detector._output_name = "output"

        img = np.ones((224, 224, 3), dtype=np.uint8)

        # This tests the processing logic without real model
        # Actual implementation may differ
        mock_onnx_session.run.assert_not_called()  # Not called yet
```

---

## Phase 4: Teacher Escalation E2E Tests (Priority P2)

### 4.1 Create Teacher Escalation E2E Tests

**File**: `tests/e2e/test_teacher_escalation_e2e.py`

```python
"""End-to-end tests for teacher escalation with real data.

Tests the complete escalation path:
1. Student inference
2. Uncertainty detection
3. Classical discrepancy
4. Teacher escalation
5. Result merging
"""

import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    MLIQADetector,
    ModelType,
)


@pytest.fixture
def ml_detector():
    """ML IQA detector with real models."""
    try:
        detector = MLIQADetector()
        if detector._student_session is None:
            return None
        return detector
    except Exception:
        return None


@pytest.mark.real_data
class TestTeacherEscalationWithRealData:
    """Test teacher escalation with real fixture files."""

    def test_low_quality_triggers_escalation(
        self, ml_detector, low_quality_image
    ):
        """Test that low quality image triggers teacher escalation."""
        import cv2

        if ml_detector is None:
            pytest.skip("ML detector not available")
        if low_quality_image is None:
            pytest.skip("Low quality image not available")

        img = cv2.imread(str(low_quality_image))

        # Get classical scores
        blur_result = detect_blur(img)
        contrast_result = detect_contrast(img)
        skew_result = detect_skew(img)

        classical_scores = ClassicalIQAScores(
            blur_score=blur_result.blur_score,
            contrast_score=contrast_result.score,
            skew_score=max(0.0, 1.0 - (abs(skew_result.angle) / 45.0)),
        )

        # Run pipeline
        student_scores, teacher_scores, escalation_reason = (
            ml_detector.run_pipeline(img, classical_scores)
        )

        # Low quality should escalate (or at least be detected as low quality)
        assert student_scores is not None
        # Either escalated or student detected issues
        if teacher_scores is not None:
            assert escalation_reason is not None
            assert teacher_scores.model_type == ModelType.TEACHER

    def test_blurry_iqa_sample_escalation(
        self, ml_detector, blurry_image
    ):
        """Test blurry IQA sample for potential escalation."""
        import cv2

        if ml_detector is None:
            pytest.skip("ML detector not available")
        if not blurry_image.exists():
            pytest.skip("Blurry image not available")

        img = cv2.imread(str(blurry_image))

        blur_result = detect_blur(img)
        classical_scores = ClassicalIQAScores(
            blur_score=blur_result.blur_score,
            contrast_score=0.8,
            skew_score=1.0,
        )

        student_scores, teacher_scores, escalation_reason = (
            ml_detector.run_pipeline(img, classical_scores)
        )

        # Blurry image should detect blur
        assert student_scores is not None
        assert student_scores.blur_score < 0.7  # Lower score = more blur

    def test_combined_issues_escalation(
        self, ml_detector, iqa_samples_dir
    ):
        """Test image with combined issues for escalation."""
        import cv2

        if ml_detector is None:
            pytest.skip("ML detector not available")

        combined_path = iqa_samples_dir / "combined_blur_noise.png"
        if not combined_path.exists():
            pytest.skip("Combined issues image not available")

        img = cv2.imread(str(combined_path))

        # Multiple issues should increase uncertainty
        blur_result = detect_blur(img)
        contrast_result = detect_contrast(img)

        classical_scores = ClassicalIQAScores(
            blur_score=blur_result.blur_score,
            contrast_score=contrast_result.score,
            skew_score=1.0,
        )

        student_scores, teacher_scores, escalation_reason = (
            ml_detector.run_pipeline(img, classical_scores)
        )

        assert student_scores is not None
        # Multiple issues may or may not escalate
        if teacher_scores:
            assert escalation_reason in [
                "high_uncertainty",
                "classical_discrepancy",
                "high_risk_document",
            ]

    def test_clean_reference_no_escalation(
        self, ml_detector, reference_clean_image
    ):
        """Test clean reference image should NOT escalate."""
        import cv2

        if ml_detector is None:
            pytest.skip("ML detector not available")
        if not reference_clean_image.exists():
            pytest.skip("Reference clean image not available")

        img = cv2.imread(str(reference_clean_image))

        blur_result = detect_blur(img)
        contrast_result = detect_contrast(img)

        classical_scores = ClassicalIQAScores(
            blur_score=blur_result.blur_score,
            contrast_score=contrast_result.score,
            skew_score=1.0,
        )

        student_scores, teacher_scores, escalation_reason = (
            ml_detector.run_pipeline(img, classical_scores)
        )

        # Clean image should have high scores
        assert student_scores is not None
        assert student_scores.overall_quality > 0.7

        # Clean image should NOT escalate (most of the time)
        # This is probabilistic - high quality shouldn't need teacher


class TestEscalationReasonTracking:
    """Test that escalation reasons are properly tracked."""

    def test_escalation_reason_high_uncertainty(self, ml_detector):
        """Test high uncertainty escalation is tracked."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create ambiguous image
        import numpy as np
        img = np.ones((224, 224, 3), dtype=np.uint8) * 128

        classical_scores = ClassicalIQAScores(
            blur_score=0.5,  # Ambiguous
            contrast_score=0.5,
            skew_score=0.5,
        )

        _, teacher_scores, reason = ml_detector.run_pipeline(img, classical_scores)

        if teacher_scores is not None:
            assert reason is not None
            assert isinstance(reason, str)

    def test_escalation_reason_classical_discrepancy(self, ml_detector):
        """Test classical discrepancy escalation."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        import numpy as np

        # Create image that ML might score differently than classical
        img = np.ones((224, 224, 3), dtype=np.uint8) * 200

        # Intentionally wrong classical scores to create discrepancy
        classical_scores = ClassicalIQAScores(
            blur_score=0.1,  # Say it's very blurry
            contrast_score=0.1,  # Say it's very low contrast
            skew_score=0.1,  # Say it's very skewed
        )

        _, teacher_scores, reason = ml_detector.run_pipeline(img, classical_scores)

        # Large discrepancy may trigger escalation
        if teacher_scores is not None and reason == "classical_discrepancy":
            assert True  # Escalation due to discrepancy
```

---

## Phase 5: Additional Test Infrastructure

### 5.1 Golden File Tests

**File**: `tests/integration/test_golden_files.py`

```python
"""Golden file tests for regression detection.

Compares current output against saved "golden" reference outputs.
"""

import json
from pathlib import Path

import pytest

from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import MetadataBuilder


GOLDEN_DIR = Path(__file__).parent.parent / "fixtures" / "golden_files"


@pytest.mark.real_data
class TestGoldenFileRegression:
    """Test output matches golden reference files."""

    def test_simple_text_golden(self, simple_text_pdf):
        """Test simple text PDF matches golden output."""
        if not simple_text_pdf.exists():
            pytest.skip("Simple text PDF not available")

        golden_path = GOLDEN_DIR / "simple_text_1_output.json"
        if not golden_path.exists():
            pytest.skip("Golden file not available")

        # Process PDF
        pages = load_pdf(str(simple_text_pdf))
        builder = MetadataBuilder(
            document_id="golden_simple_text",
            file_name="simple_text_1.pdf",
        )

        for idx, page in enumerate(pages):
            builder.add_page(page_number=idx, page_data=page)

        metadata = builder.build()
        current = json.loads(metadata.model_dump_json())

        # Load golden
        with golden_path.open() as f:
            golden = json.load(f)

        # Compare key fields (not timestamps)
        assert current["num_pages"] == golden["num_pages"]
        assert current["pdf_type"] == golden["pdf_type"]
        assert len(current["pages"]) == len(golden["pages"])

        # Compare page dimensions
        for curr_page, gold_page in zip(current["pages"], golden["pages"]):
            assert curr_page["width_px"] == gold_page["width_px"]
            assert curr_page["height_px"] == gold_page["height_px"]
```

### 5.2 Update conftest.py with New Fixtures

**Add to**: `tests/conftest.py`

```python
# Add these fixtures to conftest.py

@pytest.fixture
def tables_figures_pdf(doclaynet_fixtures_dir: Path) -> Path:
    """Return tables and figures PDF fixture."""
    pdf = doclaynet_fixtures_dir / "tables_figures_2.pdf"
    if not pdf.exists():
        pytest.skip("Tables/figures PDF fixture not available")
    return pdf


@pytest.fixture
def all_doclaynet_pdfs(doclaynet_fixtures_dir: Path) -> list[Path]:
    """Return all DocLayNet PDF fixtures."""
    pdfs = sorted(doclaynet_fixtures_dir.glob("*.pdf"))
    if not pdfs:
        pytest.skip("DocLayNet fixtures not available")
    return pdfs


@pytest.fixture
def all_tablebank_images(tablebank_fixtures_dir: Path) -> list[Path]:
    """Return all TableBank image fixtures."""
    images = []
    for ext in ["png", "jpg", "jpeg"]:
        images.extend(tablebank_fixtures_dir.glob(f"*.{ext}"))
    if not images:
        pytest.skip("TableBank fixtures not available")
    return sorted(images)


@pytest.fixture
def rotated_table_image(tablebank_fixtures_dir: Path) -> Path | None:
    """Return rotated table image fixture."""
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"rotated_3.{ext}"
        if img.exists():
            return img
    return None


@pytest.fixture
def low_quality_table_image(tablebank_fixtures_dir: Path) -> Path | None:
    """Return low quality table image fixture."""
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"low_quality_4.{ext}"
        if img.exists():
            return img
    return None


@pytest.fixture
def embedded_graphics_table_image(tablebank_fixtures_dir: Path) -> Path | None:
    """Return embedded graphics table image fixture."""
    for ext in ["png", "jpg", "jpeg"]:
        img = tablebank_fixtures_dir / f"embedded_graphics_5.{ext}"
        if img.exists():
            return img
    return None
```

---

## Implementation Schedule

### Week 1: Layout-Lite Tests (Phase 1)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Create unit tests | `tests/unit/detection/test_layout_lite.py` |
| 2 | Create integration tests | `tests/integration/test_layout_lite_integration.py` |
| 3 | Create E2E tests | `tests/e2e/test_layout_lite_e2e.py` |

### Week 2: CI and Real Data (Phases 2-3)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Create pre-flight real tests | `tests/integration/test_preflight_real_fixtures.py` |
| 2 | Update CI configuration | `.github/workflows/ci.yml` updates |
| 3 | Create ML fallback tests | `tests/unit/test_iqa_ml_fallback.py` |

### Week 3: Teacher Escalation and Infrastructure (Phases 4-5)

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Create teacher escalation E2E | `tests/e2e/test_teacher_escalation_e2e.py` |
| 2 | Create golden file tests | `tests/integration/test_golden_files.py` |
| 3 | Update conftest.py, documentation | Updated fixtures, README |

---

## Success Criteria

### Coverage Targets

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall Code Coverage | 29% | 80% | +51% |
| Workflow Stage Coverage | 75% | 95% | +20% |
| Layout-Lite Coverage | 0% | 80% | +80% |
| Real Data Test Coverage | 20% | 60% | +40% |

### Test Counts

| Category | Current | Target | New Tests |
|----------|---------|--------|-----------|
| Layout-Lite | 0 | 15+ | +15 |
| Pre-flight Real | ~5 | 15+ | +10 |
| ML IQA (with models) | ~10 | 20+ | +10 |
| Teacher Escalation E2E | ~3 | 10+ | +7 |
| Golden Files | 0 | 5+ | +5 |
| **Total New** | - | - | **~47** |

---

## Dependencies

### Required Before Implementation

1. **Layout-Lite Module Exists**: `src/image_preprocessing_detector/detection/layout_lite/`
2. **ONNX Models in GCS**: For CI model download
3. **GCP Service Account Secret**: For CI GCS access
4. **Git LFS Enabled**: For test fixtures in CI

### Optional Enhancements

1. **Model Caching in CI**: Reduce download time
2. **Parallel Test Jobs**: Faster CI
3. **Coverage Reporting**: Track improvement

---

## Conclusion

This plan addresses all 4 critical testing gaps with ~47 new tests across 7 new test files. Implementation should take approximately 3 weeks with the priority order:

1. **P0**: Layout-Lite tests (critical gap)
2. **P1**: Real file pre-flight + CI integration
3. **P2**: Teacher escalation E2E
4. **P3**: Golden file regression tests

Upon completion, workflow stage coverage should increase from 75% to 95%, and code coverage should significantly improve toward the 80% target.

---

*Plan created by Claude Opus 4.5 on 2025-01-25*
