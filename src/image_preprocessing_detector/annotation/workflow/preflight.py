"""Pre-flight validation for annotation workflows.

Phase 5 Task 5.5.1: Production hardening with pre-flight checks that validate
system requirements before starting long-running annotation operations.

Validates:
- Disk space availability
- Path accessibility (read/write)
- Model availability
- Provider connectivity (optional)
- Configuration consistency

Example:
    >>> from image_preprocessing_detector.annotation.workflow.preflight import (
    ...     PreflightChecker,
    ...     PreflightConfig,
    ...     run_preflight_checks,
    ... )
    >>>
    >>> checker = PreflightChecker()
    >>> result = checker.check_all(
    ...     dataset_path=Path("/data/pubtabnet"),
    ...     output_path=Path("/output"),
    ... )
    >>> if not result.passed:
    ...     print(f"Pre-flight failed: {result.failures}")
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class CheckSeverity(str, Enum):
    """Severity level for pre-flight check failures."""

    ERROR = "error"  # Must fix before proceeding
    WARNING = "warning"  # Can proceed but should address
    INFO = "info"  # Informational only


class CheckCategory(str, Enum):
    """Category of pre-flight check."""

    DISK = "disk"
    PATH = "path"
    MODEL = "model"
    PROVIDER = "provider"
    CONFIG = "config"
    SYSTEM = "system"


@dataclass
class CheckResult:
    """Result of a single pre-flight check.

    Attributes:
        name (str): Check name
        passed (bool): Whether check passed
        category (CheckCategory): Check category
        severity (CheckSeverity): Failure severity (if failed)
        message (str): Human-readable message
        details (dict[str, Any]): Additional details
    """

    name: str
    passed: bool
    category: CheckCategory
    severity: CheckSeverity = CheckSeverity.INFO
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "passed": self.passed,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class PreflightResult:
    """Aggregated result of all pre-flight checks.

    Attributes:
        passed (bool): Whether all critical checks passed
        checks (list[CheckResult]): Individual check results
        warnings (list[str]): List of warning messages
        errors (list[str]): List of error messages
    """

    passed: bool = True
    checks: list[CheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def failures(self) -> list[CheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed]

    @property
    def critical_failures(self) -> list[CheckResult]:
        """Get list of critical (error severity) failures."""
        return [
            c for c in self.checks if not c.passed and c.severity == CheckSeverity.ERROR
        ]

    def add_check(self, check: CheckResult) -> None:
        """Add a check result.

        Args:
            check (CheckResult): Check result to add
        """
        self.checks.append(check)

        if not check.passed:
            if check.severity == CheckSeverity.ERROR:
                self.passed = False
                self.errors.append(check.message)
            elif check.severity == CheckSeverity.WARNING:
                self.warnings.append(check.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "total_checks": len(self.checks),
            "failures": len(self.failures),
            "critical_failures": len(self.critical_failures),
            "warnings": self.warnings,
            "errors": self.errors,
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class PreflightConfig:
    """Configuration for pre-flight checks.

    Attributes:
        min_disk_space_gb (float): Minimum free disk space required
        check_write_permission (bool): Whether to verify write permissions
        check_model_availability (bool): Whether to verify model files
        check_provider_connectivity (bool): Whether to check external providers
        timeout_seconds (float): Timeout for connectivity checks
        required_read_paths (list[Path]): Paths that must be readable
        required_write_paths (list[Path]): Paths that must be writable
        model_paths (list[Path]): Model files to check
        provider_names (list[str]): Provider names to check
    """

    min_disk_space_gb: float = 10.0
    check_write_permission: bool = True
    check_model_availability: bool = True
    check_provider_connectivity: bool = False
    timeout_seconds: float = 5.0

    # Paths that must be readable
    required_read_paths: list[Path] = field(default_factory=list)

    # Paths that must be writable
    required_write_paths: list[Path] = field(default_factory=list)

    # Model files to check
    model_paths: list[Path] = field(default_factory=list)

    # Provider names to check (e.g., ["yolo", "siglip"])
    provider_names: list[str] = field(default_factory=list)


class PreflightChecker:
    """Pre-flight check runner for annotation workflows.

    Runs a series of validation checks before starting annotation
    operations to catch configuration issues early.

    Args:
        config (PreflightConfig | None): Pre-flight configuration
    """

    def __init__(self, config: PreflightConfig | None = None) -> None:
        self.config = config or PreflightConfig()
        self._custom_checks: list[Callable[[PreflightResult], None]] = []

    def register_check(
        self,
        check_fn: Callable[[PreflightResult], None],
    ) -> None:
        """Register a custom pre-flight check.

        Args:
            check_fn (Callable[[PreflightResult], None]): Check function that takes
                PreflightResult and adds checks
        """
        self._custom_checks.append(check_fn)

    def check_disk_space(
        self,
        path: Path,
        min_gb: float | None = None,
    ) -> CheckResult:
        """Check available disk space.

        Args:
            path (Path): Path to check disk space for
            min_gb (float | None): Minimum required GB (uses config default if None)

        Returns:
            CheckResult: Check result
        """
        min_required = min_gb or self.config.min_disk_space_gb

        try:
            # Get the mount point for the path
            check_path = path if path.exists() else path.parent
            while not check_path.exists() and check_path.parent != check_path:
                check_path = check_path.parent

            if not check_path.exists():
                return CheckResult(
                    name="disk_space",
                    passed=False,
                    category=CheckCategory.DISK,
                    severity=CheckSeverity.ERROR,
                    message=f"Cannot determine disk space: path not accessible: {path}",
                )

            usage = shutil.disk_usage(check_path)
            free_gb = usage.free / (1024**3)

            passed = free_gb >= min_required
            return CheckResult(
                name="disk_space",
                passed=passed,
                category=CheckCategory.DISK,
                severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
                message=(
                    f"Sufficient disk space: {free_gb:.1f}GB free"
                    if passed
                    else f"Insufficient disk space: {free_gb:.1f}GB free, {min_required}GB required"
                ),
                details={
                    "path": str(path),
                    "free_gb": round(free_gb, 2),
                    "required_gb": min_required,
                    "total_gb": round(usage.total / (1024**3), 2),
                },
            )
        except OSError as e:
            return CheckResult(
                name="disk_space",
                passed=False,
                category=CheckCategory.DISK,
                severity=CheckSeverity.ERROR,
                message=f"Failed to check disk space: {e}",
                details={"error": str(e), "path": str(path)},
            )

    def check_path_readable(self, path: Path) -> CheckResult:
        """Check if a path is readable.

        Args:
            path (Path): Path to check

        Returns:
            CheckResult: Check result
        """
        name = f"path_readable:{path.name}"

        if not path.exists():
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Path does not exist: {path}",
                details={"path": str(path)},
            )

        if not os.access(path, os.R_OK):
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Path not readable: {path}",
                details={"path": str(path)},
            )

        return CheckResult(
            name=name,
            passed=True,
            category=CheckCategory.PATH,
            message=f"Path readable: {path}",
            details={"path": str(path)},
        )

    def check_path_writable(self, path: Path) -> CheckResult:
        """Check if a path is writable.

        Args:
            path (Path): Path to check (creates parent if needed)

        Returns:
            CheckResult: Check result
        """
        name = f"path_writable:{path.name}"

        # If path doesn't exist, check if we can create it
        if not path.exists():
            parent = path.parent
            while not parent.exists() and parent.parent != parent:
                parent = parent.parent

            if not parent.exists():
                return CheckResult(
                    name=name,
                    passed=False,
                    category=CheckCategory.PATH,
                    severity=CheckSeverity.ERROR,
                    message=f"Cannot create path, no accessible parent: {path}",
                    details={"path": str(path)},
                )

            if not os.access(parent, os.W_OK):
                return CheckResult(
                    name=name,
                    passed=False,
                    category=CheckCategory.PATH,
                    severity=CheckSeverity.ERROR,
                    message=f"Cannot create path, parent not writable: {parent}",
                    details={"path": str(path), "parent": str(parent)},
                )

            return CheckResult(
                name=name,
                passed=True,
                category=CheckCategory.PATH,
                message=f"Path can be created: {path}",
                details={"path": str(path), "exists": False},
            )

        # Path exists - check write permission
        if not os.access(path, os.W_OK):
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Path not writable: {path}",
                details={"path": str(path)},
            )

        return CheckResult(
            name=name,
            passed=True,
            category=CheckCategory.PATH,
            message=f"Path writable: {path}",
            details={"path": str(path), "exists": True},
        )

    def check_model_file(self, path: Path) -> CheckResult:
        """Check if a model file exists and is readable.

        Args:
            path (Path): Path to model file

        Returns:
            CheckResult: Check result
        """
        name = f"model:{path.name}"

        if not path.exists():
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.MODEL,
                severity=CheckSeverity.ERROR,
                message=f"Model file not found: {path}",
                details={"path": str(path)},
            )

        if not path.is_file():
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.MODEL,
                severity=CheckSeverity.ERROR,
                message=f"Model path is not a file: {path}",
                details={"path": str(path)},
            )

        size_mb = path.stat().st_size / (1024 * 1024)

        return CheckResult(
            name=name,
            passed=True,
            category=CheckCategory.MODEL,
            message=f"Model file available: {path.name} ({size_mb:.1f}MB)",
            details={"path": str(path), "size_mb": round(size_mb, 2)},
        )

    def _find_missing_subdirs(
        self, path: Path, required_subdirs: list[str] | None
    ) -> list[str]:
        """Find missing required subdirectories."""
        if not required_subdirs:
            return []
        return [s for s in required_subdirs if not (path / s).is_dir()]

    def _find_missing_files(
        self, path: Path, required_files: list[str] | None
    ) -> list[str]:
        """Find missing required files."""
        if not required_files:
            return []
        return [f for f in required_files if not (path / f).exists()]

    def check_dataset_structure(
        self,
        path: Path,
        required_subdirs: list[str] | None = None,
        required_files: list[str] | None = None,
    ) -> CheckResult:
        """Check dataset directory structure.

        Args:
            path (Path): Dataset path
            required_subdirs (list[str] | None): List of required subdirectory names
            required_files (list[str] | None): List of required file names

        Returns:
            CheckResult: Check result
        """
        name = f"dataset_structure:{path.name}"

        if not path.exists():
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Dataset path does not exist: {path}",
                details={"path": str(path)},
            )

        if not path.is_dir():
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Dataset path is not a directory: {path}",
                details={"path": str(path)},
            )

        missing_subdirs = self._find_missing_subdirs(path, required_subdirs)
        missing_files = self._find_missing_files(path, required_files)

        if missing_subdirs or missing_files:
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PATH,
                severity=CheckSeverity.ERROR,
                message=f"Dataset missing required items: {missing_subdirs + missing_files}",
                details={
                    "path": str(path),
                    "missing_subdirs": missing_subdirs,
                    "missing_files": missing_files,
                },
            )

        return CheckResult(
            name=name,
            passed=True,
            category=CheckCategory.PATH,
            message=f"Dataset structure valid: {path}",
            details={"path": str(path)},
        )

    def check_provider_availability(self, provider_name: str) -> CheckResult:
        """Check if an enrichment provider is available.

        Attempts to load and check availability of the specified provider.
        Supports YOLO and SigLIP providers.

        Args:
            provider_name (str): Name of provider ("yolo" or "siglip")

        Returns:
            CheckResult: Check result indicating provider availability
        """
        name = f"provider:{provider_name}"

        try:
            if provider_name.lower() == "yolo":
                return self._check_yolo_provider(name)
            if provider_name.lower() == "siglip":
                return self._check_siglip_provider(name)
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING,
                message=f"Unknown provider: {provider_name}",
                details={"provider": provider_name},
            )
        except Exception as e:
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING,
                message=f"Provider check failed: {e}",
                details={"provider": provider_name, "error": str(e)},
            )

    def _check_yolo_provider(self, name: str) -> CheckResult:
        """Check YOLO provider availability."""
        try:
            from ..enrichment.providers.yolo import YOLOProvider

            provider = YOLOProvider()
            is_available = provider.is_available()

            return CheckResult(
                name=name,
                passed=is_available,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING
                if not is_available
                else CheckSeverity.INFO,
                message=(
                    "YOLO provider available"
                    if is_available
                    else "YOLO provider unavailable (model or dependencies missing)"
                ),
                details={
                    "provider": "yolo",
                    "available": is_available,
                    "device": provider.device,
                },
            )
        except ImportError as e:
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING,
                message=f"YOLO provider import failed: {e}",
                details={"provider": "yolo", "error": str(e)},
            )

    def _check_siglip_provider(self, name: str) -> CheckResult:
        """Check SigLIP provider availability."""
        try:
            from ..enrichment.providers.siglip import SigLIPProvider

            provider = SigLIPProvider()
            is_available = provider.is_available()

            return CheckResult(
                name=name,
                passed=is_available,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING
                if not is_available
                else CheckSeverity.INFO,
                message=(
                    "SigLIP provider available"
                    if is_available
                    else "SigLIP provider unavailable (model or dependencies missing)"
                ),
                details={
                    "provider": "siglip",
                    "available": is_available,
                    "device": provider.device,
                },
            )
        except ImportError as e:
            return CheckResult(
                name=name,
                passed=False,
                category=CheckCategory.PROVIDER,
                severity=CheckSeverity.WARNING,
                message=f"SigLIP provider import failed: {e}",
                details={"provider": "siglip", "error": str(e)},
            )

    def _check_output_path(self, result: PreflightResult, output_path: Path) -> None:
        """Add output path checks to result."""
        result.add_check(self.check_disk_space(output_path))
        if self.config.check_write_permission:
            result.add_check(self.check_path_writable(output_path))

    def _check_configured_paths(self, result: PreflightResult) -> None:
        """Add configured path checks to result."""
        for path in self.config.required_read_paths:
            result.add_check(self.check_path_readable(path))
        for path in self.config.required_write_paths:
            result.add_check(self.check_path_writable(path))

    def _check_models(self, result: PreflightResult) -> None:
        """Add model file checks to result."""
        if self.config.check_model_availability and self.config.model_paths:
            for model_path in self.config.model_paths:
                result.add_check(self.check_model_file(model_path))

    def _check_providers(self, result: PreflightResult) -> None:
        """Add provider availability checks to result."""
        if self.config.check_provider_connectivity and self.config.provider_names:
            for provider_name in self.config.provider_names:
                result.add_check(self.check_provider_availability(provider_name))

    def _run_custom_checks(self, result: PreflightResult) -> None:
        """Run registered custom checks."""
        for check_fn in self._custom_checks:
            try:
                check_fn(result)
            except Exception as e:
                result.add_check(
                    CheckResult(
                        name="custom_check",
                        passed=False,
                        category=CheckCategory.SYSTEM,
                        severity=CheckSeverity.WARNING,
                        message=f"Custom check failed: {e}",
                    )
                )

    def _log_result(self, result: PreflightResult) -> None:
        """Log pre-flight check summary."""
        if result.passed:
            logger.info(
                "preflight_passed",
                extra={
                    "total_checks": len(result.checks),
                    "warnings": len(result.warnings),
                },
            )
        else:
            logger.error(
                "preflight_failed",
                extra={
                    "total_checks": len(result.checks),
                    "failures": len(result.failures),
                    "errors": result.errors,
                },
            )

    def check_all(
        self,
        dataset_path: Path | None = None,
        output_path: Path | None = None,
        checkpoint_path: Path | None = None,
    ) -> PreflightResult:
        """Run all pre-flight checks.

        Args:
            dataset_path (Path | None): Path to dataset (optional)
            output_path (Path | None): Path for output files (optional)
            checkpoint_path (Path | None): Path for checkpoints (optional)

        Returns:
            PreflightResult: Aggregated pre-flight result
        """
        result = PreflightResult()

        # Output path checks
        if output_path:
            self._check_output_path(result, output_path)

        # Dataset path check
        if dataset_path:
            result.add_check(self.check_path_readable(dataset_path))

        # Checkpoint path check
        if checkpoint_path and self.config.check_write_permission:
            result.add_check(self.check_path_writable(checkpoint_path))

        # Configured paths, models, and providers
        self._check_configured_paths(result)
        self._check_models(result)
        self._check_providers(result)
        self._run_custom_checks(result)
        self._log_result(result)

        return result


def run_preflight_checks(
    dataset_path: Path | None = None,
    output_path: Path | None = None,
    checkpoint_path: Path | None = None,
    config: PreflightConfig | None = None,
) -> PreflightResult:
    """Convenience function to run pre-flight checks.

    Args:
        dataset_path (Path | None): Path to dataset
        output_path (Path | None): Path for output files
        checkpoint_path (Path | None): Path for checkpoints
        config (PreflightConfig | None): Pre-flight configuration

    Returns:
        PreflightResult: Pre-flight result

    Example:
        >>> result = run_preflight_checks(
        ...     dataset_path=Path("/data/pubtabnet"),
        ...     output_path=Path("/output"),
        ... )
        >>> if not result.passed:
        ...     raise RuntimeError(f"Pre-flight failed: {result.errors}")
    """
    checker = PreflightChecker(config=config)
    return checker.check_all(
        dataset_path=dataset_path,
        output_path=output_path,
        checkpoint_path=checkpoint_path,
    )


__all__ = [
    "CheckCategory",
    "CheckResult",
    "CheckSeverity",
    "PreflightChecker",
    "PreflightConfig",
    "PreflightResult",
    "run_preflight_checks",
]
