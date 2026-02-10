"""Script Router (Tier 3 of Three-Tier Script Architecture).

This module provides configurable routing from scripts to OCR engines.
The routing rules are loaded from config/script_routing.yaml and support
hot-reload without restart.

Three-tier architecture:
- Tier 1 (Storage): Full ISO 15924 codes stored in schema.py
- Tier 2 (ML Training): Grouped classes in script_ml_mapping.py
- Tier 3 (Routing): Engine selection defined here

Example:
    >>> from image_preprocessing_detector.routing.script_router import ScriptRouter
    >>> from image_preprocessing_detector.schema_utils.script_ml_mapping import (
    ...     ScriptMLMapping,
    ... )
    >>>
    >>> ml_mapping = ScriptMLMapping()
    >>> router = ScriptRouter(ml_mapping)
    >>>
    >>> # Get OCR engine config for Latin script
    >>> config = router.get_engine_config("Latn")
    >>> print(config["engine"])  # "rapidocr"
    >>>
    >>> # Check if script should escalate to VLM
    >>> router.should_escalate_to_vlm("Tibt", confidence=0.4)  # True
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from image_preprocessing_detector.schema_utils.script_ml_mapping import (
        ScriptMLMapping,
    )


class ScriptRouter:
    """Route scripts to OCR engines based on configurable rules.

    Loads routing configuration from config/script_routing.yaml and provides
    methods to determine OCR engine selection and VLM escalation.

    Attributes:
        ml_mapping: ScriptMLMapping instance for Tier 2 lookups
        routing_config_path: Path to routing YAML config
        routing: Loaded routing configuration dict
    """

    # Default config path relative to project root
    DEFAULT_CONFIG_PATH = Path("config/script_routing.yaml")

    def __init__(
        self,
        ml_mapping: ScriptMLMapping,
        routing_config_path: Path | str | None = None,
    ) -> None:
        """Initialize router with ML mapping and config.

        Args:
            ml_mapping: ScriptMLMapping instance for Tier 2 lookups
            routing_config_path: Path to routing YAML. If None, uses default.
        """
        self.ml_mapping = ml_mapping
        self.routing_config_path = self._resolve_config_path(routing_config_path)
        self._load_routing_config()

    def _resolve_config_path(self, config_path: Path | str | None) -> Path:
        """Resolve config path, searching multiple locations."""
        if config_path is not None:
            return Path(config_path)

        # Try relative to package
        package_dir = Path(__file__).parent.parent.parent.parent
        config_from_package = package_dir / self.DEFAULT_CONFIG_PATH
        if config_from_package.exists():
            return config_from_package

        # Try current working directory
        cwd_config = Path.cwd() / self.DEFAULT_CONFIG_PATH
        if cwd_config.exists():
            return cwd_config

        # Default to package-relative path even if it doesn't exist
        return config_from_package

    def _load_routing_config(self) -> None:
        """Load routing configuration from YAML file."""
        if not self.routing_config_path.exists():
            self._set_defaults()
            return

        with open(self.routing_config_path, encoding="utf-8") as f:
            self.routing: dict[str, Any] = yaml.safe_load(f) or {}

        self.version: str = self.routing.get("version", "unknown")
        self._default_engine: str = self.routing.get("default_engine", "auto")
        self._default_batch_size: int = self.routing.get("default_batch_size", 4)

        # Clear cached results
        self._get_cached_engine_config.cache_clear()

    def _set_defaults(self) -> None:
        """Set default values when config file is missing."""
        self.routing = {}
        self.version = "default"
        self._default_engine = "auto"
        self._default_batch_size = 4

    def _get_defaults(self) -> dict[str, Any]:
        """Get default routing config."""
        return {
            "engine": self._default_engine,
            "batch_size": self._default_batch_size,
        }

    @lru_cache(maxsize=256)  # noqa: B019 - Intentional caching for config lookups
    def _get_cached_engine_config(
        self, iso15924_code: str
    ) -> tuple[tuple[str, Any], ...]:
        """Cached engine config lookup (returns tuple for hashability)."""
        config = self._compute_engine_config(iso15924_code)
        # Convert dict to sorted tuple of tuples for caching
        return tuple(sorted(config.items()))

    def _compute_engine_config(self, iso15924_code: str) -> dict[str, Any]:
        """Compute engine config without caching."""
        # Priority 1: Check for specific ISO 15924 override
        overrides = self.routing.get("iso15924_overrides", {})
        if iso15924_code in overrides:
            return {**self._get_defaults(), **overrides[iso15924_code]}

        # Priority 2: Map to ML class and get routing rule
        ml_class = self.ml_mapping.to_ml_class(iso15924_code)
        rules = self.routing.get("routing_rules", {})

        if ml_class in rules:
            return {**self._get_defaults(), **rules[ml_class]}

        # Priority 3: Return defaults
        return self._get_defaults()

    def get_engine_config(self, iso15924_code: str) -> dict[str, Any]:
        """Get OCR engine configuration for a script.

        Priority:
        1. ISO 15924 override (most specific)
        2. ML class routing rule
        3. Default config

        Args:
            iso15924_code: 4-letter ISO 15924 script code

        Returns:
            Dict with engine, batch_size, and other routing params
        """
        # Convert cached tuple back to dict
        cached = self._get_cached_engine_config(iso15924_code)
        return dict(cached)

    def get_engine(self, iso15924_code: str) -> str:
        """Get OCR engine name for a script.

        Args:
            iso15924_code: 4-letter ISO 15924 script code

        Returns:
            Engine name string (e.g., "rapidocr", "paddleocr", "tesseract")
        """
        config = self.get_engine_config(iso15924_code)
        return str(config.get("engine", self._default_engine))

    def get_batch_size(self, iso15924_code: str) -> int:
        """Get recommended batch size for a script.

        Args:
            iso15924_code: 4-letter ISO 15924 script code

        Returns:
            Recommended batch size
        """
        config = self.get_engine_config(iso15924_code)
        return int(config.get("batch_size", self._default_batch_size))

    def get_lang_hint(self, iso15924_code: str) -> str | None:
        """Get language hint for OCR engine.

        Args:
            iso15924_code: 4-letter ISO 15924 script code

        Returns:
            Language hint string or None
        """
        config = self.get_engine_config(iso15924_code)
        return config.get("lang_hint")

    def is_rtl(self, iso15924_code: str) -> bool:
        """Check if script requires RTL handling.

        Args:
            iso15924_code: 4-letter ISO 15924 script code

        Returns:
            True if RTL handling required
        """
        config = self.get_engine_config(iso15924_code)
        return bool(config.get("rtl", False))

    def should_escalate_to_vlm(
        self,
        iso15924_code: str,
        confidence: float,
    ) -> bool:
        """Check if script should escalate to VLM pipeline.

        Args:
            iso15924_code: 4-letter ISO 15924 script code
            confidence: Detection confidence (0-1)

        Returns:
            True if VLM escalation recommended
        """
        vlm_config = self.routing.get("vlm_escalation", {})

        # Always escalate list
        always_escalate = vlm_config.get("always_escalate", [])
        if iso15924_code in always_escalate:
            return True

        # Unknown script escalation
        if iso15924_code == "Zzzz" and vlm_config.get("escalate_unknown", True):
            return True

        # Confidence threshold from global config
        global_threshold = vlm_config.get("confidence_threshold", 0.5)
        if confidence < global_threshold:
            return True

        # Per-script VLM threshold from routing rules
        config = self.get_engine_config(iso15924_code)
        script_threshold = config.get("vlm_escalation_threshold")
        return script_threshold is not None and confidence < script_threshold

    def get_vlm_escalation_reasons(
        self,
        iso15924_code: str,
        confidence: float,
    ) -> list[str]:
        """Get reasons why script should escalate to VLM.

        Args:
            iso15924_code: 4-letter ISO 15924 script code
            confidence: Detection confidence (0-1)

        Returns:
            List of escalation reason strings
        """
        reasons = []
        vlm_config = self.routing.get("vlm_escalation", {})

        # Always escalate list
        always_escalate = vlm_config.get("always_escalate", [])
        if iso15924_code in always_escalate:
            reasons.append(f"script_{iso15924_code}_always_escalate")

        # Unknown script
        if iso15924_code == "Zzzz" and vlm_config.get("escalate_unknown", True):
            reasons.append("unknown_script")

        # Confidence threshold
        global_threshold = vlm_config.get("confidence_threshold", 0.5)
        if confidence < global_threshold:
            reasons.append(f"low_confidence_{confidence:.2f}_below_{global_threshold}")

        # Per-script threshold
        config = self.get_engine_config(iso15924_code)
        script_threshold = config.get("vlm_escalation_threshold")
        if script_threshold is not None and confidence < script_threshold:
            reasons.append(
                f"script_threshold_{confidence:.2f}_below_{script_threshold}"
            )

        return reasons

    def get_engine_specific_config(self, engine: str) -> dict[str, Any]:
        """Get configuration for a specific OCR engine.

        Args:
            engine: Engine name (e.g., "rapidocr", "paddleocr")

        Returns:
            Engine-specific configuration dict
        """
        engine_configs = self.routing.get("engine_configs", {})
        result: dict[str, Any] = engine_configs.get(engine, {})
        return result

    def reload(self) -> None:
        """Hot-reload config without restart.

        Call this method to reload the config file if it has been
        modified. Clears cached lookups.
        """
        self._load_routing_config()

    def __repr__(self) -> str:
        """String representation."""
        num_rules = len(self.routing.get("routing_rules", {}))
        num_overrides = len(self.routing.get("iso15924_overrides", {}))
        return (
            f"ScriptRouter(version={self.version!r}, "
            f"rules={num_rules}, overrides={num_overrides})"
        )


# Module-level factory for convenience
_default_router: ScriptRouter | None = None


def get_default_router() -> ScriptRouter:
    """Get default ScriptRouter singleton.

    Lazy-loads ScriptMLMapping and ScriptRouter on first call.

    Returns:
        ScriptRouter instance with default configs
    """
    global _default_router
    if _default_router is None:
        from image_preprocessing_detector.schema_utils.script_ml_mapping import (
            get_default_mapping,
        )

        _default_router = ScriptRouter(get_default_mapping())
    return _default_router


def reset_default_router() -> None:
    """Reset the default router singleton.

    Call this after modifying configs to force reload.
    """
    global _default_router
    _default_router = None


__all__ = [
    "ScriptRouter",
    "get_default_router",
    "reset_default_router",
]
