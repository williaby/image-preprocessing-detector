"""Render Kleister Charity PDFs to page images using PyMuPDF.

Converts 3,414 PDF documents from the Kleister Charity dataset into
individual page images (PNG format, 300 DPI) suitable for Layer 1 scanning.

Dataset Structure After Rendering:
    kleister-charity/
        documents/                    # Original PDFs (git-annex)
        rendered_images/              # Output directory
            train/
                {md5}_p{page:03d}.png
            dev-0/
                {md5}_p{page:03d}.png
            test-A/
                {md5}_p{page:03d}.png

Usage:
    PYTHONPATH=. uv run python scripts/render_kleister_charity_pdfs.py
    PYTHONPATH=. uv run python scripts/render_kleister_charity_pdfs.py --split train
    PYTHONPATH=. uv run python scripts/render_kleister_charity_pdfs.py --dpi 200 --max-pages 5
"""

from __future__ import annotations

import argparse
import json
import lzma
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF

DATASET_ROOT = Path(
    os.environ.get(
        "KLEISTER_DATA_DIR",
        "/mnt/e/image_detection/01_base_data/documents/kleister-charity",
    )
)
DOCUMENTS_DIR = DATASET_ROOT / "documents"
OUTPUT_DIR = DATASET_ROOT / "rendered_images"
DEFAULT_DPI = 300
SPLITS = ["train", "dev-0", "test-A"]


def get_split_documents(split: str) -> list[str]:
    """Read document filenames from a split's in.tsv.xz file.

    Args:
        split: Split name (train, dev-0, test-A)

    Returns:
        List of PDF filenames (e.g., ['abc123.pdf', ...])
    """
    tsv_path = DATASET_ROOT / split / "in.tsv.xz"
    if not tsv_path.exists():
        print(f"  WARNING: {tsv_path} not found, skipping split")
        return []

    docs = []
    with lzma.open(tsv_path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                docs.append(parts[0])
    return docs


def get_split_labels(split: str) -> list[str]:
    """Read expected labels from a split's expected.tsv file.

    Args:
        split: Split name

    Returns:
        List of label strings (key=value pairs)
    """
    expected_path = DATASET_ROOT / split / "expected.tsv"
    if not expected_path.exists():
        return []

    labels = []
    with open(expected_path, encoding="utf-8") as f:
        for line in f:
            labels.append(line.strip())
    return labels


def render_pdf(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = DEFAULT_DPI,
    max_pages: int | None = None,
) -> list[Path]:
    """Render a PDF to individual page images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to write page images
        dpi: Resolution for rendering (default 300)
        max_pages: Maximum number of pages to render (None = all)

    Returns:
        List of paths to rendered images
    """
    rendered = []
    doc_id = pdf_path.stem  # MD5 hash filename

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        print(f"  ERROR: Could not open {pdf_path.name}: {exc}")
        return rendered

    try:
        page_count = min(doc.page_count, max_pages) if max_pages else doc.page_count
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_idx in range(page_count):
            output_path = output_dir / f"{doc_id}_p{page_idx + 1:03d}.png"
            if output_path.exists():
                rendered.append(output_path)
                continue

            try:
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=matrix)
                pix.save(str(output_path))
                rendered.append(output_path)
            except Exception as exc:
                print(f"  ERROR: Page {page_idx + 1} of {pdf_path.name}: {exc}")
    finally:
        doc.close()

    return rendered


def build_labels_index(split: str, docs: list[str]) -> dict[str, dict[str, str]]:
    """Build a mapping from document ID to parsed key=value labels.

    Args:
        split: Split name
        docs: List of document filenames for this split

    Returns:
        Dict mapping doc_id (MD5 stem) to dict of label key->value
    """
    labels_list = get_split_labels(split)
    if labels_list and len(labels_list) != len(docs):
        msg = (
            f"Document/label count mismatch for split '{split}': "
            f"{len(docs)} documents vs {len(labels_list)} labels"
        )
        raise ValueError(msg)
    index: dict[str, dict[str, str]] = {}

    for doc_name, label_str in zip(docs, labels_list, strict=False):
        doc_id = Path(doc_name).stem
        parsed: dict[str, str] = {}
        if label_str:
            for pair in label_str.split(" "):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    parsed[key] = value.replace("_", " ")
        index[doc_id] = parsed

    return index


def main() -> None:
    """Render Kleister Charity PDFs to page images."""
    parser = argparse.ArgumentParser(description="Render Kleister Charity PDFs")
    parser.add_argument(
        "--split",
        choices=SPLITS,
        help="Only render a specific split (default: all)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Rendering DPI (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum pages per PDF to render (default: all)",
    )
    parser.add_argument(
        "--save-labels",
        action="store_true",
        help="Save per-document labels as JSON sidecar files",
    )
    args = parser.parse_args()

    splits = [args.split] if args.split else SPLITS

    if not DOCUMENTS_DIR.exists():
        print(f"ERROR: Documents directory not found: {DOCUMENTS_DIR}")
        sys.exit(1)

    total_rendered = 0
    total_skipped = 0
    total_missing = 0

    for split in splits:
        docs = get_split_documents(split)
        if not docs:
            continue

        split_dir = OUTPUT_DIR / split
        split_dir.mkdir(parents=True, exist_ok=True)

        labels_index = build_labels_index(split, docs) if args.save_labels else {}

        print(f"\n[{split}] {len(docs)} documents")
        rendered_in_split = 0
        missing = 0

        for doc_name in docs:
            pdf_path = DOCUMENTS_DIR / doc_name
            if not pdf_path.exists():
                # Check if it's a broken symlink (git-annex not fetched)
                if pdf_path.is_symlink():
                    total_skipped += 1
                    missing += 1
                    continue
                total_skipped += 1
                missing += 1
                continue

            pages = render_pdf(
                pdf_path, split_dir, dpi=args.dpi, max_pages=args.max_pages
            )
            rendered_in_split += len(pages)

            # Save labels sidecar if requested
            if args.save_labels and pages:
                doc_id = Path(doc_name).stem
                if doc_id in labels_index:
                    sidecar = split_dir / f"{doc_id}_labels.json"
                    with open(sidecar, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "doc_id": doc_id,
                                "split": split,
                                "page_count": len(pages),
                                "labels": labels_index[doc_id],
                            },
                            f,
                            indent=2,
                        )

        total_rendered += rendered_in_split
        if missing:
            total_missing += missing
            print(f"  WARNING: {missing} PDFs not available (git-annex not fetched?)")
        print(f"  Rendered {rendered_in_split} page images")

    print(f"\n{'=' * 60}")
    print(f"Total rendered: {total_rendered} page images")
    if total_skipped:
        print(f"Skipped: {total_skipped} (missing PDFs)")
    if total_missing:
        print(f"Missing PDFs: {total_missing}")


if __name__ == "__main__":
    main()
