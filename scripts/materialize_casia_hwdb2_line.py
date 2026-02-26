#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Materialize CASIA-HWDB2-line Parquet files to lossless PNG images.

Reads the three HuggingFace Parquet files (train/validation/test) downloaded
from Teklia/CASIA-HWDB2-line, extracts each row's image to an individual
lossless grayscale PNG file, and writes sidecar JSONL index files that the
CasiaHwdb2LineParser expects.

Output structure:
    {data-dir}/
        data/
            train.parquet           (input — already present)
            validation.parquet      (input — already present)
            test.parquet            (input — already present)
        images/
            train/
                00000001.png
                00000002.png
                ...
            validation/
                ...
            test/
                ...
        train_index.jsonl           (sidecar for parser)
        validation_index.jsonl
        test_index.jsonl

Index schema (one JSON object per line):
    {"filename": "00000001.png", "text": "2007年高校招生...", "char_count": 16}

Idempotent: skips images that already exist unless --overwrite is set.
Grayscale: source images are RGB JPEG; converted to L (8-bit grayscale) to
reduce file size since all content is ink-on-white.

Usage:
    # Dry run — print stats, extract nothing
    python scripts/materialize_casia_hwdb2_line.py --dry-run

    # Full materialization (all 52,160 images)
    python scripts/materialize_casia_hwdb2_line.py

    # Single split
    python scripts/materialize_casia_hwdb2_line.py --splits train

    # Overwrite existing PNG files
    python scripts/materialize_casia_hwdb2_line.py --overwrite
"""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path
from typing import Any, Iterator

import pyarrow.parquet as pq
from PIL import Image
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path("/mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2-line")

# Split names that have Parquet files
ALL_SPLITS = ["train", "validation", "test"]

# Expected row counts per split (from dataset documentation)
_EXPECTED_COUNTS = {
    "train": 33_400,
    "validation": 8_320,
    "test": 10_440,
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parquet reading
# ---------------------------------------------------------------------------


def _iter_parquet_rows(parquet_path: Path, batch_size: int = 500) -> Iterator[dict[str, Any]]:
    """Iterate over rows in a HuggingFace Parquet file in batches.

    HuggingFace image datasets store images as struct columns with keys
    ``bytes`` (raw image file bytes) and ``path`` (original filename).
    The ``text`` column contains the Chinese transcription string.

    Args:
        parquet_path: Path to the .parquet file.
        batch_size: Rows to read per batch (controls memory usage).

    Yields:
        Dicts with keys ``image_bytes`` (bytes) and ``text`` (str).
    """
    pf = pq.ParquetFile(parquet_path)
    for batch in pf.iter_batches(batch_size=batch_size):
        batch_dict = batch.to_pydict()
        image_col = batch_dict["image"]
        text_col = batch_dict["text"]

        for img_struct, text in zip(image_col, text_col):
            # HuggingFace stores images as {"bytes": b"...", "path": "..."}
            if isinstance(img_struct, dict):
                img_bytes = img_struct.get("bytes") or img_struct.get("data", b"")
            elif isinstance(img_struct, bytes):
                img_bytes = img_struct
            else:
                img_bytes = b""

            yield {"image_bytes": img_bytes, "text": text or ""}


def _count_parquet_rows(parquet_path: Path) -> int:
    """Return total row count from Parquet file metadata (fast, no data read).

    Args:
        parquet_path: Path to the .parquet file.

    Returns:
        Total row count.
    """
    return pq.read_metadata(parquet_path).num_rows


# ---------------------------------------------------------------------------
# Image conversion
# ---------------------------------------------------------------------------


def _bytes_to_grayscale_png_bytes(img_bytes: bytes) -> bytes:
    """Convert raw image bytes (JPEG/any) to lossless grayscale PNG bytes.

    Args:
        img_bytes: Raw image file bytes (e.g. JPEG from Parquet).

    Returns:
        PNG-encoded grayscale image bytes.

    Raises:
        ValueError: If img_bytes is empty or cannot be decoded.
    """
    if not img_bytes:
        raise ValueError("Empty image bytes")

    img = Image.open(io.BytesIO(img_bytes))
    # Convert to grayscale — source is RGB JPEG but content is ink-on-white
    if img.mode != "L":
        img = img.convert("L")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Materialization logic
# ---------------------------------------------------------------------------


def materialize_split(
    split: str,
    data_dir: Path,
    overwrite: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Materialize one Parquet split to PNG images + sidecar index.

    Args:
        split: Split name ("train", "validation", "test").
        data_dir: Dataset root directory.
        overwrite: Re-extract images that already exist if True.
        dry_run: If True, count only — write nothing.

    Returns:
        Tuple of (n_extracted, n_skipped, n_errors).
    """
    parquet_path = data_dir / "data" / f"{split}.parquet"
    images_dir = data_dir / "images" / split
    index_path = data_dir / f"{split}_index.jsonl"

    if not parquet_path.exists():
        logger.error("Parquet not found: %s", parquet_path)
        return 0, 0, 1

    total_rows = _count_parquet_rows(parquet_path)
    expected = _EXPECTED_COUNTS.get(split, total_rows)
    if total_rows != expected:
        logger.warning(
            "%s: expected %d rows, found %d — proceeding",
            split, expected, total_rows,
        )

    logger.info(
        "Split %-10s │ %d images │ parquet=%s",
        split, total_rows, parquet_path.name,
    )

    if dry_run:
        already = sum(1 for _ in images_dir.glob("*.png")) if images_dir.exists() else 0
        logger.info("  Dry run — would extract %d images (%d already exist)", total_rows, already)
        return 0, already, 0

    images_dir.mkdir(parents=True, exist_ok=True)

    n_extracted = 0
    n_skipped = 0
    n_errors = 0
    index_records: list[dict[str, Any]] = []

    row_iter = _iter_parquet_rows(parquet_path)

    with tqdm(total=total_rows, unit="img", desc=f"  {split:>10}", leave=True) as pbar:
        for idx, row in enumerate(row_iter, start=1):
            filename = f"{idx:08d}.png"
            png_path = images_dir / filename

            if png_path.exists() and not overwrite:
                n_skipped += 1
                # Still need the index record — read text from row
                index_records.append({"filename": filename, "text": row["text"], "char_count": len(row["text"])})
                pbar.update(1)
                continue

            try:
                png_bytes = _bytes_to_grayscale_png_bytes(row["image_bytes"])
                png_path.write_bytes(png_bytes)
                index_records.append({"filename": filename, "text": row["text"], "char_count": len(row["text"])})
                n_extracted += 1
            except (ValueError, OSError, Exception) as exc:  # noqa: BLE001
                logger.debug("Row %d failed: %s", idx, exc)
                n_errors += 1

            pbar.update(1)

    # Write sidecar index
    with index_path.open("w", encoding="utf-8") as fh:
        for record in index_records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(
        "  %s done — extracted=%d  skipped=%d  errors=%d  index=%s",
        split, n_extracted, n_skipped, n_errors, index_path.name,
    )
    return n_extracted, n_skipped, n_errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for Parquet → PNG materialization."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Materialize CASIA-HWDB2-line Parquet files to lossless grayscale PNG images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Dataset root directory (contains data/ and will receive images/).",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=ALL_SPLITS,
        default=ALL_SPLITS,
        metavar="SPLIT",
        help="Which splits to process (default: train validation test).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-extract and overwrite PNG files that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be extracted without writing any files.",
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

    total_extracted = 0
    total_skipped = 0
    total_errors = 0

    for split in args.splits:
        extracted, skipped, errors = materialize_split(
            split=split,
            data_dir=data_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        total_extracted += extracted
        total_skipped += skipped
        total_errors += errors

    logger.info(
        "All splits done — extracted=%d  skipped=%d  errors=%d",
        total_extracted, total_skipped, total_errors,
    )

    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
