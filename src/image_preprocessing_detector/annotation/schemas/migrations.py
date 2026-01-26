# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Schema version migrations with rollback support.

This module provides infrastructure for migrating metadata between
schema versions, with support for both forward and backward migrations.

Migration Philosophy:
    - Additive changes (new optional fields): No migration needed
    - Field renames: Bidirectional mapping
    - Type changes: Transform functions
    - Field removals: Archive in raw_labels

Example:
    >>> from image_preprocessing_detector.annotation.schemas.migrations import (
    ...     migrate_sample,
    ...     get_migration_path,
    ...     CURRENT_VERSION,
    ... )
    >>>
    >>> # Migrate sample to current version
    >>> migrated = migrate_sample(old_sample_data, from_version="1.0")
    >>>
    >>> # Check migration path
    >>> path = get_migration_path("1.0", "2.1")
    >>> print(path)  # ["1.0->2.0", "2.0->2.1"]
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Current schema version
CURRENT_VERSION = "2.1"

# Minimum supported version for migration
MIN_SUPPORTED_VERSION = "1.0"


@dataclass
class Migration:
    """Represents a single migration step.

    Attributes:
        from_version: Source schema version
        to_version: Target schema version
        forward: Function to migrate forward
        backward: Function to migrate backward (rollback)
        description: Human-readable description
    """

    from_version: str
    to_version: str
    forward: Callable[[dict[str, Any]], dict[str, Any]]
    backward: Callable[[dict[str, Any]], dict[str, Any]]
    description: str


class MigrationRegistry:
    """Registry of all available migrations.

    Maintains a graph of migrations between schema versions,
    supporting automatic path finding for multi-step migrations.
    """

    def __init__(self) -> None:
        """Initialize empty migration registry."""
        self._migrations: dict[tuple[str, str], Migration] = {}

    def register(self, migration: Migration) -> None:
        """Register a migration.

        Args:
            migration: Migration to register
        """
        key = (migration.from_version, migration.to_version)
        self._migrations[key] = migration

    def get_migration(self, from_version: str, to_version: str) -> Migration | None:
        """Get a direct migration between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration if exists, None otherwise
        """
        return self._migrations.get((from_version, to_version))

    def get_path(self, from_version: str, to_version: str) -> list[Migration]:
        """Find migration path between versions.

        Uses breadth-first search to find shortest path.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            List of migrations to apply in order

        Raises:
            ValueError: If no path exists
        """
        if from_version == to_version:
            return []

        # BFS to find shortest path
        visited: set[str] = set()
        queue: list[tuple[str, list[Migration]]] = [(from_version, [])]

        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for (src, dst), migration in self._migrations.items():
                if src == current and dst not in visited:
                    new_path = [*path, migration]
                    if dst == to_version:
                        return new_path
                    queue.append((dst, new_path))

        raise ValueError(f"No migration path from {from_version} to {to_version}")


# Global migration registry
_registry = MigrationRegistry()


def register_migration(
    from_version: str,
    to_version: str,
    forward: Callable[[dict[str, Any]], dict[str, Any]],
    backward: Callable[[dict[str, Any]], dict[str, Any]],
    description: str,
) -> None:
    """Register a new migration.

    Args:
        from_version: Source schema version
        to_version: Target schema version
        forward: Forward migration function
        backward: Backward migration function
        description: Human-readable description
    """
    migration = Migration(
        from_version=from_version,
        to_version=to_version,
        forward=forward,
        backward=backward,
        description=description,
    )
    _registry.register(migration)


def migrate_sample(
    data: dict[str, Any],
    from_version: str | None = None,
    to_version: str = CURRENT_VERSION,
) -> dict[str, Any]:
    """Migrate sample data between schema versions.

    Args:
        data: Sample data dictionary
        from_version: Source version (auto-detected from data if None)
        to_version: Target version (defaults to current)

    Returns:
        Migrated data dictionary

    Raises:
        ValueError: If migration path not found
    """
    if from_version is None:
        from_version = data.get("record_meta", {}).get("schema_version", "1.0")

    if from_version == to_version:
        return data

    path = _registry.get_path(from_version, to_version)
    result = data.copy()

    for migration in path:
        result = migration.forward(result)
        # Update schema version in result
        if "record_meta" not in result:
            result["record_meta"] = {}
        result["record_meta"]["schema_version"] = migration.to_version

    return result


def rollback_sample(
    data: dict[str, Any],
    to_version: str,
) -> dict[str, Any]:
    """Rollback sample data to an earlier schema version.

    Args:
        data: Sample data dictionary
        to_version: Target version to rollback to

    Returns:
        Rolled back data dictionary

    Raises:
        ValueError: If rollback path not found
    """
    from_version = data.get("record_meta", {}).get("schema_version", CURRENT_VERSION)

    if from_version == to_version:
        return data

    # Find path in reverse order using backward migrations
    path = _registry.get_path(to_version, from_version)
    result = data.copy()

    # Apply backward migrations in reverse order
    for migration in reversed(path):
        result = migration.backward(result)
        if "record_meta" not in result:
            result["record_meta"] = {}
        result["record_meta"]["schema_version"] = migration.from_version

    return result


def get_migration_path(from_version: str, to_version: str) -> list[str]:
    """Get human-readable migration path.

    Args:
        from_version: Source version
        to_version: Target version

    Returns:
        List of migration step descriptions (e.g., ["1.0->2.0", "2.0->2.1"])
    """
    path = _registry.get_path(from_version, to_version)
    return [f"{m.from_version}->{m.to_version}" for m in path]


# =============================================================================
# Migration Definitions
# =============================================================================

# Migration stubs - actual migrations will be defined as needed


def _migrate_1_0_to_2_0(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate from schema 1.0 to 2.0.

    Changes:
        - Added enrichment versioning structure
        - Added reproducibility fields
    """
    return data.copy()
    # Stub: actual migration logic goes here


def _rollback_2_0_to_1_0(data: dict[str, Any]) -> dict[str, Any]:
    """Rollback from schema 2.0 to 1.0.

    Inverse of _migrate_1_0_to_2_0.
    """
    return data.copy()
    # Stub: actual rollback logic goes here


def _migrate_2_0_to_2_1(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate from schema 2.0 to 2.1.

    Changes:
        - Added ISO language/script fields
        - Added text_scope fields
        - Added paper_size fields
        - Added dataset_short_code
    """
    return data.copy()
    # These are additive changes with None defaults, so no transform needed


def _rollback_2_1_to_2_0(data: dict[str, Any]) -> dict[str, Any]:
    """Rollback from schema 2.1 to 2.0.

    Removes 2.1-specific fields.
    """
    result = data.copy()
    # Remove 2.1-specific fields from enrichment data
    if "enrichments" in result and "versions" in result["enrichments"]:
        for version in result["enrichments"]["versions"]:
            if "data" in version:
                v21_fields = [
                    "iso639_language",
                    "iso15924_script",
                    "script_family",
                    "bcp47_tag",
                    "text_scope",
                    "text_scope_content_type",
                    "text_scope_estimated_chars",
                    "text_scope_estimated_words",
                    "text_scope_detection_method",
                    "paper_size",
                    "paper_size_standard",
                    "paper_size_orientation",
                    "paper_size_confidence",
                    "paper_size_is_exact",
                    "dataset_short_code",
                ]
                for field in v21_fields:
                    version["data"].pop(field, None)
    return result


# Register migrations
register_migration(
    "1.0",
    "2.0",
    _migrate_1_0_to_2_0,
    _rollback_2_0_to_1_0,
    "Added enrichment versioning and reproducibility fields",
)

register_migration(
    "2.0",
    "2.1",
    _migrate_2_0_to_2_1,
    _rollback_2_1_to_2_0,
    "Added ISO language/script, text_scope, paper_size, dataset_short_code",
)


__all__ = [
    "CURRENT_VERSION",
    "MIN_SUPPORTED_VERSION",
    "Migration",
    "MigrationRegistry",
    "get_migration_path",
    "migrate_sample",
    "register_migration",
    "rollback_sample",
]
