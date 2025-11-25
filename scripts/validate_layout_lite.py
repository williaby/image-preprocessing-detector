#!/usr/bin/env python3
"""
Validation script for layout-lite presence flag accuracy.

Tests layout-lite coarse page attributes on a set of test images and reports F1 scores.

Usage:
    python scripts/validate_layout_lite.py <test_directory>
    python scripts/validate_layout_lite.py --help

Requirements:
    - Directory with test images/PDFs
    - Ground truth labels file: layout_labels.json

Example layout_labels.json format:
{
    "document_001.pdf": {
        "page_1": {
            "layout_type": "multi_column",
            "has_tables": true,
            "has_figures": false,
            "has_dense_math": false,
            "has_handwriting": false,
            "fuzzy_scan": false,
            "watermark": false,
            "colorful_background": false
        }
    }
}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import classification_report, f1_score

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.detection.layout_lite import LayoutLiteAnalyzer
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.utils import get_logger, setup_logging

logger = get_logger(__name__)


def load_ground_truth(labels_file: Path) -> dict[str, Any]:
    """
    Load ground truth layout labels from JSON file.

    Args:
        labels_file: Path to layout_labels.json file

    Returns:
        Dictionary mapping document/page to layout attributes
    """
    with open(labels_file, encoding="utf-8") as f:
        return json.load(f)


def analyze_layout_lite(
    pdf_path: Path, analyzer: LayoutLiteAnalyzer
) -> dict[str, Any]:
    """
    Analyze layout-lite attributes for a PDF.

    Args:
        pdf_path: Path to PDF file
        analyzer: LayoutLiteAnalyzer instance

    Returns:
        Dictionary of per-page layout attributes
    """
    try:
        pages = load_pdf(str(pdf_path))
        results = {}

        for page_idx, page_data in enumerate(pages):
            page_key = f"page_{page_idx + 1}"
            # Call analyze() which returns dict of detection results
            detection_results = analyzer.analyze(page_data.image)

            # Extract boolean flags from detection result objects
            results[page_key] = {
                "has_tables": detection_results.get("table").has_tables if detection_results.get("table") else False,
                "has_figures": detection_results.get("figure").has_figures if detection_results.get("figure") else False,
                "has_dense_math": False,  # Not implemented yet (Phase 6)
                "has_handwriting": False,  # Not implemented yet (Phase 6)
                "fuzzy_scan": detection_results.get("fuzzy_scan").fuzzy_scan if detection_results.get("fuzzy_scan") else False,
                "watermark": detection_results.get("watermark").watermark if detection_results.get("watermark") else False,
                "colorful_background": detection_results.get("colorful_background").colorful_background if detection_results.get("colorful_background") else False,
            }

        return results

    except Exception as e:  # noqa: BLE001
        logger.error("Failed to analyze layout-lite", path=str(pdf_path), error=str(e))
        return {}


def calculate_presence_flag_metrics(
    y_true: list[bool], y_pred: list[bool], flag_name: str
) -> dict[str, float]:
    """
    Calculate precision, recall, F1 for a single presence flag.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        flag_name: Name of the flag (for logging)

    Returns:
        Dictionary with precision, recall, F1 scores
    """
    if len(y_true) == 0:
        logger.warning("No samples for flag", flag=flag_name)
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # sklearn requires at least one positive and one negative sample
    if len(set(y_true)) < 2:
        logger.warning(
            "All samples have same label",
            flag=flag_name,
            label=y_true[0],
        )
        # If predictions match ground truth, perfect score
        if all(pred == y_true[0] for pred in y_pred):
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
        else:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # Calculate F1 score
    f1 = f1_score(y_true, y_pred, average="binary", zero_division=0.0)

    # Get detailed report
    report = classification_report(
        y_true, y_pred, output_dict=True, zero_division=0.0
    )

    # Extract true class metrics (label=True)
    true_class = report.get("True", {})

    return {
        "precision": true_class.get("precision", 0.0),
        "recall": true_class.get("recall", 0.0),
        "f1": f1,
    }


def validate_layout_lite(
    test_dir: Path, labels_file: Path, output_file: Path | None = None
) -> dict[str, Any]:
    """
    Run layout-lite validation on test dataset.

    Args:
        test_dir: Directory containing test PDFs
        labels_file: Path to ground truth labels JSON
        output_file: Optional path to save validation results

    Returns:
        Validation results dictionary
    """
    logger.info("Starting layout-lite validation", test_dir=str(test_dir))

    # Load ground truth
    ground_truth = load_ground_truth(labels_file)
    logger.info("Loaded ground truth labels", num_documents=len(ground_truth))

    # Initialize analyzer
    analyzer = LayoutLiteAnalyzer()

    # Collect predictions and ground truth per flag
    flag_names = [
        "has_tables",
        "has_figures",
        "has_dense_math",
        "has_handwriting",
        "fuzzy_scan",
        "watermark",
        "colorful_background",
    ]

    flag_data = {flag: {"y_true": [], "y_pred": []} for flag in flag_names}

    # Process each document
    for doc_name, doc_labels in ground_truth.items():
        pdf_path = test_dir / doc_name

        if not pdf_path.exists():
            logger.warning("Test file not found", path=str(pdf_path))
            continue

        logger.info("Processing document", document=doc_name)

        # Analyze document
        predictions = analyze_layout_lite(pdf_path, analyzer)

        # Collect per-page flags
        for page_key, page_labels in doc_labels.items():
            if page_key not in predictions:
                logger.warning(
                    "Missing predictions for page",
                    document=doc_name,
                    page=page_key,
                )
                continue

            page_preds = predictions[page_key]

            for flag_name in flag_names:
                gt_value = page_labels.get(flag_name, False)
                pred_value = page_preds.get(flag_name, False)

                flag_data[flag_name]["y_true"].append(gt_value)
                flag_data[flag_name]["y_pred"].append(pred_value)

    # Calculate metrics per flag
    results = {
        "num_documents": len(ground_truth),
        "num_pages": len(flag_data["has_tables"]["y_true"]),
        "target_f1": 0.85,
        "flags": {},
    }

    for flag_name in flag_names:
        y_true = flag_data[flag_name]["y_true"]
        y_pred = flag_data[flag_name]["y_pred"]

        metrics = calculate_presence_flag_metrics(y_true, y_pred, flag_name)

        results["flags"][flag_name] = {
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "target_met": metrics["f1"] >= 0.85,
            "num_samples": len(y_true),
            "num_positive": sum(y_true),
        }

        logger.info(
            "Flag metrics",
            flag=flag_name,
            f1=f"{metrics['f1']:.3f}",
            precision=f"{metrics['precision']:.3f}",
            recall=f"{metrics['recall']:.3f}",
            target_met=metrics["f1"] >= 0.85,
        )

    # Overall metrics
    all_f1_scores = [
        metrics["f1"] for metrics in results["flags"].values() if metrics["f1"] > 0
    ]
    results["mean_f1"] = float(np.mean(all_f1_scores)) if all_f1_scores else 0.0
    results["all_targets_met"] = all(
        flag_data["target_met"] for flag_data in results["flags"].values()
    )

    # Save results
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info("Saved validation results", output=str(output_file))

    return results


def main() -> int:
    """Run layout-lite validation from command line."""
    parser = argparse.ArgumentParser(
        description="Validate layout-lite presence flag accuracy"
    )
    parser.add_argument(
        "test_dir",
        type=Path,
        help="Directory containing test PDFs",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help="Path to ground truth labels JSON (default: test_dir/layout_labels.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/validation/layout_lite_validation.json"),
        help="Output path for validation results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level="DEBUG" if args.verbose else "INFO", json_logs=False)

    # Determine labels file
    labels_file = args.labels or (args.test_dir / "layout_labels.json")

    if not labels_file.exists():
        logger.error("Labels file not found", path=str(labels_file))
        print(f"ERROR: Labels file not found: {labels_file}")  # noqa: T201
        return 1

    # Run validation
    try:
        results = validate_layout_lite(args.test_dir, labels_file, args.output)

        # Print summary
        print("\n" + "=" * 70)  # noqa: T201
        print("Layout-Lite Validation Results")  # noqa: T201
        print("=" * 70)  # noqa: T201
        print(f"Documents: {results['num_documents']}")  # noqa: T201
        print(f"Pages: {results['num_pages']}")  # noqa: T201
        print(f"Mean F1: {results['mean_f1']:.3f}")  # noqa: T201
        print(f"Target (F1 > 0.85): {'✅ MET' if results['all_targets_met'] else '❌ MISSED'}")  # noqa: T201, E501
        print("\nPer-Flag Results:")  # noqa: T201

        for flag_name, flag_metrics in results["flags"].items():
            status = "✅" if flag_metrics["target_met"] else "❌"
            print(  # noqa: T201
                f"  {status} {flag_name:25s}  F1={flag_metrics['f1']:.3f}  "
                f"P={flag_metrics['precision']:.3f}  R={flag_metrics['recall']:.3f}"
            )

        print("=" * 70)  # noqa: T201

        return 0 if results["all_targets_met"] else 1

    except Exception as e:  # noqa: BLE001
        logger.error("Validation failed", error=str(e))
        print(f"ERROR: Validation failed: {e}")  # noqa: T201
        return 1


if __name__ == "__main__":
    sys.exit(main())
