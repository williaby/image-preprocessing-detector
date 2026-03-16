#!/usr/bin/env python3
"""VLM prompting experiment for cross-model OOD agreement system.

Evaluates multiple VLMs and prompting strategies on DIQA-5000 to determine
the best configuration for Tier 2 cross-model validation.

Prompting strategies tested:
  1. overall_only: Single prompt for overall quality rating
  2. single_prompt_3dim: One prompt asking for all 3 dimensions
  3. separate_prompts: 3 separate prompts, one per dimension (consensus-recommended)

VLM candidates:
  - Qwen3.5-9B (early-fusion multimodal, OmniDocBench 90.8)
  - MiniCPM-V 4.5 (SOTA OCR, best document parsing)

Output: JSONL with per-image ratings and SRCC/PLCC metrics vs MOS.

Usage:
    # Local inference (requires GPU with sufficient VRAM):
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/run_vlm_prompting_experiment.py \
        --model qwen3.5-9b \
        --strategy separate_prompts \
        --meta-path /path/to/diqa-5000/metas/train.json \
        --image-root /path/to/diqa-5000/images \
        --output results/vlm_prompting_experiment/

    # OpenRouter API (no GPU required):
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/run_vlm_prompting_experiment.py \
        --model qwen3.5-27b \
        --backend openrouter \
        --env-file /home/byron/dev/DeQA-Doc/.env \
        --strategy separate_prompts \
        --meta-path /path/to/diqa-5000/metas/train.json \
        --image-root /path/to/diqa-5000/images \
        --contact-sheet 25 \
        --limit 100
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Quality level mapping (matches DeQA-Score convention)
QUALITY_LEVELS = {
    "excellent": 5.0,
    "good": 4.0,
    "fair": 3.0,
    "poor": 2.0,
    "bad": 1.0,
}

DIMENSIONS = ("overall", "sharpness", "color")

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPT_OVERALL_ONLY = """Rate the overall quality of this document image.
Choose exactly one: excellent, good, fair, poor, or bad.
Respond with only one word."""

PROMPT_SINGLE_3DIM = """Rate this document image on three quality dimensions.
For each dimension, choose exactly one: excellent, good, fair, poor, or bad.

Respond in this exact format (one word per line):
overall: <rating>
sharpness: <rating>
color: <rating>"""

PROMPT_TEMPLATES_PER_DIM = {
    "overall": """Rate the overall quality of this document image.
Consider readability, clarity, and general visual quality.
Choose exactly one: excellent, good, fair, poor, or bad.
Respond with only one word.""",
    "sharpness": """Rate the sharpness quality of this document image.
Consider text clarity, edge definition, and focus.
Choose exactly one: excellent, good, fair, poor, or bad.
Respond with only one word.""",
    "color": """Rate the color fidelity of this document image.
Consider color accuracy, saturation, and consistency.
Choose exactly one: excellent, good, fair, poor, or bad.
Respond with only one word.""",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class VLMRating:
    """Single VLM rating for one image."""

    image_id: str
    model: str
    strategy: str
    ratings: dict[str, str]  # dim -> category (e.g. "good")
    scores: dict[str, float]  # dim -> numeric score (e.g. 4.0)
    raw_responses: dict[str, str]  # dim -> raw model output
    latency_ms: float


# ---------------------------------------------------------------------------
# VLM inference backends
# ---------------------------------------------------------------------------


class VLMBackend(ABC):
    """Abstract base for VLM inference."""

    @abstractmethod
    def generate(self, image_path: str, prompt: str) -> str:
        """Generate text response for image + prompt."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier string."""


class TransformersVLMBackend(VLMBackend):
    """Local inference via transformers for Qwen3.5 and MiniCPM-V."""

    def __init__(self, model_id: str, device: str = "cuda:0") -> None:
        self._model_id = model_id
        self._device = device
        self._model: Any = None
        self._processor: Any = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        log.info("Loading VLM: %s on %s", self._model_id, self._device)
        self._processor = AutoProcessor.from_pretrained(
            self._model_id, trust_remote_code=True
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_id,
            torch_dtype=torch.bfloat16,
            device_map=self._device,
            trust_remote_code=True,
        )
        self._model.eval()
        log.info("VLM loaded: %s", self._model_id)

    def generate(self, image_path: str, prompt: str) -> str:
        """Generate response using transformers pipeline."""
        import torch
        from PIL import Image

        self._ensure_loaded()

        image = Image.open(image_path).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[text], images=[image], return_tensors="pt", padding=True
        )
        inputs = inputs.to(self._model.device)

        with torch.inference_mode():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=64,
                do_sample=False,
                temperature=None,
                top_p=None,
            )

        # Decode only new tokens
        generated = output_ids[0][inputs["input_ids"].shape[1] :]
        return self._processor.decode(generated, skip_special_tokens=True).strip()

    @property
    def model_name(self) -> str:
        return self._model_id.split("/")[-1]


class OpenRouterVLMBackend(VLMBackend):
    """API-based inference via OpenRouter (OpenAI-compatible).

    Supports any vision-capable model available on OpenRouter.
    Images are sent as base64-encoded data URIs.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        max_tokens: int = 32,
        retry_attempts: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self._model_id = model_id
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        if not self._api_key:
            msg = (
                "OPENROUTER_API_KEY not set. Pass via --env-file or "
                "set OPENROUTER_API_KEY environment variable."
            )
            raise ValueError(msg)

    def _encode_image(self, image_path: str) -> str:
        """Read and base64-encode an image file."""
        path = Path(image_path)
        suffix = path.suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(
            suffix, "jpeg"
        )
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/{mime};base64,{b64}"

    def generate(self, image_path: str, prompt: str) -> str:
        """Send image + prompt to OpenRouter and return text response."""
        data_uri = self._encode_image(image_path)
        payload = json.dumps(
            {
                "model": self._model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            },
                        ],
                    }
                ],
                "max_tokens": self._max_tokens,
                "temperature": 0.0,
            }
        ).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(self._retry_attempts):
            try:
                if not self.API_URL.startswith("https://"):
                    raise ValueError(f"Only HTTPS URLs allowed, got: {self.API_URL}")
                req = urllib_request.Request(
                    self.API_URL, data=payload, headers=headers, method="POST"
                )
                with (
                    urllib_request.urlopen(
                        req, timeout=120
                    ) as resp  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected  -- CLI-only script; URL is validated as HTTPS above (line 292)
                ):
                    body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"].get("content")
                if content is None:
                    log.warning("Model returned null content: %s", body)
                    return ""
                return content.strip()
            except Exception as exc:
                last_error = exc
                status = getattr(exc, "code", None)
                if status == 429:
                    wait = self._retry_delay * (2**attempt)
                    log.warning("Rate limited (429), retrying in %.1fs...", wait)
                    time.sleep(wait)
                elif status and status >= 500:
                    wait = self._retry_delay * (2**attempt)
                    log.warning("Server error (%s), retrying in %.1fs...", status, wait)
                    time.sleep(wait)
                else:
                    log.error("OpenRouter API error: %s", exc)
                    raise

        msg = f"OpenRouter API failed after {self._retry_attempts} retries"
        raise RuntimeError(msg) from last_error

    @property
    def model_name(self) -> str:
        return self._model_id.replace("/", "_")


# ---------------------------------------------------------------------------
# Rating extraction
# ---------------------------------------------------------------------------


def parse_single_rating(response: str) -> str | None:
    """Extract a single quality category from VLM response.

    Args:
        response: Raw VLM text output.

    Returns:
        Quality category string or None if unparseable.
    """
    response_lower = response.lower().strip()
    for level in QUALITY_LEVELS:
        if level in response_lower:
            return level
    return None


def parse_three_dim_response(response: str) -> dict[str, str | None]:
    """Parse a 3-dimension response from single_prompt_3dim strategy.

    Args:
        response: Raw VLM text with format "overall: good\\nsharpness: fair\\n..."

    Returns:
        Dict mapping dimension to category (or None if unparseable).
    """
    result: dict[str, str | None] = dict.fromkeys(DIMENSIONS)
    for line in response.lower().split("\n"):
        line = line.strip()
        for dim in DIMENSIONS:
            if dim in line:
                for level in QUALITY_LEVELS:
                    if level in line:
                        result[dim] = level
                        break
    return result


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------


def run_strategy(
    backend: VLMBackend,
    strategy: str,
    image_paths: list[str],
    image_ids: list[str],
) -> list[VLMRating]:
    """Run a prompting strategy on all images.

    Args:
        backend: VLM inference backend.
        strategy: One of "overall_only", "single_prompt_3dim", "separate_prompts".
        image_paths: List of image file paths.
        image_ids: Corresponding image identifiers.

    Returns:
        List of VLMRating results.
    """
    results = []
    n_images = len(image_paths)

    for idx, (path, img_id) in enumerate(zip(image_paths, image_ids, strict=True)):
        if idx % 50 == 0:
            log.info(
                "[%s/%s] Processing %s with strategy=%s",
                idx,
                n_images,
                img_id,
                strategy,
            )

        start = time.perf_counter()
        ratings: dict[str, str] = {}
        raw_responses: dict[str, str] = {}

        if strategy == "overall_only":
            resp = backend.generate(path, PROMPT_OVERALL_ONLY)
            raw_responses["overall"] = resp
            cat = parse_single_rating(resp)
            if cat:
                ratings["overall"] = cat

        elif strategy == "single_prompt_3dim":
            resp = backend.generate(path, PROMPT_SINGLE_3DIM)
            raw_responses["all"] = resp
            parsed = parse_three_dim_response(resp)
            ratings.update({dim: cat for dim, cat in parsed.items() if cat})

        elif strategy == "separate_prompts":
            for dim in DIMENSIONS:
                resp = backend.generate(path, PROMPT_TEMPLATES_PER_DIM[dim])
                raw_responses[dim] = resp
                cat = parse_single_rating(resp)
                if cat:
                    ratings[dim] = cat

        elapsed_ms = (time.perf_counter() - start) * 1000

        scores = {dim: QUALITY_LEVELS[cat] for dim, cat in ratings.items()}
        results.append(
            VLMRating(
                image_id=img_id,
                model=backend.model_name,
                strategy=strategy,
                ratings=ratings,
                scores=scores,
                raw_responses=raw_responses,
                latency_ms=elapsed_ms,
            )
        )

    return results


def compute_metrics(
    vlm_results: list[VLMRating],
    ground_truth: dict[str, float],
    dimension: str = "overall",
) -> dict[str, float]:
    """Compute SRCC and PLCC between VLM scores and ground truth MOS.

    Args:
        vlm_results: VLM rating results.
        ground_truth: Dict mapping image_id to MOS score.
        dimension: Which dimension to evaluate.

    Returns:
        Dict with srcc, plcc, mae, n_valid, n_total, parse_rate.
    """
    vlm_scores = []
    gt_scores = []

    for r in vlm_results:
        if dimension in r.scores and r.image_id in ground_truth:
            vlm_scores.append(r.scores[dimension])
            gt_scores.append(ground_truth[r.image_id])

    n_valid = len(vlm_scores)
    n_total = len(vlm_results)

    if n_valid < 3:
        return {
            "srcc": 0.0,
            "plcc": 0.0,
            "mae": float("inf"),
            "n_valid": n_valid,
            "n_total": n_total,
            "parse_rate": n_valid / max(n_total, 1),
        }

    vlm_arr = np.array(vlm_scores)
    gt_arr = np.array(gt_scores)

    srcc, _ = stats.spearmanr(vlm_arr, gt_arr)
    plcc, _ = stats.pearsonr(vlm_arr, gt_arr)
    mae = float(np.mean(np.abs(vlm_arr - gt_arr)))

    return {
        "srcc": float(srcc),
        "plcc": float(plcc),
        "mae": mae,
        "n_valid": n_valid,
        "n_total": n_total,
        "parse_rate": n_valid / max(n_total, 1),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, dict[str, str]] = {
    "qwen3.5-9b": {
        "local": "Qwen/Qwen3.5-9B",
        "openrouter": "qwen/qwen3.5-9b",
    },
    "qwen3.5-27b": {
        "local": "Qwen/Qwen3.5-27B",
        "openrouter": "qwen/qwen3.5-27b",
    },
    "minicpm-v-4.5": {
        "local": "openbmb/MiniCPM-V-4_5",
        "openrouter": "openbmb/minicpm-v-4.5",
    },
    "qwen3-vl-8b": {
        "local": "Qwen/Qwen3-VL-8B-Instruct",
        "openrouter": "qwen/qwen3-vl-8b-instruct",
    },
    "deepseek-vl2-small": {
        "local": "deepseek-ai/DeepSeek-VL2-Small",
        "openrouter": "deepseek/deepseek-vl2-small",
    },
    "gemini-flash-lite": {
        "openrouter": "google/gemini-3.1-flash-lite-preview",
    },
    "gemini-flash-image": {
        "openrouter": "google/gemini-3.1-flash-image-preview",
    },
    "kimi-k2.5": {
        "openrouter": "moonshotai/kimi-k2.5",
    },
    "grok-4.1-fast": {
        "openrouter": "x-ai/grok-4.1-fast",
    },
    "qwen3.5-flash": {
        "openrouter": "qwen/qwen3.5-flash-02-23",
    },
}

ALL_STRATEGIES = ["overall_only", "single_prompt_3dim", "separate_prompts"]


def _load_env_file(env_path: str) -> None:
    """Load key=value pairs from an env file into os.environ."""
    path = Path(env_path)
    if not path.exists():
        log.warning("Env file not found: %s", env_path)
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    log.info("Loaded env from %s", env_path)


def _create_contact_sheet(
    image_paths: list[str],
    vlm_results: list[VLMRating],
    output_path: str,
    cols: int = 5,
    thumb_size: int = 300,
) -> str:
    """Generate a contact sheet with VLM ratings overlaid for visual validation.

    Args:
        image_paths: Paths to source images.
        vlm_results: Corresponding VLM ratings.
        output_path: Where to save the contact sheet.
        cols: Number of columns in the grid.
        thumb_size: Thumbnail dimension (square).

    Returns:
        Path to the saved contact sheet.
    """
    from PIL import Image, ImageDraw, ImageFont

    n = len(image_paths)
    rows = (n + cols - 1) // cols
    margin = 4
    label_height = 60
    cell_w = thumb_size + margin
    cell_h = thumb_size + label_height + margin

    sheet = Image.new("RGB", (cols * cell_w + margin, rows * cell_h + margin), "white")
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except OSError:
        font = ImageFont.load_default()

    result_map = {r.image_id: r for r in vlm_results}

    for idx, img_path in enumerate(image_paths):
        row, col = divmod(idx, cols)
        x = col * cell_w + margin
        y = row * cell_h + margin

        try:
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((thumb_size, thumb_size))
            sheet.paste(img, (x, y))
        except Exception:
            draw.rectangle([x, y, x + thumb_size, y + thumb_size], fill="gray")

        # Overlay rating text
        img_id = Path(img_path).name
        rating = result_map.get(img_id)
        if rating:
            label_parts = [f"{img_id[:20]}"]
            for dim, cat in rating.ratings.items():
                label_parts.append(f"{dim[:3]}:{cat}")
            label = " ".join(label_parts)
        else:
            label = img_id[:25]

        draw.text((x + 2, y + thumb_size + 2), label, fill="black", font=font)

    sheet.save(output_path)
    log.info(
        "Contact sheet saved: %s (%d images, %dx%d grid)", output_path, n, cols, rows
    )
    return output_path


def main() -> None:
    """Run VLM prompting experiment."""
    parser = argparse.ArgumentParser(
        description="VLM prompting experiment for OOD cross-model agreement"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=list(MODEL_REGISTRY.keys()),
        help="VLM model to evaluate",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="local",
        choices=["local", "openrouter"],
        help="Inference backend: local (transformers) or openrouter (API)",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env file with API keys (e.g. OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="all",
        choices=[*ALL_STRATEGIES, "all"],
        help="Prompting strategy (default: run all)",
    )
    parser.add_argument(
        "--meta-path",
        type=str,
        required=True,
        help="Path to DIQA-5000 train.json metadata",
    )
    parser.add_argument(
        "--image-root",
        type=str,
        required=True,
        help="Root directory containing DIQA-5000 images",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/vlm_prompting_experiment",
        help="Output directory for results",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Device for local inference",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of images (for testing)",
    )
    parser.add_argument(
        "--contact-sheet",
        type=int,
        default=0,
        help="Generate contact sheet with N images for visual validation (0=off)",
    )
    args = parser.parse_args()

    # Load env file if provided
    if args.env_file:
        _load_env_file(args.env_file)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load metadata
    with open(args.meta_path) as f:
        metadata = json.load(f)

    if args.limit is not None:
        metadata = metadata[: args.limit]

    # Build image paths and ground truth
    image_paths = []
    image_ids = []
    ground_truth: dict[str, float] = {}

    for item in metadata:
        img_id = item.get("image", item.get("img_path", ""))
        img_path = str(Path(args.image_root) / img_id)
        image_paths.append(img_path)
        image_ids.append(img_id)
        if "mos" in item:
            ground_truth[img_id] = item["mos"]
        elif "gt_score" in item:
            ground_truth[img_id] = item["gt_score"]

    log.info(
        "Loaded %d images, %d with ground truth", len(image_ids), len(ground_truth)
    )

    # Initialize VLM backend
    model_entry = MODEL_REGISTRY[args.model]
    if args.backend == "openrouter":
        if "openrouter" not in model_entry:
            parser.error(f"Model {args.model} has no OpenRouter backend")
        model_id = model_entry["openrouter"]
        backend: VLMBackend = OpenRouterVLMBackend(model_id=model_id)
        log.info("Using OpenRouter backend: %s", model_id)
    else:
        if "local" not in model_entry:
            parser.error(
                f"Model {args.model} has no local backend (use --backend openrouter)"
            )
        model_id = model_entry["local"]
        backend = TransformersVLMBackend(model_id=model_id, device=args.device)
        log.info("Using local transformers backend: %s", model_id)

    # Run strategies
    strategies = ALL_STRATEGIES if args.strategy == "all" else [args.strategy]
    all_metrics: dict[str, dict[str, dict[str, float]]] = {}

    for strategy in strategies:
        log.info("=" * 60)
        log.info("Running strategy: %s with model: %s", strategy, args.model)

        results = run_strategy(backend, strategy, image_paths, image_ids)

        # Save raw results
        results_path = output_dir / f"{args.model}_{strategy}_results.jsonl"
        with open(results_path, "w") as f:
            f.writelines(
                json.dumps(
                    {
                        "image_id": r.image_id,
                        "model": r.model,
                        "strategy": r.strategy,
                        "ratings": r.ratings,
                        "scores": r.scores,
                        "raw_responses": r.raw_responses,
                        "latency_ms": r.latency_ms,
                    }
                )
                + "\n"
                for r in results
            )
        log.info("Results saved to %s", results_path)

        # Compute metrics per dimension
        strategy_metrics: dict[str, dict[str, float]] = {}
        dims = ["overall"] if strategy == "overall_only" else list(DIMENSIONS)
        for dim in dims:
            if ground_truth:
                metrics = compute_metrics(results, ground_truth, dimension=dim)
                strategy_metrics[dim] = metrics
                log.info(
                    "  %s SRCC=%.4f PLCC=%.4f MAE=%.4f parse_rate=%.1f%% (n=%d/%d)",
                    dim,
                    metrics["srcc"],
                    metrics["plcc"],
                    metrics["mae"],
                    metrics["parse_rate"] * 100,
                    metrics["n_valid"],
                    metrics["n_total"],
                )

        all_metrics[strategy] = strategy_metrics

        # Compute avg latency
        latencies = [r.latency_ms for r in results]
        log.info(
            "  Avg latency: %.1fms (p50=%.1f, p95=%.1f)",
            np.mean(latencies),
            np.percentile(latencies, 50),
            np.percentile(latencies, 95),
        )

    # Generate contact sheet for visual validation
    if args.contact_sheet > 0:
        n_sheet = min(args.contact_sheet, len(image_paths))
        sheet_paths = image_paths[:n_sheet]
        # Use results from last strategy run for the sheet
        sheet_results = results[:n_sheet]
        sheet_path = str(
            output_dir / f"{args.model}_{strategies[-1]}_contact_sheet.png"
        )
        _create_contact_sheet(sheet_paths, sheet_results, sheet_path)

    # Save summary
    summary_path = output_dir / f"{args.model}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(
            {
                "model": args.model,
                "model_id": model_id,
                "backend": args.backend,
                "n_images": len(image_ids),
                "strategies": all_metrics,
            },
            f,
            indent=2,
        )
    log.info("Summary saved to %s", summary_path)

    # Print comparison table
    if len(all_metrics) > 1 and ground_truth:
        log.info("=" * 60)
        log.info("COMPARISON TABLE (SRCC vs MOS)")
        log.info("%-25s %10s %10s %10s", "Strategy", "Overall", "Sharpness", "Color")
        log.info("-" * 55)
        for strategy, dims in all_metrics.items():
            overall = dims.get("overall", {}).get("srcc", float("nan"))
            sharpness = dims.get("sharpness", {}).get("srcc", float("nan"))
            color = dims.get("color", {}).get("srcc", float("nan"))
            log.info("%-25s %10.4f %10.4f %10.4f", strategy, overall, sharpness, color)


if __name__ == "__main__":
    main()
