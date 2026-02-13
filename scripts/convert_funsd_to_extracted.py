#!/usr/bin/env python3
"""Convert FUNSD annotations to our extracted OCR+layout format.

FUNSD has per-form JSON annotations with entity-level text (question/answer/
header/other) and word-level bounding boxes in [x1,y1,x2,y2] format.

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

BATCH_SIZE = 200

CATEGORIES = [
    {"id": 0, "name": "question"},
    {"id": 1, "name": "answer"},
    {"id": 2, "name": "header"},
    {"id": 3, "name": "other"},
]

LABEL_MAP = {"question": 0, "answer": 1, "header": 2, "other": 3}


def reconstruct_page_text(form_entities: list[dict]) -> str:
    """Reconstruct reading-order text from form entities.

    Sorts entities by y then x position, joins with newlines.
    """
    valid = []
    for entity in form_entities:
        text = entity.get("text", "").strip()
        box = entity.get("box")
        if text and box and len(box) == 4:
            valid.append({"text": text, "box": box})

    if not valid:
        return ""

    # Sort by y then x
    valid.sort(key=lambda e: (e["box"][1], e["box"][0]))

    # Group into lines by y-proximity (within 10px)
    lines: list[list[dict]] = []
    current_line: list[dict] = [valid[0]]
    current_y = valid[0]["box"][1]

    for entity in valid[1:]:
        if abs(entity["box"][1] - current_y) <= 10:
            current_line.append(entity)
        else:
            current_line.sort(key=lambda e: e["box"][0])
            lines.append(current_line)
            current_line = [entity]
            current_y = entity["box"][1]

    current_line.sort(key=lambda e: e["box"][0])
    lines.append(current_line)

    return "\n".join(" ".join(e["text"] for e in line) for line in lines)


def build_annotations(form_entities: list[dict]) -> list[dict]:
    """Create COCO-style annotations from FUNSD entities."""
    annotations = []
    for ann_id, entity in enumerate(form_entities):
        box = entity.get("box")
        if not box or len(box) != 4:
            continue

        x1, y1, x2, y2 = box
        width = x2 - x1
        height = y2 - y1
        label = entity.get("label", "other")

        annotation = {
            "bbox": [float(x1), float(y1), float(width), float(height)],
            "bbox_raw": [float(x1), float(y1), float(x2), float(y2)],
            "coord_origin": "top-left",
            "category_name": label,
            "category_id": LABEL_MAP.get(label, 3),
            "area": float(width * height),
        }
        text = entity.get("text", "").strip()
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
            "description": f"FUNSD GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "funsd-gt",
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
    base_dir = Path("/mnt/e/image_detection/01_base_data/forms/funsd")
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/funsd")

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

            form_entities = data.get("form", [])
            image_name = json_path.stem + ".png"

            text = reconstruct_page_text(form_entities)
            annotations = build_annotations(form_entities)
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
                    save_batch(batch_results, batch_num, output_dir, "funsd")
                total_processed += len(batch_results)
                batch_results = []
                batch_num += 1

    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "funsd")
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
