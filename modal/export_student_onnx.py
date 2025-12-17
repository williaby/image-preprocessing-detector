# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Export Phase 7 Student (ResNet-18) model to ONNX format.

This script loads the trained student model from the Modal volume
and exports it to ONNX format for CPU inference benchmarking.

Usage:
    modal run modal/export_student_onnx.py
"""
# mypy: ignore-errors

import time
from pathlib import Path

import modal

# Create Modal app
stub = modal.App("export-student-onnx")

# Container image with onnxscript
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

# Mount the distillation volume
distillation_volume = modal.Volume.from_name("phase7-distillation-checkpoints", create_if_missing=False)


@stub.function(
    image=image,
    volumes={"/distillation_checkpoints": distillation_volume},
    timeout=600,
    cpu=8,
)
def export_to_onnx(seed: int = 42):
    """Export student model to ONNX and benchmark."""
    import torch
    import torch.nn as nn
    import numpy as np
    import onnx
    import onnxruntime as ort
    import timm
    from google.cloud import storage

    print("=" * 60)
    print("EXPORTING STUDENT MODEL TO ONNX")
    print("=" * 60)

    # =========================================================================
    # Model Definitions (same as training script)
    # =========================================================================

    class UncertaintyHead(nn.Module):
        """Single head that outputs mean (mu) and log variance (log_var)."""
        def __init__(self, in_features: int, hidden_dim: int = 256, dropout: float = 0.3):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.mu_head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),  # Output in [0, 1]
            )
            self.log_var_head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),  # Unbounded log variance
            )

        def forward(self, x):
            shared = self.shared(x)
            mu = self.mu_head(shared)
            log_var = self.log_var_head(shared)
            return mu, log_var

    class UncertaintyIQAModel(nn.Module):
        """IQA model with separate uncertainty heads for each defect type."""
        def __init__(self, backbone, feature_dim: int, num_heads: int, dropout: float, hidden_dim: int = 256):
            super().__init__()
            self.backbone = backbone
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.heads = nn.ModuleList([
                UncertaintyHead(feature_dim, hidden_dim, dropout) for _ in range(num_heads)
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

    # Load checkpoint
    checkpoint_path = Path(f"/distillation_checkpoints/student_model_seed{seed}.pt")
    print(f"\n📂 Loading checkpoint from: {checkpoint_path}")

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    print(f"  Epoch: {checkpoint['epoch']}")
    print(f"  ECE: {checkpoint['macro_ece']:.4f}")
    print(f"  MAE: {checkpoint['severity_mae']:.4f}")
    print(f"  Correlation: {checkpoint['macro_correlation']:.4f}")

    # Create student model (ResNet-18)
    print("\n🏗️ Creating student model (ResNet-18)...")
    backbone = timm.create_model("resnet18", pretrained=False, num_classes=0)
    student = UncertaintyIQAModel(
        backbone=backbone,
        feature_dim=512,  # ResNet-18 feature dim
        num_heads=5,
        dropout=0.3,
        hidden_dim=128,  # Smaller hidden dim for student
    )
    student.load_state_dict(checkpoint["model_state_dict"])
    student.eval()

    # Count parameters
    num_params = sum(p.numel() for p in student.parameters())
    print(f"  Parameters: {num_params:,} ({num_params / 1e6:.2f}M)")

    # Export to ONNX
    print("\n📦 Exporting to ONNX...")
    input_resolution = checkpoint["config"]["input_resolution"]
    dummy_input = torch.randn(1, 3, input_resolution, input_resolution)

    onnx_path = Path(f"/distillation_checkpoints/student_resnet18_seed{seed}.onnx")

    # Use torch.onnx.export
    torch.onnx.export(
        student,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["severity_mu", "severity_log_var"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "severity_mu": {0: "batch_size"},
            "severity_log_var": {0: "batch_size"},
        },
    )
    print(f"  ✅ Exported to: {onnx_path}")

    # Get ONNX model size
    onnx_size_mb = onnx_path.stat().st_size / (1024 * 1024)
    print(f"  Size: {onnx_size_mb:.2f} MB")

    # Verify ONNX model
    print("\n🔍 Verifying ONNX model...")
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    print("  ✅ ONNX model is valid")

    # Benchmark CPU inference with ONNX Runtime
    print("\n⏱️ Benchmarking CPU inference (8-core)...")
    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 8
    session_options.inter_op_num_threads = 8

    ort_session = ort.InferenceSession(
        str(onnx_path),
        session_options,
        providers=["CPUExecutionProvider"],
    )

    # Warmup
    print("  Warming up...")
    rng = np.random.default_rng(42)
    test_input = rng.standard_normal((1, 3, input_resolution, input_resolution)).astype(np.float32)
    for _ in range(10):
        _ = ort_session.run(None, {"input": test_input})

    # Benchmark
    num_iterations = 100
    print(f"  Running {num_iterations} iterations...")
    latencies = []
    for _ in range(num_iterations):
        start = time.perf_counter()
        _ = ort_session.run(None, {"input": test_input})
        latencies.append((time.perf_counter() - start) * 1000)

    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    p50_latency = np.percentile(latencies, 50)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)

    print(f"\n📊 CPU Latency Results ({input_resolution}x{input_resolution}):")
    print(f"  Average: {avg_latency:.2f}ms ± {std_latency:.2f}ms")
    print(f"  P50: {p50_latency:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")
    print(f"  P99: {p99_latency:.2f}ms")

    # Check against target
    target_latency = 60  # ms
    latency_met = avg_latency < target_latency
    print(f"\n  Target: <{target_latency}ms | Status: {'✅ MET' if latency_met else '❌ NOT MET'}")

    # Upload to GCS
    print("\n☁️ Uploading to GCS...")
    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    # Upload ONNX
    blob = bucket.blob(f"models/phase7_student_resnet18_seed{seed}.onnx")
    blob.upload_from_filename(str(onnx_path))
    print(f"  ✅ Uploaded: gs://image_detection_b/models/phase7_student_resnet18_seed{seed}.onnx")

    # Upload checkpoint
    blob = bucket.blob(f"models/phase7_student_resnet18_seed{seed}.pt")
    blob.upload_from_filename(str(checkpoint_path))
    print(f"  ✅ Uploaded: gs://image_detection_b/models/phase7_student_resnet18_seed{seed}.pt")

    # Save volume
    distillation_volume.commit()

    return {
        "onnx_path": f"gs://image_detection_b/models/phase7_student_resnet18_seed{seed}.onnx",
        "checkpoint_path": f"gs://image_detection_b/models/phase7_student_resnet18_seed{seed}.pt",
        "onnx_size_mb": onnx_size_mb,
        "model_metrics": {
            "macro_ece": checkpoint["macro_ece"],
            "severity_mae": checkpoint["severity_mae"],
            "macro_correlation": checkpoint["macro_correlation"],
            "ece_gap": checkpoint["ece_gap"],
        },
        "cpu_latency": {
            "average_ms": avg_latency,
            "p50_ms": p50_latency,
            "p95_ms": p95_latency,
            "p99_ms": p99_latency,
            "target_ms": target_latency,
            "target_met": latency_met,
        },
    }


@stub.local_entrypoint()
def main(seed: int = 42):
    """Export student model to ONNX."""
    print(f"Exporting Phase 7 student model (seed={seed})...")
    result = export_to_onnx.remote(seed=seed)

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)

    print("\n📁 Files:")
    print(f"  ONNX: {result['onnx_path']}")
    print(f"  Checkpoint: {result['checkpoint_path']}")
    print(f"  Size: {result['onnx_size_mb']:.2f} MB")

    print("\n📊 Model Metrics:")
    metrics = result["model_metrics"]
    print(f"  ECE: {metrics['macro_ece']:.4f} (gap: {metrics['ece_gap']:+.4f})")
    print(f"  MAE: {metrics['severity_mae']:.4f}")
    print(f"  Correlation: {metrics['macro_correlation']:.4f}")

    print("\n⏱️ CPU Latency:")
    latency = result["cpu_latency"]
    print(f"  Average: {latency['average_ms']:.2f}ms")
    print(f"  P95: {latency['p95_ms']:.2f}ms")
    print(f"  Target: <{latency['target_ms']}ms | {'✅ MET' if latency['target_met'] else '❌ NOT MET'}")

    # Final summary
    print("\n" + "=" * 60)
    print("SPRINT 5 FINAL STATUS")
    print("=" * 60)

    ece_target = 0.0214 + 0.03  # Teacher ECE + tolerance
    ece_met = metrics['macro_ece'] < ece_target
    mae_met = metrics['severity_mae'] < 0.12
    corr_met = metrics['macro_correlation'] > 0.75
    latency_met = latency['target_met']
    size_met = result['onnx_size_mb'] < 50

    print(f"  ECE < {ece_target:.4f}: {'✅' if ece_met else '❌'} ({metrics['macro_ece']:.4f})")
    print(f"  MAE < 0.12: {'✅' if mae_met else '❌'} ({metrics['severity_mae']:.4f})")
    print(f"  Corr > 0.75: {'✅' if corr_met else '❌'} ({metrics['macro_correlation']:.4f})")
    print(f"  Latency < 60ms: {'✅' if latency_met else '❌'} ({latency['average_ms']:.2f}ms)")
    print(f"  Size < 50MB: {'✅' if size_met else '❌'} ({result['onnx_size_mb']:.2f}MB)")

    all_met = all([ece_met, mae_met, corr_met, latency_met, size_met])
    print(f"\n  🎯 ALL TARGETS MET: {'✅ YES' if all_met else '❌ NO'}")

    return result
