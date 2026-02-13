#!/usr/bin/env python3
"""Validate OpenLID-v2 Against MLT-19 Ground Truth.

Compares OpenLID-v2 language detection accuracy against MLT-19 training samples
which have verified ground truth language labels.

This validates:
1. OpenLID-v2 accuracy vs lid.176.bin (current model)
2. Script detection accuracy (unique to OpenLID-v2)
3. Per-language breakdown to identify weak spots
4. Arabic dialect handling (known weakness)

Usage:
    # Run validation on 100 samples
    uv run python scripts/validate_openlid_mlt19.py --samples 100

    # Validate specific languages
    uv run python scripts/validate_openlid_mlt19.py --samples 50 --languages ar,zh,ja

    # Full validation (all training samples)
    uv run python scripts/validate_openlid_mlt19.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
METADATA_REGISTRY_PATH = Path("/mnt/e/image_detection/metadata_registry/json")
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")
MODEL_DIR = Path("/mnt/e/image_detection/models/language_detection")

# MLT-19 language to expected script mapping
LANG_TO_SCRIPT: dict[str, str] = {
    "ar": "Arab",
    "bn": "Beng",
    "zh": "Hans",  # or Hant
    "ja": "Jpan",
    "ko": "Hang",
    "hi": "Deva",
    "en": "Latn",
    "fr": "Latn",
    "de": "Latn",
    "it": "Latn",
}


@dataclass
class ValidationResult:
    """Result of validating one sample."""

    image_path: str
    gt_language: str
    gt_script: str | None

    # OpenLID-v2 results
    openlid_lang: str
    openlid_lang_639_3: str
    openlid_script: str
    openlid_conf: float
    openlid_correct: bool
    openlid_script_correct: bool

    # lid.176.bin results (optional)
    lid176_lang: str | None = None
    lid176_conf: float | None = None
    lid176_correct: bool | None = None

    # Metadata
    extracted_text: str = ""
    latency_openlid_ms: float = 0.0
    latency_lid176_ms: float = 0.0


@dataclass
class ValidationStats:
    """Aggregated validation statistics."""

    total: int = 0
    openlid_correct: int = 0
    openlid_script_correct: int = 0
    lid176_correct: int = 0
    skipped: int = 0

    openlid_latencies: list[float] = field(default_factory=list)
    lid176_latencies: list[float] = field(default_factory=list)

    per_language: dict[str, dict[str, int]] = field(default_factory=dict)

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result to stats."""
        self.total += 1

        if result.openlid_correct:
            self.openlid_correct += 1
        if result.openlid_script_correct:
            self.openlid_script_correct += 1
        if result.lid176_correct:
            self.lid176_correct += 1

        self.openlid_latencies.append(result.latency_openlid_ms)
        if result.latency_lid176_ms > 0:
            self.lid176_latencies.append(result.latency_lid176_ms)

        # Per-language tracking
        lang = result.gt_language
        if lang not in self.per_language:
            self.per_language[lang] = {
                "total": 0,
                "openlid_correct": 0,
                "lid176_correct": 0,
                "script_correct": 0,
            }

        self.per_language[lang]["total"] += 1
        if result.openlid_correct:
            self.per_language[lang]["openlid_correct"] += 1
        if result.lid176_correct:
            self.per_language[lang]["lid176_correct"] += 1
        if result.openlid_script_correct:
            self.per_language[lang]["script_correct"] += 1


def load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON file."""
    with open(metadata_path) as f:
        return json.load(f)


def get_training_samples_with_labels(
    metadata: dict[str, Any],
    target_languages: list[str] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Get training samples that have actual language labels."""
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
    openlid_detector: Any,
    lid176_model: Any | None,
    easyocr_reader: Any | None,
    lang_to_reader: dict[str, Any],
) -> ValidationResult | None:
    """Validate language detection on a single sample."""
    from image_preprocessing_detector.schema_utils.openlid_integration import (
        ISO639_3_TO_1,
    )

    orig_labels = sample.get("original_labels", {})
    gt_language = orig_labels.get("language_code")
    gt_script = LANG_TO_SCRIPT.get(gt_language)
    source = sample.get("source", {})
    orig_path = source.get("original_path", "")

    # Find the image
    image_path = dataset_path / orig_path
    if not image_path.exists():
        return None

    # Extract text using EasyOCR
    text = ""
    if easyocr_reader:
        reader_family = lang_to_reader.get(gt_language, "latin")
        reader = easyocr_reader.get(reader_family)
        if reader:
            try:
                results = reader.readtext(str(image_path), detail=0)
                text = " ".join(results) if results else ""
            except Exception as e:
                logger.debug(f"EasyOCR error: {e}")

    if not text:
        return None  # Skip samples where we can't extract text

    # OpenLID-v2 detection
    start = time.perf_counter()
    openlid_result = openlid_detector.detect(text)
    openlid_latency = (time.perf_counter() - start) * 1000

    # Check correctness
    # OpenLID uses more granular codes, so we also check if the 639-3 maps to GT
    openlid_correct = openlid_result.language_639_1 == gt_language

    # Also check if the raw 639-3 code maps to the expected language
    # (handles cases like arz → ar for Egyptian Arabic)
    if not openlid_correct:
        mapped = ISO639_3_TO_1.get(openlid_result.language_639_3)
        if mapped == gt_language:
            openlid_correct = True

    openlid_script_correct = (
        gt_script is None or openlid_result.script_code == gt_script
    )

    # lid.176.bin detection (if available)
    lid176_lang = None
    lid176_conf = None
    lid176_correct = None
    lid176_latency = 0.0

    if lid176_model:
        start = time.perf_counter()
        predictions = lid176_model.predict(" ".join(text.split()), k=1)
        lid176_latency = (time.perf_counter() - start) * 1000

        lid176_lang = predictions[0][0].replace("__label__", "")
        lid176_conf = float(predictions[1][0])
        lid176_correct = lid176_lang == gt_language

    return ValidationResult(
        image_path=orig_path,
        gt_language=gt_language,
        gt_script=gt_script,
        openlid_lang=openlid_result.language_639_1,
        openlid_lang_639_3=openlid_result.language_639_3,
        openlid_script=openlid_result.script_code,
        openlid_conf=openlid_result.confidence,
        openlid_correct=openlid_correct,
        openlid_script_correct=openlid_script_correct,
        lid176_lang=lid176_lang,
        lid176_conf=lid176_conf,
        lid176_correct=lid176_correct,
        extracted_text=text[:200],
        latency_openlid_ms=openlid_latency,
        latency_lid176_ms=lid176_latency,
    )


def _print_per_language_table(stats: ValidationStats) -> None:
    """Print per-language accuracy breakdown table."""
    print("\n--- Per-Language Accuracy ---")
    print(f"{'Language':<8} {'OpenLID-v2':<15} {'lid.176':<15} {'Script':<15}")
    print("-" * 55)

    for lang in sorted(stats.per_language.keys()):
        lang_stats = stats.per_language[lang]
        total = lang_stats["total"]

        openlid_pct = lang_stats["openlid_correct"] / total * 100
        lid176_pct = (
            lang_stats["lid176_correct"] / total * 100
            if lang_stats["lid176_correct"]
            else 0
        )
        script_pct = lang_stats["script_correct"] / total * 100

        openlid_str = f"{lang_stats['openlid_correct']}/{total} ({openlid_pct:.0f}%)"
        lid176_str = (
            f"{lang_stats['lid176_correct']}/{total} ({lid176_pct:.0f}%)"
            if stats.lid176_correct
            else "N/A"
        )
        script_str = f"{lang_stats['script_correct']}/{total} ({script_pct:.0f}%)"

        print(f"{lang:<8} {openlid_str:<15} {lid176_str:<15} {script_str:<15}")


def print_report(stats: ValidationStats, results: list[ValidationResult]) -> None:
    """Print validation report."""
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS: OpenLID-v2 vs lid.176.bin on MLT-19")
    print("=" * 70)

    def _safe_pct(correct: int) -> float:
        return correct / stats.total * 100 if stats.total > 0 else 0

    openlid_acc = _safe_pct(stats.openlid_correct)
    script_acc = _safe_pct(stats.openlid_script_correct)
    lid176_acc = _safe_pct(stats.lid176_correct)

    print(f"\nSamples Validated: {stats.total}")
    print(f"Samples Skipped: {stats.skipped}")

    print("\n--- Overall Accuracy ---")
    print(
        f"OpenLID-v2 Language: {stats.openlid_correct}/{stats.total} ({openlid_acc:.1f}%)"
    )
    print(
        f"OpenLID-v2 Script:   {stats.openlid_script_correct}/{stats.total} ({script_acc:.1f}%)"
    )
    if stats.lid176_correct > 0:
        print(
            f"lid.176.bin:         {stats.lid176_correct}/{stats.total} ({lid176_acc:.1f}%)"
        )

    # Latency
    if stats.openlid_latencies:
        avg_openlid = sum(stats.openlid_latencies) / len(stats.openlid_latencies)
        print("\n--- Latency ---")
        print(f"OpenLID-v2 avg: {avg_openlid:.2f}ms")
    if stats.lid176_latencies:
        avg_lid176 = sum(stats.lid176_latencies) / len(stats.lid176_latencies)
        print(f"lid.176.bin avg: {avg_lid176:.2f}ms")

    _print_per_language_table(stats)

    # Show some errors
    errors = [r for r in results if not r.openlid_correct]
    if errors:
        print("\n--- Sample Errors (first 10) ---")
        for r in errors[:10]:
            print(
                f"GT={r.gt_language}, OpenLID={r.openlid_lang} ({r.openlid_lang_639_3}), "
                f"Script={r.openlid_script}, Conf={r.openlid_conf:.2f}"
            )
            if r.extracted_text:
                print(f"  Text: {r.extracted_text[:60]}...")

    # Comparison summary
    print("\n--- Comparison Summary ---")
    if openlid_acc >= lid176_acc:
        print(f"✓ OpenLID-v2 >= lid.176.bin ({openlid_acc:.1f}% vs {lid176_acc:.1f}%)")
    else:
        print(f"⚠ OpenLID-v2 < lid.176.bin ({openlid_acc:.1f}% vs {lid176_acc:.1f}%)")

    print(f"✓ OpenLID-v2 provides script detection ({script_acc:.1f}% accuracy)")

    # Arabic-specific analysis
    if "ar" in stats.per_language:
        ar_stats = stats.per_language["ar"]
        ar_acc = ar_stats["openlid_correct"] / ar_stats["total"] * 100
        print(
            f"\nArabic-specific: {ar_stats['openlid_correct']}/{ar_stats['total']} ({ar_acc:.1f}%)"
        )
        if ar_acc < 90:
            print("  ⚠ Arabic dialect confusion detected (expected with OpenLID-v2)")


def _init_easyocr_readers_openlid() -> tuple[dict[str, Any], dict[str, str]]:
    """Initialise EasyOCR readers for script families used by OpenLID validation.

    Returns:
        Tuple of (easyocr_readers dict, lang_to_reader mapping).
    """
    import easyocr

    script_families = {
        "latin": ["en"],
        "arabic": ["ar", "en"],
        "devanagari": ["hi", "en"],
        "bengali": ["bn", "en"],
        "cjk": ["ch_sim", "en"],
        "japanese": ["ja", "en"],
        "korean": ["ko", "en"],
    }

    readers: dict[str, Any] = {}
    for family, langs in script_families.items():
        try:
            logger.info(f"Initializing EasyOCR for {family}")
            readers[family] = easyocr.Reader(langs, gpu=True)
        except Exception as e:
            logger.warning(f"Could not init {family} reader: {e}")

    lang_to_reader = {
        "en": "latin",
        "fr": "latin",
        "de": "latin",
        "it": "latin",
        "ar": "arabic",
        "hi": "devanagari",
        "bn": "bengali",
        "zh": "cjk",
        "ja": "japanese",
        "ko": "korean",
    }
    return readers, lang_to_reader


def _init_lid176_model(no_lid176: bool) -> Any:
    """Try to load the lid.176.bin fastText model."""
    if no_lid176:
        return None
    lid176_path = MODEL_DIR / "lid.176.bin"
    if not lid176_path.exists():
        return None
    try:
        import fasttext

        logger.info("Loading lid.176.bin for comparison...")
        return fasttext.load_model(str(lid176_path))
    except Exception as e:
        logger.warning(f"Could not load lid.176.bin: {e}")
    return None


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate OpenLID-v2 against MLT-19 ground truth"
    )
    parser.add_argument("--samples", type=int, default=100, help="Number of samples")
    parser.add_argument("--all", action="store_true", help="Use all training samples")
    parser.add_argument(
        "--languages", type=str, help="Comma-separated languages (e.g., 'ar,zh,ja')"
    )
    parser.add_argument(
        "--metadata", type=Path, default=METADATA_REGISTRY_PATH / "mlt19_metadata.json"
    )
    parser.add_argument(
        "--dataset-path", type=Path, default=BASE_DATA_PATH / "language/mlt19"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-lid176", action="store_true", help="Skip lid.176.bin comparison"
    )
    parser.add_argument(
        "--no-ocr", action="store_true", help="Skip OCR (use existing text)"
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
    if not args.metadata.exists():
        logger.error(f"Metadata file not found: {args.metadata}")
        return 1

    metadata = load_metadata(args.metadata)
    labeled_samples = get_training_samples_with_labels(metadata, target_languages)
    logger.info(f"Found {len(labeled_samples)} training samples with labels")

    if not args.all and len(labeled_samples) > args.samples:
        labeled_samples = random.sample(labeled_samples, args.samples)
    logger.info(f"Validating {len(labeled_samples)} samples")

    lang_dist = Counter(
        s.get("original_labels", {}).get("language_code") for _, s in labeled_samples
    )
    logger.info(f"Language distribution: {dict(lang_dist)}")

    # Initialize OpenLID-v2
    try:
        from image_preprocessing_detector.schema_utils.openlid_integration import (
            OpenLIDDetector,
        )

        logger.info("Initializing OpenLID-v2 detector...")
        openlid_detector = OpenLIDDetector(auto_download=True)
        openlid_detector.detect("test")
    except Exception as e:
        logger.error(f"Failed to initialize OpenLID-v2: {e}")
        return 1

    lid176_model = _init_lid176_model(args.no_lid176)

    # Initialize EasyOCR readers
    easyocr_readers: dict[str, Any] = {}
    lang_to_reader: dict[str, str] = {}

    if not args.no_ocr:
        try:
            easyocr_readers, lang_to_reader = _init_easyocr_readers_openlid()
        except ImportError:
            logger.warning("EasyOCR not installed")

    if not easyocr_readers and not args.no_ocr:
        logger.error("EasyOCR required for validation")
        return 1

    # Run validation
    stats = ValidationStats()
    results: list[ValidationResult] = []

    for idx, (sample_idx, sample) in enumerate(labeled_samples):
        result = validate_sample(
            sample,
            args.dataset_path,
            openlid_detector,
            lid176_model,
            easyocr_readers,
            lang_to_reader,
        )

        if result is None:
            stats.skipped += 1
            continue

        results.append(result)
        stats.add_result(result)

        if (idx + 1) % 25 == 0:
            acc = stats.openlid_correct / stats.total * 100 if stats.total > 0 else 0
            logger.info(
                f"Progress: {idx + 1}/{len(labeled_samples)} | OpenLID acc: {acc:.1f}%"
            )

    print_report(stats, results)

    return 0


if __name__ == "__main__":
    exit(main())
