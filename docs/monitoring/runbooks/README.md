---
schema_type: common
title: "Runbooks Index"
description: "Index of operational runbooks for alert response"
tags:
  - guide
  - monitoring
  - infrastructure
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Provide index to operational runbooks for alert response."
---

This directory contains operational runbooks for responding to alerts from the Image Preprocessing Detector service.

## Alert Categories

| Category | Alerts | Severity | On-Call |
|----------|--------|----------|---------|
| [Latency](./latency.md) | High latency, model slowness | Warning/Critical | Platform Team |
| [Errors](./errors.md) | Error rate spikes, processing failures | Warning/Critical | Platform Team |
| [Infrastructure](./infrastructure.md) | GPU, workers, queue | Warning/Critical | Platform Team |
| [Model](./model.md) | Escalation rate, drift | Warning | ML Team |
| [Cost](./cost.md) | Budget, GPU usage | Warning/Critical | Platform Team |

## Escalation Policy

### Severity Levels

| Level | Response Time | Notification | Action |
|-------|---------------|--------------|--------|
| **Critical** | 5 minutes | PagerDuty + Slack #alerts-critical | Immediate investigation |
| **Warning** | 30 minutes | Slack #alerts | Investigate during business hours |
| **Info** | Next business day | Slack #monitoring | Review in weekly meeting |

### On-Call Rotation

- **Primary**: Platform Team (rotating weekly)
- **Secondary**: ML Team (for model-specific issues)
- **Escalation**: Engineering Manager after 30 min without acknowledgment

### Contact Channels

| Channel | Purpose |
|---------|---------|
| #alerts-critical | Critical alerts, immediate response |
| #alerts | Warning alerts |
| #imgprep-ops | General operations discussion |
| PagerDuty | Critical after-hours alerts |

## Quick Reference

### Common Commands

```bash
# Check service health
docker ps --filter name=imgprep

# View recent logs
docker logs imgprep-worker --tail=100

# Restart workers
docker restart imgprep-worker

# Scale workers
docker compose up -d --scale imgprep-worker=4

# Check queue depth
curl -s http://imgprep:8000/metrics | grep imgprep_queue_depth

# Disable teacher model (emergency)
export IMGPREP_TEACHER_ENABLED=false
docker restart imgprep-worker
```

### Dashboard Links

- [System Overview](https://grafana.internal/d/imgprep-system)
- [Application Metrics](https://grafana.internal/d/imgprep-app)
- [Model Performance](https://grafana.internal/d/imgprep-model)
- [Cost Tracking](https://grafana.internal/d/imgprep-cost)

## Runbook Template

When creating new runbooks, use this template:

```markdown
# Alert Name

## Overview
Brief description of what triggers this alert.

## Impact
What user or system impact does this indicate?

## Investigation Steps
1. Step one
2. Step two

## Resolution
Actions to resolve the issue.

## Prevention
How to prevent recurrence.
```
