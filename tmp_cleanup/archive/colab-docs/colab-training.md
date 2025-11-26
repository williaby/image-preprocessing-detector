<!-- markdownlint-disable -->
# Google Colab Training Guide - Phase 2 & 3

**Last Updated**: 2025-01-15
**Target Platform**: Google Colab Pro
**Session Limit**: 12 hours

---

## Overview

This guide covers training ML models for Phases 2 and 3 using Google Colab Pro. The infrastructure is optimized for **12-hour session limits** with automatic checkpoint management and resumption.

### Why Google Colab?

**Cost-Effective Training**:

- Colab Pro: $10/month vs $30-200 for cloud GPU hourly rates
- Phase 2 + 3 can be completed for $20-30 (2-3 months)
- No local GPU workstation required

**Infrastructure Included**:

- V100/P100/T4 GPUs (16GB memory)
- PyTorch, CUDA pre-installed
- Google Drive integration for persistence

---

## Prerequisites

### 1. Google Colab Pro Subscription

**Sign up**: <https://colab.research.google.com/signup>

**Cost**: $10/month
**GPU Access**: V100, P100, or T4 (15-16GB VRAM)
**Session Limit**: 12 hours
**Compute Units**: ~100 units/month (sufficient for Phases 2-3)

### 2. Google Drive Setup

**Required Space**:

- Phase 2: ~25GB (dataset + checkpoints)
- Phase 3: ~50GB (larger dataset + checkpoints)
- Total: ~75GB recommended

**Free Tier**: 15GB (not enough - upgrade to 100GB for $1.99/month)

### 3. Prepare Directory Structure

Create this structure in your Google Drive:

```text
MyDrive/
└── image-preprocessing-detector/
    ├── datasets/
    │   ├── iqa_phase2/          # 50k images, ~10GB
    │   └── layout_phase3/        # 300k images, ~40GB
    ├── checkpoints/
    │   ├── phase2_iqa/
    │   └── phase3_yolov8/
    ├── logs/
    │   ├── phase2_iqa/
    │   └── phase3_yolov8/
    ├── models/
    │   ├── phase2_iqa/           # Final ONNX models
    │   └── phase3_yolov8/
    └── configs/
        ├── colab_phase2_iqa.yaml
        └── colab_phase3_yolov8.yaml
```text

---

## Phase 2: IQA Model Training

### Training Overview

**Model**: MobileNetV3-Small or EfficientNet-B0
**Task**: Multi-label classification (6 quality issues)
**Dataset**: 50,000 synthetic + real images
**Expected Time**: 12-20 hours (1-2 sessions)
**GPU Requirement**: V100 (recommended), P100, or T4

### Step-by-Step Instructions

#### Step 1: Prepare Dataset

**Option A**: Generate synthetic dataset (use `data_preparation.ipynb`)
**Option B**: Upload pre-prepared dataset to Google Drive

**Dataset format**:

```text
iqa_phase2/
├── train/
│   ├── images/
│   └── labels.json
├── val/
│   ├── images/
│   └── labels.json
└── test/
    ├── images/
    └── labels.json
```text

#### Step 2: Upload Configuration

Upload `configs/colab_phase2_iqa.yaml` to:

```text
/content/drive/MyDrive/image-preprocessing-detector/configs/colab_phase2_iqa.yaml
```text

**Key settings to adjust** (in YAML file):

- `training.batch_size`: 64 for V100, 32 for T4
- `training.epochs`: 50 (default)
- `model.architecture`: `mobilenet_v3_small` or `efficientnet_b0`

#### Step 3: Open Training Notebook

1. Navigate to `notebooks/colab/phase2_iqa_training.ipynb`
2. Open in Google Colab
3. **Runtime** → **Change runtime type** → **GPU** (Hardware accelerator)
4. Verify GPU assignment: Should be V100, P100, or T4

#### Step 4: Run Training

**Execute cells sequentially**:

1. **Cell 1**: Check GPU
2. **Cell 2**: Mount Google Drive (authorize access)
3. **Cell 3**: Install dependencies
4. **Cell 4**: Load configuration
5. **Cell 5**: Initialize utilities
6. **Cell 6**: Download dataset to local SSD
7. **Cell 7**: Create data loaders
8. **Cell 8**: Create model
9. **Cell 9**: Setup optimizer/scheduler
10. **Cell 10**: Initialize checkpoint manager
11. **Cell 11**: Setup TensorBoard
12. **Cell 12**: **Start training** ⏱️

**Cell 12 will run for ~11.5 hours** then auto-save checkpoint.

#### Step 5: Monitor Training

**TensorBoard** (embedded in notebook):

- Loss curves (train/val)
- Accuracy metrics
- Learning rate schedule

**Console Output**:

- Epoch progress
- Checkpoint saves
- Session time remaining warnings

#### Step 6: Handle Session Interruption

If session disconnects before training completes:

1. Start a **new Colab session**
2. **Re-run all cells** from Cell 1
3. **Cell 10** will auto-detect checkpoint and resume
4. Training continues from last saved epoch

**No manual intervention needed** - automatic resume!

#### Step 7: Export Model

After training completes:

1. **Cell 13**: Export to ONNX format
2. Model saved to: `models/phase2_iqa/mobilenet_v3_small_best.onnx`
3. Download from Google Drive to local machine

---

## Phase 3: YOLOv8 Layout Detection

### Training Overview

**Model**: YOLOv8n (nano) or YOLOv8s (small)
**Task**: Object detection (4 classes: table, image, handwriting, formula)
**Dataset**: 300,000+ annotated document pages
**Expected Time**: 50-80 hours (4-7 sessions)
**GPU Requirement**: V100 (recommended), P100, or T4

### Important: Multi-Session Training

YOLOv8 requires 100+ epochs. With 12-hour sessions:

| GPU | Epochs/Session | Sessions Needed | Total Time |
|-----|----------------|-----------------|------------|
| V100 | 15-20 | 5-7 | 60-84 hours |
| P100 | 12-18 | 6-8 | 72-96 hours |
| T4 | 10-15 | 7-10 | 84-120 hours |

**Plan for multiple sessions** across several days.

### Step-by-Step Instructions

#### Step 1: Prepare Dataset (YOLO Format)

**Dataset format** (required for YOLOv8):

```text
layout_phase3/
├── dataset.yaml          # Required: class names and paths
├── train/
│   ├── images/           # Training images
│   └── labels/           # YOLO format labels (.txt)
└── val/
    ├── images/           # Validation images
    └── labels/           # YOLO format labels (.txt)
```text

**dataset.yaml** structure:

```yaml
path: /content/drive/MyDrive/image-preprocessing-detector/datasets/layout_phase3
train: train/images
val: val/images

nc: 4  # Number of classes
names:
  0: table
  1: image
  2: handwriting
  3: formula
```text

**Label format** (YOLO `.txt` files):

```text
<class_id> <x_center> <y_center> <width> <height>
```text

All coordinates normalized to [0, 1].

#### Step 2: Upload Dataset & Config

1. Upload dataset to Google Drive (may take several hours)
2. Upload `configs/colab_phase3_yolov8.yaml`
3. Verify `dataset.yaml` paths are correct

#### Step 3: Open Training Notebook

1. Navigate to `notebooks/colab/phase3_yolov8_training.ipynb`
2. Open in Google Colab
3. **Runtime** → **Change runtime type** → **GPU**

#### Step 4: Start Training (First Session)

**Execute cells**:

1. **Cell 1**: Check GPU
2. **Cell 2**: Mount Google Drive
3. **Cell 3**: Install Ultralytics
4. **Cell 4**: Setup paths
5. **Cell 5**: Verify dataset
6. **Cell 6**: Initialize model
7. **Cell 7**: **Start training** ⏱️ (runs for 11.5 hours)

**Cell 7 will train for ~11.5 hours**, then auto-stop and save checkpoint.

#### Step 5: Resume Training (Subsequent Sessions)

**For each additional session**:

1. Open **new Colab session** (fresh 12-hour limit)
2. **Re-run cells 1-6** (setup)
3. **Cell 6** will detect `last.pt` checkpoint
4. **Re-run Cell 7** - training auto-resumes from last epoch

**Repeat until** `current_epoch >= 100` (target epochs).

#### Step 6: Monitor Progress

**Check progress** after each session:

- **Cell 10**: Shows current epoch / total epochs
- **Checkpoints**: `checkpoints/phase3_yolov8/last.pt` updated each session
- **Best model**: `checkpoints/phase3_yolov8/weights/best.pt` (best mAP)

**Typical session output**:

```text
Epoch 15/100: ▓▓▓▓▓░░░░░░░░░░░░░░ 15% complete
Session time remaining: 0.5 hours
Saving checkpoint... ✅
```text

#### Step 7: Validate & Export

Once training completes:

1. **Cell 8**: Validate best model (mAP metrics)
2. **Cell 9**: Export to ONNX
3. Download ONNX model from Google Drive

---

## Checkpoint Management

### How Checkpoints Work

**Automatic Saving**:

- Every 5 epochs (Phase 2) / 10 epochs (Phase 3)
- Every 30 minutes (Phase 2) / 60 minutes (Phase 3)
- At 11.5 hours (30min before session limit)

**Checkpoint Contents**:

- Model weights (`model_state_dict`)
- Optimizer state (`optimizer_state_dict`)
- Training metrics (loss, accuracy, etc.)
- Current epoch number
- Random number generator states (for reproducibility)

**Checkpoint Files**:

- `checkpoint_latest.pt`: Most recent checkpoint (auto-resume)
- `checkpoint_best.pt`: Best validation loss/mAP
- `checkpoint_epoch{N}_{timestamp}.pt`: Periodic checkpoints (last 3 kept)

### Manual Checkpoint Operations

**Check if checkpoint exists**:

```python
from pathlib import Path
checkpoint_path = Path("/content/drive/MyDrive/checkpoints/phase2_iqa/checkpoint_latest.pt")
if checkpoint_path.exists():
    print("Checkpoint found! Will resume training.")
```text

**Load specific checkpoint** (instead of latest):

```python
checkpoint_manager.load_checkpoint(
    model=model,
    optimizer=optimizer,
    checkpoint_path="/path/to/specific/checkpoint.pt"
)
```text

**Skip resume** (start from scratch):

- Delete `checkpoint_latest.pt` before running Cell 10/6

---

## Troubleshooting

### GPU Not Available

**Symptoms**: `torch.cuda.is_available() == False`

**Solutions**:

1. **Runtime** → **Change runtime type** → **GPU** (Hardware accelerator)
2. If still no GPU: Colab Pro GPU quota exhausted
   - Wait 12-24 hours for quota reset
   - Or upgrade to Colab Pro+ ($50/month) for priority access

**Check GPU usage**:

```python
from scripts.colab_utils import get_gpu_info
print(get_gpu_info())
```text

### Session Disconnects

**Symptom**: Browser tab disconnects before 12 hours

**Cause**: Colab detects inactivity

**Solution**:

- Keep browser tab **open and active**
- Disable browser sleep mode
- Optionally: Use browser extensions to simulate activity (e.g., Colab Alive)

**Checkpoint protection**: Even if disconnected, checkpoint saves to Google Drive.

### Out of Memory (OOM)

**Symptoms**: `CUDA out of memory` error

**Solutions**:

1. **Reduce batch size**:

   ```yaml
   # In config YAML
   training:
     batch_size: 32  # Reduce from 64
   ```

1. **Reduce image size** (Phase 2):

   ```yaml
   model:
     input_size: 224  # Reduce from 320
   ```

2. **Enable gradient accumulation**:

   ```yaml
   training:
     gradient_accumulation_steps: 2  # Simulate larger batch size
   ```

3. **Clear GPU memory**:

   ```python
   from scripts.colab_utils import clear_gpu_memory
   clear_gpu_memory()
   ```

### Dataset Not Found

**Symptom**: `FileNotFoundError: Dataset not found`

**Causes**:

- Google Drive not mounted
- Incorrect path in config
- Dataset not uploaded yet

**Solutions**:

1. **Verify mount**:

   ```bash
   !ls /content/drive/MyDrive/
   ```

2. **Check dataset path**:

   ```bash
   !ls /content/drive/MyDrive/image-preprocessing-detector/datasets/
   ```

3. **Update config**:

   ```yaml
   paths:
     dataset_root: "/content/drive/MyDrive/datasets/iqa_phase2"  # Adjust path
   ```

### Slow Training

**Symptoms**: < 1 epoch/hour (Phase 2) or < 5 epochs/hour (Phase 3)

**Causes**:

- T4 GPU (slower than V100)
- Large batch size causing memory swapping
- Data loading bottleneck

**Solutions**:

1. **Check GPU type**:

   ```python
   !nvidia-smi  # Should show V100 for best speed
   ```

2. **Optimize data loading**:
   - Dataset on local SSD (`/content/data`) not Google Drive
   - Increase `num_workers: 2` (Colab limit)
   - Enable `pin_memory: true`

3. **Enable mixed precision** (should be default):

   ```yaml
   training:
     mixed_precision:
       enabled: true
   ```

### Quota Exceeded

**Symptom**: "You have exceeded your compute units quota"

**Cause**: Used >100 compute units (Colab Pro monthly limit)

**Solutions**:

1. Wait for monthly reset (1st of month)
2. Upgrade to Colab Pro+ ($50/month, 500 units)
3. Use another Google account (not recommended)

---

## Cost Estimates

### Colab Pro Subscription

**Phase 2 Only**:

- 1 month: $10
- ~15-20 hours training
- Well within 100 compute units

**Phase 2 + Phase 3**:

- 2-3 months: $20-30
- ~65-100 total GPU hours
- Within 100-200 compute units

**Comparison to Alternatives**:

| Platform | Phase 2 | Phase 2+3 | Notes |
|----------|---------|-----------|-------|
| **Colab Pro** | **$10** | **$20-30** | Best value |
| Colab Pro+ | $50 | $50-100 | Faster, overkill |
| AWS P3 (V100) | $30-40 | $100-160 | Hourly rate |
| GCP P100 | $25-35 | $80-140 | Hourly rate |
| Local GPU | $0 | $0 | Requires $1500+ workstation |

### Google Drive Storage

**Phase 2 Storage**: ~25GB
**Phase 3 Storage**: ~50GB
**Total**: ~75GB

**Plans**:

- 15GB: Free (not enough)
- 100GB: $1.99/month ✅ Recommended
- 200GB: $2.99/month (extra headroom)

**Total Monthly Cost**: $10 (Colab Pro) + $2 (Drive) = **$12/month**

---

## Best Practices

### Session Management

1. **Start training early in the day** (not before sleep)
2. **Monitor first 30 minutes** to catch errors early
3. **Keep browser tab open** (disable sleep mode)
4. **Check progress** every 2-3 hours
5. **Plan Phase 3** to run across 5-7 days (1 session/day)

### Data Organization

1. **Use consistent paths** in all configs
2. **Document dataset versions** (e.g., `iqa_phase2_v1`)
3. **Keep checkpoints organized** by experiment name
4. **Delete old checkpoints** to save space (keep last 3)

### Experimentation

1. **Start with small experiments** (10 epochs) to test setup
2. **Validate dataset** before full training run
3. **Monitor TensorBoard** for training issues (overfitting, etc.)
4. **Save config file** with each experiment for reproducibility

### Security

1. **Never commit Google Drive credentials** to Git
2. **Use environment variables** for API keys (if any)
3. **Keep dataset private** if contains sensitive data

---

## Next Steps After Training

### Phase 2 Post-Training

1. **Download ONNX model** from Google Drive
2. **Run evaluation** on test set (separate notebook)
3. **Integrate model** into pipeline (`src/detection/iqa_ml.py`)
4. **Test locally** with ONNX Runtime (no GPU needed)

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

- **PROJECT_PLAN.md**: Overall project roadmap
- **ARCHITECTURE_CORRECTION.md**: Design decisions
- **notebooks/colab/README.md**: Notebook-specific docs

### External Resources

- **Google Colab Docs**: <https://colab.research.google.com/notebooks/>
- **Ultralytics YOLOv8**: <https://docs.ultralytics.com/>
- **PyTorch Lightning**: <https://lightning.ai/docs/pytorch/>
- **TensorBoard**: <https://www.tensorflow.org/tensorboard>

### Issue Reporting

If you encounter issues:

1. Check this guide first
2. Review notebook cell outputs for error messages
3. Search existing GitHub issues
4. Create new issue with:
   - Colab notebook name
   - Error message
   - GPU type (from `!nvidia-smi`)
   - Config file used

---

## FAQ

**Q: Can I use Colab Free tier?**
A: Yes, but with limitations:

- 12-hour session limit (same as Pro)
- T4 GPU only (slower)
- GPU availability not guaranteed
- No priority access during peak times

**Q: Can multiple sessions run in parallel?**
A: No, Colab Pro allows only 1 active GPU session at a time.

**Q: What happens if I exceed 12 hours?**
A: Training auto-stops at 11.5 hours and saves checkpoint. Start new session and resume.

**Q: Can I switch GPUs between sessions?**
A: Yes, checkpoints work across different GPU types (V100/P100/T4).

**Q: How do I check remaining compute units?**
A: No official way, but you'll get warning when approaching limit.

**Q: Can I pause training mid-session?**
A: Not directly, but checkpoints save every 30-60 minutes. Interrupt training, checkpoint loads at next session.

---

**Document Version**: 1.0
**Last Reviewed**: 2025-01-15
**Maintainer**: Byron Williams
