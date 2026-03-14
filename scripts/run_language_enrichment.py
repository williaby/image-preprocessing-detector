#!/usr/bin/env python3
"""Run language enrichment on datasets with missing labels.

This script applies the tiered language detection system to enrich
metadata for samples with `language_code = 'und'`.

Usage:
    # Dry run (show what would be done)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python scripts/run_language_enrichment.py --dry-run

    # Run on MLT-19 test samples (limit 100)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python scripts/run_language_enrichment.py --dataset mlt19 --limit 100

    # Run on all samples needing enrichment
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python scripts/run_language_enrichment.py --dataset mlt19 --all
"""

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
METADATA_REGISTRY = Path("/mnt/e/image_detection/metadata_registry/json")
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")

# Dataset to base path mapping
DATASET_PATHS = {
    "mlt19": BASE_DATA_PATH / "language/mlt19",
    "arabic_docs_ocr": BASE_DATA_PATH / "language/arabic_docs_ocr",
    "cvsi": BASE_DATA_PATH / "language/cvsi",
    "hindi_ocr_synthetic": BASE_DATA_PATH / "language/hindi_ocr_synthetic",
}


@dataclass
class MockLocalResult:
    """Mock result to trigger Tier 1b escalation."""

    primary_language: str = "und"
    primary_script: str | None = None
    detected_languages: list = field(default_factory=list)
    detected_scripts: list = field(default_factory=list)
    confidence: float = 0.1
    method: str = "mock_for_escalation"
    votes: list = field(default_factory=list)
    is_multilingual: bool = False


def get_samples_needing_enrichment(dataset: str) -> list[dict]:
    """Get samples with und language that need enrichment."""
    metadata_file = METADATA_REGISTRY / f"{dataset}_metadata.json"
    if not metadata_file.exists():
        logger.error(f"Metadata file not found: {metadata_file}")
        return []

    with open(metadata_file) as f:
        data = json.load(f)

    samples = data.get("samples", [])

    # Filter to samples with 'und' language
    needing = []
    for s in samples:
        lang_code = s.get("original_labels", {}).get("language_code", "und")
        if lang_code == "und":
            needing.append(s)

    return needing


def enrich_sample(
    sample: dict,
    base_path: Path,
    manager,
) -> dict | None:
    """Run language detection on a single sample."""
    rel_path = sample.get("source", {}).get("original_path", "")
    img_path = base_path / rel_path

    if not img_path.exists():
        return None

    # Create mock local result to trigger Tier 1b
    mock_local = MockLocalResult()
    result = manager.detect(img_path, mock_local)

    return {
        "sample_id": sample.get("id"),
        "image_path": str(img_path),
        "primary_language": result.primary_language,
        "primary_script": result.primary_script,
        "detected_languages": result.detected_languages,
        "detected_scripts": result.detected_scripts,
        "confidence": result.confidence,
        "method": result.method,
        "tier": result.tier,
        "model_used": result.model_used,
        "cost_usd": result.cost_usd,
        "is_multilingual": len(result.detected_languages) > 1,
    }


def update_metadata(
    dataset: str,
    enrichments: list[dict],
) -> None:
    """Update metadata file with language enrichments."""
    metadata_file = METADATA_REGISTRY / f"{dataset}_metadata.json"

    with open(metadata_file) as f:
        data = json.load(f)

    # Build lookup
    enrichment_lookup = {e["sample_id"]: e for e in enrichments}

    # Update samples
    updated = 0
    for sample in data.get("samples", []):
        sample_id = sample.get("id")
        if sample_id in enrichment_lookup:
            enrichment = enrichment_lookup[sample_id]

            # Add to enrichments
            if "enrichments" not in sample:
                sample["enrichments"] = {"current_version": 0, "versions": []}

            current_ver = sample["enrichments"].get("current_version", 0)
            new_ver = current_ver + 1

            sample["enrichments"]["versions"].append(
                {
                    "version": new_ver,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "enrichment_type": "language_detection",
                    "data": {
                        "primary_language": enrichment["primary_language"],
                        "primary_script": enrichment["primary_script"],
                        "detected_languages": enrichment["detected_languages"],
                        "detected_scripts": enrichment["detected_scripts"],
                        "confidence": enrichment["confidence"],
                        "method": enrichment["method"],
                        "tier": enrichment["tier"],
                        "model_used": enrichment["model_used"],
                        "is_multilingual": enrichment["is_multilingual"],
                    },
                }
            )
            sample["enrichments"]["current_version"] = new_ver
            updated += 1

    # Save
    backup_file = metadata_file.with_suffix(".json.bak")
    metadata_file.rename(backup_file)

    with open(metadata_file, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Updated {updated} samples, backup at {backup_file}")


def main():
    parser = argparse.ArgumentParser(description="Run language enrichment")
    parser.add_argument("--dataset", default="mlt19", help="Dataset name")
    parser.add_argument("--limit", type=int, help="Limit samples to process")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    parser.add_argument("--all", action="store_true", help="Process all samples")
    parser.add_argument(
        "--paid", action="store_true", help="Use paid model (faster, ~$0.0003/sample)"
    )
    args = parser.parse_args()

    # Import escalation
    from scripts.language_escalation import EscalationManager, EscalationConfig

    dataset = args.dataset
    base_path = DATASET_PATHS.get(dataset)

    if not base_path:
        logger.error(f"Unknown dataset: {dataset}")
        logger.info(f"Available: {list(DATASET_PATHS.keys())}")
        return 1

    # Get samples needing enrichment
    samples = get_samples_needing_enrichment(dataset)
    logger.info(f"Found {len(samples)} samples with 'und' language in {dataset}")

    if args.dry_run:
        logger.info("Dry run - no changes will be made")
        return 0

    # Limit samples if requested
    if args.limit and not args.all:
        samples = samples[: args.limit]
        logger.info(f"Processing {len(samples)} samples (limited)")
    elif not args.all:
        # Default to 10 samples for safety
        samples = samples[:10]
        logger.info(f"Processing {len(samples)} samples (use --all for full run)")

    # Setup escalation manager
    if args.paid:
        # Use paid model directly (no rate limits, ~$0.0003/sample)
        logger.info("Using PAID model: qwen/qwen-2.5-vl-7b-instruct")
        config = EscalationConfig(
            confidence_threshold=0.0,
            free_vision_model="qwen/qwen-2.5-vl-7b-instruct",  # Paid version (no :free suffix)
            tier1b_confidence_threshold=0.7,
        )
        DELAY_SECONDS = 0.1  # Minimal delay for paid tier
    else:
        # Use free tier with rate limiting
        logger.info("Using FREE model: qwen/qwen-2.5-vl-7b-instruct:free (20 req/min)")
        config = EscalationConfig(
            confidence_threshold=0.0,
            tier1b_confidence_threshold=0.7,
        )
        DELAY_SECONDS = 3.5  # Stay under 20/min limit

    manager = EscalationManager(config)

    enrichments = []
    lang_counts = Counter()
    start_time = time.time()

    for i, sample in enumerate(samples):
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            logger.info(f"Progress: {i + 1}/{len(samples)} ({rate:.1f} samples/sec)")

        result = enrich_sample(sample, base_path, manager)
        if result:
            enrichments.append(result)
            lang_counts[result["primary_language"]] += 1

        # Rate limit delay
        time.sleep(DELAY_SECONDS)

    logger.info(f"Processed {len(enrichments)} samples successfully")

    # Show distribution
    print("\nLanguage distribution:")
    for lang, count in lang_counts.most_common():
        print(f"  {lang}: {count}")

    # Update metadata
    if enrichments:
        update_metadata(dataset, enrichments)

    return 0


if __name__ == "__main__":
    sys.exit(main())
