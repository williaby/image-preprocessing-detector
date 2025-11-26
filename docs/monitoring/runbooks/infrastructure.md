---
schema_type: common
title: "Infrastructure Runbooks"
description: "Runbooks for infrastructure alerts (GPU, workers, queue)"
tags:
  - guide
  - monitoring
  - infrastructure
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document response procedures for infrastructure alerts."
---

## GPUMemoryHigh

### Overview

GPU memory usage has exceeded 90% on one or more devices.

### Impact

- Risk of out-of-memory errors
- Potential model inference failures
- May cause worker crashes

### Investigation Steps

1. **Check current GPU memory usage**

   ```bash
   kubectl exec -it deployment/imgprep-worker -n imgprep -- nvidia-smi
   ```

2. **Check for memory leaks**

   ```bash
   # Watch memory over time
   kubectl exec -it deployment/imgprep-worker -n imgprep -- watch -n 5 nvidia-smi
   ```

3. **Check batch sizes**

   ```bash
   kubectl get deployment/imgprep-worker -n imgprep -o yaml | grep BATCH_SIZE
   ```

### Resolution

#### Immediate

```bash
# Restart workers to clear GPU memory
kubectl rollout restart deployment/imgprep-worker -n imgprep
```

#### If recurring

```bash
# Reduce batch size
kubectl set env deployment/imgprep-worker IMGPREP_BATCH_SIZE=2 -n imgprep

# Or disable teacher model temporarily
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_ENABLED=false -n imgprep
```

---

## GPUUnavailable

### Overview

No models (student or teacher) are currently loaded, indicating GPU unavailability.

### Impact

- **Critical**: Processing cannot continue without models
- All requests will fail

### Investigation Steps

1. **Check pod status**

   ```bash
   kubectl get pods -n imgprep -l app=imgprep-worker
   kubectl describe pods -n imgprep -l app=imgprep-worker
   ```

2. **Check GPU availability on node**

   ```bash
   kubectl exec -it deployment/imgprep-worker -n imgprep -- nvidia-smi
   ```

3. **Check for device driver issues**

   ```bash
   kubectl logs -n imgprep -l app=imgprep-worker | grep -i "cuda\|gpu\|driver"
   ```

### Resolution

```bash
# Restart workers
kubectl rollout restart deployment/imgprep-worker -n imgprep

# If still failing, check node GPU allocation
kubectl describe node <node-name> | grep -A5 nvidia.com/gpu

# If node GPU exhausted, scale to different node
kubectl scale deployment/imgprep-worker --replicas=0 -n imgprep
# Wait for pods to terminate
kubectl scale deployment/imgprep-worker --replicas=4 -n imgprep
```

### Escalation

If GPU remains unavailable after restart, escalate to DevOps for node investigation.

---

## WorkersDegraded / NoActiveWorkers

### Overview

Worker count has dropped below minimum (2) or to zero.

### Impact

- **WorkersDegraded**: Reduced throughput, potential queue buildup
- **NoActiveWorkers**: **Critical** - No processing possible

### Investigation Steps

1. **Check pod status**

   ```bash
   kubectl get pods -n imgprep -l app=imgprep-worker -o wide
   kubectl describe pods -n imgprep -l app=imgprep-worker | grep -A10 "Events:"
   ```

2. **Check for resource constraints**

   ```bash
   kubectl describe pods -n imgprep -l app=imgprep-worker | grep -A5 "Requests:"
   ```

3. **Check node capacity**

   ```bash
   kubectl describe nodes | grep -A10 "Allocated resources:"
   ```

### Resolution

#### If pods are crashing

```bash
# Check crash reason
kubectl logs -n imgprep -l app=imgprep-worker --previous

# If OOM, increase memory limit
kubectl patch deployment imgprep-worker -n imgprep -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"worker","resources":{"limits":{"memory":"8Gi"}}}]}}}}'
```

#### If pods are pending

```bash
# Check for resource availability
kubectl describe pods -n imgprep -l app=imgprep-worker | grep -A5 "Events:"

# Scale down other workloads or request more nodes
```

#### Quick recovery

```bash
# Force restart
kubectl rollout restart deployment/imgprep-worker -n imgprep

# Scale up
kubectl scale deployment/imgprep-worker --replicas=4 -n imgprep
```

---

## QueueBacklog / CriticalQueueBacklog

### Overview

Processing queue has accumulated more items than can be processed in a reasonable time.

### Impact

- **QueueBacklog** (>500): Delays in processing, SLA risk
- **CriticalQueueBacklog** (>2000): Significant delays, potential timeouts

### Investigation Steps

1. **Check current queue depth**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_queue_depth
   ```

2. **Check processing rate**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_pages_processed_total
   ```

3. **Check worker status**

   ```bash
   kubectl get pods -n imgprep -l app=imgprep-worker
   ```

4. **Check for processing bottleneck**

   ```bash
   # Look at latency
   curl -s http://imgprep:8000/metrics | grep imgprep_processing_duration
   ```

### Resolution

#### Scale workers

```bash
# Double worker count
kubectl scale deployment/imgprep-worker --replicas=8 -n imgprep
```

#### Enable batch mode for faster processing

```bash
kubectl set env deployment/imgprep-worker IMGPREP_BATCH_MODE=true -n imgprep
```

#### If teacher escalation is causing slowdown

```bash
# Check escalation rate
curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations

# Temporarily disable teacher if > 30%
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_ENABLED=false -n imgprep
```

#### For persistent backlog

```bash
# Consider using Modal GPU for burst capacity
kubectl set env deployment/imgprep-worker IMGPREP_MODAL_ENABLED=true -n imgprep
```

### Prevention

- Set up HPA (Horizontal Pod Autoscaler) based on queue depth
- Monitor queue depth trends
- Implement rate limiting at API gateway
