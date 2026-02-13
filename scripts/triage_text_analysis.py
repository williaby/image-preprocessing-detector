#!/usr/bin/env python3
"""Fast text-based language triage (no OCR needed).

Uses pre-extracted text from annotation files for rapid language detection.
~50-100x faster than OCR-based analysis.

Supported datasets with pre-extracted text:
- fintabnet: FinTabNet.c-Structure/words/*.json
- pubtabnet: (check for similar structure)
- tablebank: (check for similar structure)

Usage:
    # Fast analysis using pre-extracted text
    PYTHONPATH=. uv run python scripts/triage_text_analysis.py --dataset fintabnet --all

    # Sample analysis
    PYTHONPATH=. uv run python scripts/triage_text_analysis.py --dataset fintabnet --sample 1000
"""

import argparse
import json
import logging
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, UTC
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

# Dataset configurations for pre-extracted text
DATASET_TEXT_SOURCES = {
    "fintabnet": {
        "base_path": BASE_DATA_PATH / "tables/fintabnet",
        "words_dir": "FinTabNet.c-Structure/words",
        "text_key": "text",
        "file_pattern": lambda img_path: img_path.stem + "_words.json",
        "text_extractor": None,  # Uses default words.json extraction
    },
    "pubtabnet": {
        "base_path": BASE_DATA_PATH / "tables/pubtabnet/pubtabnet",
        "jsonl_path": "PubTabNet_2.0.0.jsonl",
        "text_extractor": "jsonl_cells",  # Special extractor for JSONL cells/tokens
    },
}

# Global JSONL index for pubtabnet (lazy loaded)
_PUBTABNET_TEXT_INDEX: dict[str, str] | None = None

# Confidence thresholds
CONFIDENCE_BINS = [
    (0.9, 1.0, "very_high"),
    (0.7, 0.9, "high"),
    (0.5, 0.7, "medium"),
    (0.3, 0.5, "low"),
    (0.0, 0.3, "very_low"),
]


@dataclass
class TextAnalysisResult:
    """Result from text-based analysis."""

    sample_id: str
    text_length: int

    # Script detection
    detected_scripts: list[str]
    primary_script: str | None
    script_counts: dict[str, int]

    # Language detection
    fasttext_lang: str | None
    fasttext_confidence: float
    lingua_lang: str | None
    lingua_confidence: float

    # Consensus
    consensus_language: str
    consensus_confidence: float
    detector_agreement: bool
    needs_escalation: bool
    escalation_reason: str | None


def load_models():
    """Load fastText and lingua models."""
    models = {}

    # Load fastText
    try:
        import fasttext

        model_path = Path(
            "/mnt/e/image_detection/models/language_detection/lid.176.bin"
        )
        if model_path.exists():
            fasttext.FastText.eprint = lambda x: None
            models["fasttext"] = fasttext.load_model(str(model_path))
            logger.info("Loaded fastText model")
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


def extract_text_from_words_json(words_file: Path) -> str:
    """Extract text from a words JSON file."""
    if not words_file.exists():
        return ""

    try:
        with open(words_file) as f:
            words_data = json.load(f)

        texts = [w.get("text", "") for w in words_data if w.get("text")]
        return " ".join(texts)
    except Exception as e:
        logger.debug(f"Error reading {words_file}: {e}")
        return ""


def _extract_tokens(tokens: list[str]) -> str:
    """Join non-HTML tokens from a cell's token list."""
    return "".join(t for t in tokens if not (t.startswith("<") and t.endswith(">")))


def _parse_pubtabnet_record(line: str) -> tuple[str, str] | None:
    """Parse a single JSONL record and return (filename, text) or None."""
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None

    filename = record.get("filename", "")
    cells = record.get("html", {}).get("cells", [])
    texts = [_extract_tokens(c.get("tokens", [])) for c in cells]
    text = " ".join(t for t in texts if t.strip())

    if filename and text:
        return filename, text
    return None


def load_pubtabnet_index(jsonl_path: Path) -> dict[str, str]:
    """Load pubtabnet text index from JSONL (cached globally)."""
    global _PUBTABNET_TEXT_INDEX

    if _PUBTABNET_TEXT_INDEX is not None:
        return _PUBTABNET_TEXT_INDEX

    logger.info(f"Loading pubtabnet text index from {jsonl_path}...")
    _PUBTABNET_TEXT_INDEX = {}

    with open(jsonl_path) as f:
        for i, line in enumerate(f):
            if (i + 1) % 100000 == 0:
                logger.info(f"  Loaded {i + 1} records...")
            result = _parse_pubtabnet_record(line)
            if result is not None:
                _PUBTABNET_TEXT_INDEX[result[0]] = result[1]

    logger.info(f"Loaded {len(_PUBTABNET_TEXT_INDEX)} pubtabnet text entries")
    return _PUBTABNET_TEXT_INDEX


def extract_text_for_pubtabnet(sample: dict, dataset_config: dict) -> str:
    """Extract text for a pubtabnet sample using pre-loaded index."""
    rel_path = sample.get("source", {}).get("original_path", "")
    filename = Path(rel_path).name

    jsonl_path = dataset_config["base_path"] / dataset_config["jsonl_path"]
    index = load_pubtabnet_index(jsonl_path)
    return index.get(filename, "")


def detect_scripts(text: str) -> tuple[list[str], dict[str, int]]:
    """Detect scripts using Unicode analysis."""
    import unicodedata

    CHAR_TO_SCRIPT = {
        "LATIN": "Latn",
        "GREEK": "Grek",
        "CYRILLIC": "Cyrl",
        "ARABIC": "Arab",
        "HEBREW": "Hebr",
        "DEVANAGARI": "Deva",
        "BENGALI": "Beng",
        "TAMIL": "Taml",
        "TELUGU": "Telu",
        "THAI": "Thai",
        "HANGUL": "Hang",
        "HIRAGANA": "Hira",
        "KATAKANA": "Kana",
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

    scripts = [s for s, _ in script_counts.most_common()]
    return scripts, dict(script_counts)


def detect_fasttext(text: str, model) -> tuple[str | None, float]:
    """Detect language using fastText."""
    if model is None or not text.strip():
        return None, 0.0

    try:
        clean = " ".join(text.split())[:2000]
        preds = model.predict(clean, k=1)
        return preds[0][0].replace("__label__", ""), float(preds[1][0])
    except Exception:
        return None, 0.0


def detect_lingua(text: str, detector) -> tuple[str | None, float]:
    """Detect language using lingua."""
    if detector is None or not text.strip():
        return None, 0.0

    try:
        result = detector.detect_language_of(text)
        if result:
            lang = result.iso_code_639_1.name.lower()
            confs = detector.compute_language_confidence_values(text)
            conf = confs[0].value if confs else 0.5
            return lang, conf
        return None, 0.0
    except Exception:
        return None, 0.0


_SCRIPT_TO_LANG: dict[str, str] = {
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
    "Thai": "th",
    "Taml": "ta",
}

_AMBIGUOUS_SCRIPTS = {"Latn", "Cyrl", "Arab"}


def _determine_escalation_reason(
    best_conf: float, agreement: bool
) -> tuple[bool, str | None]:
    """Determine if escalation is needed and the reason."""
    if best_conf < 0.6:
        return True, "low_confidence"
    if not agreement:
        return True, "disagreement"
    return False, None


def compute_consensus(
    scripts: list[str],
    ft_lang: str | None,
    ft_conf: float,
    lingua_lang: str | None,
    lingua_conf: float,
) -> tuple[str, float, bool, bool, str | None]:
    """Compute consensus language."""
    primary_script = scripts[0] if scripts else None

    # Non-ambiguous script = high confidence
    if primary_script and primary_script not in _AMBIGUOUS_SCRIPTS:
        return _SCRIPT_TO_LANG.get(primary_script, "und"), 0.9, True, False, None

    # No text at all
    if not scripts and not ft_lang and not lingua_lang:
        return "und", 0.0, False, True, "no_text"

    # Check detector agreement
    agreement = ft_lang == lingua_lang if (ft_lang and lingua_lang) else False

    if agreement and ft_conf > 0.5 and lingua_conf > 0.5:
        return ft_lang, (ft_conf + lingua_conf) / 2, True, False, None

    if ft_conf > 0.8:
        return ft_lang, ft_conf * 0.9, False, False, None

    if lingua_conf > 0.8:
        return lingua_lang, lingua_conf * 0.9, False, False, None

    best_lang = ft_lang or lingua_lang or "und"
    best_conf = max(ft_conf, lingua_conf)
    needs_esc, reason = _determine_escalation_reason(best_conf, agreement)
    return best_lang, best_conf, agreement, needs_esc, reason


def analyze_sample(
    sample: dict,
    dataset_config: dict,
    models: dict,
) -> TextAnalysisResult | None:
    """Analyze a single sample using pre-extracted text."""

    # Extract text based on extractor type
    extractor_type = dataset_config.get("text_extractor")

    if extractor_type == "jsonl_cells":
        # Pubtabnet: extract from pre-loaded JSONL index
        text = extract_text_for_pubtabnet(sample, dataset_config)
    else:
        # Default: extract from words.json files (fintabnet)
        rel_path = sample.get("source", {}).get("original_path", "")
        img_path = Path(rel_path)
        words_dir = dataset_config["base_path"] / dataset_config["words_dir"]
        words_file = words_dir / dataset_config["file_pattern"](img_path)
        text = extract_text_from_words_json(words_file)

    if not text:
        return TextAnalysisResult(
            sample_id=sample.get("id", ""),
            text_length=0,
            detected_scripts=[],
            primary_script=None,
            script_counts={},
            fasttext_lang=None,
            fasttext_confidence=0.0,
            lingua_lang=None,
            lingua_confidence=0.0,
            consensus_language="und",
            consensus_confidence=0.0,
            detector_agreement=False,
            needs_escalation=True,
            escalation_reason="no_text",
        )

    # Detect scripts
    scripts, script_counts = detect_scripts(text)

    # Detect languages
    ft_lang, ft_conf = detect_fasttext(text, models.get("fasttext"))
    lingua_lang, lingua_conf = detect_lingua(text, models.get("lingua"))

    # Consensus
    cons_lang, cons_conf, agreement, needs_esc, reason = compute_consensus(
        scripts, ft_lang, ft_conf, lingua_lang, lingua_conf
    )

    return TextAnalysisResult(
        sample_id=sample.get("id", ""),
        text_length=len(text),
        detected_scripts=scripts,
        primary_script=scripts[0] if scripts else None,
        script_counts=script_counts,
        fasttext_lang=ft_lang,
        fasttext_confidence=ft_conf,
        lingua_lang=lingua_lang,
        lingua_confidence=lingua_conf,
        consensus_language=cons_lang,
        consensus_confidence=cons_conf,
        detector_agreement=agreement,
        needs_escalation=needs_esc,
        escalation_reason=reason,
    )


def _counter_markdown_table(
    title: str,
    header: str,
    counts: Counter,
    total: int,
    top_n: int | None = None,
) -> list[str]:
    """Build a markdown table section from a Counter."""
    lines = [
        f"## {title}",
        "",
        f"| {header} | Count | % |",
        f"|{'---' * len(header)}|-------|---|",
    ]
    items = counts.most_common(top_n) if top_n else counts.most_common()
    for name, count in items:
        lines.append(f"| {name} | {count} | {100 * count / total:.1f}% |")
    lines.append("")
    return lines


def _confidence_stratification_table(
    results: list[TextAnalysisResult],
) -> list[str]:
    """Build confidence stratification markdown table."""
    lines = [
        "## Confidence Stratification",
        "",
        "| Confidence | Count | % | Needs Escalation |",
        "|------------|-------|---|------------------|",
    ]
    total = len(results)
    for low, high, label in CONFIDENCE_BINS:
        in_bin = [r for r in results if low <= r.consensus_confidence < high]
        count = len(in_bin)
        pct = 100 * count / total if total else 0
        esc = sum(1 for r in in_bin if r.needs_escalation)
        esc_pct = 100 * esc / count if count else 0
        lines.append(
            f"| {label} ({low:.1f}-{high:.1f}) | {count} | {pct:.1f}% | {esc} ({esc_pct:.0f}%) |"
        )
    lines.append("")
    return lines


def generate_report(results: list[TextAnalysisResult], dataset: str) -> str:
    """Generate stratified report."""
    total = len(results)
    needs_esc = sum(1 for r in results if r.needs_escalation)
    no_esc = total - needs_esc

    lines = [
        f"# Language Triage Report: {dataset}",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Total samples: {total}",
        "Method: Pre-extracted text (no OCR)",
        "",
        "## Executive Summary",
        "",
        f"- **Can label locally**: {no_esc} ({100 * no_esc / total:.1f}%)",
        f"- **Needs vision API**: {needs_esc} ({100 * needs_esc / total:.1f}%)",
        "",
    ]

    script_counts = Counter(r.primary_script or "None" for r in results)
    lines.extend(
        _counter_markdown_table("Script Distribution", "Script", script_counts, total)
    )

    lang_counts = Counter(r.consensus_language for r in results)
    lines.extend(
        _counter_markdown_table(
            "Language Distribution", "Language", lang_counts, total, top_n=15
        )
    )

    lines.extend(_confidence_stratification_table(results))

    # Detector agreement
    agree = sum(1 for r in results if r.detector_agreement)
    lines.extend(
        [
            "## Detector Agreement",
            "",
            f"- **Agree**: {agree} ({100 * agree / total:.1f}%)",
            f"- **Disagree**: {total - agree} ({100 * (total - agree) / total:.1f}%)",
            "",
            "## Cost Estimate",
            "",
            f"- Samples needing vision: {needs_esc}",
            f"- @ $0.0003/sample (Qwen): ${needs_esc * 0.0003:.2f}",
            f"- @ $0.01/sample (Gemini Pro): ${needs_esc * 0.01:.2f}",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fast text-based language triage")
    parser.add_argument("--dataset", required=True, help="Dataset name")
    parser.add_argument("--sample", type=int, help="Sample N records")
    parser.add_argument("--all", action="store_true", help="Process all records")
    args = parser.parse_args()

    if args.dataset not in DATASET_TEXT_SOURCES:
        logger.error(f"Dataset {args.dataset} not configured for text extraction")
        logger.info(f"Configured: {list(DATASET_TEXT_SOURCES.keys())}")
        return 1

    config = DATASET_TEXT_SOURCES[args.dataset]

    # Load metadata
    metadata_file = METADATA_REGISTRY / f"{args.dataset}_metadata.json"
    with open(metadata_file) as f:
        data = json.load(f)

    samples = data.get("samples", [])
    logger.info(f"Loaded {len(samples)} samples")

    # Sample if needed
    if not args.all and args.sample:
        import random

        samples = random.sample(samples, min(args.sample, len(samples)))
        logger.info(f"Sampled {len(samples)} records")
    elif not args.all:
        samples = samples[:1000]
        logger.info("Using first 1000 records (use --all for full)")

    # Load models
    models = load_models()

    # Process
    results = []
    start = time.time()

    for i, sample in enumerate(samples):
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(samples) - i - 1) / rate
            logger.info(
                f"Progress: {i + 1}/{len(samples)} ({rate:.0f}/sec, ETA: {eta:.0f}s)"
            )

        result = analyze_sample(sample, config, models)
        if result:
            results.append(result)

    elapsed = time.time() - start
    logger.info(
        f"Processed {len(results)} in {elapsed:.1f}s ({len(results) / elapsed:.0f}/sec)"
    )

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = RESULTS_DIR / f"{args.dataset}_text_triage.json"
    report_file = RESULTS_DIR / f"{args.dataset}_text_triage_report.md"

    results_data = [
        {
            "sample_id": r.sample_id,
            "text_length": r.text_length,
            "detected_scripts": r.detected_scripts,
            "primary_script": r.primary_script,
            "fasttext_lang": r.fasttext_lang,
            "fasttext_confidence": r.fasttext_confidence,
            "lingua_lang": r.lingua_lang,
            "lingua_confidence": r.lingua_confidence,
            "consensus_language": r.consensus_language,
            "consensus_confidence": r.consensus_confidence,
            "detector_agreement": r.detector_agreement,
            "needs_escalation": r.needs_escalation,
            "escalation_reason": r.escalation_reason,
        }
        for r in results
    ]

    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)

    report = generate_report(results, args.dataset)
    with open(report_file, "w") as f:
        f.write(report)

    print("\n" + report)
    logger.info(f"Results: {results_file}")
    logger.info(f"Report: {report_file}")

    return 0


if __name__ == "__main__":
    exit(main())
