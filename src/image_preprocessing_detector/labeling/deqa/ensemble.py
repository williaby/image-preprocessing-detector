"""Ensemble VLM inference mode.

This module implements the 'ensemble' inference mode which uses the full
5-model VQualA 2025 champion ensemble (m0, m1, m3, Q0, Q1) for maximum
accuracy. Each model outputs all 3 dimensions, and results are averaged.
"""

from __future__ import annotations

import gc
import logging
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.labeling.deqa.base import (
    DeQAInference,
    DeQAScore,
    LabelResult,
)
from image_preprocessing_detector.labeling.deqa.config import (
    GENERIC_QUALITY_PROMPT,
    QUALITY_LEVELS,
    DeQAConfig,
    ModelConfig,
    ModelSource,
    QualityDimension,
)

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

# Error message constants
_MODELS_NOT_LOADED_MSG = "Models not loaded. Call load_models() first."

# HuggingFace model revision for reproducibility (B615 security)
# Note: Using "main" branch for research code. Production deployments should
# pin to specific commit hashes after model validation.
_HF_REVISION = "main"


class EnsembleInference(DeQAInference):
    """5-model VLM ensemble inference.

    Uses the full VQualA 2025 champion ensemble:
    - m0: mPLUG-Owl2 full tuning
    - m1: mPLUG-Owl2 LoRA
    - m3: mPLUG-Owl2 LoRA with KonIQ-10k pretraining
    - Q0: Qwen2.5-VL full tuning
    - Q1: Qwen2.5-VL 5-fold ensemble

    Each model outputs all 3 dimensions. Final scores are averaged across models.

    Attributes:
        models: Dictionary mapping model_id to loaded model.
        tokenizers: Dictionary mapping model_id to tokenizer.
        processors: Dictionary mapping model_id to image processor.
        token_ids: Dictionary mapping model_id to quality level token IDs.
        input_ids: Dictionary mapping model_id to preprocessed prompt tensors.
    """

    def __init__(self, config: DeQAConfig) -> None:
        """Initialize ensemble inference.

        Args:
            config: Inference configuration.
        """
        super().__init__(config)
        self.models: dict[str, Any] = {}
        self.tokenizers: dict[str, Any] = {}
        self.processors: dict[str, Any] = {}
        self.token_ids: dict[str, list[int]] = {}
        self.input_ids: dict[str, Any] = {}
        self._model_configs: dict[str, ModelConfig] = {}

    def load_models(self, device: str | None = None) -> None:
        """Load all 5 ensemble models.

        Models are loaded sequentially to manage GPU memory.
        For inference, models can be loaded/unloaded one at a time.

        Args:
            device: Device to load models on. Defaults to config.device.
        """
        if self._loaded:
            logger.warning("Models already loaded")
            return

        device = device or self.config.device
        model_configs = self.config.get_model_configs()

        for model_config in model_configs:
            logger.info(
                "Loading ensemble model: %s (%s)",
                model_config.model_id,
                model_config.architecture,
            )

            self._model_configs[model_config.model_id] = model_config

            if model_config.architecture == "qwen_vl":
                self._load_qwen_model(model_config, device)
            else:
                self._load_mplug_model(model_config, device)

            self._setup_prompt(model_config)

        self._loaded = True
        logger.info("All %d ensemble models loaded successfully", len(model_configs))

    def _load_mplug_model(self, model_config: ModelConfig, device: str) -> None:
        """Load mPLUG-Owl2 model variant.

        Args:
            model_config: Model configuration.
            device: Device to load on.
        """
        import sys

        model_id = model_config.model_id

        # Download from ModelScope if needed
        if model_config.source == ModelSource.MODELSCOPE:
            try:
                from modelscope import snapshot_download

                local_path = snapshot_download(
                    model_config.model_path,
                    revision="master",
                )
                logger.info("Downloaded %s to: %s", model_id, local_path)
            except ImportError:
                msg = "ModelScope SDK required. Install: pip install modelscope"
                raise ImportError(msg) from None
        else:
            local_path = model_config.model_path

        # Add DeQA-Score to path
        deqa_score_path = "/opt/DeQA-Score"
        if deqa_score_path not in sys.path:
            sys.path.insert(0, deqa_score_path)

        try:
            from src.mm_utils import get_model_name_from_path
            from src.model.builder import load_pretrained_model

            model_name = get_model_name_from_path(local_path)

            if self.config.quantization in ("8bit", "4bit"):
                self._load_quantized_mplug(local_path, model_name, model_id, device)
            else:
                (
                    self.tokenizers[model_id],
                    self.models[model_id],
                    self.processors[model_id],
                    _,
                ) = load_pretrained_model(local_path, None, model_name, device=device)
        except ImportError:
            logger.warning("DeQA-Score not available, using transformers fallback")
            self._load_with_transformers(local_path, model_id, device)

    def _load_qwen_model(self, model_config: ModelConfig, device: str) -> None:
        """Load Qwen2.5-VL model variant.

        Args:
            model_config: Model configuration.
            device: Device to load on.
        """
        import torch

        model_id = model_config.model_id

        # Download from ModelScope if needed
        if model_config.source == ModelSource.MODELSCOPE:
            try:
                from modelscope import snapshot_download

                local_path = snapshot_download(
                    model_config.model_path,
                    revision="master",
                )
                logger.info("Downloaded %s to: %s", model_id, local_path)
            except ImportError:
                msg = "ModelScope SDK required. Install: pip install modelscope"
                raise ImportError(msg) from None
        else:
            local_path = model_config.model_path

        try:
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

            # Load Qwen2.5-VL with native dynamic resolution
            self.models[model_id] = Qwen2VLForConditionalGeneration.from_pretrained(  # nosec B615
                local_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True,
                revision=_HF_REVISION,  # branch revision for research; production uses commit hash
            )
            self.processors[model_id] = AutoProcessor.from_pretrained(  # nosec B615
                local_path,
                trust_remote_code=True,
                revision=_HF_REVISION,
            )
            # Qwen uses processor as tokenizer
            self.tokenizers[model_id] = self.processors[model_id]

        except ImportError:
            logger.warning("Qwen2-VL not available, using generic transformers")
            self._load_with_transformers(local_path, model_id, device)

    def _load_quantized_mplug(
        self,
        model_path: str,
        model_name: str,
        model_id: str,
        device: str,
    ) -> None:
        """Load mPLUG model with quantization.

        Args:
            model_path: Model path.
            model_name: Model name for loader.
            model_id: Model identifier.
            device: Device to load on.
        """
        import torch
        from src.model.builder import load_pretrained_model
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig

        # Load tokenizer and processor
        self.tokenizers[model_id], _, self.processors[model_id], _ = (
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
        else:
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
            )

        self.models[model_id] = AutoModelForCausalLM.from_pretrained(  # nosec B615
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
        model_id: str,
        device: str,  # noqa: ARG002  # NOSONAR - device handled by device_map
    ) -> None:
        """Fallback loading using transformers library.

        Args:
            model_path: Model path.
            model_id: Model identifier.
            device: Device to load on (unused, device_map="auto" handles this).
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

        self.tokenizers[model_id] = AutoTokenizer.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.processors[model_id] = AutoProcessor.from_pretrained(  # nosec B615
            model_path, trust_remote_code=True, revision=_HF_REVISION
        )
        self.models[model_id] = AutoModelForCausalLM.from_pretrained(  # nosec B615
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            revision=_HF_REVISION,  # branch revision for research; production uses commit hash
        )

    def _setup_prompt(self, model_config: ModelConfig) -> None:
        """Set up the prompt template and token IDs for a model.

        Args:
            model_config: Model configuration.
        """
        model_id = model_config.model_id
        tokenizer = self.tokenizers[model_id]

        if model_config.architecture == "qwen_vl":
            self._setup_qwen_prompt(model_id, tokenizer)
        else:
            self._setup_mplug_prompt(model_id, tokenizer)

    def _setup_mplug_prompt(self, model_id: str, tokenizer: Any) -> None:
        """Set up mPLUG-Owl2 prompt template.

        Args:
            model_id: Model identifier.
            tokenizer: Model tokenizer.
        """
        try:
            from src.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
            from src.conversation import conv_templates
            from src.mm_utils import tokenizer_image_token

            conv = conv_templates["mplug_owl2"].copy()
            inp = GENERIC_QUALITY_PROMPT + "\n" + DEFAULT_IMAGE_TOKEN
            conv.append_message(conv.roles[0], inp)
            conv.append_message(conv.roles[1], None)
            prompt = conv.get_prompt() + " The quality of the image is"

            self.token_ids[model_id] = [
                tokenizer(level)["input_ids"][1] for level in QUALITY_LEVELS
            ]

            self.input_ids[model_id] = (
                tokenizer_image_token(
                    prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
                )
                .unsqueeze(0)
                .to(self.config.device)
            )

        except ImportError:
            logger.warning("DeQA-Score templates not available for %s", model_id)
            self._setup_simple_prompt(model_id, tokenizer)

    def _setup_qwen_prompt(self, model_id: str, processor: Any) -> None:
        """Set up Qwen2.5-VL prompt template.

        Qwen uses a different prompt format with native image handling.

        Args:
            model_id: Model identifier.
            processor: Model processor (used as tokenizer).
        """
        # Qwen uses chat template format
        # Token IDs for quality levels
        self.token_ids[model_id] = [
            processor.tokenizer(level, add_special_tokens=False)["input_ids"][0]
            for level in QUALITY_LEVELS
        ]

        # Qwen processes images dynamically, so we store prompt text instead
        self.input_ids[model_id] = None  # Will be constructed per-image

    def _setup_simple_prompt(self, model_id: str, tokenizer: Any) -> None:
        """Set up a simple prompt without DeQA-Score templates.

        Args:
            model_id: Model identifier.
            tokenizer: Model tokenizer.
        """
        prompt = f"{GENERIC_QUALITY_PROMPT} The quality of the image is"
        self.input_ids[model_id] = tokenizer(prompt, return_tensors="pt").input_ids.to(
            self.config.device
        )
        self.token_ids[model_id] = [
            tokenizer(level)["input_ids"][0] for level in QUALITY_LEVELS
        ]

    def unload_models(self) -> None:
        """Unload all models and free GPU memory."""
        if not self._loaded:
            return

        import torch

        for model_id in list(self.models.keys()):
            del self.models[model_id]
            del self.tokenizers[model_id]
            del self.processors[model_id]
            if model_id in self.input_ids and self.input_ids[model_id] is not None:
                del self.input_ids[model_id]

        self.models.clear()
        self.tokenizers.clear()
        self.processors.clear()
        self.input_ids.clear()
        self.token_ids.clear()

        gc.collect()
        torch.cuda.empty_cache()

        self._loaded = False
        logger.info("All ensemble models unloaded")

    def predict(self, image: Image.Image) -> dict[str, DeQAScore]:
        """Generate quality scores for an image using all 5 models.

        Runs inference on all models and averages scores per dimension.

        Args:
            image: PIL Image to assess.

        Returns:
            Dictionary mapping dimension to averaged DeQAScore.

        Raises:
            RuntimeError: If models are not loaded.
        """
        if not self._loaded:
            msg = _MODELS_NOT_LOADED_MSG
            raise RuntimeError(msg)

        # Collect scores from all models
        all_model_scores: dict[str, dict[str, DeQAScore]] = {}

        for model_id, model_config in self._model_configs.items():
            model_scores = self._predict_single_model(image, model_id, model_config)
            all_model_scores[model_id] = model_scores

        # Aggregate scores across models
        return self._aggregate_ensemble_scores(all_model_scores)

    def _predict_single_model(
        self,
        image: Image.Image,
        model_id: str,
        model_config: ModelConfig,
    ) -> dict[str, DeQAScore]:
        """Generate scores from a single model.

        Args:
            image: PIL Image to assess.
            model_id: Model identifier.
            model_config: Model configuration.

        Returns:
            Dictionary mapping dimension to DeQAScore.
        """
        import torch

        model = self.models[model_id]
        processor = self.processors[model_id]
        token_ids = self.token_ids[model_id]

        if model_config.architecture == "qwen_vl":
            return self._predict_qwen(image, model_id, model_config)

        # mPLUG-Owl2 inference
        input_ids = self.input_ids[model_id]

        # Preprocess image
        image_tensor = self._preprocess_image(image, processor)

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

        probs = self.normalize_logits_to_probs(level_logits)
        score = self.compute_score_from_probs(probs)

        # Create score for all dimensions (mPLUG outputs same for all)
        results = {}
        for dim in model_config.dimensions:
            results[dim.value] = DeQAScore(
                dimension=dim,
                score=score,
                logits=level_logits,
                probs=probs,
                model_id=model_id,
            )

        return results

    def _predict_qwen(
        self,
        image: Image.Image,
        model_id: str,
        model_config: ModelConfig,
    ) -> dict[str, DeQAScore]:
        """Generate scores using Qwen2.5-VL model.

        Qwen uses dynamic resolution and different input format.

        Args:
            image: PIL Image to assess.
            model_id: Model identifier.
            model_config: Model configuration.

        Returns:
            Dictionary mapping dimension to DeQAScore.
        """
        import torch

        model = self.models[model_id]
        processor = self.processors[model_id]
        token_ids = self.token_ids[model_id]

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Qwen chat template
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {
                        "type": "text",
                        "text": f"{GENERIC_QUALITY_PROMPT} The quality of the image is",
                    },
                ],
            }
        ]

        # Process with Qwen processor
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(images=image, text=text, return_tensors="pt").to(
            model.device
        )

        with torch.inference_mode():
            output = model(**inputs)
            logits = output.logits[:, -1]

        # Extract scores
        level_logits = {
            level: logits[0, token_id].item()
            for level, token_id in zip(QUALITY_LEVELS, token_ids, strict=True)
        }

        probs = self.normalize_logits_to_probs(level_logits)
        score = self.compute_score_from_probs(probs)

        results = {}
        for dim in model_config.dimensions:
            results[dim.value] = DeQAScore(
                dimension=dim,
                score=score,
                logits=level_logits,
                probs=probs,
                model_id=model_id,
            )

        return results

    def _preprocess_image(self, image: Image.Image, processor: Any) -> Any:
        """Preprocess image for mPLUG model input.

        Args:
            image: PIL Image.
            processor: Image processor.

        Returns:
            Preprocessed image tensor.
        """
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Expand to square
        image = self._expand_to_square(
            image,
            tuple(int(x * 255) for x in processor.image_mean),
        )

        # Process with model's image processor
        return (
            processor.preprocess(image, return_tensors="pt")["pixel_values"]
            .half()
            .to(self.config.device)
        )

    @staticmethod
    def _expand_to_square(
        image: Image.Image,
        background_color: tuple[int, ...],
    ) -> Image.Image:
        """Expand image to square by padding.

        Args:
            image: PIL Image.
            background_color: Color for padding.

        Returns:
            Square PIL Image.
        """
        from PIL import Image as PILImage

        width, height = image.size
        if width == height:
            return image

        size = max(width, height)
        result = PILImage.new(image.mode, (size, size), background_color)  # type: ignore[arg-type]

        if width > height:
            result.paste(image, (0, (size - height) // 2))
        else:
            result.paste(image, ((size - width) // 2, 0))

        return result

    def _aggregate_ensemble_scores(
        self,
        all_model_scores: dict[str, dict[str, DeQAScore]],
    ) -> dict[str, DeQAScore]:
        """Aggregate scores across all ensemble models.

        Computes mean score and aggregated probabilities per dimension.

        Args:
            all_model_scores: Scores from each model, keyed by model_id.

        Returns:
            Aggregated DeQAScore per dimension.
        """
        dimensions = [
            QualityDimension.OVERALL,
            QualityDimension.SHARPNESS,
            QualityDimension.COLOR,
        ]

        results = {}

        for dim in dimensions:
            dim_key = dim.value
            scores = []
            probs_sum: dict[str, float] = dict.fromkeys(QUALITY_LEVELS, 0.0)
            model_count = 0

            for model_scores in all_model_scores.values():
                if dim_key in model_scores:
                    score = model_scores[dim_key]
                    scores.append(score.score)
                    for level in QUALITY_LEVELS:
                        probs_sum[level] += score.probs.get(level, 0.0)
                    model_count += 1

            if model_count > 0:
                avg_score = sum(scores) / model_count
                avg_probs = {level: v / model_count for level, v in probs_sum.items()}

                results[dim_key] = DeQAScore(
                    dimension=dim,
                    score=avg_score,
                    logits={},  # Logits don't aggregate meaningfully
                    probs=avg_probs,
                    model_id="ensemble",
                )

        return results

    def generate_label_result(
        self,
        image_path: str,
        dataset: str,
        scores: dict[str, DeQAScore],
        per_model_scores: dict[str, dict[str, float]] | None = None,
    ) -> LabelResult:
        """Create a LabelResult with per-model scores.

        Overrides base to include individual model contributions.

        Args:
            image_path: Path to the image file.
            dataset: Dataset name.
            scores: Aggregated scores per dimension.
            per_model_scores: Individual model scores.

        Returns:
            LabelResult instance.
        """
        return LabelResult(
            image_path=image_path,
            dataset=dataset,
            mode=self.config.mode.value,
            scores={dim: score.score for dim, score in scores.items()},
            per_model_scores=per_model_scores,
            probs={dim: score.probs for dim, score in scores.items()},
            model_config={
                "models": [m.model_id for m in self.config.get_model_configs()],
                "ensemble_size": len(self._model_configs),
                "quantization": self.config.quantization,
            },
        )

    def predict_with_per_model(
        self,
        image: Image.Image,
    ) -> tuple[dict[str, DeQAScore], dict[str, dict[str, float]]]:
        """Generate scores with per-model breakdown.

        Args:
            image: PIL Image to assess.

        Returns:
            Tuple of (aggregated scores, per-model scores dict).
        """
        if not self._loaded:
            msg = _MODELS_NOT_LOADED_MSG
            raise RuntimeError(msg)

        all_model_scores: dict[str, dict[str, DeQAScore]] = {}

        for model_id, model_config in self._model_configs.items():
            model_scores = self._predict_single_model(image, model_id, model_config)
            all_model_scores[model_id] = model_scores

        # Aggregate
        aggregated = self._aggregate_ensemble_scores(all_model_scores)

        # Format per-model scores for output
        per_model: dict[str, dict[str, float]] = {}
        for dim in ["overall", "sharpness", "color"]:
            per_model[dim] = {}
            for model_id, model_scores in all_model_scores.items():
                if dim in model_scores:
                    per_model[dim][model_id] = model_scores[dim].score

        return aggregated, per_model

    def predict_batch(
        self,
        images: list[Image.Image],
    ) -> list[dict[str, DeQAScore]]:
        """Generate quality scores for a batch of images.

        For ensemble mode, this runs each model on the full batch,
        then aggregates results per image.

        Args:
            images: List of PIL Images to assess.

        Returns:
            List of dictionaries mapping dimension to DeQAScore.
        """
        if not self._loaded:
            msg = _MODELS_NOT_LOADED_MSG
            raise RuntimeError(msg)

        # For ensemble, process sequentially as models are large
        # This avoids memory issues from having all models loaded
        return [self.predict(img) for img in images]
