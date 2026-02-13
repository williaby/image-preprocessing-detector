#!/usr/bin/env python3
"""Layer 2 Language Enrichment for MLT-19 Test Images.

Uses multi-factor consensus analysis for language/script detection:
1. Run two detection methods
2. If both agree on language AND script → accept
3. If disagreement → run third method, use 2-of-3 majority

Detection Methods:
- fastText (lid.176.bin): 176 languages, good for short text
- lingua-py: 75 languages, high accuracy
- Unicode script analysis: Deterministic script detection

Usage:
    # Install dependencies
    uv add fasttext lingua-language-detector --optional language-detection

    # Download fastText model (one-time)
    uv run python scripts/enrich_mlt19_language.py --download-model

    # Run enrichment
    uv run python scripts/enrich_mlt19_language.py

    # Process specific batch
    uv run python scripts/enrich_mlt19_language.py --start 0 --end 1000
"""

import argparse
import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# ISO 15924 Script Detection via Unicode
# =============================================================================

# Unicode block to ISO 15924 script mapping (comprehensive)
UNICODE_BLOCK_TO_SCRIPT = {
    # Latin scripts
    (0x0041, 0x007A): "Latn",  # Basic Latin
    (0x00C0, 0x00FF): "Latn",  # Latin-1 Supplement
    (0x0100, 0x017F): "Latn",  # Latin Extended-A
    (0x0180, 0x024F): "Latn",  # Latin Extended-B
    (0x1E00, 0x1EFF): "Latn",  # Latin Extended Additional
    # Greek
    (0x0370, 0x03FF): "Grek",
    (0x1F00, 0x1FFF): "Grek",  # Greek Extended
    # Cyrillic
    (0x0400, 0x04FF): "Cyrl",
    (0x0500, 0x052F): "Cyrl",  # Cyrillic Supplement
    # Armenian
    (0x0530, 0x058F): "Armn",
    # Hebrew
    (0x0590, 0x05FF): "Hebr",
    # Arabic
    (0x0600, 0x06FF): "Arab",
    (0x0750, 0x077F): "Arab",  # Arabic Supplement
    (0x08A0, 0x08FF): "Arab",  # Arabic Extended-A
    # Syriac
    (0x0700, 0x074F): "Syrc",
    # Thaana (Maldivian)
    (0x0780, 0x07BF): "Thaa",
    # Devanagari
    (0x0900, 0x097F): "Deva",
    (0xA8E0, 0xA8FF): "Deva",  # Devanagari Extended
    # Bengali
    (0x0980, 0x09FF): "Beng",
    # Gurmukhi
    (0x0A00, 0x0A7F): "Guru",
    # Gujarati
    (0x0A80, 0x0AFF): "Gujr",
    # Oriya
    (0x0B00, 0x0B7F): "Orya",
    # Tamil
    (0x0B80, 0x0BFF): "Taml",
    # Telugu
    (0x0C00, 0x0C7F): "Telu",
    # Kannada
    (0x0C80, 0x0CFF): "Knda",
    # Malayalam
    (0x0D00, 0x0D7F): "Mlym",
    # Sinhala
    (0x0D80, 0x0DFF): "Sinh",
    # Thai
    (0x0E00, 0x0E7F): "Thai",
    # Lao
    (0x0E80, 0x0EFF): "Laoo",
    # Tibetan
    (0x0F00, 0x0FFF): "Tibt",
    # Myanmar
    (0x1000, 0x109F): "Mymr",
    # Georgian
    (0x10A0, 0x10FF): "Geor",
    # Korean Hangul
    (0x1100, 0x11FF): "Hang",  # Hangul Jamo
    (0xAC00, 0xD7AF): "Hang",  # Hangul Syllables
    (0x3130, 0x318F): "Hang",  # Hangul Compatibility Jamo
    # Ethiopic
    (0x1200, 0x137F): "Ethi",
    # Cherokee
    (0x13A0, 0x13FF): "Cher",
    # Canadian Aboriginal
    (0x1400, 0x167F): "Cans",
    # Khmer
    (0x1780, 0x17FF): "Khmr",
    # Mongolian
    (0x1800, 0x18AF): "Mong",
    # Japanese Hiragana
    (0x3040, 0x309F): "Hira",
    # Japanese Katakana
    (0x30A0, 0x30FF): "Kana",
    (0x31F0, 0x31FF): "Kana",  # Katakana Phonetic Extensions
    # CJK Unified Ideographs (Han)
    (0x4E00, 0x9FFF): "Hani",
    (0x3400, 0x4DBF): "Hani",  # CJK Extension A
    (0x20000, 0x2A6DF): "Hani",  # CJK Extension B
    (0x2A700, 0x2B73F): "Hani",  # CJK Extension C
    # Bopomofo
    (0x3100, 0x312F): "Bopo",
    # Yi
    (0xA000, 0xA48F): "Yiii",
}

# Script to primary language mapping (for scripts with single dominant language)
SCRIPT_TO_PRIMARY_LANGUAGE = {
    "Arab": "ar",  # Arabic (but also Urdu, Persian, etc.)
    "Armn": "hy",  # Armenian
    "Beng": "bn",  # Bengali
    "Cher": "chr",  # Cherokee
    "Cyrl": None,  # Cyrillic (Russian, Ukrainian, Bulgarian, etc.)
    "Deva": "hi",  # Devanagari (Hindi, Sanskrit, Marathi, etc.)
    "Ethi": "am",  # Ethiopic (Amharic, Tigrinya)
    "Geor": "ka",  # Georgian
    "Grek": "el",  # Greek
    "Gujr": "gu",  # Gujarati
    "Guru": "pa",  # Gurmukhi (Punjabi)
    "Hang": "ko",  # Hangul (Korean)
    "Hani": None,  # Han (Chinese, Japanese Kanji)
    "Hebr": "he",  # Hebrew
    "Hira": "ja",  # Hiragana (Japanese)
    "Kana": "ja",  # Katakana (Japanese)
    "Khmr": "km",  # Khmer
    "Knda": "kn",  # Kannada
    "Laoo": "lo",  # Lao
    "Latn": None,  # Latin (many languages)
    "Mlym": "ml",  # Malayalam
    "Mong": "mn",  # Mongolian
    "Mymr": "my",  # Myanmar (Burmese)
    "Orya": "or",  # Oriya
    "Sinh": "si",  # Sinhala
    "Taml": "ta",  # Tamil
    "Telu": "te",  # Telugu
    "Thai": "th",  # Thai
    "Thaa": "dv",  # Thaana (Dhivehi/Maldivian)
    "Tibt": "bo",  # Tibetan
}


@dataclass
class DetectionResult:
    """Result from a single detection method."""

    language: str  # ISO 639-1/2/3 code
    script: str | None  # ISO 15924 code
    confidence: float  # 0.0 - 1.0
    method: str  # Detection method name


@dataclass
class ConsensusResult:
    """Final consensus result from multi-factor analysis."""

    language: str
    script: str | None
    confidence: float
    method: str  # "consensus_2of2", "consensus_2of3", "majority", "single"
    votes: list[DetectionResult]
    agreement: bool


def detect_script_unicode(text: str) -> DetectionResult:
    """Detect script using Unicode block analysis.

    This is deterministic and highly accurate for script detection.
    Returns the dominant script found in the text.
    """
    if not text or not text.strip():
        return DetectionResult("und", None, 0.0, "unicode_empty")

    script_counts: Counter[str] = Counter()

    for char in text:
        if char.isspace() or char in ".,!?;:'\"()-[]{}0123456789":
            continue

        code = ord(char)

        # Find matching Unicode block
        for (start, end), script in UNICODE_BLOCK_TO_SCRIPT.items():
            if start <= code <= end:
                script_counts[script] += 1
                break

    if not script_counts:
        return DetectionResult("und", None, 0.0, "unicode_no_script")

    # Get dominant script
    total = sum(script_counts.values())
    dominant_script, dominant_count = script_counts.most_common(1)[0]
    confidence = dominant_count / total if total > 0 else 0.0

    # Check for mixed scripts (Japanese uses Hira + Kana + Hani)
    if "Hira" in script_counts or "Kana" in script_counts:
        # Japanese detected
        return DetectionResult("ja", "Jpan", confidence, "unicode_script")

    # Map script to primary language if unambiguous
    primary_lang = SCRIPT_TO_PRIMARY_LANGUAGE.get(dominant_script)
    if primary_lang:
        return DetectionResult(
            primary_lang, dominant_script, confidence, "unicode_script"
        )

    # Ambiguous script (Latin, Cyrillic, Han)
    return DetectionResult(
        "und", dominant_script, confidence, "unicode_script_ambiguous"
    )


def detect_language_fasttext(text: str, model: Any) -> DetectionResult:
    """Detect language using fastText lid.176.bin model.

    Covers 176 languages with good accuracy on short text.
    """
    if not text or not text.strip():
        return DetectionResult("und", None, 0.0, "fasttext_empty")

    try:
        # Clean text (fastText expects single line)
        clean_text = " ".join(text.split())

        # Predict
        predictions = model.predict(clean_text, k=1)
        label = predictions[0][0]  # '__label__en'
        confidence = float(predictions[1][0])

        # Extract language code
        lang_code = label.replace("__label__", "")

        # Map to script (approximate)
        script = infer_script_from_language(lang_code)

        return DetectionResult(lang_code, script, confidence, "fasttext")

    except Exception as e:
        logger.debug(f"fastText error: {e}")
        return DetectionResult("und", None, 0.0, "fasttext_error")


def detect_language_lingua(text: str, detector: Any) -> DetectionResult:
    """Detect language using lingua-py.

    High accuracy language detection, covers 75 languages.
    """
    if not text or not text.strip():
        return DetectionResult("und", None, 0.0, "lingua_empty")

    try:
        from lingua import ConfidenceValue

        # Detect with confidence
        result = detector.compute_language_confidence_values(text)

        if not result:
            return DetectionResult("und", None, 0.0, "lingua_no_result")

        # Get top result
        top: ConfidenceValue = result[0]
        lang_code = top.language.iso_code_639_1.name.lower()
        confidence = top.value

        # Map to script
        script = infer_script_from_language(lang_code)

        return DetectionResult(lang_code, script, confidence, "lingua")

    except Exception as e:
        logger.debug(f"lingua error: {e}")
        return DetectionResult("und", None, 0.0, "lingua_error")


def infer_script_from_language(lang_code: str) -> str | None:
    """Infer ISO 15924 script from language code."""
    # Common language to script mappings
    lang_to_script = {
        "ar": "Arab",
        "bn": "Beng",
        "bg": "Cyrl",
        "zh": "Hans",
        "el": "Grek",
        "gu": "Gujr",
        "he": "Hebr",
        "hi": "Deva",
        "ja": "Jpan",
        "kn": "Knda",
        "ko": "Kore",
        "ml": "Mlym",
        "mr": "Deva",
        "ne": "Deva",
        "or": "Orya",
        "pa": "Guru",
        "ru": "Cyrl",
        "sa": "Deva",
        "si": "Sinh",
        "ta": "Taml",
        "te": "Telu",
        "th": "Thai",
        "uk": "Cyrl",
        "ur": "Arab",
        "yi": "Hebr",
        # Latin script languages
        "en": "Latn",
        "es": "Latn",
        "fr": "Latn",
        "de": "Latn",
        "it": "Latn",
        "pt": "Latn",
        "nl": "Latn",
        "pl": "Latn",
        "vi": "Latn",
        "tr": "Latn",
        "id": "Latn",
        "ms": "Latn",
        "tl": "Latn",
        "sw": "Latn",
        "ro": "Latn",
        "cs": "Latn",
        "hu": "Latn",
        "fi": "Latn",
        "sv": "Latn",
        "no": "Latn",
        "da": "Latn",
    }
    return lang_to_script.get(lang_code)


def _try_two_of_two_consensus(
    votes: list[DetectionResult],
) -> ConsensusResult | None:
    """Check if the first two votes agree on language."""
    if len(votes) < 2:
        return None
    v1, v2 = votes[0], votes[1]
    if v1.language != v2.language or v1.language == "und":
        return None
    avg_conf = (v1.confidence + v2.confidence) / 2
    return ConsensusResult(
        language=v1.language,
        script=v1.script or v2.script,
        confidence=avg_conf,
        method="consensus_2of2",
        votes=votes,
        agreement=True,
    )


def _try_two_of_three_consensus(
    votes: list[DetectionResult],
) -> ConsensusResult | None:
    """Check for 2-of-3 majority among votes."""
    if len(votes) < 3:
        return None
    lang_counts = Counter(v.language for v in votes if v.language != "und")
    if not lang_counts:
        return None
    majority_lang, count = lang_counts.most_common(1)[0]
    if count < 2:
        return None
    majority_votes = [v for v in votes if v.language == majority_lang]
    avg_conf = sum(v.confidence for v in majority_votes) / len(majority_votes)
    script = next((v.script for v in majority_votes if v.script), None)
    return ConsensusResult(
        language=majority_lang,
        script=script,
        confidence=avg_conf,
        method="consensus_2of3",
        votes=votes,
        agreement=True,
    )


def consensus_detect(
    text: str,
    fasttext_model: Any = None,
    lingua_detector: Any = None,
) -> ConsensusResult:
    """Multi-factor consensus language detection.

    Strategy:
    1. Run two methods (fastText + Unicode or lingua + Unicode)
    2. If both agree on language AND script -> accept with high confidence
    3. If disagreement -> run third method, use 2-of-3 majority
    4. If no majority -> use highest confidence result
    """
    votes: list[DetectionResult] = []

    votes.append(detect_script_unicode(text))
    if fasttext_model:
        votes.append(detect_language_fasttext(text, fasttext_model))
    if lingua_detector:
        votes.append(detect_language_lingua(text, lingua_detector))

    if len(votes) < 2:
        return ConsensusResult(
            language=votes[0].language,
            script=votes[0].script,
            confidence=votes[0].confidence,
            method="single",
            votes=votes,
            agreement=True,
        )

    result = _try_two_of_two_consensus(votes)
    if result:
        return result

    result = _try_two_of_three_consensus(votes)
    if result:
        return result

    # No consensus - use highest confidence non-und result
    valid_votes = [v for v in votes if v.language != "und"]
    if valid_votes:
        best = max(valid_votes, key=lambda v: v.confidence)
        return ConsensusResult(
            language=best.language,
            script=best.script,
            confidence=best.confidence * 0.8,
            method="highest_confidence",
            votes=votes,
            agreement=False,
        )

    return ConsensusResult(
        language="und",
        script=votes[0].script if votes else None,
        confidence=0.0,
        method="no_consensus",
        votes=votes,
        agreement=True,
    )


def extract_text_easyocr(image_path: Path, reader: Any) -> str:
    """Extract text from image using EasyOCR."""
    try:
        results = reader.readtext(str(image_path), detail=0)
        return " ".join(results) if results else ""
    except Exception as e:
        logger.debug(f"EasyOCR error for {image_path}: {e}")
        return ""


def load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON file."""
    with open(metadata_path) as f:
        return json.load(f)


def save_metadata(metadata: dict[str, Any], metadata_path: Path) -> None:
    """Save metadata JSON file."""
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)


def update_enrichment(
    sample: dict[str, Any],
    result: ConsensusResult,
    git_sha: str = "manual",
) -> None:
    """Update sample's enrichment layer with consensus detection result."""
    enrichments = sample.get("enrichments", {})
    current_version = enrichments.get("current_version", 0)
    versions = enrichments.get("versions", [])

    # Get latest data or empty dict
    latest_data = versions[-1].get("data", {}).copy() if versions else {}

    # Update language fields
    latest_data["iso639_language"] = result.language
    if result.script:
        latest_data["iso15924_script"] = result.script

    # Add detection metadata
    latest_data["language_detection_method"] = result.method
    latest_data["language_detection_confidence"] = round(result.confidence, 3)
    latest_data["language_detection_agreement"] = result.agreement
    latest_data["language_detection_votes"] = [
        {
            "method": v.method,
            "language": v.language,
            "confidence": round(v.confidence, 3),
        }
        for v in result.votes
    ]

    # Create new version
    new_version = {
        "version": current_version + 1,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "enrich_mlt19_language.py",
        "method": "tier_2_ml_inference",
        "description": "Layer 2 multi-factor consensus language detection",
        "git_sha": git_sha,
        "data": latest_data,
    }

    versions.append(new_version)
    sample["enrichments"] = {
        "current_version": current_version + 1,
        "versions": versions,
    }


def download_fasttext_model(model_dir: Path) -> Path:
    """Download fastText language identification model."""
    import urllib.request

    model_path = model_dir / "lid.176.bin"
    if model_path.exists():
        logger.info(f"Model already exists: {model_path}")
        return model_path

    model_dir.mkdir(parents=True, exist_ok=True)

    url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
    logger.info(f"Downloading fastText model from {url}")
    logger.info("This is a 126MB download, please wait...")

    urllib.request.urlretrieve(
        url, model_path
    )  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
    logger.info(f"Model saved to {model_path}")

    return model_path


def _init_mlt19_fasttext(model_dir: Path) -> Any | None:
    """Initialize fastText model for MLT-19 enrichment."""
    try:
        import fasttext

        model_path = model_dir / "lid.176.bin"
        if model_path.exists():
            logger.info("Loading fastText model...")
            return fasttext.load_model(str(model_path))
        logger.warning(f"fastText model not found at {model_path}")
        logger.warning("Run with --download-model to download it")
    except ImportError:
        logger.warning("fastText not installed. Run: uv add fasttext")
    return None


def _init_mlt19_lingua() -> Any | None:
    """Initialize lingua detector for MLT-19 enrichment."""
    try:
        from lingua import LanguageDetectorBuilder

        logger.info("Initializing lingua detector...")
        return LanguageDetectorBuilder.from_all_languages().build()
    except ImportError:
        logger.warning("lingua not installed. Run: uv add lingua-language-detector")
    return None


def _init_mlt19_easyocr() -> Any | None:
    """Initialize EasyOCR reader for MLT-19 text extraction."""
    try:
        import easyocr

        logger.info("Initializing EasyOCR reader...")
        return easyocr.Reader(
            ["en", "ar", "hi", "bn", "ja", "ko", "ch_sim"],
            gpu=True,
        )
    except ImportError:
        logger.warning("EasyOCR not installed. Run: uv add easyocr")
        logger.warning("Will skip text extraction")
    return None


def _filter_und_test_samples(
    samples: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    """Filter samples to test images with 'und' language baseline."""
    return [
        (i, sample)
        for i, sample in enumerate(samples)
        if sample.get("original_labels", {}).get("raw_labels", {}).get("split")
        == "test"
        and sample.get("original_labels", {}).get("language_code") == "und"
    ]


def _detect_mlt19_sample(
    image_path: Path,
    easyocr_reader: Any | None,
    fasttext_model: Any | None,
    lingua_detector: Any | None,
) -> ConsensusResult:
    """Detect language for a single MLT-19 sample."""
    text = extract_text_easyocr(image_path, easyocr_reader) if easyocr_reader else ""

    if not text:
        return ConsensusResult(
            language="und",
            script=None,
            confidence=0.0,
            method="no_text_extracted",
            votes=[],
            agreement=True,
        )

    return consensus_detect(text, fasttext_model, lingua_detector)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich MLT-19 test images with multi-factor language detection"
    )
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--end", type=int, default=None, help="End index")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Save every N images"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(
            "/mnt/e/image_detection/metadata_registry/json/mlt19_metadata.json"
        ),
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=Path("/mnt/e/image_detection/01_base_data/language/mlt19"),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/models/language_detection"),
    )
    parser.add_argument(
        "--download-model", action="store_true", help="Download fastText model"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument(
        "--no-ocr", action="store_true", help="Skip OCR, use existing text only"
    )
    args = parser.parse_args()

    if args.download_model:
        download_fasttext_model(args.model_dir)
        return 0

    fasttext_model = _init_mlt19_fasttext(args.model_dir)
    lingua_detector = _init_mlt19_lingua()
    easyocr_reader = _init_mlt19_easyocr() if not args.no_ocr else None

    if not fasttext_model and not lingua_detector:
        logger.error("No language detection models available!")
        logger.error("Install at least one: uv add fasttext lingua-language-detector")
        return 1

    logger.info(f"Loading metadata from {args.metadata}")
    metadata = load_metadata(args.metadata)
    samples = metadata.get("samples", [])

    test_samples = _filter_und_test_samples(samples)
    logger.info(f"Found {len(test_samples)} test images needing enrichment")

    end_idx = args.end or len(test_samples)
    test_samples = test_samples[args.start : end_idx]
    logger.info(
        f"Processing {len(test_samples)} images (index {args.start} to {end_idx})"
    )

    if not test_samples:
        logger.info("No images to process")
        return 0

    processed = 0
    consensus_count = 0
    no_consensus_count = 0

    for idx, (sample_idx, sample) in enumerate(test_samples):
        orig_path = sample.get("source", {}).get("original_path", "")
        image_path = args.dataset_path / orig_path

        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            continue

        result = _detect_mlt19_sample(
            image_path,
            easyocr_reader,
            fasttext_model,
            lingua_detector,
        )
        update_enrichment(samples[sample_idx], result)

        if result.agreement:
            consensus_count += 1
        else:
            no_consensus_count += 1
        processed += 1

        if processed % 100 == 0:
            logger.info(
                f"Processed {processed}/{len(test_samples)} | "
                f"Consensus: {consensus_count} | No consensus: {no_consensus_count}"
            )

        if not args.dry_run and processed % args.batch_size == 0:
            logger.info(f"Saving checkpoint at {processed} images...")
            save_metadata(metadata, args.metadata)

    if not args.dry_run:
        logger.info("Saving final results...")
        save_metadata(metadata, args.metadata)

    logger.info("=" * 60)
    logger.info(f"Completed: {processed} images processed")
    logger.info(
        f"Consensus achieved: {consensus_count} ({consensus_count / processed * 100:.1f}%)"
    )
    logger.info(
        f"No consensus: {no_consensus_count} ({no_consensus_count / processed * 100:.1f}%)"
    )

    return 0


if __name__ == "__main__":
    exit(main())
