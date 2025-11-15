#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Validate training run artifact completeness.

Checks that a training run directory contains all required metadata files
and model artifacts for reproducibility.

Usage:
    # Validate local directory
    python scripts/validate_artifacts.py /path/to/run/directory

    # Validate from GCS
    python scripts/validate_artifacts.py \\
        --gcs-bucket rag-pipeline-models \\
        --project image-preprocessing-detector \\
        --model resnet50_teacher \\
        --run-id 2025-11-15T01-20Z_run-abc123

    # Validate with strict mode (fail on warnings)
    python scripts/validate_artifacts.py /path/to/run --strict
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


def validate_metadata_file(file_path: Path, file_type: str) -> tuple[bool, str]:
    """Validate a metadata file exists and is valid.

    Args:
        file_path: Path to metadata file
        file_type: Type of file (yaml, json, text)

    Returns:
        Tuple of (valid, message)
    """
    if not file_path.exists():
        return False, f"❌ MISSING: {file_path.name}"

    # Check file is not empty
    if file_path.stat().st_size == 0:
        return False, f"❌ EMPTY: {file_path.name}"

    # Validate format
    try:
        if file_type == "yaml":
            with open(file_path) as f:
                data = yaml.safe_load(f)
            if not data:
                return False, f"❌ INVALID: {file_path.name} (empty YAML)"
        elif file_type == "json":
            with open(file_path) as f:
                data = json.load(f)
            if not data:
                return False, f"❌ INVALID: {file_path.name} (empty JSON)"
        elif file_type == "text":
            with open(file_path) as f:
                content = f.read().strip()
            if not content:
                return False, f"❌ INVALID: {file_path.name} (empty file)"
    except Exception as e:
        return False, f"❌ INVALID: {file_path.name} ({e!s})"

    size_kb = file_path.stat().st_size / 1024
    return True, f"✅ VALID: {file_path.name:<30} ({size_kb:>6.2f} KB)"


def validate_model_file(file_path: Path) -> tuple[bool, str]:
    """Validate a model checkpoint file.

    Args:
        file_path: Path to model file

    Returns:
        Tuple of (valid, message)
    """
    if not file_path.exists():
        return False, f"❌ MISSING: {file_path.name}"

    # Check file is not empty
    if file_path.stat().st_size == 0:
        return False, f"❌ EMPTY: {file_path.name}"

    # Check minimum size (should be at least 1MB for a real model)
    min_size_mb = 1
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb < min_size_mb:
        return (
            False,
            f"⚠️  SUSPICIOUS: {file_path.name} ({size_mb:.2f} MB < {min_size_mb} MB)",
        )

    return True, f"✅ VALID: {file_path.name:<30} ({size_mb:>6.2f} MB)"


def validate_artifacts(artifact_dir: str, strict: bool = False) -> dict[str, Any]:
    """Validate all artifacts in a training run directory.

    Args:
        artifact_dir: Directory containing training run artifacts
        strict: If True, warnings are treated as errors

    Returns:
        Dictionary with validation results

    Raises:
        SystemExit: If validation fails (status code 1)
    """
    print("=" * 80)
    print("🔍 Validating Training Run Artifacts")
    print("=" * 80)
    print(f"Directory: {artifact_dir}")
    print(f"Strict mode: {strict}")
    print()

    path = Path(artifact_dir)
    if not path.exists():
        print(f"❌ ERROR: Directory does not exist: {artifact_dir}")
        sys.exit(1)

    results = {
        "required_files": [],
        "optional_files": [],
        "model_files": [],
        "errors": [],
        "warnings": [],
    }

    # =========================================================================
    # Required Metadata Files
    # =========================================================================
    print("📋 Required Metadata Files:")
    print("-" * 80)

    required_files = [
        ("training_config.yaml", "yaml"),
        ("commit_hash.txt", "text"),
        ("dataset_version.txt", "text"),
        ("env_info.txt", "text"),
    ]

    for filename, file_type in required_files:
        file_path = path / filename
        valid, message = validate_metadata_file(file_path, file_type)
        print(f"  {message}")

        results["required_files"].append(
            {"file": filename, "valid": valid, "message": message}
        )

        if not valid:
            results["errors"].append(message)

    print()

    # =========================================================================
    # Optional Metadata Files
    # =========================================================================
    print("📊 Optional Metadata Files:")
    print("-" * 80)

    optional_files = [("metrics.json", "json")]

    for filename, file_type in optional_files:
        file_path = path / filename
        if file_path.exists():
            valid, message = validate_metadata_file(file_path, file_type)
            print(f"  {message}")
            results["optional_files"].append(
                {"file": filename, "valid": valid, "message": message}
            )
            if not valid:
                results["warnings"].append(message)
        else:
            message = f"⚠️  MISSING: {filename} (optional but recommended)"
            print(f"  {message}")
            results["warnings"].append(message)

    print()

    # =========================================================================
    # Model Files
    # =========================================================================
    print("🧠 Model Files:")
    print("-" * 80)

    # Find all .pth, .pt, .onnx files
    model_extensions = ["*.pth", "*.pt", "*.onnx"]
    model_files = []
    for ext in model_extensions:
        model_files.extend(path.glob(ext))

    if not model_files:
        message = "❌ ERROR: No model files found (.pth, .pt, .onnx)"
        print(f"  {message}")
        results["errors"].append(message)
    else:
        for model_file in sorted(model_files):
            valid, message = validate_model_file(model_file)
            print(f"  {message}")
            results["model_files"].append(
                {"file": model_file.name, "valid": valid, "message": message}
            )
            if not valid:
                if "SUSPICIOUS" in message:
                    results["warnings"].append(message)
                else:
                    results["errors"].append(message)

    print()

    # =========================================================================
    # Additional Checks
    # =========================================================================
    print("🔬 Additional Validation:")
    print("-" * 80)

    # Check git status
    commit_hash_file = path / "commit_hash.txt"
    if commit_hash_file.exists():
        with open(commit_hash_file) as f:
            commit_info = f.read()
        if "dirty" in commit_info:
            message = "⚠️  WARNING: Model trained from dirty git state (uncommitted changes)"
            print(f"  {message}")
            results["warnings"].append(message)
        else:
            print("  ✅ Git state: clean (reproducible)")

    # Check config completeness
    config_file = path / "training_config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)

        required_config_keys = ["model", "training"]
        missing_keys = [key for key in required_config_keys if key not in config]

        if missing_keys:
            message = f"⚠️  WARNING: Config missing keys: {missing_keys}"
            print(f"  {message}")
            results["warnings"].append(message)
        else:
            print("  ✅ Config structure: complete")

    # Check metrics
    metrics_file = path / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)

        if not metrics:
            message = "⚠️  WARNING: metrics.json is empty"
            print(f"  {message}")
            results["warnings"].append(message)
        else:
            print(f"  ✅ Metrics: {len(metrics)} metrics recorded")

    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 80)
    print("📈 Validation Summary")
    print("=" * 80)

    num_errors = len(results["errors"])
    num_warnings = len(results["warnings"])
    num_model_files = len(results["model_files"])

    print(f"Required files: {len(results['required_files'])} checked")
    print(f"Model files: {num_model_files} found")
    print(f"Errors: {num_errors}")
    print(f"Warnings: {num_warnings}")
    print()

    if num_errors > 0:
        print("❌ VALIDATION FAILED")
        print()
        print("Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
        print()
        return results

    if num_warnings > 0:
        if strict:
            print("❌ VALIDATION FAILED (strict mode)")
            print()
            print("Warnings (treated as errors in strict mode):")
            for warning in results["warnings"]:
                print(f"  - {warning}")
            print()
            return results
        else:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print()
            print("Warnings:")
            for warning in results["warnings"]:
                print(f"  - {warning}")
            print()
            print("✅ All required artifacts present")
            print("=" * 80)
            return results

    print("✅ VALIDATION PASSED")
    print()
    print("All required artifacts present and valid!")
    print("This run is ready for promotion to Hugging Face Hub.")
    print("=" * 80)

    return results


def download_and_validate_gcs(
    bucket_name: str, project_name: str, model_name: str, run_id: str, strict: bool
) -> None:
    """Download artifacts from GCS and validate.

    Args:
        bucket_name: GCS bucket name
        project_name: Project name
        model_name: Model name
        run_id: Run identifier
        strict: Strict validation mode
    """
    from google.cloud import storage

    print("📥 Downloading artifacts from GCS...")
    print()

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    gcs_prefix = f"{project_name}/{model_name}/runs/{run_id}/"
    print(f"GCS path: gs://{bucket_name}/{gcs_prefix}")

    # Download to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / run_id

        # Download all blobs
        blobs = list(bucket.list_blobs(prefix=gcs_prefix))
        if not blobs:
            print(f"❌ ERROR: No artifacts found at gs://{bucket_name}/{gcs_prefix}")
            sys.exit(1)

        print(f"Downloading {len(blobs)} files...")
        for blob in blobs:
            rel_path = blob.name.replace(gcs_prefix, "")
            if not rel_path:  # Skip directory markers
                continue

            local_file = local_path / rel_path
            local_file.parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(str(local_file))

        print(f"✅ Downloaded to {local_path}")
        print()

        # Validate
        results = validate_artifacts(str(local_path), strict=strict)

        # Exit with appropriate code
        num_errors = len(results["errors"])
        num_warnings = len(results["warnings"])

        if num_errors > 0:
            sys.exit(1)
        if strict and num_warnings > 0:
            sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate training run artifact completeness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "artifact_dir",
        nargs="?",
        help="Local directory containing artifacts (or use --gcs-* flags)",
    )

    parser.add_argument(
        "--gcs-bucket",
        help="GCS bucket name (for validating from GCS)",
    )
    parser.add_argument(
        "--project",
        default="image-preprocessing-detector",
        help="Project name (default: image-preprocessing-detector)",
    )
    parser.add_argument(
        "--model",
        help="Model name (e.g., resnet50_teacher)",
    )
    parser.add_argument(
        "--run-id",
        help="Training run ID",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: warnings are treated as errors",
    )

    args = parser.parse_args()

    # Validate from GCS
    if args.gcs_bucket:
        if not args.model or not args.run_id:
            parser.error("--model and --run-id required when using --gcs-bucket")

        download_and_validate_gcs(
            bucket_name=args.gcs_bucket,
            project_name=args.project,
            model_name=args.model,
            run_id=args.run_id,
            strict=args.strict,
        )
        return

    # Validate local directory
    if not args.artifact_dir:
        parser.error("artifact_dir is required (or use --gcs-bucket)")

    results = validate_artifacts(args.artifact_dir, strict=args.strict)

    # Exit with appropriate code
    num_errors = len(results["errors"])
    num_warnings = len(results["warnings"])

    if num_errors > 0:
        sys.exit(1)
    if args.strict and num_warnings > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
