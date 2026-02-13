# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""OpenLID-v2 Language Detection Integration.

Integrates the OpenLID-v2 model (200 languages, ISO 639-3 + ISO 15924)
with the existing language detection pipeline.

OpenLID-v2: https://huggingface.co/laurievb/OpenLID-v2
- 200 language varieties with script identifiers
- Format: {ISO 639-3}_{ISO 15924} (e.g., eng_Latn, cmn_Hans)
- 0.93 macro-average F1 score

Usage:
    >>> from image_preprocessing_detector.schema_utils.openlid_integration import (
    ...     OpenLIDDetector,
    ...     detect_language_openlid,
    ... )
    >>> detector = OpenLIDDetector()
    >>> result = detector.detect("Hello, world!")
    >>> print(result.language_639_1, result.script_code)  # en Latn

Notes:
    - Requires numpy 2.x compatibility patch (applied automatically)
    - Model download handled via huggingface_hub
    - Arabic dialect detection is weak (F1=0.336) - use ensemble for Arabic
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

# Apply numpy 2.x compatibility patch for fasttext
# fasttext uses deprecated `np.array(x, copy=False)` which fails in numpy 2.x
_original_np_array = np.array


def _patched_np_array(*args: Any, **kwargs: Any) -> np.ndarray:
    """Wrapper that converts copy=False to np.asarray behavior."""
    if kwargs.get("copy") is False:
        kwargs.pop("copy")
        return np.asarray(*args, **kwargs)
    return _original_np_array(*args, **kwargs)


np.array = _patched_np_array  # type: ignore[assignment]

if TYPE_CHECKING:
    import fasttext

logger = logging.getLogger(__name__)

# Default model paths
DEFAULT_MODEL_DIR = Path("/mnt/e/image_detection/models/language_detection")
OPENLID_MODEL_FILENAME = "openlid_v2.bin"

# =============================================================================
# ISO 639-3 to ISO 639-1 Mapping
# =============================================================================
# Comprehensive mapping for all 200 OpenLID-v2 language varieties
# Maps ISO 639-3 codes to ISO 639-1 (2-letter) codes where available
# Languages without ISO 639-1 codes retain their ISO 639-3 codes

ISO639_3_TO_1: dict[str, str] = {
    # Acehnese (no 639-1)
    "ace": "ace",
    # Mesopotamian Arabic → Arabic
    "acm": "ar",
    # Ta'izzi-Adeni Arabic → Arabic
    "acq": "ar",
    # Tunisian Arabic → Arabic
    "aeb": "ar",
    # Afrikaans
    "afr": "af",
    # Tosk Albanian
    "als": "sq",
    # Amharic
    "amh": "am",
    # Levantine Arabic → Arabic
    "apc": "ar",
    # Standard Arabic
    "arb": "ar",
    # Najdi Arabic → Arabic
    "ars": "ar",
    # Moroccan Arabic → Arabic
    "ary": "ar",
    # Egyptian Arabic → Arabic
    "arz": "ar",
    # Assamese
    "asm": "as",
    # Asturian
    "ast": "ast",
    # Awadhi (no 639-1)
    "awa": "awa",
    # Central Aymara
    "ayr": "ay",
    # South Azerbaijani
    "azb": "az",
    # North Azerbaijani
    "azj": "az",
    # Bashkir
    "bak": "ba",
    # Bambara
    "bam": "bm",
    # Balinese (no 639-1)
    "ban": "ban",
    # Belarusian
    "bel": "be",
    # Bemba (no 639-1)
    "bem": "bem",
    # Bengali
    "ben": "bn",
    # Bhojpuri (no 639-1)
    "bho": "bho",
    # Banjar (no 639-1)
    "bjn": "bjn",
    # Tibetan
    "bod": "bo",
    # Bosnian
    "bos": "bs",
    # Buginese (no 639-1)
    "bug": "bug",
    # Bulgarian
    "bul": "bg",
    # Catalan
    "cat": "ca",
    # Cebuano (no 639-1)
    "ceb": "ceb",
    # Czech
    "ces": "cs",
    # Chokwe (no 639-1)
    "cjk": "cjk",
    # Central Kurdish
    "ckb": "ku",
    # Mandarin Chinese (Simplified)
    "cmn": "zh",
    # Crimean Tatar (no 639-1)
    "crh": "crh",
    # Welsh
    "cym": "cy",
    # Danish
    "dan": "da",
    # German
    "deu": "de",
    # Southwestern Dinka (no 639-1)
    "dik": "dik",
    # Dyula (no 639-1)
    "dyu": "dyu",
    # Dzongkha
    "dzo": "dz",
    # Standard Estonian
    "ekk": "et",
    # Greek
    "ell": "el",
    # English
    "eng": "en",
    # Esperanto
    "epo": "eo",
    # Basque
    "eus": "eu",
    # Ewe
    "ewe": "ee",
    # Faroese
    "fao": "fo",
    # Fijian
    "fij": "fj",
    # Filipino
    "fil": "fil",
    # Finnish
    "fin": "fi",
    # Fon (no 639-1)
    "fon": "fon",
    # French
    "fra": "fr",
    # Friulian (no 639-1)
    "fur": "fur",
    # Nigerian Fulfulde (no 639-1)
    "fuv": "ff",
    # West Central Oromo
    "gaz": "om",
    # Scottish Gaelic
    "gla": "gd",
    # Irish
    "gle": "ga",
    # Galician
    "glg": "gl",
    # Paraguayan Guaraní
    "gug": "gn",
    # Gujarati
    "guj": "gu",
    # Haitian Creole
    "hat": "ht",
    # Hausa
    "hau": "ha",
    # Hebrew
    "heb": "he",
    # Hindi
    "hin": "hi",
    # Chhattisgarhi (no 639-1)
    "hne": "hne",
    # Croatian
    "hrv": "hr",
    # Hungarian
    "hun": "hu",
    # Armenian
    "hye": "hy",
    # Igbo
    "ibo": "ig",
    # Ilocano (no 639-1)
    "ilo": "ilo",
    # Indonesian
    "ind": "id",
    # Icelandic
    "isl": "is",
    # Italian
    "ita": "it",
    # Javanese
    "jav": "jv",
    # Japanese
    "jpn": "ja",
    # Kabyle (no 639-1)
    "kab": "kab",
    # Jingpho (no 639-1)
    "kac": "kac",
    # Kamba (no 639-1)
    "kam": "kam",
    # Kannada
    "kan": "kn",
    # Kashmiri
    "kas": "ks",
    # Georgian
    "kat": "ka",
    # Kazakh
    "kaz": "kk",
    # Kabiyè (no 639-1)
    "kbp": "kbp",
    # Kabuverdianu (no 639-1)
    "kea": "kea",
    # Halh Mongolian
    "khk": "mn",
    # Khmer
    "khm": "km",
    # Kikuyu
    "kik": "ki",
    # Kinyarwanda
    "kin": "rw",
    # Kyrgyz
    "kir": "ky",
    # Kimbundu (no 639-1)
    "kmb": "kmb",
    # Northern Kurdish
    "kmr": "ku",
    # Central Kanuri (no 639-1)
    "knc": "kr",
    # Korean
    "kor": "ko",
    # Kituba (no 639-1)
    "ktu": "ktu",
    # Lao
    "lao": "lo",
    # Ligurian (no 639-1)
    "lij": "lij",
    # Limburgish
    "lim": "li",
    # Lingala
    "lin": "ln",
    # Lithuanian
    "lit": "lt",
    # Lombard (no 639-1)
    "lmo": "lmo",
    # Latgalian (no 639-1)
    "ltg": "ltg",
    # Luxembourgish
    "ltz": "lb",
    # Luba-Kasai
    "lua": "lu",
    # Ganda
    "lug": "lg",
    # Luo (no 639-1)
    "luo": "luo",
    # Mizo (no 639-1)
    "lus": "lus",
    # Standard Latvian
    "lvs": "lv",
    # Magahi (no 639-1)
    "mag": "mag",
    # Maithili (no 639-1)
    "mai": "mai",
    # Malayalam
    "mal": "ml",
    # Marathi
    "mar": "mr",
    # Minangkabau (no 639-1)
    "min": "min",
    # Macedonian
    "mkd": "mk",
    # Maltese
    "mlt": "mt",
    # Meitei (no 639-1)
    "mni": "mni",
    # Mossi (no 639-1)
    "mos": "mos",
    # Maori
    "mri": "mi",
    # Burmese
    "mya": "my",
    # Dutch
    "nld": "nl",
    # Norwegian Nynorsk
    "nno": "nn",
    # Norwegian Bokmål
    "nob": "nb",
    # Nepali
    "npi": "ne",
    # Northern Sotho (no 639-1)
    "nso": "nso",
    # Nuer (no 639-1)
    "nus": "nus",
    # Nyanja/Chewa
    "nya": "ny",
    # Occitan
    "oci": "oc",
    # Odia
    "ory": "or",
    # Pangasinan (no 639-1)
    "pag": "pag",
    # Punjabi
    "pan": "pa",
    # Papiamento (no 639-1)
    "pap": "pap",
    # Southern Pashto
    "pbt": "ps",
    # Iranian Persian (Western Farsi)
    "pes": "fa",
    # Plateau Malagasy
    "plt": "mg",
    # Polish
    "pol": "pl",
    # Portuguese
    "por": "pt",
    # Dari (Afghan Persian)
    "prs": "fa",
    # Ayacucho Quechua
    "quy": "qu",
    # Romanian
    "ron": "ro",
    # Rundi
    "run": "rn",
    # Russian
    "rus": "ru",
    # Sango
    "sag": "sg",
    # Sanskrit
    "san": "sa",
    # Santali (no 639-1)
    "sat": "sat",
    # Sicilian (no 639-1)
    "scn": "scn",
    # Shan (no 639-1)
    "shn": "shn",
    # Sinhala
    "sin": "si",
    # Slovak
    "slk": "sk",
    # Slovenian
    "slv": "sl",
    # Samoan
    "smo": "sm",
    # Shona
    "sna": "sn",
    # Sindhi
    "snd": "sd",
    # Somali
    "som": "so",
    # Southern Sotho
    "sot": "st",
    # Spanish
    "spa": "es",
    # Sardinian
    "srd": "sc",
    # Serbian
    "srp": "sr",
    # Swati
    "ssw": "ss",
    # Sundanese
    "sun": "su",
    # Swedish
    "swe": "sv",
    # Swahili
    "swh": "sw",
    # Silesian (no 639-1)
    "szl": "szl",
    # Tamil
    "tam": "ta",
    # Tamasheq (no 639-1)
    "taq": "taq",
    # Tatar
    "tat": "tt",
    # Telugu
    "tel": "te",
    # Tajik
    "tgk": "tg",
    # Thai
    "tha": "th",
    # Tigrinya
    "tir": "ti",
    # Tok Pisin (no 639-1)
    "tpi": "tpi",
    # Tswana
    "tsn": "tn",
    # Tsonga
    "tso": "ts",
    # Turkmen
    "tuk": "tk",
    # Tumbuka (no 639-1)
    "tum": "tum",
    # Turkish
    "tur": "tr",
    # Twi
    "twi": "tw",
    # Uyghur
    "uig": "ug",
    # Ukrainian
    "ukr": "uk",
    # Umbundu (no 639-1)
    "umb": "umb",
    # Urdu
    "urd": "ur",
    # Northern Uzbek
    "uzn": "uz",
    # Venetian (no 639-1)
    "vec": "vec",
    # Vietnamese
    "vie": "vi",
    # Waray (no 639-1)
    "war": "war",
    # Wolof
    "wol": "wo",
    # Xhosa
    "xho": "xh",
    # Eastern Yiddish
    "ydd": "yi",
    # Yoruba
    "yor": "yo",
    # Cantonese
    "yue": "yue",
    # Standard Moroccan Tamazight (no 639-1)
    "zgh": "zgh",
    # Standard Malay
    "zsm": "ms",
    # Zulu
    "zul": "zu",
}

# Reverse mapping for reference
ISO639_1_TO_3: dict[str, list[str]] = {}
for code_3, code_1 in ISO639_3_TO_1.items():
    ISO639_1_TO_3.setdefault(code_1, []).append(code_3)


# =============================================================================
# Detection Result
# =============================================================================


@dataclass
class OpenLIDResult:
    """Result from OpenLID-v2 language detection.

    Attributes:
        language_639_3: ISO 639-3 language code (e.g., "eng", "cmn")
        language_639_1: ISO 639-1 language code (e.g., "en", "zh")
        script_code: ISO 15924 script code (e.g., "Latn", "Hans")
        confidence: Detection confidence (0.0 - 1.0)
        raw_label: Original model label (e.g., "__label__eng_Latn")
        is_dialect: Whether this is a dialect/variant code
    """

    language_639_3: str
    language_639_1: str
    script_code: str
    confidence: float
    raw_label: str
    is_dialect: bool = False

    @property
    def bcp47_tag(self) -> str:
        """Return BCP 47 language tag (e.g., 'en-Latn', 'zh-Hans')."""
        return f"{self.language_639_1}-{self.script_code}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "language_639_3": self.language_639_3,
            "language_639_1": self.language_639_1,
            "script_code": self.script_code,
            "confidence": round(self.confidence, 4),
            "bcp47_tag": self.bcp47_tag,
            "is_dialect": self.is_dialect,
            "raw_label": self.raw_label,
        }


# =============================================================================
# OpenLID Detector
# =============================================================================


class OpenLIDDetector:
    """OpenLID-v2 language detector wrapper.

    Handles model loading, numpy 2.x compatibility, and result parsing.

    Example:
        >>> detector = OpenLIDDetector()
        >>> result = detector.detect("Hello, world!")
        >>> print(result.language_639_1)  # 'en'
        >>> print(result.script_code)  # 'Latn'
    """

    def __init__(
        self,
        model_path: Path | str | None = None,
        auto_download: bool = True,
    ) -> None:
        """Initialize the OpenLID detector.

        Args:
            model_path: Path to openlid_v2.bin model file.
                       If None, uses default path.
            auto_download: If True and model not found, download from HuggingFace.
        """
        if model_path is None:
            model_path = DEFAULT_MODEL_DIR / OPENLID_MODEL_FILENAME
        else:
            model_path = Path(model_path)

        self._model_path = model_path
        self._model: fasttext.FastText._FastText | None = None
        self._auto_download = auto_download

    def _ensure_model(self) -> None:
        """Ensure model is loaded, downloading if necessary."""
        if self._model is not None:
            return

        if not self._model_path.exists():
            if self._auto_download:
                self._download_model()
            else:
                raise FileNotFoundError(
                    f"OpenLID model not found at {self._model_path}. "
                    "Set auto_download=True or download manually."
                )

        self._load_model()

    def _download_model(self) -> None:
        """Download OpenLID-v2 model from HuggingFace."""
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise ImportError(
                "huggingface_hub required for model download. "
                "Install with: uv add huggingface_hub"
            ) from e

        logger.info("Downloading OpenLID-v2 model from HuggingFace...")
        self._model_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded_path = hf_hub_download(  # nosec B615
            repo_id="laurievb/OpenLID-v2",
            filename="model.bin",
            local_dir=self._model_path.parent,
        )

        # Rename to expected filename
        downloaded = Path(downloaded_path)
        if downloaded != self._model_path:
            downloaded.rename(self._model_path)

        logger.info(f"Model downloaded to: {self._model_path}")

    def _load_model(self) -> None:
        """Load the fastText model."""
        try:
            import fasttext
        except ImportError as e:
            raise ImportError(
                "fasttext required for OpenLID. Install with: uv add fasttext"
            ) from e

        logger.info(f"Loading OpenLID-v2 model from {self._model_path}")
        self._model = fasttext.load_model(str(self._model_path))
        logger.info("OpenLID-v2 model loaded successfully")

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text for OpenLID detection.

        Simplified version of openlid_normer.clean_line().
        """
        # Replace newlines and tabs with spaces
        text = text.replace("\n", " ").replace("\t", " ")
        # Collapse multiple spaces
        text = " ".join(text.split())
        return text.strip()

    def detect(self, text: str, threshold: float = 0.0) -> OpenLIDResult:
        """Detect language of text.

        Args:
            text: Text to analyze.
            threshold: Minimum confidence threshold. Returns 'und' if below.

        Returns:
            OpenLIDResult with language, script, and confidence.
        """
        self._ensure_model()
        assert self._model is not None

        clean_text = self.clean_text(text)
        if not clean_text:
            return OpenLIDResult(
                language_639_3="und",
                language_639_1="und",
                script_code="Zzzz",
                confidence=0.0,
                raw_label="",
                is_dialect=False,
            )

        predictions = self._model.predict(clean_text, k=1)
        raw_label = predictions[0][0]
        confidence = float(predictions[1][0])

        if confidence < threshold:
            return OpenLIDResult(
                language_639_3="und",
                language_639_1="und",
                script_code="Zzzz",
                confidence=confidence,
                raw_label=raw_label,
                is_dialect=False,
            )

        return self._parse_label(raw_label, confidence)

    def detect_top_k(self, text: str, k: int = 5) -> list[OpenLIDResult]:
        """Detect top-k language predictions.

        Args:
            text: Text to analyze.
            k: Number of top predictions to return.

        Returns:
            List of OpenLIDResult, sorted by confidence (descending).
        """
        self._ensure_model()
        assert self._model is not None

        clean_text = self.clean_text(text)
        if not clean_text:
            return []

        predictions = self._model.predict(clean_text, k=k)
        results = []

        for label, conf in zip(predictions[0], predictions[1], strict=False):
            results.append(self._parse_label(label, float(conf)))

        return results

    def _parse_label(self, raw_label: str, confidence: float) -> OpenLIDResult:
        """Parse OpenLID label into structured result.

        Args:
            raw_label: Raw model label like "__label__eng_Latn"
            confidence: Model confidence score

        Returns:
            OpenLIDResult with parsed components
        """
        # Parse format: __label__<lang>_<script>
        label_content = raw_label.replace("__label__", "")
        parts = label_content.split("_")

        lang_639_3 = parts[0]
        script_code = parts[1] if len(parts) > 1 else "Zzzz"

        # Map to ISO 639-1
        lang_639_1 = ISO639_3_TO_1.get(lang_639_3, lang_639_3)

        # Check if this is a dialect (639-3 maps to different 639-1)
        is_dialect = lang_639_3 != lang_639_1 and lang_639_3 not in ISO639_3_TO_1

        return OpenLIDResult(
            language_639_3=lang_639_3,
            language_639_1=lang_639_1,
            script_code=script_code,
            confidence=confidence,
            raw_label=raw_label,
            is_dialect=is_dialect,
        )

    def get_supported_languages(self) -> list[str]:
        """Get list of all supported language labels."""
        self._ensure_model()
        assert self._model is not None
        return [label.replace("__label__", "") for label in self._model.get_labels()]


# =============================================================================
# Convenience Functions
# =============================================================================


# Global detector instance (lazy initialization)
_global_detector: OpenLIDDetector | None = None


def get_detector() -> OpenLIDDetector:
    """Get or create global OpenLID detector instance."""
    global _global_detector
    if _global_detector is None:
        _global_detector = OpenLIDDetector()
    return _global_detector


def detect_language_openlid(
    text: str,
    threshold: float = 0.0,
) -> OpenLIDResult:
    """Detect language using OpenLID-v2 model.

    Convenience function using global detector instance.

    Args:
        text: Text to analyze.
        threshold: Minimum confidence threshold.

    Returns:
        OpenLIDResult with language and script information.

    Example:
        >>> result = detect_language_openlid("Bonjour le monde!")
        >>> print(result.language_639_1)  # 'fr'
        >>> print(result.script_code)  # 'Latn'
    """
    return get_detector().detect(text, threshold)


def detect_top_k_openlid(text: str, k: int = 5) -> list[OpenLIDResult]:
    """Get top-k language predictions using OpenLID-v2.

    Args:
        text: Text to analyze.
        k: Number of predictions to return.

    Returns:
        List of OpenLIDResult sorted by confidence.
    """
    return get_detector().detect_top_k(text, k)


__all__ = [
    "ISO639_1_TO_3",
    "ISO639_3_TO_1",
    "OpenLIDDetector",
    "OpenLIDResult",
    "detect_language_openlid",
    "detect_top_k_openlid",
    "get_detector",
]
