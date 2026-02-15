#!/usr/bin/env python3
"""Apply domain classifications to siw13 Layer 2 metadata.

SIW-13 (Scene Images of Words in 13 Scripts) contains cropped word images
from Google Street View in 13 writing systems. All images are scene text:
shop signs, store names, street signage, banners, and commercial signage.

Contact sheet visual review of representative samples from 6 scripts
(Arabic, Chinese, English, Japanese, Korean, Thai) confirms uniform PER
classification across all scripts. No document-type variation exists -
the dataset is exclusively cropped scene text.

13 scripts: Arabic (1,002), Cambodian (1,083), Chinese (1,298),
English (1,221), Greek (1,018), Hebrew (1,242), Japanese (1,215),
Kannada (1,029), Korean (1,561), Mongolian (1,192), Russian (1,031),
Thai (2,222), Tibetan (1,177).

Usage::

    python scripts/audit/apply_siw13_domains.py --dry-run
    python scripts/audit/apply_siw13_domains.py

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
    "/mnt/e/image_detection/metadata_registry/json/siw13_metadata.json"
)

DOMAIN = "PER"
CONFIDENCE = 0.90
METHOD = "visual_contact_sheet_review_scene_text"


def main() -> int:
    """Apply PER domain to all siw13 samples."""
    parser = argparse.ArgumentParser(
        description="Apply domain classifications to siw13 L2 metadata",
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
        help="Path to siw13 metadata JSON",
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

    script_counts: Counter[str] = Counter()
    updated = 0

    for sample in samples:
        filename = sample.get("source", {}).get("original_filename", "")
        script = filename.split("_")[0] if "_" in filename else "unknown"
        script_counts[script] += 1

        if not args.dry_run:
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if versions:
                latest_data = versions[-1].get("data", {})
                latest_data["domain_level1"] = DOMAIN
                latest_data["domain_confidence"] = CONFIDENCE
                latest_data["domain_detection_method"] = METHOD
                updated += 1

    log.info("Script distribution (all -> %s):", DOMAIN)
    for script, count in script_counts.most_common():
        log.info("  %s: %d (%.1f%%)", script, count, 100 * count / len(samples))

    if args.dry_run:
        log.info("Dry run - %d samples would be classified as %s", len(samples), DOMAIN)
    else:
        with open(args.metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Updated %d samples in %s", updated, args.metadata_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
