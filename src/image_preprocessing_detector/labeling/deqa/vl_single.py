"""Single VL model inference mode.

This module implements the 'vl' inference mode which uses a single
configurable vision-language model for quality assessment. This is
the fastest mode and supports custom model evaluation.
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
    GENERIC_QUALITY_PROMPT,
    QUALITY_LEVELS,
    DeQAConfig,
    ModelSource,
)

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

# HuggingFace model revision for reproducibility (B615 security)
_HF_REVISION = "main"


class VLSingleInference(DeQAInference):
    """Single vision-language model inference.

    Uses a single VLM (e.g., DeQA-Score-Mix3) for fast quality assessment.
    Best for rapid labeling and model evaluation.

    Attributes:
        model: Loaded model instance.
        tokenizer: Model tokenizer.
        image_processor: Image preprocessing pipeline.
        token_ids: Token IDs for quality level words.
    """

    def __init__(self, config: DeQAConfig) -> None:
        """Initialize VL single inference.

        Args:
            config: Inference configuration.
        """
        super().__init__(config)
        self.model: Any = None
        self.tokenizer: Any = None
        self.image_processor: Any = None
        self.token_ids: list[int] = []
        self.input_ids: Any = None

    def load_models(self, device: str | None = None) -> None:
        """Load the VL model.

        Args:
            device: Device to load model on. Defaults to config.device.
        """
        if self._loaded:
            logger.warning("Models already loaded")
            return

        device = device or self.config.device
        model_configs = self.config.get_model_configs()

        if not model_configs:
            msg = "No model configuration found"
            raise ValueError(msg)

        model_config = model_configs[0]
        logger.info(
            "Loading model: %s from %s", model_config.model_id, model_config.model_path
        )

        if model_config.source == ModelSource.HUGGINGFACE:
            self._load_from_huggingface(model_config.model_path, device)
        elif model_config.source == ModelSource.MODELSCOPE:
            self._load_from_modelscope(model_config.model_path, device)
        else:
            msg = f"Unsupported model source: {model_config.source}"
            raise ValueError(msg)

        self._setup_prompt()
        self._loaded = True
        logger.info("Model loaded successfully")

    def _load_from_huggingface(self, model_path: str, device: str) -> None:
        """Load model from HuggingFace.

        This method uses the DeQA-Score loading pattern for mPLUG-Owl2 models.

        Args:
            model_path: HuggingFace model path.
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
                self._load_quantized_model(model_path, model_name, device)
            else:
                self.tokenizer, self.model, self.image_processor, _ = (
                    load_pretrained_model(model_path, None, model_name, device=device)
                )
        except ImportError:
            logger.warning("DeQA-Score not available, using transformers fallback")
            self._load_with_transformers(model_path, device)

    def _load_quantized_model(
        self, model_path: str, model_name: str, device: str
    ) -> None:
        """Load model with quantization.

        Args:
            model_path: Model path.
            model_name: Model name for loader.
            device: Device to load on.
        """
        import torch
        from src.model.builder import load_pretrained_model
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig

        # Load tokenizer and processor
        self.tokenizer, _, self.image_processor, _ = load_pretrained_model(
            model_path, None, model_name, device=device
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
        self.model = AutoModelForCausalLM.from_pretrained(  # nosec B615
            model_path,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
            revision=_HF_REVISION,  # branch revision for research; production uses commit hash
        )

    def _load_with_transformers(self, model_path: str, device: str) -> None:  # noqa: ARG002  # NOSONAR - device handled by device_map
        """Fallback loading using transformers library.

        Args:
            model_path: Model path.
            device: Device to load on (unused, device_map="auto" handles this).
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.image_processor = AutoProcessor.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.model = AutoModelForCausalLM.from_pretrained(  # nosec B615
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            revision=_HF_REVISION,  # branch revision for research; production uses commit hash
        )

    def _load_from_modelscope(self, model_path: str, device: str) -> None:
        """Load model from ModelScope.

        Args:
            model_path: ModelScope model path.
            device: Device to load on.
        """
        try:
            from modelscope import snapshot_download

            # Download model to local cache
            local_path = snapshot_download(model_path)
            logger.info("Downloaded model to: %s", local_path)

            # Load using HuggingFace method
            self._load_from_huggingface(local_path, device)
        except ImportError:
            msg = "ModelScope SDK not installed. Install with: pip install modelscope"
            raise ImportError(msg) from None

    def _setup_prompt(self) -> None:
        """Set up the prompt template and token IDs."""
        try:
            from src.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
            from src.conversation import conv_templates
            from src.mm_utils import tokenizer_image_token

            # Use mPLUG-Owl2 conversation template
            conv = conv_templates["mplug_owl2"].copy()
            inp = GENERIC_QUALITY_PROMPT + "\n" + DEFAULT_IMAGE_TOKEN
            conv.append_message(conv.roles[0], inp)
            conv.append_message(conv.roles[1], None)
            prompt = conv.get_prompt() + " The quality of the image is"

            # Get token IDs for quality levels
            self.token_ids = [
                self.tokenizer(level)["input_ids"][1] for level in QUALITY_LEVELS
            ]

            # Tokenize prompt
            self.input_ids = (
                tokenizer_image_token(
                    prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
                )
                .unsqueeze(0)
                .to(self.config.device)
            )

            # NLP tokenizer IDs for quality level vocabulary (not credentials)
            logger.info(  # nosemgrep: python-logger-credential-disclosure
                "Token IDs for quality levels: %s", self.token_ids
            )

        except ImportError:
            logger.warning("DeQA-Score templates not available, using simple prompt")
            self._setup_simple_prompt()

    def _setup_simple_prompt(self) -> None:
        """Set up a simple prompt without DeQA-Score templates."""
        prompt = f"{GENERIC_QUALITY_PROMPT} The quality of the image is"
        self.input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.to(
            self.config.device
        )

        # Get token IDs for quality levels
        self.token_ids = [
            self.tokenizer(level)["input_ids"][0] for level in QUALITY_LEVELS
        ]

    def unload_models(self) -> None:
        """Unload model and free GPU memory."""
        if not self._loaded:
            return

        import torch

        del self.model
        del self.tokenizer
        del self.image_processor
        del self.input_ids

        self.model = None
        self.tokenizer = None
        self.image_processor = None
        self.input_ids = None
        self.token_ids = []

        gc.collect()
        torch.cuda.empty_cache()

        self._loaded = False
        logger.info("Models unloaded")

    def predict(self, image: Image.Image) -> dict[str, DeQAScore]:
        """Generate quality scores for an image.

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

        import torch

        # Preprocess image
        image_tensor = self._preprocess_vl_image(image)

        # Run inference
        with torch.inference_mode():
            output = self.model(
                input_ids=self.input_ids,
                images=image_tensor,
            )
            logits = output["logits"][:, -1]

        # Extract scores for quality levels
        level_logits = {
            level: logits[0, token_id].item()
            for level, token_id in zip(QUALITY_LEVELS, self.token_ids, strict=True)
        }

        # Compute probabilities
        probs = self.normalize_logits_to_probs(level_logits)

        # Compute final score
        score = self.compute_score_from_probs(probs)

        # Get model config
        model_config = self.config.get_model_configs()[0]

        # Create scores for all dimensions the model supports
        results = {}
        for dim in model_config.dimensions:
            results[dim.value] = DeQAScore(
                dimension=dim,
                score=score,
                logits=level_logits,
                probs=probs,
                model_id=model_config.model_id,
            )

        return results

    # Note: expand_to_square is inherited from base class for code deduplication.
    # _preprocess_vl_image is a thin wrapper that uses self.image_processor.

    def _preprocess_vl_image(self, image: Image.Image) -> Any:
        """Preprocess image for VL model input.

        Uses inherited preprocess_image from base class with self.image_processor.

        Args:
            image: PIL Image.

        Returns:
            Preprocessed image tensor.
        """
        return self.preprocess_image(image, self.image_processor)

    def predict_batch(
        self,
        images: list[Image.Image],
    ) -> list[dict[str, DeQAScore]]:
        """Generate quality scores for a batch of images.

        Uses batched inference for efficiency.

        Args:
            images: List of PIL Images to assess.

        Returns:
            List of dictionaries mapping dimension to DeQAScore.
        """
        if not self._loaded:
            msg = "Models not loaded. Call load_models() first."
            raise RuntimeError(msg)

        import torch

        # Preprocess all images
        image_tensors = [self._preprocess_vl_image(img) for img in images]
        batched_images = torch.cat(image_tensors, dim=0)

        # Run batched inference
        batch_size = len(images)
        with torch.inference_mode():
            output = self.model(
                input_ids=self.input_ids.repeat(batch_size, 1),
                images=batched_images,
            )
            logits = output["logits"][:, -1]

        # Extract results for each image
        results = []
        model_config = self.config.get_model_configs()[0]

        for i in range(batch_size):
            level_logits = {
                level: logits[i, token_id].item()
                for level, token_id in zip(QUALITY_LEVELS, self.token_ids, strict=True)
            }
            probs = self.normalize_logits_to_probs(level_logits)
            score = self.compute_score_from_probs(probs)

            image_results = {}
            for dim in model_config.dimensions:
                image_results[dim.value] = DeQAScore(
                    dimension=dim,
                    score=score,
                    logits=level_logits,
                    probs=probs,
                    model_id=model_config.model_id,
                )
            results.append(image_results)

        return results
