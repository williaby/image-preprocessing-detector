---
schema_type: common
title: "Modal Quick Reference"
tags:
  - ml
  - training
  - infrastructure
status: published
owner: docs-team
purpose: Quick reference for Modal training and evaluation workflows.
---

**Quick Reference for Modal GPU Training & Evaluation**

---

## Setup Status

**✅ SETUP COMPLETE** - Ready to run training!

- ✅ Modal installed and authenticated
- ✅ GCS credentials configured in Modal secrets
- ✅ GPU access verified
- ✅ Ready for training runs

### Verify Setup (Optional)

```bash
# Verify Modal authentication (shows active profile and workspace)
poetry run modal profile list

# Verify GCS secret exists
poetry run modal secret list | grep gcs-credentials

# Test GPU access (using actual working test)
poetry run modal run tmp_cleanup/modal_gpu_test.py

# Expected output:
# === Modal GPU Test Results ===
# cuda_available: True
# device_count: 1
# device_name: Tesla T4
# torch_version: 2.5.1+cu124
# ==============================
```text

**Test Results** (verified 2025-11-16):

- ✅ Authentication: `williaby` profile active
- ✅ GCS Secret: `gcs-credentials` exists (created 2025-11-14)
- ✅ GPU Access: Tesla T4 with CUDA available, PyTorch 2.5.1+cu124

### Helper Scripts Available

**Note**: Helper script expects `modal` in PATH. Since Modal is installed via Poetry, use commands directly:

```bash
# Direct commands (recommended)
poetry run modal run tmp_cleanup/modal_gpu_test.py  # Test GPU
poetry run modal run modal/train_phase2_iqa.py      # Train Phase 2
poetry run modal app list                           # List apps
open https://modal.com/apps                         # Dashboard

# Alternatively, activate poetry shell first
poetry shell
modal run tmp_cleanup/modal_gpu_test.py  # Then use modal directly
```text

**Helper script commands** (for reference):

```bash
./scripts/modal_helpers.sh test-gpu        # Test GPU access
./scripts/modal_helpers.sh train-phase2    # Start Phase 2 training
./scripts/modal_helpers.sh monitor         # Open dashboard
./scripts/modal_helpers.sh costs           # Check usage
./scripts/modal_helpers.sh secrets         # List secrets
```text

### First-Time Setup (Reference Only - Already Done)

<details>
<summary>Click to view initial setup steps (completed)</summary>

```bash
# Install Modal (DONE)
poetry add modal
poetry install

# Authenticate (DONE)
poetry run modal token new

# Setup GCS credentials - Uses base64 encoding (DONE)
./scripts/modal_helpers.sh setup-gcs-secret /path/to/service-account.json

# This encodes the key to base64 and creates Modal secret with:
#   Secret name: gcs-credentials
#   Environment variable: GCP_SA_KEY (base64 encoded)
```text

**Important**: GCS credentials are stored as base64-encoded in Modal for portability.
The helper script handles encoding automatically.

</details>

---

## GCS Dataset Ingestion

**Purpose**: Efficiently load large datasets from Google Cloud Storage into Modal training functions.

### Approach Comparison

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Python Library** (✅ USED) | No extra dependencies, works with service account JSON, parallel downloads via ThreadPoolExecutor | Requires manual download logic | Current implementation|
| **CloudBucketMount** | Streaming access, no download needed | Requires HMAC credentials (not service account JSON) | Future option if HMAC created |
| **gsutil CLI** | Simple command, parallel transfers with `-m` flag | Not installed by default in Modal containers | Would need to install gcloud SDK |

### Current Implementation (Python google-cloud-storage Library)

**Working example from [train_phase2_iqa.py](../../modal/train_phase2_iqa.py:183-258)**:

```python
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize GCS client (uses GOOGLE_APPLICATION_CREDENTIALS env var set from Modal secret)
client = storage.Client()
bucket = client.bucket("image_detection_b")

# List all blobs with prefix
prefix = "image-preprocessing-detector/datasets/iqa_phase2/"
blobs = list(bucket.list_blobs(prefix=prefix))

# Download with parallel threads (32 workers for ~3,500 files/min)
def download_blob(blob):
    relative_path = blob.name[len(prefix):]
    local_path = os.path.join("/tmp/data/training/iqa_phase2", relative_path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)
    return local_path

with ThreadPoolExecutor(max_workers=32) as executor:
    futures = [executor.submit(download_blob, blob) for blob in blobs]
    for future in as_completed(futures):
        result = future.result()  # Handle result
```text

**Performance**: ~3,500 files/min with 32 workers (50,000 files in ~14 minutes)

### Alternative: CloudBucketMount (Requires HMAC Credentials)

CloudBucketMount supports GCS but needs HMAC keys instead of service account JSON:

```python
# Create HMAC credentials in Google Cloud Console first
# Store in Modal secret with keys: GOOGLE_ACCESS_KEY_ID, GOOGLE_ACCESS_KEY_SECRET

gcs_secret = modal.Secret.from_name("gcs-hmac-credentials")

@stub.function(
    volumes={
        "/dataset": modal.CloudBucketMount(
            bucket_name="image_detection_b",
            bucket_endpoint_url="https://storage.googleapis.com",
            secret=gcs_secret,
            read_only=True,
        )
    }
)
def train():
    # Dataset accessible at /dataset/* (streaming, no download)
    pass
```text

**To create HMAC credentials**:

1. Go to Google Cloud Console → Storage → Settings → Interoperability
2. Create HMAC key for service account
3. Store `Access Key` and `Secret` in Modal secret:

   ```bash
   modal secret create gcs-hmac-credentials \
       GOOGLE_ACCESS_KEY_ID=<access_key> \
       GOOGLE_ACCESS_KEY_SECRET=<secret>
   ```

**Reference**: [Modal CloudBucketMount docs](https://modal.com/docs/reference/modal.CloudBucketMount#modalcloudbucketmount)

### Alternative: gsutil CLI (Not Recommended)

Would require installing gcloud SDK in image build:

```python
image = (
    modal.Image.debian_slim()
    .run_commands(
        "apt-get update",
        "apt-get install -y curl",
        "curl https://sdk.cloud.google.com | bash",
    )
    .pip_install("google-cloud-storage")
)

# Then use: gsutil -m rsync -r gs://bucket/path /tmp/data
```text

**Not recommended**: Adds significant image build time and complexity.

---

## Training Workflow

### Phase 2: ResNet Teacher-Student IQA

**Purpose**: Train IQA models for document quality assessment and routing decisions.

```bash
# Start training (using helper script)
./scripts/modal_helpers.sh train-phase2

# Or directly (IMPORTANT: use --detach to keep running after disconnect)
poetry run modal run --detach modal/train_phase2_iqa.py

# Monitor dashboard
./scripts/modal_helpers.sh monitor

# Monitor from CLI
poetry run modal app logs iqa-phase2-training --follow
```text

**CRITICAL**: Always use `--detach` flag when running training jobs. Without it, the job will stop if your local terminal disconnects.

**Key Details:**

- **Teacher Model**: `resnet50_teacher_iqa` (ResNet-50)
  - High-capacity backbone for IQA supervision
  - Used only during training (not deployed in production)
  - Produces soft targets and intermediate features for distillation

- **Student Model**: `resnet18_student_iqa` (ResNet-18)
  - Main production IQA model
  - Distilled from ResNet-50 teacher
  - Outputs per-page quality scores: overall quality, sharpness/blur, contrast

- **Dataset**: OHR-Bench document IQA dataset via GCS (~18 GB)
- **Recommended GPU**: **L4** (24GB VRAM, $0.80/h) - best speed/cost balance
  - Alternative: T4 (16GB, $0.59/h) for budget/experimentation
  - Alternative: A10 (24GB, $1.10/h) for faster training
- **Duration**: 13-21 hours with L4 (18-30h with T4)
- **Cost**: $10.40-$16.80 or **$0 with $30/month free tier**

**IMPORTANT**: ResNet-50/ResNet-18 architecture (NOT MobileNetV3 or EfficientNet)

### Phase 3: YOLO-Doc Layout Detection (Future)

**Purpose**: Train lightweight layout detector for routing signals in Project A.

```bash
# Start training (using helper script)
./scripts/modal_helpers.sh train-phase3

# Or directly
poetry run modal run modal/train_phase3_yolov8.py

# Runs 50-80 hours continuously
```text

**Key Details:**

- **Model**: `layout_router_yolo` (YOLO-Doc / YOLOv10-doc small variant)
  - Document-specialized YOLO variant
  - Coarse categories: dense text, multi-column, table-heavy, image-heavy
  - Used only for high-level routing signals (NOT full semantic layout)

- **Dataset**: DocLayNet-style labels, OmniDocBench-class data (~40-50 GB)
- **Recommended GPU**: **A10** (24GB VRAM, $1.10/h) - best speed/cost for long runs
  - Alternative: L4 (24GB, $0.80/h) for budget-conscious training
  - Alternative: L40S (48GB, $1.95/h) for maximum speed
- **Duration**: 39-56 hours with A10 (50-71h with L4, 28-40h with L40S)
- **Cost**: $42.90-$61.60 or **~$13-32 after $30 free tier**

**IMPORTANT**: YOLO-Doc/YOLOv10-doc variant (NOT standard YOLOv8)

---

## Device Policy & Modal Usage

**Modal is for TRAINING ONLY, not production inference.**

### Project A Device Strategy

**Training (Phase 2-3)**:

- **Phase 2 Primary**: Modal **L4 GPU** ($0.80/h) - optimal speed/cost for ResNet
- **Phase 3 Primary**: Modal **A10 GPU** ($1.10/h) - optimal for long YOLO training
- **Experimentation**: Modal **T4 GPU** ($0.59/h) - lowest cost for testing
- **Local GPU**: Available as fallback for small experiments
- **Cost**: Optimized with $30/month free tier, total ~$13-32 for both phases

**Production Inference** (when models are deployed):

- **Preferred**: Local GPU (if available and adequate)
- **Fallback**: Local CPU (ResNet-18 student is CPU-friendly)
- **NOT Modal**: Modal GPU is not used for steady-state inference

### When to Use Modal

**✅ USE Modal for:**

- Training ResNet-50 teacher model (L4 GPU recommended)
- Training ResNet-18 student model (L4 GPU recommended)
- Training YOLO-Doc layout detector (A10 GPU recommended)
- Experimentation and hyperparameter tuning (T4 GPU for budget)
- Dataset evaluation runs (T4 or L4 depending on size)

**GPU Selection Guide:**

- **T4** ($0.59/h): Quick experiments, small tests, hyperparameter search
- **L4** ($0.80/h): Phase 2 training, medium models, best speed/cost
- **A10** ($1.10/h): Phase 3 training, long runs, large models

**❌ DON'T use Modal for:**

- Production document processing
- Routine inference on documents
- Real-time API endpoints
- Steady-state pipeline operations

---

## GCS Integration

### Storage Structure

```text
gs://rag-pipeline-models/
  image-preprocessing-detector/
    resnet50_teacher/
      runs/
        2025-11-15T01-20Z_run-abc123/
          model_final.pth
          training_config.yaml
          metrics.json
          commit_hash.txt
```text

### Upload/Download

```bash
# Upload dataset to GCS
./scripts/upload_datasets_to_gcs.sh

# Download trained model
gsutil cp gs://rag-pipeline-models/image-preprocessing-detector/resnet50_teacher/runs/XXXX/model_final.pth models/

# Verify upload
gsutil du -sh gs://rag-pipeline-models/
```text

---

## GPU Selection & Pricing

### Modal GPU Options (Current Pricing)

| GPU | $/hour | VRAM | Best For | Speed vs T4 |
|-----|--------|------|----------|-------------|
| **T4** | **$0.59** | 16GB | Budget training, small models | 1.0x (baseline) |
| **L4** | **$0.80** | 24GB | Balanced choice, medium models | ~1.4x faster |
| **A10** | **$1.10** | 24GB | Large models, faster training | ~1.8x faster |
| L40S | $1.95 | 48GB | Very large models | ~2.5x faster |
| A100 (40GB) | $2.10 | 40GB | Heavy compute workloads | ~3.0x faster |
| A100 (80GB) | $2.50 | 80GB | Massive models, large batches | ~3.0x faster |
| H100 | $3.95 | 80GB | Cutting-edge performance | ~5.0x faster |
| H200 | $4.54 | 141GB | Latest generation | ~6.0x faster |
| B200 | $6.25 | 192GB | Extreme workloads | ~8.0x faster |

**Free Tier**: $30/month (resets monthly)

### Recommended GPU by Phase

**Phase 2: ResNet Teacher-Student IQA**

| GPU | Duration | Total Cost | After Free Tier | Recommendation |
|-----|----------|------------|-----------------|----------------|
| T4 | 18-30h | $10.62-$17.70 | **$0** | ✅ Best for free tier |
| **L4** | **13-21h** | **$10.40-$16.80** | **$0** | ✅ **Recommended** (35% faster, same cost after free tier) |
| A10 | 10-17h | $11.00-$18.70 | $0 | ⚠️ Overkill for ResNet, use for experimentation |

**Recommendation**: **L4 GPU**

- 35% faster than T4, still within free tier
- Better performance without significant cost increase
- Completes training in 13-21 hours vs 18-30 hours

**Phase 3: YOLO-Doc Layout Detection**

| GPU | Duration | Total Cost | After Free Tier | Recommendation |
|-----|----------|------------|-----------------|----------------|
| T4 | 70-100h | $41.30-$59.00 | $11.30-$29.00 | ⚠️ Slow, long training time |
| L4 | 50-71h | $40.00-$56.80 | $10.00-$26.80 | ✅ Good balance |
| **A10** | **39-56h** | **$42.90-$61.60** | **$12.90-$31.60** | ✅ **Recommended** (best speed/cost) |
| L40S | 28-40h | $54.60-$78.00 | $24.60-$48.00 | ⚠️ Expensive, diminishing returns |

**Recommendation**: **A10 GPU**

- 44% faster than L4, slightly higher cost
- Completes in ~2 days instead of ~3 days
- Better utilization of time vs money tradeoff

### Cost Optimization Strategy

**Recommended Approach**:

1. **Phase 2**: Use **L4** ($0.80/h) - completes within free tier, 35% faster than T4
2. **Phase 3**: Use **A10** ($1.10/h) - best speed/cost balance for long training runs
3. **Experimentation**: Use **T4** ($0.59/h) for quick tests and hyperparameter tuning

**Total Estimated Costs**:

- Phase 2 (L4): $0 (within $30 free tier)
- Phase 3 (A10): ~$13-32 (after remaining free tier credit)
- **Combined**: ~$13-32 total for both phases

### Billing Alerts

```bash
# Set alerts at Modal dashboard
open https://modal.com/settings/billing

# Warning: $10/month
# Critical: $20/month
```text

### Check Usage

```bash
# Current month usage
poetry run modal profile current

# Dashboard
open https://modal.com/usage
```text

---

## Monitoring & Debugging

### View Logs

```bash
# Stream logs
poetry run modal app logs image-detection --follow

# View last 100 lines
poetry run modal app logs image-detection --tail 100
```text

### Check Status

```bash
# List running apps
poetry run modal app list

# Check specific app
poetry run modal app describe image-detection
```text

### Cancel Training

```bash
# Via dashboard (recommended)
open https://modal.com/apps
# Find run → Click "Cancel"

# Via CLI
poetry run modal app stop image-detection
```text

---

## Common Issues

### Authentication Failed

```bash
# Re-authenticate
poetry run modal token new

# Verify
poetry run modal token current
```text

### GCS Access Failed

```bash
# Verify secret exists
poetry run modal secret list | grep gcs-credentials

# Re-create secret
poetry run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/key.json

# Test GCS access
gsutil ls gs://rag-pipeline-models/
```text

### GPU Unavailable

**Rare** - Modal has multi-cloud fallback. If it happens:

1. Check status: <https://modal.com/status>
2. Try different GPU: Change `gpu="T4"` to `gpu="A10"` in config
3. Contact Modal support

### Out of Memory (OOM)

**Solutions:**

1. Reduce batch size in config
2. Upgrade to A10 GPU (24GB vs T4 16GB)
3. Enable gradient accumulation

---

## Key Configuration Files

### Modal Training Config

**Location**: `configs/modal_phase2_iqa.yaml`

```yaml
model:
  architecture: resnet50  # Teacher model
  num_classes: 6
  input_size: 224

training:
  batch_size: 128  # L4 24GB can handle this
  epochs: 50
  learning_rate: 0.001

modal:
  gpu: L4  # Recommended: best speed/cost balance
  # Alternatives: T4 (budget), A10 (faster)
  timeout: 86400  # 24 hours
```text

### GCS Paths

- **Datasets**: `gs://rag-pipeline-models/datasets/`
- **Checkpoints**: `gs://rag-pipeline-models/image-preprocessing-detector/{model}/runs/{run_id}/`
- **Final Models**: `gs://rag-pipeline-models/image-preprocessing-detector/{model}/runs/{run_id}/model_final.pth`

---

## Quick Commands Reference

**All commands use `poetry run modal` prefix:**

```bash
# SETUP (already done)
poetry run modal token new                          # Authenticate
poetry run modal secret create gcs-credentials ...  # Setup GCS
poetry run modal run tmp_cleanup/modal_gpu_test.py  # Test GPU

# TRAINING (IMPORTANT: use --detach to keep running)
poetry run modal run --detach modal/train_phase2_iqa.py  # Start Phase 2
poetry run modal app logs iqa-phase2-training --follow    # Monitor logs

# MONITORING
poetry run modal app list                           # List running apps
poetry run modal profile list                       # Check profile/workspace
open https://modal.com/apps                         # Dashboard

# DEBUGGING
poetry run modal secret list                        # List secrets
poetry run modal app stop image-detection           # Cancel training
```text

**Alternative: Use poetry shell to avoid `poetry run` prefix**

```bash
poetry shell  # Activate poetry environment
# Then use modal directly:
modal run tmp_cleanup/modal_gpu_test.py
modal app list
modal secret list
```text

---

## Important Notes

### Model Architecture (Phase 2)

**CRITICAL**: Use **ResNet-50 teacher** and **ResNet-18 student** (NOT MobileNetV3/EfficientNet)

- Rationale: See [ADR-0034](../ADRs/0034-resnet18-phase2-iqa.md)
- Dataset: OHR-Bench (document-specific IQA)

### Session Management

- **No session timeouts** - training runs to completion
- **Automatic checkpoints** - saved to GCS every 5 epochs
- **Resumption**: Rare cloud failures auto-resume from last checkpoint

### Best Practices

1. **Test with small run first**: 5 epochs (~1 hour, <$1)
2. **Monitor daily**: Check dashboard during long runs
3. **Set timeouts**: `modal.timeout = 86400` (24 hours) in config
4. **Spread across months**: Phase 2 in Month 1, Phase 3 in Month 2 (maximize free tier)

---

## Additional Resources

- **Complete Guide**: [modal-training.md](../guides/modal-training.md)
- **Storage Setup**: [modal-storage.md](../guides/modal-storage.md)
- **Quick Start**: [PHASE2_QUICKSTART.md](../PHASE2_QUICKSTART.md)
- **Model Storage**: [MODEL_STORAGE.md](../MODEL_STORAGE.md)
- **Modal Docs**: <https://modal.com/docs>

---

**Last Updated**: 2025-11-16
**Version**: 1.2.0 (updated with current Modal GPU pricing and recommendations)
