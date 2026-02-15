#!/usr/bin/env python3
"""Apply collection-majority domain classifications to muharaf UNK samples.

MUHARAF is a word-level Arabic handwriting dataset with 25,711 word crops
from historical manuscript collections. Each collection (identified by
filename prefix) contains word crops from a set of related documents.

LLM enrichment classified ~50% of samples but left 12,936 as UNK because
the weak model couldn't determine domain from short word-level crops with
insufficient context.

Visual inspection confirms UNK and classified samples come from the same
manuscript pages (e.g., AR51_008 has both UNK and ADM crops). The UNK
status reflects LLM context limitations, not genuine domain ambiguity.

Strategy: For each collection prefix, compute the domain distribution of
already-classified (non-UNK) samples, then assign UNK samples the majority
domain of their collection. Confidence reflects how dominant the majority
domain is within the collection.

Usage::

    python scripts/audit/apply_muharaf_domains.py --dry-run
    python scripts/audit/apply_muharaf_domains.py

"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/muharaf_metadata.json"
)


def _extract_collection(path: str) -> str:
    """Extract collection prefix from filename path.

    Handles two naming patterns:
    - Standard: PREFIX_docid-wordid.png (e.g., AR51_008-11.png)
    - El-Khouri: 2015 5-XX El-Khouri_... (e.g., 2015 5-03 El-Khouri_...)

    Args:
        path: Original path/filename from metadata.

    Returns:
        Collection prefix string.
    """
    if path.startswith("2015"):
        # Historical letters with named collections
        if "El-Khouri" in path:
            return "El-Khouri"
        if "Abou-Rjaily" in path:
            return "Abou-Rjaily"
        return "2015_Other"

    # Standard prefix: letters before first digit or underscore
    match = re.match(r"^([A-Za-z]+)", path)
    if match:
        return match.group(1)
    return "UNKNOWN"


def main() -> int:
    """Apply collection-majority domains to muharaf UNK samples."""
    parser = argparse.ArgumentParser(
        description="Apply collection-majority domain to muharaf UNK samples",
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
        help="Path to muharaf metadata JSON",
    )
    parser.add_argument(
        "--min-classified",
        type=int,
        default=5,
        help="Minimum classified samples in collection to use majority (default: 5)",
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

    # Phase 1: Build collection -> domain distribution from classified samples
    collection_domains: dict[str, Counter[str]] = defaultdict(Counter)
    for sample in samples:
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            continue
        data = versions[-1].get("data", {})
        domain = data.get("domain_level1", "UNK")
        if domain == "UNK":
            continue

        path = sample.get("source", {}).get("original_path", "")
        collection = _extract_collection(path)
        collection_domains[collection][domain] += 1

    # Compute majority domain and confidence for each collection
    collection_majority: dict[str, tuple[str, float]] = {}
    for collection, domain_counts in sorted(collection_domains.items()):
        total = sum(domain_counts.values())
        if total < args.min_classified:
            log.warning(
                "Collection %s has only %d classified samples, skipping",
                collection,
                total,
            )
            continue
        majority_domain, majority_count = domain_counts.most_common(1)[0]
        proportion = majority_count / total
        # Confidence: scale from 0.5 (barely majority) to 0.85 (very dominant)
        confidence = min(0.5 + proportion * 0.4, 0.85)
        collection_majority[collection] = (majority_domain, confidence)
        log.info(
            "  %s: %s (%.0f%% of %d classified) -> conf=%.2f",
            collection,
            majority_domain,
            proportion * 100,
            total,
            confidence,
        )

    # Phase 2: Apply majority domain to UNK samples
    updated = 0
    still_unk = 0
    new_domain_counts: Counter[str] = Counter()

    for sample in samples:
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            continue
        data = versions[-1].get("data", {})
        domain = data.get("domain_level1", "UNK")

        if domain != "UNK":
            new_domain_counts[domain] += 1
            continue

        path = sample.get("source", {}).get("original_path", "")
        collection = _extract_collection(path)

        if collection in collection_majority:
            maj_domain, conf = collection_majority[collection]
            new_domain_counts[maj_domain] += 1

            if not args.dry_run:
                data["domain_level1"] = maj_domain
                data["domain_confidence"] = round(conf, 2)
                data["domain_detection_method"] = "collection_majority_propagation"
                updated += 1
        else:
            still_unk += 1
            new_domain_counts["UNK"] += 1

    log.info("After update domain distribution:")
    for domain, count in new_domain_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            domain,
            count,
            100 * count / len(samples),
        )

    unk_pct = 100 * new_domain_counts.get("UNK", 0) / len(samples)
    log.info("Remaining UNK: %d (%.1f%%)", still_unk, unk_pct)

    if args.dry_run:
        log.info("Dry run - no changes written")
    else:
        with open(args.metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Updated %d UNK samples in %s", updated, args.metadata_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
