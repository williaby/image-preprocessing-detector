#!/usr/bin/env python3
"""Apply domain classifications to jssoda UNK samples in Layer 2 metadata.

JSSODA (Japanese Simple Synthetic OCR Dataset) is a synthetic dataset of
programmatically rendered Japanese text. All 2,000 images look visually
identical (clean text on white background).

LLM enrichment (gemini-2.0-flash-lite) classified 1,307/2,000 (65.3%)
but left 693 as UNK because the weak model couldn't determine domain
from general Japanese essay text.

Visual inspection of UNK samples at full resolution reveals they are
all general-topic Japanese essays covering:
    - Personal growth and life experiences
    - Pet ownership and daily life
    - Love, family, and philosophical topics
    - Creative narratives and fiction
    - Cultural commentary (Disney, idol culture, food)

These are classified as PER (Personal/General) with moderate confidence
since the text content is personal essay/narrative in nature.

Usage::

    python scripts/audit/apply_jssoda_domains.py --dry-run
    python scripts/audit/apply_jssoda_domains.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/jssoda_metadata.json"
)


def main() -> int:
    """Apply PER domain to UNK jssoda samples."""
    parser = argparse.ArgumentParser(
        description="Apply domain classifications to jssoda UNK samples",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show counts without modifying metadata",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=METADATA_PATH,
        help="Path to jssoda metadata JSON",
    )
    args = parser.parse_args()

    if not args.metadata_path.exists():
        log.error("Metadata file not found: %s", args.metadata_path)
        return 1

    log.info("Loading metadata from %s", args.metadata_path)
    with open(args.metadata_path) as fh:
        metadata = json.load(fh)

    samples = metadata.get("samples", [])
    log.info("Total samples: %d", len(samples))

    before_counts: Counter[str] = Counter()
    updated = 0

    for sample in samples:
        enrichments = sample.get("enrichments", {})
        versions = enrichments.get("versions", [])
        if not versions:
            continue

        latest_data = versions[-1].get("data", {})
        current_domain = latest_data.get("domain_level1", "UNK")
        before_counts[current_domain] += 1

        if current_domain == "UNK" and not args.dry_run:
            latest_data["domain_level1"] = "PER"
            latest_data["domain_confidence"] = 0.6
            latest_data["domain_detection_method"] = (
                "visual_review_synthetic_japanese_essays"
            )
            updated += 1

    log.info("Before update:")
    for domain, count in before_counts.most_common():
        log.info("  %s: %d (%.1f%%)", domain, count, 100 * count / len(samples))

    if args.dry_run:
        log.info("Dry run - %d UNK would be reclassified as PER", before_counts["UNK"])
    else:
        with open(args.metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info(
            "Updated %d UNK -> PER in %s",
            updated,
            args.metadata_path,
        )

    # Show after counts
    after_counts = Counter(before_counts)
    after_counts["PER"] = after_counts.get("PER", 0) + before_counts["UNK"]
    del after_counts["UNK"]
    log.info("After update:")
    for domain, count in after_counts.most_common():
        log.info("  %s: %d (%.1f%%)", domain, count, 100 * count / len(samples))

    return 0


if __name__ == "__main__":
    sys.exit(main())
