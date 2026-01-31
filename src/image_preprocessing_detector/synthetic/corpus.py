# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Text corpus management for synthetic document generation.

This module provides text corpus loading, caching, and retrieval for
generating synthetic multi-script documents. It integrates with
OpenLID-v2 from HuggingFace for language-specific text samples.

The TextCorpusManager handles:
- Streaming OpenLID-v2 data from HuggingFace
- Mapping language codes to ISO 15924 scripts
- Caching text samples locally as JSON
- Retrieving text by script and density requirements

Example:
    >>> from image_preprocessing_detector.synthetic.corpus import TextCorpusManager
    >>> manager = TextCorpusManager()
    >>> manager.load_from_cache_or_download()
    >>> text, lang = manager.get_text_with_language("Arab", TextDensity.MEDIUM)
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.synthetic.config import (
    SCRIPT_CONFIGS,
    TextDensity,
    get_script_config,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# OpenLID-v2 dataset configuration
OPENLID_DATASET = "laurievb/OpenLID-v2"
OPENLID_CONFIG = "default"  # Changed from 'full' - dataset restructured

# Default cache location
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "synthetic_corpus"

# Script fallback mappings for scripts that share character sets
# When a script has no corpus, use the fallback script's corpus
SCRIPT_FALLBACKS: dict[str, str] = {
    "Hans": "Hant",  # Simplified Chinese uses Traditional Chinese corpus
    # Both use same Unicode blocks, just different character variants
}

# GCS bucket for pre-downloaded corpus (faster than HuggingFace streaming)
GCS_CORPUS_BUCKET = "gs://image_detection_b/datasets/synthetic-corpus/openlid-v2"

# Text length ranges for each density level (in characters)
DENSITY_CHAR_RANGES: dict[TextDensity, tuple[int, int]] = {
    TextDensity.MINIMAL: (5, 30),
    TextDensity.SHORT: (30, 150),
    TextDensity.MEDIUM: (150, 500),
    TextDensity.LONG: (500, 1500),
    TextDensity.DENSE: (1500, 5000),
}

# Sample text for testing when corpus is unavailable
# These are public domain / example texts for each script
SAMPLE_TEXTS: dict[str, tuple[str, str]] = {
    "Latn": (
        "The quick brown fox jumps over the lazy dog. This pangram contains every letter "
        "of the English alphabet at least once. Document preprocessing is essential for "
        "high-quality OCR results. Image quality assessment helps identify degradation.",
        "en",
    ),
    "Arab": (
        "السلام عليكم ورحمة الله وبركاته. هذا نص تجريبي باللغة العربية لاختبار "
        "عرض النصوص من اليمين إلى اليسار. الخط العربي جميل ومتنوع.",
        "ar",
    ),
    "Deva": (
        "नमस्ते। यह हिंदी में एक परीक्षण पाठ है। देवनागरी लिपि भारत की "
        "कई भाषाओं में उपयोग होती है। यह एक प्राचीन और सुंदर लिपि है।",
        "hi",
    ),
    "Hans": (
        "你好世界。这是一段简体中文测试文本。中文是世界上使用人数最多的语言之一。"
        "汉字有着悠久的历史和丰富的文化内涵。文档预处理对于高质量的OCR结果至关重要。",
        "zh",
    ),
    "Hant": (
        "你好世界。這是一段繁體中文測試文本。中文是世界上使用人數最多的語言之一。"
        "漢字有著悠久的歷史和豐富的文化內涵。",
        "zh",
    ),
    "Jpan": (
        "こんにちは世界。これは日本語のテストテキストです。日本語は漢字、ひらがな、"
        "カタカナの三種類の文字を使用します。文書の前処理は高品質なOCR結果に不可欠です。",
        "ja",
    ),
    "Kore": (
        "안녕하세요 세계. 이것은 한국어 테스트 텍스트입니다. 한글은 세종대왕이 창제한 "
        "과학적인 문자 체계입니다. 문서 전처리는 고품질 OCR 결과에 필수적입니다.",
        "ko",
    ),
    "Cyrl": (
        "Привет мир. Это тестовый текст на русском языке. Кириллица используется "
        "для написания многих славянских языков. Предварительная обработка документов важна.",
        "ru",
    ),
    "Grek": (
        "Γειά σου κόσμε. Αυτό είναι ένα δοκιμαστικό κείμενο στα ελληνικά. "
        "Η ελληνική γλώσσα έχει μακρά ιστορία και πλούσια κουλτούρα.",
        "el",
    ),
    "Thai": (
        "สวัสดีโลก นี่คือข้อความทดสอบภาษาไทย ภาษาไทยเป็นภาษาที่มีวรรณยุกต์ "
        "และไม่มีการเว้นวรรคระหว่างคำ การประมวลผลเอกสารล่วงหน้ามีความสำคัญ",
        "th",
    ),
    "Tibt": (
        "བཀྲ་ཤིས་བདེ་ལེགས། འདི་ནི་བོད་ཡིག་གི་ཚོད་ལྟའི་ཡི་གེ་ཞིག་ཡིན། "
        "བོད་ཡིག་ནི་འཇིག་རྟེན་གྱི་ཡིག་རིགས་གལ་ཆེན་ཞིག་ཡིན།",
        "bo",
    ),
    "Hebr": (
        "שלום עולם. זהו טקסט בדיקה בעברית. העברית היא שפה שמית עתיקה "
        "שחזרה לשימוש יומיומי במאה העשרים.",
        "he",
    ),
    "Beng": (
        "নমস্কার বিশ্ব। এটি বাংলায় একটি পরীক্ষামূলক পাঠ্য। বাংলা ভাষা "
        "বিশ্বের সবচেয়ে সুন্দর ভাষাগুলির মধ্যে একটি।",
        "bn",
    ),
    "Taml": (
        "வணக்கம் உலகம். இது தமிழில் ஒரு சோதனை உரை. தமிழ் மொழி "
        "உலகின் மிகப் பழமையான மொழிகளில் ஒன்று.",
        "ta",
    ),
    # Additional Indic scripts
    "Telu": (
        "హలో ప్రపంచం. ఇది తెలుగులో ఒక పరీక్ష పాఠ్యం. తెలుగు భాషా భారతదేశంలో ఒక ప్రాచీన మరియు అందమైన భాష.",
        "te",
    ),
    "Gujr": (
        "નમસ્તે વિશ્વ. આ ગુજરાતીમાં એક પરીક્ષણ લખાણ છે. ગુજરાતી ભાષા "
        "ભારતની સૌથી સમૃદ્ધ ભાષાઓમાંની એક છે.",
        "gu",
    ),
    "Knda": (
        "ನಮಸ್ಕಾರ ಪ್ರಪಂಚ. ಇದು ಕನ್ನಡದಲ್ಲಿ ಒಂದು ಪರೀಕ್ಷಾ ಪಠ್ಯ. ಕನ್ನಡ ಭಾಷೆ "
        "ಭಾರತದ ಅತ್ಯಂತ ಹಳೆಯ ಭಾಷೆಗಳಲ್ಲಿ ಒಂದು.",
        "kn",
    ),
    "Mlym": (
        "ഹലോ ലോകം. ഇത് മലയാളത്തിൽ ഒരു പരീക്ഷണ വാചകമാണ്. മലയാളം ഭാഷ "
        "ഭാരതത്തിലെ ഏറ്റവും സുന്ദരമായ ഭാഷകളിൽ ഒന്നാണ്.",
        "ml",
    ),
    "Orya": (
        "ନମସ୍କାର ବିଶ୍ୱ। ଏହା ଓଡ଼ିଆରେ ଏକ ପରୀକ୍ଷା ପାଠ୍ୟ। ଓଡ଼ିଆ ଭାଷା ଭାରତର ଏକ ପ୍ରାଚୀନ ଓ ସମୃଦ୍ଧ ଭାଷା।",
        "or",
    ),
    "Sinh": (
        "හෙලෝ ලෝකය. මෙය සිංහලෙන් පරීක්ෂණ පෙළකි. සිංහල භාෂාව ශ්‍රී ලංකාවේ ප්‍රධාන භාෂාවයි.",
        "si",
    ),
    "Guru": (
        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਦੁਨੀਆ। ਇਹ ਪੰਜਾਬੀ ਵਿੱਚ ਇੱਕ ਟੈਸਟ ਟੈਕਸਟ ਹੈ। ਪੰਜਾਬੀ ਭਾਸ਼ਾ "
        "ਭਾਰਤ ਅਤੇ ਪਾਕਿਸਤਾਨ ਵਿੱਚ ਬੋਲੀ ਜਾਂਦੀ ਹੈ।",
        "pa",
    ),
    # Southeast Asian scripts
    "Khmr": (
        "សួស្តីពិភពលោក។ នេះគឺជាអត្ថបទសាកល្បងជាភាសាខ្មែរ។ ភាសាខ្មែរ ជាភាសាផ្លូវការរបស់ប្រទេសកម្ពុជា។",
        "km",
    ),
    "Mymr": (
        "မင်္ဂလာပါ ကမ္ဘာ။ ဒါက မြန်မာဘာသာစကားနဲ့ စမ်းသပ်စာသားပါ။ "
        "မြန်မာဘာသာစကားသည် မြန်မာနိုင်ငံ၏ တရားဝင်ဘာသာစကားဖြစ်သည်။",
        "my",
    ),
    "Laoo": (
        "ສະບາຍດີໂລກ. ນີ້ແມ່ນຂໍ້ຄວາມທົດສອບເປັນພາສາລາວ. ພາສາລາວ ແມ່ນພາສາທາງການຂອງປະເທດລາວ.",
        "lo",
    ),
    # European scripts
    "Armn": (
        "Բարեւ աշխարհ. Սա հայերեն փորձնական տեքստն է. Հայերենը հին լեզու է.",
        "hy",
    ),
    "Geor": (
        "გამარჯობა სამყარო. ეს არის სატესტო ტექსტი ქართულ ენაზე. ქართული ენა "
        "საქართველოს ოფიციალური ენაა.",
        "ka",
    ),
    # African scripts
    "Ethi": (
        "ሰላም ዓለም። ይህ በአማርኛ የሙከራ ጽሑፍ ነው። አማርኛ ቋንቋ "
        "የኢትዮጵያ ፌዴራላዊ ዴሞክራሲያዊ ሪፐብሊክ ይፋዊ ቋንቋ ነው።",
        "am",
    ),
}


@dataclass
class TextSample:
    """A text sample from the corpus.

    Attributes:
        text: The actual text content
        language_code: ISO 639-1/3 language code
        script_code: ISO 15924 script code
        source: Where the text came from (e.g., "openlid-v2")
        char_count: Number of characters
    """

    text: str
    language_code: str
    script_code: str
    source: str = "openlid-v2"
    char_count: int = 0

    def __post_init__(self) -> None:
        """Calculate character count if not provided."""
        if self.char_count == 0:
            self.char_count = len(self.text)


@dataclass
class ScriptCorpus:
    """Corpus of text samples for a single script.

    Attributes:
        script_code: ISO 15924 script code
        samples: List of TextSample objects
        samples_by_density: Samples organized by density category
    """

    script_code: str
    samples: list[TextSample] = field(default_factory=list)
    samples_by_density: dict[TextDensity, list[TextSample]] = field(
        default_factory=dict
    )

    def add_sample(self, sample: TextSample) -> None:
        """Add a sample and categorize by density.

        Args:
            sample: TextSample to add
        """
        self.samples.append(sample)

        # Categorize by density based on character count
        for density, (min_chars, max_chars) in DENSITY_CHAR_RANGES.items():
            if min_chars <= sample.char_count < max_chars:
                if density not in self.samples_by_density:
                    self.samples_by_density[density] = []
                self.samples_by_density[density].append(sample)
                break

    def get_sample(
        self,
        density: TextDensity | None = None,
        rng: random.Random | None = None,
    ) -> TextSample | None:
        """Get a random sample, optionally filtered by density.

        Args:
            density: Optional density filter
            rng: Optional seeded Random instance for reproducibility.
                 If None, uses global random (not recommended for reproducible generation).

        Returns:
            Random TextSample or None if no samples available
        """
        # FIX BUG #5: Use provided RNG for reproducibility, fallback to global random
        choice_fn = rng.choice if rng else random.choice

        if density and density in self.samples_by_density:
            samples = self.samples_by_density[density]
            if samples:
                return choice_fn(samples)

        # Fallback to any sample
        if self.samples:
            return choice_fn(self.samples)

        return None


class TextCorpusManager:
    """Manages text corpora for synthetic document generation.

    Handles loading, caching, and retrieval of text samples from
    OpenLID-v2 organized by script for multi-script document
    generation.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_samples_per_language: int = 5000,
        min_text_length: int = 10,
        max_text_length: int = 5000,
        seed: int | None = None,
    ) -> None:
        """Initialize the corpus manager.

        Args:
            cache_dir: Directory for caching downloaded corpus
            max_samples_per_language: Maximum samples to load per language
            min_text_length: Minimum text length in characters
            max_text_length: Maximum text length in characters
            seed: Random seed for reproducible text selection
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_samples_per_language = max_samples_per_language
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length

        # FIX BUG #5: Use seeded RNG for reproducible sampling
        self._seed = seed
        self._rng = random.Random(seed) if seed is not None else None

        self.corpora: dict[str, ScriptCorpus] = {}
        self._loaded = False

    def set_seed(self, seed: int | None) -> None:
        """Set or update the random seed for reproducible sampling.

        Args:
            seed: Random seed (None uses global random)
        """
        self._seed = seed
        self._rng = random.Random(seed) if seed is not None else None

    def _get_cache_path(self, script_code: str) -> Path:
        """Get cache file path for a script.

        Args:
            script_code: ISO 15924 script code

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"corpus_{script_code}.json"

    def load_sample_texts(self, script_codes: list[str] | None = None) -> int:
        """Load built-in sample texts for testing.

        Uses predefined sample texts when corpus download is unavailable.

        Args:
            script_codes: Specific scripts to load (None = all available)

        Returns:
            Number of samples loaded
        """
        scripts_to_load = script_codes or list(SAMPLE_TEXTS.keys())
        total_loaded = 0

        for script_code in scripts_to_load:
            if script_code not in SAMPLE_TEXTS:
                continue

            text, lang_code = SAMPLE_TEXTS[script_code]

            if script_code not in self.corpora:
                self.corpora[script_code] = ScriptCorpus(script_code=script_code)

            sample = TextSample(
                text=text,
                language_code=lang_code,
                script_code=script_code,
                source="built_in_sample",
            )
            self.corpora[script_code].add_sample(sample)
            total_loaded += 1

        self._loaded = total_loaded > 0
        logger.info("Loaded %d built-in sample texts", total_loaded)
        return total_loaded

    def load_from_cache(self, script_codes: list[str] | None = None) -> int:
        """Load corpora from cached JSON files.

        Args:
            script_codes: Specific scripts to load (None = all available)

        Returns:
            Number of samples loaded
        """
        total_loaded = 0
        scripts_to_load = script_codes or list(SCRIPT_CONFIGS.keys())

        for script_code in scripts_to_load:
            cache_path = self._get_cache_path(script_code)
            if not cache_path.exists():
                logger.debug("No cache found for script: %s", script_code)
                continue

            try:
                with open(cache_path) as f:
                    data = json.load(f)

                corpus = ScriptCorpus(script_code=script_code)
                for sample_data in data.get("samples", []):
                    sample = TextSample(
                        text=sample_data["text"],
                        language_code=sample_data["language_code"],
                        script_code=script_code,
                        source=sample_data.get("source", "openlid-v2"),
                    )
                    corpus.add_sample(sample)

                self.corpora[script_code] = corpus
                total_loaded += len(corpus.samples)
                logger.info(
                    "Loaded %d samples for script %s from cache",
                    len(corpus.samples),
                    script_code,
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load cache for %s: %s", script_code, e)

        self._loaded = total_loaded > 0
        return total_loaded

    def save_to_cache(self, script_code: str) -> None:
        """Save corpus to cache file.

        Args:
            script_code: Script code to save
        """
        if script_code not in self.corpora:
            return

        corpus = self.corpora[script_code]
        cache_path = self._get_cache_path(script_code)

        data = {
            "script_code": script_code,
            "sample_count": len(corpus.samples),
            "samples": [
                {
                    "text": s.text,
                    "language_code": s.language_code,
                    "source": s.source,
                }
                for s in corpus.samples
            ],
        }

        with open(cache_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(
            "Saved %d samples for %s to cache", len(corpus.samples), script_code
        )

    def load_from_gcs(
        self,
        script_codes: list[str] | None = None,
        gcs_path: str = GCS_CORPUS_BUCKET,
    ) -> int:
        """Load corpus from Google Cloud Storage (faster than HuggingFace).

        Downloads pre-processed corpus files from GCS to local cache,
        then loads them. This is significantly faster than streaming
        from HuggingFace for subsequent runs.

        Args:
            script_codes: Specific scripts to load (None = all configured)
            gcs_path: GCS bucket path (default: GCS_CORPUS_BUCKET)

        Returns:
            Number of samples loaded
        """
        import subprocess

        scripts_to_load = script_codes or list(SCRIPT_CONFIGS.keys())
        total_loaded = 0

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading corpus from GCS: %s", gcs_path)

        for script_code in scripts_to_load:
            cache_path = self._get_cache_path(script_code)

            # Skip if already cached
            if cache_path.exists():
                logger.debug("Script %s already cached, skipping download", script_code)
                continue

            gcs_file = f"{gcs_path}/corpus_{script_code}.json"

            try:
                # Download using gsutil
                result = subprocess.run(
                    ["gsutil", "cp", gcs_file, str(cache_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    logger.info("Downloaded corpus_%s.json from GCS", script_code)
                else:
                    logger.debug(
                        "Script %s not found in GCS (may use fallback): %s",
                        script_code,
                        result.stderr.strip(),
                    )

            except FileNotFoundError:
                logger.warning("gsutil not installed, falling back to HuggingFace")
                return self.load_from_openlid(script_codes)

        # Load from cache
        total_loaded = self.load_from_cache(scripts_to_load)
        logger.info("Loaded %d samples from GCS corpus", total_loaded)
        return total_loaded

    def load_from_openlid(
        self,
        script_codes: list[str] | None = None,
        streaming: bool = True,
    ) -> int:
        """Load text corpus from OpenLID-v2 dataset.

        Args:
            script_codes: Specific scripts to load (None = all configured)
            streaming: Use streaming mode to avoid downloading full dataset

        Returns:
            Number of samples loaded
        """
        try:
            from datasets import load_dataset
        except ImportError:
            logger.error(
                "datasets library not installed. Run: uv sync --extra synthetic"
            )
            return 0

        scripts_to_load = script_codes or list(SCRIPT_CONFIGS.keys())
        total_loaded = 0

        # Build language to script mapping
        lang_to_scripts: dict[str, list[str]] = {}
        for script_code in scripts_to_load:
            config = get_script_config(script_code)
            if config:
                for lang in config.openlid_languages:
                    if lang not in lang_to_scripts:
                        lang_to_scripts[lang] = []
                    lang_to_scripts[lang].append(script_code)

        logger.info(
            "Loading OpenLID-v2 for %d scripts covering %d languages",
            len(scripts_to_load),
            len(lang_to_scripts),
        )

        # Initialize corpora
        for script_code in scripts_to_load:
            if script_code not in self.corpora:
                self.corpora[script_code] = ScriptCorpus(script_code=script_code)

        try:
            # Load dataset (streaming to avoid full download)
            dataset = load_dataset(
                OPENLID_DATASET,
                OPENLID_CONFIG,
                split="train",
                streaming=streaming,
            )

            # Track samples per language
            samples_per_lang: dict[str, int] = {}
            items_processed = 0
            items_matched = 0

            for item in dataset:  # type: ignore[union-attr]
                items_processed += 1

                # Log progress every 100K items
                if items_processed % 100000 == 0:
                    langs_complete = sum(
                        1
                        for l in lang_to_scripts
                        if samples_per_lang.get(l, 0) >= self.max_samples_per_language
                    )
                    logger.info(
                        "Progress: %d items processed, %d matched, %d/%d languages complete",
                        items_processed,
                        items_matched,
                        langs_complete,
                        len(lang_to_scripts),
                    )

                # Item type varies by streaming mode, cast to dict for access
                item_dict: dict[str, str] = dict(item)  # type: ignore[arg-type]
                lang = item_dict.get("language", item_dict.get("lang", ""))
                text = item_dict.get("text", "")

                # Skip if language not in our mapping
                if lang not in lang_to_scripts:
                    continue

                # Skip if we have enough for this language
                if samples_per_lang.get(lang, 0) >= self.max_samples_per_language:
                    continue

                # Validate text length
                text_len = len(text)
                if text_len < self.min_text_length or text_len > self.max_text_length:
                    continue

                # Clean text (basic normalization)
                text = text.strip()
                if not text:
                    continue

                # Add to all applicable scripts
                for script_code in lang_to_scripts[lang]:
                    sample = TextSample(
                        text=text,
                        language_code=lang,
                        script_code=script_code,
                    )
                    self.corpora[script_code].add_sample(sample)
                    total_loaded += 1

                samples_per_lang[lang] = samples_per_lang.get(lang, 0) + 1
                items_matched += 1

                # Log when a new language is first seen
                if samples_per_lang[lang] == 1:
                    logger.debug("First sample for language: %s", lang)

                # Check if we have enough samples overall
                if all(
                    samples_per_lang.get(lang, 0) >= self.max_samples_per_language
                    for lang in lang_to_scripts
                ):
                    break

            # Save to cache
            for script_code in scripts_to_load:
                if script_code in self.corpora and self.corpora[script_code].samples:
                    self.save_to_cache(script_code)

        except Exception as e:
            logger.error("Failed to load OpenLID-v2: %s", e)
            return total_loaded

        self._loaded = total_loaded > 0
        logger.info("Loaded %d total samples from OpenLID-v2", total_loaded)
        return total_loaded

    def load_from_cache_or_download(
        self,
        script_codes: list[str] | None = None,
        use_sample_fallback: bool = True,
        prefer_gcs: bool = True,
    ) -> int:
        """Load from cache if available, otherwise download.

        Download priority:
        1. Local cache (fastest)
        2. GCS bucket (pre-processed, fast)
        3. HuggingFace OpenLID-v2 (slowest, original source)
        4. Built-in sample texts (fallback)

        Args:
            script_codes: Specific scripts to load
            use_sample_fallback: Use built-in sample texts if download fails
            prefer_gcs: Try GCS before HuggingFace (default: True)

        Returns:
            Number of samples loaded
        """
        # Try cache first
        loaded = self.load_from_cache(script_codes)

        # Check which scripts are missing
        scripts_to_load = script_codes or list(SCRIPT_CONFIGS.keys())
        missing_scripts = [
            s
            for s in scripts_to_load
            if s not in self.corpora or len(self.corpora[s].samples) == 0
        ]

        if missing_scripts:
            # Try GCS first (faster than HuggingFace)
            if prefer_gcs:
                logger.info(
                    "Missing %d scripts, trying GCS download", len(missing_scripts)
                )
                loaded += self.load_from_gcs(missing_scripts)

            # Check if still missing after GCS
            still_missing_after_gcs = [
                s
                for s in missing_scripts
                if s not in self.corpora or len(self.corpora[s].samples) == 0
            ]

            if still_missing_after_gcs:
                logger.info(
                    "Missing %d scripts after GCS, downloading from HuggingFace",
                    len(still_missing_after_gcs),
                )
                loaded += self.load_from_openlid(still_missing_after_gcs)

        # Check again for still-missing scripts and use fallback
        if use_sample_fallback:
            still_missing = [
                s
                for s in scripts_to_load
                if s not in self.corpora or len(self.corpora[s].samples) == 0
            ]
            if still_missing:
                logger.info(
                    "Using built-in sample texts for %d scripts", len(still_missing)
                )
                loaded += self.load_sample_texts(still_missing)

        return loaded

    def get_text(
        self,
        script_code: str,
        density: TextDensity | None = None,
    ) -> str | None:
        """Get random text for a script.

        Args:
            script_code: ISO 15924 script code
            density: Optional text density filter

        Returns:
            Text string or None if not available
        """
        if not self._loaded:
            logger.warning(
                "Corpus not loaded. Call load_from_cache_or_download() first."
            )
            return None

        corpus = self.corpora.get(script_code)

        # Try fallback script if primary not available
        if not corpus and script_code in SCRIPT_FALLBACKS:
            fallback = SCRIPT_FALLBACKS[script_code]
            corpus = self.corpora.get(fallback)
            if corpus:
                logger.debug("Using fallback %s for script %s", fallback, script_code)

        if not corpus:
            logger.warning("No corpus available for script: %s", script_code)
            return None

        # Pass seeded RNG for reproducibility
        sample = corpus.get_sample(density, rng=self._rng)
        return sample.text if sample else None

    def get_text_with_language(
        self,
        script_code: str,
        density: TextDensity | None = None,
    ) -> tuple[str, str] | tuple[None, None]:
        """Get random text with its language code.

        Args:
            script_code: ISO 15924 script code
            density: Optional text density filter

        Returns:
            Tuple of (text, language_code) or (None, None) if not available
        """
        if not self._loaded:
            logger.warning(
                "Corpus not loaded. Call load_from_cache_or_download() first."
            )
            return None, None

        corpus = self.corpora.get(script_code)

        # Try fallback script if primary not available
        if not corpus and script_code in SCRIPT_FALLBACKS:
            fallback = SCRIPT_FALLBACKS[script_code]
            corpus = self.corpora.get(fallback)
            if corpus:
                logger.debug("Using fallback %s for script %s", fallback, script_code)

        if not corpus:
            logger.warning("No corpus available for script: %s", script_code)
            return None, None

        # Pass seeded RNG for reproducibility
        sample = corpus.get_sample(density, rng=self._rng)
        if sample:
            return sample.text, sample.language_code

        return None, None

    def get_available_scripts(self) -> list[str]:
        """Get list of scripts with loaded text samples.

        Returns:
            List of ISO 15924 script codes
        """
        return [code for code, corpus in self.corpora.items() if corpus.samples]

    def get_sample_count(self, script_code: str) -> int:
        """Get number of samples for a script.

        Args:
            script_code: ISO 15924 script code

        Returns:
            Number of samples (0 if not loaded)
        """
        corpus = self.corpora.get(script_code)
        return len(corpus.samples) if corpus else 0

    def get_statistics(self) -> dict[str, Any]:
        """Get corpus statistics.

        Returns:
            Dictionary with corpus statistics
        """
        stats: dict[str, Any] = {
            "total_scripts": len(self.corpora),
            "total_samples": sum(len(c.samples) for c in self.corpora.values()),
            "scripts": {},
        }

        for script_code, corpus in self.corpora.items():
            script_stats = {
                "sample_count": len(corpus.samples),
                "by_density": {
                    density.value: len(samples)
                    for density, samples in corpus.samples_by_density.items()
                },
            }
            stats["scripts"][script_code] = script_stats

        return stats


__all__ = [
    "DENSITY_CHAR_RANGES",
    "GCS_CORPUS_BUCKET",
    "ScriptCorpus",
    "TextCorpusManager",
    "TextSample",
]
