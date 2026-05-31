r"""Command-line interface for the annotation system.

This module provides CLI commands for managing the annotation pipeline,
including dataset management, migrations, and validation.

Commands:
    add-dataset: Interactive wizard for adding new datasets
    migrate: Run schema migrations with dry-run support
    validate: Validate dataset configurations
    list-datasets: List all registered datasets

Example:
    # Add a new dataset interactively
    $ python -m image_preprocessing_detector.annotation add-dataset

    # Add dataset with arguments
    $ python -m image_preprocessing_detector.annotation add-dataset \
        --name "my-dataset" --category quality --domain GENERAL

    # Validate all configurations
    $ python -m image_preprocessing_detector.annotation validate

    # Run migrations with dry-run
    $ python -m image_preprocessing_detector.annotation migrate --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from .config import (
    DATASET_CONFIGS,
    AnnotationSettings,
    validate_all_configs,
    validate_dataset_config,
)
from .parsers.template import (
    DatasetInfo,
    ParserCategory,
    generate_config_entry,
    generate_parser,
    generate_test_stub,
    validate_dataset_info,
)
from .schemas.enums import DomainLevel1
from .workflow.preflight import (
    CheckSeverity,
    PreflightChecker,
    PreflightConfig,
    PreflightResult,
)


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Annotation system management commands."""


# =============================================================================
# add-dataset command
# =============================================================================


@cli.command("add-dataset")
@click.option(
    "--name",
    "-n",
    type=str,
    help="Dataset name (e.g., 'my-dataset')",
)
@click.option(
    "--category",
    "-c",
    type=click.Choice([c.value for c in ParserCategory]),
    help="Parser category (quality, layout, handwriting, multilingual, document)",
)
@click.option(
    "--domain",
    "-d",
    type=click.Choice([d.value for d in DomainLevel1]),
    help="Document domain classification",
)
@click.option(
    "--url",
    type=str,
    default="TODO: Add dataset URL",
    help="Dataset source URL",
)
@click.option(
    "--license",
    "license_",
    type=str,
    default="TODO: Check license",
    help="Dataset license (e.g., 'Apache-2.0', 'CC-BY-4.0')",
)
@click.option(
    "--samples",
    type=str,
    default="TODO",
    help="Approximate sample count",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for generated files (default: auto-detect)",
)
@click.option(
    "--interactive/--no-interactive",
    "-i/-I",
    default=True,
    help="Enable/disable interactive prompts",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing files",
)
def add_dataset(
    name: str | None,
    category: str | None,
    domain: str | None,
    url: str,
    license_: str,
    samples: str,
    output_dir: Path | None,
    interactive: bool,
    overwrite: bool,
) -> None:
    r"""Add a new dataset to the annotation system.

    Generates parser boilerplate, config entry, and test stub for a new dataset.

    Args:
        name (str | None): Dataset name (prompted if not provided in interactive mode).
        category (str | None): Parser category (prompted if not provided).
        domain (str | None): Document domain (prompted if not provided).
        url (str): Dataset URL.
        license_ (str): Dataset license identifier.
        samples (str): Approximate sample count.
        output_dir (Path | None): Output directory for generated files.
        interactive (bool): Enable/disable interactive prompts.
        overwrite (bool): Overwrite existing files.

    Raises:
        click.Abort: If user declines to proceed.
        click.BadParameter: If required parameter is missing.
        click.UsageError: If required args missing in non-interactive mode.

    \b
    Examples:
        # Interactive mode (prompts for missing values)
        annotation add-dataset

        # Non-interactive with all options
        annotation add-dataset -n my-dataset -c quality -d GENERAL --no-interactive
    """
    # Interactive prompts for missing values
    if interactive:
        if not name:
            name = click.prompt("Dataset name", type=str)

        if not category:
            category = click.prompt(
                "Parser category",
                type=click.Choice([c.value for c in ParserCategory]),
                default="document",
            )

        if not domain:
            domain = click.prompt(
                "Document domain",
                type=click.Choice([d.value for d in DomainLevel1]),
                default="GENERAL",
            )

        if url.startswith("TODO"):
            url = click.prompt(
                "Dataset URL",
                default=url,
            )

        if license_.startswith("TODO"):
            license_ = click.prompt(
                "License",
                default=license_,
            )

        if samples == "TODO":
            samples = click.prompt(
                "Approximate sample count",
                default=samples,
            )

        # Additional options
        if click.confirm("Add content flags?", default=False):
            has_table = click.confirm("  Has tables?", default=False)
            has_formula = click.confirm("  Has formulas?", default=False)
            has_handwriting = click.confirm("  Has handwriting?", default=False)
            has_signature = click.confirm("  Has signatures?", default=False)
        else:
            has_table = None
            has_formula = None
            has_handwriting = None
            has_signature = None

        label_description = click.prompt(
            "Label format description",
            default="TODO: Describe the annotation format",
        )
    else:
        # Validate required args in non-interactive mode
        if not name:
            raise click.UsageError("--name is required in non-interactive mode")
        if not category:
            raise click.UsageError("--category is required in non-interactive mode")
        if not domain:
            raise click.UsageError("--domain is required in non-interactive mode")

        has_table = None
        has_formula = None
        has_handwriting = None
        has_signature = None
        label_description = "TODO: Describe the annotation format"

    # Validate required fields
    if not name:
        raise click.BadParameter("Dataset name is required", param_hint="--name")
    if not domain:
        raise click.BadParameter("Domain is required", param_hint="--domain")

    # Build DatasetInfo
    info = DatasetInfo(
        dataset_name=name,
        url=url,
        license=license_,
        domain=domain,
        sample_count=samples,
        label_description=label_description,
        category=ParserCategory(category),
        has_table=has_table,
        has_formula=has_formula,
        has_handwriting=has_handwriting,
        has_signature=has_signature,
    )

    # Validate
    warnings = validate_dataset_info(info)
    if warnings:
        click.echo("\nValidation messages:")
        for warning in warnings:
            click.echo(f"  {warning}")

    # Confirm before generating
    if interactive:
        click.echo(f"\nWill generate files for '{name}':")
        click.echo(f"  Parser: parsers/{category}/{info.get_module_name()}.py")
        click.echo("  Config entry code")
        click.echo("  Test stub")

        if not click.confirm("\nProceed?", default=True):
            raise click.Abort()

    # Generate parser
    try:
        parser_path = generate_parser(info, output_dir, overwrite)
        click.echo(f"Created parser: {parser_path}")
    except FileExistsError as e:
        click.echo(f"Error: {e}", err=True)
        if not click.confirm("Continue without parser file?", default=False):
            raise click.Abort() from None

    # Generate config entry
    config_code = generate_config_entry(info)
    click.echo("\n" + "=" * 60)
    click.echo("Add this to config/datasets.py DATASET_CONFIGS:")
    click.echo("=" * 60)
    click.echo(config_code)

    # Generate test stub
    test_code = generate_test_stub(info)
    click.echo("\n" + "=" * 60)
    click.echo(
        f"Create test file: tests/unit/annotation/test_{info.get_module_name()}.py"
    )
    click.echo("=" * 60)
    click.echo(test_code)

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("NEXT STEPS:")
    click.echo("=" * 60)
    click.echo(
        f"1. Implement parse() method in parsers/{category}/{info.get_module_name()}.py"
    )
    click.echo("2. Add DatasetConfig entry to config/datasets.py")
    click.echo("3. Register parser in parsers/registry.py (if not auto-discovered)")
    click.echo("4. Add tests and verify with: pytest tests/unit/annotation/")
    click.echo("5. Update documentation")


# =============================================================================
# validate command
# =============================================================================


@cli.command("validate")
@click.option(
    "--dataset",
    "-d",
    type=str,
    help="Validate specific dataset (default: all)",
)
@click.option(
    "--check-paths/--no-check-paths",
    default=False,
    help="Also check if dataset paths exist",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all messages including INFO",
)
def validate(dataset: str | None, check_paths: bool, _verbose: bool) -> None:
    r"""Validate dataset configurations.

    Args:
        dataset (str | None): Validate specific dataset (default: all).
        check_paths (bool): Also check if dataset paths exist.
        _verbose (bool): Show all messages including INFO.

    \b
    Examples:
        # Validate all datasets
        annotation validate

        # Validate specific dataset
        annotation validate -d diqa-5000

        # Check path existence
        annotation validate --check-paths
    """
    settings = None
    if check_paths:
        try:
            settings = AnnotationSettings.from_env()
        except Exception as e:
            click.echo(f"Warning: Could not load settings: {e}", err=True)
            click.echo("Path checking disabled.", err=True)
            check_paths = False

    if dataset:
        # Validate single dataset
        if dataset not in DATASET_CONFIGS:
            click.echo(f"Error: Unknown dataset '{dataset}'", err=True)
            click.echo(
                f"Available: {', '.join(sorted(DATASET_CONFIGS.keys()))}", err=True
            )
            sys.exit(1)

        config = DATASET_CONFIGS[dataset]
        result = validate_dataset_config(config, settings, check_paths)

        click.echo(result.format())

        if not result.is_valid:
            sys.exit(1)
    else:
        # Validate all datasets
        report = validate_all_configs(DATASET_CONFIGS, settings, check_paths)
        click.echo(report.summary())

        if report.invalid_count > 0:
            sys.exit(1)


# =============================================================================
# list-datasets command
# =============================================================================


@cli.command("list-datasets")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["all", "benchmark", "training"]),
    default="all",
    help="Filter by category",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "names"]),
    default="table",
    help="Output format",
)
def list_datasets(category: str, output_format: str) -> None:
    r"""List all registered datasets.

    Args:
        category (str): Filter by category ("all", "benchmark", or "training").
        output_format (str): Output format ("table", "json", or "names").

    \b
    Examples:
        # List all datasets
        annotation list-datasets

        # List only benchmark datasets
        annotation list-datasets -c benchmark

        # Output as JSON
        annotation list-datasets -f json
    """
    from .config import is_benchmark_dataset

    datasets = []
    for name, config in sorted(DATASET_CONFIGS.items()):
        is_benchmark = is_benchmark_dataset(config)

        if category == "benchmark" and not is_benchmark:
            continue
        if category == "training" and is_benchmark:
            continue

        datasets.append(
            {
                "name": name,
                "domain": config.domain.value,
                "capture": config.capture_method.value,
                "benchmark": is_benchmark,
                "parser": config.parser_name or "none",
            }
        )

    if output_format == "names":
        for ds in datasets:
            click.echo(ds["name"])
    elif output_format == "json":
        import json

        click.echo(json.dumps(datasets, indent=2))
    else:
        # Table format
        click.echo(
            f"{'Name':<25} {'Domain':<15} {'Capture':<15} {'Type':<10} {'Parser':<20}"
        )
        click.echo("-" * 85)
        for ds in datasets:
            type_str = "benchmark" if ds["benchmark"] else "training"
            click.echo(
                f"{ds['name']:<25} {ds['domain']:<15} {ds['capture']:<15} "
                f"{type_str:<10} {ds['parser']:<20}"
            )
        click.echo("-" * 85)
        click.echo(f"Total: {len(datasets)} datasets")


# =============================================================================
# migrate command
# =============================================================================


def _collect_migration_files(path: Path, recursive: bool) -> list[Path]:
    """Collect JSON files to migrate from path."""
    if path.is_file():
        return [path]
    if recursive:
        return list(path.glob("**/*.json"))
    return list(path.glob("*.json"))


def _report_migration_result(
    result: Any,
    target_version: str,
    dry_run: bool,
    is_rollback: bool,
) -> tuple[int, int, int]:
    """Report a single migration result. Returns (migrated, skipped, errors) delta."""
    if not result.success:
        click.echo(f"ERROR {result.file_path}: {result.error}", err=True)
        return (0, 0, 1)

    # Success - check if actually migrated or skipped
    if not result.migrations_applied and not is_rollback:
        click.echo(f"SKIP {result.file_path} (already at {target_version})")
        return (0, 1, 0)

    # Report migration details
    status = "DRY RUN" if result.dry_run else "MIGRATE"
    click.echo(
        f"{status} {result.file_path}: {result.from_version} -> {result.to_version}"
    )
    if result.backup_path and not dry_run:
        click.echo(f"  Backup: {result.backup_path}")
    if result.migrations_applied:
        click.echo(f"  Steps: {' -> '.join(result.migrations_applied)}")
    return (1, 0, 0)


@cli.command("migrate")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--target-version", "-t", type=str, default=None, help="Target schema version"
)
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
@click.option(
    "--backup/--no-backup", default=True, help="Create backup before migration"
)
@click.option("--recursive", "-r", is_flag=True, help="Process directory recursively")
@click.option("--rollback", type=str, default=None, help="Rollback to specific version")
def migrate(
    path: Path,
    target_version: str | None,
    dry_run: bool,
    backup: bool,
    recursive: bool,
    rollback: str | None,
) -> None:
    r"""Run schema migrations on metadata files.

    Uses FileMigrator for safe, atomic migrations with backup support.

    Args:
        path (Path): Path to file or directory to migrate.
        target_version (str | None): Target schema version (default: latest).
        dry_run (bool): Preview changes without modifying files.
        backup (bool): Create backup before migration.
        recursive (bool): Process directory recursively.
        rollback (str | None): Rollback to specific version.

    \b
    Examples:
        annotation migrate metadata.json
        annotation migrate ./metadata/ -r --dry-run
        annotation migrate metadata.json --rollback 2.0
    """
    from .schemas.migrations import CURRENT_VERSION, FileMigrator

    target_version = target_version or CURRENT_VERSION
    migrator = FileMigrator(fsync=False)
    files = _collect_migration_files(path, recursive)

    if not files:
        click.echo("No JSON files found to migrate.")
        return

    # Print header
    click.echo(f"Found {len(files)} files to process")
    click.echo(
        f"{'Rollback to' if rollback else 'Target'} version: {rollback or target_version}"
    )
    if dry_run:
        click.echo("DRY RUN - no changes will be made")
    click.echo()

    # Process files
    migrated, skipped, errors = 0, 0, 0
    for file_path in files:
        if rollback:
            result = migrator.rollback_file(file_path, rollback)
        else:
            result = migrator.migrate_file(
                file_path, target_version, dry_run, skip_backup=not backup
            )
        m, s, e = _report_migration_result(
            result, target_version, dry_run, bool(rollback)
        )
        migrated += m
        skipped += s
        errors += e

    # Summary
    click.echo(
        f"\n{'=' * 40}\nMigrated: {migrated}\nSkipped:  {skipped}\nErrors:   {errors}"
    )
    if errors > 0:
        sys.exit(1)


# =============================================================================
# preflight command
# =============================================================================


def _format_preflight_failures(failures: list[Any], verbose: bool) -> list[str]:
    """Format failure checks for output."""
    lines: list[str] = []
    for check in failures:
        severity_icon = "⚠" if check.severity == CheckSeverity.WARNING else "✗"
        lines.append(f"{severity_icon} [{check.category.value}] {check.name}")
        lines.append(f"    {check.message}")
        if verbose and check.details:
            for key, value in check.details.items():
                lines.append(f"      {key}: {value}")
    return lines


def _format_preflight_result(result: PreflightResult, verbose: bool) -> str:
    """Format pre-flight result for CLI output."""
    lines: list[str] = []
    total_checks = len(result.checks)

    # Header and summary
    status = "✓ PASSED" if result.passed else "✗ FAILED"
    lines.append(f"\nPre-flight Validation: {status}")
    lines.append("=" * 50)
    lines.append(f"Total checks: {total_checks}")
    lines.append(f"  Passed:   {total_checks - len(result.failures)}")
    lines.append(f"  Warnings: {len(result.warnings)}")
    lines.append(f"  Errors:   {len(result.errors)}")

    # Show failures (always)
    if result.failures:
        lines.append("\n--- Failures ---")
        lines.extend(_format_preflight_failures(result.failures, verbose))

    # Show all checks in verbose mode
    if verbose and result.checks:
        lines.append("\n--- All Checks ---")
        for check in result.checks:
            icon = "✓" if check.passed else "✗"
            lines.append(
                f"{icon} [{check.category.value}] {check.name}: {check.message}"
            )

    lines.append("")
    return "\n".join(lines)


def _load_preflight_settings(
    dataset: Path | None,
    output: Path | None,
    checkpoint: Path | None,
) -> tuple[AnnotationSettings | None, Path | None, Path | None, Path | None]:
    """Load settings from environment and resolve paths."""
    try:
        settings = AnnotationSettings.from_env()
        resolved_dataset = dataset or settings.e_drive_root
        resolved_output = output or settings.metadata_root
        resolved_checkpoint = checkpoint or settings.checkpoint_dir
    except Exception as e:
        click.echo(f"Warning: Could not load settings: {e}", err=True)
        return None, dataset, output, checkpoint
    else:
        return settings, resolved_dataset, resolved_output, resolved_checkpoint


def _collect_model_paths(
    settings: AnnotationSettings | None, check_models: bool
) -> list[Path]:
    """Collect model paths from settings for validation."""
    model_paths: list[Path] = []
    if check_models and settings:
        if settings.yolo_model_path:
            model_paths.append(settings.yolo_model_path)
        if settings.siglip_model_path:
            model_paths.append(settings.siglip_model_path)
    return model_paths


def _add_settings_validation(
    result: PreflightResult, settings: AnnotationSettings
) -> None:
    """Add settings validation issues to preflight result."""
    from .workflow.preflight import CheckCategory, CheckResult

    for issue in settings.validate():
        result.add_check(
            CheckResult(
                name="settings_validation",
                passed=False,
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.WARNING,
                message=issue,
            )
        )


@cli.command("preflight")
@click.option(
    "--dataset",
    "-d",
    type=click.Path(exists=True, path_type=Path),
    help="Dataset path to validate",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for results",
)
@click.option(
    "--checkpoint",
    type=click.Path(path_type=Path),
    help="Checkpoint directory",
)
@click.option(
    "--min-disk-gb",
    type=float,
    default=10.0,
    help="Minimum required disk space in GB (default: 10)",
)
@click.option(
    "--check-models/--no-check-models",
    default=True,
    help="Check model file existence (default: yes)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed check results")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.option(
    "--from-settings",
    is_flag=True,
    help="Load paths from AnnotationSettings (env vars / config)",
)
@click.option(
    "--check-providers",
    multiple=True,
    type=str,
    help="Check provider availability (e.g., --check-providers yolo --check-providers siglip)",
)
def preflight(
    dataset: Path | None,
    output: Path | None,
    checkpoint: Path | None,
    min_disk_gb: float,
    check_models: bool,
    verbose: bool,
    output_json: bool,
    from_settings: bool,
    check_providers: tuple[str, ...],
) -> None:
    r"""Run pre-flight validation checks before annotation workflow.

    Validates disk space, path accessibility, model files, and system
    readiness before starting long-running annotation operations.

    Args:
        dataset (Path | None): Dataset path to validate.
        output (Path | None): Output directory for results.
        checkpoint (Path | None): Checkpoint directory.
        min_disk_gb (float): Minimum required disk space in GB.
        check_models (bool): Check model file existence.
        verbose (bool): Show detailed check results.
        output_json (bool): Output results as JSON.
        from_settings (bool): Load paths from AnnotationSettings.
        check_providers (tuple[str, ...]): Provider names to check availability for.

    \b
    Examples:
        # Basic validation with explicit paths
        annotation preflight -d /path/to/dataset -o /path/to/output

        # Use paths from environment/settings
        annotation preflight --from-settings

        # Verbose output with model checks
        annotation preflight -d ./dataset -o ./output -v --check-models

        # JSON output for CI integration
        annotation preflight --from-settings --json
    """
    import json as json_module

    # Load settings if requested
    settings = None
    if from_settings:
        settings, dataset, output, checkpoint = _load_preflight_settings(
            dataset, output, checkpoint
        )
        if not dataset and not settings:
            click.echo("Error: --dataset required when settings unavailable", err=True)
            sys.exit(1)

    # Build model paths and configure checker
    model_paths = _collect_model_paths(settings, check_models)
    provider_names = list(check_providers) if check_providers else []
    required_paths: list[Path] = [dataset] if dataset else []
    config = PreflightConfig(
        min_disk_space_gb=min_disk_gb,
        model_paths=model_paths,
        required_read_paths=required_paths,
        check_provider_connectivity=bool(provider_names),
        provider_names=provider_names,
    )

    # Run checks
    checker = PreflightChecker(config=config)
    result = checker.check_all(
        dataset_path=dataset,
        output_path=output,
        checkpoint_path=checkpoint,
    )

    # Add settings validation if loaded
    if settings:
        _add_settings_validation(result, settings)

    # Output results
    if output_json:
        click.echo(json_module.dumps(result.to_dict(), indent=2, default=str))
    else:
        click.echo(_format_preflight_result(result, verbose))

    if not result.passed:
        sys.exit(1)


# =============================================================================
# Main entry point
# =============================================================================


def main() -> None:
    """Main entry point for annotation CLI."""
    cli()


if __name__ == "__main__":
    main()
