"""Stage 1 DeQA Inference using Tarballs from Modal NetworkFileSystem.

Processes images from pre-created tarballs stored on Modal NFS (SSD) for
efficient batch inference without memory issues.

Usage:
    # Run all tarballs
    modal run --detach modal/stage1_deqa_tarball_inference.py

    # Run specific tarball
    modal run modal/stage1_deqa_tarball_inference.py --tarball diqa-5000_part1.tar.gz

    # Test with first tarball only
    modal run modal/stage1_deqa_tarball_inference.py --test
"""

import json
import tarfile
import time
from datetime import datetime
from pathlib import Path

import modal

# Modal app definition
app = modal.App("stage1-deqa-tarball-inference")

# Create volumes
tarball_nfs = modal.NetworkFileSystem.from_name("stage1-tarballs")
results_volume = modal.Volume.from_name("stage1-deqa-results", create_if_missing=True)

# DeQA image (same as before, with NumPy 1.x fix)
deqa_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "numpy<2.0",  # Pin to 1.x for compatibility
        "torch==2.0.1",
        "torchvision==0.15.2",
        "transformers==4.36.1",
        "tokenizers==0.15.0",
        "sentencepiece==0.1.99",
        "accelerate==0.21.0",
        "peft==0.4.0",
        "bitsandbytes==0.41.0",
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

# Quality level names (from DeQA-Score)
LEVEL_NAMES = ["excellent", "good", "fair", "poor", "bad"]


@app.function(
    image=deqa_image,
    gpu="A100",
    timeout=3600 * 3,  # 3 hours max per tarball
    network_file_systems={"/tarballs": tarball_nfs},
    volumes={"/results": results_volume},
)
def process_tarball(tarball_filename: str, output_prefix: str = "stage1") -> dict:
    """Process all images in a single tarball.

    Args:
        tarball_filename: Name of tarball in /tarballs/
        output_prefix: Prefix for output filename

    Returns:
        Dict with processing statistics
    """
    import sys
    import time

    import torch
    from PIL import Image
    from tqdm import tqdm

    sys.path.insert(0, "/opt/DeQA-Score/src")
    from constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
    from conversation import conv_templates
    from mm_utils import get_model_name_from_path, tokenizer_image_token
    from model.builder import load_pretrained_model

    print(f"Processing tarball: {tarball_filename}")
    start_time = time.time()

    # Extract tarball to /tmp (ephemeral SSD)
    # Note: tarballs are in /tarballs/tarballs/ subdirectory
    tarball_path = Path("/tarballs/tarballs") / tarball_filename
    extract_dir = Path("/tmp/extracted")
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {tarball_filename} to {extract_dir}...")
    extract_start = time.time()
    with tarfile.open(tarball_path, "r:gz") as tar:
        tar.extractall(extract_dir)
    extract_time = time.time() - extract_start
    print(f"Extraction completed in {extract_time:.1f}s")

    # Find all images in extracted directory
    image_files = []
    for img_path in extract_dir.rglob("*"):
        if img_path.is_file() and img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            # Store relative path from dataset root
            relative_parts = img_path.relative_to(extract_dir).parts
            dataset_name = relative_parts[0]
            relative_path = str(Path(*relative_parts[1:]))
            image_files.append({
                "full_path": img_path,
                "relative_path": relative_path,
                "dataset": dataset_name,
            })

    print(f"Found {len(image_files)} images in tarball")

    # Load model
    model_path = "zhiyuanyou/DeQA-Score-Mix3"
    model_name = get_model_name_from_path(model_path)

    print(f"Loading model: {model_path}")
    model_load_start = time.time()
    tokenizer, model, image_processor, context_len = load_pretrained_model(
        model_path, None, model_name, device="cuda:0"
    )
    model_load_time = time.time() - model_load_start
    print(f"Model loaded in {model_load_time:.1f}s")
    print(f"image_processor type: {type(image_processor)}")
    print(f"image_processor is None: {image_processor is None}")
    if image_processor is not None:
        print(f"image_processor.image_mean: {image_processor.image_mean}")

    # Setup prompt
    conv = conv_templates["mplug_owl2"].copy()
    inp = "How would you rate the quality of this image?\n" + DEFAULT_IMAGE_TOKEN
    conv.append_message(conv.roles[0], inp)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt() + " The quality of the image is"

    # Get token IDs for quality levels
    ids_ = [id_[1] for id_ in tokenizer(LEVEL_NAMES)["input_ids"]]
    input_ids = (
        tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
        .unsqueeze(0)
        .to("cuda:0")
    )

    # Helper function to pad image to square (required by mPLUG-Owl2)
    def expand2square(pil_img, background_color):
        width, height = pil_img.size
        if width == height:
            return pil_img
        elif width > height:
            result = Image.new(pil_img.mode, (width, width), background_color)
            result.paste(pil_img, (0, (width - height) // 2))
            return result
        else:
            result = Image.new(pil_img.mode, (height, height), background_color)
            result.paste(pil_img, ((height - width) // 2, 0))
            return result

    # Process images
    results = []
    errors = 0
    inference_start = time.time()

    for idx, img_info in enumerate(tqdm(image_files, desc="Processing")):
        try:
            # Load and process image (must expand to square first)
            image = Image.open(img_info["full_path"]).convert("RGB")
            image = expand2square(
                image, tuple(int(x * 255) for x in image_processor.image_mean)
            )
            preprocessed = image_processor.preprocess(image, return_tensors="pt")
            if preprocessed is None or "pixel_values" not in preprocessed:
                print(f"preprocess returned None or missing pixel_values for {img_info['relative_path']}")
                errors += 1
                continue
            pixel_values = preprocessed["pixel_values"]
            if pixel_values is None:
                print(f"pixel_values is None for {img_info['relative_path']}")
                errors += 1
                continue
            image_tensor = pixel_values.half().to("cuda:0")

            # Run inference - get logits directly (no generate needed)
            with torch.inference_mode():
                output = model(
                    input_ids=input_ids,
                    images=image_tensor,
                )
                # Access logits as dict (not attribute) for compatibility
                output_logits = output["logits"][0, -1]  # Last token logits

            # Extract logits for quality level tokens
            logits = output_logits[ids_]

            # Calculate probabilities and weighted score
            probs = torch.nn.functional.softmax(logits, dim=0)
            weights = torch.tensor([5.0, 4.0, 3.0, 2.0, 1.0], device=probs.device)
            predicted_score = (probs * weights).sum().item()

            # Store result
            results.append({
                "image": img_info["relative_path"],
                "dataset": img_info["dataset"],
                "logits": {
                    level: logits[i].item()
                    for i, level in enumerate(LEVEL_NAMES)
                },
                "probs": {
                    level: probs[i].item()
                    for i, level in enumerate(LEVEL_NAMES)
                },
                "predicted_score": predicted_score,
                "timestamp": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            print(f"Error processing {img_info['relative_path']}: {e}")
            errors += 1

    inference_time = time.time() - inference_start

    # Save results
    output_filename = f"{output_prefix}_{tarball_filename.replace('.tar.gz', '')}_labels.jsonl"
    output_path = Path("/results") / output_filename

    with open(output_path, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    results_volume.commit()  # Persist results

    # Statistics
    total_time = time.time() - start_time
    stats = {
        "tarball": tarball_filename,
        "total_images": len(image_files),
        "processed": len(results),
        "errors": errors,
        "extract_time_s": extract_time,
        "model_load_time_s": model_load_time,
        "inference_time_s": inference_time,
        "total_time_s": total_time,
        "avg_time_per_image_s": inference_time / len(results) if results else 0,
        "output_file": output_filename,
    }

    print("\n" + "=" * 80)
    print(f"Tarball: {tarball_filename}")
    print(f"Processed: {len(results)}/{len(image_files)} images")
    print(f"Errors: {errors}")
    print(f"Times: extract={extract_time:.1f}s, model_load={model_load_time:.1f}s, "
          f"inference={inference_time:.1f}s, total={total_time:.1f}s")
    print(f"Avg: {stats['avg_time_per_image_s']:.3f}s/image")
    print(f"Results: {output_filename}")
    print("=" * 80)

    return stats


@app.local_entrypoint()
def main(
    tarball: str = None,
    test: bool = False,
):
    """Run DeQA inference on tarballs.

    Args:
        tarball: Specific tarball to process (default: all)
        test: If True, only process first tarball
    """
    print("=" * 80)
    print("Stage 1 DeQA Inference - Tarball Mode")
    print("=" * 80)

    # Load manifest to get tarball list
    # Note: manifest is in /tarballs/tarballs/ subdirectory
    manifest_path = Path("/tarballs/tarballs/manifest.json")
    # First, copy manifest locally to read it
    import subprocess

    subprocess.run(
        ["modal", "nfs", "get", "stage1-tarballs", "tarballs/manifest.json", "/tmp/manifest.json", "--force"],
        check=True,
    )
    with open("/tmp/manifest.json") as f:
        manifest = json.load(f)

    # Get tarballs to process
    if tarball:
        tarballs = [tarball]
    elif test:
        tarballs = [manifest[0]["filename"]]
        print(f"TEST MODE: Processing only {tarballs[0]}")
    else:
        tarballs = [entry["filename"] for entry in manifest]

    print(f"Processing {len(tarballs)} tarball(s)...")

    # Process tarballs (sequentially for now, could parallelize later)
    all_stats = []
    for tb in tarballs:
        print(f"\n>>> Starting {tb}...")
        stats = process_tarball.remote(tb)
        all_stats.append(stats)

    # Summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    total_images = sum(s["processed"] for s in all_stats)
    total_errors = sum(s["errors"] for s in all_stats)
    total_time = sum(s["total_time_s"] for s in all_stats)
    avg_time = sum(s["inference_time_s"] for s in all_stats) / total_images if total_images else 0

    print(f"Tarballs processed: {len(all_stats)}")
    print(f"Total images: {total_images:,}")
    print(f"Total errors: {total_errors}")
    print(f"Total time: {total_time/60:.1f} minutes")
    print(f"Avg time/image: {avg_time:.3f}s")
    print(f"\nResults saved to Modal volume: stage1-deqa-results")
    print("=" * 80)
