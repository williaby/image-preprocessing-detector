#!/usr/bin/env python3
"""
Validation script for PDF classification accuracy.

Tests PDF type classification on a set of sample PDFs and reports accuracy metrics.

Usage:
    python scripts/validate_pdf_classification.py <pdf_directory>
    python scripts/validate_pdf_classification.py --help

Requirements:
    - Directory with test PDFs
    - Ground truth labels file (optional): labels.json

Example labels.json format:
{
    "born_digital": ["doc1.pdf", "doc2.pdf"],
    "image_only": ["scan1.pdf", "scan2.pdf"],
    "hybrid": ["report1.pdf", "report2.pdf"]
}
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.classification import classify_pdf_type
from image_preprocessing_detector.utils import setup_logging


def load_ground_truth(labels_file: Path) -> dict[str, list[str]]:
    """
    Load ground truth labels from JSON file.

    Args:
        labels_file: Path to labels.json file

    Returns:
        Dictionary mapping PDF types to file names
    """
    with open(labels_file, encoding="utf-8") as f:
        return json.load(f)


def validate_classifications(
    pdf_dir: Path,
    labels_file: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Validate PDF classifications against ground truth.

    Args:
        pdf_dir: Directory containing test PDFs
        labels_file: Optional ground truth labels file
        verbose: Whether to print detailed results

    Returns:
        Dictionary with validation results and metrics
    """
    results = {
        "total_pdfs": 0,
        "classifications": defaultdict(int),
        "correct": 0,
        "incorrect": 0,
        "errors": [],
        "details": [],
    }

    # Load ground truth if available
    ground_truth: dict[str, list[str]] = {}
    if labels_file and labels_file.exists():
        ground_truth = load_ground_truth(labels_file)
        print(f"Loaded ground truth from {labels_file}")
    else:
        print("No ground truth file provided - running classification only")

    # Get all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return results

    print(f"\nValidating {len(pdf_files)} PDF files...")
    print("-" * 80)

    # Process each PDF
    for pdf_file in sorted(pdf_files):
        results["total_pdfs"] += 1

        try:
            # Classify PDF
            pdf_type = classify_pdf_type(pdf_file)
            results["classifications"][pdf_type.value] += 1

            # Check against ground truth if available
            is_correct = None
            expected_type = None
            if ground_truth:
                # Find expected type
                for gt_type, file_names in ground_truth.items():
                    if pdf_file.name in file_names:
                        expected_type = gt_type
                        break

                if expected_type:
                    is_correct = pdf_type.value == expected_type
                    if is_correct:
                        results["correct"] += 1
                    else:
                        results["incorrect"] += 1

            # Record details
            detail = {
                "file": pdf_file.name,
                "predicted": pdf_type.value,
                "expected": expected_type,
                "correct": is_correct,
            }
            results["details"].append(detail)

            # Print if verbose
            if verbose:
                status = ""
                if is_correct is not None:
                    status = "✓" if is_correct else "✗"
                print(
                    f"{status:2} {pdf_file.name:40} → {pdf_type.value:15} "
                    f"(expected: {expected_type or 'N/A'})"
                )

        except Exception as e:
            error_msg = f"Error processing {pdf_file.name}: {e!s}"
            results["errors"].append(error_msg)
            if verbose:
                print(f"✗  {error_msg}")

    return results


def print_summary(results: dict[str, Any]) -> None:
    """
    Print validation summary and metrics.

    Args:
        results: Validation results dictionary
    """
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    # Basic stats
    print(f"\nTotal PDFs processed: {results['total_pdfs']}")
    print("\nClassification distribution:")
    for pdf_type, count in sorted(results["classifications"].items()):
        percentage = (
            (count / results["total_pdfs"]) * 100 if results["total_pdfs"] > 0 else 0
        )
        print(f"  {pdf_type:15} : {count:3} ({percentage:5.1f}%)")

    # Accuracy metrics (if ground truth available)
    if results["correct"] > 0 or results["incorrect"] > 0:
        total_labeled = results["correct"] + results["incorrect"]
        accuracy = (
            (results["correct"] / total_labeled) * 100 if total_labeled > 0 else 0
        )

        print("\nAccuracy metrics:")
        print(f"  Correct predictions  : {results['correct']:3}")
        print(f"  Incorrect predictions: {results['incorrect']:3}")
        print(f"  Accuracy             : {accuracy:6.2f}%")

        # Check if target accuracy met
        if accuracy >= 99.0:
            print(f"\n✓ Target accuracy (>99%) ACHIEVED: {accuracy:.2f}%")
        else:
            print(f"\n✗ Target accuracy (>99%) NOT MET: {accuracy:.2f}%")

    # Errors
    if results["errors"]:
        print(f"\nErrors encountered: {len(results['errors'])}")
        for error in results["errors"]:
            print(f"  - {error}")

    print("\n" + "=" * 80)


def main() -> None:
    """Main validation script entry point."""
    parser = argparse.ArgumentParser(
        description="Validate PDF type classification accuracy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "pdf_dir",
        type=Path,
        help="Directory containing test PDFs",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        help="Ground truth labels file (JSON format)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for detailed results (JSON)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed classification results",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, json_logs=False)

    # Validate input
    if not args.pdf_dir.exists():
        print(f"Error: PDF directory not found: {args.pdf_dir}")
        sys.exit(1)

    if not args.pdf_dir.is_dir():
        print(f"Error: Not a directory: {args.pdf_dir}")
        sys.exit(1)

    # Run validation
    results = validate_classifications(
        pdf_dir=args.pdf_dir,
        labels_file=args.labels,
        verbose=args.verbose,
    )

    # Print summary
    print_summary(results)

    # Save detailed results if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {args.output}")

    # Exit with appropriate code
    if results["errors"]:
        sys.exit(1)
    elif results["incorrect"] > 0:
        # Had ground truth and some were incorrect
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
