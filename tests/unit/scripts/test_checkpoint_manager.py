# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/checkpoint_manager.py - Training checkpoint management.

These tests verify the checkpoint manager correctly:
- Saves and loads model checkpoints
- Tracks best models by validation loss
- Manages session timing for Colab limits
- Cleans up old checkpoints
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Skip tests if torch is not available
torch = pytest.importorskip("torch")

from checkpoint_manager import (
    CHECKPOINT_BEST_FILENAME,
    CHECKPOINT_LATEST_FILENAME,
    CheckpointManager,
)


class TestCheckpointManagerInit:
    """Tests for CheckpointManager initialization."""

    def test_creates_checkpoint_directory(self, tmp_path: Path) -> None:
        """Test that checkpoint directory is created on init."""
        checkpoint_dir = tmp_path / "checkpoints"

        _ = CheckpointManager(str(checkpoint_dir))

        assert checkpoint_dir.exists()
        assert checkpoint_dir.is_dir()

    def test_default_parameters(self, tmp_path: Path) -> None:
        """Test default parameter values."""
        manager = CheckpointManager(str(tmp_path))

        assert manager.save_interval_epochs == 5
        assert manager.save_interval_minutes == 30
        assert manager.max_session_hours == pytest.approx(11.5)
        assert manager.keep_last_n == 3

    def test_custom_parameters(self, tmp_path: Path) -> None:
        """Test custom parameter values."""
        manager = CheckpointManager(
            str(tmp_path),
            save_interval_epochs=10,
            save_interval_minutes=60,
            max_session_hours=10.0,
            keep_last_n=5,
        )

        assert manager.save_interval_epochs == 10
        assert manager.save_interval_minutes == 60
        assert manager.max_session_hours == pytest.approx(10.0)
        assert manager.keep_last_n == 5


class TestShouldSaveCheckpoint:
    """Tests for should_save_checkpoint method."""

    def test_save_at_epoch_interval(self, tmp_path: Path) -> None:
        """Test checkpoint trigger at epoch interval."""
        manager = CheckpointManager(str(tmp_path), save_interval_epochs=5)

        assert not manager.should_save_checkpoint(1)
        assert not manager.should_save_checkpoint(4)
        assert manager.should_save_checkpoint(5)
        assert manager.should_save_checkpoint(10)
        assert manager.should_save_checkpoint(15)

    def test_save_at_time_interval(self, tmp_path: Path) -> None:
        """Test checkpoint trigger at time interval."""
        manager = CheckpointManager(str(tmp_path), save_interval_minutes=1)

        # Initially should not save
        assert not manager.should_save_checkpoint(1)

        # Simulate time passing
        manager.last_checkpoint_time = time.time() - 120  # 2 minutes ago

        assert manager.should_save_checkpoint(1)


class TestShouldStopTraining:
    """Tests for should_stop_training method."""

    def test_not_stopping_early(self, tmp_path: Path) -> None:
        """Test training doesn't stop early."""
        manager = CheckpointManager(str(tmp_path), max_session_hours=12.0)

        assert not manager.should_stop_training()

    def test_stop_at_session_limit(self, tmp_path: Path) -> None:
        """Test training stops at session limit."""
        manager = CheckpointManager(str(tmp_path), max_session_hours=0.0)

        # With 0 hour limit, should stop immediately
        assert manager.should_stop_training()


class TestGetSessionStatus:
    """Tests for get_session_status method."""

    def test_session_status_structure(self, tmp_path: Path) -> None:
        """Test session status has expected structure."""
        manager = CheckpointManager(str(tmp_path))

        status = manager.get_session_status()

        assert "hours_elapsed" in status
        assert "hours_remaining" in status
        assert "minutes_since_last_checkpoint" in status
        assert "should_stop" in status

    def test_hours_elapsed_increases(self, tmp_path: Path) -> None:
        """Test hours elapsed increases over time."""
        manager = CheckpointManager(str(tmp_path))

        # Simulate time passing
        manager.session_start_time = time.time() - 3600  # 1 hour ago

        status = manager.get_session_status()

        assert status["hours_elapsed"] >= 1.0


class TestSaveCheckpoint:
    """Tests for save_checkpoint method."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        return torch.nn.Linear(10, 5)

    @pytest.fixture
    def simple_optimizer(self, simple_model):
        """Create a simple optimizer for testing."""
        return torch.optim.SGD(simple_model.parameters(), lr=0.01)

    def test_save_checkpoint_creates_files(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test that save_checkpoint creates checkpoint files."""
        manager = CheckpointManager(str(tmp_path))

        metrics = {"train_loss": 0.5, "val_loss": 0.4}

        with patch("builtins.print"):
            checkpoint_path = manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=5,
                metrics=metrics,
            )

        assert checkpoint_path.exists()
        assert (tmp_path / CHECKPOINT_LATEST_FILENAME).exists()

    def test_save_checkpoint_tracks_best_model(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test that best model is tracked by validation loss."""
        manager = CheckpointManager(str(tmp_path))

        with patch("builtins.print"):
            # Save first checkpoint with higher loss
            manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=1,
                metrics={"val_loss": 0.5},
            )

            assert manager.best_metric_value == pytest.approx(0.5)

            # Save second checkpoint with lower loss
            manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=2,
                metrics={"val_loss": 0.3},
            )

            assert manager.best_metric_value == pytest.approx(0.3)
            assert (tmp_path / CHECKPOINT_BEST_FILENAME).exists()

    def test_save_checkpoint_with_scheduler(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test saving checkpoint with learning rate scheduler."""
        manager = CheckpointManager(str(tmp_path))
        scheduler = torch.optim.lr_scheduler.StepLR(simple_optimizer, step_size=10)

        with patch("builtins.print"):
            checkpoint_path = manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=5,
                metrics={"val_loss": 0.4},
                scheduler=scheduler,
            )

        # Load checkpoint and verify scheduler state was saved
        checkpoint = torch.load(checkpoint_path)
        assert "scheduler_state_dict" in checkpoint

    def test_save_checkpoint_with_extra_state(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test saving checkpoint with extra state."""
        manager = CheckpointManager(str(tmp_path))

        extra = {"history": [0.5, 0.4, 0.3]}

        with patch("builtins.print"):
            checkpoint_path = manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=5,
                metrics={"val_loss": 0.4},
                extra_state=extra,
            )

        checkpoint = torch.load(checkpoint_path)
        assert checkpoint["extra_state"] == extra

    def test_save_checkpoint_creates_metadata_json(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test that JSON metadata file is created alongside checkpoint."""
        manager = CheckpointManager(str(tmp_path))

        with patch("builtins.print"):
            checkpoint_path = manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=5,
                metrics={"val_loss": 0.4},
            )

        # JSON file should have same base name
        json_path = checkpoint_path.with_suffix(".json")
        assert json_path.exists()

        with open(json_path) as f:
            metadata = json.load(f)

        assert metadata["epoch"] == 5
        assert metadata["metrics"]["val_loss"] == pytest.approx(0.4)


class TestLoadCheckpoint:
    """Tests for load_checkpoint method."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        return torch.nn.Linear(10, 5)

    @pytest.fixture
    def simple_optimizer(self, simple_model):
        """Create a simple optimizer for testing."""
        return torch.optim.SGD(simple_model.parameters(), lr=0.01)

    def test_load_latest_checkpoint(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test loading the latest checkpoint."""
        manager = CheckpointManager(str(tmp_path))

        with patch("builtins.print"):
            # Save a checkpoint
            manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=5,
                metrics={"val_loss": 0.4},
            )

        # Create new model instance
        new_model = torch.nn.Linear(10, 5)
        new_optimizer = torch.optim.SGD(new_model.parameters(), lr=0.01)

        with patch("builtins.print"):
            result = manager.load_checkpoint(model=new_model, optimizer=new_optimizer)

        assert result["resume_epoch"] == 6  # epoch + 1
        assert result["metrics"]["val_loss"] == pytest.approx(0.4)

    def test_load_specific_checkpoint(
        self, tmp_path: Path, simple_model, simple_optimizer
    ) -> None:
        """Test loading a specific checkpoint by path."""
        manager = CheckpointManager(str(tmp_path))

        with patch("builtins.print"):
            checkpoint_path = manager.save_checkpoint(
                model=simple_model,
                optimizer=simple_optimizer,
                epoch=10,
                metrics={"val_loss": 0.3},
            )

        new_model = torch.nn.Linear(10, 5)

        with patch("builtins.print"):
            result = manager.load_checkpoint(
                model=new_model, checkpoint_path=str(checkpoint_path)
            )

        assert result["resume_epoch"] == 11

    def test_load_nonexistent_checkpoint_raises(self, tmp_path: Path) -> None:
        """Test loading non-existent checkpoint raises error."""
        manager = CheckpointManager(str(tmp_path))
        model = torch.nn.Linear(10, 5)

        with pytest.raises(FileNotFoundError):
            manager.load_checkpoint(model=model)


class TestHasCheckpoint:
    """Tests for has_checkpoint method."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        return torch.nn.Linear(10, 5)

    def test_no_checkpoint_initially(self, tmp_path: Path) -> None:
        """Test has_checkpoint returns False when no checkpoint exists."""
        manager = CheckpointManager(str(tmp_path))

        assert not manager.has_checkpoint()

    def test_has_checkpoint_after_save(self, tmp_path: Path, simple_model) -> None:
        """Test has_checkpoint returns True after saving."""
        manager = CheckpointManager(str(tmp_path))
        optimizer = torch.optim.SGD(simple_model.parameters(), lr=0.01)

        with patch("builtins.print"):
            manager.save_checkpoint(
                model=simple_model,
                optimizer=optimizer,
                epoch=1,
                metrics={"val_loss": 0.5},
            )

        assert manager.has_checkpoint()


class TestGetBestCheckpointPath:
    """Tests for get_best_checkpoint_path method."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        return torch.nn.Linear(10, 5)

    def test_no_best_checkpoint_initially(self, tmp_path: Path) -> None:
        """Test returns None when no best checkpoint exists."""
        manager = CheckpointManager(str(tmp_path))

        assert manager.get_best_checkpoint_path() is None

    def test_best_checkpoint_after_save(self, tmp_path: Path, simple_model) -> None:
        """Test returns path after saving checkpoint with val_loss."""
        manager = CheckpointManager(str(tmp_path))
        optimizer = torch.optim.SGD(simple_model.parameters(), lr=0.01)

        with patch("builtins.print"):
            manager.save_checkpoint(
                model=simple_model,
                optimizer=optimizer,
                epoch=1,
                metrics={"val_loss": 0.5},
            )

        best_path = manager.get_best_checkpoint_path()

        assert best_path is not None
        assert best_path.exists()


class TestCleanupOldCheckpoints:
    """Tests for checkpoint cleanup functionality."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple model for testing."""
        return torch.nn.Linear(10, 5)

    def test_cleanup_keeps_recent_checkpoints(
        self, tmp_path: Path, simple_model
    ) -> None:
        """Test that recent checkpoints are kept."""
        manager = CheckpointManager(str(tmp_path), keep_last_n=2)
        optimizer = torch.optim.SGD(simple_model.parameters(), lr=0.01)

        with patch("builtins.print"):
            # Save 5 checkpoints
            for epoch in range(1, 6):
                manager.save_checkpoint(
                    model=simple_model,
                    optimizer=optimizer,
                    epoch=epoch,
                    metrics={"val_loss": 0.5 / epoch},
                )
                time.sleep(0.1)  # Ensure different timestamps

        # Count checkpoint files (excluding latest and best)
        checkpoint_files = [
            f
            for f in tmp_path.glob("checkpoint_epoch*.pt")
            if "latest" not in f.name and "best" not in f.name
        ]

        assert len(checkpoint_files) <= 2


class TestPrintSessionWarning:
    """Tests for print_session_warning method."""

    def test_no_warning_early_in_session(self, tmp_path: Path) -> None:
        """Test no warning is printed early in session."""
        manager = CheckpointManager(str(tmp_path), max_session_hours=12.0)

        with patch("builtins.print") as mock_print:
            manager.print_session_warning()

        # Should not print any warning messages
        warning_calls = [
            call
            for call in mock_print.call_args_list
            if "WARNING" in str(call) or "remaining" in str(call).lower()
        ]
        assert len(warning_calls) == 0

    def test_warning_near_session_limit(self, tmp_path: Path) -> None:
        """Test warning is printed near session limit."""
        manager = CheckpointManager(str(tmp_path), max_session_hours=1.0)

        # Simulate being near session limit
        manager.session_start_time = time.time() - (0.5 * 3600)  # 0.5 hours ago

        with patch("builtins.print") as mock_print:
            manager.print_session_warning()

        # Should print time remaining message
        print_calls = "".join(str(call) for call in mock_print.call_args_list)
        assert "remaining" in print_calls.lower() or len(mock_print.call_args_list) > 0
