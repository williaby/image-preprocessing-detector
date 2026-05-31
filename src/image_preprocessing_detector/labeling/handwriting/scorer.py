"""Multi-model VLM scorer for handwriting legibility contact sheets.

Sends a contact sheet image to each configured vision model and returns
raw per-image score dicts from every model, ready for aggregation.

Example:
    >>> from pathlib import Path
    >>> from image_preprocessing_detector.labeling.handwriting.scorer import (
    ...     HwLegibilityScorer,
    ... )
    >>> from image_preprocessing_detector.labeling.handwriting.config import (
    ...     get_default_config,
    ... )
    >>> scorer = HwLegibilityScorer(get_default_config())
    >>> result = scorer.score_sheet(Path("sheets/sheet_001.jpg"), n_images=12)
    >>> # result.model_scores["google/gemini-2.0-flash-001"][1]["legibility_score"]
"""

from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from image_preprocessing_detector.labeling.handwriting.config import (
    HwVisionModelConfig,
    LegibilityScorerConfig,
)
from image_preprocessing_detector.labeling.handwriting.prompts import (
    build_sheet_prompt,
    extract_json_from_response,
    parse_sheet_response,
)

logger = structlog.get_logger(__name__)


@dataclass
class SheetScoringResult:
    """Raw scoring output for a single contact sheet across all models.

    Attributes:
        sheet_path (Path): Path to the contact sheet image file.
        n_images (int): Number of images on the sheet.
        model_scores (dict[str, dict[int, dict[str, Any]]]): Map from model_id to per-image score dicts.
            Each inner dict maps 1-based image index to score dict.
        model_errors (dict[str, str]): Map from model_id to error message if scoring failed.
        total_tokens (int): Cumulative token count across all model calls.
    """

    sheet_path: Path
    n_images: int
    model_scores: dict[str, dict[int, dict[str, Any]]] = field(default_factory=dict)
    model_errors: dict[str, str] = field(default_factory=dict)
    total_tokens: int = 0


class HwLegibilityScorer:
    """Orchestrates per-sheet scoring across multiple OpenRouter vision models.

    Each sheet is encoded once as base64 PNG and sent to every configured
    model. Responses are parsed into per-image score dicts stored in
    SheetScoringResult.model_scores.

    Args:
        config (LegibilityScorerConfig): LegibilityScorerConfig with model roster and API settings.
    """

    def __init__(self, config: LegibilityScorerConfig) -> None:
        self._config = config
        self._client: Any = None
        self._total_tokens = 0
        self._total_calls = 0

    def score_sheet(
        self,
        sheet_path: Path,
        n_images: int,
    ) -> SheetScoringResult:
        """Score all images on a contact sheet using every configured model.

        Args:
            sheet_path (Path): Path to the saved contact sheet JPEG.
            n_images (int): Number of labeled images present on the sheet.

        Returns:
            SheetScoringResult:             SheetScoringResult with per-model, per-image score dicts.
        """
        result = SheetScoringResult(sheet_path=sheet_path, n_images=n_images)
        sheet_b64 = self._encode_sheet(sheet_path)
        messages = build_sheet_prompt(n_images)

        for model_cfg in self._config.vision_models:
            try:
                model_result = self._score_with_model(
                    model_cfg, messages, sheet_b64, n_images
                )
                result.model_scores[model_cfg.model_id] = model_result
            except Exception as exc:
                error_msg = str(exc)
                result.model_errors[model_cfg.model_id] = error_msg
                logger.warning(
                    "hw_scorer_model_failed",
                    model=model_cfg.model_id,
                    sheet=str(sheet_path),
                    error=error_msg,
                )

            # Rate limit between model calls
            if self._config.rate_limit_delay > 0:
                time.sleep(self._config.rate_limit_delay)

        result.total_tokens = self._total_tokens
        return result

    def get_usage_stats(self) -> dict[str, int]:
        """Return cumulative API usage statistics.

        Returns:
            dict[str, int]:             Dict with total_tokens and total_calls.
        """
        return {"total_tokens": self._total_tokens, "total_calls": self._total_calls}

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _score_with_model(
        self,
        model_cfg: HwVisionModelConfig,
        messages: list[dict[str, Any]],
        sheet_b64: str,
        n_images: int,
    ) -> dict[int, dict[str, Any]]:
        """Send sheet to one model and return parsed per-image scores.

        Args:
            model_cfg (HwVisionModelConfig): Model configuration (id, max_tokens, weight).
            messages (list[dict[str, Any]]): Base chat messages (system + user text).
            sheet_b64 (str): Base64-encoded contact sheet PNG string.
            n_images (int): Expected image count for response parsing.

        Returns:
            dict[int, dict[str, Any]]: Dict mapping 1-based image index to score dict.
        """
        # Deep-copy messages and append image block to user content
        import copy

        msg_with_image = copy.deepcopy(messages)
        user_content = msg_with_image[1]["content"]
        if isinstance(user_content, list):
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{sheet_b64}",
                        "detail": "high",
                    },
                }
            )

        raw_dict = self._call_with_retry(model_cfg, msg_with_image)
        return parse_sheet_response(raw_dict, n_images)

    def _call_with_retry(
        self,
        model_cfg: HwVisionModelConfig,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Make an OpenRouter API call with exponential backoff retry.

        Args:
            model_cfg (HwVisionModelConfig): Model to call.
            messages (list[dict[str, Any]]): Full message list including image content.

        Returns:
            dict[str, Any]:             Parsed JSON dict from the model.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        client = self._ensure_client()
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_cfg.model_id,
                    messages=messages,
                    max_tokens=model_cfg.max_tokens,
                    temperature=0.0,
                )
                return self._process_api_response(response, model_cfg, attempt)
            except Exception as exc:
                last_error = exc
                self._handle_retry_delay(model_cfg, attempt, exc)

        msg = f"All {self._config.max_retries} retries failed for {model_cfg.model_id}"
        raise RuntimeError(msg) from last_error

    def _process_api_response(
        self,
        response: Any,
        model_cfg: HwVisionModelConfig,
        attempt: int,
    ) -> dict[str, Any]:
        """Validate and parse a raw API response into a score dict.

        Args:
            response (Any): Raw response object from the OpenAI client.
            model_cfg (HwVisionModelConfig): Model configuration used for logging.
            attempt (int): 0-based attempt index for log context.

        Returns:
            dict[str, Any]:             Parsed JSON dict from the model response content.

        Raises:
            RuntimeError: If the response has no choices or empty content.
        """
        if not response.choices:
            error_info = getattr(response, "error", None)
            error_msg = (
                error_info.get("message", "Unknown")
                if isinstance(error_info, dict)
                else str(error_info or "No choices returned")
            )
            msg = f"Provider error: {error_msg}"
            raise RuntimeError(msg)

        if response.usage:
            self._total_tokens += response.usage.total_tokens
        self._total_calls += 1

        content = response.choices[0].message.content or ""
        if not content.strip():
            msg = "Model returned empty content"
            raise RuntimeError(msg)

        parsed = extract_json_from_response(content)
        logger.debug(
            "hw_scorer_call_success",
            model=model_cfg.model_id,
            attempt=attempt + 1,
            tokens=response.usage.total_tokens if response.usage else 0,
        )
        return parsed

    def _handle_retry_delay(
        self,
        model_cfg: HwVisionModelConfig,
        attempt: int,
        exc: Exception,
    ) -> None:
        """Log a failed attempt and sleep before the next retry.

        Args:
            model_cfg (HwVisionModelConfig): Model configuration used for logging.
            attempt (int): 0-based attempt index (sleep skipped on the last attempt).
            exc (Exception): Exception that caused this attempt to fail.
        """
        delay = self._config.retry_base_delay * (2**attempt)
        logger.warning(
            "hw_scorer_call_failed",
            model=model_cfg.model_id,
            attempt=attempt + 1,
            max_retries=self._config.max_retries,
            delay=delay,
            error=str(exc),
        )
        if attempt < self._config.max_retries - 1:
            time.sleep(delay)

    def _ensure_client(self) -> Any:
        """Lazily initialise the OpenAI SDK client for OpenRouter.

        Returns:
            Any:             Initialised OpenAI client.

        Raises:
            ImportError: If openai library is not installed.
        """
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            msg = "openai library required: pip install openai"
            raise ImportError(msg) from exc

        self._client = OpenAI(
            api_key=self._config.get_api_key(),
            base_url=self._config.openrouter_base_url,
            default_headers={
                "HTTP-Referer": self._config.http_referer,
                "X-Title": self._config.app_title,
            },
        )
        return self._client

    def _encode_sheet(self, sheet_path: Path) -> str:
        """Load a contact sheet image and encode it as base64 JPEG.

        Resizes if larger than image_max_pixels.

        Args:
            sheet_path (Path): Path to the contact sheet JPEG file.

        Returns:
            str:             Base64-encoded JPEG string.

        Raises:
            ImportError: If Pillow is not installed.
            RuntimeError: If the image cannot be loaded.
        """
        try:
            from PIL import Image as PILImage
        except ImportError as exc:
            msg = "Pillow required: pip install Pillow"
            raise ImportError(msg) from exc

        try:
            with PILImage.open(sheet_path) as img:
                if img.mode not in ("RGB",):
                    img = img.convert("RGB")  # type: ignore[assignment]

                max_px = self._config.image_max_pixels
                if max(img.size) > max_px:
                    ratio = max_px / max(img.size)
                    new_w = int(img.size[0] * ratio)
                    new_h = int(img.size[1] * ratio)
                    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)  # type: ignore[assignment]

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return base64.b64encode(buf.getvalue()).decode()

        except Exception as exc:
            msg = f"Failed to encode contact sheet: {sheet_path}"
            raise RuntimeError(msg) from exc
