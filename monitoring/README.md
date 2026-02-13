<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

# monitoring/

**Purpose**: Monitoring, telemetry, and observability configuration (Phase 4+ production deployment).

## Status

**✅ Phase 5 Implementation Complete** - Annotation pipeline monitoring is now active.

## Current Contents

```text
monitoring/
├── grafana/
│   └── annotation-dashboard.json  # Annotation pipeline dashboard
├── prometheus/
│   └── (alerting rules - planned)
└── README.md
```

### grafana/annotation-dashboard.json

A comprehensive Grafana dashboard for monitoring the annotation pipeline. Includes panels for:

- **Pipeline Overview**: Active pipelines, batches/min, errors/min, throughput
- **Pipeline Stage Performance**: Duration histograms (p50/p95) for cpu_hash, parse, gpu, io stages
- **Batch Processing**: Throughput, duration, success/error rates by dataset
- **Cache Performance**: Hit rates, sizes, eviction rates
- **Parser Operations**: Latency and operation counts by parser
- **Scanner & Checkpointing**: Scan duration, checkpoint operations, resume counts

## What Belongs Here

**✅ Belongs in monitoring/**:

- Prometheus metric configurations
- Grafana dashboard JSON files
- Alert rules (Prometheus Alertmanager)
- Telemetry collection configs
- Health check definitions
- SLO/SLI definitions

**❌ Does NOT belong here**:

- **Application logs** → Gitignored in `logs/` (runtime logs)
- **Training logs** → Google Drive or TensorBoard (training artifacts)
- **CI/CD logs** → `.github/workflows/` (workflow logs)
- **Development tools** → `tools/` (pre-deployment tools)

## Annotation Pipeline Metrics

The annotation pipeline exposes Prometheus metrics under the `imgprep_annotation_` namespace.

### Pipeline Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `imgprep_annotation_active_pipelines` | Gauge | Number of active pipeline instances |
| `imgprep_annotation_pipeline_stage_duration_seconds` | Histogram | Duration by stage (cpu_hash, parse, gpu, io) |
| `imgprep_annotation_pipeline_errors_total` | Counter | Errors by stage and error_type |

### Batch Processing Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `imgprep_annotation_batches_processed_total` | Counter | Batches processed by dataset and status |
| `imgprep_annotation_batch_size` | Histogram | Batch size distribution |
| `imgprep_annotation_batch_duration_seconds` | Histogram | Batch processing duration |
| `imgprep_annotation_batch_throughput_samples_per_second` | Gauge | Current throughput |

### Cache Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `imgprep_annotation_cache_operations_total` | Counter | Operations by cache_name and operation |
| `imgprep_annotation_cache_hit_rate` | Gauge | Hit rate (0-1) |
| `imgprep_annotation_cache_size` | Gauge | Current entries |
| `imgprep_annotation_cache_evictions_total` | Counter | Evictions |

### Parser Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `imgprep_annotation_parse_operations_total` | Counter | Operations by parser and status |
| `imgprep_annotation_parse_duration_seconds` | Histogram | Parse latency |
| `imgprep_annotation_parse_errors_total` | Counter | Errors by parser and error_type |
| `imgprep_annotation_samples_parsed_total` | Counter | Samples parsed |

### Scanner Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `imgprep_annotation_scan_operations_total` | Counter | Scans by dataset and status |
| `imgprep_annotation_scan_duration_seconds` | Histogram | Scan duration |
| `imgprep_annotation_files_discovered_total` | Counter | Files found |
| `imgprep_annotation_checkpoint_operations_total` | Counter | Checkpoint operations |
| `imgprep_annotation_scan_resume_total` | Counter | Resumed scans |

## Integration

### Prometheus Scrape Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'annotation-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Importing the Grafana Dashboard

1. Open Grafana and navigate to **Dashboards > Import**
2. Upload `grafana/annotation-dashboard.json` or paste its contents
3. Select your Prometheus data source when prompted
4. Click **Import**

### Example Alerting Rules

```yaml
# prometheus/rules/annotation_alerts.yml
groups:
  - name: annotation-alerts
    rules:
      - alert: AnnotationPipelineErrors
        expr: rate(imgprep_annotation_pipeline_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: Annotation pipeline errors detected
          description: "Pipeline stage {{ $labels.stage }} has error rate > 0.1/s"

      - alert: AnnotationLowCacheHitRate
        expr: imgprep_annotation_cache_hit_rate < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: Low cache hit rate
          description: "Cache {{ $labels.cache_name }} hit rate is {{ $value }}"

      - alert: AnnotationSlowBatchProcessing
        expr: histogram_quantile(0.95, rate(imgprep_annotation_batch_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: Slow batch processing
          description: "Batch p95 latency is {{ $value }}s"
```

## Distinction from Other Folders

### vs. logs/

- **monitoring/**: Metric collection and visualization configs
- **logs/**: Actual runtime log files (gitignored)

### vs. tools/

- **monitoring/**: Production observability (post-deployment)
- **tools/**: Development tooling (pre-deployment)

## Dependencies

The annotation monitoring module uses `prometheus_client` for metrics:

```toml
# pyproject.toml
[tool.poetry.dependencies]
prometheus-client = "^0.20.0"
```

The module gracefully degrades if prometheus_client is not installed, using stub implementations that do nothing.
