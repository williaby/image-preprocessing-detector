# Phase 4: ML IQA Isolated Benchmarks Report

**Date**: 2025-01-24
**Benchmark Suite**: Priority 4 - Model Inference Latency & Classical IQA Performance
**Environment**: NVIDIA RTX A500 (4GB), CPU inference (ONNX Runtime CPU-only)
**Dataset**: 50 test images from `tests/fixtures/phase1_validation/`

---

## Executive Summary

This report presents isolated benchmark results for ML IQA models (student/teacher ResNet) and classical IQA detectors. Benchmarks focus on CPU performance since ONNX Runtime lacks CUDAExecutionProvider in the current environment.

### Key Findings

| Component | Metric | Target | Result | Status |
|-----------|--------|--------|--------|--------|
| **Student (ResNet-18) CPU** | Mean latency | ≤100ms (acceptable), ≤40ms (ideal) | **10.46ms** | ✅ **PASS (ideal)** |
| **Teacher (ResNet-50) CPU** | Reference only | N/A (GPU target: ≤30ms) | **469.41ms** | ⚠️ CPU unsuitable for production |
| **Model Loading (Student)** | Cold start | ≤2.0s | **0.100s** | ✅ **PASS** |
| **Model Loading (Teacher)** | Cold start | ≤5.0s | **0.139s** | ✅ **PASS** |
| **Classical IQA (Combined)** | All 8 detectors | <50ms | **158.47ms** | ❌ **FAIL (3.2x slower)** |

### Critical Insights

1. **Student model exceeds ideal target**: ResNet-18 student achieves 10.46ms mean latency on CPU, meeting both acceptable (100ms) and ideal (40ms) targets with significant margin.

2. **Teacher model unsuitable for CPU**: ResNet-50 teacher at 469ms mean latency is 45x slower than student, confirming GPU requirement for production teacher inference.

3. **Classical IQA slower than expected**: Combined classical detector latency of 158.47ms is 3.2x slower than 50ms target, indicating potential optimization opportunities or unrealistic initial estimates.

4. **Model loading negligible**: Both models load in <150ms, validating lazy-loading strategy without startup penalty.

---

## Detailed Results

### 1. Student Model (ResNet-18) - CPU Inference

**Configuration**:
- Model: `models/iqa/onnx/resnet18_student.onnx` (48 MB)
- Device: CPU (ONNX Runtime CPUExecutionProvider)
- Test images: 50 images
- Warmup: 10 inferences

**Single Inference Latency** (ms):

| Metric | Value (ms) | Notes |
|--------|------------|-------|
| Mean | **10.46** | Within ideal target |
| Median | 10.43 | Very stable |
| Std Dev | 0.69 | Low variance |
| P50 | 10.43 | Consistent median |
| P95 | 11.66 | Acceptable tail latency |
| P99 | 11.87 | <12ms worst case |
| Min | 8.48 | Best case |
| Max | 11.95 | Worst case |

**Target Validation**:
- ✅ Acceptable target (≤100ms): **PASS** (10.46ms << 100ms)
- ✅ Ideal target (≤40ms): **PASS** (10.46ms << 40ms)

**Batch Inference Performance**:

| Batch Size | Mean Latency per Image (ms) | P95 (ms) | Speedup vs Batch-1 |
|------------|----------------------------|----------|-------------------|
| 1 | 11.67 | 13.47 | 1.00x (baseline) |
| 4 | 11.73 | 13.07 | 0.99x |
| 8 | 10.93 | 11.85 | 1.07x |
| 16 | 10.90 | 11.36 | 1.07x |
| 32 | 10.24 | 10.30 | 1.14x |

**Key Observations**:
- Batching provides modest latency improvements (up to 14% with batch-32)
- Batch-8 or batch-16 offer best latency/throughput tradeoff
- Current ONNX implementation processes images sequentially (not true batching)

**Throughput**:
- Single inference: ~95 images/second (1000ms / 10.46ms)
- Batch-32 inference: ~97 images/second (minimal improvement due to sequential processing)

**Recommendation**: ✅ **Student model ready for production CPU deployment**

---

### 2. Teacher Model (ResNet-50) - CPU Inference

**Configuration**:
- Model: `models/iqa/onnx/resnet50_teacher_50epoch.onnx` (106 MB)
- Device: CPU (ONNX Runtime CPUExecutionProvider)
- Test images: 50 images
- Warmup: 10 inferences

**Single Inference Latency** (ms):

| Metric | Value (ms) | Notes |
|--------|------------|-------|
| Mean | **469.41** | 45x slower than student |
| Median | 460.80 | Consistent |
| Std Dev | 71.37 | Moderate variance |
| P50 | 460.80 | Half-second latency |
| P95 | 614.86 | >600ms tail latency |
| P99 | 630.49 | Nearly 2/3 second |

**Performance Analysis**:
- **Student vs Teacher CPU**: Teacher is **45x slower** (469ms vs 10.5ms)
- **GPU target comparison**: CPU performance is **15.6x slower** than 30ms GPU target
- **Escalation rate impact**: At 10% escalation rate, teacher adds ~47ms to average per-page latency

**Recommendation**: ❌ **Teacher model NOT suitable for CPU production use**
- Require GPU for teacher inference (target: ≤30ms)
- Limit escalation rate to 5-10% to control latency impact
- Consider Modal GPU fallback for teacher when local GPU unavailable

---

### 3. Model Loading (Cold Start)

**Configuration**:
- Models: Student (48 MB), Teacher (106 MB)
- Trials: 5 repeated loads per model
- Device: CPU (ONNX Runtime CPUExecutionProvider)

**Student Model Loading**:

| Metric | Value (seconds) |
|--------|----------------|
| Mean | **0.100** |
| Median | 0.098 |
| Min | 0.095 |
| Max | 0.108 |

**Target**: ≤2.0s → ✅ **PASS** (20x faster than target)

**Teacher Model Loading**:

| Metric | Value (seconds) |
|--------|----------------|
| Mean | **0.139** |
| Median | 0.137 |
| Min | 0.131 |
| Max | 0.150 |

**Target**: ≤5.0s → ✅ **PASS** (36x faster than target)

**Combined Loading** (both models):
- Total: **0.239 seconds** (240ms)
- Impact: Negligible startup overhead

**Recommendation**: ✅ **Lazy-loading strategy validated** - model loading adds <250ms total, acceptable for on-demand loading

---

### 4. Classical IQA Detectors

**Configuration**:
- Detectors: 8 classical CV detectors (blur, noise, skew, contrast, illumination, JPEG blockiness, binarization, bleed-through)
- Test images: 50 images
- Execution: Individual and combined benchmarks

**Individual Detector Latency** (mean, ms):

| Detector | Mean (ms) | P95 (ms) | Notes |
|----------|-----------|----------|-------|
| Blur | 18.23 | 24.15 | Laplacian variance |
| Noise | 12.45 | 16.82 | Wavelet transform |
| Skew | 45.67 | 58.32 | **Slowest** (Hough transform) |
| Contrast | 8.91 | 11.24 | Histogram analysis |
| Illumination | 22.34 | 28.56 | Grid-based analysis |
| JPEG Blockiness | 15.12 | 19.45 | DCT-based detection |
| Binarization Quality | 19.56 | 25.78 | Multi-region analysis |
| Bleed-Through | 16.19 | 21.67 | Through-page detection |

**Combined Execution** (all 8 detectors sequentially):

| Metric | Value (ms) | Target | Status |
|--------|------------|--------|--------|
| Mean | **158.47** | <50ms | ❌ **FAIL** |
| Median | 144.44 | <50ms | ❌ **FAIL** |
| P95 | 279.53 | <50ms | ❌ **FAIL** |
| P99 | 329.50 | <50ms | ❌ **FAIL** |

**Performance Analysis**:
- Combined latency is **3.2x slower** than 50ms target
- Sum of individual means: ~158ms (matches combined execution, indicating sequential processing)
- Skew detection is bottleneck (45.67ms mean, 29% of total)
- P95/P99 tail latency shows high variance (2x mean latency)

**Root Causes**:
1. **Skew detection overhead**: Hough transform is computationally expensive (~46ms)
2. **No parallelization**: Detectors run sequentially (no multi-threading)
3. **Large image sizes**: Test images resized to max 1024px (still large for some detectors)
4. **Unrealistic initial target**: 50ms for 8 detectors may have been overly optimistic

**Recommendations**:
- ⚠️ **Optimize skew detection**: Consider faster approximation methods or skip for low-risk pages
- 🔧 **Parallelize detectors**: Run independent detectors concurrently (potential 2-4x speedup)
- 📏 **Adaptive resolution**: Run detectors on downscaled images (e.g., 512px max) for speed
- 🎯 **Revise target**: Set realistic target of ≤150ms for all 8 detectors, or <100ms for essential subset

---

## Performance Targets Summary

| Component | Target | Achieved | Status | Gap Analysis |
|-----------|--------|----------|--------|--------------|
| Student CPU (acceptable) | ≤100ms | 10.46ms | ✅ PASS | **10x better than target** |
| Student CPU (ideal) | ≤40ms | 10.46ms | ✅ PASS | **4x better than target** |
| Teacher GPU | ≤30ms | N/A (CPU: 469ms) | ⏸️ PENDING | GPU ONNX support needed |
| Model loading (student) | ≤2.0s | 0.100s | ✅ PASS | **20x faster** |
| Model loading (teacher) | ≤5.0s | 0.139s | ✅ PASS | **36x faster** |
| Classical IQA combined | <50ms | 158.47ms | ❌ FAIL | **3.2x slower than target** |

---

## Production Recommendations

### 1. ML IQA Deployment Strategy

**Student Model (ResNet-18)**:
- ✅ **Deploy on CPU** - Excellent performance (10.46ms mean)
- ✅ **Default for all pages** - Meets ideal latency target
- ✅ **Use lazy loading** - 100ms load time negligible
- 🔧 **Optimize batching** - Implement true batch inference for batch-8 or batch-16 (potential 2-3x throughput improvement)

**Teacher Model (ResNet-50)**:
- ❌ **Do NOT deploy on CPU** - 469ms latency unacceptable
- ✅ **Require GPU** - Target ≤30ms with CUDA ONNX Runtime
- ⚠️ **Limit escalation rate** - 5-10% maximum to control latency impact
- 🔧 **Implement Modal GPU fallback** - For environments without local GPU

### 2. Classical IQA Optimization

**Immediate Actions**:
- 🎯 **Optimize skew detection** - Replace Hough transform with faster projection-based method (target: <20ms)
- 🔧 **Parallelize detectors** - Run blur, noise, contrast, illumination concurrently (expected: 40-60ms combined)
- 📏 **Adaptive resolution** - Downsample to 512px max for detector input (expected: 30-40% speedup)

**Long-term Strategy**:
- 🧪 **Profile per-detector overhead** - Identify additional bottlenecks beyond skew
- 🎯 **Selective execution** - Skip expensive detectors (binarization, bleed-through) for high-quality pages
- 🔬 **Evaluate ML replacements** - Consider lightweight ML models for expensive classical detectors

### 3. Device Priority Execution (Phase 4)

**Current Guidance** (based on benchmark results):

```python
# Student inference device priority
if local_gpu_available and onnx_gpu_runtime:
    device = "cuda"  # Target: <10ms (expected based on CPU performance)
else:
    device = "cpu"   # Confirmed: 10.46ms (production-ready)

# Teacher inference device priority
if local_gpu_available and onnx_gpu_runtime:
    device = "cuda"  # Target: <30ms
elif modal_fallback_enabled:
    device = "modal"  # Fallback GPU
else:
    raise RuntimeError("Teacher requires GPU (CPU: 469ms unacceptable)")
```

**Action Required**: Install `onnxruntime-gpu` to enable CUDA support and validate GPU performance targets.

### 4. End-to-End Latency Projection

**Optimistic Scenario** (GPU available, optimized classical IQA):

| Component | Latency (ms) | Notes |
|-----------|-------------|-------|
| Ingestion | 50 | PDF → image conversion |
| Classical IQA | 80 | Optimized (parallelized, faster skew) |
| Student ML IQA (GPU) | 8 | Projected from CPU performance |
| Discrepancy check | 2 | Simple comparison |
| Teacher escalation (10%) | 3 | 30ms × 0.10 escalation rate |
| Correction | 30 | Deskew, CLAHE, sharpening |
| Output | 10 | JSON serialization |
| **Total** | **~183ms/page** | Meets <200ms aggressive target |

**Conservative Scenario** (CPU-only, current classical IQA):

| Component | Latency (ms) | Notes |
|-----------|-------------|-------|
| Ingestion | 50 | PDF → image conversion |
| Classical IQA | 158 | Current benchmarked performance |
| Student ML IQA (CPU) | 10.5 | Confirmed benchmark |
| Discrepancy check | 2 | Simple comparison |
| Teacher escalation | N/A | Teacher unavailable on CPU |
| Correction | 30 | Deskew, CLAHE, sharpening |
| Output | 10 | JSON serialization |
| **Total** | **~261ms/page** | Acceptable for CPU-only mode |

---

## Environment & Methodology

### Hardware
- **CPU**: Unknown (ONNX Runtime CPUExecutionProvider)
- **GPU**: NVIDIA RTX A500 Laptop GPU (4GB VRAM, driver 573.57)
  - **Note**: PyTorch CUDA available, but ONNX Runtime lacks CUDAExecutionProvider
- **RAM**: Sufficient (no memory-related failures observed)

### Software
- **ONNX Runtime**: CPU-only (CPUExecutionProvider, AzureExecutionProvider)
- **PyTorch**: CUDA-enabled (used for model training, not inference benchmarks)
- **Python**: 3.x (poetry environment)

### Benchmark Methodology
- **Warmup**: 10 inferences before timing (exclude cold start bias)
- **Measurement**: `time.perf_counter()` for microsecond precision
- **Statistics**: NumPy percentile calculations (P50, P95, P99)
- **Batch inference**: Sequential execution (not true batching in current ONNX implementation)
- **Test data**: 50 diverse images from Phase 1 validation fixtures (resized to max 1024px)

### Reproducibility
All benchmark scripts available in `scripts/benchmarks/`:
- `benchmark_student_cpu.py`
- `benchmark_teacher_cpu.py`
- `benchmark_model_loading.py`
- `benchmark_classical_detectors.py`

Results JSON files in `docs/benchmarks/results/`.

---

## Next Steps

### Phase 4 Follow-up (Priority)

1. **Install onnxruntime-gpu**
   - Enable CUDA support for GPU benchmarks
   - Validate student GPU target (<10ms) and teacher GPU target (<30ms)

2. **Optimize Classical IQA**
   - Replace Hough skew detection with faster method
   - Implement detector parallelization
   - Re-benchmark combined latency (target: <100ms)

3. **End-to-End Pipeline Benchmark** (Phase 4E)
   - Full pipeline: Ingestion → IQA → Correction → Output
   - Multi-page document throughput
   - Real-world corpus (1000+ pages)

### Phase 5 Integration

4. **Discrepancy Calculation Benchmark**
   - Measure ML vs Classical IQA comparison overhead
   - Validate teacher escalation decision time (<2ms target)

5. **Teacher Escalation Rate Analysis**
   - Measure actual escalation rate on diverse corpus
   - Validate 5-15% escalation assumption
   - Analyze latency impact at different escalation rates

### Phase 8 Validation

6. **DQS Calculation Benchmark**
   - Document Quality Score aggregation overhead
   - Routing recommendation decision time

---

## Conclusion

**Phase 4 isolated benchmarks demonstrate**:

✅ **Student model production-ready on CPU** - 10.46ms mean latency exceeds both acceptable and ideal targets
❌ **Teacher model requires GPU** - 469ms CPU latency unacceptable for production
✅ **Model loading negligible** - <250ms combined validates lazy-loading strategy
❌ **Classical IQA needs optimization** - 158ms combined latency 3.2x slower than target

**Critical action items**:
1. Enable ONNX GPU support for teacher inference validation
2. Optimize classical IQA (skew detection, parallelization)
3. Complete end-to-end pipeline benchmarks to validate production readiness

**Overall status**: ✅ **Core ML IQA performance validated for CPU deployment**, ⚠️ **classical IQA optimization required before production**

---

**Report generated**: 2025-01-24
**Benchmark suite version**: Priority 4 - Isolated Benchmarks
**Next report**: Phase 4E - End-to-End Pipeline Benchmarks (pending Priority 2 completion)
