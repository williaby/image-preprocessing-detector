---
schema_type: common
title: "ADR-027: INT8 Quantization via ONNX/TensorRT"
description: "Use INT8 quantization for 1.5-3× speedup with < 2% accuracy loss"
tags: [adr, quantization, onnx, tensorrt, optimization, int8]
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use INT8 quantization for production deployment
  optimization."
---


**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [ADR-025: MobileNetV3](0025-mobilenetv3-vs-efficientnet.md)
- [ADR-015: YOLOv8](0015-yolov8-layout-detection.md)
- [PROJECT_PLAN.md Phase 2-3](../../PROJECT_PLAN.md)

## Context

Production deployment requires optimizing model inference for latency and throughput. FP32 models are 4× larger and 2-3× slower than INT8 quantized models.

**Performance Requirements**:
- IQA: < 50ms GPU, < 200ms CPU
- YOLOv8: < 50ms GPU, < 70ms CPU (ONNX INT8)
- Accuracy loss: < 2% acceptable

## Decision

**Use INT8 quantization via ONNX Runtime for CPU, TensorRT for GPU.**

### Quantization Strategy

**IQA Classifier**:
- FP32 → INT8 via ONNX Runtime
- Post-training quantization (no retraining)
- Speedup: 1.5-2× (CPU), 1.2-1.5× (GPU)
- Accuracy drop: < 1% mAP

**YOLOv8 Layout Detector**:
- FP32 → INT8 via TensorRT
- Post-training quantization
- Speedup: 2-3× (GPU)
- Accuracy drop: < 2% mAP@.50

### Quantization Workflow

```python
# Export PyTorch → ONNX
torch.onnx.export(model, dummy_input, "model.onnx")

# Quantize ONNX (INT8)
from onnxruntime.quantization import quantize_dynamic
quantize_dynamic("model.onnx", "model_int8.onnx", weight_type=QuantType.QInt8)

# Load quantized model
import onnxruntime as ort
session = ort.InferenceSession("model_int8.onnx")
```

## Performance Impact

| Model | Precision | Size | GPU Latency | CPU Latency | Accuracy |
|-------|-----------|------|-------------|-------------|----------|
| IQA MobileNetV3 (FP32) | FP32 | 11MB | 30ms | 150ms | 0.88 mAP |
| IQA MobileNetV3 (INT8) | INT8 | 3MB | 25ms | 100ms | 0.87 mAP |
| YOLOv8n (FP32) | FP32 | 6MB | 20ms | 70ms | 0.82 mAP |
| YOLOv8n (INT8) | FP16 | 3MB | 12ms | 25ms | 0.81 mAP |

**INT8 delivers 1.5-3× speedup with < 2% accuracy loss.**

## Consequences

### Positive

1. **Faster Inference**: 1.5-3× speedup
2. **Smaller Models**: 3-4× size reduction
3. **Lower Memory**: 4× memory reduction
4. **Higher Throughput**: 1.5-3× more pages/sec

### Negative

1. **Accuracy Loss**: 1-2% mAP drop
2. **Calibration Required**: Need representative calibration dataset
3. **Complexity**: Additional deployment step

## References

- [ONNX Runtime Quantization](https://onnxruntime.ai/docs/performance/quantization.html)
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [ADR-025: MobileNetV3](0025-mobilenetv3-vs-efficientnet.md)
