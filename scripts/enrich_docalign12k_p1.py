#!/usr/bin/env python3
"""P1 enrichment for docalign12k: VLM-informed domain, language, script, content flags.

Based on stratified VLM inspection of 12 representative images across all 14
distortion groups (2026-02-13, claude-opus-4-6 vision).

Findings:
  - ~65% Chinese (zh/Hani), ~35% English (en/Latn), some bilingual
  - Domains: EDUCATION (textbooks), MEDIA (magazines), SCIENCE (papers)
  - Content flags: many has_figure, some has_table/has_formula
  - Group 14 contains handwritten notes (KI-004 exception!)
  - All documents are LTR orientation, upright (0 deg)

Strategy:
  - iso639_language = "mul" (multilingual; accurate for mixed zh+en dataset)
  - iso15924_script = "Hani" (dominant; ~65% CJK)
  - script_family = "cjk" (dominant family)
  - domain_level1 = "GENERAL" (accurate for mixed education+media+science)
  - text_direction = "ltr" (correct for both Chinese horizontal and English)
  - content_flags: conservative defaults (False) since per-image VLM not done
  - Group 14 handwriting: flag has_handwriting=True for distortion_group=14

Usage:
    PYTHONPATH=. uv run python3 scripts/enrich_docalign12k_p1.py --dry-run
    PYTHONPATH=. uv run python3 scripts/enrich_docalign12k_p1.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/docalign12k_metadata.json"
)

# VLM-informed enrichment values (from 12-image stratified inspection)
ENRICHMENT_VALUES = {
    "iso639_language": "mul",
    "iso15924_script": "Hani",
    "script_family": "cjk",
    "language_confidence": 0.7,
    "domain_level1": "GENERAL",
    "domain_confidence": 0.8,
    "domain_detection_method": "vlm_contact_sheet_review",
    "text_direction": "ltr",
    "text_directions_present": ["ltr"],
    "text_scope_detection_method": "vlm_contact_sheet_review",
}

# Group 14 contains handwritten Chinese notes with hand-drawn diagrams.
# This is an exception to the KI-004 assumption (synthetic = no handwriting).
# The source documents in group 14 include scanned handwritten pages that
# were then synthetically distorted.
HANDWRITING_GROUPS = {"14"}


def extract_distortion_group(original_path: str) -> str | None:
    """Extract distortion group number from original_path.

    Format: 'distorted_hard/{group}/{filename}.jpg'
    """
    parts = original_path.split("/")
    if len(parts) >= 3 and parts[0] == "distorted_hard":
        return parts[1]
    return None


def main() -> None:
    """Apply P1 VLM-informed enrichment to docalign12k metadata."""
    parser = argparse.ArgumentParser(
        description="P1: VLM-informed enrichment for docalign12k"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing",
    )
    args = parser.parse_args()

    # Load metadata
    log.info("Loading metadata from %s", METADATA_PATH)
    t0 = time.monotonic()
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    samples = metadata.get("samples", [])
    log.info("Loaded %d samples in %.1fs", len(samples), time.monotonic() - t0)

    # Process samples
    stats: Counter[str] = Counter()

    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        group = extract_distortion_group(original_path)

        # Find the latest enrichment version
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            stats["skip_no_enrichment"] += 1
            continue

        latest = versions[-1]
        data = latest.get("data", {})

        # Apply enrichment values
        for key, value in ENRICHMENT_VALUES.items():
            old_val = data.get(key)
            data[key] = value
            if old_val != value:
                stats[f"updated_{key}"] += 1

        # Group 14 handwriting exception (KI-004)
        if group in HANDWRITING_GROUPS:
            data["has_handwriting"] = True
            data["handwriting_present"] = True
            stats["handwriting_flagged"] += 1
        else:
            # Ensure non-group-14 remain False (KI-004: synthetic = no handwriting)
            data["has_handwriting"] = False
            data["handwriting_present"] = False

        # Update detection method metadata
        data["content_flags_source"] = "vlm_contact_sheet+ki_004_override"
        data["content_flags_tier"] = "tier_2_model"

        # Update reliability summary confidence for language/domain
        reliability = data.get("sample_reliability_summary", {})
        if isinstance(reliability, dict):
            field_summary = reliability.get("field_summary", [])
            for field_entry in field_summary:
                if field_entry.get("field") == "language":
                    field_entry["confidence"] = 0.7
                    field_entry["category"] = "soft_label"
                elif field_entry.get("field") == "domain":
                    field_entry["confidence"] = 0.8
                    field_entry["category"] = "soft_label"
            # Update min confidence
            if field_summary:
                min_conf = min(
                    (f.get("confidence", 1.0) for f in field_summary), default=1.0
                )
                reliability["min_confidence"] = min_conf
                min_field = min(field_summary, key=lambda f: f.get("confidence", 1.0))
                reliability["min_confidence_field"] = min_field.get("field", "")

        stats["processed"] += 1
        if group:
            stats[f"group_{group}"] += 1

    # Report
    log.info("--- Results ---")
    log.info("Processed: %d samples", stats.get("processed", 0))
    log.info("Handwriting flagged (group 14): %d", stats.get("handwriting_flagged", 0))
    log.info("")
    log.info("Field updates:")
    for key in sorted(stats):
        if key.startswith("updated_"):
            log.info("  %s: %d", key, stats[key])
    log.info("")
    log.info("Group distribution:")
    for key in sorted(stats):
        if key.startswith("group_"):
            log.info("  %s: %d", key, stats[key])

    if args.dry_run:
        log.info("DRY RUN - no changes written")
        return

    # Write
    log.info("Writing updated metadata to %s", METADATA_PATH)
    t0 = time.monotonic()
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    log.info("Written in %.1fs", time.monotonic() - t0)
    log.info("Done.")


if __name__ == "__main__":
    main()
