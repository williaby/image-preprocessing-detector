#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Continuous Weak Supervision Labeling for Phase 7 IQA Training.

Generates continuous quality scores [0, 1] using classical IQA detectors with:
- Adaptive label smoothing based on detector confidence
- Sample weighting from inter-detector agreement
- Normalization of raw detector outputs to [0, 1] scale

Extends Phase 3 binary labeling with continuous supervision for better calibration.

Usage:
    # Generate continuous labels for Phase 7 dataset
    python scripts/weak_supervision_labeling_continuous.py \
        --input /mnt/unraid/image_detection/benchmarks/ohr-bench \
        --output data/training/iqa_phase7_labels \
        --continuous-mode

    # Test on subset
    python scripts/weak_supervision_labeling_continuous.py \
        --input /mnt/unraid/image_detection/benchmarks/ohr-bench \
        --output data/training/iqa_phase7_labels \
        --continuous-mode \
        --max-images 1000 \
        --dry-run
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.detection.iqa_classical import (
    BinarizationQualityDetector,
    BleedThroughDetector,
    BlurDetector,
    ContrastDetector,
    IlluminationDetector,
    JPEGBlockinessDetector,
    NoiseDetector,
    SkewDetector,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass
class ContinuousScores:
    """Continuous quality scores for Phase 7 training.

    All scores in [0, 1] range where:
    - 0.0 = severe quality issue (poor)
    - 1.0 = no issue detected (good)
    """

    blur: float
    contrast: float
    skew: float
    noise: float
    illumination: float
    compression: float
    binarization: float
    bleed_through: float


@dataclass
class DetectorConfidences:
    """Confidence scores for each detector's output."""

    blur: float
    contrast: float
    skew: float
    noise: float
    illumination: float
    compression: float
    binarization: float
    bleed_through: float


class ContinuousWeakSupervisionLabeler:
    """Generates continuous weak supervision labels for Phase 7 training.

    Key improvements over Phase 3 binary labeling:
    1. Continuous scores [0, 1] instead of binary {0, 1}
    2. Adaptive label smoothing based on detector confidence
    3. Sample weighting from inter-detector agreement
    4. Proper normalization of raw detector outputs
    """

    def __init__(
        self,
        # Smoothing configuration
        high_confidence_threshold: float = 0.9,
        medium_confidence_threshold: float = 0.7,
        low_confidence_threshold: float = 0.5,
    ):
        """Initialize continuous weak supervision labeler.

        Args:
            high_confidence_threshold: Threshold for high detector confidence
            medium_confidence_threshold: Threshold for medium confidence
            low_confidence_threshold: Threshold for low confidence
        """
        # Initialize classical detectors with default thresholds
        # These are already tuned in Phase 1C
        self.skew_detector = SkewDetector()
        self.blur_detector = BlurDetector()
        self.contrast_detector = ContrastDetector()
        self.noise_detector = NoiseDetector()
        self.illumination_detector = IlluminationDetector()
        self.jpeg_detector = JPEGBlockinessDetector()
        self.binarization_detector = BinarizationQualityDetector()
        self.bleed_through_detector = BleedThroughDetector()

        # Confidence thresholds for adaptive smoothing
        self.high_conf_thresh = high_confidence_threshold
        self.medium_conf_thresh = medium_confidence_threshold
        self.low_conf_thresh = low_confidence_threshold

        logger.info(
            "Continuous weak supervision labeler initialized",
            high_conf_thresh=high_confidence_threshold,
            medium_conf_thresh=medium_confidence_threshold,
        )

    def normalize_skew_score(self, angle: float, max_angle: float = 45.0) -> float:
        """Normalize skew angle to [0, 1] continuous score.

        Args:
            angle: Detected skew angle in degrees
            max_angle: Maximum expected angle (default: 45°)

        Returns:
            Normalized score where 0=severe skew, 1=no skew
        """
        # Clamp to expected range
        abs_angle = min(abs(angle), max_angle)
        # Linear normalization: 0° → 1.0, max_angle → 0.0
        return 1.0 - (abs_angle / max_angle)

    def normalize_blur_score(
        self, laplacian_var: float, min_var: float = 10.0, max_var: float = 1000.0
    ) -> float:
        """Normalize Laplacian variance to [0, 1] continuous score.

        Args:
            laplacian_var: Laplacian variance value
            min_var: Minimum expected variance (blurry)
            max_var: Maximum expected variance (sharp)

        Returns:
            Normalized score where 0=blurry, 1=sharp
        """
        # Clamp to expected range
        clamped = np.clip(laplacian_var, min_var, max_var)
        # Linear normalization
        return (clamped - min_var) / (max_var - min_var)

    def normalize_contrast_score(
        self, rms_contrast: float, min_contrast: float = 0.01, max_contrast: float = 0.5
    ) -> float:
        """Normalize RMS contrast to [0, 1] continuous score.

        Args:
            rms_contrast: RMS contrast value
            min_contrast: Minimum expected contrast (poor)
            max_contrast: Maximum expected contrast (good)

        Returns:
            Normalized score where 0=low contrast, 1=high contrast
        """
        # Clamp to expected range
        clamped = np.clip(rms_contrast, min_contrast, max_contrast)
        # Linear normalization
        return (clamped - min_contrast) / (max_contrast - min_contrast)

    def normalize_noise_score(
        self, noise_level: float, min_noise: float = 0.0, max_noise: float = 50.0
    ) -> float:
        """Normalize noise level to [0, 1] continuous score.

        Args:
            noise_level: Estimated noise level
            min_noise: Minimum noise (clean)
            max_noise: Maximum noise (noisy)

        Returns:
            Normalized score where 0=noisy, 1=clean
        """
        # Clamp to expected range
        clamped = np.clip(noise_level, min_noise, max_noise)
        # Inverse normalization: low noise → high score
        return 1.0 - (clamped / max_noise)

    def normalize_illumination_score(
        self, uniformity: float, min_uniformity: float = 0.0, max_uniformity: float = 1.0
    ) -> float:
        """Normalize illumination uniformity to [0, 1] continuous score.

        Args:
            uniformity: Illumination uniformity metric
            min_uniformity: Minimum uniformity (poor lighting)
            max_uniformity: Maximum uniformity (even lighting)

        Returns:
            Normalized score where 0=poor lighting, 1=even lighting
        """
        # Already in [0, 1] range typically
        return np.clip(uniformity, min_uniformity, max_uniformity)

    def normalize_compression_score(
        self, blockiness: float, min_block: float = 0.0, max_block: float = 10.0
    ) -> float:
        """Normalize JPEG blockiness to [0, 1] continuous score.

        Args:
            blockiness: JPEG blockiness metric
            min_block: Minimum blockiness (no artifacts)
            max_block: Maximum blockiness (severe artifacts)

        Returns:
            Normalized score where 0=blocky, 1=no artifacts
        """
        # Clamp to expected range
        clamped = np.clip(blockiness, min_block, max_block)
        # Inverse normalization: low blockiness → high score
        return 1.0 - (clamped / max_block)

    def adaptive_smooth(self, score: float, confidence: float) -> float:
        """Apply confidence-based adaptive label smoothing.

        High confidence → preserve extremes [0.05, 0.95]
        Medium confidence → moderate smoothing [0.15, 0.85]
        Low confidence → strong smoothing [0.25, 0.75]

        Args:
            score: Normalized continuous score [0, 1]
            confidence: Detector confidence [0, 1]

        Returns:
            Smoothed score with adaptive clipping
        """
        if confidence >= self.high_conf_thresh:
            # Preserve extremes for high-confidence predictions
            return float(np.clip(score, 0.05, 0.95))
        elif confidence >= self.medium_conf_thresh:
            # Moderate smoothing for medium confidence
            return float(np.clip(score, 0.15, 0.85))
        elif confidence >= self.low_conf_thresh:
            # Strong smoothing for low confidence
            return float(np.clip(score, 0.25, 0.75))
        else:
            # Very uncertain → push toward neutral
            return float(np.clip(score, 0.35, 0.65))

    def estimate_detector_confidence(
        self, detector_name: str, metric_value: float, image: np.ndarray
    ) -> float:
        """Estimate confidence of classical detector on this sample.

        High confidence indicators:
        - Metric value far from decision boundary
        - Consistent with other detector outputs
        - High signal-to-noise ratio in image

        Args:
            detector_name: Name of detector ('blur', 'contrast', etc.)
            metric_value: Raw detector output value
            image: Input image for analysis

        Returns:
            Confidence score [0, 1]
        """
        # Base confidence from metric strength
        if detector_name == "blur":
            # Far from blur threshold → high confidence
            threshold = 200.0
            distance = abs(metric_value - threshold) / threshold
            base_conf = min(distance, 1.0)
        elif detector_name == "contrast":
            # Far from contrast threshold → high confidence
            threshold = 0.2
            distance = abs(metric_value - threshold) / threshold
            base_conf = min(distance, 1.0)
        elif detector_name == "skew":
            # Close to 0° or far from 0° → high confidence
            # Mid-range angles → lower confidence
            if abs(metric_value) < 1.0:
                base_conf = 0.9  # High confidence no skew
            elif abs(metric_value) > 10.0:
                base_conf = 0.9  # High confidence severe skew
            else:
                base_conf = 0.6  # Medium confidence
        else:
            # Default: moderate confidence
            base_conf = 0.7

        # Adjust based on image characteristics
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Check if image has structure (edges, text)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size

        # High edge density → more confident in detectors
        if edge_density > 0.1:
            structure_boost = 0.1
        elif edge_density > 0.05:
            structure_boost = 0.05
        else:
            structure_boost = 0.0

        confidence = min(base_conf + structure_boost, 1.0)
        return float(confidence)

    def compute_sample_weight(
        self, detector_scores: dict[str, float], detector_confidences: dict[str, float]
    ) -> float:
        """Compute sample weight from detector variance and confidence.

        High weight = reliable training sample:
        - High average confidence across detectors
        - Low inter-detector disagreement (variance)

        Args:
            detector_scores: Dict of {detector_name: normalized_score}
            detector_confidences: Dict of {detector_name: confidence}

        Returns:
            Sample weight [0, 1] - higher is more reliable
        """
        # Average confidence across all detectors
        mean_confidence = float(np.mean(list(detector_confidences.values())))

        # Inter-detector score variance
        score_variance = float(np.var(list(detector_scores.values())))

        # Down-weight samples with high disagreement
        # Formula: weight = mean_conf / (1 + variance)
        weight = mean_confidence / (1.0 + score_variance)

        return float(np.clip(weight, 0.1, 1.0))  # Floor at 0.1 to avoid zero weights

    def label_image(self, image_path: Path) -> dict[str, Any]:
        """Generate continuous weak supervision labels for a single image.

        Args:
            image_path: Path to input image

        Returns:
            Dictionary with continuous scores, confidences, and sample weight
        """
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # Run all classical detectors
        skew_result = self.skew_detector.detect(image)
        blur_result = self.blur_detector.detect(image)
        contrast_result = self.contrast_detector.detect(image)
        noise_result = self.noise_detector.detect(image)
        illumination_result = self.illumination_detector.detect(image)
        jpeg_result = self.jpeg_detector.detect(image)
        binarization_result = self.binarization_detector.detect(image)
        bleed_result = self.bleed_through_detector.detect(image)

        # Extract raw metric values
        raw_scores = {
            "blur": blur_result.blur_score,  # From BlurDetectionResult
            "contrast": contrast_result.score,  # From ContrastDetectionResult
            "skew": skew_result.angle,  # From SkewDetectionResult
            "noise": noise_result.noise_sigma,  # From NoiseDetectionResult
            "illumination": illumination_result.uniformity,  # From IlluminationDetectionResult
            "compression": jpeg_result.blockiness_score,  # From JPEGBlockinessResult
            "binarization": binarization_result.binarization_score,  # From BinarizationQualityResult
            "bleed_through": bleed_result.severity,  # From BleedThroughResult
        }

        # Normalize to [0, 1] continuous scores
        normalized_scores = {
            "blur": self.normalize_blur_score(raw_scores["blur"]),
            "contrast": self.normalize_contrast_score(raw_scores["contrast"]),
            "skew": self.normalize_skew_score(raw_scores["skew"]),
            "noise": self.normalize_noise_score(raw_scores["noise"]),
            "illumination": self.normalize_illumination_score(raw_scores["illumination"]),
            "compression": self.normalize_compression_score(raw_scores["compression"]),
            "binarization": raw_scores["binarization"],  # Already [0, 1]
            "bleed_through": 1.0 - raw_scores["bleed_through"],  # Invert for consistency
        }

        # Estimate detector confidences
        confidences = {
            "blur": self.estimate_detector_confidence("blur", raw_scores["blur"], image),
            "contrast": self.estimate_detector_confidence(
                "contrast", raw_scores["contrast"], image
            ),
            "skew": self.estimate_detector_confidence("skew", raw_scores["skew"], image),
            "noise": float(noise_result.confidence),
            "illumination": float(illumination_result.confidence),
            "compression": float(jpeg_result.confidence),
            "binarization": float(binarization_result.confidence),
            "bleed_through": float(bleed_result.confidence),
        }

        # Apply adaptive smoothing
        smoothed_scores = {
            detector: self.adaptive_smooth(score, confidences[detector])
            for detector, score in normalized_scores.items()
        }

        # Compute sample weight
        sample_weight = self.compute_sample_weight(normalized_scores, confidences)

        # Track smoothing ranges applied
        smoothing_applied = {}
        for detector, conf in confidences.items():
            if conf >= self.high_conf_thresh:
                smoothing_applied[detector] = [0.05, 0.95]
            elif conf >= self.medium_conf_thresh:
                smoothing_applied[detector] = [0.15, 0.85]
            elif conf >= self.low_conf_thresh:
                smoothing_applied[detector] = [0.25, 0.75]
            else:
                smoothing_applied[detector] = [0.35, 0.65]

        return {
            "image_path": str(image_path),
            "continuous_scores": smoothed_scores,
            "detector_confidences": confidences,
            "sample_weight": sample_weight,
            "smoothing_applied": smoothing_applied,
            "raw_scores": raw_scores,  # For debugging/analysis
        }

    def label_dataset(
        self,
        input_dir: Path,
        output_dir: Path,
        max_images: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Generate continuous labels for entire dataset.

        Args:
            input_dir: Directory containing images
            output_dir: Directory to save labels
            max_images: Maximum number of images to label
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

        # Statistics tracking
        stats = {
            "total_images": len(image_files),
            "labeled": 0,
            "errors": 0,
            "score_distributions": {detector: [] for detector in [
                "blur", "contrast", "skew", "noise",
                "illumination", "compression", "binarization", "bleed_through"
            ]},
            "weight_distribution": [],
            "confidence_distributions": {detector: [] for detector in [
                "blur", "contrast", "skew", "noise",
                "illumination", "compression", "binarization", "bleed_through"
            ]},
        }

        # Label images
        for image_path in tqdm(image_files, desc="Labeling images"):
            try:
                # Generate continuous labels
                result = self.label_image(image_path)

                # Track distributions
                for detector, score in result["continuous_scores"].items():
                    stats["score_distributions"][detector].append(score)

                for detector, conf in result["detector_confidences"].items():
                    stats["confidence_distributions"][detector].append(conf)

                stats["weight_distribution"].append(result["sample_weight"])

                # Save labels
                if not dry_run:
                    label_file = output_dir / f"{image_path.stem}.json"
                    with open(label_file, "w") as f:
                        json.dump(result, f, indent=2)

                stats["labeled"] += 1

            except Exception as e:
                logger.error(f"Error labeling {image_path.name}: {e}")
                stats["errors"] += 1

        # Compute distribution statistics
        stats["score_stats"] = {}
        for detector, scores in stats["score_distributions"].items():
            if scores:
                stats["score_stats"][detector] = {
                    "mean": float(np.mean(scores)),
                    "std": float(np.std(scores)),
                    "min": float(np.min(scores)),
                    "max": float(np.max(scores)),
                    "median": float(np.median(scores)),
                }

        if stats["weight_distribution"]:
            stats["weight_stats"] = {
                "mean": float(np.mean(stats["weight_distribution"])),
                "std": float(np.std(stats["weight_distribution"])),
                "min": float(np.min(stats["weight_distribution"])),
                "max": float(np.max(stats["weight_distribution"])),
            }

        return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate continuous weak supervision labels for Phase 7"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input directory containing images",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for continuous labels",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        help="Maximum number of images to label",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save labels, just compute stats",
    )
    parser.add_argument(
        "--continuous-mode",
        action="store_true",
        help="Enable continuous labeling mode (required)",
    )

    args = parser.parse_args()

    if not args.continuous_mode:
        logger.error("Must specify --continuous-mode for Phase 7 labeling")
        sys.exit(1)

    # Create labeler
    labeler = ContinuousWeakSupervisionLabeler()

    # Label dataset
    logger.info(f"Labeling images from: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Mode: Continuous (Phase 7)")

    stats = labeler.label_dataset(
        input_dir=args.input,
        output_dir=args.output,
        max_images=args.max_images,
        dry_run=args.dry_run,
    )

    # Print statistics
    print("\n=== Continuous Weak Supervision Statistics ===")
    print(f"Total images: {stats['total_images']:,}")
    print(f"Successfully labeled: {stats['labeled']:,}")
    print(f"Errors: {stats['errors']:,}")

    print("\n=== Score Distribution Statistics ===")
    for detector, dist_stats in stats.get("score_stats", {}).items():
        print(f"\n{detector:20s}:")
        print(f"  Mean:   {dist_stats['mean']:.3f}")
        print(f"  Std:    {dist_stats['std']:.3f}")
        print(f"  Min:    {dist_stats['min']:.3f}")
        print(f"  Max:    {dist_stats['max']:.3f}")
        print(f"  Median: {dist_stats['median']:.3f}")

    if "weight_stats" in stats:
        print("\n=== Sample Weight Statistics ===")
        print(f"  Mean:   {stats['weight_stats']['mean']:.3f}")
        print(f"  Std:    {stats['weight_stats']['std']:.3f}")
        print(f"  Min:    {stats['weight_stats']['min']:.3f}")
        print(f"  Max:    {stats['weight_stats']['max']:.3f}")

    if args.dry_run:
        print("\n[DRY RUN] No labels saved.")
    else:
        print(f"\nLabels saved to: {args.output}")
        print(f"\n✅ Phase 7 continuous labeling complete!")


if __name__ == "__main__":
    main()
