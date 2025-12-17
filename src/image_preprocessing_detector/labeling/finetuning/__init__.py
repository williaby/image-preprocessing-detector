"""Project C: Fine-Tuning & Label Generation.

This module provides training pipelines for DIQA-5000 fine-tuning and
DIQA-style label generation for external datasets.

Project C is the only workstream that performs learning - no benchmarking
or quantization is done here.

Architecture:
    Vision Encoder (frozen) → LoRA Adapters → Regression Head → [3 scores]

Output Scores:
    - overall: Overall document quality [0, 1]
    - sharpness: Text and image clarity [0, 1]
    - color: Color reproduction accuracy [0, 1]

Key Components:
    - DIQATrainer: Main training loop with PEFT/LoRA
    - DIQARegressionModel: Vision encoder + regression head
    - DIQATrainingDataset: Dataset adapter with split discipline
    - TrainingManifest: Full provenance tracking
    - ModelExporter: Export to PyTorch/ONNX/TorchScript

Example:
    >>> from image_preprocessing_detector.labeling.finetuning import (
    ...     DIQATrainer,
    ...     TrainingConfig,
    ... )
    >>>
    >>> config = TrainingConfig(
    ...     base_model_id="HuggingFaceTB/SmolVLM-256M-Instruct",
    ...     num_epochs=30,
    ...     use_lora=True,
    ... )
    >>> trainer = DIQATrainer(config)
    >>> metrics = trainer.train(data_dir="/data/diqa5000")
    >>> trainer.export_model("exports/", formats=["pytorch", "onnx"])
"""

from image_preprocessing_detector.labeling.finetuning.dataset import (
    DIQASample,
    DIQATrainingDataset,
    create_data_loaders,
    get_default_transforms,
)
from image_preprocessing_detector.labeling.finetuning.manifest import (
    DatasetManifest,
    ManifestBuilder,
    ModelExporter,
    ModelManifest,
    TrainingManifest,
    create_arena_model_spec,
)
from image_preprocessing_detector.labeling.finetuning.regression_head import (
    DIQAOutput,
    DIQARegressionHead,
    DIQARegressionModel,
    RegressionHeadConfig,
)
from image_preprocessing_detector.labeling.finetuning.trainer import (
    DIQATrainer,
    TrainingConfig,
    TrainingMetrics,
    train_diqa_model,
)

__all__ = [
    # Regression Head
    "DIQAOutput",
    "DIQARegressionHead",
    "DIQARegressionModel",
    # Dataset
    "DIQASample",
    # Trainer
    "DIQATrainer",
    "DIQATrainingDataset",
    # Manifest
    "DatasetManifest",
    "ManifestBuilder",
    "ModelExporter",
    "ModelManifest",
    "RegressionHeadConfig",
    "TrainingConfig",
    "TrainingManifest",
    "TrainingMetrics",
    "create_arena_model_spec",
    "create_data_loaders",
    "get_default_transforms",
    "train_diqa_model",
]
