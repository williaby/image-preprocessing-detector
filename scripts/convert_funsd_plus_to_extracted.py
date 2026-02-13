#!/usr/bin/env python3
"""Convert FUNSD+ Arrow annotations to our extracted OCR+layout format.

FUNSD+ uses HuggingFace Arrow format with word-level text, bboxes in
[x,y,w,h] format, labels (question/answer/header/other), entity grouping,
and key-value linking.

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

import pyarrow.ipc as ipc

BATCH_SIZE = 200

CATEGORIES = [
    {"id": 0, "name": "question"},
    {"id": 1, "name": "answer"},
    {"id": 2, "name": "header"},
    {"id": 3, "name": "other"},
]


def reconstruct_page_text(words: list[str], bboxes: list[list[float]]) -> str:
    """Reconstruct reading-order text from word-level annotations."""
    if not words or not bboxes:
        return ""

    valid = []
    for word, bbox in zip(words, bboxes):
        if word.strip() and bbox and len(bbox) == 4:
            valid.append({"text": word, "bbox": bbox})

    if not valid:
        return ""

    # Sort by y then x (bboxes are [x, y, w, h])
    valid.sort(key=lambda w: (w["bbox"][1], w["bbox"][0]))

    # Group into lines by y-proximity (within 5px)
    lines: list[list[dict]] = []
    current_line: list[dict] = [valid[0]]
    current_y = valid[0]["bbox"][1]

    for word in valid[1:]:
        if abs(word["bbox"][1] - current_y) <= 5:
            current_line.append(word)
        else:
            current_line.sort(key=lambda w: w["bbox"][0])
            lines.append(current_line)
            current_line = [word]
            current_y = word["bbox"][1]

    current_line.sort(key=lambda w: w["bbox"][0])
    lines.append(current_line)

    return "\n".join(" ".join(w["text"] for w in line) for line in lines)


def build_annotations(
    words: list[str],
    bboxes: list[list[float]],
    labels: list[int],
) -> list[dict]:
    """Create COCO-style annotations from word-level data."""
    annotations = []
    for word, bbox, label in zip(words, bboxes, labels):
        if not bbox or len(bbox) != 4:
            continue

        # FUNSD+ bboxes are already [x, y, w, h]
        x, y, w, h = bbox

        annotation = {
            "bbox": [float(x), float(y), float(w), float(h)],
            "coord_origin": "top-left",
            "category_id": int(label),
            "category_name": CATEGORIES[min(label, 3)]["name"],
            "area": float(w * h),
        }
        if word.strip():
            annotation["text"] = word.strip()[:200]
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
            "description": f"FUNSD+ GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "funsd-plus-gt",
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
    base_dir = Path("/mnt/e/image_detection/01_base_data/forms/funsd_plus")
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/funsd_plus")

    dry_run = "--dry-run" in sys.argv
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0

    for split in ("train", "test"):
        split_dir = base_dir / split
        arrow_files = sorted(split_dir.glob("*.arrow"))
        if not arrow_files:
            print(f"Skip {split}: no arrow files in {split_dir}")
            continue

        for arrow_path in arrow_files:
            print(f"Reading {split}/{arrow_path.name}...")
            with open(arrow_path, "rb") as f:
                reader = ipc.open_stream(f)
                table = reader.read_all()

            num_rows = len(table)
            print(f"  {num_rows} forms")

            for row_idx in range(num_rows):
                image_info = table["image"][row_idx].as_py()
                image_path = image_info.get("path", f"form_{row_idx}.png")
                image_name = Path(image_path).name

                words = table["words"][row_idx].as_py()
                bboxes = table["bboxes"][row_idx].as_py()
                labels = table["labels"][row_idx].as_py()

                text = reconstruct_page_text(words, bboxes)
                annotations = build_annotations(words, bboxes, labels)
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
                        save_batch(batch_results, batch_num, output_dir, "funsd_plus")
                    total_processed += len(batch_results)
                    batch_results = []
                    batch_num += 1

    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "funsd_plus")
        total_processed += len(batch_results)
        batch_num += 1

    print(
        f"\nDone: {total_processed} forms, {batch_num} batches, "
        f"{total_annotations} annotations"
    )
    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
