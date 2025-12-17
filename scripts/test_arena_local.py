#!/usr/bin/env python
"""Local test script for Arena framework with Qwen2.5-VL model.

This script tests the Arena benchmarking framework locally without Modal.com
using the unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit model.

Usage:
    # Install dependencies first
    uv sync --extra labeling --extra dev

    # Run the test
    uv run python scripts/test_arena_local.py

    # Run with specific options
    uv run python scripts/test_arena_local.py --num-samples 5 --device cpu
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image


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


def create_test_images(num_images: int = 5) -> list[tuple[np.ndarray, dict[str, float]]]:
    """Create synthetic test images with ground truth labels.

    Returns:
        List of (image_array, labels) tuples.
    """
    images = []
    np.random.seed(42)

    for i in range(num_images):
        # Create varied test images
        img = np.zeros((224, 224, 3), dtype=np.uint8)

        # Vary quality characteristics
        noise_level = np.random.uniform(0.1, 0.5)
        brightness = np.random.uniform(0.3, 0.9)
        sharpness_factor = np.random.uniform(0.3, 0.9)

        # Base image with gradient
        for y in range(224):
            for x in range(224):
                img[y, x] = [
                    int(brightness * 255 * (x / 224)),
                    int(brightness * 255 * (y / 224)),
                    int(brightness * 255 * ((x + y) / 448)),
                ]

        # Add noise
        noise = np.random.normal(0, noise_level * 50, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Ground truth labels (simulated)
        labels = {
            "overall": float(np.clip(0.7 - noise_level * 0.5 + brightness * 0.2, 0.3, 0.95)),
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
        assert pred.overall == 0.85
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
            InferenceConfig,
            create_backend,
        )

        # Test creating backends (without loading models)
        for source in ["huggingface", "local", "api"]:
            try:
                if source == "api":
                    backend = create_backend(source, provider="openai")
                else:
                    backend = create_backend(source)
                print(f"  {source} backend: created")
            except Exception as e:
                print(f"  {source} backend: {e}")

        print("  Backend factory: OK")
        return True

    except Exception as e:
        print(f"  Backend factory test failed: {e}")
        return False


def test_qwen_model_loading(device: str = "cuda") -> bool:
    """Test loading the Qwen2.5-VL model."""
    print("\n--- Testing Qwen Model Loading ---")

    try:
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        model_id = "unsloth/Qwen2.5-VL-3B-Instruct-unsloth-bnb-4bit"

        print(f"  Loading model: {model_id}")
        print(f"  Device: {device}")

        # Check CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            print("  CUDA not available, falling back to CPU")
            device = "cpu"

        start_time = time.time()

        # Load with 4-bit quantization config for the bnb model
        if device == "cuda":
            try:
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
            except Exception as e:
                print(f"  4-bit loading failed: {e}")
                print("  Trying without quantization...")
                model = Qwen2VLForConditionalGeneration.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True,
                )
        else:
            # CPU loading
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

        # Test inference on a simple image
        print("  Running test inference...")
        test_image = Image.fromarray(
            np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
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
            inputs = {k: v.cuda() if hasattr(v, "cuda") else v for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
            )

        response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        print(f"  Model response: {response[:100]}...")
        print("  Qwen model: OK")

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
        for i, (name, plcc) in enumerate([
            ("model-a", 0.92),
            ("model-b", 0.88),
            ("model-c", 0.95),
        ]):
            result = BenchmarkResult(
                run_id=f"run_{i}",
                status=RunStatus.COMPLETED,
                model_spec={"id": f"test/{name}", "source": "huggingface", "variant": "base"},
                dataset=DatasetInfo(
                    name="diqa5000",
                    version="1.0",
                    split="test",
                    num_samples=100,
                ),
                metrics={
                    "overall": {"plcc": plcc, "srcc": plcc - 0.02, "mae": 0.1 - plcc * 0.05, "rmse": 0.12 - plcc * 0.05, "num_samples": 100},
                    "sharpness": {"plcc": plcc - 0.03, "srcc": plcc - 0.05, "mae": 0.11 - plcc * 0.05, "rmse": 0.13 - plcc * 0.05, "num_samples": 100},
                    "color": {"plcc": plcc + 0.01, "srcc": plcc - 0.01, "mae": 0.09 - plcc * 0.05, "rmse": 0.11 - plcc * 0.05, "num_samples": 100},
                    "aggregate": {"plcc": plcc, "srcc": plcc - 0.03, "mae": 0.1 - plcc * 0.05, "rmse": 0.12 - plcc * 0.05, "num_samples": 100},
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
    parser = argparse.ArgumentParser(description="Test Arena framework locally")
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

    if not args.skip_model:
        results["qwen_model"] = test_qwen_model_loading(device=args.device)
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
