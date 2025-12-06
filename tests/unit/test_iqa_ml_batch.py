# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for batch inference integration in ML IQA detector.

Sprint 4.3.1: Tests for BatchInferenceEngine integration into iqa_ml.py.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_ml import (
    Device,
    MLIQADetector,
    MLIQAScores,
    ModelType,
)


class TestBatchInferenceIntegration:
    """Test batch inference integration in MLIQADetector."""

    def test_get_batch_engine_initialization(self) -> None:
        """Test lazy initialization of batch inference engine."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            with patch.object(MLIQADetector, "_load_student_session"):
                detector = MLIQADetector(
                    student_model_path="models/iqa/student.onnx",
                    use_orchestrator=False,  # Legacy mode for simpler testing
                )

                # Initially no batch engine
                assert detector._batch_engine is None

                # Get batch engine triggers initialization
                # Patch where it's imported (inside the method)
                with patch(
                    "image_preprocessing_detector.models.batch_inference.BatchInferenceEngine"
                ) as mock_batch_engine_class:
                    mock_engine = MagicMock()
                    mock_batch_engine_class.return_value = mock_engine

                    engine = detector.get_batch_engine(device="cpu")

                    # Verify engine initialized
                    assert engine == mock_engine
                    mock_batch_engine_class.assert_called_once()
                    mock_engine.start.assert_called_once()

                    # Subsequent calls return same engine
                    engine2 = detector.get_batch_engine(device="cpu")
                    assert engine2 == mock_engine
                    # start() should only be called once
                    assert mock_engine.start.call_count == 1

    def test_run_batch_inference_empty_list(self) -> None:
        """Test batch inference with empty image list raises error."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                student_model_path="models/iqa/student.onnx",
                use_orchestrator=False,
            )

            with pytest.raises(ValueError, match="Images list cannot be empty"):
                detector.run_batch_inference([])

    def test_run_batch_inference_success(self) -> None:
        """Test successful batch inference."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                student_model_path="models/iqa/student.onnx",
                use_orchestrator=False,
            )

            # Create test images
            images = [np.ones((224, 224, 3), dtype=np.uint8) for _ in range(3)]

            # Mock batch engine
            with patch.object(detector, "get_batch_engine") as mock_get_engine:
                mock_engine = MagicMock()
                mock_get_engine.return_value = mock_engine

                # Mock successful batch inference
                mock_engine.submit_sync.return_value = {
                    "scores": {
                        "blur_score": 0.9,
                        "noise_score": 0.8,
                        "contrast_score": 0.85,
                        "skew_score": 0.95,
                        "compression_score": 0.88,
                    },
                    "confidences": {
                        "blur": 0.9,
                        "noise": 0.8,
                        "contrast": 0.85,
                        "skew": 0.95,
                        "compression": 0.88,
                    },
                    "overall_quality": 0.88,
                }

                # Run batch inference
                results = detector.run_batch_inference(images)

                # Validate results
                assert len(results) == 3
                for result in results:
                    assert isinstance(result, MLIQAScores)
                    assert result.model_type == ModelType.STUDENT
                    assert abs(result.overall_quality - 0.88) < 1e-6
                    assert abs(result.blur_score - 0.9) < 1e-6

    def test_run_batch_inference_with_fallback(self) -> None:
        """Test batch inference falls back to single inference on failure."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            with patch.object(MLIQADetector, "_load_student_session"):
                detector = MLIQADetector(
                    student_model_path="models/iqa/student.onnx",
                    use_orchestrator=False,
                )

                # Create test images
                images = [np.ones((224, 224, 3), dtype=np.uint8) for _ in range(2)]

                # Mock batch engine that fails
                with patch.object(detector, "get_batch_engine") as mock_get_engine:
                    mock_engine = MagicMock()
                    mock_get_engine.return_value = mock_engine

                    # First call succeeds, second fails
                    mock_engine.submit_sync.side_effect = [
                        {
                            "scores": {
                                "blur_score": 0.9,
                                "noise_score": 0.8,
                                "contrast_score": 0.85,
                                "skew_score": 0.95,
                                "compression_score": 0.88,
                            },
                            "confidences": {
                                "blur": 0.9,
                                "noise": 0.8,
                                "contrast": 0.85,
                                "skew": 0.95,
                                "compression": 0.88,
                            },
                            "overall_quality": 0.88,
                        },
                        RuntimeError("Batch engine timeout"),
                    ]

                    # Mock fallback to single inference
                    with patch.object(detector, "run_student_inference") as mock_single:
                        mock_single.return_value = MLIQAScores(
                            blur_score=0.7,
                            noise_score=0.7,
                            contrast_score=0.7,
                            skew_score=0.7,
                            compression_score=0.7,
                            overall_quality=0.7,
                            confidences={"blur": 0.7},
                            model_type=ModelType.STUDENT,
                            device=Device.CPU,
                            inference_time_ms=50.0,
                        )

                        # Run batch inference
                        results = detector.run_batch_inference(images)

                        # Validate results
                        assert len(results) == 2
                        # First image succeeded via batch
                        assert abs(results[0].overall_quality - 0.88) < 1e-6
                        # Second image fell back to single inference
                        assert abs(results[1].overall_quality - 0.7) < 1e-6
                        mock_single.assert_called_once()

    def test_run_batch_inference_with_request_ids(self) -> None:
        """Test batch inference with custom request IDs."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                student_model_path="models/iqa/student.onnx",
                use_orchestrator=False,
            )

            images = [np.ones((224, 224, 3), dtype=np.uint8)]
            request_ids = ["custom_id_1"]

            with patch.object(detector, "get_batch_engine") as mock_get_engine:
                mock_engine = MagicMock()
                mock_get_engine.return_value = mock_engine

                mock_engine.submit_sync.return_value = {
                    "scores": {
                        "blur_score": 0.9,
                        "noise_score": 0.8,
                        "contrast_score": 0.85,
                        "skew_score": 0.95,
                        "compression_score": 0.88,
                    },
                    "confidences": {
                        "blur": 0.9,
                        "noise": 0.8,
                        "contrast": 0.85,
                        "skew": 0.95,
                        "compression": 0.88,
                    },
                    "overall_quality": 0.88,
                }

                _results = detector.run_batch_inference(images, request_ids=request_ids)

                # Verify custom request ID was used
                mock_engine.submit_sync.assert_called_once()
                call_args = mock_engine.submit_sync.call_args
                assert call_args.kwargs["request_id"] == "custom_id_1"
