#!/usr/bin/env python3
"""Run docling-layout-egret-xlarge inference on DIQA-5000 audit samples.

Loads the sample set, runs layout detection via LayoutPredictor, maps labels
through the project LayoutTaxonomy, and writes structured results JSON.

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/run_egret_on_samples.py

    # Override device:
    PYTHONPATH=... uv run python3 scripts/audit/run_egret_on_samples.py --device cpu

    # Override confidence threshold:
    PYTHONPATH=... uv run python3 scripts/audit/run_egret_on_samples.py --threshold 0.5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_REPO = "ds4sd/docling-layout-egret-xlarge"

SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLE_SET_PATH = SCRIPT_DIR / "results" / "diqa-5000" / "sample_set.json"
OUTPUT_PATH = SCRIPT_DIR / "results" / "diqa-5000" / "egret_results.json"

# The model outputs labels in two naming conventions:
#   - 11 standard DocLayNet labels in PascalCase (e.g. "Text", "Caption")
#   - 6 extended labels from the Docling schema (e.g. "Document Index", "Code")
# We normalise PascalCase -> lowercase_underscore so everything goes through
# the "docling" taxonomy schema which covers all 17 classes.
_MODEL_LABEL_TO_DOCLING: dict[str, str] = {
    "Caption": "caption",
    "Footnote": "footnote",
    "Formula": "formula",
    "List-item": "list_item",
    "Page-footer": "page_footer",
    "Page-header": "page_header",
    "Picture": "picture",
    "Section-header": "section_header",
    "Table": "table",
    "Text": "text",
    "Title": "title",
    "Document Index": "document_index",
    "Code": "code",
    "Checkbox-Selected": "checkbox_selected",
    "Checkbox-Unselected": "checkbox_unselected",
    "Form": "form",
    "Key-Value Region": "key_value_region",
}

# Content-flag derivation: canonical classes that set each flag.
_TABLE_CLASSES = {"TABLE"}
_FORMULA_CLASSES = {"FORMULA"}
_FIGURE_CLASSES = {"PICTURE", "CHART"}
_CODE_CLASSES = {"CODE"}
_HANDWRITING_CLASSES = {"HANDWRITTEN_TEXT"}


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Detection:
    """Single detected layout element."""

    class_name_raw: str
    class_name_canonical: str
    class_name_doclaynet: str
    bbox_coco_xywh: list[float]
    confidence: float
    source_schema: str = "docling"


@dataclass
class ImageResult:
    """Aggregated result for one sample image."""

    image_id: str
    image_path: str
    image_width: int
    image_height: int
    inference_time_ms: float
    detection_count: int = 0
    detections: list[dict[str, Any]] = field(default_factory=list)
    content_flags_derived: dict[str, bool] = field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# Taxonomy helpers
# ---------------------------------------------------------------------------
def _build_taxonomy() -> Any:
    """Lazily import and build the project LayoutTaxonomy."""
    from image_preprocessing_detector.schema_utils.layout_taxonomy import (
        LayoutTaxonomy,
    )

    return LayoutTaxonomy()


def _map_label(
    raw_label: str,
    taxonomy: Any,
) -> tuple[str, str, str]:
    """Map a raw model label to (canonical, doclaynet, docling_key).

    Returns
    -------
    tuple of (canonical_class, doclaynet_label, docling_key)
    """
    docling_key = _MODEL_LABEL_TO_DOCLING.get(raw_label)
    if docling_key is None:
        # Fallback: try the raw label lowercased with spaces -> underscores
        docling_key = raw_label.lower().replace("-", "_").replace(" ", "_")

    try:
        canonical = taxonomy.to_canonical(docling_key, "docling")
    except Exception:
        canonical = "UNKNOWN"

    # Convert canonical -> DocLayNet label via taxonomy
    try:
        doclaynet_label = taxonomy.to_doclaynet(canonical)
    except Exception:
        doclaynet_label = raw_label  # passthrough if mapping fails

    return canonical, doclaynet_label, docling_key


def _derive_content_flags(canonical_classes: set[str]) -> dict[str, bool]:
    """Derive content flags from the set of detected canonical classes."""
    return {
        "has_table": bool(canonical_classes & _TABLE_CLASSES),
        "has_formula": bool(canonical_classes & _FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & _FIGURE_CLASSES),
        "has_code": bool(canonical_classes & _CODE_CLASSES),
        "has_handwriting": bool(canonical_classes & _HANDWRITING_CLASSES),
    }


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------
def run_inference(
    samples: list[dict[str, Any]],
    device: str,
    threshold: float,
) -> list[ImageResult]:
    """Run LayoutPredictor on every sample image.

    Parameters
    ----------
    samples:
        List of sample dicts from sample_set.json (must have 'absolute_path',
        'image_id', 'image_path').
    device:
        PyTorch device string ('cuda' or 'cpu').
    threshold:
        Minimum confidence score for detections.

    Returns
    -------
    List of ImageResult, one per sample (in input order).
    """
    from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor

    # -- Download / locate model artifacts --------------------------------
    log.info("Resolving model artifacts for %s ...", MODEL_REPO)
    model_path = snapshot_download(MODEL_REPO)
    log.info("Model artefacts at: %s", model_path)

    # -- Initialise predictor ---------------------------------------------
    log.info(
        "Loading LayoutPredictor on device=%s, threshold=%.2f ...", device, threshold
    )
    predictor = LayoutPredictor(
        artifact_path=model_path,
        device=device,
        base_threshold=threshold,
    )
    log.info("Model info: %s", predictor.info())

    # -- Build taxonomy ---------------------------------------------------
    taxonomy = _build_taxonomy()

    # -- Warmup pass (optional: stabilises GPU timing) --------------------
    _warmup_image = Image.new("RGB", (640, 640), color=(255, 255, 255))
    _ = list(predictor.predict(_warmup_image))
    log.info("Warmup complete.")

    # -- Run per-sample inference -----------------------------------------
    results: list[ImageResult] = []

    for idx, sample in enumerate(samples, start=1):
        image_id: str = sample["image_id"]
        image_path_rel: str = sample["image_path"]
        abs_path: str = sample["absolute_path"]

        log.info("[%d/%d] Processing %s ...", idx, len(samples), image_id)

        # Attempt to load and run inference
        try:
            img = Image.open(abs_path).convert("RGB")
        except Exception as exc:
            log.error("Failed to open image %s: %s", abs_path, exc)
            results.append(
                ImageResult(
                    image_id=image_id,
                    image_path=image_path_rel,
                    image_width=0,
                    image_height=0,
                    inference_time_ms=0.0,
                    error=f"Image load error: {exc}",
                )
            )
            continue

        width, height = img.size

        try:
            start_ns = time.perf_counter_ns()
            raw_preds = list(predictor.predict(img))
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        except Exception as exc:
            log.error("Inference failed for %s: %s", image_id, exc)
            results.append(
                ImageResult(
                    image_id=image_id,
                    image_path=image_path_rel,
                    image_width=width,
                    image_height=height,
                    inference_time_ms=0.0,
                    error=f"Inference error: {exc}",
                )
            )
            continue

        # -- Convert predictions ------------------------------------------
        detections: list[dict[str, Any]] = []
        canonical_set: set[str] = set()

        for pred in raw_preds:
            raw_label: str = pred["label"]
            confidence: float = pred["confidence"]

            # Bounding box: model returns [l, t, r, b] with top-left origin.
            # Convert to COCO [x, y, w, h] (top-left origin).
            left: float = pred["l"]
            top: float = pred["t"]
            right: float = pred["r"]
            bottom: float = pred["b"]

            coco_x = round(left, 2)
            coco_y = round(top, 2)
            coco_w = round(right - left, 2)
            coco_h = round(bottom - top, 2)

            canonical, doclaynet_label, _docling_key = _map_label(raw_label, taxonomy)
            canonical_set.add(canonical)

            detections.append(
                {
                    "class_name_raw": raw_label,
                    "class_name_canonical": canonical,
                    "class_name_doclaynet": doclaynet_label,
                    "bbox_coco_xywh": [coco_x, coco_y, coco_w, coco_h],
                    "confidence": round(confidence, 6),
                    "source_schema": "docling",
                }
            )

        result = ImageResult(
            image_id=image_id,
            image_path=image_path_rel,
            image_width=width,
            image_height=height,
            inference_time_ms=round(elapsed_ms, 2),
            detection_count=len(detections),
            detections=detections,
            content_flags_derived=_derive_content_flags(canonical_set),
        )
        results.append(result)

        log.info(
            "  -> %d detections in %.1f ms",
            len(detections),
            elapsed_ms,
        )

    return results


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(results: list[ImageResult]) -> None:
    """Print human-readable inference summary to stdout."""
    total = len(results)
    errored = sum(1 for r in results if r.error is not None)
    successful = total - errored

    all_confidences: list[float] = []
    all_times: list[float] = []
    class_counter: Counter[str] = Counter()
    content_flag_counter: Counter[str] = Counter()

    for res in results:
        if res.error is not None:
            continue
        all_times.append(res.inference_time_ms)
        for det in res.detections:
            all_confidences.append(det["confidence"])
            class_counter[det["class_name_canonical"]] += 1
        for flag_name, flag_val in res.content_flags_derived.items():
            if flag_val:
                content_flag_counter[flag_name] += 1

    total_detections = sum(class_counter.values())

    print("\n" + "=" * 65)
    print("  EGRET Inference Summary")
    print("=" * 65)
    print(f"  Total samples:       {total}")
    print(f"  Successful:          {successful}")
    print(f"  Errors:              {errored}")
    print(f"  Total detections:    {total_detections}")

    if all_confidences:
        avg_conf = sum(all_confidences) / len(all_confidences)
        min_conf = min(all_confidences)
        max_conf = max(all_confidences)
        print(f"  Avg confidence:      {avg_conf:.4f}")
        print(f"  Min confidence:      {min_conf:.4f}")
        print(f"  Max confidence:      {max_conf:.4f}")

    if all_times:
        avg_time = sum(all_times) / len(all_times)
        min_time = min(all_times)
        max_time = max(all_times)
        total_time = sum(all_times)
        print("\n  Timing (ms):")
        print(f"    Average:           {avg_time:.1f}")
        print(f"    Min:               {min_time:.1f}")
        print(f"    Max:               {max_time:.1f}")
        print(f"    Total:             {total_time:.1f}")

    if class_counter:
        print("\n  Class distribution:")
        for cls, count in class_counter.most_common():
            pct = count / total_detections * 100
            print(f"    {cls:<25s} {count:>4d}  ({pct:5.1f}%)")

    if content_flag_counter:
        print("\n  Content flags (images with flag=True):")
        for flag, count in content_flag_counter.most_common():
            print(f"    {flag:<25s} {count:>4d} / {successful}")

    if errored:
        print("\n  Errors:")
        for res in results:
            if res.error is not None:
                print(f"    {res.image_id}: {res.error}")

    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: parse args, run inference, write results."""
    parser = argparse.ArgumentParser(
        description="Run docling-layout-egret-xlarge on DIQA-5000 audit samples.",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="PyTorch device for inference (default: cuda).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Minimum confidence threshold (default: 0.3).",
    )
    parser.add_argument(
        "--sample-set",
        type=Path,
        default=SAMPLE_SET_PATH,
        help="Path to sample_set.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Path for output results JSON.",
    )
    args = parser.parse_args()

    # -- Load sample set --------------------------------------------------
    sample_set_path: Path = args.sample_set
    if not sample_set_path.is_file():
        log.error("Sample set not found: %s", sample_set_path)
        sys.exit(1)

    with open(sample_set_path) as fh:
        sample_data = json.load(fh)

    samples: list[dict[str, Any]] = sample_data["samples"]
    log.info("Loaded %d samples from %s", len(samples), sample_set_path)

    # -- Run inference ----------------------------------------------------
    results = run_inference(
        samples=samples,
        device=args.device,
        threshold=args.threshold,
    )

    # -- Serialize results ------------------------------------------------
    output_payload: dict[str, Any] = {
        "model": MODEL_REPO,
        "inference_device": args.device,
        "confidence_threshold": args.threshold,
        "total_samples": len(samples),
        "successful_samples": sum(1 for r in results if r.error is None),
        "results": [],
    }

    for res in results:
        entry: dict[str, Any] = {
            "image_id": res.image_id,
            "image_path": res.image_path,
            "image_width": res.image_width,
            "image_height": res.image_height,
            "inference_time_ms": res.inference_time_ms,
            "detection_count": res.detection_count,
            "detections": res.detections,
            "content_flags_derived": res.content_flags_derived,
        }
        if res.error is not None:
            entry["error"] = res.error
        output_payload["results"].append(entry)

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(output_payload, fh, indent=2)

    log.info("Results written to %s", output_path)

    # -- Print summary ----------------------------------------------------
    print_summary(results)


if __name__ == "__main__":
    main()
