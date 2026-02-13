---
schema_type: common
title: "Model Runbooks"
description: "Runbooks for model-related alerts (escalation, drift)"
tags:
  - guide
  - monitoring
  - machine_learning
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document response procedures for model alerts."
---

## HighTeacherEscalationRate

### Overview

More than 25% of pages are being escalated to the teacher model for inference.

### Impact

- Increased latency (teacher is slower than student)
- Higher costs (especially if using Modal GPU)
- May indicate student model degradation or unusual input distribution

### Thresholds

| Metric | Warning |
|--------|---------|
| Escalation Rate | > 25% for 10 minutes |

### Investigation Steps

1. **Check escalation reasons**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_teacher_invocations_total
   ```

2. **Check escalation breakdown by reason**
   - `uncertainty`: Student confidence below threshold
   - `discrepancy`: Student vs classical IQA disagreement
   - `high_risk`: Document flagged as high risk

3. **Check quality score distribution**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_quality_score
   ```

4. **Review input document characteristics**

   ```bash
   docker logs imgprep-worker --tail=500 | \
     jq 'select(.model_selection == "teacher_uncertainty")' | \
     jq '.gate_result' | sort | uniq -c
   ```

### Resolution

#### If uncertainty threshold too low

```bash
# Increase uncertainty threshold (fewer escalations)
export IMGPREP_UNCERTAINTY_THRESHOLD=0.3
docker restart imgprep-worker
```

#### If document quality is unusual

```bash
# Check if specific document types are causing escalation
# May need to adjust preprocessing or add document-type-specific handling
```

#### If costs are concern

```bash
# Temporarily disable teacher model
export IMGPREP_TEACHER_ENABLED=false
docker restart imgprep-worker

# Note: This will reduce quality for difficult documents
```

### Prevention

- Monitor escalation rate trends
- Regularly validate student model accuracy
- Consider retraining student model if escalation rate increases over time

---

## TeacherBlockedFrequently

### Overview

Teacher model invocations are being blocked, likely due to budget or rate limits.

### Impact

- Reduced quality for difficult documents
- Student-only inference may miss quality issues

### Investigation Steps

1. **Check blocked reasons**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_teacher_blocked_total
   ```

2. **Check cost metrics**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_estimated_cost
   ```

3. **Check Modal GPU availability**

   ```bash
   # If using Modal
   modal app list
   ```

### Resolution

#### If budget limit

```bash
# Increase daily budget limit
export IMGPREP_DAILY_BUDGET=10
docker restart imgprep-worker

# Or use local GPU instead of Modal
export IMGPREP_TEACHER_DEVICE=gpu
docker restart imgprep-worker
```

#### If rate limit

```bash
# Reduce escalation rate by adjusting threshold
export IMGPREP_UNCERTAINTY_THRESHOLD=0.35
docker restart imgprep-worker
```

---

## ModelDrift

### Overview

The distribution of quality scores has shifted significantly, indicating potential model drift or change in input data.

### Impact

- Model may be producing inaccurate quality assessments
- Could lead to over/under correction of documents

### Investigation Steps

1. **Compare current vs historical quality distribution**

   ```bash
   # Check quality score buckets
   curl -s http://imgprep:8000/metrics | grep imgprep_quality_score_bucket
   ```

2. **Check if input data characteristics changed**

   ```bash
   # Gate decision distribution
   curl -s http://imgprep:8000/metrics | grep imgprep_pages_processed_total
   ```

3. **Review recent model changes**

   ```bash
   # Check recent container image history
   docker inspect imgprep-worker --format='{{.Config.Image}}'
   ```

### Resolution

1. **Investigate root cause**
   - Was there a model update?
   - Did input data distribution change?
   - Are there new document types being processed?

2. **If model degradation confirmed**:

   ```bash
   # Rollback to previous model version
   export IMGPREP_MODEL_VERSION=v1.2.3
   docker restart imgprep-worker
   ```

3. **If input data changed**:
   - Document the new data characteristics
   - Consider retraining the model on updated data
   - Adjust thresholds if appropriate

### Prevention

- Implement continuous model monitoring
- Track data distribution metrics
- Set up scheduled model validation tests
