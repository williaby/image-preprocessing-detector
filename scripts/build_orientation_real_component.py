#!/usr/bin/env python3
"""Build the real-document component of the orientation training dataset.

Downloads real document PDFs from GCS (DocLayNet, RVL-CDIP), renders each
page to an image, then creates 4 rotated copies (0°/90°/180°/270°).
Orientation labels are ground-truth exact because we apply the rotation
ourselves from a known upright base.

Source PDFs on GCS:
- DocLayNet: ``gs://image_detection_b/01_base_data/document_understanding/
  doclaynet/documents/``  (scientific, financial, legal, patent, manual domains)
- RVL-CDIP: ``gs://image_detection_b/01_base_data/document_understanding/
  rvlcdip/``  (administrative, financial, legal, medical domains, if available)

Target: ~30K images from ≥3 real document types, balanced across 4 orientations.
No single source may exceed 50% of the real component.

Output manifest records:
- ``image_path``: relative to output-dir (``images/{doc_id}_{page}_{deg}.jpg``)
- ``orientation``: int in {0, 90, 180, 270}
- ``provenance``: ``"real_born_digital"`` or ``"real_scan"``
- ``document_id``: source document identifier for deterministic split
- ``source_dataset``: dataset name (``"doclaynet"`` / ``"rvlcdip"``)
- ``domain``: DocLayNet domain label if available

Usage::

    # Default: DocLayNet only, 8K base docs → 32K images
    python scripts/build_orientation_real_component.py \\
        --output-dir /mnt/e/03_training_datasets/orientation_v2/real \\
        --sources doclaynet:8000 rvlcdip:3000 \\
        --target-size 224

    # Dry run: scan PDFs, report counts, skip rendering
    python scripts/build_orientation_real_component.py \\
        --output-dir /tmp/orient_real --dry-run --verbose

Requires: google-cloud-storage, PyMuPDF (fitz), opencv-python, numpy, tqdm
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# GCS paths for source PDFs
GCS_DOCLAYNET_PREFIX = (
    "01_base_data/document_understanding/doclaynet/documents"
)
GCS_RVLCDIP_PREFIX = (
    "01_base_data/document_understanding/rvlcdip"
)

# Rotation degrees for orientation labels
ROTATIONS = (0, 90, 180, 270)
# OpenCV rotation codes for each degree
_CV2_ROT = {
    0: None,
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}
DEFAULT_TARGET_SIZE = 224
DEFAULT_RENDER_DPI = 150  # Balance quality vs. memory
JPEG_QUALITY = 92

# DocLayNet domain → provenance tag (all are born_digital PDFs)
_DOCLAYNET_PROVENANCE = "real_born_digital"
_RVLCDIP_PROVENANCE = "real_scan"


class _SourceConfig(NamedTuple):
    """Configuration for a single PDF source dataset."""

    name: str
    gcs_prefix: str
    provenance: str
    max_base_docs: int


class _OrientResult(NamedTuple):
    """Output record for one orientation variant."""

    image_path: str
    orientation: int
    provenance: str
    document_id: str
    source_dataset: str
    domain: str


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def _get_gcs_bucket(bucket_name: str) -> Any:
    """Return a GCS Bucket client."""
    from google.cloud import storage  # type: ignore[import-untyped]

    return storage.Client().bucket(bucket_name)


def _parse_gcs_prefix(gcs_prefix: str) -> tuple[str, str]:
    """Split ``gs://bucket/prefix`` → ``(bucket_name, prefix)``."""
    if not gcs_prefix.startswith("gs://"):
        msg = f"Expected gs:// path, got: {gcs_prefix!r}"
        raise ValueError(msg)
    rest = gcs_prefix[5:]
    parts = rest.split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _list_pdf_blobs(bucket: Any, prefix: str) -> list[str]:
    """List all PDF blob keys under ``prefix``.

    Args:
        bucket: GCS Bucket client.
        prefix: GCS prefix to scan for ``.pdf`` files.

    Returns:
        Sorted list of GCS object keys (no ``gs://`` prefix).
    """
    blobs = bucket.list_blobs(prefix=prefix)
    keys = [b.name for b in blobs if b.name.lower().endswith(".pdf")]
    keys.sort()
    return keys


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------


def _render_pdf_page(pdf_bytes: bytes, page_idx: int, dpi: int) -> np.ndarray | None:
    """Render one page of a PDF to a BGR numpy array.

    Uses PyMuPDF (``fitz``). Returns None if PyMuPDF is unavailable or
    the page cannot be rendered.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_idx: 0-based page index to render.
        dpi: Render DPI.

    Returns:
        BGR uint8 numpy array, or None on failure.
    """
    try:
        import fitz  # type: ignore[import-untyped]  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) is required. Install with: pip install pymupdf")
        return None

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_idx >= len(doc):
            return None
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        rgb_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        return cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
    except Exception:
        logger.debug("Failed to render PDF page %d", page_idx, exc_info=True)
        return None


def _rotate_image(image: np.ndarray, degrees: int) -> np.ndarray:
    """Rotate image by exact degrees (0/90/180/270).

    Args:
        image: BGR numpy array.
        degrees: Rotation in degrees; must be in {0, 90, 180, 270}.

    Returns:
        Rotated image.
    """
    rot_code = _CV2_ROT.get(degrees)
    if rot_code is None:
        return image
    return cv2.rotate(image, rot_code)


def _resize_image(image: np.ndarray, target_size: int) -> np.ndarray:
    """Resize image so its longer side equals ``target_size``.

    Args:
        image: BGR numpy array.
        target_size: Target pixel count for the longer dimension.

    Returns:
        Resized image (INTER_AREA).
    """
    h, w = image.shape[:2]
    if max(h, w) == target_size:
        return image
    scale = target_size / max(h, w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# Document ID and split
# ---------------------------------------------------------------------------


def _make_document_id(blob_key: str, page_idx: int) -> str:
    """Create a stable document_id from blob key and page index.

    Args:
        blob_key: GCS object key.
        page_idx: Page index within the PDF.

    Returns:
        Deterministic hex document_id.
    """
    raw = f"{blob_key}:page{page_idx}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Processing one PDF page
# ---------------------------------------------------------------------------


def _process_pdf_page(
    blob_key: str,
    bucket: Any,
    page_idx: int,
    source: _SourceConfig,
    target_size: int,
    images_dir: Path,
    dry_run: bool,
) -> list[_OrientResult]:
    """Render one PDF page and save 4 rotated variants.

    Args:
        blob_key: GCS key for the PDF.
        bucket: GCS Bucket client.
        page_idx: Page to render.
        source: Source dataset configuration.
        target_size: Output image size (px on longer side).
        images_dir: Output directory for images.
        dry_run: Skip GCS download and write if True.

    Returns:
        List of 4 ``_OrientResult`` records (one per orientation).
    """
    doc_id = _make_document_id(blob_key, page_idx)
    results: list[_OrientResult] = []

    if not dry_run:
        pdf_bytes = bucket.blob(blob_key).download_as_bytes()
        base_image = _render_pdf_page(pdf_bytes, page_idx, DEFAULT_RENDER_DPI)
        if base_image is None:
            return results
        base_image = _resize_image(base_image, target_size)

    for deg in ROTATIONS:
        out_name = f"{doc_id}_p{page_idx}_{deg}.jpg"
        rel_path = f"images/{out_name}"
        out_path = images_dir / out_name

        if not dry_run:
            rotated = _rotate_image(base_image, deg)  # type: ignore[possibly-undefined]
            ok, buf = cv2.imencode(".jpg", rotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if ok:
                out_path.write_bytes(buf.tobytes())

        # Extract DocLayNet domain from blob key path structure if possible
        domain = _extract_domain(blob_key, source.name)
        results.append(
            _OrientResult(
                image_path=rel_path,
                orientation=deg,
                provenance=source.provenance,
                document_id=doc_id,
                source_dataset=source.name,
                domain=domain,
            )
        )

    return results


def _extract_domain(blob_key: str, source_name: str) -> str:
    """Extract domain label from blob key structure.

    DocLayNet blobs may contain the domain in the path:
    ``...doclaynet/documents/scientific/...`` → ``"scientific"``.

    Args:
        blob_key: GCS object key.
        source_name: Dataset name (``"doclaynet"`` or ``"rvlcdip"``).

    Returns:
        Domain string, or ``"unknown"`` if not parseable.
    """
    if source_name == "doclaynet":
        # Attempt to extract domain from path like "...documents/financial/doc.pdf"
        parts = blob_key.replace("\\", "/").split("/")
        try:
            doc_idx = parts.index("documents")
            if doc_idx + 1 < len(parts) - 1:
                return parts[doc_idx + 1]
        except ValueError:
            pass
    return "unknown"


# ---------------------------------------------------------------------------
# Source setup helpers
# ---------------------------------------------------------------------------


def _parse_source_specs(raw_specs: list[str]) -> dict[str, int]:
    """Parse ``dataset:max_docs`` source specs from CLI args.

    Args:
        raw_specs: List of strings like ``["doclaynet:8000", "rvlcdip:3000"]``.

    Returns:
        Mapping from dataset name to max base doc count.
    """
    result: dict[str, int] = {}
    for spec in raw_specs:
        if ":" in spec:
            name, count_str = spec.rsplit(":", 1)
            try:
                result[name.strip()] = int(count_str.strip())
            except ValueError:
                logger.warning("Invalid source spec %r — skipping", spec)
        else:
            # No count given → no cap
            result[spec.strip()] = 999_999
    return result


def _build_source_configs(
    source_specs: dict[str, int],
    bucket_name: str,
) -> list[_SourceConfig]:
    """Build list of source configurations from CLI specs.

    Args:
        source_specs: Dataset name → max base doc count mapping.
        bucket_name: GCS bucket containing the PDFs.

    Returns:
        List of ``_SourceConfig`` objects.
    """
    configs: list[_SourceConfig] = []
    name_to_prefix = {
        "doclaynet": GCS_DOCLAYNET_PREFIX,
        "rvlcdip": GCS_RVLCDIP_PREFIX,
    }
    name_to_provenance = {
        "doclaynet": _DOCLAYNET_PROVENANCE,
        "rvlcdip": _RVLCDIP_PROVENANCE,
    }
    for name, max_docs in source_specs.items():
        if name not in name_to_prefix:
            logger.warning("Unknown source dataset %r — skipping", name)
            continue
        configs.append(
            _SourceConfig(
                name=name,
                gcs_prefix=name_to_prefix[name],
                provenance=name_to_provenance[name],
                max_base_docs=max_docs,
            )
        )
    return configs


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def _check_mixing_cap(results: list[_OrientResult], max_single_source_pct: float) -> None:
    """Warn if any single source exceeds the mixing cap.

    Args:
        results: All output records produced so far.
        max_single_source_pct: Maximum fraction from any single source (0–1).
    """
    total = len(results)
    if total == 0:
        return
    source_counts: dict[str, int] = {}
    for r in results:
        source_counts[r.source_dataset] = source_counts.get(r.source_dataset, 0) + 1
    for src, count in source_counts.items():
        frac = count / total
        if frac > max_single_source_pct:
            logger.warning(
                "SOURCE CAP EXCEEDED: %s contributes %.1f%% (cap: %.0f%%)",
                src,
                frac * 100,
                max_single_source_pct * 100,
            )


def run_build(args: argparse.Namespace) -> int:
    """Run the real orientation component build pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success).
    """
    _setup_logging(args.verbose)
    rng = random.Random(args.seed)
    start = time.time()

    bucket_name, _ = _parse_gcs_prefix(args.gcs_bucket_root)
    bucket = _get_gcs_bucket(bucket_name)

    source_specs = _parse_source_specs(args.sources)
    if not source_specs:
        logger.error("No valid source specs provided.")
        return 1

    source_configs = _build_source_configs(source_specs, bucket_name)
    if not source_configs:
        logger.error("No valid source configs after filtering.")
        return 1

    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    if not args.dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[_OrientResult] = []
    errors = 0

    for source in source_configs:
        logger.info("Processing source: %s (max_base_docs=%d)", source.name, source.max_base_docs)
        pdf_keys = _list_pdf_blobs(bucket, source.gcs_prefix)

        if not pdf_keys:
            logger.warning("No PDFs found at gs://%s/%s", bucket_name, source.gcs_prefix)
            continue

        logger.info("Found %d PDFs for %s", len(pdf_keys), source.name)

        # Sample base documents (one page per PDF to avoid domain bias)
        rng.shuffle(pdf_keys)
        selected_keys = pdf_keys[: source.max_base_docs]

        try:
            from tqdm import tqdm  # type: ignore[import-untyped]
            progress: Any = tqdm(selected_keys, desc=f"Real orient ({source.name})", unit="pdf")
        except ImportError:
            progress = selected_keys

        for blob_key in progress:
            try:
                page_results = _process_pdf_page(
                    blob_key=blob_key,
                    bucket=bucket,
                    page_idx=0,  # first page of each PDF
                    source=source,
                    target_size=args.target_size,
                    images_dir=images_dir,
                    dry_run=args.dry_run,
                )
                all_results.extend(page_results)
            except Exception:
                logger.exception("Failed on %s", blob_key)
                errors += 1

    elapsed = time.time() - start
    throughput = len(all_results) / elapsed if elapsed > 0 else 0.0

    # Mixing cap check (50% per source max)
    _check_mixing_cap(all_results, max_single_source_pct=0.5)

    # Orientation balance check
    orient_counts: dict[int, int] = {}
    for r in all_results:
        orient_counts[r.orientation] = orient_counts.get(r.orientation, 0) + 1
    logger.info("Orientation distribution: %s", orient_counts)

    manifest_path = output_dir / "orientation_real_metadata.json"
    manifest_records = [
        {
            "image_path": r.image_path,
            "orientation": r.orientation,
            "provenance": r.provenance,
            "document_id": r.document_id,
            "source_dataset": r.source_dataset,
            "domain": r.domain,
        }
        for r in all_results
    ]

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest_records, f, indent=2)

    source_counts: dict[str, int] = {}
    for r in all_results:
        source_counts[r.source_dataset] = source_counts.get(r.source_dataset, 0) + 1

    logger.info(
        "Done: %d images (%d 4-rotation sets), %d errors | %.1fs | %.1f img/s",
        len(all_results),
        len(all_results) // 4,
        errors,
        elapsed,
        throughput,
    )
    logger.info("Source distribution: %s", source_counts)
    if not args.dry_run:
        logger.info("Manifest: %s", manifest_path)

    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Build real-document orientation component from DocLayNet/RVL-CDIP PDFs on GCS. "
            "Each PDF page is rendered then rotated 0/90/180/270° to produce exact orientation labels."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--gcs-bucket-root",
        type=str,
        default="gs://image_detection_b",
        help="GCS root URI (bucket only). Default: gs://image_detection_b",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for rendered images and orientation_real_metadata.json.",
    )
    parser.add_argument(
        "--sources",
        type=str,
        nargs="+",
        default=["doclaynet:8000", "rvlcdip:3000"],
        help=(
            "Source datasets with max base-doc counts. "
            "Format: 'name:count' e.g. 'doclaynet:8000 rvlcdip:3000'. "
            "Supported: doclaynet, rvlcdip."
        ),
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=DEFAULT_TARGET_SIZE,
        help=f"Resize longer side to this many pixels (default: {DEFAULT_TARGET_SIZE}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for PDF shuffling (default: 42).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List PDFs and report counts without downloading or rendering.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return run_build(args)


if __name__ == "__main__":
    sys.exit(main())
