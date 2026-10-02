"""Label doc3d warping severity from backward maps, calibrated to warpdoc SSIM.

Three steps (decision record: docs/planning/MASTER_PROJECT_PLAN.md, Tier 0):

1. ``score``     raw homography-residual score per backward map -> JSONL
2. ``calibrate`` unwarp a sample with its own backward map, compute
                 ``1 - SSIM(warped, unwarped)`` (same definition as
                 ``label_warping_severity.py`` for warpdoc), fit a monotone
                 raw -> severity map -> JSON
3. ``apply``     raw JSONL + calibration JSON -> final severity JSONL

Backward maps are read directly from the ``bm_*.zip`` files (no 105 GB
extraction). Records are keyed by file stem; the image with the same stem under
``--image-dir`` is the warped image.

UNVERIFIED against real data (run ``score --spot-check`` first and inspect):
  * member format (``.npy`` or ``.mat``) and that the array key is ``bm``;
  * coordinate units (auto-detected: values within [-1, 1] are treated as
    normalised, otherwise as pixels);
  * stem equality between a backward map and its image.

Example:
    uv run python scripts/label_doc3d_warping_severity.py score \\
        --bm-dir /mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/doc3d \\
        --out results/doc3d_warping/raw.jsonl --spot-check 200
"""

from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import click
import cv2
import numpy as np
from numpy.typing import NDArray
from skimage.metrics import structural_similarity as ssim

from image_preprocessing_detector.schema_utils.warping_severity import (
    Calibration,
    apply_calibration,
    fit_calibration,
    homography_residual_score,
    load_backward_map,
)

logger = logging.getLogger(__name__)

_MAP_SUFFIXES = (".npy", ".mat")


def iter_backward_maps(bm_dir: Path) -> Iterator[tuple[str, NDArray[np.float64]]]:
    """Yield ``(stem, array)`` for every backward map in ``bm_*.zip`` or loose files."""
    for zip_path in sorted(bm_dir.glob("bm_*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                suffix = Path(name).suffix
                if suffix not in _MAP_SUFFIXES:
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / Path(name).name
                    target.write_bytes(archive.read(name))
                    arr = load_backward_map(target)
                if arr is not None:
                    yield Path(name).stem, arr
    for path in sorted(bm_dir.rglob("*")):
        in_bm_dir = any(
            part.startswith("bm") for part in path.relative_to(bm_dir).parts[:-1]
        )
        if path.suffix in _MAP_SUFFIXES and in_bm_dir:
            arr = load_backward_map(path)
            if arr is not None:
                yield path.stem, arr


def unwarp(
    image_bgr: NDArray[np.uint8], bm: NDArray[np.float64]
) -> NDArray[np.uint8] | None:
    """Flatten ``image_bgr`` using its backward map; None if the map is unusable."""
    if bm.ndim != 3:
        return None
    if bm.shape[-1] != 2 and bm.shape[0] == 2:
        bm = np.transpose(bm, (1, 2, 0))
    if bm.shape[-1] != 2:
        return None
    height, width = image_bgr.shape[:2]
    finite = bm[np.isfinite(bm)]
    if finite.size == 0:
        return None
    if finite.min() >= -1.0 and finite.max() <= 1.0:  # normalised to [-1, 1]
        map_x = (bm[..., 0] + 1.0) / 2.0 * (width - 1)
        map_y = (bm[..., 1] + 1.0) / 2.0 * (height - 1)
    else:  # pixel coordinates
        map_x, map_y = bm[..., 0], bm[..., 1]
    return cv2.remap(
        image_bgr,
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def ssim_severity(warped_bgr: NDArray[np.uint8], flat_bgr: NDArray[np.uint8]) -> float:
    """``1 - SSIM`` on grayscale, identical to the warpdoc labeller's definition."""
    if warped_bgr.shape[:2] != flat_bgr.shape[:2]:
        h, w = warped_bgr.shape[:2]
        flat_bgr = cv2.resize(flat_bgr, (w, h), interpolation=cv2.INTER_AREA)
    a = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(flat_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.clip(1.0 - float(ssim(a, b, data_range=255)), 0.0, 1.0))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@click.group()
def cli() -> None:
    """doc3d warping severity labelling."""


@cli.command()
@click.option("--bm-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option(
    "--spot-check", type=int, default=0, help="Score only N maps and print stats."
)
def score(bm_dir: Path, out: Path, spot_check: int) -> None:
    """Compute raw homography-residual scores."""
    rows: list[dict[str, Any]] = []
    skipped = 0
    for stem, arr in iter_backward_maps(bm_dir):
        raw = homography_residual_score(arr)
        if raw is None:
            skipped += 1
            continue
        rows.append({"id": stem, "raw": raw, "shape": list(arr.shape)})
        if spot_check and len(rows) >= spot_check:
            break
    _write_jsonl(out, rows)
    click.echo(f"scored={len(rows)} skipped={skipped} -> {out}")
    if rows:
        raws = np.array([r["raw"] for r in rows])
        pct = np.percentile(raws, [0, 5, 25, 50, 75, 95, 100])
        click.echo(
            f"raw percentiles [0,5,25,50,75,95,100]: {np.round(pct, 5).tolist()}"
        )
        click.echo(f"example shape: {rows[0]['shape']}")
    elif spot_check:
        raise click.ClickException(
            "No usable backward maps found; check format/layout."
        )


@cli.command()
@click.option(
    "--raw", "raw_path", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option("--bm-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--image-dir", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--sample", type=int, default=2000, show_default=True)
@click.option("--seed", type=int, default=0, show_default=True)
def calibrate(
    raw_path: Path, bm_dir: Path, image_dir: Path, out: Path, sample: int, seed: int
) -> None:
    """Fit raw -> (1 - SSIM) calibration on a random sample."""
    raw_by_id = {r["id"]: r["raw"] for r in _read_jsonl(raw_path)}
    images = {p.stem: p for p in image_dir.rglob("*.png")}
    candidates = sorted(set(raw_by_id) & set(images))
    if not candidates:
        raise click.ClickException(
            "No overlap between backward-map stems and image stems."
        )
    rng = np.random.default_rng(seed)
    chosen = set(
        rng.choice(candidates, size=min(sample, len(candidates)), replace=False)
    )

    raws: list[float] = []
    refs: list[float] = []
    for stem, arr in iter_backward_maps(bm_dir):
        if stem not in chosen:
            continue
        warped = cv2.imread(str(images[stem]), cv2.IMREAD_COLOR)
        flat = None if warped is None else unwarp(warped, arr)
        if warped is None or flat is None:
            continue
        raws.append(raw_by_id[stem])
        refs.append(ssim_severity(warped, flat))
    calibration = fit_calibration(np.array(raws), np.array(refs))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(calibration.to_dict()), encoding="utf-8")
    corr = float(np.corrcoef(raws, refs)[0, 1]) if len(raws) > 2 else float("nan")
    click.echo(
        f"calibrated on {len(raws)} pairs; Pearson r(raw, ssim_severity)={corr:.3f} -> {out}"
    )
    if corr < 0.5:
        click.echo(
            "WARNING: weak correlation; check bm units/stem pairing, or fall back to "
            "depth-map std(Z) (see plan).",
            err=True,
        )


@cli.command()
@click.option(
    "--raw", "raw_path", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option(
    "--calibration", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option("--out", type=click.Path(path_type=Path), required=True)
def apply(raw_path: Path, calibration: Path, out: Path) -> None:
    """Write calibrated severities (0-1) per image id."""
    cal = Calibration.from_dict(json.loads(calibration.read_text(encoding="utf-8")))
    rows = [
        {
            "id": r["id"],
            "warping_severity": round(apply_calibration(r["raw"], cal), 4),
            "label_source": "doc3d_bm_homography_calibrated",
        }
        for r in _read_jsonl(raw_path)
    ]
    _write_jsonl(out, rows)
    sev = np.array([r["warping_severity"] for r in rows])
    click.echo(
        f"wrote {len(rows)} -> {out}; severity mean={sev.mean():.3f} std={sev.std():.3f}"
    )


if __name__ == "__main__":
    cli()
