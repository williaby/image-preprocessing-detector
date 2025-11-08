"""
Generate characteristic curves for IQA detectors.

Creates gradient test sets and analyzes detector response across
full parameter ranges to enable precision threshold tuning.
"""

import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    SkewDetector,
)
from image_preprocessing_detector.detection.text_gate import TextGate
from validation.synthetic_generator import SyntheticImageGenerator


class CharacteristicCurveAnalyzer:
    """
    Analyzes detector response across parameter ranges.

    Generates characteristic curves to visualize detector behavior
    and enable data-driven threshold tuning.
    """

    def __init__(self, output_dir: str = "validation/characteristic_curves"):
        """
        Initialize characteristic curve analyzer.

        Args:
            output_dir: Directory to save plots and analysis results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize detectors
        self.blur_detector = BlurDetector()
        self.contrast_detector = ContrastDetector()
        self.skew_detector = SkewDetector()
        self.text_gate = TextGate()

    def analyze_blur_detector(self, gradient_images: list[tuple[Path, dict]]) -> dict:
        """
        Analyze blur detector response across blur gradient.

        Args:
            gradient_images: List of (image_path, ground_truth) tuples

        Returns:
            Analysis results with detector responses and thresholds
        """
        print("\nAnalyzing Blur Detector...")

        results = {
            "kernel_sizes": [],
            "laplacian_variances": [],
            "detected_as_blurred": [],
            "severity_levels": [],
        }

        for img_path, gt in gradient_images:
            image = cv2.imread(str(img_path))
            if image is None:
                continue

            kernel_size = gt["parameter_value"]

            # Run detector
            result = self.blur_detector.detect(image)

            results["kernel_sizes"].append(kernel_size)
            results["laplacian_variances"].append(result.score)
            results["detected_as_blurred"].append(result.is_blurred)
            results["severity_levels"].append(result.severity)

        # Plot characteristic curve
        self._plot_blur_curve(results)

        # Find optimal thresholds
        thresholds = self._find_blur_thresholds(results)

        return {**results, "recommended_thresholds": thresholds}

    def analyze_skew_detector(self, gradient_images: list[tuple[Path, dict]]) -> dict:
        """
        Analyze skew detector response across rotation gradient.

        Args:
            gradient_images: List of (image_path, ground_truth) tuples

        Returns:
            Analysis results with detector responses and accuracy
        """
        print("\nAnalyzing Skew Detector...")

        results = {
            "true_angles": [],
            "detected_angles": [],
            "detected_as_skewed": [],
            "angle_errors": [],
        }

        for img_path, gt in gradient_images:
            image = cv2.imread(str(img_path))
            if image is None:
                continue

            true_angle = gt["parameter_value"]

            # Run detector
            result = self.skew_detector.detect(image)

            detected_angle = result.angle
            angle_error = abs(detected_angle - true_angle)

            results["true_angles"].append(true_angle)
            results["detected_angles"].append(detected_angle)
            results["detected_as_skewed"].append(result.is_skewed)
            results["angle_errors"].append(angle_error)

        # Plot characteristic curve
        self._plot_skew_curve(results)

        # Calculate accuracy metrics
        metrics = self._calculate_skew_metrics(results)

        return {**results, "accuracy_metrics": metrics}

    def analyze_contrast_detector(
        self, gradient_images: list[tuple[Path, dict]]
    ) -> dict:
        """
        Analyze contrast detector response across contrast gradient.

        Args:
            gradient_images: List of (image_path, ground_truth) tuples

        Returns:
            Analysis results with detector responses
        """
        print("\nAnalyzing Contrast Detector...")

        results = {
            "contrast_factors": [],
            "rms_contrast": [],
            "detected_as_low": [],
            "severity_levels": [],
        }

        for img_path, gt in gradient_images:
            image = cv2.imread(str(img_path))
            if image is None:
                continue

            contrast_factor = gt["parameter_value"]

            # Run detector
            result = self.contrast_detector.detect(image)

            results["contrast_factors"].append(contrast_factor)
            results["rms_contrast"].append(result.score)
            results["detected_as_low"].append(result.is_low_contrast)
            results["severity_levels"].append(result.severity)

        # Plot characteristic curve
        self._plot_contrast_curve(results)

        # Find optimal thresholds
        thresholds = self._find_contrast_thresholds(results)

        return {**results, "recommended_thresholds": thresholds}

    def _plot_blur_curve(self, results: dict) -> None:
        """Plot blur detector characteristic curve."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Plot 1: Laplacian Variance vs. Kernel Size
        ax1.plot(
            results["kernel_sizes"],
            results["laplacian_variances"],
            marker="o",
            linewidth=2,
            label="Laplacian Variance",
        )
        ax1.axhline(y=200, color="r", linestyle="--", label="Current Threshold")
        ax1.set_xlabel("Blur Kernel Size")
        ax1.set_ylabel("Laplacian Variance")
        ax1.set_title("Blur Detector Response Curve")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_yscale("log")

        # Plot 2: Detection Rate
        detected = [1 if d else 0 for d in results["detected_as_blurred"]]
        ax2.plot(results["kernel_sizes"], detected, marker="s", linewidth=2)
        ax2.set_xlabel("Blur Kernel Size")
        ax2.set_ylabel("Detected as Blurred (0 or 1)")
        ax2.set_title("Blur Detection Rate")
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(-0.1, 1.1)

        plt.tight_layout()
        plt.savefig(self.output_dir / "blur_characteristic_curve.png", dpi=300)
        print("  ✓ Saved plot: blur_characteristic_curve.png")
        plt.close()

    def _plot_skew_curve(self, results: dict) -> None:
        """Plot skew detector characteristic curve."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Plot 1: Detected Angle vs. True Angle
        ax1.plot(
            results["true_angles"],
            results["detected_angles"],
            marker="o",
            linewidth=2,
            label="Detected Angle",
        )
        ax1.plot(
            results["true_angles"],
            results["true_angles"],
            "r--",
            label="Perfect Detection",
        )
        ax1.set_xlabel("True Skew Angle (degrees)")
        ax1.set_ylabel("Detected Skew Angle (degrees)")
        ax1.set_title("Skew Detector Accuracy")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Angle Error
        ax2.plot(
            results["true_angles"],
            results["angle_errors"],
            marker="s",
            linewidth=2,
            color="orange",
        )
        ax2.axhline(y=1.0, color="r", linestyle="--", label="1° Tolerance")
        ax2.set_xlabel("True Skew Angle (degrees)")
        ax2.set_ylabel("Absolute Angle Error (degrees)")
        ax2.set_title("Skew Detection Error")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / "skew_characteristic_curve.png", dpi=300)
        print("  ✓ Saved plot: skew_characteristic_curve.png")
        plt.close()

    def _plot_contrast_curve(self, results: dict) -> None:
        """Plot contrast detector characteristic curve."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Plot 1: RMS Contrast vs. Contrast Factor
        ax1.plot(
            results["contrast_factors"],
            results["rms_contrast"],
            marker="o",
            linewidth=2,
            label="RMS Contrast",
        )
        ax1.axhline(y=0.4, color="r", linestyle="--", label="Current Threshold")
        ax1.set_xlabel("Contrast Factor (0=worst, 1=original)")
        ax1.set_ylabel("RMS Contrast Score")
        ax1.set_title("Contrast Detector Response Curve")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Detection Rate
        detected = [1 if d else 0 for d in results["detected_as_low"]]
        ax2.plot(results["contrast_factors"], detected, marker="s", linewidth=2)
        ax2.set_xlabel("Contrast Factor (0=worst, 1=original)")
        ax2.set_ylabel("Detected as Low Contrast (0 or 1)")
        ax2.set_title("Low Contrast Detection Rate")
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(-0.1, 1.1)

        plt.tight_layout()
        plt.savefig(self.output_dir / "contrast_characteristic_curve.png", dpi=300)
        print("  ✓ Saved plot: contrast_characteristic_curve.png")
        plt.close()

    def _find_blur_thresholds(self, results: dict) -> dict:
        """
        Find optimal blur detection thresholds based on characteristic curve.

        Returns:
            Dictionary with recommended thresholds for different severity levels
        """
        variances = np.array(results["laplacian_variances"])
        kernel_sizes = np.array(results["kernel_sizes"])

        # Find variance values at key kernel sizes
        k5_idx = np.argmin(np.abs(kernel_sizes - 5))
        k15_idx = np.argmin(np.abs(kernel_sizes - 15))
        k30_idx = np.argmin(np.abs(kernel_sizes - 30))

        return {
            "critical_blur": float(variances[k30_idx]),  # Kernel ~30
            "high_blur": float(variances[k15_idx]),  # Kernel ~15
            "medium_blur": float(variances[k5_idx]),  # Kernel ~5
            "current_threshold": 200.0,
            "note": "Lower variance = more blur",
        }

    def _find_contrast_thresholds(self, results: dict) -> dict:
        """
        Find optimal contrast detection thresholds.

        Returns:
            Dictionary with recommended thresholds for different severity levels
        """
        rms_values = np.array(results["rms_contrast"])
        factors = np.array(results["contrast_factors"])

        # Find RMS values at key contrast factors
        f02_idx = np.argmin(np.abs(factors - 0.2))
        f04_idx = np.argmin(np.abs(factors - 0.4))
        f06_idx = np.argmin(np.abs(factors - 0.6))

        return {
            "critical_contrast": float(rms_values[f02_idx]),  # Factor 0.2
            "high_contrast": float(rms_values[f04_idx]),  # Factor 0.4
            "medium_contrast": float(rms_values[f06_idx]),  # Factor 0.6
            "current_threshold": 0.4,
            "note": "Lower RMS = less contrast",
        }

    def _calculate_skew_metrics(self, results: dict) -> dict:
        """Calculate accuracy metrics for skew detector."""
        errors = np.array(results["angle_errors"])
        detected = np.array(results["detected_as_skewed"])

        return {
            "mean_absolute_error": float(np.mean(errors)),
            "rmse": float(np.sqrt(np.mean(errors**2))),
            "max_error": float(np.max(errors)),
            "detection_rate": float(np.mean(detected)),
            "errors_under_1deg": float(np.mean(errors < 1.0)),
            "errors_under_2deg": float(np.mean(errors < 2.0)),
        }


def main():
    """Generate gradient sets and analyze characteristic curves."""
    print("=" * 80)
    print("CHARACTERISTIC CURVE GENERATION FOR IQA DETECTORS")
    print("=" * 80)

    # Initialize generator
    generator = SyntheticImageGenerator(
        output_dir="validation/synthetic_images/gradients"
    )

    # Generate gradient sets
    print("\n[1/4] Generating Gradient Test Sets...\n")

    blur_gradients = generator.generate_gradient_set(
        degradation_type="blur", num_samples=30, param_range=(1, 60)
    )

    skew_gradients = generator.generate_gradient_set(
        degradation_type="skew", num_samples=40, param_range=(0.0, 20.0)
    )

    contrast_gradients = generator.generate_gradient_set(
        degradation_type="contrast", num_samples=30, param_range=(0, 100)
    )

    # Initialize analyzer
    print("\n[2/4] Initializing Characteristic Curve Analyzer...\n")
    analyzer = CharacteristicCurveAnalyzer()

    # Analyze detectors
    print("[3/4] Analyzing Detector Response Curves...")

    blur_analysis = analyzer.analyze_blur_detector(blur_gradients)
    skew_analysis = analyzer.analyze_skew_detector(skew_gradients)
    contrast_analysis = analyzer.analyze_contrast_detector(contrast_gradients)

    # Save comprehensive results
    print("\n[4/4] Saving Analysis Results...\n")

    results = {
        "blur_detector": blur_analysis,
        "skew_detector": skew_analysis,
        "contrast_detector": contrast_analysis,
    }

    # Convert numpy types to Python types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer | np.floating):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    results = convert_numpy_types(results)

    results_file = analyzer.output_dir / "characteristic_curve_analysis.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"  ✓ Saved comprehensive results: {results_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    print("\nBlur Detector:")
    print(f"  Recommended Thresholds: {blur_analysis['recommended_thresholds']}")

    print("\nSkew Detector:")
    print(f"  Accuracy Metrics: {skew_analysis['accuracy_metrics']}")

    print("\nContrast Detector:")
    print(f"  Recommended Thresholds: {contrast_analysis['recommended_thresholds']}")

    print("\n✓ Characteristic curve analysis complete!")
    print(f"  - Plots saved to: {analyzer.output_dir}")
    print(f"  - Results saved to: {results_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
