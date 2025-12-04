"""ML-based Image Quality Assessment (IQA) using teacher-student ResNet architecture.

This module implements the ML IQA pipeline with:
- Student model (ResNet-18): Fast, default inference
- Teacher model (ResNet-50): High-capacity, used for flagged pages
- Multi-head architecture: blur, noise, contrast, skew, compression
- Device selection: Local GPU → Local CPU → Modal GPU
- ONNX Runtime inference for production

Phase 2 Integration - Milestone 14.2
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from typing import Literal

from image_preprocessing_detector.orchestration import (
    DeviceOrchestrator,
    DevicePolicyConfig,
    ModalClient,
    ModalInferenceRequest,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Optional dependency: onnxruntime (required for ML IQA, not for Phase 0)
try:
    import onnxruntime as ort
except ImportError:
    ort = None


class ModelType(str, Enum):
    """IQA model types (teacher vs student)."""

    STUDENT = "student"
    TEACHER = "teacher"


class Device(str, Enum):
    """Available compute devices for inference."""

    GPU = "cuda"
    CPU = "cpu"
    MODAL = "modal"


@dataclass
class MLIQAScores:
    """Multi-head IQA scores from ML model.

    Attributes:
        blur_score: Blur quality score 0-1 (0=blurry, 1=sharp)
        noise_score: Noise quality score 0-1 (0=noisy, 1=clean)
        contrast_score: Contrast quality score 0-1 (0=low contrast, 1=good contrast)
        skew_score: Skew quality score 0-1 (0=skewed, 1=straight)
        compression_score: Compression artifact score 0-1 (0=artifacts, 1=clean)
        overall_quality: Aggregated quality score 0-1
        confidences: Per-head confidence scores (softmax max)
        model_type: Which model produced these scores (student/teacher)
        device: Device used for inference
        inference_time_ms: Inference latency in milliseconds
    """

    blur_score: float
    noise_score: float
    contrast_score: float
    skew_score: float
    compression_score: float
    overall_quality: float
    confidences: dict[str, float]
    model_type: ModelType
    device: Device
    inference_time_ms: float


@dataclass
class UncertaintyMetrics:
    """Uncertainty metrics for teacher escalation decisions.

    Attributes:
        entropy: Softmax entropy across heads (higher = more uncertain)
        min_confidence: Minimum confidence across all heads
        mean_confidence: Average confidence across heads
        head_confidences: Per-head confidence scores
    """

    entropy: float
    min_confidence: float
    mean_confidence: float
    head_confidences: dict[str, float]


@dataclass
class EscalationDecision:
    """Decision whether to escalate to teacher model.

    Attributes:
        should_escalate: Whether to escalate to teacher
        reason: Reason for escalation (or None if not escalating)
        uncertainty_metrics: Calculated uncertainty metrics
    """

    should_escalate: bool
    reason: str | None
    uncertainty_metrics: UncertaintyMetrics


@dataclass
class ClassicalIQAScores:
    """Classical IQA scores for comparison with ML IQA.

    Normalized to 0-1 scale where 1=good quality, 0=poor quality.
    All scores are continuous [0.0, 1.0] to enable quantitative discrepancy analysis.

    Attributes:
        blur_score: Blur quality (from Laplacian variance, normalized)
        contrast_score: Contrast quality (from histogram analysis)
        skew_score: Skew quality (1 - normalized_angle)
        noise_score: Noise quality (0=noisy, 1=clean) - replaces has_noise boolean
        illumination_score: Illumination quality (0=poor lighting, 1=good lighting)
        compression_score: Compression artifact quality (0=artifacts, 1=clean) - replaces has_compression boolean
        binarization_score: Binarization quality (0=poor, 1=good) - document-specific
        bleed_through_score: Bleed-through quality (0=severe, 1=none) - document-specific
    """

    # Core dimensions (required)
    blur_score: float
    contrast_score: float
    skew_score: float

    # ML IQA aligned dimensions (optional with defaults for backward compatibility)
    noise_score: float = 0.0
    illumination_score: float = 0.0
    compression_score: float = 0.0

    # Document-specific dimensions (optional)
    binarization_score: float = 0.0
    bleed_through_score: float = 0.0

    def __post_init__(self) -> None:
        """Validate all scores are in [0.0, 1.0] range."""
        score_fields = [
            "blur_score",
            "contrast_score",
            "skew_score",
            "noise_score",
            "illumination_score",
            "compression_score",
            "binarization_score",
            "bleed_through_score",
        ]

        for field_name in score_fields:
            score = getattr(self, field_name)
            if not (0.0 <= score <= 1.0):
                msg = f"{field_name} must be in [0.0, 1.0], got {score}"
                raise ValueError(msg)


@dataclass
class DiscrepancyMetrics:
    """Discrepancy metrics between student ML IQA and classical IQA.

    All discrepancies are absolute differences in [0.0, 1.0] range.

    Attributes:
        blur_discrepancy: Absolute difference in blur scores
        contrast_discrepancy: Absolute difference in contrast scores
        skew_discrepancy: Absolute difference in skew scores
        noise_discrepancy: Absolute difference in noise scores
        illumination_discrepancy: Absolute difference in illumination scores
        compression_discrepancy: Absolute difference in compression scores
        binarization_discrepancy: Absolute difference in binarization scores
        bleed_through_discrepancy: Absolute difference in bleed-through scores
        max_discrepancy: Maximum discrepancy across all metrics
        mean_discrepancy: Mean discrepancy across all metrics
        per_head_discrepancies: Per-head discrepancy values
    """

    # Core dimensions
    blur_discrepancy: float
    contrast_discrepancy: float
    skew_discrepancy: float

    # ML IQA aligned dimensions
    noise_discrepancy: float
    illumination_discrepancy: float
    compression_discrepancy: float

    # Document-specific dimensions
    binarization_discrepancy: float
    bleed_through_discrepancy: float

    # Aggregate metrics
    max_discrepancy: float
    mean_discrepancy: float
    per_head_discrepancies: dict[str, float]


class MLIQADetector:
    """ML-based IQA detector with teacher-student architecture.

    Loads ONNX models for efficient inference with multi-head predictions.
    Supports device fallback: GPU → CPU → Modal.
    """

    def __init__(
        self,
        student_model_path: str | Path | None = None,
        teacher_model_path: str | Path | None = None,
        device: Device | None = None,
        enable_modal_fallback: bool = True,
        entropy_threshold: float = 0.8,
        min_confidence_threshold: float = 0.6,
        mean_confidence_threshold: float = 0.7,
        # Phase 4: Device orchestration parameters
        device_policy: DevicePolicyConfig | None = None,
        modal_endpoint: str | None = None,
        use_orchestrator: bool = True,
    ) -> None:
        """Initialize ML IQA detector.

        Args:
            student_model_path: Path to student ONNX model (ResNet-18)
            teacher_model_path: Path to teacher ONNX model (ResNet-50)
            device: Preferred device (auto-detect if None) - LEGACY, use device_policy instead
            enable_modal_fallback: Allow fallback to Modal GPU if local unavailable - LEGACY
            entropy_threshold: Entropy threshold for escalation (default: 0.8)
            min_confidence_threshold: Min confidence threshold for escalation (default: 0.6)
            mean_confidence_threshold: Mean confidence threshold for escalation (default: 0.7)
            device_policy: Device policy configuration (Phase 4)
            modal_endpoint: Modal serverless endpoint URL (Phase 4)
            use_orchestrator: Enable Phase 4 device orchestration (default: True)
        """
        self.student_model_path = student_model_path
        self.teacher_model_path = teacher_model_path
        self.enable_modal_fallback = enable_modal_fallback

        # Uncertainty gate thresholds
        self.entropy_threshold = entropy_threshold
        self.min_confidence_threshold = min_confidence_threshold
        self.mean_confidence_threshold = mean_confidence_threshold

        # Discrepancy check threshold (default: 0.3 for 30% difference)
        self.discrepancy_threshold = 0.3

        # Phase 4: Device orchestration
        self.use_orchestrator = use_orchestrator
        self.orchestrator: DeviceOrchestrator | None
        self.modal_client: ModalClient | None

        if use_orchestrator:
            # Use DeviceOrchestrator for device selection
            self.device_policy = device_policy or DevicePolicyConfig()
            self.orchestrator = DeviceOrchestrator(config=self.device_policy)
            self.modal_client = (
                ModalClient(modal_endpoint=modal_endpoint) if modal_endpoint else None
            )
            logger.info(
                "Device orchestrator enabled",
                mode=self.device_policy.mode.value,
                modal_endpoint=modal_endpoint,
            )
        else:
            # Legacy mode: manual device selection
            self.device = device or self._detect_device()
            self.orchestrator = None
            self.modal_client = None
            logger.info("Legacy device mode", device=self.device.value)

        # Lazy-load inference sessions (per-device caching in Phase 4)
        self._student_sessions: dict[str, Any] = {}
        self._teacher_sessions: dict[str, Any] = {}

        logger.info(
            "ML IQA detector initialized",
            student_model=str(student_model_path) if student_model_path else "None",
            teacher_model=str(teacher_model_path) if teacher_model_path else "None",
            orchestrator_enabled=use_orchestrator,
            entropy_threshold=entropy_threshold,
            min_confidence_threshold=min_confidence_threshold,
            mean_confidence_threshold=mean_confidence_threshold,
        )

    def _detect_device(self) -> Device:
        """Auto-detect best available device.

        Priority: Local GPU → Local CPU → Modal GPU

        Returns:
            Device enum
        """
        if ort is None:
            logger.warning("ONNX Runtime not available, using CPU")
        else:
            try:
                providers = ort.get_available_providers()
                if "CUDAExecutionProvider" in providers:
                    logger.info("GPU detected", provider="CUDAExecutionProvider")
                    return Device.GPU
            except Exception as e:
                logger.warning("GPU detection failed", error=str(e))

        # Fallback to CPU
        logger.info("Using CPU inference")
        return Device.CPU

    def _load_student_session(self, device: str | None = None) -> Any:
        """Load student model ONNX session (lazy initialization).

        Args:
            device: Device for session (cuda/cpu, None for legacy mode)

        Returns:
            ONNX InferenceSession

        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If ONNX Runtime not available
        """
        if self.use_orchestrator and device is not None:
            # Phase 4: Per-device caching
            if device in self._student_sessions:
                return self._student_sessions[device]
        elif not self.use_orchestrator:
            # Legacy mode: single session
            if self._student_sessions.get("legacy"):
                return self._student_sessions["legacy"]
            device = "legacy"

        if self.student_model_path is None:
            raise ValueError("Student model path not set")

        model_path = Path(self.student_model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Student model not found: {model_path}")

        if ort is None:
            raise RuntimeError("ONNX Runtime not installed")

        providers = self._get_ort_providers(device)
        session = ort.InferenceSession(str(model_path), providers=providers)

        if self.use_orchestrator and device:
            self._student_sessions[device] = session
        else:
            self._student_sessions["legacy"] = session

        logger.info("Student model loaded", path=str(model_path), providers=providers)
        return session

    def _load_teacher_session(self, device: str | None = None) -> Any:
        """Load teacher model ONNX session (lazy initialization).

        Args:
            device: Device for session (cuda/cpu/modal, None for legacy mode)

        Returns:
            ONNX InferenceSession

        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If ONNX Runtime not available
        """
        if self.use_orchestrator and device is not None:
            # Phase 4: Per-device caching
            if device in self._teacher_sessions:
                return self._teacher_sessions[device]
        elif not self.use_orchestrator:
            # Legacy mode: single session
            if self._teacher_sessions.get("legacy"):
                return self._teacher_sessions["legacy"]
            device = "legacy"

        if self.teacher_model_path is None:
            raise ValueError("Teacher model path not set")

        model_path = Path(self.teacher_model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Teacher model not found: {model_path}")

        if ort is None:
            raise RuntimeError("ONNX Runtime not installed")

        providers = self._get_ort_providers(device)
        session = ort.InferenceSession(str(model_path), providers=providers)

        if self.use_orchestrator and device:
            self._teacher_sessions[device] = session
        else:
            self._teacher_sessions["legacy"] = session

        logger.info("Teacher model loaded", path=str(model_path), providers=providers)
        return session

    def _get_ort_providers(self, device: str | None = None) -> list[str]:
        """Get ONNX Runtime execution providers based on device.

        Args:
            device: Device string (cuda/cpu/legacy, None for auto-detect)

        Returns:
            List of provider names in priority order
        """
        if self.use_orchestrator and device:
            # Phase 4: Device from orchestrator
            if device == "cuda":
                return ["CUDAExecutionProvider", "CPUExecutionProvider"]
            return ["CPUExecutionProvider"]
        # Legacy mode
        if hasattr(self, "device") and self.device == Device.GPU:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input.

        Args:
            image: Input image (BGR format, HxWx3)

        Returns:
            Preprocessed image (1x3x224x224, float32, normalized)
        """
        import cv2

        # Resize to 224x224 (ResNet input size)
        resized = cv2.resize(image, (224, 224), interpolation=cv2.INTER_LINEAR)

        # Convert BGR → RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize: [0, 255] → [0, 1]
        normalized = rgb.astype(np.float32) / 255.0

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std

        # Transpose: HWC → CHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # Add batch dimension: CHW → 1CHW
        return np.expand_dims(transposed, axis=0)

    def _postprocess_outputs(
        self, outputs: dict[str, np.ndarray]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Postprocess model outputs to scores and confidences.

        Args:
            outputs: Raw model outputs (logits or softmax)

        Returns:
            Tuple of (scores_dict, confidences_dict)
        """
        # Expected output format: multi-head predictions
        # Each head: [batch, num_classes] where class 0=bad, class 1=good
        # Score = probability of "good" class
        # Confidence = max softmax probability

        scores = {}
        confidences = {}

        head_names = ["blur", "noise", "contrast", "skew", "compression"]

        for i, head_name in enumerate(head_names):
            output_key = f"head_{i}"
            if output_key in outputs:
                logits = outputs[output_key][0]  # Remove batch dimension
                # Softmax
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
                # Score = P(good class)
                scores[f"{head_name}_score"] = float(probs[1])
                # Confidence = max probability
                confidences[head_name] = float(np.max(probs))

        return scores, confidences

    def _run_modal_teacher_inference(
        self, image: np.ndarray, doc_id: str | None = None
    ) -> MLIQAScores | None:
        """Run teacher inference on Modal GPU.

        Args:
            image: Input image (BGR format)
            doc_id: Optional document ID for tracking

        Returns:
            MLIQAScores from Modal or None if Modal unavailable
        """
        if not self.modal_client:
            logger.warning("Modal client not configured")
            return None

        # Create Modal request
        request = ModalInferenceRequest(
            image_array=image, model_version="v1.0", request_id=doc_id
        )

        # Execute Modal inference
        response = self.modal_client.predict(request)
        if response is None:
            logger.warning("Modal inference failed (circuit breaker open or error)")
            return None

        # Convert Modal response to MLIQAScores
        # Calculate overall quality with division by zero protection
        overall_quality = (
            sum(response.scores.values()) / len(response.scores)
            if response.scores
            else 0.0
        )

        return MLIQAScores(
            blur_score=response.scores.get("blur", 0.0),
            noise_score=response.scores.get("noise", 0.0),
            contrast_score=response.scores.get("contrast", 0.0),
            skew_score=response.scores.get("skew", 0.0),
            compression_score=response.scores.get("compression", 0.0),
            overall_quality=overall_quality,
            confidences=response.confidences,
            model_type=ModelType.TEACHER,
            device=Device.MODAL,
            inference_time_ms=response.inference_time_ms,
        )

    def run_student_inference(self, image: np.ndarray) -> MLIQAScores:
        """Run student model inference.

        Args:
            image: Input image (BGR format)

        Returns:
            MLIQAScores with student predictions

        Raises:
            ValueError: If image is invalid
            RuntimeError: If model not loaded
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image")

        import time

        start_time = time.perf_counter()

        # Phase 4: Device selection via orchestrator
        if self.use_orchestrator and self.orchestrator:
            device_choice = self.orchestrator.select_device_for_student()
            if device_choice.device is None:
                msg = f"No device available for student: {device_choice.blocked_reason}"
                raise RuntimeError(msg)
            selected_device = device_choice.device
            logger.debug(
                "Student device selected",
                device=selected_device,
                rationale=device_choice.rationale,
            )
        else:
            # Legacy mode
            selected_device = None

        # Preprocess
        input_tensor = self._preprocess_image(image)

        # Load model session for selected device
        session = self._load_student_session(device=selected_device)

        # Run inference
        input_name = session.get_inputs()[0].name
        output_names = [output.name for output in session.get_outputs()]
        outputs = session.run(output_names, {input_name: input_tensor})

        # Convert outputs to dict
        outputs_dict = dict(zip(output_names, outputs, strict=False))

        # Postprocess
        scores, confidences = self._postprocess_outputs(outputs_dict)

        # Calculate overall quality (weighted average)
        overall = (
            scores.get("blur_score", 0.0) * 0.25
            + scores.get("noise_score", 0.0) * 0.20
            + scores.get("contrast_score", 0.0) * 0.25
            + scores.get("skew_score", 0.0) * 0.15
            + scores.get("compression_score", 0.0) * 0.15
        )

        inference_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Map device to Device enum
        if self.use_orchestrator:
            device_enum = Device.GPU if selected_device == "cuda" else Device.CPU
        else:
            device_enum = self.device

        logger.debug(
            "Student inference complete",
            overall_quality=f"{overall:.3f}",
            inference_time_ms=f"{inference_time:.1f}",
            device=device_enum.value,
        )

        return MLIQAScores(
            blur_score=scores.get("blur_score", 0.0),
            noise_score=scores.get("noise_score", 0.0),
            contrast_score=scores.get("contrast_score", 0.0),
            skew_score=scores.get("skew_score", 0.0),
            compression_score=scores.get("compression_score", 0.0),
            overall_quality=overall,
            confidences=confidences,
            model_type=ModelType.STUDENT,
            device=device_enum,
            inference_time_ms=inference_time,
        )

    def _select_teacher_device(
        self, image: np.ndarray, doc_id: str | None
    ) -> tuple[str | None, MLIQAScores | None]:
        """Select device for teacher and optionally route to Modal.

        Args:
            image: Input image for potential Modal inference
            doc_id: Optional document ID for budget tracking

        Returns:
            Tuple of (device_string, modal_scores_or_none)

        Raises:
            RuntimeError: If no device available
        """
        if not (self.use_orchestrator and self.orchestrator):
            return None, None

        device_choice = self.orchestrator.select_device_for_teacher(doc_id=doc_id)
        if device_choice.device is None:
            msg = f"No device available for teacher: {device_choice.blocked_reason}"
            raise RuntimeError(msg)

        selected_device = device_choice.device
        logger.debug(
            "Teacher device selected",
            device=selected_device,
            rationale=device_choice.rationale,
            doc_id=doc_id,
        )

        if selected_device == "modal":
            modal_scores = self._run_modal_teacher_inference(image, doc_id)
            if modal_scores is not None:
                return selected_device, modal_scores
            # Modal failed, fall back to next available device
            logger.warning("Modal inference failed, falling back to local")
            has_gpu = self.orchestrator.capabilities.has_local_gpu
            selected_device = "cuda" if has_gpu else "cpu"

        return selected_device, None

    def run_teacher_inference(
        self, image: np.ndarray, doc_id: str | None = None
    ) -> MLIQAScores:
        """Run teacher model inference (for high-risk pages).

        Args:
            image: Input image (BGR format)
            doc_id: Optional document ID for budget tracking

        Returns:
            MLIQAScores with teacher predictions

        Raises:
            ValueError: If image is invalid
            RuntimeError: If model not loaded or device unavailable
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image")

        import time

        start_time = time.perf_counter()

        # Phase 4: Device selection via orchestrator
        selected_device, modal_scores = self._select_teacher_device(image, doc_id)
        if modal_scores is not None:
            return modal_scores

        # Preprocess
        input_tensor = self._preprocess_image(image)

        # Load model session for selected device
        session = self._load_teacher_session(device=selected_device)

        # Run inference
        input_name = session.get_inputs()[0].name
        output_names = [output.name for output in session.get_outputs()]
        outputs = session.run(output_names, {input_name: input_tensor})

        # Convert outputs to dict
        outputs_dict = dict(zip(output_names, outputs, strict=False))

        # Postprocess
        scores, confidences = self._postprocess_outputs(outputs_dict)

        # Calculate overall quality
        overall = (
            scores.get("blur_score", 0.0) * 0.25
            + scores.get("noise_score", 0.0) * 0.20
            + scores.get("contrast_score", 0.0) * 0.25
            + scores.get("skew_score", 0.0) * 0.15
            + scores.get("compression_score", 0.0) * 0.15
        )

        inference_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Map device to Device enum
        if self.use_orchestrator:
            device_enum = Device.GPU if selected_device == "cuda" else Device.CPU
        else:
            device_enum = self.device

        logger.debug(
            "Teacher inference complete",
            overall_quality=f"{overall:.3f}",
            inference_time_ms=f"{inference_time:.1f}",
            device=device_enum.value,
        )

        # Record actual inference for budget tracking
        if self.use_orchestrator and self.orchestrator and selected_device:
            # Type narrowing: selected_device is guaranteed to be one of the literals here
            from typing import cast

            device_literal = cast("Literal['cuda', 'cpu', 'modal']", selected_device)
            self.orchestrator.record_teacher_inference(
                device=device_literal, inference_time_ms=inference_time
            )

        return MLIQAScores(
            blur_score=scores.get("blur_score", 0.0),
            noise_score=scores.get("noise_score", 0.0),
            contrast_score=scores.get("contrast_score", 0.0),
            skew_score=scores.get("skew_score", 0.0),
            compression_score=scores.get("compression_score", 0.0),
            overall_quality=overall,
            confidences=confidences,
            model_type=ModelType.TEACHER,
            device=device_enum,
            inference_time_ms=inference_time,
        )

    def calculate_uncertainty(self, scores: MLIQAScores) -> UncertaintyMetrics:
        """Calculate uncertainty metrics from IQA scores.

        Used for teacher escalation decisions.

        Args:
            scores: ML IQA scores from student model

        Returns:
            UncertaintyMetrics with entropy and confidence measures
        """
        confidences = {
            name: float(np.clip(value, 0.0, 1.0))
            for name, value in scores.confidences.items()
        }

        if not confidences:
            return UncertaintyMetrics(
                entropy=0.0,
                min_confidence=0.0,
                mean_confidence=0.0,
                head_confidences={},
            )

        # Calculate entropy from confidences
        # Entropy = -sum(p * log(p)) for binary classification
        entropies = []
        for conf in confidences.values():
            # Binary classification: p_good = conf, p_bad = 1 - conf
            p_good = conf
            p_bad = 1.0 - conf
            # Avoid log(0)
            h = 0.0
            if p_good > 0:
                h -= p_good * np.log2(p_good)
            if p_bad > 0:
                h -= p_bad * np.log2(p_bad)
            entropies.append(h)

        mean_entropy = float(np.mean(entropies))
        confidence_values = np.fromiter(confidences.values(), dtype=float)
        min_confidence = float(np.min(confidence_values))
        mean_confidence = float(np.mean(confidence_values))

        return UncertaintyMetrics(
            entropy=mean_entropy,
            min_confidence=min_confidence,
            mean_confidence=mean_confidence,
            head_confidences=confidences,
        )

    def should_escalate_to_teacher(
        self, student_scores: MLIQAScores
    ) -> EscalationDecision:
        """Determine if student output should be escalated to teacher model.

        Escalation triggers:
        1. High entropy (uncertainty) across heads
        2. Low minimum confidence across any head
        3. Low mean confidence across all heads

        Args:
            student_scores: Student model IQA scores

        Returns:
            EscalationDecision with escalation decision and reason
        """
        # Calculate uncertainty metrics
        uncertainty = self.calculate_uncertainty(student_scores)

        # Check escalation conditions
        reasons = []

        if uncertainty.entropy >= self.entropy_threshold:
            reasons.append(
                f"high_entropy ({uncertainty.entropy:.3f} >= {self.entropy_threshold})"
            )

        if uncertainty.min_confidence < self.min_confidence_threshold:
            reasons.append(
                f"low_min_confidence ({uncertainty.min_confidence:.3f} < {self.min_confidence_threshold})"
            )

        if uncertainty.mean_confidence < self.mean_confidence_threshold:
            reasons.append(
                f"low_mean_confidence ({uncertainty.mean_confidence:.3f} < {self.mean_confidence_threshold})"
            )

        # Decide escalation
        should_escalate = len(reasons) > 0
        reason = "; ".join(reasons) if should_escalate else None

        if should_escalate:
            logger.info(
                "Escalating to teacher model",
                reason=reason,
                entropy=f"{uncertainty.entropy:.3f}",
                min_confidence=f"{uncertainty.min_confidence:.3f}",
                mean_confidence=f"{uncertainty.mean_confidence:.3f}",
            )
        else:
            logger.debug(
                "No escalation needed",
                entropy=f"{uncertainty.entropy:.3f}",
                min_confidence=f"{uncertainty.min_confidence:.3f}",
                mean_confidence=f"{uncertainty.mean_confidence:.3f}",
            )

        return EscalationDecision(
            should_escalate=should_escalate,
            reason=reason,
            uncertainty_metrics=uncertainty,
        )

    def calculate_discrepancy(
        self,
        student_scores: MLIQAScores,
        classical_scores: ClassicalIQAScores,
    ) -> DiscrepancyMetrics:
        """Calculate discrepancy between student ML IQA and classical IQA.

        Computes absolute differences for all 8 quality dimensions to enable
        comprehensive discrepancy analysis for teacher escalation decisions.

        Args:
            student_scores: Student model ML IQA scores
            classical_scores: Classical IQA scores (normalized to 0-1)

        Returns:
            DiscrepancyMetrics with per-head and aggregate discrepancies
        """
        # Calculate per-head absolute differences (all 8 dimensions)
        blur_discrepancy = abs(student_scores.blur_score - classical_scores.blur_score)
        contrast_discrepancy = abs(
            student_scores.contrast_score - classical_scores.contrast_score
        )
        skew_discrepancy = abs(student_scores.skew_score - classical_scores.skew_score)
        noise_discrepancy = abs(
            student_scores.noise_score - classical_scores.noise_score
        )
        # Note: ML IQA doesn't have illumination head, so discrepancy with
        # classical illumination is not directly comparable. Use 0.0 for now.
        illumination_discrepancy = 0.0  # ML model doesn't predict illumination
        compression_discrepancy = abs(
            student_scores.compression_score - classical_scores.compression_score
        )
        # Note: Binarization and bleed-through are document-specific and not
        # predicted by current ML IQA models. Use 0.0 for now.
        binarization_discrepancy = 0.0  # ML model doesn't predict binarization
        bleed_through_discrepancy = 0.0  # ML model doesn't predict bleed-through

        # Aggregate metrics (only include dimensions predicted by ML model)
        ml_predicted_discrepancies = [
            blur_discrepancy,
            contrast_discrepancy,
            skew_discrepancy,
            noise_discrepancy,
            compression_discrepancy,
        ]
        max_discrepancy = float(np.max(ml_predicted_discrepancies))
        mean_discrepancy = float(np.mean(ml_predicted_discrepancies))

        per_head_discrepancies = {
            "blur": blur_discrepancy,
            "contrast": contrast_discrepancy,
            "skew": skew_discrepancy,
            "noise": noise_discrepancy,
            "compression": compression_discrepancy,
        }

        logger.debug(
            "Discrepancy calculated",
            max_discrepancy=f"{max_discrepancy:.3f}",
            mean_discrepancy=f"{mean_discrepancy:.3f}",
            per_head=per_head_discrepancies,
        )

        return DiscrepancyMetrics(
            blur_discrepancy=blur_discrepancy,
            contrast_discrepancy=contrast_discrepancy,
            skew_discrepancy=skew_discrepancy,
            noise_discrepancy=noise_discrepancy,
            illumination_discrepancy=illumination_discrepancy,
            compression_discrepancy=compression_discrepancy,
            binarization_discrepancy=binarization_discrepancy,
            bleed_through_discrepancy=bleed_through_discrepancy,
            max_discrepancy=max_discrepancy,
            mean_discrepancy=mean_discrepancy,
            per_head_discrepancies=per_head_discrepancies,
        )

    def should_escalate_due_to_discrepancy(
        self,
        student_scores: MLIQAScores,
        classical_scores: ClassicalIQAScores,
    ) -> EscalationDecision:
        """Determine if student-classical discrepancy warrants teacher escalation.

        Checks all 5 ML-predicted dimensions (blur, contrast, skew, noise, compression)
        for discrepancies that exceed the threshold.

        Args:
            student_scores: Student model ML IQA scores
            classical_scores: Classical IQA scores

        Returns:
            EscalationDecision with escalation decision and reason
        """
        # Calculate discrepancy
        discrepancy = self.calculate_discrepancy(student_scores, classical_scores)

        # Check if any ML-predicted head exceeds discrepancy threshold
        reasons = []

        if discrepancy.blur_discrepancy >= self.discrepancy_threshold:
            reasons.append(
                f"blur_discrepancy ({discrepancy.blur_discrepancy:.3f} >= {self.discrepancy_threshold})"
            )

        if discrepancy.contrast_discrepancy >= self.discrepancy_threshold:
            reasons.append(
                f"contrast_discrepancy ({discrepancy.contrast_discrepancy:.3f} >= {self.discrepancy_threshold})"
            )

        if discrepancy.skew_discrepancy >= self.discrepancy_threshold:
            reasons.append(
                f"skew_discrepancy ({discrepancy.skew_discrepancy:.3f} >= {self.discrepancy_threshold})"
            )

        if discrepancy.noise_discrepancy >= self.discrepancy_threshold:
            reasons.append(
                f"noise_discrepancy ({discrepancy.noise_discrepancy:.3f} >= {self.discrepancy_threshold})"
            )

        if discrepancy.compression_discrepancy >= self.discrepancy_threshold:
            reasons.append(
                f"compression_discrepancy ({discrepancy.compression_discrepancy:.3f} >= {self.discrepancy_threshold})"
            )

        # Decide escalation
        should_escalate = len(reasons) > 0
        reason = "; ".join(reasons) if should_escalate else None

        if should_escalate:
            logger.info(
                "Escalating due to ML-classical discrepancy",
                reason=reason,
                max_discrepancy=f"{discrepancy.max_discrepancy:.3f}",
                mean_discrepancy=f"{discrepancy.mean_discrepancy:.3f}",
            )
        else:
            logger.debug(
                "No discrepancy escalation",
                max_discrepancy=f"{discrepancy.max_discrepancy:.3f}",
            )

        # Create uncertainty metrics (not applicable for discrepancy check)
        # Use placeholder uncertainty metrics
        uncertainty = self.calculate_uncertainty(student_scores)

        return EscalationDecision(
            should_escalate=should_escalate,
            reason=reason,
            uncertainty_metrics=uncertainty,
        )

    def run_pipeline(
        self,
        image: np.ndarray,
        classical_scores: ClassicalIQAScores | None = None,
        doc_id: str | None = None,
    ) -> tuple[MLIQAScores, MLIQAScores | None, str | None]:
        """Run complete ML IQA pipeline with automatic teacher escalation.

        This is the main entry point for ML IQA analysis. It:
        1. Runs student inference
        2. Checks uncertainty gate
        3. Optionally checks classical IQA discrepancy
        4. Escalates to teacher if needed
        5. Returns final scores

        Args:
            image: Input image (BGR format)
            classical_scores: Optional classical IQA scores for discrepancy check
            doc_id: Optional document ID for budget tracking (Phase 4)

        Returns:
            Tuple of (student_scores, teacher_scores_or_none, escalation_reason_or_none)

        Example:
            >>> detector = MLIQADetector(
            ...     student_path="student.onnx", teacher_path="teacher.onnx"
            ... )
            >>> student, teacher, reason = detector.run_pipeline(image, doc_id="doc123")
            >>> if teacher is not None:
            ...     print(f"Teacher used: {reason}")
        """
        # Run student inference
        student_scores = self.run_student_inference(image)

        # Check uncertainty gate
        uncertainty_decision = self.should_escalate_to_teacher(student_scores)

        # Check discrepancy if classical scores provided
        discrepancy_decision = None
        if classical_scores is not None and not uncertainty_decision.should_escalate:
            discrepancy_decision = self.should_escalate_due_to_discrepancy(
                student_scores, classical_scores
            )

        # Determine if we should escalate
        should_escalate = uncertainty_decision.should_escalate
        escalation_reason = uncertainty_decision.reason

        if discrepancy_decision is not None and discrepancy_decision.should_escalate:
            should_escalate = True
            if escalation_reason:
                escalation_reason = (
                    f"{escalation_reason}; {discrepancy_decision.reason}"
                )
            else:
                escalation_reason = discrepancy_decision.reason

        # Run teacher if needed
        teacher_scores = None
        if should_escalate and self.teacher_model_path is not None:
            try:
                teacher_scores = self.run_teacher_inference(image, doc_id=doc_id)
                logger.info(
                    "Pipeline complete with teacher escalation",
                    reason=escalation_reason,
                    student_quality=f"{student_scores.overall_quality:.3f}",
                    teacher_quality=f"{teacher_scores.overall_quality:.3f}",
                    doc_id=doc_id,
                )
            except Exception as e:
                logger.warning(
                    "Teacher inference failed, using student scores",
                    error=str(e),
                    doc_id=doc_id,
                )
                escalation_reason = f"teacher_failed: {e}"
        else:
            logger.debug(
                "Pipeline complete (student only)",
                quality=f"{student_scores.overall_quality:.3f}",
                doc_id=doc_id,
            )

        return student_scores, teacher_scores, escalation_reason


def ml_iqa_scores_to_dict(scores: MLIQAScores) -> dict[str, Any]:
    """Convert MLIQAScores to dictionary for JSON serialization.

    Args:
        scores: MLIQAScores dataclass instance

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "source": scores.model_type.value,
        "blur_score": round(scores.blur_score, 4),
        "noise_score": round(scores.noise_score, 4),
        "contrast_score": round(scores.contrast_score, 4),
        "skew_score": round(scores.skew_score, 4),
        "compression_score": round(scores.compression_score, 4),
        "overall_quality": round(scores.overall_quality, 4),
        "confidences": {k: round(v, 4) for k, v in scores.confidences.items()},
        "device": scores.device.value,
        "inference_time_ms": round(scores.inference_time_ms, 2),
    }


def teacher_iqa_to_dict(
    scores: MLIQAScores, escalation_reason: str | None
) -> dict[str, Any]:
    """Convert teacher MLIQAScores to dictionary with escalation reason.

    Args:
        scores: Teacher MLIQAScores dataclass instance
        escalation_reason: Reason for teacher escalation

    Returns:
        Dictionary suitable for JSON serialization
    """
    result = ml_iqa_scores_to_dict(scores)
    result["escalation_reason"] = escalation_reason
    return result


def uncertainty_metrics_to_dict(metrics: UncertaintyMetrics) -> dict[str, Any]:
    """Convert UncertaintyMetrics to dictionary.

    Args:
        metrics: UncertaintyMetrics dataclass instance

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "entropy": round(metrics.entropy, 4),
        "min_confidence": round(metrics.min_confidence, 4),
        "mean_confidence": round(metrics.mean_confidence, 4),
        "head_confidences": {
            k: round(v, 4) for k, v in metrics.head_confidences.items()
        },
    }


def discrepancy_metrics_to_dict(metrics: DiscrepancyMetrics) -> dict[str, Any]:
    """Convert DiscrepancyMetrics to dictionary.

    Args:
        metrics: DiscrepancyMetrics dataclass instance

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "blur_discrepancy": round(metrics.blur_discrepancy, 4),
        "contrast_discrepancy": round(metrics.contrast_discrepancy, 4),
        "skew_discrepancy": round(metrics.skew_discrepancy, 4),
        "noise_discrepancy": round(metrics.noise_discrepancy, 4),
        "illumination_discrepancy": round(metrics.illumination_discrepancy, 4),
        "compression_discrepancy": round(metrics.compression_discrepancy, 4),
        "binarization_discrepancy": round(metrics.binarization_discrepancy, 4),
        "bleed_through_discrepancy": round(metrics.bleed_through_discrepancy, 4),
        "max_discrepancy": round(metrics.max_discrepancy, 4),
        "mean_discrepancy": round(metrics.mean_discrepancy, 4),
        "per_head_discrepancies": {
            k: round(v, 4) for k, v in metrics.per_head_discrepancies.items()
        },
    }
