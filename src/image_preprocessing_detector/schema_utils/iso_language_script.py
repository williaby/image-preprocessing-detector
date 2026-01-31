"""ISO Language and Script Code Standards.

This module provides ISO-compliant language and script metadata for documents.

Standards Used:
- ISO 639-1: 2-letter language codes (primary)
- ISO 639-3: 3-letter language codes (extended)
- ISO 15924: 4-letter script codes
- BCP 47/IETF: Combined language-script tags (e.g., "zh-Hans")

References:
- ISO 639: https://www.loc.gov/standards/iso639-2/php/code_list.php
- ISO 15924: https://unicode.org/iso15924/iso15924-codes.html
- BCP 47: https://www.rfc-editor.org/info/bcp47
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class ISO15924Script(str, Enum):
    """ISO 15924 Script Codes.

    4-letter codes for writing systems.
    Only includes scripts relevant to document processing.
    """

    # Latin-derived
    LATN = "Latn"  # Latin

    # CJK
    HANS = "Hans"  # Han (Simplified)
    HANT = "Hant"  # Han (Traditional)
    JPAN = "Jpan"  # Japanese (Han + Hiragana + Katakana)
    KORE = "Kore"  # Korean (Hangul + Han)
    HANI = "Hani"  # Han (generic, use Hans/Hant when known)

    # South Asian
    DEVA = "Deva"  # Devanagari (Hindi, Sanskrit, Nepali, Marathi)
    BENG = "Beng"  # Bengali/Bangla
    TAML = "Taml"  # Tamil
    TELU = "Telu"  # Telugu
    GUJR = "Gujr"  # Gujarati
    KNDA = "Knda"  # Kannada
    MLYM = "Mlym"  # Malayalam
    ORYA = "Orya"  # Odia/Oriya
    SINH = "Sinh"  # Sinhala
    GURU = "Guru"  # Gurmukhi (Punjabi)

    # Southeast Asian
    THAI = "Thai"  # Thai
    KHMR = "Khmr"  # Khmer
    MYMR = "Mymr"  # Myanmar/Burmese
    LAOO = "Laoo"  # Lao
    TIBT = "Tibt"  # Tibetan

    # Middle Eastern
    ARAB = "Arab"  # Arabic
    HEBR = "Hebr"  # Hebrew

    # European
    CYRL = "Cyrl"  # Cyrillic
    GREK = "Grek"  # Greek
    ARMN = "Armn"  # Armenian
    GEOR = "Geor"  # Georgian

    # Other
    ETHI = "Ethi"  # Ethiopic/Ge'ez
    HANG = "Hang"  # Hangul (Korean alphabet only)
    HIRA = "Hira"  # Hiragana
    KANA = "Kana"  # Katakana

    # Special
    ZYYY = "Zyyy"  # Common (punctuation, numbers)
    ZINH = "Zinh"  # Inherited
    ZZZZ = "Zzzz"  # Unknown/Undetermined


class ISO639Language(str, Enum):
    """ISO 639-1 Language Codes.

    2-letter codes for major languages.
    Extended with ISO 639-3 for languages without 639-1 codes.
    """

    # Major European
    EN = "en"  # English
    ES = "es"  # Spanish
    FR = "fr"  # French
    DE = "de"  # German
    IT = "it"  # Italian
    PT = "pt"  # Portuguese
    NL = "nl"  # Dutch
    PL = "pl"  # Polish
    RU = "ru"  # Russian
    UK = "uk"  # Ukrainian
    CS = "cs"  # Czech
    RO = "ro"  # Romanian
    EL = "el"  # Greek
    HU = "hu"  # Hungarian
    SV = "sv"  # Swedish
    DA = "da"  # Danish
    NO = "no"  # Norwegian
    FI = "fi"  # Finnish

    # Asian
    ZH = "zh"  # Chinese
    JA = "ja"  # Japanese
    KO = "ko"  # Korean
    VI = "vi"  # Vietnamese
    TH = "th"  # Thai
    ID = "id"  # Indonesian
    MS = "ms"  # Malay

    # South Asian
    HI = "hi"  # Hindi
    BN = "bn"  # Bengali
    PA = "pa"  # Punjabi
    TA = "ta"  # Tamil
    TE = "te"  # Telugu
    MR = "mr"  # Marathi
    GU = "gu"  # Gujarati
    KN = "kn"  # Kannada
    ML = "ml"  # Malayalam
    NE = "ne"  # Nepali
    SI = "si"  # Sinhala
    UR = "ur"  # Urdu

    # Middle Eastern
    AR = "ar"  # Arabic
    FA = "fa"  # Persian/Farsi
    HE = "he"  # Hebrew
    TR = "tr"  # Turkish

    # African
    AM = "am"  # Amharic
    SW = "sw"  # Swahili

    # Other
    TL = "tl"  # Tagalog/Filipino
    KM = "km"  # Khmer
    LO = "lo"  # Lao
    MY = "my"  # Burmese
    BO = "bo"  # Tibetan
    DZ = "dz"  # Dzongkha

    # Special
    UND = "und"  # Undetermined
    MUL = "mul"  # Multiple languages
    ZXX = "zxx"  # No linguistic content


# Mapping from script to typical languages
SCRIPT_TO_LANGUAGES: dict[str, list[str]] = {
    "Latn": [
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "nl",
        "pl",
        "cs",
        "ro",
        "hu",
        "sv",
        "da",
        "no",
        "fi",
        "vi",
        "id",
        "ms",
        "tl",
        "sw",
    ],
    "Hans": ["zh"],
    "Hant": ["zh"],
    "Jpan": ["ja"],
    "Kore": ["ko"],
    "Deva": ["hi", "mr", "ne", "sa"],
    "Beng": ["bn"],
    "Taml": ["ta"],
    "Telu": ["te"],
    "Gujr": ["gu"],
    "Knda": ["kn"],
    "Mlym": ["ml"],
    "Guru": ["pa"],
    "Sinh": ["si"],
    "Thai": ["th"],
    "Khmr": ["km"],
    "Mymr": ["my"],
    "Laoo": ["lo"],
    "Tibt": ["bo", "dz"],
    "Arab": ["ar", "fa", "ur"],
    "Hebr": ["he"],
    "Cyrl": ["ru", "uk", "bg", "sr", "mk"],
    "Grek": ["el"],
    "Armn": ["hy"],
    "Geor": ["ka"],
    "Ethi": ["am", "ti"],
}

# Mapping from language to default script
LANGUAGE_TO_DEFAULT_SCRIPT: dict[str, str] = {
    "en": "Latn",
    "es": "Latn",
    "fr": "Latn",
    "de": "Latn",
    "it": "Latn",
    "pt": "Latn",
    "zh": "Hans",  # Default to Simplified; use zh-Hant for Traditional
    "ja": "Jpan",
    "ko": "Kore",
    "hi": "Deva",
    "bn": "Beng",
    "ta": "Taml",
    "te": "Telu",
    "mr": "Deva",
    "gu": "Gujr",
    "kn": "Knda",
    "ml": "Mlym",
    "pa": "Guru",
    "ne": "Deva",
    "si": "Sinh",
    "ar": "Arab",
    "fa": "Arab",
    "ur": "Arab",
    "he": "Hebr",
    "ru": "Cyrl",
    "uk": "Cyrl",
    "el": "Grek",
    "th": "Thai",
    "km": "Khmr",
    "my": "Mymr",
    "lo": "Laoo",
    "bo": "Tibt",
    "dz": "Tibt",
    "am": "Ethi",
    "vi": "Latn",
    "id": "Latn",
    "ms": "Latn",
    "tr": "Latn",
    "sw": "Latn",
}


class ScriptFamily(str, Enum):
    """High-level script family groupings for routing decisions."""

    LATIN = "latin"
    CJK = "cjk"
    ARABIC = "arabic"
    INDIC = "indic"
    CYRILLIC = "cyrillic"
    OTHER = "other"


# Map ISO 15924 scripts to families
SCRIPT_TO_FAMILY: dict[str, ScriptFamily] = {
    "Latn": ScriptFamily.LATIN,
    "Hans": ScriptFamily.CJK,
    "Hant": ScriptFamily.CJK,
    "Jpan": ScriptFamily.CJK,
    "Kore": ScriptFamily.CJK,
    "Hani": ScriptFamily.CJK,
    "Hang": ScriptFamily.CJK,
    "Hira": ScriptFamily.CJK,
    "Kana": ScriptFamily.CJK,
    "Arab": ScriptFamily.ARABIC,
    "Hebr": ScriptFamily.ARABIC,  # RTL family
    "Deva": ScriptFamily.INDIC,
    "Beng": ScriptFamily.INDIC,
    "Taml": ScriptFamily.INDIC,
    "Telu": ScriptFamily.INDIC,
    "Gujr": ScriptFamily.INDIC,
    "Knda": ScriptFamily.INDIC,
    "Mlym": ScriptFamily.INDIC,
    "Orya": ScriptFamily.INDIC,
    "Sinh": ScriptFamily.INDIC,
    "Guru": ScriptFamily.INDIC,
    "Thai": ScriptFamily.INDIC,
    "Khmr": ScriptFamily.INDIC,
    "Mymr": ScriptFamily.INDIC,
    "Laoo": ScriptFamily.INDIC,
    "Tibt": ScriptFamily.INDIC,
    "Cyrl": ScriptFamily.CYRILLIC,
    "Grek": ScriptFamily.OTHER,
    "Armn": ScriptFamily.OTHER,
    "Geor": ScriptFamily.OTHER,
    "Ethi": ScriptFamily.OTHER,
}


@dataclass(frozen=True)
class LanguageScriptTag:
    """BCP 47 / IETF Language Tag.

    Combines ISO 639 language with ISO 15924 script.
    Format: language[-script][-region]

    Examples:
        - "en" (English, Latin implied)
        - "zh-Hans" (Chinese, Simplified Han)
        - "zh-Hant" (Chinese, Traditional Han)
        - "sr-Cyrl" (Serbian, Cyrillic)
        - "sr-Latn" (Serbian, Latin)
    """

    language: str  # ISO 639-1/3 code
    script: str | None = None  # ISO 15924 code
    region: str | None = None  # ISO 3166-1 alpha-2

    def __post_init__(self) -> None:
        """Validate language tag components."""
        # Validate language code
        if not (2 <= len(self.language) <= 3):
            raise ValueError(f"Invalid language code: {self.language}")
        if self.script and len(self.script) != 4:
            raise ValueError(f"Invalid script code: {self.script}")
        if self.region and len(self.region) != 2:
            raise ValueError(f"Invalid region code: {self.region}")

    @classmethod
    def parse(cls, tag: str) -> LanguageScriptTag:
        """Parse a BCP 47 language tag.

        Args:
            tag: Language tag like "en", "zh-Hans", "sr-Cyrl-RS"

        Returns:
            LanguageScriptTag instance
        """
        parts = tag.split("-")
        language = parts[0].lower()
        script = None
        region = None

        for part in parts[1:]:
            if len(part) == 4 and part[0].isupper():
                # Script code (4 chars, Title case)
                script = part
            elif len(part) == 2 and part.isupper():
                # Region code (2 chars, uppercase)
                region = part

        return cls(language=language, script=script, region=region)

    def to_tag(self) -> str:
        """Convert to BCP 47 tag string."""
        parts = [self.language]
        if self.script:
            parts.append(self.script)
        if self.region:
            parts.append(self.region)
        return "-".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "language_code": self.language,
            "script_code": self.script or self.get_default_script(),
            "bcp47_tag": self.to_tag(),
        }
        if self.region:
            result["region_code"] = self.region
        return result

    def get_default_script(self) -> str:
        """Get default script for language if not specified."""
        return LANGUAGE_TO_DEFAULT_SCRIPT.get(self.language, "Zzzz")

    def get_script_family(self) -> ScriptFamily:
        """Get script family for routing decisions."""
        script = self.script or self.get_default_script()
        return SCRIPT_TO_FAMILY.get(script, ScriptFamily.OTHER)

    def is_rtl(self) -> bool:
        """Check if script is right-to-left."""
        script = self.script or self.get_default_script()
        return script in ("Arab", "Hebr")

    def is_cjk(self) -> bool:
        """Check if script is CJK."""
        return self.get_script_family() == ScriptFamily.CJK


class ISOLanguageScriptInfo(TypedDict):
    """Schema-aligned language/script metadata."""

    language_code: str  # ISO 639-1/3
    script_code: str  # ISO 15924
    bcp47_tag: str  # Combined tag
    script_family: str  # High-level family
    confidence: float
    detection_method: str
    is_rtl: bool
    is_primary: bool


def create_language_script_info(
    language: str,
    script: str | None = None,
    confidence: float = 1.0,
    detection_method: str = "manual",
    is_primary: bool = True,
) -> ISOLanguageScriptInfo:
    """Create a schema-compliant language/script info dict.

    Args:
        language: ISO 639-1/3 language code
        script: ISO 15924 script code (optional, will use default)
        confidence: Detection confidence 0-1
        detection_method: How language was detected
        is_primary: Whether this is the primary language

    Returns:
        ISOLanguageScriptInfo dictionary
    """
    tag = LanguageScriptTag(language=language, script=script)

    return ISOLanguageScriptInfo(
        language_code=tag.language,
        script_code=tag.script or tag.get_default_script(),
        bcp47_tag=tag.to_tag()
        if tag.script
        else f"{tag.language}-{tag.get_default_script()}",
        script_family=tag.get_script_family().value,
        confidence=confidence,
        detection_method=detection_method,
        is_rtl=tag.is_rtl(),
        is_primary=is_primary,
    )


def normalize_legacy_script(legacy_script: str) -> str:
    """Convert legacy script names to ISO 15924 codes.

    Args:
        legacy_script: Old-style script name (e.g., "Latin", "CJK", "Arabic")

    Returns:
        ISO 15924 code
    """
    mapping = {
        # Common legacy names
        "latin": "Latn",
        "cjk": "Hani",
        "chinese": "Hans",
        "simplified chinese": "Hans",
        "traditional chinese": "Hant",
        "japanese": "Jpan",
        "korean": "Kore",
        "arabic": "Arab",
        "hebrew": "Hebr",
        "cyrillic": "Cyrl",
        "greek": "Grek",
        "devanagari": "Deva",
        "hindi": "Deva",
        "bengali": "Beng",
        "tamil": "Taml",
        "telugu": "Telu",
        "thai": "Thai",
        "tibetan": "Tibt",
        "ethiopic": "Ethi",
        "armenian": "Armn",
        "georgian": "Geor",
        "khmer": "Khmr",
        "myanmar": "Mymr",
        "burmese": "Mymr",
        "lao": "Laoo",
        "unknown": "Zzzz",
    }

    normalized = legacy_script.lower().strip()
    return mapping.get(normalized, "Zzzz")


def is_valid_iso15924_code(code: str) -> bool:
    """Check if a string is a valid ISO 15924 script code.

    Validates against the ISO15924Script enum values.

    Args:
        code: 4-letter script code to validate (e.g., "Latn", "Arab")

    Returns:
        True if code is a valid ISO 15924 script code

    Example:
        >>> is_valid_iso15924_code("Latn")
        True
        >>> is_valid_iso15924_code("INVALID")
        False
    """
    try:
        # Check if the code matches any enum value
        for member in ISO15924Script:
            if member.value == code:
                return True
        return False
    except (ValueError, TypeError):
        return False


def get_iso15924_script(code: str) -> ISO15924Script | None:
    """Convert a string code to ISO15924Script enum.

    Args:
        code: 4-letter script code (e.g., "Latn", "Arab")

    Returns:
        ISO15924Script enum member if valid, None otherwise

    Example:
        >>> get_iso15924_script("Latn")
        <ISO15924Script.LATN: 'Latn'>
        >>> get_iso15924_script("INVALID")
        None
    """
    try:
        for member in ISO15924Script:
            if member.value == code:
                return member
        return None
    except (ValueError, TypeError):
        return None


def validate_script_code_for_ml(code: str) -> tuple[bool, str | None]:
    """Validate a script code for ML pipeline usage.

    Validates that the code is a valid ISO 15924 code and provides
    suggestions for corrections if not.

    Args:
        code: Script code to validate

    Returns:
        Tuple of (is_valid, suggested_correction_or_error_message)

    Example:
        >>> validate_script_code_for_ml("Latn")
        (True, None)
        >>> validate_script_code_for_ml("latin")
        (False, "Try 'Latn' (normalized from 'latin')")
    """
    if not code:
        return False, "Script code cannot be empty"

    # Check if already valid
    if is_valid_iso15924_code(code):
        return True, None

    # Try to normalize legacy names
    normalized = normalize_legacy_script(code)
    if normalized != "Zzzz" and is_valid_iso15924_code(normalized):
        return False, f"Try '{normalized}' (normalized from '{code}')"

    # Check for case issues
    for member in ISO15924Script:
        if member.value.lower() == code.lower():
            return False, f"Case mismatch: use '{member.value}' not '{code}'"

    return False, f"Unknown script code: '{code}'"


# 10-class script detection taxonomy (for ML models)
SCRIPT_DETECTION_CLASSES: list[str] = [
    "Latn",  # Latin (Western European, Vietnamese, etc.)
    "Cyrl",  # Cyrillic (Russian, Ukrainian, etc.)
    "Arab",  # Arabic (Arabic, Persian, Urdu)
    "Deva",  # Devanagari (Hindi, Nepali, Marathi)
    "Hans",  # Simplified Chinese
    "Hant",  # Traditional Chinese
    "Jpan",  # Japanese
    "Kore",  # Korean
    "Thai",  # Thai
    "Tibt",  # Tibetan
]
