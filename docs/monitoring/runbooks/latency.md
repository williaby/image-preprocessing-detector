---
schema_type: common
title: "Latency Runbooks"
description: "Runbooks for latency alerts and performance issues"
tags:
  - guide
  - monitoring
  - performance
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document response procedures for latency alerts."
---

## HighP50Latency / HighP95Latency / CriticalP99Latency

### Overview

Processing latency has exceeded acceptable thresholds. This indicates the system is taking too long to process pages.

### Impact

- User requests taking longer than expected
- Potential timeout errors for synchronous requests
- Queue buildup if processing can't keep up

### Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| p50 | > 0.2s | - |
| p95 | > 0.5s | - |
| p99 | - | > 2.0s |

### Investigation Steps

1. **Check current latency breakdown**

   ```bash
   # View latency by operation
   curl -s http://imgprep:8000/metrics | grep imgprep_processing_duration_seconds
   ```

2. **Identify slow component**
   - Gate detection: `imgprep_gate_duration_seconds`
   - IQA: `imgprep_iqa_duration_seconds`
   - Corrections: `imgprep_correction_duration_seconds`

3. **Check resource utilization**

   ```bash
   # CPU/Memory on worker containers
   docker stats imgprep-worker --no-stream

   # GPU memory
   nvidia-smi
   ```

4. **Check for queue backlog**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_queue_depth
   ```

5. **Review recent deployments**

   ```bash
   docker inspect imgprep-worker --format='{{.Config.Image}} {{.Created}}'
   ```

### Resolution

#### If CPU-bound

```bash
# Scale workers horizontally
docker compose up -d --scale imgprep-worker=6
```

#### If GPU-bound

```bash
# Check if teacher escalation is high
curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations

# Temporarily disable teacher if escalation rate > 30%
export IMGPREP_TEACHER_ENABLED=false
docker restart imgprep-worker
```

#### If queue backlog

```bash
# Increase worker count
docker compose up -d --scale imgprep-worker=8

# Consider enabling batch mode
export IMGPREP_BATCH_MODE=true
docker restart imgprep-worker
```

### Prevention

- Set up autoscaling based on queue depth
- Monitor and alert on latency trends before they become critical
- Regular performance testing after deployments

---

## StudentModelSlow

### Overview

The student model (ResNet-18) is exceeding its target latency of 100ms p95.

### Impact

- Overall processing slowdown
- May cause teacher model to be invoked more often (higher costs)

### Investigation Steps

1. **Check model device**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_model_loaded
   ```

2. **Verify GPU availability**

   ```bash
   docker exec imgprep-worker nvidia-smi
   ```

3. **Check for memory pressure**

   ```bash
   docker exec imgprep-worker free -h
   ```

### Resolution

#### If running on CPU (should be GPU)

```bash
# Restart workers to reinitialize GPU
docker restart imgprep-worker
```

#### If GPU memory exhausted

```bash
# Reduce batch size
export IMGPREP_BATCH_SIZE=4
docker restart imgprep-worker
```

### Prevention

- Ensure GPU is always available for student model
- Monitor model load status
- Configure resource limits in docker-compose.yml
