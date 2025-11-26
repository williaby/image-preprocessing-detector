---
schema_type: common
title: "ADR-0036: Device Priority Enforcement and Budgets"
description: "Architecture decision for device priority ordering and cost control"
tags:
  - adr
  - architecture
  - performance
  - production
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document device priority enforcement strategy for GPU/CPU/Modal inference."
---

## Status

**Accepted**

## Context

Project A's ML inference must operate across heterogeneous environments:

- Local GPU (development, GPU-enabled production)
- Local CPU (most production deployments)
- Modal GPU (fallback for teacher model)

Without explicit device priority rules, we risk:

1. **Cost overruns**: Unnecessary Modal GPU calls
2. **Latency surprises**: CPU teacher inference taking >500ms
3. **Silent failures**: GPU requested but unavailable
4. **Inconsistent behavior**: Different results across environments

We need a deterministic device selection policy that:

- Prioritizes cost-effective local resources
- Blocks expensive/slow operations by default
- Provides clear override mechanisms
- Enforces budget limits

## Decision

**Implement a strict device priority hierarchy** with explicit blocking policies and budget enforcement.

### 1. Device Priority Hierarchy

```text
Priority 1: Local GPU (if available and requested)
    ↓ (fallback if unavailable)
Priority 2: Local CPU (default for student model)
    ↓ (fallback if teacher needed and CPU blocked)
Priority 3: Modal GPU (teacher inference only)
    ↓ (if Modal unavailable or budget exceeded)
Priority 4: Error (blocked operation)
```text

### 2. Device Selection Matrix

| Model | prefer_gpu=true | prefer_gpu=false | GPU Unavailable |
|-------|-----------------|------------------|-----------------|
| Student | Local GPU | Local CPU | Local CPU |
| Teacher | Local GPU | **BLOCKED** | Modal GPU |
| Layout-Lite | Local GPU | Local CPU | Local CPU |

### 3. Blocking Policies

#### Teacher on CPU: BLOCKED by Default

**Rationale**: Teacher model (ResNet-50) has unacceptable CPU latency:

- GPU: 15-25ms/page
- CPU: 300-500ms/page (20x slower)

**Default Behavior**:

```python
if need_teacher and not has_gpu and not modal_available:
    raise TeacherBlockedError(
        "Teacher model requires GPU. "
        "Set IMGPREP_ALLOW_TEACHER_CPU=true to override."
    )
```

**Override** (not recommended):

```bash
export IMGPREP_ALLOW_TEACHER_CPU=true
```

#### Modal GPU: Budget-Limited

**Rationale**: Modal costs $0.59-1.10/GPU-hour; unlimited use could exceed budget.

**Limits**:

| Limit | Default | Environment Variable |
|-------|---------|---------------------|
| Daily calls | 1000 | `IMGPREP_MODAL_DAILY_LIMIT` |
| Monthly cost | $30 | `IMGPREP_MODAL_MONTHLY_BUDGET` |
| Per-request timeout | 60s | `IMGPREP_MODAL_TIMEOUT` |

**Enforcement**:

```python
class ModalBudgetEnforcer:
    def can_call(self) -> bool:
        if self.daily_calls >= self.daily_limit:
            logger.warning("Modal daily limit reached")
            return False
        if self.monthly_cost >= self.monthly_budget:
            logger.warning("Modal monthly budget exhausted")
            return False
        return True
```

### 4. Device Selection Implementation

```python
class DeviceSelector:
    """Deterministic device selection with budget enforcement."""

    def select_device(
        self,
        model: ModelType,
        prefer_gpu: bool,
        require_teacher: bool
    ) -> Device:
        # Priority 1: Local GPU
        if prefer_gpu and self.has_local_gpu():
            return Device.LOCAL_GPU

        # Student model: CPU is fine
        if model == ModelType.STUDENT:
            return Device.LOCAL_CPU

        # Teacher model: needs GPU
        if model == ModelType.TEACHER:
            # Priority 2: Check CPU override
            if self.allow_teacher_cpu:
                logger.warning("Teacher running on CPU (slow)")
                return Device.LOCAL_CPU

            # Priority 3: Modal GPU
            if self.modal_available and self.budget_enforcer.can_call():
                return Device.MODAL_GPU

            # Priority 4: Blocked
            raise TeacherBlockedError(
                "Teacher model blocked: no GPU available"
            )

        # Layout-lite: flexible
        return Device.LOCAL_GPU if prefer_gpu else Device.LOCAL_CPU
```

### 5. Latency Budgets

| Operation | Target | Acceptable | Budget Exceeded |
|-----------|--------|------------|-----------------|
| Student GPU | 10ms | 25ms | Log warning |
| Student CPU | 100ms | 200ms | Log warning |
| Teacher GPU | 25ms | 50ms | Log warning |
| Teacher Modal | 200ms | 500ms | Count toward limit |
| Layout-lite | 20ms | 50ms | Log warning |

**Budget Exceeded Action**:

```python
if latency > ACCEPTABLE_LATENCY:
    logger.warning(
        "Latency budget exceeded",
        model=model,
        device=device,
        latency_ms=latency,
        budget_ms=ACCEPTABLE_LATENCY
    )
    metrics.increment("latency_budget_exceeded", tags=[model, device])
```

## Alternatives Considered

### Alternative 1: Automatic Device Selection

**Description**: Always use best available device without user input

**Pros**:

- Simpler API
- Optimal performance when GPU available

**Cons**:

- Unpredictable costs
- Different behavior across environments
- No user control

**Why Rejected**: Cost unpredictability unacceptable for production

### Alternative 2: GPU-Only Deployment

**Description**: Require GPU for all deployments

**Pros**:

- Consistent performance
- No fallback complexity

**Cons**:

- High infrastructure cost
- Excludes CPU-only environments
- Overkill for student-only inference

**Why Rejected**: Violates cost-efficiency principle; student model works well on CPU

### Alternative 3: No Blocking, Just Warnings

**Description**: Allow all operations with warnings for slow paths

**Pros**:

- Maximum flexibility
- No hard failures

**Cons**:

- Users may not notice warnings
- Production issues from slow inference
- Cost overruns

**Why Rejected**: Silent degradation is worse than explicit failure

### Alternative 4: Request-Level Budgets

**Description**: Enforce latency/cost budgets per-request

**Pros**:

- Fine-grained control
- Predictable request costs

**Cons**:

- Complex API
- Difficult to set appropriate limits
- Overhead for budget checking

**Why Rejected**: Complexity not justified; daily/monthly limits sufficient

## Consequences

### Positive

1. **Predictable Costs**: Budget limits prevent overruns
2. **Deterministic Behavior**: Same inputs → same device selection
3. **Clear Failures**: Blocked operations fail fast with helpful messages
4. **Explicit Overrides**: Power users can bypass limits when needed

### Negative

1. **Reduced Flexibility**: Some operations blocked by default
2. **Configuration Burden**: Users must understand device policies
3. **Potential Frustration**: Teacher model unusable without GPU

### Mitigations

| Risk | Mitigation |
|------|------------|
| Confusion about blocking | Clear error messages with override instructions |
| Legitimate high-volume needs | Adjustable limits via environment variables |
| Budget too restrictive | Start generous, tighten based on actual usage |

## Implementation Notes

### Configuration

```python
@dataclass
class DeviceConfig:
    # Local GPU settings
    prefer_gpu: bool = True
    gpu_memory_threshold_gb: float = 2.0

    # CPU fallback settings
    allow_teacher_cpu: bool = False
    cpu_thread_count: int = 4

    # Modal settings
    modal_enabled: bool = True
    modal_daily_limit: int = 1000
    modal_monthly_budget: float = 30.0
    modal_timeout_seconds: int = 60

    # Latency budgets (ms)
    student_gpu_budget: int = 25
    student_cpu_budget: int = 200
    teacher_gpu_budget: int = 50
    teacher_modal_budget: int = 500
```

### Logging

```python
# Device selection logged at INFO level
logger.info(
    "device_selected",
    model=model,
    device=device,
    prefer_gpu=prefer_gpu,
    reason=selection_reason
)

# Budget warnings at WARNING level
logger.warning(
    "approaching_budget_limit",
    limit_type="modal_daily",
    current=950,
    limit=1000
)
```

### Metrics

```python
# Prometheus metrics
device_selections = Counter(
    "imgprep_device_selections_total",
    "Device selections by model and device",
    ["model", "device"]
)

budget_exceeded = Counter(
    "imgprep_budget_exceeded_total",
    "Budget exceeded events",
    ["budget_type"]
)

inference_latency = Histogram(
    "imgprep_inference_latency_seconds",
    "Inference latency by model and device",
    ["model", "device"]
)
```

## References

- [ADR-0020: CPU-First Deployment Strategy](0020-cpu-first-deployment-strategy.md)
- [ADR-0028: ResNet Teacher-Student Architecture](0028-resnet-teacher-student-architecture.md)
- [ADR-0035: Modal GPU Integration](0035-modal-gpu-integration.md)
- [Model Cards: Latency Benchmarks](../reference/MODEL_CARDS.md)
