#!/usr/bin/env python3
"""Convert MLT-19 TXT annotations to our extracted OCR+layout format.

MLT-19 has per-image TXT files with word-level annotations:
  x1,y1,x2,y2,x3,y3,x4,y4,script_class,text_content

Only training split has GT (10K images). Test split has no GT.

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

BATCH_SIZE = 200

CATEGORIES = [
    {"id": 0, "name": "Latin"},
    {"id": 1, "name": "Arabic"},
    {"id": 2, "name": "Chinese"},
    {"id": 3, "name": "Japanese"},
    {"id": 4, "name": "Korean"},
    {"id": 5, "name": "Bangla"},
    {"id": 6, "name": "Hindi"},
    {"id": 7, "name": "Symbols"},
    {"id": 8, "name": "Mixed"},
    {"id": 9, "name": "None"},
]

SCRIPT_MAP = {cat["name"]: cat["id"] for cat in CATEGORIES}


def parse_gt_line(line: str) -> dict | None:
    """Parse a single MLT-19 GT line.

    Format: x1,y1,x2,y2,x3,y3,x4,y4,script,text
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(",")
    if len(parts) < 10:
        return None

    try:
        coords = [float(p) for p in parts[:8]]
    except ValueError:
        return None

    script = parts[8]
    text = ",".join(parts[9:])  # Text may contain commas

    xs = [coords[0], coords[2], coords[4], coords[6]]
    ys = [coords[1], coords[3], coords[5], coords[7]]

    x_min = min(xs)
    y_min = min(ys)
    width = max(xs) - x_min
    height = max(ys) - y_min

    return {
        "text": text,
        "script": script,
        "bbox": [x_min, y_min, width, height],
        "y": y_min,
        "x": x_min,
    }


def reconstruct_page_text(words: list[dict]) -> str:
    """Reconstruct reading-order text from word annotations."""
    # Filter out illegible markers
    valid = [w for w in words if w["text"] != "###" and w["text"].strip()]
    if not valid:
        return ""

    valid.sort(key=lambda w: (w["y"], w["x"]))

    # Group into lines by y-proximity (within 15px for scene text)
    lines: list[list[dict]] = []
    current_line: list[dict] = [valid[0]]
    current_y = valid[0]["y"]

    for word in valid[1:]:
        if abs(word["y"] - current_y) <= 15:
            current_line.append(word)
        else:
            current_line.sort(key=lambda w: w["x"])
            lines.append(current_line)
            current_line = [word]
            current_y = word["y"]

    current_line.sort(key=lambda w: w["x"])
    lines.append(current_line)

    return "\n".join(" ".join(w["text"] for w in line) for line in lines)


def build_annotations(words: list[dict]) -> list[dict]:
    """Create COCO-style annotations from word-level data."""
    annotations = []
    for word in words:
        bbox = word["bbox"]
        if bbox[2] <= 0 or bbox[3] <= 0:
            continue

        script = word["script"]
        annotation = {
            "bbox": [float(v) for v in bbox],
            "coord_origin": "top-left",
            "category_name": script,
            "category_id": SCRIPT_MAP.get(script, 9),
            "area": float(bbox[2] * bbox[3]),
        }
        text = word["text"]
        if text.strip() and text != "###":
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
            "description": f"MLT-19 GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "mlt19-gt",
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
    base_dir = Path("/mnt/e/image_detection/01_base_data/language/mlt19")
    gt_dir = base_dir / "TrainGT" / "TrainGT"
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/mlt19")

    dry_run = "--dry-run" in sys.argv

    if not gt_dir.exists():
        print(f"GT dir not found: {gt_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    gt_files = sorted(gt_dir.glob("*.txt"))
    print(f"Found {len(gt_files)} GT files")
    print(f"Output to {output_dir}/")

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0
    total_text_chars = 0

    for gt_path in gt_files:
        # Image name: tr_img_00001.txt -> tr_img_00001.jpg
        image_name = gt_path.stem + ".jpg"

        with open(gt_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        words = []
        for line in lines:
            parsed = parse_gt_line(line)
            if parsed:
                words.append(parsed)

        text = reconstruct_page_text(words)
        total_text_chars += len(text)
        annotations = build_annotations(words)
        total_annotations += len(annotations)

        batch_results.append(
            {
                "filename": image_name,
                "split": "train",
                "text": text,
                "annotations": annotations,
            }
        )

        if len(batch_results) >= BATCH_SIZE:
            if not dry_run:
                save_batch(batch_results, batch_num, output_dir, "mlt19")
            total_processed += len(batch_results)
            if (batch_num + 1) % 10 == 0:
                print(
                    f"  Batch {batch_num + 1}: {total_processed} processed, "
                    f"{total_annotations} annotations"
                )
            batch_results = []
            batch_num += 1

    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "mlt19")
        total_processed += len(batch_results)
        batch_num += 1

    print(
        f"\nDone: {total_processed} images, {batch_num} batches, "
        f"{total_annotations} annotations, {total_text_chars:,} chars"
    )
    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
