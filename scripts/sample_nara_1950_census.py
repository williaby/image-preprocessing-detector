#!/usr/bin/env python3
"""Sample images from NARA 1950 Census S3 bucket for handwriting training.

Downloads state metadata JSONs, builds a manifest of all available images,
then performs stratified sampling across states to select a representative
subset. Downloads selected images to the local data directory.

The NARA 1950 Census dataset contains scanned census enumeration schedules:
handwritten forms from the 1950 U.S. Population Census. Each page contains
tabular handwritten data ideal for handwriting detection and form layout.

Usage:
    # Build manifest (download metadata from S3, compute total counts)
    python scripts/sample_nara_1950_census.py manifest

    # Sample N images stratified across states
    python scripts/sample_nara_1950_census.py sample --count 1000

    # Download sampled images
    python scripts/sample_nara_1950_census.py download

    # Full pipeline: manifest → sample → download
    python scripts/sample_nara_1950_census.py all --count 1000
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(
    os.environ.get(
        "NARA_DATA_DIR",
        "/mnt/e/image_detection/01_base_data/forms/nara-1950-census",
    )
)
METADATA_DIR = DATA_DIR / "metadata"
IMAGES_DIR = DATA_DIR / "images"
MANIFEST_PATH = DATA_DIR / "manifest.json"
SAMPLE_PATH = DATA_DIR / "sample.json"

S3_BUCKET = "nara-1950-census"
S3_BASE_URL = "https://nara-1950-census.s3.us-east-2.amazonaws.com"

# All 50 states + DC + territories with metadata
US_STATES = [
    "ak",
    "al",
    "ar",
    "as",
    "az",
    "ca",
    "cn",
    "co",
    "ct",
    "dc",
    "de",
    "fl",
    "ga",
    "gu",
    "hi",
    "ia",
    "id",
    "il",
    "in",
    "jn",
    "ks",
    "ky",
    "la",
    "ma",
    "md",
    "me",
    "mi",
    "mn",
    "mo",
    "ms",
    "mt",
    "nc",
    "nd",
    "ne",
    "nh",
    "nj",
    "nm",
    "nv",
    "ny",
    "oh",
    "ok",
    "or",
    "pa",
    "pr",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "va",
    "vi",
    "vt",
    "wa",
    "wi",
    "wv",
    "wy",
]


@dataclass
class ImageRecord:
    """A single census page image with its metadata."""

    state: str
    county: str
    ed: str
    folder: str
    filename: str

    @property
    def url(self) -> str:
        """Full S3 HTTP URL for this image."""
        return f"{S3_BASE_URL}/{self.folder}/{self.filename}"

    @property
    def local_path(self) -> Path:
        """Local path for downloaded image."""
        return IMAGES_DIR / self.state / self.filename

    def to_dict(self) -> dict[str, str]:
        """Serialize to JSON-safe dict."""
        return {
            "state": self.state,
            "county": self.county,
            "ed": self.ed,
            "folder": self.folder,
            "filename": self.filename,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> ImageRecord:
        """Deserialize from dict."""
        return cls(
            state=d["state"],
            county=d["county"],
            ed=d["ed"],
            folder=d["folder"],
            filename=d["filename"],
        )


def download_state_metadata(state: str) -> dict | None:
    """Download a state's metadata JSON from S3."""
    local_path = METADATA_DIR / f"{state}.json"
    if local_path.exists():
        logger.debug("Using cached metadata for %s", state)
        with open(local_path, encoding="utf-8") as f:
            return json.load(f)

    s3_key = f"s3://{S3_BUCKET}/metadata/json/{state}.json"
    result = subprocess.run(
        ["aws", "s3", "cp", s3_key, str(local_path), "--no-sign-request"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        logger.warning("Failed to download %s: %s", state, result.stderr.strip())
        return None

    with open(local_path, encoding="utf-8") as f:
        return json.load(f)


def build_manifest_for_state(state: str, data: dict) -> list[ImageRecord]:
    """Extract all image records from a state's metadata."""
    records: list[ImageRecord] = []
    for county in data.get("county/city", []):
        county_name = county.get("name", "unknown")
        for ed_entry in county.get("enumeration", []):
            ed_id = ed_entry.get("ed", "unknown")
            schedule = ed_entry.get("schedule_image", {})
            folder = schedule.get("folder", "")
            for filename in schedule.get("files", []):
                records.append(
                    ImageRecord(
                        state=state,
                        county=county_name,
                        ed=ed_id,
                        folder=folder,
                        filename=filename,
                    )
                )
    return records


def stratified_sample(
    manifest: dict[str, list[dict[str, str]]],
    target_count: int,
    seed: int = 42,
) -> list[dict[str, str]]:
    """Sample proportionally across states, ensuring at least 1 per state."""
    rng = random.Random(
        seed
    )  # NOSONAR: seeded PRNG for reproducible sampling, not security
    total_images = sum(len(records) for records in manifest.values())
    logger.info(
        "Total images in manifest: %d across %d states", total_images, len(manifest)
    )

    if target_count >= total_images:
        logger.warning(
            "Requested %d >= total %d, returning all", target_count, total_images
        )
        return [r for records in manifest.values() for r in records]

    # Allocate at least 1 per state, rest proportionally
    sampled: list[dict[str, str]] = []
    states = sorted(manifest.keys())
    nonempty_states = [s for s in states if manifest[s]]
    remaining = target_count

    # Guard: if target_count < number of non-empty states, sample states first
    if target_count < len(nonempty_states):
        selected_states = rng.sample(nonempty_states, target_count)
        for state in selected_states:
            chosen = rng.sample(manifest[state], 1)
            sampled.extend(chosen)
        logger.info(
            "Sampled %d images across %d states (capped)",
            len(sampled),
            len(selected_states),
        )
        return sampled

    # First pass: ensure 1 per state (if state has images)
    state_allocations: dict[str, int] = {}
    for state in nonempty_states:
        state_allocations[state] = 1
        remaining -= 1

    # Second pass: distribute remaining proportionally
    if remaining > 0:
        for state in states:
            if state not in state_allocations:
                continue
            proportion = len(manifest[state]) / total_images
            extra = int(remaining * proportion)
            state_allocations[state] += extra

    # Adjust for rounding (add extras to largest states)
    allocated = sum(state_allocations.values())
    deficit = target_count - allocated
    if deficit > 0:
        by_size = sorted(states, key=lambda s: len(manifest.get(s, [])), reverse=True)
        for state in by_size[:deficit]:
            if state in state_allocations:
                state_allocations[state] += 1

    # Sample from each state
    for state in states:
        n = state_allocations.get(state, 0)
        if n <= 0:
            continue
        pool = manifest[state]
        n = min(n, len(pool))
        chosen = rng.sample(pool, n)
        sampled.extend(chosen)

    logger.info(
        "Sampled %d images across %d states", len(sampled), len(state_allocations)
    )
    return sampled


@click.group()
def cli() -> None:
    """NARA 1950 Census image sampling tool."""


@cli.command()
def manifest() -> None:
    """Build manifest from S3 metadata (downloads state JSONs)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    full_manifest: dict[str, list[dict[str, str]]] = {}
    total = 0

    for state in US_STATES:
        data = download_state_metadata(state)
        if data is None:
            continue
        records = build_manifest_for_state(state, data)
        full_manifest[state] = [r.to_dict() for r in records]
        total += len(records)
        logger.info(
            "  %s: %d images (%s)", state.upper(), len(records), data.get("state", "?")
        )

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(full_manifest, f, indent=2)

    logger.info(
        "Manifest saved: %d total images across %d states", total, len(full_manifest)
    )


@cli.command()
@click.option("--count", default=1000, help="Number of images to sample")
@click.option("--seed", default=42, help="Random seed for reproducibility")
def sample(count: int, seed: int) -> None:
    """Sample N images stratified across states."""
    if not MANIFEST_PATH.exists():
        logger.error("No manifest found. Run 'manifest' first.")
        return

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        full_manifest = json.load(f)

    sampled = stratified_sample(full_manifest, count, seed=seed)

    with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump(sampled, f, indent=2)

    # Print state distribution
    state_counts: dict[str, int] = {}
    for r in sampled:
        state_counts[r["state"]] = state_counts.get(r["state"], 0) + 1
    logger.info("Sample distribution:")
    for state in sorted(state_counts):
        logger.info("  %s: %d", state.upper(), state_counts[state])

    logger.info("Sample saved: %d images to %s", len(sampled), SAMPLE_PATH)


@cli.command()
def download() -> None:
    """Download sampled images from S3."""
    if not SAMPLE_PATH.exists():
        logger.error("No sample found. Run 'sample' first.")
        return

    with open(SAMPLE_PATH, encoding="utf-8") as f:
        sampled = json.load(f)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for record in sampled:
        img = ImageRecord.from_dict(record)
        local = img.local_path
        local.parent.mkdir(parents=True, exist_ok=True)

        if local.exists():
            skipped += 1
            continue

        result = subprocess.run(
            ["wget", "-q", "--timeout=30", "-O", str(local), img.url],
            capture_output=True,
            timeout=60,
        )
        if result.returncode == 0:
            downloaded += 1
        else:
            failed += 1
            logger.warning("Failed: %s", img.filename)

        if (downloaded + skipped) % 50 == 0:
            logger.info(
                "Progress: %d downloaded, %d skipped, %d failed",
                downloaded,
                skipped,
                failed,
            )

    logger.info(
        "Done: %d downloaded, %d skipped, %d failed", downloaded, skipped, failed
    )


@cli.command(name="all")
@click.option("--count", default=1000, help="Number of images to sample")
@click.option("--seed", default=42, help="Random seed")
@click.pass_context
def run_all(ctx: click.Context, count: int, seed: int) -> None:
    """Full pipeline: manifest → sample → download."""
    ctx.invoke(manifest)
    ctx.invoke(sample, count=count, seed=seed)
    ctx.invoke(download)


if __name__ == "__main__":
    cli()
