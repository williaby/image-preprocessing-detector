# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for schema migrations including property-based tests.

Tests migration infrastructure, FileMigrator, and invariant properties
using hypothesis for property-based testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from image_preprocessing_detector.annotation.schemas.migrations import (
    CURRENT_VERSION,
    FileMigrator,
    Migration,
    MigrationRegistry,
    get_migration_path,
    migrate_sample,
    rollback_sample,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_v1() -> dict[str, Any]:
    """Sample data at schema version 1.0."""
    return {
        "sample_id": "abc123",
        "record_meta": {"schema_version": "1.0"},
        "original": {"file_hash": "sha256:abc"},
        "enrichments": {"versions": []},
    }


@pytest.fixture
def sample_v2() -> dict[str, Any]:
    """Sample data at schema version 2.0."""
    return {
        "sample_id": "abc123",
        "record_meta": {"schema_version": "2.0"},
        "original": {"file_hash": "sha256:abc"},
        "enrichments": {"versions": []},
    }


@pytest.fixture
def sample_v21() -> dict[str, Any]:
    """Sample data at schema version 2.1."""
    return {
        "sample_id": "abc123",
        "record_meta": {"schema_version": "2.1"},
        "original": {"file_hash": "sha256:abc"},
        "enrichments": {
            "versions": [
                {
                    "data": {
                        "iso639_language": "en",
                        "iso15924_script": "Latn",
                    }
                }
            ]
        },
    }


@pytest.fixture
def migrator() -> FileMigrator:
    """Create FileMigrator instance."""
    return FileMigrator()


@pytest.fixture
def json_file(tmp_path: Path, sample_v1: dict[str, Any]) -> Path:
    """Create a temporary JSON file with v1 data."""
    file_path = tmp_path / "test_metadata.json"
    with open(file_path, "w") as f:
        json.dump(sample_v1, f)
    return file_path


# =============================================================================
# Unit Tests - MigrationRegistry
# =============================================================================


class TestMigrationRegistry:
    """Tests for MigrationRegistry class."""

    def test_register_migration(self) -> None:
        """Test registering a migration."""
        registry = MigrationRegistry()
        migration = Migration(
            from_version="1.0",
            to_version="1.1",
            forward=lambda d: d,
            backward=lambda d: d,
            description="Test migration",
        )

        registry.register(migration)

        assert registry.get_migration("1.0", "1.1") == migration

    def test_get_migration_not_found(self) -> None:
        """Test getting non-existent migration returns None."""
        registry = MigrationRegistry()

        assert registry.get_migration("1.0", "2.0") is None

    def test_get_path_same_version(self) -> None:
        """Test path between same versions is empty."""
        registry = MigrationRegistry()

        path = registry.get_path("1.0", "1.0")

        assert path == []

    def test_get_path_direct(self) -> None:
        """Test finding direct migration path."""
        registry = MigrationRegistry()
        migration = Migration(
            from_version="1.0",
            to_version="2.0",
            forward=lambda d: d,
            backward=lambda d: d,
            description="Test",
        )
        registry.register(migration)

        path = registry.get_path("1.0", "2.0")

        assert len(path) == 1
        assert path[0] == migration

    def test_get_path_multi_step(self) -> None:
        """Test finding multi-step migration path."""
        registry = MigrationRegistry()
        m1 = Migration("1.0", "1.5", lambda d: d, lambda d: d, "1->1.5")
        m2 = Migration("1.5", "2.0", lambda d: d, lambda d: d, "1.5->2")
        registry.register(m1)
        registry.register(m2)

        path = registry.get_path("1.0", "2.0")

        assert len(path) == 2
        assert path[0] == m1
        assert path[1] == m2

    def test_get_path_no_path(self) -> None:
        """Test error when no path exists."""
        registry = MigrationRegistry()
        registry.register(Migration("1.0", "1.5", lambda d: d, lambda d: d, ""))

        with pytest.raises(ValueError, match="No migration path"):
            registry.get_path("1.0", "2.0")


# =============================================================================
# Unit Tests - migrate_sample
# =============================================================================


class TestMigrateSample:
    """Tests for migrate_sample function."""

    def test_migrate_1_to_21(self, sample_v1: dict[str, Any]) -> None:
        """Test migrating from 1.0 to current version."""
        result = migrate_sample(sample_v1, "1.0", CURRENT_VERSION)

        assert result["record_meta"]["schema_version"] == CURRENT_VERSION

    def test_migrate_same_version(self, sample_v21: dict[str, Any]) -> None:
        """Test migrating to same version returns unchanged data."""
        result = migrate_sample(sample_v21, CURRENT_VERSION, CURRENT_VERSION)

        assert result == sample_v21

    def test_migrate_auto_detects_version(self, sample_v2: dict[str, Any]) -> None:
        """Test version auto-detection from data."""
        result = migrate_sample(sample_v2)  # No from_version

        assert result["record_meta"]["schema_version"] == CURRENT_VERSION

    def test_migrate_updates_version(self, sample_v1: dict[str, Any]) -> None:
        """Test migration updates schema_version field."""
        result = migrate_sample(sample_v1, "1.0", "2.0")

        assert result["record_meta"]["schema_version"] == "2.0"


# =============================================================================
# Unit Tests - rollback_sample
# =============================================================================


class TestRollbackSample:
    """Tests for rollback_sample function."""

    def test_rollback_21_to_20(self, sample_v21: dict[str, Any]) -> None:
        """Test rolling back from 2.1 to 2.0."""
        result = rollback_sample(sample_v21, "2.0")

        assert result["record_meta"]["schema_version"] == "2.0"

    def test_rollback_removes_v21_fields(self, sample_v21: dict[str, Any]) -> None:
        """Test rollback removes version-specific fields."""
        result = rollback_sample(sample_v21, "2.0")

        # V2.1 specific fields should be removed
        if result["enrichments"]["versions"]:
            data = result["enrichments"]["versions"][0].get("data", {})
            assert "iso639_language" not in data

    def test_rollback_same_version(self, sample_v21: dict[str, Any]) -> None:
        """Test rolling back to same version returns unchanged."""
        result = rollback_sample(sample_v21, CURRENT_VERSION)

        assert result == sample_v21


# =============================================================================
# Unit Tests - FileMigrator
# =============================================================================


class TestFileMigrator:
    """Tests for FileMigrator class."""

    def test_migrate_file_success(
        self, migrator: FileMigrator, json_file: Path
    ) -> None:
        """Test successful file migration."""
        result = migrator.migrate_file(json_file)

        assert result.success
        assert result.from_version == "1.0"
        assert result.to_version == CURRENT_VERSION
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_migrate_file_creates_backup(
        self, migrator: FileMigrator, json_file: Path
    ) -> None:
        """Test migration creates backup file."""
        result = migrator.migrate_file(json_file)

        assert result.backup_path is not None
        assert result.backup_path.exists()
        assert ".bak_v1.0" in str(result.backup_path)

    def test_migrate_file_dry_run(
        self, migrator: FileMigrator, json_file: Path
    ) -> None:
        """Test dry run doesn't modify file."""
        original_content = json_file.read_text()

        result = migrator.migrate_file(json_file, dry_run=True)

        assert result.dry_run
        assert result.success
        assert result.backup_path is None
        assert json_file.read_text() == original_content

    def test_migrate_file_already_current(
        self, migrator: FileMigrator, tmp_path: Path, sample_v21: dict[str, Any]
    ) -> None:
        """Test migrating file already at current version."""
        file_path = tmp_path / "current.json"
        with open(file_path, "w") as f:
            json.dump(sample_v21, f)

        result = migrator.migrate_file(file_path)

        assert result.success
        assert result.from_version == result.to_version
        assert result.migrations_applied == []

    def test_migrate_file_invalid_json(
        self, migrator: FileMigrator, tmp_path: Path
    ) -> None:
        """Test handling of invalid JSON file."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json")

        result = migrator.migrate_file(file_path)

        assert not result.success
        assert "Failed to read" in str(result.error)

    def test_rollback_file_from_backup(
        self, migrator: FileMigrator, json_file: Path
    ) -> None:
        """Test rollback restores from backup."""
        # First migrate
        migrate_result = migrator.migrate_file(json_file)
        assert migrate_result.success

        # Then rollback
        rollback_result = migrator.rollback_file(json_file, "1.0")

        assert rollback_result.success

        # Verify content is back to v1.0
        with open(json_file) as f:
            data = json.load(f)
        assert data["record_meta"]["schema_version"] == "1.0"

    def test_migrate_directory(
        self, migrator: FileMigrator, tmp_path: Path, sample_v1: dict[str, Any]
    ) -> None:
        """Test migrating all files in directory."""
        # Create multiple files
        for i in range(3):
            file_path = tmp_path / f"file_{i}.json"
            with open(file_path, "w") as f:
                json.dump(sample_v1, f)

        results = migrator.migrate_directory(tmp_path)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_list_backups(self, migrator: FileMigrator, json_file: Path) -> None:
        """Test listing backup files."""
        # Create backups
        migrator.migrate_file(json_file)

        backups = migrator.list_backups(json_file.parent)

        assert len(backups) >= 1

    def test_clean_backups(
        self, migrator: FileMigrator, tmp_path: Path, sample_v1: dict[str, Any]
    ) -> None:
        """Test cleaning old backups."""
        # Create file and multiple backups
        file_path = tmp_path / "test.json"
        with open(file_path, "w") as f:
            json.dump(sample_v1, f)

        # Create multiple backups manually
        for v in ["0.8", "0.9", "1.0"]:
            backup = tmp_path / f"test.json.bak_v{v}"
            backup.write_text("{}")

        deleted = migrator.clean_backups(tmp_path, keep_versions=1)

        assert len(deleted) == 2  # Kept 1, deleted 2


# =============================================================================
# Unit Tests - get_migration_path
# =============================================================================


class TestGetMigrationPath:
    """Tests for get_migration_path function."""

    def test_path_1_to_21(self) -> None:
        """Test path from 1.0 to 2.1."""
        path = get_migration_path("1.0", CURRENT_VERSION)

        assert "1.0->2.0" in path
        assert "2.0->2.1" in path

    def test_path_same_version(self) -> None:
        """Test path between same version is empty."""
        path = get_migration_path("2.0", "2.0")

        assert path == []


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================


# Strategy for generating sample data
sample_data_strategy = st.fixed_dictionaries(
    {
        "sample_id": st.text(min_size=1, max_size=32),
        "record_meta": st.fixed_dictionaries(
            {
                "schema_version": st.sampled_from(["1.0", "2.0", "2.1"]),
            }
        ),
        "original": st.fixed_dictionaries(
            {
                "file_hash": st.text(min_size=1, max_size=64),
            }
        ),
        "enrichments": st.fixed_dictionaries(
            {
                "versions": st.lists(
                    st.fixed_dictionaries(
                        {
                            "data": st.dictionaries(
                                st.text(min_size=1, max_size=20),
                                st.text(max_size=100),
                                max_size=5,
                            ),
                        }
                    ),
                    max_size=3,
                ),
            }
        ),
    }
)


class TestMigrationInvariants:
    """Property-based tests for migration invariants."""

    @given(data=sample_data_strategy)
    @settings(max_examples=50)
    def test_migrate_preserves_sample_id(self, data: dict[str, Any]) -> None:
        """INVARIANT: Migration never changes sample_id."""
        original_id = data["sample_id"]

        result = migrate_sample(data, to_version=CURRENT_VERSION)

        assert result["sample_id"] == original_id

    @given(data=sample_data_strategy)
    @settings(max_examples=50)
    def test_migrate_preserves_original_layer(self, data: dict[str, Any]) -> None:
        """INVARIANT: Migration preserves the immutable original layer."""
        original_hash = data["original"]["file_hash"]

        result = migrate_sample(data, to_version=CURRENT_VERSION)

        assert result["original"]["file_hash"] == original_hash

    @given(data=sample_data_strategy)
    @settings(max_examples=50)
    def test_migrate_updates_version(self, data: dict[str, Any]) -> None:
        """INVARIANT: Migration sets correct target version."""
        target = "2.1"

        result = migrate_sample(data, to_version=target)

        assert result["record_meta"]["schema_version"] == target

    @given(data=sample_data_strategy)
    @settings(max_examples=50)
    def test_migrate_roundtrip(self, data: dict[str, Any]) -> None:
        """INVARIANT: Migrate then rollback preserves structure."""
        from_version = data["record_meta"]["schema_version"]

        # Migrate forward
        migrated = migrate_sample(data, from_version, CURRENT_VERSION)

        # Rollback
        rolled_back = rollback_sample(migrated, from_version)

        # Key fields preserved
        assert rolled_back["sample_id"] == data["sample_id"]
        assert rolled_back["original"] == data["original"]
        assert rolled_back["record_meta"]["schema_version"] == from_version

    @given(data=sample_data_strategy)
    @settings(max_examples=30)
    def test_migrate_idempotent(self, data: dict[str, Any]) -> None:
        """INVARIANT: Migrating already-current data is idempotent."""
        # First migration
        result1 = migrate_sample(data, to_version=CURRENT_VERSION)

        # Second migration (should be no-op)
        result2 = migrate_sample(result1, to_version=CURRENT_VERSION)

        assert result1 == result2

    @given(
        version1=st.sampled_from(["1.0", "2.0"]),
        version2=st.sampled_from(["2.0", "2.1"]),
    )
    @settings(max_examples=20)
    def test_migration_path_exists(self, version1: str, version2: str) -> None:
        """INVARIANT: Migration path exists between supported versions."""
        # Should not raise ValueError
        path = get_migration_path(version1, version2)
        assert isinstance(path, list)


class TestFileMigratorInvariants:
    """Property-based tests for FileMigrator invariants."""

    @given(
        version=st.sampled_from(["1.0", "2.0"]),
        content=st.text(min_size=1, max_size=100),
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_backup_created_before_modify(
        self, tmp_path: Path, version: str, content: str
    ) -> None:
        """INVARIANT: Backup is created before file is modified."""
        import tempfile

        # Create unique temp directory for each hypothesis example
        test_dir = Path(tempfile.mkdtemp(dir=tmp_path))

        # Create test file
        data = {
            "sample_id": content[:32] or "test",
            "record_meta": {"schema_version": version},
            "original": {"file_hash": "test"},
            "enrichments": {"versions": []},
        }
        file_path = test_dir / "test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        migrator = FileMigrator()
        result = migrator.migrate_file(file_path)

        if result.success and version != CURRENT_VERSION:
            # Backup should exist with original content
            assert result.backup_path is not None
            assert result.backup_path.exists()

            with open(result.backup_path) as f:
                backup_data = json.load(f)
            assert backup_data["record_meta"]["schema_version"] == version

    @given(version=st.sampled_from(["1.0", "2.0", "2.1"]))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_dry_run_no_side_effects(self, tmp_path: Path, version: str) -> None:
        """INVARIANT: Dry run has no side effects."""
        import tempfile

        # Create unique temp directory for each hypothesis example
        test_dir = Path(tempfile.mkdtemp(dir=tmp_path))

        data = {
            "sample_id": "test",
            "record_meta": {"schema_version": version},
            "original": {"file_hash": "test"},
            "enrichments": {"versions": []},
        }
        file_path = test_dir / "test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        original_content = file_path.read_text()

        migrator = FileMigrator()
        result = migrator.migrate_file(file_path, dry_run=True)

        assert result.dry_run
        assert file_path.read_text() == original_content
        # No backup created
        backups = list(test_dir.glob("*.bak_*"))
        assert len(backups) == 0
