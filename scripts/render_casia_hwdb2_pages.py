#!/usr/bin/env python3
"""Render CASIA-HWDB2 DGRL page files to lossless PNG images.

The DGRL binary format stores handwritten page data as per-line grayscale
bitmaps embedded in the binary. This script reconstructs full-page images
by compositing each line's bitmap onto a white canvas at its (x, y) position,
then saves as lossless 8-bit grayscale PNG.

Output mirrors the existing _images/ placeholder structure:
    HWDB/{sub}Train/*.dgrl   →  HWDB/{sub}Train_images/*.png
    HWDB/{sub}Test/*.dgrl    →  HWDB/{sub}Test_images/*.png

A sidecar JSONL index is written per sub-dataset split:
    HWDB/{sub}Train_index.jsonl
    HWDB/{sub}Test_index.jsonl

Index schema (one JSON object per line):
    {
        "filename": "001-P16.png",
        "dgrl_source": "HWDB2.0Train/001-P16.dgrl",
        "sub_dataset": "HWDB2.0",
        "split": "train",
        "writer_id": "001",
        "page_height": 3493,
        "page_width": 2482,
        "line_count": 10,
        "char_count": 277
    }

Idempotent: skips any PNG that already exists unless --overwrite is set.

Usage:
    # Dry run — print stats, render nothing
    python scripts/render_casia_hwdb2_pages.py --dry-run

    # Full render (all 5,091 pages)
    python scripts/render_casia_hwdb2_pages.py

    # Render single sub-dataset
    python scripts/render_casia_hwdb2_pages.py --filter HWDB2.0Train

    # Overwrite previously rendered files
    python scripts/render_casia_hwdb2_pages.py --overwrite
"""

from __future__ import annotations

import json
import logging
import re
import struct
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path("/mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2/HWDB")

# DGRL format constants (see parser docstring for full spec)
_IMAGE_META_BYTES = 12  # height(4) + width(4) + line_num(4)
_LINE_POSITION_BYTES = 16  # y(4) + x(4) + h(4) + w(4)
_DEFAULT_CODE_LENGTH = 4

_STRUCT_IMAGE_META = struct.Struct("<III")
_STRUCT_LINE_POSITION = struct.Struct("<IIII")

# Sub-dataset name pattern
_SUB_DATASET_RE = re.compile(r"(HWDB2\.\d)", re.IGNORECASE)
_WRITER_ID_RE = re.compile(r"^(\d+)")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LineRecord:
    """One text line extracted from a DGRL page."""

    x: int
    y: int
    w: int
    h: int
    char_count: int
    text: str
    bitmap: bytes  # h * w grayscale bytes


@dataclass
class PageData:
    """Parsed content of a single DGRL page file."""

    height: int
    width: int
    lines: list[LineRecord] = field(default_factory=list)


@dataclass
class RenderResult:
    """Outcome of rendering one DGRL file."""

    dgrl_path: Path
    png_path: Path
    sub_dataset: str
    split: str
    writer_id: str
    line_count: int
    char_count: int
    skipped: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# DGRL parsing (reads pixel data unlike the annotation parser)
# ---------------------------------------------------------------------------


def _read_file_header(fh: Any, filename: str) -> int | None:
    """Read the DGRL variable-length header and return code_length.

    Args:
        fh: Open binary file handle positioned at start.
        filename: Used only for log messages.

    Returns:
        code_length (bytes per char), or None on malformed header.
    """
    size_raw = fh.read(4)
    if len(size_raw) < 4:
        logger.warning("Header too short in %s", filename)
        return None

    (header_size,) = struct.unpack("<I", size_raw)
    body_len = header_size - 4

    if body_len < 4:
        if body_len > 0:
            fh.seek(body_len, 1)
        return _DEFAULT_CODE_LENGTH

    header_body = fh.read(body_len)
    if len(header_body) < body_len:
        logger.warning("Truncated header body in %s", filename)
        return None

    (code_length,) = struct.unpack("<H", bytes(header_body[-4:-2]))
    if code_length not in {2, 4}:
        code_length = _DEFAULT_CODE_LENGTH

    return code_length


def _decode_labels(label_raw: bytes, char_num: int, code_length: int) -> str:
    """Decode a DGRL label block to a Unicode string (GBK encoding).

    Args:
        label_raw: Raw bytes for all character labels.
        char_num: Number of characters.
        code_length: Bytes per character (2 or 4).

    Returns:
        Decoded Unicode string with null bytes stripped.
    """
    parts: list[str] = []
    for idx in range(char_num):
        chunk = label_raw[idx * code_length : (idx + 1) * code_length]
        code = int.from_bytes(chunk, byteorder="little")
        try:
            char = struct.pack("<I", code).decode("gbk", errors="ignore")
            if char:
                parts.append(char[0])
        except (struct.error, UnicodeDecodeError):
            parts.append("\ufffd")
    return "".join(parts).replace("\x00", "")


def _parse_dgrl_with_pixels(path: Path) -> PageData | None:
    """Parse a DGRL file, loading pixel data for each line.

    Unlike the annotation parser, this function reads the grayscale bitmap
    for each line so we can reconstruct the full page image.

    Args:
        path: Path to the .dgrl file.

    Returns:
        PageData with all line records including pixel data, or None on error.
    """
    try:
        with path.open("rb") as fh:
            code_length = _read_file_header(fh, path.name)
            if code_length is None:
                return None

            meta_raw = fh.read(_IMAGE_META_BYTES)
            if len(meta_raw) < _IMAGE_META_BYTES:
                logger.warning("Truncated image meta in %s", path.name)
                return None

            height, width, line_num = _STRUCT_IMAGE_META.unpack(meta_raw)
            page = PageData(height=height, width=width)

            for _ in range(line_num):
                char_num_raw = fh.read(4)
                if not char_num_raw or len(char_num_raw) < 4:
                    break

                (char_num,) = struct.unpack("<I", char_num_raw)
                label_size = code_length * char_num
                label_raw = fh.read(label_size)
                if len(label_raw) < label_size:
                    break

                text = _decode_labels(label_raw, char_num, code_length)

                pos_raw = fh.read(_LINE_POSITION_BYTES)
                if len(pos_raw) < _LINE_POSITION_BYTES:
                    break

                y, x, h, w = _STRUCT_LINE_POSITION.unpack(pos_raw)
                bitmap_size = h * w

                if bitmap_size <= 0:
                    bitmap = b""
                else:
                    bitmap = fh.read(bitmap_size)
                    if len(bitmap) < bitmap_size:
                        logger.debug(
                            "Truncated bitmap in %s line %d", path.name, len(page.lines)
                        )
                        break

                page.lines.append(
                    LineRecord(
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        char_count=char_num,
                        text=text,
                        bitmap=bitmap,
                    )
                )

    except OSError as exc:
        logger.error("Cannot read %s: %s", path.name, exc)
        return None

    return page


# ---------------------------------------------------------------------------
# Page image assembly
# ---------------------------------------------------------------------------


def _assemble_page_image(page: PageData) -> Image.Image:
    """Composite line bitmaps onto a white canvas to reconstruct the full page.

    Each line's grayscale bitmap is placed at its (x, y) position. Areas not
    covered by any line remain white (paper background).

    Args:
        page: Parsed page data with line records.

    Returns:
        Full-page PIL Image in mode 'L' (8-bit grayscale).
    """
    canvas = Image.new("L", (page.width, page.height), color=255)

    for line in page.lines:
        if not line.bitmap or line.w <= 0 or line.h <= 0:
            continue

        # Clamp coordinates to canvas bounds (defensive)
        x_end = min(line.x + line.w, page.width)
        y_end = min(line.y + line.h, page.height)
        paste_w = x_end - line.x
        paste_h = y_end - line.y

        if paste_w <= 0 or paste_h <= 0:
            continue

        if paste_w == line.w and paste_h == line.h:
            line_img = Image.frombytes("L", (line.w, line.h), line.bitmap)
        else:
            # Line partially outside canvas — crop before pasting
            full_line = Image.frombytes("L", (line.w, line.h), line.bitmap)
            line_img = full_line.crop((0, 0, paste_w, paste_h))

        canvas.paste(line_img, (line.x, line.y))

    return canvas


# ---------------------------------------------------------------------------
# Per-file render worker
# ---------------------------------------------------------------------------


def _detect_sub_dataset_and_split(dgrl_path: Path) -> tuple[str, str]:
    """Infer sub-dataset name and split from directory path.

    Args:
        dgrl_path: Full path to a .dgrl file.

    Returns:
        Tuple of (sub_dataset, split), e.g. ("HWDB2.0", "train").
    """
    sub_dataset = "unknown"
    split = "unknown"

    for part in dgrl_path.parts:
        match = _SUB_DATASET_RE.search(part)
        if match:
            sub_dataset = match.group(1).upper()
        if "Train" in part or "train" in part:
            split = "train"
        elif "Test" in part or "test" in part:
            split = "test"

    return sub_dataset, split


def render_one(dgrl_path: Path, png_path: Path, overwrite: bool) -> RenderResult:
    """Render a single DGRL file to a PNG.

    This function is designed to be called from a process pool worker.

    Args:
        dgrl_path: Source .dgrl file path.
        png_path: Destination .png file path (parent dir must exist).
        overwrite: If False, skip files that already exist.

    Returns:
        RenderResult with outcome details.
    """
    sub_dataset, split = _detect_sub_dataset_and_split(dgrl_path)
    writer_match = _WRITER_ID_RE.match(dgrl_path.stem)
    writer_id = writer_match.group(1) if writer_match else "unknown"

    if png_path.exists() and not overwrite:
        # Count lines/chars from a quick parse for the index without re-rendering
        page = _parse_dgrl_with_pixels(dgrl_path)
        line_count = len(page.lines) if page else 0
        char_count = sum(ln.char_count for ln in page.lines) if page else 0
        return RenderResult(
            dgrl_path=dgrl_path,
            png_path=png_path,
            sub_dataset=sub_dataset,
            split=split,
            writer_id=writer_id,
            line_count=line_count,
            char_count=char_count,
            skipped=True,
        )

    page = _parse_dgrl_with_pixels(dgrl_path)
    if page is None:
        return RenderResult(
            dgrl_path=dgrl_path,
            png_path=png_path,
            sub_dataset=sub_dataset,
            split=split,
            writer_id=writer_id,
            line_count=0,
            char_count=0,
            error="DGRL parse failed",
        )

    line_count = len(page.lines)
    char_count = sum(ln.char_count for ln in page.lines)

    try:
        img = _assemble_page_image(page)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_path, format="PNG", optimize=True)
    except Exception as exc:
        return RenderResult(
            dgrl_path=dgrl_path,
            png_path=png_path,
            sub_dataset=sub_dataset,
            split=split,
            writer_id=writer_id,
            line_count=line_count,
            char_count=char_count,
            error=str(exc),
        )

    return RenderResult(
        dgrl_path=dgrl_path,
        png_path=png_path,
        sub_dataset=sub_dataset,
        split=split,
        writer_id=writer_id,
        line_count=line_count,
        char_count=char_count,
    )


# ---------------------------------------------------------------------------
# Directory discovery
# ---------------------------------------------------------------------------


@dataclass
class SubDatasetJob:
    """Paths and metadata for one sub-dataset directory."""

    dgrl_dir: Path  # e.g. HWDB/HWDB2.0Train/
    images_dir: Path  # e.g. HWDB/HWDB2.0Train_images/
    index_path: Path  # e.g. HWDB/HWDB2.0Train_index.jsonl
    sub_name: str  # e.g. "HWDB2.0Train"


def discover_jobs(data_dir: Path, filter_name: str | None) -> list[SubDatasetJob]:
    """Discover all sub-dataset DGRL directories under data_dir.

    Args:
        data_dir: Root HWDB directory.
        filter_name: If set, only process matching directory names.

    Returns:
        List of SubDatasetJob for each matched sub-dataset.
    """
    jobs: list[SubDatasetJob] = []
    for dgrl_dir in sorted(data_dir.iterdir()):
        if not dgrl_dir.is_dir():
            continue
        # Skip _images and _label directories
        if dgrl_dir.name.endswith("_images") or dgrl_dir.name.endswith("_label"):
            continue
        if filter_name and filter_name.lower() not in dgrl_dir.name.lower():
            continue

        images_dir = data_dir / f"{dgrl_dir.name}_images"
        index_path = data_dir / f"{dgrl_dir.name}_index.jsonl"
        jobs.append(
            SubDatasetJob(
                dgrl_dir=dgrl_dir,
                images_dir=images_dir,
                index_path=index_path,
                sub_name=dgrl_dir.name,
            )
        )

    return jobs


# ---------------------------------------------------------------------------
# Index writing
# ---------------------------------------------------------------------------


def _write_index(results: list[RenderResult], index_path: Path, data_dir: Path) -> None:
    """Write a JSONL sidecar index from render results.

    Args:
        results: Completed render results for one sub-dataset.
        index_path: Output .jsonl file path.
        data_dir: HWDB root (used for relative path computation).
    """
    with index_path.open("w", encoding="utf-8") as fh:
        for r in sorted(results, key=lambda x: x.png_path.name):
            if r.error:
                continue
            sub_dataset, _ = _detect_sub_dataset_and_split(r.dgrl_path)
            record = {
                "filename": r.png_path.name,
                "dgrl_source": str(r.dgrl_path.relative_to(data_dir)),
                "sub_dataset": sub_dataset,
                "split": r.split,
                "writer_id": r.writer_id,
                "line_count": r.line_count,
                "char_count": r.char_count,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for DGRL → PNG rendering."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Render CASIA-HWDB2 DGRL pages to lossless PNG images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Path to the HWDB/ directory containing HWDB2.x sub-dataset folders.",
    )
    parser.add_argument(
        "--filter",
        metavar="NAME",
        default=None,
        help="Only process sub-datasets whose directory name contains NAME (e.g. HWDB2.0Train).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel worker processes (default: 4).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-render and overwrite PNG files that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be rendered without writing any files.",
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

    jobs = discover_jobs(data_dir, args.filter)
    if not jobs:
        logger.error("No sub-dataset directories found under %s", data_dir)
        sys.exit(1)

    # Build full work list
    work_items: list[tuple[SubDatasetJob, Path, Path]] = []
    for job in jobs:
        dgrl_files = sorted(job.dgrl_dir.glob("*.dgrl"))
        for dgrl_path in dgrl_files:
            png_path = job.images_dir / f"{dgrl_path.stem}.png"
            work_items.append((job, dgrl_path, png_path))

    total = len(work_items)
    logger.info("Found %d DGRL files across %d sub-datasets", total, len(jobs))

    if args.dry_run:
        already_done = sum(1 for _, _, png in work_items if png.exists())
        logger.info(
            "Dry run — would render %d files (%d already exist)", total, already_done
        )
        for job in jobs:
            count = sum(1 for j, _, _ in work_items if j is job)
            logger.info("  %s: %d pages → %s", job.sub_name, count, job.images_dir)
        return

    # Group results by job for index writing
    job_results: dict[str, list[RenderResult]] = {j.sub_name: [] for j in jobs}
    job_lookup: dict[str, SubDatasetJob] = {j.sub_name: j for j in jobs}

    n_rendered = 0
    n_skipped = 0
    n_errors = 0

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(render_one, dgrl, png, args.overwrite): job
                for job, dgrl, png in work_items
            }
            with tqdm(total=total, unit="page", desc="Rendering") as pbar:
                for future in as_completed(futures):
                    job = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        logger.error("Worker crashed: %s", exc)
                        n_errors += 1
                        pbar.update(1)
                        continue

                    job_results[job.sub_name].append(result)
                    if result.error:
                        n_errors += 1
                        logger.warning(
                            "Error rendering %s: %s",
                            result.dgrl_path.name,
                            result.error,
                        )
                    elif result.skipped:
                        n_skipped += 1
                    else:
                        n_rendered += 1
                    pbar.update(1)
    else:
        with tqdm(total=total, unit="page", desc="Rendering") as pbar:
            for job, dgrl, png in work_items:
                result = render_one(dgrl, png, args.overwrite)
                job_results[job.sub_name].append(result)
                if result.error:
                    n_errors += 1
                    logger.warning(
                        "Error rendering %s: %s", result.dgrl_path.name, result.error
                    )
                elif result.skipped:
                    n_skipped += 1
                else:
                    n_rendered += 1
                pbar.update(1)

    # Write per-sub-dataset indexes
    logger.info("Writing sidecar index files...")
    for sub_name, results in job_results.items():
        job = job_lookup[sub_name]
        _write_index(results, job.index_path, data_dir)
        logger.info("  %s: %s", sub_name, job.index_path)

    logger.info(
        "Done — rendered=%d  skipped=%d  errors=%d",
        n_rendered,
        n_skipped,
        n_errors,
    )
    if n_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
