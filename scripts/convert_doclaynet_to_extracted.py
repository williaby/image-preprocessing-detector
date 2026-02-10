#!/usr/bin/env python3
"""Convert DocLayNet GT annotations to our extracted OCR+layout format.

Combines two DocLayNet annotation sources:
  1. Per-document JSON files (ground_truth/json/): Cell-level text + font metadata
  2. COCO annotations (ground_truth/coco/): 11 semantic layout categories

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

BATCH_SIZE = 200

# DocLayNet 11 semantic categories (from COCO annotations)
CATEGORIES = [
    {"id": 1, "name": "Caption"},
    {"id": 2, "name": "Footnote"},
    {"id": 3, "name": "Formula"},
    {"id": 4, "name": "List-item"},
    {"id": 5, "name": "Page-footer"},
    {"id": 6, "name": "Page-header"},
    {"id": 7, "name": "Picture"},
    {"id": 8, "name": "Section-header"},
    {"id": 9, "name": "Table"},
    {"id": 10, "name": "Text"},
    {"id": 11, "name": "Title"},
]


def reconstruct_page_text(cells: list[dict]) -> str:
    """Reconstruct reading-order text from cell-level annotations.

    Sorts cells by y-position (rows) then x-position (columns),
    groups into lines by y-proximity, joins with spaces and newlines.
    """
    valid_cells = []
    for cell in cells:
        text = cell.get("text", "").strip()
        bbox = cell.get("bbox")
        if text and bbox and len(bbox) == 4:
            valid_cells.append({"text": text, "bbox": bbox})

    if not valid_cells:
        return ""

    # Sort by y then x (COCO format: [x, y, w, h])
    valid_cells.sort(key=lambda c: (c["bbox"][1], c["bbox"][0]))

    # Group into lines (cells within 3px y-distance are same line)
    # DocLayNet cells are word-level, so tighter threshold than PubTabNet
    lines: list[list[dict]] = []
    current_line: list[dict] = [valid_cells[0]]
    current_y = valid_cells[0]["bbox"][1]

    for cell in valid_cells[1:]:
        if abs(cell["bbox"][1] - current_y) <= 3:
            current_line.append(cell)
        else:
            current_line.sort(key=lambda c: c["bbox"][0])
            lines.append(current_line)
            current_line = [cell]
            current_y = cell["bbox"][1]

    current_line.sort(key=lambda c: c["bbox"][0])
    lines.append(current_line)

    # Join: spaces between words in a line, newlines between lines
    text_lines = []
    for line in lines:
        text_line = " ".join(c["text"] for c in line)
        text_lines.append(text_line)

    return "\n".join(text_lines)


def load_coco_annotations(coco_dir: Path) -> dict[str, dict]:
    """Load COCO annotations indexed by image filename.

    Returns dict mapping filename -> {annotations: [...], image_info: {...}}
    """
    index: dict[str, dict] = {}

    for split_file in ("train.json", "val.json", "test.json"):
        coco_path = coco_dir / split_file
        if not coco_path.exists():
            print(f"  Warning: {coco_path} not found")
            continue

        split_name = split_file.replace(".json", "")
        print(f"  Loading COCO {split_name}...")

        with open(coco_path) as f:
            coco_data = json.load(f)

        # Build image_id -> image_info lookup
        image_lookup: dict[int, dict] = {}
        for img in coco_data.get("images", []):
            image_lookup[img["id"]] = img

        # Group annotations by image_id
        ann_by_image: dict[int, list[dict]] = {}
        for ann in coco_data.get("annotations", []):
            ann_by_image.setdefault(ann["image_id"], []).append(ann)

        # Index by filename
        for img_id, img_info in image_lookup.items():
            filename = img_info.get("file_name", "")
            if filename:
                index[filename] = {
                    "image_info": img_info,
                    "annotations": ann_by_image.get(img_id, []),
                    "split": split_name,
                }

        print(f"    {len(image_lookup)} images, "
              f"{len(coco_data.get('annotations', []))} annotations")

    return index


def save_batch(
    batch_results: list[dict],
    batch_num: int,
    output_dir: Path,
    dataset_name: str,
) -> None:
    """Save a batch in the same format as process_datasets.py output."""
    # OCR JSONL
    ocr_path = output_dir / f"ocr_batch_{batch_num}.jsonl"
    with open(ocr_path, "w") as f:
        for r in batch_results:
            f.write(
                json.dumps({
                    "source": r["filename"],
                    "text": r["text"],
                    "confidence": 1.0,
                    "tables_found": 0,
                    "processing_time_ms": 0,
                    "success": True,
                    "error": None,
                })
                + "\n"
            )

    # Layout JSON
    layout_data = {
        "info": {
            "description": f"DocLayNet GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "doclaynet-gt",
            "batch": batch_num,
        },
        "categories": CATEGORIES,
        "images": [],
        "annotations": [],
    }

    global_ann_id = 0
    for img_id, r in enumerate(batch_results):
        if r["annotations"]:
            layout_data["images"].append({
                "id": img_id,
                "file_name": r["filename"],
                "gcs_path": r["filename"],
            })
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
    base_dir = Path(
        "/mnt/e/image_detection/01_base_data/documents/doclaynet"
    )
    json_dir = base_dir / "ground_truth" / "json"
    coco_dir = base_dir / "ground_truth" / "coco"
    output_dir = Path(
        "/mnt/e/image_detection/metadata_registry/extracted/doclaynet"
    )

    dry_run = "--dry-run" in sys.argv

    if not json_dir.exists():
        print(f"JSON annotations not found: {json_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Load COCO layout annotations (indexed by filename)
    print("Loading COCO layout annotations...")
    coco_index = load_coco_annotations(coco_dir)
    print(f"  Total indexed: {len(coco_index)} images with layout annotations")

    # Step 2: Process per-document JSON files for text
    json_files = sorted(json_dir.glob("*.json"))
    print(f"\nFound {len(json_files)} per-document JSON files")
    print(f"Output to {output_dir}/")

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0
    total_text_chars = 0
    total_with_layout = 0

    for json_path in json_files:
        try:
            with open(json_path) as f:
                doc_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Skip {json_path.name}: {e}")
            continue

        cells = doc_data.get("cells", [])
        metadata = doc_data.get("metadata", {})

        # Image filename = JSON filename with .png extension
        image_name = json_path.stem + ".png"

        # Reconstruct full page text from cell-level words
        text = reconstruct_page_text(cells)
        total_text_chars += len(text)

        # Get semantic layout annotations from COCO data
        layout_annotations: list[dict] = []
        coco_entry = coco_index.get(image_name)
        split = "unknown"

        if coco_entry:
            total_with_layout += 1
            split = coco_entry.get("split", "unknown")
            for ann in coco_entry.get("annotations", []):
                bbox = ann.get("bbox", [])
                if len(bbox) != 4:
                    continue

                layout_annotations.append({
                    "bbox": [float(v) for v in bbox],
                    "coord_origin": "top-left",
                    "category_id": ann.get("category_id", 0),
                    "area": ann.get("area", 0.0),
                    "iscrowd": ann.get("iscrowd", 0),
                })

        total_annotations += len(layout_annotations)

        batch_results.append({
            "filename": image_name,
            "split": split,
            "text": text,
            "annotations": layout_annotations,
            "doc_category": metadata.get("doc_category", ""),
            "collection": metadata.get("collection", ""),
        })

        if len(batch_results) >= BATCH_SIZE:
            if not dry_run:
                save_batch(batch_results, batch_num, output_dir, "doclaynet")
            total_processed += len(batch_results)
            if (batch_num + 1) % 50 == 0:
                print(
                    f"  Batch {batch_num + 1}: {total_processed} processed, "
                    f"{total_annotations} layout annotations, "
                    f"{total_text_chars:,} chars"
                )
            batch_results = []
            batch_num += 1

    # Save final partial batch
    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "doclaynet")
        total_processed += len(batch_results)
        batch_num += 1

    print(f"\nDone: {total_processed} documents, {batch_num} batches")
    print(f"  Layout annotations: {total_annotations} "
          f"({total_with_layout}/{total_processed} docs with layout)")
    print(f"  Text: {total_text_chars:,} characters total")

    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
