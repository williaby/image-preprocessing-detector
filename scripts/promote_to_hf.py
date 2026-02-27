#!/usr/bin/env python3
#

"""Promote a model from GCS to Hugging Face Hub.

This script implements the manual promotion workflow:
1. Download artifacts from GCS canonical storage
2. Validate artifacts and metrics meet promotion criteria
3. Create/update Hugging Face Hub repository
4. Upload model files with semantic versioning
5. Generate model card

Usage:
    # Promote a specific run
    python scripts/promote_to_hf.py \\
        --gcs-bucket rag-pipeline-models \\
        --project image-preprocessing-detector \\
        --model resnet50_teacher \\
        --run-id 2025-11-15T01-20Z_run-abc123 \\
        --hf-repo williaby/doc-preproc-resnet50-teacher \\
        --version v1.0.0

    # List available runs
    python scripts/promote_to_hf.py \\
        --list-runs \\
        --gcs-bucket rag-pipeline-models \\
        --project image-preprocessing-detector \\
        --model resnet50_teacher

    # Dry run (validate without uploading)
    python scripts/promote_to_hf.py \\
        --dry-run \\
        --gcs-bucket rag-pipeline-models \\
        --project image-preprocessing-detector \\
        --model resnet50_teacher \\
        --run-id 2025-11-15T01-20Z_run-abc123 \\
        --hf-repo williaby/doc-preproc-resnet50-teacher \\
        --version v1.0.0

Environment Variables:
    HF_TOKEN: Hugging Face API token (required for push)
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from google.cloud import storage
from huggingface_hub import HfApi, create_repo

# File name constants
_TRAINING_CONFIG_FILE = "training_config.yaml"
_COMMIT_HASH_FILE = "commit_hash.txt"
_DATASET_VERSION_FILE = "dataset_version.txt"
_ENV_INFO_FILE = "env_info.txt"
_METRICS_FILE = "metrics.json"


def download_run_artifacts(
    bucket_name: str,
    project_name: str,
    model_name: str,
    run_id: str,
    local_dir: str,
) -> str:
    """Download training run artifacts from GCS.

    Args:
        bucket_name: GCS bucket name
        project_name: Project name
        model_name: Model name
        run_id: Run identifier
        local_dir: Local directory to download to

    Returns:
        Path to downloaded artifacts
    """
    print("=" * 80)
    print("📥 Downloading artifacts from GCS")
    print("=" * 80)

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    gcs_prefix = f"{project_name}/{model_name}/runs/{run_id}/"
    local_path = Path(local_dir) / run_id

    print(f"GCS path: gs://{bucket_name}/{gcs_prefix}")
    print(f"Local path: {local_path}")
    print()

    # Create local directory
    local_path.mkdir(parents=True, exist_ok=True)

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
        size_mb = blob.size / (1024 * 1024)
        print(f"  ✅ {rel_path:<40} ({size_mb:>6.2f} MB)")

    print(f"\n✅ Download complete: {local_path}")
    return str(local_path)


def validate_artifacts(artifact_dir: str) -> dict[str, Any]:
    """Validate that required artifacts are present.

    Args:
        artifact_dir: Directory containing artifacts

    Returns:
        Dictionary with validation results and loaded metadata

    Raises:
        ValueError: If required artifacts are missing
    """
    print()
    print("=" * 80)
    print("✅ Validating artifacts")
    print("=" * 80)

    path = Path(artifact_dir)

    # Check required files
    required_files = [
        _TRAINING_CONFIG_FILE,
        _COMMIT_HASH_FILE,
        _DATASET_VERSION_FILE,
        _ENV_INFO_FILE,
    ]

    missing_files = [file for file in required_files if not (path / file).exists()]

    if missing_files:
        print(f"❌ ERROR: Missing required files: {missing_files}")
        raise ValueError(f"Missing required artifacts: {missing_files}")

    print("✅ All required metadata files present")

    # Load metadata
    metadata = {}

    # Load config
    with open(path / _TRAINING_CONFIG_FILE) as f:
        metadata["config"] = yaml.safe_load(f)

    # Load metrics if present
    if (path / _METRICS_FILE).exists():
        with open(path / _METRICS_FILE) as f:
            metadata["metrics"] = json.load(f)
    else:
        print("⚠️  WARNING: metrics.json not found")
        metadata["metrics"] = {}

    # Load commit hash
    with open(path / _COMMIT_HASH_FILE) as f:
        metadata["commit_info"] = f.read()

    # Load dataset version
    with open(path / _DATASET_VERSION_FILE) as f:
        metadata["dataset_version"] = f.read()

    # Load env info
    with open(path / _ENV_INFO_FILE) as f:
        metadata["env_info"] = f.read()

    # Find model files
    model_files = list(path.glob("*.pth")) + list(path.glob("*.pt"))
    if not model_files:
        print("⚠️  WARNING: No .pth/.pt model files found")
    else:
        print(f"✅ Found {len(model_files)} model file(s):")
        for f in model_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.2f} MB)")

    metadata["model_files"] = [str(f) for f in model_files]

    return metadata


def check_promotion_criteria(metadata: dict[str, Any]) -> bool:
    """Check if model meets promotion criteria.

    Args:
        metadata: Model metadata from validation

    Returns:
        True if model meets criteria, False otherwise
    """
    print()
    print("=" * 80)
    print("📋 Checking promotion criteria")
    print("=" * 80)

    criteria_met = True

    # Check for metrics
    metrics = metadata.get("metrics", {})
    if not metrics:
        print("⚠️  WARNING: No metrics found - manual review required")
        criteria_met = False
    else:
        # Display key metrics
        print("Metrics:")
        for key, value in metrics.items():
            print(f"  - {key}: {value}")

    # Check for model files
    if not metadata.get("model_files"):
        print("❌ ERROR: No model files found")
        criteria_met = False

    # Reproducibility check
    if metadata.get("commit_info") and "dirty" in metadata["commit_info"]:
        print("⚠️  WARNING: Model trained from dirty git state")
        criteria_met = False

    print()
    if criteria_met:
        print("✅ All promotion criteria met")
    else:
        print("⚠️  Some criteria not met - proceed with caution")

    return criteria_met


def generate_model_card(
    model_name: str,
    version: str,
    metadata: dict[str, Any],
    _template: str | None = None,
) -> str:
    """Generate Hugging Face model card (README.md).

    Args:
        model_name: Model name
        version: Semantic version
        metadata: Model metadata
        template: Optional custom template

    Returns:
        Model card content
    """
    config = metadata.get("config", {})
    metrics = metadata.get("metrics", {})

    # Extract key metrics
    accuracy = metrics.get("val_accuracy", metrics.get("accuracy", "N/A"))
    macro_f1 = metrics.get("val_macro_f1", metrics.get("macro_f1", "N/A"))

    model_card = f"""# Model: {model_name}

## Version
{version}

## Overview
This model was trained for the Image Preprocessing Detector project.
It provides image quality assessment and document preprocessing capabilities.

## Intended Use
- Document preprocessing for RAG pipelines
- Image quality assessment
- Multi-label classification for image defects

## Training Details

### Architecture
- Model: {config.get("model", {}).get("architecture", "N/A")}
- Input size: {config.get("model", {}).get("input_size", "N/A")}
- Number of classes: {config.get("model", {}).get("num_classes", "N/A")}

### Training Configuration
- Batch size: {config.get("training", {}).get("batch_size", "N/A")}
- Epochs: {config.get("training", {}).get("epochs", "N/A")}
- Learning rate: {config.get("training", {}).get("learning_rate", "N/A")}
- Optimizer: {config.get("training", {}).get("optimizer", "Adam")}

### Dataset
{metadata.get("dataset_version", "N/A")}

## Performance

### Metrics
- Accuracy: {accuracy}
- Macro F1: {macro_f1}

Full metrics:
```json
{json.dumps(metrics, indent=2)}
```

## Environment
{metadata.get("env_info", "N/A")}

## Reproducibility
{metadata.get("commit_info", "N/A")}

## Usage

```python
import torch
from torchvision import transforms

# Load model
model = torch.load("model_final.pth", weights_only=True)
model.eval()

# Prepare image
transform = transforms.Compose([
    transforms.Resize({config.get("model", {}).get("input_size", 224)}),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Inference
with torch.no_grad():
    output = model(image)
```

## License
MIT

## Citation
```
@software{{image_preprocessing_detector,
  author = {{Williams, Byron}},
  title = {{Image Preprocessing Detector}},
  year = {{2025}},
  version = {{{version}}},
}}
```
"""

    return model_card


def push_to_huggingface(
    artifact_dir: str,
    hf_repo: str,
    version: str,
    metadata: dict[str, Any],
    token: str,
    private: bool = True,
    dry_run: bool = False,
) -> None:
    """Push model to Hugging Face Hub.

    Args:
        artifact_dir: Directory containing artifacts
        hf_repo: Hugging Face repository (e.g., "username/model-name")
        version: Semantic version tag
        metadata: Model metadata
        token: Hugging Face API token
        private: Create private repository
        dry_run: If True, validate but don't push
    """
    print()
    print("=" * 80)
    print("🤗 Pushing to Hugging Face Hub")
    print("=" * 80)

    if dry_run:
        print("🔍 DRY RUN MODE - Will not actually push")
        print()

    path = Path(artifact_dir)

    # Generate model card
    model_card = generate_model_card(
        model_name=hf_repo.split("/")[-1],
        version=version,
        metadata=metadata,
    )

    # Save model card
    readme_path = path / "README.md"
    with open(readme_path, "w") as f:
        f.write(model_card)
    print(f"✅ Generated README.md ({len(model_card)} chars)")

    if dry_run:
        print("\n📄 Model Card Preview:")
        print("-" * 80)
        print(model_card[:500] + "..." if len(model_card) > 500 else model_card)
        print("-" * 80)
        print("\n✅ Dry run complete - no changes made")
        return

    # Create/get repository
    api = HfApi()

    print(f"\n📦 Repository: {hf_repo}")
    print(f"   Private: {private}")
    print(f"   Version: {version}")
    print()

    try:
        repo_url = create_repo(
            repo_id=hf_repo,
            token=token,
            private=private,
            exist_ok=True,
        )
        print(f"✅ Repository ready: {repo_url}")
    except Exception as e:
        print(f"❌ ERROR: Failed to create repository: {e}")
        sys.exit(1)

    # Upload files
    print("\n📤 Uploading files...")

    # Upload model files
    for model_file in metadata.get("model_files", []):
        filename = Path(model_file).name
        print(f"  Uploading {filename}...")
        api.upload_file(
            path_or_fileobj=model_file,
            path_in_repo=filename,
            repo_id=hf_repo,
            token=token,
        )
        print(f"  ✅ Uploaded {filename}")

    # Upload README
    print("  Uploading README.md...")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=hf_repo,
        token=token,
    )
    print("  ✅ Uploaded README.md")

    # Upload metadata files
    metadata_files = [
        _TRAINING_CONFIG_FILE,
        _METRICS_FILE,
        _COMMIT_HASH_FILE,
        _DATASET_VERSION_FILE,
        _ENV_INFO_FILE,
    ]

    for filename in metadata_files:
        file_path = path / filename
        if file_path.exists():
            print(f"  Uploading {filename}...")
            api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=filename,
                repo_id=hf_repo,
                token=token,
            )
            print(f"  ✅ Uploaded {filename}")

    # Create version tag
    print(f"\n🏷️  Creating version tag: {version}")
    try:
        api.create_tag(
            repo_id=hf_repo,
            tag=version,
            token=token,
            tag_message=f"Release {version}",
        )
        print(f"✅ Created tag {version}")
    except Exception as e:
        print(f"⚠️  WARNING: Failed to create tag: {e}")

    print()
    print("=" * 80)
    print("✅ Push complete!")
    print("=" * 80)
    print(f"🤗 Model: https://huggingface.co/{hf_repo}")
    print(f"📌 Version: {version}")
    print("=" * 80)


def list_available_runs(bucket_name: str, project_name: str, model_name: str) -> None:
    """List available training runs in GCS.

    Args:
        bucket_name: GCS bucket name
        project_name: Project name
        model_name: Model name
    """
    print("=" * 80)
    print("📋 Available Training Runs")
    print("=" * 80)

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    prefix = f"{project_name}/{model_name}/runs/"
    print(f"GCS path: gs://{bucket_name}/{prefix}")
    print()

    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

    # Extract run IDs
    run_ids = []
    for prefix_path in blobs.prefixes:
        run_id = prefix_path.rstrip("/").split("/")[-1]
        run_ids.append(run_id)

    if not run_ids:
        print(f"❌ No runs found for {model_name}")
        return

    # Sort by timestamp (newest first)
    run_ids.sort(reverse=True)

    print(f"Found {len(run_ids)} run(s):\n")
    for i, run_id in enumerate(run_ids, 1):
        print(f"{i:2}. {run_id}")

    print()
    print("=" * 80)


def _validate_promotion_args(parser: argparse.ArgumentParser, args) -> str:
    """Validate required arguments for promotion mode and return HF token."""
    if not args.run_id:
        parser.error("--run-id is required for promotion")
    if not args.hf_repo and not args.dry_run:
        parser.error("--hf-repo is required for promotion")
    if not args.version:
        parser.error("--version is required for promotion")

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token and not args.dry_run:
        print("ERROR: HF_TOKEN environment variable not set")
        print("Set it with: export HF_TOKEN=your_token_here")
        sys.exit(1)

    return hf_token or ""


def _run_promotion(args, hf_token: str) -> None:
    """Download, validate, and push model artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = download_run_artifacts(
            bucket_name=args.gcs_bucket,
            project_name=args.project,
            model_name=args.model,
            run_id=args.run_id,
            local_dir=tmpdir,
        )

        metadata = validate_artifacts(artifact_dir)
        criteria_met = check_promotion_criteria(metadata)

        if not criteria_met and not args.dry_run:
            response = input("\nPromotion criteria not fully met. Continue? [y/N]: ")
            if response.lower() != "y":
                print("Promotion cancelled")
                sys.exit(1)

        if args.hf_repo or args.dry_run:
            push_to_huggingface(
                artifact_dir=artifact_dir,
                hf_repo=args.hf_repo or "dummy/repo",
                version=args.version,
                metadata=metadata,
                token=hf_token,
                private=args.private,
                dry_run=args.dry_run,
            )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Promote model from GCS to Hugging Face Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--gcs-bucket",
        default="rag-pipeline-models",
        help="GCS bucket name (default: rag-pipeline-models)",
    )
    parser.add_argument(
        "--project",
        default="image-preprocessing-detector",
        help="Project name (default: image-preprocessing-detector)",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name (e.g., resnet50_teacher)",
    )
    parser.add_argument(
        "--run-id",
        help="Training run ID to promote",
    )
    parser.add_argument(
        "--hf-repo",
        help="Hugging Face repository (e.g., username/model-name)",
    )
    parser.add_argument(
        "--version",
        help="Semantic version tag (e.g., v1.0.0)",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        default=True,
        help="Create private HF repository (default: True)",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List available training runs and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate artifacts but don't push to HF",
    )

    args = parser.parse_args()

    if args.list_runs:
        list_available_runs(args.gcs_bucket, args.project, args.model)
        return

    hf_token = _validate_promotion_args(parser, args)
    _run_promotion(args, hf_token)


if __name__ == "__main__":
    main()
