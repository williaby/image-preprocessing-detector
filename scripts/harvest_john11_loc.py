#!/usr/bin/env python3
"""Harvest John 1:1 manuscript pages from Library of Congress collections.

Downloads individual John 1:1 folios from LOC's digitized Gospel manuscripts
(St. Catherine's Sinai + Jerusalem Patriarchates). All images are Public Domain.

The LOC holds 376 Gospel manuscripts across 6 scripts. Each "Four Gospels"
manuscript contains exactly one John 1:1 page, typically 72-78% through.

Strategy:
  1. `catalog` — Build/refresh manuscript catalog from LOC API
  2. `estimate-folios` — Estimate John 1:1 folio positions per manuscript
  3. `download-candidates` — Download 3-page windows around estimated positions
  4. `identify` — Use VLM to identify the actual John 1:1 folio from candidates
  5. `harvest` — Download confirmed John 1:1 folios at full resolution
  6. `register` — Register harvested images in john11 registry
  7. `stats` — Show harvest progress

Usage:
    uv run python scripts/harvest_john11_loc.py catalog
    uv run python scripts/harvest_john11_loc.py estimate-folios
    uv run python scripts/harvest_john11_loc.py download-candidates --script Syrc
    uv run python scripts/harvest_john11_loc.py harvest --script Syrc
    uv run python scripts/harvest_john11_loc.py stats
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import click
import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_LOC_CATALOG_PATH = _PROJECT_ROOT / "config" / "john11_loc_manuscript_catalog.json"
_FOLIO_ESTIMATES_PATH = _PROJECT_ROOT / "config" / "john11_loc_folio_estimates.json"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_manuscripts_registry.jsonl"
)
_EXTENDED_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_manuscripts_extended.jsonl"
)
_DEFAULT_OUTPUT_DIR = Path(
    "/mnt/e/image_detection/01_base_data/manuscripts/john11"
)
_LOCAL_OUTPUT_DIR = _PROJECT_ROOT / "data" / "john11-manuscripts"
_CANDIDATES_DIR = _LOCAL_OUTPUT_DIR / "loc_candidates"

# ---------------------------------------------------------------------------
# LOC API config
# ---------------------------------------------------------------------------

_LOC_COLLECTIONS = {
    "sinai": {
        "name": "St. Catherine's Monastery, Mount Sinai",
        "base_url": "https://www.loc.gov/collections/manuscripts-in-st-catherines-monastery-mount-sinai/",
        "credit": (
            "Library of Congress Collection of Manuscripts "
            "in St. Catherine's Monastery, Mt. Sinai"
        ),
    },
    "jerusalem": {
        "name": "Greek and Armenian Patriarchates of Jerusalem",
        "base_url": "https://www.loc.gov/collections/greek-and-armenian-patriarchates-of-jerusalem/",
        "credit": (
            "Library of Congress Collection of Manuscripts "
            "in the Greek/Armenian Patriarchate of Jerusalem"
        ),
    },
}

_LANG_TO_SCRIPT: dict[str, str] = {
    "greek, ancient (to 1453)": "Grek",
    "greek": "Grek",
    "arabic": "Arab",
    "syriac": "Syrc",
    "georgian": "Geor",
    "old bulgarian": "Cyrs",
    "slavic languages": "Cyrs",
    "church slavic": "Cyrs",
    "armenian": "Armn",
    "ethiopic": "Ethi",
    "coptic": "Copt",
    "latin": "Latn",
}

# Typical position of John in a Four Gospels manuscript (fraction of total pages).
# Matthew ~28%, Mark ~16%, Luke ~28% → John starts ~72% through.
# We use a window because scribal practice varied.
_JOHN_START_FRACTION_MIN = 0.70
_JOHN_START_FRACTION_MAX = 0.80
_JOHN_START_FRACTION_MID = 0.75

# Minimum image dimension filter — reject images smaller than this in either
# dimension.  Website UI scraping artifacts (logos, icons, badges) are typically
# well below this threshold.  Manuscript/printed edition pages should be
# substantially larger.
MIN_IMAGE_DIMENSION = 200  # pixels

# Rate limiting — LOC API returns 429 aggressively
_REQUEST_DELAY = 2.0  # seconds between LOC API requests
_DOWNLOAD_DELAY = 1.5  # seconds between image downloads
_MAX_RETRIES = 4
_RETRY_BACKOFF = 10.0  # seconds base backoff for 429 retries

log = logging.getLogger("harvest_john11_loc")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def _get_output_dir() -> Path:
    """Return best available output directory."""
    if _DEFAULT_OUTPUT_DIR.exists():
        return _DEFAULT_OUTPUT_DIR
    _LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _LOCAL_OUTPUT_DIR


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_catalog() -> list[dict[str, Any]]:
    """Load LOC manuscript catalog."""
    if not _LOC_CATALOG_PATH.exists():
        log.error("Catalog not found at %s — run `catalog` command first", _LOC_CATALOG_PATH)
        sys.exit(1)
    with open(_LOC_CATALOG_PATH) as f:
        return json.load(f)


def _save_catalog(catalog: list[dict[str, Any]]) -> None:
    """Save LOC manuscript catalog."""
    _LOC_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOC_CATALOG_PATH, "w") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    log.info("Saved catalog with %d entries to %s", len(catalog), _LOC_CATALOG_PATH)


def _classify_gospel_type(title: str) -> str | None:
    """Classify manuscript as gospel type or None."""
    t = title.lower()
    if "four gospels" in t or "chetveroevangelie" in t:
        return "four_gospels"
    if "evangelion" in t:
        return "evangelion"
    if "lectionary" in t and "gospel" in t:
        return "lectionary_gospel"
    if "gospel" in t and any(g in t for g in ("matthew", "john", "luke", "mark")):
        return "partial_gospel"
    if "gospel" in t:
        return "gospel_other"
    return None


def _john_status(title: str) -> str:
    """Determine if manuscript definitely contains John 1:1."""
    t = title.lower()
    if "four gospels" in t or "chetveroevangelie" in t or "evangelion" in t:
        return "definite"
    if "john" in t:
        return "definite"
    if "lectionary" in t and "gospel" in t:
        return "possible"
    if "commentary" in t:
        return "unlikely"
    return "unknown"


def _fetch_loc_api(url: str) -> dict[str, Any]:
    """Fetch JSON from LOC API with rate limiting and retry on 429."""
    for attempt in range(_MAX_RETRIES):
        time.sleep(_REQUEST_DELAY)
        resp = requests.get(
            url, headers={"User-Agent": "john11-harvest/1.0 (research)"}, timeout=30,
        )
        if resp.status_code == 429:
            backoff = _RETRY_BACKOFF * (attempt + 1)
            log.warning("Rate limited (429), backing off %.1fs (attempt %d/%d)", backoff, attempt + 1, _MAX_RETRIES)
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        return resp.json()
    msg = f"Failed after {_MAX_RETRIES} retries: {url}"
    raise RuntimeError(msg)


def _get_manuscript_pages(loc_id: str) -> list[dict[str, Any]]:
    """Get page-level file info for a manuscript from LOC API.

    Returns list of page dicts, each with 'page_num' and 'iiif_url' keys.
    """
    # loc_id may use http: — ensure we use https to avoid redirect overhead
    clean_id = loc_id.replace("http://", "https://")
    item_url = clean_id.rstrip("/") + "/?fo=json"
    data = _fetch_loc_api(item_url)

    resources = data.get("resources", [])
    if not resources:
        return []

    files = resources[0].get("files", [])
    pages = []
    for i, file_group in enumerate(files):
        # Find highest resolution variant
        best = None
        best_pixels = 0
        for variant in file_group:
            pixels = variant.get("height", 0) * variant.get("width", 0)
            if pixels > best_pixels:
                best = variant
                best_pixels = pixels

        if best:
            pages.append({
                "page_num": i + 1,
                "page_idx": i,
                "url": best.get("url", ""),
                "height": best.get("height", 0),
                "width": best.get("width", 0),
            })

    return pages


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Harvest John 1:1 manuscript pages from Library of Congress."""
    _setup_logging(verbose)


@cli.command()
def catalog() -> None:
    """Build/refresh LOC Gospel manuscript catalog from API.

    Queries both St. Catherine's Sinai and Jerusalem Patriarchate collections
    for all Gospel manuscripts. Saves to config/john11_loc_manuscript_catalog.json.
    """
    all_mss: list[dict[str, Any]] = []

    for collection_key, info in _LOC_COLLECTIONS.items():
        for query in ["gospel", "evangelion"]:
            url = f"{info['base_url']}?q={query}&fo=json&c=200"
            log.info("Fetching %s/%s ...", collection_key, query)

            try:
                data = _fetch_loc_api(url)
            except Exception:
                log.exception("Failed to fetch %s/%s", collection_key, query)
                continue

            for item in data.get("results", []):
                title = item.get("title", "")
                gospel_type = _classify_gospel_type(title)
                if gospel_type is None:
                    continue

                langs = item.get("language", [])
                lang = langs[0] if langs else "unknown"
                script = _LANG_TO_SCRIPT.get(lang.lower())
                if script is None:
                    continue

                item_url = item.get("url", "")

                # Extract IIIF service ID
                iiif_id = None
                for img_url in item.get("image_url", []):
                    if "tile.loc.gov" in img_url and "service:" in img_url:
                        iiif_id = img_url.split("service:")[1].split("/")[0]
                        break

                all_mss.append({
                    "collection": collection_key,
                    "title": title.strip().rstrip("."),
                    "script_iso15924": script,
                    "language": lang,
                    "date": item.get("date", "Unknown"),
                    "gospel_type": gospel_type,
                    "john_status": _john_status(title),
                    "loc_url": item_url,
                    "loc_id": item.get("id", item_url),
                    "iiif_service_id": iiif_id,
                    "license": "PD",
                    "credit": info["credit"],
                })

    # Deduplicate by loc_id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for ms in all_mss:
        key = ms["loc_id"]
        if key not in seen:
            seen.add(key)
            unique.append(ms)

    unique.sort(key=lambda x: (x["script_iso15924"], x["collection"], x["title"]))
    _save_catalog(unique)

    # Summary
    by_script: dict[str, int] = {}
    definite = 0
    for ms in unique:
        s = ms["script_iso15924"]
        by_script[s] = by_script.get(s, 0) + 1
        if ms["john_status"] == "definite":
            definite += 1

    click.echo(f"\nTotal: {len(unique)} Gospel manuscripts ({definite} definite John 1:1)")
    for s in sorted(by_script):
        click.echo(f"  {s}: {by_script[s]}")


def _extract_folio_count_from_title(title: str) -> int | None:
    """Extract folio count from Jerusalem-style titles like '289 f. Pg. 26 ft.'."""
    import re
    match = re.search(r"(\d+)\s*f\.", title)
    if match:
        return int(match.group(1))
    return None


@cli.command("estimate-folios")
@click.option("--script", "-s", default=None, help="Filter by ISO 15924 script code (e.g. Syrc)")
@click.option("--limit", "-n", default=0, type=int, help="Max manuscripts to process (0=all)")
@click.option(
    "--from-titles", is_flag=True,
    help="Use folio counts from titles (no API calls). Works for Jerusalem collection.",
)
@click.option(
    "--from-api", is_flag=True,
    help="Fetch page counts from LOC API (slow, rate-limited). Works for all.",
)
@click.option(
    "--default-pages", type=int, default=300,
    help="Default page count for manuscripts without title-based counts.",
)
def estimate_folios(
    script: str | None,
    limit: int,
    from_titles: bool,
    from_api: bool,
    default_pages: int,
) -> None:
    """Estimate John 1:1 folio positions for each manuscript.

    Two modes:
      --from-titles: Extract folio counts from catalog titles (fast, no API).
        Jerusalem titles include 'N f.' format. Sinai titles use default.
      --from-api: Fetch page counts from LOC API (slow, rate-limited).

    Default (no flag): uses --from-titles mode.
    Saves estimates to config/john11_loc_folio_estimates.json.
    """
    if not from_api and not from_titles:
        from_titles = True  # default mode

    catalog = _load_catalog()
    definite = [m for m in catalog if m["john_status"] == "definite"]
    if script:
        definite = [m for m in definite if m["script_iso15924"] == script]
    if limit > 0:
        definite = definite[:limit]
    log.info("Estimating folios for %d definite-John manuscripts", len(definite))

    # Load existing estimates to merge (incremental runs)
    existing_estimates: list[dict[str, Any]] = []
    existing_ids: set[str] = set()
    if _FOLIO_ESTIMATES_PATH.exists():
        with open(_FOLIO_ESTIMATES_PATH) as f:
            existing_estimates = json.load(f)
        existing_ids = {e["loc_id"] for e in existing_estimates}

    estimates: list[dict[str, Any]] = list(existing_estimates)
    new_count = 0
    errors = 0

    # Skip manuscripts already estimated
    definite = [m for m in definite if m["loc_id"] not in existing_ids]
    log.info("Skipping %d already-estimated, processing %d new", len(existing_ids), len(definite))

    for i, ms in enumerate(definite):
        if i > 0 and i % 50 == 0:
            log.info("Progress: %d/%d", i, len(definite))

        total: int | None = None

        if from_titles:
            folio_count = _extract_folio_count_from_title(ms["title"])
            if folio_count:
                total = folio_count * 2  # recto + verso
            else:
                total = default_pages
                log.debug("Using default %d pages for %s", default_pages, ms["title"])

        elif from_api:
            try:
                pages = _get_manuscript_pages(ms["loc_id"])
                total = len(pages)
            except Exception:
                log.exception("Error fetching pages for %s", ms["title"])
                errors += 1
                continue

        if total is None or total < 10:
            log.warning("Skipping %s — total=%s", ms["title"], total)
            errors += 1
            continue

        # Estimate John 1:1 position
        if ms["gospel_type"] in ("four_gospels", "evangelion"):
            est_page = int(total * _JOHN_START_FRACTION_MID)
            window_start = max(1, int(total * _JOHN_START_FRACTION_MIN))
            window_end = min(total, int(total * _JOHN_START_FRACTION_MAX))
        elif "john" in ms["title"].lower():
            est_page = 1
            window_start = 1
            window_end = min(total, 10)
        else:
            est_page = int(total * _JOHN_START_FRACTION_MID)
            window_start = max(1, int(total * 0.65))
            window_end = min(total, int(total * 0.85))

        source = "title_folios" if from_titles and _extract_folio_count_from_title(ms["title"]) else "default"
        if from_api:
            source = "api"

        new_entry = {
            "loc_id": ms["loc_id"],
            "title": ms["title"],
            "script": ms["script_iso15924"],
            "collection": ms["collection"],
            "total_pages": total,
            "page_count_source": source,
            "estimated_john_page": est_page,
            "candidate_window_start": window_start,
            "candidate_window_end": window_end,
            "candidate_pages": list(range(window_start, window_end + 1)),
            "status": "estimated",
            "confirmed_page": None,
        }
        estimates.append(new_entry)
        new_count += 1

    # Save
    _FOLIO_ESTIMATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_FOLIO_ESTIMATES_PATH, "w") as f:
        json.dump(estimates, f, indent=2, ensure_ascii=False)

    log.info(
        "Saved %d folio estimates (%d new, %d errors) to %s",
        len(estimates), new_count, errors, _FOLIO_ESTIMATES_PATH,
    )

    # Summary
    by_script: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for e in estimates:
        s = e["script"]
        by_script[s] = by_script.get(s, 0) + 1
        src = e.get("page_count_source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    click.echo(f"\nFolio estimates: {len(estimates)} manuscripts")
    for s in sorted(by_script):
        click.echo(f"  {s}: {by_script[s]}")
    click.echo("\nPage count sources:")
    for src in sorted(by_source):
        click.echo(f"  {src}: {by_source[src]}")
    if errors:
        click.echo(f"  Errors: {errors}")


@cli.command("download-candidates")
@click.option("--script", "-s", default=None, help="Filter by ISO 15924 script code")
@click.option("--collection", "-c", default=None, help="Filter by collection (sinai/jerusalem)")
@click.option("--limit", "-n", default=0, type=int, help="Max manuscripts to process (0=all)")
@click.option("--dry-run", is_flag=True, help="Show what would be downloaded")
def download_candidates(
    script: str | None, collection: str | None, limit: int, dry_run: bool,
) -> None:
    """Download candidate page windows for John 1:1 identification.

    Downloads 3-5 pages around the estimated John 1:1 position for each
    manuscript. These candidates are then reviewed (manually or via VLM)
    to identify the actual John 1:1 folio.
    """
    if not _FOLIO_ESTIMATES_PATH.exists():
        log.error("Folio estimates not found — run `estimate-folios` first")
        sys.exit(1)

    with open(_FOLIO_ESTIMATES_PATH) as f:
        estimates = json.load(f)

    # Filter
    if script:
        estimates = [e for e in estimates if e["script"] == script]
    if collection:
        estimates = [e for e in estimates if e["collection"] == collection]
    if limit > 0:
        estimates = estimates[:limit]

    log.info("Processing %d manuscripts", len(estimates))

    if dry_run:
        total_pages = sum(len(e["candidate_pages"]) for e in estimates)
        click.echo(f"Would download {total_pages} candidate pages from {len(estimates)} manuscripts")
        for e in estimates:
            click.echo(
                f"  {e['script']} | {e['title'][:60]} | "
                f"pages {e['candidate_window_start']}-{e['candidate_window_end']} "
                f"of {e['total_pages']}"
            )
        return

    _CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    errors = 0

    for e in estimates:
        ms_slug = e["loc_id"].strip("/").split("/")[-1]
        ms_dir = _CANDIDATES_DIR / e["script"] / ms_slug
        ms_dir.mkdir(parents=True, exist_ok=True)

        # Get page URLs
        try:
            pages = _get_manuscript_pages(e["loc_id"])
        except Exception:
            log.exception("Failed to get pages for %s", e["title"])
            errors += 1
            continue

        # Download candidate pages
        for page_num in e["candidate_pages"]:
            if page_num > len(pages):
                continue

            page = pages[page_num - 1]
            out_path = ms_dir / f"page_{page_num:04d}.jpg"

            if out_path.exists():
                log.debug("Already exists: %s", out_path)
                continue

            try:
                time.sleep(_DOWNLOAD_DELAY)
                resp = requests.get(
                    page["url"],
                    headers={"User-Agent": "john11-harvest/1.0 (research)"},
                    timeout=60,
                )
                resp.raise_for_status()
                out_path.write_bytes(resp.content)
                downloaded += 1
                log.debug("Downloaded %s (%d bytes)", out_path.name, len(resp.content))
            except Exception:
                log.exception("Failed to download page %d of %s", page_num, e["title"])
                errors += 1

        log.info(
            "Processed %s (%s) — %d candidate pages",
            e["title"][:50], e["script"], len(e["candidate_pages"]),
        )

    click.echo(f"\nDownloaded {downloaded} pages ({errors} errors)")


@cli.command()
@click.option("--script", "-s", default=None, help="Filter by ISO 15924 script code")
@click.option("--confirmed-only", is_flag=True, help="Only harvest confirmed John 1:1 pages")
@click.option("--use-estimate", is_flag=True, help="Use estimated page (skip VLM confirmation)")
@click.option("--limit", "-n", default=0, type=int, help="Max manuscripts to harvest")
@click.option("--dry-run", is_flag=True, help="Show what would be harvested")
def harvest(
    script: str | None,
    confirmed_only: bool,
    use_estimate: bool,
    limit: int,
    dry_run: bool,
) -> None:
    """Download confirmed John 1:1 folios at full resolution.

    By default, only harvests manuscripts with confirmed_page set in the
    folio estimates file. Use --use-estimate to harvest the estimated page
    directly (useful when VLM identification is not yet complete).
    """
    if not _FOLIO_ESTIMATES_PATH.exists():
        log.error("Folio estimates not found — run `estimate-folios` first")
        sys.exit(1)

    with open(_FOLIO_ESTIMATES_PATH) as f:
        estimates = json.load(f)

    # Filter
    if script:
        estimates = [e for e in estimates if e["script"] == script]
    if confirmed_only:
        estimates = [e for e in estimates if e.get("confirmed_page") is not None]
    if limit > 0:
        estimates = estimates[:limit]

    output_dir = _get_output_dir()
    loc_dir = output_dir / "loc"
    loc_dir.mkdir(parents=True, exist_ok=True)

    log.info("Harvesting %d manuscripts to %s", len(estimates), loc_dir)

    if dry_run:
        for e in estimates:
            page = e.get("confirmed_page") or (e["estimated_john_page"] if use_estimate else None)
            status = "confirmed" if e.get("confirmed_page") else ("estimate" if use_estimate else "SKIP")
            click.echo(f"  {e['script']} | {e['title'][:60]} | page={page} ({status})")
        return

    harvested = 0
    errors = 0
    catalog = _load_catalog()
    catalog_by_id = {m["loc_id"]: m for m in catalog}

    for e in estimates:
        target_page = e.get("confirmed_page")
        if target_page is None and use_estimate:
            target_page = e["estimated_john_page"]
        if target_page is None:
            log.debug("Skipping %s — no confirmed page", e["title"])
            continue

        ms_slug = e["loc_id"].strip("/").split("/")[-1]
        script_code = e["script"]
        filename = f"loc_{e['collection']}_{script_code}_{ms_slug}_p{target_page:04d}.jpg"
        out_path = loc_dir / filename

        if out_path.exists():
            log.debug("Already harvested: %s", out_path)
            harvested += 1
            continue

        try:
            pages = _get_manuscript_pages(e["loc_id"])
            if target_page > len(pages):
                log.warning("Page %d exceeds total %d for %s", target_page, len(pages), e["title"])
                errors += 1
                continue

            page_info = pages[target_page - 1]
            time.sleep(_DOWNLOAD_DELAY)
            resp = requests.get(
                page_info["url"],
                headers={"User-Agent": "john11-harvest/1.0 (research)"},
                timeout=60,
            )
            resp.raise_for_status()
            out_path.write_bytes(resp.content)

            # Verify it's a valid image before counting
            try:
                from PIL import Image

                with Image.open(out_path) as img:
                    img.verify()
            except Exception:
                click.echo(f"  [SKIP] Invalid image: {out_path.name}")
                out_path.unlink()
                errors += 1
                continue

            # Reject images below minimum dimension (website UI artifacts, icons)
            from PIL import Image

            with Image.open(out_path) as img:
                if min(img.width, img.height) < MIN_IMAGE_DIMENSION:
                    click.echo(
                        f"  [SKIP] Below min dimension ({img.width}x{img.height} "
                        f"< {MIN_IMAGE_DIMENSION}px): {out_path.name}"
                    )
                    out_path.unlink()
                    errors += 1
                    continue

            harvested += 1
            log.info(
                "Harvested %s page %d → %s (%d bytes)",
                e["title"][:40], target_page, filename, len(resp.content),
            )
        except Exception:
            log.exception("Failed to harvest %s", e["title"])
            errors += 1

    click.echo(f"\nHarvested {harvested} images ({errors} errors) to {loc_dir}")


@cli.command()
@click.option("--script", "-s", default=None, help="Filter by ISO 15924 script code")
def register(script: str | None) -> None:
    """Register harvested LOC images in the john11 registry.

    Scans the LOC output directory for harvested images and creates
    registry entries with proper sample_ids, SHA-256, and metadata.
    """
    output_dir = _get_output_dir()
    loc_dir = output_dir / "loc"

    if not loc_dir.exists():
        log.error("No LOC harvest directory at %s", loc_dir)
        sys.exit(1)

    catalog = _load_catalog()
    catalog_by_id = {m["loc_id"]: m for m in catalog}

    images = sorted(loc_dir.glob("*.jpg"))
    if script:
        images = [p for p in images if f"_{script}_" in p.name]

    log.info("Registering %d harvested LOC images", len(images))

    # Load existing registry to check for duplicates
    existing_shas: set[str] = set()
    if _REGISTRY_PATH.exists():
        with open(_REGISTRY_PATH) as f:
            for line in f:
                entry = json.loads(line)
                existing_shas.add(entry.get("sha256", ""))

    new_entries: list[dict[str, Any]] = []
    for img_path in images:
        sha = _sha256_file(img_path)
        if sha in existing_shas:
            log.debug("Already registered: %s", img_path.name)
            continue

        # Parse filename: loc_{collection}_{script}_{ms_slug}_p{page}.jpg
        parts = img_path.stem.split("_", 3)
        if len(parts) < 4:
            log.warning("Unexpected filename format: %s", img_path.name)
            continue

        collection = parts[1]
        script_code = parts[2]
        rest = parts[3]  # {ms_slug}_p{page}

        sample_id = f"john11_{script_code.lower()}_loc_{uuid.uuid4().hex[:8]}"
        source_institution = f"loc_{collection}"

        loc_info = _LOC_COLLECTIONS.get(collection, {})

        entry = {
            "sample_id": sample_id,
            "dataset": "john11-manuscripts",
            "source_institution": source_institution,
            "source_path": str(img_path.relative_to(output_dir)),
            "sha256": sha,
            "script_iso15924": script_code,
            "license": "PD",
            "license_spdx": "LicenseRef-PublicDomain",
            "credit": loc_info.get("credit", "Library of Congress"),
            "harvest_date": str(date.today()),
            "harvest_script": "scripts/harvest_john11_loc.py",
        }
        new_entries.append(entry)

    if new_entries:
        with open(_REGISTRY_PATH, "a") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        click.echo(f"Registered {len(new_entries)} new images")
    else:
        click.echo("No new images to register")


@cli.command()
def stats() -> None:
    """Show LOC harvest statistics."""
    catalog = _load_catalog()

    click.echo("=== LOC Manuscript Catalog ===")
    by_script: dict[str, dict[str, int]] = {}
    for ms in catalog:
        s = ms["script_iso15924"]
        j = ms["john_status"]
        if s not in by_script:
            by_script[s] = {"definite": 0, "possible": 0, "unlikely": 0, "total": 0}
        by_script[s][j] = by_script[s].get(j, 0) + 1
        by_script[s]["total"] += 1

    for s in sorted(by_script):
        d = by_script[s]
        click.echo(
            f"  {s}: {d['total']} total "
            f"({d['definite']} definite, {d['possible']} possible, {d['unlikely']} unlikely)"
        )
    click.echo(f"  TOTAL: {len(catalog)}")

    # Folio estimates
    if _FOLIO_ESTIMATES_PATH.exists():
        with open(_FOLIO_ESTIMATES_PATH) as f:
            estimates = json.load(f)
        confirmed = sum(1 for e in estimates if e.get("confirmed_page") is not None)
        click.echo("\n=== Folio Estimates ===")
        click.echo(f"  Estimated: {len(estimates)}")
        click.echo(f"  Confirmed: {confirmed}")

    # Harvested files
    output_dir = _get_output_dir()
    loc_dir = output_dir / "loc"
    if loc_dir.exists():
        harvested = list(loc_dir.glob("*.jpg"))
        click.echo("\n=== Harvested Images ===")
        by_script_h: dict[str, int] = {}
        for p in harvested:
            parts = p.stem.split("_")
            if len(parts) >= 3:
                sc = parts[2]
                by_script_h[sc] = by_script_h.get(sc, 0) + 1
        for s in sorted(by_script_h):
            click.echo(f"  {s}: {by_script_h[s]}")
        click.echo(f"  TOTAL: {len(harvested)}")


if __name__ == "__main__":
    cli()
