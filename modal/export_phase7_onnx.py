# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Export Phase 7 models (MVP and Production) to ONNX format.

Exports trained models from Modal volumes to ONNX and uploads to GCS.

Supports:
- MVP models (MultiHeadIQA): Simple 5-head architecture with Sigmoid output
- Production models (UncertaintyIQAModel): Dual-output heads (mu + log_var)

Usage:
    # Export all MVP models (seeds 42, 123, 456)
    modal run modal/export_phase7_onnx.py --model-type mvp

    # Export production model
    modal run modal/export_phase7_onnx.py --model-type production

    # Export specific seed
    modal run modal/export_phase7_onnx.py --model-type mvp --seed 42
"""
# mypy: ignore-errors

from pathlib import Path

import modal

# Create Modal app
stub = modal.App("export-phase7-onnx")

# Container image
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "timm>=0.9.0",
        "numpy>=1.24.0",
        "onnx>=1.14.0",
        "onnxscript>=0.1.0",
        "onnxruntime>=1.16.0",
        "google-cloud-storage>=2.10.0",
    )
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)

# Mount volumes
mvp_volume = modal.Volume.from_name("phase7-mvp-checkpoints", create_if_missing=False)
production_volume = modal.Volume.from_name("phase7-production-checkpoints", create_if_missing=False)


@stub.function(
    image=image,
    volumes={
        "/mvp_checkpoints": mvp_volume,
        "/production_checkpoints": production_volume,
    },
    timeout=600,
    cpu=4,
)
def export_model(model_type: str, seed: int) -> dict:
    """Export a single model to ONNX."""
    import os
    import torch
    import torch.nn as nn
    import onnx
    import timm
    from google.cloud import storage

    print("=" * 60)
    print(f"EXPORTING {model_type.upper()} MODEL (seed={seed})")
    print("=" * 60)

    # Set up GCS
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    # =========================================================================
    # Model Definitions
    # =========================================================================

    class MultiHeadIQA(nn.Module):
        """MVP model: Simple 5-head architecture."""
        def __init__(self, backbone, feature_dim, num_heads, dropout):
            super().__init__()
            self.backbone = backbone
            self.heads = nn.ModuleList([
                nn.Sequential(
                    nn.Dropout(dropout),
                    nn.Linear(feature_dim, 1),
                    nn.Sigmoid()
                )
                for _ in range(num_heads)
            ])

        def forward(self, x):
            features = self.backbone(x)
            outputs = [head(features) for head in self.heads]
            return torch.cat(outputs, dim=1)

    class UncertaintyHead(nn.Module):
        """Production model head: outputs mean + log variance."""
        def __init__(self, in_features: int, dropout: float = 0.3):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.mu_head = nn.Sequential(
                nn.Linear(256, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )
            self.log_var_head = nn.Sequential(
                nn.Linear(256, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
            )

        def forward(self, x):
            shared = self.shared(x)
            mu = self.mu_head(shared)
            log_var = self.log_var_head(shared)
            return mu, log_var

    class UncertaintyIQAModel(nn.Module):
        """Production model: ResNet-50 with uncertainty heads."""
        def __init__(self, backbone, feature_dim: int, num_heads: int, dropout: float):
            super().__init__()
            self.backbone = backbone
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.heads = nn.ModuleList([
                UncertaintyHead(feature_dim, dropout) for _ in range(num_heads)
            ])

        def forward(self, x):
            features = self.backbone(x)
            if features.dim() == 4:
                features = self.pool(features).flatten(1)

            mus = []
            log_vars = []
            for head in self.heads:
                mu, log_var = head(features)
                mus.append(mu)
                log_vars.append(log_var)

            return torch.cat(mus, dim=1), torch.cat(log_vars, dim=1)

    # =========================================================================
    # Load Checkpoint
    # =========================================================================

    if model_type == "mvp":
        checkpoint_path = Path(f"/mvp_checkpoints/best_model_seed{seed}.pt")
        # Also check for legacy naming
        if not checkpoint_path.exists() and seed == 42:
            checkpoint_path = Path("/mvp_checkpoints/best_model.pt")
    else:  # production
        checkpoint_path = Path(f"/production_checkpoints/production_model_seed{seed}.pt")

    print(f"\n📂 Loading checkpoint from: {checkpoint_path}")

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint.get("config", {})

    print(f"  Epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"  ECE: {checkpoint.get('macro_ece', 'N/A')}")
    print(f"  MAE: {checkpoint.get('severity_mae', 'N/A')}")
    print(f"  Correlation: {checkpoint.get('macro_correlation', 'N/A')}")

    # =========================================================================
    # Create Model
    # =========================================================================

    print(f"\n🏗️ Creating {model_type} model (ResNet-50)...")

    backbone = timm.create_model("resnet50", pretrained=False, num_classes=0)
    feature_dim = 2048  # ResNet-50 feature dimension

    num_heads = config.get("num_heads", 5)
    dropout = config.get("dropout", 0.2 if model_type == "mvp" else 0.3)

    if model_type == "mvp":
        model = MultiHeadIQA(backbone, feature_dim, num_heads, dropout)
        output_names = ["severity"]
    else:
        model = UncertaintyIQAModel(backbone, feature_dim, num_heads, dropout)
        output_names = ["severity_mu", "severity_log_var"]

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    num_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {num_params:,} ({num_params / 1e6:.2f}M)")

    # =========================================================================
    # Export to ONNX
    # =========================================================================

    print("\n📦 Exporting to ONNX...")

    # Determine input resolution
    if model_type == "production":
        input_resolution = config.get("input_resolution", 384)
    else:
        input_resolution = 224  # MVP uses default resolution

    dummy_input = torch.randn(1, 3, input_resolution, input_resolution)

    onnx_dir = Path("/tmp/onnx_export")
    onnx_dir.mkdir(exist_ok=True)
    onnx_filename = f"phase7_{model_type}_resnet50_seed{seed}.onnx"
    onnx_path = onnx_dir / onnx_filename

    # Export with external data format for large models
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=output_names,
        dynamic_axes={
            "input": {0: "batch_size"},
            **{name: {0: "batch_size"} for name in output_names}
        },
    )

    # Check for external data file
    onnx_data_path = Path(str(onnx_path) + ".data")
    has_external_data = onnx_data_path.exists()

    onnx_size_mb = onnx_path.stat().st_size / (1024 * 1024)
    if has_external_data:
        onnx_data_size_mb = onnx_data_path.stat().st_size / (1024 * 1024)
        total_size_mb = onnx_size_mb + onnx_data_size_mb
        print(f"  ✅ Exported: {onnx_path.name} ({onnx_size_mb:.2f} MB)")
        print(f"  ✅ Data file: {onnx_data_path.name} ({onnx_data_size_mb:.2f} MB)")
        print(f"  Total size: {total_size_mb:.2f} MB")
    else:
        total_size_mb = onnx_size_mb
        print(f"  ✅ Exported: {onnx_path.name} ({onnx_size_mb:.2f} MB)")

    # Verify ONNX model
    print("\n🔍 Verifying ONNX model...")
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    print("  ✅ ONNX model is valid")

    # =========================================================================
    # Upload to GCS
    # =========================================================================

    print("\n☁️ Uploading to GCS...")

    client = storage.Client()
    bucket = client.bucket("image_detection_b")
    gcs_prefix = "models"

    # Upload ONNX file
    blob = bucket.blob(f"{gcs_prefix}/{onnx_filename}")
    blob.upload_from_filename(str(onnx_path))
    print(f"  ✅ Uploaded: gs://image_detection_b/{gcs_prefix}/{onnx_filename}")

    # Upload data file if exists
    if has_external_data:
        data_filename = f"{onnx_filename}.data"
        blob = bucket.blob(f"{gcs_prefix}/{data_filename}")
        blob.upload_from_filename(str(onnx_data_path))
        print(f"  ✅ Uploaded: gs://image_detection_b/{gcs_prefix}/{data_filename}")

    return {
        "model_type": model_type,
        "seed": seed,
        "onnx_path": f"gs://image_detection_b/{gcs_prefix}/{onnx_filename}",
        "onnx_size_mb": total_size_mb,
        "has_external_data": has_external_data,
        "input_resolution": input_resolution,
        "metrics": {
            "epoch": checkpoint.get("epoch"),
            "macro_ece": checkpoint.get("macro_ece"),
            "severity_mae": checkpoint.get("severity_mae"),
            "macro_correlation": checkpoint.get("macro_correlation"),
        },
    }


@stub.local_entrypoint()
def main(model_type: str = "mvp", seed: int = None):
    """Export Phase 7 models to ONNX.

    Args:
        model_type: "mvp" or "production"
        seed: Specific seed to export, or None for all available
    """
    print(f"Exporting Phase 7 {model_type} models...")

    if model_type == "mvp":
        if seed is not None:
            seeds = [seed]
        else:
            seeds = [42, 123, 456]  # All MVP seeds
    else:  # production
        seeds = [seed if seed is not None else 42]

    results = []
    for s in seeds:
        print(f"\n{'='*60}")
        print(f"Processing {model_type} seed {s}...")
        print("=" * 60)

        try:
            result = export_model.remote(model_type=model_type, seed=s)
            results.append(result)
            print(f"\n✅ Successfully exported {model_type} seed {s}")
        except Exception as e:
            print(f"\n❌ Failed to export {model_type} seed {s}: {e}")
            results.append({"model_type": model_type, "seed": s, "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)

    for r in results:
        if "error" in r:
            print(f"  ❌ {r['model_type']} seed {r['seed']}: {r['error']}")
        else:
            print(f"  ✅ {r['model_type']} seed {r['seed']}: {r['onnx_path']}")
            print(f"     ECE: {r['metrics'].get('macro_ece', 'N/A')}, "
                  f"MAE: {r['metrics'].get('severity_mae', 'N/A')}, "
                  f"Corr: {r['metrics'].get('macro_correlation', 'N/A')}")
            print(f"     Size: {r['onnx_size_mb']:.2f} MB, Resolution: {r['input_resolution']}x{r['input_resolution']}")

    return results
