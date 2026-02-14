#!/usr/bin/env python3
"""Extract DocLayNet GT JSON index for integration.

Reads all 81,471 GT JSON files and produces a single index with:
- doc_category -> domain_level1 mapping
- cells text -> langdetect language detection
- text_statistics from concatenated cell text
- COCO GT split membership

Output: results/doclaynet_gt_index.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GT_JSON_DIR = Path("/mnt/e/image_detection/01_base_data/documents/doclaynet/ground_truth/json")
COCO_GT_DIR = Path("/mnt/e/image_detection/01_base_data/documents/doclaynet/ground_truth/coco")
OUTPUT_PATH = Path("results/doclaynet_gt_index.json")

DOC_CATEGORY_TO_DOMAIN: dict[str, str] = {
    "financial_reports": "FIN",
    "scientific_articles": "SCI",
    "laws_and_regulations": "LEG",
    "government_tenders": "ADM",
    "manuals": "TEC",
    "patents": "TEC",
}

# Unicode ranges for script direction detection
_ARABIC_RANGES = set(range(0x0600, 0x0700)) | set(range(0x0750, 0x0780)) | set(range(0xFB50, 0xFE00)) | set(range(0xFE70, 0xFF00))
_HEBREW_RANGES = set(range(0x0590, 0x0600)) | set(range(0xFB1D, 0xFB50))


def _has_rtl_chars(text: str) -> bool:
    """Check if text contains Arabic or Hebrew characters."""
    for ch in text:
        cp = ord(ch)
        if cp in _ARABIC_RANGES or cp in _HEBREW_RANGES:
            return True
    return False


def _compute_text_statistics(text: str) -> dict:
    """Compute text statistics from concatenated cell text."""
    lines = text.split("\n") if "\n" in text else [text]
    words = text.split()
    return {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "has_content": len(text.strip()) > 0,
        "avg_line_length": round(len(text) / max(len(lines), 1), 1),
    }


def _detect_language(text: str) -> tuple[str, float]:
    """Detect language using langdetect. Returns (iso639_code, confidence)."""
    if len(text.strip()) < 20:
        return ("und", 0.1)
    try:
        import langdetect
        langdetect.DetectorFactory.seed = 42
        results = langdetect.detect_langs(text)
        if results:
            return (results[0].lang, round(results[0].prob, 3))
    except Exception:
        pass
    return ("und", 0.1)


def _script_from_language(lang_code: str) -> str:
    """Map ISO 639-1 language code to ISO 15924 script code."""
    mapping: dict[str, str] = {
        "en": "Latn", "de": "Latn", "fr": "Latn", "es": "Latn", "it": "Latn",
        "pt": "Latn", "nl": "Latn", "pl": "Latn", "sv": "Latn", "da": "Latn",
        "no": "Latn", "fi": "Latn", "ro": "Latn", "cs": "Latn", "hu": "Latn",
        "tr": "Latn", "vi": "Latn", "id": "Latn", "ms": "Latn",
        "ja": "Jpan", "zh-cn": "Hans", "zh-tw": "Hant", "ko": "Kore",
        "ru": "Cyrl", "uk": "Cyrl", "bg": "Cyrl", "sr": "Cyrl",
        "ar": "Arab", "fa": "Arab", "ur": "Arab",
        "he": "Hebr", "hi": "Deva", "th": "Thai", "el": "Grek",
    }
    return mapping.get(lang_code, "Latn")


def _direction_from_script(script_code: str) -> str:
    """Map ISO 15924 script to text direction."""
    rtl_scripts = {"Arab", "Hebr", "Thaa", "Syrc"}
    return "rtl" if script_code in rtl_scripts else "ltr"


def process_gt_json(filepath: str) -> dict | None:
    """Process a single GT JSON file. Returns extracted data or None."""
    try:
        with open(filepath) as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        cells = data.get("cells", [])

        stem = Path(filepath).stem
        doc_category = metadata.get("doc_category", "")
        collection = metadata.get("collection", "")

        sorted_cells = sorted(cells, key=lambda c: (c["bbox"][1], c["bbox"][0]))
        full_text = " ".join(
            cell["text"] for cell in sorted_cells if cell.get("text")
        )

        lang_code, lang_conf = _detect_language(full_text)
        script_code = _script_from_language(lang_code)
        text_dir = _direction_from_script(script_code)
        has_rtl = _has_rtl_chars(full_text)
        directions = ["ltr"]
        if has_rtl:
            directions = ["ltr", "rtl"] if text_dir == "ltr" else ["rtl", "ltr"]
        elif text_dir == "rtl":
            directions = ["rtl"]

        return {
            "image_id": stem,
            "doc_category": doc_category,
            "domain_level1": DOC_CATEGORY_TO_DOMAIN.get(doc_category, "UNK"),
            "collection": collection,
            "iso639_language": lang_code,
            "language_confidence": lang_conf,
            "iso15924_script": script_code,
            "text_direction": text_dir,
            "text_directions_present": directions,
            "text_statistics": _compute_text_statistics(full_text),
            "cell_count": len(cells),
            "page_no": metadata.get("page_no"),
            "num_pages": metadata.get("num_pages"),
        }
    except Exception as exc:
        log.warning("Failed to process %s: %s", filepath, exc)
        return None


def build_coco_split_index(coco_dir: Path) -> dict[str, str]:
    """Build filename -> split mapping from COCO GT files."""
    split_index: dict[str, str] = {}
    for split_name in ("train", "val", "test"):
        coco_path = coco_dir / f"{split_name}.json"
        if not coco_path.exists():
            log.warning("COCO file not found: %s", coco_path)
            continue
        log.info("Loading COCO %s.json ...", split_name)
        with open(coco_path) as f:
            coco_data = json.load(f)
        for img in coco_data.get("images", []):
            filename = img.get("file_name", "")
            stem = Path(filename).stem
            split_index[stem] = split_name
        log.info("  %s: %d images", split_name, len(coco_data.get("images", [])))
        del coco_data
    return split_index


def build_coco_content_flags(coco_dir: Path) -> dict[str, dict[str, bool]]:
    """Build filename -> content flags from COCO GT annotations."""
    content_index: dict[str, dict[str, bool]] = {}

    for split_name in ("train", "val", "test"):
        coco_path = coco_dir / f"{split_name}.json"
        if not coco_path.exists():
            continue
        log.info("Building content flags from COCO %s.json ...", split_name)
        with open(coco_path) as f:
            coco_data = json.load(f)

        categories = {
            cat["id"]: cat["name"]
            for cat in coco_data.get("categories", [])
        }
        img_id_to_stem: dict[int, str] = {}
        for img in coco_data.get("images", []):
            img_id_to_stem[img["id"]] = Path(img["file_name"]).stem

        img_categories: dict[str, set[str]] = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            stem = img_id_to_stem.get(img_id)
            if stem is None:
                continue
            cat_name = categories.get(ann.get("category_id"), "")
            if stem not in img_categories:
                img_categories[stem] = set()
            img_categories[stem].add(cat_name)

        for stem, cats in img_categories.items():
            content_index[stem] = {
                "has_table": "Table" in cats,
                "has_figure": "Picture" in cats,
                "has_formula": "Formula" in cats,
                "has_handwriting": False,
                "has_code": False,
                "has_signature": False,
            }

        for img in coco_data.get("images", []):
            stem = Path(img["file_name"]).stem
            if stem not in content_index:
                content_index[stem] = {
                    "has_table": False,
                    "has_figure": False,
                    "has_formula": False,
                    "has_handwriting": False,
                    "has_code": False,
                    "has_signature": False,
                }

        del coco_data
    return content_index


def main() -> int:
    """Build GT index for DocLayNet integration."""
    parser = argparse.ArgumentParser(description="Extract DocLayNet GT index")
    parser.add_argument("--gt-dir", type=Path, default=GT_JSON_DIR)
    parser.add_argument("--coco-dir", type=Path, default=COCO_GT_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    gt_dir = args.gt_dir
    if not gt_dir.exists():
        log.error("GT JSON directory not found: %s", gt_dir)
        return 1

    # Step 1: Build COCO split + content flag indexes
    log.info("Step 1: Building COCO GT indexes ...")
    split_index = build_coco_split_index(args.coco_dir)
    content_index = build_coco_content_flags(args.coco_dir)
    log.info("  Split index: %d entries", len(split_index))
    log.info("  Content flag index: %d entries", len(content_index))

    # Step 2: Process GT JSON files
    gt_files = sorted(gt_dir.glob("*.json"))
    log.info("Step 2: Processing %d GT JSON files with %d workers ...", len(gt_files), args.workers)

    results: dict[str, dict] = {}
    lang_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    errors = 0
    start = time.monotonic()

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_gt_json, str(fp)): fp
            for fp in gt_files
        }
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result is None:
                errors += 1
                continue

            image_id = result["image_id"]
            result["split"] = split_index.get(image_id, "unknown")
            result["content_flags"] = content_index.get(image_id, {
                "has_table": False, "has_figure": False, "has_formula": False,
                "has_handwriting": False, "has_code": False, "has_signature": False,
            })
            results[image_id] = result
            lang_counter[result["iso639_language"]] += 1
            domain_counter[result["domain_level1"]] += 1

            if i % 10000 == 0:
                elapsed = time.monotonic() - start
                rate = i / elapsed
                log.info("  Progress: %d/%d (%.0f/sec)", i, len(gt_files), rate)

    elapsed = time.monotonic() - start
    log.info("Step 2 complete: %d results, %d errors in %.1fs (%.0f files/sec)",
             len(results), errors, elapsed, len(gt_files) / elapsed)

    # Step 3: Write output
    output = {
        "dataset": "doclaynet",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "gt_json_dir": str(gt_dir),
        "total_processed": len(results),
        "errors": errors,
        "language_distribution": dict(lang_counter.most_common()),
        "domain_distribution": dict(domain_counter.most_common()),
        "split_distribution": dict(Counter(r["split"] for r in results.values()).most_common()),
        "samples": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    log.info("Step 3: Writing index to %s ...", args.output)
    with open(args.output, "w") as f:
        json.dump(output, f, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 70)
    print(f"  DOCLAYNET GT INDEX EXTRACTION")
    print("=" * 70)
    print(f"  Total processed: {len(results):,}")
    print(f"  Errors: {errors}")
    print(f"  Duration: {elapsed:.1f}s ({len(gt_files) / elapsed:.0f} files/sec)")
    print(f"\n  Language distribution (top 10):")
    for lang, count in lang_counter.most_common(10):
        pct = 100 * count / len(results)
        print(f"    {lang:6s}: {count:6,d} ({pct:.1f}%)")
    print(f"\n  Domain distribution:")
    for domain, count in domain_counter.most_common():
        pct = 100 * count / len(results)
        print(f"    {domain:6s}: {count:6,d} ({pct:.1f}%)")
    print(f"\n  Split distribution:")
    for split, count in Counter(r["split"] for r in results.values()).most_common():
        print(f"    {split:10s}: {count:6,d}")
    print(f"\n  Output: {args.output}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
