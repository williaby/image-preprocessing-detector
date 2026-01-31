# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
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
    DOCUMENT_COMPOSITION_WEIGHTS,
    LAYOUT_WEIGHTS,
    MVP_SCRIPTS,
    QUALITY_TIER_WEIGHTS,
    RESOLUTION_TIER_WEIGHTS,
    RESOLUTION_TIERS,
    SCRIPT_CONFIGS,
    TEXT_DENSITY_WEIGHTS,
    TWO_SCRIPT_COMBINATIONS,
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
    pass

logger = logging.getLogger(__name__)


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

    scripts: list[str] = field(default_factory=lambda: list(MVP_SCRIPTS))
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

            if loaded == 0:
                logger.warning("No corpus data loaded. Text generation may be limited.")
        except Exception as e:
            logger.error("Failed to initialize corpus: %s", e)
            return False

        # Initialize fonts
        logger.info("Scanning fonts...")
        try:
            if scan_fonts:
                found = self.font_manager.scan_fonts()
                if found == 0:
                    logger.warning(
                        "No fonts found. Install Noto fonts for best results."
                    )
        except Exception as e:
            logger.error("Failed to scan fonts: %s", e)
            return False

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
        return self._select_weighted(QUALITY_TIER_WEIGHTS)

    def _select_resolution_tier(self) -> str:
        """Select a resolution tier based on configured distribution."""
        return self._select_weighted(RESOLUTION_TIER_WEIGHTS)

    def _select_composition_type(self) -> str:
        """Select document composition type (single, two, three, four_plus, priority_pairs)."""
        return self._select_weighted(DOCUMENT_COMPOSITION_WEIGHTS)

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
            return self._select_weighted(valid_pairs)

        # Fallback: random pair from available scripts
        if len(available_scripts) >= 2:
            pair = self._rng.sample(available_scripts, 2)
            return (pair[0], pair[1])

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
            layouts = [
                LayoutType.HEADER_BODY,
                LayoutType.COLUMNS,
                LayoutType.INTERLEAVED,
            ]
            weights = [0.4, 0.4, 0.2]  # Favor structured layouts
            return self._rng.choices(layouts, weights=weights, k=1)[0]
        if num_scripts == 3:
            # Three scripts: COLUMNS or INTERLEAVED
            layouts = [LayoutType.COLUMNS, LayoutType.INTERLEAVED, LayoutType.STACKED]
            weights = [0.4, 0.3, 0.3]
            return self._rng.choices(layouts, weights=weights, k=1)[0]
        # Four+ scripts: INTERLEAVED or STACKED
        layouts = [LayoutType.INTERLEAVED, LayoutType.STACKED]
        weights = [0.6, 0.4]
        return self._rng.choices(layouts, weights=weights, k=1)[0]

    def _get_resolution_for_tier(self, tier: str) -> int:
        """Get target DPI for a resolution tier.

        Args:
            tier: Resolution tier (LOW, MEDIUM, HIGH)

        Returns:
            Target DPI value
        """
        tier_config = RESOLUTION_TIERS.get(tier, RESOLUTION_TIERS["MEDIUM"])
        return tier_config["target_dpi"]

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

        # Get renderer for the appropriate resolution tier
        tier_renderer = self._get_renderer_for_tier(resolution_tier)
        actual_dpi = self._get_resolution_for_tier(resolution_tier)

        # Render document at tier-specific DPI
        try:
            image, text_blocks = tier_renderer.render_document(
                text=text,
                script_code=script_code,
                language_code=language_code,
                layout_type=layout_type,
                text_density=text_density,
            )
        except Exception as e:
            logger.error("Rendering failed for %s: %s", script_code, e)
            return None

        # Apply augmentation
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
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
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0)

        # Create sample
        sample_id = str(uuid.uuid4())
        return GeneratedSample(
            image=degraded_image,
            sample_id=sample_id,
            scripts={script_code},
            language_codes=[language_code],
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
            },
            is_pristine=is_pristine,
            resolution_tier=resolution_tier,
            quality_tier=quality_tier,
        )

    def generate(self) -> Iterator[GeneratedSample]:
        """Generate samples according to configuration.

        Uses DOCUMENT_COMPOSITION_WEIGHTS to determine single vs multi-script:
        - single (35%): Pure single-script documents
        - two (45%): Bilingual documents (uses TWO_SCRIPT_COMBINATIONS weights)
        - three (12%): Three-script documents
        - four_plus (3%): Four+ script documents
        - priority_pairs (5%): High-priority script combinations

        Yields:
            GeneratedSample objects
        """
        if not self._initialized:
            raise RuntimeError("Generator not initialized. Call initialize() first.")

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
                    # Three-script document
                    if len(available_scripts) >= 3:
                        scripts = self._rng.sample(available_scripts, 3)
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
            raise RuntimeError("Generator not initialized. Call initialize() first.")

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

        for script_code in scripts:
            text, language_code = self.corpus_manager.get_text_with_language(
                script_code, text_density
            )
            if text and language_code:
                text_blocks_data.append((text, script_code, language_code))
                all_scripts.add(script_code)
                all_languages.append(language_code)

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

        # Apply augmentation
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
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
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0)

        # Create sample
        sample_id = str(uuid.uuid4())
        return GeneratedSample(
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
            },
            is_pristine=is_pristine,
            resolution_tier=resolution_tier,
            quality_tier=quality_tier,
        )

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
            raise RuntimeError("Generator not initialized. Call initialize() first.")

        # Collect text blocks for each script
        text_blocks_data: list[tuple[str, str, str]] = []
        all_scripts: set[str] = set()
        all_languages: list[str] = []

        for script_code in scripts:
            text, language_code = self.corpus_manager.get_text_with_language(
                script_code, TextDensity.MEDIUM
            )
            if text and language_code:
                text_blocks_data.append((text, script_code, language_code))
                all_scripts.add(script_code)
                all_languages.append(language_code)

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

        # Apply augmentation
        is_pristine = degradation_profile == DegradationProfile.PRISTINE
        if is_pristine or not AUGRAPHY_AVAILABLE:
            degraded_image = image
            iqa_labels = IQALabels(overall_quality=1.0)
        else:
            try:
                degraded_image, iqa_labels = self.augmentation.apply(
                    image, degradation_profile
                )
            except Exception as e:
                logger.warning("Augmentation failed: %s", e)
                degraded_image = image
                iqa_labels = IQALabels(overall_quality=1.0)

        # Create sample
        return GeneratedSample(
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
            },
            is_pristine=is_pristine,
        )

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
