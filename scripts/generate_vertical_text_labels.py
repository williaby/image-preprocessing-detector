# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Generate synthetic vertical text samples for orientation detection (FR-4.7).

Uses existing text regions from DocLayNet/DocBank and applies rotations to create
training samples with orientation annotations (0°, 90°, 180°, 270°).

Method:
1. Load DocLayNet/DocBank text annotations
2. Extract text region images
3. Apply rotations: 0°, 90°, 180°, 270°
4. Generate COCO-format annotations with orientation labels
5. Mix with real East Asian vertical text samples (if available)

License: Apache-2.0 (derived from DocLayNet CDLA-Permissive-2.0)
"""

import argparse
import json
import logging
import random
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Orientation angles
ORIENTATIONS = {
    0: "horizontal",  # 0° - normal
    90: "vertical_right",  # 90° - rotated right
    180: "upside_down",  # 180° - upside down
    270: "vertical_left",  # 270° - rotated left
}


def rotate_image(image: np.ndarray, angle: int) -> np.ndarray:
    """
    Rotate image by specified angle.

    Args:
        image: Input image
        angle: Rotation angle (0, 90, 180, 270)

    Returns:
        Rotated image
    """
    if angle == 0:
        return image
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Invalid angle: {angle}. Must be 0, 90, 180, or 270")


def adjust_bbox_for_rotation(
    bbox: list[float], img_width: int, img_height: int, angle: int
) -> list[float]:
    """
    Adjust bounding box coordinates after image rotation.

    Args:
        bbox: Original bbox [x, y, width, height]
        img_width: Original image width
        img_height: Original image height
        angle: Rotation angle (0, 90, 180, 270)

    Returns:
        Adjusted bbox [x, y, width, height]
    """
    x, y, w, h = bbox

    if angle == 0:
        return [x, y, w, h]
    if angle == 90:
        # Width and height swap, coordinates transform
        new_x = img_height - (y + h)
        new_y = x
        return [new_x, new_y, h, w]
    if angle == 180:
        new_x = img_width - (x + w)
        new_y = img_height - (y + h)
        return [new_x, new_y, w, h]
    if angle == 270:
        new_x = y
        new_y = img_width - (x + w)
        return [new_x, new_y, h, w]
    raise ValueError(f"Invalid angle: {angle}")


def get_rotated_image_dimensions(
    img_width: int, img_height: int, angle: int
) -> tuple[int, int]:
    """
    Get image dimensions after rotation.

    Args:
        img_width: Original width
        img_height: Original height
        angle: Rotation angle (0, 90, 180, 270)

    Returns:
        Tuple of (new_width, new_height)
    """
    if angle in [90, 270]:
        return (img_height, img_width)  # Dimensions swap
    return (img_width, img_height)


def generate_rotated_samples(
    coco_data: dict,
    images_dir: Path,
    output_dir: Path,
    num_samples_per_orientation: int,
    text_category_ids: list[int],
) -> dict:
    """
    Generate rotated text samples with orientation annotations.

    Args:
        coco_data: COCO format annotations
        images_dir: Directory containing source images
        output_dir: Output directory for rotated images
        num_samples_per_orientation: Number of samples to generate per orientation
        text_category_ids: List of text-related category IDs to extract

    Returns:
        COCO-format dataset with orientation annotations
    """
    output_images_dir = output_dir / "images"
    output_images_dir.mkdir(parents=True, exist_ok=True)

    # Build image ID to filename mapping
    img_id_to_info = {img["id"]: img for img in coco_data["images"]}

    # Build image ID to annotations mapping
    img_to_anns = {}
    for ann in coco_data["annotations"]:
        img_id = ann["image_id"]
        if ann.get("category_id") in text_category_ids:
            if img_id not in img_to_anns:
                img_to_anns[img_id] = []
            img_to_anns[img_id].append(ann)

    # Filter images with text annotations
    text_images = [img_id for img_id in img_to_anns if img_to_anns[img_id]]

    logger.info(f"Found {len(text_images)} images with text annotations")
    logger.info(
        f"Generating {num_samples_per_orientation} samples per orientation (4 orientations)"
    )

    # Generate output COCO dataset
    output_coco = {
        "info": {
            "description": "Synthetic vertical text dataset with orientation annotations",
            "source": "DocLayNet CDLA-Permissive-2.0 (rotated)",
            "generation_method": "Rotation augmentation (0°, 90°, 180°, 270°)",
        },
        "images": [],
        "annotations": [],
        "categories": [
            {
                "id": angle,
                "name": ORIENTATIONS[angle],
                "orientation_angle": angle,
            }
            for angle in ORIENTATIONS
        ],
    }

    # Sample images for each orientation
    samples_per_orientation = {}
    for angle in ORIENTATIONS:
        samples_per_orientation[angle] = random.sample(
            text_images, min(num_samples_per_orientation, len(text_images))
        )

    # Generate rotated samples
    new_img_id = 1
    new_ann_id = 1

    for angle in tqdm(ORIENTATIONS.keys(), desc="Processing orientations"):
        for img_id in tqdm(
            samples_per_orientation[angle],
            desc=f"Generating {angle}° samples",
            leave=False,
        ):
            img_info = img_id_to_info[img_id]
            img_path = images_dir / img_info["file_name"]

            if not img_path.exists():
                logger.warning(f"Image not found: {img_path}")
                continue

            # Load image
            img = cv2.imread(str(img_path))
            if img is None:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            # Rotate image
            rotated_img = rotate_image(img, angle)

            # Save rotated image
            output_filename = f"vertical_{angle}deg_{img_path.stem}.png"
            output_path = output_images_dir / output_filename
            cv2.imwrite(str(output_path), rotated_img)

            # Get rotated dimensions
            new_width, new_height = get_rotated_image_dimensions(
                img_info["width"], img_info["height"], angle
            )

            # Add image to output dataset
            output_coco["images"].append(
                {
                    "id": new_img_id,
                    "file_name": output_filename,
                    "width": new_width,
                    "height": new_height,
                    "original_image_id": img_id,
                    "orientation_angle": angle,
                }
            )

            # Add annotations for text regions
            for ann in img_to_anns[img_id]:
                # Adjust bbox for rotation
                adjusted_bbox = adjust_bbox_for_rotation(
                    ann["bbox"], img_info["width"], img_info["height"], angle
                )

                output_coco["annotations"].append(
                    {
                        "id": new_ann_id,
                        "image_id": new_img_id,
                        "category_id": angle,  # Category = orientation angle
                        "bbox": adjusted_bbox,
                        "area": adjusted_bbox[2] * adjusted_bbox[3],
                        "iscrowd": 0,
                        "orientation_angle": angle,
                        "orientation_label": ORIENTATIONS[angle],
                        "original_category_id": ann.get("category_id"),
                    }
                )
                new_ann_id += 1

            new_img_id += 1

    return output_coco


def generate_dataset(
    source_dir: Path,
    output_dir: Path,
    split: str = "train",
    num_samples_per_orientation: int = 1250,
    text_category_ids: list[int] = None,
) -> None:
    """
    Generate synthetic vertical text dataset.

    Args:
        source_dir: Source dataset directory (DocLayNet or DocBank)
        output_dir: Output directory for generated dataset
        split: Dataset split (train/val/test)
        num_samples_per_orientation: Samples per orientation (default: 1250)
        text_category_ids: Text category IDs to extract (default: DocLayNet text classes)
    """
    logger.info(f"Generating vertical text dataset for {split} split...")

    # Default: DocLayNet text-related category IDs
    if text_category_ids is None:
        text_category_ids = [
            1,  # Caption
            3,  # Formula
            4,  # List-item
            8,  # Section-header
            10,  # Text
            11,  # Title
        ]

    # Load COCO annotations
    coco_file = source_dir / "ground_truth" / "coco" / f"{split}.json"
    if not coco_file.exists():
        raise FileNotFoundError(f"COCO annotations not found: {coco_file}")

    with open(coco_file) as f:
        coco_data = json.load(f)

    # Images directory (DocLayNet stores all images in documents/png/)
    images_dir = source_dir / "documents" / "png"

    # Generate rotated samples
    output_coco = generate_rotated_samples(
        coco_data,
        images_dir,
        output_dir,
        num_samples_per_orientation,
        text_category_ids,
    )

    # Save output dataset
    output_file = output_dir / f"{split}_vertical_text.json"
    with open(output_file, "w") as f:
        json.dump(output_coco, f, indent=2)

    total_samples = len(output_coco["images"])
    total_annotations = len(output_coco["annotations"])

    logger.info(f"✅ Generated {total_samples} vertical text samples")
    logger.info(f"   - Annotations: {total_annotations}")
    logger.info(f"   - Orientations: {list(ORIENTATIONS.values())}")
    logger.info(f"   - Images: {output_dir / 'images'}")
    logger.info(f"   - Annotations: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic vertical text dataset"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/benchmarks/doclaynet"),
        help="Source dataset directory (DocLayNet or DocBank)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/vertical_text"),
        help="Output directory for generated dataset",
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
        default=1250,
        help="Number of samples per orientation (default: 1250, total: 5000)",
    )
    parser.add_argument(
        "--text-categories",
        type=int,
        nargs="+",
        default=None,
        help="Text category IDs to extract (default: DocLayNet text classes)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)
    np.random.seed(args.seed)

    generate_dataset(
        args.source_dir,
        args.output_dir,
        args.split,
        args.num_samples,
        args.text_categories,
    )


if __name__ == "__main__":
    main()
