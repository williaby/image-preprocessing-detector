---
schema_type: adr
title: "ADR-0035: Modal GPU Integration Strategy"
tags:
  - architecture
  - modal
  - gpu
  - infrastructure
status: accepted
owner: platform-team
decision_date: 2025-01-15
---

# ADR-0035: Modal GPU Integration Strategy

## Status

**Accepted**

## Context

Project A requires GPU compute for:
1. **Training**: ResNet teacher-student knowledge distillation (~12-24 hours)
2. **Inference**: Teacher model validation on flagged documents (~5% of traffic)

The project operates in environments with varying GPU availability:
- Development machines may have consumer GPUs or none
- Production servers may be CPU-only for cost reasons
- Occasional high-capacity GPU is needed for training and batch processing

We need a strategy that:
- Minimizes infrastructure complexity
- Controls costs (target: <$50/month for steady-state)
- Provides GPU access when needed without dedicated hardware
- Maintains low latency for production inference

## Decision

**Adopt Modal as the serverless GPU platform** for training and fallback inference with the following integration pattern:

### 1. Training Workloads (Primary Use)

All ML training runs on Modal:
- ResNet-50 teacher training
- ResNet-18 student distillation
- Layout-lite model fine-tuning

```python
# modal/train_phase2_iqa.py
@app.function(
    gpu="T4",  # or "A10" for faster training
    timeout=86400,  # 24 hours max
    secrets=[modal.Secret.from_name("gcs-credentials")]
)
def train_teacher_model(config: TrainConfig) -> ModelArtifact:
    ...
```

### 2. Inference Fallback (Secondary Use)

Modal provides GPU inference ONLY when:
- Local GPU unavailable AND
- Teacher model requested AND
- CPU inference blocked (latency >500ms unacceptable)

```python
# Device selection priority
def select_device(prefer_gpu: bool, need_teacher: bool) -> Device:
    if has_local_gpu() and prefer_gpu:
        return Device.LOCAL_GPU
    if not need_teacher:
        return Device.LOCAL_CPU
    if is_modal_available():
        return Device.MODAL_GPU
    if allow_teacher_cpu():
        return Device.LOCAL_CPU
    raise TeacherBlockedError("Teacher requires GPU")
```

### 3. Cost Control Mechanisms

| Control | Implementation |
|---------|----------------|
| Training Budget | Modal spending alerts at $30/month |
| Inference Budget | Max 1000 Modal calls/day |
| Batch Preference | Accumulate flagged docs, batch Modal calls |
| Cold Start Mitigation | Keep-warm disabled (accept cold starts) |

### 4. Secret Management

Modal secrets stored separately from application secrets:
- `gcs-credentials`: GCS service account for model/data storage
- `hf-token`: HuggingFace API token for model registry

```bash
modal secret create gcs-credentials \
  GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat service-account.json)"
```

## Alternatives Considered

### Alternative 1: Dedicated GPU Server

**Description**: Rent dedicated GPU server (e.g., Lambda Labs, Vast.ai)

**Pros**:
- Predictable latency
- No cold starts
- Full control

**Cons**:
- High fixed cost (~$200-500/month for T4)
- Underutilized during off-peak
- Maintenance overhead

**Why Rejected**: Cost exceeds budget for low-volume inference needs

### Alternative 2: Cloud Provider GPU (GCP/AWS)

**Description**: Use GCP Compute Engine or AWS EC2 GPU instances

**Pros**:
- Enterprise reliability
- Integration with other cloud services

**Cons**:
- Complex provisioning
- Minimum 1-hour billing increments
- Higher cost than Modal for sporadic use

**Why Rejected**: Per-second billing of Modal better matches workload pattern

### Alternative 3: CPU-Only with Quantized Models

**Description**: Use INT8 quantized models for CPU-only inference

**Pros**:
- Zero GPU costs
- Simpler deployment

**Cons**:
- 10-15% accuracy degradation
- Still slow for teacher model (~300ms/page)
- Doesn't solve training needs

**Why Rejected**: Accuracy impact unacceptable for teacher validation

### Alternative 4: Colab for Training

**Description**: Use Google Colab for training workloads

**Pros**:
- Free tier available
- Familiar interface

**Cons**:
- Session timeouts (12 hours max)
- Unreliable GPU availability
- Manual intervention required

**Why Rejected**: Session limits incompatible with 24-hour training runs

## Consequences

### Positive

1. **Cost Efficiency**: Pay only for actual GPU seconds used
2. **Scalability**: Automatic scaling for batch processing
3. **Simplicity**: No infrastructure to manage
4. **Flexibility**: Easy to switch GPU tiers (T4 → A10 → A100)

### Negative

1. **Cold Starts**: 5-15 second latency on first call after idle
2. **Vendor Lock-in**: Modal-specific deployment code
3. **Network Dependency**: Requires internet for GPU inference
4. **Debugging Complexity**: Remote execution harder to debug

### Mitigations

| Risk | Mitigation |
|------|------------|
| Cold starts | Batch flagged documents, async processing |
| Vendor lock-in | Abstract Modal behind interface, standard PyTorch models |
| Network issues | Graceful fallback to CPU with warning |
| Debugging | Comprehensive logging, local testing mode |

## Implementation Notes

### Directory Structure

```
modal/
├── train_phase2_iqa.py    # Training entry point
├── inference.py           # Inference functions
├── config.py              # Modal configuration
└── utils/
    ├── gcs.py            # GCS integration
    └── monitoring.py     # Cost tracking
```

### Environment Variables

```bash
# Enable Modal integration
IMGPREP_MODAL_ENABLED=true
IMGPREP_MODAL_APP_NAME=image-detection

# Budget controls
IMGPREP_MODAL_DAILY_INFERENCE_LIMIT=1000
IMGPREP_MODAL_MONTHLY_BUDGET_ALERT=30
```

### Monitoring

```python
# Track Modal usage
@app.function(schedule=modal.Cron("0 0 * * *"))
def daily_cost_report():
    usage = modal.usage.get_daily_usage()
    if usage.cost_usd > BUDGET_THRESHOLD:
        send_alert(f"Modal daily cost ${usage.cost_usd}")
```

## References

- [Modal Documentation](https://modal.com/docs)
- [Modal Pricing](https://modal.com/pricing)
- [ADR-0020: CPU-First Deployment Strategy](0020-cpu-first-deployment-strategy.md)
- [ADR-0028: ResNet Teacher-Student Architecture](0028-resnet-teacher-student-architecture.md)
