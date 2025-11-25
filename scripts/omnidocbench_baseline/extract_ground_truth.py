#!/usr/bin/env python3
"""
OmniDocBench Ground Truth Extractor for Project A Baseline Evaluation.

Extracts page-level attributes from OmniDocBench that align with Project A's scope:
- Page attributes: fuzzy_scan, watermark, colorful_background, layout_type
- Element presence: has_tables, has_figures, has_dense_math, has_handwriting

Output format matches validate_layout_lite.py expectations.

Usage:
    # From HuggingFace (requires HF_TOKEN)
    python scripts/omnidocbench_baseline/extract_ground_truth.py

    # From local dataset
    python scripts/omnidocbench_baseline/extract_ground_truth.py --local-path data/benchmarks/omnidocbench

    # Custom output
    python scripts/omnidocbench_baseline/extract_ground_truth.py --output data/omnidocbench_gt.json
"""

import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# OmniDocBench layout type mapping to Project A schema
LAYOUT_TYPE_MAPPING = {
    "single_column": "single_column",
    "double_column": "multi_column",
    "three_column": "three_column",
    "1andmore_column": "complex",  # Mixed single + multi
    "other_layout": "complex",
}

# OmniDocBench element categories relevant to Project A
TABLE_CATEGORIES = {"table"}
FIGURE_CATEGORIES = {"figure", "figure_caption"}
FORMULA_CATEGORIES = {"equation_isolated", "equation_caption"}
HANDWRITING_INDICATORS = {"note"}  # Document types that may contain handwriting


def load_omnidocbench_hf(token: str | None = None) -> Any:
    """Load OmniDocBench from HuggingFace.

    Args:
        token: HuggingFace API token

    Returns:
        HuggingFace Dataset object
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets library not found. Install with: pip install datasets")
        sys.exit(1)

    logger.info("Loading OmniDocBench from HuggingFace...")
    token = token or os.getenv("HF_TOKEN")

    if not token:
        logger.warning("No HF_TOKEN found. Dataset may not load if gated.")

    dataset = load_dataset(
        "opendatalab/OmniDocBench",
        token=token,
        trust_remote_code=True,
    )
    return dataset


def load_omnidocbench_local(path: Path) -> Any:
    """Load OmniDocBench from local disk.

    Args:
        path: Path to saved dataset

    Returns:
        HuggingFace Dataset object
    """
    try:
        from datasets import load_from_disk
    except ImportError:
        logger.error("datasets library not found. Install with: pip install datasets")
        sys.exit(1)

    logger.info(f"Loading OmniDocBench from local path: {path}")
    return load_from_disk(str(path))


def extract_page_attributes(page_info: dict[str, Any]) -> dict[str, Any]:
    """Extract page-level attributes from OmniDocBench page_info.

    Args:
        page_info: OmniDocBench page_info dict

    Returns:
        Dict with Project A page attributes
    """
    page_attr = page_info.get("page_attribute", {})

    # Map layout type
    omni_layout = page_attr.get("layout", "other_layout")
    layout_type = LAYOUT_TYPE_MAPPING.get(omni_layout, "unknown")

    # Note: OmniDocBench has a typo "colorful_backgroud" (missing 'n')
    return {
        "layout_type": layout_type,
        "fuzzy_scan": page_attr.get("fuzzy_scan", False),
        "watermark": page_attr.get("watermark", False),
        "colorful_background": page_attr.get("colorful_backgroud", False),
        # Metadata for analysis
        "_omni_layout": omni_layout,
        "_omni_data_source": page_attr.get("data_source", "unknown"),
        "_omni_language": page_attr.get("language", "unknown"),
    }


def extract_element_presence(layout_dets: list[dict[str, Any]]) -> dict[str, bool]:
    """Extract element presence flags from OmniDocBench layout_dets.

    Args:
        layout_dets: List of layout detection annotations

    Returns:
        Dict with has_tables, has_figures, has_dense_math flags
    """
    categories = [det.get("category_type", "") for det in layout_dets if det]

    # Count elements
    table_count = sum(1 for c in categories if c in TABLE_CATEGORIES)
    figure_count = sum(1 for c in categories if c in FIGURE_CATEGORIES)
    formula_count = sum(1 for c in categories if c in FORMULA_CATEGORIES)

    # Dense math threshold: >3 formulas on a page indicates dense math content
    DENSE_MATH_THRESHOLD = 3

    return {
        "has_tables": table_count > 0,
        "has_figures": figure_count > 0,
        "has_dense_math": formula_count >= DENSE_MATH_THRESHOLD,
        # Counts for analysis
        "_table_count": table_count,
        "_figure_count": figure_count,
        "_formula_count": formula_count,
    }


def check_handwriting_indicators(
    page_info: dict[str, Any], layout_dets: list[dict[str, Any]]
) -> bool:
    """Check for handwriting presence indicators.

    OmniDocBench doesn't have explicit handwriting labels at page level,
    but we can infer from:
    1. Document type (notes, exam papers)
    2. Element attributes (formula_type: handwritten)

    Args:
        page_info: Page info dict
        layout_dets: Layout detections

    Returns:
        True if handwriting indicators present
    """
    # Check document type
    data_source = page_info.get("page_attribute", {}).get("data_source", "")
    if data_source in HANDWRITING_INDICATORS:
        return True

    # Check formula attributes for handwritten type
    for det in layout_dets:
        attr = det.get("attribute", {})
        if attr.get("formula_type") == "handwritten":
            return True

    return False


def process_omnidocbench_record(record: dict[str, Any]) -> dict[str, Any]:
    """Process a single OmniDocBench record into Project A format.

    Args:
        record: OmniDocBench dataset record

    Returns:
        Dict with all Project A relevant attributes
    """
    page_info = record.get("page_info", {})
    layout_dets = record.get("layout_dets", [])

    # Extract attributes
    page_attrs = extract_page_attributes(page_info)
    element_presence = extract_element_presence(layout_dets)
    has_handwriting = check_handwriting_indicators(page_info, layout_dets)

    # Combine into Project A format
    result = {
        # Core attributes (match validate_layout_lite.py format)
        "layout_type": page_attrs["layout_type"],
        "has_tables": element_presence["has_tables"],
        "has_figures": element_presence["has_figures"],
        "has_dense_math": element_presence["has_dense_math"],
        "has_handwriting": has_handwriting,
        "fuzzy_scan": page_attrs["fuzzy_scan"],
        "watermark": page_attrs["watermark"],
        "colorful_background": page_attrs["colorful_background"],
        # Metadata for analysis
        "_metadata": {
            "image_path": page_info.get("image_path", ""),
            "page_no": page_info.get("page_no", 0),
            "width": page_info.get("width", 0),
            "height": page_info.get("height", 0),
            "omni_layout": page_attrs["_omni_layout"],
            "omni_data_source": page_attrs["_omni_data_source"],
            "omni_language": page_attrs["_omni_language"],
            "table_count": element_presence["_table_count"],
            "figure_count": element_presence["_figure_count"],
            "formula_count": element_presence["_formula_count"],
        },
    }

    return result


def extract_ground_truth(
    dataset: Any,
    split: str = "train",
) -> dict[str, dict[str, dict[str, Any]]]:
    """Extract ground truth from OmniDocBench dataset.

    Args:
        dataset: HuggingFace Dataset object
        split: Dataset split to use

    Returns:
        Dict in validate_layout_lite.py format:
        {
            "document_001.pdf": {
                "page_1": { attributes... }
            }
        }
    """
    logger.info(f"Extracting ground truth from split: {split}")

    # Get the split
    if hasattr(dataset, "keys"):
        # DatasetDict
        data = dataset[split]
    else:
        # Single Dataset
        data = dataset

    logger.info(f"Processing {len(data)} records...")

    # Group by document (image path prefix)
    ground_truth: dict[str, dict[str, dict[str, Any]]] = {}
    stats = Counter()

    for idx, record in enumerate(data):
        if idx % 100 == 0:
            logger.info(f"Processing record {idx}/{len(data)}...")

        try:
            result = process_omnidocbench_record(record)

            # Use image path as document identifier
            image_path = result["_metadata"]["image_path"]
            page_no = result["_metadata"]["page_no"]

            # Extract document name from path (e.g., "images/doc_001/page_1.jpg" -> "doc_001")
            doc_name = Path(image_path).parent.name if image_path else f"doc_{idx:04d}"
            page_key = f"page_{page_no}" if page_no else f"page_{idx + 1}"

            if doc_name not in ground_truth:
                ground_truth[doc_name] = {}

            # Remove metadata from output (keep clean format)
            output_attrs = {k: v for k, v in result.items() if not k.startswith("_")}
            ground_truth[doc_name][page_key] = output_attrs

            # Track statistics
            for key, value in output_attrs.items():
                if isinstance(value, bool) and value:
                    stats[key] += 1
                elif key == "layout_type":
                    stats[f"layout_{value}"] += 1

        except Exception as e:
            logger.warning(f"Failed to process record {idx}: {e}")
            stats["errors"] += 1

    logger.info(f"Extracted ground truth for {len(ground_truth)} documents")
    logger.info(f"Statistics: {dict(stats)}")

    return ground_truth


def save_ground_truth(
    ground_truth: dict[str, dict[str, dict[str, Any]]],
    output_path: Path,
) -> None:
    """Save ground truth to JSON file.

    Args:
        ground_truth: Extracted ground truth dict
        output_path: Output file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    logger.info(f"Saved ground truth to: {output_path}")


def generate_statistics_report(
    ground_truth: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Generate statistics report from ground truth.

    Args:
        ground_truth: Extracted ground truth dict

    Returns:
        Statistics summary dict
    """
    total_pages = sum(len(pages) for pages in ground_truth.values())

    # Count attribute occurrences
    stats: dict[str, int] = Counter()
    layout_dist: dict[str, int] = Counter()

    for doc_pages in ground_truth.values():
        for page_attrs in doc_pages.values():
            for key, value in page_attrs.items():
                if key == "layout_type":
                    layout_dist[value] += 1
                elif isinstance(value, bool) and value:
                    stats[key] += 1

    return {
        "total_documents": len(ground_truth),
        "total_pages": total_pages,
        "attribute_counts": dict(stats),
        "attribute_rates": {k: v / total_pages for k, v in stats.items()},
        "layout_distribution": dict(layout_dist),
        "layout_rates": {k: v / total_pages for k, v in layout_dist.items()},
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract OmniDocBench ground truth for Project A baseline evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--local-path",
        type=Path,
        default=None,
        help="Path to local OmniDocBench dataset (if not using HuggingFace)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/omnidocbench_baseline/layout_labels.json"),
        help="Output path for ground truth JSON",
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=None,
        help="Output path for statistics report (default: same dir as output)",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Dataset split to use (default: train)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="HuggingFace API token (default: from HF_TOKEN env var)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("OmniDocBench Ground Truth Extractor")
    print("Project A Baseline Evaluation")
    print("=" * 70 + "\n")

    # Load dataset
    if args.local_path:
        dataset = load_omnidocbench_local(args.local_path)
    else:
        dataset = load_omnidocbench_hf(args.token)

    # Extract ground truth
    ground_truth = extract_ground_truth(dataset, args.split)

    # Save ground truth
    save_ground_truth(ground_truth, args.output)

    # Generate and save statistics
    stats = generate_statistics_report(ground_truth)
    stats_path = args.stats_output or args.output.parent / "ground_truth_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Saved statistics to: {stats_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("Extraction Complete")
    print("=" * 70)
    print(f"Documents: {stats['total_documents']}")
    print(f"Pages: {stats['total_pages']}")
    print("\nAttribute Rates:")
    for attr, rate in sorted(stats["attribute_rates"].items()):
        print(f"  {attr:25s}: {rate:.1%}")
    print("\nLayout Distribution:")
    for layout, rate in sorted(stats["layout_rates"].items()):
        print(f"  {layout:25s}: {rate:.1%}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
