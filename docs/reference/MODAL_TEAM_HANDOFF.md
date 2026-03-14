# Modal GPU Platform - Team Handoff Guide

**Purpose**: Get a new team member running analysis workloads on Modal with minimal startup friction.

**Last Updated**: 2026-03-07

---

## Table of Contents

1. [What is Modal?](#what-is-modal)
2. [First-Time Setup](#first-time-setup)
3. [Essential Commands](#essential-commands)
4. [Running Jobs](#running-jobs)
5. [GCS Dataset Access](#gcs-dataset-access)
6. [Key Files in This Repo](#key-files-in-this-repo)
7. [Writing Your Own Modal Script](#writing-your-own-modal-script)
8. [GPU Selection & Pricing](#gpu-selection--pricing)
9. [Monitoring & Debugging](#monitoring--debugging)
10. [Common Issues & Fixes](#common-issues--fixes)

---

## What is Modal?

Modal is a serverless GPU platform. You write Python functions decorated with Modal annotations, and Modal runs them on cloud GPUs. No Docker, no Kubernetes, no SSH — just `modal run your_script.py`.

Key concepts:

- **App**: A named group of functions (e.g., `modal.App("my-analysis")`)
- **Image**: The container environment (Python version, pip packages)
- **Secrets**: Encrypted environment variables (e.g., GCS credentials)
- **Volumes**: Persistent storage that survives across runs
- **`--detach`**: Run a job in the background so it survives terminal disconnects

---

## First-Time Setup

### 1. Install Dependencies

This project uses `uv` as the package manager:

```bash
# From the repo root
uv sync --extra dev
```

Modal is already declared as a dependency in `pyproject.toml` (`modal>=0.63.0`).

### 2. Authenticate with Modal

```bash
uv run modal token new
```

This opens a browser to authenticate. Your token is saved to `~/.modal.toml`.

### 3. Verify Authentication

```bash
uv run modal profile list
```

You should see your workspace name and profile.

### 4. Set Up GCS Credentials (Required for Dataset Access)

You need a GCP service account JSON key file. Ask the team lead for this.

```bash
# The helper script base64-encodes the key and stores it as a Modal secret
./scripts/modal_helpers.sh setup-gcs-secret /path/to/your-service-account.json
```

This creates a Modal secret called `gcs-credentials` with the environment variable `GCP_SA_KEY` (base64-encoded).

To verify:

```bash
uv run modal secret list | grep gcs-credentials
```

### 5. Test GPU Access

```bash
uv run modal run modal/app.py::hello_gpu
```

Expected output:

```
Hello from Modal GPU: Tesla T4
CUDA Version: 12.4
PyTorch Version: 2.5.1+cu124
```

### 6. Test GCS Access

```bash
uv run modal run modal/test_gcs.py
```

This verifies Modal can reach the GCS bucket using your credentials.

---

## Essential Commands

### Running Scripts

```bash
# Run a script (blocks terminal, stops if you disconnect)
uv run modal run modal/your_script.py

# Run DETACHED (keeps running after terminal disconnect) -- USE THIS FOR LONG JOBS
uv run modal run --detach modal/your_script.py

# Run with arguments
uv run modal run --detach modal/train_siglip2_iqa.py --epochs 50 --batch-size 16

# Run a specific function from a script
uv run modal run modal/app.py::hello_gpu
```

**CRITICAL**: Always use `--detach` for any job longer than a few minutes. Without it, closing your terminal kills the job.

### Monitoring

```bash
# List running apps
uv run modal app list

# Stream logs from a running app
uv run modal app logs <app-name> --follow

# View last N lines of logs
uv run modal app logs <app-name> --tail 100

# Open the web dashboard (best for monitoring)
open https://modal.com/apps
```

### Managing Jobs

```bash
# Stop/cancel a running app
uv run modal app stop <app-name>

# Check your usage and billing
uv run modal profile current
open https://modal.com/usage
```

### Secrets Management

```bash
# List all secrets
uv run modal secret list

# Create a new secret
uv run modal secret create my-secret KEY1=value1 KEY2=value2

# Recreate GCS credentials
uv run modal secret create gcs-credentials GCP_SA_KEY="<base64-encoded-key>"
```

---

## Running Jobs

### Quick Test Pattern

Every training script in this repo supports a `--test` flag for quick validation:

```bash
# Quick test (2 epochs, synthetic data, ~2 minutes)
uv run modal run modal/train_siglip2_iqa.py --test

# Quick test for multitask model
uv run modal run modal/train_siglip2_multitask.py --test
```

### Production Run Pattern

```bash
# Always use --detach for real training runs
uv run modal run --detach modal/train_siglip2_iqa.py

# Monitor it
uv run modal app logs siglip2-iqa-training --follow
```

### Resume a Training Run

Some scripts support resuming from a checkpoint:

```bash
uv run modal run --detach modal/train_skew_estimator.py --resume RUN_ID
```

---

## GCS Dataset Access

### How It Works

1. Modal secret `gcs-credentials` holds a base64-encoded GCP service account key
2. At runtime, the shared utility decodes it and sets `GOOGLE_APPLICATION_CREDENTIALS`
3. The `google-cloud-storage` Python library uses that for authentication
4. Datasets are downloaded with parallel threads (~3,500 files/min with 32 workers)

### GCS Buckets

| Bucket | Purpose |
|--------|---------|
| `image_detection_b` | Primary dataset storage (training images, labels) |
| `rag-pipeline-models` | Model artifacts and checkpoints |
| `assured-oss-457903-diqa5000` | DIQA-5000 benchmark dataset |

### Using GCS in Your Script

Import the shared utilities rather than writing your own:

```python
from modal.shared.gcs_utils import setup_gcs_credentials, download_dataset_from_gcs, upload_to_gcs

# Inside your Modal function:
setup_gcs_credentials()  # Decodes GCP_SA_KEY and sets env var

# Download a dataset
from google.cloud import storage
client = storage.Client()
bucket = client.bucket("image_detection_b")
blobs = list(bucket.list_blobs(prefix="your/dataset/prefix/"))
```

See `modal/shared/gcs_utils.py` for the full download/upload helpers.

---

## Key Files in This Repo

### Core Modal Infrastructure

| File | Purpose |
|------|---------|
| `modal/app.py` | Base Modal app definition, shared ML image, `hello_gpu` test function |
| `modal/shared/__init__.py` | Package exports for all shared utilities |
| `modal/shared/constants.py` | GCS config, Modal volumes, Modal secrets, shared constants |
| `modal/shared/gcs_utils.py` | GCS credential setup, dataset download/upload helpers |
| `modal/shared/dataset_utils.py` | Dataset loading utilities (e.g., DIQA-5000 loader) |
| `modal/shared/metrics_utils.py` | Correlation metrics, bootstrapping, result formatting |

### Training Scripts

| File | Purpose |
|------|---------|
| `modal/train_siglip2_multitask.py` | SigLIP 2 multi-task teacher (16 heads: IQA, script, orientation, etc.) |
| `modal/train_siglip2_iqa.py` | SigLIP 2 IQA-only training |
| `modal/train_siglip2_iqa_v2.py` | SigLIP 2 IQA v2 (supports base and so400m variants) |
| `modal/train_skew_estimator.py` | MobileNetV4 skew angle estimator |
| `modal/train_phase3_doclayout_yolo.py` | DocLayout-YOLO layout detection |
| `modal/train_phase6_layout_lite.py` | Layout-lite page attribute classification |

### Configuration

| File | Purpose |
|------|---------|
| `configs/modal_phase3_doclayout_yolo.yaml` | Phase 3 training config (model, GPU, data paths, timeouts) |
| `configs/modal_phase6_layout_lite.yaml` | Phase 6 training config |

### Helper Scripts & Docs

| File | Purpose |
|------|---------|
| `scripts/modal_helpers.sh` | CLI wrapper for common Modal operations |
| `docs/reference/MODAL_QUICK_REFERENCE.md` | Detailed reference doc (GPU pricing, GCS ingestion, troubleshooting) |
| `modal/test_gcs.py` | Standalone GCS connectivity test |

---

## Writing Your Own Modal Script

### Minimal Template

```python
"""My Analysis Script.

Usage:
    uv run modal run modal/my_analysis.py
    uv run modal run --detach modal/my_analysis.py  # Long-running
"""

import modal

app = modal.App("my-analysis")

# Define your container image with required packages
my_image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch>=2.1.0",
    "torchvision>=0.16.0",
    "numpy",
    "Pillow",
    # Add your packages here
)

# Reference the shared GCS secret (already configured)
gcs_secret = modal.Secret.from_name("gcs-credentials")


@app.function(
    image=my_image,
    gpu="L4",               # See GPU table below for options
    timeout=86400,           # 24 hours max
    secrets=[gcs_secret],    # Makes GCP_SA_KEY available as env var
)
def run_analysis():
    """Your analysis function runs on a cloud GPU."""
    import torch

    print(f"Running on: {torch.cuda.get_device_name(0)}")

    # Setup GCS access if needed
    from modal.shared.gcs_utils import setup_gcs_credentials
    setup_gcs_credentials()

    # Your analysis code here
    # ...

    return {"status": "complete"}


@app.local_entrypoint()
def main():
    """Entry point when running via `modal run`."""
    result = run_analysis.remote()  # .remote() sends it to the cloud
    print(f"Result: {result}")
```

### Key Patterns

**Persistent volumes** (data survives across runs):

```python
my_volume = modal.Volume.from_name("my-data", create_if_missing=True)

@app.function(
    image=my_image,
    gpu="L4",
    volumes={"/data": my_volume},  # Mounted at /data inside the container
)
def my_function():
    # Read/write to /data — persists across runs
    pass
```

**Multiple GPU options** (specify in the decorator):

```python
@app.function(gpu="T4")    # Budget: $0.59/hr, 16GB VRAM
@app.function(gpu="L4")    # Balanced: $0.80/hr, 24GB VRAM
@app.function(gpu="A10G")  # Fast: $1.10/hr, 24GB VRAM
@app.function(gpu="A100")  # Heavy: $2.10/hr, 40GB VRAM
```

**CLI arguments** (using `modal.parameter`):

```python
@app.local_entrypoint()
def main(
    epochs: int = 10,
    batch_size: int = 32,
    test: bool = False,
):
    result = run_analysis.remote(epochs=epochs, batch_size=batch_size, test=test)
```

---

## GPU Selection & Pricing

| GPU | $/hour | VRAM | Best For |
|-----|--------|------|----------|
| **T4** | $0.59 | 16GB | Quick experiments, small models, budget runs |
| **L4** | $0.80 | 24GB | General training, best cost/performance balance |
| **A10** | $1.10 | 24GB | Long training runs, larger batch sizes |
| **L40S** | $1.95 | 48GB | Large models that need >24GB VRAM |
| **A100 (40GB)** | $2.10 | 40GB | Heavy compute, large batch training |
| **A100 (80GB)** | $2.50 | 80GB | Very large models |
| **H100** | $3.95 | 80GB | Maximum throughput |

**Free tier**: $30/month (resets monthly). A T4 for ~50 hours or an L4 for ~37 hours.

**Recommendation**: Start with **L4** for most workloads. Drop to T4 for quick tests. Use A10+ only if you need more VRAM or speed.

---

## Monitoring & Debugging

### Web Dashboard (Recommended)

The Modal web dashboard is the easiest way to monitor:

- **<https://modal.com/apps>** — See all running/completed apps
- **<https://modal.com/usage>** — Billing and compute usage
- **<https://modal.com/settings/billing>** — Set spending alerts

### CLI Monitoring

```bash
# Stream logs in real-time
uv run modal app logs <app-name> --follow

# List all apps with status
uv run modal app list

# Describe a specific app
uv run modal app describe <app-name>
```

### Finding the App Name

Each script defines its app name at the top:

```python
app = modal.App("siglip2-multitask-training")  # <-- this is the app name
```

Use that name with `modal app logs`, `modal app stop`, etc.

---

## Common Issues & Fixes

### "Not authenticated" / Token Expired

```bash
uv run modal token new    # Re-authenticate
uv run modal token current # Verify
```

### GCS Access Denied

```bash
# Verify the secret exists
uv run modal secret list | grep gcs-credentials

# Re-create if needed (get the service account JSON from team lead)
./scripts/modal_helpers.sh setup-gcs-secret /path/to/key.json

# Test connectivity
uv run modal run modal/test_gcs.py
```

### Job Died Because Terminal Closed

You forgot `--detach`. Re-run with:

```bash
uv run modal run --detach modal/your_script.py
```

### Out of Memory (OOM)

1. Reduce `batch_size` in your script or config
2. Switch to a GPU with more VRAM (e.g., T4 16GB -> L4 24GB)
3. Enable mixed precision (`torch.cuda.amp`) to halve memory usage

### GPU Unavailable

Rare, but if it happens:

1. Check Modal status: <https://modal.com/status>
2. Try a different GPU type: change `gpu="T4"` to `gpu="L4"` in your decorator
3. Wait a few minutes and retry

### Import Errors for `modal.shared`

The shared utilities use relative imports within the `modal/` package. Always run from the repo root:

```bash
cd /path/to/image_detection
uv run modal run modal/your_script.py
```

---

## Quick Start Checklist

- [ ] Clone the repo and run `uv sync --extra dev`
- [ ] Run `uv run modal token new` to authenticate
- [ ] Get the GCS service account key from the team lead
- [ ] Run `./scripts/modal_helpers.sh setup-gcs-secret /path/to/key.json`
- [ ] Run `uv run modal run modal/app.py::hello_gpu` to verify GPU access
- [ ] Run `uv run modal run modal/test_gcs.py` to verify GCS access
- [ ] Try a quick test: `uv run modal run modal/train_siglip2_iqa.py --test`
- [ ] You're ready — use `--detach` for any real workload
