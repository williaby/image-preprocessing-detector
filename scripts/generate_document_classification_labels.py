#!/usr/bin/env python3
"""
Generate Document Classification Labels (FR-2.1) via Weak Supervision

Uses DocLayNet layout annotations to classify documents into three categories:
- image_only: No extractable digital text (scanned document)
- born_digital: Extractable digital text, no significant image-based content
- hybrid: Both extractable digital text and significant embedded images

Classification logic:
1. Load DocLayNet COCO annotations (contains layout class labels)
2. For each page, check for:
   - Text-like elements (text, title, list, table, caption, section_header, formula)
   - Image elements (picture, figure)
3. Classify based on element presence:
   - No text elements → image_only (scanned/image document)
   - Text elements but no image elements → born_digital (pure digital text)
   - Text elements + image elements → hybrid (mixed content)

DocLayNet Classes (11 total):
- Text-like: 1=Caption, 2=Footnote, 3=Formula, 4=List, 5=Page-footer, 6=Page-header,
             7=Picture, 8=Section-header, 9=Table, 10=Text, 11=Title
- Image-like: 7=Picture

Usage:
    python scripts/generate_document_classification_labels.py \\
        --doclaynet-dir /path/to/doclaynet \\
        --output-dir data/training/document_classification \\
        --split train
"""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# DocLayNet class mapping (from COCO categories)
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

# Text-like classes (indicate digital text content)
TEXT_CLASSES = {1, 2, 3, 4, 5, 6, 8, 9, 10, 11}  # All except Picture

# Image-like classes (indicate embedded images)
IMAGE_CLASSES = {7}  # Picture only


def load_coco_annotations(coco_path: Path) -> dict:
    """Load COCO format annotations."""
    logger.info(f"Loading COCO annotations from {coco_path}...")
    with open(coco_path) as f:
        coco_data = json.load(f)
    logger.info(
        f"Loaded {len(coco_data.get('images', []))} images, "
        f"{len(coco_data.get('annotations', []))} annotations"
    )
    return coco_data


def classify_document_type(
    image_id: int, annotations: list[dict]
) -> tuple[str, dict[str, int]]:
    """
    Classify document type based on layout annotations.

    Args:
        image_id: COCO image ID
        annotations: List of COCO annotations for this image

    Returns:
        Tuple of (classification, class_counts)
        - classification: "image_only", "born_digital", or "hybrid"
        - class_counts: Dict mapping class names to counts
    """
    # Count elements by class
    class_counts = defaultdict(int)
    has_text = False
    has_images = False

    for ann in annotations:
        if ann["image_id"] != image_id:
            continue

        category_id = ann["category_id"]
        class_name = DOCLAYNET_CLASSES.get(category_id, "Unknown")
        class_counts[class_name] += 1

        # Check for text-like elements
        if category_id in TEXT_CLASSES:
            has_text = True

        # Check for image-like elements
        if category_id in IMAGE_CLASSES:
            has_images = True

    # Classify based on element presence
    if not has_text and not has_images:
        # No annotations at all - treat as image_only (scanned with no layout)
        classification = "image_only"
    elif not has_text:
        # Only images, no text - rare but treat as image_only
        classification = "image_only"
    elif has_text and not has_images:
        # Text but no embedded images - born digital
        classification = "born_digital"
    else:
        # Text + images - hybrid document
        classification = "hybrid"

    return classification, dict(class_counts)


def generate_classification_labels(
    doclaynet_dir: Path, output_dir: Path, split: str = "train"
) -> None:
    """
    Generate document classification labels from DocLayNet.

    Args:
        doclaynet_dir: Path to DocLayNet dataset
        output_dir: Output directory for classification labels
        split: Dataset split (train, val, test)
    """
    logger.info(f"Generating document classification labels for {split} split...")

    # Load COCO annotations
    coco_path = doclaynet_dir / "ground_truth" / "coco" / f"{split}.json"
    if not coco_path.exists():
        raise FileNotFoundError(f"COCO annotations not found: {coco_path}")

    coco_data = load_coco_annotations(coco_path)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group annotations by image
    image_annotations = defaultdict(list)
    for ann in coco_data["annotations"]:
        image_annotations[ann["image_id"]].append(ann)

    # Classify each document
    classifications = []
    class_distribution = defaultdict(int)

    logger.info(f"Classifying {len(coco_data['images'])} documents...")
    for img in tqdm(coco_data["images"], desc="Classifying documents"):
        image_id = img["id"]
        anns = image_annotations.get(image_id, [])

        # Classify document type
        classification, class_counts = classify_document_type(image_id, anns)
        class_distribution[classification] += 1

        # Store classification
        classifications.append(
            {
                "image_id": image_id,
                "file_name": img["file_name"],
                "doc_name": img.get("doc_name", Path(img["file_name"]).stem),
                "classification": classification,
                "layout_elements": class_counts,
                "width": img.get("width", 0),
                "height": img.get("height", 0),
            }
        )

    # Generate output JSON
    output_data = {
        "info": {
            "description": "Document classification labels generated from DocLayNet",
            "version": "1.0",
            "split": split,
            "total_documents": len(classifications),
            "classification_method": "weak_supervision",
            "source": "DocLayNet layout annotations",
        },
        "classes": ["image_only", "born_digital", "hybrid"],
        "class_distribution": dict(class_distribution),
        "classifications": classifications,
    }

    # Write output
    output_file = output_dir / f"{split}_document_classification.json"
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✓ Generated {len(classifications)} document classification labels")
    logger.info(f"✓ Output: {output_file}")
    logger.info("\nClass distribution:")
    for cls, count in sorted(class_distribution.items()):
        pct = count / len(classifications) * 100
        logger.info(f"  - {cls}: {count:,} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate document classification labels from DocLayNet"
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
        default=Path("data/training/document_classification"),
        help="Output directory for classification labels",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "val", "test"],
        help="Dataset split to process",
    )

    args = parser.parse_args()

    # Resolve symlinks
    doclaynet_dir = args.doclaynet_dir.resolve()
    if not doclaynet_dir.exists():
        raise FileNotFoundError(f"DocLayNet directory not found: {doclaynet_dir}")

    generate_classification_labels(doclaynet_dir, args.output_dir, args.split)


if __name__ == "__main__":
    main()
