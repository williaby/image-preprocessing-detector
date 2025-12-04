# Load Testing Guide

Comprehensive load testing framework for the Image Preprocessing Detector API using Locust.

## Prerequisites

```bash
# Install Locust
pip install locust

# Or with uv
uv pip install locust
```

## Setup Test Fixtures

Place test documents in `tests/load/fixtures/`:

```bash
# Copy sample documents
cp data/test_fixtures/*.pdf tests/load/fixtures/
cp data/test_fixtures/*.png tests/load/fixtures/

# Or create symbolic links
ln -s $(pwd)/data/test_fixtures/*.pdf tests/load/fixtures/
```

**Recommended Fixtures**:

- 3-5 PDF files of varying sizes (1-10 pages)
- 3-5 image files (PNG, JPG) at different resolutions
- Mix of high-quality and degraded samples

## Load Test Scenarios

### 1. Baseline Load Test

**Goal**: Establish performance baseline under normal load.

**Profile**: 100 concurrent users, 5 minutes duration

```bash
locust -f tests/load/locustfile.py \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host http://localhost:8000 \
    --html reports/baseline-load.html
```

**Success Criteria**:

- RPS: ≥50 requests/second
- p95 latency: <150ms (GPU) or <400ms (CPU)
- Error rate: <1%
- No memory leaks

### 2. Stress Test (Find Breaking Point)

**Goal**: Determine maximum capacity and failure modes.

**Profile**: Ramp from 0 → 1000 users over 10 minutes

```bash
locust -f tests/load/locustfile.py \
    --users 1000 \
    --spawn-rate 50 \
    --host http://localhost:8000 \
    --html reports/stress-test.html
```

**Observe**:

- CPU/memory/GPU saturation points
- Error rate increase threshold
- Latency degradation curve
- Queue depth behavior

**Expected Breaking Point**: 300-500 concurrent users (single instance, CPU)

### 3. Spike Test (Sudden Traffic Surge)

**Goal**: Test recovery from sudden traffic spikes.

**Profile**: 10 users → 500 users in 30s → back to 10 users

```bash
# Phase 1: Baseline (2 min)
locust -f tests/load/locustfile.py \
    --users 10 \
    --spawn-rate 10 \
    --run-time 2m \
    --host http://localhost:8000

# Phase 2: Spike (30s ramp + 2 min sustained)
# Manually increase to 500 users via web UI

# Phase 3: Recovery (observe 5 min)
# Manually decrease to 10 users via web UI
```

**Use Web UI for spike tests**:

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
# Open http://localhost:8089
# Manually adjust user count for spike pattern
```

**Success Criteria**:

- System remains responsive during spike
- Error rate returns to <1% within 1 minute post-spike
- No cascading failures
- Memory returns to baseline within 5 minutes

### 4. Soak Test (Long Duration Stability)

**Goal**: Verify system stability over extended runtime (24 hours).

**Profile**: 50 concurrent users, 24 hours duration

```bash
# Run in background with nohup
nohup locust -f tests/load/locustfile.py \
    --users 50 \
    --spawn-rate 5 \
    --run-time 24h \
    --host http://localhost:8000 \
    --html reports/soak-test.html \
    > soak-test.log 2>&1 &
```

**Monitor**:

- Memory leaks (RSS growth over time)
- Latency drift
- Error rate stability
- Resource cleanup (batch job store)

**Success Criteria**:

- No memory growth >10% over 24h
- Stable p95 latency (±5%)
- Error rate <0.5%
- No worker crashes

### 5. Batch-Heavy Load Test

**Goal**: Test batch processing under load.

**Profile**: Custom user class with higher batch task weight

```python
# Edit locustfile.py temporarily:
# @task(10) process_batch_small
# @task(5) process_batch_large
# @task(2) process_single_document
```

```bash
locust -f tests/load/locustfile.py \
    --users 50 \
    --spawn-rate 5 \
    --run-time 10m \
    --host http://localhost:8000 \
    --html reports/batch-heavy-load.html
```

**Observe**:

- Job queue depth
- Background task processing rate
- Memory usage with large result sets

## Interactive Load Testing (Web UI)

**Start Locust Web UI**:

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

**Open**: <http://localhost:8089>

**Advantages**:

- Real-time charts (RPS, latency, errors)
- Manual user count adjustment (spike testing)
- Live failure inspection
- Download reports mid-test

## Environment Configuration

### API Authentication

Set API key for load tests:

```bash
# Option 1: Environment variable
export LOCUST_API_KEY="your-api-key"

# Option 2: Edit locustfile.py
# api_key = "your-api-key"  # Line 32
```

### Target Environment

```bash
# Local development
locust -f tests/load/locustfile.py --host http://localhost:8000

# Staging environment
locust -f tests/load/locustfile.py --host https://staging-api.example.com

# Production (USE WITH CAUTION)
locust -f tests/load/locustfile.py --host https://api.example.com --users 10
```

## Metrics to Track

### Locust Built-in Metrics

- **RPS (Requests/Second)**: Throughput
- **Latency Distribution**: p50, p95, p99
- **Failure Rate**: % of failed requests
- **User Count**: Concurrent users

### External Metrics (Monitor Separately)

```bash
# System resources
htop          # CPU/memory
nvidia-smi    # GPU utilization
iostat        # Disk I/O

# API metrics (if Prometheus enabled)
curl http://localhost:8000/metrics

# Docker stats
docker stats
```

### Key Performance Indicators

| Metric | Target (GPU) | Target (CPU) |
|--------|--------------|--------------|
| p95 Latency (single doc) | <150ms | <400ms |
| p95 Latency (batch) | <2s | <5s |
| Throughput | ≥100 RPS | ≥30 RPS |
| Error Rate | <1% | <1% |
| Memory Growth | <10%/24h | <10%/24h |

## Analyzing Results

### HTML Report

Generated with `--html reports/test-name.html`:

- Charts: RPS, latency, failure rate over time
- Statistics table: request counts, timings
- Failure details: error messages, counts

### CSV Export

For custom analysis:

```bash
locust -f tests/load/locustfile.py \
    --csv reports/test-results \
    --host http://localhost:8000
```

Outputs:

- `test-results_stats.csv` - Request statistics
- `test-results_failures.csv` - Failure details
- `test-results_stats_history.csv` - Time-series data

### Common Failure Patterns

**High Error Rate (>5%)**:

- Check: API logs for exceptions
- Likely: Resource exhaustion, timeouts

**Increasing Latency**:

- Check: CPU/GPU utilization, queue depth
- Likely: Saturation, GC pressure

**Memory Growth**:

- Check: Batch job store size, temp file cleanup
- Likely: Leak in job storage or file handling

**Intermittent Failures**:

- Check: Rate limiting, batch size limits
- Likely: Configuration limits hit

## Troubleshooting

### No Test Fixtures

```bash
# Check fixtures directory
ls tests/load/fixtures/

# Copy sample files
cp data/test_fixtures/sample.pdf tests/load/fixtures/
```

### Authentication Errors (401/403)

```bash
# Disable auth for testing
export IMGPREP_API_AUTH_ENABLED=false

# Or set valid API key
export LOCUST_API_KEY="valid-key"
```

### Rate Limiting (429 errors)

```bash
# Disable rate limiting for load tests
export IMGPREP_API_RATE_LIMIT_ENABLED=false

# Or increase limits
export IMGPREP_API_RATE_LIMIT_REQUESTS=1000
export IMGPREP_API_RATE_LIMIT_WINDOW_SECONDS=60
```

### Locust "Too Many Open Files"

```bash
# Increase file descriptor limit
ulimit -n 10000

# Or reduce spawn rate
locust --spawn-rate 10  # Instead of 50
```

## Continuous Load Testing

### GitHub Actions Integration

```yaml
# .github/workflows/load-test.yml
name: Weekly Load Test

on:
  schedule:
    - cron: '0 2 * * 0'  # Sunday 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install locust
      - run: |
          locust -f tests/load/locustfile.py \
            --users 100 --spawn-rate 10 --run-time 5m \
            --host http://staging-api.example.com \
            --html load-test-report.html \
            --headless
      - uses: actions/upload-artifact@v4
        with:
          name: load-test-report
          path: load-test-report.html
```

## Best Practices

1. **Always test in staging first** - Never load test production without planning
2. **Start small** - Begin with 10 users, gradually increase
3. **Monitor system resources** - CPU, memory, GPU, disk I/O
4. **Use realistic test data** - Varying document sizes and types
5. **Run during off-peak hours** - Minimize user impact
6. **Document results** - Track baseline metrics over time
7. **Coordinate with team** - Notify before load tests

## References

- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://k6.io/docs/test-types/)
- [API Performance Testing](https://www.blazemeter.com/blog/api-load-testing)
