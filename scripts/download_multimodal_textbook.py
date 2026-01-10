#!/usr/bin/env python3
"""Download DAMO-NLP-SG/multimodal_textbook dataset to E: drive.

This dataset contains 6.5M keyframe images (~600GB total) from educational videos.
Images are split into 20 parts (~30GB each).

Usage:
    # Download annotations only (recommended first step)
    python scripts/download_multimodal_textbook.py --annotations-only

    # Download specific parts (0-19)
    python scripts/download_multimodal_textbook.py --parts 0 1 2

    # Download sample data only
    python scripts/download_multimodal_textbook.py --sample-only

    # Download everything (600GB+)
    python scripts/download_multimodal_textbook.py --all
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

REPO_ID = "DAMO-NLP-SG/multimodal_textbook"
# E: drive reorganized 2025-12-16: educational datasets in 01_base_data/educational/
TARGET_DIR = Path("/mnt/e/image_detection/01_base_data/educational/multimodal_textbook")


@dataclass
class DatasetFiles:
    """Categorized dataset files."""

    annotations: list[str]
    samples: list[str]
    image_parts: list[str]
    all_files: list[str]

    @classmethod
    def from_repo(cls, repo_id: str) -> DatasetFiles:
        """Fetch and categorize files from HuggingFace repo."""
        all_files = list_repo_files(repo_id, repo_type="dataset")
        return cls(
            annotations=[
                f
                for f in all_files
                if f.endswith((".json", ".json.zip")) or f == "README.md"
            ],
            samples=[f for f in all_files if f.startswith("example_data/")],
            image_parts=sorted([f for f in all_files if "tar.gz.part_" in f]),
            all_files=list(all_files),
        )


def download_files(files: list[str], target_dir: Path) -> None:
    """Download specific files from the dataset."""
    target_dir.mkdir(parents=True, exist_ok=True)

    for i, filename in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Downloading: {filename}")
        try:
            hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                repo_type="dataset",
                local_dir=str(target_dir),
                local_dir_use_symlinks=False,
            )
            print(f"  ✓ Complete: {filename}")
        except Exception as e:
            print(f"  ✗ Failed: {filename} - {e}")


def get_parts_files(parts: list[int], dataset: DatasetFiles) -> tuple[list[str], str]:
    """Get files for specific parts download."""
    files = dataset.annotations.copy()
    for part_num in parts:
        part_file = f"dataset_images_interval_7.tar.gz.part_{part_num:02d}"
        if part_file in dataset.image_parts:
            files.append(part_file)
        else:
            print(f"Warning: Part {part_num} not found")
    msg = f"Downloading {len(parts)} image parts + annotations (~{len(parts) * 30 + 11}GB)"
    return files, msg


def show_available_files(
    parser: argparse.ArgumentParser, dataset: DatasetFiles
) -> None:
    """Display help and available files."""
    parser.print_help()
    print("\n" + "-" * 60)
    print("Available image parts (20 total, ~30GB each):")
    for i, part in enumerate(dataset.image_parts):
        print(f"  Part {i}: {part}")
    print(f"\nAnnotation files ({len(dataset.annotations)} files):")
    for f in dataset.annotations:
        print(f"  {f}")


def print_extraction_steps() -> None:
    """Print post-download extraction instructions."""
    print("\nNext steps to extract images:")
    print(f"  cd {TARGET_DIR}")
    print(
        "  cat dataset_images_interval_7.tar.gz.part_* > dataset_images_interval_7.tar.gz"
    )
    print("  tar -xzvf dataset_images_interval_7.tar.gz")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download DAMO-NLP-SG/multimodal_textbook dataset"
    )
    parser.add_argument(
        "--annotations-only",
        action="store_true",
        help="Download only annotation JSON files (~11GB)",
    )
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Download only sample data for evaluation",
    )
    parser.add_argument(
        "--parts",
        nargs="+",
        type=int,
        choices=range(20),
        metavar="N",
        help="Download specific image parts (0-19, each ~30GB)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Download everything (~600GB)"
    )
    return parser.parse_args(), parser


def main() -> None:
    """Download multimodal textbook dataset with options."""
    args, parser = parse_args()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    dataset = DatasetFiles.from_repo(REPO_ID)

    print(f"Target directory: {TARGET_DIR}")
    print(f"Dataset: {REPO_ID}")
    print("-" * 60)

    # Determine files to download based on args
    files_to_download: list[str] = []
    needs_extraction = False

    if args.sample_only:
        files_to_download = dataset.samples
        print(f"Downloading sample data only ({len(files_to_download)} files)")
    elif args.annotations_only:
        files_to_download = dataset.annotations
        print(f"Downloading annotations only ({len(files_to_download)} files, ~11GB)")
    elif args.parts:
        files_to_download, msg = get_parts_files(args.parts, dataset)
        print(msg)
        needs_extraction = True
    elif args.all:
        files_to_download = dataset.all_files
        print(f"Downloading ALL files ({len(files_to_download)} files, ~611GB)")
        needs_extraction = True
    else:
        show_available_files(parser, dataset)
        return

    print("-" * 60)
    download_files(files_to_download, TARGET_DIR)

    print("-" * 60)
    print("Download complete!")
    print(f"Dataset location: {TARGET_DIR}")

    if needs_extraction:
        print_extraction_steps()


if __name__ == "__main__":
    main()
