#!/usr/bin/env python3

"""
Download Multilingual Script Datasets for Phase 10A.

Downloads multiple script/language datasets for orientation and script detection:

1. JSSODa (Japanese Simple Synthetic OCR Dataset) - HuggingFace llm-jp/JSSODa
   - Japanese vertical AND horizontal text
   - Critical for orientation training (vertical = 0°, not 270°)

2. Arabic OCR datasets - HuggingFace mssqpi/Arabic-OCR-Dataset
   - Arabic (RTL) document images

3. Process-Venue Multilingual OCR - HuggingFace Process-Venue/multilingual-ocr-dataset
   - Multiple languages/scripts

4. Dzongkha Digits - HuggingFace proadhikary/dzongkha-digits
   - Tibetan-derived script (Dzongkha handwritten digits)
   - Useful for tibetan script class in 10-class detection

These datasets support:
- Orientation detection: Japanese vertical text labeled as 0° (not 270°)
- Script detection: 10-class classification (latin, cjk_mixed, japanese, korean,
  tibetan, arabic, devanagari, cyrillic, thai, hebrew)

Output: /mnt/e/image_detection/01_base_data/language/multilingual_scripts/

Usage:
    uv run python scripts/download_japanese_vertical_datasets.py
    uv run python scripts/download_japanese_vertical_datasets.py --output /custom/path
    uv run python scripts/download_japanese_vertical_datasets.py --datasets jssoda,arabic
"""

import argparse
import json
import sys
from pathlib import Path

from tqdm import tqdm

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from datasets import load_dataset
    from PIL import Image
except ImportError:
    print("Error: Required libraries not installed.")
    print("Run: uv sync --extra ml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants (S1192: avoid duplicated literals)
# ---------------------------------------------------------------------------
_PROCESSING_DESC = "  Processing"
_MANIFEST_FILENAME = "manifest.json"


def download_jssoda(output_dir: Path, max_samples: int = 2000) -> int:
    """Download JSSODa dataset from HuggingFace.

    JSSODa (Japanese Simple Synthetic OCR Dataset):
    - Synthetically generated Japanese text images
    - Both vertical and horizontal layouts
    - 1-4 column configurations

    Args:
        output_dir: Directory to save images
        max_samples: Maximum samples to download (per split)

    Returns:
        Number of images downloaded
    """
    print("\n=== Downloading JSSODa from HuggingFace ===\n")

    # Create output directories
    jssoda_dir = output_dir / "jssoda"
    jssoda_dir.mkdir(parents=True, exist_ok=True)
    (jssoda_dir / "vertical").mkdir(exist_ok=True)
    (jssoda_dir / "horizontal").mkdir(exist_ok=True)

    total_downloaded = 0
    manifest = {"vertical": [], "horizontal": []}

    try:
        # Load training split
        print("  Loading llm-jp/JSSODa training split...")
        dataset = load_dataset("llm-jp/JSSODa", split="train")

        # Process samples
        vertical_count = 0
        horizontal_count = 0

        for idx, sample in enumerate(tqdm(dataset, desc=_PROCESSING_DESC)):
            if idx >= max_samples:
                break

            # Extract image and metadata
            image = sample.get("image")
            # JSSODa uses 'is_vertical' boolean field
            is_vertical = sample.get("is_vertical", False)
            num_columns = sample.get("num_columns", 1)

            if image is None:
                continue

            # Determine orientation category based on is_vertical field
            if is_vertical:
                orientation = "vertical"
                count = vertical_count
                vertical_count += 1
            else:
                orientation = "horizontal"
                count = horizontal_count
                horizontal_count += 1

            # Save image
            filename = f"jssoda_{orientation}_{count:05d}.png"
            filepath = jssoda_dir / orientation / filename

            if isinstance(image, Image.Image):
                image.save(filepath)
            else:
                # Handle bytes or other formats
                with open(filepath, "wb") as f:
                    f.write(image)

            # Record in manifest
            manifest[orientation].append(
                {
                    "filename": filename,
                    "path": str(filepath.relative_to(output_dir)),
                    "is_vertical": is_vertical,
                    "num_columns": num_columns,
                    "source": "llm-jp/JSSODa",
                    "split": "train",
                    "index": idx,
                }
            )

            total_downloaded += 1

        # Save manifest
        manifest_path = jssoda_dir / _MANIFEST_FILENAME
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n  Downloaded: {total_downloaded} images")
        print(f"    Vertical: {len(manifest['vertical'])}")
        print(f"    Horizontal: {len(manifest['horizontal'])}")
        print(f"  Manifest: {manifest_path}")

    except Exception as e:
        print(f"  ERROR: Failed to download JSSODa: {e}")
        return 0

    return total_downloaded


def download_jssoda_test(output_dir: Path, max_samples: int = 500) -> int:
    """Download JSSODa test split from HuggingFace.

    Args:
        output_dir: Directory to save images
        max_samples: Maximum samples to download

    Returns:
        Number of images downloaded
    """
    print("\n=== Downloading JSSODa Test Set ===\n")

    jssoda_test_dir = output_dir / "jssoda_test"
    jssoda_test_dir.mkdir(parents=True, exist_ok=True)
    (jssoda_test_dir / "vertical").mkdir(exist_ok=True)
    (jssoda_test_dir / "horizontal").mkdir(exist_ok=True)

    total_downloaded = 0
    manifest = {"vertical": [], "horizontal": []}

    try:
        print("  Loading llm-jp/JSSODa-test...")
        dataset = load_dataset("llm-jp/JSSODa-test", split="test")

        vertical_count = 0
        horizontal_count = 0

        for idx, sample in enumerate(tqdm(dataset, desc=_PROCESSING_DESC)):
            if idx >= max_samples:
                break

            image = sample.get("image")
            is_vertical = sample.get("is_vertical", False)
            num_columns = sample.get("num_columns", 1)

            if image is None:
                continue

            if is_vertical:
                orientation = "vertical"
                count = vertical_count
                vertical_count += 1
            else:
                orientation = "horizontal"
                count = horizontal_count
                horizontal_count += 1

            filename = f"jssoda_test_{orientation}_{count:05d}.png"
            filepath = jssoda_test_dir / orientation / filename

            if isinstance(image, Image.Image):
                image.save(filepath)
            else:
                with open(filepath, "wb") as f:
                    f.write(image)

            manifest[orientation].append(
                {
                    "filename": filename,
                    "path": str(filepath.relative_to(output_dir)),
                    "is_vertical": is_vertical,
                    "num_columns": num_columns,
                    "source": "llm-jp/JSSODa-test",
                    "split": "test",
                    "index": idx,
                }
            )

            total_downloaded += 1

        manifest_path = jssoda_test_dir / _MANIFEST_FILENAME
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n  Downloaded: {total_downloaded} images")
        print(f"    Vertical: {len(manifest['vertical'])}")
        print(f"    Horizontal: {len(manifest['horizontal'])}")

    except Exception as e:
        print(f"  ERROR: Failed to download JSSODa-test: {e}")
        return 0

    return total_downloaded


def download_arabic_ocr(output_dir: Path, max_samples: int = 1000) -> int:
    """Download Arabic OCR dataset from HuggingFace.

    Arabic OCR Dataset (mssqpi/Arabic-OCR-Dataset):
    - Arabic (RTL) document images
    - Useful for script detection training

    Args:
        output_dir: Directory to save images
        max_samples: Maximum samples to download

    Returns:
        Number of images downloaded
    """
    print("\n=== Downloading Arabic OCR Dataset ===\n")

    arabic_dir = output_dir / "arabic_ocr"
    arabic_dir.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    manifest = {"samples": [], "script": "arabic", "text_direction": "rtl"}

    try:
        print("  Loading mssqpi/Arabic-OCR-Dataset...")
        dataset = load_dataset("mssqpi/Arabic-OCR-Dataset", split="train")

        for idx, sample in enumerate(tqdm(dataset, desc=_PROCESSING_DESC)):
            if idx >= max_samples:
                break

            image = sample.get("image")
            if image is None:
                continue

            filename = f"arabic_ocr_{idx:05d}.png"
            filepath = arabic_dir / filename

            if isinstance(image, Image.Image):
                image.save(filepath)
            else:
                with open(filepath, "wb") as f:
                    f.write(image)

            manifest["samples"].append(
                {
                    "filename": filename,
                    "path": str(filepath.relative_to(output_dir)),
                    "source": "mssqpi/Arabic-OCR-Dataset",
                    "index": idx,
                }
            )

            total_downloaded += 1

        manifest_path = arabic_dir / _MANIFEST_FILENAME
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n  Downloaded: {total_downloaded} Arabic images")
        print(f"  Manifest: {manifest_path}")

    except Exception as e:
        print(f"  ERROR: Failed to download Arabic OCR: {e}")
        return 0

    return total_downloaded


def download_multilingual_ocr(output_dir: Path, max_samples: int = 1000) -> int:
    """Download Process-Venue Multilingual OCR dataset.

    Process-Venue/multilingual-ocr-dataset:
    - Multiple languages/scripts
    - Various document types

    Args:
        output_dir: Directory to save images
        max_samples: Maximum samples to download

    Returns:
        Number of images downloaded
    """
    print("\n=== Downloading Multilingual OCR Dataset ===\n")

    multi_dir = output_dir / "multilingual_ocr"
    multi_dir.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    manifest = {"samples": [], "scripts": {}}

    try:
        print("  Loading Process-Venue/multilingual-ocr-dataset...")
        dataset = load_dataset("Process-Venue/multilingual-ocr-dataset", split="train")

        for idx, sample in enumerate(tqdm(dataset, desc=_PROCESSING_DESC)):
            if idx >= max_samples:
                break

            image = sample.get("image")
            language = sample.get("language", "unknown")

            if image is None:
                continue

            # Create subdirectory for language
            lang_dir = multi_dir / language
            lang_dir.mkdir(exist_ok=True)

            filename = f"multi_{language}_{idx:05d}.png"
            filepath = lang_dir / filename

            if isinstance(image, Image.Image):
                image.save(filepath)
            else:
                with open(filepath, "wb") as f:
                    f.write(image)

            manifest["samples"].append(
                {
                    "filename": filename,
                    "path": str(filepath.relative_to(output_dir)),
                    "language": language,
                    "source": "Process-Venue/multilingual-ocr-dataset",
                    "index": idx,
                }
            )

            # Track script counts
            manifest["scripts"][language] = manifest["scripts"].get(language, 0) + 1

            total_downloaded += 1

        manifest_path = multi_dir / _MANIFEST_FILENAME
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n  Downloaded: {total_downloaded} multilingual images")
        print(f"  Scripts found: {list(manifest['scripts'].keys())}")
        print(f"  Manifest: {manifest_path}")

    except Exception as e:
        print(f"  ERROR: Failed to download Multilingual OCR: {e}")
        return 0

    return total_downloaded


def download_dzongkha_digits(output_dir: Path, max_samples: int = 500) -> int:
    """Download Dzongkha Handwritten Digits dataset from HuggingFace.

    Dzongkha Digits (proadhikary/dzongkha-digits):
    - 1,000 handwritten Dzongkha digit images (0-9)
    - Tibetan-derived script (useful for script detection)
    - Collected from 100 participants

    Args:
        output_dir: Directory to save images
        max_samples: Maximum samples to download

    Returns:
        Number of images downloaded
    """
    print("\n=== Downloading Dzongkha Digits Dataset ===\n")

    dzongkha_dir = output_dir / "dzongkha_digits"
    dzongkha_dir.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    manifest = {"samples": [], "script": "tibetan", "language": "dzongkha"}

    try:
        print("  Loading proadhikary/dzongkha-digits...")
        dataset = load_dataset("proadhikary/dzongkha-digits", split="train")

        for idx, sample in enumerate(tqdm(dataset, desc=_PROCESSING_DESC)):
            if idx >= max_samples:
                break

            image = sample.get("image")
            label = sample.get("label", -1)

            if image is None:
                continue

            filename = f"dzongkha_digit_{label}_{idx:05d}.png"
            filepath = dzongkha_dir / filename

            if isinstance(image, Image.Image):
                image.save(filepath)
            else:
                with open(filepath, "wb") as f:
                    f.write(image)

            manifest["samples"].append(
                {
                    "filename": filename,
                    "path": str(filepath.relative_to(output_dir)),
                    "digit_label": label,
                    "source": "proadhikary/dzongkha-digits",
                    "index": idx,
                }
            )

            total_downloaded += 1

        manifest_path = dzongkha_dir / _MANIFEST_FILENAME
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n  Downloaded: {total_downloaded} Dzongkha digit images")
        print("  Script: Tibetan (Dzongkha)")
        print(f"  Manifest: {manifest_path}")

    except Exception as e:
        print(f"  ERROR: Failed to download Dzongkha digits: {e}")
        return 0

    return total_downloaded


_KNOWN_DATASET_DIRS: frozenset[str] = frozenset(
    {
        "jssoda",
        "jssoda_test",
        "vjroda",
        "arabic_ocr",
        "multilingual_ocr",
        "dzongkha_digits",
    }
)


def _merge_script_counts(
    combined_scripts: dict,
    data: dict,
    vertical_count: int,
    horizontal_count: int,
    samples_count: int,
) -> None:
    """Merge per-manifest script counts into the combined scripts dict."""
    if "scripts" in data:
        for script, count in data["scripts"].items():
            combined_scripts[script] = combined_scripts.get(script, 0) + count

    # Track Japanese as a script
    if "japanese" not in combined_scripts and (vertical_count + horizontal_count) > 0:
        combined_scripts["japanese"] = vertical_count + horizontal_count

    # Track script by declared type (Arabic, Tibetan)
    declared_script = data.get("script")
    if declared_script in ("arabic", "tibetan"):
        combined_scripts[declared_script] = (
            combined_scripts.get(declared_script, 0) + samples_count
        )


def _process_single_manifest(
    manifest_path: Path,
    output_dir: Path,
    combined: dict,
) -> None:
    """Load one manifest file and accumulate its data into *combined*."""
    with open(manifest_path) as f:
        data = json.load(f)

    vertical_count = len(data.get("vertical", []))
    horizontal_count = len(data.get("horizontal", []))
    samples_count = len(data.get("samples", []))

    combined["datasets"].append(
        {
            "name": manifest_path.parent.name,
            "path": str(manifest_path.relative_to(output_dir)),
            "vertical_count": vertical_count,
            "horizontal_count": horizontal_count,
            "samples_count": samples_count,
        }
    )

    combined["total_vertical"] += vertical_count
    combined["total_horizontal"] += horizontal_count
    combined["total_samples"] += vertical_count + horizontal_count + samples_count

    _merge_script_counts(
        combined["scripts"],
        data,
        vertical_count,
        horizontal_count,
        samples_count,
    )


def create_combined_manifest(output_dir: Path) -> None:
    """Create a combined manifest for all script/language datasets."""
    print("\n=== Creating Combined Manifest ===\n")

    combined: dict = {
        "datasets": [],
        "total_vertical": 0,
        "total_horizontal": 0,
        "total_samples": 0,
        "scripts": {},
    }

    for manifest_path in output_dir.rglob(_MANIFEST_FILENAME):
        if manifest_path.parent.name not in _KNOWN_DATASET_DIRS:
            continue
        _process_single_manifest(manifest_path, output_dir, combined)

    # Save combined manifest
    combined_path = output_dir / "combined_manifest.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"  Total vertical: {combined['total_vertical']}")
    print(f"  Total horizontal: {combined['total_horizontal']}")
    print(f"  Total samples: {combined['total_samples']}")
    print(f"  Scripts: {combined['scripts']}")
    print(f"  Combined manifest: {combined_path}")


def print_summary(output_dir: Path) -> None:
    """Print download summary."""
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    combined_path = output_dir / "combined_manifest.json"
    if combined_path.exists():
        with open(combined_path) as f:
            combined = json.load(f)

        print(f"\nOutput Directory: {output_dir}")
        print("\nDatasets Downloaded:")
        for ds in combined["datasets"]:
            print(
                f"  - {ds['name']}: {ds['vertical_count']} vertical, "
                f"{ds['horizontal_count']} horizontal"
            )

        print(f"\nTotal Samples: {combined['total_samples']}")
        print(f"  Vertical: {combined['total_vertical']}")
        print(f"  Horizontal: {combined['total_horizontal']}")

        # Calculate how many we need for orientation training
        target_japanese = 1250  # From MobileCLIP spec
        if combined["total_vertical"] >= target_japanese:
            print(
                f"\n✓ Sufficient vertical samples for orientation training "
                f"(need {target_japanese}, have {combined['total_vertical']})"
            )
        else:
            print(
                f"\n⚠ May need more vertical samples "
                f"(need {target_japanese}, have {combined['total_vertical']})"
            )

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download multilingual script datasets for Phase 10A"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "/mnt/e/image_detection/01_base_data/language/multilingual_scripts"
        ),
        help="Output directory for datasets",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=2000,
        help="Maximum samples per dataset split",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default="jssoda,arabic,multilingual,dzongkha",
        help="Comma-separated list of datasets to download (jssoda,arabic,multilingual,dzongkha)",
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip downloading test splits",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Multilingual Script Dataset Download")
    print("Phase 10A - MobileCLIP Alignment")
    print("=" * 60)

    # Parse dataset selection
    datasets_to_download = [d.strip().lower() for d in args.datasets.split(",")]
    print(f"\nDatasets to download: {datasets_to_download}")

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Download datasets
    total = 0

    # JSSODa - Japanese vertical/horizontal text
    if "jssoda" in datasets_to_download:
        total += download_jssoda(args.output, max_samples=args.max_samples)
        if not args.skip_test:
            total += download_jssoda_test(
                args.output, max_samples=args.max_samples // 4
            )

    # Arabic OCR dataset
    if "arabic" in datasets_to_download:
        total += download_arabic_ocr(args.output, max_samples=args.max_samples // 2)

    # Multilingual OCR dataset
    if "multilingual" in datasets_to_download:
        total += download_multilingual_ocr(args.output, max_samples=args.max_samples)

    # Dzongkha (Tibetan script) digits
    if "dzongkha" in datasets_to_download:
        total += download_dzongkha_digits(
            args.output, max_samples=args.max_samples // 4
        )

    # Create combined manifest
    create_combined_manifest(args.output)

    # Print summary
    print_summary(args.output)

    if total > 0:
        print("\nDownload complete!")
        print(f"Total images: {total}")
    else:
        print("\nNo images downloaded. Check error messages above.")

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
