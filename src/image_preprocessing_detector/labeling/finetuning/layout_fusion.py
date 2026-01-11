# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Layout Fusion Downsampler for IQA training with semantic layout masks.

This module implements the Layout Fusion Downsampler architecture from the
original DocIQ paper, designed to handle 1600x1600 document images for models
that require smaller input sizes (e.g., 400x400 for ResNet).

**IMPORTANT - USAGE FOR ALL IQA TRAINING:**
This module MUST be used for ALL IQA-based training where the model cannot
accept the full 1600x1600 image resolution. The Layout Fusion Downsampler:

1. Preserves semantic layout information during downsampling
2. Fuses RGB image features with 11-class layout masks
3. Enables document-aware quality assessment
4. Maintains alignment with the original DocIQ paper architecture

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │              Layout Fusion Downsampler                   │
    ├─────────────────────────────────────────────────────────┤
    │                                                          │
    │  RGB Image [B, 3, 1600, 1600]                           │
    │         │                                                │
    │         ▼                                                │
    │  ┌─────────────────┐                                     │
    │  │  RGB Encoder    │  Conv 7x7 s4 → Conv 3x3 s1         │
    │  │  (3 → 64 ch)    │                                    │
    │  └────────┬────────┘                                     │
    │           │ [B, 64, 400, 400]                           │
    │           │                                              │
    │           ▼                                              │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │              Concatenate                         │    │
    │  │         [B, 128, 400, 400]                       │    │
    │  └─────────────────────────────────────────────────┘    │
    │           ▲                                              │
    │           │ [B, 64, 400, 400]                           │
    │  ┌────────┴────────┐                                     │
    │  │ Layout Encoder  │  Conv 3x3 s2 → Conv 3x3 s2         │
    │  │ (11 → 64 ch)    │                                    │
    │  └─────────────────┘                                     │
    │         ▲                                                │
    │  Layout Mask [B, 11, 1600, 1600]                        │
    │                                                          │
    │  Fused output: [B, 3, 400, 400] (ResNet-compatible)     │
    └─────────────────────────────────────────────────────────┘

Layout Mask Classes (11 DocLayNet classes):
    0: Caption
    1: Footnote
    2: Formula
    3: List-Item
    4: Page-Footer
    5: Page-Header
    6: Picture
    7: Section-Header
    8: Table
    9: Text
    10: Title

Reference:
    - DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3
    - Original DocIQ paper architecture

Example:
    >>> from image_preprocessing_detector.labeling.finetuning import (
    ...     LayoutFusionDownsampler,
    ...     LayoutMaskGenerator,
    ...     DocIQReplica,
    ... )
    >>>
    >>> # For training DocIQ-Replica (Generalist Anchor)
    >>> downsampler = LayoutFusionDownsampler()
    >>> mask_generator = LayoutMaskGenerator()
    >>>
    >>> # Generate layout mask
    >>> layout_mask = mask_generator.generate_mask(image)
    >>>
    >>> # Fuse RGB with layout for ResNet input
    >>> rgb_tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
    >>> layout_tensor = torch.from_numpy(layout_mask).unsqueeze(0)
    >>> fused = downsampler(rgb_tensor, layout_tensor)
    >>> # fused: [1, 3, 400, 400] - ready for ResNet backbone
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np
import structlog
import torch
import torch.nn as nn
from torch.nn import functional as nn_func

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


# DocLayNet class names for reference
DOCLAYNET_CLASSES: list[str] = [
    "Caption",
    "Footnote",
    "Formula",
    "List-Item",
    "Page-Footer",
    "Page-Header",
    "Picture",
    "Section-Header",
    "Table",
    "Text",
    "Title",
]

N_LAYOUT_CLASSES: int = 11


@dataclass
class LayoutFusionConfig:
    """Configuration for Layout Fusion Downsampler.

    Attributes:
        n_layout_classes: Number of layout classes (default 11 for DocLayNet).
        input_size: Expected input image size (default 1600x1600).
        output_size: Output size after downsampling (default 400x400).
        layout_channels: Intermediate channels for layout encoder.
        rgb_channels: Intermediate channels for RGB encoder.
        fusion_channels: Channels before final fusion to 3.
    """

    n_layout_classes: int = 11
    input_size: int = 1600
    output_size: int = 400
    layout_channels: int = 64
    rgb_channels: int = 64
    fusion_channels: int = 64


class LayoutFusionDownsampler(nn.Module):
    """Fuses RGB image with semantic layout masks.

    Matches DocIQ paper architecture: downsamples 1600x1600 input
    while incorporating 11-class layout mask information.

    This module is REQUIRED for all IQA training where the backbone
    model cannot accept the full 1600x1600 document image resolution.
    It preserves semantic layout information during downsampling,
    enabling document-aware quality assessment.

    The architecture:
    1. RGB Encoder: Downsamples RGB image while extracting features
       - Conv 7x7 stride 4: [B, 3, 1600, 1600] → [B, 32, 400, 400]
       - Conv 3x3 stride 1: [B, 32, 400, 400] → [B, 64, 400, 400]

    2. Layout Encoder: Encodes and downsamples layout mask
       - Conv 3x3 stride 2: [B, 11, 1600, 1600] → [B, 32, 800, 800]
       - Conv 3x3 stride 2: [B, 32, 800, 800] → [B, 64, 400, 400]

    3. Fusion Layer: Combines RGB and layout features
       - Concatenate: [B, 128, 400, 400]
       - Conv 1x1: [B, 128, 400, 400] → [B, 64, 400, 400]
       - Conv 1x1: [B, 64, 400, 400] → [B, 3, 400, 400]

    Example:
        >>> downsampler = LayoutFusionDownsampler()
        >>> rgb = torch.randn(4, 3, 1600, 1600)
        >>> layout = torch.randn(4, 11, 1600, 1600)  # one-hot masks
        >>> fused = downsampler(rgb, layout)
        >>> print(fused.shape)  # torch.Size([4, 3, 400, 400])

    Note:
        - Input RGB should be normalized to [0, 1] or [-1, 1]
        - Layout mask should be one-hot encoded [B, 11, H, W]
        - Output is suitable for ResNet or similar backbones
    """

    def __init__(
        self,
        config: LayoutFusionConfig | None = None,
        n_layout_classes: int | None = None,
    ) -> None:
        """Initialize Layout Fusion Downsampler.

        Args:
            config: Full configuration object.
            n_layout_classes: Number of layout classes (default 11).
                             Ignored if config is provided.
        """
        super().__init__()

        if config is None:
            config = LayoutFusionConfig(
                n_layout_classes=n_layout_classes or N_LAYOUT_CLASSES
            )
        self.config = config

        # Layout mask encoder (11 classes → 64 channels)
        # Two conv layers with stride 2 each = 4x downsampling
        self.layout_encoder = nn.Sequential(
            nn.Conv2d(config.n_layout_classes, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, config.layout_channels, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(config.layout_channels),
            nn.ReLU(inplace=True),
        )

        # RGB encoder (3 → 64 channels, matching layout spatial dims)
        # Conv 7x7 stride 4 achieves same 4x downsampling in one step
        self.rgb_encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=7, stride=4, padding=3),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, config.rgb_channels, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(config.rgb_channels),
            nn.ReLU(inplace=True),
        )

        # Fusion layer (64 + 64 → 3 for ResNet input)
        fusion_input_channels = config.layout_channels + config.rgb_channels
        self.fusion = nn.Sequential(
            nn.Conv2d(fusion_input_channels, config.fusion_channels, kernel_size=1),
            nn.BatchNorm2d(config.fusion_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(config.fusion_channels, 3, kernel_size=1),
        )

        self._init_weights()

        logger.info(
            "layout_fusion_downsampler_initialized",
            n_layout_classes=config.n_layout_classes,
            input_size=config.input_size,
            output_size=config.output_size,
        )

    def _init_weights(self) -> None:
        """Initialize weights using Kaiming initialization."""
        for module in self.modules():
            if isinstance(module, nn.Conv2d):
                nn.init.kaiming_normal_(
                    module.weight, mode="fan_out", nonlinearity="relu"
                )
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.BatchNorm2d):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(
        self,
        rgb: torch.Tensor,
        layout: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass: fuse RGB image with layout mask.

        Args:
            rgb: RGB image tensor of shape [B, 3, 1600, 1600].
                 Should be normalized (e.g., ImageNet normalization).
            layout: Layout mask tensor of shape [B, 11, 1600, 1600].
                    Should be one-hot encoded (each pixel has exactly
                    one class active, or all zeros for background).

        Returns:
            Fused tensor of shape [B, 3, 400, 400], suitable for
            ResNet or similar backbone networks.

        Raises:
            ValueError: If input shapes are invalid.
        """
        # Validate input shapes
        if rgb.dim() != 4 or rgb.shape[1] != 3:
            raise ValueError(f"Expected RGB shape [B, 3, H, W], got {rgb.shape}")
        if layout.dim() != 4 or layout.shape[1] != self.config.n_layout_classes:
            raise ValueError(
                f"Expected layout shape [B, {self.config.n_layout_classes}, H, W], "
                f"got {layout.shape}"
            )

        # Encode RGB and layout
        rgb_feat = self.rgb_encoder(rgb)  # [B, 64, H/4, W/4]
        layout_feat = self.layout_encoder(layout)  # [B, 64, H/4, W/4]

        # Handle potential size mismatch (if input isn't exactly 1600x1600)
        if rgb_feat.shape[2:] != layout_feat.shape[2:]:
            # Resize layout features to match RGB
            layout_feat = nn_func.interpolate(
                layout_feat,
                size=rgb_feat.shape[2:],
                mode="bilinear",
                align_corners=False,
            )

        # Concatenate and fuse
        fused = torch.cat([rgb_feat, layout_feat], dim=1)  # [B, 128, H/4, W/4]
        output: torch.Tensor = self.fusion(fused)  # [B, 3, H/4, W/4]
        return output

    def get_output_size(self, input_size: int = 1600) -> int:
        """Calculate output spatial size for a given input size.

        Args:
            input_size: Input image size (assumes square).

        Returns:
            Output spatial size (e.g., 400 for input 1600).
        """
        # RGB encoder uses 7x7 conv stride 4 with padding 3
        # Output size calculates as: (1600 + 6 - 7) / 4 + 1 = 400
        return (input_size + 6 - 7) // 4 + 1


@dataclass
class LayoutMaskGeneratorConfig:
    """Configuration for Layout Mask Generator.

    Attributes:
        model_path: Path or HuggingFace ID for DocLayout-YOLO model.
        target_size: Target size for masks (default 1600x1600).
        n_classes: Number of layout classes (default 11).
        confidence_threshold: Detection confidence threshold.
        cache_dir: Optional directory for caching generated masks.
        device: Device for inference ("cuda", "cpu", or None for auto).
    """

    model_path: str = "juliozhao/DocLayout-YOLO-DocStructBench"
    target_size: tuple[int, int] = (1600, 1600)
    n_classes: int = 11
    confidence_threshold: float = 0.25
    cache_dir: str | None = None
    device: str | None = None


class LayoutMaskGenerator:
    """Generates 11-class layout masks using DocLayout-YOLO.

    This class integrates with the existing DocLayoutYOLODetector to
    generate semantic layout masks for the Layout Fusion Downsampler.

    Classes (DocLayNet 11):
        0: Caption
        1: Footnote
        2: Formula
        3: List-Item
        4: Page-Footer
        5: Page-Header
        6: Picture
        7: Section-Header
        8: Table
        9: Text
        10: Title

    The generator produces one-hot encoded masks where each pixel
    belongs to at most one class. Overlapping detections use the
    higher-confidence prediction.

    Example:
        >>> generator = LayoutMaskGenerator()
        >>> mask = generator.generate_mask(image)
        >>> print(mask.shape)  # (11, 1600, 1600)
        >>>
        >>> # With caching for training datasets
        >>> generator = LayoutMaskGenerator(
        ...     config=LayoutMaskGeneratorConfig(cache_dir="masks_cache/")
        ... )
        >>> masks = generator.batch_generate(images)

    Note:
        Requires the `doclayout-yolo` package and the existing
        DocLayoutYOLODetector from this project.
    """

    # Class name to index mapping (DocLayNet order)
    CLASS_MAPPING: ClassVar[dict[str, int]] = {
        "caption": 0,
        "footnote": 1,
        "formula": 2,
        "list-item": 3,
        "list_item": 3,
        "listitem": 3,
        "page-footer": 4,
        "page_footer": 4,
        "pagefooter": 4,
        "page-header": 5,
        "page_header": 5,
        "pageheader": 5,
        "picture": 6,
        "figure": 6,
        "image": 6,
        "section-header": 7,
        "section_header": 7,
        "sectionheader": 7,
        "table": 8,
        "text": 9,
        "plain text": 9,
        "plain_text": 9,
        "title": 10,
    }

    def __init__(
        self,
        config: LayoutMaskGeneratorConfig | None = None,
    ) -> None:
        """Initialize Layout Mask Generator.

        Args:
            config: Generator configuration. Uses defaults if None.
        """
        if config is None:
            config = LayoutMaskGeneratorConfig()
        self.config = config

        # Lazy-load detector
        self._detector: object | None = None

        # Set up cache directory if specified
        self._cache_path: Path | None = None
        if config.cache_dir:
            self._cache_path = Path(config.cache_dir)
            self._cache_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            "layout_mask_generator_initialized",
            model_path=config.model_path,
            target_size=config.target_size,
            cache_enabled=config.cache_dir is not None,
        )

    def _load_detector(self) -> None:
        """Lazy-load the DocLayout-YOLO detector."""
        if self._detector is not None:
            return

        try:
            from image_preprocessing_detector.detection.doclayout_yolo import (
                DocLayoutYOLODetector,
            )

            self._detector = DocLayoutYOLODetector(
                confidence_threshold=self.config.confidence_threshold,
                device=self.config.device,
            )
            logger.info("doclayout_yolo_detector_loaded")
        except ImportError as e:
            raise ImportError(
                "DocLayout-YOLO is required for layout mask generation. "
                "Ensure doclayout-yolo is installed and the detector is available."
            ) from e

    def _get_cache_key(self, image: NDArray[np.uint8]) -> str:
        """Generate cache key from image content.

        Args:
            image: Input image array.

        Returns:
            MD5 hash of image bytes.
        """
        return hashlib.md5(image.tobytes(), usedforsecurity=False).hexdigest()

    def _load_from_cache(self, cache_key: str) -> NDArray[np.float32] | None:
        """Load mask from cache if available.

        Args:
            cache_key: Cache key (MD5 hash).

        Returns:
            Cached mask array or None if not found.
        """
        if self._cache_path is None:
            return None

        cache_file = self._cache_path / f"{cache_key}.npy"
        if cache_file.exists():
            result: NDArray[np.float32] = np.load(cache_file)
            return result
        return None

    def _save_to_cache(self, cache_key: str, mask: NDArray[np.float32]) -> None:
        """Save mask to cache.

        Args:
            cache_key: Cache key (MD5 hash).
            mask: Mask array to cache.
        """
        if self._cache_path is None:
            return

        cache_file = self._cache_path / f"{cache_key}.npy"
        np.save(cache_file, mask)

    def generate_mask(
        self,
        image: NDArray[np.uint8],
        target_size: tuple[int, int] | None = None,
    ) -> NDArray[np.float32]:
        """Generate layout mask for a single image.

        Args:
            image: Input image as numpy array [H, W, 3] (RGB or BGR).
            target_size: Output mask size (height, width).
                        Defaults to config.target_size.

        Returns:
            One-hot encoded mask of shape [11, H, W] with dtype float32.
            Each pixel has at most one class active.
        """
        target_size = target_size or self.config.target_size

        # Generate cache key for this image (used throughout)
        cache_key: str | None = None
        if self._cache_path is not None:
            cache_key = self._get_cache_key(image)
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                logger.debug("mask_loaded_from_cache", cache_key=cache_key[:8])
                return cached

        # Load detector if needed
        self._load_detector()

        # Run detection
        from image_preprocessing_detector.detection.doclayout_yolo import (
            LayoutDetectionResult,
        )

        result: LayoutDetectionResult = self._detector.detect(image)  # type: ignore[union-attr]

        # Initialize empty mask
        h, w = target_size
        mask = np.zeros((self.config.n_classes, h, w), dtype=np.float32)

        if not result.success or not result.elements:
            logger.debug("no_elements_detected", success=result.success)
            if cache_key is not None:
                self._save_to_cache(cache_key, mask)
            return mask

        # Get original image dimensions for scaling
        orig_h, orig_w = image.shape[:2]
        scale_h = h / orig_h
        scale_w = w / orig_w

        # Track confidence for overlapping regions
        confidence_map = np.zeros((h, w), dtype=np.float32)

        # Fill mask from detections (higher confidence wins overlaps)
        for element in result.elements:
            # Get class index
            class_name = element.class_name.lower()
            class_idx = self.CLASS_MAPPING.get(class_name)

            if class_idx is None:
                logger.debug("unknown_class_name", class_name=class_name)
                continue

            # Scale bounding box to target size
            x1, y1, x2, y2 = element.bbox_xyxy
            x1_scaled = int(x1 * scale_w)
            y1_scaled = int(y1 * scale_h)
            x2_scaled = int(min(x2 * scale_w, w))
            y2_scaled = int(min(y2 * scale_h, h))

            # Only fill if this detection has higher confidence
            region_confidence = confidence_map[y1_scaled:y2_scaled, x1_scaled:x2_scaled]
            new_confidence = element.confidence

            # Create mask for pixels where new detection wins
            update_mask = region_confidence < new_confidence

            # Update the one-hot mask
            for c in range(self.config.n_classes):
                if c == class_idx:
                    mask[c, y1_scaled:y2_scaled, x1_scaled:x2_scaled] = np.where(
                        update_mask,
                        1.0,
                        mask[c, y1_scaled:y2_scaled, x1_scaled:x2_scaled],
                    )
                else:
                    mask[c, y1_scaled:y2_scaled, x1_scaled:x2_scaled] = np.where(
                        update_mask,
                        0.0,
                        mask[c, y1_scaled:y2_scaled, x1_scaled:x2_scaled],
                    )

            # Update confidence map
            confidence_map[y1_scaled:y2_scaled, x1_scaled:x2_scaled] = np.maximum(
                confidence_map[y1_scaled:y2_scaled, x1_scaled:x2_scaled],
                new_confidence,
            )

        # Cache the result
        if cache_key is not None:
            self._save_to_cache(cache_key, mask)
            logger.debug("mask_saved_to_cache", cache_key=cache_key[:8])

        logger.debug(
            "mask_generated",
            num_elements=len(result.elements),
            mask_shape=mask.shape,
        )

        return mask

    def batch_generate(
        self,
        images: list[NDArray[np.uint8]],
        target_size: tuple[int, int] | None = None,
    ) -> list[NDArray[np.float32]]:
        """Generate layout masks for a batch of images.

        Args:
            images: List of input images.
            target_size: Output mask size for all images.

        Returns:
            List of mask arrays, each of shape [11, H, W].
        """
        return [self.generate_mask(img, target_size) for img in images]

    def generate_mask_tensor(
        self,
        image: NDArray[np.uint8],
        target_size: tuple[int, int] | None = None,
        device: str | torch.device = "cpu",
    ) -> torch.Tensor:
        """Generate layout mask as PyTorch tensor.

        Args:
            image: Input image as numpy array.
            target_size: Output mask size.
            device: Target device for tensor.

        Returns:
            Mask tensor of shape [11, H, W] on specified device.
        """
        mask = self.generate_mask(image, target_size)
        return torch.from_numpy(mask).to(device)


class DocIQReplica(nn.Module):
    """Full DocIQ Replica with Layout Fusion Downsampler.

    Matches original DocIQ paper architecture:
    - 1600x1600 input resolution
    - Layout Fusion Downsampler with semantic masks
    - ResNet-50 backbone
    - Multi-task head for quality prediction

    Serves as the GENERALIST ANCHOR for Track A, predicting all three
    DIQA quality dimensions with equal weighting:
    - Overall quality
    - Sharpness
    - Color fidelity

    Training follows DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3:
    - 60 epochs total (paper-aligned)
    - Phase 1: Head warmup (15 epochs, frozen backbone)
    - Phase 2: Full fine-tune (45 epochs)
    - Loss weights: [0.34, 0.33, 0.33] (equal/generalist)

    Example:
        >>> model = DocIQReplica()
        >>> rgb = torch.randn(4, 3, 1600, 1600)
        >>> layout = torch.randn(4, 11, 1600, 1600)
        >>> outputs = model(rgb, layout)
        >>> print(outputs["overall"].shape)  # torch.Size([4])
        >>> print(outputs["sharpness"].shape)  # torch.Size([4])
        >>> print(outputs["color"].shape)  # torch.Size([4])
    """

    def __init__(
        self,
        n_layout_classes: int = N_LAYOUT_CLASSES,
        freeze_backbone: bool = True,
        head_hidden_dim: int = 512,
        head_dropout: float = 0.1,
        pretrained_backbone: bool = True,
    ) -> None:
        """Initialize DocIQ Replica.

        Args:
            n_layout_classes: Number of layout classes (default 11).
            freeze_backbone: Whether to freeze ResNet backbone (Phase 1).
            head_hidden_dim: Hidden dimension for multi-task head.
            head_dropout: Dropout probability for head.
            pretrained_backbone: Use ImageNet pretrained weights.
        """
        super().__init__()

        # Layout-aware downsampler (DocIQ paper component)
        self.downsampler = LayoutFusionDownsampler(
            config=LayoutFusionConfig(n_layout_classes=n_layout_classes)
        )

        # ResNet-50 backbone (receives 400x400 fused features)
        try:
            from torchvision import models
        except ImportError as e:
            raise ImportError(
                "torchvision is required for DocIQReplica. "
                "Install with: pip install torchvision"
            ) from e

        weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained_backbone else None

        self.backbone = models.resnet50(weights=weights)
        # Remove final FC layer (we use custom head)
        self.backbone.fc = nn.Identity()

        # Track backbone frozen state
        self._backbone_frozen = freeze_backbone
        if freeze_backbone:
            self._freeze_backbone()

        # Document-specific IQA head (larger hidden dim for generalist)
        # ResNet-50 outputs 2048-dim features
        from image_preprocessing_detector.labeling.finetuning.musiq_wrapper import (
            MultiTaskHead,
            MultiTaskHeadConfig,
        )

        self.head_config = MultiTaskHeadConfig(
            in_features=2048,
            hidden_dim=head_hidden_dim,
            dropout=head_dropout,
        )
        self.head = MultiTaskHead(self.head_config)

        logger.info(
            "dociq_replica_initialized",
            n_layout_classes=n_layout_classes,
            freeze_backbone=freeze_backbone,
            head_hidden_dim=head_hidden_dim,
            pretrained_backbone=pretrained_backbone,
        )

    def _freeze_backbone(self) -> None:
        """Freeze all backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        # Also freeze downsampler in Phase 1
        for param in self.downsampler.parameters():
            param.requires_grad = False
        self._backbone_frozen = True
        logger.info("dociq_backbone_frozen")

    def unfreeze_backbone(self) -> None:
        """Unfreeze backbone parameters for Phase 2 training."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        # Also unfreeze downsampler
        for param in self.downsampler.parameters():
            param.requires_grad = True
        self._backbone_frozen = False
        logger.info("dociq_backbone_unfrozen")

    @property
    def is_backbone_frozen(self) -> bool:
        """Check if backbone is currently frozen."""
        return self._backbone_frozen

    def forward(
        self,
        rgb: torch.Tensor,
        layout: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Forward pass through full DocIQ Replica.

        Args:
            rgb: RGB image tensor [B, 3, 1600, 1600].
            layout: Layout mask tensor [B, 11, 1600, 1600].

        Returns:
            Dictionary with keys 'overall', 'sharpness', 'color',
            each containing scores of shape [B] in [0, 1].
        """
        # Fuse RGB with layout masks
        fused = self.downsampler(rgb, layout)  # [B, 3, 400, 400]

        # Extract features
        features = self.backbone(fused)  # [B, 2048]

        # Predict quality scores
        result: dict[str, Any] = self.head(features)  # {dim: [B]}
        return result

    def get_backbone_params(self) -> list[nn.Parameter]:
        """Get backbone and downsampler parameters for optimizer groups."""
        params = list(self.backbone.parameters())
        params.extend(self.downsampler.parameters())
        return params

    def get_head_params(self) -> list[nn.Parameter]:
        """Get head parameters for optimizer groups."""
        return list(self.head.parameters())

    def get_trainable_params(self) -> int:
        """Get count of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_total_params(self) -> int:
        """Get total parameter count."""
        return sum(p.numel() for p in self.parameters())


def create_dociq_replica(
    device: str = "cuda",
    freeze_backbone: bool = True,
    head_hidden_dim: int = 512,
    head_dropout: float = 0.1,
    pretrained_backbone: bool = True,
) -> DocIQReplica:
    """Factory function to create DocIQReplica model.

    Args:
        device: Device to load model on.
        freeze_backbone: Whether to freeze backbone initially (Phase 1).
        head_hidden_dim: Hidden dimension for multi-task head.
        head_dropout: Dropout probability for head.
        pretrained_backbone: Use ImageNet pretrained weights.

    Returns:
        Initialized DocIQReplica model on specified device.

    Example:
        >>> model = create_dociq_replica(device="cuda", freeze_backbone=True)
        >>> # Phase 1 training with frozen backbone
        >>> # ... train head only ...
        >>> model.unfreeze_backbone()
        >>> # Phase 2 training with full fine-tuning
    """
    model = DocIQReplica(
        n_layout_classes=N_LAYOUT_CLASSES,
        freeze_backbone=freeze_backbone,
        head_hidden_dim=head_hidden_dim,
        head_dropout=head_dropout,
        pretrained_backbone=pretrained_backbone,
    )
    result: DocIQReplica = model.to(device)
    return result
