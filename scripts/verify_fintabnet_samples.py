#!/usr/bin/env python3
"""Verify fintabnet very low confidence samples using Qwen paid vision model.

Runs vision-based language detection on samples where text-based detection
had very low confidence to verify they are English/Latin.

Usage:
    PYTHONPATH=. uv run python scripts/verify_fintabnet_samples.py --limit 50
    PYTHONPATH=. uv run python scripts/verify_fintabnet_samples.py --all
"""

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
VERY_LOW_SAMPLES = Path(
    "/mnt/e/image_detection/metadata_registry/triage_analysis/fintabnet_very_low_samples.json"
)
METADATA_FILE = Path(
    "/mnt/e/image_detection/metadata_registry/json/fintabnet_metadata.json"
)
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data/tables/fintabnet")
RESULTS_DIR = Path("/mnt/e/image_detection/metadata_registry/triage_analysis")


def _build_verifiable_samples(very_low: list[dict], metadata: dict) -> list[dict]:
    """Build list of samples that have valid image paths on disk."""
    sample_paths: dict[str, Path] = {}
    for sample in metadata.get("samples", []):
        sample_id = sample.get("id", "")
        rel_path = sample.get("source", {}).get("original_path", "")
        if sample_id and rel_path:
            sample_paths[sample_id] = BASE_DATA_PATH / rel_path

    samples_to_verify = []
    for s in very_low:
        sample_id = s["sample_id"]
        img_path = sample_paths.get(sample_id)
        if img_path is not None and img_path.exists():
            samples_to_verify.append(
                {
                    "sample_id": sample_id,
                    "image_path": img_path,
                    "text_consensus": s["consensus_language"],
                    "text_confidence": s["consensus_confidence"],
                    "text_script": s["primary_script"],
                }
            )
    return samples_to_verify


def _process_vision_result(
    sample: dict, vision_result: dict | None
) -> tuple[dict, str | None, str | None]:
    """Process a single vision detection result into a result dict.

    Returns:
        Tuple of (result_dict, detected_lang, detected_script).
    """
    if not vision_result:
        return (
            {"sample_id": sample["sample_id"], "error": "API call failed"},
            None,
            None,
        )

    lang = vision_result.get("primary_language", "und")
    script = vision_result.get("primary_script", "Unknown")
    confidence = vision_result.get("total_confidence", 0)

    result = {
        "sample_id": sample["sample_id"],
        "text_consensus": sample["text_consensus"],
        "text_script": sample["text_script"],
        "vision_language": lang,
        "vision_script": script,
        "vision_confidence": confidence,
    }
    return result, lang, script


def _print_verification_summary(
    results: list[dict],
    lang_counts: Counter,
    script_counts: Counter,
    english_latin_count: int,
) -> None:
    """Print verification results summary and recommendation."""
    total = len(results)
    successful = sum(1 for r in results if "vision_language" in r)

    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    print(f"\nTotal processed: {total}")
    print(f"Successful: {successful}")
    if successful:
        print(
            f"English + Latin: {english_latin_count} ({100 * english_latin_count / successful:.1f}%)"
        )

    print("\nVision Language Distribution:")
    for lang, count in lang_counts.most_common(10):
        print(f"  {lang}: {count} ({100 * count / successful:.1f}%)")

    print("\nVision Script Distribution:")
    for script, count in script_counts.most_common(10):
        print(f"  {script}: {count} ({100 * count / successful:.1f}%)")

    # Save results
    output_file = RESULTS_DIR / "fintabnet_vision_verification.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "total": total,
                "successful": successful,
                "english_latin_count": english_latin_count,
                "english_latin_pct": 100 * english_latin_count / successful
                if successful
                else 0,
                "language_distribution": dict(lang_counts),
                "script_distribution": dict(script_counts),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\nResults saved to: {output_file}")

    if successful > 0:
        eng_pct = 100 * english_latin_count / successful
        print("\n" + "=" * 60)
        print("RECOMMENDATION")
        print("=" * 60)
        if eng_pct >= 95:
            print(f"English/Latin confirmed at {eng_pct:.1f}%")
            print("SAFE to label entire fintabnet as English (en) / Latin (Latn)")
        elif eng_pct >= 80:
            print(f"English/Latin at {eng_pct:.1f}% - mostly safe")
            print("Consider labeling as English with note about minority cases")
        else:
            print(f"English/Latin only {eng_pct:.1f}% - mixed dataset")
            print("Recommend per-sample labeling")


def main():
    parser = argparse.ArgumentParser(description="Verify fintabnet samples with Qwen")
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of samples to verify"
    )
    parser.add_argument("--all", action="store_true", help="Verify all samples")
    args = parser.parse_args()

    from scripts.language_escalation import detect_via_vision_llm

    with open(VERY_LOW_SAMPLES) as f:
        very_low = json.load(f)

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    samples_to_verify = _build_verifiable_samples(very_low, metadata)
    logger.info(f"Found {len(samples_to_verify)} verifiable samples")

    if not args.all:
        samples_to_verify = samples_to_verify[: args.limit]
        logger.info(f"Processing {len(samples_to_verify)} samples (use --all for full)")

    model = "qwen/qwen-2.5-vl-7b-instruct"
    logger.info(f"Using model: {model}")

    results = []
    lang_counts = Counter()
    script_counts = Counter()
    english_latin_count = 0

    for i, sample in enumerate(samples_to_verify):
        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i + 1}/{len(samples_to_verify)}")

        try:
            vision_result = detect_via_vision_llm(sample["image_path"], model)
            result, lang, script = _process_vision_result(sample, vision_result)
            results.append(result)
            if lang is not None:
                lang_counts[lang] += 1
                script_counts[script] += 1
                if lang == "en" and script in ("Latn", "Latin"):
                    english_latin_count += 1
        except Exception as e:
            logger.warning(f"Error processing {sample['sample_id']}: {e}")
            results.append({"sample_id": sample["sample_id"], "error": str(e)})

        time.sleep(0.1)

    _print_verification_summary(
        results, lang_counts, script_counts, english_latin_count
    )


if __name__ == "__main__":
    main()
