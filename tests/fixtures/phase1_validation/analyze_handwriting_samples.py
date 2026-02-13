"""Analyze handwriting test samples using IQA detectors.

Analyzes both manual test samples (data/test) and SignaTR6K dataset samples
to characterize image quality and validate detector performance on handwritten content.
"""

import json
import random  # nosec B311 - used for non-cryptographic test data sampling
from pathlib import Path

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    SkewDetector,
)
from image_preprocessing_detector.detection.text_gate import TextGate

# Set random seed for reproducibility
random.seed(42)


def analyze_manual_samples():
    """Analyze manual handwriting samples from data/test."""
    print("=" * 80)
    print("MANUAL HANDWRITING SAMPLES ANALYSIS")
    print("=" * 80)
    print()

    # Find all test images
    test_dir = Path("data/test")
    image_files = (
        list(test_dir.glob("*.jpg"))
        + list(test_dir.glob("*.jpeg"))
        + list(test_dir.glob("*.png"))
        + list(test_dir.glob("*.avif"))
    )

    if not image_files:
        print("❌ No test images found in data/test/")
        return None

    print(f"Found {len(image_files)} test images")
    print()

    # Initialize detectors
    print("Initializing detectors...")
    text_gate = TextGate()
    blur_detector = BlurDetector()
    contrast_detector = ContrastDetector()
    skew_detector = SkewDetector()
    print()

    # Analyze each image
    results = []
    print("Analyzing images...")
    print("-" * 80)

    for img_path in sorted(image_files):
        try:
            # Load image
            image = cv2.imread(str(img_path))
            if image is None:
                print(f"  ⚠️  Failed to load {img_path.name}")
                continue

            # Run detectors
            text_result = text_gate.detect(image)
            blur_result = blur_detector.detect(image)
            contrast_result = contrast_detector.detect(image)
            skew_result = skew_detector.detect(image)

            result = {
                "filename": img_path.name,
                "image_size": f"{image.shape[1]}x{image.shape[0]}",
                "has_text": text_result.has_text,
                "text_confidence": float(text_result.confidence),
                "is_blurred": blur_result.is_blurred,
                "blur_score": float(blur_result.score),
                "blur_severity": blur_result.severity.value,
                "is_low_contrast": contrast_result.is_low_contrast,
                "contrast_score": float(contrast_result.score),
                "contrast_severity": contrast_result.severity.value,
                "is_skewed": skew_result.is_skewed,
                "skew_angle": float(skew_result.angle),
                "skew_severity": skew_result.severity.value,
            }

            results.append(result)

            print(f"  ✓ {img_path.name}")
            print(f"      Size: {result['image_size']}, Text: {result['has_text']}")
            print(
                f"      Blur: {result['blur_score']:.1f} ({result['blur_severity']}), "
                f"Contrast: {result['contrast_score']:.3f} ({result['contrast_severity']}), "
                f"Skew: {result['skew_angle']:.2f}° ({result['skew_severity']})"
            )

        except Exception as e:
            print(f"  ❌ Error processing {img_path.name}: {e}")
            continue

    print("-" * 80)
    print()

    return results


def analyze_signatr6k_samples(num_samples=50):
    """Analyze random samples from SignaTR6K dataset."""
    print("=" * 80)
    print("SIGNATR6K DATASET ANALYSIS")
    print("=" * 80)
    print()

    # Check dataset availability
    signatr6k_path = Path("data/benchmarks/signatr6k/test/crop")

    if not signatr6k_path.exists():
        print("❌ SignaTR6K dataset not found")
        print(f"   Expected: {signatr6k_path}")
        return None

    # Get all crops
    all_crops = list(signatr6k_path.glob("*.png"))
    print(f"Found {len(all_crops)} crop images in SignaTR6K test set")

    # Sample random crops
    sample_size = min(num_samples, len(all_crops))
    sample_crops = random.sample(all_crops, sample_size)
    print(f"Sampling {sample_size} random crops for analysis")
    print()

    # Initialize detectors
    print("Initializing detectors...")
    text_gate = TextGate()
    blur_detector = BlurDetector()
    contrast_detector = ContrastDetector()
    skew_detector = SkewDetector()
    print()

    # Analyze samples
    results = []
    issue_counts = {
        "has_text": 0,
        "is_blurred": 0,
        "is_low_contrast": 0,
        "is_skewed": 0,
        "total_samples": 0,
    }

    print("Processing samples...")
    print("-" * 80)

    for i, crop_path in enumerate(sample_crops, 1):
        try:
            # Load crop
            image = cv2.imread(str(crop_path))
            if image is None:
                continue

            # Run detectors
            text_result = text_gate.detect(image)
            blur_result = blur_detector.detect(image)
            contrast_result = contrast_detector.detect(image)
            skew_result = skew_detector.detect(image)

            result = {
                "filename": crop_path.name,
                "image_size": "256x256",  # SignaTR6K crops are all 256x256
                "has_text": text_result.has_text,
                "text_confidence": float(text_result.confidence),
                "is_blurred": blur_result.is_blurred,
                "blur_score": float(blur_result.score),
                "blur_severity": blur_result.severity.value,
                "is_low_contrast": contrast_result.is_low_contrast,
                "contrast_score": float(contrast_result.score),
                "contrast_severity": contrast_result.severity.value,
                "is_skewed": skew_result.is_skewed,
                "skew_angle": float(skew_result.angle),
                "skew_severity": skew_result.severity.value,
            }

            results.append(result)

            # Update counts
            issue_counts["total_samples"] += 1
            if text_result.has_text:
                issue_counts["has_text"] += 1
            if blur_result.is_blurred:
                issue_counts["is_blurred"] += 1
            if contrast_result.is_low_contrast:
                issue_counts["is_low_contrast"] += 1
            if skew_result.is_skewed:
                issue_counts["is_skewed"] += 1

            # Progress indicator
            if i % 10 == 0:
                print(
                    f"  Processed {i}/{sample_size} crops "
                    f"({issue_counts['is_blurred']} blurred, "
                    f"{issue_counts['is_low_contrast']} low contrast, "
                    f"{issue_counts['is_skewed']} skewed)"
                )

        except Exception as e:
            print(f"  ⚠️  Error processing {crop_path.name}: {e}")
            continue

    print("-" * 80)
    print()

    # Calculate statistics
    total = issue_counts["total_samples"]
    if total == 0:
        print("❌ No samples processed successfully")
        return None

    stats = {
        "sample_size": sample_size,
        "samples_processed": total,
        "text_detection_rate": issue_counts["has_text"] / total,
        "blur_detection_rate": issue_counts["is_blurred"] / total,
        "low_contrast_rate": issue_counts["is_low_contrast"] / total,
        "skew_detection_rate": issue_counts["is_skewed"] / total,
        "issue_counts": issue_counts,
    }

    return {"stats": stats, "results": results}


def main():
    """Run complete handwriting sample analysis."""
    print()

    # Analyze manual samples
    manual_results = analyze_manual_samples()

    print()
    print()

    # Analyze SignaTR6K samples
    signatr6k_data = analyze_signatr6k_samples(num_samples=50)

    # Save results
    output_file = Path("validation/handwriting_samples_analysis.json")
    output_data = {
        "manual_samples": manual_results or [],
        "signatr6k_samples": signatr6k_data or {},
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    # Print summary
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print()

    if manual_results:
        print(f"Manual Test Samples: {len(manual_results)}")
        blur_count = sum(1 for r in manual_results if r["is_blurred"])
        contrast_count = sum(1 for r in manual_results if r["is_low_contrast"])
        skew_count = sum(1 for r in manual_results if r["is_skewed"])

        print(f"  Blur Detected:     {blur_count}/{len(manual_results)}")
        print(f"  Low Contrast:      {contrast_count}/{len(manual_results)}")
        print(f"  Skew Detected:     {skew_count}/{len(manual_results)}")

        # Quality distribution
        blur_scores = [r["blur_score"] for r in manual_results]
        contrast_scores = [r["contrast_score"] for r in manual_results]
        print()
        print("  Quality Metrics:")
        print(f"    Blur (mean):     {np.mean(blur_scores):.1f}")
        print(f"    Contrast (mean): {np.mean(contrast_scores):.3f}")

    print()

    if signatr6k_data:
        stats = signatr6k_data["stats"]
        print(f"SignaTR6K Samples: {stats['samples_processed']}")
        print(f"  Text Detected:     {stats['text_detection_rate'] * 100:.1f}%")
        print(f"  Blur Detected:     {stats['blur_detection_rate'] * 100:.1f}%")
        print(f"  Low Contrast:      {stats['low_contrast_rate'] * 100:.1f}%")
        print(f"  Skew Detected:     {stats['skew_detection_rate'] * 100:.1f}%")

        # Quality distribution
        results = signatr6k_data["results"]
        blur_scores = [r["blur_score"] for r in results]
        contrast_scores = [r["contrast_score"] for r in results]
        print()
        print("  Quality Metrics:")
        print(f"    Blur (mean):     {np.mean(blur_scores):.1f}")
        print(f"    Blur (median):   {np.median(blur_scores):.1f}")
        print(f"    Contrast (mean): {np.mean(contrast_scores):.3f}")
        print(f"    Contrast (median): {np.median(contrast_scores):.3f}")

    print()
    print(f"Results saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
