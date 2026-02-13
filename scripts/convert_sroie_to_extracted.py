#!/usr/bin/env python3
"""Convert SROIE annotations to our extracted OCR+layout format.

SROIE has per-receipt JSON annotations with text regions (quad bboxes + text)
and named entities (company, date, address, total).

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

BATCH_SIZE = 200

CATEGORIES = [
    {"id": 0, "name": "text_region"},
]


def quad_to_coco_bbox(bbox_quad: list[list[int]]) -> tuple[float, ...]:
    """Convert SROIE quad coordinates to COCO [x, y, w, h].

    SROIE bbox_quad format: [[x1,x2,x3,x4], [y1,y2,y3,y4]]
    """
    if len(bbox_quad) != 2 or len(bbox_quad[0]) < 4 or len(bbox_quad[1]) < 4:
        return (0.0, 0.0, 0.0, 0.0)

    xs = bbox_quad[0]
    ys = bbox_quad[1]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)
    return (float(x_min), float(y_min), float(x_max - x_min), float(y_max - y_min))


def reconstruct_page_text(text_regions: list[dict]) -> str:
    """Reconstruct reading-order text from text regions."""
    valid = []
    for region in text_regions:
        text = region.get("text", "").strip()
        bbox_quad = region.get("bbox_quad")
        if text and bbox_quad:
            x, y, _, _ = quad_to_coco_bbox(bbox_quad)
            valid.append({"text": text, "y": y, "x": x})

    if not valid:
        return ""

    valid.sort(key=lambda r: (r["y"], r["x"]))

    # Group into lines by y-proximity (within 8px for receipts)
    lines: list[list[dict]] = []
    current_line: list[dict] = [valid[0]]
    current_y = valid[0]["y"]

    for region in valid[1:]:
        if abs(region["y"] - current_y) <= 8:
            current_line.append(region)
        else:
            current_line.sort(key=lambda r: r["x"])
            lines.append(current_line)
            current_line = [region]
            current_y = region["y"]

    current_line.sort(key=lambda r: r["x"])
    lines.append(current_line)

    return "\n".join(" ".join(r["text"] for r in line) for line in lines)


def build_annotations(text_regions: list[dict]) -> list[dict]:
    """Create COCO-style annotations from text regions."""
    annotations = []
    for region in text_regions:
        bbox_quad = region.get("bbox_quad")
        if not bbox_quad:
            continue

        x, y, w, h = quad_to_coco_bbox(bbox_quad)
        if w <= 0 or h <= 0:
            continue

        annotation = {
            "bbox": [x, y, w, h],
            "coord_origin": "top-left",
            "category_name": "text_region",
            "category_id": 0,
            "area": float(w * h),
        }
        text = region.get("text", "").strip()
        if text:
            annotation["text"] = text[:200]
        annotations.append(annotation)

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
            "description": f"SROIE GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "sroie-gt",
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


def main() -> None:
    base_dir = Path("/mnt/e/image_detection/01_base_data/forms/sroie_icdar2019")
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/sroie")

    dry_run = "--dry-run" in sys.argv
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0

    for split in ("train", "test"):
        ann_dir = base_dir / split / "annotations"
        if not ann_dir.exists():
            print(f"Skip {split}: {ann_dir} not found")
            continue

        json_files = sorted(ann_dir.glob("*.json"))
        print(f"{split}: {len(json_files)} annotation files")

        for json_path in json_files:
            with open(json_path) as f:
                data = json.load(f)

            text_regions = data.get("text_regions", [])
            image_name = data.get("image_id", json_path.stem) + ".jpg"

            text = reconstruct_page_text(text_regions)
            annotations = build_annotations(text_regions)
            total_annotations += len(annotations)

            batch_results.append(
                {
                    "filename": image_name,
                    "split": split,
                    "text": text,
                    "annotations": annotations,
                }
            )

            if len(batch_results) >= BATCH_SIZE:
                if not dry_run:
                    save_batch(batch_results, batch_num, output_dir, "sroie")
                total_processed += len(batch_results)
                batch_results = []
                batch_num += 1

    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "sroie")
        total_processed += len(batch_results)
        batch_num += 1

    print(
        f"\nDone: {total_processed} receipts, {batch_num} batches, "
        f"{total_annotations} annotations"
    )
    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
