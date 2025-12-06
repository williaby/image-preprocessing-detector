"""Machine learning models for image quality assessment.

This module contains deep learning models for document image quality assessment:
- ResNet-50 Teacher Model: High-capacity model for difficult/high-risk cases
- ResNet-18 Student Model: Fast production model
- Multi-head architectures for quality issue detection
- Loss functions for training multi-head models
- Model optimization utilities (ONNX export, INT8 quantization, TensorRT)
- Model registry and deployment packaging

Note:
    PyTorch-based models (ResNetTeacher, ResNetStudent, loss functions) require
    the 'ml' optional dependencies to be installed. Model optimization utilities
    are available without PyTorch.
"""

# Model optimization utilities (no torch dependency)
# Batch inference utilities (no torch dependency)
from image_preprocessing_detector.models.batch_inference import (
    BatchInferenceEngine,
    BatchInferenceMetrics,
    InferenceRequest,
    run_batch_inference,
)
from image_preprocessing_detector.models.model_optimizer import (
    BenchmarkResult,
    CalibrationDataset,
    ModelDeploymentPackage,
    ModelManifest,
    ModelOptimizer,
    ModelRegistry,
    ONNXExportConfig,
    QuantizationConfig,
    ThresholdConfig,
    ThresholdTuner,
)

__all__ = [
    "BatchInferenceEngine",
    "BatchInferenceMetrics",
    "BenchmarkResult",
    "CalibrationDataset",
    "InferenceRequest",
    "ModelDeploymentPackage",
    "ModelManifest",
    "ModelOptimizer",
    "ModelRegistry",
    "ONNXExportConfig",
    "QuantizationConfig",
    "ThresholdConfig",
    "ThresholdTuner",
    "run_batch_inference",
]

# PyTorch-dependent imports (optional)
try:
    from image_preprocessing_detector.models.loss_functions import (
        FocalLoss,
        MultiHeadIQALoss,
        WeightedMSELoss,
        compute_class_weights,
    )
    from image_preprocessing_detector.models.resnet_student import (
        ResNetStudent,
        StudentIQAHead,
    )
    from image_preprocessing_detector.models.resnet_teacher import (
        IQAHead,
        ResNetTeacher,
    )

    __all__.extend(
        [
            "FocalLoss",
            "IQAHead",
            "MultiHeadIQALoss",
            "ResNetStudent",
            "ResNetTeacher",
            "StudentIQAHead",
            "WeightedMSELoss",
            "compute_class_weights",
        ]
    )
except ImportError:
    # PyTorch not installed - ML models not available
    pass
