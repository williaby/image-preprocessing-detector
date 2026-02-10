#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Prepare Orientation Detection Training Dataset for Phase 10A.

Generates a 50,000 sample dataset for training orientation detection CNN
(MobileNetV4-Conv-S) with document-level splitting to prevent data leakage.

Key Requirements (from MOBILECLIP2_S4_S0_DATASET_DESIGN.md):
- 12,500 unique source documents
- 4 rotations each (0°, 90°, 180°, 270°) = 50,000 samples
- Document-level split (70% train, 15% val, 15% test) BEFORE rotation
- 50% degradation augmentation (35% light, 15% moderate)
- 1,250 Japanese vertical text samples (labeled as 0°, not 270°)

Output: /mnt/e/image_detection/03_training_datasets/orientation/

Usage:
    uv run python scripts/prepare_orientation_dataset.py --dry-run
    uv run python scripts/prepare_orientation_dataset.py --output /mnt/e/image_detection/03_training_datasets/orientation
"""

import argparse
import hashlib
import json
import random  # nosec B311 - used for non-cryptographic dataset shuffling/sampling
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class DatasetConfig:
    """Configuration for orientation dataset generation.

    Based on MOBILECLIP2_S4_S0_DATASET_DESIGN.md specifications.
    """

    # Total unique documents needed (will be rotated 4x each)
    TOTAL_UNIQUE_DOCS: int = 12_500

    # Split ratios (document-level, BEFORE rotation)
    TRAIN_RATIO: float = 0.70
    VAL_RATIO: float = 0.15
    TEST_RATIO: float = 0.15

    # Rotation classes
    ROTATION_ANGLES: list[int] = field(default_factory=lambda: [0, 90, 180, 270])

    # Source dataset composition (from spec)
    SOURCE_COMPOSITION: dict[str, int] = field(
        default_factory=lambda: {
            "doclaynet_scientific": 2_500,  # Scientific papers
            "doclaynet_financial": 1_875,  # Financial reports (reduced)
            "doclaynet_legal": 1_000,  # Legal documents
            "doclaynet_mixed": 500,  # Mixed layouts (manuals, patents)
            "tablebank": 1_000,  # Table-heavy documents
            "pubtabnet": 1_000,  # Scientific tables
            "rvl_cdip": 2_000,  # Real scans (diverse quality)
            "funsd": 149,  # Forms (FUNSD original - 149 train)
            "funsd_plus": 750,  # Forms (FUNSD+)
            "sroie": 1_000,  # Receipts
            "nist_sd19": 1_000,  # Handwriting pages
            # Real-world government financial documents
            "bhutan_financial": 125,  # Bhutan Financial (AFS 2024 + Tax Act 2021, 10 exclusions)
            # Multilingual script datasets (Phase 10A)
            "jssoda_vertical": 991,  # Japanese vertical text (labeled as 0°)
            "jssoda_horizontal": 1_009,  # Japanese horizontal text
            "arabic_ocr": 500,  # Arabic (RTL) documents
            # NOTE: dzongkha_digits excluded - single isolated digits, not documents
            # Useful for script detection (Phase 10B) but not orientation detection
        }
    )

    # Degradation distribution
    CLEAN_RATIO: float = 0.50  # 50% clean
    LIGHT_DEGRADED_RATIO: float = 0.35  # 35% light
    MODERATE_DEGRADED_RATIO: float = 0.15  # 15% moderate

    # Camera vs Scanner degradation split (within degraded samples)
    CAMERA_DEGRADATION_RATIO: float = 0.60
    SCANNER_DEGRADATION_RATIO: float = 0.40

    # Output image size (will be resized for training to 224x224)
    OUTPUT_MAX_SIZE: int = 1024  # Max dimension

    # Japanese vertical text samples
    JAPANESE_VERTICAL_COUNT: int = 1_250


@dataclass
class SourceDocument:
    """Represents a source document before rotation."""

    doc_id: str
    source_dataset: str
    document_type: str
    image_path: Path
    contains_tables: bool = False
    contains_handwriting: bool = False
    layout_complexity: str = "single_column"
    is_vertical_text: bool = False
    text_orientation: str = "horizontal_ltr"


@dataclass
class OrientationSample:
    """Represents a single sample in the orientation dataset."""

    sample_id: str
    source_doc_id: str
    source_dataset: str
    document_type: str
    orientation_class: int  # 0, 1, 2, 3 (for 0°, 90°, 180°, 270°)
    orientation_degrees: int  # 0, 90, 180, 270
    split: str  # train, val, test
    quality_variant: str  # clean, light_degraded, moderate_degraded
    degradation_types: list[str]
    contains_tables: bool
    contains_handwriting: bool
    layout_complexity: str
    is_vertical_text: bool
    text_orientation: str
    generation_timestamp: str
    output_path: str


class OrientationDatasetGenerator:
    """Generate orientation detection training dataset."""

    def __init__(
        self,
        base_data_path: Path,
        output_path: Path,
        config: DatasetConfig | None = None,
        seed: int = 42,
    ):
        self.base_data_path = base_data_path
        self.output_path = output_path
        self.config = config or DatasetConfig()
        self.seed = seed

        # Set random seeds for reproducibility
        random.seed(seed)
        np.random.seed(seed)

        # Tracking
        self.source_documents: list[SourceDocument] = []
        self.samples: list[OrientationSample] = []
        self.split_assignments: dict[str, str] = {}  # doc_id -> split

        # Statistics
        self.stats: dict[str, int] = defaultdict(int)

    def collect_source_documents(self) -> list[SourceDocument]:
        """Collect source documents from all configured datasets."""
        documents = []

        print("\n=== Collecting Source Documents ===\n")

        # Collect from each source dataset
        for source_name, target_count in self.config.SOURCE_COMPOSITION.items():
            source_docs = self._collect_from_source(source_name, target_count)
            documents.extend(source_docs)
            print(f"  {source_name}: {len(source_docs):,} documents")

        print(f"\n  Total collected: {len(documents):,} documents")
        print(f"  Target: {self.config.TOTAL_UNIQUE_DOCS:,} documents")

        # Trim to exact target if we have more
        if len(documents) > self.config.TOTAL_UNIQUE_DOCS:
            random.shuffle(documents)
            documents = documents[: self.config.TOTAL_UNIQUE_DOCS]
            print(f"  Trimmed to: {len(documents):,} documents")

        self.source_documents = documents
        return documents

    def _collect_from_source(
        self, source_name: str, target_count: int
    ) -> list[SourceDocument]:
        """Collect documents from a specific source dataset."""
        documents = []

        # Map source names to actual paths
        source_paths = {
            "doclaynet_scientific": self.base_data_path / "documents" / "doclaynet",
            "doclaynet_financial": self.base_data_path / "documents" / "doclaynet",
            "doclaynet_legal": self.base_data_path / "documents" / "doclaynet",
            "doclaynet_mixed": self.base_data_path / "documents" / "doclaynet",
            "tablebank": self.base_data_path / "tables" / "tablebank",
            "pubtabnet": self.base_data_path / "tables" / "pubtabnet",
            "rvl_cdip": self.base_data_path / "documents" / "rvl_cdip",
            "funsd": self.base_data_path / "forms" / "funsd",
            "funsd_plus": self.base_data_path / "forms" / "funsd_plus",
            "sroie": self.base_data_path / "forms" / "sroie",
            "nist_sd19": self.base_data_path / "handwriting" / "nist-sd19",
            # Real-world government financial documents
            "bhutan_financial": self.base_data_path / "documents" / "bhutan_financial",
            # Multilingual script datasets (Phase 10A)
            "jssoda_vertical": self.base_data_path
            / "language"
            / "multilingual_scripts"
            / "jssoda"
            / "vertical",
            "jssoda_horizontal": self.base_data_path
            / "language"
            / "multilingual_scripts"
            / "jssoda"
            / "horizontal",
            "arabic_ocr": self.base_data_path
            / "language"
            / "multilingual_scripts"
            / "arabic_ocr",
        }

        source_path = source_paths.get(source_name)
        if source_path is None or not source_path.exists():
            print(f"    WARNING: Source path not found: {source_path}")
            return []

        # Determine document type based on source
        doc_type_map = {
            "doclaynet_scientific": "scientific",
            "doclaynet_financial": "financial",
            "doclaynet_legal": "legal",
            "doclaynet_mixed": "mixed",
            "tablebank": "table",
            "pubtabnet": "table",
            "rvl_cdip": "scan",
            "funsd": "form",
            "funsd_plus": "form",
            "sroie": "receipt",
            "nist_sd19": "handwriting",
            # Real-world government financial documents
            "bhutan_financial": "financial",
            # Multilingual script datasets (Phase 10A)
            "jssoda_vertical": "japanese_vertical",
            "jssoda_horizontal": "japanese_horizontal",
            "arabic_ocr": "arabic",
        }
        doc_type = doc_type_map.get(source_name, "unknown")

        # Determine if this is vertical text (critical for orientation labeling)
        is_vertical = source_name == "jssoda_vertical"
        text_orientation = "vertical_ttb" if is_vertical else "horizontal_ltr"

        # Collect image files
        image_extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
        image_files = []

        for ext in image_extensions:
            image_files.extend(source_path.rglob(f"*{ext}"))
            image_files.extend(source_path.rglob(f"*{ext.upper()}"))

        # Sample from available files
        if len(image_files) > target_count:
            random.shuffle(image_files)
            image_files = image_files[:target_count]

        # Create SourceDocument objects
        for img_path in image_files:
            doc_id = self._generate_doc_id(source_name, img_path)
            doc = SourceDocument(
                doc_id=doc_id,
                source_dataset=source_name.split("_")[0],  # e.g., "doclaynet"
                document_type=doc_type,
                image_path=img_path,
                contains_tables=(doc_type == "table"),
                contains_handwriting=(doc_type == "handwriting"),
                layout_complexity=self._infer_layout_complexity(source_name),
                is_vertical_text=is_vertical,
                text_orientation=text_orientation,
            )
            documents.append(doc)

        return documents

    def _generate_doc_id(self, source_name: str, image_path: Path) -> str:
        """Generate a unique document ID."""
        # Use hash of source + path for uniqueness
        hash_input = f"{source_name}_{image_path.stem}"
        hash_val = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[
            :8
        ]
        return f"{source_name}_{hash_val}"

    def _infer_layout_complexity(self, source_name: str) -> str:
        """Infer layout complexity from source dataset."""
        if source_name in ("doclaynet_scientific", "doclaynet_financial"):
            return "multi_column"
        if source_name in ("funsd", "funsd_plus", "sroie"):
            return "form"
        if source_name in ("tablebank", "pubtabnet"):
            return "table"
        if source_name in ("jssoda_vertical", "jssoda_horizontal"):
            return "multilingual_text"
        if source_name == "arabic_ocr":
            return "multilingual_script"
        return "single_column"

    def split_documents(self) -> dict[str, list[SourceDocument]]:
        """Split documents into train/val/test BEFORE rotation.

        CRITICAL: This prevents data leakage by ensuring no document
        appears in multiple splits.
        """
        print("\n=== Splitting Documents (BEFORE Rotation) ===\n")

        # Shuffle documents for random split
        docs = self.source_documents.copy()
        random.shuffle(docs)

        # Calculate split sizes
        total = len(docs)
        train_size = int(total * self.config.TRAIN_RATIO)
        val_size = int(total * self.config.VAL_RATIO)
        # test_size = total - train_size - val_size

        # Split
        train_docs = docs[:train_size]
        val_docs = docs[train_size : train_size + val_size]
        test_docs = docs[train_size + val_size :]

        # Record split assignments
        for doc in train_docs:
            self.split_assignments[doc.doc_id] = "train"
        for doc in val_docs:
            self.split_assignments[doc.doc_id] = "val"
        for doc in test_docs:
            self.split_assignments[doc.doc_id] = "test"

        # Verify no overlap
        train_ids = {d.doc_id for d in train_docs}
        val_ids = {d.doc_id for d in val_docs}
        test_ids = {d.doc_id for d in test_docs}

        assert len(train_ids & val_ids) == 0, "Train/Val overlap detected!"
        assert len(train_ids & test_ids) == 0, "Train/Test overlap detected!"
        assert len(val_ids & test_ids) == 0, "Val/Test overlap detected!"

        print(
            f"  Train: {len(train_docs):,} documents ({len(train_docs) * 4:,} samples)"
        )
        print(f"  Val:   {len(val_docs):,} documents ({len(val_docs) * 4:,} samples)")
        print(f"  Test:  {len(test_docs):,} documents ({len(test_docs) * 4:,} samples)")
        print("  ✓ No document ID overlap between splits")

        return {"train": train_docs, "val": val_docs, "test": test_docs}

    def apply_rotation(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Rotate image to target orientation.

        Args:
            image: Source document image (BGR format)
            angle: Target rotation in degrees (0, 90, 180, 270)

        Returns:
            Rotated image
        """
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        if angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image  # 0° - no rotation

    def apply_degradation(
        self, image: np.ndarray, quality_level: str
    ) -> tuple[np.ndarray, list[str]]:
        """Apply degradation augmentation to image.

        Args:
            image: Source image (BGR format)
            quality_level: One of 'clean', 'light_degraded', 'moderate_degraded'

        Returns:
            Tuple of (degraded_image, list_of_applied_degradations)
        """
        if quality_level == "clean":
            return image, []

        degradation_types = []

        # Determine camera vs scanner profile
        is_camera = random.random() < self.config.CAMERA_DEGRADATION_RATIO

        if quality_level == "light_degraded":
            if is_camera:
                # Camera artifacts (light)
                if random.random() < 0.20:
                    image = self._apply_motion_blur(image, kernel_size=3)
                    degradation_types.append("motion_blur")
                if random.random() < 0.15:
                    image = self._apply_perspective_warp(image, strength=0.02)
                    degradation_types.append("perspective_warp")
                if random.random() < 0.20:
                    image = self._apply_soft_shadow(image)
                    degradation_types.append("shadow")
            else:
                # Scanner artifacts (light)
                if random.random() < 0.30:
                    image = self._apply_gaussian_blur(image, sigma=0.7)
                    degradation_types.append("gaussian_blur")
                if random.random() < 0.25:
                    image = self._apply_noise(image, std=10)
                    degradation_types.append("noise")
                if random.random() < 0.40:
                    image = self._apply_jpeg_compression(image, quality=80)
                    degradation_types.append("jpeg_compression")

        elif quality_level == "moderate_degraded":
            if is_camera:
                # Camera artifacts (moderate)
                if random.random() < 0.30:
                    image = self._apply_motion_blur(image, kernel_size=5)
                    degradation_types.append("motion_blur")
                if random.random() < 0.25:
                    image = self._apply_perspective_warp(image, strength=0.05)
                    degradation_types.append("perspective_warp")
                if random.random() < 0.30:
                    image = self._apply_hard_shadow(image)
                    degradation_types.append("shadow")
                if random.random() < 0.35:
                    image = self._apply_uneven_lighting(image)
                    degradation_types.append("uneven_lighting")
                if random.random() < 0.25:
                    image = self._apply_noise(image, std=20)
                    degradation_types.append("iso_noise")
            else:
                # Scanner artifacts (moderate)
                if random.random() < 0.30:
                    image = self._apply_gaussian_blur(image, sigma=1.2)
                    degradation_types.append("gaussian_blur")
                if random.random() < 0.30:
                    image = self._apply_noise(image, std=25)
                    degradation_types.append("scan_noise")
                if random.random() < 0.50:
                    image = self._apply_jpeg_compression(image, quality=60)
                    degradation_types.append("jpeg_compression")
                if random.random() < 0.15:
                    image = self._apply_slight_skew(image)
                    degradation_types.append("slight_skew")

        return image, degradation_types

    def _apply_gaussian_blur(self, image: np.ndarray, sigma: float) -> np.ndarray:
        """Apply Gaussian blur."""
        ksize = int(sigma * 4) | 1  # Ensure odd
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)

    def _apply_motion_blur(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """Apply motion blur."""
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[kernel_size // 2, :] = 1.0 / kernel_size
        return cv2.filter2D(image, -1, kernel)

    def _apply_noise(self, image: np.ndarray, std: float) -> np.ndarray:
        """Apply Gaussian noise."""
        noise = np.random.normal(0, std, image.shape).astype(np.float32)
        noisy = image.astype(np.float32) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)

    def _apply_jpeg_compression(self, image: np.ndarray, quality: int) -> np.ndarray:
        """Apply JPEG compression artifacts."""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, encoded = cv2.imencode(".jpg", image, encode_param)
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    def _apply_perspective_warp(self, image: np.ndarray, strength: float) -> np.ndarray:
        """Apply slight perspective distortion."""
        h, w = image.shape[:2]
        offset = int(min(h, w) * strength)

        # Random corner displacements
        src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst_pts = np.float32(
            [
                [random.randint(0, offset), random.randint(0, offset)],
                [w - random.randint(0, offset), random.randint(0, offset)],
                [w - random.randint(0, offset), h - random.randint(0, offset)],
                [random.randint(0, offset), h - random.randint(0, offset)],
            ]
        )

        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        return cv2.warpPerspective(image, matrix, (w, h), borderValue=(255, 255, 255))

    def _apply_soft_shadow(self, image: np.ndarray) -> np.ndarray:
        """Apply soft shadow effect."""
        h, w = image.shape[:2]
        shadow = np.ones((h, w), dtype=np.float32)

        # Random gradient direction
        if random.random() < 0.5:
            for i in range(w):
                shadow[:, i] = 0.7 + 0.3 * (i / w)
        else:
            for i in range(h):
                shadow[i, :] = 0.7 + 0.3 * (i / h)

        shadow = shadow[:, :, np.newaxis]
        return (image.astype(np.float32) * shadow).astype(np.uint8)

    def _apply_hard_shadow(self, image: np.ndarray) -> np.ndarray:
        """Apply hard shadow effect."""
        h, w = image.shape[:2]
        shadow = np.ones((h, w), dtype=np.float32)

        # Create rectangular shadow region
        x1 = random.randint(0, w // 3)
        y1 = random.randint(0, h // 3)
        x2 = random.randint(w // 2, w)
        y2 = random.randint(h // 2, h)
        shadow[y1:y2, x1:x2] = 0.5

        shadow = shadow[:, :, np.newaxis]
        return (image.astype(np.float32) * shadow).astype(np.uint8)

    def _apply_uneven_lighting(self, image: np.ndarray) -> np.ndarray:
        """Apply uneven lighting effect."""
        h, w = image.shape[:2]

        # Create radial gradient
        center_x = random.randint(w // 4, 3 * w // 4)
        center_y = random.randint(h // 4, 3 * h // 4)

        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_dist = np.sqrt(h**2 + w**2)
        lighting = 0.6 + 0.4 * (1 - dist / max_dist)

        lighting = lighting[:, :, np.newaxis]
        return (image.astype(np.float32) * lighting).astype(np.uint8)

    def _apply_slight_skew(self, image: np.ndarray) -> np.ndarray:
        """Apply slight rotation (1-2 degrees)."""
        h, w = image.shape[:2]
        angle = random.uniform(-2, 2)
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (w, h), borderValue=(255, 255, 255))

    def _determine_quality_level(self) -> str:
        """Determine quality level for a sample based on distribution."""
        r = random.random()
        if r < self.config.CLEAN_RATIO:
            return "clean"
        if r < self.config.CLEAN_RATIO + self.config.LIGHT_DEGRADED_RATIO:
            return "light_degraded"
        return "moderate_degraded"

    def generate_samples(
        self,
        split_docs: dict[str, list[SourceDocument]],
        dry_run: bool = False,
    ) -> list[OrientationSample]:
        """Generate all samples by rotating and augmenting documents."""
        print("\n=== Generating Samples ===\n")

        all_samples = []
        timestamp = datetime.now(tz=None).isoformat()

        # Create output directories
        if not dry_run:
            for split in ["train", "val", "test"]:
                for angle in self.config.ROTATION_ANGLES:
                    (self.output_path / split / f"{angle}deg").mkdir(
                        parents=True, exist_ok=True
                    )
            (self.output_path / "labels").mkdir(parents=True, exist_ok=True)
            (self.output_path / "metadata").mkdir(parents=True, exist_ok=True)

        for split_name, docs in split_docs.items():
            print(f"\n  Processing {split_name} split ({len(docs)} documents)...")

            for doc in tqdm(docs, desc=f"  {split_name}"):
                # Load image
                if not dry_run:
                    image = cv2.imread(str(doc.image_path))
                    if image is None:
                        print(f"    WARNING: Could not load {doc.image_path}")
                        continue

                    # Resize if needed
                    h, w = image.shape[:2]
                    if max(h, w) > self.config.OUTPUT_MAX_SIZE:
                        scale = self.config.OUTPUT_MAX_SIZE / max(h, w)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        image = cv2.resize(image, (new_w, new_h))

                # Generate 4 rotations for this document
                for angle in self.config.ROTATION_ANGLES:
                    # Determine quality level
                    quality_level = self._determine_quality_level()

                    # Apply rotation
                    if not dry_run:
                        rotated = self.apply_rotation(image, angle)

                        # Apply degradation
                        degraded, degradation_types = self.apply_degradation(
                            rotated, quality_level
                        )
                    else:
                        degradation_types = []

                    # Create sample record
                    sample_id = f"{doc.doc_id}_{angle}deg"
                    output_rel_path = f"{split_name}/{angle}deg/{sample_id}.png"

                    sample = OrientationSample(
                        sample_id=sample_id,
                        source_doc_id=doc.doc_id,
                        source_dataset=doc.source_dataset,
                        document_type=doc.document_type,
                        orientation_class=self.config.ROTATION_ANGLES.index(angle),
                        orientation_degrees=angle,
                        split=split_name,
                        quality_variant=quality_level,
                        degradation_types=degradation_types,
                        contains_tables=doc.contains_tables,
                        contains_handwriting=doc.contains_handwriting,
                        layout_complexity=doc.layout_complexity,
                        is_vertical_text=doc.is_vertical_text,
                        text_orientation=doc.text_orientation,
                        generation_timestamp=timestamp,
                        output_path=output_rel_path,
                    )

                    all_samples.append(sample)

                    # Save image
                    if not dry_run:
                        output_file = self.output_path / output_rel_path
                        cv2.imwrite(str(output_file), degraded)

                    # Track statistics
                    self.stats[f"{split_name}_total"] += 1
                    self.stats[f"{split_name}_{angle}deg"] += 1
                    self.stats[f"quality_{quality_level}"] += 1

        self.samples = all_samples
        return all_samples

    def write_labels(self, samples: list[OrientationSample], dry_run: bool = False):
        """Write JSONL label files for each split."""
        print("\n=== Writing Label Files ===\n")

        splits = {"train": [], "val": [], "test": []}

        for sample in samples:
            label_entry = {
                "image_path": sample.output_path,
                "orientation_class": sample.orientation_class,
                "orientation_degrees": sample.orientation_degrees,
                "source_document_id": sample.source_doc_id,
                "source_dataset": sample.source_dataset,
                "document_type": sample.document_type,
                "split": sample.split,
                "contains_tables": sample.contains_tables,
                "contains_handwriting": sample.contains_handwriting,
                "layout_complexity": sample.layout_complexity,
                "quality_variant": sample.quality_variant,
                "degradation_types": sample.degradation_types,
                "is_vertical_text": sample.is_vertical_text,
                "text_orientation": sample.text_orientation,
                "generation_timestamp": sample.generation_timestamp,
            }
            splits[sample.split].append(label_entry)

        for split_name, entries in splits.items():
            label_file = self.output_path / "labels" / f"{split_name}_labels.jsonl"
            print(f"  {split_name}_labels.jsonl: {len(entries):,} entries")

            if not dry_run:
                with open(label_file, "w") as f:
                    f.writelines(json.dumps(entry) + "\n" for entry in entries)

    def write_metadata(self, dry_run: bool = False):
        """Write metadata files."""
        print("\n=== Writing Metadata Files ===\n")

        # Source documents metadata
        source_docs_meta = [
            {
                "doc_id": doc.doc_id,
                "source_dataset": doc.source_dataset,
                "document_type": doc.document_type,
                "split": self.split_assignments.get(doc.doc_id, "unknown"),
                "image_path": str(doc.image_path),
            }
            for doc in self.source_documents
        ]

        # Split assignments
        split_meta = {
            "train_doc_ids": [
                d.doc_id
                for d in self.source_documents
                if self.split_assignments.get(d.doc_id) == "train"
            ],
            "val_doc_ids": [
                d.doc_id
                for d in self.source_documents
                if self.split_assignments.get(d.doc_id) == "val"
            ],
            "test_doc_ids": [
                d.doc_id
                for d in self.source_documents
                if self.split_assignments.get(d.doc_id) == "test"
            ],
        }

        # Generation config
        gen_config = {
            "total_unique_documents": len(self.source_documents),
            "total_samples": len(self.samples),
            "rotation_angles": self.config.ROTATION_ANGLES,
            "train_ratio": self.config.TRAIN_RATIO,
            "val_ratio": self.config.VAL_RATIO,
            "test_ratio": self.config.TEST_RATIO,
            "clean_ratio": self.config.CLEAN_RATIO,
            "light_degraded_ratio": self.config.LIGHT_DEGRADED_RATIO,
            "moderate_degraded_ratio": self.config.MODERATE_DEGRADED_RATIO,
            "random_seed": self.seed,
            "generation_timestamp": datetime.now(tz=None).isoformat(),
            "spec_reference": "MOBILECLIP2_S4_S0_DATASET_DESIGN.md",
        }

        if not dry_run:
            with open(
                self.output_path / "metadata" / "source_documents.json", "w"
            ) as f:
                json.dump(source_docs_meta, f, indent=2)

            with open(
                self.output_path / "metadata" / "split_assignments.json", "w"
            ) as f:
                json.dump(split_meta, f, indent=2)

            with open(
                self.output_path / "metadata" / "generation_config.json", "w"
            ) as f:
                json.dump(gen_config, f, indent=2)

        print(f"  source_documents.json: {len(source_docs_meta):,} documents")
        print(
            f"  split_assignments.json: train={len(split_meta['train_doc_ids'])}, "
            f"val={len(split_meta['val_doc_ids'])}, test={len(split_meta['test_doc_ids'])}"
        )
        print("  generation_config.json: configuration saved")

    def print_statistics(self):
        """Print generation statistics."""
        print("\n=== Dataset Statistics ===\n")

        print("  By Split:")
        for split in ["train", "val", "test"]:
            total = self.stats.get(f"{split}_total", 0)
            print(f"    {split}: {total:,} samples")
            for angle in self.config.ROTATION_ANGLES:
                count = self.stats.get(f"{split}_{angle}deg", 0)
                print(f"      {angle}°: {count:,}")

        print("\n  By Quality Level:")
        for level in ["clean", "light_degraded", "moderate_degraded"]:
            count = self.stats.get(f"quality_{level}", 0)
            pct = (count / max(sum(self.stats.values()) // 4, 1)) * 100
            print(f"    {level}: {count:,} ({pct:.1f}%)")

        total_samples = sum(
            self.stats.get(f"{split}_total", 0) for split in ["train", "val", "test"]
        )
        print(f"\n  Total Samples: {total_samples:,}")
        print("  Target: 50,000")

    def generate(self, dry_run: bool = False):
        """Run the full dataset generation pipeline."""
        print("=" * 60)
        print("Orientation Dataset Generation")
        print("Phase 10A - MobileCLIP Alignment")
        print("=" * 60)

        if dry_run:
            print("\n[DRY RUN MODE - No files will be written]\n")

        # Step 1: Collect source documents
        self.collect_source_documents()

        if len(self.source_documents) == 0:
            print("\nERROR: No source documents found. Check base_data_path.")
            return

        # Step 2: Split documents (BEFORE rotation)
        split_docs = self.split_documents()

        # Step 3: Generate samples (rotation + augmentation)
        samples = self.generate_samples(split_docs, dry_run=dry_run)

        # Step 4: Write label files
        self.write_labels(samples, dry_run=dry_run)

        # Step 5: Write metadata
        self.write_metadata(dry_run=dry_run)

        # Step 6: Print statistics
        self.print_statistics()

        print("\n" + "=" * 60)
        if dry_run:
            print("DRY RUN COMPLETE - No files written")
        else:
            print("GENERATION COMPLETE")
            print(f"Output: {self.output_path}")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate orientation detection training dataset for Phase 10A"
    )
    parser.add_argument(
        "--base-data",
        type=Path,
        default=Path("/mnt/e/image_detection/01_base_data"),
        help="Path to base data directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/mnt/e/image_detection/03_training_datasets/orientation"),
        help="Output directory for dataset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing files (validation only)",
    )

    args = parser.parse_args()

    generator = OrientationDatasetGenerator(
        base_data_path=args.base_data,
        output_path=args.output,
        seed=args.seed,
    )

    generator.generate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
