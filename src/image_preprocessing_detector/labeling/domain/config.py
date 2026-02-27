"""Configuration for domain classification and metadata enrichment pipeline.

Defines model configurations, confidence thresholds, and pipeline settings
for OpenRouter-based LLM enrichment.

Example:
    >>> from image_preprocessing_detector.labeling.domain.config import (
    ...     DomainPipelineConfig,
    ...     get_default_config,
    ... )
    >>> config = get_default_config()
    >>> print(config.primary_text_model.model_id)
    'deepseek/deepseek-r1-0528:free'
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Domain taxonomy codes (mirrors DomainLevel1 enum in annotation.schemas.enums)
VALID_DOMAIN_CODES: frozenset[str] = frozenset(
    {
        "TAX",
        "LEG",
        "FIN",
        "TEC",
        "SCI",
        "ADM",
        "MED",
        "EDU",
        "PER",
        "UNK",
    }
)

# Capture method values (mirrors CaptureMethod enum)
VALID_CAPTURE_METHODS: frozenset[str] = frozenset(
    {
        "born_digital",
        "scanner_flatbed",
        "scanner_adf",
        "camera_professional",
        "camera_smartphone",
        "fax",
        "synthetic",
        "unknown",
    }
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Common model ID constants (S1192: avoid duplicate string literals)
GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
GEMINI_FLASH_LITE_MODEL = "google/gemini-2.0-flash-lite-001"


@dataclass(frozen=True)
class DomainModelConfig:
    """Configuration for a single OpenRouter model.

    Attributes:
        model_id: OpenRouter model identifier (e.g., 'deepseek/deepseek-r1-0528:free').
        role: Model role in the pipeline ('primary_text', 'secondary_text',
            'primary_vision', 'secondary_vision').
        max_tokens: Maximum output tokens per request.
        temperature: Sampling temperature (0.0 for deterministic).
        supports_vision: Whether the model accepts image input.
    """

    model_id: str
    role: str
    max_tokens: int = 2000
    temperature: float = 0.0
    supports_vision: bool = False


@dataclass(frozen=True)
class DomainPipelineConfig:
    """Pipeline configuration for domain classification and metadata enrichment.

    Attributes:
        primary_text_model: Primary text-only model (free).
        secondary_text_model: Fallback text model for low confidence (free).
        primary_vision_model: Primary vision model for image-only samples (paid).
        secondary_vision_model: Fallback vision model (paid).
        text_confidence_threshold: Minimum confidence to accept primary text result.
        vision_confidence_threshold: Minimum confidence to accept primary vision result.
        text_truncation_chars: Max characters of sample text to include in prompt.
        image_max_pixels: Max dimension for image resizing before API call.
        rate_limit_delay: Seconds to wait between API calls.
        max_retries: Maximum retry attempts per API call.
        retry_base_delay: Base delay for exponential backoff (seconds).
        openrouter_base_url: OpenRouter API base URL.
        openrouter_api_key: API key (loaded from env if not provided).
        http_referer: HTTP-Referer header for OpenRouter (best practice).
        app_title: X-Title header for OpenRouter (best practice).
    """

    primary_text_model: DomainModelConfig = field(
        default_factory=lambda: DomainModelConfig(
            model_id=GEMINI_FLASH_MODEL,
            role="primary_text",
        )
    )
    secondary_text_model: DomainModelConfig = field(
        default_factory=lambda: DomainModelConfig(
            model_id=GEMINI_FLASH_LITE_MODEL,
            role="secondary_text",
        )
    )
    primary_vision_model: DomainModelConfig = field(
        default_factory=lambda: DomainModelConfig(
            model_id=GEMINI_FLASH_MODEL,
            role="primary_vision",
            supports_vision=True,
        )
    )
    secondary_vision_model: DomainModelConfig = field(
        default_factory=lambda: DomainModelConfig(
            model_id=GEMINI_FLASH_LITE_MODEL,
            role="secondary_vision",
            supports_vision=True,
        )
    )

    text_confidence_threshold: float = 0.85
    vision_confidence_threshold: float = 0.80
    text_truncation_chars: int = 4000
    image_max_pixels: int = 1024
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    retry_base_delay: float = 1.0

    openrouter_base_url: str = OPENROUTER_BASE_URL
    openrouter_api_key: str | None = None
    http_referer: str = "https://github.com/image-preprocessing-detector"
    app_title: str = "image-preprocessing-detector"

    def get_api_key(self) -> str:
        """Resolve API key from config or environment.

        Returns:
            OpenRouter API key.

        Raises:
            ValueError: If no API key found.
        """
        key = self.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            msg = (
                "OpenRouter API key not found. Set OPENROUTER_API_KEY "
                "environment variable or pass openrouter_api_key in config."
            )
            raise ValueError(msg)
        return key


@dataclass
class EnrichmentResult:
    """Result from a single sample enrichment API call.

    Contains all extracted metadata fields. Fields that require vision
    (capture_method, content flags) are None for text-only classification.

    Attributes:
        domain_level1: Primary domain code (3-letter, from DomainLevel1 enum).
        domain_confidence: Classification confidence (0.0-1.0).
        iso639_language: ISO 639-1/3 language code (e.g., 'en', 'ar').
        iso15924_script: ISO 15924 script code (e.g., 'Latn', 'Arab').
        content_type: Content type classification (e.g., 'scientific_paper').
        capture_method: Capture method (vision-only, CaptureMethod value).
        has_table: Table presence flag (vision-only).
        has_formula: Formula/equation presence flag (vision-only).
        has_handwriting: Handwriting presence flag (vision-only).
        has_signature: Signature presence flag (vision-only).
        has_figure: Figure/chart presence flag (vision-only).
        orientation: Page orientation (vision-only, 'portrait'/'landscape').
        reasoning: Model's reasoning for classification.
        model_used: OpenRouter model ID used for classification.
        tokens_used: Total tokens consumed by the API call.
        input_mode: Input type used ('text' or 'vision').
        escalated: Whether the result was escalated to a secondary model.
    """

    domain_level1: str
    domain_confidence: float
    iso639_language: str | None = None
    iso15924_script: str | None = None
    content_type: str | None = None
    capture_method: str | None = None
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None
    has_figure: bool | None = None
    orientation: str | None = None
    reasoning: str = ""
    model_used: str = ""
    tokens_used: int = 0
    input_mode: str = "text"
    escalated: bool = False


def get_default_config() -> DomainPipelineConfig:
    """Create default pipeline configuration.

    Returns:
        DomainPipelineConfig with default model roster and thresholds.
    """
    return DomainPipelineConfig()


# All available text models (user-specified, all free)
AVAILABLE_TEXT_MODELS: list[DomainModelConfig] = [
    DomainModelConfig(model_id="deepseek/deepseek-r1-0528:free", role="primary_text"),
    DomainModelConfig(
        model_id="meta-llama/llama-3.3-70b-instruct:free", role="secondary_text"
    ),
    DomainModelConfig(model_id="stepfun/step-3.5-flash:free", role="alternate_text"),
    DomainModelConfig(model_id="qwen/qwen3-coder:free", role="alternate_text"),
    DomainModelConfig(
        model_id="nvidia/nemotron-3-nano-30b-a3b:free", role="alternate_text"
    ),
    DomainModelConfig(model_id="z-ai/glm-4.5-air:free", role="alternate_text"),
    DomainModelConfig(model_id="tngtech/tng-r1t-chimera:free", role="alternate_text"),
]

# Available vision models (paid)
AVAILABLE_VISION_MODELS: list[DomainModelConfig] = [
    DomainModelConfig(
        model_id=GEMINI_FLASH_MODEL,
        role="primary_vision",
        supports_vision=True,
    ),
    DomainModelConfig(
        model_id=GEMINI_FLASH_LITE_MODEL,
        role="alternate_vision",
        supports_vision=True,
    ),
    DomainModelConfig(
        model_id="qwen/qwen2.5-vl-3b-instruct",
        role="secondary_vision",
        supports_vision=True,
    ),
]
