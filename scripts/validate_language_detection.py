#!/usr/bin/env python3
"""Validate Language Detection Against Ground Truth.

Uses MLT-19 training samples (which have GT language labels) to validate
the multi-factor language detection accuracy.

This validates the workflow by comparing:
- Detected language from visual analysis (EasyOCR + fastText + lingua)
- Ground truth language from MLT-19 annotations

Usage:
    # Validate on 100 training samples
    uv run python scripts/validate_language_detection.py --samples 100

    # Validate specific languages
    uv run python scripts/validate_language_detection.py --samples 50 --languages ar,zh,ja
"""

import argparse
import json
import logging
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.enrich_language import (
    METADATA_REGISTRY_PATH,
    MODEL_DIR,
    extract_text_easyocr,
    multi_language_consensus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating one sample."""

    image_path: str
    gt_language: str
    detected_language: str
    detected_languages: list[str]
    confidence: float
    method: str
    correct: bool
    extracted_text: str = ""


def load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON file."""
    with open(metadata_path) as f:
        return json.load(f)


def get_training_samples_with_labels(
    metadata: dict[str, Any],
    target_languages: list[str] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Get training samples that have actual language labels (not 'und' or 'mul')."""
    samples = metadata.get("samples", [])
    labeled_samples = []

    for i, sample in enumerate(samples):
        orig_labels = sample.get("original_labels", {})
        lang_code = orig_labels.get("language_code")
        raw_labels = orig_labels.get("raw_labels", {})

        # Only training samples with definite single-language labels
        if (
            raw_labels.get("split") == "train"
            and lang_code
            and lang_code not in ("und", "mul")
        ):
            if target_languages is None or lang_code in target_languages:
                labeled_samples.append((i, sample))

    return labeled_samples


def validate_sample(
    sample: dict[str, Any],
    dataset_path: Path,
    fasttext_model: Any,
    lingua_detector: Any,
    easyocr_readers: dict[str, Any],
    lang_to_reader: dict[str, str],
) -> ValidationResult | None:
    """Validate language detection on a single sample."""
    orig_labels = sample.get("original_labels", {})
    gt_language = orig_labels.get("language_code")
    source = sample.get("source", {})
    orig_path = source.get("original_path", "")

    # Find the image
    image_path = dataset_path / orig_path
    if not image_path.exists():
        logger.debug(f"Image not found: {image_path}")
        return None

    # Extract text using appropriate EasyOCR reader for the GT language
    text = ""
    reader_family = lang_to_reader.get(gt_language, "latin")
    easyocr_reader = easyocr_readers.get(reader_family)
    if easyocr_reader:
        text = extract_text_easyocr(image_path, easyocr_reader)

    if not text:
        return ValidationResult(
            image_path=orig_path,
            gt_language=gt_language,
            detected_language="und",
            detected_languages=[],
            confidence=0.0,
            method="no_text_extracted",
            correct=False,
        )

    # Run multi-language consensus detection
    result = multi_language_consensus(text, fasttext_model, lingua_detector)

    # Check if correct
    # For single-language GT, we consider it correct if:
    # 1. Primary language matches GT, OR
    # 2. GT language is in detected_languages list
    correct = (
        result.primary_language == gt_language
        or gt_language in result.detected_languages
    )

    return ValidationResult(
        image_path=orig_path,
        gt_language=gt_language,
        detected_language=result.primary_language,
        detected_languages=result.detected_languages,
        confidence=result.confidence,
        method=result.method,
        correct=correct,
        extracted_text=text[:200] if text else "",
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate language detection against MLT-19 ground truth"
    )
    parser.add_argument(
        "--samples", type=int, default=50, help="Number of samples to validate"
    )
    parser.add_argument(
        "--languages",
        type=str,
        default=None,
        help="Comma-separated list of languages to validate (e.g., 'ar,zh,ja')",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_REGISTRY_PATH / "mlt19_metadata.json",
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=Path("/mnt/e/image_detection/01_base_data/language/mlt19"),
    )
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    parser.add_argument("--no-ocr", action="store_true", help="Skip OCR")
    parser.add_argument(
        "--ocr-languages",
        type=str,
        default="en,ar,hi,bn,ja,ko,ch_sim",  # Compatible subset
        help="EasyOCR languages (must be compatible - see EasyOCR docs)",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # Parse target languages
    target_languages = None
    if args.languages:
        target_languages = [lang.strip() for lang in args.languages.split(",")]
        logger.info(f"Filtering to languages: {target_languages}")

    # Load metadata
    logger.info(f"Loading metadata from {args.metadata}")
    metadata = load_metadata(args.metadata)

    # Get training samples with labels
    labeled_samples = get_training_samples_with_labels(metadata, target_languages)
    logger.info(f"Found {len(labeled_samples)} training samples with language labels")

    # Sample randomly
    if len(labeled_samples) > args.samples:
        labeled_samples = random.sample(labeled_samples, args.samples)
    logger.info(f"Validating {len(labeled_samples)} samples")

    # Show language distribution
    lang_dist = Counter(
        sample.get("original_labels", {}).get("language_code")
        for _, sample in labeled_samples
    )
    logger.info(f"Language distribution: {dict(lang_dist)}")

    # Initialize detection models
    fasttext_model = None
    lingua_detector = None

    # Load fastText
    try:
        import fasttext

        model_path = args.model_dir / "lid.176.bin"
        if model_path.exists():
            logger.info("Loading fastText model...")
            fasttext_model = fasttext.load_model(str(model_path))
    except ImportError:
        logger.warning("fastText not installed")

    # Load lingua
    try:
        from lingua import LanguageDetectorBuilder

        logger.info("Initializing lingua detector...")
        lingua_detector = LanguageDetectorBuilder.from_all_languages().build()
    except ImportError:
        logger.warning("lingua not installed")

    # Load EasyOCR readers for different script families
    # EasyOCR has strict language compatibility - can't mix certain scripts
    easyocr_readers: dict[str, Any] = {}
    if not args.no_ocr:
        try:
            import easyocr

            # Create readers for different script families
            script_families = {
                "latin": ["en"],  # Latin scripts
                "arabic": ["ar", "en"],  # Arabic + Latin
                "devanagari": ["hi", "en"],  # Hindi + Latin
                "bengali": ["bn", "en"],  # Bengali + Latin
                "cjk": ["ch_sim", "en"],  # Chinese + Latin
                "japanese": ["ja", "en"],  # Japanese + Latin
                "korean": ["ko", "en"],  # Korean + Latin
            }

            for family, langs in script_families.items():
                try:
                    logger.info(f"Initializing EasyOCR for {family}: {langs}")
                    easyocr_readers[family] = easyocr.Reader(langs, gpu=True)
                except Exception as e:
                    logger.warning(f"Could not init {family} reader: {e}")

            # Map GT language codes to reader families
            lang_to_reader = {
                "en": "latin",
                "ar": "arabic",
                "hi": "devanagari",
                "bn": "bengali",
                "zh": "cjk",
                "ja": "japanese",
                "ko": "korean",
            }
        except ImportError:
            logger.warning("EasyOCR not installed")
    else:
        lang_to_reader = {}

    if not easyocr_readers:
        logger.error("EasyOCR required for validation")
        return 1

    # Run validation
    results: list[ValidationResult] = []
    correct_count = 0
    skipped_count = 0

    for idx, (sample_idx, sample) in enumerate(labeled_samples):
        result = validate_sample(
            sample,
            args.dataset_path,
            fasttext_model,
            lingua_detector,
            easyocr_readers,
            lang_to_reader,
        )

        if result is None:
            skipped_count += 1
            continue

        results.append(result)
        if result.correct:
            correct_count += 1

        # Progress
        if (idx + 1) % 10 == 0:
            accuracy = correct_count / len(results) if results else 0
            logger.info(
                f"Progress: {idx + 1}/{len(labeled_samples)} | "
                f"Accuracy: {accuracy * 100:.1f}% ({correct_count}/{len(results)})"
            )

    # Final report
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    total = len(results)
    accuracy = correct_count / total if total > 0 else 0
    print(f"\nOverall Accuracy: {accuracy * 100:.1f}% ({correct_count}/{total})")
    print(f"Skipped (image not found): {skipped_count}")

    # Per-language breakdown
    print("\nPer-Language Accuracy:")
    lang_results: dict[str, list[bool]] = {}
    for r in results:
        lang_results.setdefault(r.gt_language, []).append(r.correct)

    for lang, correct_list in sorted(lang_results.items()):
        lang_acc = sum(correct_list) / len(correct_list)
        print(
            f"  {lang}: {lang_acc * 100:.1f}% ({sum(correct_list)}/{len(correct_list)})"
        )

    # Method breakdown
    print("\nDetection Methods Used:")
    method_counts = Counter(r.method for r in results)
    for method, count in method_counts.most_common():
        method_results = [r.correct for r in results if r.method == method]
        method_acc = sum(method_results) / len(method_results)
        print(f"  {method}: {count} samples, {method_acc * 100:.1f}% accuracy")

    # Show some errors
    errors = [r for r in results if not r.correct]
    if errors:
        print("\nSample Errors (first 10):")
        for r in errors[:10]:
            print(
                f"  GT={r.gt_language}, Detected={r.detected_language} ({r.detected_languages})"
            )
            print(f"    Method: {r.method}, Conf: {r.confidence:.2f}")
            if r.extracted_text:
                print(f"    Text: {r.extracted_text[:80]}...")

    return 0


if __name__ == "__main__":
    exit(main())
