# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""OpenRouter API client for domain classification and metadata enrichment.

Uses the OpenAI SDK with a custom base URL to communicate with OpenRouter's
OpenAI-compatible API. Supports both text-only and vision (image) requests.

Example:
    >>> from image_preprocessing_detector.labeling.domain.openrouter_client import (
    ...     OpenRouterClient,
    ... )
    >>> from image_preprocessing_detector.labeling.domain.config import (
    ...     get_default_config,
    ... )
    >>> client = OpenRouterClient(get_default_config())
    >>> result = client.classify_text(
    ...     "This research paper...", "deepseek/deepseek-r1-0528:free"
    ... )
    >>> print(result.domain_level1, result.domain_confidence)
    SCI 0.95
"""

from __future__ import annotations

import base64
import io
import json
import re
import time
from pathlib import Path
from typing import Any

import structlog

from image_preprocessing_detector.labeling.domain.config import (
    VALID_CAPTURE_METHODS,
    VALID_DOMAIN_CODES,
    DomainPipelineConfig,
    EnrichmentResult,
)
from image_preprocessing_detector.labeling.domain.prompts import (
    build_text_prompt,
    build_vision_prompt,
)

logger = structlog.get_logger(__name__)


class OpenRouterError(Exception):
    """Base exception for OpenRouter client errors."""


class OpenRouterClient:
    """Client for OpenRouter API calls using OpenAI-compatible interface.

    Handles text classification and vision classification with retry logic,
    rate limiting, and structured JSON response parsing.

    Attributes:
        config: Pipeline configuration with model settings and thresholds.
    """

    def __init__(self, config: DomainPipelineConfig) -> None:
        """Initialize the OpenRouter client.

        Args:
            config: Pipeline configuration.
        """
        self._config = config
        self._client: Any = None
        self._total_tokens = 0
        self._total_calls = 0

    def _ensure_client(self) -> Any:
        """Lazily initialize the OpenAI client.

        Returns:
            Initialized OpenAI client.

        Raises:
            OpenRouterError: If openai library is not installed.
        """
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            msg = (
                "openai library required for OpenRouter integration. "
                "Install with: pip install openai"
            )
            raise OpenRouterError(msg) from exc

        api_key = self._config.get_api_key()
        self._client = OpenAI(
            api_key=api_key,
            base_url=self._config.openrouter_base_url,
            default_headers={
                "HTTP-Referer": self._config.http_referer,
                "X-Title": self._config.app_title,
            },
        )
        return self._client

    def classify_text(
        self,
        text: str,
        model_id: str,
    ) -> EnrichmentResult:
        """Classify a document from its text content.

        Args:
            text: Document text to classify.
            model_id: OpenRouter model identifier.

        Returns:
            EnrichmentResult with domain, language, script, and content type.

        Raises:
            OpenRouterError: If all retries fail.
        """
        messages = build_text_prompt(text, self._config.text_truncation_chars)
        raw = self._call_with_retry(model_id, messages)
        return _parse_text_response(raw, model_id)

    def classify_image(
        self,
        image_path: Path,
        model_id: str,
    ) -> EnrichmentResult:
        """Classify a document from its image.

        Args:
            image_path: Path to the document image file.
            model_id: OpenRouter model identifier (must support vision).

        Returns:
            EnrichmentResult with all fields (domain, language, capture, flags).

        Raises:
            OpenRouterError: If all retries fail or image cannot be loaded.
        """
        image_b64 = self._encode_image(image_path)
        messages = build_vision_prompt()

        # Append image to user message content list
        user_content = messages[1]["content"]
        if isinstance(user_content, list):
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "low",
                    },
                }
            )

        raw = self._call_with_retry(model_id, messages)
        return _parse_vision_response(raw, model_id)

    def _call_with_retry(
        self,
        model_id: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Make an API call with exponential backoff retry.

        Args:
            model_id: OpenRouter model identifier.
            messages: Chat messages to send.

        Returns:
            Parsed JSON response dict from the model.

        Raises:
            OpenRouterError: If all retries exhausted.
        """
        client = self._ensure_client()
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=self._config.primary_text_model.max_tokens,
                    temperature=0.0,
                )

                # Handle provider errors (502, empty choices)
                if not response.choices:
                    error_info = getattr(response, "error", None)
                    error_msg = (
                        error_info.get("message", "Unknown")
                        if isinstance(error_info, dict)
                        else str(error_info or "No choices returned")
                    )
                    msg = f"Provider error: {error_msg}"
                    raise OpenRouterError(msg)  # noqa: TRY301

                # Track usage
                if response.usage:
                    tokens = response.usage.total_tokens
                    self._total_tokens += tokens
                self._total_calls += 1

                # Extract response text
                content = response.choices[0].message.content or ""
                if not content.strip():
                    msg = "Model returned empty content (reasoning may have exhausted token budget)"
                    raise OpenRouterError(msg)  # noqa: TRY301
                parsed = _extract_json(content)

                logger.debug(
                    "openrouter_call_success",
                    model=model_id,
                    attempt=attempt + 1,
                    tokens=response.usage.total_tokens if response.usage else 0,
                )
                return parsed  # noqa: TRY300

            except Exception as exc:
                last_error = exc
                delay = self._config.retry_base_delay * (2**attempt)
                logger.warning(
                    "openrouter_call_failed",
                    model=model_id,
                    attempt=attempt + 1,
                    max_retries=self._config.max_retries,
                    delay=delay,
                    error=str(exc),
                )
                if attempt < self._config.max_retries - 1:
                    time.sleep(delay)

        msg = f"All {self._config.max_retries} retries failed for {model_id}"
        raise OpenRouterError(msg) from last_error

    def _encode_image(self, image_path: Path) -> str:
        """Load and encode an image as base64 PNG.

        Resizes images exceeding max_pixels to fit within bounds.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64-encoded PNG string.

        Raises:
            OpenRouterError: If image cannot be loaded.
        """
        try:
            from PIL import Image as PILImage
        except ImportError as exc:
            msg = "Pillow library required for image encoding"
            raise OpenRouterError(msg) from exc

        try:
            with PILImage.open(image_path) as img:
                # Resize if too large
                max_px = self._config.image_max_pixels
                if max(img.size) > max_px:
                    ratio = max_px / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size)

                # Convert to RGB if necessary (handles RGBA, palette, etc.)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return base64.b64encode(buf.getvalue()).decode()

        except Exception as exc:
            msg = f"Failed to load image: {image_path}"
            raise OpenRouterError(msg) from exc

    def get_usage_stats(self) -> dict[str, Any]:
        """Get cumulative API usage statistics.

        Returns:
            Dict with total_tokens and total_calls.
        """
        return {
            "total_tokens": self._total_tokens,
            "total_calls": self._total_calls,
        }


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON object from model response text.

    Handles common LLM response patterns:
    - Clean JSON
    - JSON wrapped in markdown code blocks (```json ... ```)
    - JSON with leading/trailing text

    Args:
        text: Raw model response text.

    Returns:
        Parsed JSON dict.

    Raises:
        OpenRouterError: If no valid JSON found.
    """
    # Try direct parse first
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try extracting first {...} block
    brace_match = re.search(r"\{[^{}]*\}", stripped, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try extracting nested {...} block (allows one level of nesting)
    nested_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", stripped, re.DOTALL)
    if nested_match:
        try:
            return json.loads(nested_match.group(0))
        except json.JSONDecodeError:
            pass

    msg = f"Could not extract valid JSON from response: {text[:200]}"
    raise OpenRouterError(msg)


def _parse_text_response(
    raw: dict[str, Any],
    model_id: str,
) -> EnrichmentResult:
    """Parse text model response into EnrichmentResult.

    Args:
        raw: Parsed JSON dict from model response.
        model_id: Model that produced the response.

    Returns:
        EnrichmentResult with text-extractable fields populated.
    """
    domain = str(raw.get("domain", "UNK")).upper().strip()
    if domain not in VALID_DOMAIN_CODES:
        domain = "UNK"

    confidence = _clamp_confidence(raw.get("domain_confidence", 0.5))

    return EnrichmentResult(
        domain_level1=domain,
        domain_confidence=confidence,
        iso639_language=_safe_str(raw.get("iso639_language")),
        iso15924_script=_safe_str(raw.get("iso15924_script")),
        content_type=_safe_str(raw.get("content_type")),
        reasoning=str(raw.get("reasoning", "")),
        model_used=model_id,
        input_mode="text",
    )


def _parse_vision_response(
    raw: dict[str, Any],
    model_id: str,
) -> EnrichmentResult:
    """Parse vision model response into EnrichmentResult.

    Args:
        raw: Parsed JSON dict from model response.
        model_id: Model that produced the response.

    Returns:
        EnrichmentResult with all fields populated (text + vision).
    """
    domain = str(raw.get("domain", "UNK")).upper().strip()
    if domain not in VALID_DOMAIN_CODES:
        domain = "UNK"

    confidence = _clamp_confidence(raw.get("domain_confidence", 0.5))

    capture = _safe_str(raw.get("capture_method"))
    if capture and capture not in VALID_CAPTURE_METHODS:
        capture = "unknown"

    orientation = _safe_str(raw.get("orientation"))
    if orientation and orientation not in ("portrait", "landscape"):
        orientation = None

    return EnrichmentResult(
        domain_level1=domain,
        domain_confidence=confidence,
        iso639_language=_safe_str(raw.get("iso639_language")),
        iso15924_script=_safe_str(raw.get("iso15924_script")),
        content_type=_safe_str(raw.get("content_type")),
        capture_method=capture,
        has_table=_safe_bool(raw.get("has_table")),
        has_formula=_safe_bool(raw.get("has_formula")),
        has_handwriting=_safe_bool(raw.get("has_handwriting")),
        has_signature=_safe_bool(raw.get("has_signature")),
        has_figure=_safe_bool(raw.get("has_figure")),
        orientation=orientation,
        reasoning=str(raw.get("reasoning", "")),
        model_used=model_id,
        input_mode="vision",
    )


def _clamp_confidence(value: Any) -> float:
    """Clamp a confidence value to [0.0, 1.0].

    Args:
        value: Raw confidence value from model response.

    Returns:
        Float clamped between 0.0 and 1.0.
    """
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, conf))


def _safe_str(value: Any) -> str | None:
    """Safely convert a value to string or None.

    Args:
        value: Raw value from model response.

    Returns:
        Stripped string or None.
    """
    if value is None:
        return None
    result = str(value).strip()
    return result if result else None


def _safe_bool(value: Any) -> bool | None:
    """Safely convert a value to bool or None.

    Args:
        value: Raw value from model response.

    Returns:
        Boolean or None.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)
