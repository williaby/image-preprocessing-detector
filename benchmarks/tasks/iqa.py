"""IQA task plugin for benchmarking.

Integrates classical IQA detectors with the benchmarking framework,
connecting detection modules to metrics and scoring.

SPDX-License-Identifier: Apache-2.0
"""

from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    Severity,
    SkewDetector,
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.correction.corrections import (
    correct_skew,
    enhance_contrast,
    sharpen_image,
)


def run_blur_benchmark(adapter: Any, scorer: Any) -> None:
    """Run blur detection benchmark.

    Tests blur detection accuracy against synthetic dataset with known blur levels.

    Args:
        adapter: Dataset adapter (SyntheticIQAAdapter with subset='blur')
        scorer: AggregateScorer for collecting results
    """
    detector = BlurDetector()

    # Collect predictions and ground truth
    predicted_scores = []
    ground_truth_sigmas = []

    for sample in adapter:
        # Load image
        image = cv2.imread(str(sample.image_path))
        if image is None:
            print(f"⚠ Failed to load image: {sample.image_path}")
            continue

        # Run blur detection
        result = detector.detect(image)

        # Get ground truth
        gt = sample.metadata.get("ground_truth", {})
        gt_sigma = gt.get("blur_sigma", 0.0)

        # Store for correlation analysis
        predicted_scores.append(result.score)
        ground_truth_sigmas.append(gt_sigma)

        # Record individual sample metrics
        metrics = {
            "blur_score": result.score,
            "ground_truth_sigma": gt_sigma,
            "is_blurred": result.is_blurred,
            "confidence": result.confidence,
            "severity": result.severity.value,
        }
        scorer.add_result(sample.sample_id, metrics)

    # Calculate aggregate correlation
    if len(predicted_scores) > 1:
        from benchmarks.metrics.image_metrics import blur_correlation, blur_rmse

        # Convert scores to blur levels (invert: lower score = more blur)
        # Normalize to 0-1 range for comparison
        pred_array = np.array(predicted_scores)
        gt_array = np.array(ground_truth_sigmas)

        # Invert and normalize predicted scores to match sigma scale
        # Higher Laplacian variance = sharper = lower blur sigma
        max_score = np.max(pred_array) if np.max(pred_array) > 0 else 1.0
        pred_normalized = 5.0 * (1.0 - pred_array / max_score)  # Scale to 0-5 sigma range

        try:
            corr = blur_correlation(pred_normalized, gt_array)
            rmse = blur_rmse(pred_normalized, gt_array)

            print(f"  Blur Correlation (Pearson r): {corr:.3f}")
            print(f"  Blur RMSE: {rmse:.3f}")

            # Add aggregate metrics
            scorer.add_result("_aggregate", {
                "blur_correlation": corr,
                "blur_rmse": rmse,
            })
        except Exception as e:
            print(f"⚠ Failed to calculate correlation: {e}")


def run_skew_benchmark(adapter: Any, scorer: Any) -> None:
    """Run skew detection and correction benchmark.

    Tests skew detection accuracy and deskew correction success rate.

    Args:
        adapter: Dataset adapter (SyntheticIQAAdapter with subset='skew')
        scorer: AggregateScorer for collecting results
    """
    detector = SkewDetector()

    # Collect predictions and ground truth
    predicted_angles = []
    ground_truth_angles = []
    deskew_successes = []

    for sample in adapter:
        # Load image
        image = cv2.imread(str(sample.image_path))
        if image is None:
            print(f"⚠ Failed to load image: {sample.image_path}")
            continue

        # Run skew detection
        result = detector.detect(image)

        # Get ground truth
        gt = sample.metadata.get("ground_truth", {})
        gt_angle = gt.get("skew_angle", 0.0)

        # Store for MAE analysis
        predicted_angles.append(result.angle)
        ground_truth_angles.append(gt_angle)

        # Test deskew correction
        try:
            correction_result = correct_skew(image, result.angle, result.confidence)
            corrected = correction_result.corrected_image
            correction_metadata = correction_result.parameters

            corrected_result = detector.detect(corrected)
            corrected_angle = corrected_result.angle

            # Success if corrected angle is within 0.5° of 0
            success = abs(corrected_angle) <= 0.5
            deskew_successes.append(success)
        except Exception as e:
            print(f"⚠ Deskew failed for {sample.sample_id}: {e}")
            deskew_successes.append(False)
            corrected_angle = result.angle

        # Record individual sample metrics
        metrics = {
            "detected_angle": result.angle,
            "ground_truth_angle": gt_angle,
            "corrected_angle": corrected_angle,
            "is_skewed": result.is_skewed,
            "confidence": result.confidence,
            "severity": result.severity.value,
            "deskew_success": deskew_successes[-1],
        }
        scorer.add_result(sample.sample_id, metrics)

    # Calculate aggregate metrics
    if len(predicted_angles) > 1:
        from benchmarks.metrics.image_metrics import deskew_success_rate, skew_mae

        pred_array = np.array(predicted_angles)
        gt_array = np.array(ground_truth_angles)

        try:
            mae = skew_mae(pred_array, gt_array)
            success_rate = deskew_success_rate(
                np.array([m["corrected_angle"] for m in [scorer.results[i]["metrics"] for i in range(len(scorer.results))]]),
                np.zeros_like(pred_array),  # Target is 0° after correction
                threshold=0.5,
            )

            print(f"  Skew MAE: {mae:.3f}°")
            print(f"  Deskew Success Rate: {success_rate * 100:.1f}%")

            # Add aggregate metrics
            scorer.add_result("_aggregate", {
                "skew_mae": mae,
                "deskew_success_rate": success_rate,
            })
        except Exception as e:
            print(f"⚠ Failed to calculate skew metrics: {e}")


def run_noise_benchmark(adapter: Any, scorer: Any) -> None:
    """Run noise reduction benchmark.

    Tests denoising effectiveness using SNR, PSNR, and SSIM metrics.

    Args:
        adapter: Dataset adapter (SyntheticIQAAdapter with subset='noise')
        scorer: AggregateScorer for collecting results
    """
    from benchmarks.metrics.image_metrics import psnr, snr_improvement, ssim

    for sample in adapter:
        # Load noisy image
        noisy_image = cv2.imread(str(sample.image_path))
        if noisy_image is None:
            print(f"⚠ Failed to load image: {sample.image_path}")
            continue

        # Get ground truth (clean reference)
        gt = sample.metadata.get("ground_truth", {})
        noise_level = gt.get("noise_level", 0.0)

        # For synthetic dataset, we need to load/create the clean reference
        # In practice, this would be a paired dataset or we generate it
        # For now, we'll use a simple approach: denoise and measure improvement

        try:
            # Apply denoising (using OpenCV's fastNlMeansDenoising)
            # Note: denoise_image not yet implemented in corrections module
            if len(noisy_image.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(noisy_image, None, 10, 10, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(noisy_image, None, 10, 7, 21)
            denoise_metadata = {"method": "fastNlMeans", "h": 10}

            # Calculate metrics (using original as "clean" for demonstration)
            # In real scenario, you'd have clean reference images
            psnr_value = psnr(noisy_image, denoised)
            ssim_value = ssim(noisy_image, denoised)

            # SNR improvement estimate (simplified)
            snr_before = gt.get("snr_db", 20.0)  # From ground truth
            # Estimate improvement based on PSNR
            snr_after = snr_before + (psnr_value - 30.0)  # Rough estimate

            metrics = {
                "noise_level": noise_level,
                "psnr": psnr_value,
                "ssim": ssim_value,
                "snr_improvement": snr_after - snr_before,
            }
            scorer.add_result(sample.sample_id, metrics)

            print(f"  {sample.sample_id}: PSNR={psnr_value:.1f}, SSIM={ssim_value:.3f}")

        except Exception as e:
            print(f"⚠ Noise benchmark failed for {sample.sample_id}: {e}")


def run_contrast_benchmark(adapter: Any, scorer: Any) -> None:
    """Run contrast enhancement benchmark.

    Tests CLAHE contrast enhancement effectiveness.

    Args:
        adapter: Dataset adapter (SyntheticIQAAdapter with subset='contrast')
        scorer: AggregateScorer for collecting results
    """
    detector = ContrastDetector()

    from benchmarks.metrics.image_metrics import contrast_enhancement_ratio

    for sample in adapter:
        # Load image
        image = cv2.imread(str(sample.image_path))
        if image is None:
            print(f"⚠ Failed to load image: {sample.image_path}")
            continue

        # Run contrast detection
        result = detector.detect(image)

        # Get ground truth
        gt = sample.metadata.get("ground_truth", {})
        gt_contrast_factor = gt.get("contrast_factor", 1.0)

        try:
            # Apply contrast enhancement
            correction_result = enhance_contrast(image, result.score, result.severity)
            enhanced = correction_result.corrected_image
            enhance_metadata = correction_result.parameters

            # Calculate enhancement ratio
            enhancement_ratio = contrast_enhancement_ratio(image, enhanced)

            metrics = {
                "original_contrast_score": result.score,
                "ground_truth_factor": gt_contrast_factor,
                "enhancement_ratio": enhancement_ratio,
                "is_low_contrast": result.is_low_contrast,
                "confidence": result.confidence,
            }
            scorer.add_result(sample.sample_id, metrics)

            print(f"  {sample.sample_id}: Enhancement ratio={enhancement_ratio:.2f}")

        except Exception as e:
            print(f"⚠ Contrast benchmark failed for {sample.sample_id}: {e}")


def run_binarization_benchmark(adapter: Any, scorer: Any) -> None:
    """Run binarization quality benchmark.

    Tests binarization effectiveness using F-measure and BER.

    Args:
        adapter: Dataset adapter (SyntheticIQAAdapter with subset='binarization')
        scorer: AggregateScorer for collecting results
    """
    from benchmarks.metrics.image_metrics import binarization_metrics

    for sample in adapter:
        # Load image
        image = cv2.imread(str(sample.image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            print(f"⚠ Failed to load image: {sample.image_path}")
            continue

        # Get ground truth
        gt = sample.metadata.get("ground_truth", {})
        optimal_threshold = gt.get("optimal_threshold", 127)

        try:
            # Apply Otsu's binarization
            _, binary_pred = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Create ground truth binary (using optimal threshold)
            _, binary_true = cv2.threshold(image, optimal_threshold, 255, cv2.THRESH_BINARY)

            # Calculate metrics
            precision, recall, f_measure, ber = binarization_metrics(
                binary_pred > 127,  # Convert to boolean
                binary_true > 127,
            )

            metrics = {
                "precision": precision,
                "recall": recall,
                "f_measure": f_measure,
                "ber": ber,
                "optimal_threshold": optimal_threshold,
            }
            scorer.add_result(sample.sample_id, metrics)

            print(f"  {sample.sample_id}: F-measure={f_measure:.3f}")

        except Exception as e:
            print(f"⚠ Binarization benchmark failed for {sample.sample_id}: {e}")


def run_iqa_benchmark(adapter: Any, suite_config: Dict[str, Any], scorer: Any) -> None:
    """Main entry point for IQA benchmarking.

    Routes to specific benchmark based on suite subset.

    Args:
        adapter: Dataset adapter
        suite_config: Suite configuration from registry
        scorer: AggregateScorer for collecting results
    """
    subset = suite_config.get("subset", "blur")

    print(f"Running IQA benchmark: {subset}")
    print(f"Samples: {len(adapter)}")
    print()

    if subset == "blur":
        run_blur_benchmark(adapter, scorer)
    elif subset == "skew":
        run_skew_benchmark(adapter, scorer)
    elif subset == "noise":
        run_noise_benchmark(adapter, scorer)
    elif subset == "contrast":
        run_contrast_benchmark(adapter, scorer)
    elif subset == "binarization":
        run_binarization_benchmark(adapter, scorer)
    else:
        print(f"⚠ Unknown IQA subset: {subset}")

    print(f"\n✓ Completed {len(scorer)} samples")
