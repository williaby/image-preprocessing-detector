#!/usr/bin/env python3
"""Convert FinTabNet JSON annotations to our extracted OCR+layout format.

Reconstructs page-level text from cell-level annotations in PDF annotation
JSON files and creates layout annotations from structure XML files.

FinTabNet has two annotation types:
  - PDF Annotations (JSON): Cell text + PDF-coordinate bboxes
  - Structure Annotations (XML): Table/row/column bboxes in pixel coordinates

Output format matches process_datasets.py output:
  - ocr_batch_N.jsonl  (one line per image with text, confidence, etc.)
  - layout_batch_N.json (COCO-style with annotations, categories, images)
"""

import json
import sys
import defusedxml.ElementTree as ET
from pathlib import Path

BATCH_SIZE = 200

# FinTabNet structure categories
CATEGORIES = [
    {"id": 0, "name": "table"},
    {"id": 1, "name": "table_row"},
    {"id": 2, "name": "table_column"},
    {"id": 3, "name": "table_column_header"},
    {"id": 4, "name": "table_spanning_cell"},
    {"id": 5, "name": "table_projected_row_header"},
    {"id": 6, "name": "table_cell"},
]

CATEGORY_MAP = {cat["name"]: cat["id"] for cat in CATEGORIES}


def reconstruct_page_text(cells: list[dict]) -> str:
    """Reconstruct reading-order text from cell annotations.

    Uses row_nums/column_nums for ordering, falls back to bbox positions.
    """
    valid_cells = []
    for cell in cells:
        text = cell.get("json_text_content", "").strip()
        if not text:
            text = cell.get("pdf_text_content", "").strip()
        if text:
            row = cell.get("row_nums", [0])[0]
            col = cell.get("column_nums", [0])[0]
            valid_cells.append({"text": text, "row": row, "col": col})

    if not valid_cells:
        return ""

    # Sort by row then column
    valid_cells.sort(key=lambda c: (c["row"], c["col"]))

    # Group into rows
    rows: dict[int, list[dict]] = {}
    for cell in valid_cells:
        rows.setdefault(cell["row"], []).append(cell)

    # Join: tabs between cells in a row, newlines between rows
    lines = []
    for row_idx in sorted(rows.keys()):
        row_cells = sorted(rows[row_idx], key=lambda c: c["col"])
        line = "\t".join(c["text"] for c in row_cells)
        lines.append(line)

    return "\n".join(lines)


def build_cell_annotations(cells: list[dict], img_id: int) -> list[dict]:
    """Create COCO-style cell annotations from PDF annotation bboxes."""
    annotations = []
    for ann_id, cell in enumerate(cells):
        bbox = cell.get("pdf_bbox")
        if not bbox or len(bbox) != 4:
            continue

        text = cell.get("json_text_content", "").strip()
        if not text:
            text = cell.get("pdf_text_content", "").strip()

        # PDF coords [x1, y1, x2, y2] -> COCO [x, y, w, h]
        x1, y1, x2, y2 = bbox
        x_min = min(x1, x2)
        y_min = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        annotation = {
            "id": ann_id,
            "bbox": [float(x_min), float(y_min), float(width), float(height)],
            "bbox_raw": [float(x1), float(y1), float(x2), float(y2)],
            "coord_origin": "pdf-points",
            "category_name": "table_cell",
            "category_id": CATEGORY_MAP["table_cell"],
            "page": 1,
            "area": float(width * height),
            "image_id": img_id,
        }
        if text:
            annotation["text"] = text[:200]

        is_header = cell.get("is_column_header", False)
        is_proj_header = cell.get("is_projected_row_header", False)
        if is_header:
            annotation["category_name"] = "table_column_header"
            annotation["category_id"] = CATEGORY_MAP["table_column_header"]
        elif is_proj_header:
            annotation["category_name"] = "table_projected_row_header"
            annotation["category_id"] = CATEGORY_MAP["table_projected_row_header"]

        annotations.append(annotation)

    return annotations


def parse_structure_xml(xml_path: Path) -> list[dict]:
    """Parse PASCAL VOC XML structure annotations into COCO-style dicts."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return []

    root = tree.getroot()
    annotations = []

    # Map XML object names to our category names
    name_map = {
        "table": "table",
        "table row": "table_row",
        "table column": "table_column",
        "table column header": "table_column_header",
        "table spanning cell": "table_spanning_cell",
        "table projected row header": "table_projected_row_header",
    }

    for obj in root.findall("object"):
        name_elem = obj.find("name")
        bndbox = obj.find("bndbox")
        if name_elem is None or bndbox is None:
            continue

        name = name_elem.text or ""
        cat_name = name_map.get(name)
        if cat_name is None:
            continue

        xmin = float(bndbox.findtext("xmin", "0"))
        ymin = float(bndbox.findtext("ymin", "0"))
        xmax = float(bndbox.findtext("xmax", "0"))
        ymax = float(bndbox.findtext("ymax", "0"))

        width = xmax - xmin
        height = ymax - ymin

        annotations.append(
            {
                "bbox": [xmin, ymin, width, height],
                "bbox_raw": [xmin, ymin, xmax, ymax],
                "coord_origin": "top-left",
                "category_name": cat_name,
                "category_id": CATEGORY_MAP[cat_name],
                "area": float(width * height),
            }
        )

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
                    "confidence": 1.0,
                    "tables_found": 1,
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
            "description": f"FinTabNet GT annotations for {dataset_name}",
            "version": "2.0",
            "schema": "fintabnet-gt",
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
    base_dir = Path("/mnt/e/image_detection/01_base_data/tables/fintabnet")
    pdf_ann_dir = base_dir / "FinTabNet.c-PDF_Annotations"
    structure_dir = base_dir / "FinTabNet.c-Structure"
    output_dir = Path("/mnt/e/image_detection/metadata_registry/extracted/fintabnet")

    dry_run = "--dry-run" in sys.argv

    if not pdf_ann_dir.exists():
        print(f"PDF annotations not found: {pdf_ann_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover all JSON annotation files
    json_files = sorted(pdf_ann_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON annotation files")
    print(f"Output to {output_dir}/")

    batch_results: list[dict] = []
    batch_num = 0
    total_processed = 0
    total_annotations = 0
    total_text_chars = 0

    for json_path in json_files:
        try:
            with open(json_path) as f:
                tables = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Skip {json_path.name}: {e}")
            continue

        if not isinstance(tables, list):
            tables = [tables]

        for table in tables:
            cells = table.get("cells", [])
            structure_id = table.get("structure_id", "")
            split = table.get("split", "unknown")

            # Derive image filename from structure_id
            image_name = (
                f"{structure_id}.jpg" if structure_id else json_path.stem + ".jpg"
            )

            # Reconstruct text from cells
            text = reconstruct_page_text(cells)
            total_text_chars += len(text)

            # Build cell-level annotations from PDF annotations
            cell_annotations = build_cell_annotations(cells, img_id=0)

            # Try to find and parse structure XML for layout annotations
            struct_annotations: list[dict] = []
            if structure_id:
                for split_name in ("train", "val", "test"):
                    xml_path = structure_dir / split_name / f"{structure_id}.xml"
                    if xml_path.exists():
                        struct_annotations = parse_structure_xml(xml_path)
                        break

            # Combine: cell annotations + structure annotations
            all_annotations = cell_annotations + struct_annotations
            total_annotations += len(all_annotations)

            batch_results.append(
                {
                    "filename": image_name,
                    "split": split,
                    "text": text,
                    "annotations": all_annotations,
                }
            )

            if len(batch_results) >= BATCH_SIZE:
                if not dry_run:
                    save_batch(batch_results, batch_num, output_dir, "fintabnet")
                total_processed += len(batch_results)
                if (batch_num + 1) % 50 == 0:
                    print(
                        f"  Batch {batch_num + 1}: {total_processed} processed, "
                        f"{total_annotations} annotations, "
                        f"{total_text_chars:,} chars"
                    )
                batch_results = []
                batch_num += 1

    # Save final partial batch
    if batch_results:
        if not dry_run:
            save_batch(batch_results, batch_num, output_dir, "fintabnet")
        total_processed += len(batch_results)
        batch_num += 1

    print(
        f"\nDone: {total_processed} tables, {batch_num} batches, "
        f"{total_annotations} annotations, {total_text_chars:,} text chars"
    )

    if dry_run:
        print("(dry run - no files written)")


if __name__ == "__main__":
    main()
