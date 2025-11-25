"""Validate IQA detectors on DocLayNet sample.

Uses the already-downloaded DocLayNet dataset to validate detectors
on real-world business documents without requiring external downloads.
"""

import json
import random  # nosec B311 - used for non-cryptographic test data sampling
from pathlib import Path

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    SkewDetector,
)
from image_preprocessing_detector.detection.text_gate import TextGate
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf

# Set random seed for reproducibility
random.seed(42)


def main():
    """Run validation on DocLayNet sample."""
    print("=" * 80)
    print("DOCLAYNET REAL-WORLD VALIDATION")
    print("=" * 80)
    print()

    # Check DocLayNet availability
    doclaynet_path = Path(
        "/home/byron/dev/data_ingestor/data/benchmarks/doclaynet/documents/pdf"
    )

    if not doclaynet_path.exists():
        print("❌ DocLayNet dataset not found at expected location")
        print(f"   Expected: {doclaynet_path}")
        print()
        print("Please ensure DocLayNet is downloaded and available.")
        return

    # Get all PDFs
    all_pdfs = list(doclaynet_path.glob("*.pdf"))
    print(f"Found {len(all_pdfs)} PDFs in DocLayNet dataset")

    # Sample PDFs
    sample_size = min(100, len(all_pdfs))
    sample_pdfs = random.sample(all_pdfs, sample_size)
    print(f"Sampling {sample_size} random PDFs for validation")
    print()

    # Initialize detectors
    print("Initializing detectors...")
    text_gate = TextGate()
    blur_detector = BlurDetector()
    contrast_detector = ContrastDetector()
    skew_detector = SkewDetector()
    print()

    # Process samples
    results = []
    issue_counts = {
        "has_text": 0,
        "is_blurred": 0,
        "is_low_contrast": 0,
        "is_skewed": 0,
        "total_pages": 0,
    }

    print("Processing samples...")
    print("-" * 80)

    for i, pdf_path in enumerate(sample_pdfs, 1):
        try:
            # Load PDF
            pages = load_pdf(str(pdf_path))

            if not pages:
                continue

            # Use first page only for speed
            page = pages[0]
            image = page.image

            # Run text gate
            text_result = text_gate.detect(image)

            # Run IQA detectors
            blur_result = blur_detector.detect(image)
            contrast_result = contrast_detector.detect(image)
            skew_result = skew_detector.detect(image)

            # Record results
            page_result = {
                "pdf_file": pdf_path.name,
                "page_number": 1,
                "has_text": text_result.has_text,
                "text_confidence": float(text_result.confidence),
                "is_blurred": blur_result.is_blurred,
                "blur_score": float(blur_result.score),
                "blur_severity": blur_result.severity,
                "is_low_contrast": contrast_result.is_low_contrast,
                "contrast_score": float(contrast_result.score),
                "contrast_severity": contrast_result.severity,
                "is_skewed": skew_result.is_skewed,
                "skew_angle": float(skew_result.angle),
                "skew_severity": skew_result.severity,
            }

            results.append(page_result)

            # Update counts
            issue_counts["total_pages"] += 1
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
                    f"  Processed {i}/{sample_size} PDFs "
                    f"({issue_counts['is_blurred']} blurred, "
                    f"{issue_counts['is_low_contrast']} low contrast, "
                    f"{issue_counts['is_skewed']} skewed)"
                )

        except Exception as e:
            print(f"  ⚠️  Error processing {pdf_path.name}: {e}")
            continue

    print("-" * 80)
    print()

    # Calculate statistics
    total = issue_counts["total_pages"]
    if total == 0:
        print("❌ No pages processed successfully")
        return

    stats = {
        "sample_size": sample_size,
        "pages_processed": total,
        "text_detection_rate": issue_counts["has_text"] / total,
        "blur_detection_rate": issue_counts["is_blurred"] / total,
        "low_contrast_rate": issue_counts["is_low_contrast"] / total,
        "skew_detection_rate": issue_counts["is_skewed"] / total,
        "issue_counts": issue_counts,
    }

    # Save detailed results
    output_file = Path("validation/doclaynet_validation_results.json")
    with open(output_file, "w") as f:
        json.dump(
            {
                "summary": stats,
                "detailed_results": results,
            },
            f,
            indent=2,
        )

    # Print summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print(f"Total PDFs Sampled: {sample_size}")
    print(f"Pages Processed: {total}")
    print()
    print("Detection Rates:")
    print(
        f"  Text Detected:     {stats['text_detection_rate'] * 100:.1f}% ({issue_counts['has_text']}/{total})"
    )
    print(
        f"  Blur Detected:     {stats['blur_detection_rate'] * 100:.1f}% ({issue_counts['is_blurred']}/{total})"
    )
    print(
        f"  Low Contrast:      {stats['low_contrast_rate'] * 100:.1f}% ({issue_counts['is_low_contrast']}/{total})"
    )
    print(
        f"  Skew Detected:     {stats['skew_detection_rate'] * 100:.1f}% ({issue_counts['is_skewed']}/{total})"
    )
    print()
    print(f"Results saved to: {output_file}")
    print("=" * 80)

    # Quality distribution analysis
    print()
    print("QUALITY DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print()

    # Analyze blur scores
    blur_scores = [r["blur_score"] for r in results]
    print("Blur Scores (Laplacian Variance):")
    print(f"  Mean:   {np.mean(blur_scores):.2f}")
    print(f"  Median: {np.median(blur_scores):.2f}")
    print(f"  Min:    {np.min(blur_scores):.2f}")
    print(f"  Max:    {np.max(blur_scores):.2f}")
    print(f"  Std:    {np.std(blur_scores):.2f}")
    print()

    # Analyze contrast scores
    contrast_scores = [r["contrast_score"] for r in results]
    print("Contrast Scores (RMS Contrast):")
    print(f"  Mean:   {np.mean(contrast_scores):.4f}")
    print(f"  Median: {np.median(contrast_scores):.4f}")
    print(f"  Min:    {np.min(contrast_scores):.4f}")
    print(f"  Max:    {np.max(contrast_scores):.4f}")
    print(f"  Std:    {np.std(contrast_scores):.4f}")
    print()

    # Analyze skew angles
    skew_angles = [abs(r["skew_angle"]) for r in results]
    print("Skew Angles (Absolute Degrees):")
    print(f"  Mean:   {np.mean(skew_angles):.2f}°")
    print(f"  Median: {np.median(skew_angles):.2f}°")
    print(f"  Min:    {np.min(skew_angles):.2f}°")
    print(f"  Max:    {np.max(skew_angles):.2f}°")
    print(f"  Std:    {np.std(skew_angles):.2f}°")
    print()
    print("=" * 80)

    # Recommendations
    print()
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    if stats["blur_detection_rate"] > 0.2:
        print(
            "⚠️  High blur detection rate (>20%) - may indicate conservative thresholds"
        )
        print("   Consider reviewing blur threshold settings")
    else:
        print("✅ Blur detection rate within normal range")

    if stats["low_contrast_rate"] > 0.3:
        print(
            "⚠️  High low-contrast rate (>30%) - may indicate threshold adjustment needed"
        )
        print("   Review contrast threshold settings")
    else:
        print("✅ Contrast detection rate within normal range")

    if stats["skew_detection_rate"] > 0.1:
        print("⚠️  Elevated skew detection (>10%) - review skew threshold")
    else:
        print("✅ Skew detection rate within normal range")

    print()
    print("Next Steps:")
    print("  1. Review detailed results in JSON file")
    print("  2. Spot-check flagged images manually")
    print("  3. Adjust detector thresholds if needed")
    print("  4. Update VALIDATION_RESULTS.md with findings")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
