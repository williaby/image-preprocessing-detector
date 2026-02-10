# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""CLI commands for layout taxonomy tools.

Provides commands for inspecting and comparing layout label schemas
used across document analysis datasets and detection models.

Commands:
    imgprep layout list    - Show all available schemas and class counts
    imgprep layout compare - Compare label mappings between two schemas

Example:
    imgprep layout list
    imgprep layout compare docstructbench doclaynet
    imgprep layout compare docling d4la --format json
"""

from __future__ import annotations

import csv
import io
import json
import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from image_preprocessing_detector.schema_utils.layout_taxonomy import (
        LayoutTaxonomy,
    )


def _get_taxonomy() -> LayoutTaxonomy:
    """Import and return the LayoutTaxonomy singleton.

    Returns:
        LayoutTaxonomy instance from get_default_taxonomy()

    Raises:
        SystemExit: If the layout taxonomy module is not available
    """
    try:
        from image_preprocessing_detector.schema_utils.layout_taxonomy import (
            get_default_taxonomy,
        )

        return get_default_taxonomy()
    except ImportError:
        click.echo(
            "Error: Layout taxonomy module not available. "
            "Ensure schema_utils/layout_taxonomy.py is installed.",
            err=True,
        )
        sys.exit(1)


@click.group()
def layout() -> None:
    """Layout taxonomy tools for schema comparison and management."""


@layout.command("list")
def list_schemas() -> None:
    """Show all available layout schemas and their class counts.

    Displays each schema name, number of classes, and a preview
    of class labels. Also shows the canonical superset size.

    Examples:
        imgprep layout list
    """
    taxonomy = _get_taxonomy()

    schema_names = taxonomy.get_available_schemas()
    if not schema_names:
        click.echo("No layout schemas configured.", err=True)
        sys.exit(1)

    click.echo(f"\nAvailable Layout Schemas ({len(schema_names)}):")

    for schema_name in schema_names:
        classes = taxonomy.get_schema_classes(schema_name)
        class_count = len(classes)
        preview = ", ".join(classes[:3])
        if len(classes) > 3:
            preview += ", ..."
        click.echo(f"  {schema_name:<15}: {class_count:>2} classes  ({preview})")

    canonical_classes = taxonomy.get_canonical_classes()
    canonical_count = len(canonical_classes)
    # DocLayNet top-level classes have doclaynet_index set
    top_level = sum(
        1
        for cls in canonical_classes
        if taxonomy.to_doclaynet_index(cls) is not None
        and taxonomy.to_doclaynet(cls) != "UNKNOWN"
    )

    # More accurate: top-level are those with doclaynet_index directly
    # Use the taxonomy's internal data for the count since the public
    # API doesn't expose parent info directly. Count classes whose
    # to_doclaynet returns themselves (they ARE the DocLayNet class).
    doclaynet_classes = taxonomy.get_schema_classes("doclaynet")
    top_level = len(doclaynet_classes)
    extensions = canonical_count - top_level
    click.echo(
        f"\nCanonical superset: ~{canonical_count} classes "
        f"({top_level} DocLayNet top-level + {extensions} extensions)"
    )


def _build_comparison_rows(
    taxonomy: LayoutTaxonomy,
    source_schema: str,
    target_schema: str,
) -> list[dict[str, str | bool]]:
    """Build comparison rows for two schemas.

    Args:
        taxonomy: LayoutTaxonomy instance
        source_schema: Source schema name
        target_schema: Target schema name

    Returns:
        List of dicts with keys: source_label, canonical, target_label,
        is_lossy
    """
    source_classes = taxonomy.get_schema_classes(source_schema)
    rows: list[dict[str, str | bool]] = []

    for source_label in source_classes:
        result = taxonomy.convert(source_label, source_schema, target_schema)
        target_label = result.target_label if result.target_label else "(unmapped)"
        rows.append(
            {
                "source_label": result.source_label,
                "canonical": result.canonical_class,
                "target_label": target_label,
                "is_lossy": result.is_lossy,
            }
        )

    return rows


def _format_table(
    rows: list[dict[str, str | bool]],
    source_schema: str,
    target_schema: str,
    source_count: int,
    target_count: int,
) -> str:
    """Format comparison rows as a human-readable table.

    Args:
        rows: Comparison row data
        source_schema: Source schema name
        target_schema: Target schema name
        source_count: Number of classes in source schema
        target_count: Number of classes in target schema

    Returns:
        Formatted table string
    """
    lines: list[str] = []

    header = (
        f"{source_schema} -> {target_schema} ({source_count} -> {target_count} classes)"
    )
    lines.append(header)
    lines.append("=" * len(header))

    # Calculate column widths
    src_width = max(
        len("Source Label"),
        max((len(str(r["source_label"])) for r in rows), default=0),
    )
    can_width = max(
        len("Canonical"),
        max((len(str(r["canonical"])) for r in rows), default=0),
    )
    tgt_width = max(
        len("Target Label"),
        max((len(str(r["target_label"])) for r in rows), default=0),
    )

    # Header row
    lines.append(
        f"{'Source Label':<{src_width}} | "
        f"{'Canonical':<{can_width}} | "
        f"{'Target Label':<{tgt_width}} | Lossy"
    )
    lines.append(f"{'-' * src_width}-+-{'-' * can_width}-+-{'-' * tgt_width}-+------")

    # Data rows
    for row in rows:
        lossy_marker = "*" if row["is_lossy"] else ""
        lines.append(
            f"{row['source_label']!s:<{src_width}} | "
            f"{row['canonical']!s:<{can_width}} | "
            f"{row['target_label']!s:<{tgt_width}} | "
            f"{lossy_marker}"
        )

    # Summary
    lossless = sum(1 for r in rows if not r["is_lossy"])
    lossy = sum(1 for r in rows if r["is_lossy"])
    lines.append("")
    lines.append(f"Summary: {lossless}/{len(rows)} lossless, {lossy}/{len(rows)} lossy")

    # Coverage: how many target classes are reachable
    reachable = {
        str(r["target_label"]) for r in rows if str(r["target_label"]) != "(unmapped)"
    }
    lines.append(
        f"{target_schema} coverage: {len(reachable)}/{target_count} classes reachable"
    )

    return "\n".join(lines)


def _format_json(
    rows: list[dict[str, str | bool]],
    source_schema: str,
    target_schema: str,
    source_count: int,
    target_count: int,
) -> str:
    """Format comparison rows as JSON.

    Args:
        rows: Comparison row data
        source_schema: Source schema name
        target_schema: Target schema name
        source_count: Number of classes in source schema
        target_count: Number of classes in target schema

    Returns:
        JSON string
    """
    lossless = sum(1 for r in rows if not r["is_lossy"])
    lossy = sum(1 for r in rows if r["is_lossy"])
    reachable = {
        str(r["target_label"]) for r in rows if str(r["target_label"]) != "(unmapped)"
    }

    output = {
        "source_schema": source_schema,
        "target_schema": target_schema,
        "source_class_count": source_count,
        "target_class_count": target_count,
        "mappings": [
            {
                "source_label": r["source_label"],
                "canonical": r["canonical"],
                "target_label": r["target_label"],
                "is_lossy": r["is_lossy"],
            }
            for r in rows
        ],
        "summary": {
            "total": len(rows),
            "lossless": lossless,
            "lossy": lossy,
            "target_coverage": f"{len(reachable)}/{target_count}",
        },
    }
    return json.dumps(output, indent=2)


def _format_csv(rows: list[dict[str, str | bool]]) -> str:
    """Format comparison rows as CSV.

    Args:
        rows: Comparison row data

    Returns:
        CSV string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["source_label", "canonical", "target_label", "is_lossy"])
    for row in rows:
        writer.writerow(
            [
                row["source_label"],
                row["canonical"],
                row["target_label"],
                row["is_lossy"],
            ]
        )
    return output.getvalue()


@layout.command()
@click.argument("source_schema")
@click.argument("target_schema")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format (default: table)",
)
def compare(
    source_schema: str,
    target_schema: str,
    output_format: str,
) -> None:
    """Compare label mappings between two layout schemas.

    Shows a side-by-side mapping of every class in SOURCE_SCHEMA to its
    equivalent in TARGET_SCHEMA, via the canonical superset. Lossy
    conversions (where information is lost) are flagged.

    Examples:
        imgprep layout compare docstructbench doclaynet
        imgprep layout compare docling d4la --format json
        imgprep layout compare publaynet doclaynet --format csv
    """
    taxonomy = _get_taxonomy()

    # Validate schema names
    available = taxonomy.get_available_schemas()
    for name in (source_schema, target_schema):
        if name not in available:
            click.echo(
                f"Error: Unknown schema '{name}'. Available: {', '.join(available)}",
                err=True,
            )
            sys.exit(1)

    if source_schema == target_schema:
        click.echo(
            f"Error: Source and target schemas are the same "
            f"('{source_schema}'). "
            "Choose two different schemas to compare.",
            err=True,
        )
        sys.exit(1)

    source_classes = taxonomy.get_schema_classes(source_schema)
    target_classes = taxonomy.get_schema_classes(target_schema)
    source_count = len(source_classes)
    target_count = len(target_classes)

    rows = _build_comparison_rows(taxonomy, source_schema, target_schema)

    if output_format == "table":
        click.echo(
            _format_table(
                rows,
                source_schema,
                target_schema,
                source_count,
                target_count,
            )
        )
    elif output_format == "json":
        click.echo(
            _format_json(
                rows,
                source_schema,
                target_schema,
                source_count,
                target_count,
            )
        )
    elif output_format == "csv":
        click.echo(_format_csv(rows), nl=False)
