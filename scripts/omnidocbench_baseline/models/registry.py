"""Model registry for loading and managing benchmark models.

Loads model configurations from YAML and instantiates appropriate adapters.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from scripts.omnidocbench_baseline.models.base import BaseModel, ModelConfig

logger = logging.getLogger(__name__)

# Default registry path
DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent / "model_registry.yaml"


class ModelRegistry:
    """Registry for managing benchmark model configurations.

    Loads model definitions from YAML and provides methods to
    instantiate model adapters.
    """

    def __init__(self, registry_path: Path | None = None):
        """Initialize registry from YAML file.

        Args:
            registry_path: Path to registry YAML (default: model_registry.yaml)
        """
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._configs: dict[str, ModelConfig] = {}
        self._groups: dict[str, list[str]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load model configurations from YAML."""
        if not self.registry_path.exists():
            logger.warning(f"Registry file not found: {self.registry_path}")
            return

        with open(self.registry_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Load IQA models
        for model_def in data.get("iqa_models", []):
            config = self._parse_model_config(model_def)
            self._configs[config.model_id] = config

        # Load layout models
        for model_def in data.get("layout_models", []):
            config = self._parse_model_config(model_def)
            self._configs[config.model_id] = config

        # Load handwriting models
        for model_def in data.get("handwriting_models", []):
            config = self._parse_model_config(model_def)
            self._configs[config.model_id] = config

        # Load language models
        for model_def in data.get("language_models", []):
            config = self._parse_model_config(model_def)
            self._configs[config.model_id] = config

        # Load model groups
        for group_def in data.get("model_groups", []):
            group_id = group_def.get("id")
            model_ids = group_def.get("models", [])
            self._groups[group_id] = model_ids

        logger.info(
            f"Loaded {len(self._configs)} models and {len(self._groups)} groups "
            f"from {self.registry_path}"
        )

    def _parse_model_config(self, model_def: dict[str, Any]) -> ModelConfig:
        """Parse a model definition into ModelConfig."""
        return ModelConfig(
            model_id=model_def.get("id", "unknown"),
            name=model_def.get("name", "Unknown Model"),
            version=model_def.get("version", "0.0.0"),
            model_type=model_def.get("type", "unknown"),
            description=model_def.get("description", ""),
            config=model_def.get("config", {}),
            benchmarkable_attributes=model_def.get("benchmarkable_attributes", []),
            status=model_def.get("status", "active"),
        )

    def list_models(self, status: str | None = None) -> list[str]:
        """List available model IDs.

        Args:
            status: Filter by status ("active", "planned", "deprecated")

        Returns:
            List of model IDs
        """
        if status:
            return [mid for mid, cfg in self._configs.items() if cfg.status == status]
        return list(self._configs.keys())

    def list_groups(self) -> list[str]:
        """List available model group IDs."""
        return list(self._groups.keys())

    def get_config(self, model_id: str) -> ModelConfig | None:
        """Get configuration for a model.

        Args:
            model_id: Model identifier

        Returns:
            ModelConfig or None if not found
        """
        return self._configs.get(model_id)

    def get_group_models(self, group_id: str) -> list[str]:
        """Get model IDs in a group.

        Args:
            group_id: Group identifier

        Returns:
            List of model IDs in the group
        """
        return self._groups.get(group_id, [])

    def get_models_for_attribute(self, attribute: str) -> list[str]:
        """Get models that can predict a specific attribute.

        Args:
            attribute: Attribute name (e.g., "fuzzy_scan")

        Returns:
            List of model IDs that benchmark this attribute
        """
        return [
            mid
            for mid, cfg in self._configs.items()
            if attribute in cfg.benchmarkable_attributes
        ]


def _get_adapter_class(model_type: str) -> type[BaseModel]:
    """Get the appropriate adapter class for a model type.

    Args:
        model_type: Model type from config (e.g., "resnet", "classical_cv")

    Returns:
        Adapter class
    """
    # Import adapters lazily to avoid circular imports
    if model_type == "classical_cv":
        from scripts.omnidocbench_baseline.models.adapters.classical_cv import (
            ClassicalCVAdapter,
        )

        return ClassicalCVAdapter

    if model_type == "resnet":
        from scripts.omnidocbench_baseline.models.adapters.resnet import (
            ResNetAdapter,
        )

        return ResNetAdapter

    if model_type == "heuristics":
        from scripts.omnidocbench_baseline.models.adapters.layout_lite import (
            LayoutLiteAdapter,
        )

        return LayoutLiteAdapter

    if model_type == "yolo":
        from scripts.omnidocbench_baseline.models.adapters.doclayout_yolo import (
            DocLayoutYOLOAdapter,
        )

        return DocLayoutYOLOAdapter

    if model_type in ("fasttext", "library"):
        from scripts.omnidocbench_baseline.models.adapters.language import (
            LanguageAdapter,
        )

        return LanguageAdapter

    raise ValueError(f"Unknown model type: {model_type}")


def load_model(
    model_id: str,
    registry: ModelRegistry | None = None,
) -> BaseModel:
    """Load a model by ID.

    Args:
        model_id: Model identifier from registry
        registry: Optional registry instance (creates new if None)

    Returns:
        Instantiated model adapter

    Raises:
        ValueError: If model not found or not available
    """
    if registry is None:
        registry = ModelRegistry()

    config = registry.get_config(model_id)
    if config is None:
        available = registry.list_models()
        raise ValueError(f"Model '{model_id}' not found. Available: {available}")

    if config.status == "planned":
        logger.warning(
            f"Model '{model_id}' is planned but not yet implemented. "
            f"Using placeholder behavior."
        )

    # Get adapter class and instantiate
    adapter_class = _get_adapter_class(config.model_type)
    return adapter_class(config)


def load_model_group(
    group_id: str,
    registry: ModelRegistry | None = None,
    skip_unavailable: bool = True,
) -> list[BaseModel]:
    """Load all models in a group.

    Args:
        group_id: Group identifier from registry
        registry: Optional registry instance
        skip_unavailable: Skip models that fail to load

    Returns:
        List of instantiated model adapters
    """
    if registry is None:
        registry = ModelRegistry()

    model_ids = registry.get_group_models(group_id)
    if not model_ids:
        raise ValueError(f"Model group '{group_id}' not found or empty")

    models = []
    for model_id in model_ids:
        try:
            model = load_model(model_id, registry)
            models.append(model)
        except Exception as e:
            if skip_unavailable:
                logger.warning(f"Skipping unavailable model '{model_id}': {e}")
            else:
                raise

    return models
