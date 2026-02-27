#!/usr/bin/env python3
#

"""Weak Supervision Labeling for IQA Training Data.

Generates initial labels using image quality metrics:
- BRISQUE/NIQE/PIQE for overall quality estimation
- Laplacian variance for blur detection
- Histogram metrics for contrast analysis
- Hough transform for skew detection

Usage:
    # Label all images in a directory
    python scripts/weak_supervision_labeling.py \
        --input data/training/iqa_phase2/images \
        --output data/training/iqa_phase2/labels

    # Label with specific metrics
    python scripts/weak_supervision_labeling.py \
        --input data/training/iqa_phase2/images \
        --output data/training/iqa_phase2/labels \
        --metrics brisque laplacian histogram

    # Dry run to see what would be labeled
    python scripts/weak_supervision_labeling.py \
        --input data/training/iqa_phase2/images \
        --dry-run
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class WeakSupervisionLabeler:
    """Generates weak supervision labels using image quality metrics."""

    def __init__(
        self,
        blur_threshold: float = 200.0,
        low_contrast_threshold: float = 0.3,
        skew_threshold: float = 0.5,
    ):
        """Initialize weak supervision labeler.

        Args:
            blur_threshold: Laplacian variance threshold (< threshold = blurry)
            low_contrast_threshold: RMS contrast threshold (< threshold = low contrast)
            skew_threshold: Skew angle threshold in degrees
        """
        self.blur_threshold = blur_threshold
        self.low_contrast_threshold = low_contrast_threshold
        self.skew_threshold = skew_threshold

    def detect_blur_laplacian(self, image: np.ndarray) -> dict[str, Any]:
        """Detect blur using Laplacian variance.

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with blur detection results
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        return {
            "value": 1 if laplacian_var < self.blur_threshold else 0,
            "confidence": min(
                abs(laplacian_var - self.blur_threshold) / self.blur_threshold, 1.0
            ),
            "score": float(laplacian_var),
            "source": "laplacian_variance",
        }

    def detect_low_contrast(self, image: np.ndarray) -> dict[str, Any]:
        """Detect low contrast using RMS contrast.

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with contrast detection results
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate RMS contrast
        mean = np.mean(gray)
        rms_contrast = np.sqrt(np.mean((gray - mean) ** 2)) / 255.0

        return {
            "value": 1 if rms_contrast < self.low_contrast_threshold else 0,
            "confidence": min(
                abs(rms_contrast - self.low_contrast_threshold)
                / self.low_contrast_threshold,
                1.0,
            ),
            "score": float(rms_contrast),
            "source": "rms_contrast",
        }

    def detect_skew_hough(self, image: np.ndarray) -> dict[str, Any]:
        """Detect skew using Hough transform.

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with skew detection results
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Hough line detection
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        if lines is None:
            return {
                "value": 0,
                "confidence": 0.0,
                "score": 0.0,
                "source": "hough_lines",
            }

        # Calculate angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            angles.append(angle)

        # Median angle
        median_angle = np.median(angles)

        return {
            "value": 1 if median_angle > self.skew_threshold else 0,
            "confidence": min(median_angle / 90.0, 1.0),
            "score": float(median_angle),
            "source": "hough_lines",
        }

    def estimate_quality_brisque(self, image: np.ndarray) -> dict[str, Any]:
        """Estimate image quality using BRISQUE (if available).

        Args:
            image: Input image (BGR format)

        Returns:
            Dictionary with quality estimation results
        """
        # Note: This requires opencv-contrib-python with quality module
        # For now, return placeholder
        # TODO: Install opencv-contrib-python for full BRISQUE support

        return {
            "score": None,
            "available": False,
            "message": "BRISQUE not available - requires opencv-contrib-python",
        }

    def label_image(
        self, image_path: Path, metrics: list[str] | None = None
    ) -> dict[str, Any]:
        """Generate weak supervision labels for a single image.

        Args:
            image_path: Path to input image
            metrics: List of metrics to use (default: all)

        Returns:
            Dictionary with labels for the image
        """
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # Default to all metrics
        if metrics is None:
            metrics = ["laplacian", "histogram", "hough"]

        labels = {}

        # Blur detection
        if "laplacian" in metrics:
            labels["blur"] = self.detect_blur_laplacian(image)

        # Contrast detection
        if "histogram" in metrics:
            labels["low_contrast"] = self.detect_low_contrast(image)

        # Skew detection
        if "hough" in metrics:
            labels["skew"] = self.detect_skew_hough(image)

        # Quality estimation
        if "brisque" in metrics:
            labels["quality_brisque"] = self.estimate_quality_brisque(image)

        return {
            "image_path": str(image_path),
            "labels": labels,
            "metrics_used": metrics,
        }

    def label_dataset(
        self,
        input_dir: Path,
        output_dir: Path,
        metrics: list[str] | None = None,
        max_images: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate weak supervision labels for entire dataset.

        Args:
            input_dir: Directory containing images
            output_dir: Directory to save labels
            metrics: List of metrics to use
            max_images: Maximum number of images to label (None = all)
            dry_run: If True, don't save labels

        Returns:
            Statistics about labeling process
        """
        # Find all images
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
        image_files = [
            p for p in input_dir.rglob("*") if p.suffix.lower() in image_extensions
        ]

        if max_images:
            image_files = image_files[:max_images]

        logger.info(f"Found {len(image_files)} images to label")

        # Create output directory
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Label images
        stats = {
            "total_images": len(image_files),
            "labeled": 0,
            "errors": 0,
            "label_counts": {},
        }

        for image_path in tqdm(image_files, desc="Labeling images"):
            try:
                # Generate labels
                result = self.label_image(image_path, metrics=metrics)

                # Count labels
                for label_name, label_data in result["labels"].items():
                    if label_data.get("value") == 1:
                        stats["label_counts"][label_name] = (
                            stats["label_counts"].get(label_name, 0) + 1
                        )

                # Save labels
                if not dry_run:
                    label_file = output_dir / f"{image_path.stem}.json"
                    with open(label_file, "w") as f:
                        json.dump(result, f, indent=2)

                stats["labeled"] += 1

            except Exception as e:
                logger.error(f"Error labeling {image_path.name}: {e}")
                stats["errors"] += 1

        return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate weak supervision labels for IQA training data"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Input directory containing images"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for labels (default: input_dir/labels)",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=["laplacian", "histogram", "hough", "brisque"],
        default=None,
        help="Metrics to use (default: all except brisque)",
    )
    parser.add_argument(
        "--max-images", type=int, help="Maximum number of images to label"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't save labels, just print stats"
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=200.0,
        help="Laplacian variance threshold for blur",
    )
    parser.add_argument(
        "--contrast-threshold",
        type=float,
        default=0.3,
        help="RMS contrast threshold",
    )
    parser.add_argument(
        "--skew-threshold", type=float, default=0.5, help="Skew angle threshold"
    )

    args = parser.parse_args()

    # Set output directory
    output_dir = args.output or args.input / "labels"

    # Create labeler
    labeler = WeakSupervisionLabeler(
        blur_threshold=args.blur_threshold,
        low_contrast_threshold=args.contrast_threshold,
        skew_threshold=args.skew_threshold,
    )

    # Label dataset
    logger.info(f"Labeling images from: {args.input}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Metrics: {args.metrics or 'all (default)'}")

    stats = labeler.label_dataset(
        input_dir=args.input,
        output_dir=output_dir,
        metrics=args.metrics,
        max_images=args.max_images,
        dry_run=args.dry_run,
    )

    # Print statistics
    print("\n=== Weak Supervision Labeling Statistics ===")
    print(f"Total images: {stats['total_images']:,}")
    print(f"Successfully labeled: {stats['labeled']:,}")
    print(f"Errors: {stats['errors']:,}")

    print("\n=== Label Distribution ===")
    for label_name, count in sorted(stats["label_counts"].items()):
        percentage = (count / stats["labeled"]) * 100 if stats["labeled"] > 0 else 0
        print(f"{label_name:20s}: {count:6d} ({percentage:5.2f}%)")

    if args.dry_run:
        print("\n[DRY RUN] No labels saved.")
    else:
        print(f"\nLabels saved to: {output_dir}")


if __name__ == "__main__":
    main()
