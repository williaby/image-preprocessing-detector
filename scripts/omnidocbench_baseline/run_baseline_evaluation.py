#!/usr/bin/env python3
"""
OmniDocBench Baseline Evaluation Runner for Project A.

Evaluates Project A's layout-lite detectors against OmniDocBench ground truth.
This establishes baseline performance metrics before any training.

Evaluation scope (Project A only):
- Page attributes: fuzzy_scan, watermark, colorful_background
- Layout classification: single_column, multi_column, three_column, complex
- Element presence: has_tables, has_figures, has_dense_math

NOT evaluated (Project B scope):
- OCR/text recognition (NED, BLEU)
- Table structure (TEDS)
- Formula recognition (CDM)
- Reading order

Usage:
    # Run evaluation with HuggingFace dataset
    python scripts/omnidocbench_baseline/run_baseline_evaluation.py

    # Run with local ground truth
    python scripts/omnidocbench_baseline/run_baseline_evaluation.py \\
        --ground-truth data/omnidocbench_baseline/layout_labels.json \\
        --images data/omnidocbench_baseline/images/

    # Limit evaluation (for testing)
    python scripts/omnidocbench_baseline/run_baseline_evaluation.py --limit 100
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_ground_truth(path: Path) -> dict[str, Any]:
    """Load ground truth labels from JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_image_from_dataset(dataset: Any, idx: int) -> np.ndarray | None:
    """Load image from HuggingFace dataset record.

    Args:
        dataset: HuggingFace dataset
        idx: Record index

    Returns:
        Image as numpy array (BGR format) or None if failed
    """
    try:
        import cv2
        from PIL import Image

        record = dataset[idx]

        # OmniDocBench stores images in 'image' field as PIL Image
        if "image" in record and record["image"] is not None:
            pil_image = record["image"]
            if isinstance(pil_image, Image.Image):
                # Convert PIL to OpenCV BGR format
                rgb_array = np.array(pil_image)
                if len(rgb_array.shape) == 2:
                    # Grayscale
                    return cv2.cvtColor(rgb_array, cv2.COLOR_GRAY2BGR)
                if rgb_array.shape[2] == 4:
                    # RGBA
                    return cv2.cvtColor(rgb_array, cv2.COLOR_RGBA2BGR)
                # RGB
                return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

        # Fallback: try to load from image_path
        page_info = record.get("page_info", {})
        image_path = page_info.get("image_path", "")
        if image_path:
            img = cv2.imread(image_path)
            if img is not None:
                return img

        return None

    except Exception as e:
        logger.warning(f"Failed to load image at index {idx}: {e}")
        return None


def load_image_from_path(image_path: Path) -> np.ndarray | None:
    """Load image from file path.

    Args:
        image_path: Path to image file

    Returns:
        Image as numpy array (BGR format) or None if failed
    """
    try:
        import cv2

        img = cv2.imread(str(image_path))
        return img
    except Exception as e:
        logger.warning(f"Failed to load image {image_path}: {e}")
        return None


def run_layout_lite_detection(image: np.ndarray) -> dict[str, Any]:
    """Run Project A layout-lite detection on image.

    Args:
        image: Input image (BGR format)

    Returns:
        Dict with detection results
    """
    from image_preprocessing_detector.detection.layout_lite import LayoutLiteAnalyzer

    analyzer = LayoutLiteAnalyzer()
    results = analyzer.analyze(image)

    # Extract boolean flags from detection result objects
    predictions = {
        "has_tables": results.get("table").has_tables
        if results.get("table")
        else False,
        "has_figures": results.get("figure").has_figures
        if results.get("figure")
        else False,
        "has_dense_math": False,  # Not implemented in layout-lite (Phase 6)
        "has_handwriting": False,  # Not implemented in layout-lite (Phase 6)
        "fuzzy_scan": results.get("fuzzy_scan").fuzzy_scan
        if results.get("fuzzy_scan")
        else False,
        "watermark": results.get("watermark").watermark
        if results.get("watermark")
        else False,
        "colorful_background": results.get("colorful_background").colorful_background
        if results.get("colorful_background")
        else False,
    }

    # Extract layout type from column detection
    column_result = results.get("column")
    if column_result:
        col_type = column_result.column_type
        # Map column detection to layout type
        if col_type == "single":
            predictions["layout_type"] = "single_column"
        elif col_type == "double":
            predictions["layout_type"] = "multi_column"
        elif col_type == "triple":
            predictions["layout_type"] = "three_column"
        else:
            predictions["layout_type"] = "complex"
    else:
        predictions["layout_type"] = "unknown"

    return predictions


def calculate_binary_metrics(
    y_true: list[bool], y_pred: list[bool]
) -> dict[str, float]:
    """Calculate precision, recall, F1 for binary classification.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels

    Returns:
        Dict with precision, recall, f1, support
    """
    if len(y_true) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}

    tp = sum(1 for gt, pred in zip(y_true, y_pred) if gt and pred)
    fp = sum(1 for gt, pred in zip(y_true, y_pred) if not gt and pred)
    fn = sum(1 for gt, pred in zip(y_true, y_pred) if gt and not pred)
    tn = sum(1 for gt, pred in zip(y_true, y_pred) if not gt and not pred)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": sum(y_true),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def calculate_multiclass_metrics(
    y_true: list[str], y_pred: list[str], classes: list[str]
) -> dict[str, Any]:
    """Calculate metrics for multiclass classification.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        classes: List of class names

    Returns:
        Dict with per-class and macro metrics
    """
    from sklearn.metrics import classification_report, confusion_matrix

    # Filter to valid classes
    valid_mask = [
        (gt in classes and pred in classes) for gt, pred in zip(y_true, y_pred)
    ]
    y_true_valid = [y_true[i] for i in range(len(y_true)) if valid_mask[i]]
    y_pred_valid = [y_pred[i] for i in range(len(y_pred)) if valid_mask[i]]

    if len(y_true_valid) == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}}

    # Calculate accuracy
    accuracy = sum(
        1 for gt, pred in zip(y_true_valid, y_pred_valid) if gt == pred
    ) / len(y_true_valid)

    # Get sklearn report
    report = classification_report(
        y_true_valid,
        y_pred_valid,
        labels=classes,
        output_dict=True,
        zero_division=0.0,
    )

    # Build confusion matrix
    cm = confusion_matrix(y_true_valid, y_pred_valid, labels=classes)

    return {
        "accuracy": accuracy,
        "macro_f1": report.get("macro avg", {}).get("f1-score", 0.0),
        "weighted_f1": report.get("weighted avg", {}).get("f1-score", 0.0),
        "per_class": {
            cls: {
                "precision": report.get(cls, {}).get("precision", 0.0),
                "recall": report.get(cls, {}).get("recall", 0.0),
                "f1": report.get(cls, {}).get("f1-score", 0.0),
                "support": report.get(cls, {}).get("support", 0),
            }
            for cls in classes
        },
        "confusion_matrix": cm.tolist(),
        "class_labels": classes,
    }


def evaluate_from_huggingface(
    token: str | None = None,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Run evaluation directly from HuggingFace dataset.

    Args:
        token: HuggingFace API token
        limit: Maximum samples to evaluate
        output_dir: Directory to save results

    Returns:
        Evaluation results dict
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets library required. Install with: pip install datasets")
        sys.exit(1)

    logger.info("Loading OmniDocBench from HuggingFace...")
    token = token or os.getenv("HF_TOKEN")

    dataset = load_dataset(
        "opendatalab/OmniDocBench",
        token=token,
        trust_remote_code=True,
    )

    # Get train split
    data = dataset["train"]
    total = len(data)
    if limit:
        total = min(total, limit)

    logger.info(f"Evaluating {total} samples...")

    # Collect predictions and ground truth
    binary_flags = [
        "has_tables",
        "has_figures",
        "fuzzy_scan",
        "watermark",
        "colorful_background",
    ]
    collections: dict[str, dict[str, list]] = {
        flag: {"y_true": [], "y_pred": []} for flag in binary_flags
    }
    layout_true: list[str] = []
    layout_pred: list[str] = []

    # Processing stats
    processed = 0
    errors = 0
    start_time = time.time()

    for idx in range(total):
        if idx % 50 == 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            logger.info(f"Processing {idx}/{total} ({rate:.1f} samples/sec)...")

        try:
            # Load image
            image = load_image_from_dataset(data, idx)
            if image is None:
                errors += 1
                continue

            # Get ground truth from record
            record = data[idx]
            gt = extract_ground_truth_from_record(record)

            # Run detection
            pred = run_layout_lite_detection(image)

            # Collect results
            for flag in binary_flags:
                collections[flag]["y_true"].append(gt.get(flag, False))
                collections[flag]["y_pred"].append(pred.get(flag, False))

            layout_true.append(gt.get("layout_type", "unknown"))
            layout_pred.append(pred.get("layout_type", "unknown"))

            processed += 1

        except Exception as e:
            logger.warning(f"Error processing sample {idx}: {e}")
            errors += 1

    # Calculate metrics
    results = calculate_all_metrics(
        collections, layout_true, layout_pred, processed, errors, start_time
    )

    # Save results
    if output_dir:
        save_evaluation_results(results, output_dir)

    return results


def extract_ground_truth_from_record(record: dict[str, Any]) -> dict[str, Any]:
    """Extract ground truth from OmniDocBench record.

    This mirrors the logic in extract_ground_truth.py but operates on
    a single record for online evaluation.

    Args:
        record: OmniDocBench dataset record

    Returns:
        Dict with ground truth attributes
    """
    page_info = record.get("page_info", {})
    layout_dets = record.get("layout_dets", [])

    # Page attributes (note the typo in OmniDocBench)
    page_attr = page_info.get("page_attribute", {})

    # Layout mapping
    LAYOUT_TYPE_MAPPING = {
        "single_column": "single_column",
        "double_column": "multi_column",
        "three_column": "three_column",
        "1andmore_column": "complex",
        "other_layout": "complex",
    }
    omni_layout = page_attr.get("layout", "other_layout")
    layout_type = LAYOUT_TYPE_MAPPING.get(omni_layout, "unknown")

    # Element presence
    TABLE_CATEGORIES = {"table"}
    FIGURE_CATEGORIES = {"figure", "figure_caption"}
    FORMULA_CATEGORIES = {"equation_isolated", "equation_caption"}
    DENSE_MATH_THRESHOLD = 3

    categories = [det.get("category_type", "") for det in layout_dets if det]
    table_count = sum(1 for c in categories if c in TABLE_CATEGORIES)
    figure_count = sum(1 for c in categories if c in FIGURE_CATEGORIES)
    formula_count = sum(1 for c in categories if c in FORMULA_CATEGORIES)

    return {
        "layout_type": layout_type,
        "has_tables": table_count > 0,
        "has_figures": figure_count > 0,
        "has_dense_math": formula_count >= DENSE_MATH_THRESHOLD,
        "fuzzy_scan": page_attr.get("fuzzy_scan", False),
        "watermark": page_attr.get("watermark", False),
        "colorful_background": page_attr.get("colorful_backgroud", False),
    }


def calculate_all_metrics(
    collections: dict[str, dict[str, list]],
    layout_true: list[str],
    layout_pred: list[str],
    processed: int,
    errors: int,
    start_time: float,
) -> dict[str, Any]:
    """Calculate all evaluation metrics.

    Args:
        collections: Binary flag collections
        layout_true: Layout ground truth
        layout_pred: Layout predictions
        processed: Number of processed samples
        errors: Number of errors
        start_time: Evaluation start time

    Returns:
        Complete results dict
    """
    elapsed = time.time() - start_time

    results: dict[str, Any] = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_samples": processed + errors,
            "processed": processed,
            "errors": errors,
            "elapsed_seconds": elapsed,
            "samples_per_second": processed / elapsed if elapsed > 0 else 0,
        },
        "binary_flags": {},
        "layout_classification": {},
        "summary": {},
    }

    # Binary flag metrics
    f1_scores = []
    for flag, data in collections.items():
        metrics = calculate_binary_metrics(data["y_true"], data["y_pred"])
        results["binary_flags"][flag] = metrics
        if metrics["support"] > 0:  # Only include flags with positive samples
            f1_scores.append(metrics["f1"])

    # Layout classification metrics
    layout_classes = ["single_column", "multi_column", "three_column", "complex"]
    layout_metrics = calculate_multiclass_metrics(
        layout_true, layout_pred, layout_classes
    )
    results["layout_classification"] = layout_metrics

    # Summary metrics
    results["summary"] = {
        "mean_binary_f1": np.mean(f1_scores) if f1_scores else 0.0,
        "layout_accuracy": layout_metrics["accuracy"],
        "layout_macro_f1": layout_metrics["macro_f1"],
        # Project A targets
        "targets": {
            "binary_f1_target": 0.85,
            "layout_accuracy_target": 0.80,
        },
        "target_met": {
            flag: results["binary_flags"][flag]["f1"] >= 0.85
            for flag in collections.keys()
        },
    }

    return results


def save_evaluation_results(results: dict[str, Any], output_dir: Path) -> None:
    """Save evaluation results to files.

    Args:
        results: Evaluation results dict
        output_dir: Output directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full results JSON
    results_path = output_dir / "baseline_evaluation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved results to: {results_path}")

    # Save summary report
    report_path = output_dir / "baseline_evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(results))
    logger.info(f"Saved report to: {report_path}")


def generate_markdown_report(results: dict[str, Any]) -> str:
    """Generate markdown evaluation report.

    Args:
        results: Evaluation results dict

    Returns:
        Markdown formatted report
    """
    lines = [
        "# OmniDocBench Baseline Evaluation Report",
        "",
        "## Project A Scope Evaluation",
        "",
        f"**Evaluation Date**: {results['metadata']['timestamp']}",
        f"**Samples Processed**: {results['metadata']['processed']}",
        f"**Processing Time**: {results['metadata']['elapsed_seconds']:.1f}s",
        f"**Throughput**: {results['metadata']['samples_per_second']:.1f} samples/sec",
        "",
        "---",
        "",
        "## Binary Flag Detection (Page Attributes)",
        "",
        "| Flag | Precision | Recall | F1 | Support | Target Met |",
        "|------|-----------|--------|-----|---------|------------|",
    ]

    for flag, metrics in results["binary_flags"].items():
        target_met = "✅" if metrics["f1"] >= 0.85 else "❌"
        lines.append(
            f"| {flag} | {metrics['precision']:.3f} | {metrics['recall']:.3f} | "
            f"{metrics['f1']:.3f} | {metrics['support']} | {target_met} |"
        )

    lines.extend(
        [
            "",
            f"**Mean F1**: {results['summary']['mean_binary_f1']:.3f}",
            "",
            "---",
            "",
            "## Layout Classification",
            "",
            f"**Accuracy**: {results['layout_classification']['accuracy']:.3f}",
            f"**Macro F1**: {results['layout_classification']['macro_f1']:.3f}",
            "",
            "### Per-Class Performance",
            "",
            "| Layout Type | Precision | Recall | F1 | Support |",
            "|-------------|-----------|--------|-----|---------|",
        ]
    )

    for cls, metrics in results["layout_classification"]["per_class"].items():
        lines.append(
            f"| {cls} | {metrics['precision']:.3f} | {metrics['recall']:.3f} | "
            f"{metrics['f1']:.3f} | {metrics['support']} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Evaluation Scope",
            "",
            "### In Scope (Project A)",
            "- Page attributes: fuzzy_scan, watermark, colorful_background",
            "- Layout classification: single/multi/three-column, complex",
            "- Element presence: has_tables, has_figures",
            "",
            "### Out of Scope (Project B)",
            "- Text/OCR recognition (NED, BLEU, METEOR)",
            "- Table structure extraction (TEDS)",
            "- Formula recognition (CDM)",
            "- Reading order",
            "",
            "---",
            "",
            "*Generated by Project A OmniDocBench Baseline Evaluation*",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run OmniDocBench baseline evaluation for Project A",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help="Path to ground truth JSON (if using pre-extracted labels)",
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=None,
        help="Path to images directory (if using pre-extracted)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmarks/omnidocbench_baseline"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of samples to evaluate (for testing)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="HuggingFace API token",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("OmniDocBench Baseline Evaluation")
    print("Project A - Image Preprocessing Detector")
    print("=" * 70 + "\n")

    # Run evaluation
    results = evaluate_from_huggingface(
        token=args.token,
        limit=args.limit,
        output_dir=args.output,
    )

    # Print summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"\nSamples: {results['metadata']['processed']}")
    print(f"Time: {results['metadata']['elapsed_seconds']:.1f}s")
    print("\nBinary Flag Detection (F1 scores):")

    for flag, metrics in results["binary_flags"].items():
        status = "✅" if metrics["f1"] >= 0.85 else "❌"
        print(f"  {status} {flag:25s}: {metrics['f1']:.3f}")

    print("\nLayout Classification:")
    print(f"  Accuracy: {results['layout_classification']['accuracy']:.3f}")
    print(f"  Macro F1: {results['layout_classification']['macro_f1']:.3f}")

    print(f"\nMean Binary F1: {results['summary']['mean_binary_f1']:.3f}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
