#!/usr/bin/env python3
"""Convert HierText annotations to our extracted OCR+layout format.

HierText has hierarchical annotations: paragraph → line → word.
Each level has polygon vertices and text. Lines and words have
handwritten/vertical flags.

Annotation files are single JSON objects (despite .jsonl extension).

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

BATCH_SIZE = 200

CATEGORIES = [
    {"id": 0, "name": "paragraph"},
    {"id": 1, "name": "line"},
    {"id": 2, "name": "word"},
]


def polygon_to_coco_bbox(
    vertices: list[list[float]],
) -> tuple[float, float, float, float]:
    """Convert polygon vertices to COCO [x, y, w, h] bbox."""
    if not vertices:
        return (0.0, 0.0, 0.0, 0.0)

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    x_min = min(xs)
    y_min = min(ys)
    return (x_min, y_min, max(xs) - x_min, max(ys) - y_min)


def reconstruct_page_text(paragraphs: list[dict]) -> str:
    """Reconstruct reading-order text from hierarchical annotations.

    Uses line-level text (which is the concatenation of word texts).
    """
    all_lines: list[dict] = []

    for para in paragraphs:
        if not para.get("legible", True):
            continue
        for line in para.get("lines", []):
            if not line.get("legible", True):
                continue
            text = line.get("text", "").strip()
            if not text:
                continue
            vertices = line.get("vertices", [])
            if not vertices:
                continue
            x, y, _w, _h = polygon_to_coco_bbox(vertices)
            all_lines.append({"text": text, "y": y, "x": x})

    if not all_lines:
        return ""

    # Sort by y then x for reading order
    all_lines.sort(key=lambda ln: (ln["y"], ln["x"]))
    return "\n".join(ln["text"] for ln in all_lines)


def _build_line_annotation(line: dict) -> dict | None:
    """Build a COCO-style line-level annotation from a HierText line.

    Args:
        line: HierText line dict with vertices, text, and handwritten fields.

    Returns:
        Annotation dict, or None if vertices are missing or have zero area.
    """
    line_verts = line.get("vertices", [])
    if not line_verts:
        return None

    x, y, w, h = polygon_to_coco_bbox(line_verts)
    if w <= 0 or h <= 0:
        return None

    ann: dict = {
        "bbox": [x, y, w, h],
        "coord_origin": "top-left",
        "category_name": "line",
        "category_id": 1,
        "area": float(w * h),
    }
    line_text = line.get("text", "").strip()
    if line_text:
        ann["text"] = line_text[:200]
    if line.get("handwritten", False):
        ann["handwritten"] = True
    return ann


def _build_word_annotation(word: dict) -> dict | None:
    """Build a COCO-style word-level annotation from a HierText word.

    Args:
        word: HierText word dict with vertices, text, and handwritten fields.

    Returns:
        Annotation dict, or None if vertices are missing or have zero area.
    """
    word_verts = word.get("vertices", [])
    if not word_verts:
        return None

    x, y, w, h = polygon_to_coco_bbox(word_verts)
    if w <= 0 or h <= 0:
        return None

    ann: dict = {
        "bbox": [x, y, w, h],
        "coord_origin": "top-left",
        "category_name": "word",
        "category_id": 2,
        "area": float(w * h),
    }
    word_text = word.get("text", "").strip()
    if word_text:
        ann["text"] = word_text[:200]
    if word.get("handwritten", False):
        ann["handwritten"] = True
    return ann


def build_annotations(paragraphs: list[dict]) -> list[dict]:
    """Create COCO-style annotations at word and line level."""
    annotations = []

    for para in paragraphs:
        if not para.get("legible", True):
            continue

        for line in para.get("lines", []):
            if not line.get("legible", True):
                continue

            line_ann = _build_line_annotation(line)
            if line_ann:
                annotations.append(line_ann)

            for word in line.get("words", []):
                if not word.get("legible", True):
                    continue
                word_ann = _build_word_annotation(word)
                if word_ann:
                    annotations.append(word_ann)

    return annotations


def save_batch(
    batch_results: list[dict],
    batch_num: int,
    output_dir: Path,
    dataset_name: str,
) -> None:
    """Save a batch in the same format as process_datasets.py output."""
    ocr_path = output_dir / f"ocr_batch_{batch_num}.jsonl"
    with open(ocr_path, "w") as f:
        f.writelines(
            json.dumps(
                {
                    "source": r["filename"],
                    "text": r["text"],
                    "confidence": 1.0,
                    "tables_found": 0,
                    "processing_time_ms": 0,
                    "success": True,
                    "error": None,
                }
            )
            + "\n"
            for r in batch_results
        )

    layout_data = {
        "info": {
            "description": f"HierText GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "hiertext-gt",
            "batch": batch_num,
        },
        "categories": CATEGORIES,
        "images": [],
        "annotations": [],
    }

    global_ann_id = 0
    for img_id, r in enumerate(batch_results):
        if r["annotations"]:
            layout_data["images"].append(
                {
                    "id": img_id,
                    "file_name": r["filename"],
                    "gcs_path": r["filename"],
                }
            )
            for ann in r["annotations"]:
                ann_copy = dict(ann)
                ann_copy["image_id"] = img_id
                ann_copy["id"] = global_ann_id
                layout_data["annotations"].append(ann_copy)
                global_ann_id += 1

    layout_path = output_dir / f"layout_batch_{batch_num}.json"
    with open(layout_path, "w") as f:
        json.dump(layout_data, f, indent=2)


def _flush_batch(
    batch_results: list[dict],
    batch_num: int,
    output_dir: Path,
    dry_run: bool,
    total_processed: int,
) -> tuple[int, int]:
    """Save current batch and return updated counters.

    Args:
        batch_results: Current batch of results to save.
        batch_num: Current batch number.
        output_dir: Output directory.
        dry_run: Whether this is a dry run.
        total_processed: Running total of processed images.

    Returns:
        Tuple of (updated total_processed, updated batch_num).
    """
    if not dry_run:
        save_batch(batch_results, batch_num, output_dir, "hiertext")
    total_processed += len(batch_results)
    if (batch_num + 1) % 10 == 0:
        print(f"  Batch {batch_num + 1}: {total_processed} processed")
    return total_processed, batch_num + 1


def main() -> None:
    base_dir = Path("/mnt/e/image_detection/01_base_data/text_detection/hiertext")
    gt_dir = base_dir / "gt"
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/hiertext")

    dry_run = "--dry-run" in sys.argv

    if not gt_dir.exists():
        print(f"GT dir not found: {gt_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0
    total_text_chars = 0

    for split in ("train", "validation", "test"):
        gt_path = gt_dir / f"{split}.jsonl"
        if not gt_path.exists():
            print(f"Skip {split}: {gt_path} not found")
            continue

        print(f"Loading {split} ({gt_path.stat().st_size / 1e6:.0f} MB)...")

        with open(gt_path) as f:
            data = json.load(f)

        image_annotations = data.get("annotations", [])
        print(f"  {len(image_annotations)} images")

        for img_ann in image_annotations:
            image_id = img_ann.get("image_id", "")
            paragraphs = img_ann.get("paragraphs", [])

            text = reconstruct_page_text(paragraphs)
            total_text_chars += len(text)
            annotations = build_annotations(paragraphs)
            total_annotations += len(annotations)

            batch_results.append(
                {
                    "filename": f"{image_id}.jpg",
                    "split": split,
                    "text": text,
                    "annotations": annotations,
                }
            )

            if len(batch_results) >= BATCH_SIZE:
                total_processed, batch_num = _flush_batch(
                    batch_results,
                    batch_num,
                    output_dir,
                    dry_run,
                    total_processed,
                )
                batch_results = []

    if batch_results:
        total_processed, batch_num = _flush_batch(
            batch_results,
            batch_num,
            output_dir,
            dry_run,
            total_processed,
        )

    print(
        f"\nDone: {total_processed} images, {batch_num} batches, "
        f"{total_annotations} annotations, {total_text_chars:,} chars"
    )
    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
