#!/usr/bin/env python3
"""Local-only language triage analysis (Tier 1a/1b without vision API).

Runs local detection methods to analyze language/script distribution:
- Tier 1a: Unicode script detection from OCR text
- Tier 1b: fastText + lingua language detection

NO API calls - purely local processing.

Usage:
    # Analyze sample of dataset
    PYTHONPATH=. uv run python scripts/triage_local_analysis.py --dataset fintabnet --sample 500

    # Full dataset analysis (slow - uses OCR)
    PYTHONPATH=. uv run python scripts/triage_local_analysis.py --dataset fintabnet --all

    # Generate report only (from cached results)
    PYTHONPATH=. uv run python scripts/triage_local_analysis.py --dataset fintabnet --report-only
"""

import argparse
import json
import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
METADATA_REGISTRY = Path("/mnt/e/image_detection/metadata_registry/json")
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")
RESULTS_DIR = Path("/mnt/e/image_detection/metadata_registry/triage_analysis")

# Dataset path mappings
DATASET_PATHS = {
    "fintabnet": BASE_DATA_PATH / "tables/fintabnet",
    "tablebank": BASE_DATA_PATH / "tables/tablebank",
    "pubtabnet": BASE_DATA_PATH / "tables/pubtabnet",
    "mlt19": BASE_DATA_PATH / "language/mlt19",
    "mdiw13": BASE_DATA_PATH / "language/mdiw13",
    "rvl_cdip": BASE_DATA_PATH / "documents/rvl_cdip",
    "tobacco800": BASE_DATA_PATH / "documents/tobacco800",
    "funsd": BASE_DATA_PATH / "forms/funsd",
    "sroie": BASE_DATA_PATH / "forms/sroie",
}

# Confidence thresholds for stratification
CONFIDENCE_BINS = [
    (0.9, 1.0, "very_high"),
    (0.7, 0.9, "high"),
    (0.5, 0.7, "medium"),
    (0.3, 0.5, "low"),
    (0.0, 0.3, "very_low"),
]


@dataclass
class LocalDetectionResult:
    """Result from local-only detection."""
    sample_id: str
    image_path: str

    # Text extraction
    extracted_text: str
    text_length: int
    ocr_confidence: float

    # Script detection (Tier 1a)
    detected_scripts: list[str]
    primary_script: str | None
    script_confidence: float

    # Language detection (Tier 1b local)
    fasttext_lang: str | None
    fasttext_confidence: float
    lingua_lang: str | None
    lingua_confidence: float

    # Consensus
    consensus_language: str
    consensus_confidence: float
    detector_agreement: bool
    needs_vision_escalation: bool
    escalation_reason: str | None


def load_detection_models():
    """Load fastText and lingua models."""
    models = {}

    # Load fastText
    try:
        import fasttext
        model_path = Path("/mnt/e/image_detection/models/language_detection/lid.176.bin")
        if model_path.exists():
            # Suppress fastText warnings
            fasttext.FastText.eprint = lambda x: None
            models["fasttext"] = fasttext.load_model(str(model_path))
            logger.info("Loaded fastText model")
        else:
            logger.warning(f"fastText model not found: {model_path}")
    except ImportError:
        logger.warning("fastText not installed")

    # Load lingua
    try:
        from lingua import LanguageDetectorBuilder
        models["lingua"] = LanguageDetectorBuilder.from_all_languages().build()
        logger.info("Loaded lingua detector")
    except ImportError:
        logger.warning("lingua not installed")

    return models


def load_ocr_reader():
    """Load EasyOCR reader."""
    try:
        import easyocr
        # Use English reader by default - it can detect text in any script
        reader = easyocr.Reader(["en"], gpu=True, verbose=False)
        logger.info("Loaded EasyOCR reader (GPU)")
        return reader
    except Exception as e:
        logger.warning(f"EasyOCR GPU failed, trying CPU: {e}")
        try:
            import easyocr
            reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("Loaded EasyOCR reader (CPU)")
            return reader
        except Exception as e2:
            logger.error(f"EasyOCR failed: {e2}")
            return None


def extract_text_ocr(image_path: Path, reader) -> tuple[str, float]:
    """Extract text from image using EasyOCR."""
    if reader is None:
        return "", 0.0

    try:
        results = reader.readtext(str(image_path))
        if not results:
            return "", 0.0

        texts = []
        confidences = []
        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)

        full_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return full_text, avg_confidence
    except Exception as e:
        logger.debug(f"OCR error for {image_path}: {e}")
        return "", 0.0


def detect_scripts(text: str) -> tuple[list[str], dict[str, int]]:
    """Detect scripts present in text using Unicode analysis."""
    import unicodedata

    # Unicode block to ISO 15924 script mapping
    CHAR_TO_SCRIPT = {
        "LATIN": "Latn",
        "GREEK": "Grek",
        "CYRILLIC": "Cyrl",
        "ARMENIAN": "Armn",
        "HEBREW": "Hebr",
        "ARABIC": "Arab",
        "SYRIAC": "Syrc",
        "THAANA": "Thaa",
        "DEVANAGARI": "Deva",
        "BENGALI": "Beng",
        "GURMUKHI": "Guru",
        "GUJARATI": "Gujr",
        "ORIYA": "Orya",
        "TAMIL": "Taml",
        "TELUGU": "Telu",
        "KANNADA": "Knda",
        "MALAYALAM": "Mlym",
        "SINHALA": "Sinh",
        "THAI": "Thai",
        "LAO": "Laoo",
        "TIBETAN": "Tibt",
        "MYANMAR": "Mymr",
        "GEORGIAN": "Geor",
        "HANGUL": "Hang",
        "ETHIOPIC": "Ethi",
        "CHEROKEE": "Cher",
        "CANADIAN": "Cans",
        "OGHAM": "Ogam",
        "RUNIC": "Runr",
        "KHMER": "Khmr",
        "MONGOLIAN": "Mong",
        "HIRAGANA": "Hira",
        "KATAKANA": "Kana",
        "BOPOMOFO": "Bopo",
        "HAN": "Hani",
        "CJK": "Hani",
    }

    script_counts = Counter()

    for char in text:
        if char.isalpha():
            try:
                name = unicodedata.name(char, "")
                for prefix, script in CHAR_TO_SCRIPT.items():
                    if prefix in name:
                        script_counts[script] += 1
                        break
            except ValueError:
                pass

    # Sort by count
    scripts = [s for s, _ in script_counts.most_common()]
    return scripts, dict(script_counts)


def detect_language_fasttext(text: str, model) -> tuple[str | None, float]:
    """Detect language using fastText."""
    if model is None or not text.strip():
        return None, 0.0

    try:
        # Clean text
        clean_text = " ".join(text.split())[:1000]  # Limit length
        predictions = model.predict(clean_text, k=1)

        label = predictions[0][0].replace("__label__", "")
        confidence = float(predictions[1][0])

        return label, confidence
    except Exception as e:
        logger.debug(f"fastText error: {e}")
        return None, 0.0


def detect_language_lingua(text: str, detector) -> tuple[str | None, float]:
    """Detect language using lingua."""
    if detector is None or not text.strip():
        return None, 0.0

    try:
        result = detector.detect_language_of(text)
        if result:
            # Map lingua language to ISO 639-1
            lang_code = result.iso_code_639_1.name.lower()

            # Get confidence
            confidences = detector.compute_language_confidence_values(text)
            conf = confidences[0].value if confidences else 0.5

            return lang_code, conf
        return None, 0.0
    except Exception as e:
        logger.debug(f"lingua error: {e}")
        return None, 0.0


def compute_consensus(
    scripts: list[str],
    script_counts: dict[str, int],
    ft_lang: str | None,
    ft_conf: float,
    lingua_lang: str | None,
    lingua_conf: float,
) -> tuple[str, float, bool, bool, str | None]:
    """Compute consensus language and determine if escalation needed."""

    # Script-to-language mapping for high-confidence inference
    SCRIPT_TO_LANG = {
        "Arab": "ar",
        "Deva": "hi",
        "Beng": "bn",
        "Hani": "zh",
        "Hang": "ko",
        "Hira": "ja",
        "Kana": "ja",
        "Cyrl": "ru",
        "Grek": "el",
        "Hebr": "he",
        "Thai": "Thai",
        "Tibt": "bo",
        "Taml": "ta",
        "Telu": "te",
        "Knda": "kn",
        "Mlym": "ml",
        "Gujr": "gu",
        "Guru": "pa",
        "Orya": "or",
        "Sinh": "si",
        "Mymr": "my",
        "Khmr": "km",
        "Laoo": "lo",
        "Geor": "ka",
        "Armn": "hy",
        "Ethi": "am",
    }

    # Ambiguous scripts that need language detection
    AMBIGUOUS_SCRIPTS = {"Latn", "Cyrl", "Arab"}

    primary_script = scripts[0] if scripts else None

    # Case 1: Non-ambiguous script - high confidence from script alone
    if primary_script and primary_script not in AMBIGUOUS_SCRIPTS:
        lang = SCRIPT_TO_LANG.get(primary_script, "und")
        return lang, 0.9, True, False, None

    # Case 2: No text detected
    if not scripts and not ft_lang and not lingua_lang:
        return "und", 0.0, False, True, "no_text_detected"

    # Case 3: Ambiguous script - need language detection consensus
    agreement = ft_lang == lingua_lang if (ft_lang and lingua_lang) else False

    if agreement and ft_conf > 0.5 and lingua_conf > 0.5:
        # Both agree with decent confidence
        avg_conf = (ft_conf + lingua_conf) / 2
        return ft_lang, avg_conf, True, False, None

    if ft_conf > 0.8:
        # fastText highly confident
        return ft_lang, ft_conf * 0.9, False, False, None

    if lingua_conf > 0.8:
        # lingua highly confident
        return lingua_lang, lingua_conf * 0.9, False, False, None

    # Low confidence - needs escalation
    best_lang = ft_lang or lingua_lang or "und"
    best_conf = max(ft_conf, lingua_conf)

    needs_escalation = best_conf < 0.6 or not agreement
    reason = "low_confidence" if best_conf < 0.6 else "detector_disagreement"

    return best_lang, best_conf, agreement, needs_escalation, reason


def analyze_sample(
    sample: dict,
    base_path: Path,
    ocr_reader,
    models: dict,
) -> LocalDetectionResult | None:
    """Run local-only analysis on a single sample."""

    rel_path = sample.get("source", {}).get("original_path", "")
    img_path = base_path / rel_path

    if not img_path.exists():
        return None

    # Extract text via OCR
    text, ocr_conf = extract_text_ocr(img_path, ocr_reader)

    # Detect scripts
    scripts, script_counts = detect_scripts(text)
    primary_script = scripts[0] if scripts else None
    script_conf = 0.9 if primary_script and primary_script not in {"Latn"} else 0.5

    # Detect language
    ft_lang, ft_conf = detect_language_fasttext(text, models.get("fasttext"))
    lingua_lang, lingua_conf = detect_language_lingua(text, models.get("lingua"))

    # Compute consensus
    consensus_lang, consensus_conf, agreement, needs_escalation, reason = compute_consensus(
        scripts, script_counts, ft_lang, ft_conf, lingua_lang, lingua_conf
    )

    return LocalDetectionResult(
        sample_id=sample.get("id", ""),
        image_path=str(img_path),
        extracted_text=text[:200],  # Truncate for storage
        text_length=len(text),
        ocr_confidence=ocr_conf,
        detected_scripts=scripts,
        primary_script=primary_script,
        script_confidence=script_conf,
        fasttext_lang=ft_lang,
        fasttext_confidence=ft_conf,
        lingua_lang=lingua_lang,
        lingua_confidence=lingua_conf,
        consensus_language=consensus_lang,
        consensus_confidence=consensus_conf,
        detector_agreement=agreement,
        needs_vision_escalation=needs_escalation,
        escalation_reason=reason,
    )


def generate_report(results: list[LocalDetectionResult], dataset: str) -> str:
    """Generate confidence-stratified report."""

    report_lines = [
        f"# Language Triage Analysis Report: {dataset}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Total samples analyzed: {len(results)}",
        "",
        "## Executive Summary",
        "",
    ]

    # Overall stats
    needs_escalation = sum(1 for r in results if r.needs_vision_escalation)
    no_escalation = len(results) - needs_escalation

    report_lines.extend([
        f"- **Can be labeled locally**: {no_escalation} ({100*no_escalation/len(results):.1f}%)",
        f"- **Needs vision escalation**: {needs_escalation} ({100*needs_escalation/len(results):.1f}%)",
        "",
    ])

    # Script distribution
    script_counts = Counter()
    for r in results:
        script_counts[r.primary_script or "None"] += 1

    report_lines.extend([
        "## Script Distribution",
        "",
        "| Script | Count | % |",
        "|--------|-------|---|",
    ])
    for script, count in script_counts.most_common():
        pct = 100 * count / len(results)
        report_lines.append(f"| {script} | {count} | {pct:.1f}% |")
    report_lines.append("")

    # Language distribution
    lang_counts = Counter()
    for r in results:
        lang_counts[r.consensus_language] += 1

    report_lines.extend([
        "## Language Distribution (Consensus)",
        "",
        "| Language | Count | % |",
        "|----------|-------|---|",
    ])
    for lang, count in lang_counts.most_common(15):
        pct = 100 * count / len(results)
        report_lines.append(f"| {lang} | {count} | {pct:.1f}% |")
    report_lines.append("")

    # Confidence stratification
    report_lines.extend([
        "## Confidence Stratification",
        "",
        "| Confidence | Count | % | Needs Escalation |",
        "|------------|-------|---|------------------|",
    ])

    for low, high, label in CONFIDENCE_BINS:
        in_bin = [r for r in results if low <= r.consensus_confidence < high]
        count = len(in_bin)
        pct = 100 * count / len(results) if results else 0
        esc_count = sum(1 for r in in_bin if r.needs_vision_escalation)
        esc_pct = 100 * esc_count / count if count else 0
        report_lines.append(f"| {label} ({low:.1f}-{high:.1f}) | {count} | {pct:.1f}% | {esc_count} ({esc_pct:.0f}%) |")
    report_lines.append("")

    # Escalation reasons
    reason_counts = Counter()
    for r in results:
        if r.escalation_reason:
            reason_counts[r.escalation_reason] += 1

    if reason_counts:
        report_lines.extend([
            "## Escalation Reasons",
            "",
            "| Reason | Count |",
            "|--------|-------|",
        ])
        for reason, count in reason_counts.most_common():
            report_lines.append(f"| {reason} | {count} |")
        report_lines.append("")

    # Detector agreement
    agree_count = sum(1 for r in results if r.detector_agreement)
    report_lines.extend([
        "## Detector Agreement",
        "",
        f"- **Detectors agree**: {agree_count} ({100*agree_count/len(results):.1f}%)",
        f"- **Detectors disagree**: {len(results) - agree_count} ({100*(len(results)-agree_count)/len(results):.1f}%)",
        "",
    ])

    # Cost estimate
    report_lines.extend([
        "## Cost Estimate (if using vision API)",
        "",
        f"- Samples needing vision: {needs_escalation}",
        f"- Est. cost @ $0.0003/sample: ${needs_escalation * 0.0003:.2f}",
        f"- Est. cost @ $0.01/sample (Gemini Pro): ${needs_escalation * 0.01:.2f}",
        "",
    ])

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Local-only language triage analysis")
    parser.add_argument("--dataset", required=True, help="Dataset name")
    parser.add_argument("--sample", type=int, help="Sample N records (default: 500)")
    parser.add_argument("--all", action="store_true", help="Process all records")
    parser.add_argument("--report-only", action="store_true", help="Generate report from cached results")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = RESULTS_DIR / f"{args.dataset}_triage_results.json"
    report_file = RESULTS_DIR / f"{args.dataset}_triage_report.md"

    # Report only mode
    if args.report_only:
        if not results_file.exists():
            logger.error(f"No cached results found: {results_file}")
            return 1

        with open(results_file) as f:
            results_data = json.load(f)

        results = [LocalDetectionResult(**r) for r in results_data]
        report = generate_report(results, args.dataset)

        with open(report_file, "w") as f:
            f.write(report)

        print(report)
        logger.info(f"Report saved to: {report_file}")
        return 0

    # Load metadata
    metadata_file = METADATA_REGISTRY / f"{args.dataset}_metadata.json"
    if not metadata_file.exists():
        logger.error(f"Metadata not found: {metadata_file}")
        return 1

    with open(metadata_file) as f:
        data = json.load(f)

    samples = data.get("samples", [])
    logger.info(f"Loaded {len(samples)} samples from {args.dataset}")

    # Get base path
    base_path = DATASET_PATHS.get(args.dataset)
    if not base_path:
        logger.error(f"Unknown dataset path: {args.dataset}")
        logger.info(f"Known datasets: {list(DATASET_PATHS.keys())}")
        return 1

    # Sample if requested
    if not args.all:
        import random
        sample_size = args.sample or 500
        if len(samples) > sample_size:
            samples = random.sample(samples, sample_size)
            logger.info(f"Sampled {sample_size} records")

    # Load models
    logger.info("Loading detection models...")
    models = load_detection_models()
    ocr_reader = load_ocr_reader()

    if not ocr_reader:
        logger.error("OCR reader not available")
        return 1

    # Process samples
    results = []
    start_time = time.time()

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (len(samples) - i - 1) / rate if rate > 0 else 0
            logger.info(f"Progress: {i + 1}/{len(samples)} ({rate:.1f}/sec, ETA: {eta/60:.1f} min)")

        result = analyze_sample(sample, base_path, ocr_reader, models)
        if result:
            results.append(result)

    elapsed = time.time() - start_time
    logger.info(f"Processed {len(results)} samples in {elapsed:.1f}s ({len(results)/elapsed:.1f}/sec)")

    # Save results
    results_data = [
        {
            "sample_id": r.sample_id,
            "image_path": r.image_path,
            "extracted_text": r.extracted_text,
            "text_length": r.text_length,
            "ocr_confidence": r.ocr_confidence,
            "detected_scripts": r.detected_scripts,
            "primary_script": r.primary_script,
            "script_confidence": r.script_confidence,
            "fasttext_lang": r.fasttext_lang,
            "fasttext_confidence": r.fasttext_confidence,
            "lingua_lang": r.lingua_lang,
            "lingua_confidence": r.lingua_confidence,
            "consensus_language": r.consensus_language,
            "consensus_confidence": r.consensus_confidence,
            "detector_agreement": r.detector_agreement,
            "needs_vision_escalation": r.needs_vision_escalation,
            "escalation_reason": r.escalation_reason,
        }
        for r in results
    ]

    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)
    logger.info(f"Results saved to: {results_file}")

    # Generate report
    report = generate_report(results, args.dataset)

    with open(report_file, "w") as f:
        f.write(report)

    print("\n" + report)
    logger.info(f"Report saved to: {report_file}")

    return 0


if __name__ == "__main__":
    exit(main())
