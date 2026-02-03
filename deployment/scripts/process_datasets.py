#!/usr/bin/env python3
"""
Unified Dataset Processor: Granite Docling OCR + DocLayout-YOLO Layout Detection

Processes images from GCS, extracts text via Docling, captures COCO layout via DocLayout-YOLO.
"""

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from doclayout_yolo import YOLOv10
from docling.document_converter import DocumentConverter
from google.cloud import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Dataset registry
DATASETS = {
    "pubtabnet": "datasets/pubtabnet",
    "tablebank": "datasets/tablebank",
    "fintabnet": "datasets/fintabnet",
    "doclaynet": "datasets/doclaynet",
    "funsd": "datasets/funsd",
    "sroie": "datasets/sroie",
    "mathverse": "datasets/mathverse",
    "multimodal-textbook": "datasets/multimodal_textbook",
    "nist-sd2": "datasets/nist_db2",
    "nist-sd6": "datasets/nist_sd6",
    "cc-ocr": "datasets/cc_ocr",
    "mlt19": "datasets/mlt19",
    "jssoda": "datasets/jssoda",
    "rvl-cdip": "datasets/rvl_cdip",
    # Forms datasets (receipts/invoices)
    "invoices-kaggle": "datasets/invoices_kaggle",
    "mobile-receipts-voxel51": "datasets/mobile_receipts_voxel51",
    "receipts-hitl": "datasets/receipts_hitl",
    "sroie-voxel51": "datasets/sroie_voxel51",
}

GCS_BUCKET = "image_detection_b"
GCS_PREFIX = "image-preprocessing-detector"

# DocLayout-YOLO class mapping (DocLayNet classes)
LAYOUT_CLASSES = {
    0: "Caption",
    1: "Footnote",
    2: "Formula",
    3: "List-Item",
    4: "Page-Footer",
    5: "Page-Header",
    6: "Picture",
    7: "Section-Header",
    8: "Table",
    9: "Text",
    10: "Title",
}


@dataclass
class ProcessingConfig:
    dataset: str
    batch_size: int = 200
    workers: int = 4
    local_dir: Path = field(default_factory=lambda: Path("/workspace/processing"))
    dry_run: bool = False
    skip_layout: bool = False
    skip_ocr: bool = False


@dataclass
class ProcessingResult:
    source_path: str
    gcs_path: str
    # OCR results
    text: str = ""
    ocr_confidence: float = 0.0
    tables_found: int = 0
    # Layout results (COCO format)
    layout_annotations: list = field(default_factory=list)
    # Metadata
    processing_time_ms: float = 0.0
    success: bool = True
    error: str | None = None


class UnifiedProcessor:
    """Process datasets with Docling OCR + DocLayout-YOLO layout detection."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        # Initialize models
        self.docling_converter = None
        self.layout_model = None

        # Directories
        self.input_dir = config.local_dir / "input"
        self.output_dir = config.local_dir / "output"

    def setup(self):
        """Initialize models and directories."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Docling
        if not self.config.skip_ocr:
            logger.info("Loading Docling converter...")
            self.docling_converter = DocumentConverter()
            logger.info("Docling ready")

        # Initialize DocLayout-YOLO
        if not self.config.skip_layout:
            logger.info("Loading DocLayout-YOLO...")
            self.layout_model = YOLOv10.from_pretrained(
                "juliozhao/DocLayout-YOLO-DocStructBench"
            )
            if torch.cuda.is_available():
                self.layout_model = self.layout_model.to("cuda")
            logger.info(
                f"DocLayout-YOLO ready (device: {'cuda' if torch.cuda.is_available() else 'cpu'})"
            )

    def list_gcs_files(self) -> list[str]:
        """List all image files in the dataset."""
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"
        logger.info(f"Listing files in gs://{GCS_BUCKET}/{gcs_path}")

        blobs = self.bucket.list_blobs(prefix=gcs_path)
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}

        files = [
            blob.name
            for blob in blobs
            if Path(blob.name).suffix.lower() in image_extensions
            and "__MACOSX" not in blob.name
            and not Path(blob.name).name.startswith("._")
        ]

        logger.info(f"Found {len(files)} files")
        return files

    def download_file(self, gcs_path: str) -> Path:
        """Download a single file from GCS."""
        blob = self.bucket.blob(gcs_path)
        local_path = self.input_dir / Path(gcs_path).name
        blob.download_to_filename(str(local_path))
        return local_path

    def process_ocr(self, file_path: Path) -> dict[str, Any]:
        """Extract text using Docling."""
        if self.docling_converter is None:
            return {"text": "", "confidence": 0.0, "tables": 0}

        try:
            result = self.docling_converter.convert(str(file_path))
            doc = result.document

            # Extract text content
            text = (
                doc.export_to_markdown()
                if hasattr(doc, "export_to_markdown")
                else str(doc)
            )

            # Count tables
            tables = len(doc.tables) if hasattr(doc, "tables") else 0

            return {
                "text": text,
                "confidence": 1.0,
                "tables": tables,
            }
        except Exception as e:
            logger.warning(f"OCR failed for {file_path.name}: {e}")
            return {"text": "", "confidence": 0.0, "tables": 0, "error": str(e)}

    def process_layout(self, file_path: Path) -> list[dict]:
        """Detect layout using DocLayout-YOLO, return COCO format annotations."""
        if self.layout_model is None:
            return []

        try:
            # Run inference
            results = self.layout_model.predict(
                str(file_path),
                conf=0.25,
                iou=0.45,
                verbose=False,
            )

            annotations = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for i, box in enumerate(boxes):
                    # Get coordinates (xyxy format)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    # Convert to COCO format [x, y, width, height]
                    width = x2 - x1
                    height = y2 - y1

                    # Get class and confidence
                    cls_id = int(box.cls[0].cpu().numpy())
                    conf = float(box.conf[0].cpu().numpy())

                    annotation = {
                        "id": i,
                        "bbox": [float(x1), float(y1), float(width), float(height)],
                        "category_id": cls_id,
                        "category_name": LAYOUT_CLASSES.get(cls_id, "Unknown"),
                        "confidence": conf,
                        "area": float(width * height),
                    }
                    annotations.append(annotation)

            return annotations

        except Exception as e:
            logger.warning(f"Layout detection failed for {file_path.name}: {e}")
            return []

    def process_file(self, gcs_path: str) -> ProcessingResult:
        """Process a single file through both pipelines."""
        start = time.perf_counter()

        try:
            # Download
            local_path = self.download_file(gcs_path)

            # OCR
            ocr_result = (
                self.process_ocr(local_path) if not self.config.skip_ocr else {}
            )

            # Layout
            layout_annotations = (
                self.process_layout(local_path) if not self.config.skip_layout else []
            )

            # Cleanup
            local_path.unlink(missing_ok=True)

            return ProcessingResult(
                source_path=local_path.name,
                gcs_path=gcs_path,
                text=ocr_result.get("text", ""),
                ocr_confidence=ocr_result.get("confidence", 0.0),
                tables_found=ocr_result.get("tables", 0),
                layout_annotations=layout_annotations,
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=True,
            )

        except Exception as e:
            return ProcessingResult(
                source_path=Path(gcs_path).name,
                gcs_path=gcs_path,
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e),
            )

    def save_results(self, results: list[ProcessingResult], batch_num: int):
        """Save results locally and upload to GCS."""
        dataset_output = self.output_dir / self.config.dataset
        dataset_output.mkdir(parents=True, exist_ok=True)

        # Save OCR results (JSONL)
        ocr_path = dataset_output / f"ocr_batch_{batch_num}.jsonl"
        with open(ocr_path, "w") as f:
            f.writelines(
                json.dumps(
                    {
                        "source": r.gcs_path,
                        "text": r.text,
                        "confidence": r.ocr_confidence,
                        "tables_found": r.tables_found,
                        "processing_time_ms": r.processing_time_ms,
                        "success": r.success,
                        "error": r.error,
                    }
                )
                + "\n"
                for r in results
            )

        # Save layout results (COCO-style JSON)
        layout_path = dataset_output / f"layout_batch_{batch_num}.json"
        layout_data = {
            "info": {
                "description": f"DocLayout-YOLO annotations for {self.config.dataset}",
                "version": "1.0",
                "batch": batch_num,
            },
            "categories": [{"id": k, "name": v} for k, v in LAYOUT_CLASSES.items()],
            "images": [],
            "annotations": [],
        }

        annotation_id = 0
        for img_id, r in enumerate(results):
            if r.layout_annotations:
                layout_data["images"].append(
                    {
                        "id": img_id,
                        "file_name": r.source_path,
                        "gcs_path": r.gcs_path,
                    }
                )
                for ann in r.layout_annotations:
                    ann["image_id"] = img_id
                    ann["id"] = annotation_id
                    layout_data["annotations"].append(ann)
                    annotation_id += 1

        with open(layout_path, "w") as f:
            json.dump(layout_data, f, indent=2)

        logger.info(f"Saved: {ocr_path}, {layout_path}")

        # Upload to GCS
        try:
            for local_file in [ocr_path, layout_path]:
                gcs_dest = (
                    f"{GCS_PREFIX}/extracted/{self.config.dataset}/{local_file.name}"
                )
                blob = self.bucket.blob(gcs_dest)
                blob.upload_from_filename(str(local_file))
                logger.info(f"Uploaded to gs://{GCS_BUCKET}/{gcs_dest}")
        except Exception as e:
            logger.warning(f"GCS upload failed: {e}")

    def process_dataset(self):
        """Process entire dataset in batches."""
        logger.info(f"=== Processing dataset: {self.config.dataset} ===")

        # Setup models
        self.setup()

        # List files
        all_files = self.list_gcs_files()
        if not all_files:
            logger.error("No files found")
            return

        if self.config.dry_run:
            logger.info(f"Dry run - would process {len(all_files)} files")
            for f in all_files[:10]:
                logger.info(f"  {f}")
            return

        # Process in batches
        num_batches = (
            len(all_files) + self.config.batch_size - 1
        ) // self.config.batch_size
        logger.info(f"Processing {len(all_files)} files in {num_batches} batches")

        total_success = 0
        total_failed = 0
        total_time = 0.0

        for batch_num in range(num_batches):
            start_idx = batch_num * self.config.batch_size
            end_idx = min(start_idx + self.config.batch_size, len(all_files))
            batch_files = all_files[start_idx:end_idx]

            logger.info(
                f"=== Batch {batch_num + 1}/{num_batches} ({len(batch_files)} files) ==="
            )

            results = []
            for i, gcs_path in enumerate(batch_files):
                result = self.process_file(gcs_path)
                results.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(batch_files)}")

            # Save batch results
            self.save_results(results, batch_num)

            # Stats
            batch_success = sum(1 for r in results if r.success)
            batch_time = sum(r.processing_time_ms for r in results)
            total_success += batch_success
            total_failed += len(results) - batch_success
            total_time += batch_time

            avg_time = batch_time / len(results) if results else 0
            logger.info(
                f"Batch {batch_num + 1}: {batch_success} success, {len(results) - batch_success} failed, avg {avg_time:.0f}ms/file"
            )

        # Final summary
        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        logger.info(
            f"Total time: {total_time / 1000:.1f}s, avg {total_time / len(all_files):.0f}ms/file"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Process datasets with Docling OCR + DocLayout-YOLO"
    )
    parser.add_argument("dataset", nargs="?", help="Dataset name to process")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--batch-size", type=int, default=200, help="Files per batch")
    parser.add_argument(
        "--dry-run", action="store_true", help="List files without processing"
    )
    parser.add_argument(
        "--skip-layout", action="store_true", help="Skip layout detection"
    )
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR extraction")

    args = parser.parse_args()

    if args.list:
        print("Available datasets:")
        for name, path in sorted(DATASETS.items()):
            print(f"  {name:20} -> {path}")
        return

    if not args.dataset:
        parser.print_help()
        return

    if args.dataset not in DATASETS:
        print(f"Unknown dataset: {args.dataset}")
        print(f"Available: {', '.join(sorted(DATASETS.keys()))}")
        return

    config = ProcessingConfig(
        dataset=args.dataset,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        skip_layout=args.skip_layout,
        skip_ocr=args.skip_ocr,
    )

    processor = UnifiedProcessor(config)
    processor.process_dataset()


if __name__ == "__main__":
    main()
