"""Shared utilities for enrichment integration scripts.

Centralises the enrichment version scaffolding, retrieval, and upsert
logic that was previously duplicated across every
``integrate_*_enrichments.py`` script.
"""

from __future__ import annotations

from typing import Any


def ensure_enrichment_scaffold(sample: dict[str, Any]) -> dict[str, Any]:
    """Ensure ``sample["enrichments"]["versions"]`` exists.

    Creates the nested ``{"enrichments": {"versions": []}}`` structure
    when it is missing, so callers never need to guard against
    ``KeyError``.

    Args:
        sample: A single sample dict from the L2 metadata ``"samples"``
            list.  Modified **in-place**.

    Returns:
        The *same* ``sample`` dict (for chaining convenience).
    """
    enrichments = sample.setdefault("enrichments", {})
    enrichments.setdefault("versions", [])
    return sample


def get_current_version_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Return the ``data`` dict from the latest enrichment version.

    Safely handles missing ``enrichments``, empty ``versions`` list, or
    a version entry that lacks a ``data`` key.

    Args:
        sample: A single sample dict from the L2 metadata ``"samples"``
            list.

    Returns:
        The ``data`` dict of the most recent version, or an empty dict
        if no version exists yet.
    """
    versions = sample.get("enrichments", {}).get("versions")
    if not versions:
        return {}
    return versions[-1].get("data", {})


def upsert_version(
    sample: dict[str, Any],
    version_data: dict[str, Any],
    version_number: int,
) -> None:
    """Insert or replace an enrichment version entry.

    If a version with the same ``version_number`` already exists in
    ``sample["enrichments"]["versions"]`` it is replaced in-place;
    otherwise the new entry is appended.  ``current_version`` is always
    updated.

    **Prerequisite**: call :func:`ensure_enrichment_scaffold` first (or
    otherwise guarantee that ``sample["enrichments"]["versions"]``
    exists).

    Args:
        sample: A single sample dict — modified **in-place**.
        version_data: The complete version dict (must contain at least
            ``"version"``, ``"schema_version"``, ``"data"``, etc.).
        version_number: The numeric version identifier used to detect
            duplicates.
    """
    versions: list[dict[str, Any]] = sample["enrichments"]["versions"]
    replaced = False
    for idx, ver in enumerate(versions):
        if ver.get("version") == version_number:
            versions[idx] = version_data
            replaced = True
            break
    if not replaced:
        versions.append(version_data)
    sample["enrichments"]["current_version"] = version_number
