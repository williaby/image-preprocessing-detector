# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal Application for full Arena Benchmarking on DIQA-5000.

Downloads the dataset from GCS and runs VLM inference on all 1000 test samples.

Usage:
    modal run modal/arena_full_benchmark.py::run_benchmark
    modal run modal/arena_full_benchmark.py::run_benchmark --num-samples 100
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import modal

# Import shared utilities
from modal.shared import (
    DATASET_CACHE_DIR,
    IQA_PROMPT,
    download_dataset_from_gcs,
    gcs_secret,
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
app = modal.App("arena-full-benchmark")

# Define image with VLM and GCS support
benchmark_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        "transformers>=4.46.0",
        "accelerate>=0.25.0",
        "bitsandbytes>=0.42.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.1.99",
        "huggingface_hub>=0.20.0,<1.0.0",
        "pillow>=10.0.0",
        "peft>=0.7.0",
        "qwen-vl-utils>=0.0.8",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
    )
)

# DeepSeek-OCR image - use sdpa attention instead of flash-attention to avoid build issues
# flash-attn requires CUDA toolkit for compilation which is complex in Modal
deepseek_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "transformers==4.46.3",  # DeepSeek-OCR requires this specific version
        "tokenizers==0.20.3",  # DeepSeek-OCR requires this specific version
        "accelerate>=0.25.0",
        "safetensors>=0.4.0",
        "sentencepiece>=0.1.99",
        "huggingface_hub>=0.20.0,<1.0.0",
        "pillow>=10.0.0",
        "structlog>=24.1.0",
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        # DeepSeek-OCR specific dependencies (from requirements.txt)
        "einops>=0.7.0",
        "easydict>=1.10",
        "addict>=2.4.0",
        "PyMuPDF>=1.23.0",
        "img2pdf>=0.5.0",
        "numpy>=1.24.0",
        "tiktoken>=0.5.0",
        "matplotlib>=3.7.0",
    )
)


def parse_vlm_response(response: str) -> dict[str, float | None]:
    """Parse VLM response to extract quality scores.

    Args:
        response: VLM text response.

    Returns:
        Dictionary with parsed scores or None for unparseable values.
    """
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


@app.function(
    image=benchmark_image,
    gpu="T4",
    timeout=7200,  # 2 hours for full benchmark
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=16384,  # 16GB RAM
)
def run_benchmark(
    model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct",
    num_samples: int = 0,  # 0 = all samples
    batch_size: int = 1,
) -> dict[str, Any]:
    """Run full DIQA-5000 benchmark.

    Args:
        model_id: HuggingFace model ID.
        num_samples: Number of samples to evaluate (0 = all).
        batch_size: Batch size for inference.

    Returns:
        Benchmark results with metrics.
    """
    import torch
    from PIL import Image
    from scipy import stats
    from transformers import AutoModelForVision2Seq, AutoProcessor

    print("=" * 60)
    print(f"Arena Benchmark: {model_id}")
    print("=" * 60)

    # GPU info
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
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
    )

    # Check if model is pre-quantized
    if "bnb-4bit" in model_id.lower() or "bnb-8bit" in model_id.lower():
        load_kwargs = {
            "trust_remote_code": True,
            "cache_dir": cache_dir,
            "device_map": "auto",
            "torch_dtype": torch.float16,
        }
    else:
        from transformers import BitsAndBytesConfig

        load_kwargs = {
            "trust_remote_code": True,
            "cache_dir": cache_dir,
            "device_map": "auto",
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            ),
        }

    model = AutoModelForVision2Seq.from_pretrained(model_id, **load_kwargs)
    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")
    model_volume.commit()

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load image
            image = Image.open(sample["image_path"]).convert("RGB")

            # Prepare inputs based on model type
            if "smolvlm" in model_id.lower() or "smol" in model_id.lower():
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image"},
                            {"type": "text", "text": IQA_PROMPT},
                        ],
                    }
                ]
                text = processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = processor(
                    text=text,
                    images=[image],
                    return_tensors="pt",
                ).to(model.device)
            elif "qwen" in model_id.lower():
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image},
                            {"type": "text", "text": IQA_PROMPT},
                        ],
                    }
                ]
                text = processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = processor(
                    text=[text],
                    images=[image],
                    padding=True,
                    return_tensors="pt",
                ).to(model.device)
            else:
                inputs = processor(
                    text=IQA_PROMPT,
                    images=image,
                    return_tensors="pt",
                ).to(model.device)

            # Generate
            with torch.inference_mode():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=128,
                    temperature=0.1,
                    do_sample=True,
                )

            # Decode
            if "smolvlm" in model_id.lower() or "smol" in model_id.lower():
                generated_ids = output_ids[0][len(inputs.input_ids[0]) :]
                output_text = processor.decode(generated_ids, skip_special_tokens=True)
            elif "qwen" in model_id.lower():
                generated_ids = [
                    output_ids[j][len(inputs.input_ids[j]) :]
                    for j in range(len(output_ids))
                ]
                output_text = processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )[0]
            else:
                output_text = processor.decode(output_ids[0], skip_special_tokens=True)

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            # Parse response
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

    # Compute metrics
    print("\n--- Computing Metrics ---")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(samples),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(samples) if samples else 0,
    }

    # Timing metrics
    if inference_times:
        metrics["timing"] = {
            "mean_ms": sum(inference_times) / len(inference_times),
            "min_ms": min(inference_times),
            "max_ms": max(inference_times),
            "total_s": sum(inference_times) / 1000,
            "model_load_s": model_load_time,
        }

    # Correlation metrics for each dimension
    for dim in ["overall", "sharpness", "color"]:
        gt_values = []
        pred_values = []

        for r in successful:
            gt = r["ground_truth"].get(dim)
            pred = r["predicted"].get(dim) if r["predicted"] else None

            if gt is not None and pred is not None:
                gt_values.append(gt)
                pred_values.append(pred)

        if len(gt_values) >= 3:
            # PLCC (Pearson Linear Correlation Coefficient)
            plcc, _ = stats.pearsonr(gt_values, pred_values)

            # SRCC (Spearman Rank Correlation Coefficient)
            srcc, _ = stats.spearmanr(gt_values, pred_values)

            # MAE (Mean Absolute Error)
            mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )

            # RMSE (Root Mean Square Error)
            mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            rmse = mse**0.5

            metrics[dim] = {
                "plcc": plcc,
                "srcc": srcc,
                "mae": mae,
                "rmse": rmse,
                "num_valid": len(gt_values),
            }
        else:
            metrics[dim] = {
                "plcc": None,
                "srcc": None,
                "mae": None,
                "rmse": None,
                "num_valid": len(gt_values),
                "error": "Insufficient valid predictions",
            }

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {model_id}")
    print(
        f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)"
    )
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print("\nTiming:")
        print(f"  Mean inference: {t['mean_ms']:.0f}ms")
        print(f"  Total inference: {t['total_s']:.1f}s")
        print(f"  Model load: {t['model_load_s']:.1f}s")

    for dim in ["overall", "sharpness", "color"]:
        if dim in metrics and metrics[dim].get("plcc") is not None:
            m = metrics[dim]
            print(f"\n{dim.capitalize()}:")
            print(f"  PLCC: {m['plcc']:.4f}")
            print(f"  SRCC: {m['srcc']:.4f}")
            print(f"  MAE:  {m['mae']:.4f}")
            print(f"  RMSE: {m['rmse']:.4f}")
            print(f"  Valid predictions: {m['num_valid']}")

    return {
        "metrics": metrics,
        "results": results[:10],  # Return first 10 for inspection
    }


# DeepSeek-OCR IQA prompt - simpler format for OCR model
DEEPSEEK_IQA_PROMPT = """<image>
Analyze this document image quality. Rate on a scale of 1-5:
- Overall quality:
- Sharpness:
- Color fidelity:

Respond with only the three numbers, one per line."""


@app.function(
    image=deepseek_image,
    gpu="A10G",  # A10G has better flash-attn support
    timeout=7200,
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=32768,  # 32GB RAM for 3B model
)
def run_deepseek_benchmark(
    num_samples: int = 0,
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with DeepSeek-OCR model.

    Args:
        num_samples: Number of samples to evaluate (0 = all).

    Returns:
        Benchmark results with metrics.
    """
    import tempfile

    import torch
    from scipy import stats
    from transformers import AutoModel, AutoTokenizer

    model_id = "deepseek-ai/DeepSeek-OCR"

    print("=" * 60)
    print(f"Arena Benchmark: {model_id}")
    print("=" * 60)

    # GPU info
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
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
    )

    # Try sdpa (PyTorch native) attention first, fall back to default if needed
    try:
        model = AutoModel.from_pretrained(
            model_id,
            trust_remote_code=True,
            cache_dir=cache_dir,
            use_safetensors=True,
            attn_implementation="sdpa",  # PyTorch native scaled dot-product attention
        )
        print("Using SDPA attention implementation")
    except Exception as e:
        print(f"SDPA not available ({e}), using default attention")
        model = AutoModel.from_pretrained(
            model_id,
            trust_remote_code=True,
            cache_dir=cache_dir,
            use_safetensors=True,
        )
    model = model.eval().cuda().to(torch.bfloat16)

    model_load_time = time.time() - model_start
    print(f"Model loaded in {model_load_time:.1f}s")
    model_volume.commit()

    # Create temp output dir for DeepSeek
    output_dir = tempfile.mkdtemp(prefix="deepseek-out-")

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # DeepSeek-OCR uses its own infer method
            res = model.infer(
                tokenizer,
                prompt=DEEPSEEK_IQA_PROMPT,
                image_file=sample["image_path"],
                output_path=output_dir,
                base_size=640,
                image_size=640,
                crop_mode=False,
                save_results=False,
            )

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            # Parse response - expect three numbers
            output_text = res if isinstance(res, str) else str(res)
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

    # Compute metrics (same as run_benchmark)
    print("\n--- Computing Metrics ---")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(samples),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(samples) if samples else 0,
    }

    if inference_times:
        metrics["timing"] = {
            "mean_ms": sum(inference_times) / len(inference_times),
            "min_ms": min(inference_times),
            "max_ms": max(inference_times),
            "total_s": sum(inference_times) / 1000,
            "model_load_s": model_load_time,
        }

    for dim in ["overall", "sharpness", "color"]:
        gt_values = []
        pred_values = []

        for r in successful:
            gt = r["ground_truth"].get(dim)
            pred = r["predicted"].get(dim) if r["predicted"] else None

            if gt is not None and pred is not None:
                gt_values.append(gt)
                pred_values.append(pred)

        if len(gt_values) >= 3:
            plcc, _ = stats.pearsonr(gt_values, pred_values)
            srcc, _ = stats.spearmanr(gt_values, pred_values)
            mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            rmse = mse**0.5

            metrics[dim] = {
                "plcc": plcc,
                "srcc": srcc,
                "mae": mae,
                "rmse": rmse,
                "num_valid": len(gt_values),
            }
        else:
            metrics[dim] = {
                "plcc": None,
                "srcc": None,
                "mae": None,
                "rmse": None,
                "num_valid": len(gt_values),
                "error": "Insufficient valid predictions",
            }

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {model_id}")
    print(
        f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)"
    )
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print("\nTiming:")
        print(f"  Mean inference: {t['mean_ms']:.0f}ms")
        print(f"  Total inference: {t['total_s']:.1f}s")
        print(f"  Model load: {t['model_load_s']:.1f}s")

    for dim in ["overall", "sharpness", "color"]:
        if dim in metrics and metrics[dim].get("plcc") is not None:
            m = metrics[dim]
            print(f"\n{dim.capitalize()}:")
            print(f"  PLCC: {m['plcc']:.4f}")
            print(f"  SRCC: {m['srcc']:.4f}")
            print(f"  MAE:  {m['mae']:.4f}")
            print(f"  RMSE: {m['rmse']:.4f}")
            print(f"  Valid predictions: {m['num_valid']}")

    return {
        "metrics": metrics,
        "results": results[:10],
    }


# Qwen3-VL-8B image - fits on A100, fast inference
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
    gpu="A100",  # 8B model at bf16 needs ~16GB VRAM - A100 has 40GB
    timeout=14400,  # 4 hours for full benchmark
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=32768,  # 32GB RAM
)
def run_qwen3_benchmark(
    num_samples: int = 0,
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with Qwen3-VL-8B-Instruct model.

    Args:
        num_samples: Number of samples to evaluate (0 = all).

    Returns:
        Benchmark results with metrics.
    """
    import torch
    from PIL import Image
    from scipy import stats
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    model_id = "Qwen/Qwen3-VL-8B-Instruct"

    print("=" * 60)
    print(f"Arena Benchmark: {model_id}")
    print("=" * 60)

    # GPU info
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
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
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

    # IQA prompt for Qwen3
    iqa_prompt = """Analyze this document image and rate its quality on a scale of 1-5 for each dimension.

Rate the following:
1. Overall quality (considering all aspects): a number from 1.0 to 5.0
2. Sharpness (text clarity, edge definition): a number from 1.0 to 5.0
3. Color fidelity (color accuracy, consistency): a number from 1.0 to 5.0

Respond with ONLY three lines in this exact format:
Overall: X.X
Sharpness: X.X
Color: X.X"""

    # Warmup step to avoid first-call CUDA overhead (consensus recommendation)
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
            # Load and resize image (consensus: limit to 1024px to avoid token explosion)
            image = Image.open(sample["image_path"]).convert("RGB")
            image.thumbnail((1024, 1024))  # Resize large images

            # Prepare messages for Qwen3-VL
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": iqa_prompt},
                    ],
                }
            ]

            # Process inputs
            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = inputs.to(model.device)

            # Generate (consensus: use greedy decoding for faster inference)
            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=64,  # Reduced from 128
                    do_sample=False,  # Greedy decoding - faster
                )

            # Decode
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

            # Parse response
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

    # Compute metrics
    print("\n--- Computing Metrics ---")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(samples),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(samples) if samples else 0,
    }

    if inference_times:
        metrics["timing"] = {
            "mean_ms": sum(inference_times) / len(inference_times),
            "min_ms": min(inference_times),
            "max_ms": max(inference_times),
            "total_s": sum(inference_times) / 1000,
            "model_load_s": model_load_time,
        }

    for dim in ["overall", "sharpness", "color"]:
        gt_values = []
        pred_values = []

        for r in successful:
            gt = r["ground_truth"].get(dim)
            pred = r["predicted"].get(dim) if r["predicted"] else None

            if gt is not None and pred is not None:
                gt_values.append(gt)
                pred_values.append(pred)

        if len(gt_values) >= 3:
            plcc, _ = stats.pearsonr(gt_values, pred_values)
            srcc, _ = stats.spearmanr(gt_values, pred_values)
            mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            rmse = mse**0.5

            metrics[dim] = {
                "plcc": plcc,
                "srcc": srcc,
                "mae": mae,
                "rmse": rmse,
                "num_valid": len(gt_values),
            }
        else:
            metrics[dim] = {
                "plcc": None,
                "srcc": None,
                "mae": None,
                "rmse": None,
                "num_valid": len(gt_values),
                "error": "Insufficient valid predictions",
            }

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {model_id}")
    print(
        f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)"
    )
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print("\nTiming:")
        print(f"  Mean inference: {t['mean_ms']:.0f}ms")
        print(f"  Total inference: {t['total_s']:.1f}s")
        print(f"  Model load: {t['model_load_s']:.1f}s")

    for dim in ["overall", "sharpness", "color"]:
        if dim in metrics and metrics[dim].get("plcc") is not None:
            m = metrics[dim]
            print(f"\n{dim.capitalize()}:")
            print(f"  PLCC: {m['plcc']:.4f}")
            print(f"  SRCC: {m['srcc']:.4f}")
            print(f"  MAE:  {m['mae']:.4f}")
            print(f"  RMSE: {m['rmse']:.4f}")
            print(f"  Valid predictions: {m['num_valid']}")

    return {
        "metrics": metrics,
        "results": results[:10],
    }


# InternVL3-8B image - fits on A100, fast inference
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
        "timm>=0.9.0",  # Required for InternVL vision encoder
        "google-cloud-storage>=2.14.0",
        "scipy>=1.11.0",
        "einops>=0.7.0",
    )
)


@app.function(
    image=internvl_image,
    gpu="A100",  # 8B model at bf16 needs ~16GB VRAM - A100 has 40GB
    timeout=14400,  # 4 hours for full benchmark
    volumes={"/models": model_volume, "/data": data_volume},
    secrets=[gcs_secret],
    memory=32768,  # 32GB RAM
)
def run_internvl_benchmark(
    num_samples: int = 0,
) -> dict[str, Any]:
    """Run DIQA-5000 benchmark with OpenGVLab/InternVL3-8B model.

    Args:
        num_samples: Number of samples to evaluate (0 = all).

    Returns:
        Benchmark results with metrics.
    """
    import torch
    from PIL import Image
    from scipy import stats
    from transformers import AutoModel, AutoTokenizer

    model_id = "OpenGVLab/InternVL3-8B"

    print("=" * 60)
    print(f"Arena Benchmark: {model_id}")
    print("=" * 60)

    # GPU info
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
        model_id,
        trust_remote_code=True,
        cache_dir=cache_dir,
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

    # IQA prompt for InternVL
    iqa_prompt = """<image>
Analyze this document image and rate its quality on a scale of 1-5 for each dimension.

Rate the following:
1. Overall quality (considering all aspects): a number from 1.0 to 5.0
2. Sharpness (text clarity, edge definition): a number from 1.0 to 5.0
3. Color fidelity (color accuracy, consistency): a number from 1.0 to 5.0

Respond with ONLY three lines in this exact format:
Overall: X.X
Sharpness: X.X
Color: X.X"""

    # Run inference
    print("\n--- Running Inference ---")
    results = []
    inference_times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Processing sample {i + 1}/{len(samples)}...")

        start = time.time()

        try:
            # Load image
            image = Image.open(sample["image_path"]).convert("RGB")

            # InternVL uses its own chat method
            with torch.inference_mode():
                response = model.chat(
                    tokenizer,
                    image,
                    iqa_prompt,
                    generation_config={
                        "max_new_tokens": 128,
                        "temperature": 0.1,
                        "do_sample": True,
                    },
                )

            elapsed_ms = (time.time() - start) * 1000
            inference_times.append(elapsed_ms)

            # Parse response
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

    # Compute metrics
    print("\n--- Computing Metrics ---")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(samples),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(samples) if samples else 0,
    }

    if inference_times:
        metrics["timing"] = {
            "mean_ms": sum(inference_times) / len(inference_times),
            "min_ms": min(inference_times),
            "max_ms": max(inference_times),
            "total_s": sum(inference_times) / 1000,
            "model_load_s": model_load_time,
        }

    for dim in ["overall", "sharpness", "color"]:
        gt_values = []
        pred_values = []

        for r in successful:
            gt = r["ground_truth"].get(dim)
            pred = r["predicted"].get(dim) if r["predicted"] else None

            if gt is not None and pred is not None:
                gt_values.append(gt)
                pred_values.append(pred)

        if len(gt_values) >= 3:
            plcc, _ = stats.pearsonr(gt_values, pred_values)
            srcc, _ = stats.spearmanr(gt_values, pred_values)
            mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / len(
                gt_values
            )
            rmse = mse**0.5

            metrics[dim] = {
                "plcc": plcc,
                "srcc": srcc,
                "mae": mae,
                "rmse": rmse,
                "num_valid": len(gt_values),
            }
        else:
            metrics[dim] = {
                "plcc": None,
                "srcc": None,
                "mae": None,
                "rmse": None,
                "num_valid": len(gt_values),
                "error": "Insufficient valid predictions",
            }

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {model_id}")
    print(
        f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)"
    )
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print("\nTiming:")
        print(f"  Mean inference: {t['mean_ms']:.0f}ms")
        print(f"  Total inference: {t['total_s']:.1f}s")
        print(f"  Model load: {t['model_load_s']:.1f}s")

    for dim in ["overall", "sharpness", "color"]:
        if dim in metrics and metrics[dim].get("plcc") is not None:
            m = metrics[dim]
            print(f"\n{dim.capitalize()}:")
            print(f"  PLCC: {m['plcc']:.4f}")
            print(f"  SRCC: {m['srcc']:.4f}")
            print(f"  MAE:  {m['mae']:.4f}")
            print(f"  RMSE: {m['rmse']:.4f}")
            print(f"  Valid predictions: {m['num_valid']}")

    return {
        "metrics": metrics,
        "results": results[:10],
    }


# Entry point for testing
if __name__ == "__main__":
    with app.run():
        result = run_benchmark.remote(num_samples=10)
        print(json.dumps(result["metrics"], indent=2))
