"""Auto-discover datasets from the metadata registry filesystem.

Instead of relying solely on hardcoded ``_KNOWN_CONFIGS`` in
``audit_config.py``, this module can discover datasets by scanning for
``*_metadata.json`` files in the metadata registry directory.

Known configs always take precedence.  Discovered datasets get sensible
defaults so they can participate in prescreening and scorecard computation
without manual configuration.

Usage::

    from scripts.audit.auto_discover import (
        discover_metadata_files,
        build_discovered_config,
        merge_known_and_discovered,
        list_all_datasets,
    )

    # List everything (known + discovered)
    for name in list_all_datasets():
        print(name)

    # Get a config for any dataset (known or discovered)
    cfg = get_dataset_config("my-new-dataset")
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from scripts.audit.audit_config import (
    DEFAULT_IMAGE_ROOT,
    DEFAULT_METADATA_ROOT,
    DatasetAuditConfig,
    _KNOWN_CONFIGS,
    list_known_datasets,
    load_dataset_config,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------
_METADATA_SUFFIX_RE = re.compile(r"_metadata\.json$")


def normalize_dataset_name(filename: str) -> str:
    """Derive canonical dataset name from a metadata filename.

    Strips the ``_metadata.json`` suffix and converts underscores to
    hyphens to match the canonical naming convention.

    Args:
        filename: Metadata filename (e.g. ``diqa_5000_metadata.json``).

    Returns:
        Canonical dataset name (e.g. ``diqa-5000``).

    Examples:
        >>> normalize_dataset_name("diqa_5000_metadata.json")
        'diqa-5000'
        >>> normalize_dataset_name("ohr-bench_metadata.json")
        'ohr-bench'
        >>> normalize_dataset_name("hindi_ocr_synthetic_metadata.json")
        'hindi-ocr-synthetic'
    """
    stem = _METADATA_SUFFIX_RE.sub("", filename)
    return stem.replace("_", "-")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def discover_metadata_files(
    metadata_root: Path | None = None,
) -> dict[str, Path]:
    """Discover metadata files from the filesystem.

    Scans for ``*_metadata.json`` files and returns a mapping of
    normalized dataset names to their metadata file paths.

    Args:
        metadata_root: Directory to scan. Defaults to
            ``DEFAULT_METADATA_ROOT``.

    Returns:
        Dict mapping canonical dataset name to metadata file path.
    """
    root = metadata_root or DEFAULT_METADATA_ROOT
    if not root.is_dir():
        log.warning("Metadata root does not exist: %s", root)
        return {}

    discovered: dict[str, Path] = {}
    for path in sorted(root.glob("*_metadata.json")):
        name = normalize_dataset_name(path.name)
        if name in discovered:
            log.warning(
                "Duplicate dataset name '%s' from %s (already seen %s)",
                name,
                path,
                discovered[name],
            )
            continue
        discovered[name] = path

    log.info("Discovered %d metadata files in %s", len(discovered), root)
    return discovered


def build_discovered_config(
    name: str,
    metadata_path: Path,
    *,
    image_root: Path | None = None,
) -> DatasetAuditConfig:
    """Build a ``DatasetAuditConfig`` with sensible defaults.

    Used for datasets not in ``_KNOWN_CONFIGS``.  Assumes standard
    directory layout and default stratification axes.

    Args:
        name: Canonical dataset name.
        metadata_path: Path to the ``*_metadata.json`` file.
        image_root: Root directory for dataset images.  Defaults to
            ``DEFAULT_IMAGE_ROOT / name``.

    Returns:
        A ``DatasetAuditConfig`` with discovered paths.
    """
    img_root = image_root or (DEFAULT_IMAGE_ROOT / name)
    metadata_dir = metadata_path.parent

    # Probe for optional enrichment files using common naming patterns
    base_stem = metadata_path.stem.replace("_metadata", "")
    llm_path = metadata_dir / f"{base_stem}_llm_enrichment.json"
    lang_path = metadata_dir / f"{base_stem}_language_enrichment.json"

    return DatasetAuditConfig(
        dataset_name=name,
        image_base_path=img_root,
        metadata_json_path=metadata_path,
        llm_enrichment_path=llm_path if llm_path.exists() else None,
        language_enrichment_path=lang_path if lang_path.exists() else None,
    )


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def merge_known_and_discovered(
    metadata_root: Path | None = None,
    image_root: Path | None = None,
) -> dict[str, DatasetAuditConfig]:
    """Merge known configs with auto-discovered datasets.

    Known configs always take precedence.  Discovered datasets that are
    not in ``_KNOWN_CONFIGS`` get configs built with sensible defaults.

    Args:
        metadata_root: Override metadata directory for discovery.
        image_root: Override image root for discovered datasets.

    Returns:
        Dict mapping dataset name to ``DatasetAuditConfig``.
    """
    result: dict[str, DatasetAuditConfig] = {}

    # Load all known configs
    for name in list_known_datasets():
        result[name] = load_dataset_config(name)

    # Discover additional datasets
    discovered = discover_metadata_files(metadata_root)
    new_count = 0
    for name, metadata_path in discovered.items():
        if name in result:
            continue  # Known config takes precedence
        result[name] = build_discovered_config(
            name, metadata_path, image_root=image_root
        )
        new_count += 1

    if new_count:
        log.info(
            "Added %d auto-discovered datasets (total: %d)",
            new_count,
            len(result),
        )

    return result


def list_all_datasets(
    metadata_root: Path | None = None,
) -> list[str]:
    """Return sorted list of all datasets (known + discovered).

    Args:
        metadata_root: Override metadata directory for discovery.

    Returns:
        Sorted list of canonical dataset names.
    """
    known = set(list_known_datasets())
    discovered = set(discover_metadata_files(metadata_root).keys())
    return sorted(known | discovered)


def get_dataset_config(
    dataset_name: str,
    *,
    metadata_root: Path | None = None,
    image_root: Path | None = None,
    sample_size: int | None = None,
) -> DatasetAuditConfig:
    """Get a config for any dataset, falling back to auto-discovery.

    Checks ``_KNOWN_CONFIGS`` first.  If not found, attempts to discover
    the dataset from the metadata registry filesystem.

    Args:
        dataset_name: Canonical dataset name.
        metadata_root: Override metadata directory for discovery.
        image_root: Override image root for discovered datasets.
        sample_size: Override sample size.

    Returns:
        A ``DatasetAuditConfig``.

    Raises:
        ValueError: If the dataset cannot be found in known configs or
            discovered from the filesystem.
    """
    # Try known configs first
    if dataset_name in _KNOWN_CONFIGS:
        return load_dataset_config(dataset_name, sample_size=sample_size)

    # Try auto-discovery
    discovered = discover_metadata_files(metadata_root)
    if dataset_name in discovered:
        cfg = build_discovered_config(
            dataset_name,
            discovered[dataset_name],
            image_root=image_root,
        )
        if sample_size is not None:
            cfg.sample_size = sample_size
        return cfg

    known = ", ".join(sorted(set(list_known_datasets()) | set(discovered)))
    msg = (
        f"Unknown dataset '{dataset_name}'. "
        f"Not found in known configs or metadata registry. "
        f"Available: {known}"
    )
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point for auto-discovery."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-discover datasets from metadata registry."
    )
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=None,
        help="Metadata registry directory.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    known = set(list_known_datasets())
    discovered = discover_metadata_files(args.metadata_root)

    known_only = known - set(discovered)
    discovered_only = set(discovered) - known
    both = known & set(discovered)

    print(f"\nKnown configs:           {len(known)}")
    print(f"Discovered metadata:     {len(discovered)}")
    print(f"In both:                 {len(both)}")
    print(f"Known only (no file):    {len(known_only)}")
    print(f"Discovered only (new):   {len(discovered_only)}")

    if discovered_only:
        print("\nNew datasets (not in _KNOWN_CONFIGS):")
        for name in sorted(discovered_only):
            print(f"  {name}: {discovered[name]}")

    if known_only:
        print("\nKnown configs without metadata file:")
        for name in sorted(known_only):
            print(f"  {name}")


if __name__ == "__main__":
    main()
