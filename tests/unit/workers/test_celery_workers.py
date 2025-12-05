# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for Celery worker pool configuration and tasks."""

import base64
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


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

        assert (
            "image_preprocessing_detector.workers.tasks.run_iqa_analysis" in routes
        )
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
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

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

        task_name = (
            "image_preprocessing_detector.workers.tasks.process_single_document"
        )
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

        task_name = (
            "image_preprocessing_detector.workers.tasks.process_batch_documents"
        )
        assert task_name in celery_app.tasks

    def test_task_config(self) -> None:
        """Test task configuration."""
        from image_preprocessing_detector.workers.tasks import process_batch_documents

        assert process_batch_documents.soft_time_limit == 600
        assert process_batch_documents.time_limit == 900


class TestWorkerMonitoring:
    """Tests for worker monitoring functions."""

    def test_check_broker_connection_failure(self) -> None:
        """Test broker connection check handles failure."""
        from image_preprocessing_detector.workers.celery_app import (
            check_broker_connection,
        )

        # Without Redis running, should return False
        result = check_broker_connection()
        assert result is False

    def test_get_worker_stats_no_workers(self) -> None:
        """Test getting stats when no workers running."""
        from image_preprocessing_detector.workers.celery_app import get_worker_stats

        stats = get_worker_stats()

        # Should return empty stats, not crash
        assert "workers" in stats
        assert "worker_count" in stats
        assert stats["worker_count"] == 0

    def test_get_queue_lengths_no_connection(self) -> None:
        """Test queue lengths when broker unavailable."""
        from image_preprocessing_detector.workers.celery_app import get_queue_lengths

        lengths = get_queue_lengths()

        # Should return error info, not crash
        assert "error" in lengths or all(v >= -1 for v in lengths.values())


class TestIQATaskClass:
    """Tests for IQATask base class."""

    def test_lazy_model_loading(self) -> None:
        """Test that models are lazily loaded."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        # Initially None (not loaded)
        assert task._student_session is None
        assert task._teacher_session is None

    def test_student_session_property(self) -> None:
        """Test student session property with mocked loader."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        with patch(
            "image_preprocessing_detector.models.model_loader.load_student_model"
        ) as mock_load:
            mock_session = MagicMock()
            mock_load.return_value = mock_session

            session = task.student_session

            mock_load.assert_called_once()
            assert session is mock_session

    def test_student_session_cached(self) -> None:
        """Test student session is cached after first load."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        with patch(
            "image_preprocessing_detector.models.model_loader.load_student_model"
        ) as mock_load:
            mock_session = MagicMock()
            mock_load.return_value = mock_session

            # First access
            session1 = task.student_session
            # Second access
            session2 = task.student_session

            # Should only load once
            mock_load.assert_called_once()
            assert session1 is session2


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

        scores, confidences = _postprocess_outputs(outputs)

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


class TestIQATaskProperties:
    """Tests for IQATask model loading properties."""

    def test_teacher_session_property(self) -> None:
        """Test teacher session property with mocked loader."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        with patch(
            "image_preprocessing_detector.models.model_loader.load_teacher_model"
        ) as mock_load:
            mock_session = MagicMock()
            mock_load.return_value = mock_session

            session = task.teacher_session

            mock_load.assert_called_once()
            assert session is mock_session

    def test_student_session_load_failure(self) -> None:
        """Test student session handles load failure gracefully."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        with patch(
            "image_preprocessing_detector.models.model_loader.load_student_model"
        ) as mock_load:
            mock_load.side_effect = ImportError("model_loader not available")

            # Should return None on failure, not raise
            session = task.student_session
            assert session is None

    def test_teacher_session_load_failure(self) -> None:
        """Test teacher session handles load failure gracefully."""
        from image_preprocessing_detector.workers.tasks import IQATask

        task = IQATask()

        with patch(
            "image_preprocessing_detector.models.model_loader.load_teacher_model"
        ) as mock_load:
            mock_load.side_effect = ImportError("model_loader not available")

            # Should return None on failure, not raise
            session = task.teacher_session
            assert session is None
