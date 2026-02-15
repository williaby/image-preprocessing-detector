#!/usr/bin/env python3
"""Apply visually-verified language/script classifications to omnidocbench metadata.

OmniDocBench has 1,358 document images. LLM enrichment classified ~672 (49.5%)
with iso639_language and script_family, leaving 686 unclassified.

Visual inspection of contact sheets (29 sheets across 13 prefix groups) confirms
the language distribution for all missing samples:

Chinese (zh / CJK) groups - 332 samples:
    newspaper (151)           Chinese newspaper pages (农民日报, 科教周刊, etc.)
    notes (116)               Chinese typed/handwritten study notes
    docstructbench_dianzishu (56) Chinese reference ebooks (cooking, engineering)
    exam Chinese subset (9)   Chinese English-exam papers (bilingual, Chinese origin)

English (en / Latin) groups - 354 samples:
    PPT (92)                  English presentation slides (Cambridge, Leeds, calculus)
    docstructbench_scihub (89) English scientific papers (chemistry, physics, biology)
    exam Putnam subset (61)   English Putnam math competition papers
    color (42)                English elementary school textbooks / ESL materials
    magazine (42)             The Economist magazine pages
    docstructbench_the_eye (14) English technical docs (RPG, Excel, screen printing)
    docstructbench_enbook (10) English reference books (trading, pharma, math)
    show (2)                  English dataset overview montages
    data (1)                  English dataset documentation figure
    docstructbench_academic (1) English medical journal paper

Usage::

    python scripts/audit/apply_omnidocbench_languages.py --dry-run
    python scripts/audit/apply_omnidocbench_languages.py

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

# Chinese (zh / CJK) prefix rules - checked BEFORE English defaults
ZH_PREFIXES: list[str] = [
    "newspaper_",
    "notes_",
    "docstructbench_dianzishu",
]

# Chinese exam filenames contain Chinese characters in these patterns
ZH_EXAM_MARKERS: list[str] = [
    "上海高考",
    "安徽省",
    "广西",
    "中考",
]

# English (en / Latin) prefix rules
EN_PREFIXES: list[str] = [
    "PPT_",
    "docstructbench_llm-raw-scihub",
    "docstructbench_llm-raw-the-eye",
    "docstructbench_enbook",
    "docstructbench_00",  # academic paper with DOI-like ID
    "color_",
    "magazine_",
    "show_",
    "data_",
]

# Exam English: putnam or en-file
EN_EXAM_MARKERS: list[str] = [
    "putnam",
    "en-file",
]


def classify_language(filename: str) -> tuple[str, str, float, str]:
    """Classify language and script for an omnidocbench sample.

    Args:
        filename: Original filename from metadata.

    Returns:
        Tuple of (iso639_language, script_family, confidence, method).
    """
    # Chinese prefix groups
    for prefix in ZH_PREFIXES:
        if filename.startswith(prefix):
            return ("zh", "cjk", 0.90, f"visual_review_prefix_{prefix.rstrip('_')}")

    # Exam papers: split by Chinese exam markers vs Putnam/English
    if filename.startswith("exam"):
        for marker in ZH_EXAM_MARKERS:
            if marker in filename:
                return ("zh", "cjk", 0.80, "visual_review_zh_exam_paper")
        for marker in EN_EXAM_MARKERS:
            if marker in filename.lower():
                return ("en", "latin", 0.85, "visual_review_en_putnam_exam")
        # Fallback for unrecognized exam
        return ("en", "latin", 0.60, "visual_review_exam_fallback")

    # English prefix groups
    for prefix in EN_PREFIXES:
        if filename.startswith(prefix):
            return ("en", "latin", 0.85, f"visual_review_prefix_{prefix.rstrip('_')}")

    return ("", "", 0.0, "unclassified")


def main() -> int:
    """Apply language/script classifications to omnidocbench metadata."""
    parser = argparse.ArgumentParser(
        description="Apply language/script classifications to omnidocbench metadata",
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
    log.info("Total samples: %d", len(samples))

    lang_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    updated = 0
    already_classified = 0
    unclassified = 0

    for sample in samples:
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            continue
        data = versions[-1].get("data", {})

        # Skip already-classified samples
        existing_lang = data.get("iso639_language", "")
        if existing_lang and existing_lang != "UNK":
            already_classified += 1
            lang_counts[existing_lang] += 1
            continue

        filename = sample.get("source", {}).get("original_filename", "")
        lang, script, confidence, method = classify_language(filename)

        if not lang:
            unclassified += 1
            lang_counts["UNK"] += 1
            log.warning("Unclassified: %s", filename[:80])
            continue

        lang_counts[lang] += 1
        method_counts[method] += 1

        if not args.dry_run:
            data["iso639_language"] = lang
            data["script_family"] = script
            data["language_confidence"] = confidence
            data["language_detection_method"] = f"visual_contact_sheet_review_{method}"
            updated += 1

    log.info("Language distribution (including previously classified):")
    for lang, count in lang_counts.most_common():
        log.info(
            "  %s: %d (%.1f%%)",
            lang,
            count,
            100 * count / len(samples),
        )

    log.info("Classification method distribution (new only):")
    for method, count in method_counts.most_common():
        log.info("  %s: %d", method, count)

    log.info(
        "Already classified: %d, New classifications: %d, Still unclassified: %d",
        already_classified,
        sum(method_counts.values()),
        unclassified,
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
