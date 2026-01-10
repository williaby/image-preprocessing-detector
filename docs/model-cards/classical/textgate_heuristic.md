# Model Card: Text Gate Heuristic

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `textgate_heuristic_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | Phase 1 (MVP) |
| **Status** | `complete` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 2.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | 3-method ensemble heuristic |
| **Parameters** | N/A (no learned parameters) |
| **Precision** | FP32 |
| **Input Size** | Any (processed at original resolution) |
| **Output Format** | Boolean (text_detected) + confidence score |
| **Export Formats** | Python module (no export needed) |
| **ONNX Opset** | N/A |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Fast text presence detection |
| **Role in Pipeline** | Critical routing gate - determines processing path |
| **Upstream Dependencies** | PDF ingestion, DPI upscaling |
| **Downstream Consumers** | Classical IQA (no-text), Layout-Lite (text detected) |

### Intended Use

- **Primary**: Fast (<10ms) routing decision for document processing paths
- **Secondary**: Early filter for pure image documents
- **Out of Scope**: OCR, text extraction, text quality assessment

---

## 3. Training Details

**Not Applicable** - This is a rule-based ensemble with no learned parameters.

### Algorithm Details

| Method | Technique | Weight |
|--------|-----------|--------|
| Stroke Density | Connected component analysis | 0.4 |
| Edge Density | Canny edge detection + density calculation | 0.3 |
| Texture Analysis | Local binary patterns | 0.3 |

**Ensemble Strategy**: Weighted voting with confidence aggregation

---

## 4. Performance Metrics

### 4.1 Primary Benchmark

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Latency (p50) | 6ms | <10ms | ✅ |
| Latency (p95) | 9ms | <15ms | ✅ |
| Accuracy | 94% | >90% | ✅ |
| Recall (text present) | 97% | >95% | ✅ |
| Precision (text present) | 92% | >90% | ✅ |

### 4.2 Per-Method Performance

| Method | Latency | Individual Accuracy |
|--------|---------|---------------------|
| Stroke Density | <3ms | 89% |
| Edge Density | <2ms | 85% |
| Texture Analysis | <4ms | 82% |
| **Ensemble** | <8ms | **94%** |

### 4.3 Inference Performance

| Device | Latency (p50) | Latency (p95) | Throughput | Memory |
|--------|---------------|---------------|------------|--------|
| CPU (x86) | 6ms | 9ms | 165 img/s | <50MB |
| CPU (ARM) | 8ms | 12ms | 125 img/s | <50MB |

**Note**: GPU not required - all operations are CPU-optimized.

---

## 5. Uncertainty & Calibration

| Field | Value |
|-------|-------|
| **Calibration Method** | Threshold calibration on mixed document set |
| **Confidence Output** | Weighted ensemble score [0, 1] |
| **Decision Threshold** | 0.5 (text_detected if confidence > 0.5) |
| **Ambiguity Range** | 0.4 - 0.6 (logged for review) |

---

## 6. Limitations & Known Issues

### Limitations

- **Binary Decision**: Only detects presence/absence, not text quality or quantity
- **No OCR**: Does not extract or recognize text content
- **Resolution Dependent**: Performance varies with image resolution

### Known Failure Modes

- False positives on highly textured images (fabric, foliage)
- False negatives on very small or stylized fonts
- Struggles with low-contrast text on colored backgrounds

### Bias & Fairness Considerations

- Tuned primarily on Latin script documents
- Non-Latin scripts (CJK, Arabic, etc.) may have different detection characteristics
- Handwritten text detection less reliable than printed

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | N/A (original implementation) |
| **Parent Version** | N/A (first version) |
| **Derived Models** | None |
| **Required Libraries** | OpenCV 4.8+, NumPy, scikit-image |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `text_gate.py` | Main implementation | ~8KB | N/A |
| `thresholds.yaml` | Calibrated thresholds | <1KB | N/A |

### Storage Locations

| Environment | Path |
|-------------|------|
| Source | `src/image_preprocessing_detector/detection/text_gate.py` |

---

## 9. Deployment Configuration

```yaml
# Production deployment settings
model_id: textgate_heuristic_v1.0.0
device_priority:
  - cpu  # CPU-only, no GPU needed
inference:
  timeout_ms: 15
ensemble:
  methods:
    - stroke_density
    - edge_density
    - texture_analysis
  weights:
    stroke_density: 0.4
    edge_density: 0.3
    texture_analysis: 0.3
  decision_threshold: 0.5
monitoring:
  prometheus_metrics: true
  log_level: INFO
  log_ambiguous: true  # Log cases in 0.4-0.6 range
```

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-01-03 | Initial release with 3-method ensemble | Project A Team |

---

## 11. Citation

```bibtex
@misc{textgate_heuristic_v1.0.0,
  title={{Text Gate Heuristic: Fast text detection for document routing}},
  author={{Project A Team}},
  year={{2025}},
  note={{Internal routing gate for document preprocessing pipeline}}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Project A Core Team |
| **Technical Contact** | See project repository |
| **Review Cadence** | Semi-annually (critical gate) |

---

## Checklist

- [x] All required sections completed
- [x] Performance metrics meet targets
- [x] Inference latency validated
- [x] N/A - No export needed
- [x] N/A - No GCS backup needed
- [x] Registry updated
- [x] Limitations documented
