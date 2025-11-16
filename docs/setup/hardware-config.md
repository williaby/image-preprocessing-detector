---
schema_type: common
title: "Hardware Configuration - Phase 2 Training"
tags:
  - installation
  - training
  - infrastructure
  - gpu
status: published
owner: platform-team
purpose: Setup guide for hardware configuration - phase 2 training.
---

**Generated**: 2025-11-12
**Environment**: Development Machine (WSL2)

---

## GPU Configuration

### Available Hardware

**GPU**: NVIDIA RTX A500 Laptop GPU
- **VRAM**: 4096 MB (4 GB)
- **Driver Version**: 573.57 (Host), 570.176 (WSL2)
- **CUDA Version**: 12.8
- **Compute Capability**: ~8.6 (Ampere architecture)
- **Status**: Available and idle (0% utilization)

### Training Implications

**4GB VRAM Considerations**:
- ✅ **Sufficient** for MobileNetV3-Small training (lightweight model)
- ⚠️ **Limited** for larger batch sizes - recommend batch_size ≤ 16
- ⚠️ **May struggle** with EfficientNet-B0 at larger input sizes (320×320)
- ✅ **Adequate** for ONNX Runtime inference testing

**Recommended Configuration for Phase 2**:
```python
# Training Configuration (models/iqa/config.py)
BATCH_SIZE = 8  # Conservative for 4GB VRAM (vs 32 in plan)
INPUT_SIZE = 224  # Standard size (vs 320 for higher accuracy)
NUM_WORKERS = 2  # Match physical cores, leave headroom
ACCUMULATE_GRAD_BATCHES = 4  # Effective batch size = 32
```

**Alternative Strategies**:
1. **Mixed Precision Training** (FP16/BF16): Reduce memory by ~50%
2. **Gradient Accumulation**: Simulate larger batches
3. **CPU Training**: Slower but no memory constraints (~30-60 min/epoch vs 5-10 min/epoch)
4. **Cloud GPU**: Rent V100/A10 if needed (~$1.50/hr for 8-16GB VRAM)

---

## CPU Configuration

```
Platform: linux (WSL2 on Windows)
Architecture: x86_64
Cores: 8 logical processors
```

**CPU-Only Training** (Fallback):
- Training time: 30-60 minutes per epoch (vs 5-10 minutes on GPU)
- Total training: 4-8 hours for 50 epochs with early stopping
- Inference: 8-15ms per image (acceptable for development)

---

## Storage Configuration

**Available Space**: Assumed sufficient (need ~50GB for Phase 2)

**Dataset Storage Plan**:
```
data/raw/              # 10GB (10k+ clean images)
data/augmented/        # 15GB (50k augmented images)
data/labels/           # 500MB (labels, metadata)
models/iqa/            # 5GB (checkpoints, ONNX models)
Total Estimated:       # ~30GB
```

---

## Phase 2 Training Strategy

### Recommended Approach (4GB VRAM)

**Model Selection**: MobileNetV3-Small (Phase 2 MVP)
- Model size: 2.5MB
- Parameters: ~2.5M
- Memory footprint: ~1.5GB with batch_size=8, input_size=224
- **Fits comfortably in 4GB VRAM**

**Training Configuration**:
```python
config = TrainingConfig(
    model_name="mobilenetv3_small",
    input_size=224,
    batch_size=8,  # Conservative
    accumulate_grad_batches=4,  # Effective batch_size=32
    num_epochs=50,
    learning_rate=1e-3,
    num_workers=2,
    mixed_precision=True,  # Enable AMP for memory savings
)
```

**Expected Performance**:
- Training time: 20-30 minutes per epoch
- Total training: 5-10 hours for 50 epochs (with early stopping ~15-20 epochs)
- Inference: 1-3ms per image (GPU)

### Alternative: CPU Training

If GPU memory becomes an issue:
```bash
# Force CPU training
export CUDA_VISIBLE_DEVICES=""
poetry run python scripts/train_iqa.py --device cpu --batch-size 16
```

**CPU Training Estimates**:
- Training time: 45-60 minutes per epoch
- Total training: 6-12 hours for 50 epochs
- Still viable for Phase 2 MVP

### Cloud GPU Option

If more VRAM needed for EfficientNet-B0 or larger batches:
- **Google Colab Pro**: T4 (16GB) for $10/month
- **AWS EC2 g4dn.xlarge**: T4 (16GB) at $0.526/hr
- **Lambda Labs**: A10 (24GB) at $0.60/hr
- **Estimated cost**: $20-50 for Phase 2 training

---

## Verification

```bash
# Verify GPU availability in PyTorch
poetry run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# Check CUDA version
nvcc --version || echo "NVCC not installed (not required for inference)"

# Memory available
nvidia-smi --query-gpu=memory.total,memory.free --format=csv
```

---

## Next Steps

1. ✅ **ML Dependencies**: Install torch, torchvision, timm, albumentations
2. ⚠️ **Test Training**: Run small training test to verify GPU memory usage
3. 📝 **Adjust Batch Size**: Fine-tune batch size based on actual memory usage
4. 🚀 **Begin Training**: Start with MobileNetV3-Small on 4GB VRAM

---

## Notes

- **4GB VRAM is workable** for Phase 2 MVP with MobileNetV3-Small
- Mixed precision training recommended to maximize VRAM efficiency
- CPU training is viable fallback if GPU issues arise
- Phase 3 (YOLOv8) may require cloud GPU for larger models

---

*Last Updated: 2025-11-12*
*GPU: NVIDIA RTX A500 Laptop (4GB VRAM)*
*Status: Ready for Phase 2 training*
