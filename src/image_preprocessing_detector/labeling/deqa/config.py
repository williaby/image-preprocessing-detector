"""Configuration for DeQA-Doc labeling infrastructure.

This module defines model registries, dataset configurations, and
inference settings for the multi-mode labeling system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class InferenceMode(str, Enum):
    """Supported inference modes for DeQA labeling."""

    SPECIALIST = "specialist"  # Single model with dimension-specific prompts (baseline)
    SPECIALIST_TRUE = "specialist_true"  # 3 actual dimension-specific CNN models
    ENSEMBLE = "ensemble"  # 5 VLM models (VQualA 2025 champion) - placeholder
    ENSEMBLE_TRUE = "ensemble_true"  # 6 models (3 full + 3 LoRA) with individual + aggregated scores
    VL = "vl"  # Single configurable VL model


class ModelSource(str, Enum):
    """Source location for model weights."""

    HUGGINGFACE = "huggingface"
    MODELSCOPE = "modelscope"
    LOCAL = "local"


class QualityDimension(str, Enum):
    """Quality assessment dimensions."""

    OVERALL = "overall"
    SHARPNESS = "sharpness"
    COLOR = "color"


# Quality level tokens used by DeQA-Score
QUALITY_LEVELS = ["excellent", "good", "fair", "poor", "bad"]
QUALITY_SCORES = [5.0, 4.0, 3.0, 2.0, 1.0]

# Model path constants
DEQA_DOC_MODEL_PATH = "zhalala/DeQA-Doc"
DEQA_DOC_MIX_MODEL_PATH = "zhalala/DeQA-Doc-Mix"
DEQA_SCORE_MIX3_MODEL_PATH = "zhiyuanyou/DeQA-Score-Mix3"


@dataclass
class ModelConfig:
    """Configuration for a single DeQA model variant."""

    model_id: str
    source: ModelSource
    model_path: str
    architecture: str  # e.g., "mplug_owl2", "qwen_vl"
    dimensions: list[QualityDimension]
    training_method: str | None = None  # "full", "lora"
    resolution: int | str = 1024  # Fixed resolution or "dynamic"
    pretrain_dataset: str | None = None  # e.g., "koniq-10k"
    checkpoint_subdir: str | None = (
        None  # Subdirectory within model_path for checkpoint
    )
    notes: str | None = None


# Model registry with all available DeQA model variants
MODEL_REGISTRY: dict[str, ModelConfig] = {
    # Single VL models (vl mode)
    "deqa-score-mix3": ModelConfig(
        model_id="deqa-score-mix3",
        source=ModelSource.HUGGINGFACE,
        model_path="zhiyuanyou/DeQA-Score-Mix3",
        architecture="mplug_owl2",
        dimensions=[QualityDimension.OVERALL],
        training_method="full",
        resolution=448,
        notes="Original DeQA-Score Mix3 - overall quality only",
    ),
    "deqa-doc-mix": ModelConfig(
        model_id="deqa-doc-mix",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MIX_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="full",
        resolution=1024,
        notes="Multi-dimension mixed training model",
    ),
    # Dimension specialists (specialist_true mode) - True DIQA_model from ModelScope
    # Full fine-tuned variants (higher accuracy, more parameters) - ~52GB total
    "diqa-overall": ModelConfig(
        model_id="diqa-overall",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.OVERALL],
        training_method="full",
        resolution=1024,
        checkpoint_subdir="deqa_0618_overall_norm_pair_1024",
        notes="Dimension specialist for overall quality",
    ),
    "diqa-sharpness": ModelConfig(
        model_id="diqa-sharpness",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.SHARPNESS],
        training_method="full",
        resolution=1024,
        checkpoint_subdir="deqa_0618_sharpness_norm_pair_1024",
        notes="Dimension specialist for sharpness",
    ),
    "diqa-color": ModelConfig(
        model_id="diqa-color",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.COLOR],
        training_method="full",
        resolution=1024,
        checkpoint_subdir="deqa_0618_color_norm_pair_1024",
        notes="Dimension specialist for color fidelity",
    ),
    # LoRA fine-tuned variants (faster, fewer parameters)
    "diqa-overall-lora": ModelConfig(
        model_id="diqa-overall-lora",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.OVERALL],
        training_method="lora",
        resolution=1024,
        checkpoint_subdir="deqa_lora_0623_overall_norm_pair_1024",
        notes="Dimension specialist for overall quality (LoRA)",
    ),
    "diqa-sharpness-lora": ModelConfig(
        model_id="diqa-sharpness-lora",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.SHARPNESS],
        training_method="lora",
        resolution=1024,
        checkpoint_subdir="deqa_lora_0623_sharpness_norm_pair_1024",
        notes="Dimension specialist for sharpness (LoRA)",
    ),
    "diqa-color-lora": ModelConfig(
        model_id="diqa-color-lora",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[QualityDimension.COLOR],
        training_method="lora",
        resolution=1024,
        checkpoint_subdir="deqa_lora_0623_color_norm_pair_1024",
        notes="Dimension specialist for color fidelity (LoRA)",
    ),
    # Ensemble models (ensemble mode) - mPLUG-Owl2 variants
    "m0": ModelConfig(
        model_id="m0",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="full",
        resolution=1024,
        notes="mPLUG-Owl2 full tuning variant",
    ),
    "m1": ModelConfig(
        model_id="m1",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="lora",
        resolution=1024,
        notes="mPLUG-Owl2 LoRA variant",
    ),
    "m3": ModelConfig(
        model_id="m3",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="mplug_owl2",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="lora",
        resolution=1024,
        pretrain_dataset="koniq-10k",
        notes="mPLUG-Owl2 LoRA with KonIQ-10k pretraining",
    ),
    # Ensemble models - Qwen2.5-VL variants
    "Q0": ModelConfig(
        model_id="Q0",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="qwen_vl",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="full",
        resolution="dynamic",
        notes="Qwen2.5-VL full tuning variant",
    ),
    "Q1": ModelConfig(
        model_id="Q1",
        source=ModelSource.MODELSCOPE,
        model_path=DEQA_DOC_MODEL_PATH,
        architecture="qwen_vl",
        dimensions=[
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ],
        training_method="full",
        resolution="dynamic",
        notes="Qwen2.5-VL 5-fold ensemble variant",
    ),
}


# Dataset configurations for supported benchmark datasets
@dataclass
class DatasetConfig:
    """Configuration for a benchmark dataset."""

    name: str
    manifest_path: str
    root_dir: str
    num_images: int
    priority: str  # CRITICAL, HIGH, MEDIUM
    has_ground_truth: bool = True
    dimensions: list[QualityDimension] = field(
        default_factory=lambda: [
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ]
    )


# Manifest base path (configured for E: drive staging)
MANIFEST_BASE = "/mnt/e/image_detection/06_staging/stage1_manifests"
DATA_BASE = "/mnt/e/image_detection"

DATASET_CONFIGS: dict[str, DatasetConfig] = {
    "diqa-5000": DatasetConfig(
        name="diqa-5000",
        manifest_path=f"{MANIFEST_BASE}/diqa-5000_manifest.json",
        root_dir=f"{DATA_BASE}/02_benchmark_only/diqa-5000",
        num_images=5000,
        priority="CRITICAL",
    ),
    "smartdoc-qa": DatasetConfig(
        name="smartdoc-qa",
        manifest_path=f"{MANIFEST_BASE}/smartdoc-qa_manifest.json",
        root_dir=f"{DATA_BASE}/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images",
        num_images=4260,
        priority="HIGH",
        has_ground_truth=False,
    ),
    "ocr-quality": DatasetConfig(
        name="ocr-quality",
        manifest_path=f"{MANIFEST_BASE}/ocr-quality_manifest.json",
        root_dir=f"{DATA_BASE}/01_base_data/ocr_quality/pics",
        num_images=1000,
        priority="HIGH",
        has_ground_truth=False,
    ),
    "dibco": DatasetConfig(
        name="dibco",
        manifest_path=f"{MANIFEST_BASE}/dibco_manifest.json",
        root_dir=f"{DATA_BASE}/02_benchmark_only/dibco/DIBCO",
        num_images=148,
        priority="HIGH",
        has_ground_truth=False,
    ),
    "funsd": DatasetConfig(
        name="funsd",
        manifest_path=f"{MANIFEST_BASE}/funsd_manifest.json",
        root_dir=f"{DATA_BASE}/01_base_data/forms/funsd",
        num_images=149,
        priority="MEDIUM",
        has_ground_truth=False,
    ),
    "sroie": DatasetConfig(
        name="sroie",
        manifest_path=f"{MANIFEST_BASE}/sroie_manifest.json",
        root_dir=f"{DATA_BASE}/01_base_data/forms/sroie",
        num_images=2043,
        priority="MEDIUM",
        has_ground_truth=False,
    ),
    "tobacco-800": DatasetConfig(
        name="tobacco-800",
        manifest_path=f"{MANIFEST_BASE}/tobacco-800_manifest.json",
        root_dir=f"{DATA_BASE}/01_base_data/degraded/tobacco800",
        num_images=1290,
        priority="MEDIUM",
        has_ground_truth=False,
    ),
}


@dataclass
class DeQAConfig:
    """Main configuration for DeQA labeling inference.

    Attributes:
        mode: Inference mode (specialist, ensemble, vl).
        model_id: Model identifier for vl mode (ignored for other modes).
        device: Device to run inference on.
        quantization: Quantization mode (fp16, 8bit, 4bit).
        batch_size: Batch size for inference.
        checkpoint_interval: Save checkpoint every N images.
        output_dir: Output directory for results.
        dimensions: Which dimensions to predict (default: all 3).
    """

    mode: InferenceMode
    model_id: str | None = None  # For vl mode
    device: str = "cuda:0"
    quantization: str = "fp16"
    batch_size: int = 8
    checkpoint_interval: int = 500
    output_dir: Path = Path("/results")
    dimensions: list[QualityDimension] = field(
        default_factory=lambda: [
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ]
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if isinstance(self.mode, str):
            self.mode = InferenceMode(self.mode)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Validate model_id for vl mode
        if self.mode == InferenceMode.VL and self.model_id is None:
            self.model_id = "deqa-score-mix3"  # Default

    def get_model_configs(self) -> list[ModelConfig]:
        """Get model configurations for the selected mode.

        Returns:
            List of ModelConfig instances for the inference mode.
        """
        if self.mode == InferenceMode.SPECIALIST:
            # Baseline: Single Mix3 model with dimension-specific prompts
            return [MODEL_REGISTRY["deqa-score-mix3"]]
        if self.mode == InferenceMode.SPECIALIST_TRUE:
            # True specialists: 3 separate models, each trained for one dimension
            return [
                MODEL_REGISTRY["diqa-overall"],
                MODEL_REGISTRY["diqa-sharpness"],
                MODEL_REGISTRY["diqa-color"],
            ]
        if self.mode == InferenceMode.ENSEMBLE:
            return [
                MODEL_REGISTRY["m0"],
                MODEL_REGISTRY["m1"],
                MODEL_REGISTRY["m3"],
                MODEL_REGISTRY["Q0"],
                MODEL_REGISTRY["Q1"],
            ]
        if self.mode == InferenceMode.VL:
            if self.model_id and self.model_id in MODEL_REGISTRY:
                return [MODEL_REGISTRY[self.model_id]]
            # Custom model not in registry
            return [
                ModelConfig(
                    model_id=self.model_id or "custom",
                    source=ModelSource.HUGGINGFACE,
                    model_path=self.model_id or "",
                    architecture="mplug_owl2",
                    dimensions=self.dimensions,
                )
            ]
        return []

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary."""
        return {
            "mode": self.mode.value,
            "model_id": self.model_id,
            "device": self.device,
            "quantization": self.quantization,
            "batch_size": self.batch_size,
            "checkpoint_interval": self.checkpoint_interval,
            "output_dir": str(self.output_dir),
            "dimensions": [d.value for d in self.dimensions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeQAConfig:
        """Deserialize configuration from dictionary."""
        return cls(
            mode=InferenceMode(data["mode"]),
            model_id=data.get("model_id"),
            device=data.get("device", "cuda:0"),
            quantization=data.get("quantization", "fp16"),
            batch_size=data.get("batch_size", 8),
            checkpoint_interval=data.get("checkpoint_interval", 500),
            output_dir=Path(data.get("output_dir", "/results")),
            dimensions=[QualityDimension(d) for d in data.get("dimensions", [])],
        )


# Prompt templates for different dimensions
DIMENSION_PROMPTS: dict[QualityDimension, str] = {
    QualityDimension.OVERALL: "How would you rate the overall quality of this image?",
    QualityDimension.SHARPNESS: "How would you rate the sharpness of this image?",
    QualityDimension.COLOR: "How would you rate the color fidelity of this image?",
}

# Generic quality prompt (for models that output all dimensions)
GENERIC_QUALITY_PROMPT = "How would you rate the quality of this image?"
