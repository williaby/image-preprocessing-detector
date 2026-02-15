#!/usr/bin/env python
"""Local test script for Arena framework with vision-language models.

This script tests the Arena benchmarking framework locally, including:
- Framework tests (schemas, metrics, backends)
- Modal.com integration (mock mode)
- Local VLM loading (optional)

Supported Models (for 4GB VRAM):
    - SmolVLM-256M: < 1GB VRAM (smallest VLM in the world)
    - SmolVLM-500M: ~1-2GB VRAM
    - Qwen2.5-VL-3B: ~2-3GB VRAM with 4-bit quantization

Usage:
    # Install dependencies first
    uv sync --extra labeling --extra dev

    # Run framework tests only (no model loading)
    uv run python scripts/test_arena_local.py --skip-model

    # Run with SmolVLM-256M (recommended for 4GB VRAM)
    uv run python scripts/test_arena_local.py --model smolvlm-256m

    # Run with Qwen2.5-VL-3B (requires ~3GB VRAM)
    uv run python scripts/test_arena_local.py --model qwen-3b

    # Run on CPU (slower but no VRAM needed)
    uv run python scripts/test_arena_local.py --model smolvlm-256m --device cpu

Modal Integration:
    The script tests Modal client and backend in mock mode by default.
    To test with actual Modal deployment:
    1. Deploy: modal deploy modal/arena_benchmark.py
    2. Unset mock mode: export ARENA_MODAL_MOCK=false
    3. Run: uv run python scripts/test_arena_local.py --skip-model
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

rng = np.random.default_rng(42)


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    missing = []

    try:
        import torch

        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA device: {torch.cuda.get_device_name(0)}")
    except ImportError:
        missing.append("torch")

    try:
        import transformers

        print(f"Transformers: {transformers.__version__}")
    except ImportError:
        missing.append("transformers")

    try:
        import accelerate

        print(f"Accelerate: {accelerate.__version__}")
    except ImportError:
        missing.append("accelerate")

    # bitsandbytes is optional (Linux only)
    try:
        import bitsandbytes

        print(f"Bitsandbytes: {bitsandbytes.__version__}")
    except ImportError:
        print("Bitsandbytes: Not installed (optional, Linux only)")

    if missing:
        print(f"\nMissing dependencies: {missing}")
        print("Install with: uv sync --extra labeling --extra dev")
        return False

    return True


def create_test_images(
    num_images: int = 5,
) -> list[tuple[np.ndarray, dict[str, float]]]:
    """Create synthetic test images with ground truth labels.

    Returns:
        List of (image_array, labels) tuples.
    """
    images = []
    rng_seeded = np.random.default_rng(42)

    for _ in range(num_images):
        # Create varied test images
        img = np.zeros((224, 224, 3), dtype=np.uint8)

        # Vary quality characteristics
        noise_level = rng_seeded.uniform(0.1, 0.5)
        brightness = rng_seeded.uniform(0.3, 0.9)
        sharpness_factor = rng_seeded.uniform(0.3, 0.9)

        # Base image with gradient
        for y in range(224):
            for x in range(224):
                img[y, x] = [
                    int(brightness * 255 * (x / 224)),
                    int(brightness * 255 * (y / 224)),
                    int(brightness * 255 * ((x + y) / 448)),
                ]

        # Add noise
        noise = rng_seeded.normal(0, noise_level * 50, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Ground truth labels (simulated)
        labels = {
            "overall": float(
                np.clip(0.7 - noise_level * 0.5 + brightness * 0.2, 0.3, 0.95)
            ),
            "sharpness": float(np.clip(sharpness_factor * 0.8 + 0.1, 0.2, 0.9)),
            "color": float(np.clip(brightness * 0.6 + 0.3, 0.4, 0.95)),
        }

        images.append((img, labels))

    return images


def test_schemas() -> bool:
    """Test Arena schemas."""
    print("\n--- Testing Schemas ---")
    try:
        from image_preprocessing_detector.labeling.arena.schemas import (
            BenchmarkResult,
            DatasetInfo,
            DIQAPrediction,
            ExecutionInfo,
            ProvenanceInfo,
            RunStatus,
        )

        # Test DIQAPrediction
        pred = DIQAPrediction(
            overall=0.85,
            sharpness=0.78,
            color=0.92,
            image_id="test_001",
            inference_time_ms=25.5,
        )
        assert pred.overall == pytest.approx(0.85)
        print("  DIQAPrediction: OK")

        # Test BenchmarkResult
        result = BenchmarkResult(
            run_id="test123",
            status=RunStatus.COMPLETED,
            model_spec={"id": "test-model"},
            dataset=DatasetInfo(
                name="test",
                version="1.0",
                split="test",
                num_samples=10,
            ),
            metrics={"aggregate": {"plcc": 0.9}},
            execution=ExecutionInfo(
                hardware="CPU",
                duration_seconds=1.0,
                batch_size=1,
            ),
            provenance=ProvenanceInfo(),
        )
        json_str = result.to_json()
        assert "test123" in json_str
        print("  BenchmarkResult serialization: OK")

        return True
    except Exception as e:
        print(f"  Schema test failed: {e}")
        return False


def test_metrics() -> bool:
    """Test Arena metrics computation."""
    print("\n--- Testing Metrics ---")
    try:
        from image_preprocessing_detector.labeling.arena.metrics import (
            ArenaMetrics,
            compute_mae,
            compute_plcc,
            compute_rmse,
            compute_srcc,
        )

        # Test individual metrics
        preds = [0.1, 0.2, 0.3, 0.4, 0.5]
        gt = [0.15, 0.25, 0.35, 0.45, 0.55]

        plcc = compute_plcc(preds, gt)
        srcc = compute_srcc(preds, gt)
        mae = compute_mae(preds, gt)
        rmse = compute_rmse(preds, gt)

        print(f"  PLCC: {plcc:.4f} (expected ~1.0)")
        print(f"  SRCC: {srcc:.4f} (expected ~1.0)")
        print(f"  MAE:  {mae:.4f} (expected ~0.05)")
        print(f"  RMSE: {rmse:.4f} (expected ~0.05)")

        assert plcc > 0.99, f"PLCC too low: {plcc}"
        assert srcc > 0.99, f"SRCC too low: {srcc}"
        assert mae < 0.06, f"MAE too high: {mae}"
        print("  Individual metrics: OK")

        # Test ArenaMetrics
        predictions = {
            "overall": [0.8, 0.7, 0.9],
            "sharpness": [0.7, 0.6, 0.8],
            "color": [0.85, 0.75, 0.9],
        }
        ground_truth = {
            "overall": [0.82, 0.68, 0.88],
            "sharpness": [0.72, 0.58, 0.78],
            "color": [0.83, 0.73, 0.88],
        }

        metrics = ArenaMetrics.compute(predictions, ground_truth)
        print(f"  Aggregate PLCC: {metrics.aggregate.plcc:.4f}")
        print("  ArenaMetrics: OK")

        return True
    except Exception as e:
        print(f"  Metrics test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_model_spec() -> bool:
    """Test ModelSpec schema."""
    print("\n--- Testing ModelSpec ---")
    try:
        from image_preprocessing_detector.labeling.model_spec import (
            ModelSource,
            ModelSpec,
            ModelVariant,
            RuntimeBackend,
        )

        # Create a spec for Qwen model
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
            revision="main",
            variant=ModelVariant.INT4,
            runtime=RuntimeBackend.TRANSFORMERS,
        )

        assert spec.is_quantized
        assert not spec.is_finetuned
        print(f"  Spec ID: {spec.spec_id}")
        print("  ModelSpec: OK")

        # Test serialization
        spec_dict = spec.to_dict()
        loaded = ModelSpec.from_dict(spec_dict)
        assert loaded.id == spec.id
        print("  Serialization roundtrip: OK")

        return True
    except Exception as e:
        print(f"  ModelSpec test failed: {e}")
        return False


def test_dataset_adapter() -> bool:
    """Test DIQA-5000 dataset adapter with synthetic data."""
    print("\n--- Testing Dataset Adapter ---")
    try:
        from image_preprocessing_detector.labeling.arena.datasets.diqa5000 import (
            DIQA5000Dataset,
        )

        # Create a temp directory for synthetic dataset
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the dataset (will use synthetic data)
            dataset = DIQA5000Dataset(tmpdir, split="test")

            print(f"  Dataset name: {dataset.name}")
            print(f"  Split: {dataset.current_split}")
            print(f"  Samples: {len(dataset)}")

            # Iterate over a few samples
            count = 0
            for sample in dataset:
                if count >= 3:
                    break
                print(f"    Sample {sample.image_id}: labels={sample.labels}")
                count += 1

            print("  Dataset adapter: OK")
            return True

    except Exception as e:
        print(f"  Dataset adapter test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_inference_backend_factory() -> bool:
    """Test inference backend factory."""
    print("\n--- Testing Inference Backend Factory ---")
    try:
        from image_preprocessing_detector.labeling.arena.inference.base import (
            create_backend,
        )

        # Test creating backends (without loading models)
        for source in ["huggingface", "local", "api", "modal"]:
            try:
                if source == "api":
                    create_backend(source, provider="openai")
                else:
                    create_backend(source)
                print(f"  {source} backend: created")
            except Exception as e:
                print(f"  {source} backend: {e}")

        print("  Backend factory: OK")
        return True

    except Exception as e:
        print(f"  Backend factory test failed: {e}")
        return False


def test_modal_client() -> bool:
    """Test Arena Modal client (mock mode)."""
    print("\n--- Testing Modal Client (Mock Mode) ---")
    try:
        import os

        os.environ["ARENA_MODAL_MOCK"] = "true"

        from image_preprocessing_detector.labeling.arena.modal_client import (
            ArenaInferenceRequest,
            ArenaModalClient,
        )

        client = ArenaModalClient()
        print(f"  Client initialized: app={client.app_name}")

        # Test mock prediction
        test_image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        request = ArenaInferenceRequest(
            image=test_image,
            prompt="Rate this document quality",
            request_id="test-001",
        )

        response = client.predict(request)
        assert response is not None
        assert "Overall:" in response.text
        print(f"  Mock response: {response.text[:50]}...")
        print(f"  Inference time: {response.inference_time_ms:.1f}ms")

        # Test batch prediction
        batch_requests = [
            ArenaInferenceRequest(
                image=rng.integers(0, 255, (224, 224, 3), dtype=np.uint8),
                prompt="Rate quality",
                request_id=f"batch-{i}",
            )
            for i in range(3)
        ]
        responses = client.batch_predict(batch_requests)
        assert len(responses) == 3
        print(f"  Batch predict: {len(responses)} responses")

        # Test circuit breaker stats
        stats = client.get_stats()
        print(f"  Circuit state: {stats['state']}")
        print(f"  Success rate: {stats['success_rate']:.2f}")

        print("  Modal client: OK")
        return True

    except Exception as e:
        print(f"  Modal client test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_modal_backend() -> bool:
    """Test Modal inference backend (mock mode)."""
    print("\n--- Testing Modal Backend (Mock Mode) ---")
    try:
        import os

        os.environ["ARENA_MODAL_MOCK"] = "true"

        from image_preprocessing_detector.labeling.arena.inference.base import (
            InferenceConfig,
        )
        from image_preprocessing_detector.labeling.arena.inference.modal import (
            ModalBackend,
        )
        from image_preprocessing_detector.labeling.model_spec import (
            ModelSource,
            ModelSpec,
            ModelVariant,
        )

        # Create backend
        backend = ModalBackend()
        assert not backend.is_loaded()
        print("  Backend created")

        # Load with model spec
        spec = ModelSpec(
            source=ModelSource.HUGGINGFACE,
            id="unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit",
            variant=ModelVariant.INT4,
            revision="main",
        )
        config = InferenceConfig(batch_size=4, device="modal")

        backend.load(spec, config)
        assert backend.is_loaded()
        print("  Backend loaded")

        # Test single prediction
        test_image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        prediction = backend.predict(test_image)
        assert 0 <= prediction.overall <= 1
        assert 0 <= prediction.sharpness <= 1
        assert 0 <= prediction.color <= 1
        print(
            f"  Prediction: overall={prediction.overall:.2f}, sharpness={prediction.sharpness:.2f}"
        )

        # Test batch prediction
        images = [rng.integers(0, 255, (224, 224, 3), dtype=np.uint8) for _ in range(4)]
        predictions = backend.predict_batch(images)
        assert len(predictions) == 4
        print(f"  Batch predict: {len(predictions)} predictions")

        # Test model info
        info = backend.get_model_info()
        assert info["backend"] == "modal"
        print(f"  Model info: {info['model_id']}")

        # Test provenance
        provenance = backend.get_provenance()
        assert provenance.model_checksum.startswith("modal-model:")
        print(f"  Provenance: {provenance.model_checksum}")

        # Cleanup
        backend.unload()
        assert not backend.is_loaded()
        print("  Backend unloaded")

        print("  Modal backend: OK")
        return True

    except Exception as e:
        print(f"  Modal backend test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_smolvlm_model_loading(device: str = "cuda", model_size: str = "256M") -> bool:
    """Test loading SmolVLM model (optimized for low VRAM).

    SmolVLM models are tiny vision-language models from HuggingFace:
    - 256M: < 1GB VRAM (smallest VLM in the world)
    - 500M: ~1-2GB VRAM
    - 2B: ~5.7GB VRAM (too big for 4GB GPU)

    Args:
        device: "cuda" or "cpu"
        model_size: "256M", "500M", or "2B"
    """
    print(f"\n--- Testing SmolVLM-{model_size} Model Loading ---")

    try:
        import torch
        from transformers import AutoModelForVision2Seq, AutoProcessor

        # Select model based on size
        model_ids = {
            "256M": "HuggingFaceTB/SmolVLM-256M-Instruct",
            "500M": "HuggingFaceTB/SmolVLM-500M-Instruct",
            "2B": "HuggingFaceTB/SmolVLM-Instruct",
        }

        model_id = model_ids.get(model_size, model_ids["256M"])
        print(f"  Model: {model_id}")
        print(f"  Device: {device}")

        # Check CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            print("  CUDA not available, falling back to CPU")
            device = "cpu"

        # Show GPU memory if available
        if device == "cuda":
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  GPU memory: {gpu_mem:.1f}GB")

        start_time = time.time()

        # Load model - SmolVLM is small enough to not need quantization
        if device == "cuda":
            model = AutoModelForVision2Seq.from_pretrained(
                model_id,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            model = AutoModelForVision2Seq.from_pretrained(
                model_id,
                torch_dtype=torch.float32,
                device_map="cpu",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

        load_time = time.time() - start_time
        print(f"  Model loaded in {load_time:.2f}s")

        # Show memory usage
        if device == "cuda":
            mem_used = torch.cuda.memory_allocated() / 1e9
            print(f"  GPU memory used: {mem_used:.2f}GB")

        # Test inference on a simple image
        print("  Running test inference...")
        test_image = Image.fromarray(
            rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        )

        # SmolVLM uses a simpler chat format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {
                        "type": "text",
                        "text": "Rate this image quality from 0 to 1. Reply with just a number.",
                    },
                ],
            }
        ]

        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(
            text=prompt,
            images=[test_image],
            return_tensors="pt",
        )

        if device == "cuda":
            inputs = {
                k: v.cuda() if hasattr(v, "cuda") else v for k, v in inputs.items()
            }

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
            )

        response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        print(f"  Model response: {response[:100]}...")
        print(f"  SmolVLM-{model_size}: OK")

        # Cleanup
        del model
        del processor
        if device == "cuda":
            torch.cuda.empty_cache()

        return True

    except ImportError as e:
        print(f"  Import error: {e}")
        print("  Install with: uv sync --extra labeling")
        return False
    except Exception as e:
        print(f"  Model loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qwen_vlm_loading(device: str = "cuda") -> bool:
    """Test loading Qwen2.5-VL-3B (requires ~2-3GB VRAM with 4-bit).

    For 4GB VRAM, this should work but may be tight with long sequences.
    """
    print("\n--- Testing Qwen2.5-VL-3B Model Loading ---")

    try:
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        # The 3B model is the smallest Qwen VL
        model_id = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit"

        print(f"  Model: {model_id}")
        print(f"  Device: {device}")

        # Check CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            print("  CUDA not available, falling back to CPU")
            device = "cpu"

        # Show GPU memory if available
        if device == "cuda":
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  GPU memory: {gpu_mem:.1f}GB")
            if gpu_mem < 4.0:
                print("  Warning: Model may not fit in available VRAM")

        start_time = time.time()

        # Load with 4-bit quantization
        if device == "cuda":
            from transformers import BitsAndBytesConfig

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float32,
                device_map="cpu",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

        load_time = time.time() - start_time
        print(f"  Model loaded in {load_time:.2f}s")

        # Show memory usage
        if device == "cuda":
            mem_used = torch.cuda.memory_allocated() / 1e9
            print(f"  GPU memory used: {mem_used:.2f}GB")

        # Test inference
        print("  Running test inference...")
        test_image = Image.fromarray(
            rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": test_image},
                    {"type": "text", "text": "Rate this image quality from 0 to 1."},
                ],
            }
        ]

        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(
            text=[text],
            images=[test_image],
            return_tensors="pt",
            padding=True,
        )

        if device == "cuda":
            inputs = {
                k: v.cuda() if hasattr(v, "cuda") else v for k, v in inputs.items()
            }

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
            )

        response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        print(f"  Model response: {response[:100]}...")
        print("  Qwen2.5-VL-3B: OK")

        # Cleanup
        del model
        del processor
        if device == "cuda":
            torch.cuda.empty_cache()

        return True

    except ImportError as e:
        print(f"  Import error: {e}")
        print("  Install with: uv sync --extra labeling")
        return False
    except Exception as e:
        print(f"  Model loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_leaderboard_generator() -> bool:
    """Test leaderboard generation."""
    print("\n--- Testing Leaderboard Generator ---")
    try:
        from image_preprocessing_detector.labeling.arena.leaderboard import (
            LeaderboardConfig,
            LeaderboardGenerator,
        )
        from image_preprocessing_detector.labeling.arena.schemas import (
            BenchmarkResult,
            DatasetInfo,
            ExecutionInfo,
            ProvenanceInfo,
            RunStatus,
        )

        config = LeaderboardConfig(
            title="Test Leaderboard",
            sort_by="aggregate.plcc",
        )

        generator = LeaderboardGenerator(config)

        # Add some fake results
        for i, (name, plcc) in enumerate(
            [
                ("model-a", 0.92),
                ("model-b", 0.88),
                ("model-c", 0.95),
            ]
        ):
            result = BenchmarkResult(
                run_id=f"run_{i}",
                status=RunStatus.COMPLETED,
                model_spec={
                    "id": f"test/{name}",
                    "source": "huggingface",
                    "variant": "base",
                },
                dataset=DatasetInfo(
                    name="diqa5000",
                    version="1.0",
                    split="test",
                    num_samples=100,
                ),
                metrics={
                    "overall": {
                        "plcc": plcc,
                        "srcc": plcc - 0.02,
                        "mae": 0.1 - plcc * 0.05,
                        "rmse": 0.12 - plcc * 0.05,
                        "num_samples": 100,
                    },
                    "sharpness": {
                        "plcc": plcc - 0.03,
                        "srcc": plcc - 0.05,
                        "mae": 0.11 - plcc * 0.05,
                        "rmse": 0.13 - plcc * 0.05,
                        "num_samples": 100,
                    },
                    "color": {
                        "plcc": plcc + 0.01,
                        "srcc": plcc - 0.01,
                        "mae": 0.09 - plcc * 0.05,
                        "rmse": 0.11 - plcc * 0.05,
                        "num_samples": 100,
                    },
                    "aggregate": {
                        "plcc": plcc,
                        "srcc": plcc - 0.03,
                        "mae": 0.1 - plcc * 0.05,
                        "rmse": 0.12 - plcc * 0.05,
                        "num_samples": 100,
                    },
                },
                execution=ExecutionInfo(
                    hardware="Test",
                    duration_seconds=10.0,
                    batch_size=8,
                ),
                provenance=ProvenanceInfo(),
            )
            generator.add_result(result)

        # Generate Markdown
        md = generator.to_markdown()
        assert "model-c" in md  # Should be ranked first (highest PLCC)
        print("  Markdown generation: OK")

        # Generate HTML
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            html_path = Path(f.name)
        generator.to_html(html_path)
        assert html_path.exists()
        print(f"  HTML generation: OK ({html_path})")

        return True

    except Exception as e:
        print(f"  Leaderboard test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> int:
    """Run all tests."""
    parser = argparse.ArgumentParser(
        description="Test Arena framework locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model Options for 4GB VRAM:
  smolvlm-256m  - < 1GB VRAM (smallest VLM, recommended)
  smolvlm-500m  - ~1-2GB VRAM
  qwen-3b       - ~2-3GB VRAM with 4-bit quantization

Examples:
  uv run python scripts/test_arena_local.py --skip-model           # Framework only
  uv run python scripts/test_arena_local.py --model smolvlm-256m   # Tiny model
  uv run python scripts/test_arena_local.py --model qwen-3b        # Qwen 3B
""",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=5,
        help="Number of test samples",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use for model testing",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="smolvlm-256m",
        choices=["smolvlm-256m", "smolvlm-500m", "smolvlm-2b", "qwen-3b"],
        help="Model to test (default: smolvlm-256m for 4GB VRAM)",
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Skip model loading test (faster)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Arena Local Test Suite")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        print("\nDependency check failed. Please install missing packages.")
        return 1

    results = {}

    # Run tests
    results["schemas"] = test_schemas()
    results["metrics"] = test_metrics()
    results["model_spec"] = test_model_spec()
    results["dataset_adapter"] = test_dataset_adapter()
    results["backend_factory"] = test_inference_backend_factory()
    results["leaderboard"] = test_leaderboard_generator()
    results["modal_client"] = test_modal_client()
    results["modal_backend"] = test_modal_backend()

    if not args.skip_model:
        if args.model.startswith("smolvlm"):
            # Map model arg to size
            size_map = {
                "smolvlm-256m": "256M",
                "smolvlm-500m": "500M",
                "smolvlm-2b": "2B",
            }
            model_size = size_map.get(args.model, "256M")
            results["vlm_model"] = test_smolvlm_model_loading(
                device=args.device, model_size=model_size
            )
        elif args.model == "qwen-3b":
            results["vlm_model"] = test_qwen_vlm_loading(device=args.device)
    else:
        print("\n--- Skipping Model Loading Test ---")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
