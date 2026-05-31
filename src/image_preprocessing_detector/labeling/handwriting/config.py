"""Configuration for handwriting legibility multi-model VLM scoring.

Provides model roster and pipeline settings for contact-sheet-based
legibility assessment using OpenRouter vision models.

Example:
    >>> from image_preprocessing_detector.labeling.handwriting.config import (
    ...     get_default_config,
    ... )
    >>> cfg = get_default_config()
    >>> print(cfg.sheet_cols, cfg.sheet_rows)
    4 3
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# ──────────────────────────────────────────────
# Valid enum values (mirrors Layer 2 schema)
# ──────────────────────────────────────────────

VALID_PRESENCE_CLASSES: frozenset[str] = frozenset(
    {"NONE", "MARGINAL", "PARTIAL", "SUBSTANTIAL", "DOMINANT"}
)

VALID_LEGIBILITY_CLASSES: frozenset[str] = frozenset(
    {"NOT_APPLICABLE", "ILLEGIBLE", "POOR", "FAIR", "GOOD", "EXCELLENT"}
)

# Legibility class → continuous score midpoint (for ordering / fallback mapping)
LEGIBILITY_CLASS_TO_SCORE: dict[str, float | None] = {
    "NOT_APPLICABLE": None,
    "ILLEGIBLE": 0.08,
    "POOR": 0.25,
    "FAIR": 0.50,
    "GOOD": 0.75,
    "EXCELLENT": 0.92,
}

# Conservative ordering index used for tie-breaking (lower = worse quality)
LEGIBILITY_CLASS_ORDER: dict[str, int] = {
    "NOT_APPLICABLE": -1,
    "ILLEGIBLE": 0,
    "POOR": 1,
    "FAIR": 2,
    "GOOD": 3,
    "EXCELLENT": 4,
}

PRESENCE_CLASS_ORDER: dict[str, int] = {
    "NONE": 0,
    "MARGINAL": 1,
    "PARTIAL": 2,
    "SUBSTANTIAL": 3,
    "DOMINANT": 4,
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Prompt version tag embedded in L2 metadata for audit trail
PROMPT_VERSION = "hw-legibility-v1.0"


@dataclass(frozen=True)
class HwVisionModelConfig:
    """Configuration for a single OpenRouter vision model.

    Attributes:
        model_id (str): OpenRouter model identifier.
        max_tokens (int): Maximum output tokens per request.
        weight (float): Relative weight when computing weighted consensus (1.0 = equal).
    """

    model_id: str
    max_tokens: int = 1024
    weight: float = 1.0


@dataclass(frozen=True)
class LegibilityScorerConfig:
    """Pipeline configuration for handwriting legibility VLM scoring.

    Attributes:
        vision_models (tuple[HwVisionModelConfig, ...]): Ordered list of vision models to query per sheet.
        sheet_cols (int): Number of columns in the contact sheet grid.
        sheet_rows (int): Number of rows in the contact sheet grid.
        cell_width_px (int): Width of each cell thumbnail in pixels.
        sheet_jpeg_quality (int): JPEG quality for saved contact sheets (1-95).
        label_font_size (int): Font size for the "#N" cell badge overlay.
        image_max_pixels (int): Max dimension for sheet resizing before API call.
        disagreement_threshold (float): Std dev above which a score is flagged.
        min_model_responses (int): Minimum valid model responses required for consensus.
        rate_limit_delay (float): Seconds to wait between API calls.
        max_retries (int): Maximum retry attempts per API call.
        retry_base_delay (float): Base delay for exponential backoff (seconds).
        openrouter_base_url (str): OpenRouter API base URL.
        openrouter_api_key (str | None): API key (loaded from env if None).
        http_referer (str): HTTP-Referer header for OpenRouter.
        app_title (str): X-Title header for OpenRouter.
    """

    vision_models: tuple[HwVisionModelConfig, ...] = field(
        default_factory=lambda: (
            HwVisionModelConfig(
                model_id="google/gemini-2.0-flash-001",
                weight=1.0,
            ),
            HwVisionModelConfig(
                model_id="google/gemini-2.0-flash-lite-001",
                weight=0.8,
            ),
            HwVisionModelConfig(
                model_id="qwen/qwen2.5-vl-7b-instruct",
                weight=0.8,
            ),
        )
    )

    # Contact sheet geometry
    sheet_cols: int = 4
    sheet_rows: int = 3
    cell_width_px: int = 512
    sheet_jpeg_quality: int = 85

    # Cell label overlay
    label_font_size: int = 20

    # API settings
    image_max_pixels: int = 2048
    disagreement_threshold: float = 0.20
    min_model_responses: int = 2
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    retry_base_delay: float = 1.0

    openrouter_base_url: str = OPENROUTER_BASE_URL
    openrouter_api_key: str | None = None
    http_referer: str = "https://github.com/image-preprocessing-detector"
    app_title: str = "image-preprocessing-detector"

    @property
    def images_per_sheet(self) -> int:
        """Total number of image slots in one contact sheet."""
        return self.sheet_cols * self.sheet_rows

    def get_api_key(self) -> str:
        """Resolve API key from config or environment.

        Returns:
            str:             OpenRouter API key string.

        Raises:
            ValueError: If no API key is found in config or environment.
        """
        key = self.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            msg = (
                "OpenRouter API key not found. Set OPENROUTER_API_KEY "
                "environment variable or pass openrouter_api_key in config."
            )
            raise ValueError(msg)
        return key


def get_default_config() -> LegibilityScorerConfig:
    """Create default pipeline configuration with 3-model roster.

    Returns:
        LegibilityScorerConfig:         LegibilityScorerConfig with production defaults.
    """
    return LegibilityScorerConfig()
