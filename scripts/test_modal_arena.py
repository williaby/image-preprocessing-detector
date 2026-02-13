#!/usr/bin/env python3
"""Test Modal Arena benchmark with 5 DIQA-5000 samples.

This script tests the deployed Modal app by running VLM inference
on 5 real samples from the DIQA-5000 test set.
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import modal
from PIL import Image

# DIQA-5000 dataset location
DIQA_ROOT = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
TEST_DIR = DIQA_ROOT / "test"
TEST_CSV = TEST_DIR / "test.csv"
RES_DIR = TEST_DIR / "res"

# IQA prompt for document quality assessment
IQA_PROMPT = """Analyze this document image and rate its quality on a scale of 1-5 for each dimension:
1. Overall quality (considering all aspects)
2. Sharpness (text clarity, edge definition)
3. Color fidelity (color accuracy, consistency)

Provide your ratings in this exact format:
Overall: X.X
Sharpness: X.X
Color: X.X

Where X.X is a number between 1.0 and 5.0."""


def load_test_samples(num_samples: int = 5) -> list[dict]:
    """Load test samples from DIQA-5000 test set.

    Args:
        num_samples: Number of samples to load.

    Returns:
        List of sample dictionaries with image_b64, ground_truth, and metadata.
    """
    import csv

    samples = []

    with open(TEST_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= num_samples:
                break

            image_filename = row["res"]
            image_path = RES_DIR / image_filename

            if not image_path.exists():
                print(f"Warning: Image not found: {image_path}")
                continue

            # Load and encode image
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=95)
                image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            # Parse ground truth (MOS scores 1-5)
            ground_truth = {
                "overall": float(row["overall"]),
                "sharpness": float(row["sharpness"]),
                "color": float(row["color_fidelity"]),
            }

            samples.append(
                {
                    "sample_id": image_filename.replace(".jpg", ""),
                    "image_b64": image_b64,
                    "ground_truth": ground_truth,
                    "image_path": str(image_path),
                }
            )

            print(
                f"Loaded sample {i + 1}: {image_filename} (GT: overall={ground_truth['overall']:.2f})"
            )

    return samples


def run_modal_inference(samples: list[dict]) -> list[dict]:
    """Run inference via Modal backend.

    Args:
        samples: List of sample dictionaries.

    Returns:
        List of result dictionaries with predictions.
    """
    print("\nConnecting to Modal app 'arena-benchmark'...")

    # Look up the deployed VLMInference class
    vlm_inference_cls = modal.Cls.from_name("arena-benchmark", "VLMInference")
    inference = vlm_inference_cls()

    results = []

    for i, sample in enumerate(samples):
        print(f"\nProcessing sample {i + 1}/{len(samples)}: {sample['sample_id']}...")

        try:
            result = inference.predict.remote(
                image_b64=sample["image_b64"],
                prompt=IQA_PROMPT,
                model_id="HuggingFaceTB/SmolVLM-256M-Instruct",
                max_new_tokens=128,
                temperature=0.1,
            )

            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "prediction": result,
                    "success": True,
                }
            )

            print(f"  Inference time: {result.get('inference_time_ms', 0):.0f}ms")
            print(f"  Response: {result.get('text', '')[:100]}...")

        except Exception as e:
            print(f"  Error: {e}")
            results.append(
                {
                    "sample_id": sample["sample_id"],
                    "ground_truth": sample["ground_truth"],
                    "prediction": {"error": str(e)},
                    "success": False,
                }
            )

    return results


def main():
    """Run 5-sample Modal benchmark test."""
    print("=" * 60)
    print("Modal Arena Benchmark Test - 5 DIQA-5000 Samples")
    print("=" * 60)

    # Check dataset exists
    if not TEST_CSV.exists():
        print(f"Error: DIQA-5000 test CSV not found at {TEST_CSV}")
        return 1

    if not RES_DIR.exists():
        print(f"Error: DIQA-5000 test images not found at {RES_DIR}")
        return 1

    print(f"\nDataset: {DIQA_ROOT}")
    print(f"Test CSV: {TEST_CSV}")
    print(f"Images: {RES_DIR}")

    # Load samples
    print("\n--- Loading Test Samples ---")
    samples = load_test_samples(num_samples=5)

    if not samples:
        print("Error: No samples loaded")
        return 1

    print(f"\nLoaded {len(samples)} samples")

    # Run Modal inference
    print("\n--- Running Modal Inference ---")
    results = run_modal_inference(samples)

    # Summary
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    successful = sum(1 for r in results if r["success"])
    print(f"Successful: {successful}/{len(results)}")

    for result in results:
        status = "✓" if result["success"] else "✗"
        gt = result["ground_truth"]
        print(f"\n{status} {result['sample_id']}")
        print(
            f"  Ground Truth: overall={gt['overall']:.2f}, sharpness={gt['sharpness']:.2f}, color={gt['color']:.2f}"
        )
        if result["success"]:
            print(f"  Model Response: {result['prediction'].get('text', '')[:80]}...")
            print(
                f"  Inference Time: {result['prediction'].get('inference_time_ms', 0):.0f}ms"
            )
        else:
            print(f"  Error: {result['prediction'].get('error', 'Unknown error')}")

    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
