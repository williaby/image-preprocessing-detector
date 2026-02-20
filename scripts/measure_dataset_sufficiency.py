# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Dataset Sufficiency Measurement Script

Measures current datasets against FR requirements defined in TRAINING_DATASET_CONCEPT.md v2.0.

Usage:
    poetry run python scripts/measure_dataset_sufficiency.py --output reports/sufficiency_report.md
"""

import argparse
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants for file patterns and strings
LABELS_JSON = "labels.json"
DATASET_INFO_JSON = "dataset_info.json"
PNG_PATTERN = "*.png"
JPG_PATTERN = "*.jpg"
PNG_GLOB_PATTERN = "**/*.png"
JPG_GLOB_PATTERN = "**/*.jpg"
MD_SEPARATOR = "---\n\n"
MD_SEPARATOR_WITH_NEWLINE = "\n---\n\n"
FR_4_2_ID = "FR-4.2"


class SufficiencyStatus(Enum):
    """Status levels for sufficiency metrics."""

    SUFFICIENT = "✅ SUFFICIENT"
    PARTIAL = "⚠️ PARTIAL"
    CRITICAL_GAP = "❌ CRITICAL GAP"
    NOT_MEASURED = "🔍 NOT MEASURED"


@dataclass
class FRRequirement:
    """Functional requirement with sufficiency criteria."""

    fr_id: str
    name: str
    min_samples: int
    status: SufficiencyStatus = SufficiencyStatus.NOT_MEASURED
    current_count: int = 0
    real_world_count: int = 0  # NEW: Real-world samples
    synthetic_count: int = 0  # NEW: Synthetic/generated samples
    notes: str = ""
    cost_estimate: float | None = None


@dataclass
class DatasetInventory:
    """Inventory of available datasets with metadata."""

    doclaynet_path: Path
    tablebank_path: Path
    signatr6k_path: Path
    wili2018_path: Path
    phase2_iqa_path: Path
    iam_handwriting_path: Path
    omnidocbench_path: Path
    pubtabnet_path: Path
    fintabnet_path: Path
    # Additional training datasets
    invoices_kaggle_path: Path
    mobile_receipts_path: Path
    receipts_hitl_path: Path
    docsynth300k_path: Path
    docbank_path: Path
    # Business document datasets
    nist_sd2_path: Path
    docile_path: Path


@dataclass
class SufficiencyReport:
    """Complete sufficiency measurement report."""

    fr_requirements: dict[str, FRRequirement] = field(default_factory=dict)
    layout_class_coverage: dict[int, int] = field(default_factory=dict)
    dqs_routing_matrix: np.ndarray = field(
        default_factory=lambda: np.zeros((3, 3), dtype=int)
    )
    language_coverage: dict[str, int] = field(default_factory=dict)
    quality_dimension_coverage: dict[str, dict[str, int]] = field(default_factory=dict)
    co_occurrence_matrix: dict[tuple[str, str], int] = field(default_factory=dict)
    total_cost_estimate: float = 0.0
    overall_status: SufficiencyStatus = SufficiencyStatus.NOT_MEASURED


class DatasetSufficiencyMeasurer:
    """Measures dataset sufficiency against FR requirements."""

    # DocLayNet 11 class minimums (from TRAINING_DATASET_CONCEPT.md v2.0)
    DOCLAYNET_CLASS_MINIMUMS = {
        1: 5000,  # Text
        2: 2000,  # Title
        3: 3000,  # List-Item
        4: 3000,  # Table
        5: 2500,  # Picture
        6: 2000,  # Caption
        7: 1500,  # Formula
        8: 1500,  # Footnote
        9: 2000,  # Page-Header
        10: 2000,  # Page-Footer
        11: 2000,  # Section-Header
    }

    # DQS Routing Matrix minimums (3x3 grid)
    DQS_ROUTING_MINIMUMS = {
        (0, 0): 5000,  # LOW degradation, LOW structural
        (0, 1): 7500,  # LOW degradation, MEDIUM structural
        (0, 2): 7500,  # LOW degradation, HIGH structural
        (1, 0): 7500,  # MEDIUM degradation, LOW structural
        (1, 1): 10000,  # MEDIUM degradation, MEDIUM structural
        (1, 2): 7500,  # MEDIUM degradation, HIGH structural
        (2, 0): 5000,  # HIGH degradation, LOW structural
        (2, 1): 5000,  # HIGH degradation, MEDIUM structural
        (2, 2): 2500,  # HIGH degradation, HIGH structural
    }

    def __init__(self, inventory: DatasetInventory):
        """Initialize with dataset inventory."""
        self.inventory = inventory
        self.report = SufficiencyReport()

    def _determine_sufficiency_status(
        self, current: int, required: int, partial_threshold: float = 0.5
    ) -> SufficiencyStatus:
        """Determine sufficiency status based on current vs required samples."""
        if current >= required:
            return SufficiencyStatus.SUFFICIENT
        if current >= required * partial_threshold:
            return SufficiencyStatus.PARTIAL
        return SufficiencyStatus.CRITICAL_GAP

    def _check_quality_dimension(
        self, quality_scores: dict, dimension_keys: list[str]
    ) -> bool:
        """Check if any of the dimension keys exist in quality scores."""
        return any(key in quality_scores for key in dimension_keys)

    def _load_json_labels(self, path: Path) -> list:
        """Load JSON labels from a file, returning empty list if not found."""
        if not path.exists():
            return []
        try:
            with open(path) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Error loading labels from {path}: {e}")
            return []

    def _count_image_files(self, directory: Path) -> int:
        """Count PNG and JPG files in a directory."""
        if not directory.exists():
            return 0
        return len(list(directory.glob(PNG_PATTERN))) + len(
            list(directory.glob(JPG_PATTERN))
        )

    def _count_image_files_recursive(self, directory: Path) -> int:
        """Count PNG and JPG files recursively in a directory."""
        if not directory.exists():
            return 0
        return len(list(directory.glob(PNG_GLOB_PATTERN))) + len(
            list(directory.glob(JPG_GLOB_PATTERN))
        )

    def _analyze_quality_labels(
        self, labels_paths: list[Path]
    ) -> tuple[int, bool, bool, bool]:
        """Analyze quality labels from multiple paths.

        Returns:
            tuple: (total_samples, has_overall_quality, has_sharpness, has_color_fidelity)
        """
        total_samples = 0
        has_overall_quality = False
        has_sharpness = False
        has_color_fidelity = False

        for labels_path in labels_paths:
            labels = self._load_json_labels(labels_path)
            if labels:
                total_samples += len(labels)
                # Check first sample for quality score dimensions
                sample = labels[0]
                quality_scores = sample.get("quality_scores", {})

                if not has_overall_quality:
                    has_overall_quality = self._check_quality_dimension(
                        quality_scores, ["overall_quality", "brisque", "niqe"]
                    )
                if not has_sharpness:
                    has_sharpness = self._check_quality_dimension(
                        quality_scores, ["sharpness", "laplacian_variance"]
                    )
                if not has_color_fidelity:
                    has_color_fidelity = self._check_quality_dimension(
                        quality_scores, ["color_fidelity", "rms_contrast"]
                    )

        return total_samples, has_overall_quality, has_sharpness, has_color_fidelity

    def _add_quality_requirement(
        self, fr_id: str, name: str, total_samples: int, has_dimension: bool, notes: str
    ) -> None:
        """Add a quality dimension requirement with standard 50k threshold."""
        status = (
            self._determine_sufficiency_status(total_samples, 50000)
            if has_dimension
            else SufficiencyStatus.CRITICAL_GAP
        )
        self._add_fr_requirement(
            fr_id,
            name,
            50000,
            total_samples if has_dimension else 0,
            status,
            notes,
            cost_estimate=0.0 if has_dimension else 2500.0,
        )

    def _count_coco_annotations(self, coco_dir: Path) -> Counter:
        """Count COCO annotations per class from train/val/test splits."""
        class_counts = Counter()
        for split in ["train.json", "val.json", "test.json"]:
            coco_file = coco_dir / split
            if coco_file.exists():
                with open(coco_file) as f:
                    coco_data = json.load(f)
                    for ann in coco_data.get("annotations", []):
                        class_id = ann.get("category_id")
                        if class_id:
                            class_counts[class_id] += 1
        return class_counts

    def _count_docsynth_samples(self, docsynth_path: Path) -> int:
        """Count DocSynth-300K samples with multiple fallback strategies."""
        if not docsynth_path.exists():
            return 0

        # Strategy 1: Count Parquet files
        parquet_files = list(docsynth_path.glob("part*.parquet"))
        if parquet_files:
            try:
                import pyarrow.parquet as pq

                total = 0
                for parquet_file in parquet_files:
                    metadata = pq.read_metadata(str(parquet_file))
                    total += metadata.num_rows
                logger.info(
                    f"DocSynth-300K: Found {len(parquet_files)} Parquet files with {total:,} samples"
                )
                return total
            except Exception as e:
                logger.warning(f"Error reading DocSynth-300K Parquet files: {e}")

        # Strategy 2: Check HuggingFace dataset_info.json
        if (docsynth_path / DATASET_INFO_JSON).exists():
            with open(docsynth_path / DATASET_INFO_JSON) as f:
                info = json.load(f)
                return sum(
                    split_info.get("num_examples", 0)
                    for split_info in info.get("splits", {}).values()
                )

        # Strategy 3: Count JSON annotation files
        return len(list(docsynth_path.glob("**/*.json")))

    def _add_layout_class_requirements(self, class_counts: Counter) -> None:
        """Add FR requirements for each DocLayNet layout class."""
        for class_id, min_samples in self.DOCLAYNET_CLASS_MINIMUMS.items():
            current_count = class_counts.get(class_id, 0)
            status = self._determine_sufficiency_status(current_count, min_samples)

            self._add_fr_requirement(
                f"FR-4.2.{class_id}",
                f"Class {class_id} Detection",
                min_samples,
                current_count,
                status,
                f"DocLayNet class {class_id} samples",
                cost_estimate=0.0,
            )

    def _count_parasitic_content(self, parasitic_path: Path) -> tuple[int, int]:
        """Count parasitic content annotations from weak supervision and VidOre.

        Returns:
            tuple: (parasitic_count, vidore_parasitic_count)
        """
        parasitic_count = 0
        vidore_parasitic_count = 0

        if not parasitic_path.exists():
            return 0, 0

        for split_file in parasitic_path.glob("*_parasitic_content.json"):
            try:
                with open(split_file) as f:
                    data = json.load(f)
                    count = len(
                        data.get("parasitic_annotations", data.get("annotations", []))
                    )

                    if "vidore" in split_file.name:
                        vidore_parasitic_count += count
                        logger.info(
                            f"Found {count} VidOre parasitic content annotations"
                        )
                    else:
                        parasitic_count += count
                        logger.info(
                            f"Found {count} weak supervision parasitic content annotations"
                        )
            except Exception as e:
                logger.warning(
                    f"Error reading parasitic content labels from {split_file}: {e}"
                )

        return parasitic_count, vidore_parasitic_count

    def _count_vertical_text_samples(self, vertical_text_path: Path) -> int:
        """Count vertical text samples from generated labels."""
        if not vertical_text_path.exists():
            return 0

        total = 0
        for split_file in vertical_text_path.glob("*_vertical_text.json"):
            try:
                with open(split_file) as f:
                    data = json.load(f)
                    total += len(data.get("images", []))
            except Exception as e:
                logger.warning(
                    f"Error reading vertical text labels from {split_file}: {e}"
                )
        return total

    def _build_parasitic_notes(
        self, parasitic_count: int, vidore_count: int, total: int
    ) -> str:
        """Build notes string for parasitic content detection."""
        notes_parts = []
        if parasitic_count > 0:
            notes_parts.append(
                f"Weak supervision (OCR-based): {parasitic_count:,} annotations"
            )
        if vidore_count > 0:
            notes_parts.append(
                f"VidOre V3 Finance: {vidore_count:,} annotations (spatial heuristics)"
            )
        if total == 0:
            notes_parts.append(
                "Need 10k pages with bbox + repeating pattern flag annotations"
            )
        return ". ".join(notes_parts)

    def _count_business_documents(self) -> tuple[int, dict[str, int]]:
        """Count business documents from multiple training datasets.

        Returns:
            tuple: (total_business_docs, individual_counts_dict)
        """
        counts = {
            "invoice": 0,
            "receipt": 0,
            "hitl": 0,
            "nist": 0,
            "docile": 0,
        }

        # Count invoice samples from Kaggle dataset
        invoices_path = self.inventory.invoices_kaggle_path
        if invoices_path.exists():
            for split in ["train", "val"]:
                images_dir = invoices_path / split / "images"
                counts["invoice"] += self._count_image_files(images_dir)
            logger.info(f"Found {counts['invoice']} invoice samples")

        # Mobile Receipts (Voxel51)
        mobile_receipts_path = self.inventory.mobile_receipts_path / "train"
        if (mobile_receipts_path / DATASET_INFO_JSON).exists():
            with open(mobile_receipts_path / DATASET_INFO_JSON) as f:
                info = json.load(f)
                counts["receipt"] = (
                    info.get("splits", {}).get("train", {}).get("num_examples", 0)
                )
                logger.info(f"Found {counts['receipt']} mobile receipt samples")

        # HITL Receipts
        hitl_path = self.inventory.receipts_hitl_path / "ds0"
        counts["hitl"] = self._count_image_files_recursive(hitl_path)
        if counts["hitl"] > 0:
            logger.info(f"Found {counts['hitl']} HITL receipt samples")

        # NIST DB2 and DocILE
        counts["nist"] = self._measure_nist_sd2()
        counts["docile"] = self._measure_docile()

        total = sum(counts.values())
        return total, counts

    def _count_doc_classification_labels(
        self, doc_classification_path: Path
    ) -> tuple[int, int]:
        """Count document classification labels from weak supervision and VidOre.

        Returns:
            tuple: (weak_supervision_count, vidore_count)
        """
        weak_supervision_count = 0
        vidore_count = 0

        if not doc_classification_path.exists():
            return 0, 0

        for split in ["train", "val", "test"]:
            # DocLayNet weak supervision
            json_file = (
                doc_classification_path / f"{split}_document_classification.json"
            )
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    split_count = len(data.get("classifications", []))
                    weak_supervision_count += split_count
                    logger.info(
                        f"Found {split_count} weak supervision document classification labels ({split})"
                    )

            # VidOre V3 Finance
            vidore_file = (
                doc_classification_path / f"{split}_vidore_document_classification.json"
            )
            if vidore_file.exists():
                with open(vidore_file) as f:
                    data = json.load(f)
                    vidore_split_count = len(data.get("classifications", []))
                    vidore_count += vidore_split_count
                    logger.info(
                        f"Found {vidore_split_count} VidOre document classification labels ({split})"
                    )

        return weak_supervision_count, vidore_count

    def _build_doc_classification_notes(
        self,
        counts: dict[str, int],
        total_business: int,
        weak_supervision: int,
        vidore: int,
        min_required: int,
        total_docs: int,
    ) -> str:
        """Build notes for document classification requirement."""
        notes_parts = []

        # Real-world business documents breakdown
        real_world_parts = []
        if counts["invoice"] > 0:
            real_world_parts.append(f"{counts['invoice']} invoices")
        if counts["receipt"] > 0:
            real_world_parts.append(f"{counts['receipt']} mobile receipts")
        if counts["hitl"] > 0:
            real_world_parts.append(f"{counts['hitl']} HITL receipts")
        if counts["nist"] > 0:
            real_world_parts.append(f"{counts['nist']} tax forms (NIST DB2, 20 types)")
        if counts["docile"] > 0:
            real_world_parts.append(f"{counts['docile']} business documents (DocILE)")

        if real_world_parts:
            notes_parts.append(
                f"Real-world: {' + '.join(real_world_parts)} = {total_business} total"
            )

        if weak_supervision > 0:
            notes_parts.append(
                f"Weak supervision: {weak_supervision} DocLayNet samples "
                f"(image_only, born_digital, hybrid)"
            )
        if vidore > 0:
            notes_parts.append(
                f"VidOre V3 Finance: {vidore} financial report samples (banking documents)"
            )
        if total_docs < min_required:
            notes_parts.append(
                "Need additional document types: Academic, Historical, Legal, Technical, Multi-lingual"
            )

        return ". ".join(notes_parts)

    def _count_parquet_samples(self, data_dir: Path) -> int:
        """Count samples from Parquet files in data directory."""
        if not data_dir.exists():
            return 0
        try:
            import pyarrow.parquet as pq

            total = 0
            for split in ["train", "validation", "test"]:
                parquet_file = data_dir / f"{split}.parquet"
                if parquet_file.exists():
                    total += pq.read_table(str(parquet_file)).num_rows
            return total
        except Exception as e:
            logger.warning(f"Error reading Parquet files: {e}")
            return 0

    def _count_hf_dataset_info(self, path: Path) -> int:
        """Count samples from HuggingFace dataset_info.json."""
        info_path = path / DATASET_INFO_JSON
        if not info_path.exists():
            return 0
        try:
            with open(info_path) as f:
                info = json.load(f)
            return sum(
                s.get("num_examples", 0) for s in info.get("splits", {}).values()
            )
        except ValueError as exc:
            logger.warning("Error reading dataset info from %s: %s", info_path, exc)
            return 0

    def _count_iam_handwriting_samples(self, iam_path: Path) -> int:
        """Count IAM handwriting samples with multiple fallback strategies."""
        if not iam_path.exists():
            return 0

        # Strategy 1: Count Parquet files
        total = self._count_parquet_samples(iam_path / "data")
        if total > 0:
            return total

        # Strategy 2: Count split directories
        for split in ["train", "validation", "test"]:
            total += self._count_image_files(iam_path / split)
        if total > 0:
            return total

        # Strategy 3: Count root directory
        total = self._count_image_files_recursive(iam_path)
        if total > 0:
            return total

        # Strategy 4: Check HuggingFace dataset_info.json
        return self._count_hf_dataset_info(iam_path)

    def _load_dqs_routing_labels(
        self, dqs_routing_path: Path
    ) -> tuple[int, int, np.ndarray]:
        """Load DQS routing labels and build routing matrix.

        Returns:
            tuple: (total_dqs_samples, vidore_dqs_samples, routing_matrix)
        """
        total_dqs_samples = 0
        vidore_dqs_samples = 0
        routing_matrix = np.zeros((3, 3), dtype=int)

        if not dqs_routing_path.exists():
            return 0, 0, routing_matrix

        for split in ["train", "val", "test"]:
            # DocLayNet weak supervision
            json_file = dqs_routing_path / f"{split}_dqs_routing.json"
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    labels = data.get("labels", [])
                    total_dqs_samples += len(labels)
                    logger.info(f"Found {len(labels)} DQS routing labels ({split})")

                    # Populate routing matrix from distribution
                    distribution = data.get("routing_matrix", {}).get(
                        "distribution", {}
                    )
                    self._populate_routing_matrix(routing_matrix, distribution)

            # VidOre V3 Finance
            vidore_file = dqs_routing_path / f"{split}_vidore_dqs_routing.json"
            if vidore_file.exists():
                with open(vidore_file) as f:
                    data = json.load(f)
                    labels = data.get("labels", [])
                    vidore_dqs_samples += len(labels)
                    logger.info(
                        f"Found {len(labels)} VidOre DQS routing labels ({split})"
                    )

                    # Populate routing matrix from VidOre distribution
                    distribution = data.get("routing_matrix", {}).get(
                        "distribution", {}
                    )
                    self._populate_routing_matrix(routing_matrix, distribution)

        return total_dqs_samples, vidore_dqs_samples, routing_matrix

    def _populate_routing_matrix(
        self, routing_matrix: np.ndarray, distribution: dict
    ) -> None:
        """Populate routing matrix from distribution dictionary."""
        for bin_key, count in distribution.items():
            try:
                bin_idx = int(bin_key)
            except (TypeError, ValueError):
                logger.warning("Skipping invalid DQS routing bin key: %r", bin_key)
                continue
            if not 1 <= bin_idx <= 9:
                logger.warning("Skipping out-of-range DQS routing bin: %s", bin_idx)
                continue
            row = (bin_idx - 1) // 3  # Degradation axis (0-2)
            col = (bin_idx - 1) % 3  # Complexity axis (0-2)
            routing_matrix[row, col] += int(count)

    def _build_dqs_routing_notes(
        self, total_dqs: int, vidore_dqs: int, total: int, routing_matrix: np.ndarray
    ) -> str:
        """Build notes for DQS routing requirement."""
        notes_parts = []

        if total_dqs > 0:
            notes_parts.append(
                f"Weak supervision: {total_dqs} DocLayNet samples with DQS routing labels "
                f"(Degradation × Structural Complexity)"
            )
        if vidore_dqs > 0:
            notes_parts.append(
                f"VidOre V3 Finance: {vidore_dqs} financial document samples (classical CV analysis)"
            )
        if total > 0:
            filled_bins = np.count_nonzero(routing_matrix)
            notes_parts.append(
                f"Routing matrix coverage: {filled_bins}/9 bins populated"
            )
        else:
            notes_parts.append(
                "Need samples with 2-axis DQS labels (Degradation + Structural Complexity). "
                "Can generate via weak supervision: "
                "Degradation = f(blur, noise, contrast, skew, DPI), "
                "Structural = f(multi-column, tables, formulas, figures, mixed scripts)"
            )

        return ". ".join(notes_parts)

    def _extract_docile_doc_ids(self, images: list) -> set:
        """Extract unique document IDs from DocILE images."""
        doc_ids = set()
        for img in images:
            # DocILE image IDs are formatted as: {doc_id}_{page_num}
            img_id = img.get("id", "")
            if "_" in str(img_id):
                doc_id = str(img_id).rsplit("_", 1)[0]
                doc_ids.add(doc_id)
        return doc_ids

    def measure_all(self) -> SufficiencyReport:
        """Run all sufficiency measurements."""
        logger.info("Starting dataset sufficiency measurement...")

        # FR-2.3: Learned Quality Assessment (3-dimension)
        self._measure_fr_2_3_learned_quality()

        # FR-4.2: Layout Elements (11 DocLayNet classes)
        self._measure_fr_4_2_layout_elements()

        # FR-4.4-4.7, 4.12: Structural Relationships
        self._measure_fr_4_structural_relationships()

        # FR-5.2: Signature Detection
        self._measure_fr_5_2_signature_detection()

        # FR-2.1: Document Classification
        self._measure_fr_2_1_document_classification()

        # FR-5.1: Handwriting Detection
        self._measure_fr_5_1_handwriting_detection()

        # FR-5.3: Multilingual Text
        self._measure_fr_5_3_multilingual()

        # FR-7.1: DQS Routing Matrix
        self._measure_fr_7_1_dqs_routing()

        # Additional layout training data
        self._measure_additional_layout_training()

        # Calculate overall status
        self._calculate_overall_status()

        logger.info("Sufficiency measurement complete.")
        return self.report

    def _add_dimension_requirement(
        self,
        fr_id: str,
        name: str,
        total_samples: int,
        has_data: bool,
        missing_note: str,
    ) -> None:
        """Add a quality dimension requirement."""
        notes = (
            f"{total_samples} samples with weak supervision"
            if has_data
            else missing_note
        )
        status = (
            self._determine_sufficiency_status(total_samples, 50000)
            if has_data
            else SufficiencyStatus.CRITICAL_GAP
        )
        self._add_fr_requirement(
            fr_id,
            name,
            50000,
            total_samples if has_data else 0,
            status,
            notes,
            cost_estimate=0.0 if has_data else 2500.0,
        )

    def _measure_fr_2_3_learned_quality(self) -> None:
        """Measure FR-2.3: 3-dimension learned quality assessment."""
        logger.info("Measuring FR-2.3: Learned Quality Assessment...")

        phase2_iqa_path = self.inventory.phase2_iqa_path
        if not phase2_iqa_path.exists():
            logger.warning(f"Phase 2 IQA dataset not found at {phase2_iqa_path}")
            self._add_fr_requirement(
                "FR-2.3.1",
                "Overall Quality Labels",
                50000,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                "Phase 2 IQA dataset missing - need 50k samples with weak supervision (BRISQUE/NIQE)",
                cost_estimate=0.0,
            )
            return

        labels_paths = [
            phase2_iqa_path / "train" / LABELS_JSON,
            phase2_iqa_path / "val" / LABELS_JSON,
            phase2_iqa_path / "test" / LABELS_JSON,
        ]
        total_samples, has_overall_quality, has_sharpness, has_color_fidelity = (
            self._analyze_quality_labels(labels_paths)
        )

        # FR-2.3.1: Overall Quality
        self._add_quality_requirement(
            "FR-2.3.1",
            "Overall Quality Labels",
            total_samples,
            has_overall_quality,
            f"Phase 2: {total_samples} samples with weak supervision (BRISQUE/NIQE). "
            "Phase 3: Need DIQA-5000 (5k ground-truth) - PENDING RELEASE Sept 2025",
        )

        # FR-2.3.2 and FR-2.3.3: Other dimensions
        self._add_dimension_requirement(
            "FR-2.3.2",
            "Sharpness Labels",
            total_samples,
            has_sharpness,
            "Need Laplacian variance weak supervision + DIQA-5000 sharpness ground-truth",
        )
        self._add_dimension_requirement(
            "FR-2.3.3",
            "Color Fidelity Labels",
            total_samples,
            has_color_fidelity,
            "Need histogram analysis weak supervision + DIQA-5000 color ground-truth",
        )

        # Store dimension coverage
        self.report.quality_dimension_coverage = {
            "overall_quality": {
                "current": total_samples if has_overall_quality else 0,
                "required": 50000,
            },
            "sharpness": {
                "current": total_samples if has_sharpness else 0,
                "required": 50000,
            },
            "color_fidelity": {
                "current": total_samples if has_color_fidelity else 0,
                "required": 50000,
            },
        }

    def _measure_fr_4_2_layout_elements(self) -> None:
        """Measure FR-4.2: 11 DocLayNet layout classes."""
        logger.info("Measuring FR-4.2: Layout Elements (11 classes)...")

        doclaynet_path = self.inventory.doclaynet_path
        total_required = sum(self.DOCLAYNET_CLASS_MINIMUMS.values())

        # Validate dataset exists
        if not doclaynet_path.exists():
            logger.warning(f"DocLayNet dataset not found at {doclaynet_path}")
            self._add_fr_requirement(
                FR_4_2_ID,
                "Layout Element Detection (11 classes)",
                total_required,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                "DocLayNet dataset missing - need 80k pages with COCO annotations",
                cost_estimate=0.0,
            )
            return

        # Validate COCO annotations directory
        coco_dir = doclaynet_path / "ground_truth" / "coco"
        if not coco_dir.exists():
            logger.warning(f"DocLayNet COCO annotations not found at {coco_dir}")
            self._add_fr_requirement(
                FR_4_2_ID,
                "Layout Element Detection (11 classes)",
                total_required,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                f"DocLayNet COCO annotations missing at {coco_dir}",
                cost_estimate=0.0,
            )
            return

        # Count annotations per class
        class_counts = self._count_coco_annotations(coco_dir)
        self.report.layout_class_coverage = dict(class_counts)

        # Evaluate each class and add individual requirements
        self._add_layout_class_requirements(class_counts)

        # Add overall FR-4.2 requirement with synthetic data
        total_current = sum(class_counts.values())
        docsynth_samples = self._count_docsynth_samples(
            self.inventory.docsynth300k_path
        )

        total_with_synthetic = total_current + docsynth_samples
        combined_status = self._determine_sufficiency_status(
            total_with_synthetic, total_required
        )

        notes = f"Real-world: DocLayNet {total_current:,} annotations"
        if docsynth_samples > 0:
            notes += f" | Synthetic: DocSynth-300K {docsynth_samples:,} samples"

        self._add_fr_requirement(
            FR_4_2_ID,
            "Layout Element Detection (Overall)",
            total_required,
            total_with_synthetic,
            combined_status,
            notes,
            cost_estimate=0.0,
            real_world_count=total_current,
            synthetic_count=docsynth_samples,
        )

    def _measure_fr_4_structural_relationships(self) -> None:
        """Measure FR-4.4-4.7, 4.12: Structural relationships."""
        logger.info("Measuring FR-4.4-4.7, 4.12: Structural Relationships...")

        # FR-4.4: Parasitic Content
        parasitic_path = (
            self.inventory.doclaynet_path.parent.parent
            / "training"
            / "parasitic_content"
        )
        parasitic_count, vidore_parasitic_count = self._count_parasitic_content(
            parasitic_path
        )
        total_parasitic = parasitic_count + vidore_parasitic_count

        parasitic_notes = self._build_parasitic_notes(
            parasitic_count, vidore_parasitic_count, total_parasitic
        )
        parasitic_status = self._determine_sufficiency_status(total_parasitic, 10000)

        self._add_fr_requirement(
            "FR-4.4",
            "Parasitic Content Detection",
            10000,
            total_parasitic,
            parasitic_status,
            parasitic_notes,
            cost_estimate=0.0 if total_parasitic >= 10000 else 500.0,
            real_world_count=0,
            synthetic_count=total_parasitic,
        )

        # FR-4.7: Vertical Text Detection
        vertical_text_path = (
            self.inventory.doclaynet_path.parent.parent / "training" / "vertical_text"
        )
        vertical_text_count = self._count_vertical_text_samples(vertical_text_path)

        vertical_text_notes = (
            f"Synthetic (rotation augmentation): {vertical_text_count:,} samples with orientation annotations (0°, 90°, 180°, 270°)"
            if vertical_text_count > 0
            else "Need 5k samples with bbox + orientation (0/90/180/270°) annotations"
        )
        vertical_text_status = self._determine_sufficiency_status(
            vertical_text_count, 5000
        )

        self._add_fr_requirement(
            "FR-4.7",
            "Vertical Text Detection",
            5000,
            vertical_text_count,
            vertical_text_status,
            vertical_text_notes,
            cost_estimate=0.0 if vertical_text_count >= 5000 else 500.0,
            real_world_count=0,
            synthetic_count=vertical_text_count,
        )

    def _measure_fr_5_2_signature_detection(self) -> None:
        """Measure FR-5.2: Signature detection."""
        logger.info("Measuring FR-5.2: Signature Detection...")

        signatr6k_path = self.inventory.signatr6k_path
        if not signatr6k_path.exists():
            logger.warning(f"SignaTR6K dataset not found at {signatr6k_path}")
            self._add_fr_requirement(
                "FR-5.2",
                "Signature Detection",
                6000,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                "SignaTR6K dataset missing - need 6k signature samples",
                cost_estimate=0.0,  # Free dataset
            )
            return

        # Count signature samples
        # SignaTR6K structure: train/crop/, validation/crop/, test/crop/
        total_signatures = 0
        for split in ["train", "validation", "test"]:
            split_dir = signatr6k_path / split / "crop"
            if split_dir.exists():
                # Count image files
                total_signatures += len(list(split_dir.glob(PNG_PATTERN))) + len(
                    list(split_dir.glob(JPG_PATTERN))
                )

        if total_signatures >= 6000:
            status = SufficiencyStatus.SUFFICIENT
        elif total_signatures >= 3000:
            status = SufficiencyStatus.PARTIAL
        else:
            status = SufficiencyStatus.CRITICAL_GAP

        self._add_fr_requirement(
            "FR-5.2",
            "Signature Detection",
            6000,
            total_signatures,
            status,
            f"SignaTR6K: {total_signatures} signature samples",
            cost_estimate=0.0,
        )

    def _measure_fr_5_3_multilingual(self) -> None:
        """Measure FR-5.3: Multilingual text detection."""
        logger.info("Measuring FR-5.3: Multilingual Text Detection...")

        wili2018_path = self.inventory.wili2018_path
        if not wili2018_path.exists():
            logger.warning(f"WiLI-2018 dataset not found at {wili2018_path}")
            self._add_fr_requirement(
                "FR-5.3",
                "Multilingual Text Detection",
                235,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                "WiLI-2018 dataset missing - need 235 languages",
                cost_estimate=0.0,  # Free dataset
            )
            return

        # Count language files
        # WiLI-2018 structure: x_train.txt, y_train.txt, x_test.txt, y_test.txt
        # Each line in y_train/y_test is a language code
        languages = set()
        paragraph_counts = Counter()

        for label_file in ["y_train.txt", "y_test.txt"]:
            label_path = wili2018_path / label_file
            if label_path.exists():
                with open(label_path) as f:
                    for line in f:
                        lang = line.strip()
                        if lang:
                            languages.add(lang)
                            paragraph_counts[lang] += 1

        num_languages = len(languages)
        total_paragraphs = sum(paragraph_counts.values())

        if num_languages >= 235:
            status = SufficiencyStatus.SUFFICIENT
        elif num_languages >= 200:
            status = SufficiencyStatus.PARTIAL
        else:
            status = SufficiencyStatus.CRITICAL_GAP

        self._add_fr_requirement(
            "FR-5.3",
            "Multilingual Text Detection",
            235,
            num_languages,
            status,
            f"WiLI-2018: {num_languages} languages, {total_paragraphs} paragraphs",
            cost_estimate=0.0,
        )

        # Store language coverage
        self.report.language_coverage = dict(paragraph_counts)

    def _measure_nist_sd2(self) -> int:
        """Count NIST DB2 tax form images."""
        nist_path = self.inventory.nist_sd2_path
        if not nist_path.exists():
            logger.warning(f"NIST DB2 not found at {nist_path}")
            return 0

        # Count PNG files in data directory
        data_dir = nist_path / "data"
        if not data_dir.exists():
            return 0

        png_files = list(data_dir.glob(PNG_GLOB_PATTERN))
        total_forms = len(png_files)

        logger.info(f"NIST DB2: Found {total_forms} tax form images (20 form types)")
        return total_forms

    def _measure_docile(self) -> int:
        """Count DocILE annotated documents."""
        docile_path = self.inventory.docile_path
        if not docile_path.exists():
            logger.warning(f"DocILE dataset not found at {docile_path}")
            return 0

        # Check for COCO annotation files
        total_docs = 0
        for split in ["train", "val"]:
            json_file = docile_path / f"{split}.json"
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)
                    images = data.get("images", [])
                    doc_ids = self._extract_docile_doc_ids(images)
                    split_count = len(doc_ids)
                    total_docs += split_count
                    logger.info(
                        f"DocILE: Found {split_count} documents in {split} split"
                    )

        # Fallback: check for PDF files directly
        if total_docs == 0:
            for split_dir in [docile_path / "train", docile_path / "val"]:
                if split_dir.exists():
                    total_docs += len(list(split_dir.glob("*.pdf")))

        logger.info(f"DocILE: Total {total_docs} annotated business documents")
        return total_docs

    def _measure_fr_2_1_document_classification(self) -> None:
        """Measure FR-2.1: Document classification training data."""
        logger.info("Measuring FR-2.1: Document Classification...")

        # Count business documents from training datasets
        total_business_docs, counts = self._count_business_documents()

        # Count weak supervision labels
        doc_classification_path = Path("data/training/document_classification")
        weak_supervision_count, vidore_count = self._count_doc_classification_labels(
            doc_classification_path
        )

        # Calculate totals and status
        total_docs = total_business_docs + weak_supervision_count + vidore_count
        min_required = 10000
        status = self._determine_sufficiency_status(
            total_docs, min_required, partial_threshold=0.3
        )

        # Build notes
        notes = self._build_doc_classification_notes(
            counts,
            total_business_docs,
            weak_supervision_count,
            vidore_count,
            min_required,
            total_docs,
        )

        # Calculate cost estimate
        cost_estimate = (
            0.0 if total_docs >= min_required else (min_required - total_docs) * 0.10
        )

        self._add_fr_requirement(
            "FR-2.1",
            "Document Classification Training",
            min_required,
            total_docs,
            status,
            notes,
            cost_estimate=cost_estimate,
            real_world_count=total_business_docs,
            synthetic_count=weak_supervision_count + vidore_count,
        )

    def _measure_fr_5_1_handwriting_detection(self) -> None:
        """Measure FR-5.1: Handwriting detection training data."""
        logger.info("Measuring FR-5.1: Handwriting Detection...")

        iam_path = self.inventory.iam_handwriting_path
        if not iam_path.exists():
            logger.warning(f"IAM Handwriting dataset not found at {iam_path}")
            self._add_fr_requirement(
                "FR-5.1",
                "Handwriting Detection",
                10000,
                0,
                SufficiencyStatus.CRITICAL_GAP,
                "IAM Handwriting dataset missing - need 10k+ handwritten text line samples",
                cost_estimate=0.0,
            )
            return

        # Count handwriting samples using fallback strategies
        total_handwriting = self._count_iam_handwriting_samples(iam_path)

        min_required = 10000
        status = self._determine_sufficiency_status(total_handwriting, min_required)

        self._add_fr_requirement(
            "FR-5.1",
            "Handwriting Detection",
            min_required,
            total_handwriting,
            status,
            f"IAM Handwriting: {total_handwriting} text line samples",
            cost_estimate=0.0,
        )

    def _measure_additional_layout_training(self) -> None:
        """Measure additional layout training data beyond DocLayNet."""
        logger.info("Measuring Additional Layout Training Data...")

        # Count DocSynth-300K samples
        docsynth_samples = self._count_docsynth_samples(
            self.inventory.docsynth300k_path
        )

        if docsynth_samples > 0:
            status = self._determine_sufficiency_status(docsynth_samples, 300000)
            self._add_fr_requirement(
                "FR-4.2-EXTRA",
                "Additional Layout Training (DocSynth-300K)",
                300000,
                docsynth_samples,
                status,
                f"DocSynth-300K: {docsynth_samples:,} synthetic layout samples with 71-class taxonomy (pre-training for DocLayNet fine-tuning)",
                cost_estimate=0.0,
                real_world_count=0,
                synthetic_count=docsynth_samples,
            )

    def _measure_fr_7_1_dqs_routing(self) -> None:
        """Measure FR-7.1: DQS routing matrix coverage."""
        logger.info("Measuring FR-7.1: DQS Routing Matrix...")

        # Load DQS routing labels and build matrix
        dqs_routing_path = Path("data/training/dqs_routing")
        total_dqs_samples, vidore_dqs_samples, routing_matrix = (
            self._load_dqs_routing_labels(dqs_routing_path)
        )

        total_samples = total_dqs_samples + vidore_dqs_samples
        min_required = sum(self.DQS_ROUTING_MINIMUMS.values())

        status = self._determine_sufficiency_status(
            total_samples, min_required, partial_threshold=0.1
        )

        notes = self._build_dqs_routing_notes(
            total_dqs_samples, vidore_dqs_samples, total_samples, routing_matrix
        )

        self._add_fr_requirement(
            "FR-7.1",
            "DQS Routing Matrix (3x3 grid)",
            min_required,
            total_samples,
            status,
            notes,
            cost_estimate=0.0,
            real_world_count=0,
            synthetic_count=total_samples,
        )

        # Store routing matrix in report
        self.report.dqs_routing_matrix = routing_matrix

    def _add_fr_requirement(
        self,
        fr_id: str,
        name: str,
        min_samples: int,
        current_count: int,
        status: SufficiencyStatus,
        notes: str,
        cost_estimate: float = 0.0,
        real_world_count: int = 0,
        synthetic_count: int = 0,
    ) -> None:
        """Add FR requirement to report."""
        # If real_world_count and synthetic_count not provided, assume all are real-world
        if real_world_count == 0 and synthetic_count == 0 and current_count > 0:
            real_world_count = current_count

        req = FRRequirement(
            fr_id=fr_id,
            name=name,
            min_samples=min_samples,
            current_count=current_count,
            real_world_count=real_world_count,
            synthetic_count=synthetic_count,
            status=status,
            notes=notes,
            cost_estimate=cost_estimate,
        )
        self.report.fr_requirements[fr_id] = req

        # Update total cost estimate
        if status == SufficiencyStatus.CRITICAL_GAP and cost_estimate > 0:
            self.report.total_cost_estimate += cost_estimate

    def _calculate_overall_status(self) -> None:
        """Calculate overall sufficiency status."""
        critical_gaps = sum(
            1
            for req in self.report.fr_requirements.values()
            if req.status == SufficiencyStatus.CRITICAL_GAP
        )
        partial = sum(
            1
            for req in self.report.fr_requirements.values()
            if req.status == SufficiencyStatus.PARTIAL
        )
        sufficient = sum(
            1
            for req in self.report.fr_requirements.values()
            if req.status == SufficiencyStatus.SUFFICIENT
        )

        if critical_gaps > 5:
            self.report.overall_status = SufficiencyStatus.CRITICAL_GAP
        elif partial > 3:
            self.report.overall_status = SufficiencyStatus.PARTIAL
        else:
            self.report.overall_status = SufficiencyStatus.SUFFICIENT

        logger.info(
            f"Overall Status: {self.report.overall_status.value} "
            f"(Sufficient: {sufficient}, Partial: {partial}, Critical: {critical_gaps})"
        )


def _write_report_header(f, report: SufficiencyReport) -> None:
    """Write report header and overall status."""
    f.write("# Dataset Sufficiency Report\n\n")
    f.write(
        f"**Generated**: {Path(__file__).name} (Auto-generated from dataset analysis)\n\n"
    )
    f.write(
        f"**Overall Status**: {report.overall_status.value}  \n"
        f"**Total Investment Needed**: ${report.total_cost_estimate:,.2f}\n\n"
    )


def _write_executive_summary(f, report: SufficiencyReport) -> None:
    """Write executive summary with status counts and data composition."""
    f.write(MD_SEPARATOR)
    f.write("## Executive Summary\n\n")

    # Count status levels
    critical = [
        req
        for req in report.fr_requirements.values()
        if req.status == SufficiencyStatus.CRITICAL_GAP
    ]
    partial = [
        req
        for req in report.fr_requirements.values()
        if req.status == SufficiencyStatus.PARTIAL
    ]
    sufficient = [
        req
        for req in report.fr_requirements.values()
        if req.status == SufficiencyStatus.SUFFICIENT
    ]

    f.write(
        f"- **{len(sufficient)}** FRs have SUFFICIENT data  \n"
        f"- **{len(partial)}** FRs have PARTIAL data (50-99% coverage)  \n"
        f"- **{len(critical)}** FRs have CRITICAL GAPS (0-49% coverage)  \n\n"
    )

    # Calculate and write data composition
    _write_data_composition(f, report)


def _count_synthetic_categories(report: SufficiencyReport) -> tuple[int, int, int]:
    """Count FRs by synthetic data category."""
    synthetic_only = sum(
        1
        for req in report.fr_requirements.values()
        if req.synthetic_count > 0 and req.real_world_count == 0
    )
    high_synthetic = sum(
        1
        for req in report.fr_requirements.values()
        if req.current_count > 0
        and (req.synthetic_count / req.current_count) > 0.5
        and req.real_world_count > 0
    )
    real_dominant = sum(
        1
        for req in report.fr_requirements.values()
        if req.current_count > 0 and (req.real_world_count / req.current_count) >= 0.8
    )
    return synthetic_only, high_synthetic, real_dominant


def _write_data_composition(f, report: SufficiencyReport) -> None:
    """Write data composition analysis (real-world vs synthetic)."""
    total_real = sum(req.real_world_count for req in report.fr_requirements.values())
    total_synthetic = sum(
        req.synthetic_count for req in report.fr_requirements.values()
    )
    total_samples = total_real + total_synthetic

    real_pct = (total_real / total_samples * 100) if total_samples > 0 else 0
    synthetic_pct = (total_synthetic / total_samples * 100) if total_samples > 0 else 0

    synthetic_only, high_synthetic, real_dominant = _count_synthetic_categories(report)

    f.write("### Data Composition\n\n")
    f.write(f"- **Total Samples**: {total_samples:,}\n")
    f.write(f"  - **Real-World**: {total_real:,} ({real_pct:.1f}%)\n")
    f.write(f"  - **Synthetic**: {total_synthetic:,} ({synthetic_pct:.1f}%)\n\n")

    f.write("### Synthetic Data Analysis\n\n")
    f.write(
        f"- 🔴 **Synthetic Only**: {synthetic_only} FRs (100% synthetic, 0% real-world)\n"
    )
    f.write(f"- ⚠️ **High Synthetic Ratio**: {high_synthetic} FRs (>50% synthetic)\n")
    f.write(f"- ✅ **Real-World Dominant**: {real_dominant} FRs (≥80% real-world)\n\n")


def _categorize_by_real_world_coverage(requirements) -> tuple[list, list, list]:
    """Categorize requirements by real-world data coverage percentage."""
    sufficient, partial, critical = [], [], []
    for req in requirements:
        coverage = (
            (req.real_world_count / req.min_samples * 100) if req.min_samples > 0 else 0
        )
        if coverage >= 100:
            sufficient.append(req)
        elif coverage >= 50:
            partial.append(req)
        else:
            critical.append(req)
    return sufficient, partial, critical


def _categorize_by_combined_status(requirements) -> tuple[list, list, list]:
    """Categorize requirements by combined sufficiency status."""
    return (
        [req for req in requirements if req.status == SufficiencyStatus.SUFFICIENT],
        [req for req in requirements if req.status == SufficiencyStatus.PARTIAL],
        [req for req in requirements if req.status == SufficiencyStatus.CRITICAL_GAP],
    )


def _categorize_requirements_by_status(
    report: SufficiencyReport,
) -> tuple[list, list, list, list, list, list]:
    """Categorize requirements by real-world and combined status.

    Returns:
        tuple: (real_world_sufficient, real_world_partial, real_world_critical,
                combined_sufficient, combined_partial, combined_critical)
    """
    reqs = list(report.fr_requirements.values())
    rw_sufficient, rw_partial, rw_critical = _categorize_by_real_world_coverage(reqs)
    cb_sufficient, cb_partial, cb_critical = _categorize_by_combined_status(reqs)

    return (
        rw_sufficient,
        rw_partial,
        rw_critical,
        cb_sufficient,
        cb_partial,
        cb_critical,
    )


def _write_two_part_analysis(f, report: SufficiencyReport) -> None:
    """Write two-part sufficiency analysis section."""
    f.write(MD_SEPARATOR)
    f.write("## Two-Part Sufficiency Analysis\n\n")
    f.write(
        "> **Goal**: Real-world human-annotated data is our primary target. "
        "Synthetic/weak-supervision data helps meet minimum requirements but "
        "should be supplemented with real-world data when possible.\n\n"
    )

    # Categorize requirements
    (
        real_world_sufficient,
        real_world_partial,
        real_world_critical,
        combined_sufficient,
        combined_partial,
        combined_critical,
    ) = _categorize_requirements_by_status(report)

    # Part 1: Real-World Only
    f.write("### Part 1: Real-World Only Coverage\n\n")
    f.write(
        "Coverage using **only real-world, human-annotated datasets** "
        "(excludes synthetic, weak supervision, and generated data).\n\n"
    )
    f.write(
        f"- ✅ **{len(real_world_sufficient)}** FRs have SUFFICIENT real-world data (≥100% of minimum)  \n"
        f"- ⚠️ **{len(real_world_partial)}** FRs have PARTIAL real-world data (50-99% of minimum)  \n"
        f"- ❌ **{len(real_world_critical)}** FRs have CRITICAL GAPS in real-world data (<50% of minimum)  \n\n"
    )

    # Part 2: Combined
    f.write("### Part 2: Real-World + Synthetic Coverage\n\n")
    f.write(
        "Coverage using **combined real-world + synthetic/weak-supervision data**. "
        "This represents our achievable coverage with current resources.\n\n"
    )
    f.write(
        f"- ✅ **{len(combined_sufficient)}** FRs have SUFFICIENT combined data (≥100% of minimum)  \n"
        f"- ⚠️ **{len(combined_partial)}** FRs have PARTIAL combined data (50-99% of minimum)  \n"
        f"- ❌ **{len(combined_critical)}** FRs have CRITICAL GAPS in combined data (<50% of minimum)  \n\n"
    )

    # Gap analysis
    synthetic_filled_gaps = len(
        [
            req
            for req in report.fr_requirements.values()
            if req.real_world_count < req.min_samples * 0.5
            and req.current_count >= req.min_samples * 0.5
        ]
    )

    f.write("### Gap Analysis\n\n")
    f.write(
        f"- **{synthetic_filled_gaps}** Critical gaps in real-world data are filled by synthetic/weak-supervision  \n"
        f"- **{len(real_world_critical) - synthetic_filled_gaps}** Critical gaps remain even with synthetic data  \n\n"
    )


def _calculate_coverage_status(
    real_coverage_pct: float,
) -> str:
    """Calculate coverage status emoji from percentage."""
    if real_coverage_pct >= 100:
        return "✅ SUFFICIENT"
    if real_coverage_pct >= 50:
        return "⚠️ PARTIAL"
    return "❌ GAP"


def _calculate_synthetic_flag(req: FRRequirement) -> str:
    """Calculate synthetic composition flag for requirement."""
    if req.synthetic_count > 0 and req.real_world_count == 0:
        return " 🔴"  # Synthetic only
    if req.current_count > 0 and (req.synthetic_count / req.current_count) > 0.5:
        return " ⚠️"  # High synthetic ratio
    return ""


def _write_fr_breakdown_table(f, report: SufficiencyReport) -> None:
    """Write FR-by-FR breakdown table."""
    f.write(MD_SEPARATOR)
    f.write("## FR-by-FR Breakdown\n\n")
    f.write(
        "| FR ID | Requirement | Min Samples | Real-World | Synthetic | Total | Real-World Status | Combined Status | Notes |\n"
    )
    f.write(
        "|-------|-------------|-------------|------------|-----------|-------|-------------------|-----------------|-------|\n"
    )

    for fr_id in sorted(report.fr_requirements.keys()):
        req = report.fr_requirements[fr_id]

        real_coverage_pct = (
            (req.real_world_count / req.min_samples * 100) if req.min_samples > 0 else 0
        )
        combined_coverage_pct = (
            (req.current_count / req.min_samples * 100) if req.min_samples > 0 else 0
        )

        real_world_status = _calculate_coverage_status(real_coverage_pct)
        flag = _calculate_synthetic_flag(req)

        f.write(
            f"| {req.fr_id} | {req.name} | {req.min_samples:,} | "
            f"{req.real_world_count:,} ({real_coverage_pct:.0f}%) | "
            f"{req.synthetic_count:,} | "
            f"{req.current_count:,} ({combined_coverage_pct:.0f}%){flag} | "
            f"{real_world_status} | "
            f"{req.status.value} | "
            f"{req.notes} |\n"
        )


def _write_critical_gaps(
    f, critical: list[FRRequirement], report: SufficiencyReport
) -> None:
    """Write critical gaps section."""
    f.write(MD_SEPARATOR_WITH_NEWLINE)
    f.write("## Critical Gaps (Priority 1)\n\n")

    if critical:
        f.write("| FR ID | Requirement | Missing Samples | Cost Estimate | Notes |\n")
        f.write("|-------|-------------|-----------------|---------------|-------|\n")

        for req in critical:
            missing = req.min_samples - req.current_count
            cost_str = (
                f"${req.cost_estimate:,.2f}" if req.cost_estimate else "Free dataset"
            )
            f.write(
                f"| {req.fr_id} | {req.name} | {missing:,} | {cost_str} | {req.notes} |\n"
            )

        f.write(
            f"\n**Total Investment for Critical Gaps**: ${report.total_cost_estimate:,.2f}\n\n"
        )
    else:
        f.write("✅ **No critical gaps identified!**\n\n")


def _write_layout_coverage(f, report: SufficiencyReport) -> None:
    """Write layout class coverage section."""
    if not report.layout_class_coverage:
        return

    f.write(MD_SEPARATOR)
    f.write("## FR-4.2: Layout Element Coverage (11 Classes)\n\n")
    f.write("| Class ID | Min Required | Current Count | Status |\n")
    f.write("|----------|--------------|---------------|--------|\n")

    for (
        class_id,
        min_required,
    ) in DatasetSufficiencyMeasurer.DOCLAYNET_CLASS_MINIMUMS.items():
        current = report.layout_class_coverage.get(class_id, 0)
        status = _calculate_coverage_status(
            (current / min_required * 100) if min_required > 0 else 0
        ).split()[0]
        f.write(f"| Class {class_id} | {min_required:,} | {current:,} | {status} |\n")


def _write_quality_coverage(f, report: SufficiencyReport) -> None:
    """Write quality dimension coverage section."""
    if not report.quality_dimension_coverage:
        return

    f.write(MD_SEPARATOR_WITH_NEWLINE)
    f.write("## FR-2.3: Learned Quality Dimensions\n\n")
    f.write("| Dimension | Required | Current | Status |\n")
    f.write("|-----------|----------|---------|--------|\n")

    for dim, counts in report.quality_dimension_coverage.items():
        current = counts["current"]
        required = counts["required"]
        status = _calculate_coverage_status(
            (current / required * 100) if required > 0 else 0
        ).split()[0]
        f.write(
            f"| {dim.replace('_', ' ').title()} | {required:,} | {current:,} | {status} |\n"
        )


def _write_language_coverage(f, report: SufficiencyReport) -> None:
    """Write multilingual coverage section."""
    if not report.language_coverage:
        return

    f.write(MD_SEPARATOR_WITH_NEWLINE)
    f.write(
        f"## FR-5.3: Multilingual Coverage ({len(report.language_coverage)} Languages)\n\n"
    )

    # Top 20 languages by sample count
    top_languages = sorted(
        report.language_coverage.items(), key=lambda x: x[1], reverse=True
    )[:20]

    f.write("**Top 20 Languages by Sample Count:**\n\n")
    f.write("| Language Code | Paragraph Count |\n")
    f.write("|---------------|----------------|\n")

    f.writelines(f"| {lang} | {count:,} |\n" for lang, count in top_languages)

    total_paragraphs = sum(report.language_coverage.values())
    f.write(
        f"\n**Total**: {len(report.language_coverage)} languages, {total_paragraphs:,} paragraphs\n\n"
    )


def _write_recommendations(f, report: SufficiencyReport) -> None:
    """Write recommendations section."""
    f.write(MD_SEPARATOR)
    f.write("## Recommendations\n\n")

    # Priority 0: Real-World Data Acquisition
    f.write("### Priority 0: Real-World Data Acquisition Strategy\n\n")
    f.write(
        "> **Philosophy**: While synthetic/weak-supervision data helps meet minimum requirements, "
        "**real-world human-annotated data should be prioritized** for production model quality.\n\n"
    )
    f.write("**Focus areas for real-world data acquisition:**\n\n")

    # Identify FRs with critical real-world gaps
    real_world_gaps = [
        req
        for req in report.fr_requirements.values()
        if req.real_world_count < req.min_samples * 0.5
        and req.current_count >= req.min_samples * 0.5
    ]

    if real_world_gaps:
        for req in sorted(
            real_world_gaps,
            key=lambda x: x.min_samples - x.real_world_count,
            reverse=True,
        )[:5]:
            missing_real = req.min_samples - req.real_world_count
            f.write(
                f"- **{req.fr_id}** ({req.name}): Need {missing_real:,} real-world samples "
                f"(currently {req.real_world_count:,}/{req.min_samples:,}, filled with {req.synthetic_count:,} synthetic)  \n"
            )
    else:
        f.write(
            "- ✅ All FRs with synthetic data also have sufficient real-world coverage  \n"
        )

    f.write("\n")

    # Additional recommendation sections (Priority 1-4)
    _write_additional_recommendations(f)


def _write_additional_recommendations(f) -> None:
    """Write additional recommendation priorities."""
    f.write("### Priority 1: Benchmark Dataset Usage Policy\n\n")
    f.write(
        "> **IMPORTANT**: Several datasets are located in `/data/benchmarks/` but have train/validation splits "
        "that could be used for training. **Test splits must NEVER be used for training.**\n\n"
    )
    f.write("**Benchmark datasets with usable train/validation splits:**\n\n")
    f.write(
        "- **SignaTR6K**: Train (5,169) + Validation (530) = 5,699 usable for FR-5.2 signature detection  \n"
    )
    f.write("  - ❌ **Test split (558) is RESERVED for peer benchmarking**  \n")
    f.write(
        "- **WiLI-2018**: Train split (117,500) usable for FR-5.3 multilingual detection  \n"
    )
    f.write("  - ❌ **Test split (117,500) is RESERVED for peer benchmarking**  \n")
    f.write(
        "- **DocLayNet**: Used for weak supervision label generation (parasitic content, document classification, DQS routing)  \n"
    )
    f.write(
        "  - ⚠️ **Verify test split is excluded from weak supervision generation**  \n\n"
    )

    f.write("### Priority 2: Structural Relationship Annotations (~$8,500)\n\n")
    f.write("- **FR-4.5**: Footnote linking (6k pages, $1,500)  \n")
    f.write("- **FR-4.12**: Reading order sequences (40k pages, $5,000)  \n")
    f.write("- **FR-4.6**: Figure-caption linking (10k pairs, $1,000)  \n")
    f.write("- **FR-4.4**: Parasitic content flags (10k pages, $500)  \n")
    f.write("- **FR-4.7**: Vertical text orientation (5k samples, $500)  \n\n")

    f.write("### Priority 3: Weak Supervision Generation (FREE)\n\n")
    f.write(
        "- **FR-2.3**: Generate 3-dimension quality labels using BRISQUE, NIQE, Laplacian, histogram analysis  \n"
    )
    f.write(
        "- **FR-7.1**: Generate DQS routing matrix labels (degradation + structural complexity)  \n\n"
    )

    f.write("### Priority 4: Wait for DIQA-5000 (Sept 2025)\n\n")
    f.write(
        "- Replace weak supervision with 5k ground-truth 3-dimension quality labels  \n"
    )
    f.write("- Validate learned quality models against human ratings  \n\n")

    f.write(MD_SEPARATOR)
    f.write("**Report End**\n")


def generate_markdown_report(report: SufficiencyReport, output_path: Path) -> None:
    """Generate Markdown sufficiency report."""
    logger.info(f"Generating Markdown report at {output_path}...")

    # Get categorized requirements for critical gaps section
    (
        _,
        _,
        _,
        _,
        _,
        critical,
    ) = _categorize_requirements_by_status(report)

    with open(output_path, "w") as f:
        _write_report_header(f, report)
        _write_executive_summary(f, report)
        _write_two_part_analysis(f, report)
        _write_fr_breakdown_table(f, report)
        _write_critical_gaps(f, critical, report)
        _write_layout_coverage(f, report)
        _write_quality_coverage(f, report)
        _write_language_coverage(f, report)
        _write_recommendations(f, report)

    logger.info(f"Report generated at {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Measure dataset sufficiency against FR requirements"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/reference/DATASET_SUFFICIENCY_REPORT.md"),
        help="Output path for sufficiency report (default: docs/reference/DATASET_SUFFICIENCY_REPORT.md)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("/home/byron/dev/image_detection/data"),
        help="Root directory for datasets",
    )

    args = parser.parse_args()

    # Build dataset inventory
    inventory = DatasetInventory(
        doclaynet_path=args.data_root / "benchmarks" / "doclaynet",
        tablebank_path=args.data_root / "benchmarks" / "tablebank",
        signatr6k_path=args.data_root / "benchmarks" / "signatr6k",
        wili2018_path=args.data_root / "benchmarks" / "wili_2018",
        phase2_iqa_path=args.data_root / "training" / "iqa_phase2",
        iam_handwriting_path=args.data_root
        / "training"
        / "specialized"
        / "handwriting"
        / "iam",
        omnidocbench_path=args.data_root / "benchmarks" / "omnidocbench",
        pubtabnet_path=args.data_root / "benchmarks" / "pubtabnet",
        fintabnet_path=args.data_root / "benchmarks" / "fintabnet",
        # Additional training datasets
        invoices_kaggle_path=args.data_root / "training" / "invoices_kaggle",
        mobile_receipts_path=args.data_root / "training" / "mobile_receipts_voxel51",
        receipts_hitl_path=args.data_root / "training" / "receipts_hitl",
        docsynth300k_path=args.data_root / "training" / "layout" / "docsynth300k",
        docbank_path=args.data_root / "training" / "layout" / "docbank",
        # Business document datasets
        nist_sd2_path=args.data_root / "training" / "business_documents" / "sd02",
        docile_path=args.data_root / "training" / "business_documents" / "docile",
    )

    # Run measurements
    measurer = DatasetSufficiencyMeasurer(inventory)
    report = measurer.measure_all()

    # Generate report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_markdown_report(report, args.output)

    logger.info(f"✅ Sufficiency measurement complete. Report at {args.output}")


if __name__ == "__main__":
    main()
