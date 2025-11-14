# Modal Storage Setup Guide

**Project**: image-detection
**GCP Project ID**: image-detection-478105
**GCS Bucket**: image_detection_b
**Last Updated**: 2025-01-14

---

## Overview

Modal integrates seamlessly with your existing GCS bucket (`gs://image_detection_b`). This guide covers storage configuration for Modal training workflows.

### Storage Architecture

```
Local Machine (Dataset Generation)
    ↓
Google Cloud Storage (Central Repository)
    ↓
Modal (Training Environment)
    ↓
Google Cloud Storage (Model Output)
    ↓
Local Machine (Deployment)
```

**No data migration needed** - Modal mounts existing GCS bucket directly!

---

## Storage Options

### Option 1: GCS Integration (RECOMMENDED - Already Setup!)

**Advantages**:
- ✅ Use existing GCS bucket (`gs://image_detection_b`)
- ✅ No data migration required
- ✅ Consistent with current workflow
- ✅ Known costs (~$0.50/month for 25GB)
- ✅ Works with existing upload scripts

**How it works**:
1. Modal mounts GCS bucket using service account credentials
2. Training script reads datasets from GCS
3. Checkpoints/models written back to GCS
4. Download final models locally via `gsutil`

### Option 2: Modal Volumes (Alternative)

**Advantages**:
- ✅ Native Modal storage (optimized for Modal)
- ✅ Faster access than GCS mounting (potentially)
- ✅ Persistent across function calls

**Disadvantages**:
- ❌ Requires data upload to Modal separately
- ❌ Pricing structure unclear (check Modal docs)
- ❌ Adds complexity to workflow

**Recommendation**: Stick with GCS (Option 1) unless performance testing shows significant benefit.

---

## GCS Configuration for Modal

### Prerequisites

You already have:
- ✅ GCP Project: `image-detection-478105`
- ✅ GCS Bucket: `gs://image_detection_b`
- ✅ Service Account Key: (you'll provide during setup)

### Step 1: Authenticate Modal with GCS

**Create Modal Secret** with GCS credentials:

```bash
# Upload service account key as Modal secret
poetry run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/image-detection-478105-service-account.json

# Verify secret created
poetry run modal secret list | grep gcs-credentials
```

**Expected Output**:
```
gcs-credentials    Created 2025-01-14
```

### Step 2: Verify GCS Access from Modal

**Test script** (`modal/test_gcs_access.py`):

```python
import modal

stub = modal.Stub("test-gcs")
gcs_secret = modal.Secret.from_name("gcs-credentials")

@stub.function(
    image=modal.Image.debian_slim().pip_install("google-cloud-storage"),
    secrets=[gcs_secret],
)
def test_gcs():
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    # List first 5 objects
    blobs = list(bucket.list_blobs(max_results=5))
    print(f"✅ GCS Access Verified! Found {len(blobs)} objects:")
    for blob in blobs:
        print(f"  - {blob.name}")

if __name__ == "__main__":
    with stub.run():
        test_gcs.remote()
```

**Run test**:
```bash
poetry run modal run modal/test_gcs_access.py
```

### Step 3: Use GCS in Training Scripts

**Example** from `modal/train_phase2_iqa.py`:

```python
import modal
from google.cloud import storage

stub = modal.Stub("iqa-phase2-training")
gcs_secret = modal.Secret.from_name("gcs-credentials")

@stub.function(
    image=modal.Image.debian_slim()
        .pip_install("google-cloud-storage", "torch", "torchvision"),
    secrets=[gcs_secret],
    gpu="T4",
)
def train_iqa():
    """Training function with GCS integration"""

    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    # Download dataset to local cache
    print("Downloading dataset from GCS...")
    download_dir = "/tmp/data/iqa_phase2"

    # Download dataset files (example)
    for blob in bucket.list_blobs(prefix="datasets/iqa_phase2/train/images"):
        local_path = f"{download_dir}/{blob.name}"
        blob.download_to_filename(local_path)

    # Training code here...
    # ...

    # Upload checkpoint to GCS
    checkpoint_blob = bucket.blob("checkpoints/phase2_iqa/checkpoint_epoch_10.pth")
    checkpoint_blob.upload_from_filename("/tmp/checkpoint.pth")

    print("✅ Checkpoint uploaded to GCS")
```

---

## Expected Directory Structure

### GCS Bucket Layout (No Changes!)

Your existing structure works perfectly:

```
gs://image_detection_b/
├── configs/
│   ├── modal_phase2_iqa.yaml           # NEW (Modal config)
│   └── modal_phase3_yolov8.yaml        # NEW (Modal config)
├── datasets/
│   ├── iqa_phase2/                     # EXISTING
│   │   ├── train/
│   │   │   ├── images/
│   │   │   │   ├── img_000001.png
│   │   │   │   └── ... (35,000 images)
│   │   │   └── labels.json
│   │   ├── val/
│   │   │   ├── images/
│   │   │   └── labels.json
│   │   └── test/
│   │       ├── images/
│   │       └── labels.json
│   └── layout_phase3/                  # PHASE 3 (to be created)
│       ├── dataset.yaml
│       ├── train/
│       ├── val/
│       └── test/
├── checkpoints/
│   ├── phase2_iqa/                     # Modal writes here
│   │   ├── checkpoint_epoch_5.pth
│   │   ├── checkpoint_epoch_10.pth
│   │   └── best_model.pth
│   └── phase3_yolov8/                  # Phase 3
│       ├── last.pt
│       └── best.pt
├── logs/
│   ├── phase2_iqa/                     # TensorBoard logs
│   │   └── events.out.tfevents.*
│   └── phase3_yolov8/
├── models/
│   ├── phase2_iqa/                     # Final models
│   │   ├── best_model.onnx
│   │   └── best_model.pth
│   └── phase3_yolov8/
│       ├── best_model.onnx
│       └── best.pt
└── external_iqa/                       # EXISTING (validation datasets)
    ├── LIVE/
    ├── CSIQ/
    └── LIVE_Challenge/
```

---

## Dataset Upload Workflow (No Changes!)

### Phase 2: IQA Dataset

**Existing workflow still works**:

```bash
# 1. Generate synthetic dataset locally
poetry run python scripts/prepare_phase2_data.py \
  --source-dirs data/raw/tobacco800 \
  --output-dir datasets/iqa_phase2 \
  --num-samples 50000 \
  --preset medium

# 2. Upload to GCS using existing script
./scripts/upload_datasets_to_gcs.sh

# Expected output:
# Uploading datasets/iqa_phase2/ to gs://image_detection_b/datasets/
# [====================================] 100% Done
# ✅ Upload complete: ~18 GB

# 3. Verify upload
gsutil du -sh gs://image_detection_b/datasets/iqa_phase2/
# Output: 18 GB

# 4. Modal will automatically access this during training
```

### Phase 3: Layout Detection Dataset

**Same workflow** (Phase 3 Week 1):

```bash
# 1. Download annotated datasets
# (See docs/guides/dataset-installation.md for download instructions)

# 2. Convert to YOLO format (scripts provided in Phase 3)
poetry run python scripts/convert_to_yolo_format.py \
  --source data/raw/publaynet \
  --output datasets/layout_phase3/train

# 3. Upload to GCS
gsutil -m cp -r datasets/layout_phase3 gs://image_detection_b/datasets/

# 4. Verify upload
gsutil du -sh gs://image_detection_b/datasets/layout_phase3/
# Expected: ~40-50 GB
```

---

## Storage Performance Optimization

### Option 1: Direct GCS Mount (Current Approach)

**Pros**:
- Simple implementation
- No intermediate storage needed
- Works with existing scripts

**Cons**:
- Network latency for each file access
- Slower than local disk for small file reads

**Best for**: Large files (checkpoints, models), infrequent access

### Option 2: Download to Local Cache (Recommended for Training)

**Approach**: Download dataset to Modal's local SSD before training

```python
@stub.function(
    image=...,
    secrets=[gcs_secret],
    gpu="T4",
)
def train_iqa():
    from google.cloud import storage

    # Download dataset to /tmp (fast local SSD)
    print("Downloading dataset to local cache...")
    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    # Download all training images
    for blob in bucket.list_blobs(prefix="datasets/iqa_phase2/train/images"):
        local_path = f"/tmp/data/{blob.name}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)

    # Train using local files (fast!)
    dataset = ImageDataset(root="/tmp/data/datasets/iqa_phase2/train")

    # ... training loop ...

    # Upload results back to GCS
    checkpoint_blob = bucket.blob("checkpoints/phase2_iqa/best.pth")
    checkpoint_blob.upload_from_filename("/tmp/best.pth")
```

**Pros**:
- Fast disk access during training
- Minimal network overhead

**Cons**:
- Initial download time (~5-10 min for 18 GB)
- Requires sufficient local storage (Modal provides 50-100 GB)

**Best for**: Training with small files accessed frequently (images)

### Option 3: Modal Volumes (Advanced)

**Use Case**: If you run many experiments and want persistent caching

```python
import modal

# Create persistent volume
dataset_volume = modal.NetworkFileSystem.from_name(
    "iqa-datasets",
    create_if_missing=True
)

@stub.function(
    image=...,
    secrets=[gcs_secret],
    gpu="T4",
    network_file_systems={"/data": dataset_volume},
)
def train_iqa():
    # First run: Download to volume
    if not os.path.exists("/data/iqa_phase2"):
        download_from_gcs_to_volume()

    # Subsequent runs: Use cached data
    dataset = ImageDataset(root="/data/iqa_phase2")

    # Training...
```

**Pros**:
- Persistent across function calls
- Faster subsequent runs
- Good for hyperparameter tuning (many runs)

**Cons**:
- Additional complexity
- Volume storage costs (check Modal pricing)

**Recommendation**: Start with Option 2 (download to local cache), upgrade to Option 3 if you run 10+ experiments.

---

## Configuration Upload

### Upload Training Configs to GCS

```bash
# Upload Modal configs to GCS
gsutil cp configs/modal_phase2_iqa.yaml gs://image_detection_b/configs/
gsutil cp configs/modal_phase3_yolov8.yaml gs://image_detection_b/configs/

# Verify
gsutil ls gs://image_detection_b/configs/
```

### Access Config in Modal Function

```python
@stub.function(
    image=...,
    secrets=[gcs_secret],
)
def train_iqa():
    from google.cloud import storage
    import yaml

    # Download config from GCS
    client = storage.Client()
    bucket = client.bucket("image_detection_b")

    config_blob = bucket.blob("configs/modal_phase2_iqa.yaml")
    config_content = config_blob.download_as_text()

    config = yaml.safe_load(config_content)
    print(f"Loaded config: {config['model']['architecture']}")

    # Use config for training
    model = create_model(config['model'])
```

---

## Cost Analysis

### GCS Storage Costs (Existing)

**Standard Storage**: $0.020/GB/month

| Data | Size | Monthly Cost |
|------|------|--------------|
| Phase 2 datasets | 18 GB | $0.36 |
| Phase 3 datasets | 50 GB | $1.00 |
| Checkpoints | 5 GB | $0.10 |
| Models | 1 GB | $0.02 |
| **Total** | **74 GB** | **$1.48/month** |

**Egress Costs**:
- GCS → Modal: Free (same cloud provider region)
- Modal → GCS: Free (same region)

### Modal Storage Costs

**Local SSD** (ephemeral):
- Included in function execution cost
- No additional charge
- Lost when function completes

**Modal Volumes** (persistent):
- Pricing: Check https://modal.com/pricing
- Estimated: ~$0.10-0.20/GB/month (competitive with GCS)
- Only needed for persistent caching

**Recommendation**: Use GCS ($1.48/month) + Modal local SSD (free) for most cost-effective setup.

---

## Troubleshooting

### GCS Authentication Failures

**Symptom**: `google.auth.exceptions.DefaultCredentialsError`

**Solution**:
```bash
# Verify secret exists
poetry run modal secret list | grep gcs-credentials

# If missing, re-create
poetry run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/service-account-key.json

# Test access
poetry run modal run modal/test_gcs_access.py
```

### Slow Dataset Downloads

**Symptom**: Download takes >30 minutes for 18 GB

**Solutions**:
1. **Use parallel downloads**:
   ```python
   from concurrent.futures import ThreadPoolExecutor

   def download_blob(blob):
       local_path = f"/tmp/data/{blob.name}"
       blob.download_to_filename(local_path)

   with ThreadPoolExecutor(max_workers=10) as executor:
       executor.map(download_blob, blobs)
   ```

2. **Compress datasets** before uploading to GCS:
   ```bash
   tar -czf iqa_phase2.tar.gz datasets/iqa_phase2/
   gsutil cp iqa_phase2.tar.gz gs://image_detection_b/datasets/
   ```

3. **Use Modal Volumes** for persistent caching (advanced)

### Permission Denied Errors

**Symptom**: `403 Forbidden` when accessing GCS

**Solution**:
```bash
# Check service account permissions
gcloud projects get-iam-policy image-detection-478105 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*"

# Ensure service account has Storage Object Viewer role
gcloud projects add-iam-policy-binding image-detection-478105 \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@image-detection-478105.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### Out of Disk Space

**Symptom**: `No space left on device` during download

**Solution**:
```python
# Download only what's needed, or use streaming
# Option 1: Download in batches
for i in range(0, len(blobs), 1000):
    batch = blobs[i:i+1000]
    download_batch(batch)
    train_on_batch(batch)
    cleanup_batch(batch)

# Option 2: Increase Modal disk size (future feature)
# Check Modal docs for custom disk sizes
```

---

## Best Practices

### 1. Dataset Organization

**Keep GCS organized**:
```
gs://image_detection_b/
├── datasets/           # Raw datasets (read-only during training)
├── checkpoints/        # Temporary (delete after 30 days)
├── models/             # Final artifacts (keep long-term)
└── logs/               # TensorBoard logs (archive after training)
```

### 2. Lifecycle Management

**Auto-delete old checkpoints**:

```bash
# Create lifecycle rule
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["checkpoints/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://image_detection_b
```

### 3. Efficient Uploads

**Use `gsutil -m` for parallel uploads**:
```bash
# Parallel upload (10x faster)
gsutil -m cp -r datasets/iqa_phase2 gs://image_detection_b/datasets/

# Monitor progress
gsutil -m -o "GSUtil:parallel_process_count=16" cp -r ...
```

### 4. Checkpoint Strategy

**Save checkpoints to GCS periodically**:
```python
# Every 5 epochs
if epoch % 5 == 0:
    # Save locally first (fast)
    torch.save(state_dict, f"/tmp/checkpoint_epoch_{epoch}.pth")

    # Upload to GCS (async, non-blocking)
    bucket.blob(f"checkpoints/phase2_iqa/checkpoint_epoch_{epoch}.pth") \
        .upload_from_filename(f"/tmp/checkpoint_epoch_{epoch}.pth")
```

---

## Quick Reference

### Common GCS Operations

```bash
# List bucket contents
gsutil ls gs://image_detection_b/

# Check storage usage
gsutil du -sh gs://image_detection_b/

# Download file
gsutil cp gs://image_detection_b/models/phase2_iqa/best_model.onnx models/

# Upload file
gsutil cp models/best_model.onnx gs://image_detection_b/models/phase2_iqa/

# Sync directory
gsutil -m rsync -r datasets/iqa_phase2 gs://image_detection_b/datasets/iqa_phase2

# Delete old checkpoints
gsutil -m rm gs://image_detection_b/checkpoints/phase2_iqa/checkpoint_epoch_*.pth
```

### Modal Secret Management

```bash
# Create secret
modal secret create gcs-credentials GOOGLE_APPLICATION_CREDENTIALS=@/path/to/key.json

# List secrets
modal secret list

# Delete secret
modal secret delete gcs-credentials
```

---

## Summary

**Storage Setup**: ✅ No changes needed!

1. **Continue using GCS** bucket `gs://image_detection_b`
2. **Upload datasets** with existing scripts
3. **Modal mounts GCS** via service account secret
4. **Training reads from GCS**, writes checkpoints back
5. **Download final models** via `gsutil`

**Costs**:
- GCS Storage: $1.48/month (existing)
- GCS → Modal Transfer: Free (same region)
- Modal Local SSD: Free (included)
- **Total**: ~$1.50/month (unchanged)

**Next Steps**:
1. Create Modal secret with GCS credentials (after Step 3)
2. Test GCS access from Modal
3. Run training - Modal handles the rest!

---

**For training instructions, see**: [modal-training.md](modal-training.md)
