# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Generate weak supervision labels for parasitic content detection (FR-4.4).

Uses existing header/footer bboxes from DocLayNet to identify repeating patterns
across multi-page documents.

Method:
1. Load DocLayNet COCO annotations (page-header and page-footer classes)
2. Extract text content from header/footer regions using OCR
3. Compute cross-page similarity scores
4. Flag as "repeating" if similarity > 0.85 across 3+ pages
5. Generate annotations with repeating pattern flags

License: Apache-2.0 (derived from DocLayNet CDLA-Permissive-2.0)
"""

import argparse
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import pytesseract
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# DocLayNet class IDs
CLASS_PAGE_HEADER = 6  # page-header
CLASS_PAGE_FOOTER = 5  # page-footer


@dataclass
class ProcessingContext:
    """Context for element processing with shared mappings."""

    img_id_to_path: dict[int, Path]
    img_to_anns: dict[int, list[dict]]
    parasitic_annotations: dict[int, dict]


@dataclass
class PatternConfig:
    """Configuration for pattern detection."""

    similarity_threshold: float
    min_occurrences: int


def extract_text_from_bbox(
    image_path: Path, bbox: list[float], padding: int = 5
) -> str:
    """
    Extract text from bounding box region using Tesseract OCR.

    Args:
        image_path: Path to image file
        bbox: COCO format [x, y, width, height]
        padding: Pixels to add around bbox (default: 5)

    Returns:
        Extracted text (normalized)
    """
    # Load image
    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning(f"Failed to load image: {image_path}")
        return ""

    # Extract bbox region with padding
    x, y, w, h = [int(v) for v in bbox]
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img.shape[1] - x, w + 2 * padding)
    h = min(img.shape[0] - y, h + 2 * padding)

    roi = img[y : y + h, x : x + w]

    try:
        # Extract text using Tesseract
        text = pytesseract.image_to_string(roi, config="--psm 6")
        # Normalize: lowercase, strip whitespace, remove extra spaces
        text = " ".join(text.lower().strip().split())
        return text
    except Exception as e:
        logger.warning(f"OCR failed for {image_path}: {e}")
        return ""


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute text similarity using SequenceMatcher (Levenshtein-based).

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score [0.0, 1.0]
    """
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1, text2).ratio()


def group_pages_by_document(coco_data: dict) -> dict[str, list[int]]:
    """
    Group image IDs by document using doc_name field from COCO annotations.

    Args:
        coco_data: COCO format annotations

    Returns:
        Dict mapping document name to list of image IDs
    """
    doc_to_images = defaultdict(list)
    for img in coco_data["images"]:
        img_id = img["id"]
        # Use doc_name from COCO metadata (DocLayNet provides this field)
        doc_name = img.get("doc_name", Path(img["file_name"]).stem)
        doc_to_images[doc_name].append(img_id)

    return doc_to_images


def identify_repeating_patterns(
    coco_data: dict,
    images_dir: Path,
    similarity_threshold: float = 0.85,
    min_occurrences: int = 3,
) -> dict[int, dict]:
    """
    Identify repeating header/footer patterns across multi-page documents.

    Args:
        coco_data: COCO format annotations
        images_dir: Directory containing images
        similarity_threshold: Minimum similarity to consider pattern repeating (default: 0.85)
        min_occurrences: Minimum page occurrences to flag as repeating (default: 3)

    Returns:
        Dict mapping annotation ID to parasitic content metadata
    """
    logger.info("Grouping pages by document...")
    doc_to_images = group_pages_by_document(coco_data)

    # Build image ID to filename mapping
    img_id_to_path = {
        img["id"]: images_dir / img["file_name"] for img in coco_data["images"]
    }

    # Build image ID to annotations mapping
    img_to_anns = defaultdict(list)
    for ann in coco_data["annotations"]:
        img_to_anns[ann["image_id"]].append(ann)

    # Identify repeating patterns
    parasitic_annotations = {}
    total_docs = len(
        [pages for pages in doc_to_images.values() if len(pages) >= min_occurrences]
    )

    logger.info(
        f"Processing {total_docs} multi-page documents (≥{min_occurrences} pages)..."
    )

    for doc_name, image_ids in tqdm(doc_to_images.items(), desc="Processing documents"):
        if len(image_ids) < min_occurrences:
            continue  # Skip single-page or short documents

        # Process headers
        _process_element_type(
            doc_name,
            image_ids,
            CLASS_PAGE_HEADER,
            img_id_to_path,
            img_to_anns,
            similarity_threshold,
            min_occurrences,
            parasitic_annotations,
        )

        # Process footers
        _process_element_type(
            doc_name,
            image_ids,
            CLASS_PAGE_FOOTER,
            img_id_to_path,
            img_to_anns,
            similarity_threshold,
            min_occurrences,
            parasitic_annotations,
        )

    return parasitic_annotations


def _collect_element_texts(
    image_ids: list[int],
    class_id: int,
    context: ProcessingContext,
) -> tuple[list[str], list[dict]]:
    """
    Collect text content from all instances of an element type across pages.

    Args:
        image_ids: List of page image IDs
        class_id: DocLayNet class ID (header or footer)
        context: Processing context with mappings

    Returns:
        Tuple of (texts, annotations) for elements with extracted text
    """
    element_texts = []
    element_anns = []

    for img_id in sorted(image_ids):
        img_path = context.img_id_to_path.get(img_id)
        if not img_path or not img_path.exists():
            continue

        # Find annotations for this element type
        anns = [
            ann
            for ann in context.img_to_anns[img_id]
            if ann.get("category_id") == class_id
        ]

        for ann in anns:
            bbox = ann["bbox"]
            text = extract_text_from_bbox(img_path, bbox)
            if text:  # Only store non-empty text
                element_texts.append(text)
                element_anns.append(ann)

    return element_texts, element_anns


def _find_repeating_patterns(
    element_texts: list[str],
    config: PatternConfig,
) -> list[list[int]]:
    """
    Find repeating text patterns using similarity clustering.

    Args:
        element_texts: List of text content from elements
        config: Pattern detection configuration

    Returns:
        List of groups, where each group is a list of indices of similar texts
    """
    repeating_groups = []
    processed = set()

    for i, text in enumerate(element_texts):
        if i in processed:
            continue

        # Find all texts similar to this one
        similar_indices = [i]
        for j, other_text in enumerate(element_texts):
            if i != j and j not in processed:
                sim = compute_similarity(text, other_text)
                if sim >= config.similarity_threshold:
                    similar_indices.append(j)

        # Flag as repeating if ≥ min_occurrences
        if len(similar_indices) >= config.min_occurrences:
            repeating_groups.append(similar_indices)
            processed.update(similar_indices)

    return repeating_groups


def _mark_parasitic_annotations(
    repeating_groups: list[list[int]],
    element_texts: list[str],
    element_anns: list[dict],
    image_ids: list[int],
    doc_name: str,
    class_id: int,
    context: ProcessingContext,
) -> None:
    """
    Mark annotations as parasitic based on repeating pattern groups.

    Args:
        repeating_groups: Groups of similar text indices
        element_texts: List of text content
        element_anns: List of annotations
        image_ids: List of page image IDs
        doc_name: Document identifier
        class_id: DocLayNet class ID
        context: Processing context to update
    """
    for group in repeating_groups:
        for idx in group:
            ann = element_anns[idx]
            img_id = ann["image_id"]
            page_num = image_ids.index(img_id) + 1  # 1-indexed page number

            context.parasitic_annotations[ann["id"]] = {
                "annotation_id": ann["id"],
                "image_id": img_id,
                "bbox": ann["bbox"],
                "category_id": class_id,
                "document": doc_name,
                "page_number": page_num,
                "repeating_pattern": True,
                "pattern_group": f"{doc_name}_{class_id}_{min(group)}",
                "occurrences": len(group),
                "text_preview": element_texts[group[0]][
                    :100
                ],  # First 100 chars of representative text
            }


def _process_element_type(
    doc_name: str,
    image_ids: list[int],
    class_id: int,
    img_id_to_path: dict[int, Path],
    img_to_anns: dict[int, list[dict]],
    similarity_threshold: float,
    min_occurrences: int,
    parasitic_annotations: dict[int, dict],
) -> None:
    """
    Process single element type (header or footer) for repeating patterns.

    Orchestrates the pattern detection pipeline by delegating to specialized helper functions.

    Args:
        doc_name: Document identifier
        image_ids: List of page image IDs
        class_id: DocLayNet class ID (header or footer)
        img_id_to_path: Mapping from image ID to file path
        img_to_anns: Mapping from image ID to annotations
        similarity_threshold: Similarity threshold for repeating patterns
        min_occurrences: Minimum occurrences to flag as repeating
        parasitic_annotations: Output dict to populate
    """
    # Create processing context and configuration
    context = ProcessingContext(
        img_id_to_path=img_id_to_path,
        img_to_anns=img_to_anns,
        parasitic_annotations=parasitic_annotations,
    )
    config = PatternConfig(
        similarity_threshold=similarity_threshold,
        min_occurrences=min_occurrences,
    )

    # Step 1: Collect text from all element instances
    element_texts, element_anns = _collect_element_texts(image_ids, class_id, context)

    if len(element_texts) < config.min_occurrences:
        return  # Not enough samples

    # Step 2: Find repeating patterns using similarity clustering
    repeating_groups = _find_repeating_patterns(element_texts, config)

    # Step 3: Mark annotations as parasitic
    _mark_parasitic_annotations(
        repeating_groups,
        element_texts,
        element_anns,
        image_ids,
        doc_name,
        class_id,
        context,
    )


def generate_dataset(
    doclaynet_dir: Path,
    output_dir: Path,
    split: str = "train",
    similarity_threshold: float = 0.85,
    min_occurrences: int = 3,
) -> None:
    """
    Generate parasitic content detection dataset from DocLayNet.

    Args:
        doclaynet_dir: DocLayNet dataset root directory
        output_dir: Output directory for generated annotations
        split: Dataset split (train/val/test)
        similarity_threshold: Similarity threshold for repeating patterns
        min_occurrences: Minimum occurrences to flag as repeating
    """
    logger.info(f"Generating parasitic content labels for {split} split...")

    # Load COCO annotations
    coco_file = doclaynet_dir / "ground_truth" / "coco" / f"{split}.json"
    if not coco_file.exists():
        raise FileNotFoundError(f"COCO annotations not found: {coco_file}")

    with open(coco_file) as f:
        coco_data = json.load(f)

    # Images directory (DocLayNet stores all images in documents/png/)
    images_dir = doclaynet_dir / "documents" / "png"

    # Identify repeating patterns
    parasitic_annotations = identify_repeating_patterns(
        coco_data, images_dir, similarity_threshold, min_occurrences
    )

    # Generate output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{split}_parasitic_content.json"

    output_data = {
        "info": {
            "description": "Parasitic content detection labels (weak supervision from DocLayNet)",
            "source": "DocLayNet CDLA-Permissive-2.0",
            "generation_method": "Text similarity clustering",
            "similarity_threshold": similarity_threshold,
            "min_occurrences": min_occurrences,
        },
        "parasitic_annotations": list(parasitic_annotations.values()),
        "statistics": {
            "total_parasitic_elements": len(parasitic_annotations),
            "total_documents": len(
                {ann["document"] for ann in parasitic_annotations.values()}
            ),
            "total_pages": len(
                {ann["page_number"] for ann in parasitic_annotations.values()}
            ),
        },
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✅ Generated {len(parasitic_annotations)} parasitic content labels")
    logger.info(f"   - Documents: {output_data['statistics']['total_documents']}")
    logger.info(f"   - Pages: {output_data['statistics']['total_pages']}")
    logger.info(f"   - Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate parasitic content detection labels (weak supervision)"
    )
    parser.add_argument(
        "--doclaynet-dir",
        type=Path,
        default=Path("data/benchmarks/doclaynet"),
        help="DocLayNet dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/parasitic_content"),
        help="Output directory for generated labels",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "val", "test"],
        help="Dataset split to process",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.85,
        help="Similarity threshold for repeating patterns (default: 0.85)",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=3,
        help="Minimum occurrences to flag as repeating (default: 3)",
    )

    args = parser.parse_args()

    generate_dataset(
        args.doclaynet_dir,
        args.output_dir,
        args.split,
        args.similarity_threshold,
        args.min_occurrences,
    )


if __name__ == "__main__":
    main()
