# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal Application for Arena Benchmarking with VLM inference.

Provides GPU functions for running Vision Language Model (VLM) inference
on the DIQA-5000 benchmark dataset for document quality assessment.

Usage:
    modal run modal/arena_benchmark.py::test_gpu       # Test GPU access
    modal run modal/arena_benchmark.py::run_inference  # Run single inference
    modal deploy modal/arena_benchmark.py              # Deploy for remote calls
"""

from __future__ import annotations

import base64
import io
import time
from typing import Any

import modal

# Create Modal app for Arena benchmarking
app = modal.App("arena-benchmark")

# Define VLM image with transformers and quantization support
vlm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "transformers>=4.40.0",
        "accelerate>=0.25.0",
        "bitsandbytes>=0.42.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.1.99",
        "huggingface_hub>=0.20.0,<1.0.0",
        "pillow>=10.0.0",
        "peft>=0.7.0",
        "qwen-vl-utils>=0.0.8",
        "structlog>=24.1.0",
    )
)

# Model cache volume for HuggingFace models
model_volume = modal.Volume.from_name("arena-models", create_if_missing=True)

@app.function(
    image=vlm_image,
    gpu="T4",  # Start with T4 (16GB), can upgrade to A10 (24GB) if needed
    timeout=600,
    volumes={"/models": model_volume},
)
def test_gpu() -> dict[str, Any]:
    """Test GPU access and CUDA availability.

    Returns:
        Dictionary with GPU info and CUDA version
    """
    import torch

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return {
            "status": "ok",
            "gpu": gpu_name,
            "memory_gb": round(gpu_memory, 1),
            "cuda_version": torch.version.cuda,
            "pytorch_version": torch.__version__,
        }
    return {"status": "error", "error": "No GPU available"}


@app.cls(
    image=vlm_image,
    gpu="T4",
    timeout=1800,  # 30 min for batch processing
    volumes={"/models": model_volume},
    scaledown_window=300,  # Keep warm for 5 minutes
)
class VLMInference:
    """Vision Language Model inference service for Arena benchmarking.

    Supports multiple VLM architectures:
    - Qwen2.5-VL (recommended for quality assessment)
    - SmolVLM (lightweight alternative)
    - Other HuggingFace VLMs

    Example:
        >>> inference = modal.Cls.lookup("arena-benchmark", "VLMInference")()
        >>> result = inference.predict.remote(
        ...     image_b64="...",
        ...     prompt="Rate the quality of this document...",
        ...     model_id="unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit"
        ... )
    """

    def __init__(self) -> None:
        """Initialize inference service."""
        self._model = None
        self._processor = None
        self._current_model_id: str | None = None

    @modal.enter()
    def setup(self) -> None:
        """Pre-warm the container (optional model loading)."""
        import torch

        # Log GPU info on startup
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")

    def _load_model(self, model_id: str) -> None:
        """Load or switch VLM model.

        Args:
            model_id: HuggingFace model ID
        """
        import os
        import torch
        from transformers import AutoModelForVision2Seq, AutoProcessor

        if self._current_model_id == model_id and self._model is not None:
            return  # Model already loaded

        print(f"Loading model: {model_id}")
        start = time.time()

        # Clear previous model
        if self._model is not None:
            del self._model
            del self._processor
            torch.cuda.empty_cache()

        # Set cache directory
        cache_dir = "/models/huggingface"
        os.makedirs(cache_dir, exist_ok=True)

        # Load processor
        self._processor = AutoProcessor.from_pretrained(
            model_id,
            trust_remote_code=True,
            cache_dir=cache_dir,
        )

        # Load model with appropriate settings based on model type
        load_kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "cache_dir": cache_dir,
            "device_map": "auto",
        }

        # Check if model is already quantized (bnb-4bit in name)
        if "bnb-4bit" in model_id.lower() or "bnb-8bit" in model_id.lower():
            # Pre-quantized model, load directly
            load_kwargs["torch_dtype"] = torch.float16
        elif "gguf" in model_id.lower():
            # GGUF models need different handling
            load_kwargs["torch_dtype"] = torch.float16
        else:
            # Apply 4-bit quantization for non-quantized models
            from transformers import BitsAndBytesConfig

            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

        self._model = AutoModelForVision2Seq.from_pretrained(
            model_id,
            **load_kwargs,
        )

        self._current_model_id = model_id

        elapsed = time.time() - start
        print(f"Model loaded in {elapsed:.1f}s")

        # Commit volume to persist cached model
        model_volume.commit()

    @modal.method()
    def predict(
        self,
        image_b64: str,
        prompt: str,
        model_id: str = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
        max_new_tokens: int = 256,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Run VLM inference on an image.

        Args:
            image_b64: Base64-encoded image (JPEG or PNG)
            prompt: Text prompt for the model
            model_id: HuggingFace model ID
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Dictionary with:
                - text: Generated text response
                - inference_time_ms: Inference latency
                - model_id: Model used
                - device: GPU device name
        """
        import torch
        from PIL import Image

        start = time.time()

        # Load model if needed
        self._load_model(model_id)

        # Decode image
        image_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Prepare inputs based on model type
        if "qwen" in model_id.lower():
            # Qwen-VL format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            inputs = self._processor(
                text=[text],
                images=[image],
                padding=True,
                return_tensors="pt",
            ).to(self._model.device)
        elif "smolvlm" in model_id.lower() or "smol" in model_id.lower():
            # SmolVLM format - uses chat template with image placeholder
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            inputs = self._processor(
                text=text,
                images=[image],
                return_tensors="pt",
            ).to(self._model.device)
        else:
            # Generic VLM format
            inputs = self._processor(
                text=prompt,
                images=image,
                return_tensors="pt",
            ).to(self._model.device)

        # Generate
        with torch.inference_mode():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,
            )

        # Decode output
        # Skip input tokens to get only the generated text
        if "qwen" in model_id.lower():
            generated_ids = [
                output_ids[i][len(inputs.input_ids[i]):]
                for i in range(len(output_ids))
            ]
            output_text = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )[0]
        elif "smolvlm" in model_id.lower() or "smol" in model_id.lower():
            # SmolVLM: skip input tokens
            generated_ids = output_ids[0][len(inputs.input_ids[0]):]
            output_text = self._processor.decode(
                generated_ids,
                skip_special_tokens=True,
            )
        else:
            output_text = self._processor.decode(
                output_ids[0],
                skip_special_tokens=True,
            )
            # Remove input prompt from output if present
            if prompt in output_text:
                output_text = output_text.split(prompt)[-1].strip()

        elapsed_ms = (time.time() - start) * 1000

        return {
            "text": output_text,
            "inference_time_ms": elapsed_ms,
            "model_id": model_id,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        }

    @modal.method()
    def batch_predict(
        self,
        images_b64: list[str],
        prompts: list[str],
        model_id: str = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
        max_new_tokens: int = 256,
        temperature: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Run VLM inference on multiple images.

        Args:
            images_b64: List of base64-encoded images
            prompts: List of prompts (same length as images)
            model_id: HuggingFace model ID
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            List of prediction results
        """
        if len(images_b64) != len(prompts):
            return [{"error": "images_b64 and prompts must have same length"}]

        results = []
        for img_b64, prompt in zip(images_b64, prompts):
            try:
                result = self.predict(
                    image_b64=img_b64,
                    prompt=prompt,
                    model_id=model_id,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "model_id": model_id,
                })

        return results

    @modal.method()
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the currently loaded model.

        Returns:
            Dictionary with model info
        """
        import torch

        return {
            "current_model_id": self._current_model_id,
            "model_loaded": self._model is not None,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "gpu_memory_allocated_gb": torch.cuda.memory_allocated(0) / (1024**3) if torch.cuda.is_available() else 0,
            "gpu_memory_reserved_gb": torch.cuda.memory_reserved(0) / (1024**3) if torch.cuda.is_available() else 0,
        }


@app.function(
    image=vlm_image,
    gpu="T4",
    timeout=300,
    volumes={"/models": model_volume},
)
def run_inference(
    image_b64: str,
    prompt: str,
    model_id: str = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
) -> dict[str, Any]:
    """Standalone function for single inference (for testing).

    Args:
        image_b64: Base64-encoded image
        prompt: Text prompt
        model_id: HuggingFace model ID

    Returns:
        Inference result dictionary
    """
    inference = VLMInference()
    inference.setup()
    return inference.predict(
        image_b64=image_b64,
        prompt=prompt,
        model_id=model_id,
    )


# Entry point for testing
if __name__ == "__main__":
    with app.run():
        result = test_gpu.remote()
        print(f"GPU Test Result: {result}")
