"""Configuration models for synthetic document generation.

This module defines the core configuration types for the multi-script
synthetic document generator, including script configurations, layout
types, and text density settings.

The 27 supported scripts are mapped to their ISO 15924 codes, Noto fonts,
and OpenLID-v2 language codes for text corpus sourcing.

Example:
    >>> from image_preprocessing_detector.synthetic.config import (
    ...     SCRIPT_CONFIGS,
    ...     LayoutType,
    ...     TextDensity,
    ... )
    >>> config = SCRIPT_CONFIGS["Tibt"]
    >>> print(config.name)  # "Tibetan"
    >>> print(config.direction)  # "ltr"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
    ScriptFamily,
)


class ColorMode(StrEnum):
    """Color mode for generated document images.

    Controls post-processing color conversion for training diversity.
    """

    COLOR = "color"
    """Full RGB color (default)."""

    GRAYSCALE = "grayscale"
    """Grayscale conversion (simulates B&W scans)."""

    BINARIZED = "binarized"
    """Binary threshold (simulates high-contrast copies/faxes)."""


# Color mode distribution for multi-task training diversity (must sum to 1.0)
COLOR_MODE_WEIGHTS: dict[ColorMode, float] = {
    ColorMode.COLOR: 0.60,
    ColorMode.GRAYSCALE: 0.25,
    ColorMode.BINARIZED: 0.15,
}


class LayoutType(StrEnum):
    """Document layout types for synthetic generation.

    These map to Layer 2 StructureInfo.layout_type values.
    """

    STACKED = "stacked"
    """Vertical stack of text blocks."""

    COLUMNS = "columns"
    """Side-by-side columns (2-3)."""

    HEADER_BODY = "header_body"
    """Header in one script, body in another."""

    HEADER_BODY_FOOTER = "header_body_footer"
    """Three-section layout with header, body, footer."""

    INTERLEAVED = "interleaved"
    """Alternating paragraphs by script."""

    FORM = "form"
    """Labels and values in different scripts."""

    SIDEBAR = "sidebar"
    """Main content with sidebar annotation."""

    CAPTIONED = "captioned"
    """Main block with caption below."""

    SINGLE_LINE = "single_line"
    """Single line(s) of text (labels, titles)."""

    SHORT_BLOCKS = "short_blocks"
    """Multiple short text blocks (sparse layout)."""

    DENSE_TEXT = "dense_text"
    """Dense paragraphs with minimal margins."""


class TextDensity(StrEnum):
    """Text density levels for generated documents.

    Controls text length and coverage in generated images.
    Maps to Layer 2 StructureInfo.text_density.
    """

    MINIMAL = "minimal"
    """Very short text (1-2 words). Maps to Layer 2 'sparse'."""

    SHORT = "short"
    """Short text (1-2 sentences). Maps to Layer 2 'sparse'."""

    MEDIUM = "medium"
    """Medium text (paragraph). Maps to Layer 2 'moderate'."""

    LONG = "long"
    """Longer text (multiple paragraphs). Maps to Layer 2 'moderate'."""

    DENSE = "dense"
    """Maximum density (full page). Maps to Layer 2 'dense'."""


# Mapping from TextDensity to Layer 2 text_density values
DENSITY_TO_LAYER2: dict[TextDensity, str] = {
    TextDensity.MINIMAL: "sparse",
    TextDensity.SHORT: "sparse",
    TextDensity.MEDIUM: "moderate",
    TextDensity.LONG: "moderate",
    TextDensity.DENSE: "dense",
}

# Mapping from LayoutType to Layer 2 layout_type values
LAYOUT_TO_LAYER2: dict[LayoutType, str] = {
    LayoutType.STACKED: "single_column",
    LayoutType.COLUMNS: "multi_column",
    LayoutType.HEADER_BODY: "single_column",
    LayoutType.HEADER_BODY_FOOTER: "single_column",
    LayoutType.INTERLEAVED: "single_column",
    LayoutType.FORM: "form_based",
    LayoutType.SIDEBAR: "multi_column",
    LayoutType.CAPTIONED: "single_column",
    LayoutType.SINGLE_LINE: "single_column",
    LayoutType.SHORT_BLOCKS: "complex",
    LayoutType.DENSE_TEXT: "single_column",
}


# =============================================================================
# Distribution Weights for Dataset Generation
# =============================================================================

# Geometric transform ranges for base dataset generation
# Base generates ±22° skew (expanded from ±10° to avoid coverage gaps
# with the 42-bin skew estimator's critical/moderate zones).
# Derived skew view scripts extend to ±45° for full-range training.
SKEW_RANGE_DEGREES: tuple[float, float] = (-22.0, 22.0)

# CJK vertical text (tategaki) generation ratios
# For scripts supporting both horizontal and vertical writing
CJK_VERTICAL_RATIOS: dict[str, float] = {
    "Jpan": 0.30,  # 30% vertical (novels, newspapers, traditional docs)
    "Hans": 0.10,  # 10% vertical (calligraphy, traditional signage)
    "Hant": 0.10,  # 10% vertical (calligraphy, traditional signage)
}

# English as most common secondary language in multi-script compositions
# When selecting a secondary script in multi-script generation,
# Latn is weighted at this probability (vs uniform ~3.7% across 27 scripts)
ENGLISH_SECONDARY_WEIGHT: float = 0.40

# Output sizes for derived training views (pixels)
# Primary size for training + 512px variant for 20% of samples
OUTPUT_SIZES: list[int] = [224, 384, 512]

# Resolution tiers for NaFlex optimization (variable resolution training)
# 7-tier DPI distribution for multi-task training diversity
# (expanded from 3 tiers to support resolution quality dataset generation)
RESOLUTION_TIERS: dict[str, dict[str, tuple[int, int] | int]] = {
    "VERY_LOW": {"width_range": (400, 500), "target_dpi": 72},
    "LOW": {"width_range": (500, 700), "target_dpi": 100},
    "MEDIUM_LOW": {"width_range": (700, 850), "target_dpi": 150},
    "MEDIUM": {"width_range": (850, 1000), "target_dpi": 200},
    "STANDARD": {"width_range": (1000, 1200), "target_dpi": 300},
    "HIGH": {"width_range": (1200, 1400), "target_dpi": 400},
    "VERY_HIGH": {"width_range": (1400, 1700), "target_dpi": 600},
}

# Resolution tier distribution (must sum to 1.0)
RESOLUTION_TIER_WEIGHTS: dict[str, float] = {
    "VERY_LOW": 0.08,
    "LOW": 0.12,
    "MEDIUM_LOW": 0.15,
    "MEDIUM": 0.20,
    "STANDARD": 0.25,
    "HIGH": 0.12,
    "VERY_HIGH": 0.08,
}

# Quality tiers with IQA ranges (must sum to 1.0)
# CRITICAL: Quality distribution MUST be independent of script to prevent spurious correlations
QUALITY_TIER_WEIGHTS: dict[str, float] = {
    "PRISTINE": 0.10,  # overall_quality 0.95-1.00, no augmentation
    "HIGH": 0.25,  # overall_quality 0.80-0.95, light augmentation
    "MEDIUM": 0.35,  # overall_quality 0.60-0.80, moderate augmentation
    "LOW": 0.20,  # overall_quality 0.40-0.60, heavy augmentation
    "DEGRADED": 0.10,  # overall_quality 0.00-0.40, heavy + extras
}

# Layout type weights matching script_dataset_structure.md (must sum to 1.0)
LAYOUT_WEIGHTS: dict[LayoutType, float] = {
    LayoutType.STACKED: 0.14,  # Reduced from 0.15 to fund DENSE_TEXT increase
    LayoutType.HEADER_BODY: 0.15,
    LayoutType.COLUMNS: 0.12,
    LayoutType.FORM: 0.12,
    LayoutType.INTERLEAVED: 0.10,
    LayoutType.HEADER_BODY_FOOTER: 0.08,
    LayoutType.SIDEBAR: 0.08,
    LayoutType.CAPTIONED: 0.08,
    LayoutType.SINGLE_LINE: 0.05,
    LayoutType.SHORT_BLOCKS: 0.04,
    LayoutType.DENSE_TEXT: 0.04,  # Increased from 0.03 for better dense text coverage
}

# Text density weights (must sum to 1.0)
TEXT_DENSITY_WEIGHTS: dict[TextDensity, float] = {
    TextDensity.MINIMAL: 0.10,  # 5-30 chars
    TextDensity.SHORT: 0.20,  # 20-100 chars
    TextDensity.MEDIUM: 0.40,  # 80-300 chars
    TextDensity.LONG: 0.20,  # 250-800 chars
    TextDensity.DENSE: 0.10,  # 600-2000 chars
}

# Document composition weights (single vs multi-script)
# Adjusted for multi-task training: more single-script for cleaner labels
DOCUMENT_COMPOSITION_WEIGHTS: dict[str, float] = {
    "single": 0.45,  # 45% pure single-script (up from 35% for cleaner labels)
    "two": 0.38,  # 38% bilingual (down from 45%)
    "three": 0.10,  # 10% complex multilingual (down from 12%)
    "four_plus": 0.02,  # 2% edge cases (down from 3%)
    "priority_pairs": 0.05,  # 5% reserved for specific high-priority combinations
}

# Priority two-script combinations with relative weights
# Higher weight = more samples generated for this combination
TWO_SCRIPT_COMBINATIONS: dict[tuple[str, str], int] = {
    ("Latn", "Arab"): 12,  # English + Arabic forms
    ("Latn", "Hans"): 10,  # English + Chinese
    ("Latn", "Deva"): 10,  # English + Hindi
    ("Latn", "Tibt"): 8,  # English + Dzongkha (priority use case)
    ("Latn", "Cyrl"): 8,  # English + Russian
    ("Latn", "Jpan"): 8,  # English + Japanese
    ("Latn", "Kore"): 6,  # English + Korean
    ("Latn", "Thai"): 6,  # English + Thai
    ("Latn", "Beng"): 5,  # English + Bengali
    ("Latn", "Hant"): 5,  # English + Traditional Chinese
    ("Arab", "Deva"): 4,  # Urdu + Hindi regions
    ("Cyrl", "Latn"): 4,  # Russian + English
    ("Hans", "Hant"): 3,  # Simplified + Traditional Chinese
}

# Language weighting for scripts with multiple languages
# Ensures diverse language coverage within each script
LANGUAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "Latn": {
        # Major languages (60% of Latin samples)
        "eng_Latn": 0.15,
        "spa_Latn": 0.10,
        "fra_Latn": 0.08,
        "deu_Latn": 0.06,
        "por_Latn": 0.05,
        "ita_Latn": 0.04,
        "vie_Latn": 0.04,
        "tur_Latn": 0.04,
        "pol_Latn": 0.03,
        "nld_Latn": 0.03,
        # Medium languages (25% spread across ~20 languages at 1-2% each)
        # Minor languages get remaining 15% spread evenly (~0.15% each)
        # Note: When a language isn't specified, sample uniformly from remaining
    },
    "Arab": {
        "arb_Arab": 0.20,  # Modern Standard Arabic
        "arz_Arab": 0.12,  # Egyptian Arabic
        "pes_Arab": 0.12,  # Persian/Farsi
        "urd_Arab": 0.10,  # Urdu
        "ary_Arab": 0.08,  # Moroccan Arabic
        "apc_Arab": 0.06,  # North Levantine
        "ajp_Arab": 0.06,  # South Levantine
        "acm_Arab": 0.05,  # Mesopotamian
        "prs_Arab": 0.05,  # Dari
        "pbt_Arab": 0.04,  # Pashto
        # Remaining 12% distributed among other Arabic-script languages
    },
    "Cyrl": {
        "rus_Cyrl": 0.35,  # Russian
        "ukr_Cyrl": 0.20,  # Ukrainian
        "bul_Cyrl": 0.10,  # Bulgarian
        "srp_Cyrl": 0.08,  # Serbian
        "mkd_Cyrl": 0.06,  # Macedonian
        "bel_Cyrl": 0.05,  # Belarusian
        "kaz_Cyrl": 0.05,  # Kazakh
        # Remaining 11% distributed among other Cyrillic languages
    },
    "Deva": {
        "hin_Deva": 0.40,  # Hindi
        "mar_Deva": 0.20,  # Marathi
        "npi_Deva": 0.15,  # Nepali
        "bho_Deva": 0.08,  # Bhojpuri
        "mai_Deva": 0.06,  # Maithili
        "san_Deva": 0.04,  # Sanskrit
        # Remaining 7% distributed among other Devanagari languages
    },
}


@dataclass(frozen=True)
class ScriptConfig:
    """Configuration for a single ISO 15924 script.

    Immutable configuration defining how to generate documents
    for a specific writing script, including font requirements,
    text direction, and OpenLID-v2 language mappings.

    Attributes:
        code (str): ISO 15924 4-letter script code (e.g., "Tibt", "Arab")
        name (str): Human-readable script name (e.g., "Tibetan", "Arabic")
        direction (Literal['ltr', 'rtl', 'ttb']): Text direction ("ltr", "rtl", or "ttb")
        fonts (list[str]): List of Noto font filenames for this script
        openlid_languages (list[str]): OpenLID-v2 language codes that use this script
        script_family (ScriptFamily): High-level script family for OCR routing
        is_rtl (bool): True if script is right-to-left
        requires_shaping (bool): True if script requires HarfBuzz text shaping
        min_font_size (int): Minimum readable font size in pixels
        max_font_size (int): Maximum font size in pixels
        rq_min_font_size (int): Minimum font size for resolution quality training
        rq_max_font_size (int): Maximum font size covering all coarse buckets

    """

    code: str
    name: str
    direction: Literal["ltr", "rtl", "ttb"]
    fonts: list[str]
    openlid_languages: list[str]
    script_family: ScriptFamily
    is_rtl: bool = False
    requires_shaping: bool = False
    min_font_size: int = 12
    max_font_size: int = 28
    rq_min_font_size: int = 6  # Broader range for resolution quality training
    rq_max_font_size: int = 48  # Covers all 5 coarse buckets across 7 DPI tiers

    def get_iso15924_enum(self) -> ISO15924Script | None:
        """Get the corresponding ISO15924Script enum value."""
        try:
            return ISO15924Script(self.code)
        except ValueError:
            return None


# Common font name constants (S1192: avoid duplicate string literals)
NOTO_SERIF_FONT = "NotoSerif-Regular.ttf"
NOTO_SANS_FONT = "NotoSans-Regular.ttf"

# =============================================================================
# Script Configurations (27 scripts)
# =============================================================================

SCRIPT_CONFIGS: dict[str, ScriptConfig] = {
    # --- Latin-based scripts ---
    # OpenLID-v2 uses {ISO 639-3}_{ISO 15924} format (e.g., eng_Latn)
    # All 125 Latin-script languages from OpenLID-v2
    "Latn": ScriptConfig(
        code="Latn",
        name="Latin",
        direction="ltr",
        fonts=[NOTO_SANS_FONT, NOTO_SERIF_FONT],
        openlid_languages=[
            # Major European languages
            "eng_Latn",  # English
            "spa_Latn",  # Spanish
            "fra_Latn",  # French
            "deu_Latn",  # German
            "ita_Latn",  # Italian
            "por_Latn",  # Portuguese
            "nld_Latn",  # Dutch
            "pol_Latn",  # Polish
            "ron_Latn",  # Romanian
            "hun_Latn",  # Hungarian
            "ces_Latn",  # Czech
            "slk_Latn",  # Slovak
            "hrv_Latn",  # Croatian
            "slv_Latn",  # Slovenian
            "lit_Latn",  # Lithuanian
            "lvs_Latn",  # Latvian (Standard)
            "ltg_Latn",  # Latgalian
            "est_Latn",  # Estonian
            "fin_Latn",  # Finnish
            "swe_Latn",  # Swedish
            "dan_Latn",  # Danish
            "nob_Latn",  # Norwegian Bokmal
            "nno_Latn",  # Norwegian Nynorsk
            "isl_Latn",  # Icelandic
            "fao_Latn",  # Faroese
            "cat_Latn",  # Catalan
            "glg_Latn",  # Galician
            "ast_Latn",  # Asturian
            "oci_Latn",  # Occitan
            "eus_Latn",  # Basque
            "mlt_Latn",  # Maltese
            "cym_Latn",  # Welsh
            "gle_Latn",  # Irish
            "gla_Latn",  # Scottish Gaelic
            "bos_Latn",  # Bosnian
            "als_Latn",  # Tosk Albanian
            "ltz_Latn",  # Luxembourgish
            "lim_Latn",  # Limburgish
            "lij_Latn",  # Ligurian
            "lmo_Latn",  # Lombard
            "vec_Latn",  # Venetian
            "scn_Latn",  # Sicilian
            "srd_Latn",  # Sardinian
            "fur_Latn",  # Friulian
            "szl_Latn",  # Silesian
            "epo_Latn",  # Esperanto
            # Southeast Asian (Latin script)
            "vie_Latn",  # Vietnamese
            "ind_Latn",  # Indonesian
            "zsm_Latn",  # Standard Malay
            "tgl_Latn",  # Tagalog
            "ceb_Latn",  # Cebuano
            "ilo_Latn",  # Ilocano
            "war_Latn",  # Waray
            "pag_Latn",  # Pangasinan
            "jav_Latn",  # Javanese
            "sun_Latn",  # Sundanese
            "min_Latn",  # Minangkabau
            "ban_Latn",  # Balinese
            "bug_Latn",  # Buginese
            "bjn_Latn",  # Banjar
            "ace_Latn",  # Acehnese
            # Turkish and Central Asian
            "tur_Latn",  # Turkish
            "azj_Latn",  # North Azerbaijani
            "uzn_Latn",  # Northern Uzbek
            "tuk_Latn",  # Turkmen
            "crh_Latn",  # Crimean Tatar
            "kmr_Latn",  # Northern Kurdish
            # African languages
            "swh_Latn",  # Swahili
            "yor_Latn",  # Yoruba
            "ibo_Latn",  # Igbo
            "hau_Latn",  # Hausa
            "zul_Latn",  # Zulu
            "xho_Latn",  # Xhosa
            "sna_Latn",  # Shona
            "kin_Latn",  # Kinyarwanda
            "run_Latn",  # Rundi
            "lin_Latn",  # Lingala
            "wol_Latn",  # Wolof
            "afr_Latn",  # Afrikaans
            "som_Latn",  # Somali
            "nya_Latn",  # Nyanja
            "ssw_Latn",  # Swati
            "sot_Latn",  # Southern Sotho
            "nso_Latn",  # Northern Sotho
            "tsn_Latn",  # Tswana
            "tso_Latn",  # Tsonga
            "lug_Latn",  # Ganda
            "luo_Latn",  # Luo
            "kik_Latn",  # Kikuyu
            "kam_Latn",  # Kamba
            "bem_Latn",  # Bemba
            "tum_Latn",  # Tumbuka
            "umb_Latn",  # Umbundu
            "kmb_Latn",  # Kimbundu
            "kon_Latn",  # Kikongo
            "lua_Latn",  # Luba-Kasai
            "sag_Latn",  # Sango
            "ewe_Latn",  # Ewe
            "twi_Latn",  # Twi
            "fon_Latn",  # Fon
            "bam_Latn",  # Bambara
            "dyu_Latn",  # Dyula
            "mos_Latn",  # Mossi
            "fuv_Latn",  # Nigerian Fulfulde
            "kbp_Latn",  # Kabiye
            "gaz_Latn",  # West Central Oromo
            "dik_Latn",  # Southwestern Dinka
            "nus_Latn",  # Nuer
            "cjk_Latn",  # Chokwe
            "knc_Latn",  # Central Kanuri
            # Americas
            "hat_Latn",  # Haitian Creole
            "pap_Latn",  # Papiamento
            "kea_Latn",  # Kabuverdianu
            "grn_Latn",  # Guarani
            "quy_Latn",  # Ayacucho Quechua
            "ayr_Latn",  # Central Aymara
            # Oceania
            "mri_Latn",  # Maori
            "smo_Latn",  # Samoan
            "fij_Latn",  # Fijian
            "tpi_Latn",  # Tok Pisin
            # Other
            "kab_Latn",  # Kabyle
            "plt_Latn",  # Plateau Malagasy
            "kac_Latn",  # Jingpho
            "lus_Latn",  # Mizo
            "taq_Latn",  # Tamasheq (Latin)
        ],
        script_family=ScriptFamily.LATIN,
    ),
    # --- CJK scripts ---
    "Hans": ScriptConfig(
        code="Hans",
        name="Chinese (Simplified)",
        direction="ltr",
        fonts=["NotoSansSC-Regular.ttf", "NotoSerifSC-Regular.ttf"],
        openlid_languages=["zho_Hans"],  # Chinese Simplified
        script_family=ScriptFamily.CJK,
        requires_shaping=True,
    ),
    "Hant": ScriptConfig(
        code="Hant",
        name="Chinese (Traditional)",
        direction="ltr",
        fonts=["NotoSansTC-Regular.ttf", "NotoSerifTC-Regular.ttf"],
        openlid_languages=["zho_Hant", "yue_Hant"],  # Chinese Traditional, Cantonese
        script_family=ScriptFamily.CJK,
        requires_shaping=True,
    ),
    "Jpan": ScriptConfig(
        code="Jpan",
        name="Japanese",
        direction="ltr",
        fonts=["NotoSansJP-Regular.ttf", "NotoSerifJP-Regular.ttf"],
        openlid_languages=["jpn_Jpan"],  # Japanese
        script_family=ScriptFamily.CJK,
        requires_shaping=True,
    ),
    "Kore": ScriptConfig(
        code="Kore",
        name="Korean",
        direction="ltr",
        fonts=["NotoSansKR-Regular.ttf", "NotoSerifKR-Regular.ttf"],
        openlid_languages=["kor_Hang"],  # Korean (OpenLID uses Hang for Hangul)
        script_family=ScriptFamily.CJK,
        requires_shaping=True,
    ),
    # --- Arabic script family ---
    # All 21 Arabic-script languages from OpenLID-v2
    "Arab": ScriptConfig(
        code="Arab",
        name="Arabic",
        direction="rtl",
        fonts=["NotoNaskhArabic-Regular.ttf", "NotoSansArabic-Regular.ttf"],
        openlid_languages=[
            # Arabic varieties
            "arb_Arab",  # Modern Standard Arabic
            "arz_Arab",  # Egyptian Arabic
            "ary_Arab",  # Moroccan Arabic
            "acm_Arab",  # Mesopotamian Arabic
            "apc_Arab",  # North Levantine Arabic
            "ajp_Arab",  # South Levantine Arabic
            "acq_Arab",  # Ta'izzi-Adeni Arabic
            "aeb_Arab",  # Tunisian Arabic
            "ars_Arab",  # Najdi Arabic
            # Persian and related
            "pes_Arab",  # Western Persian (Farsi)
            "prs_Arab",  # Dari
            "pbt_Arab",  # Southern Pashto
            "azb_Arab",  # South Azerbaijani
            # Urdu and related
            "urd_Arab",  # Urdu
            "snd_Arab",  # Sindhi
            # Other Arabic-script languages
            "uig_Arab",  # Uyghur
            "kas_Arab",  # Kashmiri (Arabic script)
            "ckb_Arab",  # Central Kurdish (Sorani)
            "ace_Arab",  # Acehnese (Arabic script)
            "bjn_Arab",  # Banjar (Arabic script)
            "knc_Arab",  # Central Kanuri (Arabic script)
        ],
        script_family=ScriptFamily.ARABIC,
        is_rtl=True,
        requires_shaping=True,
    ),
    "Hebr": ScriptConfig(
        code="Hebr",
        name="Hebrew",
        direction="rtl",
        fonts=["NotoSansHebrew-Regular.ttf", "NotoSerifHebrew-Regular.ttf"],
        openlid_languages=["heb_Hebr", "ydd_Hebr"],  # Hebrew, Eastern Yiddish
        script_family=ScriptFamily.ARABIC,  # Grouped for RTL handling
        is_rtl=True,
        requires_shaping=True,
    ),
    # --- Indic scripts ---
    "Deva": ScriptConfig(
        code="Deva",
        name="Devanagari",
        direction="ltr",
        fonts=["NotoSansDevanagari-Regular.ttf", "NotoSerifDevanagari-Regular.ttf"],
        openlid_languages=[
            "hin_Deva",  # Hindi
            "mar_Deva",  # Marathi
            "npi_Deva",  # Nepali
            "san_Deva",  # Sanskrit
            "bho_Deva",  # Bhojpuri
            "mai_Deva",  # Maithili
            "mag_Deva",  # Magahi
            "awa_Deva",  # Awadhi
            "hne_Deva",  # Chhattisgarhi
            "kas_Deva",  # Kashmiri (Devanagari)
        ],
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Beng": ScriptConfig(
        code="Beng",
        name="Bengali",
        direction="ltr",
        fonts=["NotoSansBengali-Regular.ttf", "NotoSerifBengali-Regular.ttf"],
        openlid_languages=[
            "ben_Beng",  # Bengali
            "asm_Beng",  # Assamese
            "mni_Beng",  # Meitei (Bengali script)
        ],
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Taml": ScriptConfig(
        code="Taml",
        name="Tamil",
        direction="ltr",
        fonts=["NotoSansTamil-Regular.ttf", "NotoSerifTamil-Regular.ttf"],
        openlid_languages=["tam_Taml"],  # Tamil
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Telu": ScriptConfig(
        code="Telu",
        name="Telugu",
        direction="ltr",
        fonts=["NotoSansTelugu-Regular.ttf", "NotoSerifTelugu-Regular.ttf"],
        openlid_languages=["tel_Telu"],  # Telugu
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Gujr": ScriptConfig(
        code="Gujr",
        name="Gujarati",
        direction="ltr",
        fonts=["NotoSansGujarati-Regular.ttf", "NotoSerifGujarati-Regular.ttf"],
        openlid_languages=["guj_Gujr"],  # Gujarati
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Knda": ScriptConfig(
        code="Knda",
        name="Kannada",
        direction="ltr",
        fonts=["NotoSansKannada-Regular.ttf", "NotoSerifKannada-Regular.ttf"],
        openlid_languages=["kan_Knda"],  # Kannada
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Mlym": ScriptConfig(
        code="Mlym",
        name="Malayalam",
        direction="ltr",
        fonts=["NotoSansMalayalam-Regular.ttf", "NotoSerifMalayalam-Regular.ttf"],
        openlid_languages=["mal_Mlym"],  # Malayalam
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Orya": ScriptConfig(
        code="Orya",
        name="Odia",
        direction="ltr",
        fonts=["NotoSansOriya-Regular.ttf"],
        openlid_languages=["ory_Orya"],  # Odia
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Sinh": ScriptConfig(
        code="Sinh",
        name="Sinhala",
        direction="ltr",
        fonts=["NotoSansSinhala-Regular.ttf", "NotoSerifSinhala-Regular.ttf"],
        openlid_languages=["sin_Sinh"],  # Sinhala
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    "Guru": ScriptConfig(
        code="Guru",
        name="Gurmukhi",
        direction="ltr",
        fonts=["NotoSansGurmukhi-Regular.ttf", "NotoSerifGurmukhi-Regular.ttf"],
        openlid_languages=["pan_Guru"],  # Eastern Panjabi
        script_family=ScriptFamily.INDIC,
        requires_shaping=True,
    ),
    # --- Southeast Asian scripts ---
    "Thai": ScriptConfig(
        code="Thai",
        name="Thai",
        direction="ltr",
        fonts=["NotoSansThai-Regular.ttf", "NotoSerifThai-Regular.ttf"],
        openlid_languages=["tha_Thai"],  # Thai
        script_family=ScriptFamily.OTHER,
        requires_shaping=True,
    ),
    "Khmr": ScriptConfig(
        code="Khmr",
        name="Khmer",
        direction="ltr",
        fonts=["NotoSansKhmer-Regular.ttf", "NotoSerifKhmer-Regular.ttf"],
        openlid_languages=["khm_Khmr"],  # Khmer
        script_family=ScriptFamily.OTHER,
        requires_shaping=True,
    ),
    "Mymr": ScriptConfig(
        code="Mymr",
        name="Myanmar",
        direction="ltr",
        fonts=["NotoSansMyanmar-Regular.ttf", "NotoSerifMyanmar-Regular.ttf"],
        openlid_languages=["mya_Mymr", "shn_Mymr"],  # Burmese, Shan
        script_family=ScriptFamily.OTHER,
        requires_shaping=True,
    ),
    "Laoo": ScriptConfig(
        code="Laoo",
        name="Lao",
        direction="ltr",
        fonts=["NotoSansLao-Regular.ttf", "NotoSerifLao-Regular.ttf"],
        openlid_languages=["lao_Laoo"],  # Lao
        script_family=ScriptFamily.OTHER,
        requires_shaping=True,
    ),
    "Tibt": ScriptConfig(
        code="Tibt",
        name="Tibetan",
        direction="ltr",
        fonts=["NotoSerifTibetan-Regular.ttf", "NotoSansTibetan-Regular.ttf"],
        openlid_languages=["bod_Tibt", "dzo_Tibt"],  # Standard Tibetan, Dzongkha
        script_family=ScriptFamily.OTHER,
        requires_shaping=True,
        min_font_size=16,  # Tibetan needs larger fonts for readability
        max_font_size=32,
    ),
    # --- Cyrillic and European scripts ---
    "Cyrl": ScriptConfig(
        code="Cyrl",
        name="Cyrillic",
        direction="ltr",
        fonts=[NOTO_SANS_FONT, NOTO_SERIF_FONT],
        openlid_languages=[
            "rus_Cyrl",  # Russian
            "ukr_Cyrl",  # Ukrainian
            "bul_Cyrl",  # Bulgarian
            "srp_Cyrl",  # Serbian
            "mkd_Cyrl",  # Macedonian
            "bel_Cyrl",  # Belarusian
            "kaz_Cyrl",  # Kazakh
            "kir_Cyrl",  # Kyrgyz
            "tgk_Cyrl",  # Tajik
            "khk_Cyrl",  # Halh Mongolian
            "bak_Cyrl",  # Bashkir
            "tat_Cyrl",  # Tatar
        ],
        script_family=ScriptFamily.CYRILLIC,
    ),
    "Grek": ScriptConfig(
        code="Grek",
        name="Greek",
        direction="ltr",
        fonts=[NOTO_SANS_FONT, NOTO_SERIF_FONT],
        openlid_languages=["ell_Grek"],  # Greek
        script_family=ScriptFamily.OTHER,
    ),
    "Armn": ScriptConfig(
        code="Armn",
        name="Armenian",
        direction="ltr",
        fonts=["NotoSansArmenian-Regular.ttf", "NotoSerifArmenian-Regular.ttf"],
        openlid_languages=["hye_Armn"],  # Armenian
        script_family=ScriptFamily.OTHER,
    ),
    "Geor": ScriptConfig(
        code="Geor",
        name="Georgian",
        direction="ltr",
        fonts=["NotoSansGeorgian-Regular.ttf", "NotoSerifGeorgian-Regular.ttf"],
        openlid_languages=["kat_Geor"],  # Georgian
        script_family=ScriptFamily.OTHER,
    ),
    # --- African scripts ---
    "Ethi": ScriptConfig(
        code="Ethi",
        name="Ethiopic",
        direction="ltr",
        fonts=["NotoSansEthiopic-Regular.ttf", "NotoSerifEthiopic-Regular.ttf"],
        openlid_languages=["amh_Ethi", "tir_Ethi"],  # Amharic, Tigrinya
        script_family=ScriptFamily.OTHER,
    ),
}

# =============================================================================
# Font Diversity Configuration
# =============================================================================
# Based on font_research.md - comprehensive typographic strategy for NaFlex training
# Ensures model learns invariant script features, not font-specific artifacts

# Font tier distribution (must sum to 1.0)
# Based on font_research.md and font_research_2.md (adversarial/handwriting analysis)
# Higher tier = more common in real-world documents
FONT_TIER_WEIGHTS: dict[str, float] = {
    "SYSTEM": 0.40,  # Most common system/default fonts (Arial equiv, MS defaults)
    "REGIONAL": 0.25,  # Region-specific popular fonts
    "STYLISTIC": 0.15,  # Stylistic variety (serif, display, literacy fonts)
    "HANDWRITING": 0.15,  # Authentic noise - cursive, brush, informal styles
    "ADVERSARIAL": 0.05,  # Mimicry fonts (Latin styled to look like other scripts)
}

# Font family recommendations by script
# Format: {script_code: {tier: [font_family_names]}}
# Font families are matched by substring in filename (e.g., "Liberation" matches "LiberationSans-Regular.ttf")
FONT_RECOMMENDATIONS: dict[str, dict[str, list[str]]] = {
    # Latin script - extensive variety needed
    "Latn": {
        "SYSTEM": ["Liberation", "Roboto", "DejaVu"],  # Arial/Times equivalents
        "REGIONAL": ["PTSans", "PTSerif", "FiraSans", "OpenSans"],  # Russian, European
        "STYLISTIC": ["Charis", "Gentium", "Andika", "Doulos"],  # SIL linguistic fonts
        "HANDWRITING": ["Caveat", "DancingScript", "PatrickHand"],  # Script fonts
        "ADVERSARIAL": [
            "UnifrakturMaguntia",
            "CinzelDecorative",
            "ComforterBrush",
            "MonsieurLaDoulaise",
        ],
    },
    # Arabic script - Naskh style (NOT Nastaliq)
    "Arab": {
        "SYSTEM": [
            "NotoNaskhArabic",
            "NotoSansArabic",
            "NotoKufiArabic",
        ],  # + Kufi geometric
        "REGIONAL": ["Amiri", "Scheherazade", "Tajawal"],  # Classical + modern web
        "STYLISTIC": ["AmiriQuran", "Mada", "ElMessiri"],  # Quranic + sans + display
        "HANDWRITING": ["ArefRuqaa", "PlaypenSansArabic"],  # Ruq'ah cascade style
        "ADVERSARIAL": ["ReemKufi", "Gulzar"],
    },
    # Urdu requires Nastaliq (cascading style) - CRITICAL distinction
    # Note: When language is urd_Arab or pnb_Arab, use Nastaliq fonts
    "Arab_Nastaliq": {
        "SYSTEM": ["NotoNastaliq", "AwamiNastaliq"],  # Nastaliq variants
        "REGIONAL": ["AwamiNastaliq"],  # SIL Nastaliq
        "STYLISTIC": ["NotoNastaliq"],  # Variety
        "HANDWRITING": ["AwamiNastaliq"],  # Nastaliq IS handwriting style
        "ADVERSARIAL": [],
    },
    # Hebrew
    "Hebr": {
        "SYSTEM": ["NotoSansHebrew", "NotoSerifHebrew"],
        "REGIONAL": ["NotoSansHebrew"],  # Limited variety available
        "STYLISTIC": ["NotoSerifHebrew", "NotoRashiHebrew"],  # Rashi for religious
        "HANDWRITING": ["DanaYad", "GvretLevin"],  # Ktav Yad (handwriting)
        "ADVERSARIAL": [],
    },
    # Devanagari (Hindi, Marathi, Nepali)
    "Deva": {
        "SYSTEM": ["Lohit-Devanagari", "NotoSansDevanagari"],  # Linux standard
        "REGIONAL": ["NotoSerifDevanagari", "Hind", "Mukta"],  # Serif + modern sans
        "STYLISTIC": ["TiroDevanagariHindi", "Baloo2"],  # Serif variety + display
        "HANDWRITING": ["Kalam"],  # Breaks shirorekha (headline)
        "ADVERSARIAL": ["Jaini", "Modak"],  # Fragmented shirorekha + filled counters
    },
    # Bengali (Bangladesh and India)
    "Beng": {
        "SYSTEM": ["NotoSansBengali", "NotoSerifBengali"],
        "REGIONAL": ["SolaimanLipi", "Kalpurush"],  # Bangladesh fonts - CRITICAL
        "STYLISTIC": ["NotoSerifBengali"],
        "HANDWRITING": ["Atma", "Galada"],  # Informal, display styles
        "ADVERSARIAL": [],
    },
    # Tamil
    "Taml": {
        "SYSTEM": ["NotoSansTamil", "NotoSerifTamil"],
        "REGIONAL": ["Catamaran", "HindMadurai", "MuktaMalar"],  # Modern sans families
        "STYLISTIC": ["ArimaMadurai"],  # Serif variety
        "HANDWRITING": ["Kavivanar"],  # Informal handwriting style
        "ADVERSARIAL": [],
    },
    # Telugu
    "Telu": {
        "SYSTEM": ["NotoSansTelugu", "NotoSerifTelugu"],
        "REGIONAL": ["HindGuntur", "Ramabhadra", "Mandali"],  # Modern sans families
        "STYLISTIC": ["NTR"],  # Variety
        "ADVERSARIAL": ["LakkiReddy"],  # Telugu display (structural destruction)
    },
    # Gujarati
    "Gujr": {
        "SYSTEM": ["NotoSansGujarati", "NotoSerifGujarati"],
        "REGIONAL": ["HindVadodara", "MuktaVaani"],  # Modern sans families
        "STYLISTIC": ["Rasa", "BalooBhai2"],  # Serif + display
        "ADVERSARIAL": [],
    },
    # Kannada
    "Knda": {
        "SYSTEM": ["NotoSansKannada", "NotoSerifKannada"],
        "REGIONAL": ["Timmana", "HindMysuru"],  # Modern sans families
        "STYLISTIC": ["BalooTamma2", "Benne"],  # Display + serif
        "ADVERSARIAL": [],
    },
    # Malayalam
    "Mlym": {
        "SYSTEM": ["NotoSansMalayalam", "NotoSerifMalayalam"],
        "REGIONAL": ["Manjari"],  # Modern Malayalam (SMC project)
        "STYLISTIC": ["NotoSerifMalayalam"],
        "HANDWRITING": ["Chilanka"],  # SMC handwriting font
        "ADVERSARIAL": [],
    },
    # Odia (most underserved — no NotoSerif exists)
    "Orya": {
        "SYSTEM": ["NotoSansOriya"],
        "REGIONAL": ["BalooBhaina2", "AnekOdia"],  # Display + variable sans
        "STYLISTIC": ["Alkatra"],  # Handwritten-style display
        "ADVERSARIAL": [],
    },
    # Sinhala
    "Sinh": {
        "SYSTEM": ["NotoSansSinhala", "NotoSerifSinhala"],
        "REGIONAL": ["AbhayaLibre"],  # Sinhala serif (Google Fonts)
        "STYLISTIC": ["Yaldevi"],  # Sinhala sans-serif (Google Fonts)
        "ADVERSARIAL": ["StickNoBills"],  # Condensed stencil (structural destruction)
    },
    # Gurmukhi (Punjabi)
    "Guru": {
        "SYSTEM": ["NotoSansGurmukhi", "NotoSerifGurmukhi"],
        "REGIONAL": ["MuktaMahee"],  # Modern sans (Ek Type foundry)
        "STYLISTIC": ["BalooPaaji2"],  # Display style
        "ADVERSARIAL": [],
    },
    # Thai - looped vs loopless distinction
    "Thai": {
        "SYSTEM": [
            "NotoSansThai",
            "NotoSerifThai",
            "NotoLoopedThai",
        ],  # Loopless + looped
        "REGIONAL": ["Kanit", "Pridi"],  # Geometric sans + serif (Google Fonts)
        "STYLISTIC": ["BaiJamjuree", "Mitr"],  # Square sans + rounded sans
        "HANDWRITING": ["Itim"],  # Thai handwriting style
        "ADVERSARIAL": ["Charmonman"],  # Latin-like Thai decorative
    },
    # Khmer
    "Khmr": {
        "SYSTEM": ["NotoSansKhmer", "NotoSerifKhmer"],
        "REGIONAL": ["Battambang", "Content"],  # Traditional + modern (Google Fonts)
        "STYLISTIC": ["Moul"],  # Decorative/header style
        "ADVERSARIAL": ["Moul"],  # Moul: wavy ornamental contours (dual-listed)
    },
    # Myanmar - Padauk for minorities
    "Mymr": {
        "SYSTEM": ["NotoSansMyanmar", "NotoSerifMyanmar"],
        "REGIONAL": ["Padauk"],  # SIL - covers Shan, Karen minorities
        "STYLISTIC": ["NotoSerifMyanmar", "Khyay"],  # Serif + display/headline
        "ADVERSARIAL": [],
    },
    # Lao
    "Laoo": {
        "SYSTEM": [
            "NotoSansLao",
            "NotoSerifLao",
            "NotoLoopedLao",
        ],  # Traditional looped
        "REGIONAL": [
            "NotoLoopedLao",
            "Phetsarath",
        ],  # Looped variant + govt calligraphic
        "STYLISTIC": ["NotoSerifLao"],
        "ADVERSARIAL": [],
    },
    # Tibetan - larger font sizes needed
    "Tibt": {
        "SYSTEM": ["NotoSerifTibetan", "NotoSansTibetan"],
        "REGIONAL": [
            "Jomolhari",
            "Uchen",
            "DDCUchen",
        ],  # Open Pecha + Google + fontlibrary
        "STYLISTIC": [
            "TibetanMachineUni",
            "MonlamUni",
        ],  # GPL fonts with distinct styles
    },
    # CJK - Simplified Chinese
    "Hans": {
        "SYSTEM": ["NotoSansSC", "NotoSerifSC", "NotoSansCJKsc"],
        "REGIONAL": ["NotoSerifSC"],
        "STYLISTIC": ["NotoSansSC"],
        "HANDWRITING": ["ARKaiti", "MaShanZheng"],  # Brush/Kaiti styles
        "ADVERSARIAL": ["LiuJianMaoCao"],  # Grass script (caoshu) — radical destruction
    },
    # CJK - Traditional Chinese
    "Hant": {
        "SYSTEM": ["NotoSansTC", "NotoSerifTC", "NotoSansCJKtc"],
        "REGIONAL": ["NotoSerifTC"],
        "STYLISTIC": ["NotoSansTC"],
        "HANDWRITING": ["ARKaiti"],  # Brush styles
        "ADVERSARIAL": [],
    },
    # CJK - Japanese
    "Jpan": {
        "SYSTEM": ["NotoSansJP", "NotoSerifJP", "NotoSansCJKjp"],
        "REGIONAL": ["NotoSerifJP"],
        "STYLISTIC": ["NotoSansJP"],
        "HANDWRITING": ["HiraginoGyosho", "Kouzan"],  # Semi-cursive, dry brush
        "ADVERSARIAL": [],
    },
    # CJK - Korean
    "Kore": {
        "SYSTEM": ["NotoSansKR", "NotoSerifKR", "NotoSansCJKkr"],
        "REGIONAL": [
            "NanumGothic",
            "NanumMyeongjo",
        ],  # Gothic (sans) + Myeongjo (serif)
        "STYLISTIC": ["NotoSerifKR"],
        "HANDWRITING": ["NanumPen", "NanumBrush"],  # Pen/brush scripts
        "ADVERSARIAL": ["NanumBrushScript"],  # Extreme brush calligraphy
    },
    # Cyrillic - Bulgarian has distinct glyph forms
    "Cyrl": {
        "SYSTEM": ["Liberation", "DejaVu", "NotoSans", "NotoSerif"],
        "REGIONAL": ["PTSans", "PTSerif"],  # Russian ParaType standard
        "STYLISTIC": ["FiraSans"],  # Bulgarian locl features
        "HANDWRITING": ["BadScript", "Caveat", "MarckScript"],  # Russian cursive
        "ADVERSARIAL": ["Lobster", "Pacifico"],  # Cross-script unification with Latin
    },
    # Bulgarian Cyrillic - distinct glyph forms (looks like Latin g)
    "Cyrl_Bulgarian": {
        "SYSTEM": ["NotoSans", "NotoSerif"],
        "REGIONAL": ["Simbal", "Vollkorn"],  # Bulgarian-specific locl fonts
        "STYLISTIC": ["FiraSans", "Exo2"],  # With locl features enabled
        "HANDWRITING": ["BadScript"],
        "ADVERSARIAL": [],
    },
    # Greek
    "Grek": {
        "SYSTEM": ["Liberation", "DejaVu", "NotoSans", "NotoSerif"],
        "REGIONAL": ["NotoSerif", "GFSNeohellenic"],  # Historical academic style
        "STYLISTIC": ["NotoSans"],
        "HANDWRITING": ["Atma", "AMSEuler"],  # Marker, blackboard math
        "ADVERSARIAL": ["GFSBodoni", "EBGaramond"],  # High-contrast + 3-script unified
    },
    # Armenian
    "Armn": {
        "SYSTEM": ["NotoSansArmenian", "NotoSerifArmenian"],
        "REGIONAL": ["NotoSerifArmenian"],
        "STYLISTIC": ["NotoSansArmenian"],
    },
    # Georgian
    "Geor": {
        "SYSTEM": ["NotoSansGeorgian", "NotoSerifGeorgian"],
        "REGIONAL": ["NotoSerifGeorgian"],
        "STYLISTIC": ["NotoSansGeorgian"],
    },
    # Ethiopic
    "Ethi": {
        "SYSTEM": ["NotoSansEthiopic", "NotoSerifEthiopic"],
        "REGIONAL": ["Abyssinica", "Brana"],  # SIL + raeytype
        "STYLISTIC": ["GeezManuscriptZemen"],  # COLR manuscript style
    },
    # Cherokee — limited OFL ecosystem
    "Cher": {
        "SYSTEM": ["NotoSansCherokee"],
        "REGIONAL": [
            "AboriginalSans",
            "AboriginalSerif",
        ],  # Chris Harvey, covers Cher+Cans
        "STYLISTIC": ["NotoSansCherokee"],
    },
    # Canadian Syllabics (Unified Canadian Aboriginal Syllabics)
    "Cans": {
        "SYSTEM": ["NotoSansCanadianAboriginal"],
        "REGIONAL": ["BJCree", "AboriginalSans"],  # SIL Cree + Chris Harvey
        "STYLISTIC": ["AboriginalSerif"],  # Serif variety
    },
}

# Languages that require Nastaliq style (instead of Naskh)
# These will use FONT_RECOMMENDATIONS["Arab_Nastaliq"] instead of "Arab"
NASTALIQ_LANGUAGES: set[str] = {
    "urd_Arab",  # Urdu
    "pnb_Arab",  # Western Punjabi (Shahmukhi)
    "kas_Arab",  # Kashmiri (Arabic script)
    "snd_Arab",  # Sindhi (some prefer Nastaliq)
}

# Languages that require Bulgarian Cyrillic localized forms
# These will use FONT_RECOMMENDATIONS["Cyrl_Bulgarian"] for proper glyph rendering
BULGARIAN_CYRILLIC_LANGUAGES: set[str] = {
    "bul_Cyrl",  # Bulgarian
}

# =============================================================================
# Mimicry/Adversarial Font Configuration
# =============================================================================
# Based on font_research_2.md - fonts designed to LOOK like other scripts
# CRITICAL: These are Latin fonts styled to mimic target scripts
# They must be labeled as "Latn" (their true script) NOT the target script
# This trains the model to distinguish topology from texture

# Mimicry fonts: Latin fonts that visually mimic other scripts
# Format: {target_script_mimicked: [font_family_names]}
# These fonts should be rendered with LATIN text but generate visual confusion
MIMICRY_FONTS: dict[str, list[str]] = {
    # Latin fonts that look Arabic (Orientalist tropes)
    "Arab": ["Alhambra", "Aladin", "ArabianOnenightstand"],
    # Latin fonts that look Greek (stone-carved aesthetic)
    "Grek": ["Lithos", "CaesarDressing", "Dalek", "PFHellenica"],
    # Latin fonts that look Hebrew (square aspect, reversed contrast)
    "Hebr": ["Sefarad", "HebrewLatino"],
    # Latin fonts that look Chinese ("Chop Suey" / "Wonton" style)
    "Hans": ["Wonton", "Shanghai", "ChopSuey"],
    # Latin fonts that look Cyrillic (Constructivist aesthetic)
    "Cyrl": ["Konstruktor", "RussoOne"],
}

# Handwriting fonts by script for authentic noise
# These capture the topological transformations that occur in real handwriting
HANDWRITING_FONTS: dict[str, list[str]] = {
    # Russian cursive: т→m, и→u topological transforms
    "Cyrl": ["BadScript", "Caveat", "MarckScript"],
    # Arabic Ruq'ah: cascading baseline, dot merging
    "Arab": ["ArefRuqaa", "PlaypenSansArabic", "Kaleem"],
    # Hebrew Ktav Yad: completely different from Dfus (print)
    "Hebr": ["DanaYad", "GvretLevin"],
    # CJK brush styles: stroke connectivity, ghost strokes
    "Hans": ["ARKaiti", "MaShanZheng"],
    "Jpan": ["HiraginoGyosho", "Kouzan"],
    "Kore": ["NanumPen", "NanumBrush"],
    # Indic: breaks shirorekha (headline)
    "Deva": ["Kalam"],
    "Beng": ["Atma", "Galada"],
    # Greek: marker aesthetics, blackboard math
    "Grek": ["GFSNeohellenic", "Atma", "AMSEuler"],
    # Latin: standard script fonts
    "Latn": ["Caveat", "DancingScript", "PatrickHand", "BadScript"],
}


# Priority scripts for MVP (10 scripts covering major script families)
MVP_SCRIPTS: list[str] = [
    "Latn",  # Latin - baseline
    "Arab",  # Arabic - RTL, complex shaping
    "Deva",  # Devanagari - Indic conjuncts
    "Hans",  # Chinese Simplified - CJK
    "Jpan",  # Japanese - Mixed scripts
    "Kore",  # Korean - Hangul blocks
    "Cyrl",  # Cyrillic - LTR non-Latin
    "Grek",  # Greek - diacritics
    "Thai",  # Thai - no word boundaries
    "Tibt",  # Tibetan - vertical stacking
]


def get_script_config(script_code: str) -> ScriptConfig | None:
    """Get configuration for a script by its ISO 15924 code.

    Args:
        script_code (str): ISO 15924 4-letter script code

    Returns:
        ScriptConfig | None: ScriptConfig if found, None otherwise

    """
    return SCRIPT_CONFIGS.get(script_code)


def get_scripts_by_family(family: ScriptFamily) -> list[ScriptConfig]:
    """Get all script configurations for a given script family.

    Args:
        family (ScriptFamily): Script family to filter by

    Returns:
        list[ScriptConfig]: List of ScriptConfig objects in that family

    """
    return [cfg for cfg in SCRIPT_CONFIGS.values() if cfg.script_family == family]


def get_rtl_scripts() -> list[ScriptConfig]:
    """Get all right-to-left script configurations."""
    return [cfg for cfg in SCRIPT_CONFIGS.values() if cfg.is_rtl]


def get_complex_scripts() -> list[ScriptConfig]:
    """Get all scripts that require HarfBuzz text shaping."""
    return [cfg for cfg in SCRIPT_CONFIGS.values() if cfg.requires_shaping]


__all__ = [
    "BULGARIAN_CYRILLIC_LANGUAGES",
    "CJK_VERTICAL_RATIOS",
    "COLOR_MODE_WEIGHTS",
    "DENSITY_TO_LAYER2",
    "DOCUMENT_COMPOSITION_WEIGHTS",
    "ENGLISH_SECONDARY_WEIGHT",
    "FONT_RECOMMENDATIONS",
    "FONT_TIER_WEIGHTS",
    "HANDWRITING_FONTS",
    "LANGUAGE_WEIGHTS",
    "LAYOUT_TO_LAYER2",
    "LAYOUT_WEIGHTS",
    "MIMICRY_FONTS",
    "MVP_SCRIPTS",
    "NASTALIQ_LANGUAGES",
    "OUTPUT_SIZES",
    "QUALITY_TIER_WEIGHTS",
    "RESOLUTION_TIERS",
    "RESOLUTION_TIER_WEIGHTS",
    "SCRIPT_CONFIGS",
    "SKEW_RANGE_DEGREES",
    "TEXT_DENSITY_WEIGHTS",
    "TWO_SCRIPT_COMBINATIONS",
    "ColorMode",
    "LayoutType",
    "ScriptConfig",
    "TextDensity",
    "get_complex_scripts",
    "get_rtl_scripts",
    "get_script_config",
    "get_scripts_by_family",
]
