---
schema_type: common
title: "Error Runbooks"
description: "Runbooks for error rate alerts and processing failures"
tags:
  - guide
  - monitoring
  - infrastructure
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document response procedures for error alerts."
---

## HighErrorRate / CriticalErrorRate

### Overview

The percentage of pages failing processing has exceeded thresholds.

### Impact

- Documents not being processed correctly
- User-facing errors
- Potential data loss if errors aren't retried

### Thresholds

| Alert | Threshold | For Duration |
|-------|-----------|--------------|
| HighErrorRate | > 5% | 5 minutes |
| CriticalErrorRate | > 20% | 2 minutes |

### Investigation Steps

1. **Identify error category**

   ```bash
   curl -s http://imgprep:8000/metrics | grep imgprep_errors_total
   ```

2. **Check error codes distribution**

   ```bash
   # Most common error codes
   curl -s http://imgprep:8000/metrics | grep imgprep_errors_total | sort -t'=' -k2 -rn
   ```

3. **Review application logs**

   ```bash
   kubectl logs -n imgprep -l app=imgprep-worker --tail=500 | grep ERROR
   ```

4. **Check for correlation with specific inputs**

   ```bash
   # Look for patterns in error logs
   kubectl logs -n imgprep -l app=imgprep-worker --tail=1000 | \
     grep -E "error_code.*E[0-9]+" | \
     jq -r '.document_id' | sort | uniq -c | sort -rn
   ```

### Common Error Codes

| Code | Category | Description | Resolution |
|------|----------|-------------|------------|
| E1001 | Validation | Invalid file type | Check input validation |
| E1006 | Validation | Corrupt PDF | Skip or retry with fallback |
| E2001 | Processing | General processing failure | Check logs for root cause |
| E2002 | Processing | IQA failed | Check model status |
| E3001 | Infrastructure | GPU unavailable | Restart workers |
| E3005 | Infrastructure | Timeout | Scale workers |

### Resolution

#### For Validation Errors (E1xxx)

```bash
# Check what invalid inputs are being submitted
kubectl logs -n imgprep -l app=imgprep-worker --tail=1000 | \
  grep "E100" | jq '.details'

# Add input validation at API gateway level if needed
```

#### For Processing Errors (E2xxx)

```bash
# Restart workers to clear any corrupted state
kubectl rollout restart deployment/imgprep-worker -n imgprep

# If IQA errors (E2002), check model status
curl -s http://imgprep:8000/metrics | grep imgprep_model_loaded
```

#### For Infrastructure Errors (E3xxx)

```bash
# Check infrastructure health
kubectl get pods -n imgprep -o wide
kubectl describe pods -n imgprep -l app=imgprep-worker

# Restart affected components
kubectl rollout restart deployment/imgprep-worker -n imgprep
```

### Prevention

- Implement input validation at API gateway
- Add circuit breakers for external dependencies
- Configure automatic retries for transient errors

---

## ProcessingErrorSpike

### Overview

More than 50 processing errors in 5 minutes indicates a systematic issue.

### Investigation Steps

1. **Check if errors are correlated**

   ```bash
   # Same document?
   kubectl logs -n imgprep -l app=imgprep-worker --tail=500 | \
     grep "E2" | jq '.document_id' | sort | uniq -c
   ```

2. **Check for pattern in page types**

   ```bash
   kubectl logs -n imgprep -l app=imgprep-worker --tail=500 | \
     grep "E2" | jq '.gate_result' | sort | uniq -c
   ```

### Resolution

If errors are from specific documents:

```bash
# Block problematic document temporarily
# Add to blocklist or move to manual review queue
```

If errors are widespread:

```bash
# Rollback recent deployment if applicable
kubectl rollout undo deployment/imgprep-worker -n imgprep
```

---

## InfrastructureErrorSpike

### Overview

Infrastructure errors indicate problems with GPUs, storage, or network.

### Investigation Steps

1. **Check pod health**

   ```bash
   kubectl get pods -n imgprep -o wide
   kubectl describe pods -n imgprep | grep -A5 "Conditions:"
   ```

2. **Check node health**

   ```bash
   kubectl get nodes -o wide
   kubectl describe nodes | grep -A10 "Conditions:"
   ```

3. **Check GPU status**

   ```bash
   kubectl exec -it deployment/imgprep-worker -n imgprep -- nvidia-smi
   ```

### Resolution

```bash
# Restart workers
kubectl rollout restart deployment/imgprep-worker -n imgprep

# If GPU issues, cordon and drain node
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets
```

### Escalation

If infrastructure errors persist after restart, escalate to DevOps team.
