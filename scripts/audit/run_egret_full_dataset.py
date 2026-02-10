#!/usr/bin/env python3
"""Run docling-layout-egret-xlarge inference on ALL DIQA-5000 images (5,500).

Batch processes all images from the dataset directory, writes results to
COCO-format JSON files compatible with the Docling GPU layout batch format
(so they can directly replace the existing layout data).

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/run_egret_full_dataset.py

    # CPU only (slower):
    PYTHONPATH=... uv run python3 scripts/audit/run_egret_full_dataset.py --device cpu

    # Custom batch size for output files:
    PYTHONPATH=... uv run python3 scripts/audit/run_egret_full_dataset.py --batch-size 250
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MODEL_REPO = "ds4sd/docling-layout-egret-xlarge"
DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
OUTPUT_DIR = Path("/mnt/e/image_detection/metadata_registry/extracted/diqa-5000-egret")

# Model label -> docling schema key (same as DoclingLayoutProvider)
_MODEL_LABEL_TO_DOCLING: dict[str, str] = {
    "Caption": "caption",
    "Footnote": "footnote",
    "Formula": "formula",
    "List-item": "list_item",
    "Page-footer": "page_footer",
    "Page-header": "page_header",
    "Picture": "picture",
    "Section-header": "section_header",
    "Table": "table",
    "Text": "text",
    "Title": "title",
    "Document Index": "document_index",
    "Code": "code",
    "Checkbox-Selected": "checkbox_selected",
    "Checkbox-Unselected": "checkbox_unselected",
    "Form": "form",
    "Key-Value Region": "key_value_region",
}


def discover_images(dataset_dir: Path) -> list[dict[str, str]]:
    """Find all JPG images in the dataset directory."""
    images: list[dict[str, str]] = []

    for jpg in sorted(dataset_dir.rglob("*.jpg")):
        rel_path = jpg.relative_to(dataset_dir)
        # image_id = filename without extension
        image_id = jpg.stem
        images.append(
            {
                "image_id": image_id,
                "filename": jpg.name,
                "relative_path": str(rel_path),
                "absolute_path": str(jpg),
            }
        )

    return images


def map_label(raw_label: str, taxonomy: Any) -> tuple[str, str]:
    """Map raw model label to (canonical, category_name).

    Returns (canonical_class, docling_category_name).
    """
    docling_key = _MODEL_LABEL_TO_DOCLING.get(raw_label)
    if docling_key is None:
        docling_key = raw_label.lower().replace("-", "_").replace(" ", "_")

    try:
        canonical = taxonomy.to_canonical(docling_key, "docling")
    except Exception:
        canonical = docling_key.upper()

    return canonical, docling_key


def run_batch(
    images: list[dict[str, str]],
    device: str,
    threshold: float,
    output_dir: Path,
    batch_size: int,
) -> dict[str, int]:
    """Run egret inference on all images and write COCO-format batch files."""
    from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor

    from image_preprocessing_detector.schema_utils.layout_taxonomy import LayoutTaxonomy

    # Download/locate model
    log.info("Resolving model artifacts for %s ...", MODEL_REPO)
    model_path = snapshot_download(MODEL_REPO)
    log.info("Model at: %s", model_path)

    # Initialize predictor
    log.info(
        "Loading LayoutPredictor (device=%s, threshold=%.2f) ...", device, threshold
    )
    predictor = LayoutPredictor(
        artifact_path=model_path,
        device=device,
        base_threshold=threshold,
    )
    log.info("Model info: %s", predictor.info())

    taxonomy = LayoutTaxonomy()

    # Warmup
    warmup = Image.new("RGB", (640, 640), color=(255, 255, 255))
    list(predictor.predict(warmup))
    log.info("Warmup complete.")

    output_dir.mkdir(parents=True, exist_ok=True)

    stats: dict[str, int] = Counter()
    total = len(images)
    batch_num = 0
    all_times: list[float] = []

    # Process in batches for output
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_images = images[batch_start:batch_end]

        # Build COCO-format output
        coco_images: list[dict[str, Any]] = []
        coco_annotations: list[dict[str, Any]] = []
        categories_seen: dict[str, int] = {}
        ann_id = 0

        for local_idx, img_info in enumerate(batch_images):
            global_idx = batch_start + local_idx
            image_id = local_idx  # COCO image_id is sequential within batch
            filename = img_info["filename"]

            log.info("[%d/%d] %s ...", global_idx + 1, total, img_info["image_id"])

            try:
                img = Image.open(img_info["absolute_path"]).convert("RGB")
            except Exception as exc:
                log.error("Failed to open %s: %s", filename, exc)
                stats["errors"] += 1
                continue

            width, height = img.size

            coco_images.append(
                {
                    "id": image_id,
                    "file_name": filename,
                    "width": width,
                    "height": height,
                }
            )

            try:
                start_ns = time.perf_counter_ns()
                raw_preds = list(predictor.predict(img))
                elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
                all_times.append(elapsed_ms)
            except Exception as exc:
                log.error("Inference failed for %s: %s", filename, exc)
                stats["errors"] += 1
                continue

            stats["success"] += 1

            for pred in raw_preds:
                raw_label = pred["label"]
                confidence = pred["confidence"]

                # Convert bbox: [l, t, r, b] -> COCO [x, y, w, h]
                left = pred["l"]
                top = pred["t"]
                right = pred["r"]
                bottom = pred["b"]

                bbox = [
                    round(left, 2),
                    round(top, 2),
                    round(right - left, 2),
                    round(bottom - top, 2),
                ]
                area = round(bbox[2] * bbox[3], 2)

                canonical, category_name = map_label(raw_label, taxonomy)

                # Track category IDs
                if category_name not in categories_seen:
                    categories_seen[category_name] = len(categories_seen)

                coco_annotations.append(
                    {
                        "id": ann_id,
                        "image_id": image_id,
                        "category_id": categories_seen[category_name],
                        "category_name": category_name,
                        "canonical_class": canonical,
                        "bbox": bbox,
                        "bbox_raw": [
                            round(left, 2),
                            round(top, 2),
                            round(right, 2),
                            round(bottom, 2),
                        ],
                        "area": area,
                        "confidence": round(confidence, 6),
                        "source": "egret_xlarge",
                    }
                )
                ann_id += 1
                stats["total_annotations"] += 1

            if (global_idx + 1) % 100 == 0:
                avg_ms = sum(all_times[-100:]) / min(100, len(all_times[-100:]))
                remaining = total - (global_idx + 1)
                eta_sec = remaining * avg_ms / 1000
                log.info(
                    "  Progress: %d/%d (%.0f ms/img, ETA: %.0f sec)",
                    global_idx + 1,
                    total,
                    avg_ms,
                    eta_sec,
                )

        # Build categories list
        categories = [
            {"id": cat_id, "name": cat_name}
            for cat_name, cat_id in sorted(categories_seen.items(), key=lambda x: x[1])
        ]

        # Write COCO-format batch file
        batch_output = {
            "info": {
                "description": "Egret-xlarge layout annotations for diqa-5000",
                "version": "1.0",
                "schema": "egret-xlarge",
                "model": MODEL_REPO,
                "device": device,
                "threshold": threshold,
                "batch": batch_num,
            },
            "categories": categories,
            "images": coco_images,
            "annotations": coco_annotations,
        }

        out_path = output_dir / f"egret_batch_{batch_num:03d}.json"
        with open(out_path, "w") as fh:
            json.dump(batch_output, fh, indent=2, ensure_ascii=False)

        log.info(
            "  Batch %d: %d images, %d annotations -> %s",
            batch_num,
            len(coco_images),
            len(coco_annotations),
            out_path,
        )
        batch_num += 1

    # Print summary
    if all_times:
        avg_time = sum(all_times) / len(all_times)
        total_sec = sum(all_times) / 1000
        log.info(
            "Complete: %d images in %.1f sec (%.1f ms/img avg)",
            stats["success"],
            total_sec,
            avg_time,
        )

    return dict(stats)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run docling-layout-egret-xlarge on all DIQA-5000 images.",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="PyTorch device (default: cuda).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Minimum confidence threshold (default: 0.3).",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DATASET_DIR,
        help="Path to DIQA-5000 dataset directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for batch files.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of images per output batch file (default: 200).",
    )
    args = parser.parse_args()

    # Discover images
    images = discover_images(args.dataset_dir)
    log.info("Found %d images in %s", len(images), args.dataset_dir)

    if not images:
        log.error("No images found!")
        sys.exit(1)

    # Run batch inference
    stats = run_batch(
        images=images,
        device=args.device,
        threshold=args.threshold,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )

    print(f"\n{'=' * 50}")
    print("  Egret Full Dataset Results")
    print(f"{'=' * 50}")
    print(f"  Success: {stats.get('success', 0)}")
    print(f"  Errors:  {stats.get('errors', 0)}")
    print(f"  Total annotations: {stats.get('total_annotations', 0)}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
