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
   curl -s http://imgprep:8000/metrics | grep imgprep_processing_duration
   ```

2. **Identify slow component**
   - Gate detection: `imgprep_gate_duration_seconds`
   - IQA: `imgprep_iqa_duration_seconds`
   - Corrections: `imgprep_correction_duration_seconds`

3. **Check resource utilization**

   ```bash
   # CPU/Memory on worker pods
   kubectl top pods -n imgprep -l app=imgprep-worker

   # GPU memory
   nvidia-smi
   ```

4. **Check for queue backlog**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_queue_depth
   ```

5. **Review recent deployments**

   ```bash
   kubectl rollout history deployment/imgprep-worker -n imgprep
   ```

### Resolution

#### If CPU-bound

```bash
# Scale workers horizontally
kubectl scale deployment/imgprep-worker --replicas=6 -n imgprep
```

#### If GPU-bound

```bash
# Check if teacher escalation is high
curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations

# Temporarily disable teacher if escalation rate > 30%
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_ENABLED=false -n imgprep
```

#### If queue backlog

```bash
# Increase worker count
kubectl scale deployment/imgprep-worker --replicas=8 -n imgprep

# Consider enabling batch mode
kubectl set env deployment/imgprep-worker IMGPREP_BATCH_MODE=true -n imgprep
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
   kubectl exec -it deployment/imgprep-worker -n imgprep -- nvidia-smi
   ```

3. **Check for memory pressure**

   ```bash
   kubectl exec -it deployment/imgprep-worker -n imgprep -- free -h
   ```

### Resolution

#### If running on CPU (should be GPU)

```bash
# Restart workers to reinitialize GPU
kubectl rollout restart deployment/imgprep-worker -n imgprep
```

#### If GPU memory exhausted

```bash
# Reduce batch size
kubectl set env deployment/imgprep-worker IMGPREP_BATCH_SIZE=4 -n imgprep
```

### Prevention

- Ensure GPU is always available for student model
- Monitor model load status
- Set resource requests/limits appropriately
