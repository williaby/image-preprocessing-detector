"""Schema version migrations with rollback support.

This module provides infrastructure for migrating metadata between
schema versions, with support for both forward and backward migrations.

Migration Philosophy:
    - Additive changes (new optional fields): No migration needed
    - Field renames: Bidirectional mapping
    - Type changes: Transform functions
    - Field removals: Archive in raw_labels

File Migration (Backup-Before-Migrate Pattern):
    >>> from image_preprocessing_detector.annotation.schemas.migrations import (
    ...     FileMigrator,
    ...     MigrationResult,
    ... )
    >>>
    >>> # Migrate file with automatic backup
    >>> migrator = FileMigrator()
    >>> result = migrator.migrate_file(Path("metadata.json"))
    >>> if result.success:
    ...     print(f"Migrated {result.from_version} -> {result.to_version}")
    ...     print(f"Backup: {result.backup_path}")
    >>>
    >>> # Rollback if needed
    >>> migrator.rollback_file(Path("metadata.json"), "2.0")

In-Memory Migration:
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

import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

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
        record_meta = data.get("record_meta", {})
        from_version = str(record_meta.get("schema_version", "1.0"))

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


# =============================================================================
# File Migration with Backup Support (Phase 3.2.2)
# =============================================================================


class MigrationError(Exception):
    """Exception raised when migration fails.

    Attributes:
        file_path: Path to the file being migrated
        from_version: Source version
        to_version: Target version
        cause: Original exception
    """

    def __init__(
        self,
        file_path: Path | str,
        from_version: str,
        to_version: str,
        cause: Exception | None = None,
    ):
        """Initialize migration error.

        Args:
            file_path: Path to the file being migrated.
            from_version: Source schema version.
            to_version: Target schema version.
            cause: Original exception that triggered the failure.
        """
        self.file_path = Path(file_path)
        self.from_version = from_version
        self.to_version = to_version
        self.cause = cause

        msg = f"Migration failed for {file_path}: {from_version} -> {to_version}"
        if cause:
            msg += f" ({cause})"
        super().__init__(msg)


@dataclass
class MigrationResult:
    """Result of a file migration operation.

    Attributes:
        file_path: Path to the migrated file
        success: Whether migration succeeded
        from_version: Source schema version
        to_version: Target schema version
        backup_path: Path to backup file (if created)
        dry_run: Whether this was a dry run (no changes made)
        error: Error message if migration failed
        migrations_applied: List of migration steps applied
    """

    file_path: Path
    success: bool
    from_version: str
    to_version: str
    backup_path: Path | None = None
    dry_run: bool = False
    error: str | None = None
    migrations_applied: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Human-readable result."""
        if self.dry_run:
            status = "DRY RUN"
        elif self.success:
            status = "SUCCESS"
        else:
            status = "FAILED"

        result = (
            f"[{status}] {self.file_path}: {self.from_version} -> {self.to_version}"
        )
        if self.error:
            result += f" ({self.error})"
        return result


class FileMigrator:
    """File-level migration with backup-before-migrate pattern.

    CRITICAL: Always creates backup before modifying files.
    Backups are preserved on failure for manual recovery.

    Attributes:
        backup_dir: Directory for backup files (default: alongside original)
        backup_suffix: Suffix for backup files (default: .bak_v{version})
        fsync: Whether to fsync after writes for durability

    Example:
        >>> migrator = FileMigrator()
        >>>
        >>> # Migrate single file
        >>> result = migrator.migrate_file(Path("metadata.json"))
        >>> if result.success:
        ...     print(f"Backup at: {result.backup_path}")
        >>>
        >>> # Dry run to preview changes
        >>> result = migrator.migrate_file(Path("metadata.json"), dry_run=True)
        >>>
        >>> # Migrate directory
        >>> results = migrator.migrate_directory(Path("./metadata/"))
    """

    def __init__(
        self,
        backup_dir: Path | None = None,
        backup_suffix: str = ".bak_v{version}",
        fsync: bool = False,
    ):
        """Initialize FileMigrator.

        Args:
            backup_dir: Directory for backups (None = same dir as file)
            backup_suffix: Suffix template for backup files
            fsync: Whether to fsync writes for durability
        """
        self.backup_dir = backup_dir
        self.backup_suffix = backup_suffix
        self.fsync = fsync

    def migrate_file(
        self,
        file_path: Path,
        target_version: str = CURRENT_VERSION,
        dry_run: bool = False,
        skip_backup: bool = False,
    ) -> MigrationResult:
        """Migrate a single JSON file to target version.

        CRITICAL: Creates backup before any modification.

        Args:
            file_path: Path to JSON metadata file
            target_version: Target schema version (default: current)
            dry_run: If True, return result without modifying file
            skip_backup: If True, skip backup creation (dangerous)

        Returns:
            MigrationResult with details of the operation

        Raises:
            MigrationError: If migration fails and backup cannot be restored
        """
        file_path = Path(file_path)

        # Load and parse file
        try:
            with open(file_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return MigrationResult(
                file_path=file_path,
                success=False,
                from_version="unknown",
                to_version=target_version,
                error=f"Failed to read file: {e}",
            )

        # Get current version
        current_version = data.get("record_meta", {}).get("schema_version", "1.0")

        # Check if migration needed
        if current_version == target_version:
            return MigrationResult(
                file_path=file_path,
                success=True,
                from_version=current_version,
                to_version=target_version,
                dry_run=dry_run,
                migrations_applied=[],
            )

        # Get migration path
        try:
            path = _registry.get_path(current_version, target_version)
            migrations_applied = [f"{m.from_version}->{m.to_version}" for m in path]
        except ValueError as e:
            return MigrationResult(
                file_path=file_path,
                success=False,
                from_version=current_version,
                to_version=target_version,
                error=str(e),
            )

        # Dry run - return what would happen
        if dry_run:
            return MigrationResult(
                file_path=file_path,
                success=True,
                from_version=current_version,
                to_version=target_version,
                dry_run=True,
                migrations_applied=migrations_applied,
            )

        # Create backup BEFORE migration
        backup_path = None
        if not skip_backup:
            backup_path = self._create_backup(file_path, current_version)
            logger.info(f"Created backup: {backup_path}")

        # Apply migrations
        try:
            migrated_data = migrate_sample(data, current_version, target_version)

            # Write migrated file
            self._write_json(file_path, migrated_data)

            return MigrationResult(
                file_path=file_path,
                success=True,
                from_version=current_version,
                to_version=target_version,
                backup_path=backup_path,
                migrations_applied=migrations_applied,
            )

        except Exception as exc:
            logger.exception(f"Migration failed for {file_path}")
            # Backup preserved for recovery
            return MigrationResult(
                file_path=file_path,
                success=False,
                from_version=current_version,
                to_version=target_version,
                backup_path=backup_path,
                error=str(exc),
            )

    def rollback_file(
        self,
        file_path: Path,
        to_version: str,
    ) -> MigrationResult:
        """Rollback file to a specific version.

        First tries to restore from backup file. If no backup exists,
        applies backward migrations.

        Args:
            file_path: Path to file to rollback
            to_version: Version to rollback to

        Returns:
            MigrationResult with rollback details
        """
        file_path = Path(file_path)

        # Try to find backup
        backup_path = self._get_backup_path(file_path, to_version)
        if backup_path.exists():
            # Restore from backup
            shutil.copy(backup_path, file_path)
            logger.info(f"Restored from backup: {backup_path}")
            return MigrationResult(
                file_path=file_path,
                success=True,
                from_version="backup",
                to_version=to_version,
                backup_path=backup_path,
            )

        # No backup - try backward migration
        try:
            with open(file_path) as f:
                data = json.load(f)

            current_version = data.get("record_meta", {}).get(
                "schema_version", CURRENT_VERSION
            )

            # Create backup of current state before rollback
            pre_rollback_backup = self._create_backup(file_path, current_version)

            # Apply backward migrations
            rolled_back = rollback_sample(data, to_version)
            self._write_json(file_path, rolled_back)

            return MigrationResult(
                file_path=file_path,
                success=True,
                from_version=current_version,
                to_version=to_version,
                backup_path=pre_rollback_backup,
            )

        except Exception as e:
            return MigrationResult(
                file_path=file_path,
                success=False,
                from_version="unknown",
                to_version=to_version,
                error=str(e),
            )

    def migrate_directory(
        self,
        directory: Path,
        target_version: str = CURRENT_VERSION,
        pattern: str = "**/*.json",
        dry_run: bool = False,
    ) -> list[MigrationResult]:
        """Migrate all JSON files in a directory.

        Args:
            directory: Directory to process
            target_version: Target schema version
            pattern: Glob pattern for files
            dry_run: If True, preview changes without modifying

        Returns:
            List of MigrationResult for each file
        """
        directory = Path(directory)
        results = []

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                result = self.migrate_file(file_path, target_version, dry_run)
                results.append(result)

        return results

    def list_backups(self, directory: Path) -> list[Path]:
        """List all backup files in a directory.

        Args:
            directory: Directory to search

        Returns:
            List of backup file paths
        """
        return list(directory.glob("*.bak_v*"))

    def clean_backups(
        self,
        directory: Path,
        keep_versions: int = 2,
        dry_run: bool = False,
    ) -> list[Path]:
        """Clean old backup files, keeping recent versions.

        Args:
            directory: Directory to clean
            keep_versions: Number of backup versions to keep per file
            dry_run: If True, return files that would be deleted

        Returns:
            List of deleted (or would-be-deleted) backup paths
        """
        # Group backups by original file
        backup_groups: dict[str, list[Path]] = {}
        for backup in self.list_backups(directory):
            # Extract original filename (everything before .bak_v)
            name = backup.name
            if ".bak_v" in name:
                original = name.split(".bak_v")[0]
                if original not in backup_groups:
                    backup_groups[original] = []
                backup_groups[original].append(backup)

        deleted = []
        for backups in backup_groups.values():
            # Sort by modification time, newest first
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Delete old backups
            for backup in backups[keep_versions:]:
                if not dry_run:
                    backup.unlink()
                    logger.info(f"Deleted old backup: {backup}")
                deleted.append(backup)

        return deleted

    def _create_backup(self, file_path: Path, version: str) -> Path:
        """Create backup of file before migration.

        Args:
            file_path: File to backup
            version: Current version for backup naming

        Returns:
            Path to backup file
        """
        # Determine backup path
        suffix = self.backup_suffix.format(version=version)
        if self.backup_dir:
            backup_dir = self.backup_dir
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_name = file_path.name + suffix
            backup_path = backup_dir / backup_name
        else:
            backup_path = file_path.with_suffix(file_path.suffix + suffix)

        # Add timestamp if backup already exists (preserve version marker)
        if backup_path.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            # Append timestamp while preserving version: .bak_v1.0 -> .bak_v1.0.20250126123456
            backup_path = backup_path.parent / f"{backup_path.name}.{timestamp}"

        shutil.copy(file_path, backup_path)
        return backup_path

    def _get_backup_path(self, file_path: Path, version: str) -> Path:
        """Get backup path for a version, searching for timestamped variants.

        First checks for exact match, then searches for timestamped backups
        matching the version pattern.

        Args:
            file_path: Original file path
            version: Version to find backup for

        Returns:
            Path to most recent backup for this version (may not exist)
        """
        suffix = self.backup_suffix.format(version=version)

        if self.backup_dir:
            backup_dir = self.backup_dir
            base_backup = backup_dir / (file_path.name + suffix)
            search_pattern = f"{file_path.name}{suffix}*"
        else:
            backup_dir = file_path.parent
            base_backup = file_path.with_suffix(file_path.suffix + suffix)
            search_pattern = f"{file_path.stem}{file_path.suffix}{suffix}*"

        # Try exact match first
        if base_backup.exists():
            return base_backup

        # Search for timestamped variants
        matching_backups = sorted(
            backup_dir.glob(search_pattern),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,  # Most recent first
        )

        if matching_backups:
            return matching_backups[0]

        # Return expected path even if it doesn't exist
        return base_backup

    def _write_json(self, file_path: Path, data: dict[str, Any]) -> None:
        """Write JSON file atomically with optional fsync.

        Uses atomic write pattern to prevent corruption on crash.

        Args:
            file_path: File to write
            data: Data to serialize
        """
        from ..integrity.atomic import atomic_json_write

        atomic_json_write(file_path, data, indent=2, fsync=self.fsync)


__all__ = [
    "CURRENT_VERSION",
    "MIN_SUPPORTED_VERSION",
    "FileMigrator",
    "Migration",
    "MigrationError",
    "MigrationRegistry",
    "MigrationResult",
    "get_migration_path",
    "migrate_sample",
    "register_migration",
    "rollback_sample",
]
