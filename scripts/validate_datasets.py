# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""
Dataset Validation Script

Validates that all required datasets are present locally and checks their status
against the DATASET_INSTALLATION.md requirements.

Usage:
    python scripts/validate_datasets.py
    python scripts/validate_datasets.py --upload-to-gcs
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Expected datasets configuration
EXPECTED_DATASETS = {
    "benchmarks": {
        "doclaynet": {
            "path": "benchmarks/doclaynet",
            "type": "symlink",
            "target": "/home/byron/dev/data_ingestor/data/benchmarks/doclaynet",
            "phase": 1,
            "required": True,
            "description": "DocLayNet layout detection dataset",
        },
        "signatr6k": {
            "path": "benchmarks/signatr6k",
            "type": "directory",
            "phase": "?",
            "required": False,
            "description": "Signature detection dataset",
        },
        "synthetic_iqa": {
            "path": "benchmarks/synthetic_iqa",
            "type": "directory",
            "phase": 1,
            "required": True,
            "description": "Synthetic IQA dataset (auto-generated)",
        },
        "cocotext": {
            "path": "benchmarks/cocotext",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "COCO-Text annotations",
        },
        "omnidocbench": {
            "path": "benchmarks/omnidocbench",
            "type": "directory",
            "phase": 3,
            "required": False,
            "description": "OmniDocBench multi-task benchmark",
        },
        "tablebank": {
            "path": "benchmarks/tablebank",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "TableBank table detection dataset",
        },
        "pubtabnet": {
            "path": "benchmarks/pubtabnet",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "PubTabNet table structure dataset",
        },
        "fintabnet": {
            "path": "benchmarks/fintabnet",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "FinTabNet financial table dataset",
        },
        "wili_2018": {
            "path": "benchmarks/wili_2018",
            "type": "directory",
            "phase": 2,
            "required": False,
            "description": "WiLI language identification dataset",
        },
    },
    "raw": {
        "docbank": {
            "path": "raw/docbank",
            "type": "directory",
            "phase": 1,
            "required": False,
            "description": "DocBank raw data",
        },
        "rvl-cdip": {
            "path": "raw/rvl-cdip",
            "type": "directory",
            "phase": 1,
            "required": False,
            "description": "RVL-CDIP document classification",
        },
        "tobacco800": {
            "path": "raw/tobacco800",
            "type": "directory",
            "phase": 1,
            "required": False,
            "description": "Tobacco800 document classification",
        },
    },
}


def get_directory_size(path: Path) -> int:
    """Calculate directory size in bytes."""
    total_size = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
    except Exception as e:
        logger.warning(f"Error calculating size for {path}: {e}")
        return 0
    return total_size


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def count_files(path: Path, pattern: str = "*") -> int:
    """Count files matching pattern in directory."""
    try:
        return len(list(path.rglob(pattern)))
    except Exception:
        return 0


def validate_dataset(
    dataset_name: str, config: dict, data_root: Path
) -> tuple[str, dict]:
    """
    Validate a single dataset.

    Returns:
        Tuple of (status, details_dict)
        status: 'found', 'missing', 'symlink_broken', 'empty'
    """
    dataset_path = data_root / config["path"]

    # Check if exists
    if not dataset_path.exists():
        return "missing", {
            "path": str(dataset_path),
            "required": config["required"],
            "phase": config["phase"],
        }

    # Check if symlink
    if dataset_path.is_symlink():
        target = dataset_path.resolve()
        if not target.exists():
            return "symlink_broken", {
                "path": str(dataset_path),
                "target": str(target),
                "required": config["required"],
                "phase": config["phase"],
            }
        # Symlink is valid
        size = get_directory_size(target)
        file_count = count_files(target)
        return "found", {
            "path": str(dataset_path),
            "type": "symlink",
            "target": str(target),
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],
        }

    # Regular directory
    if dataset_path.is_dir():
        size = get_directory_size(dataset_path)
        file_count = count_files(dataset_path)

        # Check if empty
        if file_count == 0:
            return "empty", {
                "path": str(dataset_path),
                "required": config["required"],
                "phase": config["phase"],
            }

        return "found", {
            "path": str(dataset_path),
            "type": "directory",
            "size": size,
            "size_human": format_size(size),
            "file_count": file_count,
            "required": config["required"],
            "phase": config["phase"],
        }

    return "unknown", {
        "path": str(dataset_path),
        "required": config["required"],
        "phase": config["phase"],
    }


def validate_all_datasets(data_root: Path) -> dict:
    """Validate all expected datasets."""
    results = {
        "summary": {
            "total": 0,
            "found": 0,
            "missing": 0,
            "empty": 0,
            "broken": 0,
            "total_size": 0,
        },
        "benchmarks": {},
        "raw": {},
        "required_missing": [],
    }

    # Validate benchmark datasets
    for name, config in EXPECTED_DATASETS["benchmarks"].items():
        results["summary"]["total"] += 1
        status, details = validate_dataset(name, config, data_root)
        results["benchmarks"][name] = {
            "status": status,
            "details": details,
            "description": config["description"],
        }

        if status == "found":
            results["summary"]["found"] += 1
            results["summary"]["total_size"] += details.get("size", 0)
        elif status == "missing":
            results["summary"]["missing"] += 1
            if config["required"]:
                results["required_missing"].append(name)
        elif status == "empty":
            results["summary"]["empty"] += 1
        elif status == "symlink_broken":
            results["summary"]["broken"] += 1
            if config["required"]:
                results["required_missing"].append(name)

    # Validate raw datasets
    for name, config in EXPECTED_DATASETS["raw"].items():
        results["summary"]["total"] += 1
        status, details = validate_dataset(name, config, data_root)
        results["raw"][name] = {
            "status": status,
            "details": details,
            "description": config["description"],
        }

        if status == "found":
            results["summary"]["found"] += 1
            results["summary"]["total_size"] += details.get("size", 0)
        elif status == "missing":
            results["summary"]["missing"] += 1
            if config["required"]:
                results["required_missing"].append(name)
        elif status == "empty":
            results["summary"]["empty"] += 1
        elif status == "symlink_broken":
            results["summary"]["broken"] += 1
            if config["required"]:
                results["required_missing"].append(name)

    return results


def print_validation_report(results: dict):
    """Print formatted validation report."""
    print("\n" + "=" * 80)
    print("DATASET VALIDATION REPORT")
    print("=" * 80)

    # Summary
    summary = results["summary"]
    print("\n📊 SUMMARY")
    print("-" * 80)
    print(f"Total datasets expected: {summary['total']}")
    print(f"✅ Found: {summary['found']}")
    print(f"❌ Missing: {summary['missing']}")
    print(f"⚠️  Empty: {summary['empty']}")
    print(f"🔗 Broken symlinks: {summary['broken']}")
    print(f"💾 Total size: {format_size(summary['total_size'])}")

    # Required missing
    if results["required_missing"]:
        print("\n❗ REQUIRED DATASETS MISSING:")
        print("-" * 80)
        for name in results["required_missing"]:
            print(f"  - {name}")

    # Benchmark datasets
    print("\n📚 BENCHMARK DATASETS")
    print("-" * 80)
    for name, info in results["benchmarks"].items():
        status = info["status"]
        details = info["details"]

        if status == "found":
            emoji = "✅"
            size_info = f" ({details['size_human']}, {details['file_count']} files)"
            type_info = f" [{details['type']}]"
        elif status == "missing":
            emoji = "❌"
            size_info = ""
            type_info = ""
        elif status == "empty":
            emoji = "⚠️"
            size_info = " (empty directory)"
            type_info = ""
        elif status == "symlink_broken":
            emoji = "🔗"
            size_info = " (broken symlink)"
            type_info = ""
        else:
            emoji = "❓"
            size_info = ""
            type_info = ""

        required_marker = " [REQUIRED]" if details["required"] else ""
        phase_info = f" [Phase {details['phase']}]"

        print(
            f"  {emoji} {name:<20} {status:<15}{size_info}{type_info}{phase_info}{required_marker}"
        )
        print(f"     {info['description']}")
        if status == "found" and details["type"] == "symlink":
            print(f"     → {details['target']}")

    # Raw datasets
    print("\n📁 RAW DATASETS")
    print("-" * 80)
    for name, info in results["raw"].items():
        status = info["status"]
        details = info["details"]

        if status == "found":
            emoji = "✅"
            size_info = f" ({details['size_human']}, {details['file_count']} files)"
        elif status == "missing":
            emoji = "❌"
            size_info = ""
        elif status == "empty":
            emoji = "⚠️"
            size_info = " (empty directory)"
        else:
            emoji = "❓"
            size_info = ""

        phase_info = f" [Phase {details['phase']}]"

        print(f"  {emoji} {name:<20} {status:<15}{size_info}{phase_info}")
        print(f"     {info['description']}")

    print("\n" + "=" * 80)


def save_validation_json(results: dict, output_path: Path):
    """Save validation results to JSON file."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Validation results saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate dataset presence and status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root", default="data", help="Root data directory (default: data)"
    )
    parser.add_argument("--output-json", help="Save validation results to JSON file")
    parser.add_argument(
        "--upload-to-gcs",
        action="store_true",
        help="Upload datasets to GCS after validation (not yet implemented)",
    )

    args = parser.parse_args()

    # Get data root
    if os.path.isabs(args.data_root):
        data_root = Path(args.data_root)
    else:
        project_root = Path(__file__).parent.parent
        data_root = project_root / args.data_root

    if not data_root.exists():
        logger.error(f"Data directory not found: {data_root}")
        return 1

    logger.info(f"Validating datasets in: {data_root.absolute()}")

    # Validate all datasets
    results = validate_all_datasets(data_root)

    # Print report
    print_validation_report(results)

    # Save JSON if requested
    if args.output_json:
        output_path = Path(args.output_json)
        save_validation_json(results, output_path)

    # Upload to GCS if requested
    if args.upload_to_gcs:
        logger.warning(
            "GCS upload not yet implemented - use scripts/upload_datasets_to_gcs.sh"
        )

    # Exit with error if required datasets are missing
    if results["required_missing"]:
        logger.error(
            f"Validation failed: {len(results['required_missing'])} required datasets missing"
        )
        return 1

    logger.info("✅ Validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
