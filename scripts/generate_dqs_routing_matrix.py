# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Generate DQS Routing Matrix Labels (FR-7.1) via Weak Supervision

Creates a 3x3 routing matrix based on two axes:
1. Degradation Quality: Low / Medium / High (blur, noise, contrast, skew, DPI)
2. Structural Complexity: Low / Medium / High (multi-column, tables, formulas, figures)

This generates 9 routing bins:
- (Low Degradation, Low Complexity) → Bin 1
- (Low Degradation, Medium Complexity) → Bin 2
- ...
- (High Degradation, High Complexity) → Bin 9

Degradation Metrics (Classical CV):
- Blur: Laplacian variance (lower = more blur)
- Noise: Local variance in flat regions
- Contrast: RMS contrast
- Skew: Hough transform angle deviation
- DPI: Estimated from image dimensions

Structural Complexity Metrics (DocLayNet annotations):
- Multi-column: Column count heuristic from text block positions
- Tables: Count of table annotations
- Formulas: Count of formula annotations
- Figures: Count of picture annotations
- Mixed scripts: Language diversity (if available)

Usage:
    python scripts/generate_dqs_routing_matrix.py \\
        --doclaynet-dir /path/to/doclaynet \\
        --output-dir data/training/dqs_routing \\
        --split train \\
        --num-samples 6400  # 3x3 grid = 9 bins, need ~6400 samples per split
"""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# DocLayNet class mapping
DOCLAYNET_CLASSES = {
    1: "Caption",
    2: "Footnote",
    3: "Formula",
    4: "List",
    5: "Page-footer",
    6: "Page-header",
    7: "Picture",
    8: "Section-header",
    9: "Table",
    10: "Text",
    11: "Title",
}


def calculate_blur_score(image: np.ndarray) -> float:
    """
    Calculate blur score using Laplacian variance.

    Args:
        image: Input image (BGR or grayscale)

    Returns:
        Blur score (higher = sharper, lower = blurrier)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    return float(variance)


def calculate_noise_score(image: np.ndarray) -> float:
    """
    Estimate noise using local variance in flat regions.

    Args:
        image: Input image (BGR or grayscale)

    Returns:
        Noise score (higher = more noise)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Compute local variance using window
    kernel_size = 5
    mean = cv2.blur(gray.astype(np.float32), (kernel_size, kernel_size))
    sqr_mean = cv2.blur(gray.astype(np.float32) ** 2, (kernel_size, kernel_size))
    variance = sqr_mean - mean**2

    # Use median variance of flat regions (low gradient)
    gradient = cv2.Laplacian(gray, cv2.CV_64F)
    flat_mask = np.abs(gradient) < 10  # Flat regions
    if flat_mask.sum() > 0:
        noise = np.median(variance[flat_mask])
    else:
        noise = np.median(variance)

    return float(noise)


def calculate_contrast_score(image: np.ndarray) -> float:
    """
    Calculate RMS contrast.

    Args:
        image: Input image (BGR or grayscale)

    Returns:
        RMS contrast (higher = more contrast)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # RMS contrast
    mean_intensity = gray.mean()
    rms_contrast = np.sqrt(((gray - mean_intensity) ** 2).mean())
    return float(rms_contrast)


def calculate_skew_score(image: np.ndarray) -> float:
    """
    Estimate skew using Hough transform.

    Args:
        image: Input image (BGR or grayscale)

    Returns:
        Skew angle in degrees (0 = no skew)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Hough line detection
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)

    if lines is None or len(lines) == 0:
        return 0.0

    # Compute angles
    angles = []
    for line in lines:
        _, theta = line[0]
        angle = np.degrees(theta) - 90  # Convert to -90 to 90 range
        angles.append(angle)

    # Median angle deviation from 0
    median_angle = np.median(angles)
    skew = abs(median_angle)
    return float(skew)


def estimate_dpi(image: np.ndarray) -> float:
    """
    Estimate DPI from image dimensions (rough heuristic).

    Args:
        image: Input image

    Returns:
        Estimated DPI (assuming A4 page)
    """
    height, _ = image.shape[:2]

    # Assume A4 page (8.27 x 11.69 inches)
    # Use height for estimate
    a4_height_inches = 11.69
    estimated_dpi = height / a4_height_inches

    return float(estimated_dpi)


def calculate_structural_complexity(
    annotations: list[dict], image_width: int
) -> dict[str, int]:
    """
    Calculate structural complexity metrics from layout annotations.

    Args:
        annotations: COCO annotations for the page
        image_width: Image width

    Returns:
        Dict with complexity metrics
    """
    metrics = {
        "table_count": 0,
        "formula_count": 0,
        "picture_count": 0,
        "text_blocks": 0,
        "column_count": 1,  # Default to single column
    }

    # Count layout elements
    text_boxes = []
    for ann in annotations:
        cat_id = ann["category_id"]
        class_name = DOCLAYNET_CLASSES.get(cat_id, "Unknown")

        if class_name == "Table":
            metrics["table_count"] += 1
        elif class_name == "Formula":
            metrics["formula_count"] += 1
        elif class_name == "Picture":
            metrics["picture_count"] += 1
        elif class_name == "Text":
            metrics["text_blocks"] += 1
            # Store bbox for column detection
            bbox = ann["bbox"]  # [x, y, width, height]
            text_boxes.append(bbox)

    # Estimate column count from text block positions
    if len(text_boxes) > 5:
        # Sort by x-coordinate
        x_positions = sorted([bbox[0] for bbox in text_boxes])

        # Find clusters in x-positions (columns)
        clusters = []
        current_cluster = [x_positions[0]]
        for x in x_positions[1:]:
            if x - current_cluster[-1] < image_width * 0.1:  # 10% threshold
                current_cluster.append(x)
            else:
                clusters.append(current_cluster)
                current_cluster = [x]
        clusters.append(current_cluster)

        metrics["column_count"] = len(clusters)

    return metrics


def classify_degradation(
    blur: float, noise: float, contrast: float, skew: float, dpi: float
) -> str:
    """
    Classify degradation level based on quality metrics.

    Thresholds (empirically determined):
    - Blur: >500 = high quality, <100 = low quality
    - Noise: <10 = high quality, >50 = low quality
    - Contrast: >50 = high quality, <20 = low quality
    - Skew: <1° = high quality, >5° = low quality
    - DPI: >200 = high quality, <100 = low quality

    Returns:
        "low", "medium", or "high" degradation
    """
    # Score each metric (0-1 scale, higher = better quality)
    blur_score = min(blur / 500, 1.0)
    noise_score = max(1.0 - noise / 50, 0.0)
    contrast_score = min(contrast / 50, 1.0)
    skew_score = max(1.0 - skew / 5, 0.0)
    dpi_score = min(dpi / 200, 1.0)

    # Average quality score
    quality = (blur_score + noise_score + contrast_score + skew_score + dpi_score) / 5

    # Map to degradation level (inverse of quality)
    if quality > 0.7:
        return "low"  # Low degradation (high quality)
    if quality > 0.4:
        return "medium"
    return "high"  # High degradation (low quality)


def classify_structural_complexity(metrics: dict[str, int]) -> str:
    """
    Classify structural complexity level.

    Complexity factors:
    - Multi-column layout: +complexity
    - Tables: +complexity
    - Formulas: +complexity
    - Figures: +complexity

    Returns:
        "low", "medium", or "high" complexity
    """
    complexity_score = 0

    # Column count
    if metrics["column_count"] > 2:
        complexity_score += 2
    elif metrics["column_count"] > 1:
        complexity_score += 1

    # Tables
    if metrics["table_count"] > 2:
        complexity_score += 2
    elif metrics["table_count"] > 0:
        complexity_score += 1

    # Formulas
    if metrics["formula_count"] > 5:
        complexity_score += 2
    elif metrics["formula_count"] > 0:
        complexity_score += 1

    # Figures
    if metrics["picture_count"] > 3:
        complexity_score += 2
    elif metrics["picture_count"] > 0:
        complexity_score += 1

    # Classify based on total score
    if complexity_score >= 5:
        return "high"
    if complexity_score >= 2:
        return "medium"
    return "low"


def generate_dqs_routing_labels(
    doclaynet_dir: Path,
    output_dir: Path,
    split: str = "train",
    num_samples: int = 6400,
) -> None:
    """
    Generate DQS routing matrix labels from DocLayNet.

    Args:
        doclaynet_dir: Path to DocLayNet dataset
        output_dir: Output directory for DQS routing labels
        split: Dataset split (train, val, test)
        num_samples: Target number of samples (default 6400 for balanced 3x3 grid)
    """
    logger.info(f"Generating DQS routing matrix labels for {split} split...")

    # Load COCO annotations
    coco_path = doclaynet_dir / "ground_truth" / "coco" / f"{split}.json"
    if not coco_path.exists():
        raise FileNotFoundError(f"COCO annotations not found: {coco_path}")

    with open(coco_path) as f:
        coco_data = json.load(f)

    logger.info(
        f"Loaded {len(coco_data['images'])} images, "
        f"{len(coco_data['annotations'])} annotations"
    )

    # Get image directory
    images_dir = doclaynet_dir / "documents" / "png"
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group annotations by image
    image_annotations = defaultdict(list)
    for ann in coco_data["annotations"]:
        image_annotations[ann["image_id"]].append(ann)

    # Process images (sample if too many)
    images_to_process = coco_data["images"]
    if len(images_to_process) > num_samples:
        logger.info(f"Sampling {num_samples} from {len(images_to_process)} images...")
        import random

        random.seed(42)
        images_to_process = random.sample(images_to_process, num_samples)  # nosec B311

    # Generate DQS labels
    dqs_labels = []
    routing_matrix = defaultdict(int)  # Track distribution across 9 bins

    logger.info(f"Processing {len(images_to_process)} images...")
    for img in tqdm(images_to_process, desc="Analyzing images"):
        image_id = img["id"]
        file_name = img["file_name"]
        image_path = images_dir / file_name

        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}, skipping...")
            continue

        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning(f"Failed to load image: {image_path}, skipping...")
            continue

        # Calculate degradation metrics
        blur = calculate_blur_score(image)
        noise = calculate_noise_score(image)
        contrast = calculate_contrast_score(image)
        skew = calculate_skew_score(image)
        dpi = estimate_dpi(image)

        # Calculate structural complexity metrics
        anns = image_annotations.get(image_id, [])
        complexity_metrics = calculate_structural_complexity(
            anns, img.get("width", image.shape[1])
        )

        # Classify degradation and complexity
        degradation = classify_degradation(blur, noise, contrast, skew, dpi)
        complexity = classify_structural_complexity(complexity_metrics)

        # Map to routing bin (1-9)
        deg_idx = {"low": 0, "medium": 1, "high": 2}[degradation]
        comp_idx = {"low": 0, "medium": 1, "high": 2}[complexity]
        routing_bin = deg_idx * 3 + comp_idx + 1  # 1-indexed

        routing_matrix[routing_bin] += 1

        # Store label
        dqs_labels.append(
            {
                "image_id": image_id,
                "file_name": file_name,
                "degradation": degradation,
                "complexity": complexity,
                "routing_bin": routing_bin,
                "degradation_metrics": {
                    "blur": round(blur, 2),
                    "noise": round(noise, 2),
                    "contrast": round(contrast, 2),
                    "skew": round(skew, 2),
                    "dpi": round(dpi, 2),
                },
                "complexity_metrics": complexity_metrics,
            }
        )

    # Generate output JSON
    output_data = {
        "info": {
            "description": "DQS routing matrix labels generated from DocLayNet",
            "version": "1.0",
            "split": split,
            "total_samples": len(dqs_labels),
            "generation_method": "weak_supervision",
            "source": "DocLayNet images + annotations",
        },
        "routing_matrix": {
            "bins": 9,
            "degradation_levels": ["low", "medium", "high"],
            "complexity_levels": ["low", "medium", "high"],
            "distribution": dict(routing_matrix),
        },
        "labels": dqs_labels,
    }

    # Write output
    output_file = output_dir / f"{split}_dqs_routing.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✓ Generated {len(dqs_labels)} DQS routing labels")
    logger.info(f"✓ Output: {output_file}")
    logger.info("\nRouting matrix distribution (3x3 grid):")
    logger.info("Degradation (rows) × Complexity (cols)")
    for deg in ["low", "medium", "high"]:
        deg_idx = {"low": 0, "medium": 1, "high": 2}[deg]
        row = []
        for comp in ["low", "medium", "high"]:
            comp_idx = {"low": 0, "medium": 1, "high": 2}[comp]
            bin_num = deg_idx * 3 + comp_idx + 1
            count = routing_matrix.get(bin_num, 0)
            row.append(f"{count:5d}")
        logger.info(f"{deg:8s}: {' '.join(row)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate DQS routing matrix labels from DocLayNet"
    )
    parser.add_argument(
        "--doclaynet-dir",
        type=Path,
        default=Path("data/benchmarks/doclaynet"),
        help="Path to DocLayNet dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/dqs_routing"),
        help="Output directory for DQS routing labels",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "val", "test"],
        help="Dataset split to process",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=6400,
        help="Number of samples to generate (default: 6400 for balanced 3x3 grid)",
    )

    args = parser.parse_args()

    # Resolve symlinks
    doclaynet_dir = args.doclaynet_dir.resolve()
    if not doclaynet_dir.exists():
        raise FileNotFoundError(f"DocLayNet directory not found: {doclaynet_dir}")

    generate_dqs_routing_labels(
        doclaynet_dir, args.output_dir, args.split, args.num_samples
    )


if __name__ == "__main__":
    main()
