#!/usr/bin/env python3
"""Create Final Training Dataset.

Merges weak supervision labels with manual corrections and creates train/val/test splits.

Usage:
    python scripts/create_final_dataset.py \
        --weak-supervision-dir data/weak_supervision_labels \
        --corrected-labels-dir data/corrected_labels \
        --output-dir data/final_training_dataset \
        --train-ratio 0.8 \
        --val-ratio 0.1 \
        --test-ratio 0.1

Sprint 3.3.5: Create Final Training Dataset (Milestone 10.3)
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.progress import track
from rich.table import Table

console = Console()

# Quality issue types
QUALITY_ISSUES = [
    "noise",
    "blur",
    "skew",
    "perspective",
    "low_contrast",
    "orientation",
]


def load_labels(label_path: Path) -> dict[str, Any]:
    """Load labels from JSON file.

    Args:
        label_path: Path to labels JSON file

    Returns:
        Dictionary with labels and metadata
    """
    with open(label_path) as f:
        return json.load(f)


def merge_labels(
    weak_supervision_dir: Path,
    corrected_labels_dir: Path,
) -> list[dict[str, Any]]:
    """Merge weak supervision labels with manual corrections.

    Manual corrections take precedence over weak supervision.

    Args:
        weak_supervision_dir: Directory with weak supervision labels
        corrected_labels_dir: Directory with manual corrections

    Returns:
        List of merged label dictionaries
    """
    console.print("\n[bold cyan]Merging Labels[/bold cyan]")
    console.print(f"Weak supervision: {weak_supervision_dir}")
    console.print(f"Manual corrections: {corrected_labels_dir}")

    # Load all weak supervision labels
    ws_files = {f.stem: f for f in weak_supervision_dir.glob("*_labels.json")}
    console.print(f"Found {len(ws_files)} weak supervision files")

    # Load all corrected labels
    corrected_files = {}
    if corrected_labels_dir.exists():
        corrected_files = {
            f.stem.replace("_corrected", "_labels"): f
            for f in corrected_labels_dir.glob("*_corrected.json")
        }
        console.print(f"Found {len(corrected_files)} corrected label files")
    else:
        console.print(
            "[yellow]No corrected labels directory found - using only weak supervision[/yellow]"
        )

    # Merge labels (corrected takes precedence)
    merged_labels = []
    corrected_count = 0
    ws_count = 0

    for stem, ws_file in track(
        ws_files.items(),
        description="Merging labels",
        total=len(ws_files),
    ):
        # Load weak supervision labels
        ws_data = load_labels(ws_file)

        # Check if manual correction exists
        if stem in corrected_files:
            # Use corrected labels
            corrected_data = load_labels(corrected_files[stem])

            merged_labels.append(
                {
                    "image_path": corrected_data["image_path"],
                    "label_path": str(corrected_files[stem]),
                    "label_source": "manual_correction",
                    "corrected_labels": corrected_data["corrected_labels"],
                    "quality_scores": corrected_data.get("quality_scores", {}),
                    "annotator_notes": corrected_data.get("annotator_notes", ""),
                }
            )
            corrected_count += 1
        else:
            # Use weak supervision labels
            # Convert to same format as corrected labels
            ws_labels_dict = {
                issue: ws_data["labels"][issue]["value"]
                for issue in QUALITY_ISSUES
                if issue in ws_data["labels"]
            }

            merged_labels.append(
                {
                    "image_path": ws_data["image_path"],
                    "label_path": str(ws_file),
                    "label_source": "weak_supervision",
                    "corrected_labels": ws_labels_dict,  # Use WS labels as ground truth
                    "quality_scores": ws_data.get("quality_scores", {}),
                    "annotator_notes": "",
                }
            )
            ws_count += 1

    console.print(f"\n[green]Merged {len(merged_labels)} total samples:[/green]")
    console.print(f"  Manual corrections: {corrected_count}")
    console.print(f"  Weak supervision: {ws_count}")

    return merged_labels


def split_dataset(
    merged_labels: list[dict[str, Any]],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split dataset into train, val, and test sets.

    Args:
        merged_labels: List of merged label dictionaries
        train_ratio: Ratio of training samples (default: 0.8)
        val_ratio: Ratio of validation samples (default: 0.1)
        test_ratio: Ratio of test samples (default: 0.1)
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Tuple of (train_samples, val_samples, test_samples)
    """
    # Validate ratios
    if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
        msg = f"Ratios must sum to 1.0 (got {train_ratio + val_ratio + test_ratio})"
        raise ValueError(msg)

    # Shuffle with fixed seed
    random.seed(random_seed)
    shuffled = merged_labels.copy()
    random.shuffle(shuffled)

    # Calculate split indices
    total = len(shuffled)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    # Split
    train_samples = shuffled[:train_end]
    val_samples = shuffled[train_end:val_end]
    test_samples = shuffled[val_end:]

    console.print(f"\n[bold cyan]Dataset Split (seed={random_seed})[/bold cyan]")
    console.print(
        f"Train: {len(train_samples)} ({len(train_samples) / total * 100:.1f}%)"
    )
    console.print(f"Val: {len(val_samples)} ({len(val_samples) / total * 100:.1f}%)")
    console.print(f"Test: {len(test_samples)} ({len(test_samples) / total * 100:.1f}%)")

    return train_samples, val_samples, test_samples


def save_split(
    output_dir: Path,
    split_name: str,
    samples: list[dict[str, Any]],
) -> None:
    """Save dataset split to JSON file.

    Args:
        output_dir: Output directory
        split_name: Split name ("train", "val", or "test")
        samples: List of sample dictionaries
    """
    split_file = output_dir / f"{split_name}_split.json"

    split_data = {
        "split": split_name,
        "num_samples": len(samples),
        "samples": samples,
    }

    with open(split_file, "w") as f:
        json.dump(split_data, f, indent=2)

    console.print(f"[green]✅ Saved {split_name} split to {split_file}[/green]")


def calculate_label_distribution(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate label distribution for a dataset split.

    Args:
        samples: List of sample dictionaries

    Returns:
        Dictionary with label statistics
    """
    label_counts = dict.fromkeys(QUALITY_ISSUES, 0)
    total_samples = len(samples)

    for sample in samples:
        labels = sample["corrected_labels"]
        for issue in QUALITY_ISSUES:
            if labels.get(issue, 0) == 1:
                label_counts[issue] += 1

    percentages = {
        issue: (count / total_samples) * 100 if total_samples > 0 else 0
        for issue, count in label_counts.items()
    }

    return {
        "total_samples": total_samples,
        "label_counts": label_counts,
        "label_percentages": percentages,
        "average_issues_per_image": sum(label_counts.values()) / total_samples
        if total_samples > 0
        else 0,
    }


def verify_dataset_integrity(
    train_samples: list[dict],
    val_samples: list[dict],
    test_samples: list[dict],
) -> bool:
    """Verify dataset integrity (no overlaps, all files exist).

    Args:
        train_samples: Training samples
        val_samples: Validation samples
        test_samples: Test samples

    Returns:
        True if dataset is valid, False otherwise
    """
    console.print("\n[bold cyan]Verifying Dataset Integrity[/bold cyan]")

    # Check for overlaps
    train_images = {s["image_path"] for s in train_samples}
    val_images = {s["image_path"] for s in val_samples}
    test_images = {s["image_path"] for s in test_samples}

    train_val_overlap = train_images & val_images
    train_test_overlap = train_images & test_images
    val_test_overlap = val_images & test_images

    if train_val_overlap or train_test_overlap or val_test_overlap:
        console.print("[red]❌ Dataset integrity check FAILED:[/red]")
        if train_val_overlap:
            console.print(f"  Train-Val overlap: {len(train_val_overlap)} images")
        if train_test_overlap:
            console.print(f"  Train-Test overlap: {len(train_test_overlap)} images")
        if val_test_overlap:
            console.print(f"  Val-Test overlap: {len(val_test_overlap)} images")
        return False

    # Check that all images exist
    all_samples = train_samples + val_samples + test_samples
    missing_images = []
    missing_labels = []

    for sample in all_samples:
        image_path = Path(sample["image_path"])
        label_path = Path(sample["label_path"])

        if not image_path.exists():
            missing_images.append(str(image_path))

        if not label_path.exists():
            missing_labels.append(str(label_path))

    if missing_images or missing_labels:
        console.print("[red]❌ Dataset integrity check FAILED:[/red]")
        if missing_images:
            console.print(f"  Missing {len(missing_images)} images")
        if missing_labels:
            console.print(f"  Missing {len(missing_labels)} labels")
        return False

    console.print("[green]✅ Dataset integrity check PASSED[/green]")
    return True


def print_statistics_table(
    train_stats: dict,
    val_stats: dict,
    test_stats: dict,
) -> None:
    """Print label distribution statistics table.

    Args:
        train_stats: Training set statistics
        val_stats: Validation set statistics
        test_stats: Test set statistics
    """
    table = Table(title="Label Distribution Statistics")

    table.add_column("Quality Issue", style="cyan")
    table.add_column("Train", style="magenta")
    table.add_column("Val", style="magenta")
    table.add_column("Test", style="magenta")

    for issue in QUALITY_ISSUES:
        train_pct = train_stats["label_percentages"][issue]
        val_pct = val_stats["label_percentages"][issue]
        test_pct = test_stats["label_percentages"][issue]

        table.add_row(
            issue.replace("_", " ").title(),
            f"{train_stats['label_counts'][issue]} ({train_pct:.1f}%)",
            f"{val_stats['label_counts'][issue]} ({val_pct:.1f}%)",
            f"{test_stats['label_counts'][issue]} ({test_pct:.1f}%)",
        )

    # Add total row
    table.add_row(
        "[bold]Total Samples[/bold]",
        f"[bold]{train_stats['total_samples']}[/bold]",
        f"[bold]{val_stats['total_samples']}[/bold]",
        f"[bold]{test_stats['total_samples']}[/bold]",
    )

    console.print("\n")
    console.print(table)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create final training dataset (Sprint 3.3.5)"
    )
    parser.add_argument(
        "--weak-supervision-dir",
        type=Path,
        default=Path("data/weak_supervision_labels"),
        help="Directory with weak supervision labels",
    )
    parser.add_argument(
        "--corrected-labels-dir",
        type=Path,
        default=Path("data/corrected_labels"),
        help="Directory with manual corrections",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/final_training_dataset"),
        help="Output directory for final dataset",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Training set ratio (default: 0.8)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="Validation set ratio (default: 0.1)",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.1,
        help="Test set ratio (default: 0.1)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # Validate input directories
    if not args.weak_supervision_dir.exists():
        console.print(
            f"[red]Error: Weak supervision directory not found: {args.weak_supervision_dir}[/red]"
        )
        return

    # Merge labels
    merged_labels = merge_labels(
        args.weak_supervision_dir,
        args.corrected_labels_dir,
    )

    if not merged_labels:
        console.print("[red]Error: No labels found to merge[/red]")
        return

    # Split dataset
    train_samples, val_samples, test_samples = split_dataset(
        merged_labels,
        args.train_ratio,
        args.val_ratio,
        args.test_ratio,
        args.random_seed,
    )

    # Verify integrity
    if not verify_dataset_integrity(train_samples, val_samples, test_samples):
        console.print("[red]Dataset integrity check failed - aborting[/red]")
        return

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Save splits
    save_split(args.output_dir, "train", train_samples)
    save_split(args.output_dir, "val", val_samples)
    save_split(args.output_dir, "test", test_samples)

    # Calculate and display statistics
    train_stats = calculate_label_distribution(train_samples)
    val_stats = calculate_label_distribution(val_samples)
    test_stats = calculate_label_distribution(test_samples)

    print_statistics_table(train_stats, val_stats, test_stats)

    # Save metadata
    metadata = {
        "creation_timestamp": datetime.now().isoformat(),
        "weak_supervision_dir": str(args.weak_supervision_dir),
        "corrected_labels_dir": str(args.corrected_labels_dir),
        "total_samples": len(merged_labels),
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
        "test_samples": len(test_samples),
        "train_ratio": args.train_ratio,
        "val_ratio": args.val_ratio,
        "test_ratio": args.test_ratio,
        "random_seed": args.random_seed,
        "quality_issues": QUALITY_ISSUES,
        "statistics": {
            "train": train_stats,
            "val": val_stats,
            "test": test_stats,
        },
    }

    metadata_file = args.output_dir / "dataset_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    console.print(f"\n[green]✅ Saved dataset metadata to {metadata_file}[/green]")

    # Success message
    console.print(
        "\n[bold green]✅ Final Training Dataset Created Successfully![/bold green]"
    )
    console.print(f"[cyan]Dataset saved to: {args.output_dir}[/cyan]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Test dataset loading:")
    console.print(f"   [cyan]python data/dataset.py {args.output_dir}[/cyan]")
    console.print("2. Train DocLayout-YOLO model:")
    console.print("   [cyan]modal run modal/train_phase3_doclayout_yolo.py[/cyan]\n")


if __name__ == "__main__":
    main()
