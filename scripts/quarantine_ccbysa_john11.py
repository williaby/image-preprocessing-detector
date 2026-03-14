"""Quarantine CC-BY-SA images in the John 1:1 manuscript dataset.

Adds a ``license_tier`` field to all 577 L2 JSON records and updates the
extended registry, flagging the 59 Wikimedia images that carry CC-BY-SA
ShareAlike obligations.

Commands
--------
quarantine  -- Add license_tier to L2 JSONs and rewrite extended registry.
validate    -- Verify all 577 records have license_tier; assert count == 59.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import click

REPO_ROOT = Path("/home/byron/dev/image_detection")
L2_DIR = REPO_ROOT / "metadata_registry/json/john11-manuscripts"
REGISTRY = REPO_ROOT / "metadata_registry/john11_manuscripts_registry.jsonl"
EXTENDED_REGISTRY = REPO_ROOT / "metadata_registry/john11_manuscripts_extended.jsonl"
QUARANTINE_MANIFEST = REPO_ROOT / "metadata_registry/john11_ccbysa_manifest.json"
QUARANTINE_DATE = "2026-03-12"
QUARANTINE_REASON = "4-model consensus review identified CC-BY-SA viral licensing risk"

# SPDX normalization map: primary-registry license value → SPDX identifier
_SPDX_MAP: dict[str, str] = {
    "public_domain": "PD",
    "CC0": "CC0-1.0",
    "CC-BY-4.0": "CC-BY-4.0",
    "CC-BY-2.0": "CC-BY-2.0",
    "CC-BY-SA": "CC-BY-SA-4.0",
    "CC-BY-SA-4.0": "CC-BY-SA-4.0",
    "CC-BY-SA-3.0": "CC-BY-SA-3.0",
    "CC-BY-SA-2.0": "CC-BY-SA-2.0",
}


def _is_cc_by_sa(license_value: str) -> bool:
    """Return True when *license_value* contains a CC-BY-SA variant."""
    return "cc-by-sa" in license_value.lower()


def _build_license_tier(license_value: str) -> dict[str, Any]:
    """Return the license_tier dict for *license_value*."""
    spdx = _SPDX_MAP.get(license_value, license_value)
    if _is_cc_by_sa(license_value):
        return {
            "tier": "restricted_sharealike",
            "license_spdx": spdx,
            "training_eligible": True,
            "redistribution_requires": "share_alike",
            "quarantine_reason": f"consensus_review_{QUARANTINE_DATE}",
            "confidence": 1.0,
            "provenance_tier": "tier_0_exact",
            "is_soft_label": False,
            "detection_method": "license_registry_lookup",
        }
    return {
        "tier": "open",
        "license_spdx": spdx,
        "training_eligible": True,
        "redistribution_requires": "none",
        "quarantine_reason": None,
        "confidence": 1.0,
        "provenance_tier": "tier_0_exact",
        "is_soft_label": False,
        "detection_method": "license_registry_lookup",
    }


def _load_license_map() -> dict[str, str]:
    """Return a mapping of sample_id → raw license string from REGISTRY."""
    mapping: dict[str, str] = {}
    with REGISTRY.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            sample_id: str = rec["sample_id"]
            license_value: str = rec.get("license", "")
            mapping[sample_id] = license_value
    return mapping


def _atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write *records* as JSONL to *path* using an atomic rename."""
    tmp_path = path.with_suffix(".jsonl.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# quarantine command
# ---------------------------------------------------------------------------


@click.command(name="quarantine")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without writing any files.",
)
def quarantine_cmd(dry_run: bool) -> None:
    """Add license_tier to all 577 L2 JSONs and rewrite extended registry."""
    if not L2_DIR.exists():
        click.echo(f"ERROR: L2 directory not found: {L2_DIR}", err=True)
        sys.exit(1)

    license_map = _load_license_map()
    click.echo(f"Loaded license map: {len(license_map)} entries from registry.")

    # ------------------------------------------------------------------ L2 JSON
    l2_files = sorted(L2_DIR.glob("*.json"))
    if not l2_files:
        click.echo("ERROR: No L2 JSON files found.", err=True)
        sys.exit(1)

    updated_l2 = 0
    skipped_no_id = 0
    skipped_no_license = 0
    ccbysa_sample_ids: list[str] = []
    ccbysa_scripts: dict[str, int] = {}

    for json_path in l2_files:
        with json_path.open(encoding="utf-8") as fh:
            record: dict[str, Any] = json.load(fh)

        sample_id: str | None = record.get("sample_id")
        if not sample_id:
            skipped_no_id += 1
            continue

        license_value = license_map.get(sample_id)
        if license_value is None:
            skipped_no_license += 1
            click.echo(
                f"  WARNING: no registry entry for sample_id={sample_id}",
                err=True,
            )
            continue

        tier = _build_license_tier(license_value)

        if "data" not in record:
            record["data"] = {}
        record["data"]["license_tier"] = tier

        if _is_cc_by_sa(license_value):
            ccbysa_sample_ids.append(sample_id)
            # Collect script from extended registry via L2 language field
            script = (
                record.get("data", {}).get("language", {}).get("script_code", "UNK")
                or "UNK"
            )
            ccbysa_scripts[script] = ccbysa_scripts.get(script, 0) + 1

        if not dry_run:
            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=2, ensure_ascii=False)
                fh.write("\n")

        updated_l2 += 1

    click.echo(
        f"L2 JSONs: {updated_l2} updated"
        + (f", {skipped_no_id} skipped (no sample_id)" if skipped_no_id else "")
        + (f", {skipped_no_license} skipped (no registry entry)" if skipped_no_license else "")
        + (" [DRY RUN — no files written]" if dry_run else "")
        + "."
    )

    # --------------------------------------------------- extended registry
    extended_records: list[dict[str, Any]] = []
    with EXTENDED_REGISTRY.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            rec = json.loads(raw)
            sample_id = rec.get("sample_id", "")
            license_value = license_map.get(sample_id, "")
            rec["license_tier"] = _build_license_tier(license_value)
            extended_records.append(rec)

    if not dry_run:
        _atomic_write_jsonl(EXTENDED_REGISTRY, extended_records)
    click.echo(
        f"Extended registry: {len(extended_records)} records rewritten"
        + (" [DRY RUN]" if dry_run else "")
        + "."
    )

    # --------------------------------------------------------- quarantine manifest
    manifest: dict[str, Any] = {
        "created": QUARANTINE_DATE,
        "reason": QUARANTINE_REASON,
        "total_quarantined": len(ccbysa_sample_ids),
        "quarantined_sample_ids": sorted(ccbysa_sample_ids),
        "scripts_affected": ccbysa_scripts,
    }

    if not dry_run:
        with QUARANTINE_MANIFEST.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    click.echo(
        f"Quarantine manifest: {len(ccbysa_sample_ids)} CC-BY-SA images flagged"
        + (" [DRY RUN]" if dry_run else "")
        + "."
    )
    click.echo(f"  Scripts affected: {ccbysa_scripts}")

    if dry_run:
        click.echo("\nDry-run complete — no files were modified.")
    else:
        click.echo("\nQuarantine complete.")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@click.command(name="validate")
def validate_cmd() -> None:
    """Verify all 577 L2 records have license_tier; assert restricted count == 59."""
    l2_files = sorted(L2_DIR.glob("*.json"))
    total = len(l2_files)
    missing_tier: list[str] = []
    restricted_count = 0
    open_count = 0
    errors: list[str] = []

    for json_path in l2_files:
        with json_path.open(encoding="utf-8") as fh:
            try:
                record: dict[str, Any] = json.load(fh)
            except json.JSONDecodeError as exc:
                errors.append(f"{json_path.name}: JSON parse error — {exc}")
                continue

        data = record.get("data", {})
        tier_obj: dict[str, Any] | None = data.get("license_tier")  # type: ignore[assignment]

        if tier_obj is None:
            missing_tier.append(json_path.stem)
            continue

        tier_value = tier_obj.get("tier", "")
        if tier_value == "restricted_sharealike":
            restricted_count += 1
        elif tier_value == "open":
            open_count += 1
        else:
            errors.append(f"{json_path.stem}: unknown tier value '{tier_value}'")

    click.echo(f"L2 files scanned     : {total}")
    click.echo(f"license_tier present : {total - len(missing_tier)}")
    click.echo(f"license_tier missing : {len(missing_tier)}")
    click.echo(f"tier=open            : {open_count}")
    click.echo(f"tier=restricted_sha  : {restricted_count}")

    if errors:
        click.echo(f"\nERRORS ({len(errors)}):", err=True)
        for err in errors:
            click.echo(f"  {err}", err=True)

    if missing_tier:
        click.echo(f"\nMISSING license_tier ({len(missing_tier)} files):", err=True)
        for sid in missing_tier[:20]:
            click.echo(f"  {sid}", err=True)
        if len(missing_tier) > 20:
            click.echo(f"  ... and {len(missing_tier) - 20} more", err=True)

    # --------------------------------------------------------- assertions
    passed = True

    if len(missing_tier) != 0:
        click.echo(
            f"\nFAIL: {len(missing_tier)} records are missing license_tier (expected 0).",
            err=True,
        )
        passed = False

    if total != 577:
        click.echo(
            f"\nFAIL: expected 577 L2 files, found {total}.",
            err=True,
        )
        passed = False

    if restricted_count != 59:
        click.echo(
            f"\nFAIL: expected 59 restricted_sharealike records, found {restricted_count}.",
            err=True,
        )
        passed = False

    if passed:
        click.echo(
            "\nPASS: all 577 records have license_tier; 59 flagged as restricted_sharealike."
        )
    else:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Quarantine CC-BY-SA images in the John 1:1 manuscript dataset."""


cli.add_command(quarantine_cmd)
cli.add_command(validate_cmd)

if __name__ == "__main__":
    cli()
