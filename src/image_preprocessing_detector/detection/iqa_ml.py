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
from typing import Any

import numpy as np

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

    Attributes:
        blur_score: Blur quality (from Laplacian variance, normalized)
        contrast_score: Contrast quality (from histogram analysis)
        skew_score: Skew quality (1 - normalized_angle)
        has_noise: Whether noise is detected (boolean)
        has_compression: Whether compression artifacts detected (boolean)
    """

    blur_score: float
    contrast_score: float
    skew_score: float
    has_noise: bool = False
    has_compression: bool = False


@dataclass
class DiscrepancyMetrics:
    """Discrepancy metrics between student ML IQA and classical IQA.

    Attributes:
        blur_discrepancy: Absolute difference in blur scores
        contrast_discrepancy: Absolute difference in contrast scores
        skew_discrepancy: Absolute difference in skew scores
        max_discrepancy: Maximum discrepancy across all metrics
        mean_discrepancy: Mean discrepancy across all metrics
        per_head_discrepancies: Per-head discrepancy values
    """

    blur_discrepancy: float
    contrast_discrepancy: float
    skew_discrepancy: float
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
    ) -> None:
        """Initialize ML IQA detector.

        Args:
            student_model_path: Path to student ONNX model (ResNet-18)
            teacher_model_path: Path to teacher ONNX model (ResNet-50)
            device: Preferred device (auto-detect if None)
            enable_modal_fallback: Allow fallback to Modal GPU if local unavailable
            entropy_threshold: Entropy threshold for escalation (default: 0.8)
            min_confidence_threshold: Min confidence threshold for escalation (default: 0.6)
            mean_confidence_threshold: Mean confidence threshold for escalation (default: 0.7)
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

        # Auto-detect device if not specified
        self.device = device or self._detect_device()

        # Lazy-load inference sessions
        self._student_session: Any = None
        self._teacher_session: Any = None

        logger.info(
            "ML IQA detector initialized",
            student_model=str(student_model_path) if student_model_path else "None",
            teacher_model=str(teacher_model_path) if teacher_model_path else "None",
            device=self.device.value,
            modal_fallback=enable_modal_fallback,
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

    def _load_student_session(self) -> Any:
        """Load student model ONNX session (lazy initialization).

        Returns:
            ONNX InferenceSession

        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If ONNX Runtime not available
        """
        if self._student_session is not None:
            return self._student_session

        if self.student_model_path is None:
            raise ValueError("Student model path not set")

        model_path = Path(self.student_model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Student model not found: {model_path}")

        if ort is None:
            raise RuntimeError("ONNX Runtime not installed")

        providers = self._get_ort_providers()
        self._student_session = ort.InferenceSession(
            str(model_path), providers=providers
        )
        logger.info("Student model loaded", path=str(model_path), providers=providers)
        return self._student_session

    def _load_teacher_session(self) -> Any:
        """Load teacher model ONNX session (lazy initialization).

        Returns:
            ONNX InferenceSession

        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If ONNX Runtime not available
        """
        if self._teacher_session is not None:
            return self._teacher_session

        if self.teacher_model_path is None:
            raise ValueError("Teacher model path not set")

        model_path = Path(self.teacher_model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Teacher model not found: {model_path}")

        if ort is None:
            raise RuntimeError("ONNX Runtime not installed")

        providers = self._get_ort_providers()
        self._teacher_session = ort.InferenceSession(
            str(model_path), providers=providers
        )
        logger.info("Teacher model loaded", path=str(model_path), providers=providers)
        return self._teacher_session

    def _get_ort_providers(self) -> list[str]:
        """Get ONNX Runtime execution providers based on device.

        Returns:
            List of provider names in priority order
        """
        if self.device == Device.GPU:
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

        # Preprocess
        input_tensor = self._preprocess_image(image)

        # Load model session
        session = self._load_student_session()

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

        logger.debug(
            "Student inference complete",
            overall_quality=f"{overall:.3f}",
            inference_time_ms=f"{inference_time:.1f}",
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
            device=self.device,
            inference_time_ms=inference_time,
        )

    def run_teacher_inference(self, image: np.ndarray) -> MLIQAScores:
        """Run teacher model inference (for high-risk pages).

        Args:
            image: Input image (BGR format)

        Returns:
            MLIQAScores with teacher predictions

        Raises:
            ValueError: If image is invalid
            RuntimeError: If model not loaded
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image")

        import time

        start_time = time.perf_counter()

        # Preprocess
        input_tensor = self._preprocess_image(image)

        # Load model session
        session = self._load_teacher_session()

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

        logger.debug(
            "Teacher inference complete",
            overall_quality=f"{overall:.3f}",
            inference_time_ms=f"{inference_time:.1f}",
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
            device=self.device,
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

        Args:
            student_scores: Student model ML IQA scores
            classical_scores: Classical IQA scores (normalized to 0-1)

        Returns:
            DiscrepancyMetrics with per-head and aggregate discrepancies
        """
        # Calculate per-head absolute differences
        blur_discrepancy = abs(student_scores.blur_score - classical_scores.blur_score)
        contrast_discrepancy = abs(
            student_scores.contrast_score - classical_scores.contrast_score
        )
        skew_discrepancy = abs(student_scores.skew_score - classical_scores.skew_score)

        # Aggregate metrics
        discrepancies = [blur_discrepancy, contrast_discrepancy, skew_discrepancy]
        max_discrepancy = float(np.max(discrepancies))
        mean_discrepancy = float(np.mean(discrepancies))

        per_head_discrepancies = {
            "blur": blur_discrepancy,
            "contrast": contrast_discrepancy,
            "skew": skew_discrepancy,
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

        Args:
            student_scores: Student model ML IQA scores
            classical_scores: Classical IQA scores

        Returns:
            EscalationDecision with escalation decision and reason
        """
        # Calculate discrepancy
        discrepancy = self.calculate_discrepancy(student_scores, classical_scores)

        # Check if any head exceeds discrepancy threshold
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
