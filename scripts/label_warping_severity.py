"""Compute SSIM-based warping severity labels for paired distorted/flat datasets.

Reads L2 metadata files for each dataset, resolves distorted + flat image pairs,
computes SSIM-based severity, and writes the ``warping_severity`` field into
``enrichments.versions[-1].data`` of each sample in-place.

Supported datasets
------------------
- warpdoc: 1,020 paired images.
  Distorted: ``WarpDoc/image/{type}/{num}.jpg``
  Clean (digital): ``WarpDoc/digital/{type}/{num}.jpg``
- wsrd: 2,200 pairs with GT (input: ``{year}/{split}_input/``,
  clean: ``{year}/{split}_gt/``).  ``ntire2023/test_input`` is skipped — no GT exists.
  Note: wsrd is primarily a shadow dataset; include here to compute a paired
  distortion metric for samples that exhibit both shadow and perspective distortion.
- anyphotodoc6300: 6,306 warped images (8 document types, camera-captured).
  Distorted: ``init_{N}/{type}_{a}_{b}_{flat_id}_{view}.JPG``
  Clean: ``flat/{type_name}/{flat_id:02d}.png``
  Type mapping (N → name): 1=bill, 2=book, 3=complex, 4=education,
  5=invoice, 6=magazine, 7=single_column, 8=two_column.
- docalign12k: ~30K synthetically distorted images (14 distortion groups).
  Distorted: ``distorted_hard/{group}/{image_id}.jpg``
  Clean: ``flat/{group}/{image_id}.jpg``

Formula (from STREAM_4C_DATASET_HANDOFF.md §4.5)::

    severity = round(1.0 - ssim(distorted_gray, flat_gray, data_range=255), 4)
    severity = max(0.0, min(1.0, severity))

SSIM is appropriate for warping severity (unlike shadow severity) because warping
causes structural distortion — moved edges and deformed shapes — which SSIM captures
well via its structural component.

Warpdoc distortion types are stored in the auxiliary ``warping_type`` field
(not used during training; kept for Phase E evaluation analysis).

Output writes back to the SAME L2 metadata file atomically (temp file → rename).

Usage
-----
::

    # Spot-check 50 pairs before full run (REQUIRED)
    uv run python scripts/label_warping_severity.py \\
        --datasets warpdoc \\
        --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-dir /mnt/e/image_detection/01_base_data/correction/ \\
        --spot-check 50

    # Full run (all datasets)
    uv run python scripts/label_warping_severity.py \\
        --datasets warpdoc wsrd anyphotodoc6300 docalign12k \\
        --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-dir /mnt/e/image_detection/01_base_data/correction/
"""

from __future__ import annotations

import json
import logging
import random
import shutil
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import click
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset-specific pair resolvers
# ---------------------------------------------------------------------------


def _resolve_warpdoc_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path, str | None] | None:
    """Resolve distorted + clean pair for warpdoc, with optional warping type.

    Warpdoc paths follow ``WarpDoc/image/{type}/{num}.jpg``.
    The clean reference is at ``WarpDoc/digital/{type}/{num}.jpg``.

    Args:
        original_path: L2 ``source.original_path``, e.g.
            ``WarpDoc/image/curved/0000.jpg``.
        base_dir: Root directory of the warpdoc dataset on disk.

    Returns:
        ``(distorted_path, clean_path, warping_type)`` if both files exist,
        else ``None``.  ``warping_type`` is the folder name (e.g. ``"curved"``).
    """
    if "WarpDoc/image/" not in original_path:
        return None

    distorted = base_dir / original_path
    clean_path = base_dir / original_path.replace("WarpDoc/image/", "WarpDoc/digital/")

    if not distorted.exists():
        logger.debug("Distorted image not found: %s", distorted)
        return None
    if not clean_path.exists():
        logger.debug("Clean image not found: %s", clean_path)
        return None

    # Extract distortion type from path component after "image/"
    parts = original_path.split("/")
    try:
        img_idx = parts.index("image")
        warping_type = parts[img_idx + 1]
    except (ValueError, IndexError):
        warping_type = None

    return distorted, clean_path, warping_type


def _resolve_wsrd_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path, None] | None:
    """Resolve input + GT pair for wsrd.

    Args:
        original_path: L2 path, e.g. ``ntire2023/train_input/0000.png``.
        base_dir: Root directory of the wsrd dataset on disk.

    Returns:
        ``(distorted_path, clean_path, None)`` if both files exist, else ``None``.
    """
    if "_input/" not in original_path:
        return None  # GT sample; skip

    # ntire2023/test_input has no GT
    if "test_input" in original_path:
        return None

    distorted = base_dir / original_path
    clean_path = base_dir / original_path.replace("_input/", "_gt/")

    if not distorted.exists():
        logger.debug("Distorted image not found: %s", distorted)
        return None
    if not clean_path.exists():
        logger.debug("Clean image not found: %s", clean_path)
        return None

    return distorted, clean_path, None


# Ordered alphabetically: init_1=bill, init_2=book, ..., init_8=two_column
_ANYPHOTODOC_TYPE_NAMES: list[str] = [
    "bill",
    "book",
    "complex",
    "education",
    "invoice",
    "magazine",
    "single_column",
    "two_column",
]


def _resolve_anyphotodoc6300_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path, None] | None:
    """Resolve distorted + flat pair for anyphotodoc6300.

    Warped images live in ``init_{N}/{type}_{a}_{b}_{flat_id}_{view}.JPG``.
    The flat reference is ``flat/{type_name}/{flat_id:02d}.png``, where
    ``type_name`` is derived from N (1=bill … 8=two_column) and ``flat_id``
    is the 4th underscore-delimited component of the filename stem.

    Args:
        original_path: L2 ``source.original_path``, e.g.
            ``init_1/1_1_1_10_1.JPG``.
        base_dir: Root directory of the anyphotodoc6300 dataset on disk.

    Returns:
        ``(distorted_path, flat_path, None)`` if both files exist, else ``None``.
    """
    parts = Path(original_path).parts
    if len(parts) < 2 or not parts[0].startswith("init_"):
        return None

    try:
        type_idx = int(parts[0].split("_")[1]) - 1  # 0-indexed
    except (ValueError, IndexError):
        return None

    if not (0 <= type_idx < len(_ANYPHOTODOC_TYPE_NAMES)):
        return None
    type_name = _ANYPHOTODOC_TYPE_NAMES[type_idx]

    # Extract flat_id from the 4th underscore-delimited component of filename stem
    stem = Path(parts[1]).stem
    name_parts = stem.split("_")
    if len(name_parts) < 4:
        return None
    try:
        flat_id = int(name_parts[3])
    except ValueError:
        return None

    distorted = base_dir / original_path
    flat_path = base_dir / "flat" / type_name / f"{flat_id:02d}.png"

    if not distorted.exists():
        logger.debug("Distorted image not found: %s", distorted)
        return None
    if not flat_path.exists():
        logger.debug("Flat image not found: %s", flat_path)
        return None

    return distorted, flat_path, None


def _resolve_docalign12k_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path, None] | None:
    """Resolve distorted + flat pair for docalign12k.

    Distorted images are at ``distorted_hard/{group}/{image_id}.jpg``.
    The clean reference is at ``flat/{group}/{image_id}.jpg`` — same relative
    path with ``distorted_hard`` replaced by ``flat``.

    Args:
        original_path: L2 ``source.original_path``, e.g.
            ``distorted_hard/1/000101_00028.jpg``.
        base_dir: Root directory of the docalign12k dataset on disk.

    Returns:
        ``(distorted_path, flat_path, None)`` if both files exist, else ``None``.
    """
    if "distorted_hard/" not in original_path:
        return None

    distorted = base_dir / original_path
    flat_path = base_dir / original_path.replace("distorted_hard/", "flat/")

    if not distorted.exists():
        logger.debug("Distorted image not found: %s", distorted)
        return None
    if not flat_path.exists():
        logger.debug("Flat image not found: %s", flat_path)
        return None

    return distorted, flat_path, None


# resolver returns (distorted, clean, warping_type | None) or None
_PAIR_RESOLVERS: dict[str, Any] = {
    "warpdoc": _resolve_warpdoc_pair,
    "wsrd": _resolve_wsrd_pair,
    "anyphotodoc6300": _resolve_anyphotodoc6300_pair,
    "docalign12k": _resolve_docalign12k_pair,
}

_DATASET_BASE_DIRS: dict[str, str] = {
    "warpdoc": "warpdoc",
    "wsrd": "wsrd",
    "anyphotodoc6300": "anyphotodoc6300",
    "docalign12k": "docalign12k",
}


# ---------------------------------------------------------------------------
# SSIM severity computation
# ---------------------------------------------------------------------------


def _compute_severity(distorted_path: Path, clean_path: Path) -> float | None:
    """Compute warping severity as 1 - SSIM between distorted and flat images.

    Args:
        distorted_path: Path to the distorted (warped) image.
        clean_path: Path to the flat reference image.

    Returns:
        Float severity in ``[0.0, 1.0]``, or ``None`` on load error.
    """
    distorted_bgr = cv2.imread(str(distorted_path))
    clean_bgr = cv2.imread(str(clean_path))

    if distorted_bgr is None:
        logger.warning("Failed to load distorted image: %s", distorted_path)
        return None
    if clean_bgr is None:
        logger.warning("Failed to load clean image: %s", clean_path)
        return None

    if distorted_bgr.shape[:2] != clean_bgr.shape[:2]:
        h, w = distorted_bgr.shape[:2]
        clean_bgr = cv2.resize(clean_bgr, (w, h), interpolation=cv2.INTER_AREA)

    distorted_gray = cv2.cvtColor(distorted_bgr, cv2.COLOR_BGR2GRAY)
    clean_gray = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY)

    score = float(ssim(distorted_gray, clean_gray, data_range=255))
    severity = round(1.0 - score, 4)
    return float(np.clip(severity, 0.0, 1.0))


# ---------------------------------------------------------------------------
# L2 metadata helpers
# ---------------------------------------------------------------------------


def _get_latest_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable ``data`` dict of the latest enrichment version.

    Creates a stub version entry if none with a ``data`` key exists.

    Args:
        sample: A single sample dict from the L2 metadata ``samples`` array.

    Returns:
        The ``data`` dict of the latest version (always mutable).
    """
    enrichments: dict[str, Any] = sample.setdefault("enrichments", {})
    versions: list[dict[str, Any]] = enrichments.setdefault("versions", [])

    for version_entry in reversed(versions):
        if "data" in version_entry:
            return version_entry["data"]

    stub: dict[str, Any] = {
        "version": len(versions) + 1,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "label_warping_severity.py",
        "method": "ssim_paired",
        "data": {},
    }
    versions.append(stub)
    enrichments["current_version"] = len(versions)
    return stub["data"]


def _load_l2(path: Path) -> dict[str, Any]:
    """Load L2 metadata JSON.

    Args:
        path: Path to the metadata file.

    Returns:
        Parsed metadata dict.
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[return-value]


def _save_l2(data: dict[str, Any], path: Path) -> None:
    """Write L2 metadata to disk atomically (temp file → rename).

    Args:
        data: Metadata dict to serialise.
        path: Destination path.
    """
    parent = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    shutil.move(str(tmp_path), path)


# ---------------------------------------------------------------------------
# Core labeling logic
# ---------------------------------------------------------------------------


def _label_dataset(
    dataset_name: str,
    l2_metadata_dir: Path,
    base_data_dir: Path,
    spot_check: int,
    batch_size: int,
) -> dict[str, int]:
    """Label warping severity for a single dataset.

    Args:
        dataset_name: One of ``"warpdoc"``, ``"wsrd"``,
            ``"anyphotodoc6300"``, ``"docalign12k"``.
        l2_metadata_dir: Directory containing ``{dataset}_metadata.json`` files.
        base_data_dir: Parent directory of per-dataset correction folders.
        spot_check: If > 0, sample this many pairs and print stats, then exit.
        batch_size: Commit progress to disk every N pairs.

    Returns:
        Dict with counts: ``labelled``, ``skipped``, ``errors``, ``already_done``.
    """
    resolver = _PAIR_RESOLVERS[dataset_name]
    dataset_base = base_data_dir / _DATASET_BASE_DIRS[dataset_name]
    l2_path = l2_metadata_dir / f"{dataset_name}_metadata.json"

    if not l2_path.exists():
        msg = f"L2 metadata not found: {l2_path}"
        raise FileNotFoundError(msg)
    if not dataset_base.exists():
        msg = f"Dataset directory not found: {dataset_base}"
        raise FileNotFoundError(msg)

    click.echo(f"\n[{dataset_name}] Loading L2 metadata from {l2_path} …")
    metadata = _load_l2(l2_path)
    samples: list[dict[str, Any]] = metadata.get("samples", [])
    click.echo(f"[{dataset_name}] {len(samples):,} samples loaded")

    counts = {"labelled": 0, "skipped": 0, "errors": 0, "already_done": 0}

    if spot_check > 0:
        _run_spot_check(dataset_name, samples, resolver, dataset_base, spot_check)
        return counts

    modified = False
    for batch_start in range(0, len(samples), batch_size):
        batch = samples[batch_start : batch_start + batch_size]

        for sample in tqdm(
            batch,
            desc=f"{dataset_name} [{batch_start}–{batch_start + len(batch)}]",
            unit="img",
        ):
            original_path: str = sample.get("source", {}).get("original_path", "")
            result = resolver(original_path, dataset_base)

            if result is None:
                counts["skipped"] += 1
                continue

            distorted_path, clean_path, warping_type = result
            data_dict = _get_latest_data(sample)

            if "warping_severity" in data_dict:
                counts["already_done"] += 1
                continue

            severity = _compute_severity(distorted_path, clean_path)
            if severity is None:
                counts["errors"] += 1
                continue

            data_dict["warping_severity"] = severity
            if warping_type is not None:
                data_dict["warping_type"] = warping_type

            counts["labelled"] += 1
            modified = True

        if modified:
            click.echo(f"  Saving progress at sample {batch_start + len(batch):,} …")
            _save_l2(metadata, l2_path)
            modified = False

    _save_l2(metadata, l2_path)
    return counts


def _run_spot_check(
    dataset_name: str,
    samples: list[dict[str, Any]],
    resolver: Any,
    dataset_base: Path,
    n: int,
) -> None:
    """Sample N pairs and print severity distribution for visual inspection.

    Args:
        dataset_name: Dataset identifier for display.
        samples: Full sample list.
        resolver: Pair-resolver function for this dataset.
        dataset_base: Root directory on disk.
        n: Number of pairs to check.
    """
    eligible = [
        s
        for s in samples
        if resolver(s.get("source", {}).get("original_path", ""), dataset_base)
        is not None
    ]

    if not eligible:
        click.echo(
            f"[{dataset_name}] No eligible pairs found for spot-check!", err=True
        )
        return

    sample_set = random.sample(eligible, min(n, len(eligible)))
    severities: list[float] = []
    failures = 0

    click.echo(f"\n[{dataset_name}] Spot-checking {len(sample_set)} pairs …")
    click.echo(f"  {'path':<55} {'sev':>6} {'type'}")
    click.echo(f"  {'-' * 55} {'------':>6} ------")

    for sample in sample_set:
        orig = sample.get("source", {}).get("original_path", "")
        result = resolver(orig, dataset_base)
        if result is None:
            failures += 1
            continue

        distorted_path, clean_path, warping_type = result
        severity = _compute_severity(distorted_path, clean_path)
        if severity is None:
            failures += 1
            continue

        severities.append(severity)
        display = orig[-52:] if len(orig) > 52 else orig
        click.echo(f"  {display:<55} {severity:>6.4f} {warping_type or '-'}")

    if not severities:
        click.echo(f"[{dataset_name}] All spot-check pairs failed to load!", err=True)
        return

    arr = np.array(severities)
    click.echo(
        f"\n[{dataset_name}] Spot-check summary ({len(severities)} of {n} pairs):"
    )
    click.echo(
        f"  min={arr.min():.4f}  max={arr.max():.4f}  "
        f"mean={arr.mean():.4f}  median={np.median(arr):.4f}"
    )
    click.echo(f"  failures: {failures}")
    click.echo(
        "\nINSPECT: warpdoc should show higher severity for 'crumple'/'fold' "
        "than 'perspective'. If values cluster near 0, check path mapping."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--datasets",
    multiple=True,
    default=["warpdoc"],
    show_default=True,
    help="Datasets to label. Choices: warpdoc, wsrd, anyphotodoc6300, docalign12k.",
)
@click.option(
    "--l2-metadata-dir",
    default="/mnt/e/image_detection/metadata_registry/json/",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory containing {dataset}_metadata.json files.",
)
@click.option(
    "--base-data-dir",
    default="/mnt/e/image_detection/01_base_data/correction/",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Parent of per-dataset correction directories (warpdoc/, wsrd/).",
)
@click.option(
    "--spot-check",
    default=0,
    type=int,
    metavar="N",
    help="Sample N pairs and print severity stats, then exit without writing.",
)
@click.option(
    "--batch-size",
    default=500,
    show_default=True,
    type=int,
    help="Save progress to disk every N pairs (resume support).",
)
@click.option("--verbose", is_flag=True, help="Enable DEBUG logging.")
def main(
    datasets: tuple[str, ...],
    l2_metadata_dir: Path,
    base_data_dir: Path,
    spot_check: int,
    batch_size: int,
    verbose: bool,
) -> None:
    """Label warping severity for paired distorted/flat datasets.

    Reads L2 metadata, computes SSIM-based severity for each distorted/clean pair,
    and writes ``warping_severity`` into ``enrichments.versions[-1].data``.
    The auxiliary ``warping_type`` field is also written for warpdoc samples
    (not used in training; kept for evaluation).

    Run with ``--spot-check 50`` first to verify path mapping before full run.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    unknown = set(datasets) - set(_PAIR_RESOLVERS)
    if unknown:
        raise click.BadParameter(
            f"Unknown datasets: {unknown}. Valid: {set(_PAIR_RESOLVERS)}",
            param_hint="--datasets",
        )

    total: dict[str, int] = {
        "labelled": 0,
        "skipped": 0,
        "errors": 0,
        "already_done": 0,
    }

    for dataset_name in datasets:
        counts = _label_dataset(
            dataset_name=dataset_name,
            l2_metadata_dir=l2_metadata_dir,
            base_data_dir=base_data_dir,
            spot_check=spot_check,
            batch_size=batch_size,
        )
        click.echo(
            f"\n[{dataset_name}] done — "
            f"labelled={counts['labelled']:,}  "
            f"already_done={counts['already_done']:,}  "
            f"skipped={counts['skipped']:,}  "
            f"errors={counts['errors']:,}"
        )
        for k in total:
            total[k] += counts[k]

    if not spot_check:
        click.echo(
            f"\nTotal — labelled={total['labelled']:,}  "
            f"already_done={total['already_done']:,}  "
            f"skipped={total['skipped']:,}  "
            f"errors={total['errors']:,}"
        )


if __name__ == "__main__":
    main()
