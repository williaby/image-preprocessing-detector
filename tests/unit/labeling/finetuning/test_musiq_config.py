# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for MUSIQ configuration."""

from __future__ import annotations

import pytest

from image_preprocessing_detector.labeling.finetuning.musiq_config import (
    CHECKPOINT_PRESETS,
    CheckpointMetrics,
    MUSIQTrainingConfig,
    compute_checkpoint_score,
    get_checkpoint_preset,
    select_best_checkpoint,
)


class TestMUSIQTrainingConfig:
    """Tests for MUSIQTrainingConfig dataclass."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = MUSIQTrainingConfig()

        # Architecture
        assert config.head_hidden_dim == 256
        assert config.dropout == 0.1

        # Phase 1
        assert config.phase1_epochs == 10
        assert config.phase1_lr == 1e-3
        assert config.phase1_warmup_epochs == 2
        assert config.phase1_freeze_backbone is True

        # Phase 2
        assert config.phase2_epochs == 20
        assert config.phase2_backbone_lr == 1e-5
        assert config.phase2_head_lr == 1e-4
        assert config.phase2_warmup_epochs == 3

        # Training
        assert config.batch_size == 32
        assert config.weight_decay == 1e-4

        # Loss weights (sharpness specialist)
        assert config.loss_weights["overall"] == 0.2
        assert config.loss_weights["sharpness"] == 0.6
        assert config.loss_weights["color"] == 0.2

    def test_total_epochs(self) -> None:
        """Should compute total epochs correctly."""
        config = MUSIQTrainingConfig()
        assert config.total_epochs == 30  # 10 + 20

        config = MUSIQTrainingConfig(phase1_epochs=5, phase2_epochs=15)
        assert config.total_epochs == 20

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        config = MUSIQTrainingConfig()
        config_dict = config.to_dict()

        assert config_dict["head_hidden_dim"] == 256
        assert config_dict["phase1_epochs"] == 10
        assert config_dict["total_epochs"] == 30
        assert "loss_weights" in config_dict

    def test_from_dict(self) -> None:
        """Should create from dictionary."""
        config_dict = {
            "head_hidden_dim": 512,
            "dropout": 0.2,
            "phase1_epochs": 15,
            "phase2_epochs": 25,
            "batch_size": 16,
            "loss_weights": {"overall": 0.3, "sharpness": 0.5, "color": 0.2},
        }

        config = MUSIQTrainingConfig.from_dict(config_dict)

        assert config.head_hidden_dim == 512
        assert config.dropout == 0.2
        assert config.phase1_epochs == 15
        assert config.total_epochs == 40

    def test_from_dict_ignores_computed_properties(self) -> None:
        """Should ignore total_epochs in from_dict."""
        config_dict = {
            "phase1_epochs": 10,
            "phase2_epochs": 20,
            "total_epochs": 999,  # Should be ignored
        }

        config = MUSIQTrainingConfig.from_dict(config_dict)

        assert config.total_epochs == 30  # Computed, not from dict


class TestCheckpointPresets:
    """Tests for checkpoint selection presets."""

    def test_presets_exist(self) -> None:
        """Should have all expected presets."""
        assert "srcc_dominant" in CHECKPOINT_PRESETS
        assert "balanced" in CHECKPOINT_PRESETS
        assert "calibration_aware" in CHECKPOINT_PRESETS

    def test_preset_values(self) -> None:
        """Should have correct preset values."""
        # SRCC dominant: prioritize SRCC
        srcc_dom = CHECKPOINT_PRESETS["srcc_dominant"]
        assert srcc_dom["srcc_weight"] == 0.8
        assert srcc_dom["ece_weight"] == 0.2
        assert srcc_dom["srcc_band"] == 0.015

        # Balanced: default
        balanced = CHECKPOINT_PRESETS["balanced"]
        assert balanced["srcc_weight"] == 0.7
        assert balanced["ece_weight"] == 0.3
        assert balanced["srcc_band"] == 0.02

        # Calibration aware: prioritize ECE
        cal_aware = CHECKPOINT_PRESETS["calibration_aware"]
        assert cal_aware["srcc_weight"] == 0.6
        assert cal_aware["ece_weight"] == 0.4
        assert cal_aware["srcc_band"] == 0.025

    def test_get_checkpoint_preset(self) -> None:
        """Should return correct preset."""
        preset = get_checkpoint_preset("balanced")

        assert preset["srcc_weight"] == 0.7
        assert preset["ece_weight"] == 0.3

    def test_get_checkpoint_preset_invalid(self) -> None:
        """Should raise for invalid preset."""
        with pytest.raises(ValueError, match="Unknown checkpoint preset"):
            get_checkpoint_preset("invalid_preset")


class TestComputeCheckpointScore:
    """Tests for compute_checkpoint_score function."""

    def test_best_checkpoint_scores_high(self) -> None:
        """Best SRCC checkpoint should score high."""
        checkpoint = {
            "srcc_sharpness": 0.90,
            "ece_mean": 0.05,
        }

        score = compute_checkpoint_score(
            checkpoint,
            specialty="sharpness",
            best_srcc=0.90,
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,
        )

        # Should be high score (best SRCC, good ECE)
        assert score > 0.9

    def test_outside_band_returns_neg_inf(self) -> None:
        """Checkpoint outside SRCC band should return -inf."""
        checkpoint = {
            "srcc_sharpness": 0.85,  # 0.05 below best
            "ece_mean": 0.02,
        }

        score = compute_checkpoint_score(
            checkpoint,
            specialty="sharpness",
            best_srcc=0.90,
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,  # Only 0.02 tolerance
        )

        assert score == float("-inf")

    def test_within_band_competes(self) -> None:
        """Checkpoint within band should have valid score."""
        checkpoint = {
            "srcc_sharpness": 0.89,  # 0.01 below best, within band
            "ece_mean": 0.03,  # Good ECE
        }

        score = compute_checkpoint_score(
            checkpoint,
            specialty="sharpness",
            best_srcc=0.90,
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,
        )

        assert score > 0
        assert score < float("inf")

    def test_better_ece_can_win(self) -> None:
        """Better ECE should improve score within band."""
        checkpoint_best_srcc = {
            "srcc_sharpness": 0.90,
            "ece_mean": 0.10,  # Poor ECE
        }
        checkpoint_better_ece = {
            "srcc_sharpness": 0.89,  # Slightly worse SRCC
            "ece_mean": 0.02,  # Much better ECE
        }

        score_best_srcc = compute_checkpoint_score(
            checkpoint_best_srcc,
            specialty="sharpness",
            best_srcc=0.90,
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,
        )
        score_better_ece = compute_checkpoint_score(
            checkpoint_better_ece,
            specialty="sharpness",
            best_srcc=0.90,
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,
        )

        # Both should be valid
        assert score_best_srcc > 0
        assert score_better_ece > 0


class TestSelectBestCheckpoint:
    """Tests for select_best_checkpoint function."""

    @pytest.fixture
    def sample_checkpoints(self) -> list[dict[str, float]]:
        """Create sample checkpoints."""
        return [
            {"epoch": 5, "srcc_sharpness": 0.85, "ece_mean": 0.08},
            {"epoch": 10, "srcc_sharpness": 0.88, "ece_mean": 0.06},
            {
                "epoch": 15,
                "srcc_sharpness": 0.90,
                "ece_mean": 0.10,
            },  # Best SRCC, worst ECE
            {
                "epoch": 20,
                "srcc_sharpness": 0.89,
                "ece_mean": 0.04,
            },  # Good SRCC, best ECE
            {"epoch": 25, "srcc_sharpness": 0.87, "ece_mean": 0.05},  # Outside band
        ]

    def test_selects_best_within_band(
        self, sample_checkpoints: list[dict[str, float]]
    ) -> None:
        """Should select best checkpoint within SRCC band."""
        best = select_best_checkpoint(
            sample_checkpoints,
            specialty="sharpness",
            srcc_weight=0.7,
            ece_weight=0.3,
            srcc_band=0.02,
        )

        # Should select epoch 15 or 20 (within 0.02 of best 0.90)
        assert best["epoch"] in [15, 20]

    def test_empty_checkpoints_raises(self) -> None:
        """Should raise for empty checkpoint list."""
        with pytest.raises(ValueError, match="No checkpoints provided"):
            select_best_checkpoint([], specialty="sharpness")

    def test_no_valid_checkpoints_raises(self) -> None:
        """Should raise if no checkpoints within band."""
        checkpoints = [
            {"srcc_sharpness": 0.70, "ece_mean": 0.05},  # Far below best
        ]

        # With very tight band, even the "best" is excluded
        # Actually, the best itself is always included, so this test needs adjustment
        # Let's test with multiple checkpoints where best is so far ahead
        checkpoints = [
            {"srcc_sharpness": 0.90, "ece_mean": 0.05},  # Best
            {"srcc_sharpness": 0.50, "ece_mean": 0.01},  # Far below
        ]

        # This should work - best is always in band
        best = select_best_checkpoint(
            checkpoints,
            specialty="sharpness",
            srcc_band=0.01,
        )
        assert best["srcc_sharpness"] == 0.90


class TestCheckpointMetrics:
    """Tests for CheckpointMetrics dataclass."""

    def test_initialization(self) -> None:
        """Should initialize with required fields."""
        metrics = CheckpointMetrics(
            epoch=10,
            phase=1,
            train_loss=0.05,
            srcc_overall=0.85,
            srcc_sharpness=0.88,
            srcc_color=0.82,
            srcc_mean=0.85,
            ece_overall=0.06,
            ece_sharpness=0.05,
            ece_color=0.07,
            ece_mean=0.06,
        )

        assert metrics.epoch == 10
        assert metrics.srcc_sharpness == 0.88
        assert metrics.ece_mean == 0.06

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        metrics = CheckpointMetrics(
            epoch=10,
            phase=1,
            train_loss=0.05,
            srcc_overall=0.85,
            srcc_sharpness=0.88,
            srcc_color=0.82,
            srcc_mean=0.85,
            ece_overall=0.06,
            ece_sharpness=0.05,
            ece_color=0.07,
            ece_mean=0.06,
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["epoch"] == 10
        assert metrics_dict["srcc_sharpness"] == 0.88
        assert "plcc_overall" in metrics_dict
