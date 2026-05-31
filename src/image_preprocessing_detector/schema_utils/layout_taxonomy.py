"""Layout Taxonomy - Hub-and-spoke canonical superset for cross-schema conversion.

This module provides configurable mapping between layout detection schemas
(DocLayNet, DocStructBench, PubLayNet, Docling, D4LA, DocSynth300K) via a
canonical superset of 57 classes organized as a tree hierarchy.

The mapping is loaded from config/layout_taxonomy.yaml and supports
hot-reload without restart.

Architecture:
- 11 DocLayNet top-level classes form the root nodes (indices 0-10)
- 46 extended classes from other schemas are children beneath them
- Every canonical class has a ``parent`` pointing to the nearest DocLayNet class
- Coarsening to DocLayNet is simply "walk up to parent"

Example:
    >>> from image_preprocessing_detector.schema_utils.layout_taxonomy import (
    ...     LayoutTaxonomy,
    ... )
    >>> tax = LayoutTaxonomy()
    >>> tax.to_canonical("figure_caption", "docstructbench")
    'FIGURE_CAPTION'
    >>> result = tax.convert("figure_caption", "docstructbench", "doclaynet")
    >>> result.target_label
    'Caption'
    >>> result.is_lossy
    True
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ConversionResult:
    """Result of converting a label between schemas.

    Attributes:
        canonical_class (str): The canonical superset class name.
        target_label (str): The label in the target schema.
        is_lossy (bool): True if information was lost during conversion.
        loss_description (str | None): Human-readable description of what was lost.
        confidence (float): 1.0 for exact mappings, <1.0 for ambiguous expansions.
        source_schema (str): The source schema name.
        source_label (str): The original label in the source schema.
    """

    canonical_class: str
    target_label: str
    is_lossy: bool
    loss_description: str | None
    confidence: float
    source_schema: str
    source_label: str


class LayoutTaxonomy:
    """Config-driven layout label taxonomy converter.

    Loads taxonomy from config/layout_taxonomy.yaml and provides methods
    to convert labels between schemas via a canonical superset hierarchy.

    Attributes:
        DEFAULT_CONFIG_PATH: Default path to the YAML config file (relative to project root).

    Args:
        config_path (Path | str | None): Path to config YAML. If None, uses default path.
            Searches relative to package, then project root.
    """

    DEFAULT_CONFIG_PATH = Path("config/layout_taxonomy.yaml")

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = self._resolve_config_path(config_path)
        self._load_config()

    def _resolve_config_path(self, config_path: Path | str | None) -> Path:
        """Resolve config path, searching multiple locations."""
        if config_path is not None:
            return Path(config_path)

        # Try relative to package (schema_utils -> schema -> detection -> src -> root)
        package_dir = Path(__file__).parent.parent.parent.parent.parent
        config_from_package = package_dir / self.DEFAULT_CONFIG_PATH
        if config_from_package.exists():
            return config_from_package

        # Try current working directory
        cwd_config = Path.cwd() / self.DEFAULT_CONFIG_PATH
        if cwd_config.exists():
            return cwd_config

        # Default to package-relative path even if it doesn't exist
        return config_from_package

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            msg = (
                f"Layout taxonomy config not found: {self.config_path}. "
                "Ensure config/layout_taxonomy.yaml exists."
            )
            raise FileNotFoundError(msg)

        with open(self.config_path, encoding="utf-8") as f:
            self._config: dict[str, Any] = yaml.safe_load(f) or {}

        self._canonical: dict[str, dict[str, Any]] = self._config.get(
            "canonical_classes", {}
        )
        self._schemas: dict[str, dict[str, Any]] = self._config.get("schemas", {})
        self._aliases: dict[str, str] = self._config.get("aliases", {})
        self._version: str = self._config.get("version", "unknown")

        # Build reverse mappings: schema -> {canonical -> [native_labels]}
        self._reverse_maps: dict[str, dict[str, list[str]]] = {}
        for schema_name, schema_def in self._schemas.items():
            rev: defaultdict[str, list[str]] = defaultdict(list)
            for native_label, canonical in schema_def.get("class_mapping", {}).items():
                rev[canonical].append(native_label)
            self._reverse_maps[schema_name] = rev

        # Clear caches
        self._cached_to_canonical.cache_clear()
        self._cached_to_doclaynet.cache_clear()

    def _normalize_label(self, label: str) -> str:
        """Resolve alias to normalized label form.

        Args:
            label (str): Raw label string from any source.

        Returns:
            str: Normalized label after alias resolution."""
        return self._aliases.get(label, label)

    @lru_cache(maxsize=512)  # noqa: B019 - Intentional caching for config lookups
    def _cached_to_canonical(self, label: str, schema: str) -> str:
        """Cached canonical lookup."""
        normalized = self._normalize_label(label)

        if schema not in self._schemas:
            return "UNKNOWN"

        class_mapping = self._schemas[schema].get("class_mapping", {})
        canonical = class_mapping.get(normalized)
        if canonical is not None:
            return str(canonical)

        # Try the original label before normalization
        canonical = class_mapping.get(label)
        if canonical is not None:
            return str(canonical)

        return "UNKNOWN"

    def to_canonical(self, label: str, schema: str) -> str:
        """Map a schema-specific label to its canonical class.

        Args:
            label (str): Native label from the schema (e.g., "figure_caption").
            schema (str): Schema name (e.g., "docstructbench").

        Returns:
            str: Canonical class name (e.g., "FIGURE_CAPTION"), or "UNKNOWN"."""
        return self._cached_to_canonical(label, schema)

    def _get_parent(self, canonical: str) -> str | None:
        """Get parent canonical class, or None if top-level.

        Args:
            canonical (str): Canonical class name.

        Returns:
            str | None: Parent canonical class name, or None."""
        cls_def = self._canonical.get(canonical)
        if cls_def is None:
            return None
        return cls_def.get("parent")

    def _walk_to_doclaynet(self, canonical: str) -> str | None:
        """Walk parent chain until reaching a DocLayNet top-level class.

        Args:
            canonical (str): Starting canonical class.

        Returns:
            str | None: DocLayNet top-level canonical class, or None if unreachable."""
        visited: set[str] = set()
        current: str | None = canonical
        while current is not None and current not in visited:
            visited.add(current)
            cls_def = self._canonical.get(current)
            if cls_def is None:
                return None
            if cls_def.get("doclaynet_index") is not None:
                return current
            parent = cls_def.get("parent")
            if parent is None:
                return None
            current = parent
        return None

    def from_canonical(self, canonical: str, target_schema: str) -> ConversionResult:
        """Convert a canonical class to a target schema label.

        If the canonical class is not directly mapped in the target schema,
        walks the parent chain to find the nearest mapped ancestor.

        Args:
            canonical (str): Canonical class name.
            target_schema (str): Target schema name.

        Returns:
            ConversionResult: ConversionResult with target label and loss metadata.

        Raises:
            ValueError: If target_schema is not recognized.
        """
        if target_schema not in self._schemas:
            msg = (
                f"Unknown target schema: {target_schema!r}. "
                f"Available: {list(self._schemas.keys())}"
            )
            raise ValueError(msg)

        reverse_map = self._reverse_maps.get(target_schema, {})

        # Direct match
        direct_labels = reverse_map.get(canonical)
        if direct_labels:
            # Multiple labels map to same canonical -> ambiguous expansion
            if len(direct_labels) == 1:
                return ConversionResult(
                    canonical_class=canonical,
                    target_label=direct_labels[0],
                    is_lossy=False,
                    loss_description=None,
                    confidence=1.0,
                    source_schema="canonical",
                    source_label=canonical,
                )
            # Ambiguous: return first (alphabetically) with reduced confidence
            sorted_labels = sorted(direct_labels)
            return ConversionResult(
                canonical_class=canonical,
                target_label=sorted_labels[0],
                is_lossy=False,
                loss_description=None,
                confidence=round(1.0 / len(direct_labels), 2),
                source_schema="canonical",
                source_label=canonical,
            )

        # Walk parent chain for coarsening
        visited: set[str] = set()
        current = canonical
        while current not in visited:
            visited.add(current)
            parent = self._get_parent(current)
            if parent is None:
                break
            parent_labels = reverse_map.get(parent)
            if parent_labels:
                target_label = sorted(parent_labels)[0]
                return ConversionResult(
                    canonical_class=canonical,
                    target_label=target_label,
                    is_lossy=True,
                    loss_description=(
                        f"{canonical} coarsened to {parent} (via parent chain)"
                    ),
                    confidence=1.0,
                    source_schema="canonical",
                    source_label=canonical,
                )
            current = parent

        # No mapping found
        return ConversionResult(
            canonical_class=canonical,
            target_label="(unmapped)",
            is_lossy=True,
            loss_description=f"{canonical} has no mapping in {target_schema}",
            confidence=0.0,
            source_schema="canonical",
            source_label=canonical,
        )

    def convert(self, label: str, source: str, target: str) -> ConversionResult:
        """Convert a label from one schema to another via canonical hub.

        Args:
            label (str): Native label in the source schema.
            source (str): Source schema name.
            target (str): Target schema name.

        Returns:
            ConversionResult: ConversionResult with full conversion metadata."""
        canonical = self.to_canonical(label, source)
        result = self.from_canonical(canonical, target)
        return ConversionResult(
            canonical_class=result.canonical_class,
            target_label=result.target_label,
            is_lossy=(result.is_lossy or canonical != result.canonical_class),
            loss_description=result.loss_description,
            confidence=result.confidence,
            source_schema=source,
            source_label=label,
        )

    @lru_cache(maxsize=64)  # noqa: B019 - Intentional caching for config lookups
    def _cached_to_doclaynet(self, canonical: str) -> str:
        """Cached DocLayNet coarsening."""
        result = self._walk_to_doclaynet(canonical)
        if result is None:
            return "UNKNOWN"

        # Find the DocLayNet native label
        reverse_map = self._reverse_maps.get("doclaynet", {})
        labels = reverse_map.get(result)
        if labels:
            return labels[0]
        return "UNKNOWN"

    def to_doclaynet(self, canonical_class: str) -> str:
        """Coarsen a canonical class to its DocLayNet-11 label.

        Walks the parent chain until reaching a DocLayNet top-level class,
        then returns the native DocLayNet label string.

        Args:
            canonical_class (str): Canonical class name.

        Returns:
            str: DocLayNet label string (e.g., "Caption"), or "UNKNOWN"."""
        return self._cached_to_doclaynet(canonical_class)

    def to_doclaynet_index(self, canonical_class: str) -> int | None:
        """Get the DocLayNet index (0-10) for a canonical class.

        Walks the parent chain to the nearest DocLayNet top-level class
        and returns its index.

        Args:
            canonical_class (str): Canonical class name.

        Returns:
            int | None: DocLayNet index (0-10), or None if not mappable."""
        doclaynet_canonical = self._walk_to_doclaynet(canonical_class)
        if doclaynet_canonical is None:
            return None
        cls_def = self._canonical.get(doclaynet_canonical, {})
        idx = cls_def.get("doclaynet_index")
        if idx is not None:
            return int(idx)
        return None

    def build_doclaynet_index_map(self) -> dict[str, int]:
        """Build mapping from ALL known labels to DocLayNet indices.

        Includes native labels from all schemas plus aliases. Each label
        is mapped to the DocLayNet index (0-10) of its canonical class's
        nearest DocLayNet ancestor.

        Returns:
            dict[str, int]: Dict mapping label strings to DocLayNet indices (0-10)."""
        index_map: dict[str, int] = {}

        # Map all native labels from all schemas
        for schema_def in self._schemas.values():
            for native_label, canonical in schema_def.get("class_mapping", {}).items():
                idx = self.to_doclaynet_index(str(canonical))
                if idx is not None:
                    index_map[native_label] = idx

        # Map all aliases
        for alias, normalized in self._aliases.items():
            # Try to find which schema contains the normalized label
            for schema_def in self._schemas.values():
                class_mapping = schema_def.get("class_mapping", {})
                if normalized in class_mapping:
                    canonical = str(class_mapping[normalized])
                    idx = self.to_doclaynet_index(canonical)
                    if idx is not None:
                        index_map[alias] = idx
                    break

        # Map canonical names themselves
        for canonical_name in self._canonical:
            idx = self.to_doclaynet_index(canonical_name)
            if idx is not None:
                index_map[canonical_name] = idx

        return index_map

    def convert_annotations(
        self,
        anns: list[dict[str, Any]],
        source: str,
        target: str,
    ) -> list[dict[str, Any]]:
        """Batch-convert annotation dicts from one schema to another.

        Each annotation dict must have a ``"label"`` key. The label is
        converted and additional metadata fields are added.

        Args:
            anns (list[dict[str, Any]]): List of annotation dicts with ``"label"`` keys.
            source (str): Source schema name.
            target (str): Target schema name.

        Returns:
            list[dict[str, Any]]: New list of annotation dicts with converted labels and metadata."""
        results: list[dict[str, Any]] = []
        for ann in anns:
            converted = self.convert(ann.get("label", ""), source, target)
            new_ann = dict(ann)
            new_ann["label"] = converted.target_label
            new_ann["canonical_class"] = converted.canonical_class
            new_ann["source_label"] = converted.source_label
            new_ann["is_lossy"] = converted.is_lossy
            new_ann["conversion_confidence"] = converted.confidence
            if converted.loss_description:
                new_ann["loss_description"] = converted.loss_description
            results.append(new_ann)
        return results

    def get_schema_classes(self, schema: str) -> list[str]:
        """Get all native class labels for a schema.

        Args:
            schema (str): Schema name.

        Returns:
            list[str]: Sorted list of native class labels.

        Raises:
            ValueError: If schema is not recognized.
        """
        if schema not in self._schemas:
            msg = f"Unknown schema: {schema!r}. Available: {list(self._schemas.keys())}"
            raise ValueError(msg)

        class_mapping = self._schemas[schema].get("class_mapping", {})
        return sorted(class_mapping.keys())

    def get_mask_channel_count(self, schema: str) -> int:
        """Get the number of mask channels for a schema.

        This is the number of unique classes in the schema, useful for
        configuring segmentation mask dimensions.

        Args:
            schema (str): Schema name.

        Returns:
            int: Number of classes in the schema."""
        return len(self.get_schema_classes(schema))

    def build_mask_index_map(self, schema: str) -> dict[str, int]:
        """Build class-to-index mapping for segmentation masks.

        Returns a mapping of native labels to indices 0..N-1 in
        alphabetical order.

        Args:
            schema (str): Schema name.

        Returns:
            dict[str, int]: Dict mapping native labels to integer indices."""
        classes = self.get_schema_classes(schema)
        return {cls: idx for idx, cls in enumerate(classes)}

    def get_available_schemas(self) -> list[str]:
        """Get list of all available schema names.

        Returns:
            list[str]: Sorted list of schema names."""
        return sorted(self._schemas.keys())

    def get_canonical_classes(self) -> list[str]:
        """Get list of all canonical class names.

        Returns:
            list[str]: Sorted list of canonical class names."""
        return sorted(self._canonical.keys())

    def reload(self) -> None:
        """Hot-reload config without restart.

        Call this method to reload the config file if it has been
        modified. Clears all cached mappings.
        """
        self._load_config()

    @property
    def version(self) -> str:
        """Config version string."""
        return self._version

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LayoutTaxonomy(version={self._version!r}, "
            f"canonical_classes={len(self._canonical)}, "
            f"schemas={len(self._schemas)})"
        )


# Module-level singleton for convenience
_default_taxonomy: LayoutTaxonomy | None = None


def get_default_taxonomy() -> LayoutTaxonomy:
    """Get default LayoutTaxonomy singleton.

    Returns:
        LayoutTaxonomy: LayoutTaxonomy instance with default config."""
    global _default_taxonomy
    if _default_taxonomy is None:
        _default_taxonomy = LayoutTaxonomy()
    return _default_taxonomy


def reset_default_taxonomy() -> None:
    """Reset the default taxonomy singleton.

    Call this after modifying config to force reload.
    """
    global _default_taxonomy
    _default_taxonomy = None


__all__ = [
    "ConversionResult",
    "LayoutTaxonomy",
    "get_default_taxonomy",
    "reset_default_taxonomy",
]
