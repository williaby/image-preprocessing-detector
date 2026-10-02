"""Tests for doc3d backward-map warping severity and SSIM calibration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from image_preprocessing_detector.schema_utils.warping_severity import (
    Calibration,
    apply_calibration,
    fit_calibration,
    homography_residual_score,
    load_backward_map,
    normalise_backward_map,
)

SIZE = 128


def _grid() -> np.ndarray:
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    return np.stack([xs, ys], axis=-1)


def _perspective(grid: np.ndarray) -> np.ndarray:
    homography = np.array([[1.1, 0.1, 5.0], [-0.05, 0.95, 3.0], [1e-4, 5e-5, 1.0]])
    pts = np.concatenate([grid, np.ones((*grid.shape[:2], 1))], axis=-1) @ homography.T
    return pts[..., :2] / pts[..., 2:3]


def _curled(amplitude: float) -> np.ndarray:
    grid = _grid()
    out = grid.copy()
    out[..., 1] += amplitude * np.sin(grid[..., 0] / SIZE * np.pi * 2)
    return out


@pytest.mark.unit
class TestHomographyResidualScore:
    def test_identity_is_zero(self) -> None:
        score = homography_residual_score(_grid())
        assert score is not None
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_pure_perspective_is_not_warping(self) -> None:
        score = homography_residual_score(_perspective(_grid()))
        assert score is not None
        assert score < 1e-6

    def test_curl_scores_positive_and_monotone(self) -> None:
        scores = [homography_residual_score(_curled(a)) for a in (2.0, 6.0, 12.0)]
        assert all(s is not None for s in scores)
        assert 0.0 < scores[0] < scores[1] < scores[2]  # type: ignore[operator]

    def test_scale_invariant(self) -> None:
        base = homography_residual_score(_curled(6.0))
        scaled = homography_residual_score(_curled(6.0) * 3.0)
        assert base is not None
        assert scaled == pytest.approx(base, rel=1e-6)

    def test_channels_first_accepted(self) -> None:
        bm = _curled(6.0)
        a = homography_residual_score(bm)
        b = homography_residual_score(np.transpose(bm, (2, 0, 1)))
        assert a == pytest.approx(b)

    def test_nan_regions_tolerated(self) -> None:
        bm = _curled(6.0)
        bm[:20] = np.nan
        assert homography_residual_score(bm) is not None

    @pytest.mark.parametrize(
        "bm",
        [
            np.zeros((4, 4, 2)),
            np.zeros((SIZE, SIZE)),
            np.full((SIZE, SIZE, 2), np.nan),
            np.zeros((SIZE, SIZE, 2)),
        ],
    )
    def test_unusable_returns_none(self, bm: np.ndarray) -> None:
        assert homography_residual_score(bm) is None

    def test_normalise_rejects_bad_shapes(self) -> None:
        assert normalise_backward_map(np.zeros((SIZE, SIZE, 3))) is None


@pytest.mark.unit
class TestCalibration:
    def test_isotonic_output_is_monotone(self) -> None:
        rng = np.random.default_rng(0)
        raw = np.sort(rng.uniform(0, 0.1, 200))
        reference = np.clip(raw * 5 + rng.normal(0, 0.05, 200), 0, 1)
        cal = fit_calibration(raw, reference)
        assert np.all(np.diff(cal.ys) >= -1e-12)

    def test_recovers_known_mapping(self) -> None:
        raw = np.linspace(0.0, 0.1, 100)
        cal = fit_calibration(raw, raw * 8.0)
        assert apply_calibration(0.05, cal) == pytest.approx(0.4, abs=1e-6)

    def test_clamped_outside_range(self) -> None:
        raw = np.linspace(0.01, 0.1, 50)
        cal = fit_calibration(raw, np.linspace(0.1, 0.9, 50))
        assert apply_calibration(0.0, cal) == pytest.approx(0.1)
        assert apply_calibration(5.0, cal) == pytest.approx(0.9)

    def test_output_in_unit_interval(self) -> None:
        raw = np.linspace(0, 1, 20)
        cal = fit_calibration(raw, np.linspace(0.0, 2.0, 20))
        assert 0.0 <= apply_calibration(0.9, cal) <= 1.0

    def test_too_few_pairs_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 10"):
            fit_calibration(np.arange(5.0), np.arange(5.0))

    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same shape"):
            fit_calibration(np.arange(10.0), np.arange(11.0))

    def test_nonfinite_pairs_dropped(self) -> None:
        raw = np.linspace(0, 0.1, 30)
        ref = raw * 5
        raw[0] = np.nan
        assert len(fit_calibration(raw, ref).xs) == 29

    def test_roundtrip_dict(self) -> None:
        cal = fit_calibration(np.linspace(0, 0.1, 20), np.linspace(0, 0.5, 20))
        assert Calibration.from_dict(cal.to_dict()) == cal


@pytest.mark.unit
class TestLoadBackwardMap:
    def test_npy_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "bm.npy"
        np.save(path, _grid())
        loaded = load_backward_map(path)
        assert loaded is not None
        assert loaded.shape == (SIZE, SIZE, 2)

    def test_mat_roundtrip(self, tmp_path: Path) -> None:
        from scipy.io import savemat

        path = tmp_path / "bm.mat"
        savemat(str(path), {"bm": _grid()})
        loaded = load_backward_map(path)
        assert loaded is not None
        assert loaded.shape == (SIZE, SIZE, 2)

    def test_missing_and_unknown(self, tmp_path: Path) -> None:
        assert load_backward_map(tmp_path / "nope.npy") is None
        (tmp_path / "x.txt").write_text("x")
        assert load_backward_map(tmp_path / "x.txt") is None
