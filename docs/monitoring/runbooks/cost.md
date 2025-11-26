# Cost Runbooks

## HighDailyCost

### Overview

Estimated daily cost has exceeded $5 threshold.

### Impact

- Budget consumption faster than planned
- May exhaust monthly free tier

### Thresholds

| Metric | Warning |
|--------|---------|
| Daily Cost | > $5 |

### Investigation Steps

1. **Check current cost breakdown**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_estimated_cost
   ```

2. **Check teacher invocation rate**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations_total
   ```

3. **Check Modal GPU usage**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_modal_gpu_seconds_total
   ```

4. **Identify cost drivers**

   ```bash
   # Pages processed today
   curl -s http://imgprep:8000/metrics | grep imgprep_pages_processed_total

   # Teacher escalation rate
   # Cost/page ratio
   ```

### Resolution

#### Reduce teacher usage

```bash
# Increase uncertainty threshold (fewer escalations)
kubectl set env deployment/imgprep-worker IMGPREP_UNCERTAINTY_THRESHOLD=0.35 -n imgprep

# Or disable teacher entirely
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_ENABLED=false -n imgprep
```

#### Use local GPU instead of Modal

```bash
# Switch to local GPU (if available)
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_DEVICE=gpu -n imgprep
kubectl set env deployment/imgprep-worker IMGPREP_MODAL_ENABLED=false -n imgprep
```

#### Implement rate limiting

```bash
# Add daily teacher limit
kubectl set env deployment/imgprep-worker IMGPREP_DAILY_TEACHER_LIMIT=1000 -n imgprep
```

---

## CostSpike

### Overview

Cost rate has suddenly increased, indicating unusual usage pattern.

### Investigation Steps

1. **Check recent traffic volume**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_pages_processed_total
   ```

2. **Check escalation rate**

   ```bash
   # Calculate escalation percentage
   teacher=$(curl -s http://imgprep:8000/metrics | grep 'imgprep_teacher_invocations_total' | awk '{sum+=$2}END{print sum}')
   pages=$(curl -s http://imgprep:8000/metrics | grep 'imgprep_pages_processed_total' | awk '{sum+=$2}END{print sum}')
   echo "Escalation rate: $(echo "scale=2; $teacher/$pages*100" | bc)%"
   ```

3. **Check for unusual document types**

   ```bash
   kubectl logs -n imgprep -l app=imgprep-worker --tail=1000 | \
     jq 'select(.event == "page_processed")' | \
     jq '.gate_result' | sort | uniq -c
   ```

### Resolution

#### If traffic spike

```bash
# Consider if this is expected (marketing campaign, batch job, etc.)
# If unexpected, investigate source of traffic
```

#### If escalation spike

```bash
# Check if specific document types are causing escalations
# Adjust thresholds or implement filtering
```

---

## MonthlyBudgetWarning / MonthlyBudgetCritical

### Overview

Approaching or exceeding the $30 monthly Modal free tier budget.

### Impact

- **Warning (>$20)**: Risk of exceeding budget
- **Critical (>$28)**: Budget will be exceeded soon

### Investigation Steps

1. **Check current spend**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_estimated_cost
   ```

2. **Calculate remaining budget**

   ```bash
   # Days remaining in month
   days_remaining=$(( ($(date -d "$(date +%Y-%m-01) +1 month -1 day" +%s) - $(date +%s)) / 86400 ))
   echo "Days remaining: $days_remaining"
   ```

3. **Project end-of-month spend**

   ```bash
   # Current daily rate * days remaining
   ```

### Resolution

#### Immediate cost reduction

```bash
# Disable Modal GPU, use local only
kubectl set env deployment/imgprep-worker IMGPREP_MODAL_ENABLED=false -n imgprep

# Or set strict daily budget
kubectl set env deployment/imgprep-worker IMGPREP_DAILY_BUDGET=0.5 -n imgprep
```

#### Long-term solutions

1. Increase uncertainty threshold to reduce teacher usage
2. Use local GPU for teacher inference when available
3. Implement smarter escalation logic
4. Consider upgrading Modal plan if usage is justified

---

## HighModalGPUUsage

### Overview

Modal GPU usage rate exceeds 100 seconds/hour.

### Impact

- Higher than expected costs
- May indicate inefficient usage

### Investigation Steps

1. **Check average inference time**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_iqa_duration_seconds
   ```

2. **Check teacher invocation frequency**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations_total
   ```

3. **Check for inefficiencies**
   - Are results being cached?
   - Is batch processing enabled?
   - Are there retry loops?

### Resolution

#### Enable batching

```bash
# Process multiple images per GPU call
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_BATCH_SIZE=8 -n imgprep
```

#### Enable caching

```bash
# Cache teacher results
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_CACHE_ENABLED=true -n imgprep
```

#### Optimize model

```bash
# Use ONNX optimized model
kubectl set env deployment/imgprep-worker IMGPREP_TEACHER_FORMAT=onnx -n imgprep
```

### Cost Reference

| GPU Type | Modal Cost | Time for $1 |
|----------|------------|-------------|
| T4 | $0.000076/sec | ~3.7 hours |
| A10 | $0.000183/sec | ~1.5 hours |
| A100 | $0.000417/sec | ~40 min |

Monthly free tier: $30 = ~109 hours of T4 time
