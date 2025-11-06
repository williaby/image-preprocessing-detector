"""
Validation framework for IQA detectors.

Tests detector accuracy against synthetic images with known ground truth.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import detect_text


@dataclass
class ValidationMetrics:
    """Metrics for a single detector."""

    detector_name: str
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    # For continuous values (angles, scores)
    mae: float | None = None  # Mean Absolute Error
    rmse: float | None = None  # Root Mean Square Error
    predictions: list[dict] = None  # Detailed predictions

    def __post_init__(self) -> None:
        """Initialize predictions list if not provided."""
        if self.predictions is None:
            self.predictions = []


class DetectorValidator:
    """
    Validates IQA detectors against synthetic test images.

    Calculates accuracy metrics and generates detailed reports.
    """

    def __init__(self, test_set: dict[str, list[tuple[Path, dict]]]):
        """
        Initialize validator with test set.

        Args:
            test_set: Dictionary mapping defect type to list of (filepath, ground_truth)
        """
        self.test_set = test_set
        self.results: dict[str, ValidationMetrics] = {}

    def validate_skew_detector(self) -> ValidationMetrics:
        """
        Validate skew detector accuracy.

        Tests both classification (has_skew) and regression (angle estimation).

        Returns:
            ValidationMetrics for skew detector
        """
        print("\nValidating Skew Detector...")

        tp = fp = tn = fn = 0
        angle_errors = []
        predictions = []

        # Test all images in test set
        all_images = []
        for images in self.test_set.values():
            all_images.extend(images)

        for filepath, ground_truth in all_images:
            # Load image
            img = cv2.imread(str(filepath))
            if img is None:
                print(f"  ⚠️  Failed to load {filepath}")
                continue

            # Run detector
            result = detect_skew(img)

            # Classification metrics (has_skew)
            gt_has_skew = ground_truth["has_skew"]
            pred_has_skew = result.is_skewed

            if gt_has_skew and pred_has_skew:
                tp += 1
            elif not gt_has_skew and pred_has_skew:
                fp += 1
            elif not gt_has_skew and not pred_has_skew:
                tn += 1
            elif gt_has_skew and not pred_has_skew:
                fn += 1

            # Regression metrics (angle estimation)
            gt_angle = ground_truth["skew_angle"]
            pred_angle = result.angle
            angle_error = abs(gt_angle - pred_angle)
            angle_errors.append(angle_error)

            predictions.append(
                {
                    "file": filepath.name,
                    "gt_has_skew": gt_has_skew,
                    "pred_has_skew": pred_has_skew,
                    "gt_angle": gt_angle,
                    "pred_angle": pred_angle,
                    "angle_error": angle_error,
                    "confidence": result.confidence,
                    "severity": result.severity.value,
                }
            )

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        mae = np.mean(angle_errors) if angle_errors else 0.0
        rmse = np.sqrt(np.mean(np.array(angle_errors) ** 2)) if angle_errors else 0.0

        metrics = ValidationMetrics(
            detector_name="Skew Detector",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            mae=mae,
            rmse=rmse,
            predictions=predictions,
        )

        print(f"  ✓ Tested {len(all_images)} images")
        print(f"  Accuracy: {accuracy:.2%}")
        print(f"  Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")
        print(f"  Angle MAE: {mae:.2f}°, RMSE: {rmse:.2f}°")

        return metrics

    def validate_blur_detector(self) -> ValidationMetrics:
        """
        Validate blur detector accuracy.

        Returns:
            ValidationMetrics for blur detector
        """
        print("\nValidating Blur Detector...")

        tp = fp = tn = fn = 0
        predictions = []

        all_images = []
        for images in self.test_set.values():
            all_images.extend(images)

        for filepath, ground_truth in all_images:
            img = cv2.imread(str(filepath))
            if img is None:
                continue

            result = detect_blur(img)

            gt_is_blurred = ground_truth["is_blurred"]
            pred_is_blurred = result.is_blurred

            if gt_is_blurred and pred_is_blurred:
                tp += 1
            elif not gt_is_blurred and pred_is_blurred:
                fp += 1
            elif not gt_is_blurred and not pred_is_blurred:
                tn += 1
            elif gt_is_blurred and not pred_is_blurred:
                fn += 1

            predictions.append(
                {
                    "file": filepath.name,
                    "gt_is_blurred": gt_is_blurred,
                    "pred_is_blurred": pred_is_blurred,
                    "blur_score": result.score,
                    "confidence": result.confidence,
                    "severity": result.severity.value,
                }
            )

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        metrics = ValidationMetrics(
            detector_name="Blur Detector",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            predictions=predictions,
        )

        print(f"  ✓ Tested {len(all_images)} images")
        print(f"  Accuracy: {accuracy:.2%}")
        print(f"  Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")

        return metrics

    def validate_contrast_detector(self) -> ValidationMetrics:
        """
        Validate contrast detector accuracy.

        Returns:
            ValidationMetrics for contrast detector
        """
        print("\nValidating Contrast Detector...")

        tp = fp = tn = fn = 0
        predictions = []

        all_images = []
        for images in self.test_set.values():
            all_images.extend(images)

        for filepath, ground_truth in all_images:
            img = cv2.imread(str(filepath))
            if img is None:
                continue

            result = detect_contrast(img)

            gt_is_low = ground_truth["is_low_contrast"]
            pred_is_low = result.is_low_contrast

            if gt_is_low and pred_is_low:
                tp += 1
            elif not gt_is_low and pred_is_low:
                fp += 1
            elif not gt_is_low and not pred_is_low:
                tn += 1
            elif gt_is_low and not pred_is_low:
                fn += 1

            predictions.append(
                {
                    "file": filepath.name,
                    "gt_is_low_contrast": gt_is_low,
                    "pred_is_low_contrast": pred_is_low,
                    "contrast_score": result.score,
                    "confidence": result.confidence,
                    "severity": result.severity.value,
                }
            )

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        metrics = ValidationMetrics(
            detector_name="Contrast Detector",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            predictions=predictions,
        )

        print(f"  ✓ Tested {len(all_images)} images")
        print(f"  Accuracy: {accuracy:.2%}")
        print(f"  Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")

        return metrics

    def validate_text_gate(self) -> ValidationMetrics:
        """
        Validate text detection gate.

        All synthetic images should have text detected.

        Returns:
            ValidationMetrics for text gate
        """
        print("\nValidating Text Detection Gate...")

        tp = fp = tn = fn = 0
        predictions = []

        all_images = []
        for images in self.test_set.values():
            all_images.extend(images)

        for filepath, _ground_truth in all_images:
            img = cv2.imread(str(filepath))
            if img is None:
                continue

            result = detect_text(img)

            # All synthetic images should have text
            gt_has_text = True  # Ground truth
            pred_has_text = result.has_text

            if gt_has_text and pred_has_text:
                tp += 1
            elif not gt_has_text and pred_has_text:
                fp += 1
            elif not gt_has_text and not pred_has_text:
                tn += 1
            elif gt_has_text and not pred_has_text:
                fn += 1

            predictions.append(
                {
                    "file": filepath.name,
                    "gt_has_text": gt_has_text,
                    "pred_has_text": pred_has_text,
                    "confidence": result.confidence,
                    "stroke_density": result.stroke_density,
                    "component_score": result.component_score,
                }
            )

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        metrics = ValidationMetrics(
            detector_name="Text Detection Gate",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            predictions=predictions,
        )

        print(f"  ✓ Tested {len(all_images)} images")
        print(f"  Accuracy: {accuracy:.2%}")
        print(f"  Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.2%}")

        return metrics

    def run_validation(self) -> dict[str, ValidationMetrics]:
        """
        Run complete validation on all detectors.

        Returns:
            Dictionary mapping detector name to ValidationMetrics
        """
        print("=" * 70)
        print("DETECTOR VALIDATION REPORT")
        print("=" * 70)

        self.results = {
            "text_gate": self.validate_text_gate(),
            "skew": self.validate_skew_detector(),
            "blur": self.validate_blur_detector(),
            "contrast": self.validate_contrast_detector(),
        }

        return self.results

    def generate_report(
        self, output_path: str | Path = "validation/report.json"
    ) -> None:
        """
        Generate detailed validation report.

        Args:
            output_path: Path to save JSON report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "test_set_summary": {
                defect: len(images) for defect, images in self.test_set.items()
            },
            "detectors": {},
        }

        for detector_name, metrics in self.results.items():
            report["detectors"][detector_name] = {
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "confusion_matrix": {
                    "true_positives": metrics.true_positives,
                    "false_positives": metrics.false_positives,
                    "true_negatives": metrics.true_negatives,
                    "false_negatives": metrics.false_negatives,
                },
                "mae": metrics.mae,
                "rmse": metrics.rmse,
                "predictions": metrics.predictions,
            }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Detailed report saved to: {output_path}")

    def print_summary(self) -> None:
        """Print summary table of validation results."""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(
            f"{'Detector':<25} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1 Score':<12}"
        )
        print("-" * 70)

        for _detector_name, metrics in self.results.items():
            print(
                f"{metrics.detector_name:<25} "
                f"{metrics.accuracy:<12.2%} "
                f"{metrics.precision:<12.2%} "
                f"{metrics.recall:<12.2%} "
                f"{metrics.f1_score:<12.2%}"
            )

            if metrics.mae is not None:
                print(f"  └─ Angle MAE: {metrics.mae:.2f}°, RMSE: {metrics.rmse:.2f}°")

        print("=" * 70)


if __name__ == "__main__":
    from validation.synthetic_generator import SyntheticImageGenerator

    # Generate test set
    print("Step 1: Generating synthetic test images...")
    generator = SyntheticImageGenerator()
    test_set = generator.generate_test_set()

    # Run validation
    print("\nStep 2: Validating detectors...")
    validator = DetectorValidator(test_set)
    results = validator.run_validation()

    # Print summary
    validator.print_summary()

    # Generate detailed report
    validator.generate_report()

    print("\n✓ Validation complete!")
