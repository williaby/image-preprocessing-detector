#!/usr/bin/env python3
"""Materialize Kuzushiji sub-datasets (K-MNIST / K-49 / K-Kanji) to individual PNG
files with sidecar JSONL index files required by KuzushijiParser.

K-MNIST and K-49 are stored as binary arrays (IDX format or NumPy NPZ).  This
script decodes them into individual grayscale PNG images and writes per-split
``{split}_index.jsonl`` files mapping each filename to its Unicode character label.

K-Kanji images are already individual PNGs (extracted from kkanji.tar by the
download step with Unicode directory names); this script only writes the sidecar
``all_index.jsonl`` for them.

Prerequisites
-------------
Run ``scripts/download_kuzushiji_kaggle.sh`` (or the Kaggle download commands in
``docs/datasets/source/kuzushiji.md``) first, then run this script.

Expected on-disk layout before running (output of Kaggle download + tar extraction)::

    kuzushiji/
        kmnist/
            data/
                train-images-idx3-ubyte[.gz]
                train-labels-idx1-ubyte[.gz]
                t10k-images-idx3-ubyte[.gz]
                t10k-labels-idx1-ubyte[.gz]
                -- OR --
                kmnist-train-imgs.npz
                kmnist-train-labels.npz
                kmnist-test-imgs.npz
                kmnist-test-labels.npz
            kmnist_classmap.csv
        k49/
            data/
                k49-train-imgs.npz
                k49-train-labels.npz
                k49-test-imgs.npz
                k49-test-labels.npz
            k49_classmap.csv
        kkanji/
            kkanji2/
                <unicode-char>/     (e.g. ``亡/``, ``一/``)
                    001.png
                    ...

Output added by this script::

    kuzushiji/
        kmnist/
            images/
                train/  00000001.png …
                test/   00000001.png …
            train_index.jsonl
            test_index.jsonl
        k49/
            images/
                train/  00000001.png …
                test/   00000001.png …
            train_index.jsonl
            test_index.jsonl
        kkanji/
            all_index.jsonl   (filename relative to kkanji2/ root, char, class_dir)

Sidecar JSONL schema::

    {"filename": "00000001.png", "label_int": 0, "char_unicode": "お", "split": "train"}

Usage::

    # Dry run — print stats, write nothing
    uv run python scripts/materialize_kuzushiji.py --dry-run

    # Materialize all sub-datasets
    uv run python scripts/materialize_kuzushiji.py

    # Single sub-dataset
    uv run python scripts/materialize_kuzushiji.py --sub-dataset kmnist
    uv run python scripts/materialize_kuzushiji.py --sub-dataset k49
    uv run python scripts/materialize_kuzushiji.py --sub-dataset kkanji

    # Overwrite existing PNG files (kmnist/k49 only; kkanji PNGs are not re-written)
    uv run python scripts/materialize_kuzushiji.py --overwrite
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import struct
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path("/mnt/e/image_detection/01_base_data/handwriting/kuzushiji")

ALL_SUB_DATASETS = ["kmnist", "k49", "kkanji"]

# Expected image counts (for validation warnings)
_EXPECTED_KMNIST = {"train": 60_000, "test": 10_000}
_EXPECTED_K49 = {"train": 232_365, "test": 38_547}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classmap loading
# ---------------------------------------------------------------------------


def _load_classmap(csv_path: Path) -> dict[int, str]:
    """Load a Kuzushiji classmap CSV into an int→char dict.

    CSV format::

        index,codepoint,char
        0,U+304A,お

    Args:
        csv_path: Path to ``kmnist_classmap.csv`` or ``k49_classmap.csv``.

    Returns:
        Dict mapping integer label → Unicode character string.
    """
    mapping: dict[int, str] = {}
    if not csv_path.exists():
        logger.warning("Classmap not found: %s — char_unicode will be empty", csv_path)
        return mapping

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                idx = int(row["index"])
                char = row["char"].strip()
                mapping[idx] = char
            except (KeyError, ValueError):
                continue

    logger.debug("Loaded %d classmap entries from %s", len(mapping), csv_path.name)
    return mapping


# ---------------------------------------------------------------------------
# IDX binary decoding (K-MNIST format)
# ---------------------------------------------------------------------------


def _open_idx(path: Path):  # type: ignore[return]
    """Open an IDX binary file, decompressing on-the-fly if .gz.

    Args:
        path: Path to the IDX file (with or without .gz suffix).

    Returns:
        Open binary file-like object at position 0.
    """
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def _decode_idx_images(path: Path) -> np.ndarray:
    """Decode an IDX3 (images) file to a uint8 NumPy array.

    Args:
        path: Path to IDX3 image file (gzipped or raw).

    Returns:
        NumPy array of shape (N, rows, cols), dtype uint8.

    Raises:
        ValueError: If the magic number is not 0x00000803.
    """
    with _open_idx(path) as fh:
        magic, n_images, n_rows, n_cols = struct.unpack(">IIII", fh.read(16))
        if magic != 0x00000803:
            raise ValueError(f"Bad IDX3 magic 0x{magic:08X} in {path.name}")
        raw = fh.read(n_images * n_rows * n_cols)
    return np.frombuffer(raw, dtype=np.uint8).reshape(n_images, n_rows, n_cols)


def _decode_idx_labels(path: Path) -> np.ndarray:
    """Decode an IDX1 (labels) file to a uint8 NumPy array.

    Args:
        path: Path to IDX1 label file (gzipped or raw).

    Returns:
        NumPy array of shape (N,), dtype uint8.

    Raises:
        ValueError: If the magic number is not 0x00000801.
    """
    with _open_idx(path) as fh:
        magic, n_labels = struct.unpack(">II", fh.read(8))
        if magic != 0x00000801:
            raise ValueError(f"Bad IDX1 magic 0x{magic:08X} in {path.name}")
        raw = fh.read(n_labels)
    return np.frombuffer(raw, dtype=np.uint8)


def _resolve_idx_pair(data_dir: Path, split: str) -> tuple[Path | None, Path | None]:
    """Find IDX image + label files for a split, preferring uncompressed.

    Checks both compressed (``train-images-idx3-ubyte.gz``) and uncompressed
    (``train-images-idx3-ubyte``) variants, preferring uncompressed.

    Args:
        data_dir: ``kmnist/data/`` directory.
        split: ``"train"`` or ``"test"``.

    Returns:
        Tuple of (images_path, labels_path), either may be None if not found.
    """
    prefix = "train" if split == "train" else "t10k"
    img_candidates = [
        data_dir / f"{prefix}-images-idx3-ubyte",
        data_dir / f"{prefix}-images-idx3-ubyte.gz",
    ]
    lbl_candidates = [
        data_dir / f"{prefix}-labels-idx1-ubyte",
        data_dir / f"{prefix}-labels-idx1-ubyte.gz",
    ]
    img_path = next((p for p in img_candidates if p.is_file()), None)
    lbl_path = next((p for p in lbl_candidates if p.is_file()), None)
    return img_path, lbl_path


# ---------------------------------------------------------------------------
# NPZ decoding (K-49 format)
# ---------------------------------------------------------------------------


def _load_npz_images(path: Path) -> np.ndarray:
    """Load image array from a K-49 NPZ file.

    K-49 NPZ files store images under key ``'arr_0'`` or the first available key.

    Args:
        path: Path to the NPZ file.

    Returns:
        NumPy array of shape (N, 28, 28), dtype uint8.
    """
    data = np.load(path)
    key = "arr_0" if "arr_0" in data else next(iter(data.keys()))
    return data[key].astype(np.uint8)


def _load_npz_labels(path: Path) -> np.ndarray:
    """Load label array from a K-49 NPZ labels file.

    Args:
        path: Path to the NPZ file.

    Returns:
        NumPy array of shape (N,), dtype int.
    """
    data = np.load(path)
    key = "arr_0" if "arr_0" in data else next(iter(data.keys()))
    return data[key].astype(int)


# ---------------------------------------------------------------------------
# Common PNG writer
# ---------------------------------------------------------------------------


def _write_pngs_and_index(
    images: np.ndarray,
    labels: np.ndarray,
    classmap: dict[int, str],
    images_dir: Path,
    index_path: Path,
    split: str,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Write PNG files and sidecar JSONL index for one split.

    Args:
        images: Array of shape (N, H, W), uint8.
        labels: Array of shape (N,), integer class labels.
        classmap: Mapping from label int to Unicode character.
        images_dir: Directory to write PNG files into.
        index_path: Path for the sidecar JSONL file.
        split: Split name for the ``split`` field in each index record.
        overwrite: Re-write PNGs that already exist.
        dry_run: Count only — write nothing.

    Returns:
        Tuple of (n_extracted, n_skipped, n_errors).
    """
    n = len(images)
    if dry_run:
        already = sum(1 for _ in images_dir.glob("*.png")) if images_dir.exists() else 0
        logger.info("  Dry run — would write %d PNGs (%d already exist)", n, already)
        return 0, already, 0

    images_dir.mkdir(parents=True, exist_ok=True)
    index_records: list[dict[str, Any]] = []
    n_extracted = 0
    n_skipped = 0
    n_errors = 0

    with tqdm(total=n, unit="img", desc=f"  {split:>8}", leave=True) as pbar:
        for idx in range(n):
            filename = f"{idx + 1:08d}.png"
            png_path = images_dir / filename
            label_int = int(labels[idx])
            char_unicode = classmap.get(label_int, "")

            if png_path.exists() and not overwrite:
                n_skipped += 1
            else:
                try:
                    img = Image.fromarray(images[idx], mode="L")
                    img.save(png_path, format="PNG", optimize=False)
                    n_extracted += 1
                except (OSError, ValueError) as exc:
                    logger.debug("Index %d save failed: %s", idx, exc)
                    n_errors += 1
                    pbar.update(1)
                    continue

            index_records.append(
                {
                    "filename": filename,
                    "label_int": label_int,
                    "char_unicode": char_unicode,
                    "split": split,
                }
            )
            pbar.update(1)

    with index_path.open("w", encoding="utf-8") as fh:
        for rec in index_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info(
        "  %s done — extracted=%d  skipped=%d  errors=%d  index=%s",
        split,
        n_extracted,
        n_skipped,
        n_errors,
        index_path.name,
    )
    return n_extracted, n_skipped, n_errors


# ---------------------------------------------------------------------------
# K-MNIST materialization
# ---------------------------------------------------------------------------


def materialize_kmnist(
    data_dir: Path,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Materialize K-MNIST IDX or NPZ data to PNGs + sidecar JSONL.

    Tries IDX binary first; falls back to NPZ if IDX files are absent.

    Args:
        data_dir: Root of the ``kmnist/`` sub-dataset directory.
        overwrite: Re-extract images that already exist.
        dry_run: Count only — write nothing.

    Returns:
        Tuple of (total_extracted, total_skipped, total_errors).
    """
    classmap = _load_classmap(data_dir / "kmnist_classmap.csv")
    raw_dir = data_dir / "data"
    total_extracted = total_skipped = total_errors = 0

    for split in ("train", "test"):
        expected = _EXPECTED_KMNIST[split]
        images_dir = data_dir / "images" / split
        index_path = data_dir / f"{split}_index.jsonl"

        # Try IDX first
        img_path, lbl_path = _resolve_idx_pair(raw_dir, split)
        if img_path and lbl_path:
            logger.info("K-MNIST %s — using IDX: %s", split, img_path.name)
            try:
                images = _decode_idx_images(img_path)
                labels = _decode_idx_labels(lbl_path)
            except (ValueError, OSError) as exc:
                logger.error("IDX decode failed for %s: %s", split, exc)
                total_errors += 1
                continue
        else:
            # Fall back to NPZ
            prefix = "kmnist-train" if split == "train" else "kmnist-test"
            npz_img = raw_dir / f"{prefix}-imgs.npz"
            npz_lbl = raw_dir / f"{prefix}-labels.npz"
            if not npz_img.exists() or not npz_lbl.exists():
                logger.error(
                    "K-MNIST %s: neither IDX nor NPZ files found in %s", split, raw_dir
                )
                total_errors += 1
                continue
            logger.info("K-MNIST %s — using NPZ: %s", split, npz_img.name)
            images = _load_npz_images(npz_img)
            labels = _load_npz_labels(npz_lbl)

        if len(images) != expected:
            logger.warning(
                "K-MNIST %s: expected %d images, got %d", split, expected, len(images)
            )

        extracted, skipped, errors = _write_pngs_and_index(
            images,
            labels,
            classmap,
            images_dir,
            index_path,
            split,
            overwrite,
            dry_run,
        )
        total_extracted += extracted
        total_skipped += skipped
        total_errors += errors

    return total_extracted, total_skipped, total_errors


# ---------------------------------------------------------------------------
# K-49 materialization
# ---------------------------------------------------------------------------


def materialize_k49(
    data_dir: Path,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Materialize K-49 NPZ data to PNGs + sidecar JSONL.

    Args:
        data_dir: Root of the ``k49/`` sub-dataset directory.
        overwrite: Re-extract images that already exist.
        dry_run: Count only — write nothing.

    Returns:
        Tuple of (total_extracted, total_skipped, total_errors).
    """
    classmap = _load_classmap(data_dir / "k49_classmap.csv")
    raw_dir = data_dir / "data"
    total_extracted = total_skipped = total_errors = 0

    for split in ("train", "test"):
        expected = _EXPECTED_K49[split]
        images_dir = data_dir / "images" / split
        index_path = data_dir / f"{split}_index.jsonl"

        npz_img = raw_dir / f"k49-{split}-imgs.npz"
        npz_lbl = raw_dir / f"k49-{split}-labels.npz"

        if not npz_img.exists() or not npz_lbl.exists():
            logger.error("K-49 %s: NPZ files not found in %s", split, raw_dir)
            total_errors += 1
            continue

        logger.info("K-49 %s — loading NPZ: %s", split, npz_img.name)
        images = _load_npz_images(npz_img)
        labels = _load_npz_labels(npz_lbl)

        if len(images) != expected:
            logger.warning(
                "K-49 %s: expected %d images, got %d", split, expected, len(images)
            )

        extracted, skipped, errors = _write_pngs_and_index(
            images,
            labels,
            classmap,
            images_dir,
            index_path,
            split,
            overwrite,
            dry_run,
        )
        total_extracted += extracted
        total_skipped += skipped
        total_errors += errors

    return total_extracted, total_skipped, total_errors


# ---------------------------------------------------------------------------
# K-Kanji index writing (images already on disk)
# ---------------------------------------------------------------------------


def materialize_kkanji(
    data_dir: Path,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Write a sidecar index for K-Kanji images that are already on disk.

    K-Kanji images are extracted from ``kkanji.tar`` into
    ``kkanji/kkanji2/<unicode-char>/`` directories.  This function scans
    those directories and writes ``kkanji/all_index.jsonl``.

    The index schema for K-Kanji (no official split)::

        {"filename": "<char>/<image>.png", "char_unicode": "<char>", "split": "all"}

    Args:
        data_dir: Root of the ``kkanji/`` sub-dataset directory.
        dry_run: Count only — write nothing.

    Returns:
        Tuple of (n_indexed, 0, 0).
    """
    kkanji2_dir = data_dir / "kkanji2"
    index_path = data_dir / "all_index.jsonl"

    if not kkanji2_dir.exists():
        logger.error("K-Kanji directory not found: %s", kkanji2_dir)
        return 0, 0, 1

    char_dirs = sorted(p for p in kkanji2_dir.iterdir() if p.is_dir())
    if not char_dirs:
        logger.error("No character directories found in %s", kkanji2_dir)
        return 0, 0, 1

    if dry_run:
        n_files = sum(1 for d in char_dirs for _ in d.glob("*.png"))
        logger.info(
            "K-Kanji dry run — %d character dirs, %d PNG files", len(char_dirs), n_files
        )
        return n_files, 0, 0

    records: list[dict[str, Any]] = []
    with tqdm(total=len(char_dirs), unit="class", desc="  K-Kanji", leave=True) as pbar:
        for char_dir in char_dirs:
            char = char_dir.name
            for png_path in sorted(char_dir.glob("*.png")):
                # filename is relative: "亡/72d56fc.png"
                filename = f"{char}/{png_path.name}"
                records.append(
                    {
                        "filename": filename,
                        "char_unicode": char,
                        "split": "all",
                    }
                )
            pbar.update(1)

    with index_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info("K-Kanji done — %d images indexed in %s", len(records), index_path.name)
    return len(records), 0, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for Kuzushiji materialization."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Materialize K-MNIST / K-49 / K-Kanji to individual PNGs "
            "and sidecar JSONL index files for KuzushijiParser."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Root kuzushiji/ directory (default: %(default)s).",
    )
    parser.add_argument(
        "--sub-dataset",
        choices=[*ALL_SUB_DATASETS, "all"],
        default="all",
        metavar="DS",
        help="Which sub-dataset to process: kmnist | k49 | kkanji | all (default: all).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-extract PNG files that already exist (kmnist/k49 only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing any files.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        sys.exit(1)

    if args.dry_run:
        logger.info("DRY RUN — no files will be written")

    to_run = ALL_SUB_DATASETS if args.sub_dataset == "all" else [args.sub_dataset]
    total_extracted = total_skipped = total_errors = 0

    for sub in to_run:
        sub_dir = data_dir / sub
        if not sub_dir.exists():
            logger.error("Sub-dataset directory not found: %s", sub_dir)
            total_errors += 1
            continue

        logger.info("── %s ──", sub.upper())

        if sub == "kmnist":
            e, s, err = materialize_kmnist(sub_dir, args.overwrite, args.dry_run)
        elif sub == "k49":
            e, s, err = materialize_k49(sub_dir, args.overwrite, args.dry_run)
        else:  # kkanji
            e, s, err = materialize_kkanji(sub_dir, args.dry_run)

        total_extracted += e
        total_skipped += s
        total_errors += err

    logger.info(
        "All done — extracted=%d  skipped=%d  errors=%d",
        total_extracted,
        total_skipped,
        total_errors,
    )

    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
