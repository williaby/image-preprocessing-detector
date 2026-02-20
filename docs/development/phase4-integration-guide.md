---
title: Phase 4 Integration Guide
status: draft
tags: [development, architecture]
owner: "core-maintainer"
purpose: Guide for integrating Phase 4 device orchestration into the ML IQA pipeline.
schema_type: common
---

## Overview

This guide describes how to integrate the Phase 4 device orchestration components (`DeviceOrchestrator` and `ModalClient`) into the existing `iqa_ml.py` pipeline.

**Target Sprint**: 4.1.6 - Gate Wiring (2 hours estimated)

## Current Architecture (Before Integration)

### iqa_ml.py Current State

```python
class MLIQADetector:
    def __init__(
        self,
        student_model_path: str | Path | None = None,
        teacher_model_path: str | Path | None = None,
        device: Device | None = None,  # Single device for both models
        enable_modal_fallback: bool = True,
        entropy_threshold: float = 0.8,
        min_confidence_threshold: float = 0.6,
        mean_confidence_threshold: float = 0.7,
    ):
        self.device = device or self._detect_device()  # One device for everything
        self._student_session = None
        self._teacher_session = None
```

**Issues with Current Approach**:

1. Single `device` parameter for both student and teacher
2. No budget enforcement mechanism
3. No circuit breaker for Modal fallback
4. Manual device detection in `_detect_device()`
5. No separation between local and remote inference

## Proposed Architecture (After Integration)

### Modified MLIQADetector Initialization

```python
from image_preprocessing_detector.orchestration import (
    DeviceOrchestrator,
    DevicePolicyConfig,
    InferenceMode,
    ModalClient,
    CircuitBreakerConfig,
)

class MLIQADetector:
    def __init__(
        self,
        student_model_path: str | Path | None = None,
        teacher_model_path: str | Path | None = None,
        device_policy: DevicePolicyConfig | None = None,
        modal_endpoint: str | None = None,
        # Keep existing uncertainty gate parameters
        entropy_threshold: float = 0.8,
        min_confidence_threshold: float = 0.6,
        mean_confidence_threshold: float = 0.7,
        # Keep existing discrepancy threshold
        discrepancy_threshold: float = 0.3,
    ):
        """Initialize ML IQA detector with device orchestration.

        Args:
            student_model_path: Path to student ONNX model
            teacher_model_path: Path to teacher ONNX model
            device_policy: Device policy configuration (defaults to production mode)
            modal_endpoint: Modal serverless endpoint URL
            entropy_threshold: Entropy threshold for uncertainty gate
            min_confidence_threshold: Min confidence for uncertainty gate
            mean_confidence_threshold: Mean confidence for uncertainty gate
            discrepancy_threshold: Discrepancy threshold for classical comparison
        """
        self.student_model_path = student_model_path
        self.teacher_model_path = teacher_model_path

        # NEW: Device orchestration
        self.device_policy = device_policy or DevicePolicyConfig()
        self.orchestrator = DeviceOrchestrator(config=self.device_policy)

        # NEW: Modal client for remote inference
        if modal_endpoint:
            modal_config = CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=60.0,
            )
            self.modal_client = ModalClient(
                config=modal_config,
                modal_endpoint=modal_endpoint,
            )
        else:
            self.modal_client = None

        # Keep existing uncertainty gate thresholds
        self.entropy_threshold = entropy_threshold
        self.min_confidence_threshold = min_confidence_threshold
        self.mean_confidence_threshold = mean_confidence_threshold
        self.discrepancy_threshold = discrepancy_threshold

        # Lazy-load inference sessions (per-device)
        self._student_sessions: dict[str, Any] = {}  # device -> session
        self._teacher_sessions: dict[str, Any] = {}  # device -> session

        logger.info(
            "ML IQA detector initialized with device orchestration",
            student_model=str(student_model_path) if student_model_path else "None",
            teacher_model=str(teacher_model_path) if teacher_model_path else "None",
            device_mode=self.device_policy.mode.value,
            modal_available=self.modal_client is not None,
        )
```

### Modified run_pipeline Method

```python
def run_pipeline(
    self,
    image: np.ndarray,
    classical_scores: ClassicalIQAScores | None = None,
    doc_id: str | None = None,
) -> tuple[MLIQAScores, MLIQAScores | None]:
    """Run complete ML IQA pipeline with device orchestration.

    Args:
        image: Input image as numpy array
        classical_scores: Classical IQA scores for discrepancy check
        doc_id: Document identifier for budget tracking

    Returns:
        Tuple of (student_scores, teacher_scores)
        teacher_scores is None if not escalated or blocked by budget
    """
    # Step 1: Student inference with device selection
    student_device_choice = self.orchestrator.select_device_for_student()
    if student_device_choice.device is None:
        msg = "No device available for student inference"
        raise RuntimeError(msg)

    student_scores = self._run_student_inference(
        image, device=student_device_choice.device
    )

    logger.debug(
        "Student inference complete",
        device=student_device_choice.device,
        rationale=student_device_choice.rationale,
        inference_time_ms=student_scores.inference_time_ms,
    )

    # Step 2: Decide if teacher escalation needed
    escalation_decision = self._should_escalate_to_teacher(
        student_scores, classical_scores
    )

    if not escalation_decision.should_escalate:
        logger.debug(
            "Teacher escalation not needed",
            uncertainty_metrics=escalation_decision.uncertainty_metrics,
        )
        return (student_scores, None)

    # Step 3: Teacher inference with device selection and budget enforcement
    teacher_device_choice = self.orchestrator.select_device_for_teacher(doc_id=doc_id)

    if teacher_device_choice.device is None:
        # Blocked by budget or policy
        logger.warning(
            "Teacher inference blocked",
            reason=teacher_device_choice.blocked_reason,
            rationale=teacher_device_choice.rationale,
            escalation_reason=escalation_decision.reason,
        )
        return (student_scores, None)

    # Step 4: Execute teacher inference on selected device
    if teacher_device_choice.device == "modal":
        # Remote inference via Modal
        teacher_scores = self._run_modal_teacher_inference(image)
    else:
        # Local inference (GPU or CPU)
        teacher_scores = self._run_teacher_inference(
            image, device=teacher_device_choice.device
        )

    if teacher_scores:
        # Record usage for budget tracking
        self.orchestrator.record_teacher_inference(
            device=teacher_device_choice.device,
            inference_time_ms=teacher_scores.inference_time_ms,
        )

        logger.info(
            "Teacher inference complete",
            device=teacher_device_choice.device,
            rationale=teacher_device_choice.rationale,
            inference_time_ms=teacher_scores.inference_time_ms,
            escalation_reason=escalation_decision.reason,
            estimated_cost_usd=teacher_device_choice.estimated_cost_usd,
        )

    return (student_scores, teacher_scores)
```

### New Helper Methods

```python
def _run_student_inference(
    self, image: np.ndarray, device: str
) -> MLIQAScores:
    """Run student inference on specified device.

    Args:
        image: Input image
        device: Device to use ("cuda" or "cpu")

    Returns:
        ML IQA scores from student model
    """
    # Get or create ONNX session for this device
    if device not in self._student_sessions:
        self._student_sessions[device] = self._load_student_session(device)

    session = self._student_sessions[device]

    # Preprocess image
    input_tensor = self._preprocess_image(image)

    # Run inference
    start_time = time.perf_counter()
    outputs = session.run(None, {"input": input_tensor})
    inference_time_ms = (time.perf_counter() - start_time) * 1000

    # Parse outputs to MLIQAScores
    scores = self._parse_model_outputs(
        outputs,
        model_type=ModelType.STUDENT,
        device=Device.GPU if device == "cuda" else Device.CPU,
        inference_time_ms=inference_time_ms,
    )

    return scores

def _run_teacher_inference(
    self, image: np.ndarray, device: str
) -> MLIQAScores:
    """Run teacher inference on specified local device.

    Args:
        image: Input image
        device: Device to use ("cuda" or "cpu")

    Returns:
        ML IQA scores from teacher model
    """
    # Get or create ONNX session for this device
    if device not in self._teacher_sessions:
        self._teacher_sessions[device] = self._load_teacher_session(device)

    session = self._teacher_sessions[device]

    # Preprocess image
    input_tensor = self._preprocess_image(image)

    # Run inference
    start_time = time.perf_counter()
    outputs = session.run(None, {"input": input_tensor})
    inference_time_ms = (time.perf_counter() - start_time) * 1000

    # Parse outputs to MLIQAScores
    scores = self._parse_model_outputs(
        outputs,
        model_type=ModelType.TEACHER,
        device=Device.GPU if device == "cuda" else Device.CPU,
        inference_time_ms=inference_time_ms,
    )

    return scores

def _run_modal_teacher_inference(
    self, image: np.ndarray
) -> MLIQAScores | None:
    """Run teacher inference on Modal GPU.

    Args:
        image: Input image

    Returns:
        ML IQA scores from teacher model, or None if Modal unavailable
    """
    if self.modal_client is None:
        logger.warning("Modal client not configured")
        return None

    # Create Modal request
    from image_preprocessing_detector.orchestration import ModalInferenceRequest

    request = ModalInferenceRequest(
        image_array=image,
        model_version="v1.0",
        request_id=f"req_{time.time_ns()}",
    )

    # Execute with circuit breaker
    response = self.modal_client.predict(request)

    if response is None:
        logger.warning("Modal inference failed or circuit breaker open")
        return None

    # Convert Modal response to MLIQAScores
    scores = MLIQAScores(
        blur_score=response.scores["blur"],
        noise_score=response.scores["noise"],
        contrast_score=response.scores["contrast"],
        skew_score=response.scores["skew"],
        compression_score=response.scores["compression"],
        overall_quality=sum(response.scores.values()) / len(response.scores),
        confidences=response.confidences,
        model_type=ModelType.TEACHER,
        device=Device.MODAL,
        inference_time_ms=response.inference_time_ms,
    )

    return scores

def _load_student_session(self, device: str) -> Any:
    """Load student ONNX session for specified device.

    Args:
        device: Device to load session for ("cuda" or "cpu")

    Returns:
        ONNX InferenceSession
    """
    if self.student_model_path is None:
        raise ValueError("Student model path not set")

    model_path = Path(self.student_model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Student model not found: {model_path}")

    if ort is None:
        raise RuntimeError("ONNX Runtime not installed")

    # Select providers based on device
    if device == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]

    session = ort.InferenceSession(str(model_path), providers=providers)
    logger.info(
        "Student model loaded",
        path=str(model_path),
        device=device,
        providers=providers,
    )
    return session

def _load_teacher_session(self, device: str) -> Any:
    """Load teacher ONNX session for specified device.

    Args:
        device: Device to load session for ("cuda" or "cpu")

    Returns:
        ONNX InferenceSession
    """
    if self.teacher_model_path is None:
        raise ValueError("Teacher model path not set")

    model_path = Path(self.teacher_model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Teacher model not found: {model_path}")

    if ort is None:
        raise RuntimeError("ONNX Runtime not installed")

    # Select providers based on device
    if device == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]

    session = ort.InferenceSession(str(model_path), providers=providers)
    logger.info(
        "Teacher model loaded",
        path=str(model_path),
        device=device,
        providers=providers,
    )
    return session
```

## Migration Path

### Phase 1: Add Orchestrator (Backward Compatible)

1. Add new parameters to `__init__()` with defaults
2. Keep old `device` parameter functional (deprecated)
3. If `device_policy` is None, use legacy device detection

```python
def __init__(
    self,
    student_model_path: str | Path | None = None,
    teacher_model_path: str | Path | None = None,
    device: Device | None = None,  # DEPRECATED: Use device_policy instead
    device_policy: DevicePolicyConfig | None = None,  # NEW
    modal_endpoint: str | None = None,  # NEW
    # ... existing parameters
):
    if device_policy is None and device is not None:
        # Legacy mode: Use old device parameter
        logger.warning("device parameter is deprecated, use device_policy instead")
        self.legacy_mode = True
        self.device = device
    else:
        # New mode: Use orchestrator
        self.legacy_mode = False
        self.orchestrator = DeviceOrchestrator(config=device_policy or DevicePolicyConfig())
```

### Phase 2: Update run_pipeline (Gradual)

1. Check `self.legacy_mode` flag
2. Route to old or new implementation

```python
def run_pipeline(self, image, classical_scores=None, doc_id=None):
    if self.legacy_mode:
        return self._run_pipeline_legacy(image, classical_scores)
    else:
        return self._run_pipeline_orchestrated(image, classical_scores, doc_id)
```

### Phase 3: Deprecation (3 months)

1. Add deprecation warnings to old parameters
2. Update all tests to use new API
3. Update documentation

### Phase 4: Remove Legacy (6 months)

1. Remove `device` parameter
2. Remove `_run_pipeline_legacy()` method
3. Make `device_policy` required

## Configuration Examples

### Production Mode (Default)

```python
from image_preprocessing_detector.detection.iqa_ml import MLIQADetector
from image_preprocessing_detector.orchestration import (
    DevicePolicyConfig,
    InferenceMode,
)

config = DevicePolicyConfig(
    mode=InferenceMode.PRODUCTION,
    allow_cpu_teacher=False,  # Block CPU teacher
    enable_modal=True,
    teacher_budget_per_doc=10,
    teacher_budget_per_batch=100,
    teacher_budget_monthly_hours=10.0,
)

detector = MLIQADetector(
    student_model_path="models/student.onnx",
    teacher_model_path="models/teacher.onnx",
    device_policy=config,
    modal_endpoint="https://modal.com/...",
)
```

### QA Mode (Allow CPU Teacher)

```python
config = DevicePolicyConfig(
    mode=InferenceMode.QA,
    allow_cpu_teacher=True,  # Allow CPU with warning
    teacher_budget_per_doc=50,  # Higher budget for testing
)

detector = MLIQADetector(
    student_model_path="models/student.onnx",
    teacher_model_path="models/teacher.onnx",
    device_policy=config,
)
```

### Development Mode (No Budgets)

```python
config = DevicePolicyConfig(
    mode=InferenceMode.DEVELOPMENT,
    allow_cpu_teacher=True,
    teacher_budget_per_doc=1000,  # Effectively unlimited
    teacher_budget_per_batch=10000,
)

detector = MLIQADetector(
    student_model_path="models/student.onnx",
    teacher_model_path="models/teacher.onnx",
    device_policy=config,
)
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/detection/test_iqa_ml_orchestration.py

def test_student_inference_with_orchestrator():
    """Test student inference uses orchestrator."""
    config = DevicePolicyConfig(mode=InferenceMode.PRODUCTION)
    detector = MLIQADetector(
        student_model_path="models/student.onnx",
        device_policy=config,
    )

    # Mock orchestrator
    with patch.object(detector.orchestrator, 'select_device_for_student') as mock:
        mock.return_value = DeviceChoice(device="cuda", rationale="GPU available")

        image = np.zeros((224, 224, 3), dtype=np.uint8)
        scores, _ = detector.run_pipeline(image)

        assert mock.called
        assert scores.device == Device.GPU

def test_teacher_budget_enforcement():
    """Test teacher inference respects budget."""
    config = DevicePolicyConfig(
        mode=InferenceMode.PRODUCTION,
        teacher_budget_per_doc=2,
    )
    detector = MLIQADetector(
        student_model_path="models/student.onnx",
        teacher_model_path="models/teacher.onnx",
        device_policy=config,
    )

    image = np.zeros((224, 224, 3), dtype=np.uint8)

    # First 2 pages should get teacher
    for i in range(2):
        _, teacher_scores = detector.run_pipeline(image, doc_id="doc1")
        assert teacher_scores is not None  # Assuming escalation triggers

    # 3rd page should be blocked
    _, teacher_scores = detector.run_pipeline(image, doc_id="doc1")
    assert teacher_scores is None  # Blocked by budget
```

### Integration Tests

```python
# tests/integration/test_device_routing_e2e.py

def test_local_gpu_to_modal_fallback():
    """Test fallback from local GPU to Modal when GPU unavailable."""
    # TODO: Implement E2E test for Sprint 4.2.7
    pass

def test_modal_circuit_breaker_integration():
    """Test circuit breaker behavior in full pipeline."""
    # TODO: Implement E2E test for Sprint 4.2.7
    pass
```

## Rollout Plan

### Week 1: Implementation (Sprint 4.1.6)

- [ ] Add `device_policy` and `modal_endpoint` parameters
- [ ] Implement `_run_pipeline_orchestrated()` method
- [ ] Add per-device session caching
- [ ] Add Modal inference method
- [ ] Maintain backward compatibility

### Week 2: Testing

- [ ] Add unit tests for orchestration integration
- [ ] Add integration tests (Sprint 4.2.7)
- [ ] Test budget enforcement
- [ ] Test circuit breaker behavior
- [ ] Validate performance (no regression)

### Week 3: Documentation

- [ ] Update API documentation
- [ ] Add migration guide
- [ ] Update examples in guides
- [ ] Add troubleshooting section

### Month 2-3: Deprecation

- [ ] Add deprecation warnings
- [ ] Update all existing code to new API
- [ ] Monitor for issues

### Month 4-6: Cleanup

- [ ] Remove legacy parameters
- [ ] Remove backward compatibility code
- [ ] Update all documentation

## Success Criteria

> Legend: [x] = design complete, [ ] = pending implementation/verification

- [x] Orchestrator integrated without breaking existing tests
- [x] Teacher budget enforcement works in production
- [x] Modal fallback works with circuit breaker
- [ ] No performance regression (<5% overhead)
- [ ] All 68 orchestration tests still pass
- [ ] New integration tests pass (Sprint 4.2.7)
- [ ] Documentation complete

## References

- [phase4-implementation-summary.md](phase4-implementation-summary.md) - Implementation status
- [device_orchestrator.py](../../src/image_preprocessing_detector/orchestration/device_orchestrator.py) - Orchestrator implementation
- [modal_client.py](../../src/image_preprocessing_detector/orchestration/modal_client.py) - Modal client
- [iqa_ml.py](../../src/image_preprocessing_detector/detection/iqa_ml.py) - Current implementation

---

**Status**: Planning | **Sprint**: 4.1.6 | **Estimated**: 2 hours
**Next Steps**: Implement backward-compatible integration, then test
