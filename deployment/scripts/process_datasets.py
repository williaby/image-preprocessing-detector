#!/usr/bin/env python3
# ruff: noqa: T201
"""Unified Dataset Processor: Docling OCR + Native Layout Extraction.

Processes images from GCS, extracts text and layout via Docling's native schema.
Layout labels follow the Docling document model (docling-core).
"""

import argparse
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    "diqa-5000": "datasets/diqa-5000",
    "smartdoc-qa": "datasets/smartdoc-qa",
    "mathverse": "datasets/mathverse",
    "multimodal-textbook": "datasets/multimodal_textbook",
    "nist-sd2": "datasets/nist_db2",
    "nist-sd6": "datasets/nist_sd6",
    "cc-ocr": "datasets/cc_ocr",
    "mlt19": "datasets/mlt19",
    "jssoda": "datasets/multilingual_scripts/multilingual_scripts/jssoda",
    "rvl-cdip": "datasets/rvl_cdip",
    # Forms datasets (receipts/invoices)
    "invoices-kaggle": "datasets/invoices_kaggle",
    "mobile-receipts-voxel51": "datasets/mobile_receipts_voxel51",
    "receipts-hitl": "datasets/receipts_hitl",
    "sroie-voxel51": "datasets/sroie_voxel51",
    # Remaining datasets needing text + layout extraction
    "docsynth": "datasets/docsynth300k",
    "doc3d": "datasets/doc3d",
    "siw13": "datasets/siw13",
    "signatr6k": "datasets/signatr6k",
    "cvsi": "datasets/cvsi",
    "arabic-docs": "datasets/arabic_docs_ocr",
    "realdae": "datasets/realdae",
    "tobacco800": "datasets/tobacco800",
    "dibco": "datasets/dibco",
    "bhutan-afs": "datasets/bhutan_financial",
    # Benchmark and financial datasets
    "financebench": "datasets/financebench",
    "ohr-bench": "datasets/ohr_bench",
    "omnidocbench": "datasets/omnidocbench",
    # Non-Latin script datasets (layout-only extraction)
    "mdiw13": "datasets/mdiw13",
    "hindi-synth": "datasets/hindi_ocr_synthetic",
    "muharaf": "datasets/muharaf",
    "yarmouk": "datasets/yarmouk_ocr",
    "pucit-ohul": "datasets/pucit_ohul_urdu",
    "mle2e": "datasets/mle2e",
    "nepali-handwritten": "datasets/nepali_handwritten",
    "dzongkha-digits": "datasets/multilingual_scripts/multilingual_scripts/dzongkha_digits",
    "tibhcr": "datasets/tibhcr",
}

# Datasets stored as parquet with embedded images (not standalone image files)
PARQUET_DATASETS = {
    "docsynth",
}

# Datasets stored as Arrow shards (HuggingFace datasets format)
ARROW_DATASETS = {
    "omnidocbench",
}

# Datasets stored as zip archives containing PDFs
ZIP_DATASETS = {
    "ohr-bench": "pdfs.zip",  # value is the zip filename within the dataset dir
}

GCS_BUCKET = os.environ.get("GCS_BUCKET", "image_detection_b")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "image-preprocessing-detector")


@dataclass
class ProcessingConfig:
    """Configuration for dataset processing."""

    dataset: str
    batch_size: int = 200
    workers: int = 4
    local_dir: Path = field(default_factory=lambda: Path("/workspace/processing"))
    dry_run: bool = False
    skip_ocr: bool = False


@dataclass
class ProcessingResult:
    """Result of processing a single dataset file."""

    source_path: str
    gcs_path: str
    # OCR results
    text: str = ""
    ocr_confidence: float = 0.0
    tables_found: int = 0
    # Layout results (Docling native schema)
    layout_annotations: list = field(default_factory=list)
    # Metadata
    processing_time_ms: float = 0.0
    success: bool = True
    error: str | None = None


class UnifiedProcessor:
    """Process datasets with Docling OCR + native layout extraction."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(GCS_BUCKET)

        # Initialize model
        self.docling_converter = None

        # Global category map for consistent IDs across batches.
        # This is cumulative: new category names discovered in later batches are
        # appended with incrementing IDs so that category_id values remain stable
        # across all output batch files for the same processing run.
        self._category_map: dict[str, int] = {}

        # Directories
        self.input_dir = config.local_dir / "input"
        self.output_dir = config.local_dir / "output"

    def setup(self):
        """Initialize Docling converter and directories."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Loading Docling converter...")
        if self.config.skip_ocr:
            # Layout-only mode: disable OCR for faster processing
            try:
                from docling.datamodel.pipeline_options import PipelineOptions

                pipeline_options = PipelineOptions(do_ocr=False)
                self.docling_converter = DocumentConverter(
                    pipeline_options=pipeline_options
                )
                logger.info("Docling ready (layout-only, OCR disabled)")
            except (ImportError, TypeError):
                # Fallback: run full pipeline, discard text in output
                logger.warning(
                    "Could not configure OCR-free pipeline, "
                    "falling back to full pipeline with text discarded"
                )
                self.docling_converter = DocumentConverter()
                logger.info("Docling ready (full pipeline, text will be discarded)")
        else:
            self.docling_converter = DocumentConverter()
            logger.info("Docling ready")

    def is_parquet_dataset(self) -> bool:
        """Check if dataset uses parquet format with embedded images."""
        return self.config.dataset in PARQUET_DATASETS

    def is_arrow_dataset(self) -> bool:
        """Check if dataset uses Arrow/HuggingFace format with embedded images."""
        return self.config.dataset in ARROW_DATASETS

    def is_zip_dataset(self) -> bool:
        """Check if dataset stores documents in a zip archive."""
        return self.config.dataset in ZIP_DATASETS

    def list_parquet_files(self) -> list[str]:
        """List all parquet files in the dataset."""
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"
        logger.info(f"Listing parquet files in gs://{GCS_BUCKET}/{gcs_path}")

        blobs = self.bucket.list_blobs(prefix=gcs_path)
        files = [blob.name for blob in blobs if blob.name.endswith(".parquet")]

        logger.info(f"Found {len(files)} parquet files")
        return sorted(files)

    def list_arrow_files(self) -> list[str]:
        """List all Arrow shard files in the dataset."""
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"
        logger.info(f"Listing arrow files in gs://{GCS_BUCKET}/{gcs_path}")

        blobs = self.bucket.list_blobs(prefix=gcs_path)
        files = [
            blob.name
            for blob in blobs
            if blob.name.endswith(".arrow") and "/train/" in blob.name
        ]

        logger.info(f"Found {len(files)} arrow files")
        return sorted(files)

    def list_gcs_files(self) -> list[str]:
        """List all image/PDF files in the dataset."""
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}"
        logger.info(f"Listing files in gs://{GCS_BUCKET}/{gcs_path}")

        blobs = self.bucket.list_blobs(prefix=gcs_path)
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".pdf"}

        files = [
            blob.name
            for blob in blobs
            if Path(blob.name).suffix.lower() in image_extensions
            and "__MACOSX" not in blob.name
            and ".git/" not in blob.name
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

    def process_document(self, file_path: Path) -> dict[str, Any]:
        """Extract text and layout using Docling's native pipeline.

        Returns dict with 'text', 'confidence', 'tables', and 'layout' keys.
        Layout annotations use Docling's native schema labels with COCO-format bboxes.
        """
        if self.docling_converter is None:
            return {"text": "", "confidence": 0.0, "tables": 0, "layout": []}

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

            # Extract layout annotations from Docling's document model
            annotations = []
            ann_id = 0

            if hasattr(doc, "iterate_items"):
                for item, _level in doc.iterate_items():
                    label = str(item.label) if hasattr(item, "label") else "unknown"

                    # Extract bounding box from provenance
                    if hasattr(item, "prov") and item.prov:
                        for prov_item in item.prov:
                            bbox = getattr(prov_item, "bbox", None)
                            if bbox is None:
                                continue

                            # Docling bbox: l (left), t (top), r (right), b (bottom)
                            # Docling uses PDF coordinates (origin bottom-left, y up)
                            # so t > b for valid boxes. We store raw coordinates
                            # and normalize to positive width/height for COCO.
                            left = getattr(bbox, "l", 0.0)
                            top = getattr(bbox, "t", 0.0)
                            right = getattr(bbox, "r", 0.0)
                            bottom = getattr(bbox, "b", 0.0)

                            # COCO format [x, y, width, height] with positive dimensions
                            x_min = min(left, right)
                            y_min = min(top, bottom)
                            width = abs(right - left)
                            height = abs(top - bottom)

                            page_no = getattr(prov_item, "page_no", 1)

                            annotation = {
                                "id": ann_id,
                                "bbox": [
                                    float(x_min),
                                    float(y_min),
                                    float(width),
                                    float(height),
                                ],
                                "bbox_raw": [
                                    float(left),
                                    float(top),
                                    float(right),
                                    float(bottom),
                                ],
                                "coord_origin": "bottom-left",
                                "category_name": label,
                                "page": page_no,
                                "area": float(width * height),
                            }

                            # Include text snippet for non-picture elements
                            item_text = getattr(item, "text", "")
                            if item_text and label not in ("picture",):
                                annotation["text"] = item_text[:200]

                            annotations.append(annotation)
                            ann_id += 1

            return {  # noqa: TRY300
                "text": text,
                "confidence": 1.0,
                "tables": tables,
                "layout": annotations,
            }

        except Exception as e:
            logger.warning(f"Processing failed for {file_path.name}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "tables": 0,
                "layout": [],
                "error": str(e),
            }

    def process_file(self, gcs_path: str) -> ProcessingResult:
        """Process a single file: download from GCS, run Docling, return results."""
        start = time.perf_counter()

        try:
            # Download
            local_path = self.download_file(gcs_path)

            # Process with Docling (layout always, text unless skip_ocr)
            doc_result = self.process_document(local_path)

            # Cleanup
            local_path.unlink(missing_ok=True)

            # When skip_ocr, discard text but keep layout
            text = "" if self.config.skip_ocr else doc_result.get("text", "")
            confidence = (
                0.0 if self.config.skip_ocr else doc_result.get("confidence", 0.0)
            )

            return ProcessingResult(
                source_path=local_path.name,
                gcs_path=gcs_path,
                text=text,
                ocr_confidence=confidence,
                tables_found=doc_result.get("tables", 0),
                layout_annotations=doc_result.get("layout", []),
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

    def process_local_file(
        self, local_path: Path, source_name: str
    ) -> ProcessingResult:
        """Process a local file (already on disk) through Docling pipeline."""
        start = time.perf_counter()

        try:
            doc_result = self.process_document(local_path)

            # When skip_ocr, discard text but keep layout
            text = "" if self.config.skip_ocr else doc_result.get("text", "")
            confidence = (
                0.0 if self.config.skip_ocr else doc_result.get("confidence", 0.0)
            )

            return ProcessingResult(
                source_path=local_path.name,
                gcs_path=source_name,
                text=text,
                ocr_confidence=confidence,
                tables_found=doc_result.get("tables", 0),
                layout_annotations=doc_result.get("layout", []),
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=True,
            )
        except Exception as e:
            return ProcessingResult(
                source_path=local_path.name,
                gcs_path=source_name,
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

        # Save layout results (Docling native schema)
        layout_path = dataset_output / f"layout_batch_{batch_num}.json"

        # Register new category names in global map for consistent IDs across batches
        for r in results:
            for ann in r.layout_annotations:
                cat_name = ann.get("category_name", "unknown")
                if cat_name not in self._category_map:
                    self._category_map[cat_name] = len(self._category_map)
        category_map = self._category_map

        layout_data = {
            "info": {
                "description": f"Docling layout annotations for {self.config.dataset}",
                "version": "2.0",
                "schema": "docling-native",
                "batch": batch_num,
            },
            "categories": [
                {"id": idx, "name": name} for name, idx in category_map.items()
            ],
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
                    ann_copy = dict(ann)
                    ann_copy["image_id"] = img_id
                    ann_copy["id"] = annotation_id
                    ann_copy["category_id"] = category_map.get(
                        ann.get("category_name", "unknown"), -1
                    )
                    layout_data["annotations"].append(ann_copy)
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

    def process_parquet_dataset(self):
        """Process a parquet-based dataset (images embedded in parquet files)."""
        import pyarrow.parquet as pq

        logger.info(f"=== Processing parquet dataset: {self.config.dataset} ===")
        self.setup()

        parquet_files = self.list_parquet_files()
        if not parquet_files:
            logger.error("No parquet files found")
            return

        if self.config.dry_run:
            logger.info(f"Dry run - {len(parquet_files)} parquet files")
            for f in parquet_files:
                logger.info(f"  {f}")
            return

        total_success = 0
        total_failed = 0
        total_time = 0.0
        global_batch_num = 0
        temp_dir = self.input_dir / "parquet_extract"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for pq_idx, pq_gcs_path in enumerate(parquet_files):
            logger.info(
                f"=== Parquet {pq_idx + 1}/{len(parquet_files)}: {Path(pq_gcs_path).name} ==="
            )

            # Download parquet
            local_pq = self.input_dir / Path(pq_gcs_path).name
            blob = self.bucket.blob(pq_gcs_path)
            blob.download_to_filename(str(local_pq))
            logger.info(
                f"Downloaded {local_pq.name} ({local_pq.stat().st_size / 1e9:.1f} GB)"
            )

            # Read parquet
            table = pq.read_table(str(local_pq))
            num_rows = len(table)
            logger.info(f"Contains {num_rows} images")

            # Validate expected columns exist
            column_names = set(table.column_names)
            missing_cols = {"filename", "image_data"} - column_names
            if missing_cols:
                logger.error(
                    f"Parquet file {local_pq.name} missing required columns: "
                    f"{sorted(missing_cols)}. Available columns: {sorted(column_names)}"
                )
                local_pq.unlink(missing_ok=True)
                continue

            # Process in batches within this parquet
            for batch_start in range(0, num_rows, self.config.batch_size):
                batch_end = min(batch_start + self.config.batch_size, num_rows)
                results = []

                for row_idx in range(batch_start, batch_end):
                    try:
                        filename = table["filename"][row_idx].as_py()
                        image_data = table["image_data"][row_idx].as_py()
                    except KeyError as e:
                        logger.warning(f"Missing column in parquet row {row_idx}: {e}")
                        continue

                    # Write image to temp file
                    img_path = temp_dir / filename
                    img_path.write_bytes(image_data)

                    # Process
                    source_name = f"{pq_gcs_path}::{filename}"
                    result = self.process_local_file(img_path, source_name)
                    results.append(result)

                    # Cleanup temp image
                    img_path.unlink(missing_ok=True)

                    if (row_idx - batch_start + 1) % 10 == 0:
                        logger.info(
                            f"Progress: {row_idx - batch_start + 1}/{batch_end - batch_start}"
                        )

                self.save_results(results, global_batch_num)

                batch_success = sum(1 for r in results if r.success)
                batch_time = sum(r.processing_time_ms for r in results)
                total_success += batch_success
                total_failed += len(results) - batch_success
                total_time += batch_time

                avg_time = batch_time / len(results) if results else 0
                logger.info(
                    f"Batch {global_batch_num}: {batch_success} success, "
                    f"{len(results) - batch_success} failed, avg {avg_time:.0f}ms/file"
                )
                global_batch_num += 1

            # Cleanup parquet file
            local_pq.unlink(missing_ok=True)
            logger.info(f"Cleaned up {local_pq.name}")

        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        total_images = total_success + total_failed
        if total_images > 0:
            logger.info(
                f"Total time: {total_time / 1000:.1f}s, avg {total_time / total_images:.0f}ms/file"
            )

    def process_arrow_dataset(self):
        """Process an Arrow/HuggingFace dataset (images embedded in Arrow shards)."""
        import pyarrow.ipc as ipc

        logger.info(f"=== Processing arrow dataset: {self.config.dataset} ===")
        self.setup()

        arrow_files = self.list_arrow_files()
        if not arrow_files:
            logger.error("No arrow files found")
            return

        if self.config.dry_run:
            logger.info(f"Dry run - {len(arrow_files)} arrow files")
            for f in arrow_files:
                logger.info(f"  {f}")
            return

        total_success = 0
        total_failed = 0
        total_time = 0.0
        global_batch_num = 0
        temp_dir = self.input_dir / "arrow_extract"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for shard_idx, arrow_gcs_path in enumerate(arrow_files):
            logger.info(
                f"=== Arrow shard {shard_idx + 1}/{len(arrow_files)}: "
                f"{Path(arrow_gcs_path).name} ==="
            )

            # Download arrow shard
            local_arrow = self.input_dir / Path(arrow_gcs_path).name
            blob = self.bucket.blob(arrow_gcs_path)
            blob.download_to_filename(str(local_arrow))
            logger.info(
                f"Downloaded {local_arrow.name} "
                f"({local_arrow.stat().st_size / 1e6:.1f} MB)"
            )

            # Read arrow (HuggingFace streaming format)
            with open(local_arrow, "rb") as f:
                reader = ipc.open_stream(f)
                table = reader.read_all()
            num_rows = len(table)
            logger.info(f"Contains {num_rows} images")

            # Validate the Arrow schema contains the expected 'image' column
            if "image" not in table.column_names:
                logger.error(
                    f"Arrow shard {local_arrow.name} missing required 'image' column. "
                    f"Available columns: {sorted(table.column_names)}"
                )
                local_arrow.unlink(missing_ok=True)
                continue

            # Process in batches within this shard
            for batch_start in range(0, num_rows, self.config.batch_size):
                batch_end = min(batch_start + self.config.batch_size, num_rows)
                results = []

                for row_idx in range(batch_start, batch_end):
                    try:
                        image_col = table["image"][row_idx].as_py()
                        image_bytes = image_col["bytes"]
                        image_path_str = image_col.get("path", f"image_{row_idx}.png")
                    except (KeyError, TypeError) as e:
                        logger.warning(
                            f"Invalid image structure in arrow row {row_idx}: {e}. "
                            f"Expected dict with 'bytes' key."
                        )
                        continue
                    filename = Path(image_path_str).name or f"image_{row_idx}.png"

                    # Write image to temp file
                    img_path = temp_dir / filename
                    img_path.write_bytes(image_bytes)

                    # Process
                    source_name = f"{arrow_gcs_path}::{filename}"
                    result = self.process_local_file(img_path, source_name)
                    results.append(result)

                    # Cleanup temp image
                    img_path.unlink(missing_ok=True)

                    if (row_idx - batch_start + 1) % 10 == 0:
                        logger.info(
                            f"Progress: {row_idx - batch_start + 1}/"
                            f"{batch_end - batch_start}"
                        )

                self.save_results(results, global_batch_num)

                batch_success = sum(1 for r in results if r.success)
                batch_time = sum(r.processing_time_ms for r in results)
                total_success += batch_success
                total_failed += len(results) - batch_success
                total_time += batch_time

                avg_time = batch_time / len(results) if results else 0
                logger.info(
                    f"Batch {global_batch_num}: {batch_success} success, "
                    f"{len(results) - batch_success} failed, avg {avg_time:.0f}ms/file"
                )
                global_batch_num += 1

            # Cleanup arrow file
            local_arrow.unlink(missing_ok=True)
            logger.info(f"Cleaned up {local_arrow.name}")

        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        total_images = total_success + total_failed
        if total_images > 0:
            logger.info(
                f"Total time: {total_time / 1000:.1f}s, "
                f"avg {total_time / total_images:.0f}ms/file"
            )

    def process_zip_dataset(self):
        """Process a dataset stored as a zip archive of PDFs."""
        import zipfile

        logger.info(f"=== Processing zip dataset: {self.config.dataset} ===")
        self.setup()

        zip_filename = ZIP_DATASETS[self.config.dataset]
        gcs_path = f"{GCS_PREFIX}/{DATASETS[self.config.dataset]}/{zip_filename}"

        # Download zip
        local_zip = self.input_dir / zip_filename
        logger.info(f"Downloading {zip_filename} from GCS...")
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(str(local_zip))
        logger.info(
            f"Downloaded {local_zip.name} ({local_zip.stat().st_size / 1e9:.1f} GB)"
        )

        # Extract to temp dir
        extract_dir = self.input_dir / "zip_extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Extracting zip archive...")
        with zipfile.ZipFile(str(local_zip), "r") as zf:
            zf.extractall(str(extract_dir))
        local_zip.unlink(missing_ok=True)

        # Find all PDF/image files in extracted contents
        doc_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
        all_files = sorted(
            f
            for f in extract_dir.rglob("*")
            if f.suffix.lower() in doc_extensions and f.is_file()
        )
        logger.info(f"Found {len(all_files)} documents in zip")

        if self.config.dry_run:
            logger.info(f"Dry run - would process {len(all_files)} files")
            for f in all_files[:10]:
                logger.info(f"  {f.name}")
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
                f"=== Batch {batch_num + 1}/{num_batches} "
                f"({len(batch_files)} files) ==="
            )

            results = []
            for i, file_path in enumerate(batch_files):
                source_name = f"{zip_filename}::{file_path.relative_to(extract_dir)}"
                result = self.process_local_file(file_path, source_name)
                results.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(batch_files)}")

            self.save_results(results, batch_num)

            batch_success = sum(1 for r in results if r.success)
            batch_time = sum(r.processing_time_ms for r in results)
            total_success += batch_success
            total_failed += len(results) - batch_success
            total_time += batch_time

            avg_time = batch_time / len(results) if results else 0
            logger.info(
                f"Batch {batch_num + 1}: {batch_success} success, "
                f"{len(results) - batch_success} failed, avg {avg_time:.0f}ms/file"
            )

        # Cleanup extracted files
        shutil.rmtree(str(extract_dir), ignore_errors=True)

        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        if all_files:
            logger.info(
                f"Total time: {total_time / 1000:.1f}s, "
                f"avg {total_time / len(all_files):.0f}ms/file"
            )

    def process_dataset(self):
        """Process entire dataset in batches."""
        if self.is_parquet_dataset():
            self.process_parquet_dataset()
            return
        if self.is_arrow_dataset():
            self.process_arrow_dataset()
            return
        if self.is_zip_dataset():
            self.process_zip_dataset()
            return

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
    """Run dataset processing CLI."""
    parser = argparse.ArgumentParser(
        description="Process datasets with Docling OCR + native layout extraction"
    )
    parser.add_argument("dataset", nargs="?", help="Dataset name to process")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--batch-size", type=int, default=200, help="Files per batch")
    parser.add_argument(
        "--dry-run", action="store_true", help="List files without processing"
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
        skip_ocr=args.skip_ocr,
    )

    processor = UnifiedProcessor(config)
    processor.process_dataset()


if __name__ == "__main__":
    main()
