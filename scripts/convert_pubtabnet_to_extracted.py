#!/usr/bin/env python3
"""Convert PubTabNet JSONL annotations to our extracted OCR+layout format.

Reconstructs page-level text from cell-level tokens and creates layout
annotations in the same schema as Docling native output, avoiding the
need to run 519K images through Docling GPU processing.

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
from pathlib import Path

# HTML tags to strip from cell tokens
HTML_TAGS = {
    "<b>",
    "</b>",
    "<i>",
    "</i>",
    "<sup>",
    "</sup>",
    "<sub>",
    "</sub>",
    "<br>",
    "<br/>",
}

BATCH_SIZE = 200


def extract_cell_text(tokens: list[str]) -> str:
    """Join character tokens, stripping HTML formatting tags."""
    return "".join(t for t in tokens if t not in HTML_TAGS)


def reconstruct_page_text(cells: list[dict]) -> str:
    """Reconstruct reading-order text from cell annotations.

    Sorts cells by y-position (rows) then x-position (columns),
    groups into rows by y-proximity, joins with tabs and newlines.
    """
    # Filter to cells that have text and bboxes
    valid_cells = []
    for cell in cells:
        text = extract_cell_text(cell.get("tokens", []))
        bbox = cell.get("bbox")
        if text.strip() and bbox:
            valid_cells.append({"text": text, "bbox": bbox})

    if not valid_cells:
        return ""

    # Sort by y then x
    valid_cells.sort(key=lambda c: (c["bbox"][1], c["bbox"][0]))

    # Group into rows (cells within 5px y-distance are same row)
    rows: list[list[dict]] = []
    current_row: list[dict] = [valid_cells[0]]
    current_y = valid_cells[0]["bbox"][1]

    for cell in valid_cells[1:]:
        if abs(cell["bbox"][1] - current_y) <= 5:
            current_row.append(cell)
        else:
            # Sort current row by x
            current_row.sort(key=lambda c: c["bbox"][0])
            rows.append(current_row)
            current_row = [cell]
            current_y = cell["bbox"][1]
    # Don't forget last row
    current_row.sort(key=lambda c: c["bbox"][0])
    rows.append(current_row)

    # Join: tabs between cells in a row, newlines between rows
    lines = []
    for row in rows:
        line = "\t".join(c["text"] for c in row)
        lines.append(line)

    return "\n".join(lines)


def build_layout_annotations(cells: list[dict], img_id: int) -> list[dict]:
    """Create COCO-style layout annotations from cell bboxes."""
    annotations = []
    for ann_id, cell in enumerate(cells):
        bbox = cell.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        text = extract_cell_text(cell.get("tokens", []))

        # PubTabNet uses [x1, y1, x2, y2] -> convert to COCO [x, y, w, h]
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1

        annotation = {
            "id": ann_id,
            "bbox": [float(x1), float(y1), float(width), float(height)],
            "bbox_raw": [float(x1), float(y1), float(x2), float(y2)],
            "coord_origin": "top-left",
            "category_name": "table_cell",
            "page": 1,
            "area": float(width * height),
            "image_id": img_id,
            "category_id": 0,
        }
        if text.strip():
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
    # OCR JSONL
    ocr_path = output_dir / f"ocr_batch_{batch_num}.jsonl"
    with open(ocr_path, "w") as f:
        f.writelines(
            json.dumps(
                {
                    "source": r["filename"],
                    "text": r["text"],
                    "confidence": 1.0,  # Ground truth = perfect confidence
                    "tables_found": 1,  # Each image is a table
                    "processing_time_ms": 0,
                    "success": True,
                    "error": None,
                }
            )
            + "\n"
            for r in batch_results
        )

    # Layout JSON
    layout_data = {
        "info": {
            "description": f"PubTabNet cell annotations for {dataset_name}",
            "version": "2.0",
            "schema": "pubtabnet-gt",
            "batch": batch_num,
        },
        "categories": [{"id": 0, "name": "table_cell"}],
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
    jsonl_path = Path(
        "/mnt/e/image_detection/01_base_data/tables/pubtabnet/pubtabnet/"
        "PubTabNet_2.0.0.jsonl"
    )
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/pubtabnet")

    dry_run = "--dry-run" in sys.argv

    if not jsonl_path.exists():
        print(f"JSONL not found: {jsonl_path}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading {jsonl_path}...")
    print(f"Output to {output_dir}/")

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0

    with open(jsonl_path) as f:
        for line_num, line in enumerate(f):
            entry = json.loads(line)
            cells = entry.get("html", {}).get("cells", [])

            text = reconstruct_page_text(cells)
            annotations = build_layout_annotations(cells, img_id=0)

            batch_results.append(
                {
                    "filename": entry["filename"],
                    "split": entry.get("split", "unknown"),
                    "text": text,
                    "annotations": annotations,
                }
            )
            total_annotations += len(annotations)

            if len(batch_results) >= BATCH_SIZE:
                if not dry_run:
                    save_batch(batch_results, batch_num, output_dir, "pubtabnet")
                total_processed += len(batch_results)
                if (batch_num + 1) % 50 == 0:
                    print(
                        f"  Batch {batch_num + 1}: {total_processed} processed, "
                        f"{total_annotations} annotations"
                    )
                batch_results = []
                batch_num += 1

    # Save final partial batch
    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "pubtabnet")
        total_processed += len(batch_results)
        batch_num += 1

    print(
        f"\nDone: {total_processed} images, {batch_num} batches, "
        f"{total_annotations} annotations"
    )

    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
