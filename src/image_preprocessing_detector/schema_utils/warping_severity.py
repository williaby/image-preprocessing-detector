"""Warping severity from doc3d backward maps, calibrated to the SSIM scale.

doc3d (MIT) ships a backward map per image but, in our local copy, no depth
maps. A backward map ``bm`` sends each pixel of the flattened page to its
location in the warped image. A *flat* page photographed from an arbitrary
viewpoint is related to the flattened page by a homography, so warping
(non-planar curl, folds) is exactly the part of ``bm`` a homography cannot
explain.

``raw_score`` is the RMS residual of a least-squares homography fit,
normalised by the extent of the map, so it is unit- and resolution-free.

``raw_score`` is NOT on the same scale as the ``1 - SSIM`` labels already
written for warpdoc by ``scripts/label_warping_severity.py``. Mixing the two
would teach the warping head two definitions of severity, so
:func:`fit_calibration` learns a monotone (isotonic) mapping from raw score to
``1 - SSIM`` on a calibration sample, and :func:`apply_calibration` applies it.

Decision record: docs/planning/MASTER_PROJECT_PLAN.md (Tier 0, warping severity).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

_MIN_VALID_POINTS = 100
_FIT_GRID_STRIDE = 4


@dataclass(frozen=True)
class Calibration:
    """Monotone non-decreasing map from raw score to severity in [0, 1]."""

    xs: tuple[float, ...]
    ys: tuple[float, ...]

    def to_dict(self) -> dict[str, list[float]]:
        """Serialise for JSON storage."""
        return {"xs": list(self.xs), "ys": list(self.ys)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Calibration:
        """Load from :meth:`to_dict` output."""
        return cls(xs=tuple(data["xs"]), ys=tuple(data["ys"]))


def normalise_backward_map(bm: NDArray[np.float64]) -> NDArray[np.float64] | None:
    """Return the map as ``(H, W, 2)`` float64, or None if it is unusable.

    Accepts ``(H, W, 2)`` or channels-first ``(2, H, W)``.
    """
    arr = np.asarray(bm, dtype=np.float64)
    if arr.ndim != 3:
        return None
    if arr.shape[-1] != 2 and arr.shape[0] == 2:
        arr = np.transpose(arr, (1, 2, 0))
    if arr.shape[-1] != 2 or arr.shape[0] < 8 or arr.shape[1] < 8:
        return None
    return arr


def homography_residual_score(bm: NDArray[np.float64]) -> float | None:
    """Scale-free non-planarity of a backward map (0 = perfectly planar).

    Returns None if the map is malformed or has too few finite points.
    """
    arr = normalise_backward_map(bm)
    if arr is None:
        return None

    height, width, _ = arr.shape
    ys, xs = np.mgrid[0:height:_FIT_GRID_STRIDE, 0:width:_FIT_GRID_STRIDE]
    src = np.stack([xs / max(width - 1, 1), ys / max(height - 1, 1)], axis=-1)
    dst = arr[::_FIT_GRID_STRIDE, ::_FIT_GRID_STRIDE]

    all_src = src.reshape(-1, 2)
    all_dst = dst.reshape(-1, 2)
    valid = np.isfinite(all_dst).all(axis=1)
    if int(valid.sum()) < _MIN_VALID_POINTS:
        return None
    src_pts, dst_pts = all_src[valid], all_dst[valid]

    extent = np.ptp(dst_pts, axis=0)
    diagonal = float(np.hypot(extent[0], extent[1]))
    if diagonal <= 0.0:
        return None

    homography, _ = cv2.findHomography(src_pts, dst_pts, method=0)
    if homography is None:
        return None

    projected = cv2.perspectiveTransform(src_pts.reshape(-1, 1, 2), homography)
    residual = dst_pts - projected.reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return rms / diagonal


def _pool_adjacent_violators(values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Isotonic (non-decreasing) least-squares fit of ``values``."""
    blocks: list[list[float]] = []  # [sum, count]
    for value in values:
        blocks.append([float(value), 1.0])
        while (
            len(blocks) > 1
            and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]
        ):
            total, count = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += count
    return np.concatenate([np.full(int(c), s / c) for s, c in blocks])


def fit_calibration(
    raw: NDArray[np.float64], reference: NDArray[np.float64]
) -> Calibration:
    """Fit a monotone map from raw scores to reference (``1 - SSIM``) severity.

    Args:
        raw: Raw scores from :func:`homography_residual_score`.
        reference: Reference severities in [0, 1], same length.

    Raises:
        ValueError: If inputs are mismatched or have fewer than 10 usable pairs.
    """
    raw = np.asarray(raw, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if raw.shape != reference.shape:
        msg = "raw and reference must have the same shape"
        raise ValueError(msg)
    keep = np.isfinite(raw) & np.isfinite(reference)
    if int(keep.sum()) < 10:
        msg = "need at least 10 finite (raw, reference) pairs to calibrate"
        raise ValueError(msg)

    order = np.argsort(raw[keep], kind="stable")
    xs = raw[keep][order]
    ys = _pool_adjacent_violators(reference[keep][order])
    # np.interp needs strictly increasing xs; tied raw scores collapse to one point
    # carrying the mean of their isotonic values (group means stay non-decreasing).
    unique_xs, inverse, counts = np.unique(xs, return_inverse=True, return_counts=True)
    unique_ys = np.bincount(inverse, weights=ys) / counts
    return Calibration(
        xs=tuple(unique_xs.tolist()),
        ys=tuple(np.clip(unique_ys, 0.0, 1.0).tolist()),
    )


def apply_calibration(raw: float, calibration: Calibration) -> float:
    """Map a raw score to calibrated severity in [0, 1] (clamped at the ends)."""
    value = float(np.interp(raw, calibration.xs, calibration.ys))
    return float(np.clip(value, 0.0, 1.0))


def load_backward_map(path: Path) -> NDArray[np.float64] | None:
    """Load a doc3d backward map from ``.npy`` or ``.mat``.

    The on-disk format of the local ``bm_*.zip`` files has not been verified
    against real data (the dataset docs say NPY; the upstream release used
    MATLAB files). Returns None if the file cannot be read.
    """
    try:
        if path.suffix == ".npy":
            return np.asarray(np.load(path), dtype=np.float64)
        if path.suffix == ".mat":
            from scipy.io import loadmat

            mat: dict[str, Any] = loadmat(str(path))
            bm = mat.get("bm")
            return None if bm is None else np.asarray(bm, dtype=np.float64)
    except (OSError, ValueError, NotImplementedError):
        # NotImplementedError: scipy cannot read v7.3 (HDF5) .mat files.
        return None
    return None
