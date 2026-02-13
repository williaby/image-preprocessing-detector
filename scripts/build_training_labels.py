#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""
Build training labels from annotated metadata registry.

Implements Layer 3 (TRAINING) of the three-layer metadata architecture:
1. IMMUTABLE LAYER: Original labels (from annotate_base_metadata.py)
2. ENRICHMENT LAYER: Derived annotations (from annotate_base_metadata.py)
3. TRAINING LAYER: Computed on-demand (THIS SCRIPT)

Training layer outputs:
- iqa_vector: 45-dimensional severity vector (one per degradation type)
- iqa_binary: Binary presence/absence (thresholded from iqa_vector)
- anchor_score: Best available normalized score (0=best, 1=worst)
- anchor_source: Priority ranking (human > llm_high > llm_medium > synthetic)
- anchor_weight: Training weight based on source quality
- element_labels: Per-element annotations with bboxes for Phase 9

Usage:
    # Build training labels from metadata registry
    python scripts/build_training_labels.py --input /path/to/metadata_registry

    # Build with specific output path
    python scripts/build_training_labels.py --input /path/to/metadata_registry --output training_labels.parquet

    # Generate statistics
    python scripts/build_training_labels.py --input /path/to/metadata_registry --stats

Updated 2025-12-17: Initial implementation for Phase 7 training pipeline.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Common file name constants (S1192: avoid duplicate string literals)
TRAINING_LABELS_FILE = "training_labels.parquet"

# =============================================================================
# Constants - Degradation Index (aligned with detection-taxonomy.md)
# =============================================================================

# 45-dimensional degradation index mapping
# Each degradation type maps to a unique index in the iqa_vector
DEGRADATION_INDEX: dict[str, int] = {
    # Group 1: Blur/Focus (0-5)
    "motion_blur": 0,
    "defocus_blur": 1,
    "gaussian_blur": 2,
    "lens_aberration": 3,
    "depth_of_field": 4,
    "camera_shake": 5,
    # Group 2: Noise (6-12)
    "gaussian_noise": 6,
    "salt_pepper_noise": 7,
    "speckle_noise": 8,
    "film_grain": 9,
    "sensor_noise": 10,
    "quantization_noise": 11,
    "banding": 12,
    # Group 3: Geometric (13-18)
    "skew": 13,
    "rotation": 14,
    "perspective": 15,
    "barrel_distortion": 16,
    "pincushion_distortion": 17,
    "page_curl": 18,
    # Group 4: Illumination (19-25)
    "underexposure": 19,
    "overexposure": 20,
    "uneven_lighting": 21,
    "shadow": 22,
    "glare": 23,
    "vignetting": 24,
    "color_cast": 25,
    # Group 5: Compression (26-29)
    "jpeg_artifacts": 26,
    "jpeg2000_artifacts": 27,
    "webp_artifacts": 28,
    "low_bitrate": 29,
    # Group 6: Physical (30-36)
    "paper_yellowing": 30,
    "foxing": 31,
    "staining": 32,
    "bleed_through": 33,
    "fading": 34,
    "creasing": 35,
    "roller_marks": 36,
    # Group 7: Text/Content (37-41)
    "faint_text": 37,
    "broken_characters": 38,
    "merged_characters": 39,
    "halftone_interference": 40,
    "moire_pattern": 41,
    # Group 8: Scanner Artifacts (42-44)
    "dust_scratches": 42,
    "scan_lines": 43,
    "edge_shadow": 44,
}

NUM_DEGRADATION_TYPES = 45


class AnchorSource(str, Enum):
    """Anchor score source priority ranking."""

    HUMAN = "human"  # Weight: 1.0
    LLM_HIGH = "llm_high"  # Weight: 0.8 (confidence > 0.8)
    LLM_MEDIUM = "llm_medium"  # Weight: 0.5 (confidence 0.5-0.8)
    LLM_LOW = "llm_low"  # Weight: 0.3 (confidence < 0.5)
    SYNTHETIC = "synthetic"  # Weight: 0.3 (augmentation-derived)
    NONE = "none"  # Weight: 0.0 (no anchor)


ANCHOR_WEIGHTS: dict[AnchorSource, float] = {
    AnchorSource.HUMAN: 1.0,
    AnchorSource.LLM_HIGH: 0.8,
    AnchorSource.LLM_MEDIUM: 0.5,
    AnchorSource.LLM_LOW: 0.3,
    AnchorSource.SYNTHETIC: 0.3,
    AnchorSource.NONE: 0.0,
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TrainingLabels:
    """Training-ready labels for a single sample."""

    sample_id: str

    # IQA multi-label vector
    iqa_vector: list[float]  # 45-dimensional severity vector
    iqa_binary: list[bool]  # Binary presence/absence

    # Perceptual score anchors
    anchor_score: float | None  # 0-1 scale (0=best, 1=worst)
    anchor_source: AnchorSource
    anchor_weight: float

    # Individual score references
    human_mos_normalized: float | None
    llm_mos_normalized: float | None
    llm_confidence: float | None

    # Phase 9 element labels (JSON-serialized for complex structure)
    element_labels_json: str | None

    # Metadata
    dataset_name: str
    has_annotations: bool


# =============================================================================
# Score Normalization
# =============================================================================


def normalize_diqa_mos(mos: float) -> float:
    """Normalize DIQA MOS (1-5 scale) to 0-1 (0=best, 1=worst)."""
    # DIQA: 5 = best quality, 1 = worst quality
    # Normalize to 0-1 where 0=best, 1=worst
    return (5.0 - mos) / 4.0


def normalize_live_dmos(dmos: float) -> float:
    """Normalize LIVE DMOS (0-100 scale) to 0-1 (0=best, 1=worst)."""
    # LIVE: 0 = no distortion (best), 100 = max distortion (worst)
    return dmos / 100.0


def normalize_csiq_dmos(dmos: float) -> float:
    """Normalize CSIQ DMOS (already 0-1) to 0-1 (0=best, 1=worst)."""
    # CSIQ: 0 = best, 1 = worst (already normalized)
    return dmos


def normalize_smartdoc_mos(mos: float) -> float:
    """Normalize SmartDoc MOS (1-5 scale) to 0-1 (0=best, 1=worst)."""
    # SmartDoc: 5 = best quality, 1 = worst quality
    return (5.0 - mos) / 4.0


# =============================================================================
# Training Label Computation
# =============================================================================


def compute_anchor_score(
    record: dict[str, Any],
) -> tuple[float | None, AnchorSource, float]:
    """Compute best available anchor score with source priority.

    Priority: human > llm_high > llm_medium > llm_low > synthetic > none

    Returns:
        Tuple of (anchor_score, anchor_source, anchor_weight)
    """
    # Check for human MOS scores (highest priority)
    diqa_mos = record.get("diqa_mos")
    live_dmos = record.get("live_dmos")
    csiq_dmos = record.get("csiq_dmos")
    smartdoc_mos = record.get("smartdoc_mos")

    if diqa_mos is not None:
        return (
            normalize_diqa_mos(diqa_mos),
            AnchorSource.HUMAN,
            ANCHOR_WEIGHTS[AnchorSource.HUMAN],
        )
    if live_dmos is not None:
        return (
            normalize_live_dmos(live_dmos),
            AnchorSource.HUMAN,
            ANCHOR_WEIGHTS[AnchorSource.HUMAN],
        )
    if csiq_dmos is not None:
        return (
            normalize_csiq_dmos(csiq_dmos),
            AnchorSource.HUMAN,
            ANCHOR_WEIGHTS[AnchorSource.HUMAN],
        )
    if smartdoc_mos is not None:
        return (
            normalize_smartdoc_mos(smartdoc_mos),
            AnchorSource.HUMAN,
            ANCHOR_WEIGHTS[AnchorSource.HUMAN],
        )

    # Check for LLM predictions (second priority)
    llm_mos = record.get("llm_predicted_mos")
    llm_confidence = record.get("llm_prediction_confidence")

    if llm_mos is not None:
        # Normalize LLM MOS (assuming DIQA-aligned 1-5 scale)
        normalized = normalize_diqa_mos(llm_mos)

        # Determine LLM quality tier based on confidence
        if llm_confidence is not None:
            if llm_confidence > 0.8:
                source = AnchorSource.LLM_HIGH
            elif llm_confidence > 0.5:
                source = AnchorSource.LLM_MEDIUM
            else:
                source = AnchorSource.LLM_LOW
        else:
            source = AnchorSource.LLM_MEDIUM  # Default if no confidence

        return normalized, source, ANCHOR_WEIGHTS[source]

    # No anchor available
    return None, AnchorSource.NONE, ANCHOR_WEIGHTS[AnchorSource.NONE]


def extract_element_labels(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract Phase 9 element labels from COCO annotations.

    Converts raw COCO annotations to ElementLabel format:
    - element_id: unique ID
    - element_type: table, formula, figure, etc.
    - bbox: [x, y, width, height] COCO format
    - confidence: detection confidence
    - classifier_output: type-specific classification
    """
    element_labels: list[dict[str, Any]] = []
    element_id = 0

    # DocLayNet annotations
    doclaynet_json = record.get("doclaynet_annotations_json")
    if doclaynet_json:
        try:
            annotations = json.loads(doclaynet_json)
            for ann in annotations:
                element_labels.append(
                    {
                        "element_id": f"doclaynet_{element_id}",
                        "element_type": _map_doclaynet_category(
                            ann.get("category_name", "")
                        ),
                        "bbox": ann.get("bbox", [0, 0, 0, 0]),
                        "confidence": ann.get("score", 1.0),
                        "source": "doclaynet",
                        "original_category": ann.get("category_name"),
                    }
                )
                element_id += 1
        except (json.JSONDecodeError, TypeError):
            pass

    # TableBank annotations
    tablebank_json = record.get("tablebank_annotations_json")
    if tablebank_json:
        try:
            annotations = json.loads(tablebank_json)
            for ann in annotations:
                element_labels.append(
                    {
                        "element_id": f"tablebank_{element_id}",
                        "element_type": "table",
                        "bbox": ann.get("bbox", [0, 0, 0, 0]),
                        "confidence": ann.get("score", 1.0),
                        "source": "tablebank",
                        "table_type": "unknown",  # Would need classifier
                    }
                )
                element_id += 1
        except (json.JSONDecodeError, TypeError):
            pass

    return element_labels


def _map_doclaynet_category(category: str) -> str:
    """Map DocLayNet category to ElementLabel element_type."""
    mapping = {
        "Table": "table",
        "Formula": "formula",
        "Picture": "figure",
        "Caption": "caption",
        "Footnote": "footnote",
        "Page-Footer": "footer",
        "Page-Header": "header",
        "Section-Header": "header",
        "Title": "header",
        "Text": "text",
        "List-Item": "text",
    }
    return mapping.get(category, "unknown")


def build_iqa_vector(_record: dict[str, Any]) -> tuple[list[float], list[bool]]:
    """Build 45-dimensional IQA vector from degradation annotations.

    Currently returns zeros - will be populated when classical CV
    detectors run on images and store degradation scores.

    Returns:
        Tuple of (iqa_vector, iqa_binary)
    """
    # Initialize with zeros
    iqa_vector = [0.0] * NUM_DEGRADATION_TYPES
    iqa_binary = [False] * NUM_DEGRADATION_TYPES

    # TODO: Populate from classical CV detector outputs
    # This would come from running the detection pipeline and
    # storing results in the enrichment layer

    return iqa_vector, iqa_binary


def process_record(record: dict[str, Any]) -> TrainingLabels:
    """Process a single metadata record into training labels."""
    # Compute anchor score
    anchor_score, anchor_source, anchor_weight = compute_anchor_score(record)

    # Compute normalized scores
    human_normalized = None
    if record.get("diqa_mos"):
        human_normalized = normalize_diqa_mos(record["diqa_mos"])
    elif record.get("live_dmos"):
        human_normalized = normalize_live_dmos(record["live_dmos"])
    elif record.get("csiq_dmos"):
        human_normalized = normalize_csiq_dmos(record["csiq_dmos"])
    elif record.get("smartdoc_mos"):
        human_normalized = normalize_smartdoc_mos(record["smartdoc_mos"])

    llm_normalized = None
    if record.get("llm_predicted_mos"):
        llm_normalized = normalize_diqa_mos(record["llm_predicted_mos"])

    # Build IQA vector
    iqa_vector, iqa_binary = build_iqa_vector(record)

    # Extract element labels
    element_labels = extract_element_labels(record)
    element_labels_json = json.dumps(element_labels) if element_labels else None

    return TrainingLabels(
        sample_id=record["sample_id"],
        iqa_vector=iqa_vector,
        iqa_binary=iqa_binary,
        anchor_score=anchor_score,
        anchor_source=anchor_source,
        anchor_weight=anchor_weight,
        human_mos_normalized=human_normalized,
        llm_mos_normalized=llm_normalized,
        llm_confidence=record.get("llm_prediction_confidence"),
        element_labels_json=element_labels_json,
        dataset_name=record["dataset_name"],
        has_annotations=bool(element_labels),
    )


# =============================================================================
# Main Processing
# =============================================================================


def build_training_labels(input_path: Path, output_path: Path) -> int:
    """Build training labels from metadata registry.

    Args:
        input_path: Path to metadata_registry directory or parquet file
        output_path: Path for output training_labels.parquet

    Returns:
        Number of samples processed
    """
    # Load source data
    if input_path.is_file() and input_path.suffix == ".parquet":
        parquet_path = input_path
    else:
        parquet_path = input_path / "samples.parquet"

    if not parquet_path.exists():
        logger.error(f"Parquet file not found: {parquet_path}")
        return 0

    logger.info(f"Loading metadata from {parquet_path}")
    table = pq.read_table(parquet_path)
    df = table.to_pandas()
    logger.info(f"Loaded {len(df)} samples")

    # Process each record
    training_records = []
    for _, row in df.iterrows():
        record = row.to_dict()
        labels = process_record(record)

        training_records.append(
            {
                "sample_id": labels.sample_id,
                "dataset_name": labels.dataset_name,
                # IQA vector (stored as JSON for Parquet compatibility)
                "iqa_vector_json": json.dumps(labels.iqa_vector),
                "iqa_binary_json": json.dumps(labels.iqa_binary),
                # Anchor scores
                "anchor_score": labels.anchor_score,
                "anchor_source": labels.anchor_source.value,
                "anchor_weight": labels.anchor_weight,
                # Individual scores
                "human_mos_normalized": labels.human_mos_normalized,
                "llm_mos_normalized": labels.llm_mos_normalized,
                "llm_confidence": labels.llm_confidence,
                # Element labels
                "element_labels_json": labels.element_labels_json,
                "has_annotations": labels.has_annotations,
            }
        )

    # Save to Parquet
    output_table = pa.Table.from_pylist(training_records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(output_table, output_path, compression="snappy")

    logger.info(f"Saved {len(training_records)} training labels to {output_path}")
    return len(training_records)


def generate_statistics(input_path: Path) -> dict[str, Any]:
    """Generate statistics about training labels."""
    if input_path.is_file() and input_path.suffix == ".parquet":
        parquet_path = input_path
    else:
        parquet_path = input_path / TRAINING_LABELS_FILE

    if not parquet_path.exists():
        logger.error(f"Training labels not found: {parquet_path}")
        return {}

    table = pq.read_table(parquet_path)
    df = table.to_pandas()

    stats = {
        "total_samples": len(df),
        "by_dataset": df["dataset_name"].value_counts().to_dict(),
        "by_anchor_source": df["anchor_source"].value_counts().to_dict(),
        "with_human_anchor": len(df[df["anchor_source"] == "human"]),
        "with_llm_anchor": len(
            df[df["anchor_source"].isin(["llm_high", "llm_medium", "llm_low"])]
        ),
        "with_annotations": len(df[df["has_annotations"]]),
        "no_anchor": len(df[df["anchor_source"] == "none"]),
    }

    return stats


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build training labels from metadata registry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Build training labels
    python scripts/build_training_labels.py --input /mnt/e/image_detection/metadata_registry

    # Custom output path
    python scripts/build_training_labels.py --input /path/to/registry --output my_labels.parquet

    # Generate statistics
    python scripts/build_training_labels.py --input /path/to/registry --stats
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to metadata_registry directory or parquet file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for training_labels.parquet (default: input_dir/training_labels.parquet)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Generate statistics report",
    )

    args = parser.parse_args()

    if args.stats:
        stats = generate_statistics(args.input)
        if stats:
            logger.info("\n" + "=" * 70)
            logger.info("TRAINING LABELS STATISTICS")
            logger.info("=" * 70)
            logger.info(f"Total samples: {stats['total_samples']:,}")

            logger.info("\nBy Dataset:")
            for ds, count in sorted(stats["by_dataset"].items(), key=lambda x: -x[1]):
                logger.info(f"  {ds}: {count:,}")

            logger.info("\nBy Anchor Source:")
            for source, count in sorted(
                stats["by_anchor_source"].items(), key=lambda x: -x[1]
            ):
                logger.info(f"  {source}: {count:,}")

            logger.info(f"\nWith Human Anchor: {stats['with_human_anchor']:,}")
            logger.info(f"With LLM Anchor: {stats['with_llm_anchor']:,}")
            logger.info(f"With Annotations: {stats['with_annotations']:,}")
            logger.info(f"No Anchor: {stats['no_anchor']:,}")
    else:
        # Determine output path
        if args.output:
            output_path = args.output
        elif args.input.is_file():
            output_path = args.input.parent / TRAINING_LABELS_FILE
        else:
            output_path = args.input / TRAINING_LABELS_FILE

        count = build_training_labels(args.input, output_path)
        if count > 0:
            logger.info(f"\nTraining labels built successfully: {count:,} samples")


if __name__ == "__main__":
    main()
