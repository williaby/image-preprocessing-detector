"""Image quality assessment metrics.

Implements metrics for evaluating:
- Blur detection and quantification
- Skew detection and correction
- Noise reduction
- Contrast enhancement
- Binarization quality

All metrics are deterministic and pure functions (no I/O).

"""

import numpy as np
from numpy.typing import NDArray
from scipy import stats
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def laplacian_variance(image: NDArray[np.uint8]) -> float:
    """Calculate Laplacian variance as blur metric.

    Higher values indicate sharper images.

    Args:
        image: Grayscale image (H x W)

    Returns:
        Laplacian variance (higher = sharper)

    Reference:
        Pech-Pacheco et al. "Diatom autofocusing in brightfield microscopy"
    """
    # Convert to float for processing
    if image.dtype != np.float64:
        image = image.astype(np.float64)

    # Laplacian kernel
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)

    # Convolve
    from scipy.ndimage import convolve

    lap = convolve(image, laplacian)

    # Return variance
    return float(np.var(lap))


def blur_correlation(
    predicted_blur: NDArray[np.float64], ground_truth_blur: NDArray[np.float64]
) -> float:
    """Calculate Pearson correlation between predicted and ground truth blur.

    Args:
        predicted_blur: Predicted blur values (N,)
        ground_truth_blur: Ground truth blur values (N,)

    Returns:
        Pearson correlation coefficient (-1 to 1)

    Target: ≥ 0.85 (FR-3.1)
    """
    if len(predicted_blur) != len(ground_truth_blur):
        raise ValueError("Arrays must have same length")

    correlation, _ = stats.pearsonr(predicted_blur, ground_truth_blur)
    return float(correlation)


def blur_rmse(
    predicted_blur: NDArray[np.float64], ground_truth_blur: NDArray[np.float64]
) -> float:
    """Calculate RMSE between predicted and ground truth blur.

    Args:
        predicted_blur: Predicted blur values (N,)
        ground_truth_blur: Ground truth blur values (N,)

    Returns:
        Root mean squared error

    Target: ≤ 0.05 (FR-3.2)
    """
    if len(predicted_blur) != len(ground_truth_blur):
        raise ValueError("Arrays must have same length")

    mse = np.mean((predicted_blur - ground_truth_blur) ** 2)
    return float(np.sqrt(mse))


def skew_mae(
    predicted_angles: NDArray[np.float64], ground_truth_angles: NDArray[np.float64]
) -> float:
    """Calculate mean absolute error for skew angle prediction.

    Args:
        predicted_angles: Predicted skew angles in degrees (N,)
        ground_truth_angles: Ground truth angles in degrees (N,)

    Returns:
        Mean absolute error in degrees

    Target: ≤ 0.5° (FR-3.3)
    """
    if len(predicted_angles) != len(ground_truth_angles):
        raise ValueError("Arrays must have same length")

    mae = np.mean(np.abs(predicted_angles - ground_truth_angles))
    return float(mae)


def deskew_success_rate(
    corrected_angles: NDArray[np.float64],
    ground_truth_angles: NDArray[np.float64],
    threshold: float = 0.5,
) -> float:
    """Calculate success rate for deskewing.

    Success = corrected angle within threshold of ground truth.

    Args:
        corrected_angles: Angles after deskewing (N,)
        ground_truth_angles: Target angles (typically 0°)
        threshold: Success threshold in degrees

    Returns:
        Success rate (0 to 1)

    Target: ≥ 0.99 (FR-3.4)
    """
    if len(corrected_angles) != len(ground_truth_angles):
        raise ValueError("Arrays must have same length")

    errors = np.abs(corrected_angles - ground_truth_angles)
    successes = np.sum(errors <= threshold)
    return float(successes / len(corrected_angles))


def snr_db(clean_image: NDArray[np.uint8], noisy_image: NDArray[np.uint8]) -> float:
    """Calculate signal-to-noise ratio in decibels.

    Args:
        clean_image: Reference clean image
        noisy_image: Noisy image

    Returns:
        SNR in dB (higher = better)

    Target: SNR improvement ≥ 6 dB (FR-3.5)
    """
    clean = clean_image.astype(np.float64)
    noisy = noisy_image.astype(np.float64)

    signal_power = np.mean(clean**2)
    noise = noisy - clean
    noise_power = np.mean(noise**2)

    if noise_power < 1e-10:  # Avoid division by zero
        return float("inf")

    snr = 10 * np.log10(signal_power / noise_power)
    return float(snr)


def snr_improvement(
    original: NDArray[np.uint8],
    denoised: NDArray[np.uint8],
    reference: NDArray[np.uint8],
) -> float:
    """Calculate SNR improvement after denoising.

    Args:
        original: Original noisy image
        denoised: Denoised image
        reference: Clean reference image

    Returns:
        SNR improvement in dB (positive = improvement)
    """
    snr_before = snr_db(reference, original)
    snr_after = snr_db(reference, denoised)
    return float(snr_after - snr_before)


def psnr(
    reference: NDArray[np.uint8],
    test: NDArray[np.uint8],
    data_range: int | None = None,
) -> float:
    """Calculate Peak Signal-to-Noise Ratio.

    Args:
        reference: Reference image
        test: Test image
        data_range: Data range (default: 255 for uint8)

    Returns:
        PSNR in dB (higher = better)

    Target: ≥ 30 dB (FR-3.6)
    """
    if data_range is None:
        data_range = 255 if reference.dtype == np.uint8 else 1

    return float(peak_signal_noise_ratio(reference, test, data_range=data_range))


def ssim(
    reference: NDArray[np.uint8],
    test: NDArray[np.uint8],
    data_range: int | None = None,
    multichannel: bool = False,
) -> float:
    """Calculate Structural Similarity Index.

    Args:
        reference: Reference image
        test: Test image
        data_range: Data range (default: 255 for uint8)
        multichannel: Whether image is multichannel (RGB)

    Returns:
        SSIM (0 to 1, higher = better)

    Target: ≥ 0.9 (FR-3.6)
    """
    if data_range is None:
        data_range = 255 if reference.dtype == np.uint8 else 1

    return float(
        structural_similarity(
            reference,
            test,
            data_range=data_range,
            channel_axis=2 if multichannel else None,
        )
    )


def binarization_metrics(
    binary_pred: NDArray[np.bool_],
    binary_true: NDArray[np.bool_],
) -> tuple[float, float, float, float]:
    """Calculate binarization quality metrics.

    Args:
        binary_pred: Predicted binary mask
        binary_true: Ground truth binary mask

    Returns:
        Tuple of (precision, recall, f_measure, ber)
        - precision: TP / (TP + FP)
        - recall: TP / (TP + FN)
        - f_measure: Harmonic mean of precision and recall
        - ber: Bit Error Rate (1 - accuracy)

    Target: F-measure ≥ 0.95 (FR-3.7)
    """
    # Flatten arrays
    pred = binary_pred.ravel()
    true = binary_true.ravel()

    # Calculate confusion matrix elements
    tp = np.sum((pred == True) & (true == True))  # noqa: E712
    fp = np.sum((pred == True) & (true == False))  # noqa: E712
    fn = np.sum((pred == False) & (true == True))  # noqa: E712
    tn = np.sum((pred == False) & (true == False))  # noqa: E712

    # Precision
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    # Recall
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # F-measure (harmonic mean)
    if precision + recall > 0:
        f_measure = 2 * (precision * recall) / (precision + recall)
    else:
        f_measure = 0.0

    # Bit Error Rate
    total = len(pred)
    correct = tp + tn
    ber = 1.0 - (correct / total)

    return (
        float(precision),
        float(recall),
        float(f_measure),
        float(ber),
    )


def contrast_enhancement_ratio(
    original: NDArray[np.uint8], enhanced: NDArray[np.uint8]
) -> float:
    """Calculate contrast enhancement ratio.

    Measures how much the dynamic range was improved.

    Args:
        original: Original image
        enhanced: Contrast-enhanced image

    Returns:
        Enhancement ratio (>1 = improvement)
    """
    # Calculate intensity ranges
    orig_std = np.std(original.astype(np.float64))
    enh_std = np.std(enhanced.astype(np.float64))

    if orig_std < 1e-6:  # Avoid division by zero
        return 1.0

    ratio = enh_std / orig_std
    return float(ratio)


def histogram_uniformity(image: NDArray[np.uint8], bins: int = 256) -> float:
    """Calculate histogram uniformity after equalization.

    Measures how uniform the intensity distribution is.

    Args:
        image: Grayscale image
        bins: Number of histogram bins

    Returns:
        Uniformity score (0 to 1, higher = more uniform)
    """
    hist, _ = np.histogram(image, bins=bins, range=(0, 255))
    hist = hist.astype(np.float64)

    # Normalize
    hist = hist / np.sum(hist)

    # Ideal uniform distribution
    uniform = np.ones_like(hist) / bins

    # Calculate distance from uniform (lower = better)
    distance = np.sum(np.abs(hist - uniform))

    # Convert to uniformity score (higher = better)
    uniformity = 1.0 - (distance / 2.0)  # Max distance is 2.0

    return float(uniformity)


def aggregate_iqa_metrics(
    metrics: dict,
) -> dict:
    """Aggregate IQA metrics into overall scores.

    Args:
        metrics: Dictionary of individual metrics

    Returns:
        Dictionary with aggregated scores and pass/fail status
    """
    # FR-3.x targets
    targets = {
        "blur_correlation": 0.85,
        "blur_rmse": 0.05,
        "skew_mae": 0.5,
        "deskew_success_rate": 0.99,
        "snr_improvement": 6.0,
        "psnr": 30.0,
        "ssim": 0.9,
        "f_measure": 0.95,
    }

    # Check which metrics pass
    results = {}
    for metric, target in targets.items():
        if metric in metrics:
            value = metrics[metric]
            # Determine pass/fail based on metric type
            if metric in ["blur_rmse", "skew_mae"]:
                passed = value <= target  # Lower is better
            else:
                passed = value >= target  # Higher is better

            results[metric] = {
                "value": value,
                "target": target,
                "passed": passed,
            }

    # Calculate overall pass rate
    total = len(results)
    passed = sum(1 for r in results.values() if r["passed"])
    pass_rate = passed / total if total > 0 else 0.0

    results["overall"] = {
        "pass_rate": pass_rate,
        "passed_count": passed,
        "total_count": total,
    }

    return results
