---
schema_type: common
title: "Drift Detection FAQ"
description: "FAQ for drift detection troubleshooting and false positives"
tags:
  - guide
  - monitoring
  - machine_learning
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Answer common questions about drift detection and troubleshooting."
---

Frequently asked questions about drift detection, common false positives, and troubleshooting.

---

## General Questions

### What is drift detection?

Drift detection monitors for changes in data distributions and model performance that may indicate:

- **Data drift**: Input data characteristics changing over time
- **Concept drift**: The relationship between inputs and outputs changing
- **Model degradation**: Model accuracy declining due to stale training data

### Why do we need drift detection?

ML models are trained on historical data. When production data differs significantly from training data, model performance can degrade silently. Drift detection provides early warning of these issues.

### What metrics are monitored?

| Category | Metrics |
|----------|---------|
| Distribution | KL divergence, PSI |
| Performance | mAP, F1, precision, recall |
| Operational | Escalation rate, processing time |

---

## Common False Positives

### "KL divergence spike but no quality impact"

**Symptom:** KL divergence alert fires but model performance remains stable.

**Common Causes:**

1. **Seasonal variation**: Document types may naturally vary by time of year
   - *Example*: Tax season brings more form-heavy documents

2. **Batch processing**: Large batch of similar documents can temporarily skew distributions
   - *Example*: Processing a backlog of scanned receipts

3. **New customer onboarding**: New data sources with different characteristics
   - *Example*: Onboarding a customer with unique document formats

**Resolution:**

1. Check if performance metrics (mAP, F1) are affected
2. If performance is stable, consider:
   - Adjusting KL threshold for the specific feature
   - Adding feature-specific seasonality adjustments
   - Documenting the expected variation

**To Prevent:**

- Review reference distributions quarterly
- Consider per-source or per-document-type thresholds
- Use longer smoothing windows (7-day vs 1-day)

---

### "PSI alert during batch processing"

**Symptom:** PSI alert fires during large batch jobs.

**Common Causes:**

1. **Homogeneous batches**: Large batches of similar documents shift distributions temporarily

2. **Batch scheduling**: End-of-day or end-of-week processing creates temporary spikes

**Resolution:**

1. Check if alert correlates with batch processing schedule
2. If batch-related:
   - Add exclusion for known batch windows
   - Use longer evaluation windows

**Configuration:**

```python
# Consider batch windows in alert config
config = AlertConfig(
    cooldown_minutes=120,  # Longer cooldown during batch windows
)
```

---

### "mAP drop alert but manual review shows good results"

**Symptom:** mAP drop alert fires but spot-checking samples shows correct predictions.

**Common Causes:**

1. **Test set staleness**: Evaluation set no longer representative of production data

2. **Labeling inconsistency**: Ground truth labels may be inconsistent

3. **Edge case concentration**: Test set may overweight difficult cases

**Resolution:**

1. Review evaluation set for representativeness
2. Check for labeling quality issues
3. Compare evaluation vs production sample distributions

**To Prevent:**

- Refresh evaluation set quarterly
- Use stratified sampling for evaluation
- Track evaluation set statistics alongside production

---

### "Escalation rate spike but teacher performance stable"

**Symptom:** Teacher escalation rate increases significantly.

**Common Causes:**

1. **Input quality degradation**: Lower quality inputs trigger more uncertainty

2. **Student model threshold drift**: Student confidence thresholds may need tuning

3. **New document types**: Unfamiliar documents cause student uncertainty

**Resolution:**

1. Review samples that triggered escalation
2. Check student model confidence distribution
3. Verify teacher is handling escalations correctly

**If legitimate:**

- Consider updating student model
- Harvest escalated samples for training data

---

### "Alert fires repeatedly despite cooldown"

**Symptom:** Same alert fires multiple times within expected cooldown period.

**Common Causes:**

1. **Feature name mismatch**: Slightly different feature names bypass cooldown
   - *Example*: "quality_score" vs "quality-score"

2. **Cooldown per severity**: Different severity levels have separate cooldowns

**Resolution:**

1. Check alert IDs for consistency
2. Verify feature naming conventions
3. Review cooldown configuration

```python
# Verify cooldown settings
config = AlertConfig(
    cooldown_minutes=60,  # Ensure adequate cooldown
)
```

---

## Troubleshooting

### How do I investigate a drift alert?

1. **Get alert details:**

   ```bash
   cat /var/log/imgprep/drift_alerts.log | grep "<alert_id>"
   ```

2. **View included samples:**

   ```bash
   cat data/alert_history.json | jq '.alerts["<alert_id>"].samples'
   ```

3. **Compare distributions:**

   ```python
   from image_preprocessing_detector.drift import ReferenceStore, DistributionTracker

   store = ReferenceStore('data/drift_references')
   ref = store.get_reference('quality_score')

   # Compare with current production data
   ```

4. **Check for correlated metrics:**
   - Look at processing time, error rate, escalation rate
   - Check if multiple features drifting together

### How do I tune alert thresholds?

1. **Calculate false positive rate:**

   ```bash
   # Count alerts that were false positives
   grep "false_positive" /var/log/imgprep/drift_alerts.log | wc -l
   ```

2. **Analyze threshold impact:**

   ```python
   from image_preprocessing_detector.drift.alerting import AlertConfig, AlertManager

   # Test new threshold in dry-run mode
   config = AlertConfig(
       kl_warning=0.20,  # Proposed new threshold
       kl_critical=0.35,
       dry_run=True,
   )
   ```

3. **Update documentation:**
   - Document threshold change reason
   - Update `thresholds.md`

### How do I reset reference distributions?

**When to reset:**

- Legitimate data source change
- Model update/retraining
- Business process change

**Procedure:**

```bash
# 1. Backup current references
cp -r data/drift_references data/drift_references_backup_$(date +%Y%m%d)

# 2. Clear specific reference
rm data/drift_references/quality_score.json

# 3. Generate new reference from recent data
poetry run python -c "
from image_preprocessing_detector.drift import (
    create_tracker, create_drift_detector
)

tracker = create_tracker()
# Load recent representative samples into tracker
# tracker.add_sample(...)

detector = create_drift_detector('data/drift_references')
detector.create_reference_from_tracker(tracker, 'quality_score', min_samples=1000)
"
```

### How do I disable alerting temporarily?

**For maintenance:**

```python
# Use dry-run mode
config = AlertConfig(dry_run=True)
```

**For specific features:**

```python
# Exclude features from monitoring
# (requires code change - consider adding exclusion list)
```

**Important:** Document all temporary disables and set reminder to re-enable.

---

## Alert-Specific FAQ

### KL Divergence Alerts

**Q: What KL value is "normal"?**

A: For stable systems:

- < 0.05: Excellent stability
- 0.05-0.15: Normal variation
- 0.15-0.30: Requires attention
- > 0.30: Significant drift

**Q: Why is KL divergence asymmetric?**

A: KL(P||Q) measures how P differs from reference Q. The values KL(P||Q) and KL(Q||P) can be very different. We use KL(current||reference) to detect when current data deviates from the expected reference.

### PSI Alerts

**Q: What's the difference between PSI and KL?**

A: PSI is symmetric and commonly used in credit risk for population stability. KL is asymmetric and from information theory. Both detect distribution shifts but PSI is easier to interpret.

**Q: Why do we monitor both?**

A: Different metrics catch different types of drift. Using both provides more robust detection.

### Performance Alerts

**Q: How often is evaluation run?**

A: By default, every 24 hours. Can be configured via `evaluation_interval_hours` in job config.

**Q: What dataset is used for evaluation?**

A: The "change detection set" - a held-out dataset representative of production traffic. Should be refreshed quarterly.

---

## Contact & Escalation

**For urgent issues:**

- Slack: #imgprep-alerts
- On-call: See PagerDuty schedule

**For non-urgent questions:**

- Slack: #imgprep-support
- Documentation: This FAQ and related docs

**To suggest FAQ updates:**

- Create a PR updating this file
- Or post in #imgprep-support
