#!/usr/bin/env python3
"""
Local Dataset Processor via Docling API

Processes local image datasets through a remote Docling OCR server,
extracting text and layout annotations in COCO format.

Usage:
    python scripts/process_local_datasets_docling.py invoices_kaggle --layout-only
    python scripts/process_local_datasets_docling.py mobile_receipts_voxel51 --text-and-layout
"""

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Dataset paths (relative to base data directory)
BASE_DATA_DIR = Path("/mnt/e/image_detection/01_base_data")

DATASETS = {
    "invoices_kaggle": BASE_DATA_DIR / "forms/invoices_kaggle",
    "mobile_receipts_voxel51": BASE_DATA_DIR / "forms/mobile_receipts_voxel51/images",
    "receipts_hitl": BASE_DATA_DIR / "forms/receipts_hitl/images",
    "sroie_voxel51": BASE_DATA_DIR / "forms/sroie_voxel51_labeled",
}

# Docling API settings
DOCLING_API_URL = "http://192.168.1.209:5001"


@dataclass
class ProcessingConfig:
    dataset: str
    docling_url: str = DOCLING_API_URL
    batch_size: int = 50
    output_dir: Path = field(default_factory=lambda: Path("processing_output"))
    dry_run: bool = False
    extract_text: bool = True
    extract_layout: bool = True
    timeout: float = 120.0  # seconds per file


@dataclass
class ProcessingResult:
    file_path: str
    file_name: str
    # OCR results
    text: str = ""
    markdown: str = ""
    # Layout results
    layout_elements: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    # Metadata
    processing_time_ms: float = 0.0
    success: bool = True
    error: str | None = None


def _extract_text_content(result_data: dict) -> tuple[str, str]:
    """Extract text and markdown from a Docling API response.

    Returns:
        Tuple of (text, markdown).
    """
    if "document" in result_data:
        doc = result_data["document"]
        return doc.get("text", ""), doc.get("markdown", doc.get("md_content", ""))
    if "text" in result_data:
        return result_data["text"], result_data.get(
            "markdown", result_data.get("md_content", "")
        )
    return "", ""


def _extract_layout_and_tables(
    result_data: dict,
) -> tuple[list[dict], list]:
    """Extract layout elements and tables from a Docling API response.

    Returns:
        Tuple of (layout_elements, tables).
    """
    if "document" not in result_data:
        return [], []

    doc = result_data["document"]
    layout_elements: list[dict] = []

    if "main_text" in doc:
        for i, item in enumerate(doc["main_text"]):
            element: dict = {
                "id": i,
                "type": item.get("type", "text"),
                "text": item.get("text", ""),
            }
            if "bbox" in item:
                element["bbox"] = item["bbox"]
            layout_elements.append(element)

    tables = doc.get("tables", [])
    return layout_elements, tables


class LocalDatasetProcessor:
    """Process local datasets through Docling API."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.client = httpx.Client(timeout=config.timeout)

        # Resolve dataset path
        if config.dataset in DATASETS:
            self.dataset_path = DATASETS[config.dataset]
        else:
            self.dataset_path = Path(config.dataset)

        # Output directory
        self.output_dir = config.output_dir / config.dataset

    def check_api_health(self) -> bool:
        """Check if Docling API is available."""
        try:
            response = self.client.get(f"{self.config.docling_url}/health")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Docling API healthy: {data}")
                return True
        except Exception as e:
            logger.error(f"Docling API not available: {e}")
        return False

    def list_image_files(self) -> list[Path]:
        """List all image files in the dataset."""
        if not self.dataset_path.exists():
            logger.error(f"Dataset path not found: {self.dataset_path}")
            return []

        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}

        files = [
            f
            for f in self.dataset_path.rglob("*")
            if f.suffix.lower() in image_extensions
            and not f.name.startswith(".")
            and "__MACOSX" not in str(f)
        ]

        files.sort()
        logger.info(f"Found {len(files)} image files in {self.dataset_path}")
        return files

    def process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file through Docling API."""
        start = time.perf_counter()

        try:
            response = self._call_docling_api(file_path)

            if response.status_code != 200:
                return ProcessingResult(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    processing_time_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=f"API error: {response.status_code} - {response.text[:200]}",
                )

            result_data = response.json()
            text, markdown = _extract_text_content(result_data)
            layout_elements, tables = _extract_layout_and_tables(result_data)

            return ProcessingResult(
                file_path=str(file_path),
                file_name=file_path.name,
                text=text,
                markdown=markdown,
                layout_elements=layout_elements,
                tables=tables,
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=True,
            )

        except Exception as e:
            return ProcessingResult(
                file_path=str(file_path),
                file_name=file_path.name,
                processing_time_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e),
            )

    def _call_docling_api(self, file_path: Path) -> Any:
        """Send a file to the Docling API and return the response."""
        with open(file_path, "rb") as f:
            file_content = f.read()

        files = {"file": (file_path.name, file_content, "image/jpeg")}
        data = {
            "options": json.dumps(
                {
                    "do_ocr": self.config.extract_text,
                    "do_table_structure": True,
                    "generate_markdown": True,
                }
            )
        }
        return self.client.post(
            f"{self.config.docling_url}/v1/convert/file",
            files=files,
            data=data,
        )

    def save_results(self, results: list[ProcessingResult], batch_num: int):
        """Save batch results to output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        jsonl_path = self._save_jsonl(results, batch_num)

        if self.config.extract_layout:
            self._save_coco_layout(results, batch_num)

        logger.info(f"Saved batch {batch_num}: {jsonl_path}")

    def _save_jsonl(
        self,
        results: list[ProcessingResult],
        batch_num: int,
    ) -> Path:
        """Save individual results as JSONL and return the file path."""
        jsonl_path = self.output_dir / f"batch_{batch_num:04d}.jsonl"
        with open(jsonl_path, "w") as f:
            for r in results:
                record = {
                    "file_path": r.file_path,
                    "file_name": r.file_name,
                    "text": r.text if self.config.extract_text else "",
                    "markdown": r.markdown if self.config.extract_text else "",
                    "layout_elements": (
                        r.layout_elements if self.config.extract_layout else []
                    ),
                    "tables": r.tables,
                    "processing_time_ms": r.processing_time_ms,
                    "success": r.success,
                    "error": r.error,
                }
                f.write(json.dumps(record) + "\n")
        return jsonl_path

    def _save_coco_layout(
        self,
        results: list[ProcessingResult],
        batch_num: int,
    ) -> None:
        """Save layout annotations in COCO format."""
        coco_path = self.output_dir / f"layout_coco_batch_{batch_num:04d}.json"
        coco_data: dict = {
            "info": {
                "description": f"Docling layout annotations for {self.config.dataset}",
                "batch": batch_num,
            },
            "images": [],
            "annotations": [],
            "categories": [
                {"id": i, "name": name}
                for i, name in enumerate(
                    [
                        "text",
                        "title",
                        "section_header",
                        "list_item",
                        "table",
                        "figure",
                        "caption",
                        "footnote",
                        "formula",
                        "page_header",
                        "page_footer",
                    ]
                )
            ],
        }

        ann_id = 0
        for img_id, r in enumerate(results):
            if not (r.success and r.layout_elements):
                continue
            coco_data["images"].append(
                {
                    "id": img_id,
                    "file_name": r.file_name,
                    "file_path": r.file_path,
                }
            )
            for elem in r.layout_elements:
                ann: dict = {
                    "id": ann_id,
                    "image_id": img_id,
                    "category_id": self._type_to_category_id(elem.get("type", "text")),
                    "category_name": elem.get("type", "text"),
                }
                if "bbox" in elem:
                    ann["bbox"] = elem["bbox"]
                if "text" in elem:
                    ann["text"] = elem["text"][:500]
                coco_data["annotations"].append(ann)
                ann_id += 1

        with open(coco_path, "w") as f:
            json.dump(coco_data, f, indent=2)

    def _type_to_category_id(self, type_name: str) -> int:
        """Map element type to category ID."""
        mapping = {
            "text": 0,
            "paragraph": 0,
            "title": 1,
            "section_header": 2,
            "heading": 2,
            "list_item": 3,
            "list": 3,
            "table": 4,
            "figure": 5,
            "picture": 5,
            "image": 5,
            "caption": 6,
            "footnote": 7,
            "formula": 8,
            "equation": 8,
            "page_header": 9,
            "header": 9,
            "page_footer": 10,
            "footer": 10,
        }
        return mapping.get(type_name.lower(), 0)

    def _process_batch(
        self,
        batch_files: list[Path],
        batch_num: int,
        num_batches: int,
    ) -> tuple[int, int, float]:
        """Process a single batch and return (success_count, failed_count, time_ms)."""
        logger.info(
            f"=== Batch {batch_num + 1}/{num_batches} ({len(batch_files)} files) ==="
        )

        results = []
        for i, file_path in enumerate(batch_files):
            result = self.process_file(file_path)
            results.append(result)

            status = "+" if result.success else "x"
            if (i + 1) % 10 == 0 or not result.success:
                logger.info(
                    f"  [{i + 1}/{len(batch_files)}] {status} "
                    f"{file_path.name} ({result.processing_time_ms:.0f}ms)"
                )

        self.save_results(results, batch_num)

        batch_success = sum(1 for r in results if r.success)
        batch_time = sum(r.processing_time_ms for r in results)
        batch_failed = len(results) - batch_success

        avg_time = batch_time / len(results) if results else 0
        logger.info(
            f"Batch {batch_num + 1}: {batch_success} success, "
            f"{batch_failed} failed, avg {avg_time:.0f}ms/file"
        )

        return batch_success, batch_failed, batch_time

    def process_dataset(self):
        """Process entire dataset."""
        logger.info(f"=== Processing dataset: {self.config.dataset} ===")
        logger.info(f"Dataset path: {self.dataset_path}")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Extract text: {self.config.extract_text}")
        logger.info(f"Extract layout: {self.config.extract_layout}")

        if not self.check_api_health():
            logger.error("Docling API not available. Exiting.")
            return

        all_files = self.list_image_files()
        if not all_files:
            logger.error("No image files found")
            return

        if self.config.dry_run:
            logger.info(f"Dry run - would process {len(all_files)} files")
            for f in all_files[:10]:
                logger.info(f"  {f}")
            return

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

            s, f, t = self._process_batch(batch_files, batch_num, num_batches)
            total_success += s
            total_failed += f
            total_time += t

        logger.info("=== Processing complete ===")
        logger.info(f"Total: {total_success} success, {total_failed} failed")
        logger.info(
            f"Total time: {total_time / 1000:.1f}s, "
            f"avg {total_time / len(all_files):.0f}ms/file"
        )
        logger.info(f"Output: {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Process local datasets through Docling API"
    )
    parser.add_argument("dataset", nargs="?", help="Dataset name or path")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument(
        "--docling-url", default=DOCLING_API_URL, help="Docling API URL"
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Files per batch")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("processing_output"),
        help="Output directory",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List files without processing"
    )
    parser.add_argument(
        "--layout-only", action="store_true", help="Extract layout only (skip text)"
    )
    parser.add_argument(
        "--text-only", action="store_true", help="Extract text only (skip layout)"
    )
    parser.add_argument(
        "--text-and-layout",
        action="store_true",
        help="Extract both text and layout (default)",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Timeout per file in seconds"
    )

    args = parser.parse_args()

    if args.list:
        print("Available datasets:")
        for name, path in sorted(DATASETS.items()):
            exists = "✓" if path.exists() else "✗"
            count = (
                len(list(path.rglob("*.jpg"))) + len(list(path.rglob("*.png")))
                if path.exists()
                else 0
            )
            print(f"  {exists} {name:30} -> {path} ({count} images)")
        return

    if not args.dataset:
        parser.print_help()
        return

    # Determine extraction mode
    extract_text = True
    extract_layout = True
    if args.layout_only:
        extract_text = False
    if args.text_only:
        extract_layout = False

    config = ProcessingConfig(
        dataset=args.dataset,
        docling_url=args.docling_url,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        extract_text=extract_text,
        extract_layout=extract_layout,
        timeout=args.timeout,
    )

    processor = LocalDatasetProcessor(config)
    processor.process_dataset()


if __name__ == "__main__":
    main()
