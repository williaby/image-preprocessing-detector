# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Docling Layout Egret provider for document layout detection.

This module provides a docling-layout-egret-xlarge enrichment provider
for high-quality document layout detection. Uses the LayoutPredictor
from docling-ibm-models with the egret-xlarge model from HuggingFace.

The model outputs 17 classes (11 DocLayNet standard + 6 Docling extended).
Bounding boxes are converted to COCO xywh format.

Classes:
    DoclingLayoutProvider: Egret-based layout detection provider

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.docling_layout import (
    ...     DoclingLayoutProvider,
    ... )
    >>>
    >>> provider = DoclingLayoutProvider(confidence_threshold=0.3)
    >>> if provider.is_available():
    ...     enrichment = provider.enrich(Path("document.jpg"))
    ...     print(f"Found {len(enrichment.layout_detections)} elements")
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from ...schemas.enrichment import EnrichmentData
from ..errors import InferenceError, ProviderUnavailableError

logger = logging.getLogger(__name__)

# Model outputs labels in PascalCase; we map to docling schema keys
# for taxonomy conversion.
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

# Canonical classes that set content flags
_TABLE_CLASSES = {"TABLE"}
_FORMULA_CLASSES = {"FORMULA"}
_FIGURE_CLASSES = {"PICTURE", "CHART"}
_CODE_CLASSES = {"CODE"}


class DoclingLayoutProvider:
    """Docling Layout Egret provider for document layout detection.

    Wraps the docling-ibm-models LayoutPredictor with the
    ds4sd/docling-layout-egret-xlarge model for high-quality layout
    detection across 17 document element classes.

    Attributes:
        model_repo: HuggingFace model repository ID
        confidence_threshold: Minimum confidence for detections (0.0-1.0)
        batch_size: Batch size for processing (sequential per-image)
        device: Device to use ("cuda", "cpu", or None for auto-detect)
    """

    MODEL_REPO = "ds4sd/docling-layout-egret-xlarge"

    def __init__(
        self,
        confidence_threshold: float = 0.3,
        batch_size: int = 1,
        device: str | None = None,
    ):
        """Initialize DoclingLayoutProvider.

        Args:
            confidence_threshold: Minimum detection confidence (default: 0.3)
            batch_size: Number of images per batch (default: 1, sequential)
            device: Device to use (None for auto-detect, "cuda" or "cpu")
        """
        self.confidence_threshold = confidence_threshold
        self.batch_size = batch_size
        self._device = device
        self._predictor: Any | None = None
        self._model_path: str | None = None
        self._taxonomy: Any | None = None
        self._device_available: bool | None = None

    @property
    def name(self) -> str:
        """Provider name for logging and provenance."""
        return "docling_layout_egret_xlarge"

    @property
    def tier(self) -> str:
        """Enrichment tier (tier_2_model for ML inference)."""
        return "tier_2_model"

    @property
    def device(self) -> str:
        """Get device for inference (auto-detect if not specified)."""
        if self._device is not None:
            return self._device

        try:
            import torch

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self._device = "cpu"

        return self._device

    def is_available(self) -> bool:
        """Check if egret model dependencies are available.

        Checks:
        - docling_ibm_models package installed
        - huggingface_hub for model download
        - PIL for image loading
        - torch + CUDA if device is "cuda"

        Returns:
            True if provider can be used
        """
        if self._device_available is not None:
            return self._device_available

        try:
            import docling_ibm_models.layoutmodel.layout_predictor  # noqa: F401
            import huggingface_hub  # noqa: F401
            import PIL  # noqa: F401
        except ImportError as e:
            logger.debug("Missing dependency for DoclingLayoutProvider: %s", e)
            self._device_available = False
            return False

        if self.device == "cuda":
            try:
                import torch

                if not torch.cuda.is_available():
                    logger.debug("CUDA requested but not available")
                    self._device_available = False
                    return False
            except ImportError:
                logger.debug("torch not installed")
                self._device_available = False
                return False

        self._device_available = True
        return True

    def supports(self, _image_path: Path) -> bool:
        """Check if this image should be processed.

        Args:
            _image_path: Path to image file (unused)

        Returns:
            True (processes all images by default)
        """
        return True

    def _ensure_loaded(self) -> None:
        """Lazy-load egret model on first use.

        Downloads model from HuggingFace if not cached, then
        initializes the LayoutPredictor.

        Raises:
            ProviderUnavailableError: If model cannot be loaded
        """
        if self._predictor is not None:
            return

        if not self.is_available():
            raise ProviderUnavailableError(
                self.name, "Required dependencies not installed"
            )

        try:
            from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
            from huggingface_hub import snapshot_download

            logger.info("Downloading/resolving model %s ...", self.MODEL_REPO)
            self._model_path = snapshot_download(self.MODEL_REPO)
            logger.info("Model artifacts at: %s", self._model_path)

            logger.info(
                "Loading LayoutPredictor on device=%s, threshold=%.2f ...",
                self.device,
                self.confidence_threshold,
            )
            self._predictor = LayoutPredictor(
                artifact_path=self._model_path,
                device=self.device,
                base_threshold=self.confidence_threshold,
            )
            logger.info("Egret model loaded: %s", self._predictor.info())

            # Warmup pass to stabilize GPU timing
            from PIL import Image as PILImage

            warmup = PILImage.new("RGB", (640, 640), color=(255, 255, 255))
            list(self._predictor.predict(warmup))
            logger.info("Warmup complete.")

        except Exception as e:
            raise ProviderUnavailableError(
                self.name, f"Model loading failed: {e}"
            ) from e

    def _get_taxonomy(self) -> Any:
        """Lazily load LayoutTaxonomy for label mapping."""
        if self._taxonomy is not None:
            return self._taxonomy

        from image_preprocessing_detector.schema_utils.layout_taxonomy import (
            LayoutTaxonomy,
        )

        self._taxonomy = LayoutTaxonomy()
        return self._taxonomy

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image with layout detection.

        Args:
            image_path: Path to image file

        Returns:
            EnrichmentData with layout_detections and content flags populated

        Raises:
            InferenceError: If inference fails
            ProviderUnavailableError: If provider is not available
        """
        return self.enrich_batch([image_path])[0]

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images with layout detection.

        Args:
            image_paths: List of image file paths

        Returns:
            List of EnrichmentData in same order as image_paths

        Raises:
            InferenceError: If batch inference fails
            ProviderUnavailableError: If provider is not available
        """
        if not image_paths:
            return []

        self._ensure_loaded()

        results: list[EnrichmentData] = []
        for path in image_paths:
            try:
                enrichment = self._process_single(path)
                results.append(enrichment)
            except Exception as e:
                logger.exception("Egret inference failed for %s", path)
                raise InferenceError(self.name, 1, e) from e

        return results

    def _process_single(self, image_path: Path) -> EnrichmentData:
        """Process a single image through egret.

        Args:
            image_path: Path to image file

        Returns:
            EnrichmentData with layout detections
        """
        from PIL import Image as PILImage

        assert self._predictor is not None

        img = PILImage.open(image_path).convert("RGB")

        start_ns = time.perf_counter_ns()
        raw_preds = list(self._predictor.predict(img))
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

        taxonomy = self._get_taxonomy()
        detections, canonical_classes = self._convert_predictions(raw_preds, taxonomy)

        logger.debug(
            "%s: %d detections in %.1fms",
            image_path.name,
            len(detections),
            elapsed_ms,
        )

        enrichment = EnrichmentData()
        enrichment.layout_detections = detections

        # Derive content flags from detected classes
        enrichment.has_table = bool(canonical_classes & _TABLE_CLASSES)
        enrichment.has_formula = bool(canonical_classes & _FORMULA_CLASSES)
        enrichment.has_figure = bool(canonical_classes & _FIGURE_CLASSES)

        return enrichment

    def _convert_predictions(
        self,
        raw_preds: list[dict[str, Any]],
        taxonomy: Any,
    ) -> tuple[list[dict[str, Any]], set[str]]:
        """Convert raw model predictions to standardized detections.

        The model returns predictions with keys: label, confidence, l, t, r, b
        (left, top, right, bottom with top-left origin).

        We convert to COCO xywh format and map labels via LayoutTaxonomy.

        Args:
            raw_preds: List of prediction dicts from LayoutPredictor
            taxonomy: LayoutTaxonomy instance for label mapping

        Returns:
            Tuple of (detection_list, set_of_canonical_classes)
        """
        detections: list[dict[str, Any]] = []
        canonical_classes: set[str] = set()

        for pred in raw_preds:
            raw_label: str = pred["label"]
            confidence: float = pred["confidence"]

            # Convert bbox: model returns [l, t, r, b] top-left origin
            # -> COCO [x, y, w, h] top-left origin
            left: float = pred["l"]
            top: float = pred["t"]
            right: float = pred["r"]
            bottom: float = pred["b"]

            bbox = [
                round(left, 2),
                round(top, 2),
                round(right - left, 2),
                round(bottom - top, 2),
            ]

            # Map label through taxonomy
            docling_key = _MODEL_LABEL_TO_DOCLING.get(raw_label)
            if docling_key is None:
                docling_key = raw_label.lower().replace("-", "_").replace(" ", "_")

            try:
                canonical = taxonomy.to_canonical(docling_key, "docling")
            except Exception:
                canonical = "UNKNOWN"

            try:
                doclaynet_label = taxonomy.to_doclaynet(canonical)
            except Exception:
                doclaynet_label = raw_label

            canonical_classes.add(canonical)

            detection = {
                "class_name": doclaynet_label,
                "class_name_canonical": canonical,
                "bbox": bbox,
                "confidence": round(confidence, 6),
                "source": self.name,
                "source_schema": "docling",
            }
            detections.append(detection)

        return detections, canonical_classes


__all__ = ["DoclingLayoutProvider"]
