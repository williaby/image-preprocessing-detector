#!/usr/bin/env python3
"""
Extract language-specific text samples from WiLI-2018 dataset.

The WiLI-2018 dataset contains text samples in 235 languages. This script
extracts specific language samples for testing multilingual text detection.
"""

import argparse
import csv
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Target languages for fixtures (10 diverse languages)
TARGET_LANGUAGES = {
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish",
    "zho": "Chinese",
    "ara": "Arabic",
    "rus": "Russian",
    "jpn": "Japanese",
    "kor": "Korean",
    "hin": "Hindi",
}

# WiLI uses 3-letter ISO codes, map common variations
LANGUAGE_CODE_MAP = {
    "eng": "eng",
    "fra": "fra",
    "deu": "deu",
    "spa": "spa",
    "zho": "zho",  # Chinese (macro language)
    "ara": "ara",
    "rus": "rus",
    "jpn": "jpn",
    "kor": "kor",
    "hin": "hin",
}


def load_labels_mapping(labels_file: Path) -> dict[str, str]:
    """Load language code to name mapping from labels.csv."""
    mapping = {}
    with open(labels_file) as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = row["Label"]
            name = row["English"]
            mapping[code] = name
    return mapping


def extract_language_samples(
    x_file: Path,
    y_file: Path,
    output_dir: Path,
    target_langs: dict[str, str],
    max_samples_per_lang: int = 1,
) -> dict[str, any]:
    """
    Extract specific language samples from WiLI dataset.

    Args:
        x_file: Path to x_train.txt or x_test.txt
        y_file: Path to y_train.txt or y_test.txt
        output_dir: Directory to write extracted samples
        target_langs: Dict of language codes to extract
        max_samples_per_lang: Maximum samples per language

    Returns:
        Dict with extraction results
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "extracting_samples",
        x_file=str(x_file),
        y_file=str(y_file),
        target_langs=len(target_langs),
    )

    extracted = {}
    samples_found = dict.fromkeys(target_langs.keys(), 0)

    # Read files line by line (they're large)
    with open(x_file, encoding="utf-8") as xf, open(y_file, encoding="utf-8") as yf:
        for line_num, (text_line, label_line) in enumerate(zip(xf, yf, strict=False), 1):
            label = label_line.strip()

            # Check if this is a target language
            if label in target_langs and samples_found[label] < max_samples_per_lang:
                # Extract sample
                text = text_line.strip()
                lang_name = target_langs[label]

                # Create output file
                output_file = (
                    output_dir / f"{lang_name.lower().replace(' ', '_')}_{label}.txt"
                )

                with open(output_file, "w", encoding="utf-8") as out:
                    out.write(text)

                samples_found[label] += 1
                extracted[label] = {
                    "name": lang_name,
                    "file": output_file.name,
                    "line_num": line_num,
                    "length": len(text),
                }

                logger.info(
                    "extracted_sample",
                    lang=label,
                    name=lang_name,
                    file=output_file.name,
                    length=len(text),
                )

                # Check if we've found all targets
                if all(
                    count >= max_samples_per_lang for count in samples_found.values()
                ):
                    break

    # Report missing languages
    missing = [
        f"{code} ({target_langs[code]})"
        for code, count in samples_found.items()
        if count == 0
    ]
    if missing:
        logger.warning("missing_languages", count=len(missing), langs=missing)

    return {
        "extracted": len(extracted),
        "samples": extracted,
        "missing": missing,
    }


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract language samples from WiLI-2018 dataset"
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "benchmarks" / "wili_2018",
        help="WiLI-2018 dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "test_fixtures" / "wili_2018",
        help="Output directory for fixtures",
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["train", "test"],
        default="test",
        help="Dataset split to use",
    )
    parser.add_argument(
        "--samples-per-lang",
        type=int,
        default=1,
        help="Samples per language",
    )

    args = parser.parse_args()

    # Setup logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )

    # Check dataset exists
    dataset_dir = args.dataset_dir
    if not dataset_dir.exists():
        logger.error("dataset_not_found", path=str(dataset_dir))
        return

    # Load labels mapping
    labels_file = dataset_dir / "labels.csv"
    if labels_file.exists():
        labels_map = load_labels_mapping(labels_file)
        logger.info("loaded_labels", count=len(labels_map))
    else:
        logger.warning("labels_file_not_found")
        labels_map = {}

    # Extract samples
    x_file = dataset_dir / f"x_{args.split}.txt"
    y_file = dataset_dir / f"y_{args.split}.txt"

    if not x_file.exists() or not y_file.exists():
        logger.error(
            "dataset_files_not_found",
            x_file=str(x_file),
            y_file=str(y_file),
        )
        return

    result = extract_language_samples(
        x_file,
        y_file,
        args.output_dir,
        LANGUAGE_CODE_MAP,
        args.samples_per_lang,
    )

    print(f"\nExtracted {result['extracted']} language samples")
    if result["missing"]:
        print(f"Warning: {len(result['missing'])} languages not found")
        for lang in result["missing"]:
            print(f"  - {lang}")


if __name__ == "__main__":
    main()
