"""Tests for Defect 1/2 label parsing in modal/train_siglip2_multitask.py.

The training module imports ``modal`` at import time, so it is loaded with a
stub ``modal`` module; only the pure parsing helpers are exercised.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "modal" / "train_siglip2_multitask.py"
)


@pytest.fixture(scope="module")
def trainer() -> ModuleType:
    """Import the trainer with ``modal`` stubbed out."""
    saved = sys.modules.get("modal")
    sys.modules["modal"] = MagicMock()
    try:
        spec = importlib.util.spec_from_file_location(
            "_siglip2_multitask", _MODULE_PATH
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = (
            module  # dataclasses resolve annotations via sys.modules
        )
        spec.loader.exec_module(module)
        return module
    finally:
        if saved is None:
            sys.modules.pop("modal", None)
        else:
            sys.modules["modal"] = saved


@pytest.mark.unit
class TestParseCodeLabel:
    """``has_code`` selects the class; ``code_confidence`` only masks (enrichment rows)."""

    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            (
                {"has_code": False, "code_confidence": 1.0},
                0,
            ),  # confident NEGATIVE stays 0
            ({"has_code": False, "code_confidence": 0.8}, 0),
            ({"has_code": True, "code_confidence": 0.8}, 1),
            ({"has_code": True, "code_confidence": 1.0}, 1),
            ({"has_code": True}, 1),
            ({"has_code": False}, 0),
        ],
    )
    def test_has_code_selects_class(
        self, trainer: ModuleType, entry: dict[str, object], expected: int
    ) -> None:
        assert trainer._parse_code_label(entry) == expected

    @pytest.mark.parametrize(
        "confidence", [0.3, 0.5, 0.69, -1.0, 1.5, float("nan"), "x"]
    )
    def test_low_or_invalid_confidence_masks_a_has_code_row(
        self, trainer: ModuleType, confidence: object
    ) -> None:
        assert (
            trainer._parse_code_label({"has_code": True, "code_confidence": confidence})
            is None
        )
        assert (
            trainer._parse_code_label(
                {"has_code": False, "code_confidence": confidence}
            )
            is None
        )

    @pytest.mark.parametrize("has_code", [1, 0, "true", None])
    def test_non_bool_has_code_falls_back_to_legacy_probability(
        self, trainer: ModuleType, has_code: object
    ) -> None:
        assert (
            trainer._parse_code_label({"has_code": has_code, "code_confidence": 0.9})
            == 1
        )
        assert (
            trainer._parse_code_label({"has_code": has_code, "code_confidence": 0.1})
            == 0
        )

    @pytest.mark.parametrize(
        ("confidence", "expected"),
        [(1.0, 1), (0.999, 1), (0.7, 1), (0.0, 0), (0.1, 0), (0.3, 0), ("1", 1)],
    )
    def test_legacy_probability_form(
        self, trainer: ModuleType, confidence: object, expected: int
    ) -> None:
        assert trainer._parse_code_label({"code_confidence": confidence}) == expected

    @pytest.mark.parametrize("confidence", [0.31, 0.5, 0.69])
    def test_legacy_ambiguous_band_is_masked_not_truncated(
        self, trainer: ModuleType, confidence: float
    ) -> None:
        assert trainer._parse_code_label({"code_confidence": confidence}) is None

    @pytest.mark.parametrize(
        "confidence", [-1.0, 1.5, float("nan"), float("inf"), None, "x"]
    )
    def test_legacy_invalid_is_masked(
        self, trainer: ModuleType, confidence: object
    ) -> None:
        assert trainer._parse_code_label({"code_confidence": confidence}) is None


@pytest.mark.unit
class TestParseHwScore:
    @pytest.mark.parametrize(
        ("raw", "expected"), [(0.0, 0.0), (0.4, 0.4), (1.0, 1.0), ("0.25", 0.25)]
    )
    def test_valid_scores(
        self, trainer: ModuleType, raw: object, expected: float
    ) -> None:
        assert trainer._parse_hw_score(raw) == expected

    def test_zero_is_a_real_label_not_na(self, trainer: ModuleType) -> None:
        """Defect 1: 0.0 (no handwriting) must stay a valid label."""
        assert trainer._parse_hw_score(0.0) == 0.0

    @pytest.mark.parametrize("raw", [-1.0, -0.5, 1.2, float("nan"), None, "n/a"])
    def test_na_and_invalid_are_masked(self, trainer: ModuleType, raw: object) -> None:
        assert trainer._parse_hw_score(raw) is None
