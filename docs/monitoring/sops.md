# Standard Operating Procedures (SOPs)

This document outlines regular operational procedures for monitoring and drift detection.

---

## Daily Tasks

### Morning Health Check (15 minutes)

**When:** 9:00 AM local time

**Checklist:**

- [ ] Review overnight alerts in #imgprep-alerts Slack channel
- [ ] Check Grafana dashboards for anomalies
- [ ] Verify evaluation job ran successfully
- [ ] Review queue depth and processing latency

**Commands:**

```bash
# Check for overnight critical alerts
grep "CRITICAL" /var/log/imgprep/drift_alerts.log | tail -20

# Verify evaluation job status
cat data/performance_monitoring/reports/latest.json | jq '.timestamp, .alerts'

# Check current metrics
curl -s "http://prometheus:9090/api/v1/query?query=imgprep_drift_kl_divergence" | jq '.data.result'
```

### End-of-Day Summary (10 minutes)

**When:** 5:00 PM local time

**Checklist:**

- [ ] Resolve or escalate any pending alerts
- [ ] Document any manual interventions
- [ ] Update incident log if applicable

---

## Weekly Tasks

### Weekly Drift Review (30 minutes)

**When:** Monday 10:00 AM

**Purpose:** Review drift trends and identify early warning signs.

**Procedure:**

1. **Review KL Divergence Trends**

   ```bash
   # Get 7-day KL divergence trend
   curl -s "http://prometheus:9090/api/v1/query_range?query=imgprep_drift_kl_divergence&start=$(date -d '7 days ago' +%s)&end=$(date +%s)&step=1h" > weekly_kl.json
   ```

2. **Review Model Performance Trends**

   ```bash
   # Check mAP trend
   poetry run python -c "
   from image_preprocessing_detector.drift.performance import MetricsStore
   store = MetricsStore('data/performance_monitoring/metrics')
   history = store.get_history('mAP', days=7)
   for ts, val in history:
       print(f'{ts}: {val:.4f}')
   "
   ```

3. **Check Harvested Samples**

   ```bash
   # Count samples harvested this week
   find data/drift_samples/ -name "*.png" -mtime -7 | wc -l

   # Review harvest reasons
   cat data/drift_samples/manifests/latest_manifest.json | jq '.samples[].harvest_reason' | sort | uniq -c
   ```

4. **Document Findings**
   - Update weekly status report
   - Note any trends requiring attention
   - Schedule follow-up actions

### Weekly Reference Distribution Check (15 minutes)

**When:** Friday 2:00 PM

**Purpose:** Ensure reference distributions are current and valid.

**Procedure:**

1. **Check Reference Ages**

   ```bash
   # List reference distributions and their ages
   ls -la data/drift_references/*.json

   # Check expiration dates
   for f in data/drift_references/*.json; do
       echo "$f: $(jq -r '.expires_at' $f)"
   done
   ```

2. **Rotate Expiring References**

   ```bash
   # If any references expire within 7 days, schedule rotation
   poetry run python -c "
   from image_preprocessing_detector.drift import ReferenceStore
   store = ReferenceStore('data/drift_references')
   expired = store.rotate_expired()
   print(f'Rotated {len(expired)} expired references')
   "
   ```

---

## Monthly Tasks

### Monthly Performance Report (1 hour)

**When:** First Monday of month

**Purpose:** Generate comprehensive monthly performance report.

**Procedure:**

1. **Gather Metrics**

   ```bash
   # Export monthly metrics
   poetry run python scripts/generate_monthly_report.py --month=$(date -d 'last month' +%Y-%m)
   ```

2. **Compile Report**
   - mAP/F1 trends and comparison to baseline
   - Drift detection events and resolutions
   - Harvested sample statistics
   - Alert frequency and response times

3. **Review with Team**
   - Schedule monthly review meeting
   - Discuss trends and concerns
   - Plan improvements for next month

### Monthly Reference Rotation (30 minutes)

**When:** Last Friday of month

**Purpose:** Refresh reference distributions with recent data.

**Procedure:**

1. **Backup Current References**

   ```bash
   tar -czf backup_references_$(date +%Y%m).tar.gz data/drift_references/
   ```

2. **Generate New References**

   ```bash
   poetry run python -c "
   from image_preprocessing_detector.drift import (
       create_tracker, create_drift_detector, FeatureType
   )

   detector = create_drift_detector('data/drift_references')
   tracker = create_tracker()

   # Load last month's samples into tracker
   # (implementation depends on data pipeline)

   for feature in FeatureType:
       ref = detector.create_reference_from_tracker(tracker, feature, min_samples=1000)
       if ref:
           print(f'Created reference for {feature.value}')
   "
   ```

3. **Validate New References**
   - Compare new references to old
   - Verify no unexpected distribution shifts
   - Document any significant changes

### Monthly Alert Threshold Review (45 minutes)

**When:** Second Monday of month

**Purpose:** Review and tune alert thresholds based on false positive/negative rates.

**Procedure:**

1. **Calculate False Positive Rate**

   ```bash
   # Review alerts that were resolved without action
   grep "resolved" /var/log/imgprep/drift_alerts.log | grep -c "false_positive"
   ```

2. **Identify Missed Events**
   - Review incidents that weren't caught by alerts
   - Identify gaps in alerting coverage

3. **Adjust Thresholds**
   - If FP rate > 10%, consider raising thresholds
   - If missed events, consider lowering thresholds
   - Update `docs/monitoring/thresholds.md`

4. **Test New Thresholds**

   ```bash
   # Use dry-run mode to test
   poetry run python -c "
   from image_preprocessing_detector.drift.alerting import AlertConfig, AlertManager

   config = AlertConfig(
       kl_warning=0.18,  # Proposed new threshold
       kl_critical=0.32,
       dry_run=True,
   )
   manager = AlertManager(config)

   # Replay recent data and check alert counts
   # ...
   "
   ```

---

## Quarterly Tasks

### Quarterly Model Evaluation (2 hours)

**When:** First week of quarter

**Purpose:** Comprehensive evaluation of model performance and drift detection effectiveness.

**Procedure:**

1. **Full Evaluation Suite**

   ```bash
   # Run comprehensive evaluation
   poetry run python -m image_preprocessing_detector.drift.performance full_evaluation \
       --model /models/iqa_student.onnx \
       --dataset /data/quarterly_eval_set \
       --output quarterly_eval_$(date +%Y_Q$((($(date +%-m)-1)/3+1))).json
   ```

2. **Compare to Previous Quarter**
   - mAP/F1 trends
   - Drift detection accuracy
   - Alert response times

3. **Review Active Learning Pipeline**
   - Total samples harvested
   - Privacy review completion rate
   - Re-training impact analysis

4. **Generate Quarterly Report**
   - Executive summary
   - Key metrics and trends
   - Recommendations for next quarter

### Quarterly Privacy Audit (1 hour)

**When:** Second week of quarter

**Purpose:** Audit harvested samples for privacy compliance.

**Procedure:**

1. **Review Sample Inventory**

   ```bash
   # Count samples by privacy status
   find data/drift_samples/manifests/ -name "*.json" -exec jq '.samples[].privacy_status' {} \; | sort | uniq -c
   ```

2. **Audit Requires_Review Samples**
   - Manual review of flagged samples
   - Update privacy status
   - Delete rejected samples

3. **Update Privacy Checklist**
   - Review and update checklist based on findings
   - Document any new PII patterns discovered

4. **Generate Compliance Report**
   - Summary of privacy review activities
   - Approval/rejection statistics
   - Recommendations for process improvements

### Quarterly Retention Cleanup (30 minutes)

**When:** Last week of quarter

**Purpose:** Clean up old data according to retention policies.

**Procedure:**

1. **Clean Old Metrics**

   ```bash
   # Remove metrics older than retention period
   poetry run python -c "
   from image_preprocessing_detector.drift.performance import MetricsStore
   store = MetricsStore('data/performance_monitoring/metrics')
   removed = store.cleanup_old_results()
   print(f'Removed {removed} old evaluation results')
   "
   ```

2. **Archive Old Samples**

   ```bash
   # Archive samples older than 90 days
   find data/drift_samples/ -name "*.png" -mtime +90 -exec mv {} archive/ \;
   ```

3. **Clean Alert History**

   ```bash
   poetry run python -c "
   from image_preprocessing_detector.drift.alerting import AlertHistory
   history = AlertHistory('data/alert_history')
   removed = history.cleanup_old_alerts()
   print(f'Removed {removed} old alerts')
   "
   ```

---

## Incident Response

### P1 (Critical) - Immediate Response

**Trigger:** Critical drift alert (KL > 0.3, mAP drop > 5%)

**Response Time:** 15 minutes

**Procedure:**

1. Acknowledge alert immediately
2. Assess impact on production
3. Consider enabling fallback mode (disable teacher if causing issues)
4. Escalate to on-call engineer
5. Begin investigation per runbook

### P2 (Warning) - Urgent Response

**Trigger:** Warning drift alert

**Response Time:** 1 hour

**Procedure:**

1. Acknowledge alert
2. Review alert details and samples
3. Determine if trend requires action
4. Schedule remediation if needed

### P3 (Informational) - Scheduled Response

**Trigger:** Informational alerts or scheduled reviews

**Response Time:** Next business day

**Procedure:**

1. Review during daily health check
2. Document in weekly report if significant
3. Schedule follow-up as needed

---

## Escalation Matrix

| Severity | Primary | Secondary | Escalation Time |
|----------|---------|-----------|-----------------|
| P1 Critical | On-call Engineer | Engineering Lead | 30 minutes |
| P2 Warning | Platform Team | On-call Engineer | 2 hours |
| P3 Info | Platform Team | - | Next business day |

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | (rotating) | #oncall-imgprep |
| Platform Team Lead | TBD | @platform-lead |
| Data Governance | TBD | @data-governance |
| ML Engineering | TBD | @ml-engineering |
