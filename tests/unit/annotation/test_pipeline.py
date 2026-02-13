# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for annotation pipeline.

Test Coverage:
    - Checkpointing (CheckpointInfo, CheckpointManager)
    - Progress tracking (ProgressTracker, ProgressState)
    - Pipeline stages (ParsedSample, EnrichedSample)
    - AnnotationPipeline integration
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.integrity.checkpointing import (
    CheckpointInfo,
    CheckpointManager,
)
from image_preprocessing_detector.annotation.schemas.enrichment import EnrichmentData
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels
from image_preprocessing_detector.annotation.workflow.pipeline import (
    AnnotationPipeline,
    EnrichedSample,
    ParsedSample,
    PipelineResult,
    PipelineStats,
    _parse_single_image,
)
from image_preprocessing_detector.annotation.workflow.progress import (
    ProgressState,
    ProgressTracker,
    format_eta,
)

# ============================================================================
# CheckpointInfo Tests
# ============================================================================


class TestCheckpointInfo:
    """Test CheckpointInfo dataclass."""

    def test_create_checkpoint_info(self):
        """Test creating CheckpointInfo."""
        info = CheckpointInfo(
            dataset_name="test-dataset",
            processed_count=100,
            last_path="train/img100.png",
            last_hash="abc123",
        )

        assert info.dataset_name == "test-dataset"
        assert info.processed_count == 100
        assert info.last_path == "train/img100.png"
        assert info.last_hash == "abc123"
        assert info.version == 1
        assert info.timestamp is not None

    def test_to_dict(self):
        """Test converting to dictionary."""
        info = CheckpointInfo(
            dataset_name="test",
            processed_count=50,
            last_path="img.png",
            last_hash="hash123",
        )

        d = info.to_dict()

        assert d["dataset_name"] == "test"
        assert d["processed_count"] == 50
        assert d["last_path"] == "img.png"
        assert d["last_hash"] == "hash123"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "dataset_name": "test",
            "processed_count": 75,
            "last_path": "img.png",
            "last_hash": "hash456",
            "timestamp": "2025-01-26T12:00:00",
            "version": 1,
        }

        info = CheckpointInfo.from_dict(data)

        assert info.dataset_name == "test"
        assert info.processed_count == 75
        assert info.timestamp == "2025-01-26T12:00:00"


# ============================================================================
# CheckpointManager Tests
# ============================================================================


class TestCheckpointManager:
    """Test CheckpointManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a checkpoint manager with temp directory."""
        return CheckpointManager(checkpoint_dir=tmp_path)

    def test_init_creates_directory(self, tmp_path):
        """Test manager creates checkpoint directory."""
        checkpoint_dir = tmp_path / "checkpoints"
        assert not checkpoint_dir.exists()

        manager = CheckpointManager(checkpoint_dir=checkpoint_dir)

        assert checkpoint_dir.exists()

    def test_get_resume_point_no_checkpoint(self, manager):
        """Test get_resume_point returns None when no checkpoint."""
        result = manager.get_resume_point("nonexistent-dataset")
        assert result is None

    def test_save_and_get_checkpoint(self, manager):
        """Test saving and retrieving checkpoint."""
        manager.save_checkpoint(
            dataset_name="test-dataset",
            processed_count=100,
            last_path="train/img100.png",
            last_hash="abc123",
        )

        resume = manager.get_resume_point("test-dataset")

        assert resume is not None
        assert resume.dataset_name == "test-dataset"
        assert resume.processed_count == 100
        assert resume.last_path == "train/img100.png"
        assert resume.last_hash == "abc123"

    def test_clear_checkpoint(self, manager):
        """Test clearing a checkpoint."""
        manager.save_checkpoint(
            dataset_name="test-dataset",
            processed_count=100,
            last_path="test.png",
            last_hash="hash",
        )

        assert manager.get_resume_point("test-dataset") is not None

        result = manager.clear_checkpoint("test-dataset")

        assert result is True
        assert manager.get_resume_point("test-dataset") is None

    def test_clear_nonexistent_checkpoint(self, manager):
        """Test clearing nonexistent checkpoint returns False."""
        result = manager.clear_checkpoint("nonexistent")
        assert result is False

    def test_list_checkpoints(self, manager):
        """Test listing all checkpoints."""
        manager.save_checkpoint("dataset-a", 10, "a.png", "hash-a")
        manager.save_checkpoint("dataset-b", 20, "b.png", "hash-b")

        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 2
        names = {c.dataset_name for c in checkpoints}
        assert names == {"dataset-a", "dataset-b"}

    def test_get_stats(self, manager):
        """Test getting checkpoint stats."""
        manager.save_checkpoint("dataset-a", 10, "a.png", "hash-a")

        stats = manager.get_stats()

        assert stats["total_checkpoints"] == 1
        assert "dataset-a" in stats["datasets"]

    def test_checkpoint_path_sanitization(self, manager):
        """Test dataset names with special chars are sanitized."""
        manager.save_checkpoint("dataset/with/slashes", 10, "a.png", "hash")

        resume = manager.get_resume_point("dataset/with/slashes")
        assert resume is not None

    def test_invalid_checkpoint_file(self, manager, tmp_path):
        """Test handling of invalid checkpoint JSON."""
        # Write invalid JSON
        checkpoint_path = tmp_path / "bad.checkpoint.json"
        checkpoint_path.write_text("invalid json")

        # Should return None and not crash
        result = manager.get_resume_point("bad")
        assert result is None


# ============================================================================
# Progress Tracker Tests
# ============================================================================


class TestProgressState:
    """Test ProgressState dataclass."""

    def test_create_state(self):
        """Test creating ProgressState."""
        state = ProgressState(dataset_name="test", total=100)

        assert state.dataset_name == "test"
        assert state.total == 100
        assert state.current == 0
        assert state.errors == 0

    def test_elapsed_seconds(self):
        """Test elapsed time calculation."""
        state = ProgressState(dataset_name="test", total=100)
        time.sleep(0.1)

        elapsed = state.elapsed_seconds
        assert elapsed >= 0.1

    def test_rate_calculation(self):
        """Test rate calculation."""
        state = ProgressState(dataset_name="test", total=100)
        state.current = 50
        # Force a known elapsed time by setting start_time
        state.start_time = time.perf_counter() - 1.0  # 1 second ago

        rate = state.rate
        assert rate == pytest.approx(50.0, rel=0.1)

    def test_percent_complete(self):
        """Test percent complete calculation."""
        state = ProgressState(dataset_name="test", total=100)
        state.current = 50

        assert state.percent_complete == 50.0

    def test_eta_seconds(self):
        """Test ETA calculation."""
        state = ProgressState(dataset_name="test", total=100)
        state.current = 50
        state.start_time = time.perf_counter() - 1.0  # 1 second ago

        eta = state.eta_seconds
        assert eta is not None
        assert eta == pytest.approx(1.0, rel=0.2)


class TestProgressTracker:
    """Test ProgressTracker."""

    def test_start_tracking(self):
        """Test starting progress tracking."""
        tracker = ProgressTracker()
        tracker.start("test-dataset", total=100)

        state = tracker.get_state()
        assert state is not None
        assert state.dataset_name == "test-dataset"
        assert state.total == 100

    def test_update_progress(self):
        """Test updating progress."""
        tracker = ProgressTracker()
        tracker.start("test", total=100)

        tracker.update(10)
        state = tracker.get_state()

        assert state.current == 10

    def test_update_with_errors(self):
        """Test updating with error count."""
        tracker = ProgressTracker()
        tracker.start("test", total=100)

        tracker.update(10, errors=2)
        state = tracker.get_state()

        assert state.current == 10
        assert state.errors == 2

    def test_finish(self):
        """Test finishing tracking."""
        tracker = ProgressTracker()
        tracker.start("test", total=100)
        tracker.update(100)

        final_state = tracker.finish()

        assert final_state is not None
        assert final_state.current == 100

    def test_callback_invocation(self):
        """Test callback is invoked on updates."""
        callback_calls = []

        def callback(current, total, rate, dataset_name):
            callback_calls.append((current, total, dataset_name))

        tracker = ProgressTracker(callback=callback, update_interval=0)
        tracker.start("test", total=100)
        tracker.update(50)

        assert len(callback_calls) >= 1
        assert callback_calls[-1][0] == 50

    def test_get_summary(self):
        """Test getting summary statistics."""
        tracker = ProgressTracker()
        tracker.start("dataset-a", total=100)
        tracker.update(50)
        tracker.finish()

        tracker.start("dataset-b", total=200)
        tracker.update(100)

        summary = tracker.get_summary()

        assert summary["datasets_count"] == 2
        assert summary["total_items"] == 300
        assert summary["total_processed"] == 150


class TestFormatEta:
    """Test format_eta helper."""

    def test_format_eta_none(self):
        """Test formatting None ETA."""
        assert format_eta(None) == "unknown"

    def test_format_eta_seconds(self):
        """Test formatting small ETA."""
        assert format_eta(30) == "30s"

    def test_format_eta_minutes(self):
        """Test formatting minutes."""
        assert format_eta(150) == "2m 30s"

    def test_format_eta_hours(self):
        """Test formatting hours."""
        assert format_eta(7230) == "2h 0m"


# ============================================================================
# Pipeline Data Classes Tests
# ============================================================================


class TestParsedSample:
    """Test ParsedSample dataclass."""

    def test_create_parsed_sample(self, tmp_path):
        """Test creating ParsedSample."""
        image_path = tmp_path / "test.png"
        sample = ParsedSample(
            image_path=image_path,
            relative_path="test.png",
            file_hash="abc123",
            original_labels=OriginalLabels(),
            dataset_name="test-dataset",
        )

        assert sample.image_path == image_path
        assert sample.relative_path == "test.png"
        assert sample.file_hash == "abc123"
        assert sample.dataset_name == "test-dataset"


class TestEnrichedSample:
    """Test EnrichedSample dataclass."""

    def test_create_enriched_sample(self, tmp_path):
        """Test creating EnrichedSample."""
        parsed = ParsedSample(
            image_path=tmp_path / "test.png",
            relative_path="test.png",
            file_hash="abc123",
            original_labels=OriginalLabels(),
            dataset_name="test",
        )

        enriched = EnrichedSample(
            parsed=parsed,
            enrichment=EnrichmentData(),
        )

        assert enriched.parsed is parsed
        assert isinstance(enriched.enrichment, EnrichmentData)
        assert enriched.enrichment_errors == []


class TestPipelineStats:
    """Test PipelineStats dataclass."""

    def test_default_stats(self):
        """Test default PipelineStats values."""
        stats = PipelineStats()

        assert stats.total_images == 0
        assert stats.success_count == 0
        assert stats.error_count == 0
        assert stats.cpu_time_seconds == 0.0


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_pipeline_result_properties(self, tmp_path):
        """Test PipelineResult computed properties."""
        # Create real sample objects instead of MagicMock
        sample1 = EnrichedSample(
            parsed=ParsedSample(
                image_path=tmp_path / "img1.png",
                relative_path="img1.png",
                file_hash="hash1",
                original_labels=OriginalLabels(),
                dataset_name="test",
            ),
            enrichment=EnrichmentData(),
        )
        sample2 = EnrichedSample(
            parsed=ParsedSample(
                image_path=tmp_path / "img2.png",
                relative_path="img2.png",
                file_hash="hash2",
                original_labels=OriginalLabels(),
                dataset_name="test",
            ),
            enrichment=EnrichmentData(),
        )

        result = PipelineResult(
            dataset_name="test",
            samples=[sample1, sample2],
            errors=[(Path("a.png"), "error")],
        )

        assert result.success_count == 2
        assert result.error_count == 1


# ============================================================================
# Worker Function Tests
# ============================================================================


class TestParseSingleImage:
    """Test _parse_single_image worker function."""

    def test_parse_single_image_success(self, tmp_path):
        """Test successful image parsing."""
        # Create test image
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"test image content")

        result = _parse_single_image(
            image_path=image_path,
            dataset_path=tmp_path,
            dataset_name="test-dataset",
            _parser_config={},
        )

        assert isinstance(result, ParsedSample)
        assert result.image_path == image_path
        assert result.relative_path == "test.png"
        assert result.file_hash is not None
        assert len(result.file_hash) == 64  # SHA256 hex

    def test_parse_single_image_missing_file(self, tmp_path):
        """Test handling of missing file."""
        image_path = tmp_path / "nonexistent.png"

        result = _parse_single_image(
            image_path=image_path,
            dataset_path=tmp_path,
            dataset_name="test",
            _parser_config={},
        )

        # Should return (path, error) tuple
        assert isinstance(result, tuple)
        assert result[0] == image_path


# ============================================================================
# AnnotationPipeline Tests
# ============================================================================


class TestAnnotationPipeline:
    """Test AnnotationPipeline class.

    Refactored to use real components where possible (Phase 6.2).
    Uses fixtures from conftest.py:
    - sample_settings: Real AnnotationSettings with tmp_path
    - parser_registry_with_mock: Real ParserRegistry with MockParser
    - real_enrichment_manager: Real EnrichmentManager with SimulatedInferenceProvider
    - mock_checkpoint_manager: Real CheckpointManager with tmp_path
    """

    def test_pipeline_creation(
        self,
        sample_settings,
        parser_registry_with_mock,
        real_enrichment_manager,
        mock_checkpoint_manager,
    ):
        """Test creating pipeline with real components."""
        pipeline = AnnotationPipeline(
            settings=sample_settings,
            parser_registry=parser_registry_with_mock,
            enrichment_manager=real_enrichment_manager,
            checkpoint_manager=mock_checkpoint_manager,
        )

        assert pipeline.settings is sample_settings
        assert pipeline.parsers is parser_registry_with_mock
        assert pipeline.enrichment is real_enrichment_manager
        assert pipeline.checkpoints is mock_checkpoint_manager

    def test_batches_utility(self):
        """Test _batches static method."""
        items = list(range(10))
        batches = list(AnnotationPipeline._batches(items, 3))

        assert len(batches) == 4
        assert batches[0] == [0, 1, 2]
        assert batches[-1] == [9]

    def test_find_resume_index(
        self,
        sample_settings,
        parser_registry_with_mock,
        real_enrichment_manager,
        mock_checkpoint_manager,
    ):
        """Test finding resume index."""
        pipeline = AnnotationPipeline(
            settings=sample_settings,
            parser_registry=parser_registry_with_mock,
            enrichment_manager=real_enrichment_manager,
            checkpoint_manager=mock_checkpoint_manager,
        )

        paths = [Path("/data/img1.png"), Path("/data/img2.png"), Path("/data/img3.png")]

        # Should find img2.png and return next index
        idx = pipeline._find_resume_index(paths, "img2.png")
        assert idx == 2

        # Should return 0 if not found
        idx = pipeline._find_resume_index(paths, "nonexistent.png")
        assert idx == 0

    def test_process_dataset_no_parser(
        self,
        sample_settings,
        real_enrichment_manager,
        mock_checkpoint_manager,
    ):
        """Test processing with no parser returns error."""
        from image_preprocessing_detector.annotation.parsers.registry import (
            ParserRegistry,
        )

        # Empty registry - no parsers registered
        empty_registry = ParserRegistry()

        pipeline = AnnotationPipeline(
            settings=sample_settings,
            parser_registry=empty_registry,
            enrichment_manager=real_enrichment_manager,
            checkpoint_manager=mock_checkpoint_manager,
        )

        result = pipeline.process_dataset(
            dataset_name="unknown-dataset",
            image_paths=[Path("/data/img.png")],
            dataset_config={},
        )

        assert len(result.errors) == 1
        assert "No parser" in result.errors[0][1]


# ============================================================================
# Integration Tests
# ============================================================================


class TestPipelineIntegration:
    """Integration tests for complete pipeline flow.

    Refactored to use real components (Phase 6.2).
    """

    def test_end_to_end_with_real_files(
        self,
        tmp_path,
        sample_rgb_bytes,
        real_enrichment_manager,
        mock_parser_factory,
    ):
        """Test complete pipeline with actual files and real components."""
        from image_preprocessing_detector.annotation.config.settings import (
            AnnotationSettings,
        )
        from image_preprocessing_detector.annotation.parsers.registry import (
            ParserRegistry,
        )

        # Create test images (real PNG bytes)
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        for i in range(3):
            img_path = images_dir / f"img{i}.png"
            img_path.write_bytes(sample_rgb_bytes)

        # Use real settings with test-appropriate values
        metadata_root = tmp_path / "metadata"
        metadata_root.mkdir()

        settings = AnnotationSettings(
            e_drive_root=tmp_path,
            metadata_root=metadata_root,
            checkpoint_dir=tmp_path / "checkpoints",
            workers=1,
            batch_size=2,
            checkpoint_interval=1,
            yolo_model_path=None,
            siglip_model_path=None,
        )

        # Use real parser registry with mock parser configured for test-dataset
        test_parser = mock_parser_factory("test-dataset")
        parser_registry = ParserRegistry()
        parser_registry.register(test_parser)

        # Use real checkpoint manager
        checkpoint_manager = CheckpointManager(checkpoint_dir=settings.checkpoint_dir)

        # Create and run pipeline with real components
        pipeline = AnnotationPipeline(
            settings=settings,
            parser_registry=parser_registry,
            enrichment_manager=real_enrichment_manager,
            checkpoint_manager=checkpoint_manager,
        )

        image_paths = list(images_dir.glob("*.png"))

        result = pipeline.process_dataset(
            dataset_name="test-dataset",
            image_paths=image_paths,
            dataset_config={"path": str(tmp_path)},
        )

        # Verify results
        assert result.dataset_name == "test-dataset"
        assert result.success_count == 3
        assert result.error_count == 0
        assert result.stats.total_images == 3

        # Verify test parser was actually called
        assert len(test_parser.parse_calls) == 3

        # Verify checkpoint manager was used (checkpoint may be cleared on success)
        # The checkpoint dir should exist and have been initialized
        assert checkpoint_manager.checkpoint_dir.exists()
