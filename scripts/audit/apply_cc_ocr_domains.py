#!/usr/bin/env python3
"""Apply visually-verified domain classifications to cc-ocr Layer 2 metadata.

CC-OCR is a comprehensive Chinese-centric OCR benchmark with 4 tracks:

1. doc_parsing (230): Scientific tables, benchmark results, molecular structures
   -> SCI (scientific/technical content dominates)

2. kie (2,008): Key Information Extraction - diverse document types:
   - Chinese receipts/invoices (numeric filenames, 600) -> FIN
   - Business invoices (X prefix, 347) -> FIN
   - English commercial invoices (eng prefix, 120) -> FIN
   - Hotel invoices (hot prefix, 40) -> FIN
   - Exam papers (img prefix, 311) -> EDU
   - Test papers (test prefix, 100) -> EDU
   - Medical receipts/hospital (med prefix, 240) -> MED
   - UK nutritional labels (UK prefix, 94) -> ADM
   - NZ nutritional labels (NZL prefix, 52) -> ADM
   - Singapore nutritional labels (SGP prefix, 36) -> ADM
   - Nutrition facts (GOG prefix, 21) -> ADM
   - Nutrition facts (nf prefix, 47) -> ADM

3. multi_lan_ocr (1,496): Scene text in 10 languages (Arabic, French, German,
   Italian, Japanese, Korean, Portuguese, Russian, Spanish, Vietnamese)
   -> PER (everyday signage, product labels, street photos)

4. multi_scene_ocr (2,550): Diverse scene text, store signage, brand logos
   -> PER (commercial/everyday scene text)
   Minor exceptions: doc_jinhuodan (14) -> FIN, doc_sifa (28) -> ADM

Usage::

    python scripts/audit/apply_cc_ocr_domains.py --dry-run
    python scripts/audit/apply_cc_ocr_domains.py

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
    "/mnt/e/image_detection/metadata_registry/json/cc_ocr_metadata.json"
)

# KIE prefix -> (domain, confidence), ordered by specificity (longest first)
KIE_PREFIX_MAP: list[tuple[str, str, float]] = [
    # Nutritional label prefixes
    ("GOG_", "ADM", 0.85),
    ("NZL_", "ADM", 0.85),
    ("SGP_", "ADM", 0.85),
    ("UK_", "ADM", 0.85),
    ("nf", "ADM", 0.85),
    # Document types
    ("med-", "MED", 0.90),
    ("eng-", "FIN", 0.90),
    ("hot-", "FIN", 0.85),
    ("img_", "EDU", 0.85),
    ("test_", "EDU", 0.85),
    # Business invoices
    ("X", "FIN", 0.85),
]

# multi_scene_ocr prefix exceptions
SCENE_PREFIX_MAP: list[tuple[str, str, float]] = [
    ("doc_jinhuodan", "FIN", 0.80),
    ("doc_sifa", "ADM", 0.80),
]


def classify_cc_ocr(track: str, filename: str) -> tuple[str, float]:
    """Classify domain for a CC-OCR sample.

    Args:
        track: Track directory (doc_parsing, kie, multi_lan_ocr, multi_scene_ocr).
        filename: Image filename.

    Returns:
        Tuple of (domain_code, confidence).
    """
    if track == "doc_parsing":
        return ("SCI", 0.80)

    if track == "kie":
        for prefix, domain, conf in KIE_PREFIX_MAP:
            if filename.startswith(prefix):
                return (domain, conf)
        # Default for numeric filenames (Chinese receipts/invoices)
        if filename[0].isdigit():
            return ("FIN", 0.85)
        return ("FIN", 0.70)  # fallback for remaining KIE

    if track == "multi_lan_ocr":
        return ("PER", 0.75)

    if track == "multi_scene_ocr":
        for prefix, domain, conf in SCENE_PREFIX_MAP:
            if filename.startswith(prefix):
                return (domain, conf)
        return ("PER", 0.75)

    return ("UNK", 0.0)


def main() -> int:
    """Apply domain classifications to cc-ocr metadata."""
    parser = argparse.ArgumentParser(
        description="Apply visual domain classifications to cc-ocr L2 metadata",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show classification counts without modifying metadata",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=METADATA_PATH,
        help="Path to cc_ocr metadata JSON",
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

    domain_counts: Counter[str] = Counter()
    track_domain: dict[str, Counter[str]] = {}
    updated = 0

    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        filename = sample.get("source", {}).get("original_filename", "")
        track = original_path.split("/")[0] if "/" in original_path else ""

        domain, confidence = classify_cc_ocr(track, filename)
        domain_counts[domain] += 1

        if track not in track_domain:
            track_domain[track] = Counter()
        track_domain[track][domain] += 1

        if domain != "UNK" and not args.dry_run:
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if versions:
                latest_data = versions[-1].get("data", {})
                latest_data["domain_level1"] = domain
                latest_data["domain_confidence"] = confidence
                latest_data["domain_detection_method"] = (
                    "visual_contact_sheet_review_track_prefix"
                )
                updated += 1

    log.info("Per-track domain distribution:")
    for track in sorted(track_domain):
        track_total = sum(track_domain[track].values())
        log.info("  %s (%d samples):", track, track_total)
        for domain, count in track_domain[track].most_common():
            log.info(
                "    %s: %d (%.1f%%)",
                domain,
                count,
                100 * count / track_total,
            )

    log.info("Overall domain distribution:")
    for domain, count in domain_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            domain,
            count,
            100 * count / len(samples),
        )

    if args.dry_run:
        log.info("Dry run - no changes written")
    else:
        with open(args.metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Updated %d samples in %s", updated, args.metadata_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
