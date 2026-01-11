# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal Application for VLM-based IQA Benchmarking on DIQA-5000.

Benchmarks LLM-style vision models (InternVL, Qwen3-VL, etc.) that use
natural language prompts for image quality assessment.

Usage:
    modal run modal/arena_vlm_benchmark.py::run_qwen3_benchmark --num-samples 10
    modal run modal/arena_vlm_benchmark.py::run_internvl_benchmark --num-samples 10
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import modal

# Import shared utilities
from modal.shared import (
    DATASET_CACHE_DIR,
    IQA_PROMPT,
    compute_metrics,
    download_dataset_from_gcs,
    gcs_secret,
    print_results,
)
from modal.shared import (
    arena_data_volume as data_volume,
)
from modal.shared import (
    arena_model_volume as model_volume,
)
from modal.shared import (
    load_diqa5000_dataset as load_dataset,
)

# Create Modal app
app = modal.App("arena-vlm-benchmark")


def parse_vlm_response(response: str) -> dict[str, float | None]:
    """Parse VLM response to extract quality scores."""
    scores: dict[str, float | None] = {
        "overall": None,
        "sharpness": None,
        "color": None,
    }

    lines = response.lower().split("\n")
    for line in lines:
        line = line.strip()
        for key in scores:
            if key in line:
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    try:
                        value = float(match.group(1))
                        if 1.0 <= value <= 5.0:
                            scores[key] = value
                    except ValueError:
                        pass

    return scores


# =============================================================================
# Qwen3-VL-8B Benchmark
# =============================================================================

qwen3_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "transformers>=4.57.0",
        "accelerate>=0.25.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.1.99",
        "huggingface_hub>=0.20.0,<1.0.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "qwen-vl-utils>=0.0.8",
    )
)


@app.function(
    image=qwen3_image,
    gpu="A100",
    timeout=14400,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=32768,
)
def run_qwen3_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with Qwen3-VL-8B-Instruct model."""
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    model_id = "Qwen/Qwen3-VL-8B-Instruct"

    print("=" * 60)
    print(f"Arena VLM Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # Load model
    print(f"\nLoading model: {model_id}")
    model_start = time.time()

    cache_dir = "/models/huggingface"
    os.makedirs(cache_dir, exist_ok=True)

    processor = AutoProcessor.from_pretrained(
        model_id, trust_remote_code=True, cache_dir=cache_dir
    )

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")
    model_volume.commit()

    # Warmup
    print("\n--- Warmup ---")
    warmup_msg = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
    warmup_inputs = processor.apply_chat_template(
        warmup_msg,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)
    with torch.inference_mode():
        _ = model.generate(**warmup_inputs, max_new_tokens=4)
    print("Warmup complete")

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and resize image
            image = Image.open(sample["image_path"]).convert("RGB")
            image.thumbnail((1024, 1024))

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": IQA_PROMPT},
                    ],
                }
            ]

            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = inputs.to(model.device)

            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=64,
                    do_sample=False,
                )

            generated_ids_trimmed = [
                out_ids[len(in_ids) :]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            predicted = parse_vlm_response(output_text)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "response": output_text[:200],
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}


# =============================================================================
# InternVL3-8B Benchmark
# =============================================================================

internvl_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "transformers>=4.46.0",
        "accelerate>=0.25.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.1.99",
        "huggingface_hub>=0.20.0,<1.0.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "einops>=0.7.0",
        "timm>=0.9.0",
    )
)


@app.function(
    image=internvl_image,
    gpu="A100",
    timeout=14400,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=32768,
)
def run_internvl_benchmark(num_samples: int = 0) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with InternVL3-8B model."""
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer

    model_id = "OpenGVLab/InternVL3-8B"

    print("=" * 60)
    print(f"Arena VLM Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        )

    # Download dataset
    dataset_path = download_dataset_from_gcs(DATASET_CACHE_DIR)
    data_volume.commit()

    # Load samples
    samples = load_dataset(dataset_path)
    if num_samples > 0:
        samples = samples[:num_samples]
    print(f"Evaluating {len(samples)} samples")

    # Load model
    print(f"\nLoading model: {model_id}")
    model_start = time.time()

    cache_dir = "/models/huggingface"
    os.makedirs(cache_dir, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_id, trust_remote_code=True, cache_dir=cache_dir
    )

    model = AutoModel.from_pretrained(
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    model = model.eval()

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")
    model_volume.commit()

    # Warmup
    print("\n--- Warmup ---")
    try:
        with torch.inference_mode():
            _ = model.chat(
                tokenizer, None, "Hi", generation_config={"max_new_tokens": 4}
            )
        print("Warmup complete")
    except Exception as e:
        print(f"Warmup skipped (model may not support text-only): {e}")

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    # InternVL prompt with image token
    iqa_prompt = f"<image>\n{IQA_PROMPT}"

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load and resize image
            image = Image.open(sample["image_path"]).convert("RGB")
            image.thumbnail((1024, 1024))

            with torch.inference_mode():
                response = model.chat(
                    tokenizer,
                    image,
                    iqa_prompt,
                    generation_config={
                        "max_new_tokens": 64,
                        "do_sample": False,
                    },
                )

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            output_text = response if isinstance(response, str) else str(response)
            predicted = parse_vlm_response(output_text)

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": predicted,
                    "response": output_text[:200],
                    "inference_time_ms": elapsed_ms,
                    "success": True,
                }
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "predicted": None,
                    "error": str(e),
                    "inference_time_ms": elapsed_ms,
                    "success": False,
                }
            )

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}
