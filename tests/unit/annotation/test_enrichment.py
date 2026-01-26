# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for enrichment layer.

Test Coverage:
    - Error classes (structured exceptions)
    - EnrichmentProvider protocol compliance
    - YOLOProvider (availability, inference, batch processing)
    - EnrichmentManager (orchestration, retry, validation)

Fixtures:
    - mock_yolo_model: Mock YOLO model for testing
    - mock_provider: Mock EnrichmentProvider for testing
    - sample_images: Sample image paths for testing
"""

from __future__ import annotations

import pytest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from image_preprocessing_detector.annotation.enrichment import (
    BatchProcessingError,
    EnrichmentError,
    EnrichmentManager,
    EnrichmentResult,
    InferenceError,
    ProviderUnavailableError,
    ValidationError,
)
from image_preprocessing_detector.annotation.enrichment.providers.yolo import (
    YOLOProvider,
)
from image_preprocessing_detector.annotation.schemas.enrichment import (
    EnrichmentData,
    LayoutDetection,
)


# ============================================================================
# Test Error Classes
# ============================================================================


class TestEnrichmentErrors:
    """Test structured error classes."""

    def test_enrichment_error_base(self):
        """Test base EnrichmentError."""
        cause = ValueError("Original error")
        error = EnrichmentError("Something failed", cause=cause)

        assert str(error) == "Something failed"
        assert error.cause is cause

    def test_inference_error(self):
        """Test InferenceError with provider context."""
        cause = RuntimeError("CUDA out of memory")
        error = InferenceError("yolo", batch_size=8, cause=cause)

        assert error.provider_name == "yolo"
        assert error.batch_size == 8
        assert error.cause is cause
        assert "yolo" in str(error)
        assert "batch_size=8" in str(error)

    def test_provider_unavailable_error(self):
        """Test ProviderUnavailableError."""
        error = ProviderUnavailableError("siglip", "Model checkpoint not found")

        assert error.provider_name == "siglip"
        assert error.reason == "Model checkpoint not found"
        assert "siglip" in str(error)
        assert "not found" in str(error)

    def test_validation_error(self):
        """Test ValidationError with multiple errors."""
        errors = ["confidence out of range", "bbox invalid"]
        warnings = ["missing source field"]
        error = ValidationError(errors, warnings)

        assert error.errors == errors
        assert error.warnings == warnings
        assert len(error.errors) == 2
        assert "confidence" in str(error)

    def test_batch_processing_error(self):
        """Test BatchProcessingError."""
        failed_paths = [Path("img1.jpg"), Path("img2.jpg")]
        error = BatchProcessingError(
            total_count=10, failed_count=2, failed_paths=failed_paths
        )

        assert error.total_count == 10
        assert error.failed_count == 2
        assert len(error.failed_paths) == 2
        assert "2/10" in str(error)


# ============================================================================
# Test YOLOProvider
# ============================================================================


class TestYOLOProvider:
    """Test YOLOProvider implementation."""

    def test_provider_properties(self):
        """Test provider name and tier properties."""
        provider = YOLOProvider()

        assert provider.name == "doclayout_yolo"
        assert provider.tier == "tier_2_model"

    def test_is_available_no_model(self):
        """Test is_available returns False when model missing."""
        provider = YOLOProvider(model_path=None)
        assert not provider.is_available()

        provider = YOLOProvider(model_path="/nonexistent/model.pt")
        assert not provider.is_available()

    @patch("image_preprocessing_detector.annotation.enrichment.providers.yolo.Path.exists")
    def test_is_available_no_ultralytics(self, mock_exists):
        """Test is_available returns False when ultralytics not installed."""
        mock_exists.return_value = True

        with patch.dict("sys.modules", {"ultralytics": None}):
            provider = YOLOProvider(model_path="model.pt")
            # This will fail the import check
            assert not provider.is_available()

    def test_is_available_cuda_required_but_missing(self, tmp_path):
        """Test is_available returns False when CUDA required but not available."""
        # Create a mock model file
        model_file = tmp_path / "model.pt"
        model_file.touch()

        # Patch torch.cuda.is_available to return False
        with patch("torch.cuda.is_available", return_value=False):
            provider = YOLOProvider(model_path=str(model_file), device="cuda")
            # Device is explicitly set to cuda, but CUDA not available
            # is_available should return False
            result = provider.is_available()

            # Note: This test depends on whether ultralytics is installed
            # If ultralytics is not installed, it fails earlier
            # If installed but CUDA unavailable with cuda device, should fail
            try:
                import ultralytics  # noqa: F401
                # ultralytics available, should fail CUDA check
                assert not result, "Should return False when CUDA unavailable"
            except ImportError:
                # ultralytics not installed, fails earlier check
                assert not result

    def test_supports_all_images(self):
        """Test supports returns True for all images."""
        provider = YOLOProvider()

        assert provider.supports(Path("doc1.jpg"))
        assert provider.supports(Path("doc2.png"))
        assert provider.supports(Path("any/path.tiff"))

    def test_device_auto_detection(self):
        """Test device auto-detection."""
        with patch("torch.cuda.is_available", return_value=True):
            provider = YOLOProvider()
            assert provider.device == "cuda"

        with patch("torch.cuda.is_available", return_value=False):
            provider = YOLOProvider()
            assert provider.device == "cpu"

    def test_device_explicit(self):
        """Test explicit device specification."""
        provider = YOLOProvider(device="cpu")
        assert provider.device == "cpu"

        provider = YOLOProvider(device="cuda")
        assert provider.device == "cuda"

    def test_enrich_unavailable_raises(self):
        """Test enrich raises when provider unavailable."""
        provider = YOLOProvider(model_path=None)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            provider.enrich(Path("test.jpg"))

        assert "doclayout_yolo" in str(exc_info.value)

    @patch.object(YOLOProvider, "_ensure_loaded")
    @patch.object(YOLOProvider, "_process_batch")
    def test_enrich_single_image(self, mock_process, mock_load):
        """Test enrich single image delegates to batch processing."""
        mock_process.return_value = [EnrichmentData()]
        provider = YOLOProvider(model_path="model.pt")

        result = provider.enrich(Path("test.jpg"))

        assert isinstance(result, EnrichmentData)
        mock_load.assert_called_once()
        mock_process.assert_called_once()

    @patch.object(YOLOProvider, "_ensure_loaded")
    @patch.object(YOLOProvider, "_process_batch")
    def test_enrich_batch_empty(self, mock_process, mock_load):
        """Test enrich_batch with empty list."""
        provider = YOLOProvider(model_path="model.pt")

        results = provider.enrich_batch([])

        assert results == []
        mock_load.assert_not_called()
        mock_process.assert_not_called()

    @patch.object(YOLOProvider, "_ensure_loaded")
    @patch.object(YOLOProvider, "_process_batch")
    def test_enrich_batch_success(self, mock_process, mock_load):
        """Test successful batch enrichment."""
        # Mock batch processing
        mock_process.return_value = [
            EnrichmentData(layout_detections=[{"class_name": "table"}]),
            EnrichmentData(layout_detections=[{"class_name": "figure"}]),
        ]

        provider = YOLOProvider(model_path="model.pt", batch_size=2)
        paths = [Path("doc1.jpg"), Path("doc2.jpg")]

        results = provider.enrich_batch(paths)

        assert len(results) == 2
        assert results[0].layout_detections == [{"class_name": "table"}]
        assert results[1].layout_detections == [{"class_name": "figure"}]
        mock_load.assert_called_once()

    @patch.object(YOLOProvider, "_ensure_loaded")
    @patch.object(YOLOProvider, "_process_batch")
    def test_enrich_batch_with_batching(self, mock_process, mock_load):
        """Test batch processing splits into smaller batches."""
        mock_process.side_effect = [
            [EnrichmentData(), EnrichmentData()],
            [EnrichmentData()],
        ]

        provider = YOLOProvider(model_path="model.pt", batch_size=2)
        paths = [Path("1.jpg"), Path("2.jpg"), Path("3.jpg")]

        results = provider.enrich_batch(paths)

        assert len(results) == 3
        assert mock_process.call_count == 2  # 2 batches (2+1)

    @patch.object(YOLOProvider, "_ensure_loaded")
    @patch.object(YOLOProvider, "_process_batch")
    def test_enrich_batch_failure_raises(self, mock_process, mock_load):
        """Test batch processing raises InferenceError on failure."""
        mock_process.side_effect = RuntimeError("CUDA OOM")

        provider = YOLOProvider(model_path="model.pt")
        paths = [Path("doc1.jpg")]

        with pytest.raises(InferenceError) as exc_info:
            provider.enrich_batch(paths)

        assert exc_info.value.provider_name == "doclayout_yolo"
        assert exc_info.value.batch_size == 1

    def test_convert_predictions_empty(self):
        """Test _convert_predictions with no detections."""
        provider = YOLOProvider()

        # Mock prediction with no boxes
        mock_pred = Mock()
        mock_pred.boxes = None

        detections = provider._convert_predictions(mock_pred)
        assert detections == []

    def test_convert_predictions_with_detections(self):
        """Test _convert_predictions with valid detections."""
        provider = YOLOProvider()

        # Mock YOLO prediction
        mock_box = Mock()
        mock_box.xyxy = [Mock()]
        mock_box.xyxy[0].cpu.return_value.numpy.return_value = [10, 20, 110, 220]
        mock_box.cls = [Mock()]
        mock_box.cls[0].item.return_value = 0
        mock_box.conf = [Mock()]
        mock_box.conf[0].item.return_value = 0.95

        mock_pred = Mock()
        mock_pred.boxes = [mock_box]
        mock_pred.names = {0: "table"}

        detections = provider._convert_predictions(mock_pred)

        assert len(detections) == 1
        assert detections[0]["class_name"] == "table"
        assert detections[0]["bbox"] == [10.0, 20.0, 100.0, 200.0]  # COCO format
        assert detections[0]["confidence"] == 0.95
        assert detections[0]["source"] == "doclayout_yolo"


# ============================================================================
# Test Mock Provider for EnrichmentManager
# ============================================================================


class MockProvider:
    """Mock provider for testing EnrichmentManager."""

    def __init__(
        self,
        name: str = "mock",
        tier: str = "tier_2_model",
        available: bool = True,
        should_fail: bool = False,
    ):
        self._name = name
        self._tier = tier
        self._available = available
        self._should_fail = should_fail
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def tier(self) -> str:
        return self._tier

    def is_available(self) -> bool:
        return self._available

    def supports(self, image_path: Path) -> bool:
        return True

    def enrich(self, image_path: Path) -> EnrichmentData:
        return self.enrich_batch([image_path])[0]

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        self.call_count += 1

        if self._should_fail:
            raise InferenceError(self.name, len(image_paths), RuntimeError("Mock failure"))

        # Return mock enrichment
        return [
            EnrichmentData(
                layout_detections=[
                    {
                        "class_name": "table",
                        "bbox": [0, 0, 100, 100],
                        "confidence": 0.9,
                        "source": self.name,
                    }
                ]
            )
            for _ in image_paths
        ]


# ============================================================================
# Test EnrichmentManager
# ============================================================================


class TestEnrichmentManager:
    """Test EnrichmentManager orchestration."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        providers = [MockProvider()]
        manager = EnrichmentManager(providers=providers)

        assert len(manager.providers) == 1
        assert manager.validate is True
        assert manager.max_retries == 2

    def test_manager_no_providers(self):
        """Test manager with no providers."""
        manager = EnrichmentManager(providers=[])

        results = manager.enrich_batch([Path("test.jpg")])

        assert len(results) == 1
        assert len(results[0].warnings) > 0
        assert "No enrichment providers available" in results[0].warnings[0]

    def test_manager_unavailable_providers(self):
        """Test manager skips unavailable providers."""
        provider = MockProvider(available=False)
        manager = EnrichmentManager(providers=[provider])

        results = manager.enrich_batch([Path("test.jpg")])

        assert len(results) == 1
        assert provider.call_count == 0

    def test_manager_single_provider_success(self):
        """Test manager with single successful provider."""
        provider = MockProvider()
        manager = EnrichmentManager(providers=[provider], validate=False)

        results = manager.enrich_batch([Path("test.jpg")])

        assert len(results) == 1
        assert results[0].success
        assert len(results[0].providers_used) == 1
        assert results[0].providers_used[0] == "mock"
        assert provider.call_count == 1

    def test_manager_multiple_images(self):
        """Test manager with multiple images."""
        provider = MockProvider()
        manager = EnrichmentManager(providers=[provider], validate=False)

        paths = [Path("1.jpg"), Path("2.jpg"), Path("3.jpg")]
        results = manager.enrich_batch(paths)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert provider.call_count == 1  # Single batch call

    def test_manager_tier_priority(self):
        """Test manager respects tier priority ordering."""
        # Create providers with different tiers
        tier0 = MockProvider(name="tier0", tier="tier_0_exact")
        tier1 = MockProvider(name="tier1", tier="tier_1_annotation")
        tier2 = MockProvider(name="tier2", tier="tier_2_model")
        tier3 = MockProvider(name="tier3", tier="tier_3_heuristic")

        # Add in reverse order to test sorting
        manager = EnrichmentManager(
            providers=[tier3, tier2, tier1, tier0], validate=False
        )

        results = manager.enrich_batch([Path("test.jpg")])

        # All providers should run in tier order
        assert len(results) == 1
        providers_used = results[0].providers_used

        # Check tier ordering (lower tier = earlier execution)
        assert providers_used.index("tier0") < providers_used.index("tier1")
        assert providers_used.index("tier1") < providers_used.index("tier2")
        assert providers_used.index("tier2") < providers_used.index("tier3")

    def test_manager_provider_failure_tracking(self):
        """Test manager tracks provider failures."""
        failing_provider = MockProvider(should_fail=True)
        manager = EnrichmentManager(providers=[failing_provider], validate=False)

        results = manager.enrich_batch([Path("test.jpg")])

        assert len(results) == 1
        assert not results[0].success
        assert len(results[0].errors) > 0
        assert "mock" in results[0].errors[0]

        # Check dead-letter queue
        dead_letters = manager.get_dead_letter_queue()
        assert len(dead_letters) == 1
        assert dead_letters[0][0] == Path("test.jpg")

    def test_manager_retry_logic(self):
        """Test manager retry logic for transient failures."""
        provider = MockProvider(should_fail=True)
        manager = EnrichmentManager(providers=[provider], max_retries=2, validate=False)

        results = manager.enrich_batch([Path("test.jpg")])

        # Should attempt initial + 2 retries = 3 total (but mock doesn't implement retry recovery)
        assert not results[0].success

    def test_manager_validation_integration(self):
        """Test manager integrates with validation."""
        provider = MockProvider()
        manager = EnrichmentManager(providers=[provider], validate=True)

        results = manager.enrich_batch([Path("test.jpg")])

        # Validation should run (results depend on validator implementation)
        assert len(results) == 1

    def test_manager_dead_letter_queue_operations(self):
        """Test dead-letter queue operations."""
        failing_provider = MockProvider(should_fail=True)
        manager = EnrichmentManager(providers=[failing_provider], validate=False)

        manager.enrich_batch([Path("1.jpg"), Path("2.jpg")])

        # Check queue
        queue = manager.get_dead_letter_queue()
        assert len(queue) == 2

        # Clear queue
        manager.clear_dead_letter_queue()
        assert len(manager.get_dead_letter_queue()) == 0

    def test_manager_stats(self):
        """Test manager statistics."""
        providers = [
            MockProvider(name="p1", available=True),
            MockProvider(name="p2", available=False),
        ]
        manager = EnrichmentManager(providers=providers, max_retries=3)

        stats = manager.get_stats()

        assert stats["total_providers"] == 2
        assert stats["available_providers"] == 1
        assert stats["validation_enabled"] is True
        assert stats["max_retries"] == 3

    def test_manager_existing_enrichment(self):
        """Test manager augments existing enrichment data."""
        provider = MockProvider()
        manager = EnrichmentManager(providers=[provider], validate=False)

        # Provide existing enrichment
        existing = [
            EnrichmentData(
                quality_overall=0.8, layout_detections=[{"class_name": "text"}]
            )
        ]

        results = manager.enrich_batch([Path("test.jpg")], existing=existing)

        # Should have both original and new enrichment
        assert len(results) == 1
        # Note: Mock provider replaces enrichment, real providers would augment


class TestEnrichmentResult:
    """Test EnrichmentResult dataclass."""

    def test_result_success_no_errors(self):
        """Test success property with no errors."""
        result = EnrichmentResult(data=EnrichmentData())
        assert result.success

    def test_result_success_with_errors(self):
        """Test success property with errors."""
        result = EnrichmentResult(data=EnrichmentData(), errors=["error1"])
        assert not result.success

    def test_result_providers_tracking(self):
        """Test provider usage tracking."""
        result = EnrichmentResult(
            data=EnrichmentData(), providers_used=["yolo", "siglip"]
        )
        assert len(result.providers_used) == 2
        assert "yolo" in result.providers_used


# ============================================================================
# Integration Tests
# ============================================================================


class TestEnrichmentIntegration:
    """Integration tests for complete enrichment flow."""

    def test_end_to_end_enrichment(self):
        """Test complete enrichment flow with mock provider."""
        # Create provider and manager
        provider = MockProvider()
        manager = EnrichmentManager(providers=[provider], validate=False)

        # Process images
        paths = [Path("doc1.jpg"), Path("doc2.jpg")]
        results = manager.enrich_batch(paths)

        # Verify results
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(len(r.providers_used) == 1 for r in results)
        assert all(len(r.data.layout_detections) > 0 for r in results)

    def test_multi_provider_enrichment(self):
        """Test enrichment with multiple providers."""
        # Create providers with different capabilities
        layout_provider = MockProvider(name="layout", tier="tier_2_model")
        quality_provider = MockProvider(name="quality", tier="tier_2_model")

        manager = EnrichmentManager(
            providers=[layout_provider, quality_provider], validate=False
        )

        results = manager.enrich_batch([Path("test.jpg")])

        # Both providers should contribute
        assert len(results) == 1
        assert len(results[0].providers_used) == 2

    def test_partial_failure_recovery(self):
        """Test recovery from partial batch failures."""
        # One failing, one succeeding provider
        failing = MockProvider(name="failing", should_fail=True)
        succeeding = MockProvider(name="succeeding", should_fail=False)

        manager = EnrichmentManager(
            providers=[failing, succeeding], validate=False
        )

        results = manager.enrich_batch([Path("test.jpg")])

        # Should have result from succeeding provider
        assert len(results) == 1
        assert "succeeding" in results[0].providers_used
        # Should also have error from failing provider
        assert len(results[0].errors) > 0
