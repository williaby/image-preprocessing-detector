---
schema_type: common
title: "Level 2: Production Runtime"
description: "Detailed production runtime workflow diagrams for Project A"
tags:
- architecture
- diagrams
- plantuml
- level_2
- production_runtime
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the detailed production runtime workflows including device selection,
  primary workflow, and processing details."
---

# Level 2: Production Runtime

This level provides detailed diagrams for the Production Runtime workstream - the live document processing pipeline.

---

## Device Selection Flow

How the system selects the optimal inference device (Local GPU, Modal GPU, or CPU) based on availability, budget, and document characteristics.

![Device Selection Flow](project-a-device-selection-flow.svg)

---

## Primary Workflow - High Level

High-level view of the document processing pipeline from ingestion to output.

![Primary Workflow High Level](project-a-primary-workflow-high-level.svg)

---

## Primary Workflow - Detailed

Detailed activity diagram showing every step in the document processing pipeline.

![Primary Workflow Detailed](project-a-primary-workflow-detailed.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Device Orchestrator | `src/utils/device_orchestrator.py` | Device selection and fallback |
| Ingestion | `src/ingestion/` | PDF/image loading and DPI handling |
| Text Gate | `src/detection/text_gate.py` | Fast text presence detection |
| Classical IQA | `src/detection/iqa_classical.py` | 7 classical CV detectors |
| ML IQA | `src/detection/iqa_ml.py` | Teacher-student ResNet models |
| Layout Detection | `src/detection/layout_lite.py` | DocLayout-YOLO (11 classes) |
| Corrections | `src/correction/` | Deskew, CLAHE, denoising |
| DQS Calculator | `src/metrics/dqs_calculator.py` | Document Quality Score |
| Routing | `src/routing/` | OCR strategy recommendation |

---

## Pipeline State Machine

The production runtime processes documents through a series of well-defined states with explicit entry/exit conditions, timeouts, and error handling.

### Processing States

| State | Entry Condition | Exit Condition | Timeout | Fallback |
|-------|----------------|----------------|---------|----------|
| **INGESTION** | PDF/image received | Pages extracted to 300 DPI | 30s | Abort document |
| **PREFLIGHT** | Pages extracted | DPI analyzed, upscaling complete (if needed) | 15s | Skip upscaling |
| **PDF_CLASSIFICATION** | Preflight complete | PDF type determined (image_only/born_digital/hybrid) | 10s | Default to image_only |
| **TEXT_GATE** | Classification complete | Text presence determined | 10s | Default to TEXT_DETECTED |
| **CLASSICAL_IQA** | Text gate: NO_TEXT or TEXT_DETECTED | Classical detectors complete (8 detectors) | 30s | Skip failed detectors |
| **LAYOUT_LITE** | Text gate: TEXT_DETECTED | Layout classification complete (11 classes) | 60s | Skip layout, use text-gate-only routing |
| **ML_IQA_STUDENT** | IQA route determined | Student inference complete | 100s | Fallback to classical only |
| **UNCERTAINTY_CHECK** | Student inference complete | Uncertainty evaluated (entropy, discrepancy) | 5s | Skip teacher |
| **ML_IQA_TEACHER** | High uncertainty/discrepancy detected | Teacher inference complete | 200s | Use student prediction |
| **CORRECTION** | IQA complete (classical + ML) | Corrections applied (deskew, CLAHE, etc.) | 50s | Skip corrections, flag in metadata |
| **DQS_CALCULATION** | Corrections complete | Document Quality Score computed | 10s | Default DQS = 0.5 |
| **ROUTING** | DQS computed | Routing recommendation generated | 5s | Default to OCR_ADVANCED |
| **OUTPUT** | Routing complete | JSON + images serialized to GCS | 10s | Abort document |

### State Transition Rules

**Happy Path (Text Detected, GPU Available)**:

```text
INGESTION → PREFLIGHT → PDF_CLASSIFICATION → TEXT_GATE (TEXT_DETECTED) →
CLASSICAL_IQA → LAYOUT_LITE → ML_IQA_STUDENT → UNCERTAINTY_CHECK (low) →
CORRECTION → DQS_CALCULATION → ROUTING → OUTPUT
```

**Fallback Path (No Text, CPU Only)**:

```text
INGESTION → PREFLIGHT → PDF_CLASSIFICATION → TEXT_GATE (NO_TEXT) →
CLASSICAL_IQA → ML_IQA_STUDENT (CPU) → CORRECTION → DQS_CALCULATION → ROUTING → OUTPUT
```

**Error Recovery Path (Student Fails, Teacher Escalation)**:

```text
INGESTION → ... → ML_IQA_STUDENT (TIMEOUT) → UNCERTAINTY_CHECK (high) →
ML_IQA_TEACHER (Modal GPU) → CORRECTION → DQS_CALCULATION → ROUTING → OUTPUT
```

### Timeout Behavior

**Per-State Timeouts**:

- Short operations (< 15s): Text gate, PDF classification, DQS calculation
- Medium operations (30-60s): Classical IQA, corrections, layout detection
- Long operations (100-200s): ML IQA student/teacher inference

**Total Pipeline Timeout**:

- **Target**: < 150ms/page (GPU) or < 500ms/page (CPU)
- **Maximum**: 600s total per document (abort if exceeded)

**Timeout Escalation**:

1. First timeout: Log warning, continue to next state with fallback
2. Second timeout in same document: Increment error count
3. Third timeout: Abort document, return partial results with error metadata

---

## Error Handling & Recovery

### Error Classification

| Category | Severity | Recovery Strategy | Examples |
|----------|----------|-------------------|----------|
| **TRANSIENT** | Low | Retry with exponential backoff (max 3 attempts) | Network timeout, Modal GPU temporary unavailability |
| **RESOURCE** | Medium | Fallback device, reduce batch size | GPU OOM, Modal budget exhausted |
| **DATA** | High | Skip page/element, log for review | Corrupted PDF page, invalid image format |
| **CRITICAL** | Critical | Abort document, alert | Missing model file, configuration error |

### Retry Logic

**Exponential Backoff with Jitter**:

```python
# Retry delays: 1s, 2s, 4s (max 3 attempts)
base_delay = 1.0
max_retries = 3

for attempt in range(max_retries):
    try:
        result = process_page()
        break
    except TransientError as e:
        if attempt < max_retries - 1:
            jitter = random.uniform(0.8, 1.2)  # ±20% jitter
            delay = base_delay * (2 ** attempt) * jitter
            time.sleep(delay)
        else:
            handle_permanent_failure(e)
```

**Purpose of Jitter**: Prevents thundering herd when multiple workers retry simultaneously

### Circuit Breaker Pattern (Modal GPU)

**States**:

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures (5 consecutive), block requests for 60s
- **HALF_OPEN**: After 60s timeout, allow 1 test request

**Configuration**:

```python
CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 consecutive failures
    timeout_seconds=60,       # Stay open for 60s
    success_threshold=2       # Require 2 successes to close from HALF_OPEN
)
```

**Integration**: DeviceOrchestrator uses circuit breaker for Modal GPU fallback decisions

### Partial Failure Handling

**Principle**: Process as many pages as possible, flag failures in metadata

**Page-Level Failures**:

```json
{
  "page_number": 42,
  "status": "failed",
  "error": {
    "category": "DATA",
    "code": "CORRUPTED_IMAGE",
    "message": "Failed to decode image data",
    "timestamp": "2025-01-16T10:30:00Z"
  },
  "fallback_used": false
}
```

**Document-Level Thresholds**:

- **< 10% pages failed**: Continue processing, flag failed pages
- **10-50% pages failed**: Complete processing, set document `status: "partial_success"`
- **> 50% pages failed**: Abort document, set `status: "failed"`

### Error Telemetry

**Prometheus Metrics**:

- `iqa_errors_total{error_code, category}`: Error counters by type
- `iqa_retry_attempts_total{reason}`: Retry attempt tracking
- `iqa_circuit_breaker_state{service}`: Circuit breaker state (0=closed, 1=open, 2=half_open)

**Structured Logging**:

```python
logger.error(
    "ml_iqa_timeout",
    page_number=42,
    timeout_seconds=100,
    device="modal_gpu",
    retry_attempt=2,
    trace_id=trace_id
)
```

---

## Device Orchestration

### Device Priority Algorithm

**Decision Tree** (from `src/utils/device_orchestrator.py`):

```text
1. Check Local GPU Available?
   ├─ YES: Check Local GPU Memory > 4GB?
   │   ├─ YES: Use Local GPU ✅
   │   └─ NO: Check Modal GPU Available?
   │       ├─ YES: Check Budget Remaining?
   │       │   ├─ YES: Use Modal GPU ✅
   │       │   └─ NO: Use CPU (budget exhausted) ⚠️
   │       └─ NO: Use CPU (Modal unavailable) ⚠️
   └─ NO: Check Modal GPU Available?
       ├─ YES: Check Budget Remaining?
       │   ├─ YES: Use Modal GPU ✅
       │   └─ NO: Check Policy Allow CPU?
       │       ├─ YES: Use CPU ⚠️
       │       └─ NO: BLOCK (fail fast) ❌
       └─ NO: Check Policy Allow CPU?
           ├─ YES: Use CPU ⚠️
           └─ NO: BLOCK (fail fast) ❌
```

### Budget Enforcement (Three Tiers)

**Budget Configuration**:

```python
BudgetConfig(
    per_document_limit_usd=0.05,    # $0.05 per document
    per_batch_limit_usd=5.00,       # $5.00 per batch job
    monthly_limit_usd=30.00         # $30/month total
)
```

**Enforcement Points**:

1. **Pre-Request Check**: Before Modal GPU invocation
2. **Post-Request Update**: Increment spend tracking
3. **Budget Exhaustion**: Automatic fallback to CPU or BLOCK (policy-dependent)

**Cost Tracking**:

- T4 GPU: $0.000072/second (~$0.0043/minute)
- A10 GPU: $0.000126/second (~$0.0076/minute)
- Typical inference: 10s/page × $0.00072 = $0.0072/page

### Performance Characteristics by Device

| Device | Latency (Student) | Latency (Teacher) | Throughput | Cost/Page |
|--------|------------------|-------------------|------------|-----------|
| **Local GPU (T4)** | 10-25ms | 30-50ms | 40-100 pages/sec | $0.00 (free) |
| **Modal GPU (T4)** | 15-30ms | 40-60ms | 30-65 pages/sec | $0.007 |
| **CPU (Local)** | 40-100ms | 150-300ms | 10-25 pages/sec | $0.00 (free) |

**Policy Recommendations**:

- **Development**: CPU allowed (cost = $0)
- **Staging**: Modal GPU allowed (budget = $30/month)
- **Production**: Prefer Local GPU, Modal GPU allowed with high budget, CPU BLOCKED (quality enforcement)

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **None** | N/A | Production Runtime is the entry point for live processing |

**Note**: Production Runtime is independent during operation but consumes trained models from Workstream 2:

- Student model (ResNet-18): Production inference
- Teacher model (ResNet-50): Selective escalation
- Layout model (YOLOv10-doc): Layout-lite detection

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **Project B (Unify)** | `DocumentMetadata.json`, corrected page images (PNG) | OCR orchestration input |
| **Workstream 7 (Monitoring & Drift)** | Predictions, quality scores, latency metrics | Drift detection, active learning sample harvesting |

### External Dependencies

| Service/Tool | Purpose | Configuration | Fallback |
|--------------|---------|---------------|----------|
| **Modal GPU** | Serverless GPU inference (teacher escalation) | T4/A10, $30/month budget | CPU inference |
| **Local GPU** | Primary inference device | CUDA 12.1+, 4GB+ VRAM | Modal or CPU |
| **GCS Bucket** | Artifact storage (inputs, outputs) | `gs://rag-pipeline-prod/` | Local filesystem (dev) |
| **Prometheus** | Metrics collection | Port 9090 | Logs only |

---

## Processing Modes

### Mode 1: No-Text Path (Classical CV Heavy)

**Trigger**: Text Gate detects NO_TEXT (pure image content)

**Pipeline**:

```text
Ingestion → Preflight → PDF Classification → Text Gate (NO_TEXT) →
Classical IQA (8 detectors) → Student ML IQA → Correction → DQS → Routing → Output
```

**Characteristics**:

- **Skip**: Layout-lite detection (no text to layout)
- **Focus**: Visual degradations (blur, noise, contrast, skew)
- **Performance**: ~100-150ms/page (GPU) or ~300-400ms/page (CPU)

**Routing Strategy**: Heavy bias toward `VISION_SIMPLE` or `VISION_STRUCTURED` (OCR not primary concern)

---

### Mode 2: Text-Detected Path (Layout + Hybrid IQA)

**Trigger**: Text Gate detects TEXT_DETECTED

**Pipeline**:

```text
Ingestion → Preflight → PDF Classification → Text Gate (TEXT_DETECTED) →
Classical IQA → Layout-Lite (11 classes) → Student ML IQA (full page + embedded elements) →
Uncertainty Check → [Teacher if needed] → Correction → DQS → Routing → Output
```

**Characteristics**:

- **Include**: Layout-lite for coarse page attributes
- **Hybrid IQA**: Full-page quality + per-element quality for figures/tables
- **Performance**: ~150-250ms/page (GPU) or ~400-600ms/page (CPU)

**Routing Strategy**: Balanced between OCR_FAST/ADVANCED and VISION strategies based on DQS + structural complexity

---

### Mode 3: Teacher Escalation (High Uncertainty)

**Triggers** (from `src/detection/iqa_ml.py`):

1. **High Entropy**: Student prediction entropy > 0.7
2. **Low Confidence**: Student max probability < 0.5
3. **Boundary Cases**: Quality score in [0.4, 0.6] (ambiguous range)
4. **Discrepancy**: Classical vs ML IQA disagreement > 0.2

**Escalation Flow**:

```text
Student Prediction: quality=0.55, entropy=0.82
    ↓
Uncertainty Check: entropy > 0.7 → ESCALATE
    ↓
Device Selection: Local GPU available? NO → Modal GPU? YES → Use Modal GPU
    ↓
Teacher Inference: quality=0.48, entropy=0.35
    ↓
Reconciliation: Use teacher prediction (higher confidence)
```

**Performance Impact**:

- **Escalation Rate**: Typically 5-15% of pages
- **Latency Increase**: +30-50ms (Local GPU) or +40-60ms (Modal GPU)
- **Cost**: $0.007/page for Modal GPU escalation

---

## Error Handling Patterns

### Category 1: Transient Errors

**Examples**:

- Network timeout to Modal GPU
- Temporary GCS unavailability
- Redis connection lost (Celery workers)

**Recovery**:

```python
@retry(
    max_attempts=3,
    backoff=exponential_backoff(base=1.0, jitter=0.2),
    retry_on=[NetworkTimeout, ConnectionError]
)
def invoke_modal_gpu(image: np.ndarray) -> Prediction:
    """Invoke Modal GPU with automatic retry."""
    ...
```

**Metrics**: `iqa_retry_attempts_total{reason="network_timeout"}`

---

### Category 2: Resource Errors

**Examples**:

- GPU out of memory (OOM)
- Modal GPU budget exhausted
- Worker pool saturation

**Recovery**:

```python
try:
    prediction = student_model.predict_gpu(image, batch_size=32)
except GPUOutOfMemory:
    logger.warning("gpu_oom", device="local", batch_size=32)
    # Reduce batch size and retry
    prediction = student_model.predict_gpu(image, batch_size=8)
except BudgetExhausted:
    logger.warning("modal_budget_exhausted", spent_usd=30.00)
    # Fallback to CPU
    prediction = student_model.predict_cpu(image)
```

**Metrics**: `iqa_device_fallback_total{from="local_gpu", to="cpu", reason="oom"}`

---

### Category 3: Data Errors

**Examples**:

- Corrupted PDF page
- Invalid image format
- Zero-size image after extraction

**Recovery**: Skip page, log for review, continue processing remaining pages

```python
for page_num, page_image in enumerate(pages):
    try:
        result = process_page(page_image)
        results.append(result)
    except CorruptedImageError as e:
        logger.error("corrupted_page", page_number=page_num, trace_id=trace_id)
        results.append(PageMetadata(
            page_number=page_num,
            status="failed",
            error=ErrorInfo(category="DATA", code="CORRUPTED_IMAGE", message=str(e))
        ))
        continue  # Skip to next page
```

**Document-Level Decision**:

- If failed_pages / total_pages > 0.5: Set `document.status = "failed"`
- Else: Set `document.status = "partial_success"`

**Metrics**: `iqa_pages_failed_total{error_code="CORRUPTED_IMAGE"}`

---

### Category 4: Critical Errors

**Examples**:

- Missing model checkpoint file
- Configuration error (invalid DQS weights)
- Unrecoverable service failure

**Recovery**: Abort document immediately, alert

```python
try:
    student_model = load_model("models/resnet18_student.onnx")
except FileNotFoundError:
    logger.critical("missing_model_file", model="student", path="models/resnet18_student.onnx")
    # Alert to PagerDuty/Slack
    alert_manager.dispatch(
        AlertType.CRITICAL_ERROR,
        message="Student model file missing - service degraded"
    )
    # Abort all processing until resolved
    raise CriticalServiceError("Cannot operate without student model")
```

**Metrics**: `iqa_critical_errors_total{error_code="MISSING_MODEL"}`

---

## Performance Optimization Patterns

### Batch Processing

**Strategy**: Process multiple pages in single GPU call for higher throughput

**Implementation**:

```python
# Batch pages for GPU inference
batch_size = 32 if device == "gpu" else 8
for batch_start in range(0, len(pages), batch_size):
    batch = pages[batch_start : batch_start + batch_size]
    predictions = student_model.predict_batch(batch)
```

**Benefits**:

- **GPU Throughput**: 40-100 pages/sec (vs 10-25 single-page)
- **Amortized Overhead**: Model load/unload cost spread across batch
- **Memory Efficiency**: Tensor caching for repeated operations

### Tensor Caching

**Hot Path**: Reuse allocated tensors across pages

```python
# Allocate once, reuse for entire document
input_tensor = torch.zeros((batch_size, 3, 224, 224), device="cuda")

for batch in batches:
    # Reuse pre-allocated tensor (no new GPU memory allocation)
    input_tensor[:len(batch)] = preprocess_images(batch)
    predictions = model(input_tensor[:len(batch)])
```

**Memory Savings**: 50-70% reduction in GPU memory allocations

### Async I/O (Phase 5)

**Current**: Synchronous GCS upload after all processing complete
**Future**: Async upload while processing continues

```python
# Phase 5: Upload corrected images asynchronously
upload_task = asyncio.create_task(
    upload_to_gcs(corrected_image, gcs_uri)
)

# Continue processing while upload happens in background
next_page_result = process_next_page()

# Wait only at document completion
await upload_task
```

**Benefit**: 10-20% latency reduction for multi-page documents

---

## Integration with Model Registry

### Model Loading

**Source**: Models trained in Workstream 2, validated in Workstream 6

**Registry Structure**:

```text
gs://image-detection-models/production/
├── student/
│   ├── resnet18_v1.0.0.onnx         # Primary inference
│   ├── resnet18_v1.0.0.pt           # TorchScript fallback
│   └── resnet18_v1.0.0_metadata.json
└── teacher/
    ├── resnet50_v1.0.0.onnx
    └── resnet50_v1.0.0_metadata.json
```

**Metadata Schema**:

```json
{
  "model_id": "resnet18_v1.0.0",
  "architecture": "ResNet-18",
  "training_date": "2025-01-10",
  "arena_plcc": 0.68,
  "arena_ci_lower": 0.65,
  "arena_ci_upper": 0.71,
  "graduation_date": "2025-01-12",
  "approved_by": "ml_team",
  "production_deployed": true
}
```

**Loading at Runtime**:

```python
from image_preprocessing_detector.utils.model_loader import load_production_model

# Load latest validated model
student = load_production_model(
    model_type="student",
    backend="onnx",
    device="cuda"
)
```

---

## Monitoring Integration (Workstream 7)

### Real-Time Metrics Emission

**During Processing**:

```python
from image_preprocessing_detector.metrics import get_metrics_collector

metrics = get_metrics_collector()

# After each page
metrics.record_page_processed(
    status="success",
    gate_result="text_detected",
    latency_ms=42.5,
    device="local_gpu"
)

# After IQA inference
metrics.record_quality_score(0.72, dimension="overall")
metrics.record_inference_latency(15.3, model="student", device="local_gpu")

# If teacher escalation
if escalated:
    metrics.record_teacher_invocation(reason="high_entropy", device="modal_gpu")
```

### Active Learning Sample Harvesting

**Harvest Triggers** (from Workstream 7 `drift/active_learning.py`):

1. **High Entropy**: Student entropy > 0.7
2. **Low Agreement**: Teacher-student gap > 0.15
3. **Quality Outlier**: Quality score < 0.2 or > 0.95
4. **Drift Period**: Sample during detected drift window

**Sampling Rate**: 10% of flagged pages (reservoir sampling to limit storage)

**Output**: Images sent to Workstream 7 for privacy review → retraining dataset

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project pipeline context |
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Model Training](../model-training/index.md) | Training pipeline |
| **Level 2** | [Monitoring & Drift](../monitoring-drift/index.md) | Continuous improvement integration |
| **Level 2** | [Model Arena](../model-arena/index.md) | Model validation and graduation |

---

## Level 3 Assessment

**Recommendation**: **Level 3 REQUIRED** (Unanimous agreement from multi-model consensus)

**Rationale**:

- **15,000+ lines of production code** - Largest codebase in Project A
- **Mission-critical pipeline** - Core business logic for document processing
- **Complex state management** - 13 states with intricate error handling
- **Device orchestration** - Multi-tier fallback with budget enforcement

**Planned Level 3 Documentation**:

1. **Pipeline State Machine & Error Handling** (`level-3/production-runtime/pipeline-state-machine.md`)
   - Full state diagram with transitions
   - Error recovery flows
   - Edge case handling
2. **DeviceOrchestrator Internals** (`level-3/production-runtime/device-orchestrator.md`)
   - Device selection algorithm details
   - Budget enforcement implementation
   - Circuit breaker state machine

See [ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md](../../ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md) Issues 4.3 and 4.4 for implementation timeline.

---

## Source Files & Traceability

### Workflow Step → Source File Mapping

| Workflow Step | Source Files | LOC | Total | Status |
|---------------|--------------|-----|-------|--------|
| **Ingestion & Preflight** | ingestion/**init**.py, document_processor.py, pdf_loader.py, image_loader.py, office_processor.py, pdf_analyzer.py, pdf_resolution.py, pdf_upscaler.py | 45, 303, 265, 280, 492, 256, 264, 330 | 2,235 | ✅ Complete (Phases 0, 1, 1B) |
| **Classification** | classification/**init**.py, pdf_type_classifier.py, pdf_image_detector.py, pdf_text_extractor.py | 21, 135, 194, 122 | 472 | ✅ Complete (Phase 2) |
| **Text Gate** | detection/text_gate.py | 334 | 334 | ✅ Complete (Phase 1) |
| **Classical IQA** | detection/**init**.py, detection/iqa_classical.py, detection/advanced_detectors.py, detection/discrepancy.py, detection/orientation_detector.py | 190, 2844, 892, 786, 608 | 5,320 | ✅ Complete (Phases 1, 1C) |
| **Layout-Lite** | detection/doclayout_yolo.py, detection/layout_lite/* (12 files) | 801, 1808 | 2,609 | ✅ Complete (Phase 2) |
| **ML IQA** | detection/iqa_ml.py, detection/hybrid_iqa.py | 1303, 351 | 1,654 | ✅ Complete (Phase 3) |
| **Correction** | correction/**init**.py, correction/corrections.py | 62, 1222 | 1,284 | ✅ Complete (Phase 1) |
| **DQS & Routing** | metrics/**init**.py, metrics/dqs_calculator.py, routing/**init**.py, routing/recommendation_engine.py | 49, 1369, 10, 140 | 1,568 | ✅ Complete (Phase 2) |
| **Output** | output/**init**.py, output/json_generator.py | 17, 486 | 503 | ✅ Complete (Phase 0, 2) |
| **Device Orchestration** | utils/device_probe.py | 183 | 183 | ⚠️ In Progress (Phase 4 - 98% complete) |
| **Workers** | workers/**init**.py, workers/celery_app.py, workers/tasks.py | 27, 250, 471 | 748 | ✅ Complete (Phase 4) |

**Workstream Total**: 16,910 lines ✅ (matches LOC extraction)

**Validation**: All files listed in traceability table match [FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md](../../FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md#ws1-production-runtime)

---

## Related Documentation

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project pipeline context |
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Model Training](../model-training/index.md) | Training pipeline |
| **Level 3** | [Pipeline State Machine](../../level-3/production-runtime/pipeline-state-machine.md) | Complete state machine specification |
| **Level 3** | [Device Orchestrator](../../level-3/production-runtime/device-orchestrator.md) | Device selection and budget enforcement |
| **Level 3** | [Production Runtime Swimlane](../../level-3/production-runtime/production-runtime-swimlane.puml) | Detailed swimlane with LOC annotations |
