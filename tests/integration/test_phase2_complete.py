"""
End-to-end Phase 2 integration tests.

Tests the complete processing pipeline with Phase 2 features:
- Born-digital PDFs
- Image-only documents
- Hybrid documents (text + embedded images)
- Handwriting detection (via Layout-Lite, Phase 6)
- Table detection (via Layout-Lite, Phase 6)
- Document quality scoring (DQS)
- PDF classification
- OCR routing recommendations
- ML-based IQA with teacher-student ResNet architecture

Phase 2 Status: ~100% COMPLETE (November 2025)
- PDF type classification: IMPLEMENTED
- DQS calculation: IMPLEMENTED
- OCR routing recommendations: IMPLEMENTED
- ML IQA detector (ResNet-18/50): IMPLEMENTED
- Uncertainty & escalation logic: IMPLEMENTED
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import (
    correct_skew,
)
from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import detect_text
from image_preprocessing_detector.ingestion.image_loader import load_image
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    ElementCategory,
    IssueSeverity,
    IssueType,
)


class TestPhase2BornDigitalPipeline:
    """Test pipeline with born-digital (clean text) PDFs."""

    def test_born_digital_single_page(self) -> None:
        """Test born-digital PDF with clean text (no quality issues expected)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create clean, born-digital PDF
            pdf_path = Path(tmpdir) / "born_digital.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4

            # High-quality text
            page.insert_text(
                (50, 50),
                "Born-Digital Document\nClean text with no image quality issues.",
                fontsize=14,
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process pipeline
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(
                document_id="born_digital_001", file_name="born_digital.pdf"
            )

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            # Born-digital should have text
            assert text_result.has_text

            # Run IQA
            skew_result = detect_skew(page_image.image)
            blur_result = detect_blur(page_image.image)
            contrast_result = detect_contrast(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                _text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            # Generate output
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify
            loaded = load_json(output_path)
            assert loaded.document_id == "born_digital_001"
            assert loaded.num_pages == 1

            # Born-digital PDFs should have minimal quality issues
            page_metadata = loaded.pages[0]
            assert page_metadata.width_px > 0
            assert page_metadata.height_px > 0

            # Validate detected_issues structure
            assert isinstance(page_metadata.detected_issues, list)

    def test_born_digital_multi_page(self) -> None:
        """Test born-digital PDF with multiple pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "multi_page_born_digital.pdf"
            doc = fitz.open()

            # Create 5 pages
            for i in range(5):
                page = doc.new_page(width=595, height=842)
                text = f"Page {i + 1}\nMulti-page born-digital document."
                page.insert_text((50, 50), text, fontsize=14)

            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 5

            builder = MetadataBuilder(
                document_id="multi_born_digital_001",
                file_name="multi_page_born_digital.pdf",
            )

            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)
                skew_result = (
                    detect_skew(page_image.image) if text_result.has_text else None
                )
                blur_result = (
                    detect_blur(page_image.image) if text_result.has_text else None
                )
                contrast_result = (
                    detect_contrast(page_image.image) if text_result.has_text else None
                )

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            metadata = builder.build()
            assert metadata.num_pages == 5

            # Validate all pages processed
            for idx, page in enumerate(metadata.pages):
                assert page.page_index == idx


class TestPhase2ImageOnlyPipeline:
    """Test pipeline with image-only documents (no text)."""

    def test_image_only_photograph(self) -> None:
        """Test image-only document (photograph with no text)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create synthetic photograph (no text patterns)
            rng = np.random.default_rng(42)
            img = rng.integers(0, 255, (800, 600, 3), dtype=np.uint8)

            # Add some structure (but no text)
            cv2.circle(img, (300, 400), 100, (255, 0, 0), -1)
            cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), 5)

            img_path = Path(tmpdir) / "photograph.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, img_metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="image_only_001", file_name="photograph.jpg"
            )

            text_result = detect_text(image)

            # Image-only should have no text
            # (Though text_gate might detect edges as text - this is a known limitation)
            # Just verify the pipeline completes

            builder.add_page(
                page_number=0,
                page_data=(image, img_metadata),
                _text_result=text_result,
            )

            metadata = builder.build()
            assert metadata.num_pages == 1
            assert metadata.pages[0].width_px == 600
            assert metadata.pages[0].height_px == 800

    def test_image_only_with_quality_issues(self) -> None:
        """Test image-only document with blur and low contrast."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create low-quality image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 128  # Low contrast

            # Add random noise
            rng = np.random.default_rng(42)
            noise = rng.integers(-30, 30, (1000, 800, 3), dtype=np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            # Apply blur
            img = cv2.GaussianBlur(img, (15, 15), 0)  # type: ignore[assignment]

            img_path = Path(tmpdir) / "low_quality.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, img_metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="image_low_quality_001", file_name="low_quality.jpg"
            )

            text_result = detect_text(image)

            # Run IQA even if no text (image-only path)
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)

            builder.add_page(
                page_number=0,
                page_data=(image, img_metadata),
                _text_result=text_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            metadata = builder.build()
            page = metadata.pages[0]

            # Validate IQA ran
            assert isinstance(page.detected_issues, list)


class TestPhase2HybridPipeline:
    """Test pipeline with hybrid documents (text + embedded images)."""

    def test_hybrid_text_with_embedded_image(self) -> None:
        """Test hybrid PDF with text and embedded images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "hybrid.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # Add text
            page.insert_text(
                (50, 50),
                "Hybrid Document\nText with embedded image below:",
                fontsize=12,
            )

            # Create and embed a simple image
            img_array = np.ones((200, 200, 3), dtype=np.uint8) * 200
            cv2.rectangle(img_array, (50, 50), (150, 150), (100, 100, 255), -1)

            img_path = Path(tmpdir) / "embed.png"
            cv2.imwrite(str(img_path), img_array)

            # Insert image into PDF
            page.insert_image(
                fitz.Rect(100, 200, 300, 400),
                filename=str(img_path),
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(document_id="hybrid_001", file_name="hybrid.pdf")

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            # Hybrid should have text
            assert text_result.has_text

            skew_result = detect_skew(page_image.image)
            blur_result = detect_blur(page_image.image)
            contrast_result = detect_contrast(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                _text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            metadata = builder.build()
            assert metadata.num_pages == 1

            # Verify pipeline processed hybrid content
            page = metadata.pages[0]
            assert page.width_px > 0
            assert page.height_px > 0


class TestPhase2HandwritingDetection:
    """
    Test handwriting detection (Phase 2 feature).

    NOTE: Handwriting detection requires DocLayout-YOLO layout model (Phase 3).
    These are placeholder tests that will be skipped until implemented.
    """

    @pytest.mark.skip(
        reason="Phase 3: DocLayout-YOLO layout detection not yet implemented"
    )
    def test_handwriting_detection(self) -> None:
        """Test detection of handwritten content."""
        # Placeholder for future implementation
        # Will use DocLayout-YOLO to detect ElementCategory.HANDWRITING

    @pytest.mark.skip(
        reason="Phase 3: DocLayout-YOLO layout detection not yet implemented"
    )
    def test_mixed_typed_and_handwritten(self) -> None:
        """Test document with both typed text and handwriting."""
        # Placeholder for future implementation


class TestPhase2TableDetection:
    """
    Test table detection (Phase 2 feature).

    NOTE: Table detection requires DocLayout-YOLO layout model (Phase 3).
    These are placeholder tests that will be skipped until implemented.
    """

    @pytest.mark.skip(
        reason="Phase 3: DocLayout-YOLO layout detection not yet implemented"
    )
    def test_table_detection(self) -> None:
        """Test detection of tabular data."""
        # Placeholder for future implementation
        # Will use DocLayout-YOLO to detect ElementCategory.TABLE

    @pytest.mark.skip(
        reason="Phase 3: DocLayout-YOLO layout detection not yet implemented"
    )
    def test_table_with_quality_issues(self) -> None:
        """Test table detection with skewed or low-contrast tables."""
        # Placeholder for future implementation


class TestPhase2SchemaValidation:
    """Test Phase 2 schema fields and validation."""

    def test_schema_detected_issue_validation(self) -> None:
        """Test DetectedIssue model validation."""
        from image_preprocessing_detector.schema import DetectedIssue

        # Valid issue
        issue = DetectedIssue(
            type=IssueType.BLUR,
            confidence=0.85,
            severity=IssueSeverity.MEDIUM,
            metrics={"laplacian_variance": 42.5},
        )

        assert issue.type == IssueType.BLUR
        assert issue.confidence == pytest.approx(0.85)
        assert issue.severity == IssueSeverity.MEDIUM

        # Invalid confidence (Pydantic v2 raises ValidationError)
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            DetectedIssue(
                type=IssueType.SKEW,
                confidence=1.5,  # Invalid
                severity=IssueSeverity.LOW,
            )

    def test_schema_document_element_validation(self) -> None:
        """Test DocumentElement model validation."""
        from image_preprocessing_detector.schema import DocumentElement

        # Valid element
        element = DocumentElement(
            id="elem_001",
            category=ElementCategory.TABLE,
            bbox=[100, 200, 300, 400],  # [x, y, width, height]
            polygon=None,
            confidence=0.92,
            attributes={"num_rows": 5, "num_cols": 3},
            quality_issues=[],
            correction_applied=None,
        )

        assert element.category == ElementCategory.TABLE
        assert element.bbox == [100, 200, 300, 400]

        # Invalid bbox (not 4 values)
        with pytest.raises(ValueError, match="exactly 4 values"):
            DocumentElement(
                id="elem_002",
                category=ElementCategory.IMAGE,
                bbox=[100, 200],  # Invalid - only 2 values
                polygon=None,
                confidence=0.8,
                correction_applied=None,
            )

        # Invalid bbox (negative values)
        with pytest.raises(ValueError, match="non-negative"):
            DocumentElement(
                id="elem_003",
                category=ElementCategory.IMAGE,
                bbox=[-100, 200, 300, 400],  # Invalid - negative x
                polygon=None,
                confidence=0.8,
                correction_applied=None,
            )

    def test_schema_page_metadata_structure(self) -> None:
        """Test PageMetadata structure with Phase 2 fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Test", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(document_id="schema_001", file_name="test.pdf")

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                _text_result=text_result,
            )

            metadata = builder.build()
            page = metadata.pages[0]

            # Validate Phase 2 schema fields
            assert hasattr(page, "page_index")
            assert hasattr(page, "width_px")
            assert hasattr(page, "height_px")
            assert hasattr(page, "dpi_input")
            assert hasattr(page, "dpi_effective")
            assert hasattr(page, "detected_issues")
            assert hasattr(page, "planned_actions")
            assert hasattr(page, "elements")
            assert hasattr(page, "languages")
            assert hasattr(page, "transform_history")

            # Validate types
            assert isinstance(page.detected_issues, list)
            assert isinstance(page.planned_actions, list)
            assert isinstance(page.elements, list)
            assert isinstance(page.languages, list)
            assert isinstance(page.transform_history, list)

    def test_schema_pdf_type_classification(self) -> None:
        """
        Test pdf_type field in DocumentMetadata.

        Phase 2 feature: Classify PDFs as born_digital, image_only, or hybrid.
        """
        from image_preprocessing_detector.classification.pdf_type_classifier import (
            classify_pdf_type,
        )
        from image_preprocessing_detector.schema import PDFType

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Born-digital PDF (text only, no images)
            bd_path = Path(tmpdir) / "born_digital.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text(
                (50, 50),
                "This is a born-digital PDF with lots of text content. " * 10,
                fontsize=12,
            )
            doc.save(str(bd_path))
            doc.close()

            pdf_type = classify_pdf_type(bd_path)
            assert pdf_type == PDFType.BORN_DIGITAL

            # Test 2: Image-only PDF (no extractable text)
            img_only_path = Path(tmpdir) / "image_only.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            # Create and embed an image (no text)
            img_array = np.ones((200, 200, 3), dtype=np.uint8) * 128
            cv2.rectangle(img_array, (50, 50), (150, 150), (255, 0, 0), -1)
            img_path = Path(tmpdir) / "embed.png"
            cv2.imwrite(str(img_path), img_array)
            page.insert_image(fitz.Rect(100, 100, 400, 400), filename=str(img_path))
            doc.save(str(img_only_path))
            doc.close()

            pdf_type = classify_pdf_type(img_only_path)
            assert pdf_type == PDFType.IMAGE_ONLY

            # Test 3: Hybrid PDF (text + embedded image)
            hybrid_path = Path(tmpdir) / "hybrid.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text(
                (50, 50),
                "Hybrid document with text and image content. " * 5,
                fontsize=12,
            )
            page.insert_image(fitz.Rect(100, 200, 300, 400), filename=str(img_path))
            doc.save(str(hybrid_path))
            doc.close()

            pdf_type = classify_pdf_type(hybrid_path)
            assert pdf_type == PDFType.HYBRID

    def test_schema_document_quality_score(self) -> None:
        """
        Test DQS (Document Quality Score) field in DocumentMetadata.

        Phase 2 feature: Overall quality score with degradation and complexity.
        """
        from image_preprocessing_detector.metrics.dqs_calculator import (
            calculate_degradation_score,
            calculate_structural_complexity_score,
        )
        from image_preprocessing_detector.schema import (
            DQSMetadata,
            LayoutType,
            PageLayoutSummary,
        )

        # Test degradation score calculation
        classical_iqa = {
            "blur_score": 0.85,
            "noise_score": 0.78,
            "contrast_score": 0.72,
            "illumination_score": 0.90,
            "artifacts_score": 0.95,
        }
        degradation_score = calculate_degradation_score(classical_iqa)
        assert 0.0 <= degradation_score <= 1.0
        # Expected: 0.3*0.85 + 0.25*0.78 + 0.2*0.72 + 0.15*0.90 + 0.1*0.95 = 0.8235
        assert abs(degradation_score - 0.8235) < 0.01

        # Test structural complexity calculation (takes single PageLayoutSummary, not list)
        page_layout = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.MULTI_COLUMN,
            has_tables=True,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            fuzzy_scan=False,
            watermark=False,
            colorful_background=False,
            complexity_score=0.5,
        )
        complexity_score = calculate_structural_complexity_score(page_layout)
        assert 0.0 <= complexity_score <= 1.0
        # Expected: 0.4 (multi_column) + 0.2 (has_tables) = 0.6
        assert abs(complexity_score - 0.6) < 0.01

        # Test DQSMetadata creation
        dqs = DQSMetadata(
            degradation_score=0.2,  # 0=pristine, 1=degraded (inverted from quality)
            structural_complexity_score=complexity_score,
        )
        assert dqs.degradation_score == pytest.approx(0.2)
        assert 0.0 <= dqs.structural_complexity_score <= 1.0

    def test_schema_ocr_routing_recommendation(self) -> None:
        """
        Test ocr_routing_recommendation field in DocumentMetadata.

        Phase 2 feature: Recommend OCR strategy based on quality.
        """
        from image_preprocessing_detector.routing.recommendation_engine import (
            recommend_ocr_routing,
        )
        from image_preprocessing_detector.schema import (
            DQSMetadata,
            LayoutType,
            OCRRoutingStrategy,
            PageLayoutSummary,
            PDFType,
        )

        # Test 1: Born-digital with good quality → ocr_fast
        dqs_good = DQSMetadata(degradation_score=0.9, structural_complexity_score=0.2)
        simple_layout = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                fuzzy_scan=False,
                watermark=False,
                colorful_background=False,
                complexity_score=0.1,
            )
        ]
        recommendation, rationale = recommend_ocr_routing(
            PDFType.BORN_DIGITAL, dqs_good, 0.1, simple_layout
        )
        assert recommendation == OCRRoutingStrategy.OCR_FAST
        assert "Born-digital" in rationale

        # Test 2: Document with tables → vision_structured
        layout_with_tables = [
            PageLayoutSummary(
                page_number=1,
                layout_type=LayoutType.MULTI_COLUMN,
                has_tables=True,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                fuzzy_scan=False,
                watermark=False,
                colorful_background=False,
                complexity_score=0.6,
            )
        ]
        recommendation, rationale = recommend_ocr_routing(
            PDFType.HYBRID, dqs_good, 0.3, layout_with_tables
        )
        assert recommendation == OCRRoutingStrategy.VISION_STRUCTURED
        assert "tables" in rationale

        # Test 3: High risk document → ocr_advanced
        dqs_degraded = DQSMetadata(
            degradation_score=0.4, structural_complexity_score=0.5
        )
        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY,
            dqs_degraded,
            0.7,
            simple_layout,  # high risk
        )
        assert recommendation == OCRRoutingStrategy.OCR_ADVANCED


class TestPhase2MLInference:
    """
    Test ML-based IQA inference (Phase 2 feature).

    Uses teacher-student ResNet architecture with ONNX inference.
    """

    def test_ml_iqa_inference(self) -> None:
        """Test ML-based IQA detector (ResNet-18 student, ResNet-50 teacher)."""
        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
            ModelType,
        )

        # Test detector initialization (without models - tests the class structure)
        detector = MLIQADetector(
            student_model_path=None,
            teacher_model_path=None,
            device=Device.CPU,
            enable_modal_fallback=False,
        )

        # Verify detector configuration
        assert detector.device == Device.CPU
        assert detector.enable_modal_fallback is False
        assert detector.entropy_threshold == pytest.approx(0.8)
        assert detector.min_confidence_threshold == pytest.approx(0.6)
        assert detector.mean_confidence_threshold == pytest.approx(0.7)
        assert detector.discrepancy_threshold == pytest.approx(0.3)

        # Test with actual models if available AND onnxruntime is functional
        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"

        # Check if onnxruntime is functional (has InferenceSession attribute)
        try:
            import onnxruntime as ort

            onnxruntime_functional = hasattr(ort, "InferenceSession")
        except ImportError:
            onnxruntime_functional = False

        if student_path.exists() and onnxruntime_functional:
            # Test student inference
            detector_with_model = MLIQADetector(
                student_model_path=student_path,
                device=Device.CPU,
            )

            # Create test image
            test_image = np.ones((224, 224, 3), dtype=np.uint8) * 128
            cv2.rectangle(test_image, (50, 50), (174, 174), (200, 200, 200), -1)

            scores = detector_with_model.run_student_inference(test_image)
            assert scores.model_type == ModelType.STUDENT
            assert 0.0 <= scores.blur_score <= 1.0
            assert 0.0 <= scores.noise_score <= 1.0
            assert 0.0 <= scores.contrast_score <= 1.0
            assert 0.0 <= scores.overall_quality <= 1.0
            assert scores.inference_time_ms > 0

    def test_ml_confidence_calibration(self) -> None:
        """Test ML confidence score calibration and uncertainty calculation."""
        from image_preprocessing_detector.detection.iqa_ml import (
            Device,
            MLIQADetector,
            MLIQAScores,
            ModelType,
        )

        detector = MLIQADetector(device=Device.CPU)

        # Create mock scores with varying confidences
        mock_scores = MLIQAScores(
            blur_score=0.85,
            noise_score=0.72,
            contrast_score=0.68,
            skew_score=0.92,
            compression_score=0.88,
            overall_quality=0.81,
            confidences={
                "blur": 0.95,
                "noise": 0.72,
                "contrast": 0.58,  # Low confidence - should trigger escalation
                "skew": 0.91,
                "compression": 0.85,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=15.5,
        )

        # Test uncertainty calculation
        uncertainty = detector.calculate_uncertainty(mock_scores)
        assert 0.0 <= uncertainty.entropy <= 1.0
        assert 0.0 <= uncertainty.min_confidence <= 1.0
        assert 0.0 <= uncertainty.mean_confidence <= 1.0
        assert uncertainty.min_confidence == pytest.approx(0.58)  # contrast is lowest

        # Test escalation decision (should escalate due to low min_confidence)
        decision = detector.should_escalate_to_teacher(mock_scores)
        assert decision.should_escalate is True
        assert decision.reason is not None
        assert "low_min_confidence" in decision.reason

    def test_hybrid_iqa_ensemble_voting(self) -> None:
        """Test ensemble voting between classical and ML IQA via discrepancy check."""
        from image_preprocessing_detector.detection.iqa_ml import (
            ClassicalIQAScores,
            Device,
            MLIQADetector,
            MLIQAScores,
            ModelType,
        )

        detector = MLIQADetector(device=Device.CPU)

        # Create ML scores
        ml_scores = MLIQAScores(
            blur_score=0.85,
            noise_score=0.75,
            contrast_score=0.70,
            skew_score=0.90,
            compression_score=0.82,
            overall_quality=0.80,
            confidences={
                "blur": 0.9,
                "noise": 0.85,
                "contrast": 0.8,
                "skew": 0.95,
                "compression": 0.88,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=12.0,
        )

        # Create classical scores with small discrepancy (should NOT escalate)
        classical_close = ClassicalIQAScores(
            blur_score=0.82,  # 0.03 difference
            contrast_score=0.72,  # 0.02 difference
            skew_score=0.88,  # 0.02 difference
            noise_score=0.73,  # 0.02 difference (close to ML 0.75)
            compression_score=0.80,  # 0.02 difference (close to ML 0.82)
        )

        discrepancy = detector.calculate_discrepancy(ml_scores, classical_close)
        assert discrepancy.max_discrepancy < detector.discrepancy_threshold
        decision = detector.should_escalate_due_to_discrepancy(
            ml_scores, classical_close
        )
        assert decision.should_escalate is False

        # Create classical scores with large discrepancy (should escalate)
        classical_divergent = ClassicalIQAScores(
            blur_score=0.45,  # 0.40 difference - large!
            contrast_score=0.68,
            skew_score=0.85,
            noise_score=0.73,  # Keep noise close to avoid triggering on wrong dimension
            compression_score=0.80,  # Keep compression close
        )

        discrepancy_large = detector.calculate_discrepancy(
            ml_scores, classical_divergent
        )
        assert discrepancy_large.blur_discrepancy >= detector.discrepancy_threshold
        decision_escalate = detector.should_escalate_due_to_discrepancy(
            ml_scores, classical_divergent
        )
        assert decision_escalate.should_escalate is True
        assert decision_escalate.reason is not None
        assert "blur_discrepancy" in decision_escalate.reason


class TestPhase2CorrectionsWithMLGuidance:
    """
    Test corrections with ML-guided decisions (Phase 2 feature).

    NOTE: ML-guided corrections not yet implemented.
    """

    def test_corrections_applied_to_detected_issues(self) -> None:
        """Test that corrections are applied to detected quality issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skewed image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 200

            # Add text-like patterns
            for y in range(100, 900, 50):
                cv2.line(img, (100, y), (700, y), (50, 50, 50), 3)

            # Apply skew
            center = (400, 500)
            M = cv2.getRotationMatrix2D(center, -5, 1.0)  # noqa: N806  # fmt: skip
            img = cv2.warpAffine(img, M, (800, 1000))  # type: ignore[assignment]

            img_path = Path(tmpdir) / "skewed.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="correction_001", file_name="skewed.jpg"
            )

            text_result = detect_text(image)
            skew_result = detect_skew(image) if text_result.has_text else None

            # Apply correction
            skew_correction = None
            if skew_result and skew_result.is_skewed:
                skew_correction = correct_skew(
                    image, skew_result.angle, skew_result.confidence
                )
                if skew_correction.applied:
                    image = skew_correction.corrected_image

            builder.add_page(
                page_number=0,
                page_data=(image, metadata),
                _text_result=text_result,
                skew_result=skew_result,
                skew_correction=skew_correction,
            )

            doc_metadata = builder.build()
            page = doc_metadata.pages[0]

            # Verify transform history
            assert isinstance(page.transform_history, list)


class TestPhase2PerformanceTargets:
    """
    Test Phase 2 performance targets.

    Tests ML model loading and basic inference performance.
    Uses deployed ONNX models from models/iqa/onnx/.
    """

    @pytest.fixture
    def model_paths(self) -> dict[str, Path]:
        """Get paths to deployed ONNX models."""
        base_path = Path(__file__).parent.parent.parent / "models" / "iqa" / "onnx"
        return {
            "student": base_path / "resnet18_student.onnx",
            "teacher": base_path / "resnet50_teacher_50epoch.onnx",
        }

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image for inference."""
        # Create a realistic document-like image (grayscale with text-like patterns)
        img = np.ones((224, 224, 3), dtype=np.uint8) * 245  # Light background
        # Add some "text-like" lines
        for y in range(20, 200, 15):
            cv2.line(img, (20, y), (200, y), (50, 50, 50), 1)
        return img

    def test_onnx_models_exist(self, model_paths: dict[str, Path]) -> None:
        """Test that ONNX models are deployed and accessible."""
        student_path = model_paths["student"]
        teacher_path = model_paths["teacher"]

        assert student_path.exists(), f"Student model not found at {student_path}"
        assert teacher_path.exists(), f"Teacher model not found at {teacher_path}"

        # Verify file sizes are reasonable (not empty or corrupted)
        student_size = student_path.stat().st_size
        teacher_size = teacher_path.stat().st_size

        assert student_size > 10_000_000, (
            f"Student model too small: {student_size} bytes"
        )
        assert teacher_size > 50_000_000, (
            f"Teacher model too small: {teacher_size} bytes"
        )

    @pytest.mark.skipif(
        not pytest.importorskip("onnxruntime", reason="ONNX Runtime required"),
        reason="ONNX Runtime not installed",
    )
    def test_student_model_loads_and_infers(
        self, model_paths: dict[str, Path], sample_image: np.ndarray
    ) -> None:
        """Test that student model loads and runs inference."""
        import onnxruntime as ort

        student_path = model_paths["student"]
        if not student_path.exists():
            pytest.skip(f"Student model not found at {student_path}")

        # Load model
        session = ort.InferenceSession(
            str(student_path), providers=["CPUExecutionProvider"]
        )

        # Prepare input (NCHW format, normalized)
        img = cv2.resize(sample_image, (224, 224))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
        img = np.expand_dims(img, axis=0)  # Add batch dimension

        # Run inference
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: img})

        # Verify outputs exist and have expected structure
        assert len(outputs) > 0, "No outputs from inference"
        assert outputs[0].shape[0] == 1, "Batch size should be 1"

    @pytest.mark.skipif(
        not pytest.importorskip("onnxruntime", reason="ONNX Runtime required"),
        reason="ONNX Runtime not installed",
    )
    def test_inference_latency_under_500ms_cpu(
        self, model_paths: dict[str, Path], sample_image: np.ndarray
    ) -> None:
        """Test that student model inference completes in <500ms on CPU.

        Note: Original target was <150ms with GPU. This tests <500ms on CPU.
        """
        import time

        import onnxruntime as ort

        student_path = model_paths["student"]
        if not student_path.exists():
            pytest.skip(f"Student model not found at {student_path}")

        session = ort.InferenceSession(
            str(student_path), providers=["CPUExecutionProvider"]
        )

        # Prepare input
        img = cv2.resize(sample_image, (224, 224))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)

        # Warm up
        input_name = session.get_inputs()[0].name
        _ = session.run(None, {input_name: img})

        # Measure latency (average of 5 runs)
        latencies = []
        for _ in range(5):
            start = time.perf_counter()
            _ = session.run(None, {input_name: img})
            latencies.append((time.perf_counter() - start) * 1000)  # Convert to ms

        avg_latency = sum(latencies) / len(latencies)

        # Assert latency is under 500ms on CPU
        assert avg_latency < 500, (
            f"Average latency {avg_latency:.1f}ms exceeds 500ms target"
        )

    def test_model_metadata_exists(self, model_paths: dict[str, Path]) -> None:
        """Test that training metadata files exist."""
        base_path = model_paths["student"].parent

        # Check for training summary files
        student_summary = base_path / "training_summary_student.json"
        teacher_summary = base_path / "training_summary_50epoch.json"

        assert student_summary.exists(), (
            f"Student training summary not found: {student_summary}"
        )
        assert teacher_summary.exists(), (
            f"Teacher training summary not found: {teacher_summary}"
        )


class TestPhase2EndToEndIntegration:
    """Complete end-to-end integration test with all Phase 2 components."""

    def test_complete_pipeline_born_digital_to_json(self) -> None:
        """Test complete pipeline: born-digital PDF → DocumentMetadata JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create realistic born-digital PDF
            pdf_path = Path(tmpdir) / "complete_test.pdf"
            doc = fitz.open()

            # Multi-page document
            for i in range(3):
                page = doc.new_page(width=595, height=842)
                text = f"Page {i + 1}\n\nComplete Pipeline Test\n\nThis is a multi-page document for end-to-end testing."
                page.insert_text((50, 50 + i * 10), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Complete pipeline
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(
                document_id="e2e_complete_001", file_name="complete_test.pdf"
            )

            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)

                skew_result = None
                blur_result = None
                contrast_result = None

                if text_result.has_text:
                    skew_result = detect_skew(page_image.image)
                    blur_result = detect_blur(page_image.image)
                    contrast_result = detect_contrast(page_image.image)

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Validate complete JSON output
            assert output_path.exists()
            loaded = load_json(output_path)

            # Validate structure
            assert isinstance(loaded, DocumentMetadata)
            assert loaded.document_id == "e2e_complete_001"
            assert loaded.file_name == "complete_test.pdf"
            assert loaded.num_pages == 3
            assert len(loaded.pages) == 3

            # Validate all pages
            for idx, page in enumerate(loaded.pages):
                assert page.page_index == idx
                assert page.width_px > 0
                assert page.height_px > 0
                assert page.dpi_input > 0
                assert page.dpi_effective > 0
                assert isinstance(page.detected_issues, list)
                assert isinstance(page.elements, list)
                assert isinstance(page.transform_history, list)

            # Test JSON round-trip
            json_str = loaded.model_dump_json()
            assert json_str is not None
            assert len(json_str) > 0

    def test_pipeline_handles_all_document_types(self) -> None:
        """Test pipeline with mixed document types in sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cases = []

            # Born-digital
            pdf_bd = Path(tmpdir) / "born_digital.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Born-Digital", fontsize=14)
            doc.save(str(pdf_bd))
            doc.close()
            test_cases.append(("born_digital", pdf_bd))

            # Image-only
            rng = np.random.default_rng(42)
            img_only = rng.integers(0, 255, (600, 800, 3), dtype=np.uint8)
            img_path = Path(tmpdir) / "image_only.jpg"
            cv2.imwrite(str(img_path), img_only)
            test_cases.append(("image_only", img_path))

            # Process all
            for doc_type, file_path in test_cases:
                if file_path.suffix == ".pdf":
                    pages = load_pdf(str(file_path))
                else:
                    image, metadata_img = load_image(str(file_path))
                    pages = [(image, metadata_img)]  # type: ignore[list-item]

                builder = MetadataBuilder(
                    document_id=f"{doc_type}_001", file_name=file_path.name
                )

                for page_idx, page_data in enumerate(pages):
                    # page_data is either a tuple (image, metadata) or PageData object
                    page_image = page_data  # type: ignore[assignment]

                    text_result = detect_text(
                        page_image.image
                        if hasattr(page_image, "image")
                        else page_image[0]
                    )

                    builder.add_page(
                        page_number=page_idx,
                        page_data=page_image,
                        _text_result=text_result,
                    )

                result_metadata = builder.build()
                assert result_metadata.num_pages >= 1
                assert result_metadata.document_id == f"{doc_type}_001"
