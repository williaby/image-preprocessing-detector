#!/usr/bin/env python3
"""Apply visually-verified domain classifications to arabic-docs-ocr Layer 2 metadata.

The arabic-docs-ocr dataset contains 8,203 camera-captured Arabic document images
organized into 12 categories by document type in the filesystem path structure:
    Documents/Documents/{category}/img/{filename}

Domain classifications were determined by visual inspection of contact sheet
montages for all 12 categories (~56 sheets per category, 15 images per sheet).

Category -> Domain mapping (visually verified):
    Administrative form (643)  -> ADM   Bureaucratic forms, UNHCR docs, registration
    Book (652)                 -> EDU   Textbooks, novels, language/literature books
    Business card (609)        -> ADM   Shop, restaurant, doctor, service cards
    Comics (712)               -> PER   Arabic children's comics, illustrated stories
    Handwritten text (710)     -> PER   Personal notes, letters, some study notes
    Invoice (661)              -> FIN   Itemized financial invoices
    Label (662)                -> ADM   Product packaging, price tags, store signage
    Magazine (742)             -> NEWS  Arabic celebrity/culture magazines
    Map (689)                  -> EDU   Educational geographic reference maps
    Newspaper (731)            -> NEWS  Arabic newspaper pages with headlines
    Official document (693)    -> LEG   Government IDs, passports, certificates
    Receipt (699)              -> FIN   Restaurant/store purchase receipts

Usage::

    python scripts/audit/apply_arabic_docs_domains.py --dry-run
    python scripts/audit/apply_arabic_docs_domains.py

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
    "/mnt/e/image_detection/metadata_registry/json/arabic_docs_ocr_metadata.json"
)

# Category -> (domain, confidence) mapping from visual review of contact sheets
CATEGORY_DOMAIN_MAP: dict[str, tuple[str, float]] = {
    "Administrative form": ("ADM", 0.90),
    "Book": ("EDU", 0.80),
    "Business card": ("ADM", 0.85),
    "Comics": ("PER", 0.85),
    "Handwritten text": ("PER", 0.80),
    "Invoice": ("FIN", 0.90),
    "Label": ("ADM", 0.80),
    "Magazine": ("NEWS", 0.90),
    "Map": ("EDU", 0.90),
    "Newspaper": ("NEWS", 0.95),
    "Official document": ("LEG", 0.90),
    "Receipt": ("FIN", 0.90),
}


def classify_from_path(original_path: str) -> tuple[str, float]:
    """Extract category from path and return (domain, confidence).

    Path format: Documents/Documents/{category}/img/{filename}

    Args:
        original_path: The original_path field from metadata source.

    Returns:
        Tuple of (domain_code, confidence). Returns ("UNK", 0.0) if
        category cannot be determined.
    """
    parts = original_path.split("/")
    if len(parts) >= 3:
        category = parts[2]
        if category in CATEGORY_DOMAIN_MAP:
            return CATEGORY_DOMAIN_MAP[category]
    return ("UNK", 0.0)


def main() -> int:
    """Apply domain classifications to arabic-docs-ocr metadata."""
    parser = argparse.ArgumentParser(
        description="Apply visual domain classifications to arabic-docs-ocr L2 metadata",
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
        help="Path to arabic_docs_ocr metadata JSON",
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
    category_counts: Counter[str] = Counter()
    updated = 0
    unmatched: list[str] = []

    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        if not original_path:
            unmatched.append("<no path>")
            domain_counts["UNK"] += 1
            continue

        # Extract category for reporting
        parts = original_path.split("/")
        if len(parts) >= 3:
            category_counts[parts[2]] += 1

        domain, confidence = classify_from_path(original_path)
        domain_counts[domain] += 1

        if domain == "UNK":
            unmatched.append(original_path)
            continue

        if not args.dry_run:
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if versions:
                latest_data = versions[-1].get("data", {})
                latest_data["domain_level1"] = domain
                latest_data["domain_confidence"] = confidence
                latest_data["domain_detection_method"] = (
                    "visual_contact_sheet_review_category_path"
                )
                updated += 1

    log.info("Category distribution:")
    for cat, count in category_counts.most_common():
        domain, conf = CATEGORY_DOMAIN_MAP.get(cat, ("UNK", 0.0))
        log.info(
            "  %s: %d -> %s (%.0f%% conf)",
            cat,
            count,
            domain,
            conf * 100,
        )

    log.info("Domain distribution:")
    for domain, count in domain_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            domain,
            count,
            100 * count / len(samples),
        )

    if unmatched:
        log.warning(
            "%d unmatched paths (first 10): %s",
            len(unmatched),
            unmatched[:10],
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
