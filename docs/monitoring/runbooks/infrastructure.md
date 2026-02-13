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
   docker exec imgprep-worker nvidia-smi
   ```

2. **Check for memory leaks**

   ```bash
   # Watch memory over time
   docker exec imgprep-worker watch -n 5 nvidia-smi
   ```

3. **Check batch sizes**

   ```bash
   docker exec imgprep-worker printenv | grep BATCH_SIZE
   ```

### Resolution

#### Immediate

```bash
# Restart workers to clear GPU memory
docker restart imgprep-worker
```

#### If recurring

```bash
# Reduce batch size
export IMGPREP_BATCH_SIZE=2
docker restart imgprep-worker

# Or disable teacher model temporarily
export IMGPREP_TEACHER_ENABLED=false
docker restart imgprep-worker
```

---

## GPUUnavailable

### Overview

No models (student or teacher) are currently loaded, indicating GPU unavailability.

### Impact

- **Critical**: Processing cannot continue without models
- All requests will fail

### Investigation Steps

1. **Check container status**

   ```bash
   docker ps --filter name=imgprep-worker
   docker inspect imgprep-worker --format='{{.State.Status}}'
   ```

2. **Check GPU availability**

   ```bash
   docker exec imgprep-worker nvidia-smi
   ```

3. **Check for device driver issues**

   ```bash
   docker logs imgprep-worker | grep -i "cuda\|gpu\|driver"
   ```

### Resolution

```bash
# Restart workers
docker restart imgprep-worker

# If still failing, check GPU availability on host
nvidia-smi

# Stop and restart with fresh state
docker compose down imgprep-worker
docker compose up -d imgprep-worker
```

### Escalation

If GPU remains unavailable after restart, escalate to DevOps for host investigation.

---

## WorkersDegraded / NoActiveWorkers

### Overview

Worker count has dropped below minimum (2) or to zero.

### Impact

- **WorkersDegraded**: Reduced throughput, potential queue buildup
- **NoActiveWorkers**: **Critical** - No processing possible

### Investigation Steps

1. **Check container status**

   ```bash
   docker ps --filter name=imgprep-worker
   docker inspect imgprep-worker --format='{{.State.Status}} {{.State.ExitCode}}'
   ```

2. **Check for resource constraints**

   ```bash
   docker stats imgprep-worker --no-stream
   ```

3. **Check host capacity**

   ```bash
   free -h
   df -h
   ```

### Resolution

#### If containers are crashing

```bash
# Check crash reason
docker logs imgprep-worker --tail=200

# If OOM, increase memory limit in docker-compose.yml
# services.imgprep-worker.deploy.resources.limits.memory: "8g"
docker compose up -d imgprep-worker
```

#### If containers are not starting

```bash
# Check resource availability on host
docker stats --no-stream
free -h
```

#### Quick recovery

```bash
# Force restart
docker restart imgprep-worker

# Scale up via docker compose
docker compose up -d --scale imgprep-worker=4
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
   docker ps --filter name=imgprep-worker
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
docker compose up -d --scale imgprep-worker=8
```

#### Enable batch mode for faster processing

```bash
export IMGPREP_BATCH_MODE=true
docker restart imgprep-worker
```

#### If teacher escalation is causing slowdown

```bash
# Check escalation rate
curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations

# Temporarily disable teacher if > 30%
export IMGPREP_TEACHER_ENABLED=false
docker restart imgprep-worker
```

#### For persistent backlog

```bash
# Consider using Modal GPU for burst capacity
export IMGPREP_MODAL_ENABLED=true
docker restart imgprep-worker
```

### Prevention

- Monitor queue depth trends
- Implement rate limiting at API gateway
- Use Docker Compose scaling for burst capacity
