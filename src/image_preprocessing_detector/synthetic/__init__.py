"""Synthetic document generation module for multi-script training data.

This module provides tools for generating synthetic document images
with multi-script text and controlled degradations for training
SigLIP and other vision models on script identification tasks.

Key Features:
    - Support for 27 ISO 15924 scripts (Latin, CJK, Arabic, Indic, etc.)
    - Integration with OpenLID-v2 (200+ languages) for text corpus
    - Augraphy-based document degradation with IQA labels
    - Layer 2 schema-compatible output for annotation system
    - Noto font discovery and management
    - 11 layout types for document rendering
    - 4 degradation profiles (pristine, mild, moderate, severe)

Usage:
    >>> from image_preprocessing_detector.synthetic import (
    ...     MultiScriptDocumentGenerator,
    ...     GenerationConfig,
    ...     DegradationProfile,
    ... )
    >>>
    >>> # Configure and initialize generator
    >>> config = GenerationConfig(
    ...     scripts=["Arab", "Latn", "Deva"],
    ...     samples_per_script=100,
    ... )
    >>> generator = MultiScriptDocumentGenerator(config)
    >>> generator.initialize()
    >>>
    >>> # Generate samples
    >>> for sample in generator.generate():
    ...     sample.image.save(f"output/{sample.sample_id}.png")

Module Structure:
    config.py
        ScriptConfig, LayoutType, TextDensity, SCRIPT_CONFIGS
    corpus.py
        TextCorpusManager, TextSample, ScriptCorpus
    fonts.py
        FontManager, FontInfo, FontCache
    renderer.py
        DocumentRenderer, RenderRegion, RenderState
    augmentation.py
        AugmentationPipeline, DegradationProfile
    schema_adapter.py
        Layer2SchemaAdapter, IQALabels, GeneratedSample, TextBlock
    generator.py
        MultiScriptDocumentGenerator, GenerationConfig, GenerationStats

Dependencies:
    - pillow: Image rendering
    - datasets: OpenLID-v2 access (optional, for downloading)
    - augraphy: Document degradation (optional, for augmentation)

System Requirements:
    - libraqm: Required for complex script rendering (Arabic, Devanagari, etc.)
      Install: apt-get install libraqm-dev (Ubuntu) or brew install libraqm (macOS)
    - Noto fonts: Recommended for comprehensive script coverage
"""

from image_preprocessing_detector.synthetic.augmentation import (
    AUGRAPHY_AVAILABLE,
    AugmentationPipeline,
    DegradationProfile,
)
from image_preprocessing_detector.synthetic.config import (
    DENSITY_TO_LAYER2,
    LAYOUT_TO_LAYER2,
    MVP_SCRIPTS,
    SCRIPT_CONFIGS,
    LayoutType,
    ScriptConfig,
    TextDensity,
    get_complex_scripts,
    get_rtl_scripts,
    get_script_config,
    get_scripts_by_family,
)
from image_preprocessing_detector.synthetic.corpus import (
    DENSITY_CHAR_RANGES,
    ScriptCorpus,
    TextCorpusManager,
    TextSample,
)
from image_preprocessing_detector.synthetic.fonts import (
    FONT_SEARCH_PATHS,
    FontCache,
    FontInfo,
    FontManager,
)
from image_preprocessing_detector.synthetic.generator import (
    GenerationConfig,
    GenerationStats,
    MultiScriptDocumentGenerator,
)
from image_preprocessing_detector.synthetic.renderer import (
    DEFAULT_DPI,
    DEFAULT_MARGINS,
    DEFAULT_PAGE_SIZE,
    DocumentRenderer,
    RenderRegion,
    RenderState,
)
from image_preprocessing_detector.synthetic.schema_adapter import (
    IQA_TO_DEGRADATION_MAPPING,
    GeneratedSample,
    IQALabels,
    Layer2SchemaAdapter,
    TextBlock,
    numeric_to_categorical_severity,
)

__all__ = [
    "AUGRAPHY_AVAILABLE",
    "DEFAULT_DPI",
    "DEFAULT_MARGINS",
    "DEFAULT_PAGE_SIZE",
    "DENSITY_CHAR_RANGES",
    "DENSITY_TO_LAYER2",
    "FONT_SEARCH_PATHS",
    "IQA_TO_DEGRADATION_MAPPING",
    "LAYOUT_TO_LAYER2",
    "MVP_SCRIPTS",
    "SCRIPT_CONFIGS",
    "AugmentationPipeline",
    "DegradationProfile",
    "DocumentRenderer",
    "FontCache",
    "FontInfo",
    "FontManager",
    "GeneratedSample",
    "GenerationConfig",
    "GenerationStats",
    "IQALabels",
    "Layer2SchemaAdapter",
    "LayoutType",
    "MultiScriptDocumentGenerator",
    "RenderRegion",
    "RenderState",
    "ScriptConfig",
    "ScriptCorpus",
    "TextBlock",
    "TextCorpusManager",
    "TextDensity",
    "TextSample",
    "get_complex_scripts",
    "get_rtl_scripts",
    "get_script_config",
    "get_scripts_by_family",
    "numeric_to_categorical_severity",
]
