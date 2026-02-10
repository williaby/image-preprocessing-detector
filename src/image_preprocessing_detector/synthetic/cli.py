# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""CLI interface for synthetic multi-script document generation.

Provides commands for generating synthetic training datasets for SigLIP
script identification training.

Commands:
    imgprep synthetic generate - Generate synthetic dataset
    imgprep synthetic status - Check corpus and font availability
    imgprep synthetic preview - Generate preview samples

Example:
    # Generate 1000 samples per script for 10 MVP scripts
    imgprep synthetic generate --samples-per-script 1000

    # Generate for specific scripts only
    imgprep synthetic generate --scripts Arab,Latn,Deva --samples 500

    # Check system readiness
    imgprep synthetic status
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click

from image_preprocessing_detector.synthetic.augmentation import (
    AUGRAPHY_AVAILABLE,
    DegradationProfile,
)
from image_preprocessing_detector.synthetic.config import (
    MVP_SCRIPTS,
    SCRIPT_CONFIGS,
)
from image_preprocessing_detector.synthetic.corpus import TextCorpusManager
from image_preprocessing_detector.synthetic.fonts import FontManager
from image_preprocessing_detector.synthetic.generator import (
    GenerationConfig,
    MultiScriptDocumentGenerator,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default output path on E drive
DEFAULT_OUTPUT_PATH = Path(
    "/mnt/e/image_detection/03_training_datasets/synthetic_multiscript"
)

# Alternative paths for different environments
FALLBACK_OUTPUT_PATHS = [
    Path.home() / "datasets" / "synthetic_multiscript",
    Path.cwd() / "synthetic_output",
]


def _get_output_path(custom_path: Path | None = None) -> Path:
    """Determine the output path, checking availability.

    Args:
        custom_path: User-specified path (takes priority)

    Returns:
        Available output path
    """
    if custom_path:
        return custom_path

    # Try default E drive path
    if DEFAULT_OUTPUT_PATH.parent.exists():
        return DEFAULT_OUTPUT_PATH

    # Try fallback paths
    for path in FALLBACK_OUTPUT_PATHS:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue

    # Last resort: current directory
    return Path.cwd() / "synthetic_output"


@click.group()
def synthetic() -> None:
    """Synthetic multi-script document generation commands."""


@synthetic.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Output directory (default: {DEFAULT_OUTPUT_PATH})",
)
@click.option(
    "--scripts",
    "-s",
    type=str,
    default=None,
    help="Comma-separated script codes (default: MVP scripts)",
)
@click.option(
    "--samples-per-script",
    "-n",
    type=int,
    default=100,
    help="Samples per script (default: 100)",
)
@click.option(
    "--pristine-ratio",
    type=float,
    default=0.2,
    help="Ratio of pristine (undegraded) samples (default: 0.2)",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for reproducibility",
)
@click.option(
    "--format",
    "image_format",
    type=click.Choice(["png", "jpg"]),
    default="png",
    help="Output image format (default: png)",
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Skip corpus download (use cache only)",
)
@click.option(
    "--no-metadata",
    is_flag=True,
    help="Skip metadata JSON generation",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be generated without creating files",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt for large datasets",
)
@click.option(
    "--profile",
    type=click.Choice(["fast", "mild", "moderate", "severe", "all"]),
    default="fast",
    help="Degradation profile for augmented samples (default: fast - uses only fast augmenters)",
)
@click.option(
    "--dpi",
    type=click.Choice(["150", "300"]),
    default="300",
    help="Output resolution in DPI (150 = faster augmentation, 300 = full quality)",
)
@click.option(
    "--augmenter",
    type=click.Choice(["augraphy", "albumentations", "hybrid"]),
    default="albumentations",
    help="Augmentation library (albumentations ~600x faster, hybrid = augraphy + albumentations)",
)
@click.option(
    "--color-mode",
    is_flag=True,
    help="Enable random color mode conversion (60%% color, 25%% grayscale, 15%% binarized)",
)
@click.option(
    "--skew",
    is_flag=True,
    help="Enable random skew augmentation (+/-10 degrees with exact angle labels)",
)
@click.option(
    "--orientation",
    is_flag=True,
    help="Enable random orientation augmentation (0/90/180/270 with class labels)",
)
def generate(
    output: Path | None,
    scripts: str | None,
    samples_per_script: int,
    pristine_ratio: float,
    seed: int | None,
    image_format: str,
    skip_download: bool,
    no_metadata: bool,
    dry_run: bool,
    yes: bool,
    profile: str,
    dpi: str,
    augmenter: str,
    color_mode: bool,
    skew: bool,
    orientation: bool,
) -> None:
    """Generate synthetic multi-script document dataset.

    Creates synthetic document images with ground truth labels for
    training SigLIP on script identification.

    Examples:
        # Generate 100 samples per MVP script (10 scripts = 1000 total)
        imgprep synthetic generate

        # Generate 500 samples for specific scripts
        imgprep synthetic generate -s Arab,Latn,Deva -n 500

        # Generate to custom location with reproducible seed
        imgprep synthetic generate -o ./my_dataset --seed 42

        # Preview what would be generated
        imgprep synthetic generate --dry-run
    """
    # Parse scripts
    if scripts:
        script_list = [s.strip() for s in scripts.split(",")]
        # Validate
        invalid = [s for s in script_list if s not in SCRIPT_CONFIGS]
        if invalid:
            click.echo(f"Error: Unknown script codes: {', '.join(invalid)}", err=True)
            click.echo(
                f"Valid codes: {', '.join(sorted(SCRIPT_CONFIGS.keys()))}", err=True
            )
            sys.exit(1)
    else:
        script_list = list(MVP_SCRIPTS)

    # Determine output path
    output_path = _get_output_path(output)

    # Calculate totals
    total_samples = len(script_list) * samples_per_script
    pristine_count = int(total_samples * pristine_ratio)
    degraded_count = total_samples - pristine_count

    click.echo("=" * 60)
    click.echo("Multi-Script Synthetic Document Generator")
    click.echo("=" * 60)
    click.echo(
        f"Scripts:         {len(script_list)} ({', '.join(script_list[:5])}{'...' if len(script_list) > 5 else ''})"
    )
    click.echo(f"Samples/script:  {samples_per_script}")
    click.echo(f"Total samples:   {total_samples}")
    click.echo(f"  - Pristine:    {pristine_count} ({pristine_ratio:.0%})")
    click.echo(f"  - Degraded:    {degraded_count} ({1 - pristine_ratio:.0%})")
    click.echo(f"Output path:     {output_path}")
    click.echo(f"Image format:    {image_format}")
    click.echo(f"Resolution:      {dpi} DPI")
    click.echo(f"Augmenter:       {augmenter}")
    click.echo(f"Degradation:     {profile} profile")
    if color_mode or skew or orientation:
        multi_task = []
        if color_mode:
            multi_task.append("color-mode")
        if skew:
            multi_task.append("skew")
        if orientation:
            multi_task.append("orientation")
        click.echo(f"Multi-task:      {', '.join(multi_task)}")
    click.echo("=" * 60)

    if dry_run:
        click.echo("\n[DRY RUN] No files will be created.")
        click.echo("\nWould generate:")
        for script in script_list:
            config = SCRIPT_CONFIGS[script]
            click.echo(f"  {script} ({config.name}): {samples_per_script} samples")
        return

    # Confirm before generating large datasets (skip if --yes flag)
    if (
        total_samples > 500
        and not yes
        and not click.confirm(f"\nGenerate {total_samples} samples?")
    ):
        click.echo("Aborted.")
        return

    # Map profile string to DegradationProfile enum(s)
    profile_map = {
        "fast": [DegradationProfile.FAST],
        "mild": [DegradationProfile.MILD],
        "moderate": [DegradationProfile.MODERATE],
        "severe": [DegradationProfile.SEVERE],
        "all": list(DegradationProfile),  # All profiles
    }
    degradation_profiles = profile_map.get(profile, [DegradationProfile.FAST])

    # Create config
    config = GenerationConfig(
        scripts=script_list,
        samples_per_script=samples_per_script,
        output_dir=output_path,
        save_images=True,
        save_metadata=not no_metadata,
        image_format=image_format,
        seed=seed,
        pristine_ratio=pristine_ratio,
        degradation_profiles=degradation_profiles,
        dpi=int(dpi),
        augmenter=augmenter,
        color_mode_enabled=color_mode,
        skew_augmentation=skew,
        orientation_augmentation=orientation,
    )

    # Create generator
    generator = MultiScriptDocumentGenerator(config)

    # Initialize
    click.echo("\nInitializing...")
    try:
        success = generator.initialize(download_corpus=not skip_download)
        if not success:
            click.echo("Error: Failed to initialize generator", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error during initialization: {e}", err=True)
        sys.exit(1)

    # Check available scripts
    available = generator.get_available_scripts()
    if not available:
        click.echo("Error: No scripts available (missing fonts or corpus)", err=True)
        click.echo("Run 'imgprep synthetic status' for details", err=True)
        sys.exit(1)

    missing = set(script_list) - set(available)
    if missing:
        click.echo(f"Warning: Missing fonts/corpus for: {', '.join(missing)}", err=True)
        script_list = [s for s in script_list if s in available]
        if not script_list:
            click.echo("Error: No scripts available to generate", err=True)
            sys.exit(1)
        config.scripts = script_list

    # Generate
    click.echo(f"\nGenerating {len(script_list) * samples_per_script} samples...")

    generated = 0
    with click.progressbar(
        generator.generate(),
        length=len(script_list) * samples_per_script,
        label="Generating",
        show_pos=True,
    ) as progress:
        for _sample in progress:
            generated += 1

    # Get stats
    stats = generator.get_statistics()

    click.echo("\n" + "=" * 60)
    click.echo("Generation Complete!")
    click.echo("=" * 60)
    click.echo(f"Total samples:   {stats.total_samples}")
    click.echo(f"Failed:          {stats.failed_samples}")
    click.echo(f"Output:          {output_path}")

    if stats.samples_per_script:
        click.echo("\nSamples per script:")
        for script, count in sorted(stats.samples_per_script.items()):
            click.echo(f"  {script}: {count}")

    # Write manifest
    manifest_path = output_path / "manifest.json"
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "generator_version": "1.0.0",
        "total_samples": stats.total_samples,
        "scripts": script_list,
        "samples_per_script": samples_per_script,
        "pristine_ratio": pristine_ratio,
        "seed": seed,
        "image_format": image_format,
        "stats": {
            "per_script": stats.samples_per_script,
            "per_layout": stats.samples_per_layout,
            "per_profile": stats.samples_per_profile,
            "failed": stats.failed_samples,
        },
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    click.echo(f"\nManifest:        {manifest_path}")


@synthetic.command()
def status() -> None:
    """Check synthetic generation readiness.

    Shows status of:
    - System dependencies (libraqm, Noto fonts)
    - Corpus cache status
    - Available scripts
    """
    click.echo("=" * 60)
    click.echo("Synthetic Generator Status")
    click.echo("=" * 60)

    # Check Augraphy
    click.echo(
        f"\nAugraphy:        {'✓ Available' if AUGRAPHY_AVAILABLE else '✗ NOT AVAILABLE'}"
    )
    if not AUGRAPHY_AVAILABLE:
        click.echo("  Install with: uv sync --extra synthetic")

    # Check fonts
    click.echo("\nScanning fonts...")
    font_manager = FontManager()
    font_count = font_manager.scan_fonts()
    click.echo(f"Fonts found:     {font_count}")

    # Check which scripts have fonts
    scripts_with_fonts = []
    scripts_without_fonts = []
    for script_code in SCRIPT_CONFIGS:
        if font_manager.has_font_for_script(script_code):
            scripts_with_fonts.append(script_code)
        else:
            scripts_without_fonts.append(script_code)

    click.echo(f"Scripts w/fonts: {len(scripts_with_fonts)}/{len(SCRIPT_CONFIGS)}")

    if scripts_without_fonts:
        click.echo(f"Missing fonts:   {', '.join(scripts_without_fonts[:10])}")
        if len(scripts_without_fonts) > 10:
            click.echo(
                f"                 ... and {len(scripts_without_fonts) - 10} more"
            )

    # Check corpus cache
    click.echo("\nChecking corpus cache...")
    corpus_manager = TextCorpusManager()
    loaded = corpus_manager.load_from_cache()

    if loaded > 0:
        available = corpus_manager.get_available_scripts()
        click.echo(f"Cached corpus:   {loaded} samples across {len(available)} scripts")
        click.echo(f"Scripts:         {', '.join(available[:10])}")
    else:
        click.echo("Cached corpus:   None (will download on first generate)")

    # Check default output path
    click.echo(f"\nDefault output:  {DEFAULT_OUTPUT_PATH}")
    if DEFAULT_OUTPUT_PATH.parent.exists():
        click.echo("                 ✓ Path available")
    else:
        click.echo("                 ✗ E drive not mounted, will use fallback")

    # Summary
    click.echo("\n" + "=" * 60)
    if font_count > 0 and (True):  # Can generate pristine without augraphy
        click.echo("Status: Ready to generate")
        if not AUGRAPHY_AVAILABLE:
            click.echo("        (Pristine only - install augraphy for degradation)")
    else:
        click.echo("Status: NOT READY")
        if font_count == 0:
            click.echo(
                "        Install Noto fonts: sudo apt-get install fonts-noto fonts-noto-cjk"
            )


@synthetic.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd() / "synthetic_preview",
    help="Output directory for preview samples",
)
@click.option(
    "--scripts",
    "-s",
    type=str,
    default="Latn,Arab,Hans,Deva,Tibt",
    help="Comma-separated script codes to preview",
)
@click.option(
    "--count",
    "-n",
    type=int,
    default=2,
    help="Samples per script (default: 2)",
)
@click.option(
    "--skip-download",
    is_flag=True,
    default=True,
    help="Skip corpus download (use sample texts, default: True)",
)
def preview(output: Path, scripts: str, count: int, skip_download: bool) -> None:
    """Generate preview samples for visual inspection.

    Creates a small number of samples to verify rendering quality
    before full dataset generation.

    Example:
        imgprep synthetic preview
        imgprep synthetic preview -s Arab,Tibt,Thai -n 3
    """
    script_list = [s.strip() for s in scripts.split(",")]

    # Validate scripts
    invalid = [s for s in script_list if s not in SCRIPT_CONFIGS]
    if invalid:
        click.echo(f"Error: Unknown scripts: {', '.join(invalid)}", err=True)
        sys.exit(1)

    click.echo(f"Generating preview samples for: {', '.join(script_list)}")
    click.echo(f"Output: {output}")

    # Create generator with small config
    config = GenerationConfig(
        scripts=script_list,
        samples_per_script=count,
        output_dir=output,
        save_images=True,
        save_metadata=True,
        pristine_ratio=0.5,  # Half pristine, half degraded
    )

    generator = MultiScriptDocumentGenerator(config)

    click.echo("\nInitializing...")
    if not generator.initialize(download_corpus=not skip_download):
        click.echo("Error: Failed to initialize", err=True)
        sys.exit(1)

    click.echo("Generating preview samples...")
    generated = 0
    for sample in generator.generate():
        script = next(iter(sample.scripts))
        status = "pristine" if sample.is_pristine else "degraded"
        click.echo(f"  {script}: {sample.sample_id[:8]}... ({status})")
        generated += 1

    click.echo(f"\n✓ Generated {generated} preview samples")
    click.echo(f"  View at: {output}")


# Export for main CLI integration
__all__ = ["synthetic"]
