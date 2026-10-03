"""Tests for weights-only checkpoint loading with numpy scalar allowlisting.

Covers the regression where ``torch.load(weights_only=True)`` rejected the
repo's own trainer checkpoints (numpy scalar metrics) and verifies that the
narrow allowlist does not reopen the pickle code-execution hole.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from image_preprocessing_detector.utils.safe_checkpoint import (
    load_checkpoint_weights_only,
    numpy_scalar_safe_globals,
)

torch = pytest.importorskip("torch")
scipy_stats = pytest.importorskip("scipy.stats")


def _trainer_style_checkpoint() -> dict[str, Any]:
    """Build a checkpoint shaped like modal/train_siglip2_multitask.py output."""
    srcc = scipy_stats.spearmanr([1, 2, 3, 4, 5], [1, 3, 2, 5, 4])[0]
    assert type(srcc) is np.float64
    return {
        "epoch": 7,
        "phase": 2,
        "model_state_dict": {"backbone.weight": torch.arange(6.0).reshape(2, 3)},
        "config": {"lr": 1e-4, "model_variant": "base"},
        "metrics": {
            "val_loss": 0.25,
            "iqa_srcc_overall": srcc,
            "script_accuracy": np.float32(0.91),
            "n_samples": np.int64(128),
            "converged": np.bool_(True),
        },
        "composite_score": srcc,
    }


class _CodeExecutionPayload:
    """Pickle payload that would create a sentinel file if it were executed."""

    def __init__(self, sentinel: Path) -> None:
        self.sentinel = sentinel

    def __reduce__(self) -> tuple[Any, tuple[Any, ...]]:
        return (Path.write_text, (self.sentinel, "pwned"))


def test_plain_weights_only_load_rejects_numpy_scalar_metrics(tmp_path: Path) -> None:
    """Reproduce the regression: stock weights_only=True rejects the checkpoint."""
    path = tmp_path / "best_model.pt"
    torch.save(_trainer_style_checkpoint(), path)

    with pytest.raises(Exception, match=r"Unsupported global|numpy"):
        torch.load(path, map_location="cpu", weights_only=True)


def test_trainer_checkpoint_round_trips(tmp_path: Path) -> None:
    """A trainer-style checkpoint with numpy scalar metrics loads intact."""
    expected = _trainer_style_checkpoint()
    path = tmp_path / "best_model.pt"
    torch.save(expected, path)

    loaded = load_checkpoint_weights_only(path, map_location="cpu")

    assert torch.equal(
        loaded["model_state_dict"]["backbone.weight"],
        expected["model_state_dict"]["backbone.weight"],
    )
    assert loaded["epoch"] == 7
    assert loaded["metrics"]["iqa_srcc_overall"] == pytest.approx(
        expected["metrics"]["iqa_srcc_overall"],
    )
    assert loaded["metrics"]["script_accuracy"] == pytest.approx(0.91, abs=1e-6)
    assert loaded["metrics"]["n_samples"] == 128
    assert bool(loaded["metrics"]["converged"]) is True
    assert loaded["composite_score"] == pytest.approx(expected["composite_score"])


def test_plain_python_checkpoint_round_trips(tmp_path: Path) -> None:
    """Checkpoints with only tensors and Python primitives still load."""
    path = tmp_path / "plain.pt"
    torch.save({"model_state_dict": {"w": torch.ones(2)}, "epoch": 1}, path)

    loaded = load_checkpoint_weights_only(path)

    assert loaded["epoch"] == 1
    assert torch.equal(loaded["model_state_dict"]["w"], torch.ones(2))


def test_malicious_pickle_payload_is_rejected(tmp_path: Path) -> None:
    """An arbitrary-code pickle payload must not execute and must raise."""
    sentinel = tmp_path / "pwned.txt"
    path = tmp_path / "evil.pt"
    torch.save(
        {"model_state_dict": {}, "payload": _CodeExecutionPayload(sentinel)}, path
    )

    with pytest.raises(Exception, match=r"Unsupported global|Can only build"):
        load_checkpoint_weights_only(path)

    assert not sentinel.exists()


def test_numpy_object_array_is_rejected(tmp_path: Path) -> None:
    """The allowlist covers numeric scalars only, not arrays or object dtypes."""
    path = tmp_path / "array.pt"
    torch.save({"metrics": np.array([object(), object()], dtype=object)}, path)

    with pytest.raises(Exception, match=r"Unsupported global|Can only build"):
        load_checkpoint_weights_only(path)


def test_allowlist_is_not_left_registered_globally(tmp_path: Path) -> None:
    """The numpy globals apply only inside the loader, not process-wide."""
    path = tmp_path / "best_model.pt"
    torch.save(_trainer_style_checkpoint(), path)
    load_checkpoint_weights_only(path)

    with pytest.raises(Exception, match=r"Unsupported global|numpy"):
        torch.load(path, map_location="cpu", weights_only=True)


def test_allowlist_contains_no_object_dtype() -> None:
    """Object-dtype support must never be allowlisted."""
    names = {
        getattr(item, "__name__", repr(item)) for item in numpy_scalar_safe_globals()
    }
    assert "ObjectDType" not in names
    assert "dtype" in names
