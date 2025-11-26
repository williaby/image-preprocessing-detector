---
schema_type: common
title: "Drift Detection Guide"
description: "Comprehensive guide for model drift detection and monitoring"
tags:
  - guide
  - monitoring
  - machine_learning
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document drift detection architecture, configuration, and response procedures."
---

This document provides comprehensive guidance on model drift detection, monitoring, and response procedures.

## Overview

Drift detection monitors for:

1. **Feature Distribution Drift** - Changes in input data distributions
2. **Model Performance Drift** - Degradation in model accuracy over time
3. **Concept Drift** - Changes in the relationship between inputs and outputs

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Production Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│  Input → Text Gate → IQA (Student) → Corrections → Output      │
│            ↓            ↓                                       │
│     Distribution    Predictions                                 │
│       Tracker         & Entropy                                 │
└───────────┬─────────────┬───────────────────────────────────────┘
            │             │
            ▼             ▼
┌─────────────────┐  ┌─────────────────┐
│  Reference      │  │  Performance    │
│  Distributions  │  │  Metrics Store  │
│  (Monthly)      │  │  (Daily)        │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Drift Detector                                │
├─────────────────────────────────────────────────────────────────┤
│  • KL Divergence: Compare current vs reference distributions    │
│  • PSI: Population Stability Index for shift detection          │
│  • mAP/F1 Tracking: Monitor model accuracy trends               │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Alert Manager                                 │
├─────────────────────────────────────────────────────────────────┤
│  • Threshold evaluation (KL >0.3, mAP drop >5%)                 │
│  • Cooldown management (prevent alert fatigue)                  │
│  • Multi-channel dispatch (log, Slack, PagerDuty)               │
│  • Dry-run mode for validation                                  │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Active Learning                               │
├─────────────────────────────────────────────────────────────────┤
│  • Harvest high-entropy samples                                  │
│  • Store low-agreement cases                                     │
│  • Generate re-training manifests                                │
│  • Privacy review workflow                                       │
└─────────────────────────────────────────────────────────────────┘
```text

---

## Key Metrics & Thresholds

### Distribution Drift (KL Divergence)

| Threshold | Value | Interpretation |
|-----------|-------|----------------|
| Warning | 0.15 | Noticeable distribution shift |
| Critical | 0.30 | Significant drift requiring action |

**Features Monitored:**

- Quality scores (0-1)
- Blur scores
- Skew angles
- Contrast scores
- Noise levels
- Processing times
- Gate confidence

### Population Stability Index (PSI)

| Threshold | Value | Interpretation |
|-----------|-------|----------------|
| Warning | 0.10 | Moderate population shift |
| Critical | 0.25 | Significant shift |

### Model Performance

| Metric | Warning | Critical |
|--------|---------|----------|
| mAP drop | 3% | 5% |
| F1 drop | 3% | 5% |
| Precision drop | 5% | 10% |
| Recall drop | 5% | 10% |

---

## Monitoring Locations

### Prometheus Metrics

```promql
# Distribution drift
imgprep_drift_kl_divergence{feature="quality_score"}
imgprep_drift_psi{feature="quality_score"}

# Model performance
imgprep_model_map
imgprep_model_f1
imgprep_model_precision
imgprep_model_recall

# Active learning
imgprep_harvested_samples_total{reason="high_entropy"}
imgprep_harvested_samples_total{reason="low_agreement"}
```

### Grafana Dashboards

1. **Model Performance** (`model-performance.json`)
   - mAP/F1 trends over time
   - Escalation rates
   - Quality score distributions

2. **Drift Detection** (to be added)
   - KL divergence by feature
   - PSI trends
   - Reference distribution comparisons

### Log Locations

```bash
# Alert logs
/var/log/imgprep/drift_alerts.log

# Evaluation job logs
/var/log/imgprep/performance_evaluation.log

# Harvested samples manifest
/data/drift_samples/manifests/latest_manifest.json
```

---

## Alert Response Flow

```text
┌──────────────────────────────────────────────────────────────┐
│                     Alert Received                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. Acknowledge Alert                                          │
│    • Respond within SLA (15min critical, 1hr warning)         │
│    • Update alert status in dashboard                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Initial Triage                                             │
│    • Review alert samples                                     │
│    • Check recent deployments                                 │
│    • Verify data source changes                               │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Investigation                                              │
│    • Compare current vs reference distributions               │
│    • Run evaluation on test set                               │
│    • Check for correlated alerts                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Remediation                                                │
│    • Update reference distributions (if data change)          │
│    • Trigger re-training (if model degradation)               │
│    • Roll back deployment (if recent change)                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Resolution                                                 │
│    • Verify metrics normalized                                │
│    • Document root cause                                      │
│    • Update runbook if needed                                 │
└──────────────────────────────────────────────────────────────┘
```text

---

## Runbook Quick Reference

### KL Divergence Alert

```bash
# 1. View current drift metrics
curl -s "http://prometheus:9090/api/v1/query?query=imgprep_drift_kl_divergence" | jq

# 2. Compare distributions
poetry run python -c "
from image_preprocessing_detector.drift import ReferenceStore, create_tracker
store = ReferenceStore('data/drift_references')
ref = store.get_reference('quality_score')
print(f'Reference mean: {ref.stats.mean:.4f}')
print(f'Reference std: {ref.stats.std:.4f}')
"

# 3. Check recent samples
ls -la data/drift_samples/$(date +%Y%m%d)/

# 4. If data change is legitimate, update reference
poetry run python -c "
from image_preprocessing_detector.drift import DriftDetector, create_tracker, ReferenceStore
tracker = create_tracker()
# ... load recent samples into tracker
store = ReferenceStore('data/drift_references')
detector = DriftDetector(store)
detector.create_reference_from_tracker(tracker, 'quality_score', min_samples=1000)
"
```

### mAP Drop Alert

```bash
# 1. Check recent evaluation results
cat data/performance_monitoring/reports/latest.json | jq '.current_evaluation.metrics'

# 2. Compare with baseline
cat data/performance_monitoring/reports/latest.json | jq '.baseline_evaluation.metrics'

# 3. Run manual evaluation
poetry run python -m image_preprocessing_detector.drift.performance evaluate \
    --model /models/iqa_student.onnx \
    --dataset /data/change_detection_set

# 4. If significant degradation, trigger re-training queue
# (manual step - see re-training pipeline documentation)
```

---

## Related Documentation

- [Threshold Reference](thresholds.md)
- [Baseline Metrics Guide](baseline-metrics.md)
- [Runbooks](runbooks/)
- [Active Learning Privacy Checklist](../drift/privacy_checklist.md)
