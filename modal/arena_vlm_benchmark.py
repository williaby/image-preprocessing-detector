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

import base64
import csv
import os
import re
import tarfile
import time
from pathlib import Path
from typing import Any

import modal

# Create Modal app
app = modal.App("arena-vlm-benchmark")

# GCS configuration
GCS_BUCKET = "assured-oss-457903-diqa5000"
GCS_ARCHIVE = "diqa5000-test.tar.gz"
DATASET_CACHE_DIR = "/data/diqa5000"

# Volumes for caching
model_volume = modal.Volume.from_name("arena-models", create_if_missing=True)
data_volume = modal.Volume.from_name("arena-data", create_if_missing=True)

# GCS credentials secret
gcs_secret = modal.Secret.from_name("gcs-credentials")

# IQA prompt for VLMs
IQA_PROMPT = """Analyze this document image and rate its quality on a scale of 1-5 for each dimension.

Rate the following:
1. Overall quality (considering all aspects): a number from 1.0 to 5.0
2. Sharpness (text clarity, edge definition): a number from 1.0 to 5.0
3. Color fidelity (color accuracy, consistency): a number from 1.0 to 5.0

Respond with ONLY three lines in this exact format:
Overall: X.X
Sharpness: X.X
Color: X.X"""


def setup_gcs_credentials() -> None:
    """Setup GCS credentials from Modal secret."""
    import tempfile

    gcp_sa_key_b64 = os.environ.get("GCP_SA_KEY")
    if not gcp_sa_key_b64:
        print("Warning: GCP_SA_KEY not found, trying default credentials")
        return

    gcp_sa_key_json = base64.b64decode(gcp_sa_key_b64).decode("utf-8")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="gcp-sa-key-"
    ) as f:
        f.write(gcp_sa_key_json)
        f.flush()
        credentials_path = f.name

    os.chmod(credentials_path, 0o600)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    print(f"GCS credentials configured at {credentials_path}")


def download_dataset_from_gcs(cache_dir: str) -> Path:
    """Download and extract DIQA-5000 dataset from GCS."""
    from google.cloud import storage

    cache_path = Path(cache_dir)
    test_dir = cache_path / "test"
    csv_path = test_dir / "test.csv"

    if csv_path.exists():
        print(f"Dataset already cached at {cache_path}")
        return cache_path

    setup_gcs_credentials()

    print(f"Downloading dataset from gs://{GCS_BUCKET}/{GCS_ARCHIVE}...")
    start = time.time()

    cache_path.mkdir(parents=True, exist_ok=True)
    archive_path = cache_path / GCS_ARCHIVE

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_ARCHIVE)
    blob.download_to_filename(str(archive_path))

    download_time = time.time() - start
    print(f"Downloaded in {download_time:.1f}s")

    print("Extracting dataset...")
    start = time.time()
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(cache_path)
    extract_time = time.time() - start
    print(f"Extracted in {extract_time:.1f}s")

    archive_path.unlink()
    return cache_path


def load_dataset(dataset_path: Path) -> list[dict]:
    """Load DIQA-5000 test samples."""
    test_dir = dataset_path / "test"
    csv_path = test_dir / "test.csv"
    res_dir = test_dir / "res"

    samples = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_filename = row["res"]
            image_path = res_dir / image_filename

            if not image_path.exists():
                continue

            samples.append({
                "sample_id": image_filename.replace(".jpg", ""),
                "image_path": str(image_path),
                "ground_truth": {
                    "overall": float(row["overall"]),
                    "sharpness": float(row["sharpness"]),
                    "color": float(row["color_fidelity"]),
                },
            })

    print(f"Loaded {len(samples)} samples")
    return samples


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


def compute_metrics(results: list[dict], model_id: str, model_load_time: float,
                   inference_times: list[float]) -> dict[str, Any]:
    """Compute benchmark metrics from results."""
    from scipy import stats

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    metrics: dict[str, Any] = {
        "model_id": model_id,
        "num_samples": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(results) if results else 0,
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
            mae = sum(abs(g - p) for g, p in zip(gt_values, pred_values)) / len(gt_values)
            mse = sum((g - p) ** 2 for g, p in zip(gt_values, pred_values)) / len(gt_values)
            rmse = mse ** 0.5

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

    return metrics


def print_results(metrics: dict[str, Any]) -> None:
    """Print benchmark results."""
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Model: {metrics['model_id']}")
    print(f"Samples: {metrics['num_samples']} ({metrics['successful']} successful, {metrics['failed']} failed)")
    print(f"Success Rate: {metrics['success_rate']:.1%}")

    if "timing" in metrics:
        t = metrics["timing"]
        print(f"\nTiming:")
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
    from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

    model_id = "Qwen/Qwen3-VL-8B-Instruct"

    print("=" * 60)
    print(f"Arena VLM Benchmark: {model_id}")
    print("=" * 60)

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")

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
        warmup_msg, tokenize=True, add_generation_prompt=True,
        return_dict=True, return_tensors="pt"
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
            print(f"Processing sample {i+1}/{len(samples)}...")

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
                out_ids[len(in_ids):]
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

            results.append({
                "sample_id": sample["sample_id"],
                "ground_truth": sample["ground_truth"],
                "predicted": predicted,
                "response": output_text[:200],
                "inference_time_ms": elapsed_ms,
                "success": True,
            })

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append({
                "sample_id": sample["sample_id"],
                "ground_truth": sample["ground_truth"],
                "predicted": None,
                "error": str(e),
                "inference_time_ms": elapsed_ms,
                "success": False,
            })

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
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")

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
            _ = model.chat(tokenizer, None, "Hi", generation_config={"max_new_tokens": 4})
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
            print(f"Processing sample {i+1}/{len(samples)}...")

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

            results.append({
                "sample_id": sample["sample_id"],
                "ground_truth": sample["ground_truth"],
                "predicted": predicted,
                "response": output_text[:200],
                "inference_time_ms": elapsed_ms,
                "success": True,
            })

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            results.append({
                "sample_id": sample["sample_id"],
                "ground_truth": sample["ground_truth"],
                "predicted": None,
                "error": str(e),
                "inference_time_ms": elapsed_ms,
                "success": False,
            })

    # Compute and print metrics
    print("\n--- Computing Metrics ---")
    metrics = compute_metrics(results, model_id, model_load_time, inference_times)
    print_results(metrics)

    return {"metrics": metrics, "results": results[:10]}
