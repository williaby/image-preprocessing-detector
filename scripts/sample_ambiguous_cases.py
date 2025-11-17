#!/usr/bin/env python3
"""Sample Ambiguous Cases for Manual Review.

Identifies low-confidence weak supervision predictions and samples images for manual validation.

Usage:
    python scripts/sample_ambiguous_cases.py \\
        --input-dir data/weak_supervision_labels \\
        --output-dir data/annotation_queue \\
        --num-samples 2000 \\
        --confidence-threshold 0.85

Sprint 3.3.2: Sample Ambiguous Cases (Milestone 10.3)
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.progress import track
from rich.table import Table

console = Console()

# Ambiguity detection thresholds (aligned with weak_supervision.py thresholds)
# These define borderline ranges where predictions are most uncertain
LAPLACIAN_BLUR_MIN = 80  # Lower bound for borderline blur (below = clearly blurry)
LAPLACIAN_BLUR_MAX = 150  # Upper bound for borderline blur (above = clearly sharp)
RMS_CONTRAST_MIN = 0.25  # Lower bound for borderline contrast
RMS_CONTRAST_MAX = 0.35  # Upper bound for borderline contrast
SKEW_ANGLE_MIN = 1.5  # Lower bound for borderline skew (degrees)
SKEW_ANGLE_MAX = 3.0  # Upper bound for borderline skew (degrees)
CONFIDENCE_VARIANCE_THRESHOLD = 0.15  # Threshold for mixed confidence detection


def load_weak_supervision_labels(labels_path: Path) -> dict[str, Any]:
    """Load weak supervision labels from JSON file.

    Args:
        labels_path: Path to labels JSON file

    Returns:
        Dictionary with image_path, labels, and quality_scores
    """
    with open(labels_path) as f:
        return json.load(f)


def calculate_uncertainty(labels_data: dict[str, Any]) -> float:
    """Calculate uncertainty score for an image based on label confidence.

    Lower confidence = higher uncertainty.

    Args:
        labels_data: Weak supervision labels dictionary

    Returns:
        Uncertainty score (0.0 = certain, 1.0 = uncertain)
    """
    labels = labels_data.get("labels", {})

    if not labels:
        return 1.0  # Maximum uncertainty if no labels

    # Extract confidence scores
    confidences = [label.get("confidence", 0.0) for label in labels.values()]

    # Images with low average confidence are uncertain
    mean_confidence = np.mean(confidences)
    uncertainty = 1.0 - mean_confidence

    return float(uncertainty)


def calculate_edge_case_score(labels_data: dict[str, Any]) -> float:
    """Calculate edge case score based on borderline quality metrics.

    Edge cases have quality metrics near decision thresholds.

    Args:
        labels_data: Weak supervision labels dictionary

    Returns:
        Edge case score (0.0 = clear, 1.0 = edge case)
    """
    quality_scores = labels_data.get("quality_scores", {})
    labels = labels_data.get("labels", {})

    edge_scores = []

    # Check if blur is borderline (Laplacian variance near threshold)
    laplacian_var = quality_scores.get("laplacian_variance", 0)
    if LAPLACIAN_BLUR_MIN < laplacian_var < LAPLACIAN_BLUR_MAX:
        edge_scores.append(1.0)

    # Check if contrast is borderline (RMS contrast near threshold)
    rms_contrast = quality_scores.get("rms_contrast", 0)
    if RMS_CONTRAST_MIN < rms_contrast < RMS_CONTRAST_MAX:
        edge_scores.append(1.0)

    # Check if skew is borderline (angle near threshold)
    skew_angle = quality_scores.get("skew_angle_degrees", 0)
    if SKEW_ANGLE_MIN < skew_angle < SKEW_ANGLE_MAX:
        edge_scores.append(1.0)

    # Check for mixed confidence (some high, some low)
    confidences = [label.get("confidence", 0.0) for label in labels.values()]
    if confidences:
        confidence_std = np.std(confidences)
        if confidence_std > CONFIDENCE_VARIANCE_THRESHOLD:
            edge_scores.append(confidence_std)

    if not edge_scores:
        return 0.0

    return float(np.mean(edge_scores))


def calculate_composite_priority(labels_data: dict[str, Any]) -> float:
    """Calculate composite priority score for sampling.

    Combines uncertainty and edge case scores.

    Args:
        labels_data: Weak supervision labels dictionary

    Returns:
        Priority score (higher = more important to annotate)
    """
    uncertainty = calculate_uncertainty(labels_data)
    edge_case = calculate_edge_case_score(labels_data)

    # Weighted combination (uncertainty is more important)
    priority = 0.7 * uncertainty + 0.3 * edge_case

    return float(priority)


def sample_ambiguous_cases(
    input_dir: Path,
    output_dir: Path,
    num_samples: int = 2000,
    confidence_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """Sample ambiguous cases for manual review.

    Args:
        input_dir: Directory containing weak supervision labels
        output_dir: Directory to save sampled annotation queue
        num_samples: Number of images to sample (default: 2000)
        confidence_threshold: Confidence threshold for filtering (default: 0.85)

    Returns:
        List of sampled label dictionaries with priority scores
    """
    console.print("\n[bold cyan]Sampling Ambiguous Cases for Manual Review[/bold cyan]")
    console.print(f"Input: {input_dir}")
    console.print(f"Output: {output_dir}")
    console.print(f"Target samples: {num_samples}")
    console.print(f"Confidence threshold: {confidence_threshold}\n")

    # Load all weak supervision labels
    label_files = sorted(input_dir.glob("*_labels.json"))
    console.print(f"Found {len(label_files)} label files")

    if not label_files:
        console.print("[red]No label files found![/red]")
        return []

    # Calculate priority scores
    console.print("\n[yellow]Calculating priority scores...[/yellow]")
    scored_labels = []

    for label_file in track(label_files, description="Processing labels"):
        try:
            labels_data = load_weak_supervision_labels(label_file)

            # Calculate uncertainty and priority
            uncertainty = calculate_uncertainty(labels_data)
            edge_case = calculate_edge_case_score(labels_data)
            priority = calculate_composite_priority(labels_data)

            # Check if below confidence threshold
            mean_confidence = 1.0 - uncertainty
            if mean_confidence < confidence_threshold:
                scored_labels.append(
                    {
                        "label_file": str(label_file),
                        "image_path": labels_data["image_path"],
                        "uncertainty": uncertainty,
                        "edge_case_score": edge_case,
                        "priority": priority,
                        "mean_confidence": mean_confidence,
                        "labels": labels_data["labels"],
                        "quality_scores": labels_data.get("quality_scores", {}),
                    }
                )
        except Exception as e:
            console.print(f"[red]Error processing {label_file}: {e}[/red]")
            continue

    console.print(f"\nFiltered to {len(scored_labels)} low-confidence images")

    # Sort by priority (highest first)
    scored_labels.sort(key=lambda x: x["priority"], reverse=True)

    # Sample top N
    sampled = scored_labels[:num_samples]
    console.print(f"Sampled {len(sampled)} images for annotation\n")

    # Display statistics
    table = Table(title="Sampling Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total labels", str(len(label_files)))
    table.add_row("Low-confidence images", str(len(scored_labels)))
    table.add_row("Sampled for annotation", str(len(sampled)))
    table.add_row(
        "Mean uncertainty", f"{np.mean([x['uncertainty'] for x in sampled]):.3f}"
    )
    table.add_row(
        "Mean edge case score",
        f"{np.mean([x['edge_case_score'] for x in sampled]):.3f}",
    )
    table.add_row("Mean priority", f"{np.mean([x['priority'] for x in sampled]):.3f}")

    console.print(table)

    # Save annotation queue
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy sampled label files to annotation queue
    console.print(f"\n[yellow]Copying sampled labels to {output_dir}...[/yellow]")
    for item in track(sampled, description="Copying files"):
        src_file = Path(item["label_file"])
        dst_file = output_dir / src_file.name
        shutil.copy(src_file, dst_file)

    # Save sampling metadata
    metadata_file = output_dir / "sampling_metadata.json"
    metadata = {
        "total_labels": len(label_files),
        "low_confidence_count": len(scored_labels),
        "sampled_count": len(sampled),
        "num_samples_requested": num_samples,
        "confidence_threshold": confidence_threshold,
        "sampling_strategy": "priority-based (uncertainty + edge case score)",
        "statistics": {
            "mean_uncertainty": float(np.mean([x["uncertainty"] for x in sampled])),
            "mean_edge_case_score": float(
                np.mean([x["edge_case_score"] for x in sampled])
            ),
            "mean_priority": float(np.mean([x["priority"] for x in sampled])),
            "min_priority": float(np.min([x["priority"] for x in sampled])),
            "max_priority": float(np.max([x["priority"] for x in sampled])),
        },
        "sampled_files": [
            {
                "label_file": item["label_file"],
                "image_path": item["image_path"],
                "priority": item["priority"],
                "uncertainty": item["uncertainty"],
                "edge_case_score": item["edge_case_score"],
            }
            for item in sampled
        ],
    }

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    console.print(f"[green]✅ Saved sampling metadata to {metadata_file}[/green]\n")

    return sampled


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sample ambiguous cases for manual review (Sprint 3.3.2)"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/weak_supervision_labels"),
        help="Directory containing weak supervision labels",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/annotation_queue"),
        help="Directory to save sampled annotation queue",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=2000,
        help="Number of images to sample for annotation (default: 2000)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.85,
        help="Confidence threshold for filtering (default: 0.85)",
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.input_dir.exists():
        console.print(f"[red]Error: Input directory not found: {args.input_dir}[/red]")
        console.print(
            "[yellow]Please generate weak supervision labels first using data/weak_supervision.py[/yellow]"
        )
        return

    # Sample ambiguous cases
    sampled = sample_ambiguous_cases(
        args.input_dir,
        args.output_dir,
        args.num_samples,
        args.confidence_threshold,
    )

    if sampled:
        console.print(
            f"[bold green]✅ Successfully sampled {len(sampled)} ambiguous cases[/bold green]"
        )
        console.print(f"[cyan]Annotation queue ready in: {args.output_dir}[/cyan]")
        console.print("\n[bold]Next step:[/bold] Run manual validation UI:")
        console.print(
            f"[cyan]streamlit run tools/manual_validation_ui.py -- --input-dir {args.output_dir}[/cyan]\n"
        )
    else:
        console.print("[yellow]No ambiguous cases found[/yellow]")


if __name__ == "__main__":
    main()
