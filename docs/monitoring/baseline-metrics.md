# Baseline Metrics Guide

This document describes how to capture, analyze, and maintain baseline metrics for alert threshold tuning.

## Purpose

Baseline metrics provide the foundation for:
- Setting appropriate alert thresholds
- Detecting anomalies and drift
- Capacity planning
- Performance regression detection

## Capture Schedule

| Baseline Type | Frequency | Retention |
|---------------|-----------|-----------|
| Daily snapshot | Daily at 00:00 UTC | 90 days |
| Weekly summary | Sunday 00:00 UTC | 1 year |
| Monthly report | 1st of month | 3 years |
| Release baseline | Each deploy | Indefinite |

---

## Metrics to Capture

### Latency Metrics

```promql
# Processing latency percentiles
histogram_quantile(0.50, sum(rate(imgprep_processing_duration_seconds_bucket[24h])) by (le))
histogram_quantile(0.95, sum(rate(imgprep_processing_duration_seconds_bucket[24h])) by (le))
histogram_quantile(0.99, sum(rate(imgprep_processing_duration_seconds_bucket[24h])) by (le))

# IQA latency by model
histogram_quantile(0.95, sum(rate(imgprep_iqa_duration_seconds_bucket[24h])) by (le, model))

# Gate latency
histogram_quantile(0.95, sum(rate(imgprep_gate_duration_seconds_bucket[24h])) by (le))
```

### Throughput Metrics

```promql
# Pages processed per day
sum(increase(imgprep_pages_processed_total[24h]))

# Pages by status
sum(increase(imgprep_pages_processed_total[24h])) by (status)

# Pages by gate result
sum(increase(imgprep_pages_processed_total[24h])) by (gate_result)
```

### Error Metrics

```promql
# Error rate
sum(rate(imgprep_pages_processed_total{status="error"}[24h]))
  / sum(rate(imgprep_pages_processed_total[24h]))

# Errors by category
sum(increase(imgprep_errors_total[24h])) by (category)

# Errors by code (top 10)
topk(10, sum(increase(imgprep_errors_total[24h])) by (error_code))
```

### Model Metrics

```promql
# Teacher escalation rate
sum(rate(imgprep_teacher_invocations_total[24h]))
  / sum(rate(imgprep_pages_processed_total[24h]))

# Escalation by reason
sum(increase(imgprep_teacher_invocations_total[24h])) by (reason)

# Quality score distribution
histogram_quantile(0.50, sum(rate(imgprep_quality_score_bucket[24h])) by (le))
avg(rate(imgprep_quality_score_sum[24h]) / rate(imgprep_quality_score_count[24h]))
```

### Cost Metrics

```promql
# Daily cost
sum(increase(imgprep_estimated_cost_dollars_total[24h]))

# Cost by type
sum(increase(imgprep_estimated_cost_dollars_total[24h])) by (cost_type)

# GPU seconds used
sum(increase(imgprep_modal_gpu_seconds_total[24h]))
```

### Infrastructure Metrics

```promql
# Average queue depth
avg_over_time(imgprep_queue_depth[24h])

# Max queue depth
max_over_time(imgprep_queue_depth[24h])

# Average active workers
avg_over_time(imgprep_active_workers[24h])

# GPU memory (if applicable)
avg_over_time(imgprep_gpu_memory_bytes[24h])
```

---

## Capture Scripts

### Daily Baseline Capture

```bash
#!/bin/bash
# capture-baseline.sh - Run daily via cron

PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus:9090}"
OUTPUT_DIR="${OUTPUT_DIR:-/data/baselines}"
DATE=$(date +%Y-%m-%d)

mkdir -p "$OUTPUT_DIR"

# Latency baselines
curl -s "$PROMETHEUS_URL/api/v1/query?query=histogram_quantile(0.50,sum(rate(imgprep_processing_duration_seconds_bucket[24h]))by(le))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-latency-p50.txt"

curl -s "$PROMETHEUS_URL/api/v1/query?query=histogram_quantile(0.95,sum(rate(imgprep_processing_duration_seconds_bucket[24h]))by(le))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-latency-p95.txt"

curl -s "$PROMETHEUS_URL/api/v1/query?query=histogram_quantile(0.99,sum(rate(imgprep_processing_duration_seconds_bucket[24h]))by(le))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-latency-p99.txt"

# Throughput baseline
curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(increase(imgprep_pages_processed_total[24h]))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-throughput.txt"

# Error rate baseline
curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(rate(imgprep_pages_processed_total{status=\"error\"}[24h]))/sum(rate(imgprep_pages_processed_total[24h]))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-error-rate.txt"

# Escalation rate baseline
curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(rate(imgprep_teacher_invocations_total[24h]))/sum(rate(imgprep_pages_processed_total[24h]))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-escalation-rate.txt"

# Cost baseline
curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(increase(imgprep_estimated_cost_dollars_total[24h]))" \
  | jq '.data.result[0].value[1]' > "$OUTPUT_DIR/$DATE-daily-cost.txt"

echo "Baseline captured for $DATE"
```

### Weekly Summary Generation

```bash
#!/bin/bash
# generate-weekly-summary.sh

OUTPUT_DIR="${OUTPUT_DIR:-/data/baselines}"
WEEK=$(date +%Y-W%V)

# Aggregate daily baselines into weekly summary
python3 << EOF
import os
import json
from datetime import datetime, timedelta
import statistics

output_dir = "$OUTPUT_DIR"
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

metrics = ['latency-p50', 'latency-p95', 'latency-p99', 'throughput',
           'error-rate', 'escalation-rate', 'daily-cost']

summary = {'week': '$WEEK', 'metrics': {}}

for metric in metrics:
    values = []
    for i in range(7):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        filepath = f"{output_dir}/{date}-{metric}.txt"
        if os.path.exists(filepath):
            with open(filepath) as f:
                try:
                    values.append(float(f.read().strip().strip('"')))
                except:
                    pass

    if values:
        summary['metrics'][metric] = {
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'stddev': statistics.stdev(values) if len(values) > 1 else 0
        }

with open(f"{output_dir}/weekly-{summary['week']}.json", 'w') as f:
    json.dump(summary, f, indent=2)

print(f"Weekly summary generated: weekly-{summary['week']}.json")
EOF
```

---

## Baseline Analysis

### Detecting Drift

Compare current metrics against baselines:

```python
#!/usr/bin/env python3
"""Detect metric drift from baseline."""

import json
import sys
from pathlib import Path

def load_baseline(baseline_file: str) -> dict:
    """Load baseline metrics."""
    with open(baseline_file) as f:
        return json.load(f)

def check_drift(current: float, baseline: dict, threshold: float = 2.0) -> bool:
    """Check if current value has drifted from baseline.

    Returns True if drift detected (outside threshold * stddev).
    """
    avg = baseline['avg']
    stddev = baseline['stddev']

    if stddev == 0:
        # No variance in baseline, use percentage threshold
        return abs(current - avg) / avg > 0.2 if avg > 0 else False

    # Check if outside threshold * standard deviations
    return abs(current - avg) > threshold * stddev

def main():
    baseline_file = sys.argv[1] if len(sys.argv) > 1 else 'baseline.json'
    baseline = load_baseline(baseline_file)

    # Example current values (would come from Prometheus in practice)
    current = {
        'latency-p50': 0.085,
        'latency-p95': 0.210,
        'error-rate': 0.008,
        'escalation-rate': 0.12,
    }

    drifted = []
    for metric, value in current.items():
        if metric in baseline['metrics']:
            if check_drift(value, baseline['metrics'][metric]):
                drifted.append(metric)
                print(f"DRIFT: {metric} = {value} (baseline avg: {baseline['metrics'][metric]['avg']:.3f})")

    if not drifted:
        print("No drift detected")

    return 1 if drifted else 0

if __name__ == '__main__':
    sys.exit(main())
```

### Baseline Report Template

```markdown
# Baseline Report: YYYY-MM-DD

## Summary

| Metric | Current | Baseline | Change |
|--------|---------|----------|--------|
| Latency p50 | X ms | Y ms | +Z% |
| Latency p95 | X ms | Y ms | +Z% |
| Error Rate | X% | Y% | +Z% |
| Escalation Rate | X% | Y% | +Z% |
| Daily Cost | $X | $Y | +Z% |

## Analysis

### Latency
- [Commentary on latency trends]

### Errors
- [Commentary on error patterns]

### Model Performance
- [Commentary on escalation rates]

### Cost
- [Commentary on cost trends]

## Recommendations

1. [Action items if thresholds need adjustment]
2. [Capacity planning notes]
3. [Investigation items]
```

---

## Initial Baseline Values

These values were established during load testing (2025-01-15):

### CPU-Only Deployment

| Metric | p50 | p95 | p99 |
|--------|-----|-----|-----|
| Processing Latency | 80ms | 200ms | 400ms |
| IQA (Student) | 40ms | 80ms | 150ms |
| Gate Latency | 5ms | 10ms | 20ms |

| Metric | Typical | Peak |
|--------|---------|------|
| Throughput | 2 pages/sec | 5 pages/sec |
| Error Rate | 0.5% | 2% |
| Escalation Rate | 12% | 20% |
| Queue Depth | 50 | 200 |

### GPU Deployment

| Metric | p50 | p95 | p99 |
|--------|-----|-----|-----|
| Processing Latency | 25ms | 60ms | 120ms |
| IQA (Student) | 10ms | 20ms | 40ms |
| IQA (Teacher) | 25ms | 50ms | 100ms |
| Gate Latency | 3ms | 8ms | 15ms |

| Metric | Typical | Peak |
|--------|---------|------|
| Throughput | 8 pages/sec | 15 pages/sec |
| Error Rate | 0.3% | 1% |
| Escalation Rate | 10% | 18% |
| Queue Depth | 30 | 150 |

### Cost Baseline

| Metric | Daily | Weekly | Monthly |
|--------|-------|--------|---------|
| Estimated Cost | $1-3 | $7-20 | $30-80 |
| Modal GPU Seconds | 3000-6000 | 20k-40k | 80k-160k |

---

## Cron Setup

Add to crontab for automated baseline capture:

```cron
# Daily baseline at midnight UTC
0 0 * * * /opt/imgprep/scripts/capture-baseline.sh >> /var/log/imgprep/baseline.log 2>&1

# Weekly summary on Sunday at 1am UTC
0 1 * * 0 /opt/imgprep/scripts/generate-weekly-summary.sh >> /var/log/imgprep/baseline.log 2>&1

# Monthly report on 1st at 2am UTC
0 2 1 * * /opt/imgprep/scripts/generate-monthly-report.sh >> /var/log/imgprep/baseline.log 2>&1
```

---

## Prometheus Recording Rules

For efficient baseline queries, add these recording rules:

```yaml
groups:
  - name: imgprep_baseline_recordings
    interval: 5m
    rules:
      # Processing latency percentiles
      - record: imgprep:processing_latency_p50:5m
        expr: histogram_quantile(0.50, sum(rate(imgprep_processing_duration_seconds_bucket[5m])) by (le))

      - record: imgprep:processing_latency_p95:5m
        expr: histogram_quantile(0.95, sum(rate(imgprep_processing_duration_seconds_bucket[5m])) by (le))

      - record: imgprep:processing_latency_p99:5m
        expr: histogram_quantile(0.99, sum(rate(imgprep_processing_duration_seconds_bucket[5m])) by (le))

      # Error rate
      - record: imgprep:error_rate:5m
        expr: >
          sum(rate(imgprep_pages_processed_total{status="error"}[5m]))
          / sum(rate(imgprep_pages_processed_total[5m]))

      # Escalation rate
      - record: imgprep:escalation_rate:5m
        expr: >
          sum(rate(imgprep_teacher_invocations_total[5m]))
          / sum(rate(imgprep_pages_processed_total[5m]))

      # Cost rate ($/hour)
      - record: imgprep:cost_rate_hourly:5m
        expr: sum(rate(imgprep_estimated_cost_dollars_total[5m])) * 3600

      # Throughput
      - record: imgprep:throughput_pages_per_second:5m
        expr: sum(rate(imgprep_pages_processed_total[5m]))
```
