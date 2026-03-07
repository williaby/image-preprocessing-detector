#!/usr/bin/env python3
"""DeQA-Doc bridge script — runs inside the DeQA-Doc venv.

This is a STANDALONE script with NO image_detection dependencies.
It loads a per-dimension mPLUG-Owl2 model and scores images read
from stdin, writing JSONL predictions to stdout.

Usage (from DeQA-Doc venv):
    echo '{"image_path": "/abs/path/to/img.jpg"}' | \
        python bridge_script.py \
            --model-path /path/to/deqa_overall_model \
            --dimension overall \
            --device cuda:0

Protocol:
    stdin:  one JSON object per line: {"image_path": "<abs_path>"}
    stdout: one JSON object per line: {
        "image_path": "<abs_path>",
        "dimension": "overall",
        "level_probs": [0.05, 0.15, 0.40, 0.25, 0.15],
        "expected_mos": 3.42,
        "score_normalized": 0.605,
        "status": "ok"
    }
    stderr: logging/progress (not parsed by caller)

    On error for a single image:
    {"image_path": "<path>", "dimension": "...", "status": "error", "error": "..."}

    Sentinel: {"status": "done", "processed": N, "errors": M}
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# Guard: this script must run inside the DeQA-Doc venv
try:
    import torch
    from PIL import Image
except ImportError as exc:
    print(
        json.dumps(
            {
                "status": "fatal",
                "error": f"Missing dependency: {exc}. "
                "This script must run inside the DeQA-Doc venv.",
            }
        ),
        flush=True,
    )
    sys.exit(1)


# Dimension-specific prompt suffixes (match DeQA-Doc training)
DIMENSION_PROMPTS: dict[str, str] = {
    "overall": "The overall_quality of the image is",
    "sharpness": "The sharpness of the image is",
    "color_fidelity": "The color_fidelity of the image is",
}

LEVEL_NAMES: list[str] = ["excellent", "good", "fair", "poor", "bad"]
LEVEL_MOS: list[float] = [5.0, 4.0, 3.0, 2.0, 1.0]


def _load_model(
    model_path: str,
    device: str,
    preprocessor_path: str | None = None,
    load_8bit: bool = False,
    load_4bit: bool = False,
) -> tuple[Any, Any, Any, list[int]]:
    """Load mPLUG-Owl2 model and return (tokenizer, model, processor, level_ids)."""
    # Must set PYTHONPATH to include DeQA-Score root before calling
    from src.mm_utils import get_model_name_from_path
    from src.model.builder import load_pretrained_model

    # Suppress redundant torch init (these are methods, so lambda _self matches signature)
    torch.nn.Linear.reset_parameters = lambda _self: None  # type: ignore[assignment]
    torch.nn.LayerNorm.reset_parameters = lambda _self: None  # type: ignore[assignment]

    model_name = get_model_name_from_path(model_path)
    tokenizer, model, image_processor, _ = load_pretrained_model(
        model_path,
        None,  # model_base
        model_name,
        load_8bit,
        load_4bit,
        device=device,
        preprocessor_path=preprocessor_path,
    )

    level_ids = [
        tokenizer(f" {name}", add_special_tokens=False)["input_ids"][-1]
        for name in LEVEL_NAMES
    ]

    return tokenizer, model, image_processor, level_ids


def _build_input_ids(tokenizer: Any, dimension: str, device: str) -> torch.Tensor:
    """Build tokenized input IDs for the given dimension prompt."""
    from src.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
    from src.conversation import conv_templates
    from src.mm_utils import tokenizer_image_token

    conv = conv_templates["mplug_owl2"].copy()
    user_msg = "How would you rate the quality of this image?\n" + DEFAULT_IMAGE_TOKEN
    conv.append_message(conv.roles[0], user_msg)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt() + " " + DIMENSION_PROMPTS[dimension]

    return (
        tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
        .unsqueeze(0)
        .to(device)
    )


def _expand2square(
    pil_img: Image.Image, background_color: tuple[int, int, int]
) -> Image.Image:
    """Pad image to square with background color."""
    width, height = pil_img.size
    if width == height:
        return pil_img
    side = max(width, height)
    result = Image.new(pil_img.mode, (side, side), background_color)
    if width > height:
        result.paste(pil_img, (0, (width - height) // 2))
    else:
        result.paste(pil_img, ((height - width) // 2, 0))
    return result


def _score_batch(
    image_paths: list[str],
    model: Any,
    image_processor: Any,
    input_ids: torch.Tensor,
    level_ids: list[int],
    device: str,
    dimension: str,
) -> list[dict[str, Any]]:
    """Score a batch of images, returning prediction dicts."""
    results: list[dict[str, Any]] = []
    mean_vals = [int(x * 255) for x in image_processor.image_mean]
    bg_color = (mean_vals[0], mean_vals[1], mean_vals[2])

    image_tensors = []
    valid_paths: list[str] = []
    error_paths: list[tuple[str, str]] = []

    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            img = _expand2square(img, bg_color)
            tensor = (
                image_processor.preprocess(img, return_tensors="pt")["pixel_values"]
                .half()
                .to(device)
            )
            image_tensors.append(tensor)
            valid_paths.append(path)
        except Exception as exc:
            error_paths.append((path, str(exc)))

    # Process valid images
    if image_tensors:
        with torch.inference_mode():
            output_logits = model(
                input_ids=input_ids.repeat(len(image_tensors), 1),
                images=torch.cat(image_tensors, 0),
            )["logits"][:, -1]

        for j, path in enumerate(valid_paths):
            logits_at_levels = output_logits[j, level_ids]
            probs = torch.softmax(logits_at_levels, dim=0).cpu().tolist()
            expected_mos = sum(p * m for p, m in zip(probs, LEVEL_MOS, strict=True))
            score_normalized = (expected_mos - 1.0) / 4.0

            results.append(
                {
                    "image_path": path,
                    "dimension": dimension,
                    "level_probs": [round(p, 6) for p in probs],
                    "expected_mos": round(expected_mos, 4),
                    "score_normalized": round(score_normalized, 4),
                    "status": "ok",
                }
            )

    # Report errors
    for path, err in error_paths:
        results.append(
            {
                "image_path": path,
                "dimension": dimension,
                "status": "error",
                "error": err,
            }
        )

    return results


def main() -> None:
    """Main loop: read image paths from stdin, write predictions to stdout."""
    parser = argparse.ArgumentParser(
        description="DeQA-Doc bridge for subprocess inference"
    )
    parser.add_argument(
        "--model-path", type=str, required=True, help="Path to per-dimension model"
    )
    parser.add_argument(
        "--dimension", type=str, required=True, choices=list(DIMENSION_PROMPTS)
    )
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--preprocessor-path", type=str, default=None)
    parser.add_argument("--load-8bit", action="store_true")
    parser.add_argument("--load-4bit", action="store_true")
    args = parser.parse_args()

    # Log to stderr (stdout is for results)
    print(
        f"Loading model for dimension '{args.dimension}' from {args.model_path}...",
        file=sys.stderr,
        flush=True,
    )

    tokenizer, model, image_processor, level_ids = _load_model(
        args.model_path,
        args.device,
        preprocessor_path=args.preprocessor_path,
        load_8bit=args.load_8bit,
        load_4bit=args.load_4bit,
    )
    input_ids = _build_input_ids(tokenizer, args.dimension, args.device)

    print(
        f"Model loaded. Ready to score (batch_size={args.batch_size}).",
        file=sys.stderr,
        flush=True,
    )

    processed = 0
    errors = 0
    batch_paths: list[str] = []

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
            image_path = record["image_path"]
        except (json.JSONDecodeError, KeyError) as exc:
            print(
                json.dumps(
                    {"status": "error", "error": f"Invalid input: {exc}", "raw": line}
                ),
                flush=True,
            )
            errors += 1
            continue

        batch_paths.append(image_path)

        if len(batch_paths) >= args.batch_size:
            results = _score_batch(
                batch_paths,
                model,
                image_processor,
                input_ids,
                level_ids,
                args.device,
                args.dimension,
            )
            for r in results:
                print(json.dumps(r), flush=True)
                if r["status"] == "error":
                    errors += 1
                else:
                    processed += 1
            batch_paths = []

    # Flush remaining batch
    if batch_paths:
        results = _score_batch(
            batch_paths,
            model,
            image_processor,
            input_ids,
            level_ids,
            args.device,
            args.dimension,
        )
        for r in results:
            print(json.dumps(r), flush=True)
            if r["status"] == "error":
                errors += 1
            else:
                processed += 1

    # Sentinel
    print(
        json.dumps({"status": "done", "processed": processed, "errors": errors}),
        flush=True,
    )


if __name__ == "__main__":
    main()
