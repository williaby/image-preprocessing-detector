# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Phase 7: Pseudo-Label Generation with Qwen3-VL-8B on Modal.

Generates continuous quality labels for document images using Qwen3-VL-8B.
These pseudo-labels enable training with continuous severity scores [0,1]
instead of binary labels.

Usage:
    # Generate labels for local images
    modal run modal/generate_pseudo_labels.py --input-dir ./data/images --output-dir ./data/labels

    # Generate labels from GCS bucket
    modal run modal/generate_pseudo_labels.py --gcs-bucket my-bucket --gcs-prefix images/ --output-dir ./data/labels

    # Process with multiple parallel workers
    modal run modal/generate_pseudo_labels.py --input-dir ./data/images --output-dir ./data/labels --num-workers 4

    # Resume from checkpoint
    modal run modal/generate_pseudo_labels.py --input-dir ./data/images --output-dir ./data/labels --resume

Reference:
    - Phase 7 Strategy: docs/development/phase-7-continuous-labels-strategy.md
    - Model: Qwen3-VL-8B-Instruct (OCRBench: 896-905, DocVQA: 97%)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import modal
from image_preprocessing_detector.utils.datetime_compat import utc_now
from image_preprocessing_detector.utils.path_security import validate_safe_path

# ============================================================================
# Modal App Configuration
# ============================================================================

app = modal.App("phase7-pseudo-labels")

# Docker image with Qwen3-VL dependencies
qwen_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.4.0",
        "torchvision>=0.19.0",
        "transformers>=4.45.0",
        "accelerate>=0.34.0",
        "qwen-vl-utils>=0.0.8",
        "pillow>=10.0.0",
        "google-cloud-storage>=2.10.0",
        "tqdm>=4.66.0",
    )
    # Install flash-attention for faster inference
    .run_commands(
        "pip install flash-attn --no-build-isolation || echo 'Flash attention install failed, continuing without it'"
    )
)

# GCS credentials secret
gcs_secret = modal.Secret.from_name("gcs-credentials")

# Persistent volume for checkpoints and outputs
output_volume = modal.Volume.from_name("pseudo-labels-output", create_if_missing=True)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ContinuousQualityLabel:
    """Continuous quality labels for Phase 7 training.

    All severity scores are in range [0, 1]:
    - 0.0 = no degradation, perfect quality
    - 1.0 = maximum degradation, unreadable
    """

    # Per-issue severity scores [0, 1]
    blur_severity: float = 0.0
    noise_severity: float = 0.0
    skew_severity: float = 0.0
    contrast_severity: float = 0.0
    compression_severity: float = 0.0

    # Document-specific degradations
    ink_degradation: float = 0.0
    paper_degradation: float = 0.0

    # Aggregated scores
    overall_quality: float = 1.0  # 1.0 = best, 0.0 = worst

    # Label provenance
    label_source: str = "mllm_pseudo"
    model_name: str = "qwen3-vl-8b-instruct"
    label_confidence: float = 0.85
    generation_timestamp: str = field(default_factory=lambda: utc_now().isoformat())

    # Raw model response for debugging
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "blur_severity": self.blur_severity,
            "noise_severity": self.noise_severity,
            "skew_severity": self.skew_severity,
            "contrast_severity": self.contrast_severity,
            "compression_severity": self.compression_severity,
            "ink_degradation": self.ink_degradation,
            "paper_degradation": self.paper_degradation,
            "overall_quality": self.overall_quality,
            "label_source": self.label_source,
            "model_name": self.model_name,
            "label_confidence": self.label_confidence,
            "generation_timestamp": self.generation_timestamp,
            # Include quality_scores for backward compatibility with weak supervision format
            "quality_scores": {
                "blur": self.blur_severity,
                "noise": self.noise_severity,
                "skew": self.skew_severity,
                "contrast": self.contrast_severity,
                "compression": self.compression_severity,
                "overall": self.overall_quality,
            },
            # Include binary labels for backward compatibility
            "labels": {
                "blur": {
                    "value": int(self.blur_severity >= 0.3),
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.blur_severity,
                },
                "noise": {
                    "value": int(self.noise_severity >= 0.3),
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.noise_severity,
                },
                "skew": {
                    "value": int(self.skew_severity >= 0.3),
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.skew_severity,
                },
                "illumination": {
                    "value": int(self.contrast_severity >= 0.3),
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.contrast_severity,
                },
                "artifacts": {
                    "value": int(self.compression_severity >= 0.3),
                    "confidence": self.label_confidence,
                    "source": self.label_source,
                    "severity": self.compression_severity,
                },
            },
        }

    @classmethod
    def from_model_response(
        cls,
        response: dict[str, Any],
        model_name: str = "qwen3-vl-8b-instruct",
        raw_response: str = "",
    ) -> ContinuousQualityLabel:
        """Create from model JSON response."""

        def _clamp(value: Any, default: float = 0.0) -> float:
            """Clamp value to [0, 1] range."""
            try:
                v = float(value)
                return max(0.0, min(1.0, v))
            except (TypeError, ValueError):
                return default

        return cls(
            blur_severity=_clamp(response.get("blur_severity", 0)),
            noise_severity=_clamp(response.get("noise_severity", 0)),
            skew_severity=_clamp(response.get("skew_severity", 0)),
            contrast_severity=_clamp(response.get("contrast_severity", 0)),
            compression_severity=_clamp(response.get("compression_severity", 0)),
            ink_degradation=_clamp(response.get("ink_degradation", 0)),
            paper_degradation=_clamp(response.get("paper_degradation", 0)),
            overall_quality=_clamp(response.get("overall_quality", 1.0), default=1.0),
            model_name=model_name,
            raw_response=raw_response,
        )


# ============================================================================
# Prompt Templates
# ============================================================================

QUALITY_ASSESSMENT_PROMPT = """You are a document image quality assessment expert. Analyze this document image and rate its quality degradations.

Rate each degradation type on a scale from 0.0 to 1.0:
- 0.0 = No degradation present (perfect quality)
- 0.5 = Moderate degradation (noticeable but readable)
- 1.0 = Severe degradation (significantly impacts readability)

Assess the following quality dimensions:

1. **blur_severity**: Blurriness of text and content (motion blur, defocus, camera shake)
2. **noise_severity**: Visual noise, grain, or speckles in the image
3. **skew_severity**: Rotation or misalignment of the document
4. **contrast_severity**: Poor contrast, washed out, or overly dark regions
5. **compression_severity**: JPEG artifacts, blocking, or ringing
6. **ink_degradation**: Faded ink, bleeding, or ink spread (for scanned documents)
7. **paper_degradation**: Paper aging, stains, creases, or damage
8. **overall_quality**: Overall document quality (1.0 = excellent, 0.0 = unreadable)

IMPORTANT: Respond ONLY with a valid JSON object. No additional text or explanation.

Example response format:
```json
{
    "blur_severity": 0.15,
    "noise_severity": 0.25,
    "skew_severity": 0.05,
    "contrast_severity": 0.10,
    "compression_severity": 0.20,
    "ink_degradation": 0.00,
    "paper_degradation": 0.05,
    "overall_quality": 0.85
}
```"""


# ============================================================================
# Modal Class: Qwen3-VL Labeler
# ============================================================================


@app.cls(
    gpu=modal.gpu.A10G(),
    image=qwen_image,
    timeout=7200,  # 2 hours max per container
    container_idle_timeout=300,  # Keep warm for 5 minutes
    retries=modal.Retries(max_retries=2, initial_delay=5.0, backoff_coefficient=2.0),
)
class Qwen3VLLabeler:
    """Modal class for Qwen3-VL-8B inference.

    Loads the model once on container startup and processes images efficiently.
    """

    model_name: str = "Qwen/Qwen3-VL-8B-Instruct"

    @modal.enter()
    def load_model(self):
        """Load Qwen3-VL-8B model on container startup."""
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        print(f"Loading model: {self.model_name}")
        start_time = time.time()

        # Check GPU availability
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(
                f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
            )
        else:
            print("WARNING: No GPU available, inference will be slow")

        # Load model with optimizations
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            # Try flash attention, fall back to default if unavailable
            attn_implementation="flash_attention_2"
            if self._flash_attn_available()
            else "sdpa",
        )

        # Load processor
        self.processor = AutoProcessor.from_pretrained(self.model_name)

        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.1f}s")

    def _flash_attn_available(self) -> bool:
        """Check if flash attention is available."""
        try:
            import flash_attn  # noqa: F401

            return True
        except ImportError:
            return False

    @modal.method()
    def generate_label(self, image_bytes: bytes, image_id: str = "") -> dict[str, Any]:
        """Generate quality labels for a single image.

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, etc.)
            image_id: Optional identifier for logging

        Returns:
            Dictionary with continuous quality labels
        """
        import io

        from PIL import Image
        from qwen_vl_utils import process_vision_info

        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Prepare messages for Qwen3-VL
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": QUALITY_ASSESSMENT_PROMPT},
                    ],
                }
            ]

            # Process inputs
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            image_inputs, video_inputs = process_vision_info(messages)

            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda")

            # Generate response
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.1,  # Low temperature for consistent outputs
                do_sample=False,  # Greedy decoding for determinism
            )

            # Decode response
            generated_ids = [
                output_ids[len(input_ids) :]
                for input_ids, output_ids in zip(inputs.input_ids, output_ids)
            ]
            response_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

            # Parse JSON from response
            labels = self._parse_json_response(response_text)

            # Create structured label
            quality_label = ContinuousQualityLabel.from_model_response(
                labels,
                model_name=self.model_name,
                raw_response=response_text,
            )

            result = quality_label.to_dict()
            result["image_id"] = image_id
            result["status"] = "success"

            return result

        except Exception as e:
            print(f"Error processing image {image_id}: {e}")
            return {
                "image_id": image_id,
                "status": "error",
                "error": str(e),
                "label_source": "mllm_pseudo",
                "model_name": self.model_name,
            }

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Extract JSON from model response.

        Handles various response formats:
        - Pure JSON
        - JSON wrapped in ```json ... ```
        - JSON with surrounding text
        """
        # Try direct JSON parse
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from code blocks
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(code_block_pattern, response_text)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # Try finding JSON-like structure
        json_pattern = r"\{[^{}]*\}"
        matches = re.findall(json_pattern, response_text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Return default values if parsing fails
        print(f"WARNING: Could not parse JSON from response: {response_text[:200]}...")
        return {
            "blur_severity": 0.5,
            "noise_severity": 0.5,
            "skew_severity": 0.5,
            "contrast_severity": 0.5,
            "compression_severity": 0.5,
            "overall_quality": 0.5,
            "parse_error": True,
        }

    @modal.method()
    def generate_labels_batch(
        self, image_batch: list[tuple[bytes, str]]
    ) -> list[dict[str, Any]]:
        """Generate labels for a batch of images.

        Args:
            image_batch: List of (image_bytes, image_id) tuples

        Returns:
            List of label dictionaries
        """
        results = []
        for image_bytes, image_id in image_batch:
            result = self.generate_label(image_bytes, image_id)
            results.append(result)
        return results


# ============================================================================
# Batch Processing Functions
# ============================================================================


@app.function(
    image=qwen_image,
    secrets=[gcs_secret],
    volumes={"/output": output_volume},
    timeout=14400,  # 4 hours
)
def process_gcs_dataset(
    bucket_name: str,
    prefix: str = "",
    output_prefix: str = "labels/",
    batch_size: int = 10,
    max_images: int | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    """Process images from GCS bucket and save labels.

    Args:
        bucket_name: GCS bucket name
        prefix: Prefix path to images in bucket
        output_prefix: Prefix for output labels in bucket
        batch_size: Number of images per batch
        max_images: Maximum images to process (None = all)
        resume: Skip already processed images

    Returns:
        Processing statistics
    """
    import base64
    import os

    from google.cloud import storage
    from tqdm import tqdm

    # Setup GCS client
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(base64.b64decode(gcp_sa_key).decode())
            credentials_path = f.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # List images
    image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
    blobs = list(bucket.list_blobs(prefix=prefix))
    image_blobs = [b for b in blobs if Path(b.name).suffix.lower() in image_extensions]

    if max_images:
        image_blobs = image_blobs[:max_images]

    print(f"Found {len(image_blobs)} images in gs://{bucket_name}/{prefix}")

    # Check for already processed images if resuming
    processed_ids = set()
    if resume:
        label_blobs = list(bucket.list_blobs(prefix=output_prefix))
        for lb in label_blobs:
            if lb.name.endswith("_labels.json"):
                stem = Path(lb.name).stem.replace("_labels", "")
                processed_ids.add(stem)
        print(f"Found {len(processed_ids)} already processed images")

    # Filter out processed images
    pending_blobs = [b for b in image_blobs if Path(b.name).stem not in processed_ids]
    print(f"Processing {len(pending_blobs)} pending images")

    if not pending_blobs:
        return {"status": "complete", "processed": 0, "total": len(image_blobs)}

    # Initialize labeler
    labeler = Qwen3VLLabeler()

    # Process in batches
    stats = {
        "processed": 0,
        "success": 0,
        "errors": 0,
        "total": len(pending_blobs),
        "start_time": utc_now().isoformat(),
    }

    for i in tqdm(range(0, len(pending_blobs), batch_size), desc="Processing batches"):
        batch_blobs = pending_blobs[i : i + batch_size]

        # Download images
        batch_data = []
        for blob in batch_blobs:
            try:
                image_bytes = blob.download_as_bytes()
                image_id = Path(blob.name).stem
                batch_data.append((image_bytes, image_id))
            except Exception as e:
                print(f"Error downloading {blob.name}: {e}")
                stats["errors"] += 1

        # Generate labels
        if batch_data:
            results = labeler.generate_labels_batch.remote(batch_data)

            # Save results to GCS
            for result in results:
                image_id = result.get("image_id", "unknown")
                output_path = f"{output_prefix}{image_id}_labels.json"

                try:
                    output_blob = bucket.blob(output_path)
                    output_blob.upload_from_string(
                        json.dumps(result, indent=2),
                        content_type="application/json",
                    )
                    stats["success"] += 1
                except Exception as e:
                    print(f"Error saving {output_path}: {e}")
                    stats["errors"] += 1

                stats["processed"] += 1

        # Save checkpoint every 100 images
        if stats["processed"] % 100 == 0:
            checkpoint_path = f"{output_prefix}_checkpoint.json"
            checkpoint_blob = bucket.blob(checkpoint_path)
            checkpoint_blob.upload_from_string(
                json.dumps(stats, indent=2),
                content_type="application/json",
            )

    stats["end_time"] = utc_now().isoformat()
    stats["status"] = "complete"

    # Save final stats
    final_stats_path = f"{output_prefix}_final_stats.json"
    stats_blob = bucket.blob(final_stats_path)
    stats_blob.upload_from_string(
        json.dumps(stats, indent=2),
        content_type="application/json",
    )

    print("\nProcessing complete!")
    print(f"  Total: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Errors: {stats['errors']}")

    return stats


@app.function(
    image=qwen_image,
    volumes={"/output": output_volume},
    timeout=14400,  # 4 hours
)
def process_local_dataset(
    image_paths: list[str],
    output_dir: str = "/output/labels",
    batch_size: int = 10,
    resume: bool = True,
) -> dict[str, Any]:
    """Process local images and save labels.

    Args:
        image_paths: List of image file paths
        output_dir: Directory to save label JSON files
        batch_size: Number of images per batch
        resume: Skip already processed images

    Returns:
        Processing statistics
    """
    from tqdm import tqdm

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check for already processed images if resuming
    processed_ids = set()
    if resume:
        for label_file in output_path.glob("*_labels.json"):
            stem = label_file.stem.replace("_labels", "")
            processed_ids.add(stem)
        print(f"Found {len(processed_ids)} already processed images")

    # Filter out processed images
    pending_paths = [p for p in image_paths if Path(p).stem not in processed_ids]
    print(f"Processing {len(pending_paths)} pending images")

    if not pending_paths:
        return {"status": "complete", "processed": 0, "total": len(image_paths)}

    # Initialize labeler
    labeler = Qwen3VLLabeler()

    # Process in batches
    stats = {
        "processed": 0,
        "success": 0,
        "errors": 0,
        "total": len(pending_paths),
        "start_time": utc_now().isoformat(),
    }

    for i in tqdm(range(0, len(pending_paths), batch_size), desc="Processing batches"):
        batch_paths = pending_paths[i : i + batch_size]

        # Load images
        batch_data = []
        for image_path in batch_paths:
            try:
                # Validate path to prevent directory traversal
                validated_path = validate_safe_path(image_path, must_exist=True)
                with open(validated_path, "rb") as f:
                    image_bytes = f.read()
                image_id = Path(image_path).stem
                batch_data.append((image_bytes, image_id))
            except Exception as e:
                print(f"Error loading {image_path}: {e}")
                stats["errors"] += 1

        # Generate labels
        if batch_data:
            results = labeler.generate_labels_batch.remote(batch_data)

            # Save results
            for result in results:
                image_id = result.get("image_id", "unknown")
                label_path = output_path / f"{image_id}_labels.json"

                try:
                    # Validate path to prevent directory traversal
                    validated_path = validate_safe_path(label_path)
                    with open(validated_path, "w") as f:
                        json.dump(result, f, indent=2)
                    stats["success"] += 1
                except Exception as e:
                    print(f"Error saving {label_path}: {e}")
                    stats["errors"] += 1

                stats["processed"] += 1

    stats["end_time"] = utc_now().isoformat()
    stats["status"] = "complete"

    # Save final stats
    stats_path = output_path / "_final_stats.json"
    # Validate path to prevent directory traversal
    validated_stats_path = validate_safe_path(stats_path)
    with open(validated_stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    output_volume.commit()

    print("\nProcessing complete!")
    print(f"  Total: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Errors: {stats['errors']}")

    return stats


# ============================================================================
# Parallel Processing with Multiple Workers
# ============================================================================


@app.function(
    image=qwen_image,
    secrets=[gcs_secret],
    timeout=3600,
)
def process_image_chunk(
    chunk_data: list[tuple[str, str]],  # (bucket_name, blob_name) or (path, image_id)
    output_bucket: str | None = None,
    output_prefix: str = "labels/",
    source_type: str = "gcs",  # "gcs" or "local"
) -> list[dict[str, Any]]:
    """Process a chunk of images in parallel.

    This function is designed to be called by modal.Function.map() for
    parallel processing across multiple workers.
    """
    import base64
    import os

    if source_type == "gcs":
        from google.cloud import storage

        # Setup GCS
        gcp_sa_key = os.environ.get("GCP_SA_KEY")
        if gcp_sa_key:
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                f.write(base64.b64decode(gcp_sa_key).decode())
                credentials_path = f.name
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        client = storage.Client()

    labeler = Qwen3VLLabeler()
    results = []

    for item in chunk_data:
        if source_type == "gcs":
            bucket_name, blob_name = item
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            image_bytes = blob.download_as_bytes()
            image_id = Path(blob_name).stem
        else:
            image_path = item[0]
            image_id = item[1] if len(item) > 1 else Path(item[0]).stem
            # Validate path to prevent directory traversal
            validated_path = validate_safe_path(image_path, must_exist=True)
            with open(validated_path, "rb") as f:
                image_bytes = f.read()

        # Generate label
        result = labeler.generate_label.remote(image_bytes, image_id)
        results.append(result)

        # Save to GCS if specified
        if output_bucket and source_type == "gcs":
            output_path = f"{output_prefix}{image_id}_labels.json"
            output_blob = client.bucket(output_bucket).blob(output_path)
            output_blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type="application/json",
            )

    return results


@app.function(
    image=qwen_image,
    secrets=[gcs_secret],
    timeout=14400,
)
def process_dataset_parallel(
    bucket_name: str,
    prefix: str = "",
    output_prefix: str = "labels/",
    num_workers: int = 4,
    max_images: int | None = None,
    chunk_size: int = 50,
) -> dict[str, Any]:
    """Process dataset with parallel workers for maximum throughput.

    Args:
        bucket_name: GCS bucket name
        prefix: Prefix path to images in bucket
        output_prefix: Prefix for output labels
        num_workers: Number of parallel workers
        max_images: Maximum images to process
        chunk_size: Images per chunk per worker

    Returns:
        Processing statistics
    """
    import base64
    import os

    from google.cloud import storage

    # Setup GCS
    gcp_sa_key = os.environ.get("GCP_SA_KEY")
    if gcp_sa_key:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(base64.b64decode(gcp_sa_key).decode())
            credentials_path = f.name
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # List images
    image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
    blobs = list(bucket.list_blobs(prefix=prefix))
    image_blobs = [b for b in blobs if Path(b.name).suffix.lower() in image_extensions]

    if max_images:
        image_blobs = image_blobs[:max_images]

    print(f"Found {len(image_blobs)} images")
    print(f"Using {num_workers} parallel workers")

    # Create chunks for parallel processing
    blob_names = [(bucket_name, b.name) for b in image_blobs]
    chunks = [
        blob_names[i : i + chunk_size] for i in range(0, len(blob_names), chunk_size)
    ]

    print(f"Split into {len(chunks)} chunks of ~{chunk_size} images each")

    # Process chunks in parallel
    start_time = time.time()
    all_results = []

    for chunk_results in process_image_chunk.map(
        chunks,
        kwargs={
            "output_bucket": bucket_name,
            "output_prefix": output_prefix,
            "source_type": "gcs",
        },
    ):
        all_results.extend(chunk_results)

    elapsed_time = time.time() - start_time

    # Compile statistics
    stats = {
        "total": len(image_blobs),
        "processed": len(all_results),
        "success": sum(1 for r in all_results if r.get("status") == "success"),
        "errors": sum(1 for r in all_results if r.get("status") == "error"),
        "elapsed_seconds": elapsed_time,
        "images_per_second": len(all_results) / elapsed_time if elapsed_time > 0 else 0,
        "num_workers": num_workers,
        "chunk_size": chunk_size,
    }

    print("\nParallel processing complete!")
    print(f"  Total: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Time: {elapsed_time:.1f}s ({stats['images_per_second']:.1f} img/s)")

    return stats


# ============================================================================
# CLI Entry Points
# ============================================================================


@app.local_entrypoint()
def main(
    input_dir: str | None = None,
    gcs_bucket: str | None = None,
    gcs_prefix: str = "",
    output_dir: str = "./data/pseudo_labels",
    batch_size: int = 10,
    num_workers: int = 1,
    max_images: int | None = None,
    resume: bool = True,
    parallel: bool = False,
):
    """Generate pseudo-labels for document images using Qwen3-VL-8B.

    Examples:
        # Process local images
        modal run modal/generate_pseudo_labels.py --input-dir ./data/images

        # Process GCS bucket
        modal run modal/generate_pseudo_labels.py --gcs-bucket my-bucket --gcs-prefix images/

        # Parallel processing with 4 workers
        modal run modal/generate_pseudo_labels.py --gcs-bucket my-bucket --parallel --num-workers 4
    """
    print("=" * 60)
    print("Phase 7: Pseudo-Label Generation with Qwen3-VL-8B")
    print("=" * 60)

    if gcs_bucket:
        # GCS-based processing
        if parallel and num_workers > 1:
            print(f"\nUsing parallel processing with {num_workers} workers")
            stats = process_dataset_parallel.remote(
                bucket_name=gcs_bucket,
                prefix=gcs_prefix,
                output_prefix=output_dir.lstrip("/") + "/",
                num_workers=num_workers,
                max_images=max_images,
                chunk_size=batch_size * num_workers,
            )
        else:
            print("\nUsing sequential processing")
            stats = process_gcs_dataset.remote(
                bucket_name=gcs_bucket,
                prefix=gcs_prefix,
                output_prefix=output_dir.lstrip("/") + "/",
                batch_size=batch_size,
                max_images=max_images,
                resume=resume,
            )
    elif input_dir:
        # Local file processing
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
        image_paths = [
            str(p)
            for p in Path(input_dir).rglob("*")
            if p.suffix.lower() in image_extensions
        ]

        if max_images:
            image_paths = image_paths[:max_images]

        print(f"\nFound {len(image_paths)} images in {input_dir}")

        stats = process_local_dataset.remote(
            image_paths=image_paths,
            output_dir=output_dir,
            batch_size=batch_size,
            resume=resume,
        )
    else:
        print("ERROR: Must specify either --input-dir or --gcs-bucket")
        return

    print("\n" + "=" * 60)
    print("Processing Statistics:")
    print(json.dumps(stats, indent=2))
    print("=" * 60)


# ============================================================================
# Testing
# ============================================================================


@app.function(image=qwen_image, gpu=modal.gpu.A10G())
def test_single_image(image_url: str = "") -> dict[str, Any]:
    """Test the labeler with a single image URL or sample image.

    Usage:
        modal run modal/generate_pseudo_labels.py::test_single_image
    """
    import io
    import urllib.parse
    import urllib.request

    from PIL import Image

    # Use a sample document image if no URL provided
    if not image_url:
        # Create a simple test image
        print("Creating sample test image...")
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        # Add some noise to simulate a document
        import random

        pixels = img.load()
        for i in range(800):
            for j in range(600):
                if random.random() < 0.01:
                    pixels[i, j] = (0, 0, 0)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
    else:
        # Validate URL scheme to prevent file:// and other dangerous schemes
        parsed = urllib.parse.urlparse(image_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. Only HTTP/HTTPS URLs are allowed."
            )
        print(f"Downloading image from {image_url}...")
        with urllib.request.urlopen(image_url) as response:  # noqa: S310
            image_bytes = response.read()

    print("Generating labels...")
    labeler = Qwen3VLLabeler()
    result = labeler.generate_label.remote(image_bytes, "test_image")

    print("\nResult:")
    print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    # For local testing
    print("Run with: modal run modal/generate_pseudo_labels.py")
