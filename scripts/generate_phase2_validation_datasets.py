#!/usr/bin/env python3
"""
Generate comprehensive test datasets for Phase 2 validation.

Creates 4 test datasets:
1. PDF Classification (100 PDFs: born_digital, image_only, hybrid)
2. Layout-Lite (50 documents with layout labels)
3. DQS Correlation (50 documents with synthetic OCR accuracy)
4. Routing Accuracy (50 documents with routing labels)

Uses existing test fixtures from tests/fixtures/phase1_validation/
"""

import json
import random  # nosec B311 - used for non-cryptographic dataset generation
import sys
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.schema import LayoutType, PDFType
from image_preprocessing_detector.utils import get_logger, setup_logging

logger = get_logger(__name__)

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)


class Phase2DatasetGenerator:
    """Generate Phase 2 validation datasets."""

    def __init__(self, fixtures_dir: Path, output_dir: Path):
        """Initialize generator."""
        self.fixtures_dir = fixtures_dir
        self.output_dir = output_dir
        self.images = list((fixtures_dir / "synthetic_images").glob("*.png"))
        self.gradient_images = list(
            (fixtures_dir / "synthetic_images" / "gradients").glob("*.png")
        )

        logger.info(
            "Initialized dataset generator",
            base_images=len(self.images),
            gradient_images=len(self.gradient_images),
        )

    def generate_all_datasets(self) -> dict[str, Any]:
        """Generate all 4 validation datasets."""
        results = {}

        logger.info("Starting dataset generation")

        # Dataset 1: PDF Classification (100 samples)
        results["pdf_classification"] = self.generate_pdf_classification_dataset()

        # Dataset 2: Layout-Lite (50 samples)
        results["layout_lite"] = self.generate_layout_lite_dataset()

        # Dataset 3: DQS Correlation (50 samples)
        results["dqs_correlation"] = self.generate_dqs_correlation_dataset()

        # Dataset 4: Routing Accuracy (50 samples)
        results["routing_accuracy"] = self.generate_routing_accuracy_dataset()

        logger.info("All datasets generated successfully")
        return results

    def generate_pdf_classification_dataset(self) -> dict[str, Any]:
        """Generate 100 PDFs for classification validation."""
        logger.info("Generating PDF classification dataset")

        dataset_dir = self.output_dir / "pdf_classification"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        labels = {"born_digital": [], "image_only": [], "hybrid": []}

        # Born-digital PDFs (40 samples) - text only, no images
        for i in range(40):
            pdf_path = dataset_dir / f"born_digital_{i:03d}.pdf"
            self._create_born_digital_pdf(pdf_path, pages=random.randint(1, 5))
            labels["born_digital"].append(pdf_path.name)

        # Image-only PDFs (40 samples) - images only, no extractable text
        for i in range(40):
            pdf_path = dataset_dir / f"image_only_{i:03d}.pdf"
            image_paths = random.sample(self.images + self.gradient_images, k=random.randint(1, 3))
            self._create_image_only_pdf(pdf_path, image_paths)
            labels["image_only"].append(pdf_path.name)

        # Hybrid PDFs (20 samples) - text + embedded images
        for i in range(20):
            pdf_path = dataset_dir / f"hybrid_{i:03d}.pdf"
            image_paths = random.sample(self.images, k=random.randint(1, 2))
            self._create_hybrid_pdf(pdf_path, image_paths, pages=random.randint(1, 3))
            labels["hybrid"].append(pdf_path.name)

        # Save labels
        labels_file = dataset_dir / "labels.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, indent=2)

        logger.info(
            "PDF classification dataset generated",
            born_digital=len(labels["born_digital"]),
            image_only=len(labels["image_only"]),
            hybrid=len(labels["hybrid"]),
        )

        return {
            "dataset_dir": str(dataset_dir),
            "labels_file": str(labels_file),
            "total_pdfs": 100,
        }

    def generate_layout_lite_dataset(self) -> dict[str, Any]:
        """Generate 50 documents with layout labels."""
        logger.info("Generating layout-lite dataset")

        dataset_dir = self.output_dir / "layout_lite"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        labels = {}

        # Generate 50 PDFs with various layout characteristics
        for i in range(50):
            pdf_path = dataset_dir / f"layout_doc_{i:03d}.pdf"

            # Randomly decide layout characteristics
            layout_type = random.choice([
                "single_column", "multi_column", "three_column", "complex"
            ])
            has_tables = random.random() < 0.3
            has_figures = random.random() < 0.4
            has_dense_math = random.random() < 0.1
            has_handwriting = random.random() < 0.1
            fuzzy_scan = random.random() < 0.2
            watermark = random.random() < 0.1
            colorful_background = random.random() < 0.1

            # Create PDF with characteristics
            num_pages = random.randint(1, 3)
            self._create_layout_pdf(
                pdf_path,
                layout_type=layout_type,
                has_tables=has_tables,
                has_figures=has_figures,
                fuzzy_scan=fuzzy_scan,
                num_pages=num_pages,
            )

            # Create labels for each page
            page_labels = {}
            for page_num in range(1, num_pages + 1):
                page_labels[f"page_{page_num}"] = {
                    "layout_type": layout_type,
                    "has_tables": has_tables,
                    "has_figures": has_figures,
                    "has_dense_math": has_dense_math,
                    "has_handwriting": has_handwriting,
                    "fuzzy_scan": fuzzy_scan,
                    "watermark": watermark,
                    "colorful_background": colorful_background,
                }

            labels[pdf_path.name] = page_labels

        # Save labels
        labels_file = dataset_dir / "layout_labels.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, indent=2)

        logger.info("Layout-lite dataset generated", documents=50)

        return {
            "dataset_dir": str(dataset_dir),
            "labels_file": str(labels_file),
            "total_documents": 50,
        }

    def generate_dqs_correlation_dataset(self) -> dict[str, Any]:
        """Generate 50 documents with synthetic OCR accuracy."""
        logger.info("Generating DQS correlation dataset")

        dataset_dir = self.output_dir / "dqs_correlation"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        ocr_accuracy = {}

        # Generate 50 images with varying quality levels
        for i in range(50):
            # Select image based on degradation level
            if i < 10:
                # Clean images (high OCR accuracy)
                source = [img for img in self.images if "clean" in str(img)]
                expected_accuracy = random.uniform(0.95, 0.99)
            elif i < 25:
                # Moderate degradation
                source = [img for img in self.images if "blur_k5" in str(img) or "contrast" in str(img)]
                expected_accuracy = random.uniform(0.75, 0.90)
            else:
                # Heavy degradation
                source = [img for img in self.images + self.gradient_images if "blur_k" in str(img) or "skew" in str(img)]
                expected_accuracy = random.uniform(0.40, 0.70)

            if not source:
                source = self.images

            source_img = random.choice(source)
            img_path = dataset_dir / f"dqs_doc_{i:03d}.png"

            # Copy image
            img = cv2.imread(str(source_img))
            cv2.imwrite(str(img_path), img)

            # Synthetic OCR accuracy (inversely correlated with degradation)
            ocr_accuracy[img_path.name] = {
                "character_accuracy": expected_accuracy,
                "word_accuracy": expected_accuracy - random.uniform(0.02, 0.05),
                "source_degradation": "clean" if i < 10 else "moderate" if i < 25 else "heavy",
            }

        # Save OCR accuracy labels
        labels_file = dataset_dir / "ocr_accuracy.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(ocr_accuracy, f, indent=2)

        logger.info("DQS correlation dataset generated", documents=50)

        return {
            "dataset_dir": str(dataset_dir),
            "labels_file": str(labels_file),
            "total_documents": 50,
        }

    def generate_routing_accuracy_dataset(self) -> dict[str, Any]:
        """Generate 50 documents with routing labels."""
        logger.info("Generating routing accuracy dataset")

        dataset_dir = self.output_dir / "routing_accuracy"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        routing_labels = {}

        # Generate 50 PDFs with known routing recommendations
        for i in range(50):
            pdf_path = dataset_dir / f"routing_doc_{i:03d}.pdf"

            # Determine routing based on document characteristics
            if i < 15:
                # Clean born-digital → ocr_fast
                self._create_born_digital_pdf(pdf_path, pages=random.randint(1, 3))
                routing = "ocr_fast"
                pdf_type = "born_digital"
            elif i < 30:
                # Degraded image-only → ocr_advanced
                source_imgs = [img for img in self.images if "blur" in str(img) or "skew" in str(img)]
                self._create_image_only_pdf(pdf_path, random.sample(source_imgs, k=2))
                routing = "ocr_advanced"
                pdf_type = "image_only"
            elif i < 40:
                # Documents with tables → vision_structured
                self._create_hybrid_pdf(pdf_path, random.sample(self.images, k=1), pages=1)
                routing = "vision_structured"
                pdf_type = "hybrid"
            else:
                # Simple images → vision_simple
                source_imgs = [img for img in self.images if "clean" in str(img)]
                self._create_image_only_pdf(pdf_path, random.sample(source_imgs, k=1))
                routing = "vision_simple"
                pdf_type = "image_only"

            routing_labels[pdf_path.name] = {
                "expected_routing": routing,
                "pdf_type": pdf_type,
                "rationale": f"Test case {i}: {routing} based on {pdf_type}",
            }

        # Save routing labels
        labels_file = dataset_dir / "routing_labels.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(routing_labels, f, indent=2)

        logger.info("Routing accuracy dataset generated", documents=50)

        return {
            "dataset_dir": str(dataset_dir),
            "labels_file": str(labels_file),
            "total_documents": 50,
        }

    def _create_born_digital_pdf(self, output_path: Path, pages: int = 1) -> None:
        """Create a born-digital PDF with text only."""
        doc = fitz.open()

        for page_num in range(pages):
            page = doc.new_page(width=595, height=842)  # A4

            # Add substantial text
            text = f"Born-Digital Document - Page {page_num + 1}\n\n"
            text += "This is a clean, text-based PDF document with no embedded images. "
            text += "It represents the ideal case for OCR fast routing. " * 10

            page.insert_text((50, 50 + page_num * 10), text, fontsize=12)

        doc.save(str(output_path))
        doc.close()

    def _create_image_only_pdf(self, output_path: Path, image_paths: list[Path]) -> None:
        """Create an image-only PDF with embedded images."""
        doc = fitz.open()

        for img_path in image_paths:
            page = doc.new_page(width=595, height=842)

            # Embed image (no text)
            page.insert_image(fitz.Rect(50, 50, 545, 792), filename=str(img_path))

        doc.save(str(output_path))
        doc.close()

    def _create_hybrid_pdf(self, output_path: Path, image_paths: list[Path], pages: int = 1) -> None:
        """Create a hybrid PDF with text and embedded images."""
        doc = fitz.open()

        for page_num in range(pages):
            page = doc.new_page(width=595, height=842)

            # Add text
            text = f"Hybrid Document - Page {page_num + 1}\n\n"
            text += "This document contains both text and embedded images. "
            text += "It requires vision-based structured extraction. " * 5

            page.insert_text((50, 50), text, fontsize=12)

            # Embed image if available
            if page_num < len(image_paths):
                page.insert_image(
                    fitz.Rect(100, 300, 500, 700),
                    filename=str(image_paths[page_num]),
                )

        doc.save(str(output_path))
        doc.close()

    def _create_layout_pdf(
        self,
        output_path: Path,
        layout_type: str,
        has_tables: bool,
        has_figures: bool,
        fuzzy_scan: bool,
        num_pages: int,
    ) -> None:
        """Create a PDF with specific layout characteristics."""
        doc = fitz.open()

        for page_num in range(num_pages):
            page = doc.new_page(width=595, height=842)

            # Add text based on layout type
            if layout_type == "single_column":
                text = "Single column layout. " * 50
                page.insert_text((50, 50), text, fontsize=12)
            elif layout_type == "multi_column":
                # Simulate multi-column with two text blocks
                text_left = "Left column. " * 25
                text_right = "Right column. " * 25
                page.insert_text((50, 50), text_left, fontsize=10)
                page.insert_text((320, 50), text_right, fontsize=10)
            else:
                # Complex layout
                text = "Complex layout with mixed content. " * 30
                page.insert_text((50, 50), text, fontsize=11)

            # Add table simulation if needed
            if has_tables:
                page.insert_text((50, 400), "Table Header | Column 1 | Column 2", fontsize=10)
                page.insert_text((50, 420), "Row 1       | Data A   | Data B", fontsize=10)

            # Add figure if needed
            if has_figures and self.images:
                fig_img = random.choice(self.images)
                page.insert_image(fitz.Rect(400, 600, 550, 750), filename=str(fig_img))

        doc.save(str(output_path))
        doc.close()


def main() -> int:
    """Generate Phase 2 validation datasets."""
    setup_logging(level="INFO", json_logs=False)

    # Paths
    fixtures_dir = Path(__file__).parents[1] / "tests" / "fixtures" / "phase1_validation" / "data"
    output_dir = Path(__file__).parents[1] / "tests" / "fixtures" / "phase2_validation"

    if not fixtures_dir.exists():
        logger.error("Fixtures directory not found", path=str(fixtures_dir))
        return 1

    # Generate datasets
    generator = Phase2DatasetGenerator(fixtures_dir, output_dir)
    results = generator.generate_all_datasets()

    # Print summary
    print("\n" + "=" * 70)  # noqa: T201
    print("Phase 2 Validation Datasets Generated")  # noqa: T201
    print("=" * 70)  # noqa: T201

    for dataset_name, dataset_info in results.items():
        print(f"\n{dataset_name.upper()}:")  # noqa: T201
        for key, value in dataset_info.items():
            print(f"  {key}: {value}")  # noqa: T201

    print("\n" + "=" * 70)  # noqa: T201
    print(f"All datasets saved to: {output_dir}")  # noqa: T201
    print("=" * 70)  # noqa: T201

    return 0


if __name__ == "__main__":
    sys.exit(main())
