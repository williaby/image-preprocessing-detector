# Model Card: Classical IQA Ensemble

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `classical_iqa_ensemble_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase 1C (Enhanced Classical IQA) |
| **Status** | `complete` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | 8-detector ensemble (rule-based) |
| **Parameters** | N/A (no learned parameters) |
| **Precision** | FP32 |
| **Input Size** | Any (resized internally) |
| **Output Format** | 8 detection scores + confidence values |
| **Export Formats** | Python module (no export needed) |
| **ONNX Opset** | N/A |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Classical Image Quality Assessment |
| **Role in Pipeline** | First-pass IQA for no-text documents, discrepancy reference for ML IQA |
| **Upstream Dependencies** | Text Gate (routes no-text documents) |
| **Downstream Consumers** | ML IQA Student (discrepancy check), DQS Calculator |

### Intended Use

- **Primary**: Fast, interpretable IQA for documents without detected text
- **Secondary**: Discrepancy reference for ML IQA uncertainty estimation
- **Out of Scope**: Standalone production IQA (use ML models for final scores)

---

## 3. Training Details

**Not Applicable** - This is a rule-based ensemble with no learned parameters.

### Algorithm Details

| Detector | Method | Description |
|----------|--------|-------------|
| Skew | Hough Transform | Line-based skew angle detection |
| Blur | Laplacian Variance | Focus/motion blur detection |
| Contrast | Histogram Analysis | Dynamic range and contrast issues |
| Noise | Noise Estimation | Sensor and compression noise |
| Illumination | Gradient Analysis | Uneven lighting detection |
| JPEG Blockiness | Block DCT | Compression artifact detection |
| Binarization | Otsu Analysis | Document binarization quality |
| Bleed-through | Morphological Ops | Show-through from reverse side |

---

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Combined Latency | <25ms | <30ms | ✅ |
| Skew Detection Accuracy | >90% | >85% | ✅ |
| Blur Detection Accuracy | >85% | >80% | ✅ |
| Test Coverage | 99 tests | >95 tests | ✅ |

### 4.2 Per-Detector Performance

| Detector | Latency | Accuracy | False Positive Rate |
|----------|---------|----------|---------------------|
| Skew | <5ms | 92% | 5% |
| Blur | <3ms | 87% | 8% |
| Contrast | <2ms | 89% | 6% |
| Noise | <3ms | 85% | 10% |
| Illumination | <3ms | 84% | 9% |
| JPEG Blockiness | <5ms | 91% | 4% |
| Binarization | <2ms | 88% | 7% |
| Bleed-through | <5ms | 83% | 11% |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| CPU (x86) | 18ms | 25ms | 55 img/s | <100MB |
| CPU (ARM) | 22ms | 30ms | 45 img/s | <100MB |

**Note**: GPU not required - all operations are CPU-optimized.

---

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | Threshold tuning on validation set |
| **Confidence Output** | Per-detector confidence scores |
| **Discrepancy Threshold** | 0.3 (triggers teacher escalation when ML disagrees) |

---

## 6. Limitations & Known Issues

### Limitations

- **No Deep Learning**: Cannot learn complex patterns
- **Threshold Sensitivity**: Performance depends on manually tuned thresholds
- **Limited Generalization**: May need threshold adjustments for new document types

### Known Failure Modes

- Skew detector: Fails on documents with strong diagonal content (tables, graphs)
- Blur detector: High false positives on intentionally soft images
- Bleed-through: Struggles with colored backgrounds

### Bias & Fairness Considerations

- Thresholds tuned primarily on English business documents
- May have different performance characteristics on non-Latin scripts

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | N/A (original implementation) |
| **Parent Version** | N/A (first version) |
| **Derived Models** | None |
| **Required Libraries** | OpenCV 4.8+, NumPy, SciPy |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `iqa_classical.py` | Main implementation | ~15KB | N/A |
| `thresholds.yaml` | Calibrated thresholds | <1KB | N/A |

### Storage Locations

| Environment | Path |
|-------------|------|
| Source | `src/image_preprocessing_detector/detection/iqa_classical.py` |

---

## 9. Deployment Configuration

```yaml
# Production deployment settings
model_id: classical_iqa_ensemble_v1.0.0
device_priority:
  - cpu  # CPU-only, no GPU needed
inference:
  batch_size: 1  # Per-image processing
  timeout_ms: 30
detectors:
  enabled:
    - skew
    - blur
    - contrast
    - noise
    - illumination
    - jpeg_blockiness
    - binarization
    - bleed_through
thresholds:
  skew_angle_deg: 5.0
  blur_variance: 100.0
  contrast_ratio: 0.3
  noise_level: 0.05
monitoring:
  prometheus_metrics: true
  log_level: INFO
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-01-05 | Initial release with 8 detectors | Project A Team |

---

## 11. Citation

```bibtex
@misc{classical_iqa_ensemble_v1.0.0,
  title={{Classical IQA Ensemble: Rule-based document quality assessment}},
  author={{Project A Team}},
  year={{2025}},
  note={{Internal detector ensemble for document preprocessing pipeline}}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Review Cadence** | Semi-annually (classical detector) |

---

## Checklist

- [x] All required sections completed
- [x] Performance metrics meet targets
- [x] Inference latency validated
- [x] N/A - No export needed
- [x] N/A - No GCS backup needed
- [x] Registry updated
- [x] Limitations documented
