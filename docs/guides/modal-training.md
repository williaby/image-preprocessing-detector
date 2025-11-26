---
schema_type: common
title: "Modal Training Guide - Phase 2 & 3"
tags:
  - guide
  - modal
  - training
status: published
owner: docs-team
purpose: Guide for modal training guide - phase 2 & 3.
---

**Last Updated**: 2025-01-14
**Target Platform**: Modal (Serverless GPU Compute)
**Session Limit**: None (runs to completion)

---

## Overview

This guide covers training ML models for Phases 2 and 3 using Modal, a serverless GPU compute platform. Modal eliminates session timeouts, provides instant cold starts, and offers $30/month in free compute credits.

### Why Modal?

**Cost-Effective Training**:

- $30/month free credits (recurring monthly)
- T4 GPU: $0.5904/hour (~$0.01/minute)
- Pay only for actual compute time (scales to zero)
- Phase 2 + 3 estimated at $0-15 total (mostly within free tier)

**Infrastructure Advantages**:

- **No Session Timeouts**: Train for days without interruption
- **Sub-Second Cold Starts**: <1 second vs 2-3 minutes for notebooks
- **Guaranteed GPU Access**: No queues, multi-cloud fallback
- **Production-Ready**: Container-based workflow from day 1
- **Python-Native**: Define infrastructure with decorators, no YAML

**Comparison to Alternatives**:

| Feature | Modal | Colab Pro | AWS EC2 |
|---------|-------|-----------|---------|
| Free Credits | $30/month | None | None |
| Session Timeout | None | 12 hours | None |
| Cold Start | <1 sec | N/A | ~5 min |
| Cost (40 hrs T4) | $23.62 ($0 w/ credits) | $20 (2 months) | $147 |
| Production Workflow | Yes | No | Yes |

---

## Prerequisites

### 1. Modal Account Setup

**Sign up**: <https://modal.com/>

**Cost**: Free (includes $30/month credits)
**GPU Access**: T4, A10, A100 (pay-per-second)
**Session Limit**: None (automatic timeout at 24 hours configurable)

### 2. GCS Bucket Access

**Required**:

- GCP Project: image-detection-478105
- GCS Bucket: `gs://image_detection_b`
- Service Account Key: (you provide during setup)

**Storage Cost**: ~$0.50/month for 25GB (existing infrastructure)

### 3. Local Development Setup

**Install Modal CLI**:

```bash
# Add to project dependencies
poetry add modal

# Install
poetry install

# Verify
poetry run modal --version
```

---

## Quick Start (5 Steps)

### Step 1: Install Modal CLI

```bash
cd /home/byron/dev/image_detection
poetry add modal
poetry install
```

### Step 2: Authenticate

```bash
# Opens browser for authentication
poetry run modal token new

# Verify authentication
poetry run modal token current
```

**Expected Output**:

```text
✓ Web authentication finished successfully!
Token written to ~/.modal.toml
```text

### Step 3: Setup GCS Credentials

```bash
# Upload service account key as Modal secret
poetry run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/image-detection-478105-service-account.json

# Verify secret exists
poetry run modal secret list | grep gcs-credentials
```

### Step 4: Test GPU Access

```bash
# Test GPU is accessible
poetry run modal run modal/app.py::hello_gpu
```

**Expected Output**:

```text
✓ Initialized. View run at https://modal.com/...
✓ Created objects.
├── 🔨 Created function hello_gpu.
└── 🔨 Created image ml_image.
✅ Hello from Modal GPU: Tesla T4
```text

### Step 5: Run Training

```bash
# Phase 2: IQA Training
poetry run modal run modal/train_phase2_iqa.py

# Monitor at: https://modal.com/apps
```

---

## Phase 2: IQA Model Training

### Training Overview

**Model**: MobileNetV3-Small or EfficientNet-B0
**Task**: Multi-label classification (6 quality issues)
**Dataset**: 50,000 synthetic + validation images (~18 GB)
**Expected Time**: 12-24 hours (single run, no interruptions)
**GPU Requirement**: T4 (16GB) recommended
**Cost**: ~$7-14 or $0 if within $30 free tier

### Dataset Preparation

**Use existing workflow** - no changes needed!

```bash
# 1. Generate synthetic dataset locally
poetry run python scripts/prepare_phase2_data.py \
  --source-dirs data/raw/tobacco800 \
  --output-dir datasets/iqa_phase2 \
  --num-samples 50000 \
  --preset medium

# 2. Upload to GCS (existing script)
./scripts/upload_datasets_to_gcs.sh

# 3. Verify upload
gsutil du -sh gs://image_detection_b/datasets/iqa_phase2/
# Expected: ~18 GB
```

**Dataset format** (already structured correctly):

```text
gs://image_detection_b/datasets/iqa_phase2/
├── train/
│   ├── images/          # 35,000 images
│   └── labels.json
├── val/
│   ├── images/          # 7,500 images
│   └── labels.json
└── test/
    ├── images/          # 7,500 images
    └── labels.json
```text

### Configuration

**Edit** `configs/modal_phase2_iqa.yaml` if needed (defaults are sensible):

```yaml
model:
  architecture: mobilenetv3_small  # or efficientnet_b0
  num_classes: 6
  input_size: 224

training:
  batch_size: 128  # T4 16GB can handle this
  epochs: 50
  learning_rate: 0.001

modal:
  gpu: T4  # or A10 for 50% faster training
  timeout: 86400  # 24 hours
```

### Run Training

```bash
# Start training
poetry run modal run modal/train_phase2_iqa.py

# Terminal output shows:
# - Modal app URL
# - Real-time training logs
# - GPU utilization
# - Cost accumulation
```

**Training runs to completion** - no checkpoints needed for session management!

### Monitor Training

**Option 1: Modal Dashboard** (Recommended)

```bash
# Open dashboard
open https://modal.com/apps
# or
xdg-open https://modal.com/apps
```

**Dashboard shows**:

- Live stdout/stderr logs
- GPU utilization graphs
- Cost accumulation in real-time
- Function call history

**Option 2: CLI Logs**

```bash
# Stream logs from terminal
poetry run modal app logs image-detection --follow
```

### Training Output

**Checkpoints** (saved every 5 epochs):

- Uploaded to: `gs://image_detection_b/checkpoints/phase2_iqa/`
- Format: `checkpoint_epoch_10.pth`, `checkpoint_epoch_15.pth`, etc.

**Final Model**:

- ONNX export: `gs://image_detection_b/models/phase2_iqa/best_model.onnx`
- PyTorch checkpoint: `gs://image_detection_b/models/phase2_iqa/best_model.pth`

**TensorBoard Logs**:

- Uploaded to: `gs://image_detection_b/logs/phase2_iqa/`
- View locally:

  ```bash
  gsutil -m cp -r gs://image_detection_b/logs/phase2_iqa /tmp/logs
  tensorboard --logdir /tmp/logs
  ```

### Download Trained Model

```bash
# Download final ONNX model
gsutil cp gs://image_detection_b/models/phase2_iqa/best_model.onnx models/

# Verify
ls -lh models/best_model.onnx

# Test inference
poetry run python -c "
import onnxruntime as ort
sess = ort.InferenceSession('models/best_model.onnx')
print('Model loaded successfully!')
print(f'Input shape: {sess.get_inputs()[0].shape}')
print(f'Output shape: {sess.get_outputs()[0].shape}')
"
```

---

## Phase 3: YOLOv8 Layout Detection

### Training Overview

**Model**: YOLOv8n (nano) or YOLOv8s (small)
**Task**: Object detection (4 classes: table, image, handwriting, formula)
**Dataset**: 300,000+ annotated document pages (~40-50 GB)
**Expected Time**: 50-80 hours (runs continuously, no session limits!)
**GPU Requirement**: A10 (24GB) recommended for speed
**Cost**: ~$41-47 or ~$11 after $30/month free credits (spread over 2 months)

### Dataset Preparation

**Phase 3 datasets** (to be downloaded in Phase 3 Week 1):

```bash
# Download annotated datasets (see docs/guides/dataset-installation.md)
# - PubLayNet: 360k pages
# - DocLayNet: 80k pages
# - TableBank: 417k images

# Convert to YOLO format (scripts provided in Phase 3)
poetry run python scripts/convert_to_yolo_format.py \
  --source data/raw/publaynet \
  --output datasets/layout_phase3/train

# Upload to GCS
gsutil -m cp -r datasets/layout_phase3 gs://image_detection_b/datasets/

# Verify upload (should be ~40-50GB)
gsutil du -sh gs://image_detection_b/datasets/layout_phase3/
```

**Dataset format** (YOLO):

```text
gs://image_detection_b/datasets/layout_phase3/
├── dataset.yaml          # YOLO config
├── train/
│   ├── images/           # Training images
│   └── labels/           # YOLO format (.txt)
├── val/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```text

**dataset.yaml** structure:

```yaml
path: /data/layout_phase3  # Modal mount path
train: train/images
val: val/images

nc: 4  # Number of classes
names:
  0: table
  1: image
  2: handwriting
  3: formula
```

### Configuration

**Edit** `configs/modal_phase3_yolov8.yaml`:

```yaml
model:
  architecture: yolov8n  # or yolov8s for better accuracy
  num_classes: 4

training:
  batch_size: 32
  epochs: 100  # No session timeout, runs to completion!

modal:
  gpu: A10  # 24GB VRAM, faster than T4
  timeout: 259200  # 72 hours (3 days)
```

### Run Training

```bash
# Start YOLOv8 training
poetry run modal run modal/train_phase3_yolov8.py

# Runs for 50-80 hours continuously (no manual resumption needed!)
```

**Key Advantage**: With Modal, YOLOv8 training completes in a **single run** vs 5-7 resumptions with Colab Pro's 12-hour limit.

### Monitor Progress

Same as Phase 2:

- **Dashboard**: <https://modal.com/apps>
- **CLI**: `poetry run modal app logs image-detection --follow`

**Typical Progress**:

```text
Epoch 10/100: train/box_loss: 0.042, val/mAP@0.5: 0.68
Epoch 20/100: train/box_loss: 0.031, val/mAP@0.5: 0.75
...
Epoch 100/100: val/mAP@0.5: 0.87 ✓ Best model saved
```text

### Export & Download

```bash
# Download final ONNX model
gsutil cp gs://image_detection_b/models/phase3_yolov8/best_model.onnx models/

# Download best checkpoint for fine-tuning
gsutil cp gs://image_detection_b/models/phase3_yolov8/best.pt models/
```

---

## Cost Management

### Understanding Modal Pricing

**T4 GPU**: $0.000164/second = $0.5904/hour
**A10 GPU**: $0.000306/second = $1.1016/hour
**CPU**: $0.0000131/core/second
**Memory**: $0.00000222/GiB/second

**Free Tier**: $30/month (resets monthly)

### Cost Estimates

**Phase 2 (40 hours T4)**:

```text
40 hours × $0.5904/hour = $23.62
Less free credits: -$30
Net cost: $0
```text

**Phase 3 (70 hours A10)**:

```text
70 hours × $1.1016/hour = $77.11
Month 1 free credits: -$30
Month 2 free credits: -$30
Net cost: $17.11
```text

**Total Phases 2+3**: ~$17 (vs $50 for Colab Pro)

### Setting Billing Alerts

1. Go to: <https://modal.com/settings/billing>
2. Set alerts:
   - **Warning**: $10/month
   - **Critical**: $20/month
   - **Email**: Enabled

### Tracking Usage

```bash
# Check current month usage
poetry run modal profile current

# View detailed cost breakdown
# (Visit dashboard: https://modal.com/usage)
```

**Create tracking log**: `docs/infrastructure/modal-cost-tracking.md`

```markdown
# Modal Cost Tracking

| Date | Task | GPU | Duration | Cost | Notes |
|------|------|-----|----------|------|-------|
| 2025-01-15 | Phase 2 training | T4 | 18h | $10.63 | Initial run |
| ... | ... | ... | ... | ... | ... |

**Monthly Total**: $10.63 / $30 free (35% used)
```

---

## Troubleshooting

### Authentication Issues

**Symptom**: `modal: command not found` or `Not authenticated`

**Solution**:

```bash
# Verify Modal installed
poetry run modal --version

# Re-authenticate
poetry run modal token new

# Check current token
poetry run modal token current
```

### GPU Unavailable

**Symptom**: "No GPU available" or function fails

**Solution**:
Modal has multi-cloud fallback. This is rare, but if it happens:

1. Check Modal status: <https://modal.com/status>
2. Try different GPU: Change `gpu="T4"` to `gpu="A10"` in config
3. Contact Modal support (usually responds within hours)

### GCS Mount Failures

**Symptom**: `FileNotFoundError: gs://image_detection_b/...`

**Solution**:

```bash
# Verify GCS secret exists
poetry run modal secret list | grep gcs-credentials

# Re-create secret if needed
poetry run modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS=@/path/to/key.json

# Test GCS access locally
gsutil ls gs://image_detection_b/datasets/
```

### Out of Memory (OOM)

**Symptom**: `CUDA out of memory` error

**Solutions**:

1. **Reduce batch size** in config:

   ```yaml
   training:
     batch_size: 64  # Reduce from 128
   ```

1. **Upgrade GPU**:

   ```yaml
   modal:
     gpu: A10  # 24GB vs T4 16GB
   ```

2. **Enable gradient accumulation**:

   ```yaml
   training:
     gradient_accumulation_steps: 2
   ```

### Cost Overruns

**Symptom**: Used more than expected free credits

**Prevention**:

1. **Set timeouts** in config:

   ```yaml
   modal:
     timeout: 86400  # 24 hours max
   ```

2. **Monitor dashboard** daily during training

3. **Test with small run first**:

   ```yaml
   training:
     epochs: 5  # Test run
   ```

### Training Hangs

**Symptom**: No progress for >30 minutes

**Solution**:

```bash
# Check logs
poetry run modal app logs image-detection --follow

# If truly stuck, cancel via dashboard:
# https://modal.com/apps → Find run → "Cancel"

# Restart training (Modal handles resumption via checkpoints)
poetry run modal run modal/train_phase2_iqa.py
```

---

## Best Practices

### Development Workflow

1. **Test locally first** (CPU):

   ```bash
   # Validate training script syntax
   python modal/train_phase2_iqa.py --dry-run
   ```

1. **Small Modal test** (5 epochs):

   ```bash
   # Edit config: epochs: 5
   poetry run modal run modal/train_phase2_iqa.py
   # Verify everything works (~1 hour, <$1)
   ```

2. **Full training run**:

   ```bash
   # Edit config: epochs: 50
   poetry run modal run modal/train_phase2_iqa.py
   # Monitor daily
   ```

### Checkpoint Strategy

**Even though Modal has no session timeout**, still save checkpoints:

- **Reason**: Long runs (70+ hours) may encounter rare cloud failures
- **Frequency**: Every 5-10 epochs
- **Storage**: GCS (`gs://image_detection_b/checkpoints/`)

**Example resumption** (manual, rarely needed):

```python
# modal/train_phase2_iqa.py
# Modal handles this automatically if timeout occurs
if checkpoint_exists():
    load_checkpoint()
    print(f"Resumed from epoch {last_epoch}")
```

### Cost Optimization

1. **Spread across months**:
   - Phase 2 in January: $30 free
   - Phase 3 in February/March: $30+$30 free
   - Minimizes out-of-pocket costs

2. **Use T4 for experimentation, A10 for production**:
   - T4: $0.59/hour (cheaper, adequate)
   - A10: $1.10/hour (50% faster, more VRAM)

3. **Test with small datasets first**:
   - Validate pipeline with 1,000 images
   - Then scale to 50,000

---

## Comparison to Colab Pro

| Feature | Modal | Colab Pro |
|---------|-------|-----------|
| **Session Timeout** | None | 12 hours |
| **Free Credits** | $30/month | None |
| **Cost (40h T4)** | $23.62 ($0 w/ credits) | $20 (2 months) |
| **Cold Start** | <1 second | N/A |
| **GPU Guarantee** | Yes | Queue possible |
| **Workflow** | Python scripts | Jupyter notebooks |
| **Production Ready** | Yes | No |
| **Checkpoint Management** | Optional | Required (every 12h) |
| **Multi-day Training** | Easy | Manual resumption |
| **Learning Curve** | 1-2 hours | <1 hour |

**Verdict**: Modal is better for production training, Colab was better for rapid notebook experimentation (which we're skipping).

---

## Next Steps After Training

### Phase 2 Post-Training

1. **Download ONNX model** from GCS
2. **Run evaluation** on test set
3. **Integrate model** into pipeline (`src/detection/iqa_ml.py`)
4. **Test locally** with ONNX Runtime (CPU)

### Phase 3 Post-Training

1. **Download YOLOv8 ONNX model**
2. **Run validation** on diverse test set
3. **Integrate layout detector** (`src/detection/layout_detector.py`)
4. **Test end-to-end pipeline** with sample documents

### Model Optimization

1. **INT8 quantization** for faster CPU inference
2. **TensorRT export** for GPU deployment (optional)
3. **Model pruning** for mobile deployment (future)

---

## Support & Resources

### Documentation

- **Modal Docs**: <https://modal.com/docs/guide>
- **Modal GPU Guide**: <https://modal.com/docs/guide/gpu>
- **Modal Secrets**: <https://modal.com/docs/guide/secrets>
- **PROJECT_PLAN.md**: Overall project roadmap
- **ARCHITECTURE_CORRECTION.md**: Design decisions

### External Resources

- **Modal Examples**: <https://modal.com/docs/examples>
- **Ultralytics YOLOv8**: <https://docs.ultralytics.com/>
- **PyTorch ONNX**: <https://pytorch.org/docs/stable/onnx.html>

### Issue Reporting

If you encounter Modal-specific issues:

1. Check Modal status: <https://modal.com/status>
2. Review Modal docs: <https://modal.com/docs>
3. Contact Modal support: <support@modal.com> (fast response)
4. Create GitHub issue with:
   - Modal function name
   - Error message
   - GPU type used
   - Config file used

---

## FAQ

**Q: Can I use Modal Free tier?**
A: Yes! $30/month free credits cover most Phase 2 training entirely.

**Q: What happens if I exceed $30 free credits?**
A: Billing automatically uses pay-as-you-go. Set alerts to avoid surprises.

**Q: Can multiple training runs happen in parallel?**
A: Yes! Modal supports concurrent functions. Limited by Starter tier (10 concurrent GPUs).

**Q: What happens if training exceeds timeout?**
A: Function stops, but checkpoints are saved. Restart training and it resumes automatically.

**Q: Can I use my own GPU instead?**
A: Yes, but Modal is more cost-effective for sporadic training. Save local GPU for inference.

**Q: How do I check remaining free credits?**
A: Visit <https://modal.com/usage> or run `modal profile current`

**Q: Can I pause training mid-run?**
A: Cancel via dashboard, checkpoints auto-save every 5-10 epochs. Restart to resume.

**Q: What if Modal goes down during training?**
A: Rare, but checkpoints saved to GCS persist. Restart when Modal recovers.

---

**Document Version**: 1.0
**Last Reviewed**: 2025-01-14
**Maintainer**: Byron Williams
