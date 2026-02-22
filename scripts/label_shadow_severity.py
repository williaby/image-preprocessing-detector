"""Compute luminance-delta shadow severity labels for paired shadow/clean datasets.

Reads L2 metadata files for each dataset, resolves shadow + clean image pairs,
computes luminance-delta severity, and writes the ``shadow_severity`` field into
``enrichments.versions[-1].data`` of each sample in-place.

Supported datasets
------------------
- sd7k: 7,239 paired images (shadow: ``{split}/input/``, clean: ``{split}/target/``)
- wsrd: 2,200 pairs with GT (shadow: ``{year}/{split}_input/``,
  clean: ``{year}/{split}_gt/``).  ``ntire2023/test_input`` is skipped — no GT exists.

Formula::

    # Shadow darkens regions; measure average luminance reduction
    delta = max(clean_gray.float() - shadow_gray.float(), 0.0)
    severity = round(clip(mean(delta) / 255.0, 0.0, 1.0), 4)

SSIM is intentionally NOT used here: SSIM penalises blur, noise, and JPEG
compression equally alongside luminance changes, conflating different degradation
types.  The luminance-delta formula specifically isolates the darkening effect of
shadows (positive values where clean > shadow) while ignoring sensor noise and
compression artefacts that may differ between the two exposures.

Output writes back to the SAME L2 metadata file atomically (temp file → rename).

Usage
-----
::

    # Spot-check 50 pairs before full run (REQUIRED before processing all data)
    uv run python scripts/label_shadow_severity.py \\
        --datasets sd7k \\
        --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-dir /mnt/e/image_detection/01_base_data/correction/ \\
        --spot-check 50

    # Full run
    uv run python scripts/label_shadow_severity.py \\
        --datasets sd7k wsrd \\
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
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset-specific pair resolvers
# ---------------------------------------------------------------------------

_SD7K_BASE = "01_base_data/correction/sd7k"
_WSRD_BASE = "01_base_data/correction/wsrd"


def _resolve_sd7k_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path] | None:
    """Resolve shadow + clean pair for sd7k.

    Args:
        original_path: L2 ``source.original_path`` value, e.g. ``test/input/IMG_0106.png``.
        base_dir: Root directory of the sd7k dataset on disk.

    Returns:
        ``(shadow_path, clean_path)`` if both files exist, else ``None``.
    """
    if "/input/" not in original_path:
        return None  # GT file or unexpected path; skip

    shadow = base_dir / original_path
    clean = base_dir / original_path.replace("/input/", "/target/")

    if not shadow.exists():
        logger.debug("Shadow image not found: %s", shadow)
        return None
    if not clean.exists():
        logger.debug("Clean image not found: %s", clean)
        return None

    return shadow, clean


def _resolve_wsrd_pair(
    original_path: str,
    base_dir: Path,
) -> tuple[Path, Path] | None:
    """Resolve shadow + clean pair for wsrd.

    Args:
        original_path: L2 path, e.g. ``ntire2023/train_input/0000.png``.
        base_dir: Root directory of the wsrd dataset on disk.

    Returns:
        ``(shadow_path, clean_path)`` if both files exist, else ``None``.
    """
    if "_input/" not in original_path:
        return None  # GT sample or test-only path; skip

    # ntire2023/test_input has no GT — skip silently
    if "test_input" in original_path:
        return None

    shadow = base_dir / original_path
    clean = base_dir / original_path.replace("_input/", "_gt/")

    if not shadow.exists():
        logger.debug("Shadow image not found: %s", shadow)
        return None
    if not clean.exists():
        logger.debug("Clean image not found: %s", clean)
        return None

    return shadow, clean


_PAIR_RESOLVERS: dict[str, Any] = {
    "sd7k": _resolve_sd7k_pair,
    "wsrd": _resolve_wsrd_pair,
}

_DATASET_BASE_DIRS: dict[str, str] = {
    "sd7k": "sd7k",
    "wsrd": "wsrd",
}


# ---------------------------------------------------------------------------
# Luminance-delta severity computation
# ---------------------------------------------------------------------------


def _compute_severity(shadow_path: Path, clean_path: Path) -> float | None:
    """Compute shadow severity as mean luminance reduction (clean − shadow).

    Uses per-pixel luminance difference rather than SSIM so that the metric
    isolates the darkening effect of shadows and is unaffected by blur, noise,
    or JPEG compression artefacts that cause SSIM to misclassify quality.

    Args:
        shadow_path: Path to the shadow (degraded) image.
        clean_path: Path to the clean reference image.

    Returns:
        Float severity in ``[0.0, 1.0]``, or ``None`` on load error.
        Typical range for sd7k: 0.05–0.45.
    """
    shadow_bgr = cv2.imread(str(shadow_path))
    clean_bgr = cv2.imread(str(clean_path))

    if shadow_bgr is None:
        logger.warning("Failed to load shadow image: %s", shadow_path)
        return None
    if clean_bgr is None:
        logger.warning("Failed to load clean image: %s", clean_path)
        return None

    # Resize clean to match shadow if sizes differ (rare edge case)
    if shadow_bgr.shape[:2] != clean_bgr.shape[:2]:
        h, w = shadow_bgr.shape[:2]
        clean_bgr = cv2.resize(clean_bgr, (w, h), interpolation=cv2.INTER_AREA)

    shadow_gray = cv2.cvtColor(shadow_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    clean_gray = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Positive delta = shadow darker than clean; negative = sensor noise / ignored
    delta = np.maximum(clean_gray - shadow_gray, 0.0)
    severity = round(float(np.clip(delta.mean() / 255.0, 0.0, 1.0)), 4)
    return severity


# ---------------------------------------------------------------------------
# L2 metadata helpers
# ---------------------------------------------------------------------------


def _get_latest_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable ``data`` dict of the latest enrichment version.

    If no versions with a ``data`` key exist, creates and appends a minimal
    version entry so the severity field has somewhere to live.

    Args:
        sample: A single sample dict from the L2 metadata ``samples`` array.

    Returns:
        The ``data`` dict of the latest version (may be newly created, always mutable).
    """
    enrichments: dict[str, Any] = sample.setdefault("enrichments", {})
    versions: list[dict[str, Any]] = enrichments.setdefault("versions", [])

    # Find last version that has a data dict
    for version_entry in reversed(versions):
        if "data" in version_entry:
            return version_entry["data"]

    # No version with data — create a stub so we can store the field
    stub: dict[str, Any] = {
        "version": len(versions) + 1,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "label_shadow_severity.py",
        "method": "luminance_delta_paired",
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

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is malformed.
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
    """Label shadow severity for a single dataset.

    Args:
        dataset_name: One of ``"sd7k"``, ``"wsrd"``.
        l2_metadata_dir: Directory containing ``{dataset}_metadata.json`` files.
        base_data_dir: Parent directory of per-dataset correction folders.
        spot_check: If > 0, sample this many pairs and print stats, then exit.
        batch_size: Commit progress to disk every N pairs (resume support).

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
            pair = resolver(original_path, dataset_base)

            if pair is None:
                counts["skipped"] += 1
                continue

            shadow_path, clean_path = pair
            data_dict = _get_latest_data(sample)

            if "shadow_severity" in data_dict:
                counts["already_done"] += 1
                continue

            severity = _compute_severity(shadow_path, clean_path)
            if severity is None:
                counts["errors"] += 1
                continue

            data_dict["shadow_severity"] = severity
            counts["labelled"] += 1
            modified = True

        if modified:
            click.echo(f"  Saving progress at sample {batch_start + len(batch):,} …")
            _save_l2(metadata, l2_path)
            modified = False

    # Final save if needed
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
    click.echo(f"  {'path':<55} {'sev':>6}")
    click.echo(f"  {'-' * 55} {'------':>6}")

    for sample in sample_set:
        orig = sample.get("source", {}).get("original_path", "")
        pair = resolver(orig, dataset_base)
        if pair is None:
            failures += 1
            continue

        shadow_path, clean_path = pair
        severity = _compute_severity(shadow_path, clean_path)
        if severity is None:
            failures += 1
            continue

        severities.append(severity)
        display = orig[-52:] if len(orig) > 52 else orig
        click.echo(f"  {display:<55} {severity:>6.4f}")

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
        "\nINSPECT: sd7k should show broad range 0.1–0.9. "
        "If most values cluster near 0 or 1, check path mapping."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--datasets",
    multiple=True,
    default=["sd7k", "wsrd"],
    show_default=True,
    help="Datasets to label. Choices: sd7k, wsrd.",
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
    help="Parent of per-dataset correction directories (sd7k/, wsrd/).",
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
    """Label shadow severity for paired shadow datasets.

    Reads L2 metadata, computes luminance-delta severity for each shadow/clean
    pair, and writes ``shadow_severity`` into ``enrichments.versions[-1].data``.

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
