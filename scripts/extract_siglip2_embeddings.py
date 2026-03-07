#!/usr/bin/env python3
"""Extract SigLIP2 penultimate-layer embeddings for OOD detector fitting.

Runs SigLIP2MultiTaskDetector.predict(return_embedding=True) on a dataset
and saves the 768-dim embeddings as a numpy array for Mahalanobis OOD fitting.

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/extract_siglip2_embeddings.py \
        --checkpoint models/siglip2_multitask/best_model.pt \
        --meta-path /path/to/diqa-5000/metas/train.json \
        --image-root /path/to/diqa-5000/images/ \
        --output results/embeddings/diqa5000_train.npy

    # Then fit OOD detector:
    uv run python3 scripts/extract_siglip2_embeddings.py \
        --fit-ood results/embeddings/diqa5000_train.npy \
        --ood-output models/ood/ood_params.npz
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def extract_embeddings(
    checkpoint_path: str,
    meta_path: str,
    image_root: str,
    output_path: str,
    device: str = "cuda:0",
    limit: int | None = None,
) -> np.ndarray:
    """Extract embeddings for all images in a metadata file.

    Args:
        checkpoint_path: Path to SigLIP2 multitask checkpoint.
        meta_path: Path to dataset metadata JSON.
        image_root: Root directory for images.
        output_path: Output path for .npy embeddings.
        device: Device for inference.
        limit: Optional limit on number of images.

    Returns:
        Embeddings array (n_images, 768).
    """
    from image_preprocessing_detector.detection.siglip2_multitask import (
        SigLIP2MultiTaskConfig,
        SigLIP2MultiTaskDetector,
    )

    # Load metadata
    with open(meta_path) as f:
        metadata = json.load(f)

    if limit:
        metadata = metadata[:limit]

    log.info("Loaded %d images from %s", len(metadata), meta_path)

    # Initialize detector
    config = SigLIP2MultiTaskConfig(device=device)
    detector = SigLIP2MultiTaskDetector(
        checkpoint_path=checkpoint_path,
        config=config,
    )

    embeddings = []
    image_ids = []

    for idx, item in enumerate(metadata):
        img_id = item.get("image", item.get("img_path", ""))
        img_path = str(Path(image_root) / img_id)

        if idx % 100 == 0:
            log.info("[%d/%d] Processing %s", idx, len(metadata), img_id)

        image = cv2.imread(img_path)
        if image is None:
            log.warning("Failed to read: %s", img_path)
            continue

        result = detector.predict(image, return_embedding=True)
        if result.embedding is not None:
            embeddings.append(result.embedding)
            image_ids.append(img_id)

    if not embeddings:
        log.error("No embeddings extracted; all image reads or predictions failed")
        sys.exit(1)

    embeddings_arr = np.stack(embeddings, axis=0)
    log.info(
        "Extracted %d embeddings, shape: %s", len(embeddings), embeddings_arr.shape
    )

    # Save
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_path, embeddings_arr)
    log.info("Saved embeddings to %s", output_path)

    # Save image IDs alongside
    ids_path = str(output_path).replace(".npy", "_ids.json")
    with open(ids_path, "w") as f:
        json.dump(image_ids, f, indent=2)
    log.info("Saved image IDs to %s", ids_path)

    return embeddings_arr


def fit_ood_detector(
    embeddings_path: str,
    output_path: str,
    threshold_percentile: float = 95.0,
) -> None:
    """Fit OOD detector from pre-extracted embeddings.

    Args:
        embeddings_path: Path to .npy embeddings.
        output_path: Output path for OOD params .npz.
        threshold_percentile: Percentile for OOD threshold.
    """
    from image_preprocessing_detector.detection.ood_detector import (
        EmbeddingOODDetector,
    )

    embeddings = np.load(embeddings_path)
    log.info("Loaded embeddings: %s", embeddings.shape)

    if embeddings.shape[0] == 0:
        log.error("Embeddings array is empty; cannot fit OOD detector")
        sys.exit(1)

    detector = EmbeddingOODDetector.from_embeddings(
        embeddings, threshold_percentile=threshold_percentile
    )

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    detector.save(output_path)
    log.info("OOD detector saved to %s", output_path)

    # Report statistics
    results = detector.score_batch(embeddings)
    distances = np.array([r.mahalanobis_distance for r in results])
    n_flagged = sum(1 for r in results if r.is_ood)
    log.info(
        "Calibration stats: median=%.2f, p95=%.2f, p99=%.2f, flagged=%d/%d (%.1f%%)",
        np.median(distances),
        np.percentile(distances, 95),
        np.percentile(distances, 99),
        n_flagged,
        len(results),
        100 * n_flagged / len(results),
    )


def main() -> None:
    """Extract embeddings and/or fit OOD detector."""
    parser = argparse.ArgumentParser(
        description="Extract SigLIP2 embeddings for OOD detection"
    )

    # Extraction args
    parser.add_argument("--checkpoint", type=str, help="SigLIP2 checkpoint path")
    parser.add_argument("--meta-path", type=str, help="Dataset metadata JSON")
    parser.add_argument("--image-root", type=str, help="Image root directory")
    parser.add_argument("--output", type=str, help="Output .npy path for embeddings")
    parser.add_argument("--device", type=str, default="cuda:0", help="Inference device")
    parser.add_argument(
        "--limit", type=int, default=None, help="Image limit (for testing)"
    )

    # OOD fitting args
    parser.add_argument(
        "--fit-ood", type=str, help="Path to embeddings .npy to fit OOD from"
    )
    parser.add_argument(
        "--ood-output", type=str, help="Output .npz path for OOD params"
    )
    parser.add_argument(
        "--threshold-pct", type=float, default=95.0, help="OOD threshold percentile"
    )

    args = parser.parse_args()

    if args.checkpoint and args.meta_path and args.image_root and args.output:
        extract_embeddings(
            checkpoint_path=args.checkpoint,
            meta_path=args.meta_path,
            image_root=args.image_root,
            output_path=args.output,
            device=args.device,
            limit=args.limit,
        )

    if args.fit_ood and args.ood_output:
        fit_ood_detector(
            embeddings_path=args.fit_ood,
            output_path=args.ood_output,
            threshold_percentile=args.threshold_pct,
        )

    if not any([args.checkpoint, args.fit_ood]):
        parser.print_help()


if __name__ == "__main__":
    main()
