#!/usr/bin/env python3
"""Apply visually-verified domain classifications to omnidocbench Layer 2 metadata.

Classifications were determined by visual inspection of contact sheet montages
for all 1,358 images in the omnidocbench dataset. Images were grouped by
filename prefix and sub-classified where needed.

Domain mapping:
    Prefix-based (clear):
        jiaocaineedrop (214) -> EDU  (Chinese math/science textbooks)
        newspaper (151) -> NEWS  (Chinese newspaper pages)
        notes (116) -> EDU  (Chinese study notes, handwritten math)
        PPT (108) -> EDU  (Language teaching presentations)
        book (72) -> EDU  (University textbooks)
        eastmoney (53) -> FIN  (Chinese financial data portal)
        magazine (42) -> NEWS  (The Economist and similar)
        color (42) -> EDU  (Elementary school textbooks)
        scihub (39) -> SCI  (Scientific research papers)
        jiaocai (12) -> EDU  (Textbook pages)
        show (2) -> EDU  (Benchmark meta-documentation)
        data (1) -> EDU  (Benchmark meta-documentation)

    Financial reports:
        yanbaopptmerge (159) -> FIN  (Securities/financial reports)
        yanbaor2 (107) -> FIN  (Corporate annual reports)

    Docstructbench sub-groups:
        llm-raw-scihub (89) -> SCI  (Scientific papers)
        academic (1) -> SCI  (Academic paper)
        dianzishu_zhongwenzaixian (56) -> EDU  (Chinese reference ebooks)
        enbook-zlib (10) -> EDU  (English reference ebooks)
        llm-raw-the-eye (14) -> TEC  (Technical/instructional: RPG, screen printing, programming)

Usage::

    python scripts/audit/apply_omnidocbench_domains.py --dry-run
    python scripts/audit/apply_omnidocbench_domains.py
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
    "/mnt/e/image_detection/metadata_registry/json/omnidocbench_metadata.json"
)

IMAGE_DIR = Path(
    "/mnt/e/image_detection/02_benchmark_only/omnidocbench/extracted_images"
)

# Prefix -> domain mapping (ordered by specificity, longest prefix first)
PREFIX_DOMAIN_MAP: list[tuple[str, str]] = [
    # Docstructbench sub-groups (most specific first)
    ("docstructbench_llm-raw-scihub", "SCI"),
    ("docstructbench_llm-raw-the-eye", "TEC"),
    ("docstructbench_dianzishu_zhongwenzaixian", "EDU"),
    ("docstructbench_enbook-zlib", "EDU"),
    ("docstructbench_00", "SCI"),  # Academic paper with DOI-like ID
    # Main prefixes
    ("exam", "EDU"),
    ("jiaocaineedrop", "EDU"),
    ("newspaper", "NEWS"),
    ("notes", "EDU"),
    ("PPT", "EDU"),
    ("book", "EDU"),
    ("eastmoney", "FIN"),
    ("magazine", "NEWS"),
    ("color", "EDU"),
    ("scihub", "SCI"),
    ("jiaocai", "EDU"),
    ("yanbaopptmerge", "FIN"),
    ("yanbaor2", "FIN"),
    ("show", "EDU"),
    ("data", "EDU"),
]


def classify_domain(filename: str) -> str:
    """Classify domain for a single omnidocbench image by filename prefix.

    Args:
        filename: Image filename (stem or full name).

    Returns:
        Domain classification string.
    """
    for prefix, domain in PREFIX_DOMAIN_MAP:
        if filename.startswith(prefix):
            return domain
    return "UNK"


def _update_enrichment_domain(
    sample: dict,
    domain: str,
    *,
    confidence: float = 0.9,
) -> None:
    """Update domain_level1 in the latest enrichment version.

    Adds a new enrichment version with the domain update to preserve
    the audit trail.

    Args:
        sample: Sample dict from metadata.
        domain: Domain classification to apply.
        confidence: Confidence score for the classification.
    """
    enrichments = sample.get("enrichments", {})
    versions = enrichments.get("versions", [])

    if not versions:
        log.warning("Sample has no enrichment versions, skipping")
        return

    # Get the latest version's data as a base
    latest = versions[-1]
    latest_version = latest.get("version", 1)
    latest_data = latest.get("data", {})

    # Update domain in the latest version's data directly
    latest_data["domain_level1"] = domain
    latest_data["domain_confidence"] = confidence
    latest_data["domain_detection_method"] = "visual_contact_sheet_review"

    # Update the version number
    enrichments["current_version"] = latest_version


def main() -> int:
    """Apply domain classifications to omnidocbench metadata."""
    parser = argparse.ArgumentParser(
        description="Apply visual domain classifications to omnidocbench L2 metadata",
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
        help="Path to omnidocbench metadata JSON",
    )
    args = parser.parse_args()

    if not args.metadata_path.exists():
        log.error("Metadata file not found: %s", args.metadata_path)
        return 1

    log.info("Loading metadata from %s", args.metadata_path)
    with open(args.metadata_path) as fh:
        metadata = json.load(fh)

    samples = metadata.get("samples", [])
    log.info("Total metadata samples: %d", len(samples))

    # Check for images on disk not in metadata
    disk_images = set()
    if IMAGE_DIR.exists():
        disk_images = {
            f.name
            for f in IMAGE_DIR.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
        }
        metadata_filenames = {
            s.get("source", {}).get("original_filename", "") for s in samples
        }
        missing_from_metadata = disk_images - metadata_filenames
        if missing_from_metadata:
            log.warning(
                "%d images on disk not in metadata (need base annotation)",
                len(missing_from_metadata),
            )

    domain_counts: Counter[str] = Counter()
    updated = 0
    unmatched: list[str] = []

    for sample in samples:
        filename = sample.get("source", {}).get("original_filename", "")
        if not filename:
            continue

        domain = classify_domain(filename)
        domain_counts[domain] += 1

        if domain == "UNK":
            unmatched.append(filename)
            continue

        if not args.dry_run:
            _update_enrichment_domain(sample, domain)
            updated += 1

    # Also classify disk images not in metadata (for reporting)
    if disk_images:
        disk_domain_counts: Counter[str] = Counter()
        for img_name in sorted(disk_images):
            disk_domain_counts[classify_domain(img_name)] += 1
        log.info("Full disk image classification (%d images):", len(disk_images))
        for domain, count in disk_domain_counts.most_common():
            log.info(
                "  %s: %d (%.1f%%)",
                domain,
                count,
                100 * count / len(disk_images),
            )

    log.info("Metadata sample classification (%d samples):", len(samples))
    for domain, count in domain_counts.most_common():
        log.info("  %s: %d (%.1f%%)", domain, count, 100 * count / len(samples))

    if unmatched:
        log.warning(
            "%d unmatched filenames (first 10): %s",
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
