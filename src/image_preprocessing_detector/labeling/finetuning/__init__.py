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

Layout Fusion Downsampler (CRITICAL FOR IQA TRAINING):
    The LayoutFusionDownsampler MUST be used for ALL IQA-based training
    where the model cannot accept the full 1600x1600 image resolution.
    It preserves semantic layout information during downsampling.

    See: docs/planning/DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3

    Components:
        - LayoutFusionDownsampler: Fuses RGB with 11-class layout masks
        - LayoutMaskGenerator: Generates masks via DocLayout-YOLO
        - DocIQReplica: Full DocIQ paper architecture (Generalist Anchor)

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

Layout Fusion Example:
    >>> from image_preprocessing_detector.labeling.finetuning import (
    ...     LayoutFusionDownsampler,
    ...     LayoutMaskGenerator,
    ...     DocIQReplica,
    ... )
    >>>
    >>> # Generate layout masks for training
    >>> mask_generator = LayoutMaskGenerator()
    >>> layout_mask = mask_generator.generate_mask(image)
    >>>
    >>> # Use DocIQ Replica with layout fusion
    >>> model = DocIQReplica(freeze_backbone=True)
    >>> outputs = model(rgb_tensor, layout_tensor)
"""

from image_preprocessing_detector.labeling.finetuning.dataset import (
    DIQASample,
    DIQATrainingDataset,
    create_data_loaders,
    get_default_transforms,
)

# Layout Fusion Downsampler (Sub-Track A3: DocIQ Replica / Generalist Anchor)
# CRITICAL: Must be used for ALL IQA training with 1600x1600 input resolution
from image_preprocessing_detector.labeling.finetuning.layout_fusion import (
    DOCLAYNET_CLASSES,
    N_LAYOUT_CLASSES,
    DocIQReplica,
    LayoutFusionConfig,
    LayoutFusionDownsampler,
    LayoutMaskGenerator,
    LayoutMaskGeneratorConfig,
    create_dociq_replica,
)
from image_preprocessing_detector.labeling.finetuning.manifest import (
    DatasetManifest,
    ManifestBuilder,
    ModelExporter,
    ModelManifest,
    TrainingManifest,
    create_arena_model_spec,
)

# MUSIQ Fine-Tuning (Sub-Track A1: Sharpness Specialist)
from image_preprocessing_detector.labeling.finetuning.musiq_config import (
    CHECKPOINT_PRESETS,
    CheckpointMetrics,
    MUSIQTrainingConfig,
    compute_checkpoint_score,
    get_checkpoint_preset,
    select_best_checkpoint,
)
from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
    DIQA5000TrainingDataset,
    collate_diqa_batch,
    create_dataloaders,
    get_phase1_transforms,
    get_phase2_transforms,
    get_validation_transforms,
)
from image_preprocessing_detector.labeling.finetuning.musiq_loss import (
    MUSIQSpecialistLoss,
    differentiable_rank_loss,
    dimension_loss,
    focal_calibration_loss,
    musiq_specialist_loss,
)
from image_preprocessing_detector.labeling.finetuning.musiq_wrapper import (
    MultiTaskHead,
    MultiTaskHeadConfig,
    MUSIQBackbone,
    MUSIQMultiTask,
    create_musiq_multitask,
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
    "CHECKPOINT_PRESETS",
    "DOCLAYNET_CLASSES",
    "N_LAYOUT_CLASSES",
    "CheckpointMetrics",
    "DIQA5000TrainingDataset",
    "DIQAOutput",
    "DIQARegressionHead",
    "DIQARegressionModel",
    "DIQASample",
    "DIQATrainer",
    "DIQATrainingDataset",
    "DatasetManifest",
    "DocIQReplica",
    "LayoutFusionConfig",
    "LayoutFusionDownsampler",
    "LayoutMaskGenerator",
    "LayoutMaskGeneratorConfig",
    "MUSIQBackbone",
    "MUSIQMultiTask",
    "MUSIQSpecialistLoss",
    "MUSIQTrainingConfig",
    "ManifestBuilder",
    "ModelExporter",
    "ModelManifest",
    "MultiTaskHead",
    "MultiTaskHeadConfig",
    "RegressionHeadConfig",
    "TrainingConfig",
    "TrainingManifest",
    "TrainingMetrics",
    "collate_diqa_batch",
    "compute_checkpoint_score",
    "create_arena_model_spec",
    "create_data_loaders",
    "create_dataloaders",
    "create_dociq_replica",
    "create_musiq_multitask",
    "differentiable_rank_loss",
    "dimension_loss",
    "focal_calibration_loss",
    "get_checkpoint_preset",
    "get_default_transforms",
    "get_phase1_transforms",
    "get_phase2_transforms",
    "get_validation_transforms",
    "musiq_specialist_loss",
    "select_best_checkpoint",
    "train_diqa_model",
]
