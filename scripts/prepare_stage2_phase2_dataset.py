#!/usr/bin/env python3
"""Prepare Stage 2 dataset for Phase 2 with Layer 2 metadata integration.

This script enhances the existing Stage 2 JSONL splits with Layer 2 enrichments:
- Content type flags (has_table, has_formula, has_handwriting, has_figure)
- Domain classification (domain_level1, domain_confidence)
- Resolution categories
- Capture method detection

IMPORTANT: This preserves existing layout masks - no need to regenerate them.
"""

import json
from pathlib import Path

# Layer 2 metadata registry location
METADATA_REGISTRY = Path("/mnt/e/image_detection/metadata_registry/json")

# Stage 2 splits location
STAGE2_SPLITS = Path("/home/byron/dev/image_detection/stage2_diqa_ensemble/splits")

# Output location for enhanced splits
OUTPUT_DIR = Path(
    "/home/byron/dev/image_detection/stage2_diqa_ensemble/splits_with_layer2"
)


def load_layer2_metadata(dataset_name: str) -> dict:
    """Load Layer 2 metadata for a dataset."""
    metadata_file = METADATA_REGISTRY / f"{dataset_name}_metadata.json"

    if not metadata_file.exists():
        print(f"⚠️  No Layer 2 metadata found for {dataset_name}")
        return {}

    with open(metadata_file) as f:
        data = json.load(f)

    # Index by filename for matching (extracted from source field)
    index = {}
    for sample in data.get("samples", []):
        source = sample.get("source", {})
        if isinstance(source, dict):
            filename = source.get("original_filename", "")
            if filename and "enrichments" in sample:
                index[filename] = sample["enrichments"]

    return index


def enhance_split_with_layer2(split_file: Path, output_file: Path) -> dict:
    """Enhance JSONL split with Layer 2 metadata."""
    print(f"\nProcessing: {split_file.name}")

    # Load all Layer 2 metadata (map Stage 2 names to metadata filenames)
    dataset_name_mapping = {
        "diqa-5000": "diqa-5000",
        "funsd": "funsd",
        "sroie": "sroie",
        "tobacco-800": "tobacco800",  # Stage 2 uses hyphen, metadata has no hyphen
        "smartdoc-qa": "smartdoc-qa",
    }

    layer2_cache = {}
    for stage2_name, metadata_name in dataset_name_mapping.items():
        layer2_cache[stage2_name] = load_layer2_metadata(metadata_name)

    enhanced_count = 0
    missing_count = 0
    total_count = 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(split_file) as fin, open(output_file, "w") as fout:
        for line in fin:
            total_count += 1
            sample = json.loads(line)

            # Get dataset and extract filename for matching
            dataset = sample.get("source_dataset", "unknown")
            image_id = sample.get("image_id", "")
            # Extract filename from image_id (e.g., "diqa-5000/train/res/train_res_01537.jpg")
            filename = Path(image_id).name if image_id else ""

            # Look up Layer 2 enrichments by filename
            dataset_metadata = layer2_cache.get(dataset, {})
            enrichments = dataset_metadata.get(filename)

            if enrichments:
                # Extract relevant Layer 2 fields
                current_version = enrichments.get("current_version", 1)
                versions = enrichments.get("versions", [])

                if versions and len(versions) >= current_version:
                    layer2_data = versions[current_version - 1].get("data", {})

                    # Add Layer 2 fields to sample
                    sample["layer2"] = {
                        "has_table": layer2_data.get("has_table", False),
                        "has_formula": layer2_data.get("has_formula", False),
                        "has_handwriting": layer2_data.get("has_handwriting", False),
                        "has_figure": layer2_data.get("has_figure", False),
                        "domain_level1": layer2_data.get("domain_level1", "UNK"),
                        "domain_confidence": layer2_data.get("domain_confidence", 0.3),
                        "capture_method": layer2_data.get("capture_method", "unknown"),
                        "resolution_category": layer2_data.get(
                            "resolution_category", "unknown"
                        ),
                    }
                    enhanced_count += 1
            else:
                # No Layer 2 data found
                sample["layer2"] = None
                missing_count += 1

            fout.write(json.dumps(sample) + "\n")

    stats = {
        "total": total_count,
        "enhanced": enhanced_count,
        "missing": missing_count,
        "coverage": enhanced_count / total_count if total_count > 0 else 0.0,
    }

    print(f"  Total: {total_count}")
    print(f"  Enhanced: {enhanced_count} ({stats['coverage'] * 100:.1f}%)")
    print(f"  Missing: {missing_count}")

    return stats


def main():
    """Process all splits."""
    print("=" * 60)
    print("Stage 2 Dataset Enhancement with Layer 2 Metadata")
    print("=" * 60)

    if not METADATA_REGISTRY.exists():
        print(f"❌ Metadata registry not found: {METADATA_REGISTRY}")
        return

    if not STAGE2_SPLITS.exists():
        print(f"❌ Stage 2 splits not found: {STAGE2_SPLITS}")
        return

    all_stats = {}
    for split in ["train", "val", "test"]:
        input_file = STAGE2_SPLITS / f"{split}.jsonl"
        output_file = OUTPUT_DIR / f"{split}.jsonl"

        if input_file.exists():
            all_stats[split] = enhance_split_with_layer2(input_file, output_file)

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")

    for split, stats in all_stats.items():
        print(
            f"{split.upper()}: {stats['enhanced']}/{stats['total']} enhanced ({stats['coverage'] * 100:.1f}%)"
        )

    print(f"\n✅ Enhanced splits saved to: {OUTPUT_DIR}")
    print(f"\nNext steps:")
    print(f"1. Upload enhanced splits to Modal volume:")
    print(f"   poetry run modal volume put stage2-training-data \\")
    print(f"     {OUTPUT_DIR}/ /data/stage2_diqa_ensemble/splits_with_layer2/")
    print(f"2. Update training script to load from splits_with_layer2/")
    print(f"3. Launch Phase 2 training")


if __name__ == "__main__":
    main()
