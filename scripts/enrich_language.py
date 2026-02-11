#!/usr/bin/env python3
"""Generic Layer 2 Language Enrichment Tool.

Reusable multi-factor consensus language detection for ANY dataset with missing
language/script identifiers. Properly handles multi-language documents.

Key Features:
1. Works with any dataset in the metadata registry
2. Detects ALL languages present in a document (not just dominant)
3. Reports multi-language documents with full list: `["en", "dz"]` (English AND Dzongkha)
4. Uses ISO 639-1/2/3 for languages, ISO 15924 for scripts
5. Multi-factor consensus: 2-of-2 agreement, or 2-of-3 majority on disagreement

Detection Methods:
- Unicode script analysis: Deterministic, always available, detects ALL scripts
- fastText (lid.176.bin): 176 languages, good for short text
- lingua-py: 75 languages, high accuracy

Multi-Language Handling:
- Each script/language found is counted separately
- Documents with significant presence of multiple languages get `mul` code
- Full list of detected languages stored in `detected_languages` field
- Example: Bhutan doc with English AND Dzongkha → `mul` with `["en", "dz"]`

Usage:
    # Install dependencies (one-time)
    uv add fasttext lingua-language-detector easyocr --optional language-detection

    # Download fastText model (one-time)
    uv run python scripts/enrich_language.py --download-model

    # List datasets needing enrichment
    uv run python scripts/enrich_language.py --list-datasets

    # Enrich specific dataset
    uv run python scripts/enrich_language.py --dataset mlt19

    # Enrich all datasets with missing languages
    uv run python scripts/enrich_language.py --all
"""

import argparse
import json
import logging
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
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
# Configuration
# =============================================================================

METADATA_REGISTRY_PATH = Path("/mnt/e/image_detection/metadata_registry/json")
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")
MODEL_DIR = Path("/mnt/e/image_detection/models/language_detection")

# Minimum character threshold to consider a language "present" (not noise)
MIN_CHARS_FOR_LANGUAGE = 5
# Minimum percentage to consider a language "significant" in multi-language doc
MIN_LANGUAGE_PERCENTAGE = 0.10  # 10%


# =============================================================================
# ISO 15924 Script Detection via Unicode
# =============================================================================

# Unicode block to ISO 15924 script mapping (comprehensive)
UNICODE_BLOCK_TO_SCRIPT: dict[tuple[int, int], str] = {
    # Latin scripts
    (0x0041, 0x007A): "Latn",  # Basic Latin
    (0x00C0, 0x00FF): "Latn",  # Latin-1 Supplement
    (0x0100, 0x017F): "Latn",  # Latin Extended-A
    (0x0180, 0x024F): "Latn",  # Latin Extended-B
    (0x1E00, 0x1EFF): "Latn",  # Latin Extended Additional
    (0x2C60, 0x2C7F): "Latn",  # Latin Extended-C
    (0xA720, 0xA7FF): "Latn",  # Latin Extended-D
    # Greek
    (0x0370, 0x03FF): "Grek",
    (0x1F00, 0x1FFF): "Grek",  # Greek Extended
    # Cyrillic
    (0x0400, 0x04FF): "Cyrl",
    (0x0500, 0x052F): "Cyrl",  # Cyrillic Supplement
    (0x2DE0, 0x2DFF): "Cyrl",  # Cyrillic Extended-A
    (0xA640, 0xA69F): "Cyrl",  # Cyrillic Extended-B
    # Armenian
    (0x0530, 0x058F): "Armn",
    # Hebrew
    (0x0590, 0x05FF): "Hebr",
    # Arabic
    (0x0600, 0x06FF): "Arab",
    (0x0750, 0x077F): "Arab",  # Arabic Supplement
    (0x08A0, 0x08FF): "Arab",  # Arabic Extended-A
    (0xFB50, 0xFDFF): "Arab",  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF): "Arab",  # Arabic Presentation Forms-B
    # Syriac
    (0x0700, 0x074F): "Syrc",
    # Thaana (Maldivian)
    (0x0780, 0x07BF): "Thaa",
    # N'Ko
    (0x07C0, 0x07FF): "Nkoo",
    # Samaritan
    (0x0800, 0x083F): "Samr",
    # Mandaic
    (0x0840, 0x085F): "Mand",
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
    (0xAA60, 0xAA7F): "Mymr",  # Myanmar Extended-A
    # Georgian
    (0x10A0, 0x10FF): "Geor",
    (0x2D00, 0x2D2F): "Geor",  # Georgian Supplement
    # Korean Hangul
    (0x1100, 0x11FF): "Hang",  # Hangul Jamo
    (0xAC00, 0xD7AF): "Hang",  # Hangul Syllables
    (0x3130, 0x318F): "Hang",  # Hangul Compatibility Jamo
    (0xA960, 0xA97F): "Hang",  # Hangul Jamo Extended-A
    (0xD7B0, 0xD7FF): "Hang",  # Hangul Jamo Extended-B
    # Ethiopic
    (0x1200, 0x137F): "Ethi",
    (0x1380, 0x139F): "Ethi",  # Ethiopic Supplement
    (0x2D80, 0x2DDF): "Ethi",  # Ethiopic Extended
    # Cherokee
    (0x13A0, 0x13FF): "Cher",
    # Canadian Aboriginal
    (0x1400, 0x167F): "Cans",
    # Ogham
    (0x1680, 0x169F): "Ogam",
    # Runic
    (0x16A0, 0x16FF): "Runr",
    # Tagalog
    (0x1700, 0x171F): "Tglg",
    # Hanunoo
    (0x1720, 0x173F): "Hano",
    # Buhid
    (0x1740, 0x175F): "Buhd",
    # Tagbanwa
    (0x1760, 0x177F): "Tagb",
    # Khmer
    (0x1780, 0x17FF): "Khmr",
    (0x19E0, 0x19FF): "Khmr",  # Khmer Symbols
    # Mongolian
    (0x1800, 0x18AF): "Mong",
    # Limbu
    (0x1900, 0x194F): "Limb",
    # Tai Le
    (0x1950, 0x197F): "Tale",
    # New Tai Lue
    (0x1980, 0x19DF): "Talu",
    # Buginese
    (0x1A00, 0x1A1F): "Bugi",
    # Tai Tham
    (0x1A20, 0x1AAF): "Lana",
    # Balinese
    (0x1B00, 0x1B7F): "Bali",
    # Sundanese
    (0x1B80, 0x1BBF): "Sund",
    # Batak
    (0x1BC0, 0x1BFF): "Batk",
    # Lepcha
    (0x1C00, 0x1C4F): "Lepc",
    # Ol Chiki
    (0x1C50, 0x1C7F): "Olck",
    # Japanese Hiragana
    (0x3040, 0x309F): "Hira",
    # Japanese Katakana
    (0x30A0, 0x30FF): "Kana",
    (0x31F0, 0x31FF): "Kana",  # Katakana Phonetic Extensions
    # Bopomofo
    (0x3100, 0x312F): "Bopo",
    (0x31A0, 0x31BF): "Bopo",  # Bopomofo Extended
    # CJK Unified Ideographs (Han)
    (0x4E00, 0x9FFF): "Hani",
    (0x3400, 0x4DBF): "Hani",  # CJK Extension A
    (0x20000, 0x2A6DF): "Hani",  # CJK Extension B
    (0x2A700, 0x2B73F): "Hani",  # CJK Extension C
    (0x2B740, 0x2B81F): "Hani",  # CJK Extension D
    (0xF900, 0xFAFF): "Hani",  # CJK Compatibility Ideographs
    # Yi
    (0xA000, 0xA48F): "Yiii",
    (0xA490, 0xA4CF): "Yiii",  # Yi Radicals
    # Lisu
    (0xA4D0, 0xA4FF): "Lisu",
    # Vai
    (0xA500, 0xA63F): "Vaii",
    # Bamum
    (0xA6A0, 0xA6FF): "Bamu",
    # Syloti Nagri
    (0xA800, 0xA82F): "Sylo",
    # Phags-pa
    (0xA840, 0xA87F): "Phag",
    # Saurashtra
    (0xA880, 0xA8DF): "Saur",
    # Kayah Li
    (0xA900, 0xA92F): "Kali",
    # Rejang
    (0xA930, 0xA95F): "Rjng",
    # Javanese
    (0xA980, 0xA9DF): "Java",
    # Cham
    (0xAA00, 0xAA5F): "Cham",
    # Tai Viet
    (0xAA80, 0xAADF): "Tavt",
    # Meetei Mayek
    (0xABC0, 0xABFF): "Mtei",
}

# Script to common language mappings (for scripts with dominant language)
# Scripts with None can map to multiple languages
SCRIPT_TO_PRIMARY_LANGUAGE: dict[str, str | None] = {
    "Arab": "ar",  # Arabic (but also Urdu, Persian, Pashto, etc.)
    "Armn": "hy",  # Armenian
    "Bali": "ban",  # Balinese
    "Bamu": "bax",  # Bamum
    "Batk": None,  # Batak (multiple languages)
    "Beng": "bn",  # Bengali/Bangla
    "Bopo": "zh",  # Bopomofo (Chinese)
    "Bugi": "bug",  # Buginese
    "Buhd": "bku",  # Buhid
    "Cans": None,  # Canadian Aboriginal (many languages)
    "Cham": "cjm",  # Cham
    "Cher": "chr",  # Cherokee
    "Cyrl": None,  # Cyrillic (Russian, Ukrainian, Bulgarian, Serbian, etc.)
    "Deva": "hi",  # Devanagari (Hindi, Sanskrit, Marathi, Nepali, etc.)
    "Ethi": "am",  # Ethiopic (Amharic, Tigrinya, etc.)
    "Geor": "ka",  # Georgian
    "Grek": "el",  # Greek
    "Gujr": "gu",  # Gujarati
    "Guru": "pa",  # Gurmukhi (Punjabi)
    "Hang": "ko",  # Hangul (Korean)
    "Hani": None,  # Han (Chinese, Japanese Kanji, Korean Hanja)
    "Hano": "hnn",  # Hanunoo
    "Hebr": "he",  # Hebrew
    "Hira": "ja",  # Hiragana (Japanese)
    "Java": "jv",  # Javanese
    "Kali": "kyu",  # Kayah Li
    "Kana": "ja",  # Katakana (Japanese)
    "Khmr": "km",  # Khmer
    "Knda": "kn",  # Kannada
    "Lana": None,  # Tai Tham (Northern Thai, Tai Lue)
    "Laoo": "lo",  # Lao
    "Latn": None,  # Latin (hundreds of languages)
    "Lepc": "lep",  # Lepcha
    "Limb": "lif",  # Limbu
    "Lisu": "lis",  # Lisu
    "Mand": "mid",  # Mandaic
    "Mlym": "ml",  # Malayalam
    "Mong": "mn",  # Mongolian
    "Mtei": "mni",  # Meetei Mayek
    "Mymr": "my",  # Myanmar (Burmese)
    "Nkoo": None,  # N'Ko (Mandinka, Bambara, etc.)
    "Ogam": "sga",  # Ogham (Old Irish)
    "Olck": "sat",  # Ol Chiki (Santali)
    "Orya": "or",  # Oriya/Odia
    "Phag": None,  # Phags-pa (historical)
    "Rjng": "rej",  # Rejang
    "Runr": None,  # Runic (historical)
    "Samr": "smp",  # Samaritan
    "Saur": "saz",  # Saurashtra
    "Sinh": "si",  # Sinhala
    "Sund": "su",  # Sundanese
    "Sylo": "syl",  # Syloti Nagri
    "Syrc": None,  # Syriac (Aramaic varieties)
    "Tagb": "tbw",  # Tagbanwa
    "Tale": "tdd",  # Tai Le
    "Talu": "khb",  # New Tai Lue
    "Taml": "ta",  # Tamil
    "Tavt": None,  # Tai Viet
    "Telu": "te",  # Telugu
    "Tglg": "tl",  # Tagalog
    "Thaa": "dv",  # Thaana (Dhivehi/Maldivian)
    "Thai": "th",  # Thai
    "Tibt": "bo",  # Tibetan
    "Vaii": "vai",  # Vai
    "Yiii": "ii",  # Yi
}

# Language to script mappings (for inference)
LANGUAGE_TO_SCRIPT: dict[str, str] = {
    # Arabic script languages
    "ar": "Arab",
    "fa": "Arab",  # Persian
    "ur": "Arab",  # Urdu
    "ps": "Arab",  # Pashto
    "ks": "Arab",  # Kashmiri
    "sd": "Arab",  # Sindhi
    "ug": "Arab",  # Uyghur
    "ku": "Arab",  # Kurdish (can also be Latn)
    # Cyrillic languages
    "ru": "Cyrl",
    "uk": "Cyrl",
    "bg": "Cyrl",
    "sr": "Cyrl",  # Serbian (can also be Latn)
    "mk": "Cyrl",
    "kk": "Cyrl",
    "ky": "Cyrl",
    "tg": "Cyrl",
    "mn": "Cyrl",  # Mongolian (modern)
    "be": "Cyrl",  # Belarusian
    # Devanagari languages
    "hi": "Deva",
    "mr": "Deva",  # Marathi
    "ne": "Deva",  # Nepali
    "sa": "Deva",  # Sanskrit
    "bho": "Deva",  # Bhojpuri
    "mai": "Deva",  # Maithili
    "kok": "Deva",  # Konkani
    # South Asian scripts
    "bn": "Beng",  # Bengali
    "as": "Beng",  # Assamese
    "gu": "Gujr",
    "pa": "Guru",
    "or": "Orya",
    "ta": "Taml",
    "te": "Telu",
    "kn": "Knda",
    "ml": "Mlym",
    "si": "Sinh",
    # East Asian
    "zh": "Hans",  # Simplified Chinese
    "ja": "Jpan",  # Japanese (mixed scripts)
    "ko": "Kore",  # Korean (mixed scripts)
    # Southeast Asian
    "th": "Thai",
    "lo": "Laoo",
    "km": "Khmr",
    "my": "Mymr",
    "vi": "Latn",  # Vietnamese
    # Others
    "el": "Grek",
    "he": "Hebr",
    "yi": "Hebr",
    "hy": "Armn",
    "ka": "Geor",
    "am": "Ethi",
    "ti": "Ethi",  # Tigrinya
    "bo": "Tibt",
    "dz": "Tibt",  # Dzongkha (Bhutan)
    # Latin script languages (partial list)
    "en": "Latn",
    "es": "Latn",
    "fr": "Latn",
    "de": "Latn",
    "it": "Latn",
    "pt": "Latn",
    "nl": "Latn",
    "pl": "Latn",
    "cs": "Latn",
    "sk": "Latn",
    "hu": "Latn",
    "ro": "Latn",
    "fi": "Latn",
    "sv": "Latn",
    "no": "Latn",
    "da": "Latn",
    "tr": "Latn",
    "id": "Latn",
    "ms": "Latn",
    "tl": "Latn",
    "sw": "Latn",
    "hr": "Latn",
    "sl": "Latn",
    "et": "Latn",
    "lv": "Latn",
    "lt": "Latn",
    "sq": "Latn",
    "az": "Latn",
    "uz": "Latn",
    "mt": "Latn",
    "cy": "Latn",
    "ga": "Latn",
    "gd": "Latn",
    "eu": "Latn",
    "ca": "Latn",
    "gl": "Latn",
    "af": "Latn",
    "zu": "Latn",
    "xh": "Latn",
    "st": "Latn",
    "tn": "Latn",
    "sn": "Latn",
    "ny": "Latn",
    "mg": "Latn",
    "ha": "Latn",
    "ig": "Latn",
    "yo": "Latn",
    "so": "Latn",
    "rw": "Latn",
    "la": "Latn",
    "eo": "Latn",
    "jv": "Latn",  # Modern Javanese often uses Latin
    "su": "Latn",  # Modern Sundanese often uses Latin
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ScriptCount:
    """Count of characters in a specific script."""

    script: str  # ISO 15924 code
    count: int
    percentage: float


@dataclass
class LanguageDetection:
    """Single language detection from one method."""

    language: str  # ISO 639-1/2/3 code
    script: str | None  # ISO 15924 code
    confidence: float  # 0.0 - 1.0
    method: str


@dataclass
class MultiLanguageResult:
    """Result that can represent multiple languages in a document."""

    primary_language: str  # ISO 639 code or "mul" for multiple
    primary_script: str | None  # ISO 15924 code
    detected_languages: list[str]  # All languages found (e.g., ["en", "dz"])
    detected_scripts: list[str]  # All scripts found
    confidence: float
    method: str  # Detection method
    agreement: bool  # Whether detection methods agreed
    votes: list[LanguageDetection] = field(default_factory=list)
    script_breakdown: list[ScriptCount] = field(default_factory=list)


# =============================================================================
# Detection Functions
# =============================================================================


def detect_all_scripts(text: str) -> list[ScriptCount]:
    """Detect ALL scripts present in text using Unicode block analysis.

    Returns list of all scripts found, sorted by percentage (descending).
    """
    if not text or not text.strip():
        return []

    script_counts: Counter[str] = Counter()

    for char in text:
        # Skip punctuation, numbers, whitespace
        if char.isspace() or unicodedata.category(char).startswith(
            ("P", "N", "S", "Z")
        ):
            continue

        code = ord(char)

        # Find matching Unicode block
        for (start, end), script in UNICODE_BLOCK_TO_SCRIPT.items():
            if start <= code <= end:
                script_counts[script] += 1
                break

    if not script_counts:
        return []

    total = sum(script_counts.values())
    results = []
    for script, count in script_counts.most_common():
        results.append(
            ScriptCount(script=script, count=count, percentage=count / total)
        )

    return results


def script_to_languages(script: str) -> list[str]:
    """Get possible languages for a given script.

    Returns list of ISO 639 codes that commonly use this script.
    """
    languages = []

    # Check primary language for script
    primary = SCRIPT_TO_PRIMARY_LANGUAGE.get(script)
    if primary:
        languages.append(primary)

    # Check all languages that use this script
    for lang, lang_script in LANGUAGE_TO_SCRIPT.items():
        if lang_script == script and lang not in languages:
            languages.append(lang)

    return languages


def detect_language_fasttext(text: str, model: Any) -> LanguageDetection:
    """Detect language using fastText lid.176.bin model."""
    if not text or not text.strip():
        return LanguageDetection("und", None, 0.0, "fasttext_empty")

    try:
        # Clean text (fastText expects single line)
        clean_text = " ".join(text.split())

        # Predict
        predictions = model.predict(clean_text, k=1)
        label = predictions[0][0]  # '__label__en'
        confidence = float(predictions[1][0])

        # Extract language code
        lang_code = label.replace("__label__", "")
        script = LANGUAGE_TO_SCRIPT.get(lang_code)

        return LanguageDetection(lang_code, script, confidence, "fasttext")

    except Exception as e:
        logger.debug(f"fastText error: {e}")
        return LanguageDetection("und", None, 0.0, "fasttext_error")


def detect_language_openlid(text: str, detector: Any) -> LanguageDetection:
    """Detect language using OpenLID-v2 model.

    OpenLID-v2 provides both language (ISO 639-3) and script (ISO 15924)
    in a single prediction. This function normalizes dialects to their
    macro-language codes for consistency.

    Args:
        text: Text to analyze
        detector: OpenLIDDetector instance

    Returns:
        LanguageDetection with normalized language code
    """
    if not text or not text.strip():
        return LanguageDetection("und", None, 0.0, "openlid_empty")

    try:
        result = detector.detect(text)

        if result.language_639_1 == "und":
            return LanguageDetection("und", None, result.confidence, "openlid_und")

        # Normalize Devanagari dialects to Hindi for routing consistency
        # OpenLID detects: san (Sanskrit), mar (Marathi), bho (Bhojpuri),
        # awa (Awadhi), hne (Chhattisgarhi), mai (Maithili) etc.
        lang_code = result.language_639_1
        if result.script_code == "Deva" and lang_code not in ("hi", "mr", "ne", "sa"):
            # Treat Hindi dialects (Bhojpuri, Awadhi, etc.) as Hindi for routing
            # but preserve the original detection in method name
            return LanguageDetection(
                language="hi",
                script=result.script_code,
                confidence=result.confidence,
                method=f"openlid_deva_variant_{result.language_639_3}",
            )

        # Normalize Arabic dialects to macro-language 'ar'
        # OpenLID detects: arb (MSA), arz (Egyptian), ary (Moroccan),
        # acm (Mesopotamian), apc (Levantine), etc.
        if result.script_code == "Arab" and lang_code == result.language_639_3:
            # This is a 3-letter Arabic variant code, normalize to 'ar'
            # but preserve variant info in method
            return LanguageDetection(
                language="ar",
                script=result.script_code,
                confidence=result.confidence,
                method=f"openlid_arab_variant_{result.language_639_3}",
            )

        return LanguageDetection(
            language=lang_code,
            script=result.script_code,
            confidence=result.confidence,
            method="openlid",
        )

    except Exception as e:
        logger.debug(f"OpenLID error: {e}")
        return LanguageDetection("und", None, 0.0, "openlid_error")


def detect_language_lingua(text: str, detector: Any) -> LanguageDetection:
    """Detect language using lingua-py."""
    if not text or not text.strip():
        return LanguageDetection("und", None, 0.0, "lingua_empty")

    try:
        from lingua import ConfidenceValue

        # Detect with confidence
        result = detector.compute_language_confidence_values(text)

        if not result:
            return LanguageDetection("und", None, 0.0, "lingua_no_result")

        # Get top result
        top: ConfidenceValue = result[0]
        lang_code = top.language.iso_code_639_1.name.lower()
        confidence = top.value
        script = LANGUAGE_TO_SCRIPT.get(lang_code)

        return LanguageDetection(lang_code, script, confidence, "lingua")

    except Exception as e:
        logger.debug(f"lingua error: {e}")
        return LanguageDetection("und", None, 0.0, "lingua_error")


def multi_language_consensus(
    text: str,
    fasttext_model: Any = None,
    lingua_detector: Any = None,
    openlid_detector: Any = None,
) -> MultiLanguageResult:
    """Multi-factor consensus detection that handles multiple languages.

    Detection Priority (updated for OpenLID-v2):
    1. Detect ALL scripts via Unicode (deterministic)
    2. OpenLID-v2 as PRIMARY detector (provides language + script)
    3. lingua as SECONDARY for consensus
    4. fastText lid.176 as FALLBACK
    5. Cross-reference and report ALL significant languages

    OpenLID-v2 Advantages:
    - 200 language varieties with script identification
    - Better for non-Latin scripts (Bengali, Korean, Japanese)
    - Dialect detection (normalized for routing)

    Example: Doc with English AND Dzongkha text
    - Unicode detects: Latn (40%), Tibt (60%)
    - OpenLID detects: en_Latn (0.75), bo_Tibt (0.85)
    - Result: mul, detected_languages=["en", "bo"]
    """
    votes: list[LanguageDetection] = []
    detected_languages: list[str] = []
    detected_scripts: list[str] = []

    # Step 1: Detect ALL scripts via Unicode
    script_breakdown = detect_all_scripts(text)

    if not script_breakdown:
        return MultiLanguageResult(
            primary_language="und",
            primary_script=None,
            detected_languages=[],
            detected_scripts=[],
            confidence=0.0,
            method="no_script_detected",
            agreement=True,
            script_breakdown=[],
        )

    # Identify significant scripts (>= MIN_LANGUAGE_PERCENTAGE)
    significant_scripts = [
        sc for sc in script_breakdown if sc.percentage >= MIN_LANGUAGE_PERCENTAGE
    ]

    detected_scripts = [sc.script for sc in significant_scripts]

    # Step 2: For each significant script, infer possible languages
    script_languages: dict[str, list[str]] = {}
    ambiguous_scripts: list[str] = []  # Scripts needing statistical detection

    for sc in significant_scripts:
        possible_langs = script_to_languages(sc.script)
        if possible_langs:
            script_languages[sc.script] = possible_langs
            # Add primary language to detected list for unambiguous scripts
            primary = SCRIPT_TO_PRIMARY_LANGUAGE.get(sc.script)
            if primary and primary not in detected_languages:
                detected_languages.append(primary)
            elif not primary:
                # Ambiguous script (Latin, Cyrillic, Han) - needs statistical detection
                ambiguous_scripts.append(sc.script)

    # Step 3: Run statistical language detectors
    # OpenLID-v2 is PRIMARY (provides language + script in one call)
    if openlid_detector:
        ol_result = detect_language_openlid(text, openlid_detector)
        votes.append(ol_result)
        if ol_result.language != "und" and ol_result.language not in detected_languages:
            detected_languages.append(ol_result.language)
        # OpenLID also provides script - validate against Unicode detection
        if ol_result.script and ol_result.script not in detected_scripts:
            # OpenLID detected a script not in Unicode analysis (rare)
            detected_scripts.append(ol_result.script)

    # lingua as SECONDARY for consensus
    if lingua_detector:
        lg_result = detect_language_lingua(text, lingua_detector)
        votes.append(lg_result)
        if lg_result.language != "und" and lg_result.language not in detected_languages:
            detected_languages.append(lg_result.language)

    # fastText lid.176 as FALLBACK (only if OpenLID not available)
    if fasttext_model and not openlid_detector:
        ft_result = detect_language_fasttext(text, fasttext_model)
        votes.append(ft_result)
        if ft_result.language != "und" and ft_result.language not in detected_languages:
            detected_languages.append(ft_result.language)

    # Step 4: Determine primary language
    # If multiple significant scripts → multi-language document
    if len(significant_scripts) > 1:
        # Check for Japanese (uses Hira + Kana + Hani together)
        script_set = set(detected_scripts)
        if script_set & {"Hira", "Kana"} and "Hani" in script_set:
            # This is Japanese using mixed scripts (not multi-language)
            return MultiLanguageResult(
                primary_language="ja",
                primary_script="Jpan",
                detected_languages=["ja"],
                detected_scripts=detected_scripts,
                confidence=0.9,
                method="japanese_mixed_script",
                agreement=True,
                votes=votes,
                script_breakdown=script_breakdown,
            )

        # Check for Korean (uses Hang + sometimes Hani)
        if "Hang" in script_set:
            if "Hani" in script_set and len(script_set) == 2:
                return MultiLanguageResult(
                    primary_language="ko",
                    primary_script="Kore",
                    detected_languages=["ko"],
                    detected_scripts=detected_scripts,
                    confidence=0.9,
                    method="korean_mixed_script",
                    agreement=True,
                    votes=votes,
                    script_breakdown=script_breakdown,
                )

        # Genuine multi-language document
        return MultiLanguageResult(
            primary_language="mul",
            primary_script=significant_scripts[0].script,  # Most common
            detected_languages=detected_languages,
            detected_scripts=detected_scripts,
            confidence=0.85,
            method="multi_script_detected",
            agreement=True,
            votes=votes,
            script_breakdown=script_breakdown,
        )

    # Single script - check detector agreement
    primary_script = significant_scripts[0].script

    # Check if detectors agree
    if len(votes) >= 2:
        v1, v2 = votes[0], votes[1]
        if v1.language == v2.language and v1.language != "und":
            avg_conf = (v1.confidence + v2.confidence) / 2
            return MultiLanguageResult(
                primary_language=v1.language,
                primary_script=primary_script,
                detected_languages=[v1.language],
                detected_scripts=detected_scripts,
                confidence=avg_conf,
                method="consensus_2of2",
                agreement=True,
                votes=votes,
                script_breakdown=script_breakdown,
            )

    # No consensus - use best guess from script + detectors
    if votes and any(v.language != "und" for v in votes):
        best_vote = max(
            [v for v in votes if v.language != "und"],
            key=lambda v: v.confidence,
        )
        return MultiLanguageResult(
            primary_language=best_vote.language,
            primary_script=primary_script,
            detected_languages=[best_vote.language],
            detected_scripts=detected_scripts,
            confidence=best_vote.confidence * 0.8,  # Reduce for no consensus
            method="highest_confidence",
            agreement=False,
            votes=votes,
            script_breakdown=script_breakdown,
        )

    # Fall back to script-based inference
    primary_lang = SCRIPT_TO_PRIMARY_LANGUAGE.get(primary_script, "und")

    # Confidence depends on script ambiguity:
    # - Latin/Cyrillic/Han: Low confidence (many possible languages)
    # - Other scripts: High confidence (script strongly determines language)
    ambiguous_scripts = {"Latn", "Cyrl", "Hani", "Arab"}
    base_confidence = significant_scripts[0].percentage
    if primary_script in ambiguous_scripts:
        # Reduce confidence for ambiguous scripts - language uncertain
        confidence = base_confidence * 0.4
        method = "script_inference_ambiguous"
    else:
        # High confidence for unambiguous scripts
        confidence = base_confidence * 0.85
        method = "script_inference"

    return MultiLanguageResult(
        primary_language=primary_lang or "und",
        primary_script=primary_script,
        detected_languages=[primary_lang] if primary_lang else [],
        detected_scripts=detected_scripts,
        confidence=confidence,
        method=method,
        agreement=True,
        votes=votes,
        script_breakdown=script_breakdown,
    )


def extract_text_easyocr(image_path: Path, reader: Any) -> str:
    """Extract text from image using EasyOCR."""
    try:
        results = reader.readtext(str(image_path), detail=0)
        return " ".join(results) if results else ""
    except Exception as e:
        logger.debug(f"EasyOCR error for {image_path}: {e}")
        return ""


# =============================================================================
# Metadata Operations
# =============================================================================


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
    result: MultiLanguageResult,
    git_sha: str = "manual",
) -> None:
    """Update sample's enrichment layer with multi-language detection result."""
    enrichments = sample.get("enrichments", {})
    current_version = enrichments.get("current_version", 0)
    versions = enrichments.get("versions", [])

    # Get latest data or empty dict
    latest_data = versions[-1].get("data", {}).copy() if versions else {}

    # Update language fields
    latest_data["iso639_language"] = result.primary_language
    if result.primary_script:
        latest_data["iso15924_script"] = result.primary_script

    # Multi-language support: store full list
    latest_data["detected_languages"] = result.detected_languages
    latest_data["detected_scripts"] = result.detected_scripts

    # Add detection metadata
    latest_data["language_detection_method"] = result.method
    latest_data["language_detection_confidence"] = round(result.confidence, 3)
    latest_data["language_detection_agreement"] = result.agreement

    # Store votes for audit trail
    latest_data["language_detection_votes"] = [
        {
            "method": v.method,
            "language": v.language,
            "confidence": round(v.confidence, 3),
        }
        for v in result.votes
    ]

    # Store script breakdown
    latest_data["script_breakdown"] = [
        {"script": sc.script, "count": sc.count, "percentage": round(sc.percentage, 3)}
        for sc in result.script_breakdown
    ]

    # Create new version
    new_version = {
        "version": current_version + 1,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "enrich_language.py",
        "method": "tier_2_ml_inference",
        "description": "Layer 2 multi-factor multi-language detection",
        "git_sha": git_sha,
        "data": latest_data,
    }

    versions.append(new_version)
    sample["enrichments"] = {
        "current_version": current_version + 1,
        "versions": versions,
    }


def find_datasets_needing_enrichment() -> list[tuple[str, Path, int]]:
    """Find all datasets with samples missing language codes.

    Returns list of (dataset_name, metadata_path, count_needing_enrichment).
    """
    results = []

    for metadata_file in METADATA_REGISTRY_PATH.glob("*_metadata.json"):
        dataset_name = metadata_file.stem.replace("_metadata", "")

        try:
            metadata = load_metadata(metadata_file)
            samples = metadata.get("samples", [])

            # Count samples needing enrichment
            needs_enrichment = 0
            for sample in samples:
                orig_labels = sample.get("original_labels", {})
                lang_code = orig_labels.get("language_code")

                # Needs enrichment if missing, "und", or empty
                if not lang_code or lang_code == "und":
                    needs_enrichment += 1

            if needs_enrichment > 0:
                results.append((dataset_name, metadata_file, needs_enrichment))

        except Exception as e:
            logger.warning(f"Error reading {metadata_file}: {e}")

    return sorted(results, key=lambda x: x[2], reverse=True)


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


# =============================================================================
# Main Entry Point
# =============================================================================


def process_dataset(
    dataset_name: str,
    metadata_path: Path,
    fasttext_model: Any,
    lingua_detector: Any,
    easyocr_reader: Any | None,
    openlid_detector: Any | None = None,
    start_idx: int = 0,
    end_idx: int | None = None,
    batch_size: int = 100,
    dry_run: bool = False,
) -> dict[str, int]:
    """Process a single dataset for language enrichment.

    Args:
        dataset_name: Name of the dataset
        metadata_path: Path to metadata JSON
        fasttext_model: lid.176.bin model (fallback)
        lingua_detector: lingua-py detector (secondary)
        easyocr_reader: EasyOCR reader for text extraction
        openlid_detector: OpenLID-v2 detector (primary) - recommended
        start_idx: Starting sample index
        end_idx: Ending sample index
        batch_size: Checkpoint save frequency
        dry_run: If True, don't save changes

    Returns:
        Stats dict with processing counts.
    """
    logger.info(f"Loading metadata from {metadata_path}")
    metadata = load_metadata(metadata_path)
    samples = metadata.get("samples", [])

    # Find dataset base path from metadata or config
    dataset_info = metadata.get("dataset_info", {})
    base_path = dataset_info.get("base_path")

    if not base_path:
        # Try common patterns
        for category in ["language", "document_ocr", "receipts", "forms", "tables"]:
            test_path = BASE_DATA_PATH / category / dataset_name
            if test_path.exists():
                base_path = str(test_path)
                break

    if not base_path:
        logger.warning(f"Could not determine base path for {dataset_name}")
        base_path = str(BASE_DATA_PATH)

    dataset_path = Path(base_path)

    # Filter to samples needing enrichment
    samples_to_process: list[tuple[int, dict[str, Any]]] = []
    for i, sample in enumerate(samples):
        orig_labels = sample.get("original_labels", {})
        lang_code = orig_labels.get("language_code")

        if not lang_code or lang_code == "und":
            samples_to_process.append((i, sample))

    logger.info(f"Found {len(samples_to_process)} samples needing language enrichment")

    # Apply slice
    end = end_idx if end_idx else len(samples_to_process)
    samples_to_process = samples_to_process[start_idx:end]
    logger.info(
        f"Processing {len(samples_to_process)} samples (index {start_idx} to {end})"
    )

    if not samples_to_process:
        return {
            "processed": 0,
            "multi_language": 0,
            "single_language": 0,
            "undetermined": 0,
        }

    # Process samples
    stats = {
        "processed": 0,
        "multi_language": 0,
        "single_language": 0,
        "undetermined": 0,
    }

    for idx, (sample_idx, sample) in enumerate(samples_to_process):
        source = sample.get("source", {})
        orig_path = source.get("original_path", "")

        # Try multiple path resolutions
        image_path = None
        for candidate in [
            dataset_path / orig_path,
            Path(orig_path),
            BASE_DATA_PATH / orig_path,
        ]:
            if candidate.exists():
                image_path = candidate
                break

        if not image_path:
            logger.debug(f"Image not found: {orig_path}")
            continue

        # Extract text from image
        text = ""
        if easyocr_reader:
            text = extract_text_easyocr(image_path, easyocr_reader)

        if not text:
            # No text extracted
            result = MultiLanguageResult(
                primary_language="und",
                primary_script=None,
                detected_languages=[],
                detected_scripts=[],
                confidence=0.0,
                method="no_text_extracted",
                agreement=True,
                script_breakdown=[],
            )
            stats["undetermined"] += 1
        else:
            # Run multi-language consensus detection
            # OpenLID-v2 is primary, lingua secondary, fastText fallback
            result = multi_language_consensus(
                text,
                fasttext_model=fasttext_model,
                lingua_detector=lingua_detector,
                openlid_detector=openlid_detector,
            )

            if result.primary_language == "mul":
                stats["multi_language"] += 1
            elif result.primary_language == "und":
                stats["undetermined"] += 1
            else:
                stats["single_language"] += 1

        # Update enrichment layer
        update_enrichment(samples[sample_idx], result)
        stats["processed"] += 1

        # Progress logging
        if stats["processed"] % 100 == 0:
            logger.info(
                f"Processed {stats['processed']}/{len(samples_to_process)} | "
                f"Multi: {stats['multi_language']} | Single: {stats['single_language']} | "
                f"Und: {stats['undetermined']}"
            )

        # Save checkpoint
        if not dry_run and stats["processed"] % batch_size == 0:
            logger.info(f"Saving checkpoint at {stats['processed']} samples...")
            save_metadata(metadata, metadata_path)

    # Final save
    if not dry_run and stats["processed"] > 0:
        logger.info("Saving final results...")
        save_metadata(metadata, metadata_path)

    return stats


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich datasets with multi-factor multi-language detection"
    )
    parser.add_argument("--dataset", type=str, help="Specific dataset name to process")
    parser.add_argument(
        "--all", action="store_true", help="Process all datasets needing enrichment"
    )
    parser.add_argument(
        "--list-datasets", action="store_true", help="List datasets needing enrichment"
    )
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--end", type=int, default=None, help="End index")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Save every N samples"
    )
    parser.add_argument(
        "--model-dir", type=Path, default=MODEL_DIR, help="Language model directory"
    )
    parser.add_argument(
        "--download-model", action="store_true", help="Download fastText model"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument(
        "--no-ocr", action="store_true", help="Skip OCR, use metadata text only"
    )
    parser.add_argument(
        "--ocr-languages",
        type=str,
        default="en,ar,hi,bn,ja,ko,ch_sim",  # Compatible subset
        help="Comma-separated EasyOCR languages (must be compatible)",
    )
    parser.add_argument(
        "--no-openlid",
        action="store_true",
        help="Disable OpenLID-v2 (use lid.176.bin instead)",
    )
    args = parser.parse_args()

    # List datasets mode
    if args.list_datasets:
        datasets = find_datasets_needing_enrichment()
        if not datasets:
            logger.info("No datasets need language enrichment!")
            return 0

        logger.info(f"Found {len(datasets)} datasets needing enrichment:")
        for name, path, count in datasets:
            logger.info(f"  {name}: {count:,} samples need enrichment")
        return 0

    # Download model mode
    if args.download_model:
        download_fasttext_model(args.model_dir)
        return 0

    # Determine datasets to process
    if args.dataset:
        metadata_path = METADATA_REGISTRY_PATH / f"{args.dataset}_metadata.json"
        if not metadata_path.exists():
            logger.error(f"Metadata not found: {metadata_path}")
            return 1
        datasets_to_process = [(args.dataset, metadata_path)]
    elif args.all:
        datasets_needing = find_datasets_needing_enrichment()
        datasets_to_process = [(name, path) for name, path, _ in datasets_needing]
    else:
        parser.print_help()
        return 1

    if not datasets_to_process:
        logger.info("No datasets to process")
        return 0

    # Initialize detection models
    fasttext_model = None
    lingua_detector = None
    openlid_detector = None
    easyocr_reader = None

    # Load OpenLID-v2 (PRIMARY - recommended)
    if not args.no_openlid:
        try:
            from image_preprocessing_detector.schema_utils.openlid_integration import (
                OpenLIDDetector,
            )

            logger.info("Initializing OpenLID-v2 detector (primary)...")
            openlid_detector = OpenLIDDetector(auto_download=True)
            # Warm up the model
            openlid_detector.detect("test")
            logger.info("OpenLID-v2 ready (200 languages, provides script detection)")
        except ImportError:
            logger.warning("OpenLID integration not available")
        except Exception as e:
            logger.warning(f"OpenLID-v2 initialization error: {e}")

    # Load fastText lid.176.bin (FALLBACK - only if OpenLID not available)
    if not openlid_detector:
        try:
            import fasttext

            model_path = args.model_dir / "lid.176.bin"
            if model_path.exists():
                logger.info("Loading fastText lid.176.bin model (fallback)...")
                fasttext_model = fasttext.load_model(str(model_path))
            else:
                logger.warning(f"fastText model not found at {model_path}")
                logger.warning("Run with --download-model to download it")
        except ImportError:
            logger.warning("fastText not installed. Run: uv add fasttext")

    # Load lingua (SECONDARY - for consensus)
    try:
        from lingua import LanguageDetectorBuilder

        logger.info("Initializing lingua detector (secondary)...")
        lingua_detector = LanguageDetectorBuilder.from_all_languages().build()
    except ImportError:
        logger.warning("lingua not installed. Run: uv add lingua-language-detector")

    # Load EasyOCR
    if not args.no_ocr:
        try:
            import easyocr

            ocr_langs = args.ocr_languages.split(",")
            logger.info(f"Initializing EasyOCR reader for languages: {ocr_langs}")
            easyocr_reader = easyocr.Reader(ocr_langs, gpu=True)
        except ImportError:
            logger.warning("EasyOCR not installed. Run: uv add easyocr")
        except Exception as e:
            logger.warning(f"EasyOCR initialization error: {e}")

    if not openlid_detector and not fasttext_model and not lingua_detector:
        logger.error("No language detection models available!")
        logger.error("Install OpenLID-v2 (recommended) or fastText/lingua")
        return 1

    # Log detection strategy
    if openlid_detector:
        logger.info("Detection strategy: OpenLID-v2 (primary) + lingua (consensus)")
    else:
        logger.info("Detection strategy: fastText (primary) + lingua (consensus)")

    # Process datasets
    total_stats = {
        "processed": 0,
        "multi_language": 0,
        "single_language": 0,
        "undetermined": 0,
    }

    for dataset_name, metadata_path in datasets_to_process:
        logger.info("=" * 60)
        logger.info(f"Processing dataset: {dataset_name}")

        stats = process_dataset(
            dataset_name=dataset_name,
            metadata_path=metadata_path,
            fasttext_model=fasttext_model,
            lingua_detector=lingua_detector,
            easyocr_reader=easyocr_reader,
            openlid_detector=openlid_detector,
            start_idx=args.start,
            end_idx=args.end,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

        for key in total_stats:
            total_stats[key] += stats[key]

        logger.info(f"Dataset {dataset_name} complete: {stats}")

    # Final summary
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info(f"Total processed: {total_stats['processed']:,}")
    logger.info(f"Multi-language documents: {total_stats['multi_language']:,}")
    logger.info(f"Single-language documents: {total_stats['single_language']:,}")
    logger.info(f"Undetermined: {total_stats['undetermined']:,}")

    return 0


if __name__ == "__main__":
    exit(main())
