"""Modal-based Stage 1 DeQA-Doc Inference.

This runs DeQA-Doc inference on Modal's cloud GPUs for faster processing.
With an A100 (40GB), can process all 13,890 images in ~30-45 minutes.

Usage:
    # Test with 100 samples first (detached mode recommended)
    modal run --detach modal/stage1_deqa_inference.py --test

    # Run all datasets (always use --detach for long runs)
    modal run --detach modal/stage1_deqa_inference.py

    # Run specific dataset
    modal run --detach modal/stage1_deqa_inference.py --dataset diqa-5000

    # Dry run (no processing)
    modal run modal/stage1_deqa_inference.py --dry-run

Note: Always use --detach (-d) for non-trivial runs to avoid losing progress
if your local terminal disconnects.
"""

import json
import time
from datetime import datetime
from pathlib import Path

import modal

# Modal app definition
app = modal.App("stage1-deqa-inference")

# Create a volume for storing results
results_volume = modal.Volume.from_name("stage1-deqa-results", create_if_missing=True)

# Docker image with DeQA-Score dependencies
# Strategy: Use DeQA-Score's pinned versions but add bitsandbytes 0.43 (last compatible)
deqa_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")  # Install git for cloning DeQA-Score
    .pip_install(
        "numpy<2.0",  # Pin to 1.x for compatibility
        "torch==2.0.1",
        "torchvision==0.15.2",
        "transformers==4.36.1",
        "tokenizers==0.15.0",
        "sentencepiece==0.1.99",
        "accelerate==0.21.0",
        "peft==0.4.0",
        "bitsandbytes==0.43.3",  # Upgraded from 0.41.0 for better NF4 (still torch 2.0 compat)
        "pydantic<2,>=1",
        "scipy",
        "Pillow",
        "tqdm",
        "einops==0.6.1",
        "timm==0.6.13",
        "icecream",
    )
    .run_commands(
        "git clone https://github.com/zhiyuanyou/DeQA-Score.git /opt/DeQA-Score",
        "cd /opt/DeQA-Score && pip install -e .",
    )
)

# Stage 1 dataset configurations
STAGE1_DATASETS = {
    "diqa-5000": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/diqa-5000_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/diqa-5000",
        "images": 5000,
        "priority": "CRITICAL",
    },
    "smartdoc-qa": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/smartdoc-qa_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images",
        "images": 4260,
        "priority": "HIGH",
    },
    "ocr-quality": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/ocr-quality_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/ocr_quality/pics",
        "images": 1000,
        "priority": "HIGH",
    },
    "dibco": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/dibco_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/dibco/DIBCO",
        "images": 148,
        "priority": "HIGH",
    },
    "funsd": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/funsd_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/funsd",
        "images": 149,
        "priority": "MEDIUM",
    },
    "sroie": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/sroie_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/sroie",
        "images": 2043,
        "priority": "MEDIUM",
    },
    "tobacco-800": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/tobacco-800_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/degraded/tobacco800",
        "images": 1290,
        "priority": "MEDIUM",
    },
}

LEVEL_NAMES = ["excellent", "good", "fair", "poor", "bad"]
LEVEL_SCORES = [5.0, 4.0, 3.0, 2.0, 1.0]


def get_quantization_config(quantize_mode: str | None):
    """Get BitsAndBytesConfig for specified quantization mode.

    Args:
        quantize_mode: One of 'fp16', '8bit', '4bit', or None

    Returns:
        BitsAndBytesConfig or None for FP16 mode

    Raises:
        ValueError: If invalid quantization mode specified
    """
    if not quantize_mode or quantize_mode == "fp16":
        return None

    import torch
    from transformers import BitsAndBytesConfig

    if quantize_mode == "4bit":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",  # Normal Float 4-bit (best quality)
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,  # Nested quantization for better compression
        )
    if quantize_mode == "8bit":
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,  # Outlier threshold for mixed precision
        )
    raise ValueError(
        f"Invalid quantize mode: {quantize_mode}. Use 'fp16', '8bit', or '4bit'"
    )


@app.function(
    image=deqa_image,
    gpu="A100",  # Use A100 for fastest inference
    timeout=3600 * 8,  # 8 hour timeout for full run
    volumes={"/results": results_volume},
)
def run_deqa_inference_batch(
    entries: list[dict],  # List of {"image": path, "dataset": name, "root_dir": root}
    image_data: dict[str, bytes],  # "dataset|rel_path" -> image bytes
    output_name: str = "batch",
    quantize_mode: str = "fp16",  # Quantization mode: 'fp16', '8bit', or '4bit'
) -> dict:
    """Run DeQA-Doc inference on a batch of images.

    Args:
        entries: List of entries with image path, dataset name, and root_dir
        image_data: Dict mapping "dataset|rel_path" to image bytes
        output_name: Name for output file
        quantize_mode: Quantization mode ('fp16', '8bit', '4bit'). Default: fp16

    Returns:
        Dict with results summary
    """
    import io
    import sys

    sys.path.insert(0, "/opt/DeQA-Score")

    import torch
    from PIL import Image
    from src.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
    from src.conversation import conv_templates
    from src.mm_utils import get_model_name_from_path, tokenizer_image_token
    from src.model.builder import load_pretrained_model
    from tqdm import tqdm

    print(f"Processing {len(entries)} images...")
    print(f"Image data keys: {len(image_data)}")

    # Load model (using base DeQA-Score since DeQA-Doc-Mix is on ModelScope)
    # DeQA-Doc-Mix is on ModelScope (zhalala/DeQA-Doc-Mix), not HuggingFace
    # Using zhiyuanyou/DeQA-Score-Mix3 as fallback (publicly accessible)
    model_path = "zhiyuanyou/DeQA-Score-Mix3"
    model_name = get_model_name_from_path(model_path)

    print(f"Loading model: {model_path} (quantization: {quantize_mode})")
    start_load = time.time()

    # Get quantization config
    quant_config = get_quantization_config(quantize_mode)

    if quant_config:
        # Load with quantization - modify DeQA-Score's loader to accept quant_config
        from transformers import AutoModelForCausalLM

        print(f"Loading with quantization config: {quantize_mode}")

        # Use DeQA-Score's load_pretrained_model but monkey-patch for quantization
        # Load tokenizer and processor normally
        tokenizer, _, image_processor, _ = load_pretrained_model(
            model_path, None, model_name, device="cuda:0"
        )

        # Load model separately with quantization
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )
    else:
        # Original FP16 loading via DeQA-Score's load_pretrained_model
        print("Loading in FP16 (full precision)")
        tokenizer, model, image_processor, _ = load_pretrained_model(
            model_path, None, model_name, device="cuda:0"
        )

    print(f"Model loaded in {time.time() - start_load:.1f}s")
    print(f"Model dtype: {next(model.parameters()).dtype}")
    print(f"Model device: {next(model.parameters()).device}")

    # Setup prompt
    conv = conv_templates["mplug_owl2"].copy()
    inp = "How would you rate the quality of this image?\n" + DEFAULT_IMAGE_TOKEN
    conv.append_message(conv.roles[0], inp)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt() + " The quality of the image is"

    # Get token IDs for quality levels
    ids_ = [id_[1] for id_ in tokenizer(LEVEL_NAMES)["input_ids"]]
    print(f"Token IDs for quality levels: {ids_}")

    input_ids = (
        tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
        .unsqueeze(0)
        .to("cuda:0")
    )

    def expand2square(pil_img, background_color):
        width, height = pil_img.size
        if width == height:
            return pil_img
        if width > height:
            result = Image.new(pil_img.mode, (width, width), background_color)
            result.paste(pil_img, (0, (width - height) // 2))
            return result
        result = Image.new(pil_img.mode, (height, height), background_color)
        result.paste(pil_img, ((height - width) // 2, 0))
        return result

    results = []
    errors = []
    batch_size = 8  # A100 can handle larger batches

    image_tensors = []
    batch_entries = []

    start_inference = time.time()

    for i, entry in enumerate(tqdm(entries, desc="Processing")):
        dataset = entry["dataset"]
        rel_path = entry["image"]
        key = f"{dataset}|{rel_path}"

        # Load image from bytes
        if key not in image_data:
            errors.append(
                {
                    "image": rel_path,
                    "dataset": dataset,
                    "error": f"Image not found in data: {key}",
                }
            )
            continue

        try:
            image = Image.open(io.BytesIO(image_data[key])).convert("RGB")
            image = expand2square(
                image, tuple(int(x * 255) for x in image_processor.image_mean)
            )
            image_tensor = (
                image_processor.preprocess(image, return_tensors="pt")["pixel_values"]
                .half()
                .to("cuda:0")
            )

            image_tensors.append(image_tensor)
            batch_entries.append(entry)

        except Exception as e:
            errors.append(
                {
                    "image": rel_path,
                    "dataset": dataset,
                    "error": str(e),
                }
            )
            continue

        # Process batch
        if len(image_tensors) >= batch_size or i == len(entries) - 1:
            if image_tensors:
                with torch.inference_mode():
                    output_logits = model(
                        input_ids=input_ids.repeat(len(image_tensors), 1),
                        images=torch.cat(image_tensors, 0),
                    )["logits"][:, -1]
                    output_probs = torch.softmax(output_logits, dim=1)

                for j, batch_entry in enumerate(batch_entries):
                    logits = {
                        tok: output_logits[j, id_].item()
                        for tok, id_ in zip(LEVEL_NAMES, ids_)
                    }
                    probs = {
                        tok: output_probs[j, id_].item()
                        for tok, id_ in zip(LEVEL_NAMES, ids_)
                    }

                    # Calculate weighted score
                    prob_values = [probs[name] for name in LEVEL_NAMES]
                    score = sum(p * s for p, s in zip(prob_values, LEVEL_SCORES))

                    results.append(
                        {
                            "image": batch_entry["image"],
                            "dataset": batch_entry["dataset"],
                            "logits": logits,
                            "probs": probs,
                            "predicted_score": score,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                image_tensors = []
                batch_entries = []

    inference_time = time.time() - start_inference
    print(f"Inference completed in {inference_time:.1f}s")
    print(f"Processed: {len(results)}, Errors: {len(errors)}")

    # Save results to volume
    output_path = f"/results/{output_name}_deqa_labels.jsonl"
    with open(output_path, "w") as f:
        f.writelines(json.dumps(result) + "\n" for result in results)

    # Save errors if any
    if errors:
        error_path = f"/results/{output_name}_errors.jsonl"
        with open(error_path, "w") as f:
            f.writelines(json.dumps(error) + "\n" for error in errors)
        print(f"Errors saved to {error_path}")

    print(f"Results saved to {output_path}")

    # Commit volume changes
    results_volume.commit()

    return {
        "output_name": output_name,
        "total_entries": len(entries),
        "processed": len(results),
        "errors": len(errors),
        "inference_time_seconds": inference_time,
        "avg_time_per_image": inference_time / max(len(results), 1),
    }


@app.local_entrypoint()
def main(
    dataset: str = None,
    test: bool = False,
    validation: bool = False,  # Use 400-sample validation set
    dry_run: bool = False,
    quantize: str = "fp16",  # Quantization mode: 'fp16', '8bit', or '4bit'
):
    """Run Stage 1 inference on Modal.

    Args:
        dataset: Specific dataset to process (default: all)
        test: Run test with 100 samples only
        validation: Run 400-sample stratified validation
        dry_run: Just print what would be done
        quantize: Quantization mode ('fp16', '8bit', '4bit'). Default: fp16
    """
    # ===== SAFETY WARNING FOR NON-DETACHED RUNS =====
    import os

    # Check if running in detached mode (Modal sets this env var)
    is_detached = os.environ.get("MODAL_IS_REMOTE", "0") == "1"

    if not test and not validation and not dry_run and not is_detached:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: RUNNING PRODUCTION JOB WITHOUT --detach FLAG")
        print("=" * 70)
        print("Full inference takes 30-45 minutes. Without --detach:")
        print("  • Terminal disconnect = lost progress")
        print("  • Can't close laptop/terminal")
        print("  • SSH timeouts kill the job")
        print()
        print("RECOMMENDED: Cancel (Ctrl+C) and restart with:")
        print(
            f"  modal run --detach modal/stage1_deqa_inference.py --all --quantize {quantize}"
        )
        print("=" * 70)
        print()

        # Give user 10 seconds to cancel
        for i in range(10, 0, -1):
            print(f"Continuing in {i} seconds... (Ctrl+C to cancel)", end="\r")
            time.sleep(1)
        print("\nProceeding with attached mode (not recommended)...")
    # ===== END SAFETY WARNING =====

    print("=" * 60)
    print("Stage 1 DeQA-Doc Inference (Modal)")
    print(f"Quantization Mode: {quantize.upper()}")
    print("=" * 60)

    if validation:
        # Validation mode - use 400 sample stratified manifest
        validation_manifest_path = Path(
            "/mnt/e/image_detection/06_staging/stage1_manifests/validation_350_manifest.json"
        )

        if not validation_manifest_path.exists():
            print(f"ERROR: Validation manifest not found: {validation_manifest_path}")
            print("Run: uv run python scripts/create_stratified_validation.py")
            return

        with open(validation_manifest_path) as f:
            entries = json.load(f)

        print(f"Validation mode: {len(entries)} samples (stratified)")
        print()

        if dry_run:
            print("Dry run - would process:")
            for entry in entries[:5]:
                print(f"  {entry['dataset']}: {entry['image']}")
            print(f"  ... and {len(entries) - 5} more")
            return

        # Load images
        print("Loading validation images...")
        image_data = {}
        missing = []

        for entry in entries:
            root_dir = Path(entry["root_dir"])
            image_path = root_dir / entry["image"]
            key = f"{entry['dataset']}|{entry['image']}"

            if image_path.exists():
                image_data[key] = image_path.read_bytes()
            else:
                missing.append(str(image_path))

        print(f"Loaded {len(image_data)} images")
        if missing:
            print(f"Missing {len(missing)} images:")
            for m in missing[:5]:
                print(f"  {m}")

        # Run inference
        output_name = f"validation_{quantize}"
        print(f"\nStarting Modal inference (output: {output_name})...")
        result = run_deqa_inference_batch.remote(
            entries=entries,
            image_data=image_data,
            output_name=output_name,
            quantize_mode=quantize,
        )

        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print(f"Total entries: {result['total_entries']}")
        print(f"Processed: {result['processed']}")
        print(f"Errors: {result['errors']}")
        print(f"Inference time: {result['inference_time_seconds']:.1f}s")
        print(f"Avg time/image: {result['avg_time_per_image']:.3f}s")
        print(
            f"\nResults saved to Modal volume: stage1-deqa-results/{result['output_name']}_deqa_labels.jsonl"
        )

        if result["errors"] == 0 and result["processed"] == result["total_entries"]:
            print(
                f"\n✅ VALIDATION PASSED ({quantize.upper()}) - Ready for comparison!"
            )
            print(
                f"Download: modal volume get stage1-deqa-results {output_name}_deqa_labels.jsonl ./results/"
            )
        else:
            print("\n⚠️ VALIDATION HAD ISSUES - Check errors before proceeding")

        return

    if test:
        # Test mode - use 100 sample manifest
        sample_manifest_path = Path(
            "/mnt/e/image_detection/06_staging/stage1_manifests/sample_100_manifest.json"
        )

        if not sample_manifest_path.exists():
            print(f"ERROR: Sample manifest not found: {sample_manifest_path}")
            print("Run: uv run python scripts/create_sample_manifest.py")
            return

        with open(sample_manifest_path) as f:
            entries = json.load(f)

        print(f"Test mode: {len(entries)} samples")
        print()

        if dry_run:
            print("Dry run - would process:")
            for entry in entries[:5]:
                print(f"  {entry['dataset']}: {entry['image']}")
            print(f"  ... and {len(entries) - 5} more")
            return

        # Load images
        print("Loading images...")
        image_data = {}
        missing = []

        for entry in entries:
            root_dir = Path(entry["root_dir"])
            image_path = root_dir / entry["image"]
            key = f"{entry['dataset']}|{entry['image']}"

            if image_path.exists():
                image_data[key] = image_path.read_bytes()
            else:
                missing.append(str(image_path))

        print(f"Loaded {len(image_data)} images")
        if missing:
            print(f"Missing {len(missing)} images:")
            for m in missing[:5]:
                print(f"  {m}")

        # Run inference
        print("\nStarting Modal inference...")
        result = run_deqa_inference_batch.remote(
            entries=entries,
            image_data=image_data,
            output_name="sample_100_test",
            quantize_mode=quantize,  # Pass quantization mode
        )

        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Total entries: {result['total_entries']}")
        print(f"Processed: {result['processed']}")
        print(f"Errors: {result['errors']}")
        print(f"Inference time: {result['inference_time_seconds']:.1f}s")
        print(f"Avg time/image: {result['avg_time_per_image']:.3f}s")
        print(
            f"\nResults saved to Modal volume: stage1-deqa-results/{result['output_name']}_deqa_labels.jsonl"
        )

        if result["errors"] == 0 and result["processed"] == result["total_entries"]:
            print("\n✅ TEST PASSED - Ready for full run!")
            print("Run: modal run modal/stage1_deqa_inference.py")
        else:
            print("\n⚠️ TEST HAD ISSUES - Check errors before full run")

        return

    # Full run mode
    if dataset:
        datasets_to_process = {dataset: STAGE1_DATASETS[dataset]}
    else:
        datasets_to_process = STAGE1_DATASETS

    total_images = sum(d["images"] for d in datasets_to_process.values())
    print(f"Datasets: {len(datasets_to_process)}")
    print(f"Total images: {total_images}")
    print(f"Estimated time: ~{total_images * 0.15 / 60:.1f} minutes (A100)")
    print()

    if dry_run:
        print("Dry run - would process:")
        for name, config in datasets_to_process.items():
            print(f"  {name}: {config['images']} images ({config['priority']})")
        return

    all_results = []

    for name, config in datasets_to_process.items():
        print(f"\n{'=' * 40}")
        print(f"Processing {name} ({config['images']} images)...")
        print(f"{'=' * 40}")

        # Load manifest
        manifest_path = Path(config["manifest"])
        if not manifest_path.exists():
            print(f"  ERROR: Manifest not found: {manifest_path}")
            continue

        with open(manifest_path) as f:
            manifest_data = json.load(f)

        # Create entries with dataset info
        entries = [
            {"image": item["image"], "dataset": name, "root_dir": config["root_dir"]}
            for item in manifest_data
        ]

        # Load images into memory
        root_dir = Path(config["root_dir"])
        image_data = {}
        missing = 0

        print(f"  Loading images from {root_dir}...")
        for entry in entries:
            image_path = root_dir / entry["image"]
            key = f"{name}|{entry['image']}"

            if image_path.exists():
                image_data[key] = image_path.read_bytes()
            else:
                missing += 1

        print(f"  Loaded {len(image_data)} images ({missing} missing)")

        if not image_data:
            print(f"  ERROR: No images loaded for {name}")
            continue

        # Run inference on Modal
        result = run_deqa_inference_batch.remote(
            entries=entries,
            image_data=image_data,
            output_name=name,
            quantize_mode=quantize,  # Pass quantization mode
        )

        all_results.append(result)
        print(f"  Completed: {result['processed']}/{result['total_entries']} processed")
        print(f"  Errors: {result['errors']}")
        print(f"  Time: {result['inference_time_seconds']:.1f}s")

    # Summary
    print("\n" + "=" * 60)
    print("STAGE 1 INFERENCE COMPLETE")
    print("=" * 60)

    total_processed = sum(r["processed"] for r in all_results)
    total_errors = sum(r["errors"] for r in all_results)
    total_time = sum(r["inference_time_seconds"] for r in all_results)

    print(f"Total processed: {total_processed}")
    print(f"Total errors: {total_errors}")
    print(f"Total time: {total_time / 60:.1f} minutes")
    print("\nResults saved to Modal volume: stage1-deqa-results/")

    # List output files
    for result in all_results:
        print(f"  - {result['output_name']}_deqa_labels.jsonl")


if __name__ == "__main__":
    main()
