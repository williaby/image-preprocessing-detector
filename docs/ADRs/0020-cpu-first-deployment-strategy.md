---
schema_type: common
title: "ADR-020: CPU-First Deployment Strategy for Phase 1"
description: "Deploy Phase 1 MVP with CPU-only operation, reserving GPU for Phase
  2-3 ML models"
tags: [adr, deployment, cpu, gpu, performance]
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to deploy Phase 1 with CPU-only operation and defer
  GPU infrastructure to Phase 2."
---


**Status**: Accepted
**Date**: 2025-11-04
**Deciders**: Byron Williams
**Related**:

- [PHASE_1_KICKOFF.md](../../PHASE_1_KICKOFF.md)
- [PHASE_1_COMPLETE.md](../../PHASE_1_COMPLETE.md)
- [ADR-014: Classical CV + ML Hybrid for IQA](0014-classical-ml-hybrid-iqa.md)

## Context

Phase 1 MVP uses classical computer vision methods (Hough transform, Laplacian, histogram analysis) that can run on CPU or GPU. We needed to decide whether to require GPU from Phase 1 or deploy CPU-first and add GPU later.

### Hardware Available

**Development Machine**:

- CPU: 2× Intel Xeon E5-2690 (16 cores, 32 threads total)
- GPU: NVIDIA Quadro P2000 (5GB VRAM, 1024 CUDA cores)
- RAM: 64GB DDR4

**Performance Considerations**:

- Classical CV operations: CPU-optimized (OpenCV)
- GPU acceleration: Minimal benefit for classical methods (~10-20% speedup)
- GPU reserved for: Phase 2 ML training, Phase 3 inference

## Decision

**Deploy Phase 1 with CPU-only operation, reserve Quadro P2000 GPU for Phase 2-3 ML workloads.**

### Phase 1 Performance Targets (CPU)

**Latency**: < 2s per page
**Throughput**: 0.5 pages/second (single thread)

**Achieved Performance** (Phase 1 Complete):

- End-to-end: ~800ms per page (exceeds target)
- PDF rendering: ~300ms
- Text detection: <50ms
- Classical IQA: ~170ms (skew, blur, contrast)
- Corrections: ~280ms (deskew, CLAHE, sharpening)

## Consequences

### Positive

1. **Broader Deployment**: No GPU requirement for Phase 1 MVP
2. **Cost Savings**: CPU-only instances cheaper than GPU instances
3. **Simplified Setup**: No CUDA drivers, GPU memory management
4. **Hardware Flexibility**: Runs on any modern CPU (no NVIDIA requirement)
5. **Reserved GPU**: Quadro P2000 available for Phase 2 ML training
6. **Lower Risk**: CPU-only deployment easier to debug and maintain

### Negative

1. **Slower Throughput**: 0.5 pages/sec vs ~6 pages/sec on GPU (Phase 3 target)
2. **Limited Scalability**: CPU-bound for batch processing
3. **Future Migration**: Will need deployment changes when adding GPU in Phase 2-3

### Neutral

1. **Phase 2 Transition**: ML models will require GPU infrastructure
2. **Hardware Utilization**: Quadro P2000 idle during Phase 1 (acceptable)

## Alternatives Considered

### Alternative 1: GPU-First from Phase 1

**Approach**: Require CUDA GPU for all deployments from Phase 1

**Advantages**:

- Faster classical CV operations (~10-20% speedup)
- GPU infrastructure ready for Phase 2
- Higher throughput potential

**Disadvantages**:

- Limits deployment targets (requires NVIDIA GPU)
- Higher cost ($0.50/hr GPU vs $0.10/hr CPU on cloud)
- Complexity (CUDA drivers, GPU memory management)
- Classical CV gains minimal benefit from GPU

**Why Rejected**: Classical methods don't benefit enough to justify GPU requirement

### Alternative 2: Hybrid CPU/GPU Deployment

**Approach**: Support both CPU and GPU, automatic detection

**Advantages**:

- Flexibility
- Automatic acceleration if GPU available
- Graceful degradation

**Disadvantages**:

- Code complexity (dual code paths)
- Testing overhead (both modes)
- Maintenance burden

**Why Rejected**: Premature optimization, adds complexity for minimal Phase 1 benefit

### Alternative 3: Cloud GPU Instances

**Approach**: Deploy on cloud GPU instances (AWS p3, GCP T4)

**Advantages**:

- Scalable GPU access
- Pay-per-use

**Disadvantages**:

- Higher cost ($0.50-3.00/hr vs $0.10/hr CPU)
- Overkill for classical CV
- Vendor lock-in

**Why Rejected**: Excessive cost for minimal Phase 1 benefit

## Implementation

### Phase 1 CPU-Only Operation

**Classical Detectors** (CPU-optimized):

```python
class SkewDetector:
    def detect(self, image: np.ndarray) -> SkewResult:
        # Hough transform (CPU-optimized via OpenCV)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, ...)

        # Projection profile (numpy CPU operations)
        projection = np.sum(edges, axis=1)
        ...
```

**Performance Optimization**:

- Single-threaded: ~800ms/page
- Multi-threaded (4 workers): ~2 pages/sec aggregate throughput
- Batch processing: Queue-based parallelism

### Phase 2-3 GPU Integration (Planned)

**ML Models** (GPU-required):

```python
class IQAClassifier:
    def __init__(self):
        if torch.cuda.is_available():
            self.device = "cuda"
            self.model = load_model().to("cuda")
        else:
            raise RuntimeError("GPU required for ML models")

    def predict(self, image: np.ndarray):
        # Inference on GPU
        tensor = torch.from_numpy(image).to(self.device)
        return self.model(tensor)
```

**Hybrid Deployment**:

```python
# Phase 3: CPU fallback if GPU unavailable
if torch.cuda.is_available():
    iqa_detector = HybridIQADetector()  # Classical + ML ensemble
else:
    logger.warning("GPU unavailable, using classical detectors only")
    iqa_detector = ClassicalIQADetector()  # CPU-only fallback
```

### Deployment Configurations

**Phase 1 (Current)**:

- Instance: CPU-only (e.g., AWS c5.2xlarge, 8 vCPUs)
- Throughput: 0.5 pages/sec (single worker)
- Cost: ~$0.10/hr

**Phase 2 (ML Training)**:

- Instance: GPU (NVIDIA Quadro P2000 local, or AWS p3.2xlarge)
- Training: 10-20 hours for IQA classifier
- Cost: ~$3/hr (cloud) or $0/hr (local)

**Phase 3 (ML Inference)**:

- Instance: GPU (AWS p3.2xlarge or g4dn.xlarge T4)
- Throughput: 6+ pages/sec (with YOLOv8 + ML IQA)
- Cost: ~$0.50-1.00/hr

## Performance Benchmarks

### Phase 1 CPU Performance (Actual)

| Operation | Time (ms) | CPU Cores | Notes |
|-----------|-----------|-----------|-------|
| PDF rendering | ~300ms | Single | PyMuPDF |
| Text detection | <50ms | Single | OpenCV ensemble |
| Skew detection | ~100ms | Single | Hough + projection |
| Blur detection | ~20ms | Single | Laplacian |
| Contrast detection | ~30ms | Single | Histogram |
| Deskew correction | ~150ms | Single | Affine transform |
| CLAHE enhancement | ~100ms | Single | Adaptive histogram |
| Sharpening | ~80ms | Single | Unsharp mask |
| **Total** | **~800ms** | **Single** | **End-to-end** |

### Phase 3 GPU Performance (Projected)

| Operation | GPU Time | CPU Time | Speedup |
|-----------|----------|----------|---------|
| YOLOv8 layout | ~20ms | ~200ms | 10× |
| ML IQA classifier | ~30ms | ~200ms | 6.7× |
| Classical IQA | ~170ms | ~170ms | 1× (no benefit) |
| **Total** | **~220ms** | **~570ms** | **2.6×** |

**Note**: Classical operations (Hough, Laplacian) see minimal GPU benefit

## Hardware Utilization

**Phase 1 (Current)**:

- CPU: 100% utilized (classical CV)
- GPU: 0% utilized (idle)
- GPU Status: Reserved for Phase 2 training

**Phase 2 (ML Training)**:

- CPU: 30% utilized (data loading)
- GPU: 90% utilized (model training)
- Duration: 10-20 hours for IQA classifier

**Phase 3 (Production)**:

- CPU: 40% utilized (preprocessing, data movement)
- GPU: 80% utilized (YOLOv8 + ML IQA inference)

## References

- [PHASE_1_KICKOFF.md Hardware Specifications](../../PHASE_1_KICKOFF.md#hardware-specifications)
- [PHASE_1_COMPLETE.md Performance Benchmarks](../../PHASE_1_COMPLETE.md#performance-benchmarks)
- [ADR-014: Classical CV + ML Hybrid for IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-015: YOLOv8 for Layout Detection](0015-yolov8-layout-detection.md)

## Lessons Learned

1. **Classical CV is CPU-Efficient**: Minimal GPU benefit for Hough, Laplacian, histograms
2. **Reserve GPU for ML**: Better to save GPU for Phase 2-3 where it provides 6-10× speedup
3. **CPU Performance Sufficient**: 800ms/page meets Phase 1 MVP requirements
4. **Graceful Phase Transition**: CPU-first allows smooth migration to GPU in Phase 2-3
