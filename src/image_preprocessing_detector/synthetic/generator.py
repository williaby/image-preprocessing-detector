"""Multi-script synthetic document generator for SigLIP training.

This module provides the main generator class that orchestrates text corpus,
font management, document rendering, and augmentation to produce synthetic
training images with ground truth labels.

Key Features:
    - Generate documents in 27 ISO 15924 scripts
    - Controllable layout, density, and degradation
    - Layer 2 schema-compatible metadata output
    - Batch generation with progress tracking
    - Multi-script document support

Example:
    >>> from image_preprocessing_detector.synthetic.generator import (
    ...     MultiScriptDocumentGenerator,
    ...     GenerationConfig,
    ... )
    >>> config = GenerationConfig(
    ...     scripts=["Arab", "Latn", "Deva"],
    ...     samples_per_script=100,
    ... )
    >>> generator = MultiScriptDocumentGenerator(config)
    >>> generator.initialize()
    >>> for sample in generator.generate():
    ...     sample.image.save(f"output/{sample.sample_id}.png")
"""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.synthetic.augmentation import (
    AUGRAPHY_AVAILABLE,
    AugmentationPipeline,
    DegradationProfile,
)
from image_preprocessing_detector.synthetic.augmentation_fast import (
    ALBUMENTATIONS_AVAILABLE,
    AugmentationProfile,
    FastAugmentationPipeline,
)
from image_preprocessing_detector.synthetic.augmentation_hybrid import (
    HYBRID_AVAILABLE,
    HybridAugmentationPipeline,
    HybridProfile,
)
from image_preprocessing_detector.synthetic.config import (
    CJK_VERTICAL_RATIOS,
    COLOR_MODE_WEIGHTS,
    DOCUMENT_COMPOSITION_WEIGHTS,
    ENGLISH_SECONDARY_WEIGHT,
    LAYOUT_WEIGHTS,
    MVP_SCRIPTS,
    QUALITY_TIER_WEIGHTS,
    RESOLUTION_TIER_WEIGHTS,
    RESOLUTION_TIERS,
    SCRIPT_CONFIGS,
    SKEW_RANGE_DEGREES,
    TEXT_DENSITY_WEIGHTS,
    TWO_SCRIPT_COMBINATIONS,
    ColorMode,
    LayoutType,
    TextDensity,
)
from image_preprocessing_detector.synthetic.corpus import TextCorpusManager
from image_preprocessing_detector.synthetic.fonts import FontManager
from image_preprocessing_detector.synthetic.renderer import DocumentRenderer
from image_preprocessing_detector.synthetic.schema_adapter import (
    GeneratedSample,
    IQALabels,
    Layer2SchemaAdapter,
)

if TYPE_CHECKING:
    from PIL.Image import Image as PILImageType

logger = logging.getLogger(__name__)

_NOT_INITIALIZED_MSG = "Generator not initialized. Call initialize() first."


@dataclass
class GenerationConfig:
    """Configuration for document generation.

    Attributes:
        scripts: List of ISO 15924 script codes to generate
        samples_per_script: Number of samples per script
        layout_types: Layout types to use (None = all)
        text_densities: Text densities to use (None = all)
        degradation_profiles: Degradation profiles (None = all)
        output_dir: Directory to save generated images
        save_images: Whether to save images to disk
        save_metadata: Whether to save metadata JSON
        image_format: Output image format (png, jpg)
        seed: Random seed for reproducibility
        pristine_ratio: Ratio of pristine (undegraded) samples (0-1)
    """

    scripts: list[str] = field(
        default_factory=lambda: list(MVP_SCRIPTS)
    )  # nosemgrep: python.lang.maintainability.return.return-not-in-function
    samples_per_script: int = 100
    layout_types: list[LayoutType] | None = None
    text_densities: list[TextDensity] | None = None
    degradation_profiles: list[DegradationProfile] | None = None
    output_dir: Path | None = None
    save_images: bool = True
    save_metadata: bool = True
    image_format: str = "png"
    seed: int | None = None
    pristine_ratio: float = 0.2
    dpi: int = 300  # Output resolution (300 = full, 150 = half for faster augmentation)
    augmenter: str = "albumentations"  # "augraphy", "albumentations", or "hybrid"
    # Hybrid mode: Augraphy for bleed-through/ink/paper + Albumentations for blur/noise/compression
    # Multi-task training augmentation flags
    color_mode_enabled: bool = (
        False  # Apply random color mode conversion (grayscale/binarized)
    )
    skew_augmentation: bool = (
        False  # Apply random skew (SKEW_RANGE_DEGREES) with exact angle label
    )
    orientation_augmentation: bool = (
        False  # Apply 0/90/180/270 rotation with class label
    )

    def __post_init__(self) -> None:
        """Validate and set defaults."""
        if self.layout_types is None:
            self.layout_types = list(LayoutType)
        if self.text_densities is None:
            self.text_densities = list(TextDensity)
        if self.degradation_profiles is None:
            self.degradation_profiles = list(DegradationProfile)
        if self.output_dir is not None:
            self.output_dir = Path(self.output_dir)


@dataclass
class GenerationStats:
    """Statistics from a generation run.

    Attributes:
        total_samples: Total samples generated
        samples_per_script: Count per script code
        samples_per_layout: Count per layout type
        samples_per_profile: Count per degradation profile
        failed_samples: Number of failed generations
        errors: List of error messages
    """

    total_samples: int = 0
    samples_per_script: dict[str, int] = field(default_factory=dict)
    samples_per_layout: dict[str, int] = field(default_factory=dict)
    samples_per_profile: dict[str, int] = field(default_factory=dict)
    failed_samples: int = 0
    errors: list[str] = field(default_factory=list)


class MultiScriptDocumentGenerator:
    """Generates synthetic multi-script documents for training.

    Orchestrates text corpus, fonts, rendering, and augmentation
    to produce training data with ground truth labels.
    """

    def __init__(
        self,
        config: GenerationConfig | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            config: Generation configuration (uses defaults if None)
        """
        self.config = config or GenerationConfig()
        self._initialized = False

        # Components (initialized lazily)
        self._corpus_manager: TextCorpusManager | None = None
        self._font_manager: FontManager | None = None
        self._renderer: DocumentRenderer | None = None
        self._renderers_by_tier: dict[
            str, DocumentRenderer
        ] = {}  # Cache per-tier renderers
        self._augmentation: AugmentationPipeline | None = None
        self._fast_augmentation: FastAugmentationPipeline | None = None
        self._hybrid_augmentation: HybridAugmentationPipeline | None = None
        self._schema_adapter: Layer2SchemaAdapter | None = None

        # Generation state
        self._stats = GenerationStats()
        self._rng: Any = None

    @property
    def corpus_manager(self) -> TextCorpusManager:
        """Get the text corpus manager."""
        if self._corpus_manager is None:
            # Pass seed for reproducible text selection (FIX BUG #5)
            self._corpus_manager = TextCorpusManager(seed=self.config.seed)
        return self._corpus_manager

    @property
    def font_manager(self) -> FontManager:
        """Get the font manager."""
        if self._font_manager is None:
            self._font_manager = FontManager()
        return self._font_manager

    @property
    def renderer(self) -> DocumentRenderer:
        """Get the document renderer."""
        if self._renderer is None:
            # Calculate page size based on DPI (A4 dimensions)
            # A4 is 8.27 x 11.69 inches
            dpi = self.config.dpi
            page_width = int(8.27 * dpi)
            page_height = int(11.69 * dpi)
            # Scale margins proportionally
            base_margin = int(150 * dpi / 300)  # 150px at 300 DPI
            margins = (base_margin, base_margin, base_margin, base_margin)
            self._renderer = DocumentRenderer(
                self.font_manager,
                page_size=(page_width, page_height),
                margins=margins,
                dpi=dpi,
            )
        return self._renderer

    @property
    def augmentation(self) -> AugmentationPipeline:
        """Get the Augraphy augmentation pipeline."""
        if self._augmentation is None:
            self._augmentation = AugmentationPipeline(seed=self.config.seed)
        return self._augmentation

    @property
    def fast_augmentation(self) -> FastAugmentationPipeline:
        """Get the Albumentations augmentation pipeline."""
        if not hasattr(self, "_fast_augmentation") or self._fast_augmentation is None:
            self._fast_augmentation = FastAugmentationPipeline(seed=self.config.seed)
        return self._fast_augmentation

    @property
    def hybrid_augmentation(self) -> HybridAugmentationPipeline:
        """Get the hybrid augmentation pipeline (Augraphy + Albumentations)."""
        if (
            not hasattr(self, "_hybrid_augmentation")
            or self._hybrid_augmentation is None
        ):
            self._hybrid_augmentation = HybridAugmentationPipeline(
                seed=self.config.seed
            )
        return self._hybrid_augmentation

    @property
    def schema_adapter(self) -> Layer2SchemaAdapter:
        """Get the schema adapter."""
        if self._schema_adapter is None:
            self._schema_adapter = Layer2SchemaAdapter()
        return self._schema_adapter

    def initialize(
        self,
        download_corpus: bool = True,
        scan_fonts: bool = True,
    ) -> bool:
        """Initialize all components.

        Args:
            download_corpus: Whether to download missing corpus data
            scan_fonts: Whether to scan for available fonts

        Returns:
            True if initialization successful
        """
        import random

        self._rng = random.Random(self.config.seed)

        # Initialize corpus
        logger.info("Initializing text corpus...")
        loaded = 0
        try:
            if download_corpus:
                loaded = self.corpus_manager.load_from_cache_or_download(
                    self.config.scripts, use_sample_fallback=True
                )
            else:
                # Skip download, but still use sample texts as fallback
                loaded = self.corpus_manager.load_from_cache(self.config.scripts)
                if loaded == 0:
                    logger.info("No cache found, using built-in sample texts")
                    loaded = self.corpus_manager.load_sample_texts(self.config.scripts)
        except Exception as e:
            logger.error("Failed to initialize corpus: %s", e)
            return False

        if loaded == 0:
            raise RuntimeError(
                "Corpus empty - cannot generate diverse text. "
                "Run corpus download or set use_sample_fallback=True to proceed "
                "with built-in sample texts (low diversity)."
            )

        # Initialize fonts
        logger.info("Scanning fonts...")
        found = 0
        try:
            if scan_fonts:
                found = self.font_manager.scan_fonts()
        except Exception as e:
            logger.error("Failed to scan fonts: %s", e)
            return False

        if scan_fonts and found == 0:
            raise RuntimeError(
                "No fonts found for any configured script. "
                "Install Noto fonts: "
                "https://fonts.google.com/noto or run scripts/install_fonts.sh"
            )

        # Create output directory if needed
        if self.config.output_dir:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info("Generator initialized successfully")
        return True

    def _select_random(self, items: list[Any]) -> Any:
        """Select a random item from list."""
        return self._rng.choice(items) if items else None

    def _select_weighted(self, weights: dict[Any, float]) -> Any:
        """Select an item based on weighted probability.

        Args:
            weights: Dictionary mapping items to their probability weights

        Returns:
            Selected item based on weighted random choice
        """
        items = list(weights.keys())
        probs = list(weights.values())
        # Normalize probabilities
        total = sum(probs)
        if total > 0:
            probs = [p / total for p in probs]
        return self._rng.choices(items, weights=probs, k=1)[0]

    def _select_quality_tier(self) -> str:
        """Select a quality tier based on configured distribution."""
        return str(self._select_weighted(QUALITY_TIER_WEIGHTS))

    def _select_resolution_tier(self) -> str:
        """Select a resolution tier based on configured distribution."""
        return str(self._select_weighted(RESOLUTION_TIER_WEIGHTS))

    def _select_composition_type(self) -> str:
        """Select document composition type (single, two, three, four_plus, priority_pairs)."""
        return str(self._select_weighted(DOCUMENT_COMPOSITION_WEIGHTS))

    def _select_two_script_pair(self, available_scripts: list[str]) -> tuple[str, str]:
        """Select a two-script combination based on configured weights.

        Args:
            available_scripts: List of available script codes

        Returns:
            Tuple of (primary_script, secondary_script)
        """
        # Filter TWO_SCRIPT_COMBINATIONS to available scripts
        valid_pairs = {
            pair: weight
            for pair, weight in TWO_SCRIPT_COMBINATIONS.items()
            if pair[0] in available_scripts and pair[1] in available_scripts
        }

        if valid_pairs:
            # Weighted selection from valid pairs
            result: Any = self._select_weighted(valid_pairs)  # type: ignore[arg-type]
            return result  # type: ignore[no-any-return]

        # Fallback: random pair with English secondary weighting
        if len(available_scripts) >= 2:
            primary = self._rng.choice(available_scripts)
            # Weight Latin at ENGLISH_SECONDARY_WEIGHT probability as secondary
            other_scripts = [s for s in available_scripts if s != primary]
            if (
                "Latn" in other_scripts
                and self._rng.random() < ENGLISH_SECONDARY_WEIGHT
            ):
                secondary = "Latn"
            else:
                secondary = self._rng.choice(other_scripts)
            return (primary, secondary)

        # Last resort: use same script twice
        return (available_scripts[0], available_scripts[0])

    def _select_multi_script_layout(self, num_scripts: int) -> LayoutType:
        """Select appropriate layout for multi-script documents.

        Args:
            num_scripts: Number of scripts in the document

        Returns:
            LayoutType appropriate for the script count
        """
        if num_scripts == 2:
            # Two scripts: HEADER_BODY, COLUMNS, or INTERLEAVED
            layouts: list[LayoutType] = [
                LayoutType.HEADER_BODY,
                LayoutType.COLUMNS,
                LayoutType.INTERLEAVED,
            ]
            weights = [0.4, 0.4, 0.2]  # Favor structured layouts
            selected: LayoutType = self._rng.choices(layouts, weights=weights, k=1)[0]
            return selected
        if num_scripts == 3:
            # Three scripts: COLUMNS or INTERLEAVED
            layouts3: list[LayoutType] = [
                LayoutType.COLUMNS,
                LayoutType.INTERLEAVED,
                LayoutType.STACKED,
            ]
            weights3 = [0.4, 0.3, 0.3]
            selected3: LayoutType = self._rng.choices(layouts3, weights=weights3, k=1)[
                0
            ]
            return selected3
        # Four+ scripts: INTERLEAVED or STACKED
        layouts4: list[LayoutType] = [LayoutType.INTERLEAVED, LayoutType.STACKED]
        weights4 = [0.6, 0.4]
        selected4: LayoutType = self._rng.choices(layouts4, weights=weights4, k=1)[0]
        return selected4

    def _get_resolution_for_tier(self, tier: str) -> int:
        """Get target DPI for a resolution tier.

        Args:
            tier: Resolution tier (LOW, MEDIUM, HIGH)

        Returns:
            Target DPI value
        """
        tier_config = RESOLUTION_TIERS.get(tier, RESOLUTION_TIERS["STANDARD"])
        dpi = tier_config["target_dpi"]
        return dpi if isinstance(dpi, int) else dpi[0]

    def _get_renderer_for_tier(self, resolution_tier: str) -> DocumentRenderer:
        """Get or create a renderer for the specified resolution tier.

        This ensures images are actually rendered at the target DPI for the tier,
        not just labeled with the tier but rendered at a fixed DPI.

        Args:
            resolution_tier: Resolution tier (LOW, MEDIUM, HIGH)

        Returns:
            DocumentRenderer configured for the tier's DPI
        """
        if resolution_tier in self._renderers_by_tier:
            return self._renderers_by_tier[resolution_tier]

        # Get target DPI for this tier
        target_dpi = self._get_resolution_for_tier(resolution_tier)

        # Calculate page size for this DPI (A4 dimensions: 8.27 x 11.69 inches)
        page_width = int(8.27 * target_dpi)
        page_height = int(11.69 * target_dpi)

        # Scale margins proportionally (150px at 300 DPI baseline)
        base_margin = int(150 * target_dpi / 300)
        margins = (base_margin, base_margin, base_margin, base_margin)

        # Create and cache the renderer
        renderer = DocumentRenderer(
            self.font_manager,
            page_size=(page_width, page_height),
            margins=margins,
            dpi=target_dpi,
        )
        self._renderers_by_tier[resolution_tier] = renderer

        logger.debug(
            "Created renderer for tier %s: %dx%d @ %d DPI",
            resolution_tier,
            page_width,
            page_height,
            target_dpi,
        )
        return renderer

    def _apply_color_mode(self, image: Any) -> tuple[Any, str]:
        """Apply random color mode conversion for training diversity.

        Converts image to grayscale or binarized based on COLOR_MODE_WEIGHTS.
        The image is always returned as RGB (3-channel) for model compatibility.

        Args:
            image: PIL Image in RGB mode

        Returns:
            Tuple of (converted image, color_mode string)
        """
        mode = self._select_weighted(COLOR_MODE_WEIGHTS)

        if mode == ColorMode.GRAYSCALE:
            gray = image.convert("L")
            return gray.convert("RGB"), "grayscale"

        if mode == ColorMode.BINARIZED:
            gray = image.convert("L")
            # Otsu-style adaptive threshold via simple mean
            import numpy as np

            arr = np.array(gray)
            threshold = int(arr.mean() * 0.85)  # Slightly below mean for document text
            binary = gray.point(lambda p: 255 if p > threshold else 0)
            return binary.convert("RGB"), "binarized"

        return image, "color"

    def _apply_skew_augmentation(self, image: Any) -> tuple[Any, float]:
        """Apply random skew rotation with exact angle label.

        Applies a random rotation within SKEW_RANGE_DEGREES (default ±22°)
        with white fill. The exact angle is stored as a tier_0_exact label
        for regression training.

        Args:
            image: PIL Image

        Returns:
            Tuple of (rotated image, angle in degrees)
        """
        angle = self._rng.uniform(SKEW_RANGE_DEGREES[0], SKEW_RANGE_DEGREES[1])
        rotated = image.rotate(
            -angle,  # PIL rotates counter-clockwise, negate for clockwise convention
            expand=False,
            fillcolor=(255, 255, 255),
        )
        return rotated, angle

    def _apply_orientation_augmentation(self, image: Any) -> tuple[Any, int]:
        """Apply random 0/90/180/270 degree rotation with class label.

        Args:
            image: PIL Image

        Returns:
            Tuple of (rotated image, orientation class)
        """
        from PIL import Image as PILImage

        orientation = self._rng.choice([0, 90, 180, 270])
        if orientation == 0:
            return image, 0
        if orientation == 90:
            return image.transpose(PILImage.Transpose.ROTATE_90), 90
        if orientation == 180:
            return image.transpose(PILImage.Transpose.ROTATE_180), 180
        return image.transpose(PILImage.Transpose.ROTATE_270), 270

    def _measure_char_height(self, image: Any) -> tuple[float | None, float | None]:
        """Measure character height via connected component analysis.

        Uses a simple binarize + connected component approach to estimate
        the median character height in the image.

        Args:
            image: PIL Image

        Returns:
            Tuple of (char_height_px, quality_score) or (None, None) if measurement fails
        """
        try:
            import numpy as np

            gray = np.array(image.convert("L"))
            # Binarize with adaptive threshold
            threshold = int(gray.mean() * 0.85)
            binary = (gray < threshold).astype(np.uint8)

            # Find connected components
            try:
                import cv2

                num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
                    binary, connectivity=8
                )
            except ImportError:
                return None, None

            if num_labels < 3:  # Need at least a few components
                return None, None

            # Get heights of components (skip background label 0)
            heights = stats[1:, cv2.CC_STAT_HEIGHT]
            areas = stats[1:, cv2.CC_STAT_AREA]

            # Filter: keep components with reasonable aspect ratio and size
            widths = stats[1:, cv2.CC_STAT_WIDTH]
            aspect_ratios = heights / np.maximum(widths, 1)
            min_area = max(4, gray.size * 0.00001)  # At least 4 pixels
            max_area = gray.size * 0.1  # No more than 10% of image

            mask = (
                (areas > min_area)
                & (areas < max_area)
                & (aspect_ratios > 0.2)
                & (aspect_ratios < 5.0)
            )

            filtered_heights = heights[mask]
            if len(filtered_heights) < 3:
                return None, None

            median_height = float(np.median(filtered_heights))

            # Map character height to quality score (from plan Section 3.2)
            if median_height < 16:
                quality = median_height / 16.0 * 0.15
            elif median_height < 24:
                quality = 0.15 + (median_height - 16) / 8.0 * 0.20
            elif median_height < 32:
                quality = 0.35 + (median_height - 24) / 8.0 * 0.20
            elif median_height < 48:
                quality = 0.55 + (median_height - 32) / 16.0 * 0.20
            elif median_height < 64:
                quality = 0.75 + (median_height - 48) / 16.0 * 0.10
            elif median_height < 96:
                quality = 0.85 + (median_height - 64) / 32.0 * 0.10
            else:
                quality = min(1.0, 0.95 + (median_height - 96) / 200.0 * 0.05)

            return median_height, round(quality, 4)

        except Exception as e:
            logger.debug("Character height measurement failed: %s", e)
            return None, None

    def _compute_image_sha256(self, image: Any) -> str:
        """Compute SHA256 hash of a PIL Image for split registry integration.

        Serializes the image to PNG bytes in memory and hashes the result.
        This provides a content-addressable identifier for the pristine image.

        Args:
            image: PIL Image

        Returns:
            Hex-encoded SHA256 hash string
        """
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return hashlib.sha256(buf.getvalue()).hexdigest()

    def _measure_char_height_rendered(self, image: Any) -> float | None:
        """Measure actual rendered character height on the pristine image.

        Uses connected component analysis on the clean rendered image
        BEFORE any degradation or geometric transforms. This is the
        key advantage of synthetic data: exact ground truth, not estimates.

        Args:
            image: Pristine rendered PIL Image (no degradation applied)

        Returns:
            Median character height in pixels, or None if measurement fails
        """
        char_height, _ = self._measure_char_height(image)
        return char_height

    def _select_text_direction(self, script_code: str) -> str:
        """Select text direction for a script, supporting CJK vertical text.

        For scripts in CJK_VERTICAL_RATIOS (Jpan, Hans, Hant), randomly
        selects vertical (ttb) direction based on configured ratios.
        Other scripts use their default direction from ScriptConfig.

        Args:
            script_code: ISO 15924 script code

        Returns:
            Text direction: "ltr", "rtl", or "ttb"
        """
        vertical_ratio = CJK_VERTICAL_RATIOS.get(script_code)
        if vertical_ratio is not None and self._rng.random() < vertical_ratio:
            return "ttb"

        # Use default direction from config
        config = SCRIPT_CONFIGS.get(script_code)
        if config:
            return config.direction
        return "ltr"

    def _apply_geometric_transforms(
        self,
        image: Any,
    ) -> tuple[Any, float | None, int | None]:
        """Apply geometric transforms (skew, orientation) to a rendered image.

        These MUST be applied BEFORE the augmentation/degradation pipeline so that
        pixel-level effects (noise, blur, compression artifacts) are added in the
        correct reference frame. Real scanners physically rotate/skew the document
        first, then sensor noise is added on top.

        Args:
            image: Clean rendered image (pre-augmentation)

        Returns:
            Tuple of (transformed_image, skew_angle_degrees, orientation_class).
            skew_angle is None if skew augmentation is disabled.
            orientation_class is None if orientation augmentation is disabled.
        """
        skew_angle: float | None = None
        orientation_class: int | None = None

        # 1. Skew augmentation (applied before orientation)
        if self.config.skew_augmentation:
            image, skew_angle = self._apply_skew_augmentation(image)

        # 2. Orientation augmentation (applied after skew)
        if self.config.orientation_augmentation:
            image, orientation_class = self._apply_orientation_augmentation(image)

        return image, skew_angle, orientation_class

    def _apply_post_processing(
        self,
        sample: GeneratedSample,
    ) -> GeneratedSample:
        """Apply non-geometric post-processing to a generated sample.

        This applies color mode conversion and character height measurement AFTER
        the augmentation pipeline. Geometric transforms (skew, orientation) are
        applied earlier via _apply_geometric_transforms() BEFORE augmentation
        to avoid unrealistic "rotated noise" artifacts.

        Args:
            sample: Generated sample to post-process

        Returns:
            Sample with post-processing applied and metadata updated
        """
        image = sample.image

        # 1. Color mode conversion (after augmentation is fine - changes color space)
        if self.config.color_mode_enabled:
            image, color_mode = self._apply_color_mode(image)
            sample.color_mode = color_mode

        # 2. Character height measurement (non-destructive, measurement only)
        char_height, quality_score = self._measure_char_height(image)
        if char_height is not None:
            sample.char_height_px = char_height
            sample.char_height_quality_score = quality_score

        sample.image = image
        return sample

    def _generate_single_sample(
        self,
        script_code: str,
        layout_type: LayoutType,
        text_density: TextDensity,
        degradation_profile: DegradationProfile,
        quality_tier: str = "MEDIUM",
        resolution_tier: str = "MEDIUM",
    ) -> GeneratedSample | None:
        """Generate a single sample.

        Args:
            script_code: ISO 15924 script code
            layout_type: Layout type to use
            text_density: Text density level
            degradation_profile: Degradation profile
            quality_tier: Quality tier (PRISTINE, HIGH, MEDIUM, LOW, DEGRADED)
            resolution_tier: Resolution tier (LOW, MEDIUM, HIGH)

        Returns:
            GeneratedSample or None if failed
        """
        # Get text from corpus
        text, language_code = self.corpus_manager.get_text_with_language(
            script_code, text_density
        )

        if not text:
            logger.warning("No text available for script %s", script_code)
            return None

        # Select text direction (supports CJK vertical text)
        text_direction = self._select_text_direction(script_code)

        # Get renderer for the appropriate resolution tier
        tier_renderer = self._get_renderer_for_tier(resolution_tier)
        actual_dpi = self._get_resolution_for_tier(resolution_tier)

        # Render document at tier-specific DPI
        try:
            image, text_blocks = tier_renderer.render_document(
                text=text,
                script_code=script_code,
                language_code=language_code or "",
                layout_type=layout_type,
                _text_density=text_density,
            )
        except Exception as e:
            logger.error("Rendering failed for %s: %s", script_code, e)
            return None

        # Measure char_height_rendered_px on pristine image BEFORE any transforms
        # This is the key advantage of synthetic data: exact ground truth
        char_height_rendered = self._measure_char_height_rendered(image)

        # Compute SHA256 of pristine image for split registry integration
        base_image_sha256 = self._compute_image_sha256(image)

        # Capture degradation seed for reproducible replay
        degradation_seed = self._rng.randint(0, 2**31 - 1)

        # Capture the fonts actually used by the renderer (sorted for deterministic metadata)
        sorted_fonts = sorted(tier_renderer.last_rendered_fonts)
        font_families: list[str] = [f for f, _ in sorted_fonts]
        font_styles: list[str] = [s for _, s in sorted_fonts]

        # Apply geometric transforms BEFORE augmentation to avoid "rotated noise"
        # artifacts. Real scanners rotate/skew the physical document, then sensor
        # noise is added - so we must transform geometry on the clean image first.
        image, skew_angle, orientation_class = self._apply_geometric_transforms(image)

        # Apply augmentation (noise, blur, degradation on geometrically-correct image)
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
        document_age: str | None = None
        if is_pristine:
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "albumentations" and ALBUMENTATIONS_AVAILABLE:
            # Map DegradationProfile to AugmentationProfile
            profile_map = {
                DegradationProfile.MILD: AugmentationProfile.LIGHT,
                DegradationProfile.MODERATE: AugmentationProfile.MODERATE,
                DegradationProfile.SEVERE: AugmentationProfile.HEAVY,
                DegradationProfile.FAST: AugmentationProfile.MODERATE,
            }
            alb_profile = profile_map.get(
                degradation_profile, AugmentationProfile.MODERATE
            )
            try:
                degraded_image, fast_labels = self.fast_augmentation.apply(
                    image, alb_profile
                )
                # Convert FastIQALabels to IQALabels (8 dimensions)
                iqa_labels = IQALabels(
                    blur=fast_labels.blur,
                    noise=fast_labels.noise,
                    compression=fast_labels.compression,
                    ink_degradation=fast_labels.ink_degradation,
                    paper_degradation=fast_labels.paper_degradation,
                    geometric_distortion=fast_labels.geometric_distortion,
                    bleed_through=fast_labels.bleed_through,
                    overall_quality=fast_labels.overall_quality,
                )
            except Exception as e:
                logger.warning("Albumentations failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "hybrid" and HYBRID_AVAILABLE:
            # Hybrid mode: Augraphy for document effects + Albumentations for capture effects
            hybrid_profile_map = {
                DegradationProfile.MILD: HybridProfile.LIGHT,
                DegradationProfile.MODERATE: HybridProfile.MODERATE,
                DegradationProfile.SEVERE: HybridProfile.HEAVY,
                DegradationProfile.FAST: HybridProfile.MODERATE,
            }
            hybrid_profile = hybrid_profile_map.get(
                degradation_profile, HybridProfile.MODERATE
            )
            # Randomly apply document aging: 15% AGED, 5% HISTORICAL
            aging_roll = self._rng.random()
            if aging_roll < 0.05:
                hybrid_profile = HybridProfile.HISTORICAL
                document_age = "historical"
            elif aging_roll < 0.20:
                hybrid_profile = HybridProfile.AGED
                document_age = "aged"
            else:
                document_age = "modern"
            try:
                # Hybrid pipeline returns IQALabels directly
                degraded_image, iqa_labels = self.hybrid_augmentation.apply(
                    image, hybrid_profile
                )
            except Exception as e:
                logger.warning("Hybrid augmentation failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "augraphy" and AUGRAPHY_AVAILABLE:
            try:
                degraded_image, iqa_labels = self.augmentation.apply(
                    image, degradation_profile
                )
            except Exception as e:
                logger.warning("Augraphy failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        else:
            # No augmentation available/configured - use original image
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0, noise=0.0, blur=0.0)

        # Create sample
        sample_id = str(uuid.uuid4())
        sample = GeneratedSample(
            image=degraded_image,
            sample_id=sample_id,
            scripts={script_code},
            language_codes=[language_code or ""],
            layout_type=layout_type,
            text_density=text_density,
            iqa_labels=iqa_labels,
            text_blocks=text_blocks,
            resolution_dpi=actual_dpi,  # Use tier-specific DPI, not config default
            width_px=degraded_image.width,
            height_px=degraded_image.height,
            generation_params={
                "degradation_profile": degradation_profile.value,
                "layout_type": layout_type.value,
                "text_density": text_density.value,
                "degradation_seed": degradation_seed,
                "base_image_sha256": base_image_sha256,
                "font_families_used": font_families,
                "font_styles_used": font_styles,
            },
            is_pristine=is_pristine,
            resolution_tier=resolution_tier,
            quality_tier=quality_tier,
        )
        if document_age is not None:
            sample.document_age = document_age

        # Store v2.3 metadata
        sample.text_directions = {script_code: text_direction}
        sample.char_height_rendered_px = char_height_rendered

        # Store geometric transform metadata (applied before augmentation)
        if skew_angle is not None:
            sample.skew_angle_degrees = skew_angle
        if orientation_class is not None:
            sample.orientation_class = orientation_class
            sample.width_px = degraded_image.width
            sample.height_px = degraded_image.height

        return sample

    def generate(self) -> Iterator[GeneratedSample]:
        """Generate samples according to configuration.

        Uses DOCUMENT_COMPOSITION_WEIGHTS to determine single vs multi-script:
        - single (35%): Pure single-script documents
        - two (45%): Bilingual documents (uses TWO_SCRIPT_COMBINATIONS weights)
        - three (12%): Three-script documents
        - four_plus (3%): Four+ script documents
        - priority_pairs (5%): High-priority script combinations

        Per-script enforcement: each script is limited to ``samples_per_script``
        primary-script credits.  Once a script's counter reaches its target it is
        removed from the pool of available scripts so the remaining budget is
        filled by the under-represented scripts.  Multi-script compositions credit
        only the *first* (primary) script of the document.

        Corpus or font initialization failures are surfaced as RuntimeError rather
        than silent empty output so the caller (e.g. worker process) can detect
        the problem early and log a meaningful error.

        Yields:
            GeneratedSample objects

        Raises:
            RuntimeError: If the generator has not been initialised via
                ``initialize()``.
        """
        if not self._initialized:
            raise RuntimeError(_NOT_INITIALIZED_MSG)

        # Harden corpus/font availability check before entering the hot loop.
        # initialize() already validates these, but a subsequent corpus eviction
        # or font manager reset would leave the generator in a broken state that
        # previously produced only None samples and silent failures.
        if self._corpus_manager is not None:
            loaded_scripts = self._corpus_manager.get_available_scripts()
            if not loaded_scripts:
                raise RuntimeError(
                    "Corpus manager has no loaded scripts.  "
                    "Ensure initialize() completed successfully."
                )
        if self._font_manager is not None:
            font_scripts = self._font_manager.get_available_scripts()
            if not font_scripts:
                raise RuntimeError(
                    "Font manager has no available scripts.  "
                    "Install Noto fonts or provide a valid fonts directory."
                )

        self._stats = GenerationStats()
        layout_types = self.config.layout_types or list(LayoutType)
        text_densities = self.config.text_densities or list(TextDensity)

        # Map quality tiers to degradation profiles
        quality_tier_to_profile = {
            "PRISTINE": DegradationProfile.PRISTINE,
            "HIGH": DegradationProfile.MILD,
            "MEDIUM": DegradationProfile.MODERATE,
            "LOW": DegradationProfile.SEVERE,
            "DEGRADED": DegradationProfile.SEVERE,  # + extra transforms
        }

        # Calculate total samples and distribute by composition type
        total_samples = len(self.config.scripts) * self.config.samples_per_script
        available_scripts = [s for s in self.config.scripts if s in SCRIPT_CONFIGS]

        if not available_scripts:
            logger.error("No valid scripts in configuration")
            return

        # Per-script counter: tracks primary-script credits so no single script
        # can overshoot its samples_per_script target.  Scripts are pruned from
        # available_scripts once they hit the limit, preventing the Latn/Arab/Deva
        # overshoot observed in the v3 run caused by the chunk_per_script bug.
        per_script_counts: dict[str, int] = dict.fromkeys(available_scripts, 0)
        script_target = self.config.samples_per_script

        samples_generated = 0

        while samples_generated < total_samples:
            # Select composition type
            composition_type = self._select_composition_type()

            # Select common parameters
            if text_densities == list(TextDensity):
                text_density = self._select_weighted(TEXT_DENSITY_WEIGHTS)
            else:
                text_density = self._select_random(text_densities)

            quality_tier = self._select_quality_tier()
            degradation_profile = quality_tier_to_profile.get(
                quality_tier, DegradationProfile.MODERATE
            )
            resolution_tier = self._select_resolution_tier()

            sample = None

            try:
                if composition_type == "single":
                    # Single-script document
                    script_code = self._select_random(available_scripts)
                    if layout_types == list(LayoutType):
                        layout_type = self._select_weighted(LAYOUT_WEIGHTS)
                    else:
                        layout_type = self._select_random(layout_types)

                    sample = self._generate_single_sample(
                        script_code=script_code,
                        layout_type=layout_type,
                        text_density=text_density,
                        degradation_profile=degradation_profile,
                        quality_tier=quality_tier,
                        resolution_tier=resolution_tier,
                    )

                elif composition_type in ("two", "priority_pairs"):
                    # Two-script document
                    if len(available_scripts) >= 2:
                        scripts = list(self._select_two_script_pair(available_scripts))
                        layout_type = self._select_multi_script_layout(2)
                        sample = self._generate_multi_script_sample(
                            scripts=scripts,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )
                    else:
                        # Fallback to single-script if not enough scripts
                        script_code = available_scripts[0]
                        layout_type = self._select_weighted(LAYOUT_WEIGHTS)
                        sample = self._generate_single_sample(
                            script_code=script_code,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )

                elif composition_type == "three":
                    # Three-script document (ensure Latn is likely included)
                    if len(available_scripts) >= 3:
                        scripts = self._rng.sample(available_scripts, 3)
                        # English secondary weighting: inject Latn if not present
                        if (
                            "Latn" in available_scripts
                            and "Latn" not in scripts
                            and self._rng.random() < ENGLISH_SECONDARY_WEIGHT
                        ):
                            scripts[self._rng.randint(1, 2)] = "Latn"
                        layout_type = self._select_multi_script_layout(3)
                        sample = self._generate_multi_script_sample(
                            scripts=scripts,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )
                    elif len(available_scripts) >= 2:
                        # Fallback to two scripts
                        scripts = self._rng.sample(available_scripts, 2)
                        layout_type = self._select_multi_script_layout(2)
                        sample = self._generate_multi_script_sample(
                            scripts=scripts,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )
                    else:
                        script_code = available_scripts[0]
                        layout_type = self._select_weighted(LAYOUT_WEIGHTS)
                        sample = self._generate_single_sample(
                            script_code=script_code,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )

                elif composition_type == "four_plus":
                    # Four+ script document
                    num_scripts = min(self._rng.randint(4, 6), len(available_scripts))
                    if num_scripts >= 4:
                        scripts = self._rng.sample(available_scripts, num_scripts)
                        layout_type = self._select_multi_script_layout(num_scripts)
                        sample = self._generate_multi_script_sample(
                            scripts=scripts,
                            layout_type=layout_type,
                            text_density=text_density,
                            degradation_profile=degradation_profile,
                            quality_tier=quality_tier,
                            resolution_tier=resolution_tier,
                        )
                    else:
                        # Fallback to whatever we have
                        scripts = available_scripts[:num_scripts]
                        layout_type = self._select_multi_script_layout(len(scripts))
                        if len(scripts) > 1:
                            sample = self._generate_multi_script_sample(
                                scripts=scripts,
                                layout_type=layout_type,
                                text_density=text_density,
                                degradation_profile=degradation_profile,
                                quality_tier=quality_tier,
                                resolution_tier=resolution_tier,
                            )
                        else:
                            sample = self._generate_single_sample(
                                script_code=scripts[0],
                                layout_type=layout_type,
                                text_density=text_density,
                                degradation_profile=degradation_profile,
                                quality_tier=quality_tier,
                                resolution_tier=resolution_tier,
                            )

                if sample:
                    # Apply post-processing (color mode, char height measurement)
                    # Note: geometric transforms (skew, orientation) are already applied
                    # inside _generate_single_sample/_generate_multi_script_sample BEFORE
                    # augmentation to produce realistic noise patterns.
                    sample = self._apply_post_processing(sample)

                    # Update stats
                    self._stats.total_samples += 1
                    for script_code in sample.scripts:
                        self._stats.samples_per_script[script_code] = (
                            self._stats.samples_per_script.get(script_code, 0) + 1
                        )
                    self._stats.samples_per_layout[sample.layout_type.value] = (
                        self._stats.samples_per_layout.get(sample.layout_type.value, 0)
                        + 1
                    )
                    profile_name = sample.generation_params.get(
                        "degradation_profile", "moderate"
                    )
                    self._stats.samples_per_profile[profile_name] = (
                        self._stats.samples_per_profile.get(profile_name, 0) + 1
                    )

                    # Per-script enforcement: credit the primary script and prune
                    # scripts that have reached their individual target.  Using the
                    # sorted-first script as the primary credit mirrors _save_sample's
                    # directory assignment logic so the counter stays consistent.
                    primary_script = sorted(sample.scripts)[0]
                    if primary_script in per_script_counts:
                        per_script_counts[primary_script] += 1
                        if per_script_counts[primary_script] >= script_target:
                            available_scripts = [
                                s for s in available_scripts if s != primary_script
                            ]
                            logger.debug(
                                "Script %s reached target %d; removed from pool "
                                "(%d scripts remaining)",
                                primary_script,
                                script_target,
                                len(available_scripts),
                            )

                    # Save if configured
                    if self.config.save_images and self.config.output_dir:
                        self._save_sample(sample)

                    samples_generated += 1
                    yield sample
                else:
                    self._stats.failed_samples += 1

            except Exception as e:
                logger.error("Generation failed: %s", e)
                self._stats.failed_samples += 1
                self._stats.errors.append(str(e))

    def _save_sample(self, sample: GeneratedSample) -> None:
        """Save sample to disk.

        Args:
            sample: Sample to save
        """
        if not self.config.output_dir:
            return

        # Create script subdirectory - use sorted() for deterministic ordering (FIX BUG #4)
        script_code = sorted(sample.scripts)[0]
        script_dir = self.config.output_dir / script_code
        script_dir.mkdir(exist_ok=True)

        # Save image
        image_path = script_dir / f"{sample.sample_id}.{self.config.image_format}"
        sample.image.save(image_path)

        # Save metadata if configured
        if self.config.save_metadata:
            import json

            # Pass augmentation source for proper detection_method tracking (FIX BUG #6)
            metadata = self.schema_adapter.build_enrichment_metadata(
                sample, augmentation_source=self.config.augmenter
            )
            metadata_path = script_dir / f"{sample.sample_id}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

    def generate_batch(
        self,
        scripts: list[str] | None = None,
        count: int = 100,
    ) -> list[GeneratedSample]:
        """Generate a batch of samples.

        Args:
            scripts: Scripts to use (None = use config)
            count: Total samples to generate

        Returns:
            List of GeneratedSample objects
        """
        if not self._initialized:
            raise RuntimeError(_NOT_INITIALIZED_MSG)

        # Temporarily modify config
        original_scripts = self.config.scripts
        original_count = self.config.samples_per_script

        if scripts:
            self.config.scripts = scripts

        # Calculate samples per script
        samples_per = count // len(self.config.scripts)
        self.config.samples_per_script = max(1, samples_per)

        # Generate
        samples = list(self.generate())

        # Restore config
        self.config.scripts = original_scripts
        self.config.samples_per_script = original_count

        return samples[:count]  # Trim to exact count

    def _generate_multi_script_sample(
        self,
        scripts: list[str],
        layout_type: LayoutType,
        text_density: TextDensity,
        degradation_profile: DegradationProfile,
        quality_tier: str = "MEDIUM",
        resolution_tier: str = "MEDIUM",
    ) -> GeneratedSample | None:
        """Generate a multi-script sample with proper layout semantics.

        For HEADER_BODY: first script is header, second is body.
        For COLUMNS: scripts are distributed across columns.
        For INTERLEAVED: scripts alternate in blocks.

        Args:
            scripts: List of ISO 15924 script codes (2-4 scripts)
            layout_type: Layout type to use
            text_density: Text density level
            degradation_profile: Degradation profile
            quality_tier: Quality tier (PRISTINE, HIGH, MEDIUM, LOW, DEGRADED)
            resolution_tier: Resolution tier (LOW, MEDIUM, HIGH)

        Returns:
            GeneratedSample or None if failed
        """
        if not scripts:
            return None

        # Collect text blocks for each script
        text_blocks_data: list[tuple[str, str, str]] = []
        all_scripts: set[str] = set()
        all_languages: list[str] = []

        # Select text direction for each script (v2.3: CJK vertical support)
        script_directions: dict[str, str] = {}

        for script_code in scripts:
            text, language_code = self.corpus_manager.get_text_with_language(
                script_code, text_density
            )
            if text and language_code:
                text_blocks_data.append((text, script_code, language_code))
                all_scripts.add(script_code)
                all_languages.append(language_code)
                script_directions[script_code] = self._select_text_direction(
                    script_code
                )

        if not text_blocks_data:
            logger.warning("No text available for multi-script document")
            return None

        # Get renderer for the appropriate resolution tier
        tier_renderer = self._get_renderer_for_tier(resolution_tier)
        actual_dpi = self._get_resolution_for_tier(resolution_tier)

        # Handle HEADER_BODY specially: first script is header, rest is body
        if layout_type == LayoutType.HEADER_BODY and len(text_blocks_data) >= 2:
            try:
                image, text_blocks = tier_renderer.render_header_body_multi_script(
                    header_data=text_blocks_data[0],
                    body_data=text_blocks_data[1:],
                )
            except AttributeError:
                # Fallback if method not implemented yet
                image, text_blocks = tier_renderer.render_multi_script_document(
                    text_blocks_data, layout_type
                )
        else:
            # Standard multi-script rendering
            try:
                image, text_blocks = tier_renderer.render_multi_script_document(
                    text_blocks_data, layout_type
                )
            except Exception as e:
                logger.error("Multi-script rendering failed: %s", e)
                return None

        # Measure char_height_rendered_px on pristine image BEFORE any transforms
        char_height_rendered = self._measure_char_height_rendered(image)

        # Compute SHA256 of pristine image for split registry integration
        base_image_sha256 = self._compute_image_sha256(image)

        # Capture degradation seed for reproducible replay
        degradation_seed = self._rng.randint(0, 2**31 - 1)

        # Capture the fonts actually used by the renderer (sorted for deterministic metadata)
        sorted_fonts = sorted(tier_renderer.last_rendered_fonts)
        font_families: list[str] = [f for f, _ in sorted_fonts]
        font_styles: list[str] = [s for _, s in sorted_fonts]

        # Apply geometric transforms BEFORE augmentation to avoid "rotated noise"
        # artifacts. Real scanners rotate/skew the physical document, then sensor
        # noise is added - so we must transform geometry on the clean image first.
        image, skew_angle, orientation_class = self._apply_geometric_transforms(image)

        # Apply augmentation (noise, blur, degradation on geometrically-correct image)
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
        document_age: str | None = None
        if is_pristine:
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "albumentations" and ALBUMENTATIONS_AVAILABLE:
            profile_map = {
                DegradationProfile.MILD: AugmentationProfile.LIGHT,
                DegradationProfile.MODERATE: AugmentationProfile.MODERATE,
                DegradationProfile.SEVERE: AugmentationProfile.HEAVY,
                DegradationProfile.FAST: AugmentationProfile.MODERATE,
            }
            alb_profile = profile_map.get(
                degradation_profile, AugmentationProfile.MODERATE
            )
            try:
                degraded_image, fast_labels = self.fast_augmentation.apply(
                    image, alb_profile
                )
                iqa_labels = IQALabels(
                    blur=fast_labels.blur,
                    noise=fast_labels.noise,
                    compression=fast_labels.compression,
                    ink_degradation=fast_labels.ink_degradation,
                    paper_degradation=fast_labels.paper_degradation,
                    geometric_distortion=fast_labels.geometric_distortion,
                    bleed_through=fast_labels.bleed_through,
                    overall_quality=fast_labels.overall_quality,
                )
            except Exception as e:
                logger.warning("Albumentations failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "hybrid" and HYBRID_AVAILABLE:
            # Hybrid mode: Augraphy for document effects + Albumentations for capture effects
            hybrid_profile_map = {
                DegradationProfile.MILD: HybridProfile.LIGHT,
                DegradationProfile.MODERATE: HybridProfile.MODERATE,
                DegradationProfile.SEVERE: HybridProfile.HEAVY,
                DegradationProfile.FAST: HybridProfile.MODERATE,
            }
            hybrid_profile = hybrid_profile_map.get(
                degradation_profile, HybridProfile.MODERATE
            )
            # Randomly apply document aging: 15% AGED, 5% HISTORICAL
            aging_roll = self._rng.random()
            if aging_roll < 0.05:
                hybrid_profile = HybridProfile.HISTORICAL
                document_age = "historical"
            elif aging_roll < 0.20:
                hybrid_profile = HybridProfile.AGED
                document_age = "aged"
            else:
                document_age = "modern"
            try:
                degraded_image, iqa_labels = self.hybrid_augmentation.apply(
                    image, hybrid_profile
                )
            except Exception as e:
                logger.warning("Hybrid augmentation failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        elif self.config.augmenter == "augraphy" and AUGRAPHY_AVAILABLE:
            try:
                degraded_image, iqa_labels = self.augmentation.apply(
                    image, degradation_profile
                )
            except Exception as e:
                logger.warning("Augraphy failed: %s. Using original.", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)
        else:
            # No augmentation available/configured - use original image
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0, noise=0.0, blur=0.0)

        # Create sample
        sample_id = str(uuid.uuid4())
        sample = GeneratedSample(
            image=degraded_image,
            sample_id=sample_id,
            scripts=all_scripts,
            language_codes=all_languages,
            layout_type=layout_type,
            text_density=text_density,
            iqa_labels=iqa_labels,
            text_blocks=text_blocks,
            resolution_dpi=actual_dpi,
            width_px=degraded_image.width,
            height_px=degraded_image.height,
            generation_params={
                "multi_script": True,
                "script_count": len(all_scripts),
                "degradation_profile": degradation_profile.value,
                "layout_type": layout_type.value,
                "text_density": text_density.value,
                "degradation_seed": degradation_seed,
                "base_image_sha256": base_image_sha256,
                "font_families_used": font_families,
                "font_styles_used": font_styles,
            },
            is_pristine=is_pristine,
            resolution_tier=resolution_tier,
            quality_tier=quality_tier,
        )
        if document_age is not None:
            sample.document_age = document_age

        # Store v2.3 metadata
        sample.char_height_rendered_px = char_height_rendered

        # Store text direction metadata (v2.3: CJK vertical support)
        if script_directions:
            sample.text_directions = script_directions

        # Store geometric transform metadata (applied before augmentation)
        if skew_angle is not None:
            sample.skew_angle_degrees = skew_angle
        if orientation_class is not None:
            sample.orientation_class = orientation_class
            sample.width_px = degraded_image.width
            sample.height_px = degraded_image.height

        return sample

    def _apply_degradation(
        self,
        image: PILImageType,
        degradation_profile: DegradationProfile,
    ) -> tuple[PILImageType, IQALabels, bool]:
        """Apply degradation augmentation for multi-script documents.

        Returns (degraded_image, iqa_labels, is_pristine).
        """
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
        if is_pristine or not AUGRAPHY_AVAILABLE:
            return image, IQALabels(overall_quality=1.0), is_pristine
        try:
            degraded_image, iqa_labels = self.augmentation.apply(
                image, degradation_profile
            )
            return degraded_image, iqa_labels, is_pristine
        except Exception as e:
            logger.warning("Augmentation failed: %s", e)
            return image, IQALabels(overall_quality=1.0), is_pristine

    @staticmethod
    def _store_geometric_metadata(
        sample: GeneratedSample,
        skew_angle: float | None,
        orientation_class: int | None,
        degraded_image: PILImageType,
    ) -> None:
        """Store geometric transform metadata on the sample."""
        if skew_angle is not None:
            sample.skew_angle_degrees = skew_angle
        if orientation_class is not None:
            sample.orientation_class = orientation_class
            sample.width_px = degraded_image.width
            sample.height_px = degraded_image.height

    def _collect_multi_script_text(
        self, scripts: list[str]
    ) -> tuple[list[tuple[str, str, str]], set[str], list[str], dict[str, str]]:
        """Collect text blocks, scripts, languages, and directions for multi-script doc."""
        text_blocks_data: list[tuple[str, str, str]] = []
        all_scripts: set[str] = set()
        all_languages: list[str] = []
        script_directions: dict[str, str] = {}

        for script_code in scripts:
            text, language_code = self.corpus_manager.get_text_with_language(
                script_code, TextDensity.MEDIUM
            )
            if text and language_code:
                text_blocks_data.append((text, script_code, language_code))
                all_scripts.add(script_code)
                all_languages.append(language_code)
                script_directions[script_code] = self._select_text_direction(
                    script_code
                )

        return text_blocks_data, all_scripts, all_languages, script_directions

    def _collect_font_families(
        self,
        _all_scripts: set[str],
        renderer: Any | None = None,
    ) -> tuple[list[str], list[str]]:
        """Collect font families and styles actually used during rendering.

        Reads the renderer's ``last_rendered_fonts`` list which is populated
        by ``_load_font`` during each ``render_document`` call, ensuring
        metadata reflects the fonts that were truly rendered.

        Args:
            all_scripts: Set of script codes (kept for API compat, unused).
            renderer: The renderer instance whose tracked fonts to read.
                Falls back to ``self.renderer`` if not provided.

        Returns:
            Tuple of (font_families, font_styles).
        """
        target_renderer = renderer or self.renderer
        if (
            hasattr(target_renderer, "last_rendered_fonts")
            and target_renderer.last_rendered_fonts
        ):
            return (
                [f for f, _ in target_renderer.last_rendered_fonts],
                [s for _, s in target_renderer.last_rendered_fonts],
            )
        return [], []

    def generate_multi_script_document(
        self,
        scripts: list[str],
        layout_type: LayoutType = LayoutType.COLUMNS,
        degradation_profile: DegradationProfile = DegradationProfile.MODERATE,
    ) -> GeneratedSample | None:
        """Generate a document with multiple scripts.

        Args:
            scripts: List of ISO 15924 script codes to include
            layout_type: Layout type to use
            degradation_profile: Degradation profile

        Returns:
            GeneratedSample or None if failed
        """
        if not self._initialized:
            raise RuntimeError(_NOT_INITIALIZED_MSG)

        text_blocks_data, all_scripts, all_languages, script_directions = (
            self._collect_multi_script_text(scripts)
        )

        if not text_blocks_data:
            logger.error("No text available for any of the requested scripts")
            return None

        # Render multi-script document
        try:
            image, text_blocks = self.renderer.render_multi_script_document(
                text_blocks_data, layout_type
            )
        except Exception as e:
            logger.error("Multi-script rendering failed: %s", e)
            return None

        # Measure char_height_rendered_px on pristine image BEFORE any transforms
        char_height_rendered = self._measure_char_height_rendered(image)
        base_image_sha256 = self._compute_image_sha256(image)
        degradation_seed = self._rng.randint(0, 2**31 - 1)
        font_families, font_styles = self._collect_font_families(all_scripts)

        # Apply geometric transforms BEFORE augmentation to avoid "rotated noise"
        image, skew_angle, orientation_class = self._apply_geometric_transforms(image)

        # Apply augmentation
        degraded_image, iqa_labels, is_pristine = self._apply_degradation(
            image, degradation_profile
        )

        # Create sample
        sample = GeneratedSample(
            image=degraded_image,
            sample_id=str(uuid.uuid4()),
            scripts=all_scripts,
            language_codes=all_languages,
            layout_type=layout_type,
            text_density=TextDensity.MEDIUM,
            iqa_labels=iqa_labels,
            text_blocks=text_blocks,
            resolution_dpi=300,
            width_px=degraded_image.width,
            height_px=degraded_image.height,
            generation_params={
                "multi_script": True,
                "scripts": list(all_scripts),
                "degradation_profile": degradation_profile.value,
                "degradation_seed": degradation_seed,
                "base_image_sha256": base_image_sha256,
                "font_families_used": font_families,
                "font_styles_used": font_styles,
            },
            is_pristine=is_pristine,
        )

        # Store v2.3 metadata
        sample.char_height_rendered_px = char_height_rendered
        if script_directions:
            sample.text_directions = script_directions
        self._store_geometric_metadata(
            sample, skew_angle, orientation_class, degraded_image
        )

        return sample

    def get_statistics(self) -> GenerationStats:
        """Get generation statistics.

        Returns:
            GenerationStats from the last generation run
        """
        return self._stats

    def get_available_scripts(self) -> list[str]:
        """Get scripts with available corpus and fonts.

        Returns:
            List of ISO 15924 script codes
        """
        corpus_scripts = set(self.corpus_manager.get_available_scripts())
        font_scripts = set(self.font_manager.get_available_scripts())
        return sorted(corpus_scripts & font_scripts)


__all__ = [
    "GenerationConfig",
    "GenerationStats",
    "MultiScriptDocumentGenerator",
]
