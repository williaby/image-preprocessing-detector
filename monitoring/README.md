<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

# monitoring/

**Purpose**: Monitoring, telemetry, and observability configuration (Phase 4+ production deployment).

## Status

**⏳ Placeholder for Phase 4** - This folder is currently empty and will be populated during Phase 4: Production Hardening.

## What Will Go Here (Phase 4+)

**✅ Will belong in monitoring/**:
- Prometheus metric configurations
- Grafana dashboard JSON files
- Alert rules (Prometheus Alertmanager)
- Telemetry collection configs
- Health check definitions
- SLO/SLI definitions

**❌ Will NOT belong here**:
- **Application logs** → Gitignored in `logs/` (runtime logs)
- **Training logs** → Google Drive or TensorBoard (training artifacts)
- **CI/CD logs** → `.github/workflows/` (workflow logs)
- **Development tools** → `tools/` (pre-deployment tools)

## Planned Structure (Phase 4)

```
monitoring/
├── prometheus/
│   ├── rules/
│   │   ├── latency_alerts.yml
│   │   ├── error_rate_alerts.yml
│   │   └── throughput_alerts.yml
│   └── prometheus.yml
├── grafana/
│   ├── dashboards/
│   │   ├── iqa_performance.json
│   │   ├── layout_detection.json
│   │   └── system_health.json
│   └── datasources.yml
├── opentelemetry/
│   └── otel-collector-config.yaml
└── README.md
```

## Planned Metrics (Phase 4)

### Performance Metrics
- **Latency**: p50, p95, p99 per page
- **Throughput**: pages/second per worker
- **Queue Depth**: pending documents in queue

### Quality Metrics
- **IQA Accuracy**: mAP, F1 scores over time
- **Layout Detection**: mAP@.50 over time
- **Confidence Distribution**: confidence score histograms

### System Health
- **CPU/Memory**: Resource utilization
- **GPU Utilization**: GPU memory, compute usage
- **Disk I/O**: Read/write throughput
- **Network**: Request/response times

### Business Metrics
- **Documents Processed**: Total count, rate
- **Error Rate**: Failed document processing
- **Model Version**: Active model versions in production

## Integration (Phase 4)

### Prometheus
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'image-preprocessing'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboards
- IQA Performance: Visualize detection accuracy over time
- System Health: CPU, memory, GPU utilization
- Document Processing: Throughput, latency, error rates

### Alerting Rules
```yaml
# prometheus/rules/latency_alerts.yml
groups:
  - name: latency
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(processing_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High p95 latency detected"
```

## Distinction from Other Folders

### vs. logs/
- **monitoring/**: Metric collection and visualization configs
- **logs/**: Actual runtime log files (gitignored)

### vs. tools/
- **monitoring/**: Production observability (post-deployment)
- **tools/**: Development tooling (pre-deployment)

## Current State

- **`.gitkeep`**: Preserves empty folder structure for future use
- **No active monitoring**: Will be implemented in Phase 4

## Phase 4 Implementation Plan

1. **Week 21-22**: Prometheus setup, basic metrics
2. **Week 22-23**: Grafana dashboards for visualization
3. **Week 23-24**: Alerting rules and incident response
4. **Week 24**: OpenTelemetry integration for distributed tracing

## Dependencies (Phase 4)

```toml
# pyproject.toml - Will add in Phase 4
[tool.poetry.dependencies]
prometheus-client = "^0.20.0"
opentelemetry-api = "^1.23.0"
opentelemetry-sdk = "^1.23.0"
opentelemetry-instrumentation-fastapi = "^0.44b0"
```
