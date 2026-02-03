#!/usr/bin/env python3
"""Calculate text statistics from extracted text content.

This script processes extracted text (from GCS OCR, ground truth, etc.) and:
1. Populates the text_content field in Layer 2 metadata
2. Computes text_statistics from the text_content

Two-stage pipeline:
- Stage 1: Text extraction (dataset-specific) → text_content
- Stage 2: Statistics calculation (universal) → text_statistics

Usage:
    # Process all datasets with available text
    python scripts/calculate_text_statistics.py

    # Process specific dataset
    python scripts/calculate_text_statistics.py --dataset funsd

    # Dry run (show what would be processed)
    python scripts/calculate_text_statistics.py --dataset funsd --dry-run

    # Custom paths
    python scripts/calculate_text_statistics.py \
        --layer2-dir /mnt/e/image_detection/metadata_registry/json \
        --annotations-dir /mnt/e/image_detection/annotations
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Text source configurations per dataset
TEXT_SOURCE_CONFIGS: dict[str, dict[str, Any]] = {
    "funsd": {
        "source_type": "ground_truth",
        "source_format": "funsd_annotation",
        "base_data_path": "/mnt/e/image_detection/01_base_data/forms/funsd",
        # FUNSD now uses original filenames directly (e.g., 82092117.png)
        # No hash mapping needed since Layer 2 keys match annotation keys
        "uses_file_hash_mapping": False,
    },
    "sroie": {
        "source_type": "ground_truth",
        "source_format": "txt_file",
        "text_dir": "ground_truth",
        "file_pattern": "*.txt",
    },
    "iam": {
        "source_type": "ground_truth",
        "source_format": "txt_file",
        "text_dir": "ground_truth",
        "file_pattern": "*.txt",
    },
    # Add more dataset configs as needed
}


@dataclass
class TextStatistics:
    """Computed text statistics."""

    character_count: int
    character_count_no_spaces: int
    word_count: int
    sentence_count: int | None
    paragraph_count: int | None
    line_count: int | None
    avg_word_length: float | None
    avg_sentence_length: float | None
    avg_paragraph_length: float | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "character_count": self.character_count,
            "character_count_no_spaces": self.character_count_no_spaces,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "line_count": self.line_count,
            "avg_word_length": self.avg_word_length,
            "avg_sentence_length": self.avg_sentence_length,
            "avg_paragraph_length": self.avg_paragraph_length,
        }


def calculate_text_stats(text: str) -> TextStatistics:
    """Calculate text statistics from raw text.

    Args:
        text: Raw text content

    Returns:
        TextStatistics with all computed metrics
    """
    if not text or not text.strip():
        return TextStatistics(
            character_count=0,
            character_count_no_spaces=0,
            word_count=0,
            sentence_count=0,
            paragraph_count=0,
            line_count=0,
            avg_word_length=None,
            avg_sentence_length=None,
            avg_paragraph_length=None,
        )

    # Character counts
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", "").replace("\t", "").replace("\n", ""))

    # Word count (whitespace tokenization)
    words = text.split()
    word_count = len(words)

    # Sentence count (punctuation-based: . ! ?)
    # Handle abbreviations and decimals carefully
    sentences = re.split(r"[.!?]+(?:\s|$)", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences) if sentences else 1

    # Paragraph count (double newline or explicit markers)
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    paragraph_count = len(paragraphs) if paragraphs else 1

    # Line count
    lines = text.split("\n")
    lines = [line for line in lines if line.strip()]
    line_count = len(lines)

    # Average word length
    avg_word_length = None
    if word_count > 0:
        total_word_chars = sum(len(w) for w in words)
        avg_word_length = round(total_word_chars / word_count, 2)

    # Average sentence length (in words)
    avg_sentence_length = None
    if sentence_count > 0 and word_count > 0:
        avg_sentence_length = round(word_count / sentence_count, 2)

    # Average paragraph length (in sentences)
    avg_paragraph_length = None
    if paragraph_count > 0 and sentence_count > 0:
        avg_paragraph_length = round(sentence_count / paragraph_count, 2)

    return TextStatistics(
        character_count=char_count,
        character_count_no_spaces=char_count_no_spaces,
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=paragraph_count,
        line_count=line_count,
        avg_word_length=avg_word_length,
        avg_sentence_length=avg_sentence_length,
        avg_paragraph_length=avg_paragraph_length,
    )


def load_gcs_ocr_text(
    annotations_dir: Path, dataset: str
) -> dict[str, dict[str, Any]]:
    """Load text from GCS OCR JSONL files.

    Args:
        annotations_dir: Base annotations directory
        dataset: Dataset name

    Returns:
        Dict mapping filename to text content and metadata
    """
    config = TEXT_SOURCE_CONFIGS.get(dataset, {})
    text_dir = config.get("text_dir", "gcs_ocr")
    file_pattern = config.get("file_pattern", "ocr_batch_*.jsonl")

    ocr_dir = annotations_dir / dataset / text_dir
    if not ocr_dir.exists():
        print(f"  ⚠️  OCR directory not found: {ocr_dir}")
        return {}

    text_map: dict[str, dict[str, Any]] = {}

    for jsonl_file in sorted(ocr_dir.glob(file_pattern)):
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    source = record.get("source", "")
                    text = record.get("text", "")
                    confidence = record.get("confidence", 0.0)
                    success = record.get("success", False)

                    if not success or not text:
                        continue

                    # Extract filename from source path
                    # e.g., "image-preprocessing-detector/datasets/funsd/.../82092117.png"
                    filename = Path(source).stem  # Get filename without extension

                    text_map[filename] = {
                        "full_text": text,
                        "source_type": config.get("source_type", "ocr_doctr"),
                        "source_format": config.get("source_format", "jsonl_gcs_ocr"),
                        "source_file": str(jsonl_file.name),
                        "confidence": confidence,
                    }
                except json.JSONDecodeError:
                    continue

    return text_map


def load_funsd_annotations(base_data_path: Path) -> dict[str, dict[str, Any]]:
    """Load text from FUNSD original annotation JSON files.

    FUNSD annotations have structure:
    {
        "form": [
            {"text": "...", "words": [{"text": "..."}], ...}
        ]
    }

    Args:
        base_data_path: Path to FUNSD base data (contains train/test subdirs)

    Returns:
        Dict mapping original filename to text content
    """
    text_map: dict[str, dict[str, Any]] = {}

    for split in ["train", "test"]:
        annotations_dir = base_data_path / split / "annotations"
        if not annotations_dir.exists():
            continue

        for json_file in sorted(annotations_dir.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Extract text from all form elements
                form = data.get("form", [])
                all_text_parts = []

                for element in form:
                    # Use element-level text (concatenated from words)
                    text = element.get("text", "")
                    if text and text.strip():
                        all_text_parts.append(text.strip())

                full_text = "\n".join(all_text_parts)
                filename = json_file.stem  # e.g., "82092117"

                text_map[filename] = {
                    "full_text": full_text,
                    "source_type": "ground_truth",
                    "source_format": "funsd_annotation",
                    "source_file": str(json_file.relative_to(base_data_path)),
                    "confidence": 1.0,
                    "split": split,
                }

            except Exception as e:
                print(f"  ⚠️  Error reading {json_file}: {e}")
                continue

    return text_map


def build_funsd_filename_mapping(
    metadata_samples: list[dict[str, Any]],
    base_data_path: Path,
) -> dict[str, str]:
    """Build mapping from Layer 2 sample keys to original FUNSD filenames.

    FUNSD files were renamed from original names (e.g., 0000971160.png) to
    standardized names (e.g., funsd_000000.jpg) based on sorted order.

    This function rebuilds that mapping by:
    1. Getting the sorted list of original filenames
    2. Matching funsd_NNNNNN to the Nth file in sorted order

    Args:
        metadata_samples: Layer 2 samples
        base_data_path: FUNSD base data path

    Returns:
        Dict mapping Layer 2 sample key to original FUNSD filename
    """
    # Get sorted list of original training images
    # (Layer 2 metadata was built from the 149 training images)
    train_images_dir = base_data_path / "train" / "images"
    if not train_images_dir.exists():
        print(f"  ⚠️  Train images directory not found: {train_images_dir}")
        return {}

    original_files = sorted([f.stem for f in train_images_dir.glob("*.png")])

    # Build mapping: funsd_NNNNNN -> original_filename
    mapping: dict[str, str] = {}
    for sample in metadata_samples:
        sample_filename = sample.get("source", {}).get("original_filename", "")
        if not sample_filename:
            continue

        sample_key = Path(sample_filename).stem  # e.g., "funsd_000000"

        # Extract index from funsd_NNNNNN
        if sample_key.startswith("funsd_"):
            try:
                idx = int(sample_key.replace("funsd_", ""))
                if 0 <= idx < len(original_files):
                    mapping[sample_key] = original_files[idx]
            except ValueError:
                continue

    return mapping


def load_ground_truth_text(
    annotations_dir: Path, dataset: str
) -> dict[str, dict[str, Any]]:
    """Load text from ground truth text files.

    Args:
        annotations_dir: Base annotations directory
        dataset: Dataset name

    Returns:
        Dict mapping filename to text content and metadata
    """
    config = TEXT_SOURCE_CONFIGS.get(dataset, {})
    text_dir = config.get("text_dir", "ground_truth")
    file_pattern = config.get("file_pattern", "*.txt")

    gt_dir = annotations_dir / dataset / text_dir
    if not gt_dir.exists():
        print(f"  ⚠️  Ground truth directory not found: {gt_dir}")
        return {}

    text_map: dict[str, dict[str, Any]] = {}

    for txt_file in sorted(gt_dir.glob(file_pattern)):
        try:
            with open(txt_file, encoding="utf-8") as f:
                text = f.read()

            filename = txt_file.stem

            text_map[filename] = {
                "full_text": text,
                "source_type": "ground_truth",
                "source_format": "txt_file",
                "source_file": str(txt_file.name),
                "confidence": 1.0,
            }
        except Exception as e:
            print(f"  ⚠️  Error reading {txt_file}: {e}")
            continue

    return text_map


def load_text_for_dataset(
    annotations_dir: Path,
    dataset: str,
    metadata_samples: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str] | None]:
    """Load text content for a dataset from the appropriate source.

    Args:
        annotations_dir: Base annotations directory
        dataset: Dataset name
        metadata_samples: Layer 2 samples (needed for hash-based mapping)

    Returns:
        Tuple of (text_map, filename_mapping) where filename_mapping maps
        Layer 2 keys to text_map keys if needed
    """
    config = TEXT_SOURCE_CONFIGS.get(dataset)
    if not config:
        print(f"  ⚠️  No text source configuration for dataset: {dataset}")
        return {}, None

    source_format = config.get("source_format", "")

    if source_format == "funsd_annotation":
        # FUNSD uses hash-based mapping due to renamed files
        base_data_path = Path(config.get("base_data_path", ""))
        if not base_data_path.exists():
            print(f"  ⚠️  FUNSD base data path not found: {base_data_path}")
            return {}, None

        text_map = load_funsd_annotations(base_data_path)

        # Build filename mapping if we have metadata samples
        filename_mapping = None
        if metadata_samples and config.get("uses_file_hash_mapping"):
            filename_mapping = build_funsd_filename_mapping(
                metadata_samples, base_data_path
            )
            print(f"  🔗 Built hash mapping for {len(filename_mapping)} samples")

        return text_map, filename_mapping

    elif source_format == "jsonl_gcs_ocr":
        return load_gcs_ocr_text(annotations_dir, dataset), None
    elif source_format == "txt_file":
        return load_ground_truth_text(annotations_dir, dataset), None
    else:
        print(f"  ⚠️  Unknown source format: {source_format}")
        return {}, None


def extract_sample_key(sample: dict[str, Any]) -> str | None:
    """Extract a key to match sample with text content.

    Tries multiple strategies to find a matchable identifier.
    """
    # Try original_filename first
    source = sample.get("source", {})
    if source:
        original_filename = source.get("original_filename", "")
        if original_filename:
            return Path(original_filename).stem

        original_path = source.get("original_path", "")
        if original_path:
            return Path(original_path).stem

    # Try sample id
    sample_id = sample.get("id", "")
    if sample_id:
        return sample_id

    return None


def process_dataset(
    layer2_dir: Path,
    annotations_dir: Path,
    dataset: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Process a dataset to add text_content and text_statistics.

    Args:
        layer2_dir: Directory containing Layer 2 metadata JSON files
        annotations_dir: Directory containing extracted text
        dataset: Dataset name
        dry_run: If True, don't write changes
        verbose: Print detailed progress

    Returns:
        Processing statistics
    """
    stats = {
        "dataset": dataset,
        "samples_total": 0,
        "samples_with_text": 0,
        "samples_updated": 0,
        "samples_skipped": 0,
        "text_stats_summary": {},
    }

    # Find Layer 2 metadata file
    metadata_file = layer2_dir / f"{dataset}_metadata.json"
    if not metadata_file.exists():
        print(f"  ❌ Layer 2 metadata not found: {metadata_file}")
        return stats

    # Load Layer 2 metadata first (needed for hash mapping)
    print(f"  📖 Loading Layer 2 metadata...")
    with open(metadata_file, encoding="utf-8") as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])

    # Load text content (pass samples for hash-based mapping if needed)
    print(f"  📖 Loading text content...")
    text_map, filename_mapping = load_text_for_dataset(
        annotations_dir, dataset, metadata_samples=samples
    )
    if not text_map:
        print(f"  ⚠️  No text content found for {dataset}")
        return stats

    print(f"  ✅ Found text for {len(text_map)} files")

    stats["samples_total"] = len(samples)

    # Collect statistics for aggregation
    all_char_counts = []
    all_word_counts = []
    all_sentence_counts = []
    all_paragraph_counts = []
    all_avg_word_lengths = []
    all_avg_sentence_lengths = []

    # Process each sample
    updated_count = 0
    for sample in samples:
        sample_key = extract_sample_key(sample)
        if not sample_key:
            stats["samples_skipped"] += 1
            continue

        # Map sample key to text key if needed
        text_key = sample_key
        if filename_mapping:
            text_key = filename_mapping.get(sample_key, sample_key)

        # Check if text exists for this sample
        text_data = text_map.get(text_key)
        if not text_data:
            stats["samples_skipped"] += 1
            continue

        stats["samples_with_text"] += 1

        # Get the current enrichment data
        enrichments = sample.get("enrichments", {})
        versions = enrichments.get("versions", [])

        if not versions:
            stats["samples_skipped"] += 1
            continue

        # Get the latest version's data
        latest_version = versions[-1]
        data = latest_version.get("data", {})

        # Create text_content entry
        full_text = text_data.get("full_text", "")
        text_content = {
            "full_text": full_text,
            "source_type": text_data.get("source_type", "unknown"),
            "source_format": text_data.get("source_format"),
            "source_file": text_data.get("source_file"),
            "extraction_method": "calculate_text_statistics.py_v1.0.0",
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": text_data.get("confidence"),
            "encoding": "utf-8",
            "is_complete": True,
        }

        # Calculate text statistics
        text_stats = calculate_text_stats(full_text)

        text_statistics = {
            **text_stats.to_dict(),
            "text_source": text_data.get("source_type", "unknown"),
            "computation_method": "regex_simple",
        }

        # Update the data
        if not dry_run:
            data["text_content"] = text_content
            data["text_statistics"] = text_statistics

        updated_count += 1

        # Collect for aggregation
        all_char_counts.append(text_stats.character_count)
        all_word_counts.append(text_stats.word_count)
        if text_stats.sentence_count is not None:
            all_sentence_counts.append(text_stats.sentence_count)
        if text_stats.paragraph_count is not None:
            all_paragraph_counts.append(text_stats.paragraph_count)
        if text_stats.avg_word_length is not None:
            all_avg_word_lengths.append(text_stats.avg_word_length)
        if text_stats.avg_sentence_length is not None:
            all_avg_sentence_lengths.append(text_stats.avg_sentence_length)

        if verbose:
            print(f"    {sample_key}: {text_stats.word_count} words, {text_stats.sentence_count} sentences")

    stats["samples_updated"] = updated_count

    # Compute aggregate statistics
    def compute_summary(values: list[float | int]) -> dict[str, Any] | None:
        if not values:
            return None
        return {
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
            "percentiles": {
                "p25": round(statistics.quantiles(values, n=4)[0], 2) if len(values) >= 4 else None,
                "p50": round(statistics.median(values), 2),
                "p75": round(statistics.quantiles(values, n=4)[2], 2) if len(values) >= 4 else None,
            },
        }

    stats["text_stats_summary"] = {
        "character_count": compute_summary(all_char_counts),
        "word_count": compute_summary(all_word_counts),
        "sentence_count": compute_summary(all_sentence_counts),
        "paragraph_count": compute_summary(all_paragraph_counts),
        "avg_word_length": compute_summary(all_avg_word_lengths),
        "avg_sentence_length": compute_summary(all_avg_sentence_lengths),
    }

    # Save updated metadata
    if not dry_run and updated_count > 0:
        print(f"  💾 Saving updated metadata...")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Updated {updated_count} samples")
    elif dry_run:
        print(f"  🔍 [DRY RUN] Would update {updated_count} samples")

    return stats


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate text statistics from extracted text content"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Process specific dataset (default: all configured datasets)",
    )
    parser.add_argument(
        "--layer2-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Directory containing Layer 2 metadata JSON files",
    )
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/annotations"),
        help="Directory containing extracted text annotations",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("TEXT STATISTICS CALCULATOR")
    print("=" * 60)
    print(f"Layer 2 directory: {args.layer2_dir}")
    print(f"Annotations directory: {args.annotations_dir}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - no changes will be made")
    print()

    # Determine which datasets to process
    if args.dataset:
        datasets = [args.dataset]
    else:
        datasets = list(TEXT_SOURCE_CONFIGS.keys())

    all_stats = []
    for dataset in datasets:
        print(f"\n📊 Processing {dataset}...")
        stats = process_dataset(
            layer2_dir=args.layer2_dir,
            annotations_dir=args.annotations_dir,
            dataset=dataset,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        all_stats.append(stats)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for stat in all_stats:
        dataset = stat["dataset"]
        total = stat["samples_total"]
        with_text = stat["samples_with_text"]
        updated = stat["samples_updated"]
        pct = (with_text / total * 100) if total > 0 else 0

        print(f"\n{dataset}:")
        print(f"  Total samples: {total}")
        print(f"  With text: {with_text} ({pct:.1f}%)")
        print(f"  Updated: {updated}")

        summary = stat.get("text_stats_summary", {})
        if summary.get("word_count"):
            wc = summary["word_count"]
            print(f"  Word count: {wc['min']}-{wc['max']} (μ={wc['mean']})")
        if summary.get("sentence_count"):
            sc = summary["sentence_count"]
            print(f"  Sentence count: {sc['min']}-{sc['max']} (μ={sc['mean']})")


if __name__ == "__main__":
    main()
