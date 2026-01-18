"""Specialist dimension-specific inference mode.

This module implements the 'specialist' inference mode which uses 3 separate
CNN models trained specifically for each quality dimension (overall, sharpness,
color). This provides focused per-dimension accuracy.
"""

from __future__ import annotations

import gc
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.labeling.deqa.base import (
    DeQAInference,
    DeQAScore,
)
from image_preprocessing_detector.labeling.deqa.config import (
    DIMENSION_PROMPTS,
    QUALITY_LEVELS,
    DeQAConfig,
    ModelConfig,
    ModelSource,
    QualityDimension,
)

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

# HuggingFace model revision for reproducibility
_HF_REVISION = "main"


class SpecialistInference(DeQAInference):
    """Dimension-specific specialist model inference.

    Uses 3 separate models (DIQA_model variants) each trained specifically
    for one quality dimension. Each model outputs only its specialized
    dimension, providing focused accuracy at the cost of 3x inference passes.

    Attributes:
        models: Dictionary mapping dimension to loaded model.
        tokenizers: Dictionary mapping dimension to tokenizer.
        processors: Dictionary mapping dimension to image processor.
        token_ids: Dictionary mapping dimension to quality level token IDs.
        input_ids: Dictionary mapping dimension to preprocessed prompt tensors.
    """

    def __init__(self, config: DeQAConfig) -> None:
        """Initialize specialist inference.

        Args:
            config: Inference configuration.
        """
        super().__init__(config)
        self.models: dict[str | QualityDimension, Any] = {}
        self.tokenizers: dict[str | QualityDimension, Any] = {}
        self.processors: dict[str | QualityDimension, Any] = {}
        self.token_ids: dict[str | QualityDimension, list[int]] = {}
        self.input_ids: dict[str | QualityDimension, Any] = {}
        self._model_configs: dict[QualityDimension, ModelConfig] = {}

    def load_models(self, device: str | None = None) -> None:
        """Load all 3 dimension specialist models.

        Args:
            device: Device to load models on. Defaults to config.device.
        """
        if self._loaded:
            logger.warning("Models already loaded")
            return

        device = device or self.config.device
        model_configs = self.config.get_model_configs()

        for model_config in model_configs:
            dimension = model_config.dimensions[0]  # Specialists have 1 dimension
            logger.info(
                "Loading specialist model for %s: %s",
                dimension.value,
                model_config.model_id,
            )

            self._model_configs[dimension] = model_config

            if model_config.source == ModelSource.MODELSCOPE:
                self._load_from_modelscope(model_config, dimension, device)
            elif model_config.source == ModelSource.HUGGINGFACE:
                self._load_from_huggingface(model_config, dimension, device)
            else:
                msg = f"Unsupported model source: {model_config.source}"
                raise ValueError(msg)

            self._setup_prompt(dimension)

        self._loaded = True
        logger.info("All specialist models loaded successfully")

    def _load_from_modelscope(
        self,
        model_config: ModelConfig,
        dimension: QualityDimension,
        device: str,
    ) -> None:
        """Load model from ModelScope.

        Args:
            model_config: Model configuration.
            dimension: Quality dimension this model handles.
            device: Device to load on.
        """
        try:
            from modelscope import snapshot_download

            # Download model to local cache
            # For specialists, download the dimension-specific checkpoint
            local_path = snapshot_download(
                model_config.model_path,
                revision="master",
            )
            logger.info("Downloaded model to: %s", local_path)

            # Load using DeQA-Score pattern
            self._load_mplug_model(local_path, dimension, device)
        except ImportError:
            msg = "ModelScope SDK not installed. Install with: pip install modelscope"
            raise ImportError(msg) from None

    def _load_from_huggingface(
        self,
        model_config: ModelConfig,
        dimension: QualityDimension,
        device: str,
    ) -> None:
        """Load model from HuggingFace.

        Args:
            model_config: Model configuration.
            dimension: Quality dimension this model handles.
            device: Device to load on.
        """
        self._load_mplug_model(model_config.model_path, dimension, device)

    def _load_mplug_model(
        self,
        model_path: str,
        dimension: QualityDimension,
        device: str,
    ) -> None:
        """Load mPLUG-Owl2 model using DeQA-Score pattern.

        Args:
            model_path: Path to model weights.
            dimension: Quality dimension this model handles.
            device: Device to load on.
        """
        import sys

        # Add DeQA-Score to path (allow override via DEQA_SCORE_PATH env var)
        deqa_score_path = os.environ.get("DEQA_SCORE_PATH", "/opt/DeQA-Score")
        if Path(deqa_score_path).is_dir() and deqa_score_path not in sys.path:
            sys.path.insert(0, deqa_score_path)

        try:
            from src.mm_utils import get_model_name_from_path
            from src.model.builder import load_pretrained_model

            model_name = get_model_name_from_path(model_path)

            # Load with DeQA-Score's loader
            if self.config.quantization in ("8bit", "4bit"):
                self._load_quantized_model(model_path, model_name, dimension, device)
            else:
                (
                    self.tokenizers[dimension],
                    self.models[dimension],
                    self.processors[dimension],
                    _,
                ) = load_pretrained_model(model_path, None, model_name, device=device)
        except ImportError:
            logger.warning("DeQA-Score not available, using transformers fallback")
            self._load_with_transformers(model_path, dimension, device)

    def _load_quantized_model(
        self,
        model_path: str,
        model_name: str,
        dimension: QualityDimension,
        device: str,
    ) -> None:
        """Load model with quantization.

        Args:
            model_path: Model path.
            model_name: Model name for loader.
            dimension: Quality dimension.
            device: Device to load on.
        """
        import torch
        from src.model.builder import load_pretrained_model
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig

        # Load tokenizer and processor
        self.tokenizers[dimension], _, self.processors[dimension], _ = (
            load_pretrained_model(model_path, None, model_name, device=device)
        )

        # Configure quantization
        if self.config.quantization == "4bit":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:  # 8bit
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
            )

        # Load model with quantization
        self.models[dimension] = AutoModelForCausalLM.from_pretrained(  # nosec B615
            model_path,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
            revision=_HF_REVISION,  # branch revision for research; production uses commit hash
        )

    def _load_with_transformers(
        self,
        model_path: str,
        dimension: QualityDimension,
        device: str,  # noqa: ARG002  # NOSONAR - device handled by device_map
    ) -> None:
        """Fallback loading using transformers library.

        Args:
            model_path: Model path.
            dimension: Quality dimension.
            device: Device to load on (unused, device_map="auto" handles this).
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

        self.tokenizers[dimension] = AutoTokenizer.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.processors[dimension] = AutoProcessor.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.models[dimension] = AutoModelForCausalLM.from_pretrained(  # nosec B615
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            revision=_HF_REVISION,  # branch revision for research; production uses commit hash
        )

    def _setup_prompt(self, dimension: QualityDimension) -> None:
        """Set up the prompt template and token IDs for a dimension.

        Args:
            dimension: Quality dimension to set up.
        """
        try:
            from src.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
            from src.conversation import conv_templates
            from src.mm_utils import tokenizer_image_token

            tokenizer = self.tokenizers[dimension]

            # Use dimension-specific prompt
            prompt_text = DIMENSION_PROMPTS[dimension]

            # Use mPLUG-Owl2 conversation template
            conv = conv_templates["mplug_owl2"].copy()
            inp = prompt_text + "\n" + DEFAULT_IMAGE_TOKEN
            conv.append_message(conv.roles[0], inp)
            conv.append_message(conv.roles[1], None)
            prompt = conv.get_prompt() + " The quality of the image is"

            # Get token IDs for quality levels
            self.token_ids[dimension] = [
                tokenizer(level)["input_ids"][1] for level in QUALITY_LEVELS
            ]

            # Tokenize prompt
            self.input_ids[dimension] = (
                tokenizer_image_token(
                    prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
                )
                .unsqueeze(0)
                .to(self.config.device)
            )

            # NLP tokenizer IDs for quality level vocabulary (not credentials)
            logger.info(  # nosemgrep: python-logger-credential-disclosure
                "Token IDs for %s dimension: %s",
                dimension.value,
                self.token_ids[dimension],
            )

        except ImportError:
            logger.warning("DeQA-Score templates not available, using simple prompt")
            self._setup_simple_prompt(dimension)

    def _setup_simple_prompt(self, dimension: QualityDimension) -> None:
        """Set up a simple prompt without DeQA-Score templates.

        Args:
            dimension: Quality dimension to set up.
        """
        tokenizer = self.tokenizers[dimension]
        prompt_text = DIMENSION_PROMPTS[dimension]
        prompt = f"{prompt_text} The quality of the image is"

        self.input_ids[dimension] = tokenizer(prompt, return_tensors="pt").input_ids.to(
            self.config.device
        )

        # Get token IDs for quality levels
        self.token_ids[dimension] = [
            tokenizer(level)["input_ids"][0] for level in QUALITY_LEVELS
        ]

    def unload_models(self) -> None:
        """Unload all models and free GPU memory."""
        if not self._loaded:
            return

        import torch

        # list() required: we delete keys while iterating, need a copy
        for dimension in list(self.models.keys()):
            del self.models[dimension]
            del self.tokenizers[dimension]
            del self.processors[dimension]
            if dimension in self.input_ids:
                del self.input_ids[dimension]

        self.models.clear()
        self.tokenizers.clear()
        self.processors.clear()
        self.input_ids.clear()
        self.token_ids.clear()

        gc.collect()
        torch.cuda.empty_cache()

        self._loaded = False
        logger.info("All specialist models unloaded")

    def predict(self, image: Image.Image) -> dict[str, DeQAScore]:
        """Generate quality scores for an image using all 3 specialists.

        Args:
            image: PIL Image to assess.

        Returns:
            Dictionary mapping dimension to DeQAScore.

        Raises:
            RuntimeError: If models are not loaded.
        """
        if not self._loaded:
            msg = "Models not loaded. Call load_models() first."
            raise RuntimeError(msg)

        results: dict[str, DeQAScore] = {}

        for dimension in [
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ]:
            if dimension not in self.models:
                continue

            score = self._predict_single_dimension(image, dimension)
            results[dimension.value] = score

        return results

    def _predict_single_dimension(
        self,
        image: Image.Image,
        dimension: QualityDimension,
    ) -> DeQAScore:
        """Generate quality score for a single dimension.

        Args:
            image: PIL Image to assess.
            dimension: Quality dimension to predict.

        Returns:
            DeQAScore for the dimension.
        """
        import torch

        # Get model components for this dimension
        model = self.models[dimension]
        processor = self.processors[dimension]
        input_ids = self.input_ids[dimension]
        token_ids = self.token_ids[dimension]
        model_config = self._model_configs[dimension]

        # Preprocess image
        image_tensor = self.preprocess_image(image, processor)

        # Run inference
        with torch.inference_mode():
            output = model(
                input_ids=input_ids,
                images=image_tensor,
            )
            logits = output["logits"][:, -1]

        # Extract scores for quality levels
        level_logits = {
            level: logits[0, token_id].item()
            for level, token_id in zip(QUALITY_LEVELS, token_ids, strict=True)
        }

        # Compute probabilities
        probs = self.normalize_logits_to_probs(level_logits)

        # Compute final score
        score = self.compute_score_from_probs(probs)

        return DeQAScore(
            dimension=dimension,
            score=score,
            logits=level_logits,
            probs=probs,
            model_id=model_config.model_id,
        )

    # Note: _preprocess_image and _expand_to_square are inherited from base class
    # as preprocess_image and expand_to_square for code deduplication

    def predict_batch(
        self,
        images: list[Image.Image],
    ) -> list[dict[str, DeQAScore]]:
        """Generate quality scores for a batch of images.

        For specialist mode, processes each dimension separately in batch,
        then combines results per image.

        Args:
            images: List of PIL Images to assess.

        Returns:
            List of dictionaries mapping dimension to DeQAScore.
        """
        if not self._loaded:
            msg = "Models not loaded. Call load_models() first."
            raise RuntimeError(msg)

        batch_size = len(images)

        # Collect scores per dimension
        dimension_scores: dict[QualityDimension, list[DeQAScore]] = {}

        for dimension in [
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ]:
            if dimension not in self.models:
                continue

            dimension_scores[dimension] = self._predict_batch_single_dimension(
                images, dimension
            )

        # Combine into per-image results
        results = []
        for i in range(batch_size):
            image_results = {}
            for dimension, scores in dimension_scores.items():
                image_results[dimension.value] = scores[i]
            results.append(image_results)

        return results

    def _predict_batch_single_dimension(
        self,
        images: list[Image.Image],
        dimension: QualityDimension,
    ) -> list[DeQAScore]:
        """Generate quality scores for a batch on single dimension.

        Args:
            images: List of PIL Images.
            dimension: Quality dimension to predict.

        Returns:
            List of DeQAScore for the dimension.
        """
        import torch

        model = self.models[dimension]
        processor = self.processors[dimension]
        input_ids = self.input_ids[dimension]
        token_ids = self.token_ids[dimension]
        model_config = self._model_configs[dimension]

        # Preprocess all images
        image_tensors = [self.preprocess_image(img, processor) for img in images]
        batched_images = torch.cat(image_tensors, dim=0)

        batch_size = len(images)

        # Run batched inference
        with torch.inference_mode():
            output = model(
                input_ids=input_ids.repeat(batch_size, 1),
                images=batched_images,
            )
            logits = output["logits"][:, -1]

        # Extract results for each image
        results = []
        for i in range(batch_size):
            level_logits = {
                level: logits[i, token_id].item()
                for level, token_id in zip(QUALITY_LEVELS, token_ids, strict=True)
            }
            probs = self.normalize_logits_to_probs(level_logits)
            score = self.compute_score_from_probs(probs)

            results.append(
                DeQAScore(
                    dimension=dimension,
                    score=score,
                    logits=level_logits,
                    probs=probs,
                    model_id=model_config.model_id,
                )
            )

        return results
