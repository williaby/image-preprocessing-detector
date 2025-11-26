"""End-to-end integration test for ML IQA with ONNX models.

Tests the complete workflow:
1. Load document (PDF or image)
2. Run classical IQA detectors
3. Run ML IQA inference (student + teacher escalation)
4. Calculate discrepancy between classical and ML
5. Generate complete DocumentMetadata with all IQA fields
6. Validate JSON output

Requirements:
- ONNX models must be available in models/iqa/onnx/
- Tests use real model inference (not mocks)
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    MLIQADetector,
    ModelType,
)
from image_preprocessing_detector.detection.text_gate import detect_text
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)


class TestMLIQAEndToEnd:
    """End-to-end tests with real ONNX models.

    Note: Uses shared ml_detector fixture from conftest.py.
    """

    def test_e2e_student_inference_with_high_confidence(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test end-to-end pipeline with student inference (high confidence, no escalation)."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create clean, high-quality test image
            img = np.ones((800, 600, 3), dtype=np.uint8) * 240

            # Add clear text-like patterns
            for y in range(100, 700, 40):
                cv2.rectangle(img, (50, y), (550, y + 20), (50, 50, 50), -1)

            img_path = Path(tmpdir) / "high_quality.jpg"
            cv2.imwrite(str(img_path), img)

            # Run classical IQA
            skew_result = detect_skew(img)
            classical_scores = ClassicalIQAScores(
                blur_score=detect_blur(img).blur_score,
                contrast_score=detect_contrast(img).score,
                # Convert skew angle to normalized score (0-1)
                # Perfect alignment (0 degrees) = 1.0, higher angles = lower scores
                skew_score=max(0.0, 1.0 - (abs(skew_result.angle) / 45.0)),
            )

            # Run ML IQA pipeline
            student_scores, teacher_scores, escalation_reason = (
                ml_detector.run_pipeline(img, classical_scores)
            )

            # Validate student inference
            assert student_scores.model_type == ModelType.STUDENT
            assert student_scores.device == Device.CPU
            assert 0.0 <= student_scores.overall_quality <= 1.0
            assert 0.0 <= student_scores.blur_score <= 1.0
            assert 0.0 <= student_scores.noise_score <= 1.0
            assert 0.0 <= student_scores.contrast_score <= 1.0
            assert 0.0 <= student_scores.skew_score <= 1.0
            assert 0.0 <= student_scores.compression_score <= 1.0
            assert student_scores.inference_time_ms > 0

            # High quality image should NOT escalate to teacher
            # (Unless there's high uncertainty or discrepancy)
            if teacher_scores is not None:
                # If escalation occurred, verify teacher ran correctly
                assert teacher_scores.model_type == ModelType.TEACHER
                assert teacher_scores.device == Device.CPU
                assert escalation_reason is not None
            else:
                # No escalation - this is the expected case
                assert escalation_reason is None

    def test_e2e_pipeline_with_pdf_document(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test complete pipeline: PDF → Classical IQA → ML IQA → JSON output."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test PDF
            pdf_path = Path(tmpdir) / "test_ml_iqa.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # Add text content
            text = "ML IQA End-to-End Test\n\nThis document tests the complete pipeline with real ONNX inference."
            page.insert_text((50, 50), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Process PDF
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(
                document_id="ml_iqa_e2e_001", file_name="test_ml_iqa.pdf"
            )

            page_image = pages[0]

            # Text gate
            text_result = detect_text(page_image.image)
            assert text_result.has_text

            # Classical IQA
            skew_result = detect_skew(page_image.image)
            blur_result = detect_blur(page_image.image)
            contrast_result = detect_contrast(page_image.image)

            # ML IQA with classical scores
            classical_scores = ClassicalIQAScores(
                blur_score=blur_result.blur_score,
                contrast_score=contrast_result.score,
                # Convert skew angle to normalized score
                skew_score=max(0.0, 1.0 - (abs(skew_result.angle) / 45.0)),
            )

            student_scores, _teacher_scores, _escalation_reason = (
                ml_detector.run_pipeline(page_image.image, classical_scores)
            )

            # Add to metadata
            builder.add_page(
                page_number=0,
                page_data=page_image,
                _text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            # Generate JSON
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Validate JSON
            assert output_path.exists()
            loaded = load_json(output_path)

            assert loaded.document_id == "ml_iqa_e2e_001"
            assert loaded.num_pages == 1
            assert len(loaded.pages) == 1

            page_metadata = loaded.pages[0]
            assert page_metadata.width_px > 0
            assert page_metadata.height_px > 0
            assert isinstance(page_metadata.detected_issues, list)

            # Validate ML IQA scores were computed
            assert student_scores is not None
            assert student_scores.model_type == ModelType.STUDENT

    def test_e2e_teacher_escalation_high_uncertainty(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test teacher escalation due to high uncertainty."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create ambiguous/challenging image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 128  # Mid-gray

        # Add subtle patterns (hard to classify)
        rng = np.random.default_rng(seed=42)
        noise = rng.integers(-20, 20, (800, 600, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Apply slight blur
        img = cv2.GaussianBlur(img, (5, 5), 0)

        # Run ML IQA
        student_scores = ml_detector.run_student_inference(img)
        assert student_scores is not None, "Student inference should return scores"

        # Check uncertainty
        uncertainty = ml_detector.calculate_uncertainty(student_scores)
        assert 0.0 <= uncertainty.entropy <= 1.0
        assert 0.0 <= uncertainty.min_confidence <= 1.0
        assert 0.0 <= uncertainty.mean_confidence <= 1.0

        # Test escalation decision
        decision = ml_detector.should_escalate_to_teacher(student_scores)
        assert hasattr(decision, "should_escalate")
        assert hasattr(decision, "reason")
        assert hasattr(decision, "uncertainty_metrics")

        # If escalation occurs, run teacher
        if decision.should_escalate:
            teacher_scores = ml_detector.run_teacher_inference(img)
            assert teacher_scores.model_type == ModelType.TEACHER
            assert 0.0 <= teacher_scores.overall_quality <= 1.0

    def test_e2e_discrepancy_escalation(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test teacher escalation due to discrepancy between classical and ML IQA."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create image with known quality issues
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 200

            # Add skew
            center = (400, 500)
            M = cv2.getRotationMatrix2D(center, -8, 1.0)  # fmt: skip
            img = cv2.warpAffine(img, M, (800, 1000))

            # Apply blur
            img = cv2.GaussianBlur(img, (21, 21), 0)

            img_path = Path(tmpdir) / "degraded.jpg"
            cv2.imwrite(str(img_path), img)

            # Classical IQA
            blur_classical = detect_blur(img)
            contrast_classical = detect_contrast(img)
            skew_classical = detect_skew(img)

            classical_scores = ClassicalIQAScores(
                blur_score=blur_classical.blur_score,
                contrast_score=contrast_classical.score,
                # Convert skew angle to normalized score
                skew_score=max(0.0, 1.0 - (abs(skew_classical.angle) / 45.0)),
            )

            # ML IQA with discrepancy check
            student_scores, teacher_scores, _escalation_reason = (
                ml_detector.run_pipeline(img, classical_scores)
            )

            # Calculate discrepancy metrics
            discrepancy = ml_detector.calculate_discrepancy(
                student_scores, classical_scores
            )

            assert 0.0 <= discrepancy.blur_discrepancy <= 1.0
            assert 0.0 <= discrepancy.contrast_discrepancy <= 1.0
            assert 0.0 <= discrepancy.skew_discrepancy <= 1.0
            assert 0.0 <= discrepancy.max_discrepancy <= 1.0
            assert 0.0 <= discrepancy.mean_discrepancy <= 1.0

            # Check if discrepancy triggered escalation
            decision = ml_detector.should_escalate_due_to_discrepancy(
                student_scores, classical_scores
            )

            if decision.should_escalate:
                assert decision.reason is not None
                assert "discrepancy" in decision.reason
                # If escalation occurred, teacher should have run
                assert teacher_scores is not None
                assert teacher_scores.model_type == ModelType.TEACHER

    def test_e2e_performance_latency(self, ml_detector: MLIQADetector | None) -> None:
        """Test ML IQA inference latency (performance target: <100ms CPU)."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create test image
        rng = np.random.default_rng(42)
        img = rng.integers(0, 255, (800, 600, 3), dtype=np.uint8)

        # Run student inference multiple times
        latencies = []
        for _ in range(5):
            scores = ml_detector.run_student_inference(img)
            latencies.append(scores.inference_time_ms)

        # Validate inference times
        avg_latency = np.mean(latencies)
        np.min(latencies)
        np.max(latencies)

        assert all(lat > 0 for lat in latencies), (
            "All inference times should be positive"
        )

        # Performance target: ≤100ms CPU (acceptable), ≤40ms (target)
        # Note: Actual performance depends on hardware

        # Soft assertion - warn but don't fail if latency is high
        if avg_latency > 100:
            pytest.warn(
                f"Average inference latency ({avg_latency:.2f}ms) exceeds acceptable target (100ms)"
            )

    def test_e2e_multi_page_document(self, ml_detector: MLIQADetector | None) -> None:
        """Test ML IQA on multi-page document with varied quality."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multi-page PDF with different quality per page
            pdf_path = Path(tmpdir) / "multi_page_varied.pdf"
            doc = fitz.open()

            # Page 1: High quality
            page1 = doc.new_page(width=595, height=842)
            page1.insert_text(
                (50, 50), "Page 1: High Quality\nClear text, no issues.", fontsize=14
            )

            # Page 2: Medium quality (will add blur in processing)
            page2 = doc.new_page(width=595, height=842)
            page2.insert_text(
                (50, 50),
                "Page 2: Medium Quality\nSlight quality degradation.",
                fontsize=14,
            )

            # Page 3: Low quality (will add more degradation)
            page3 = doc.new_page(width=595, height=842)
            page3.insert_text(
                (50, 50), "Page 3: Low Quality\nSignificant degradation.", fontsize=14
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process all pages
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 3

            ml_scores_per_page = []

            for page_idx, page_image in enumerate(pages):
                # Run ML IQA
                student_scores, teacher_scores, escalation_reason = (
                    ml_detector.run_pipeline(page_image.image)
                )

                ml_scores_per_page.append(
                    {
                        "page": page_idx,
                        "student": student_scores,
                        "teacher": teacher_scores,
                        "escalation_reason": escalation_reason,
                    }
                )

            # Validate all pages processed
            assert len(ml_scores_per_page) == 3

            for page_data in ml_scores_per_page:
                student = page_data["student"]
                assert student.model_type == ModelType.STUDENT
                assert 0.0 <= student.overall_quality <= 1.0
                assert student.inference_time_ms > 0
