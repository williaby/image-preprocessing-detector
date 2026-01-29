#!/usr/bin/env python3
"""Tiered Language Detection Escalation Module.

Provides escalation to vision LLMs via OpenRouter when local detection
has low confidence or high variance.

Tiers:
1. Local: Unicode script + fastText + lingua (free, fast)
2. Vision LLM: OpenRouter → Gemini/GPT for image-based detection (~$0.01/image)
3. Human Review: Queue uncertain samples for manual review

Usage:
    from scripts.language_escalation import (
        EscalationManager,
        EscalationConfig,
        detect_with_escalation,
    )

    # Configure escalation
    config = EscalationConfig(
        confidence_threshold=0.6,
        variance_threshold=0.3,
        vision_model="google/gemini-2.5-pro",
    )

    # Run detection with automatic escalation
    manager = EscalationManager(config)
    result = manager.detect(image_path, local_result)
"""

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
REVIEW_QUEUE_PATH = Path("/mnt/e/image_detection/metadata_registry/review_queue")

# Tier 1b: FREE vision models for initial image-based detection
FREE_VISION_MODELS = [
    "qwen/qwen-2.5-vl-7b-instruct:free",  # Best: explicit multilingual text recognition
    "google/gemma-3-27b-it:free",  # Good: 140+ languages, 131K context
    "mistralai/mistral-small-3.1-24b-instruct:free",  # Good: image analysis + multilingual
]

# Tier 2: PAID vision models for escalation when free tier uncertain
PAID_VISION_MODELS = [
    "google/gemini-2.5-pro",  # Best multilingual, 1M context
    "qwen/qwen3-vl-235b-a22b-instruct",  # Strong vision-language
    "openai/gpt-5.1",  # Excellent vision understanding
]

# Script to valid languages mapping (for validation)
SCRIPT_VALID_LANGUAGES: dict[str, set[str]] = {
    "Latn": {"en", "es", "fr", "de", "it", "pt", "nl", "pl", "cs", "hu", "ro", "fi", "sv", "no", "da", "tr", "id", "ms", "tl", "sw", "hr", "sl", "et", "lv", "lt", "sq", "az", "uz", "mt", "cy", "ga", "gd", "eu", "ca", "gl", "af", "zu", "xh", "st", "tn", "sn", "ny", "mg", "ha", "ig", "yo", "so", "rw", "la", "eo", "vi"},
    "Cyrl": {"ru", "uk", "bg", "sr", "mk", "kk", "ky", "tg", "mn", "be"},
    "Arab": {"ar", "fa", "ur", "ps", "ks", "sd", "ug", "ku"},
    "Deva": {"hi", "mr", "ne", "sa", "bho", "mai", "kok"},
    "Beng": {"bn", "as"},
    "Gujr": {"gu"},
    "Guru": {"pa"},
    "Orya": {"or"},
    "Taml": {"ta"},
    "Telu": {"te"},
    "Knda": {"kn"},
    "Mlym": {"ml"},
    "Sinh": {"si"},
    "Thai": {"th"},
    "Laoo": {"lo"},
    "Khmr": {"km"},
    "Mymr": {"my"},
    "Tibt": {"bo", "dz"},
    "Geor": {"ka"},
    "Armn": {"hy"},
    "Hebr": {"he", "yi"},
    "Grek": {"el"},
    "Hang": {"ko"},
    "Hani": {"zh", "ja"},  # Han used by Chinese and Japanese
    "Hira": {"ja"},
    "Kana": {"ja"},
    "Jpan": {"ja"},  # Combined Japanese script
    "Kore": {"ko"},  # Combined Korean script
    "Hans": {"zh"},  # Simplified Chinese
    "Hant": {"zh"},  # Traditional Chinese
    "Ethi": {"am", "ti"},
}

# Prompt for vision-based language detection
LANGUAGE_DETECTION_PROMPT = """Analyze this image and identify ALL languages present in the text.

Return a JSON object with:
{
    "languages": [{"code": "ISO 639-1 code", "script": "ISO 15924 code", "confidence": 0.0-1.0, "sample_text": "example"}],
    "primary_language": "ISO 639-1 code of dominant language",
    "primary_script": "ISO 15924 code of dominant script",
    "is_multilingual": true/false,
    "total_confidence": 0.0-1.0,
    "notes": "any relevant observations"
}

Important:
- Use ISO 639-1 codes (2-letter) when available, otherwise ISO 639-3 (3-letter)
- Use ISO 15924 codes for scripts (e.g., Latn, Arab, Deva, Hani)
- If multiple languages share a script, identify each separately
- Confidence should reflect certainty of detection
- Include sample_text showing detected language

Only return the JSON object, no other text."""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class EscalationConfig:
    """Configuration for escalation behavior."""

    # Thresholds for escalation from Tier 1a to 1b
    confidence_threshold: float = 0.6  # Escalate if below
    variance_threshold: float = 0.3  # Escalate if above

    # Tier 1b: FREE vision model settings
    free_vision_model: str = "qwen/qwen-2.5-vl-7b-instruct:free"
    free_fallback_models: list[str] = field(default_factory=lambda: FREE_VISION_MODELS[1:])
    tier1b_confidence_threshold: float = 0.7  # Escalate to Tier 2 if below

    # Tier 2: PAID vision model settings (escalation)
    paid_vision_model: str = "google/gemini-2.5-pro"
    paid_fallback_models: list[str] = field(default_factory=lambda: PAID_VISION_MODELS[1:])
    max_retries: int = 2

    # Script validation
    validate_script_match: bool = True  # Validate detected language matches script

    # Cost controls
    max_cost_per_image: float = 0.05  # USD
    daily_budget: float = 10.0  # USD

    # Review queue
    review_queue_path: Path = REVIEW_QUEUE_PATH
    queue_if_tier2_uncertain: bool = True
    tier2_confidence_threshold: float = 0.7  # Queue if Tier 2 below this


@dataclass
class ConfidenceMetrics:
    """Rich confidence metadata with uncertainty bounds."""

    point_estimate: float
    lower_bound: float
    upper_bound: float
    variance: float
    detector_agreement: bool
    needs_escalation: bool
    escalation_reason: str | None = None


@dataclass
class ScriptValidation:
    """Result of validating language against detected script."""

    is_valid: bool
    detected_script: str | None
    detected_language: str
    valid_languages_for_script: set[str]
    mismatch_reason: str | None = None


@dataclass
class EscalationResult:
    """Result from escalated detection."""

    tier: int  # 1a=script, 1b=free_vision, 2=paid_vision, 3=human_review
    primary_language: str
    primary_script: str | None
    detected_languages: list[str]
    detected_scripts: list[str]
    confidence: float
    confidence_metrics: ConfidenceMetrics
    method: str
    model_used: str | None = None
    cost_usd: float = 0.0
    queued_for_review: bool = False
    raw_response: dict[str, Any] | None = None
    script_validation: ScriptValidation | None = None


# =============================================================================
# Confidence Calculation
# =============================================================================


def calculate_confidence_metrics(
    local_result: Any,  # MultiLanguageResult from enrich_language.py
) -> ConfidenceMetrics:
    """Calculate rich confidence metrics from local detection result."""
    votes = getattr(local_result, "votes", [])

    if not votes:
        return ConfidenceMetrics(
            point_estimate=local_result.confidence,
            lower_bound=0.0,
            upper_bound=local_result.confidence,
            variance=1.0,
            detector_agreement=False,
            needs_escalation=True,
            escalation_reason="no_detector_votes",
        )

    # Calculate confidence bounds and variance
    confidences = [v.confidence for v in votes if v.confidence > 0]

    if not confidences:
        return ConfidenceMetrics(
            point_estimate=local_result.confidence,
            lower_bound=0.0,
            upper_bound=local_result.confidence,
            variance=1.0,
            detector_agreement=False,
            needs_escalation=True,
            escalation_reason="zero_confidence_votes",
        )

    point_estimate = sum(confidences) / len(confidences)
    lower_bound = min(confidences)
    upper_bound = max(confidences)

    # Calculate variance
    if len(confidences) > 1:
        mean = point_estimate
        variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
    else:
        variance = 0.0

    # Check detector agreement
    languages = [v.language for v in votes if v.language != "und"]
    unique_langs = set(languages)
    detector_agreement = len(unique_langs) <= 1

    # Determine if escalation needed
    needs_escalation = False
    escalation_reason = None

    if point_estimate < 0.6:
        needs_escalation = True
        escalation_reason = "low_confidence"
    elif variance > 0.3:
        needs_escalation = True
        escalation_reason = "high_variance"
    elif not detector_agreement:
        needs_escalation = True
        escalation_reason = "detector_disagreement"

    return ConfidenceMetrics(
        point_estimate=point_estimate,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        variance=variance,
        detector_agreement=detector_agreement,
        needs_escalation=needs_escalation,
        escalation_reason=escalation_reason,
    )


# =============================================================================
# Vision LLM Detection (Tier 2)
# =============================================================================


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for API submission."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: Path) -> str:
    """Determine MIME type from file extension."""
    suffix = image_path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(suffix, "image/jpeg")


def detect_via_vision_llm(
    image_path: Path,
    model: str,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Send image to vision LLM for language detection.

    Returns parsed JSON response or None on failure.
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        return None

    # Encode image
    try:
        image_b64 = encode_image_base64(image_path)
        media_type = get_image_media_type(image_path)
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        return None

    # Build request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/image-preprocessing-detector",
        "X-Title": "Language Detection Escalation",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": LANGUAGE_DETECTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,  # Low temperature for consistent detection
        "max_tokens": 1000,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        parsed = json.loads(content.strip())

        # Add usage info if available
        if "usage" in result:
            parsed["_usage"] = result["usage"]
            parsed["_model"] = model

        return parsed

    except httpx.HTTPStatusError as e:
        logger.error(f"Vision API HTTP error: {e.response.status_code} - {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse vision API response as JSON: {e}")
        logger.debug(f"Raw response: {content if 'content' in dir() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        return None


def estimate_cost(model: str, usage: dict[str, int] | None) -> float:
    """Estimate cost in USD based on model and token usage."""
    if not usage:
        return 0.01  # Default estimate

    # Approximate pricing per 1K tokens (as of 2026)
    pricing = {
        "google/gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
        "qwen/qwen3-vl-235b-a22b-instruct": {"input": 0.001, "output": 0.003},
        "openai/gpt-5.1": {"input": 0.005, "output": 0.015},
    }

    model_pricing = pricing.get(model, {"input": 0.002, "output": 0.006})

    input_cost = (usage.get("prompt_tokens", 0) / 1000) * model_pricing["input"]
    output_cost = (usage.get("completion_tokens", 0) / 1000) * model_pricing["output"]

    return input_cost + output_cost


# =============================================================================
# Human Review Queue (Tier 3)
# =============================================================================


def queue_for_review(
    image_path: Path,
    local_result: Any,
    tier2_result: dict[str, Any] | None,
    reason: str,
    config: EscalationConfig,
) -> None:
    """Add sample to human review queue."""
    queue_dir = config.review_queue_path
    queue_dir.mkdir(parents=True, exist_ok=True)

    queue_file = queue_dir / "pending_review.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_path": str(image_path),
        "reason": reason,
        "local_detection": {
            "language": getattr(local_result, "primary_language", "und"),
            "script": getattr(local_result, "primary_script", None),
            "confidence": getattr(local_result, "confidence", 0.0),
        },
        "tier2_detection": tier2_result,
        "status": "pending",
    }

    with open(queue_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    logger.info(f"Queued for review: {image_path} (reason: {reason})")


# =============================================================================
# Script Validation
# =============================================================================


def validate_language_script_match(
    detected_language: str,
    detected_scripts: list[str],
) -> ScriptValidation:
    """Validate that detected language is compatible with detected script(s).

    This catches cases where statistical language detection returns a language
    that doesn't match the script we detected in Tier 1a.

    Example: Script=Tibt but language=en would be a mismatch.
    """
    if not detected_scripts or detected_language in ("und", "mul"):
        return ScriptValidation(
            is_valid=True,
            detected_script=detected_scripts[0] if detected_scripts else None,
            detected_language=detected_language,
            valid_languages_for_script=set(),
            mismatch_reason=None,
        )

    primary_script = detected_scripts[0]
    valid_languages = SCRIPT_VALID_LANGUAGES.get(primary_script, set())

    # If we don't have a mapping for this script, assume valid
    if not valid_languages:
        return ScriptValidation(
            is_valid=True,
            detected_script=primary_script,
            detected_language=detected_language,
            valid_languages_for_script=valid_languages,
            mismatch_reason=None,
        )

    # Check if detected language is valid for this script
    is_valid = detected_language in valid_languages

    mismatch_reason = None
    if not is_valid:
        mismatch_reason = (
            f"Language '{detected_language}' not valid for script '{primary_script}'. "
            f"Expected one of: {sorted(valid_languages)[:5]}..."
        )

    return ScriptValidation(
        is_valid=is_valid,
        detected_script=primary_script,
        detected_language=detected_language,
        valid_languages_for_script=valid_languages,
        mismatch_reason=mismatch_reason,
    )


# =============================================================================
# Escalation Manager
# =============================================================================


class EscalationManager:
    """Manages tiered language detection with automatic escalation."""

    def __init__(self, config: EscalationConfig | None = None):
        self.config = config or EscalationConfig()
        self._daily_spend = 0.0
        self._last_reset = datetime.now(timezone.utc).date()

    def _check_budget(self, estimated_cost: float) -> bool:
        """Check if we're within daily budget."""
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset:
            self._daily_spend = 0.0
            self._last_reset = today

        return (self._daily_spend + estimated_cost) <= self.config.daily_budget

    def detect(
        self,
        image_path: Path,
        local_result: Any,  # MultiLanguageResult from Tier 1a
    ) -> EscalationResult:
        """Run detection with automatic tiered escalation.

        Architecture:
        - Tier 1a: Script detection via Unicode (in local_result)
        - Tier 1b: FREE vision LLM + script validation
        - Tier 2: PAID vision LLM (escalation)
        - Tier 3: Human review queue

        Args:
            image_path: Path to the image file
            local_result: Result from local detection (Tier 1a script + statistical)

        Returns:
            EscalationResult with final detection and metadata
        """
        # Calculate confidence metrics from Tier 1a
        metrics = calculate_confidence_metrics(local_result)

        # Validate script-language match from Tier 1a
        script_validation = None
        if self.config.validate_script_match:
            script_validation = validate_language_script_match(
                local_result.primary_language,
                local_result.detected_scripts,
            )
            if not script_validation.is_valid:
                logger.warning(f"Script mismatch: {script_validation.mismatch_reason}")
                metrics.needs_escalation = True
                metrics.escalation_reason = "script_language_mismatch"

        # Check if Tier 1a is sufficient (high confidence, no mismatch)
        if not metrics.needs_escalation:
            return EscalationResult(
                tier=1,  # Tier 1a
                primary_language=local_result.primary_language,
                primary_script=local_result.primary_script,
                detected_languages=local_result.detected_languages,
                detected_scripts=local_result.detected_scripts,
                confidence=local_result.confidence,
                confidence_metrics=metrics,
                method=f"tier1a_{local_result.method}",
                script_validation=script_validation,
            )

        # =================================================================
        # Tier 1b: FREE Vision LLM
        # =================================================================
        logger.info(
            f"Escalating to Tier 1b ({self.config.free_vision_model}) - "
            f"reason: {metrics.escalation_reason}"
        )

        tier1b_result = None
        model_used = None

        # Try free models (no cost)
        free_models = [self.config.free_vision_model] + self.config.free_fallback_models

        for model in free_models[: self.config.max_retries + 1]:
            tier1b_result = detect_via_vision_llm(image_path, model)
            if tier1b_result:
                model_used = model
                break

        if tier1b_result:
            tier1b_confidence = tier1b_result.get("total_confidence", 0.7)
            tier1b_languages = [
                lang["code"] for lang in tier1b_result.get("languages", [])
            ]
            tier1b_scripts = [
                lang.get("script") for lang in tier1b_result.get("languages", []) if lang.get("script")
            ]
            tier1b_primary_lang = tier1b_result.get("primary_language", "und")

            # Validate Tier 1b result against Tier 1a scripts
            tier1b_validation = None
            if self.config.validate_script_match and local_result.detected_scripts:
                tier1b_validation = validate_language_script_match(
                    tier1b_primary_lang,
                    local_result.detected_scripts,  # Use Tier 1a scripts
                )

            # Check if Tier 1b is confident AND passes script validation
            if (
                tier1b_confidence >= self.config.tier1b_confidence_threshold
                and (tier1b_validation is None or tier1b_validation.is_valid)
            ):
                return EscalationResult(
                    tier=1,  # Tier 1b (still "free tier")
                    primary_language=tier1b_primary_lang,
                    primary_script=tier1b_result.get("primary_script"),
                    detected_languages=tier1b_languages,
                    detected_scripts=tier1b_scripts or local_result.detected_scripts,
                    confidence=tier1b_confidence,
                    confidence_metrics=metrics,
                    method="tier1b_free_vision",
                    model_used=model_used,
                    cost_usd=0.0,  # Free!
                    raw_response=tier1b_result,
                    script_validation=tier1b_validation,
                )

            # Tier 1b uncertain or script mismatch - escalate to Tier 2
            logger.info(
                f"Tier 1b uncertain (conf={tier1b_confidence:.2f}, "
                f"script_valid={tier1b_validation.is_valid if tier1b_validation else 'N/A'}) - "
                f"escalating to Tier 2"
            )

        # =================================================================
        # Tier 2: PAID Vision LLM
        # =================================================================
        # Check budget before Tier 2
        estimated_cost = 0.01
        if not self._check_budget(estimated_cost):
            logger.warning("Daily budget exceeded, using Tier 1b result")
            if tier1b_result:
                return EscalationResult(
                    tier=1,
                    primary_language=tier1b_result.get("primary_language", "und"),
                    primary_script=tier1b_result.get("primary_script"),
                    detected_languages=tier1b_languages,
                    detected_scripts=tier1b_scripts or local_result.detected_scripts,
                    confidence=tier1b_confidence * 0.8,
                    confidence_metrics=metrics,
                    method="tier1b_budget_exceeded",
                    model_used=model_used,
                    cost_usd=0.0,
                )
            # Fall back to Tier 1a
            return EscalationResult(
                tier=1,
                primary_language=local_result.primary_language,
                primary_script=local_result.primary_script,
                detected_languages=local_result.detected_languages,
                detected_scripts=local_result.detected_scripts,
                confidence=local_result.confidence * 0.7,
                confidence_metrics=metrics,
                method="tier1a_budget_exceeded",
                script_validation=script_validation,
            )

        logger.info(f"Escalating to Tier 2 ({self.config.paid_vision_model})")

        tier2_result = None
        tier2_model = None
        cost = 0.0

        # Try paid models
        paid_models = [self.config.paid_vision_model] + self.config.paid_fallback_models

        for model in paid_models[: self.config.max_retries + 1]:
            tier2_result = detect_via_vision_llm(image_path, model)
            if tier2_result:
                tier2_model = model
                cost = estimate_cost(model, tier2_result.get("_usage"))
                self._daily_spend += cost
                break

        if tier2_result:
            tier2_confidence = tier2_result.get("total_confidence", 0.8)
            tier2_languages = [
                lang["code"] for lang in tier2_result.get("languages", [])
            ]
            tier2_scripts = [
                lang.get("script") for lang in tier2_result.get("languages", []) if lang.get("script")
            ]
            tier2_primary_lang = tier2_result.get("primary_language", "und")

            # Validate against Tier 1a scripts
            tier2_validation = None
            if self.config.validate_script_match and local_result.detected_scripts:
                tier2_validation = validate_language_script_match(
                    tier2_primary_lang,
                    local_result.detected_scripts,
                )

            # Check if Tier 2 is confident enough
            if tier2_confidence >= self.config.tier2_confidence_threshold:
                return EscalationResult(
                    tier=2,
                    primary_language=tier2_primary_lang,
                    primary_script=tier2_result.get("primary_script"),
                    detected_languages=tier2_languages,
                    detected_scripts=tier2_scripts or local_result.detected_scripts,
                    confidence=tier2_confidence,
                    confidence_metrics=metrics,
                    method="tier2_paid_vision",
                    model_used=tier2_model,
                    cost_usd=cost,
                    raw_response=tier2_result,
                    script_validation=tier2_validation,
                )

            # Tier 2 uncertain - queue for human review
            if self.config.queue_if_tier2_uncertain:
                queue_for_review(
                    image_path,
                    local_result,
                    tier2_result,
                    reason=f"tier2_low_confidence_{tier2_confidence:.2f}",
                    config=self.config,
                )

                return EscalationResult(
                    tier=3,
                    primary_language=tier2_primary_lang,
                    primary_script=tier2_result.get("primary_script"),
                    detected_languages=tier2_languages,
                    detected_scripts=tier2_scripts or local_result.detected_scripts,
                    confidence=tier2_confidence,
                    confidence_metrics=metrics,
                    method="tier3_queued_for_review",
                    model_used=tier2_model,
                    cost_usd=cost,
                    queued_for_review=True,
                    raw_response=tier2_result,
                    script_validation=tier2_validation,
                )

        # =================================================================
        # Tier 2 failed - fall back to best available
        # =================================================================
        logger.warning("Tier 2 detection failed")

        # Use Tier 1b if available
        if tier1b_result:
            if self.config.queue_if_tier2_uncertain:
                queue_for_review(
                    image_path,
                    local_result,
                    tier1b_result,
                    reason="tier2_api_failed_using_tier1b",
                    config=self.config,
                )
            return EscalationResult(
                tier=1,
                primary_language=tier1b_result.get("primary_language", "und"),
                primary_script=tier1b_result.get("primary_script"),
                detected_languages=tier1b_languages,
                detected_scripts=tier1b_scripts or local_result.detected_scripts,
                confidence=tier1b_confidence * 0.7,
                confidence_metrics=metrics,
                method="tier1b_tier2_failed",
                model_used=model_used,
                cost_usd=0.0,
                queued_for_review=self.config.queue_if_tier2_uncertain,
            )

        # Fall back to Tier 1a
        if self.config.queue_if_tier2_uncertain:
            queue_for_review(
                image_path,
                local_result,
                None,
                reason="all_vision_failed",
                config=self.config,
            )

        return EscalationResult(
            tier=1,
            primary_language=local_result.primary_language,
            primary_script=local_result.primary_script,
            detected_languages=local_result.detected_languages,
            detected_scripts=local_result.detected_scripts,
            confidence=local_result.confidence * 0.6,
            confidence_metrics=metrics,
            method="tier1a_all_vision_failed",
            queued_for_review=self.config.queue_if_tier2_uncertain,
            script_validation=script_validation,
        )


# =============================================================================
# Convenience Function
# =============================================================================


def detect_with_escalation(
    image_path: Path,
    local_result: Any,
    config: EscalationConfig | None = None,
) -> EscalationResult:
    """Convenience function for single-image detection with escalation.

    Args:
        image_path: Path to image file
        local_result: Result from local Tier 1 detection
        config: Optional escalation configuration

    Returns:
        EscalationResult with tier, languages, confidence, and metadata
    """
    manager = EscalationManager(config)
    return manager.detect(image_path, local_result)


# =============================================================================
# CLI for Testing
# =============================================================================


def main() -> int:
    """Test escalation on a single image."""
    import argparse

    from scripts.enrich_language import (
        multi_language_consensus,
        extract_text_easyocr,
    )

    parser = argparse.ArgumentParser(description="Test language detection escalation")
    parser.add_argument("image", type=Path, help="Image file to analyze")
    parser.add_argument("--model", default="google/gemini-2.5-pro", help="Vision model")
    parser.add_argument("--force-tier2", action="store_true", help="Force Tier 2 escalation")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.image.exists():
        logger.error(f"Image not found: {args.image}")
        return 1

    # Run local detection first
    logger.info("Running Tier 1 (local) detection...")

    try:
        import easyocr

        reader = easyocr.Reader(["en"], gpu=True)
        text = extract_text_easyocr(args.image, reader)
    except Exception as e:
        logger.warning(f"EasyOCR failed: {e}")
        text = ""

    if text:
        # Load models for local detection
        try:
            import fasttext

            ft_model = fasttext.load_model(
                "/mnt/e/image_detection/models/language_detection/lid.176.bin"
            )
        except Exception:
            ft_model = None

        try:
            from lingua import LanguageDetectorBuilder

            lingua_detector = LanguageDetectorBuilder.from_all_languages().build()
        except Exception:
            lingua_detector = None

        local_result = multi_language_consensus(text, ft_model, lingua_detector)
    else:
        # No text extracted - create minimal result
        from dataclasses import dataclass

        @dataclass
        class MinimalResult:
            primary_language: str = "und"
            primary_script: str | None = None
            detected_languages: list[str] = field(default_factory=list)
            detected_scripts: list[str] = field(default_factory=list)
            confidence: float = 0.0
            method: str = "no_text"
            votes: list = field(default_factory=list)

        local_result = MinimalResult()

    logger.info(f"Tier 1 result: {local_result.primary_language} ({local_result.confidence:.2f})")

    # Configure escalation
    config = EscalationConfig(
        vision_model=args.model,
        confidence_threshold=1.0 if args.force_tier2 else 0.6,  # Force escalation if requested
    )

    # Run with escalation
    result = detect_with_escalation(args.image, local_result, config)

    # Print results
    print("\n" + "=" * 60)
    print("ESCALATION RESULT")
    print("=" * 60)
    print(f"Tier: {result.tier}")
    print(f"Method: {result.method}")
    print(f"Primary Language: {result.primary_language}")
    print(f"Primary Script: {result.primary_script}")
    print(f"Detected Languages: {result.detected_languages}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Confidence Interval: [{result.confidence_metrics.lower_bound:.3f}, {result.confidence_metrics.upper_bound:.3f}]")
    print(f"Variance: {result.confidence_metrics.variance:.3f}")
    print(f"Model Used: {result.model_used}")
    print(f"Cost: ${result.cost_usd:.4f}")
    print(f"Queued for Review: {result.queued_for_review}")

    return 0


if __name__ == "__main__":
    exit(main())
