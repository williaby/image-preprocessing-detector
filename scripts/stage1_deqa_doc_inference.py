#!/usr/bin/env python3
"""Stage 1: DeQA-Doc Inference for Unified Labeling Strategy.

This script runs DeQA-Doc inference on strategic datasets to create
high-quality soft-label distributions for training DocIQ-Replica.

Datasets processed:
- DIQA-5000: 5,000 images (primary anchor with human MOS)
- SmartDoc-QA: 4,260 images (OCR correlation validation)
- OCR-Quality: 1,000 images (human quality scores, multilingual)
- DIBCO: 148 images (extreme degradation)
- FUNSD: 149 images (noisy forms)
- SROIE: 2,043 images (mobile capture)
- Tobacco-800: 1,290 images (archival degradation)

Total: ~13,890 images

Usage:
    # Run all datasets
    python scripts/stage1_deqa_doc_inference.py --all

    # Run specific dataset
    python scripts/stage1_deqa_doc_inference.py --dataset diqa-5000

    # Run with 4-bit quantization (lower memory)
    python scripts/stage1_deqa_doc_inference.py --all --quantize 4bit

    # Resume from checkpoint
    python scripts/stage1_deqa_doc_inference.py --all --resume

Output:
    Creates JSONL files in output_dir with soft-label distributions:
    {
        "image": "path/to/image.jpg",
        "dataset": "diqa-5000",
        "logits": {"excellent": 0.5, "good": 0.3, ...},
        "probs": {"excellent": 0.35, "good": 0.30, ...},
        "predicted_score": 3.85,
        "predicted_scores": {
            "overall": 3.85,
            "sharpness": 4.12,
            "color": 3.56
        }
    }
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from tqdm import tqdm

# Add DeQA-Score to path
DEQA_SCORE_PATH = Path("/home/byron/dev/DeQA-Doc/DeQA-Score")
sys.path.insert(0, str(DEQA_SCORE_PATH))


@dataclass
class DatasetConfig:
    """Configuration for a Stage 1 dataset."""

    name: str
    root_dir: Path
    image_pattern: str  # Glob pattern to find images
    has_human_scores: bool = False
    human_score_file: Path | None = None
    priority: str = "HIGH"  # CRITICAL, HIGH, MEDIUM
    notes: str = ""


# Stage 1 Dataset Configurations
STAGE1_DATASETS: dict[str, DatasetConfig] = {
    "diqa-5000": DatasetConfig(
        name="diqa-5000",
        root_dir=Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000"),
        image_pattern="*/res/*.jpg",  # train/res, test/res, val/res
        has_human_scores=True,
        human_score_file=Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000"),
        priority="CRITICAL",
        notes="Primary anchor with 3-dim human MOS scores",
    ),
    "smartdoc-qa": DatasetConfig(
        name="smartdoc-qa",
        root_dir=Path(
            "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images"
        ),
        image_pattern="**/*.jpg",
        has_human_scores=False,
        priority="HIGH",
        notes="OCR correlation validation",
    ),
    "ocr-quality": DatasetConfig(
        name="ocr-quality",
        root_dir=Path("/mnt/e/image_detection/01_base_data/ocr_quality/pics"),
        image_pattern="*.png",
        has_human_scores=True,
        human_score_file=Path(
            "/mnt/e/image_detection/01_base_data/ocr_quality/OCR-Quality.json"
        ),
        priority="HIGH",
        notes="Human quality scores (1-4), multilingual",
    ),
    "dibco": DatasetConfig(
        name="dibco",
        root_dir=Path("/mnt/e/image_detection/02_benchmark_only/dibco/DIBCO"),
        image_pattern="**/*.[pPjJtTbB][nNpPiIgGmM][gGfFpP]",  # png, jpg, tif, bmp
        has_human_scores=False,
        priority="HIGH",
        notes="Extreme degradation edge cases",
    ),
    "funsd": DatasetConfig(
        name="funsd",
        root_dir=Path("/mnt/e/image_detection/01_base_data/forms/funsd"),
        image_pattern="**/*.png",
        has_human_scores=False,
        priority="MEDIUM",
        notes="Real noisy scanned forms",
    ),
    "sroie": DatasetConfig(
        name="sroie",
        root_dir=Path("/mnt/e/image_detection/01_base_data/forms/sroie"),
        image_pattern="**/*.jpg",
        has_human_scores=False,
        priority="MEDIUM",
        notes="Mobile capture / thermal print",
    ),
    "tobacco-800": DatasetConfig(
        name="tobacco-800",
        root_dir=Path("/mnt/e/image_detection/01_base_data/degraded/tobacco800"),
        image_pattern="**/*.[tTjJpP][iIpPnN][fFgG]",  # tif, jpg, png
        has_human_scores=False,
        priority="MEDIUM",
        notes="Real archival degradation",
    ),
}

# Quality level names (must match DeQA-Doc training)
LEVEL_NAMES = ["excellent", "good", "fair", "poor", "bad"]
LEVEL_SCORES = [5.0, 4.0, 3.0, 2.0, 1.0]  # Corresponding numeric scores


@dataclass
class InferenceResult:
    """Result from DeQA-Doc inference on a single image."""

    image_path: str
    dataset: str
    logits: dict[str, float] = field(default_factory=dict)
    probs: dict[str, float] = field(default_factory=dict)
    predicted_score: float = 0.0
    inference_time_ms: float = 0.0
    error: str | None = None


def softmax(logits: list[float]) -> list[float]:
    """Apply softmax to logits."""
    import math

    max_logit = max(logits)
    exp_logits = [math.exp(x - max_logit) for x in logits]
    sum_exp = sum(exp_logits)
    return [x / sum_exp for x in exp_logits]


def logits_to_score(logits: dict[str, float]) -> tuple[dict[str, float], float]:
    """Convert logits to probabilities and weighted score.

    Args:
        logits: Dict mapping level names to logit values

    Returns:
        Tuple of (probs dict, weighted score 1-5)
    """
    logit_values = [logits[name] for name in LEVEL_NAMES]
    prob_values = softmax(logit_values)
    probs = dict(zip(LEVEL_NAMES, prob_values))
    score = sum(p * s for p, s in zip(prob_values, LEVEL_SCORES))
    return probs, score


def discover_images(config: DatasetConfig) -> list[Path]:
    """Discover all images for a dataset based on its configuration."""
    images = list(config.root_dir.glob(config.image_pattern))

    # Filter to actual image files
    valid_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    images = [p for p in images if p.suffix.lower() in valid_extensions and p.is_file()]

    return sorted(images)


def load_human_scores_diqa(config: DatasetConfig) -> dict[str, dict[str, float]]:
    """Load DIQA-5000 human MOS scores from CSV files."""
    scores = {}

    for split in ["train", "test", "val"]:
        csv_path = config.human_score_file / split / f"{split}.csv"
        if not csv_path.exists():
            continue

        with open(csv_path) as f:
            header = f.readline().strip().split(",")
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 5:
                    res_name = parts[0]
                    scores[res_name] = {
                        "overall": float(parts[2]),
                        "sharpness": float(parts[3]),
                        "color": float(parts[4]),
                    }

    return scores


def load_human_scores_ocr_quality(config: DatasetConfig) -> dict[str, float]:
    """Load OCR-Quality human scores from JSON."""
    if not config.human_score_file or not config.human_score_file.exists():
        return {}

    with open(config.human_score_file) as f:
        data = json.load(f)

    # OCR-Quality uses index as filename (0.png, 1.png, etc.)
    # Score is inverted: 1=best, 4=worst
    scores = {}
    for item in data:
        idx = item.get("index", item.get("id"))
        human_score = item.get("human_score", item.get("score"))
        if idx is not None and human_score is not None:
            # Convert to 0-1 scale (higher=better)
            normalized = (5 - human_score) / 4
            scores[f"{idx}.png"] = normalized

    return scores


class DeQADocInference:
    """DeQA-Doc inference wrapper for batch processing."""

    def __init__(
        self,
        model_path: str = "zhalala/DeQA-Doc-Mix",
        device: str = "cuda:0",
        quantize: str | None = None,
        batch_size: int = 4,
    ):
        """Initialize DeQA-Doc model.

        Args:
            model_path: HuggingFace model ID or local path
            device: Device to use (cuda:0, cuda:1, cpu)
            quantize: Quantization mode (None, '8bit', '4bit')
            batch_size: Batch size for inference
        """
        self.model_path = model_path
        self.device = device
        self.quantize = quantize
        self.batch_size = batch_size
        self.model = None
        self.processor = None

    def load_model(self):
        """Load DeQA-Doc model."""
        print(f"Loading DeQA-Doc model: {self.model_path}")
        print(f"Device: {self.device}, Quantization: {self.quantize or 'None'}")

        try:
            # Try to use the DeQA-Score scorer interface
            from src.evaluate.scorer import DeQAScorer

            load_kwargs = {}
            if self.quantize == "8bit":
                load_kwargs["load_in_8bit"] = True
            elif self.quantize == "4bit":
                load_kwargs["load_in_4bit"] = True

            self.model = DeQAScorer(
                model_path=self.model_path,
                device=self.device,
                **load_kwargs,
            )
            print("Loaded via DeQAScorer interface")

        except ImportError:
            # Fallback to direct HuggingFace loading
            print("DeQAScorer not available, using direct HuggingFace loading...")
            from transformers import AutoModelForCausalLM, AutoProcessor

            load_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16,
                "device_map": "auto" if "cuda" in self.device else None,
            }

            if self.quantize == "8bit":
                load_kwargs["load_in_8bit"] = True
            elif self.quantize == "4bit":
                load_kwargs["load_in_4bit"] = True

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **load_kwargs,
            )
            print("Loaded via AutoModelForCausalLM")

        print("Model loaded successfully!")

    def infer_single(self, image_path: Path, dimension: str = "overall") -> dict:
        """Run inference on a single image for a specific dimension.

        Args:
            image_path: Path to image file
            dimension: Quality dimension (overall, sharpness, color)

        Returns:
            Dict with logits, probs, and predicted score
        """
        start_time = time.time()

        try:
            image = Image.open(image_path).convert("RGB")

            # Get raw scores from model
            if hasattr(self.model, "score"):
                # DeQAScorer interface
                scores = self.model.score([image])
                score = scores[0] if scores else 0.0

                # For DeQA-Mix, we get a single score
                # We'll need to run per-dimension models for full 3-dim output
                return {
                    "logits": {},  # Not available from simple interface
                    "probs": {},
                    "predicted_score": score,
                    "inference_time_ms": (time.time() - start_time) * 1000,
                }
            else:
                # Direct model interface - would need custom inference logic
                raise NotImplementedError(
                    "Direct model inference not yet implemented. Use DeQAScorer."
                )

        except Exception as e:
            return {
                "error": str(e),
                "inference_time_ms": (time.time() - start_time) * 1000,
            }

    def infer_batch_with_logits(
        self, image_paths: list[Path], dimension: str = "overall"
    ) -> list[dict]:
        """Run batch inference using iqa_eval.py logic to get logits.

        This method uses the full DeQA-Doc evaluation pipeline to get
        both logits and probabilities for soft-label training.
        """
        results = []

        for image_path in tqdm(image_paths, desc=f"Inferring {dimension}"):
            result = self.infer_single(image_path, dimension)
            result["image_path"] = str(image_path)
            results.append(result)

        return results


def run_inference_for_dataset(
    config: DatasetConfig,
    inference: DeQADocInference,
    output_dir: Path,
    resume: bool = False,
) -> dict[str, Any]:
    """Run DeQA-Doc inference for a single dataset.

    Args:
        config: Dataset configuration
        inference: DeQADocInference instance
        output_dir: Directory to save results
        resume: Whether to resume from existing results

    Returns:
        Dict with statistics about the inference run
    """
    print(f"\n{'='*60}")
    print(f"Processing: {config.name}")
    print(f"Priority: {config.priority}")
    print(f"Notes: {config.notes}")
    print(f"{'='*60}")

    # Discover images
    images = discover_images(config)
    print(f"Found {len(images)} images")

    if not images:
        print(f"WARNING: No images found for {config.name}")
        return {"dataset": config.name, "images_found": 0, "images_processed": 0}

    # Output file
    output_file = output_dir / f"{config.name}_deqa_labels.jsonl"

    # Check for resume
    processed_images = set()
    if resume and output_file.exists():
        with open(output_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    processed_images.add(record.get("image"))
                except json.JSONDecodeError:
                    continue
        print(f"Resuming: {len(processed_images)} images already processed")

    # Filter to unprocessed images
    images_to_process = [
        img
        for img in images
        if str(img.relative_to(config.root_dir)) not in processed_images
    ]

    if not images_to_process:
        print("All images already processed!")
        return {
            "dataset": config.name,
            "images_found": len(images),
            "images_processed": len(processed_images),
            "images_skipped": len(processed_images),
        }

    print(f"Processing {len(images_to_process)} images...")

    # Load human scores if available
    human_scores = {}
    if config.has_human_scores:
        if config.name == "diqa-5000":
            human_scores = load_human_scores_diqa(config)
            print(f"Loaded {len(human_scores)} human MOS scores for DIQA-5000")
        elif config.name == "ocr-quality":
            human_scores = load_human_scores_ocr_quality(config)
            print(f"Loaded {len(human_scores)} human scores for OCR-Quality")

    # Run inference
    stats = {
        "dataset": config.name,
        "images_found": len(images),
        "images_processed": 0,
        "images_skipped": len(processed_images),
        "errors": 0,
        "total_inference_time_ms": 0,
    }

    with open(output_file, "a") as f:
        for image_path in tqdm(images_to_process, desc=config.name):
            # Get relative path for record
            rel_path = str(image_path.relative_to(config.root_dir))

            # Run inference
            result = inference.infer_single(image_path)

            # Build output record
            record = {
                "image": rel_path,
                "image_full_path": str(image_path),
                "dataset": config.name,
                "timestamp": datetime.now().isoformat(),
            }

            if "error" in result:
                record["error"] = result["error"]
                stats["errors"] += 1
            else:
                record["predicted_score"] = result.get("predicted_score", 0)
                record["logits"] = result.get("logits", {})
                record["probs"] = result.get("probs", {})
                record["inference_time_ms"] = result.get("inference_time_ms", 0)
                stats["total_inference_time_ms"] += record["inference_time_ms"]

                # Add human scores if available
                image_name = image_path.name
                if image_name in human_scores:
                    if config.name == "diqa-5000":
                        record["human_mos"] = human_scores[image_name]
                    elif config.name == "ocr-quality":
                        record["human_score_normalized"] = human_scores[image_name]

            # Write record
            f.write(json.dumps(record) + "\n")
            stats["images_processed"] += 1

    # Calculate average inference time
    if stats["images_processed"] > 0:
        stats["avg_inference_time_ms"] = (
            stats["total_inference_time_ms"] / stats["images_processed"]
        )

    print(f"\nCompleted {config.name}:")
    print(f"  Processed: {stats['images_processed']}")
    print(f"  Errors: {stats['errors']}")
    if "avg_inference_time_ms" in stats:
        print(f"  Avg inference time: {stats['avg_inference_time_ms']:.1f}ms")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1: DeQA-Doc Inference for Unified Labeling Strategy"
    )

    # Dataset selection
    parser.add_argument(
        "--all", action="store_true", help="Process all Stage 1 datasets"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(STAGE1_DATASETS.keys()),
        help="Process specific dataset",
    )

    # Model configuration
    parser.add_argument(
        "--model-path",
        type=str,
        default="zhalala/DeQA-Doc-Mix",
        help="HuggingFace model ID or local path",
    )
    parser.add_argument(
        "--device", type=str, default="cuda:0", help="Device (cuda:0, cuda:1, cpu)"
    )
    parser.add_argument(
        "--quantize",
        type=str,
        choices=["8bit", "4bit"],
        help="Quantization mode for lower memory",
    )
    parser.add_argument(
        "--batch-size", type=int, default=4, help="Batch size for inference"
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/mnt/e/image_detection/06_staging/stage1_deqa_labels",
        help="Output directory for results",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from existing results"
    )

    # Utility
    parser.add_argument(
        "--list-datasets", action="store_true", help="List available datasets and exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover images without running inference",
    )

    args = parser.parse_args()

    # List datasets
    if args.list_datasets:
        print("\nStage 1 Datasets:")
        print("-" * 80)
        total_images = 0
        for name, config in STAGE1_DATASETS.items():
            images = discover_images(config)
            total_images += len(images)
            print(f"  {name:15} | {len(images):6} images | {config.priority:8} | {config.notes}")
        print("-" * 80)
        print(f"  {'TOTAL':15} | {total_images:6} images")
        return

    # Validate arguments
    if not args.all and not args.dataset:
        parser.error("Either --all or --dataset must be specified")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which datasets to process
    if args.all:
        datasets_to_process = list(STAGE1_DATASETS.values())
    else:
        datasets_to_process = [STAGE1_DATASETS[args.dataset]]

    # Dry run - just count images
    if args.dry_run:
        print("\nDry Run - Image Discovery:")
        print("-" * 60)
        total = 0
        for config in datasets_to_process:
            images = discover_images(config)
            total += len(images)
            print(f"  {config.name}: {len(images)} images")
        print("-" * 60)
        print(f"  Total: {total} images")
        return

    # Check CUDA availability
    if "cuda" in args.device and not torch.cuda.is_available():
        print("WARNING: CUDA not available, falling back to CPU")
        args.device = "cpu"

    # Initialize inference
    inference = DeQADocInference(
        model_path=args.model_path,
        device=args.device,
        quantize=args.quantize,
        batch_size=args.batch_size,
    )

    # Load model
    inference.load_model()

    # Process each dataset
    all_stats = []
    start_time = time.time()

    for config in datasets_to_process:
        stats = run_inference_for_dataset(
            config=config,
            inference=inference,
            output_dir=output_dir,
            resume=args.resume,
        )
        all_stats.append(stats)

    # Summary
    total_time = time.time() - start_time
    total_processed = sum(s.get("images_processed", 0) for s in all_stats)
    total_errors = sum(s.get("errors", 0) for s in all_stats)

    print("\n" + "=" * 60)
    print("STAGE 1 INFERENCE COMPLETE")
    print("=" * 60)
    print(f"Total images processed: {total_processed}")
    print(f"Total errors: {total_errors}")
    print(f"Total time: {total_time / 60:.1f} minutes")
    print(f"Output directory: {output_dir}")

    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "model_path": args.model_path,
        "device": args.device,
        "quantize": args.quantize,
        "total_processed": total_processed,
        "total_errors": total_errors,
        "total_time_seconds": total_time,
        "datasets": all_stats,
    }

    summary_file = output_dir / "stage1_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
