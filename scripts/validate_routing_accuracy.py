#!/usr/bin/env python3
"""
Routing Accuracy Validation Script (Sprint 2.7.4)

Validates routing recommendation engine accuracy against manually labeled test set.
Target: >85% accuracy vs human expert labels.

Usage:
    PYTHONPATH=. poetry run python scripts/validate_routing_accuracy.py

Requirements:
    - Manually labeled test set (50+ documents) with ground truth OCR routing
    - Test documents with diverse characteristics (pdf_type, quality, layout)
    - DocumentMetadata JSON files or CSV with document attributes

TODO (Sprint 2.7.4):
    - [ ] Create labeled test set (50 documents)
    - [ ] Manual labeling: assign optimal OCR routing for each document
    - [ ] Run routing engine predictions on test set
    - [ ] Calculate accuracy metrics (precision, recall, F1 per routing class)
    - [ ] Generate validation report with confusion matrix
"""

from pathlib import Path

from image_preprocessing_detector.routing import recommend_ocr_routing
from image_preprocessing_detector.schema import (
    DocumentQualityScore,
    OCRRoutingRecommendation,
    PageLayoutSummary,
    PDFType,
)


class RoutingValidationResult:
    """Results from routing validation run."""

    def __init__(self):
        """Initialize validation result tracking."""
        self.total_documents = 0
        self.correct_predictions = 0
        self.predictions: list[dict] = []
        self.confusion_matrix: dict[str, dict[str, int]] = {}

    def add_prediction(
        self,
        document_id: str,
        ground_truth: OCRRoutingRecommendation,
        predicted: OCRRoutingRecommendation,
        rationale: str,
    ) -> None:
        """Record a single prediction."""
        self.total_documents += 1
        is_correct = ground_truth == predicted

        if is_correct:
            self.correct_predictions += 1

        self.predictions.append(
            {
                "document_id": document_id,
                "ground_truth": ground_truth.value,
                "predicted": predicted.value,
                "correct": is_correct,
                "rationale": rationale,
            }
        )

        # Update confusion matrix
        gt_key = ground_truth.value
        pred_key = predicted.value

        if gt_key not in self.confusion_matrix:
            self.confusion_matrix[gt_key] = {}

        if pred_key not in self.confusion_matrix[gt_key]:
            self.confusion_matrix[gt_key][pred_key] = 0

        self.confusion_matrix[gt_key][pred_key] += 1

    @property
    def accuracy(self) -> float:
        """Calculate overall accuracy."""
        if self.total_documents == 0:
            return 0.0
        return self.correct_predictions / self.total_documents

    def print_report(self) -> None:
        """Print validation report to console."""
        print("\n" + "=" * 80)
        print("ROUTING RECOMMENDATION ENGINE VALIDATION REPORT")
        print("=" * 80)
        print(f"\nTotal Documents: {self.total_documents}")
        print(f"Correct Predictions: {self.correct_predictions}")
        print(f"Accuracy: {self.accuracy:.2%}")
        print("Target Accuracy: 85.00%")
        print(f"Status: {'✓ PASS' if self.accuracy >= 0.85 else '✗ FAIL'}")

        print("\n" + "-" * 80)
        print("CONFUSION MATRIX")
        print("-" * 80)
        print(f"{'Ground Truth':<20} | {'Predicted':<20} | {'Count':<10}")
        print("-" * 80)

        for gt, predictions in sorted(self.confusion_matrix.items()):
            for pred, count in sorted(predictions.items()):
                marker = "✓" if gt == pred else "✗"
                print(f"{marker} {gt:<18} | {pred:<20} | {count:<10}")

        print("\n" + "-" * 80)
        print("MISCLASSIFICATIONS")
        print("-" * 80)

        misclassified = [p for p in self.predictions if not p["correct"]]
        if not misclassified:
            print("None - all predictions correct!")
        else:
            for pred in misclassified:
                print(f"\nDocument: {pred['document_id']}")
                print(f"  Expected: {pred['ground_truth']}")
                print(f"  Got: {pred['predicted']}")
                print(f"  Rationale: {pred['rationale']}")

        print("\n" + "=" * 80)


def load_test_set(test_set_path: Path) -> list[dict]:
    """
    Load manually labeled test set.

    TODO: Implement loader for test set format (CSV, JSON, or directory of files)

    Args:
        test_set_path: Path to test set data

    Returns:
        List of test documents with attributes and ground truth labels

    Example test document format:
        {
            "document_id": "doc-001",
            "pdf_type": "born_digital",
            "dqs": {"degradation_score": 0.92, "structural_complexity_score": 0.15},
            "pre_ocr_risk": 0.08,
            "page_layout_summary": [...],
            "ground_truth_routing": "ocr_fast"
        }
    """
    # TODO: Implement actual test set loading
    raise NotImplementedError(
        "Test set loading not yet implemented. "
        "Please create manually labeled test set first (Sprint 2.7.4)."
    )


def run_validation(test_set_path: Path) -> RoutingValidationResult:
    """
    Run routing validation on test set.

    Args:
        test_set_path: Path to manually labeled test set

    Returns:
        RoutingValidationResult with accuracy metrics
    """
    result = RoutingValidationResult()

    # Load test set
    test_documents = load_test_set(test_set_path)

    # Run routing engine on each document
    for doc in test_documents:
        # Extract attributes
        pdf_type = PDFType(doc["pdf_type"]) if doc.get("pdf_type") else None
        dqs = DocumentQualityScore(**doc["dqs"])
        pre_ocr_risk = doc["pre_ocr_risk"]
        page_layouts = [PageLayoutSummary(**p) for p in doc["page_layout_summary"]]

        # Get ground truth
        ground_truth = OCRRoutingRecommendation(doc["ground_truth_routing"])

        # Get prediction
        predicted, rationale = recommend_ocr_routing(
            pdf_type=pdf_type,
            dqs=dqs,
            pre_ocr_risk=pre_ocr_risk,
            page_layout_summary=page_layouts,
        )

        # Record result
        result.add_prediction(
            document_id=doc["document_id"],
            ground_truth=ground_truth,
            predicted=predicted,
            rationale=rationale,
        )

    return result


def main():
    """Main validation script entry point."""
    import sys

    print("Routing Recommendation Engine Validation (Sprint 2.7.4)")
    print("-" * 80)

    # Check if test set path provided
    if len(sys.argv) < 2:
        print("\nERROR: Test set path required")
        print("\nUsage:")
        print(
            "  poetry run python scripts/validate_routing_accuracy.py <test_set_path>"
        )
        print("\nExample:")
        print(
            "  poetry run python scripts/validate_routing_accuracy.py data/routing_test_set.json"
        )
        print(
            "\nNOTE: Test set must be manually created and labeled first (Sprint 2.7.4)."
        )
        sys.exit(1)

    test_set_path = Path(sys.argv[1])

    if not test_set_path.exists():
        print(f"\nERROR: Test set not found at: {test_set_path}")
        print("\nPlease create manually labeled test set first.")
        print("See Sprint 2.7.4 requirements in milestone documentation.")
        sys.exit(1)

    # Run validation
    try:
        result = run_validation(test_set_path)
        result.print_report()

        # Exit with error code if accuracy below target
        if result.accuracy < 0.85:
            print("\n⚠️  WARNING: Accuracy below 85% target!")
            sys.exit(1)
        else:
            print("\n✓ Validation successful - accuracy meets target!")
            sys.exit(0)

    except NotImplementedError as e:
        print(f"\nNOT YET IMPLEMENTED: {e}")
        print("\nTODO for Sprint 2.7.4:")
        print("  1. Create test set with 50+ diverse documents")
        print("  2. Manually label each with optimal OCR routing")
        print("  3. Implement load_test_set() function")
        print("  4. Run validation and achieve >85% accuracy")
        sys.exit(2)


if __name__ == "__main__":
    main()
