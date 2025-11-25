# Alert Threshold Reference

This document provides the definitive reference for all alert thresholds, their justifications, and tuning guidance.

## Overview

Alert thresholds are carefully tuned to balance sensitivity (catching real issues) against noise (false positives). This document captures the final values after load testing and validation.

## Threshold Philosophy

1. **Start Conservative**: Initial thresholds are set conservatively to catch issues
2. **Tune Based on Data**: Adjust after observing real-world behavior
3. **Document Changes**: Every threshold change requires justification
4. **Review Quarterly**: Revisit thresholds as system evolves

---

## Latency Thresholds

### Processing Latency

| Percentile | Warning | Critical | Justification |
|------------|---------|----------|---------------|
| p50 | 200ms | - | Median should stay fast; indicates general slowdown |
| p95 | 500ms | - | Tail latency; catches degraded performance |
| p99 | - | 2000ms | Extreme tail; indicates serious issues |

**Baseline Values** (from load testing):
- p50: ~80ms (CPU), ~25ms (GPU)
- p95: ~200ms (CPU), ~60ms (GPU)
- p99: ~400ms (CPU), ~120ms (GPU)

**Tuning Notes**:
- Thresholds set at ~2.5x baseline to allow for load spikes
- CPU-only deployments may need higher thresholds
- Consider adjusting if document complexity changes significantly

### Student Model Latency

| Metric | Threshold | Justification |
|--------|-----------|---------------|
| p95 | 100ms | Student must be fast for production; target <100ms |

**Baseline**: ~40ms (CPU), ~10ms (GPU)

---

## Error Rate Thresholds

### Overall Error Rate

| Severity | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Warning | >5% | 5min | Elevated but manageable |
| Critical | >20% | 2min | Severe impact; requires immediate action |

**Baseline**: <0.5% under normal operation

**Tuning Notes**:
- 5% catches gradual degradation before customer impact
- 20% indicates system failure; shorter duration for faster response
- Adjust warning threshold if certain error types are expected (e.g., malformed input)

### Error Spikes

| Category | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Processing | >50 errors/5min | 2min | Sudden spike indicates new issue |
| Infrastructure | >10 errors/5min | 2min | Infra errors are more severe |

---

## Infrastructure Thresholds

### GPU Memory

| Severity | Threshold | Justification |
|----------|-----------|---------------|
| Warning | >90% | Approaching OOM; need to investigate |

**Baseline**: ~60% with student model loaded, ~75% with both models

**Tuning Notes**:
- T4 (16GB): More headroom
- Smaller GPUs may need lower threshold

### Worker Health

| Alert | Threshold | Duration | Justification |
|-------|-----------|----------|---------------|
| Degraded | <2 workers | 5min | Reduced capacity |
| Critical | 0 workers | 1min | Complete outage |

### Queue Backlog

| Severity | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Warning | >500 items | 10min | Building backlog |
| Critical | >2000 items | 5min | Severe backlog; scale immediately |

**Baseline**: <100 items under normal load

**Tuning Notes**:
- Adjust based on expected traffic patterns
- Batch processing may have temporary spikes (consider excluding)

---

## Model & Escalation Thresholds

### Teacher Escalation Rate

| Severity | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Warning | >25% | 10min | Higher than expected; cost impact |

**Baseline**: ~10-15% for typical documents

**Tuning Notes**:
- Escalation rate depends on document complexity
- Complex/degraded documents may escalate more frequently
- Consider per-document-type alerting if available

### Model Drift

| Metric | Threshold | Duration | Justification |
|--------|-----------|----------|---------------|
| Quality Score Shift | >0.1 | 30min | Significant distribution change |

**Baseline**: Quality scores should be stable (stddev ~0.05)

---

## Cost Thresholds

### Daily Cost

| Severity | Threshold | Justification |
|----------|-----------|---------------|
| Warning | >$5/day | Above typical daily spend |

**Baseline**: ~$1-3/day for typical workload

### Monthly Budget

| Severity | Threshold | Justification |
|----------|-----------|---------------|
| Warning | >$20 (30-day) | 67% of $30 free tier |
| Critical | >$28 (30-day) | 93% of budget; will exceed |

### Cost Rate Spike

| Severity | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Warning | >$1/hour | 30min | Sustained high rate |

### GPU Usage Rate

| Severity | Threshold | Duration | Justification |
|----------|-----------|----------|---------------|
| Warning | >100 sec/hour | 30min | Higher than optimal |

**Baseline**: ~30-50 GPU seconds/hour

---

## Availability Thresholds

### Throughput

| Alert | Condition | Duration | Justification |
|-------|-----------|----------|---------------|
| Low | <0.1 pages/sec AND queue >10 | 5min | Processing slowed with work pending |
| Stalled | 0 pages/10min AND queue >0 | 5min | Complete stop |

### Service Health

| Alert | Condition | Duration | Justification |
|-------|-----------|----------|---------------|
| Down | up == 0 | 1min | Instance not responding |

---

## Threshold Tuning Process

### When to Tune

1. **False Positive Rate >10%**: Alert fires but no real issue
2. **Missed Incidents**: Real issues not caught by alerts
3. **System Changes**: New models, hardware, or traffic patterns
4. **Quarterly Review**: Regular health check

### Tuning Procedure

1. **Gather Data**:
   ```bash
   # Export last 30 days of metrics
   curl -s "http://prometheus:9090/api/v1/query_range?query=imgprep_processing_duration_seconds&start=$(date -d '30 days ago' +%s)&end=$(date +%s)&step=1h" > metrics.json
   ```

2. **Calculate Percentiles**:
   ```python
   import numpy as np
   # Calculate p50, p95, p99 from exported data
   p50 = np.percentile(data, 50)
   p95 = np.percentile(data, 95)
   p99 = np.percentile(data, 99)
   ```

3. **Set Threshold**:
   - Warning: ~2x baseline (catches degradation)
   - Critical: ~5x baseline (catches severe issues)

4. **Validate**:
   - Run load test with new thresholds
   - Monitor for 7 days before finalizing
   - Document changes in this file

### Load Test Validation

Run these scenarios to validate thresholds:

```bash
# Normal load (should NOT alert)
poetry run imgprep benchmark --pages 1000 --workers 4 --rate 10/s

# High load (should trigger warning)
poetry run imgprep benchmark --pages 5000 --workers 4 --rate 50/s

# Failure injection (should trigger critical)
poetry run imgprep benchmark --pages 1000 --workers 1 --inject-errors 0.3
```

---

## Change Log

| Date | Alert | Old Value | New Value | Reason |
|------|-------|-----------|-----------|--------|
| 2025-01-15 | Initial | - | - | Initial threshold values established |

---

## Quick Reference Card

```
LATENCY
  p50 > 200ms (5min)     → Warning: check load
  p95 > 500ms (5min)     → Warning: investigate tail
  p99 > 2s (5min)        → Critical: serious issue

ERRORS
  Rate > 5% (5min)       → Warning: elevated errors
  Rate > 20% (2min)      → Critical: system failure
  Processing > 50/5min   → Warning: spike detected
  Infra > 10/5min        → Critical: infra issue

INFRASTRUCTURE
  GPU Memory > 90%       → Warning: approaching OOM
  Workers < 2 (5min)     → Warning: degraded capacity
  Workers == 0 (1min)    → Critical: outage
  Queue > 500 (10min)    → Warning: backlog building
  Queue > 2000 (5min)    → Critical: severe backlog

MODEL
  Escalation > 25%       → Warning: high teacher usage
  Teacher blocked        → Warning: escalations failing
  Drift > 0.1            → Warning: distribution shift

COST
  Daily > $5             → Warning: high spend
  Monthly > $20          → Warning: approaching budget
  Monthly > $28          → Critical: budget exhausted
  Rate > $1/hr (30min)   → Warning: cost spike
  GPU > 100s/hr          → Warning: high GPU usage

AVAILABILITY
  Throughput < 0.1/s     → Warning: slow processing
  Stalled (10min)        → Critical: processing stopped
  Service down           → Critical: instance down
```
