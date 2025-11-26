"""Unit tests for JSON generator ML IQA integration.

Tests that MetadataBuilder correctly populates ml_iqa and teacher_iqa fields
when ML IQA scores are provided.
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_ml import Device, MLIQAScores, ModelType
from image_preprocessing_detector.ingestion.image_loader import ImageMetadata
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)


class TestMetadataBuilderMLIQAIntegration:
    """Test MetadataBuilder with ML IQA scores."""

    def test_add_page_with_student_scores(self) -> None:
        """Test that add_page correctly populates ml_iqa field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Test Document", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            # Load PDF
            pages = load_pdf(str(pdf_path))

            # Create mock student scores
            student_scores = MLIQAScores(
                blur_score=0.85,
                noise_score=0.78,
                contrast_score=0.82,
                skew_score=0.91,
                compression_score=0.87,
                overall_quality=0.85,
                confidences={
                    "blur": 0.85,
                    "noise": 0.78,
                    "contrast": 0.82,
                    "skew": 0.91,
                    "compression": 0.87,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=89.5,
            )

            # Build metadata with ML IQA scores
            builder = MetadataBuilder(
                document_id="test_ml_iqa_001", file_name="test.pdf"
            )
            builder.add_page(
                page_number=0,
                page_data=pages[0],
                ml_iqa_student=student_scores,
            )

            # Generate and load JSON
            output_path = Path(tmpdir) / "output.json"
            metadata = builder.build()
            generate_json(metadata, output_path)

            loaded = load_json(output_path)

            # Validate ml_iqa field is populated
            assert loaded.pages[0].ml_iqa is not None
            assert loaded.pages[0].ml_iqa["source"] == "student"
            assert loaded.pages[0].ml_iqa["blur_score"] == pytest.approx(0.85)
            assert loaded.pages[0].ml_iqa["noise_score"] == pytest.approx(0.78)
            assert loaded.pages[0].ml_iqa["overall_quality"] == pytest.approx(0.85)
            assert loaded.pages[0].ml_iqa["device"] == "cpu"
            assert loaded.pages[0].ml_iqa["inference_time_ms"] == pytest.approx(89.5)

            # Validate teacher_iqa is None
            assert loaded.pages[0].teacher_iqa is None

    def test_add_page_with_teacher_escalation(self) -> None:
        """Test that add_page correctly populates teacher_iqa field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple image
            img = np.ones((800, 600, 3), dtype=np.uint8) * 128
            cv2.rectangle(img, (100, 100), (500, 700), (200, 200, 200), -1)

            img_path = Path(tmpdir) / "test.jpg"
            cv2.imwrite(str(img_path), img)

            # Create mock student scores
            student_scores = MLIQAScores(
                blur_score=0.55,
                noise_score=0.52,
                contrast_score=0.58,
                skew_score=0.50,
                compression_score=0.53,
                overall_quality=0.54,
                confidences={
                    "blur": 0.55,
                    "noise": 0.52,
                    "contrast": 0.58,
                    "skew": 0.50,
                    "compression": 0.53,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=87.2,
            )

            # Create mock teacher scores (better quality detected)
            teacher_scores = MLIQAScores(
                blur_score=0.82,
                noise_score=0.75,
                contrast_score=0.88,
                skew_score=0.79,
                compression_score=0.84,
                overall_quality=0.82,
                confidences={
                    "blur": 0.90,
                    "noise": 0.85,
                    "contrast": 0.92,
                    "skew": 0.88,
                    "compression": 0.91,
                },
                model_type=ModelType.TEACHER,
                device=Device.CPU,
                inference_time_ms=210.3,
            )

            escalation_reason = "low_min_confidence (0.500 < 0.600); low_mean_confidence (0.536 < 0.700)"

            # Build metadata with both student and teacher
            builder = MetadataBuilder(
                document_id="test_teacher_001", file_name="test.jpg"
            )

            # Create proper ImageMetadata for test fixture
            img_metadata = ImageMetadata(
                width=img.shape[1], height=img.shape[0], dpi_x=72.0, dpi_y=72.0
            )

            builder.add_page(
                page_number=0,
                page_data=(img, img_metadata),
                ml_iqa_student=student_scores,
                ml_iqa_teacher=teacher_scores,
                ml_iqa_escalation_reason=escalation_reason,
            )

            # Generate metadata
            metadata = builder.build()

            # Validate both ml_iqa and teacher_iqa are populated
            page = metadata.pages[0]

            # Student scores
            assert page.ml_iqa is not None
            assert page.ml_iqa["source"] == "student"
            assert page.ml_iqa["overall_quality"] == pytest.approx(0.54)

            # Teacher scores with escalation reason
            assert page.teacher_iqa is not None
            assert page.teacher_iqa["source"] == "teacher"
            assert page.teacher_iqa["overall_quality"] == pytest.approx(0.82)
            assert page.teacher_iqa["escalation_reason"] == escalation_reason
            assert page.teacher_iqa["inference_time_ms"] == pytest.approx(210.3)

    def test_add_page_without_ml_iqa(self) -> None:
        """Test that add_page works when ML IQA scores are not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "No ML IQA", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            # Load PDF
            pages = load_pdf(str(pdf_path))

            # Build metadata WITHOUT ML IQA scores
            builder = MetadataBuilder(
                document_id="test_no_ml_001", file_name="test.pdf"
            )
            builder.add_page(
                page_number=0,
                page_data=pages[0],
                # No ml_iqa_student or ml_iqa_teacher provided
            )

            metadata = builder.build()

            # Validate ml_iqa and teacher_iqa are None
            assert metadata.pages[0].ml_iqa is None
            assert metadata.pages[0].teacher_iqa is None

    def test_ml_iqa_score_precision(self) -> None:
        """Test that ML IQA scores are rounded to appropriate precision."""
        with tempfile.TemporaryDirectory():
            # Create test image
            img = np.ones((100, 100, 3), dtype=np.uint8) * 128

            # Create scores with high precision
            student_scores = MLIQAScores(
                blur_score=0.8512345,
                noise_score=0.7891234,
                contrast_score=0.8234567,
                skew_score=0.9123456,
                compression_score=0.8745678,
                overall_quality=0.8497456,
                confidences={
                    "blur": 0.8512345,
                    "noise": 0.7891234,
                    "contrast": 0.8234567,
                    "skew": 0.9123456,
                    "compression": 0.8745678,
                },
                model_type=ModelType.STUDENT,
                device=Device.GPU,
                inference_time_ms=15.3456789,
            )

            builder = MetadataBuilder(
                document_id="test_precision_001", file_name="test.jpg"
            )

            # Create proper ImageMetadata for test fixture
            img_metadata = ImageMetadata(
                width=img.shape[1], height=img.shape[0], dpi_x=72.0, dpi_y=72.0
            )

            builder.add_page(
                page_number=0,
                page_data=(img, img_metadata),
                ml_iqa_student=student_scores,
            )

            metadata = builder.build()
            ml_iqa = metadata.pages[0].ml_iqa

            # Validate precision (scores should be rounded to 4 decimal places)
            assert ml_iqa["blur_score"] == pytest.approx(0.8512)
            assert ml_iqa["noise_score"] == pytest.approx(0.7891)
            assert ml_iqa["contrast_score"] == pytest.approx(0.8235)
            assert ml_iqa["overall_quality"] == pytest.approx(0.8497)

            # Inference time should be rounded to 2 decimal places
            assert ml_iqa["inference_time_ms"] == pytest.approx(15.35)
