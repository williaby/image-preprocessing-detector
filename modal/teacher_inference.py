# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Modal serverless endpoint for teacher model inference.

Sprint 4.2.1: Package Teacher for Modal (Phase 4B)

Provides GPU-accelerated teacher inference on Modal's serverless infrastructure:
- Downloads teacher ONNX model from GCS on container startup
- Runs inference on T4/A10 GPU with ONNX Runtime
- Returns multi-head IQA scores with confidence
- Includes request validation and size guardrails

Usage:
    # Deploy endpoint
    modal deploy modal/teacher_inference.py

    # Test locally
    modal run modal/teacher_inference.py::test_inference

    # Check endpoint URL
    modal app list

GCS Model Path:
    gs://image_detection_b/models/phase2_iqa/resnet50_teacher_baseline.onnx

Architecture:
    - Input: 224x224 RGB image (ImageNet normalized)
    - Output: 5 heads (blur, noise, skew, illumination, artifacts)
    - Model: ResNet-50 teacher trained on 100K IQA dataset
"""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import modal

# =============================================================================
# Constants
# =============================================================================

# GCS model location
GCS_BUCKET = "image_detection_b"
GCS_MODEL_PATH = "models/phase2_iqa/resnet50_teacher_baseline.onnx"
LOCAL_MODEL_PATH = Path("/root/models/resnet50_teacher.onnx")

# Model configuration
INPUT_SIZE = 224
ISSUE_TYPES = ["blur", "noise", "skew", "illumination", "artifacts"]

# Request guardrails (Sprint 4.2.2)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB max
MAX_IMAGE_DIMENSION = 8192  # 8K max dimension
MIN_IMAGE_DIMENSION = 32  # Minimum 32px

# ImageNet normalization constants
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# =============================================================================
# Modal App Configuration
# =============================================================================

app = modal.App("iqa-teacher-inference")

# Define container image with inference dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # ONNX inference (CPU and GPU support)
        "onnxruntime-gpu>=1.16.0",
        # Image processing
        "numpy>=1.24.0,<2.0.0",
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
        # GCS for model download
        "google-cloud-storage>=2.10.0",
    )
    # Copy GCS credentials
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)


# =============================================================================
# Helper Functions
# =============================================================================


def download_model_from_gcs() -> Path:
    """Download teacher ONNX model from GCS.

    Returns:
        Path to local model file
    """
    from google.cloud import storage

    # Set credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/.gcp/service-account.json"

    # Create local directory
    LOCAL_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    if LOCAL_MODEL_PATH.exists():
        print(f"Model already cached: {LOCAL_MODEL_PATH}")
        return LOCAL_MODEL_PATH

    print(f"Downloading model from gs://{GCS_BUCKET}/{GCS_MODEL_PATH}...")
    start_time = time.time()

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_MODEL_PATH)
    blob.download_to_filename(str(LOCAL_MODEL_PATH))

    download_time = time.time() - start_time
    model_size_mb = LOCAL_MODEL_PATH.stat().st_size / (1024 * 1024)
    print(f"Downloaded {model_size_mb:.1f} MB in {download_time:.1f}s")

    return LOCAL_MODEL_PATH


def validate_image_request(
    image_bytes: bytes | None, image_array: list | None
) -> tuple[bool, str | None]:
    """Validate image request before processing.

    Sprint 4.2.2: Request size guardrails

    Args:
        image_bytes: Raw image bytes (base64 decoded)
        image_array: Image as nested list (for direct array input)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if image_bytes is None and image_array is None:
        return False, "Either image_bytes or image_array must be provided"

    if image_bytes is not None:
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            return (
                False,
                f"Image exceeds max size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB",
            )

    return True, None


def preprocess_image(image_array: Any) -> Any:
    """Preprocess image for ONNX inference.

    Args:
        image_array: Image as numpy array (H, W, C) uint8

    Returns:
        Preprocessed tensor (1, 3, 224, 224) float32
    """
    import cv2
    import numpy as np

    # Ensure numpy array
    if not isinstance(image_array, np.ndarray):
        image_array = np.array(image_array, dtype=np.uint8)

    # Validate dimensions
    if len(image_array.shape) != 3 or image_array.shape[2] != 3:
        raise ValueError(f"Expected RGB image (H, W, 3), got shape {image_array.shape}")

    h, w = image_array.shape[:2]
    if h > MAX_IMAGE_DIMENSION or w > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Image dimensions ({w}x{h}) exceed max {MAX_IMAGE_DIMENSION}")
    if h < MIN_IMAGE_DIMENSION or w < MIN_IMAGE_DIMENSION:
        raise ValueError(f"Image dimensions ({w}x{h}) below min {MIN_IMAGE_DIMENSION}")

    # Convert BGR to RGB if needed (OpenCV loads as BGR)
    if image_array.dtype != np.uint8:
        image_array = image_array.astype(np.uint8)

    # Resize to model input size
    resized = cv2.resize(
        image_array, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR
    )

    # Convert to float32 and normalize to [0, 1]
    tensor = resized.astype(np.float32) / 255.0

    # Apply ImageNet normalization
    for c in range(3):
        tensor[:, :, c] = (tensor[:, :, c] - IMAGENET_MEAN[c]) / IMAGENET_STD[c]

    # Transpose to NCHW format
    tensor = np.transpose(tensor, (2, 0, 1))  # HWC -> CHW
    tensor = np.expand_dims(tensor, axis=0)  # Add batch dimension

    return tensor.astype(np.float32)


# =============================================================================
# Modal Class for Persistent ONNX Session
# =============================================================================


@app.cls(
    image=image,
    gpu="T4",  # T4 16GB - cost-optimized for inference
    timeout=300,  # 5 minute timeout per request
    container_idle_timeout=300,  # Keep warm for 5 minutes
    allow_concurrent_inputs=10,  # Handle up to 10 concurrent requests
)
class TeacherInference:
    """Modal class for teacher model inference with persistent ONNX session."""

    @modal.enter()
    def load_model(self) -> None:
        """Load ONNX model on container startup."""
        import onnxruntime as ort

        print("Initializing TeacherInference...")

        # Download model from GCS
        model_path = download_model_from_gcs()

        # Create ONNX Runtime session with GPU provider
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=providers,
        )

        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

        # Warm up the model
        import numpy as np

        dummy_input = np.random.randn(1, 3, INPUT_SIZE, INPUT_SIZE).astype(np.float32)
        self.session.run(None, {self.input_name: dummy_input})

        print("Model loaded and warmed up")
        print(f"  Input: {self.input_name}")
        print(f"  Outputs: {self.output_names}")
        print(f"  Provider: {self.session.get_providers()[0]}")

    @modal.method()
    def predict(
        self,
        image_b64: str | None = None,
        image_array: list | None = None,
        request_id: str | None = None,
        model_version: str = "v1.0",
    ) -> dict[str, Any]:
        """Run teacher inference on input image.

        Args:
            image_b64: Base64-encoded image bytes (JPEG/PNG)
            image_array: Image as nested list (H, W, C) uint8
            request_id: Optional request ID for correlation
            model_version: Model version string

        Returns:
            Dictionary with scores, confidences, timing, and metadata
        """
        import io

        import numpy as np
        from PIL import Image

        start_time = time.time()

        try:
            # Decode input
            if image_b64 is not None:
                image_bytes = base64.b64decode(image_b64)
                is_valid, error = validate_image_request(image_bytes, None)
                if not is_valid:
                    return {"error": error, "request_id": request_id}

                # Load image from bytes
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                image_np = np.array(img)

            elif image_array is not None:
                is_valid, error = validate_image_request(None, image_array)
                if not is_valid:
                    return {"error": error, "request_id": request_id}
                image_np = np.array(image_array, dtype=np.uint8)

            else:
                return {"error": "No image provided", "request_id": request_id}

            # Preprocess
            preprocess_start = time.time()
            input_tensor = preprocess_image(image_np)
            preprocess_time = (time.time() - preprocess_start) * 1000

            # Run inference
            inference_start = time.time()
            outputs = self.session.run(None, {self.input_name: input_tensor})
            inference_time = (time.time() - inference_start) * 1000

            # Parse outputs - model outputs 5 separate heads
            scores = {}
            confidences = {}

            for i, issue_type in enumerate(ISSUE_TYPES):
                if i < len(outputs):
                    # Sigmoid activation for probability
                    raw_score = (
                        float(outputs[i][0][0])
                        if outputs[i].ndim > 1
                        else float(outputs[i][0])
                    )
                    score = 1.0 / (1.0 + np.exp(-raw_score))  # Sigmoid
                    scores[issue_type] = round(score, 4)
                    # Confidence based on how far from 0.5 (more extreme = more confident)
                    confidences[issue_type] = round(abs(score - 0.5) * 2, 4)

            total_time = (time.time() - start_time) * 1000

            return {
                "scores": scores,
                "confidences": confidences,
                "inference_time_ms": round(inference_time, 2),
                "preprocess_time_ms": round(preprocess_time, 2),
                "total_time_ms": round(total_time, 2),
                "device_tag": "T4",
                "model_version": model_version,
                "request_id": request_id,
            }

        except Exception as e:
            return {
                "error": str(e),
                "request_id": request_id,
                "total_time_ms": round((time.time() - start_time) * 1000, 2),
            }


# =============================================================================
# Standalone Functions for Testing
# =============================================================================


@app.function(image=image, gpu="T4", timeout=60)
def test_inference() -> dict[str, Any]:
    """Test function to verify model loading and inference.

    Usage:
        modal run modal/teacher_inference.py::test_inference
    """
    import numpy as np

    print("Testing teacher inference endpoint...")

    # Create a synthetic test image
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Test the inference class
    inferencer = TeacherInference()
    result = inferencer.predict.local(
        image_array=test_image.tolist(),
        request_id="test-001",
        model_version="v1.0",
    )

    print(f"Result: {result}")
    return result


@app.function(image=image, timeout=60)
def health_check() -> dict[str, Any]:
    """Health check endpoint for monitoring.

    Returns status without loading the model.
    """
    return {
        "status": "healthy",
        "model_path": f"gs://{GCS_BUCKET}/{GCS_MODEL_PATH}",
        "input_size": INPUT_SIZE,
        "issue_types": ISSUE_TYPES,
    }


# =============================================================================
# Local Entrypoint
# =============================================================================


@app.local_entrypoint()
def main() -> None:
    """Run test inference when invoked via modal run."""
    print("Running teacher inference test...")
    result = test_inference.remote()
    print(f"Test result: {result}")

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print("Inference successful!")
        print(f"  Scores: {result.get('scores', {})}")
        print(f"  Inference time: {result.get('inference_time_ms', 0):.1f} ms")
        print(f"  Total time: {result.get('total_time_ms', 0):.1f} ms")
