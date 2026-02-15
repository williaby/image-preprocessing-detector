#!/usr/bin/env python3
"""Apply domain classifications to mdiw13 Layer 2 metadata.

MDIW-13 (Multiscript Document Image Words in 13 scripts) contains 290,213
word/line/document crops from printed and handwritten sources in 13 scripts
(Arabic, Bangla, Gujrati, Gurmukhi, Hindi, Japanese, Kannada, Malayalam,
Oriya, Roman, Tamil, Telugu, Thai).

The dataset has two major subsets:

1. SIW_MultiscriptDatabase (~203K samples):
   - MultiscriptPrintedWords/Lines/Documents + Original variants
   - MultiscriptHandwrittenWords/Lines/Documents + Original variants
   Path structure explicitly contains "Printed" or "Handwritten".

2. ICDAR_SIW_Competition (~87K samples):
   - TrainCompetition_WITHGroundTruth (~31K): Has printed/ and handwritten/
     subdirectories in the path.
   - TestCompetition_WITHOUTGroundTruth (~56K): Uses positional lookup from
     TestCompeititionTasks.txt (0=handwritten, 1=printed).

Domain mapping (from visual inspection of contact sheets for all 1,135
document-level images across 13 scripts):
    - Printed: NEWS (newspaper/magazine article word crops) - confidence 0.85
    - Handwritten: PER (personal writing, notes, essays) - confidence 0.80

Usage::

    python scripts/audit/apply_mdiw13_domains.py --dry-run
    python scripts/audit/apply_mdiw13_domains.py

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
    "/mnt/e/image_detection/metadata_registry/json/mdiw13_metadata.json"
)

TASK_FILE_PATH = Path(
    "/mnt/e/image_detection/01_base_data/language/mdiw13/"
    "SIW_Database/ICDAR_SIW_Competition/TestCompeititionTasks.txt"
)

# Domain mappings from visual inspection of contact sheets
PRINTED_DOMAIN = "NEWS"
PRINTED_CONFIDENCE = 0.85
HANDWRITTEN_DOMAIN = "PER"
HANDWRITTEN_CONFIDENCE = 0.80


def _load_competition_task_labels(task_path: Path) -> dict[int, int]:
    """Load competition task labels (positional: line N -> sample N+1).

    The file has one value per line: 0=handwritten, 1=printed.
    Line index 0 corresponds to sample000001.png.

    Args:
        task_path: Path to TestCompeititionTasks.txt.

    Returns:
        Dict mapping 1-based sample number to task label (0 or 1).
    """
    labels: dict[int, int] = {}
    with open(task_path) as fh:
        for idx, line in enumerate(fh):
            val = line.strip()
            if val in ("0", "1"):
                labels[idx + 1] = int(val)
    return labels


def _classify_sample(
    original_path: str,
    task_labels: dict[int, int],
) -> tuple[str, float, str]:
    """Classify a single mdiw13 sample by path and competition labels.

    Args:
        original_path: The original_path field from metadata source.
        task_labels: Competition task labels (sample_num -> 0/1).

    Returns:
        Tuple of (domain, confidence, method).
    """
    # SIW_MultiscriptDatabase: path contains Printed or Handwritten
    if "Printed" in original_path:
        return (PRINTED_DOMAIN, PRINTED_CONFIDENCE, "path_printed_keyword")
    if "Handwritten" in original_path:
        return (
            HANDWRITTEN_DOMAIN,
            HANDWRITTEN_CONFIDENCE,
            "path_handwritten_keyword",
        )

    # Competition training: has printed/ or handwritten/ subdirectory
    if "TrainCompetition" in original_path:
        if "/printed/" in original_path:
            return (PRINTED_DOMAIN, 0.80, "competition_train_printed_subdir")
        if "/handwritten/" in original_path:
            return (
                HANDWRITTEN_DOMAIN,
                0.80,
                "competition_train_handwritten_subdir",
            )

    # Competition test: positional lookup from task file
    if "TestCompetition" in original_path:
        # Extract sample number from filename like sample000001.png
        filename = original_path.rsplit("/", 1)[-1]
        if filename.startswith("sample"):
            try:
                sample_num = int(filename[6:].split(".")[0])
                task_label = task_labels.get(sample_num)
                if task_label == 1:
                    return (
                        PRINTED_DOMAIN,
                        0.80,
                        "competition_task_label_printed",
                    )
                if task_label == 0:
                    return (
                        HANDWRITTEN_DOMAIN,
                        0.80,
                        "competition_task_label_handwritten",
                    )
            except ValueError:
                pass

    return ("UNK", 0.0, "unclassified")


def main() -> int:
    """Apply domain classifications to mdiw13 metadata."""
    parser = argparse.ArgumentParser(
        description="Apply domain classifications to mdiw13 L2 metadata",
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
        help="Path to mdiw13 metadata JSON",
    )
    parser.add_argument(
        "--task-file",
        type=Path,
        default=TASK_FILE_PATH,
        help="Path to TestCompeititionTasks.txt for competition test labels",
    )
    args = parser.parse_args()

    if not args.metadata_path.exists():
        log.error("Metadata file not found: %s", args.metadata_path)
        return 1

    # Load competition task labels
    task_labels: dict[int, int] = {}
    if args.task_file.exists():
        task_labels = _load_competition_task_labels(args.task_file)
        log.info(
            "Loaded %d competition task labels (printed=%d, handwritten=%d)",
            len(task_labels),
            sum(1 for v in task_labels.values() if v == 1),
            sum(1 for v in task_labels.values() if v == 0),
        )
    else:
        log.warning(
            "Task file not found: %s (competition test samples will be UNK)",
            args.task_file,
        )

    log.info("Loading metadata from %s", args.metadata_path)
    with open(args.metadata_path) as fh:
        metadata = json.load(fh)

    samples = metadata.get("samples", [])
    log.info("Total samples: %d", len(samples))

    domain_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    updated = 0

    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        domain, confidence, method = _classify_sample(original_path, task_labels)
        domain_counts[domain] += 1
        method_counts[method] += 1

        if domain != "UNK" and not args.dry_run:
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if versions:
                latest_data = versions[-1].get("data", {})
                latest_data["domain_level1"] = domain
                latest_data["domain_confidence"] = confidence
                latest_data["domain_detection_method"] = (
                    f"visual_contact_sheet_review_{method}"
                )
                updated += 1

    log.info("Domain distribution:")
    for domain, count in domain_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            domain,
            count,
            100 * count / len(samples),
        )

    log.info("Classification method distribution:")
    for method, count in method_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            method,
            count,
            100 * count / len(samples),
        )

    unk_count = domain_counts.get("UNK", 0)
    if unk_count > 0:
        log.warning(
            "Remaining UNK: %d (%.1f%%)", unk_count, 100 * unk_count / len(samples)
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
