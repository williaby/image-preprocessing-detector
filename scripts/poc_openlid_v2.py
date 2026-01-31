#!/usr/bin/env python3
"""Proof-of-Concept: OpenLID-v2 Language Detection Model.

Tests OpenLID-v2 compatibility with the project's numpy 2.x environment
and compares results with the current lid.176.bin model.

OpenLID-v2: https://huggingface.co/laurievb/OpenLID-v2
- 200 language varieties
- ISO 639-3 + ISO 15924 labels (e.g., eng_Latn, arb_Arab)
- 0.93 macro-average F1 score

Usage:
    # Run full PoC (downloads model if needed)
    uv run python scripts/poc_openlid_v2.py

    # Skip comparison with lid.176.bin
    uv run python scripts/poc_openlid_v2.py --skip-comparison

    # Test with custom text
    uv run python scripts/poc_openlid_v2.py --text "Your text here"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Monkey-patch fasttext for numpy 2.x compatibility
# fasttext uses deprecated `np.array(x, copy=False)` which fails in numpy 2.x
# See: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
_original_array = np.array


def _patched_array(*args, **kwargs):
    """Wrapper that converts copy=False to np.asarray behavior."""
    if kwargs.get("copy") is False:
        kwargs.pop("copy")
        return np.asarray(*args, **kwargs)
    return _original_array(*args, **kwargs)


np.array = _patched_array

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Model paths
MODEL_DIR = Path("/mnt/e/image_detection/models/language_detection")
OPENLID_MODEL_PATH = MODEL_DIR / "openlid_v2.bin"
LID176_MODEL_PATH = MODEL_DIR / "lid.176.bin"

# ISO 639-3 to ISO 639-1 mapping (common languages)
ISO639_3_TO_1: dict[str, str] = {
    "eng": "en", "spa": "es", "fra": "fr", "deu": "de", "ita": "it",
    "por": "pt", "nld": "nl", "pol": "pl", "rus": "ru", "ukr": "uk",
    "ces": "cs", "ron": "ro", "ell": "el", "hun": "hu", "swe": "sv",
    "dan": "da", "nor": "no", "fin": "fi", "zho": "zh", "cmn": "zh",
    "jpn": "ja", "kor": "ko", "vie": "vi", "tha": "th", "ind": "id",
    "msa": "ms", "hin": "hi", "ben": "bn", "pan": "pa", "tam": "ta",
    "tel": "te", "mar": "mr", "guj": "gu", "kan": "kn", "mal": "ml",
    "nep": "ne", "sin": "si", "urd": "ur", "arb": "ar", "arz": "ar",
    "fas": "fa", "heb": "he", "tur": "tr", "amh": "am", "swa": "sw",
    "tgl": "tl", "khm": "km", "lao": "lo", "mya": "my", "bod": "bo",
    "dzo": "dz", "bul": "bg", "srp": "sr", "mkd": "mk", "slv": "sl",
    "hrv": "hr", "bos": "bs", "slk": "sk", "lit": "lt", "lav": "lv",
    "est": "et", "kat": "ka", "hye": "hy", "aze": "az", "uzb": "uz",
    "kaz": "kk", "tgk": "tg", "mon": "mn", "bel": "be",
}

# Test samples covering different scripts and languages
TEST_SAMPLES: list[tuple[str, str, str]] = [
    # (text, expected_lang_639_1, expected_script)
    ("The quick brown fox jumps over the lazy dog.", "en", "Latn"),
    ("Le renard brun rapide saute par-dessus le chien paresseux.", "fr", "Latn"),
    ("Der schnelle braune Fuchs springt über den faulen Hund.", "de", "Latn"),
    ("El rápido zorro marrón salta sobre el perro perezoso.", "es", "Latn"),
    ("Быстрая коричневая лиса прыгает через ленивую собаку.", "ru", "Cyrl"),
    ("Швидка руда лисиця перестрибує через ледачого пса.", "uk", "Cyrl"),
    ("这是一段中文测试文本，用于测试语言检测功能。", "zh", "Hans"),
    ("這是一段繁體中文測試文本，用於測試語言檢測功能。", "zh", "Hant"),
    ("これは日本語のテスト文です。言語検出機能をテストします。", "ja", "Jpan"),
    ("이것은 한국어 테스트 문장입니다. 언어 감지 기능을 테스트합니다.", "ko", "Kore"),
    ("यह हिंदी में एक परीक्षण वाक्य है। भाषा पहचान का परीक्षण।", "hi", "Deva"),
    ("এটি বাংলায় একটি পরীক্ষামূলক বাক্য। ভাষা সনাক্তকরণ পরীক্ষা।", "bn", "Beng"),
    ("இது தமிழில் ஒரு சோதனை வாக்கியம். மொழி கண்டறிதல் சோதனை.", "ta", "Taml"),
    ("هذه جملة اختبار باللغة العربية. اختبار اكتشاف اللغة.", "ar", "Arab"),
    ("این یک جمله آزمایشی به زبان فارسی است. تست تشخیص زبان.", "fa", "Arab"),
    ("זוהי משפט בדיקה בעברית. בדיקת זיהוי שפה.", "he", "Hebr"),
    ("นี่คือประโยคทดสอบภาษาไทย ทดสอบการตรวจจับภาษา", "th", "Thai"),
    ("Đây là câu thử nghiệm tiếng Việt. Kiểm tra phát hiện ngôn ngữ.", "vi", "Latn"),
    ("བོད་སྐད་ཀྱི་ཚོད་ལྟའི་ཚིག་གྲུབ་འདི་ཡིན།", "bo", "Tibt"),
    ("Αυτή είναι μια δοκιμαστική πρόταση στα ελληνικά.", "el", "Grek"),
]


@dataclass
class DetectionResult:
    """Result from a language detection model."""

    lang_code: str  # ISO 639-1 or 639-3
    script_code: str | None  # ISO 15924
    confidence: float
    raw_label: str
    model_name: str
    latency_ms: float


def download_openlid_model() -> Path:
    """Download OpenLID-v2 model from HuggingFace."""
    if OPENLID_MODEL_PATH.exists():
        logger.info(f"OpenLID-v2 model already exists: {OPENLID_MODEL_PATH}")
        return OPENLID_MODEL_PATH

    logger.info("Downloading OpenLID-v2 model from HuggingFace...")

    try:
        from huggingface_hub import hf_hub_download

        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        downloaded_path = hf_hub_download(
            repo_id="laurievb/OpenLID-v2",
            filename="model.bin",
            local_dir=MODEL_DIR,
            local_dir_use_symlinks=False,
        )

        # Rename to our expected name
        Path(downloaded_path).rename(OPENLID_MODEL_PATH)
        logger.info(f"Model saved to: {OPENLID_MODEL_PATH}")
        return OPENLID_MODEL_PATH

    except ImportError:
        logger.error("huggingface_hub not installed. Run: uv add huggingface_hub")
        raise


def load_fasttext_model(model_path: Path) -> Any:
    """Load a fastText model."""
    import fasttext

    logger.info(f"Loading model: {model_path.name}")
    start = time.perf_counter()
    model = fasttext.load_model(str(model_path))
    load_time = (time.perf_counter() - start) * 1000
    logger.info(f"Model loaded in {load_time:.0f}ms")
    return model


def clean_text_openlid(text: str) -> str:
    """Clean text for OpenLID-v2 (simplified version of openlid_normer).

    The full openlid_normer package may have additional dependencies.
    This is a simplified version that handles the basics.
    """
    # Replace newlines and tabs with spaces
    text = text.replace("\n", " ").replace("\t", " ")
    # Collapse multiple spaces
    text = " ".join(text.split())
    return text.strip()


def detect_openlid(text: str, model: Any) -> DetectionResult:
    """Detect language using OpenLID-v2 model."""
    clean_text = clean_text_openlid(text)

    start = time.perf_counter()
    predictions = model.predict(clean_text, k=1)
    latency = (time.perf_counter() - start) * 1000

    raw_label = predictions[0][0]  # '__label__eng_Latn'
    confidence = float(predictions[1][0])

    # Parse OpenLID format: __label__<lang>_<script>
    label_parts = raw_label.replace("__label__", "").split("_")
    lang_639_3 = label_parts[0]
    script_code = label_parts[1] if len(label_parts) > 1 else None

    # Convert to ISO 639-1 if possible
    lang_639_1 = ISO639_3_TO_1.get(lang_639_3, lang_639_3)

    return DetectionResult(
        lang_code=lang_639_1,
        script_code=script_code,
        confidence=confidence,
        raw_label=raw_label,
        model_name="OpenLID-v2",
        latency_ms=latency,
    )


def detect_lid176(text: str, model: Any) -> DetectionResult:
    """Detect language using lid.176.bin model."""
    clean_text = " ".join(text.split())

    start = time.perf_counter()
    predictions = model.predict(clean_text, k=1)
    latency = (time.perf_counter() - start) * 1000

    raw_label = predictions[0][0]  # '__label__en'
    confidence = float(predictions[1][0])

    # Parse lid.176 format: __label__<lang>
    lang_code = raw_label.replace("__label__", "")

    return DetectionResult(
        lang_code=lang_code,
        script_code=None,  # lid.176 doesn't provide script
        confidence=confidence,
        raw_label=raw_label,
        model_name="lid.176.bin",
        latency_ms=latency,
    )


def get_top_k_predictions(text: str, model: Any, k: int = 5, is_openlid: bool = True) -> list[tuple[str, float]]:
    """Get top-k predictions from a model."""
    clean_text = clean_text_openlid(text) if is_openlid else " ".join(text.split())
    predictions = model.predict(clean_text, k=k)

    results = []
    for label, conf in zip(predictions[0], predictions[1]):
        lang = label.replace("__label__", "")
        results.append((lang, float(conf)))

    return results


def run_comparison(
    openlid_model: Any,
    lid176_model: Any | None,
    samples: list[tuple[str, str, str]],
) -> dict[str, Any]:
    """Run comparison between models on test samples."""
    results = {
        "openlid": {"correct": 0, "total": 0, "latencies": []},
        "lid176": {"correct": 0, "total": 0, "latencies": []},
    }

    print("\n" + "=" * 90)
    print(f"{'Text (truncated)':<35} {'Expected':<10} {'OpenLID-v2':<20} {'lid.176':<15}")
    print("=" * 90)

    for text, expected_lang, expected_script in samples:
        truncated = text[:32] + "..." if len(text) > 35 else text

        # OpenLID-v2
        openlid_result = detect_openlid(text, openlid_model)
        results["openlid"]["total"] += 1
        results["openlid"]["latencies"].append(openlid_result.latency_ms)

        openlid_correct = openlid_result.lang_code == expected_lang
        if openlid_correct:
            results["openlid"]["correct"] += 1

        openlid_str = f"{openlid_result.lang_code}_{openlid_result.script_code} ({openlid_result.confidence:.2f})"
        openlid_mark = "✓" if openlid_correct else "✗"

        # lid.176.bin (if available)
        lid176_str = "N/A"
        lid176_mark = ""
        if lid176_model:
            lid176_result = detect_lid176(text, lid176_model)
            results["lid176"]["total"] += 1
            results["lid176"]["latencies"].append(lid176_result.latency_ms)

            lid176_correct = lid176_result.lang_code == expected_lang
            if lid176_correct:
                results["lid176"]["correct"] += 1

            lid176_str = f"{lid176_result.lang_code} ({lid176_result.confidence:.2f})"
            lid176_mark = "✓" if lid176_correct else "✗"

        print(
            f"{truncated:<35} {expected_lang}-{expected_script:<7} "
            f"{openlid_mark} {openlid_str:<17} {lid176_mark} {lid176_str:<12}"
        )

    return results


def print_summary(results: dict[str, Any]) -> None:
    """Print comparison summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # OpenLID-v2
    openlid = results["openlid"]
    if openlid["total"] > 0:
        accuracy = openlid["correct"] / openlid["total"] * 100
        avg_latency = sum(openlid["latencies"]) / len(openlid["latencies"])
        print(f"\nOpenLID-v2:")
        print(f"  Accuracy: {openlid['correct']}/{openlid['total']} ({accuracy:.1f}%)")
        print(f"  Avg latency: {avg_latency:.2f}ms")

    # lid.176.bin
    lid176 = results["lid176"]
    if lid176["total"] > 0:
        accuracy = lid176["correct"] / lid176["total"] * 100
        avg_latency = sum(lid176["latencies"]) / len(lid176["latencies"])
        print(f"\nlid.176.bin:")
        print(f"  Accuracy: {lid176['correct']}/{lid176['total']} ({accuracy:.1f}%)")
        print(f"  Avg latency: {avg_latency:.2f}ms")


def check_environment() -> None:
    """Check and display environment info."""
    print("=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)

    # Python version
    print(f"Python: {sys.version.split()[0]}")

    # NumPy version
    print(f"NumPy: {np.__version__}")

    # fastText version
    try:
        import fasttext

        print(f"fastText: {fasttext.__version__ if hasattr(fasttext, '__version__') else 'installed'}")
    except ImportError:
        print("fastText: NOT INSTALLED")
        print("  Install with: uv add fasttext")
        sys.exit(1)

    # huggingface_hub
    try:
        import huggingface_hub

        print(f"huggingface_hub: {huggingface_hub.__version__}")
    except ImportError:
        print("huggingface_hub: NOT INSTALLED (needed for download)")

    print()


def test_single_text(text: str, openlid_model: Any) -> None:
    """Test a single text input."""
    print("\n" + "=" * 60)
    print("SINGLE TEXT TEST")
    print("=" * 60)
    print(f"Input: {text[:100]}{'...' if len(text) > 100 else ''}")

    result = detect_openlid(text, openlid_model)
    print(f"\nResult:")
    print(f"  Language: {result.lang_code} (raw: {result.raw_label.replace('__label__', '')})")
    print(f"  Script: {result.script_code}")
    print(f"  Confidence: {result.confidence:.4f}")
    print(f"  Latency: {result.latency_ms:.2f}ms")

    # Show top 5
    print(f"\nTop 5 predictions:")
    top_k = get_top_k_predictions(text, openlid_model, k=5)
    for i, (lang, conf) in enumerate(top_k, 1):
        print(f"  {i}. {lang}: {conf:.4f}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenLID-v2 Proof-of-Concept")
    parser.add_argument("--skip-comparison", action="store_true", help="Skip comparison with lid.176.bin")
    parser.add_argument("--text", type=str, help="Test with custom text")
    parser.add_argument("--download-only", action="store_true", help="Only download the model")
    args = parser.parse_args()

    # Environment check
    check_environment()

    # Download model if needed
    try:
        model_path = download_openlid_model()
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return 1

    if args.download_only:
        logger.info("Download complete. Exiting.")
        return 0

    # Load OpenLID-v2
    try:
        openlid_model = load_fasttext_model(model_path)
        logger.info("✓ OpenLID-v2 loaded successfully with numpy 2.x!")
    except Exception as e:
        logger.error(f"Failed to load OpenLID-v2: {e}")
        logger.error("This may indicate numpy 2.x incompatibility")
        return 1

    # Test single text if provided
    if args.text:
        test_single_text(args.text, openlid_model)
        return 0

    # Load lid.176.bin for comparison (if available and not skipped)
    lid176_model = None
    if not args.skip_comparison and LID176_MODEL_PATH.exists():
        try:
            lid176_model = load_fasttext_model(LID176_MODEL_PATH)
        except Exception as e:
            logger.warning(f"Could not load lid.176.bin: {e}")

    # Run comparison
    results = run_comparison(openlid_model, lid176_model, TEST_SAMPLES)

    # Print summary
    print_summary(results)

    # Key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    print(f"✓ NumPy {np.__version__} compatibility: WORKING")
    print(f"✓ OpenLID-v2 provides language+script in single prediction")
    print(f"✓ Label format: __label__<iso639-3>_<iso15924>")

    if lid176_model:
        openlid_acc = results["openlid"]["correct"] / results["openlid"]["total"] * 100
        lid176_acc = results["lid176"]["correct"] / results["lid176"]["total"] * 100
        if openlid_acc >= lid176_acc:
            print(f"✓ OpenLID-v2 accuracy >= lid.176.bin ({openlid_acc:.0f}% vs {lid176_acc:.0f}%)")
        else:
            print(f"⚠ OpenLID-v2 accuracy < lid.176.bin ({openlid_acc:.0f}% vs {lid176_acc:.0f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
