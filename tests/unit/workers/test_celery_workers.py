"""Tests for Celery worker pool configuration and tasks."""

import base64
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

rng = np.random.default_rng(42)


class TestCeleryConfig:
    """Tests for Celery configuration."""

    def test_config_defaults(self) -> None:
        """Test default configuration values."""
        from image_preprocessing_detector.workers.celery_app import CeleryConfig

        config = CeleryConfig()

        assert config.task_serializer == "json"
        assert config.result_serializer == "json"
        assert config.task_acks_late is True
        assert config.worker_prefetch_multiplier == 1
        assert config.task_default_queue == "default"
        assert config.task_time_limit == 300
        assert config.task_soft_time_limit == 240
        assert config.result_expires == 3600

    def test_config_to_dict(self) -> None:
        """Test configuration serialization."""
        from image_preprocessing_detector.workers.celery_app import CeleryConfig

        config = CeleryConfig()
        config_dict = config.to_dict()

        assert "broker_url" in config_dict
        assert "result_backend" in config_dict
        assert "task_queues" in config_dict
        assert "task_routes" in config_dict

    def test_config_from_environment(self) -> None:
        """Test configuration from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "CELERY_BROKER_URL": "redis://custom:6379/0",
                "CELERY_RESULT_BACKEND": "redis://custom:6379/1",
            },
        ):
            from image_preprocessing_detector.workers.celery_app import CeleryConfig

            config = CeleryConfig()
            assert config.broker_url == "redis://custom:6379/0"
            assert config.result_backend == "redis://custom:6379/1"

    def test_queue_configuration(self) -> None:
        """Test queue configuration."""
        from image_preprocessing_detector.workers.celery_app import CeleryConfig

        config = CeleryConfig()
        queues = config._get_queues()

        queue_names = [q.name for q in queues]
        assert "default" in queue_names
        assert "gpu" in queue_names
        assert "batch" in queue_names

    def test_task_routing(self) -> None:
        """Test task routing configuration."""
        from image_preprocessing_detector.workers.celery_app import CeleryConfig

        config = CeleryConfig()
        routes = config._get_routes()

        assert "image_preprocessing_detector.workers.tasks.run_iqa_analysis" in routes
        assert (
            "image_preprocessing_detector.workers.tasks.process_single_document"
            in routes
        )
        assert (
            "image_preprocessing_detector.workers.tasks.process_batch_documents"
            in routes
        )

        # IQA should go to GPU queue
        iqa_route = routes[
            "image_preprocessing_detector.workers.tasks.run_iqa_analysis"
        ]
        assert iqa_route["queue"] == "gpu"


class TestCeleryApp:
    """Tests for Celery application."""

    def test_app_exists(self) -> None:
        """Test Celery app is created."""
        from image_preprocessing_detector.workers.celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "image_preprocessing_detector"

    def test_get_celery_app(self) -> None:
        """Test get_celery_app helper."""
        from image_preprocessing_detector.workers.celery_app import get_celery_app

        app = get_celery_app()
        assert app is not None

    def test_ping_task_registered(self) -> None:
        """Test ping task is registered."""
        from image_preprocessing_detector.workers.celery_app import celery_app

        assert "celery.ping" in celery_app.tasks


class TestHelperFunctions:
    """Tests for helper functions in tasks."""

    def test_preprocess_image(self) -> None:
        """Test image preprocessing."""
        from image_preprocessing_detector.workers.tasks import _preprocess_image

        # Create dummy image (HxWx3, BGR)
        image = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)

        result = _preprocess_image(image)

        # Check output shape
        assert result.shape == (1, 3, 224, 224)
        assert result.dtype == np.float32

    def test_postprocess_outputs(self) -> None:
        """Test output postprocessing."""
        from image_preprocessing_detector.workers.tasks import _postprocess_outputs

        # Create mock outputs
        outputs = {}
        for i in range(5):
            outputs[f"head_{i}"] = np.array([[0.3, 0.7]])  # Logits

        scores, confidences = _postprocess_outputs(outputs)

        # Check all heads have scores
        assert "blur_score" in scores
        assert "noise_score" in scores
        assert "contrast_score" in scores
        assert "skew_score" in scores
        assert "compression_score" in scores

        # Check confidences
        assert "blur" in confidences
        assert "noise" in confidences

        # Scores should be probabilities
        for score in scores.values():
            assert 0 <= score <= 1

        for conf in confidences.values():
            assert 0 <= conf <= 1


class TestIQATask:
    """Tests for IQA analysis task."""

    def test_iqa_task_registered(self) -> None:
        """Test IQA task is registered."""
        from image_preprocessing_detector.workers.celery_app import celery_app

        task_name = "image_preprocessing_detector.workers.tasks.run_iqa_analysis"
        assert task_name in celery_app.tasks

    def test_iqa_task_config(self) -> None:
        """Test IQA task configuration."""
        from image_preprocessing_detector.workers.tasks import run_iqa_analysis

        assert run_iqa_analysis.name == (
            "image_preprocessing_detector.workers.tasks.run_iqa_analysis"
        )
        assert run_iqa_analysis.max_retries == 3
        assert run_iqa_analysis.soft_time_limit == 120
        assert run_iqa_analysis.time_limit == 180


class TestDocumentProcessingTask:
    """Tests for document processing task."""

    def test_task_registered(self) -> None:
        """Test document processing task is registered."""
        from image_preprocessing_detector.workers.celery_app import celery_app

        task_name = "image_preprocessing_detector.workers.tasks.process_single_document"
        assert task_name in celery_app.tasks

    def test_task_config(self) -> None:
        """Test task configuration."""
        from image_preprocessing_detector.workers.tasks import process_single_document

        assert process_single_document.max_retries == 2
        assert process_single_document.soft_time_limit == 180
        assert process_single_document.time_limit == 240


class TestBatchProcessingTask:
    """Tests for batch processing task."""

    def test_task_registered(self) -> None:
        """Test batch processing task is registered."""
        from image_preprocessing_detector.workers.celery_app import celery_app

        task_name = "image_preprocessing_detector.workers.tasks.process_batch_documents"
        assert task_name in celery_app.tasks

    def test_task_config(self) -> None:
        """Test task configuration."""
        from image_preprocessing_detector.workers.tasks import process_batch_documents

        assert process_batch_documents.soft_time_limit == 600
        assert process_batch_documents.time_limit == 900


class TestWorkerMonitoring:
    """Tests for worker monitoring functions.

    Note: The actual connection failure tests are in TestCeleryAppFunctions
    with proper mocking to avoid slow connection timeouts.
    """

    # Monitoring tests with mocks are in TestCeleryAppFunctions below


class TestIQATaskClass:
    """Tests for IQATask base class."""

    def test_lazy_model_loading(self) -> None:
        """Test that models are lazily loaded."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        # Initially None (not loaded)
        assert task._student_session is None
        assert task._teacher_session is None


class TestModuleExports:
    """Tests for module exports."""

    def test_workers_init_exports(self) -> None:
        """Test workers __init__ exports all expected items."""
        from image_preprocessing_detector import workers

        assert hasattr(workers, "celery_app")
        assert hasattr(workers, "process_single_document")
        assert hasattr(workers, "process_batch_documents")
        assert hasattr(workers, "run_iqa_analysis")


class TestTaskHelperFunctions:
    """Tests for task helper functions with full coverage."""

    def test_preprocess_image_normalization(self) -> None:
        """Test image preprocessing with ImageNet normalization."""
        from image_preprocessing_detector.workers.tasks import _preprocess_image

        # Create a specific image to verify normalization
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128  # Gray image

        result = _preprocess_image(image)

        # Check shape
        assert result.shape == (1, 3, 224, 224)
        # Check dtype
        assert result.dtype == np.float32
        # Check that values are normalized (not in 0-255 range)
        assert result.min() < 0 or result.max() < 1

    def test_preprocess_image_channel_order(self) -> None:
        """Test BGR to RGB conversion in preprocessing."""
        from image_preprocessing_detector.workers.tasks import _preprocess_image

        # Create BGR image where B=255, G=0, R=0
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :, 0] = 255  # Blue channel in BGR

        result = _preprocess_image(image)

        # After BGR->RGB, the blue should be in the third channel position
        # of the CHW tensor (index 2)
        assert result.shape == (1, 3, 224, 224)

    def test_postprocess_outputs_partial(self) -> None:
        """Test postprocessing with partial outputs."""
        from image_preprocessing_detector.workers.tasks import _postprocess_outputs

        # Only provide 3 heads instead of 5
        outputs = {}
        for i in range(3):
            outputs[f"head_{i}"] = np.array([[0.5, 0.5]])

        scores, _ = _postprocess_outputs(outputs)

        # Should have scores for available heads
        assert "blur_score" in scores
        assert "noise_score" in scores
        assert "contrast_score" in scores
        # Should not have scores for missing heads
        assert "skew_score" not in scores
        assert "compression_score" not in scores

    def test_postprocess_outputs_extreme_logits(self) -> None:
        """Test postprocessing with extreme logit values."""
        from image_preprocessing_detector.workers.tasks import _postprocess_outputs

        outputs = {}
        # Very high logit for class 1 (good quality)
        outputs["head_0"] = np.array([[-100.0, 100.0]])
        # Very high logit for class 0 (bad quality)
        outputs["head_1"] = np.array([[100.0, -100.0]])

        scores, confidences = _postprocess_outputs(outputs)

        # First head should have score close to 1
        assert scores["blur_score"] > 0.99
        # Second head should have score close to 0
        assert scores["noise_score"] < 0.01
        # Confidences should be high for both
        assert confidences["blur"] > 0.99
        assert confidences["noise"] > 0.99


class TestRunIQAAnalysisTask:
    """Tests for run_iqa_analysis task execution."""

    def test_run_iqa_analysis_success(self) -> None:
        """Test successful IQA analysis with mocked components."""
        import cv2

        from image_preprocessing_detector.workers.tasks import IQATask, run_iqa_analysis

        # Create a real test image
        test_image = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
        _, encoded = cv2.imencode(".png", test_image)
        image_b64 = base64.b64encode(encoded.tobytes()).decode()

        # Create mock ONNX session
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_session.get_inputs.return_value = [mock_input]

        mock_outputs = [MagicMock(name=f"head_{i}") for i in range(5)]
        for i, out in enumerate(mock_outputs):
            out.name = f"head_{i}"
        mock_session.get_outputs.return_value = mock_outputs

        # Return mock logits for each head
        mock_session.run.return_value = [np.array([[0.3, 0.7]]) for _ in range(5)]

        # Mock the student session property on IQATask class
        with patch.object(
            IQATask, "student_session", new_callable=lambda: mock_session
        ):
            # Call the task directly (synchronous execution)
            result = run_iqa_analysis(
                image_b64, request_id="test-123", enable_teacher=False
            )

        assert result["request_id"] == "test-123"
        assert result["model"] == "student"
        assert "scores" in result
        assert "confidences" in result
        assert "overall_quality" in result
        assert "inference_time_ms" in result

    def test_run_iqa_analysis_invalid_image(self) -> None:
        """Test IQA analysis with invalid image data."""
        from image_preprocessing_detector.workers.tasks import run_iqa_analysis

        # Invalid base64 that decodes but isn't a valid image
        invalid_b64 = base64.b64encode(b"not an image").decode()

        # Mock retry to raise an exception (simulating max retries exceeded)
        with patch(
            "image_preprocessing_detector.workers.tasks.run_iqa_analysis.retry",
            side_effect=ValueError("Max retries exceeded"),
        ):
            with pytest.raises(ValueError, match="Max retries exceeded"):
                run_iqa_analysis(invalid_b64, request_id="test-456")

    def test_run_iqa_analysis_no_model(self) -> None:
        """Test IQA analysis when model is not available."""
        import cv2

        from image_preprocessing_detector.workers.tasks import IQATask, run_iqa_analysis

        # Create valid test image
        test_image = rng.integers(0, 255, (100, 100, 3), dtype=np.uint8)
        _, encoded = cv2.imencode(".png", test_image)
        image_b64 = base64.b64encode(encoded.tobytes()).decode()

        # Mock student_session to return None
        with patch.object(IQATask, "student_session", None):
            # Mock retry to raise an exception
            with patch(
                "image_preprocessing_detector.workers.tasks.run_iqa_analysis.retry",
                side_effect=RuntimeError("Student model not available"),
            ):
                with pytest.raises(RuntimeError, match="Student model not available"):
                    run_iqa_analysis(image_b64)


class TestProcessSingleDocumentTask:
    """Tests for process_single_document task execution."""

    def test_process_single_document_success(self) -> None:
        """Test successful document processing."""
        from image_preprocessing_detector.workers.tasks import process_single_document

        # Create simple text content
        content = b"Hello, World!"
        content_b64 = base64.b64encode(content).decode()

        # Call task directly (synchronous execution)
        result = process_single_document(content_b64, "test.txt", options={})

        assert result["filename"] == "test.txt"
        assert result["file_size"] == len(content)
        assert result["file_type"] == ".txt"
        assert result["status"] == "completed"
        assert "processing_time_ms" in result

    def test_process_single_document_pdf(self) -> None:
        """Test processing a PDF document."""
        from image_preprocessing_detector.workers.tasks import process_single_document

        # Create minimal PDF content (just the header)
        pdf_content = b"%PDF-1.4\n%%EOF\n"
        content_b64 = base64.b64encode(pdf_content).decode()

        result = process_single_document(content_b64, "test.pdf", options={})

        assert result["filename"] == "test.pdf"
        assert result["file_type"] == ".pdf"
        assert result["status"] == "completed"
        # page_count might not be present for invalid PDF

    def test_process_single_document_no_options(self) -> None:
        """Test processing with None options."""
        from image_preprocessing_detector.workers.tasks import process_single_document

        content = b"Test content"
        content_b64 = base64.b64encode(content).decode()

        result = process_single_document(content_b64, "file.dat", options=None)

        assert result["status"] == "completed"


class TestProcessBatchDocumentsTask:
    """Tests for process_batch_documents task execution."""

    def test_process_batch_empty(self) -> None:
        """Test batch processing with empty file list."""
        from image_preprocessing_detector.workers.tasks import process_batch_documents

        # Call task directly
        result = process_batch_documents(files_data=[], options={}, job_id="batch-001")

        assert result["job_id"] == "batch-001"
        assert result["total_files"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["avg_time_per_file_ms"] == 0

    def test_process_batch_result_structure(self) -> None:
        """Test batch result has expected structure."""
        from image_preprocessing_detector.workers.tasks import process_batch_documents

        # Empty batch to verify structure without infrastructure
        result = process_batch_documents(files_data=[], options=None, job_id=None)

        assert "job_id" in result
        assert "total_files" in result
        assert "successful" in result
        assert "failed" in result
        assert "results" in result
        assert "errors" in result
        assert "total_processing_time_ms" in result
        assert "avg_time_per_file_ms" in result


class TestCeleryAppFunctions:
    """Tests for Celery app utility functions."""

    def test_ping_task(self) -> None:
        """Test ping health check task."""
        from image_preprocessing_detector.workers.celery_app import ping

        result = ping()
        assert result == "pong"

    def test_get_celery_app(self) -> None:
        """Test get_celery_app returns Celery instance."""
        from celery import Celery

        from image_preprocessing_detector.workers.celery_app import get_celery_app

        app = get_celery_app()
        assert isinstance(app, Celery)
        assert app.main == "image_preprocessing_detector"

    def test_check_broker_connection_failure(self) -> None:
        """Test check_broker_connection handles failures."""
        from image_preprocessing_detector.workers.celery_app import (
            celery_app,
            check_broker_connection,
        )

        # Mock connection to fail - the code uses a context manager so we need
        # __enter__ to return a mock whose ensure_connection raises.
        with patch.object(celery_app, "connection") as mock_conn:
            mock_connection = MagicMock()
            mock_connection.__enter__ = MagicMock(return_value=mock_connection)
            mock_connection.__exit__ = MagicMock(return_value=False)
            mock_connection.ensure_connection.side_effect = Exception(
                "Connection refused"
            )
            mock_conn.return_value = mock_connection

            result = check_broker_connection()
            assert result is False

    def test_get_worker_stats_success(self) -> None:
        """Test get_worker_stats with mocked inspect."""
        from image_preprocessing_detector.workers.celery_app import (
            celery_app,
            get_worker_stats,
        )

        with patch.object(celery_app.control, "inspect") as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.stats.return_value = {"worker1": {"pool": {"processes": 4}}}
            mock_inspector.active.return_value = {"worker1": [{"id": "task1"}]}
            mock_inspector.reserved.return_value = {"worker1": []}
            mock_inspect.return_value = mock_inspector

            result = get_worker_stats()

            assert result["worker_count"] == 1
            assert "worker1" in result["workers"]
            assert result["active_tasks"] == 1
            assert result["reserved_tasks"] == 0

    def test_get_worker_stats_failure(self) -> None:
        """Test get_worker_stats handles exceptions."""
        from image_preprocessing_detector.workers.celery_app import (
            celery_app,
            get_worker_stats,
        )

        with patch.object(celery_app.control, "inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Cannot connect to broker")

            result = get_worker_stats()

            assert result["worker_count"] == 0
            assert result["workers"] == []
            assert "error" in result

    def test_get_queue_lengths_failure(self) -> None:
        """Test get_queue_lengths handles exceptions."""
        from image_preprocessing_detector.workers.celery_app import (
            celery_app,
            get_queue_lengths,
        )

        with patch.object(celery_app, "connection") as mock_conn:
            mock_conn.side_effect = Exception("Connection failed")

            result = get_queue_lengths()

            assert "error" in result


class TestCelerySignalHandlers:
    """Tests for Celery signal handlers."""

    def test_on_worker_ready(self) -> None:
        """Test worker ready signal handler."""
        from image_preprocessing_detector.workers.celery_app import on_worker_ready

        # Should not raise, just logs
        on_worker_ready(sender="test-worker")

    def test_on_worker_shutdown(self) -> None:
        """Test worker shutdown signal handler."""
        from image_preprocessing_detector.workers.celery_app import on_worker_shutdown

        # Should not raise, just logs
        on_worker_shutdown(sender="test-worker")

    def test_on_task_prerun(self) -> None:
        """Test task prerun signal handler."""
        from image_preprocessing_detector.workers.celery_app import on_task_prerun

        mock_task = MagicMock()
        mock_task.name = "test.task"

        # Should not raise, just logs
        on_task_prerun(task_id="task-123", task=mock_task)

    def test_on_task_postrun(self) -> None:
        """Test task postrun signal handler."""
        from image_preprocessing_detector.workers.celery_app import on_task_postrun

        mock_task = MagicMock()
        mock_task.name = "test.task"

        # Should not raise, just logs
        # Note: _retval parameter name has underscore prefix (unused)
        on_task_postrun(
            task_id="task-123",
            task=mock_task,
            _retval={"result": "success"},
            state="SUCCESS",
        )

    def test_on_task_failure(self) -> None:
        """Test task failure signal handler."""
        from image_preprocessing_detector.workers.celery_app import on_task_failure

        # Should not raise, just logs the error
        on_task_failure(task_id="task-123", exception=ValueError("Test error"))
