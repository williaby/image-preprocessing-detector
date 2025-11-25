#!/usr/bin/env python3
"""
Risk Distribution Visualization Script (Milestone 9.1 - Sprint 2.6.4)

Generates visualizations of pre-OCR risk score distributions across a test dataset.
Creates histogram plots showing:
1. Distribution of pre-OCR risk scores
2. Distribution of DQS degradation scores
3. Distribution of DQS structural complexity scores
4. (Optional) Overlay with OCR accuracy when ground truth is available

Outputs:
- docs/validation/risk_distribution.png
- docs/validation/dqs_distribution.png
- docs/validation/risk_statistics.json

Usage:
    python scripts/visualize_risk_distribution.py --input-dir /path/to/documents
    python scripts/visualize_risk_distribution.py --input-dir /path/to/documents --with-ocr-data ocr_results.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.ingestion.document_processor import process_document


def collect_risk_scores(input_dir: Path, max_documents: int = 50) -> dict[str, Any]:
    """
    Process documents and collect risk scores.

    Args:
        input_dir: Directory containing PDF/image files
        max_documents: Maximum number of documents to process

    Returns:
        Dictionary with collected scores and metadata
    """
    risk_scores = []
    degradation_scores = []
    complexity_scores = []
    pdf_types = []
    doc_ids = []

    # Find all PDF files in input directory
    pdf_files = list(input_dir.glob("**/*.pdf"))[:max_documents]

    if not pdf_files:
        print(f"Warning: No PDF files found in {input_dir}")
        return {
            "risk_scores": [],
            "degradation_scores": [],
            "complexity_scores": [],
            "pdf_types": [],
            "doc_ids": [],
        }

    print(f"Processing {len(pdf_files)} documents...")

    for pdf_file in pdf_files:
        try:
            # Process document
            metadata = process_document(pdf_file)

            # Collect scores
            if metadata.pre_ocr_risk is not None:
                risk_scores.append(metadata.pre_ocr_risk)
            if metadata.dqs is not None:
                degradation_scores.append(metadata.dqs.degradation_score)
                complexity_scores.append(metadata.dqs.structural_complexity_score)
            if metadata.pdf_type is not None:
                pdf_types.append(metadata.pdf_type.value)
            doc_ids.append(metadata.document_id)

            print(
                f"  ✓ {pdf_file.name}: risk={metadata.pre_ocr_risk:.3f}, "
                f"degradation={metadata.dqs.degradation_score:.3f}"
            )

        except Exception as e:
            print(f"  ✗ {pdf_file.name}: Error - {e}")
            continue

    return {
        "risk_scores": risk_scores,
        "degradation_scores": degradation_scores,
        "complexity_scores": complexity_scores,
        "pdf_types": pdf_types,
        "doc_ids": doc_ids,
    }


def calculate_statistics(scores: list[float]) -> dict[str, float]:
    """Calculate descriptive statistics for scores."""
    if not scores:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "q25": 0.0,
            "q75": 0.0,
        }

    scores_array = np.array(scores)
    return {
        "mean": float(np.mean(scores_array)),
        "median": float(np.median(scores_array)),
        "std": float(np.std(scores_array)),
        "min": float(np.min(scores_array)),
        "max": float(np.max(scores_array)),
        "q25": float(np.percentile(scores_array, 25)),
        "q75": float(np.percentile(scores_array, 75)),
    }


def plot_risk_distribution(
    data: dict[str, Any],
    output_path: Path,
    ocr_accuracy: list[float] | None = None,
) -> None:
    """
    Create histogram visualization of pre-OCR risk distribution.

    Args:
        data: Dictionary with collected scores
        output_path: Path to save the plot
        ocr_accuracy: Optional OCR accuracy scores for overlay
    """
    risk_scores = data["risk_scores"]

    if not risk_scores:
        print("Warning: No risk scores to plot")
        return

    _fig, axes = plt.subplots(
        2 if ocr_accuracy else 1, 1, figsize=(10, 8 if ocr_accuracy else 6)
    )
    if not ocr_accuracy:
        axes = [axes]

    # Plot 1: Risk score distribution
    axes[0].hist(risk_scores, bins=20, color="steelblue", alpha=0.7, edgecolor="black")
    axes[0].axvline(
        np.mean(risk_scores), color="red", linestyle="--", linewidth=2, label="Mean"
    )
    axes[0].axvline(
        np.median(risk_scores),
        color="green",
        linestyle="--",
        linewidth=2,
        label="Median",
    )
    axes[0].set_xlabel("Pre-OCR Risk Score", fontsize=12)
    axes[0].set_ylabel("Frequency", fontsize=12)
    axes[0].set_title(
        "Distribution of Pre-OCR Risk Scores", fontsize=14, fontweight="bold"
    )
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    # Add statistics text
    stats = calculate_statistics(risk_scores)
    stats_text = (
        f"n={len(risk_scores)}\n"
        f"μ={stats['mean']:.3f}\n"
        f"σ={stats['std']:.3f}\n"
        f"median={stats['median']:.3f}"
    )
    axes[0].text(
        0.95,
        0.95,
        stats_text,
        transform=axes[0].transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )

    # Plot 2: OCR accuracy overlay (if available)
    if ocr_accuracy:
        axes[1].scatter(risk_scores, ocr_accuracy, alpha=0.6, color="darkgreen", s=50)
        axes[1].set_xlabel("Pre-OCR Risk Score", fontsize=12)
        axes[1].set_ylabel("OCR Accuracy", fontsize=12)
        axes[1].set_title(
            "Pre-OCR Risk vs. OCR Accuracy", fontsize=14, fontweight="bold"
        )
        axes[1].grid(visible=True, alpha=0.3)

        # Add correlation coefficient
        if len(risk_scores) == len(ocr_accuracy):
            corr = np.corrcoef(risk_scores, ocr_accuracy)[0, 1]
            axes[1].text(
                0.05,
                0.95,
                f"Correlation: {corr:.3f}",
                transform=axes[1].transAxes,
                fontsize=10,
                verticalalignment="top",
                bbox={"boxstyle": "round", "facecolor": "lightblue", "alpha": 0.5},
            )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved risk distribution plot to {output_path}")


def plot_dqs_distribution(data: dict[str, Any], output_path: Path) -> None:
    """
    Create visualization of DQS component distributions.

    Args:
        data: Dictionary with collected scores
        output_path: Path to save the plot
    """
    degradation_scores = data["degradation_scores"]
    complexity_scores = data["complexity_scores"]

    if not degradation_scores or not complexity_scores:
        print("Warning: No DQS scores to plot")
        return

    _fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Degradation score distribution
    axes[0].hist(
        degradation_scores, bins=20, color="coral", alpha=0.7, edgecolor="black"
    )
    axes[0].axvline(
        np.mean(degradation_scores),
        color="red",
        linestyle="--",
        linewidth=2,
        label="Mean",
    )
    axes[0].set_xlabel("Degradation Score", fontsize=12)
    axes[0].set_ylabel("Frequency", fontsize=12)
    axes[0].set_title(
        "DQS: Degradation Score Distribution", fontsize=14, fontweight="bold"
    )
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    # Add statistics
    deg_stats = calculate_statistics(degradation_scores)
    deg_text = (
        f"n={len(degradation_scores)}\n"
        f"μ={deg_stats['mean']:.3f}\n"
        f"σ={deg_stats['std']:.3f}"
    )
    axes[0].text(
        0.95,
        0.95,
        deg_text,
        transform=axes[0].transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )

    # Plot 2: Structural complexity distribution
    axes[1].hist(
        complexity_scores, bins=20, color="mediumpurple", alpha=0.7, edgecolor="black"
    )
    axes[1].axvline(
        np.mean(complexity_scores),
        color="red",
        linestyle="--",
        linewidth=2,
        label="Mean",
    )
    axes[1].set_xlabel("Structural Complexity Score", fontsize=12)
    axes[1].set_ylabel("Frequency", fontsize=12)
    axes[1].set_title(
        "DQS: Structural Complexity Distribution", fontsize=14, fontweight="bold"
    )
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    # Add statistics
    comp_stats = calculate_statistics(complexity_scores)
    comp_text = (
        f"n={len(complexity_scores)}\n"
        f"μ={comp_stats['mean']:.3f}\n"
        f"σ={comp_stats['std']:.3f}"
    )
    axes[1].text(
        0.95,
        0.95,
        comp_text,
        transform=axes[1].transAxes,
        fontsize=10,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Saved DQS distribution plot to {output_path}")


def save_statistics(data: dict[str, Any], output_path: Path) -> None:
    """
    Save statistics to JSON file.

    Args:
        data: Dictionary with collected scores
        output_path: Path to save JSON statistics
    """
    statistics = {
        "pre_ocr_risk": calculate_statistics(data["risk_scores"]),
        "degradation_score": calculate_statistics(data["degradation_scores"]),
        "structural_complexity": calculate_statistics(data["complexity_scores"]),
        "pdf_type_distribution": {
            pdf_type: data["pdf_types"].count(pdf_type)
            for pdf_type in set(data["pdf_types"])
        },
        "total_documents": len(data["doc_ids"]),
    }

    with open(output_path, "w") as f:
        json.dump(statistics, f, indent=2)

    print(f"✓ Saved statistics to {output_path}")


def main() -> None:
    """Main entry point for visualization script."""
    parser = argparse.ArgumentParser(
        description="Generate pre-OCR risk distribution visualizations"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing PDF/image files to analyze",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/validation"),
        help="Output directory for visualizations (default: docs/validation)",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=50,
        help="Maximum number of documents to process (default: 50)",
    )
    parser.add_argument(
        "--with-ocr-data",
        type=Path,
        help="Optional JSON file with OCR accuracy data for overlay",
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Input directory {args.input_dir} does not exist")
        sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Collect risk scores
    print(f"\n{'=' * 60}")
    print("Pre-OCR Risk Distribution Analysis")
    print(f"{'=' * 60}\n")

    data = collect_risk_scores(args.input_dir, args.max_documents)

    if not data["risk_scores"]:
        print("\nError: No documents were successfully processed")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"Successfully processed {len(data['risk_scores'])} documents")
    print(f"{'=' * 60}\n")

    # Load OCR accuracy data if provided
    ocr_accuracy = None
    if args.with_ocr_data:
        try:
            with open(args.with_ocr_data) as f:
                ocr_data = json.load(f)
                ocr_accuracy = ocr_data.get("accuracy_scores", [])
                print(f"✓ Loaded OCR accuracy data: {len(ocr_accuracy)} scores\n")
        except Exception as e:
            print(f"Warning: Could not load OCR data: {e}\n")

    # Generate visualizations
    print("Generating visualizations...\n")

    risk_plot_path = args.output_dir / "risk_distribution.png"
    plot_risk_distribution(data, risk_plot_path, ocr_accuracy)

    dqs_plot_path = args.output_dir / "dqs_distribution.png"
    plot_dqs_distribution(data, dqs_plot_path)

    stats_path = args.output_dir / "risk_statistics.json"
    save_statistics(data, stats_path)

    print(f"\n{'=' * 60}")
    print("Analysis Complete!")
    print(f"{'=' * 60}")
    print(f"Output directory: {args.output_dir}")
    print(f"  - {risk_plot_path.name}")
    print(f"  - {dqs_plot_path.name}")
    print(f"  - {stats_path.name}")
    print()


if __name__ == "__main__":
    main()
