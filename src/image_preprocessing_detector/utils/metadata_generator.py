# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Metadata generation for reproducible ML training runs.

Generates required metadata files for each training run:
- commit_hash.txt: Git commit hash of training code
- dataset_version.txt: Dataset version/hash
- env_info.txt: Python, CUDA, and library versions
- training_config.yaml: Training hyperparameters
- metrics.json: Training and evaluation metrics

Usage:
    from image_preprocessing_detector.utils.metadata_generator import generate_run_metadata

    generate_run_metadata(
        output_dir="/root/output",
        config=training_config,
        dataset_version="v1.2.0",
        metrics={"train_loss": 0.15, "val_acc": 0.92}
    )
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


def get_git_commit_hash(repo_path: str = ".") -> str:
    """Get current Git commit hash.

    Args:
        repo_path: Path to git repository (default: current directory)

    Returns:
        Full commit hash (40 characters)

    Raises:
        RuntimeError: If not in a git repository or git command fails
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get git commit hash: {e.stderr}") from e


def get_git_branch(repo_path: str = ".") -> str:
    """Get current Git branch name.

    Args:
        repo_path: Path to git repository

    Returns:
        Branch name
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_status(repo_path: str = ".") -> str:
    """Check if repository has uncommitted changes.

    Args:
        repo_path: Path to git repository

    Returns:
        "clean" or "dirty" (has uncommitted changes)
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return "dirty" if result.stdout.strip() else "clean"
    except subprocess.CalledProcessError:
        return "unknown"


def generate_commit_hash_file(output_dir: str, repo_path: str = ".") -> str:
    """Generate commit_hash.txt file.

    Args:
        output_dir: Directory to write file
        repo_path: Path to git repository

    Returns:
        Path to generated file

    Example content:
        commit: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
        branch: feature/phase2-iqa
        status: clean
        timestamp: 2025-11-15T01:20:35Z
    """
    commit_hash = get_git_commit_hash(repo_path)
    branch = get_git_branch(repo_path)
    status = get_git_status(repo_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = f"""commit: {commit_hash}
branch: {branch}
status: {status}
timestamp: {timestamp}
"""

    file_path = os.path.join(output_dir, "commit_hash.txt")
    with open(file_path, "w") as f:
        f.write(content)

    return file_path


def generate_dataset_version_file(
    output_dir: str,
    dataset_version: str,
    dataset_info: Optional[dict[str, Any]] = None,
) -> str:
    """Generate dataset_version.txt file.

    Args:
        output_dir: Directory to write file
        dataset_version: Dataset version identifier (e.g., "v1.2.0", "sha256:abc123...")
        dataset_info: Additional dataset metadata (optional)

    Returns:
        Path to generated file

    Example content:
        version: v1.2.0
        num_train_samples: 35000
        num_val_samples: 5000
        labels: ["blur", "skew", "contrast", "noise"]
        created: 2025-11-01T00:00:00Z
    """
    content = f"version: {dataset_version}\n"

    if dataset_info:
        for key, value in dataset_info.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            content += f"{key}: {value}\n"

    file_path = os.path.join(output_dir, "dataset_version.txt")
    with open(file_path, "w") as f:
        f.write(content)

    return file_path


def get_cuda_version() -> str:
    """Get CUDA version if available.

    Returns:
        CUDA version string or "N/A"
    """
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Extract version from output like "release 11.8, V11.8.89"
        for line in result.stdout.split("\n"):
            if "release" in line.lower():
                return line.split("release")[-1].split(",")[0].strip()
        return "N/A"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"


def get_installed_packages() -> dict[str, str]:
    """Get versions of key ML packages.

    Returns:
        Dictionary of package names to versions
    """
    packages = {}

    # Core ML packages
    try:
        import torch

        packages["torch"] = torch.__version__
    except ImportError:
        packages["torch"] = "N/A"

    try:
        import torchvision

        packages["torchvision"] = torchvision.__version__
    except ImportError:
        packages["torchvision"] = "N/A"

    try:
        import timm

        packages["timm"] = timm.__version__
    except ImportError:
        packages["timm"] = "N/A"

    try:
        import albumentations

        packages["albumentations"] = albumentations.__version__
    except ImportError:
        packages["albumentations"] = "N/A"

    try:
        import onnx

        packages["onnx"] = onnx.__version__
    except ImportError:
        packages["onnx"] = "N/A"

    return packages


def generate_env_info_file(output_dir: str) -> str:
    """Generate env_info.txt file with environment details.

    Args:
        output_dir: Directory to write file

    Returns:
        Path to generated file

    Example content:
        python: 3.12.0
        platform: Linux-6.5.0-1025-gcp-x86_64
        cuda: 11.8
        torch: 2.1.0
        torchvision: 0.16.0
        timm: 0.9.12
        albumentations: 1.3.1
        onnx: 1.14.0
    """
    cuda_version = get_cuda_version()
    packages = get_installed_packages()

    content = f"""python: {sys.version.split()[0]}
platform: {platform.platform()}
cuda: {cuda_version}
"""

    for package, version in packages.items():
        content += f"{package}: {version}\n"

    file_path = os.path.join(output_dir, "env_info.txt")
    with open(file_path, "w") as f:
        f.write(content)

    return file_path


def generate_training_config_file(
    output_dir: str,
    config: dict[str, Any],
) -> str:
    """Generate training_config.yaml file.

    Args:
        output_dir: Directory to write file
        config: Training configuration dictionary

    Returns:
        Path to generated file

    Example config:
        {
            "model": {
                "architecture": "resnet50",
                "pretrained": True,
                "num_classes": 4
            },
            "training": {
                "batch_size": 128,
                "epochs": 100,
                "learning_rate": 0.001
            }
        }
    """
    file_path = os.path.join(output_dir, "training_config.yaml")
    with open(file_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    return file_path


def generate_metrics_file(
    output_dir: str,
    metrics: dict[str, Any],
) -> str:
    """Generate metrics.json file.

    Args:
        output_dir: Directory to write file
        metrics: Training and evaluation metrics

    Returns:
        Path to generated file

    Example metrics:
        {
            "final_train_loss": 0.15,
            "final_val_loss": 0.18,
            "val_accuracy": 0.92,
            "val_macro_f1": 0.91,
            "best_epoch": 87,
            "total_epochs": 100,
            "training_time_seconds": 3600,
            "inference_latency_ms": 12.5
        }
    """
    file_path = os.path.join(output_dir, "metrics.json")
    with open(file_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return file_path


def generate_run_metadata(
    output_dir: str,
    config: dict[str, Any],
    dataset_version: str,
    metrics: Optional[dict[str, Any]] = None,
    dataset_info: Optional[dict[str, Any]] = None,
    repo_path: str = ".",
) -> dict[str, str]:
    """Generate all required metadata files for a training run.

    This is the main entry point for metadata generation.
    Creates all required files for reproducibility.

    Args:
        output_dir: Directory to write metadata files
        config: Training configuration dictionary
        dataset_version: Dataset version identifier
        metrics: Training/evaluation metrics (optional, can be added later)
        dataset_info: Additional dataset metadata (optional)
        repo_path: Path to git repository

    Returns:
        Dictionary mapping metadata type to file path

    Example:
        >>> metadata = generate_run_metadata(
        ...     output_dir="/root/output",
        ...     config={"model": {"architecture": "resnet50"}, ...},
        ...     dataset_version="v1.2.0",
        ...     metrics={"val_accuracy": 0.92, ...},
        ... )
        >>> print(metadata)
        {
            "commit_hash": "/root/output/commit_hash.txt",
            "dataset_version": "/root/output/dataset_version.txt",
            "env_info": "/root/output/env_info.txt",
            "training_config": "/root/output/training_config.yaml",
            "metrics": "/root/output/metrics.json"
        }
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    files = {}

    # Generate required metadata files
    print("📝 Generating training run metadata...")

    files["commit_hash"] = generate_commit_hash_file(output_dir, repo_path)
    print(f"  ✅ Generated commit_hash.txt")

    files["dataset_version"] = generate_dataset_version_file(
        output_dir, dataset_version, dataset_info
    )
    print(f"  ✅ Generated dataset_version.txt")

    files["env_info"] = generate_env_info_file(output_dir)
    print(f"  ✅ Generated env_info.txt")

    files["training_config"] = generate_training_config_file(output_dir, config)
    print(f"  ✅ Generated training_config.yaml")

    if metrics:
        files["metrics"] = generate_metrics_file(output_dir, metrics)
        print(f"  ✅ Generated metrics.json")

    print(f"\n✅ Metadata generation complete: {len(files)} files created")

    return files


def generate_run_id(prefix: str = "run") -> str:
    """Generate a unique run identifier with timestamp.

    Args:
        prefix: Prefix for run ID (default: "run")

    Returns:
        Run ID in format: YYYY-MM-DDTHH-MMZ_{prefix}-{random}

    Example:
        >>> run_id = generate_run_id("iqa-phase2")
        >>> print(run_id)
        2025-11-15T01-20Z_iqa-phase2-a1b2c3
    """
    import secrets

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
    random_suffix = secrets.token_hex(3)
    return f"{timestamp}_{prefix}-{random_suffix}"
