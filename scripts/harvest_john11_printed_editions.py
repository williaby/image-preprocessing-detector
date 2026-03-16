#!/usr/bin/env python3
"""Harvest John 1:1 printed edition images from open-access sources.

Multi-source download CLI for building the john11-printed-editions dataset.
Only harvests from institutions with verified open licenses (Phase 1).

Expected yield (Phase 1 verified-only): ~300-500 images across 22 scripts.

Usage:
    # Dry run — check API connectivity and expected yield
    uv run python scripts/harvest_john11_printed_editions.py harvest-internet-archive --dry-run

    # Download from verified PD sources
    uv run python scripts/harvest_john11_printed_editions.py harvest-internet-archive
    uv run python scripts/harvest_john11_printed_editions.py harvest-wikimedia
    uv run python scripts/harvest_john11_printed_editions.py harvest-gallica

    # Show registry stats
    uv run python scripts/harvest_john11_printed_editions.py stats

Requires:
    requests>=2.28.0   (already in base deps)
    Pillow>=10.0.0     (already in base deps)
    PyYAML>=6.0        (already in base deps)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import click
import requests
import yaml

from harvest_utils import append_entry as _append_entry
from harvest_utils import compute_sha256 as _compute_sha256
from harvest_utils import load_registry as _load_registry

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_CATALOG_PATH = _PROJECT_ROOT / "config" / "john11_printed_editions_catalog.yaml"
_LICENSE_PATH = _PROJECT_ROOT / "config" / "john11_printed_editions_licenses.yaml"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_printed_editions_registry.jsonl"
)
_DEFAULT_OUTPUT_DIR = Path(
    "/mnt/e/image_detection/01_base_data/printed_editions/john11"
)
# Local fallback when E: drive is unavailable
_LOCAL_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "john11-printed-editions"
)

# Minimum image dimension filter — reject images smaller than this in either
# dimension.  Website UI scraping artifacts (logos, icons, badges) are typically
# well below this threshold.  Manuscript/printed edition pages should be
# substantially larger.
MIN_IMAGE_DIMENSION = 200  # pixels

# MediaWiki API
_WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# Wikimedia categories for printed Bible images by script
_WIKIMEDIA_CATEGORIES: dict[str, list[str]] = {
    "Latn": [
        "Category:Gutenberg_Bible",
        "Category:Incunabula",
        "Category:Printed_Bibles",
        "Category:King_James_Version",
        "Category:Luther_Bible",
        "Category:Printed_editions_of_the_Vulgate",
    ],
    "Grek": [
        "Category:Greek_New_Testament",
        "Category:Textus_Receptus",
    ],
    "Cyrl": [
        "Category:Ostrog_Bible",
        "Category:Russian_Bible",
    ],
    "Goth": [
        "Category:Codex_Argenteus",
    ],
}

_USER_AGENT = (
    "John11PrintedEditionsHarvester/1.0 "
    "(https://github.com/ByronWilliamsCPA/image_detection; dataset research)"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry helper for rate-limited APIs
# ---------------------------------------------------------------------------


def _fetch_json_with_retry(
    url: str,
    *,
    max_retries: int = 4,
    initial_delay: float = 10.0,
) -> dict[str, Any] | None:
    """Fetch JSON from a URL with exponential backoff on 429/5xx errors."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries:
                    click.echo(
                        f"    [RETRY] {resp.status_code}, waiting {delay:.0f}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                click.echo(
                    f"    [ERROR] {resp.status_code} after {max_retries} retries"
                )
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt < max_retries:
                click.echo(f"    [RETRY] {exc}, waiting {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
                continue
            click.echo(f"    [ERROR] Failed after {max_retries} retries: {exc}")
            return None
    return None


# ---------------------------------------------------------------------------
# Shared helpers (identical pattern to harvest_john11_manuscripts.py)
# ---------------------------------------------------------------------------


# _compute_sha256, _load_registry, _append_entry imported from harvest_utils


def _build_entry(
    filepath: Path,
    source_url: str,
    source_institution: str,
    catalog_number: int | None,
    license_str: str,
    acquisition_method: str,
    output_dir: Path,
    script_iso15924: str,
) -> dict[str, Any]:
    """Build a registry entry for a downloaded image."""
    from PIL import Image

    sha256 = _compute_sha256(filepath)
    rel_path = str(filepath.relative_to(output_dir))

    with Image.open(filepath) as img:
        dims = [img.width, img.height]

    return {
        "sample_id": str(uuid.uuid4()),
        "sha256": sha256,
        "source_path": rel_path,
        "source_url": source_url,
        "source_institution": source_institution,
        "catalog_number": catalog_number,
        "license": license_str,
        "script_iso15924": script_iso15924,
        "registered_date": str(date.today()),
        "original_dimensions": dims,
        "acquisition_method": acquisition_method,
    }


def _download_image(
    url: str,
    output_path: Path,
    *,
    sha_set: set[str],
    registry_path: Path,
    source_institution: str,
    catalog_number: int | None,
    license_str: str,
    acquisition_method: str,
    output_dir: Path,
    script_iso15924: str,
    dry_run: bool = False,
    rate_limit: float = 1.0,
) -> bool:
    """Download an image, register it, and return True if successful.

    Skips if SHA256 already in registry (dedup). Returns False on skip/error.
    """
    if dry_run:
        click.echo(f"  [DRY RUN] Would download: {url}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()

        with output_path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=65_536):
                fh.write(chunk)

        # Verify it's a valid image before registering
        try:
            from PIL import Image

            with Image.open(output_path) as img:
                img.verify()
        except Exception:
            click.echo(f"  [SKIP] Invalid image: {output_path.name}")
            output_path.unlink()
            return False

        # Reject images below minimum dimension (website UI artifacts, icons)
        from PIL import Image

        with Image.open(output_path) as img:
            if min(img.width, img.height) < MIN_IMAGE_DIMENSION:
                click.echo(
                    f"  [SKIP] Below min dimension ({img.width}x{img.height} "
                    f"< {MIN_IMAGE_DIMENSION}px): {output_path.name}"
                )
                output_path.unlink()
                return False

        sha256 = _compute_sha256(output_path)
        if sha256 in sha_set:
            click.echo(f"  [SKIP] Duplicate SHA256: {output_path.name}")
            output_path.unlink()
            return False

        entry = _build_entry(
            output_path,
            url,
            source_institution,
            catalog_number,
            license_str,
            acquisition_method,
            output_dir,
            script_iso15924,
        )
        _append_entry(entry, registry_path)
        sha_set.add(sha256)
        click.echo(f"  [OK] {output_path.name} ({entry['original_dimensions']})")

        if rate_limit > 0:
            time.sleep(rate_limit)
        return True

    except requests.RequestException as exc:
        click.echo(f"  [ERROR] {url}: {exc}", err=True)
        if output_path.exists():
            output_path.unlink()
        return False
    except Exception as exc:
        click.echo(f"  [ERROR] Processing {output_path.name}: {exc}", err=True)
        if output_path.exists():
            output_path.unlink()
        return False


def _load_catalog() -> dict[int, dict[str, Any]]:
    """Load the printed editions catalog YAML."""
    with _CATALOG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _load_licenses() -> dict[str, dict[str, Any]]:
    """Load the source license verification YAML."""
    with _LICENSE_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _extract_image_url_from_canvas(canvas: dict[str, Any]) -> str | None:
    """Extract the best image URL from an IIIF canvas (v2 or v3)."""
    # IIIF v2
    images = canvas.get("images", [])
    for img in images:
        resource = img.get("resource", {})
        url = resource.get("@id", "")
        if url:
            if url.endswith("/info.json"):
                url = url.replace("/info.json", "/full/full/0/default.jpg")
            return url
        service = resource.get("service", {})
        if isinstance(service, list):
            service = service[0] if service else {}
        service_id = service.get("@id", "")
        if service_id:
            return f"{service_id}/full/full/0/default.jpg"

    # IIIF v3
    items = canvas.get("items", [])
    for anno_page in items:
        for anno in anno_page.get("items", []):
            body = anno.get("body", {})
            url = body.get("id", "")
            if url:
                return url
            service = body.get("service", [])
            if isinstance(service, list) and service:
                s_id = service[0].get("id", "")
                if s_id:
                    return f"{s_id}/full/max/0/default.jpg"

    return None


def _resolve_output_dir(output_dir: Path) -> Path:
    """Use E: drive if available, otherwise local fallback."""
    if output_dir.parent.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    click.echo(
        f"[INFO] E: drive not available, using local: {_LOCAL_OUTPUT_DIR}",
        err=True,
    )
    _LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return _LOCAL_OUTPUT_DIR


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=_DEFAULT_OUTPUT_DIR,
    show_default=True,
    help="Base directory for downloaded images.",
)
@click.option(
    "--registry",
    type=click.Path(path_type=Path),
    default=_REGISTRY_PATH,
    show_default=True,
    help="Path to the JSONL registry file.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, output_dir: Path, registry: Path, verbose: bool) -> None:
    """Harvest John 1:1 printed edition images from open-access sources."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = _resolve_output_dir(output_dir)
    ctx.obj["registry"] = registry


# ---------------------------------------------------------------------------
# harvest-internet-archive (PRIMARY — highest yield source)
# ---------------------------------------------------------------------------


def _get_ia_page_urls(ia_id: str, max_pages: int) -> list[str]:
    """Fetch page image URLs from an IA item's IIIF manifest.

    IA serves scanned book pages via IIIF v3 manifests at:
      https://iiif.archive.org/iiif/{ia_id}/manifest.json

    Each canvas body.id contains a direct JPEG URL for the page.
    """
    manifest_url = f"https://iiif.archive.org/iiif/{ia_id}/manifest.json"
    try:
        resp = requests.get(
            manifest_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=60,
        )
        resp.raise_for_status()
        manifest = resp.json()
    except requests.RequestException as exc:
        logger.warning("IIIF manifest fetch failed for %s: %s", ia_id, exc)
        return []

    urls: list[str] = []

    # IIIF v3 (IA default)
    for item in manifest.get("items", []):
        for anno_page in item.get("items", []):
            for anno in anno_page.get("items", []):
                body = anno.get("body", {})
                url = body.get("id", "")
                if url and url.endswith((".jpg", ".png", ".tif")):
                    urls.append(url)

    # IIIF v2 fallback
    if not urls:
        for seq in manifest.get("sequences", []):
            for canvas in seq.get("canvases", []):
                img_url = _extract_image_url_from_canvas(canvas)
                if img_url:
                    urls.append(img_url)

    if 0 < max_pages < len(urls):
        urls = urls[:max_pages]

    return urls


@cli.command("harvest-internet-archive")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=5,
    show_default=True,
    help="Max page scans to download per IA item (0 = all).",
)
@click.option(
    "--scripts",
    type=str,
    default="all",
    show_default=True,
    help="Comma-separated ISO 15924 codes to harvest, or 'all'.",
)
@click.pass_context
def harvest_internet_archive(
    ctx: click.Context, dry_run: bool, max_pages: int, scripts: str
) -> None:
    """Harvest from Internet Archive via IIIF manifests.

    Uses the IA IIIF v3 manifest API to enumerate page images for each
    catalog item. Only items with verified PD status are harvested.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    catalog = _load_catalog()

    # Filter catalog to IA Phase 1 items
    ia_items = [
        (cat_num, entry)
        for cat_num, entry in catalog.items()
        if entry.get("harvest_source") == "harvest-internet-archive"
        and entry.get("harvest_phase") == 1
        and entry.get("ia_item_id")
    ]

    # Filter by script if specified
    if scripts != "all":
        target_scripts = {s.strip() for s in scripts.split(",")}
        ia_items = [
            (n, e) for n, e in ia_items if e["script_iso15924"] in target_scripts
        ]

    click.echo(f"Found {len(ia_items)} IA items to harvest.")
    total_downloaded = 0

    for cat_num, entry in ia_items:
        ia_id = entry["ia_item_id"]
        name = entry["edition_name"]
        script_code = entry["script_iso15924"]
        license_str = entry.get("license", "public_domain")

        subdir = output_dir / "internet_archive" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        click.echo(f"\n[{cat_num}] {name} ({ia_id}) — {script_code}")

        page_urls = _get_ia_page_urls(ia_id, max_pages)
        click.echo(f"  Found {len(page_urls)} pages via IIIF manifest")

        if not page_urls:
            click.echo("  [SKIP] No pages found in IIIF manifest")
            continue

        if dry_run:
            for i, url in enumerate(page_urls[:5]):
                click.echo(f"    [DRY RUN] page {i}: {url[:100]}...")
            if len(page_urls) > 5:
                click.echo(f"    ... and {len(page_urls) - 5} more")
            continue

        for i, url in enumerate(page_urls):
            out_path = subdir / f"{ia_id}_page_{i:04d}.jpg"

            ok = _download_image(
                url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="internet_archive",
                catalog_number=cat_num,
                license_str=license_str,
                acquisition_method="ia_iiif_manifest",
                output_dir=output_dir,
                script_iso15924=script_code,
                rate_limit=0.5,
            )
            if ok:
                total_downloaded += 1

    click.echo(f"\nInternet Archive harvest complete: {total_downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-wikimedia
# ---------------------------------------------------------------------------


@cli.command("harvest-wikimedia")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--rate-limit",
    type=float,
    default=1.0,
    show_default=True,
    help="Seconds between requests (Wikimedia etiquette).",
)
@click.option(
    "--max-images",
    type=int,
    default=0,
    help="Maximum images to download per script (0 = unlimited).",
)
@click.option(
    "--scripts",
    type=str,
    default="all",
    show_default=True,
    help="Comma-separated ISO 15924 codes to harvest, or 'all'.",
)
@click.pass_context
def harvest_wikimedia(
    ctx: click.Context,
    dry_run: bool,
    rate_limit: float,
    max_images: int,
    scripts: str,
) -> None:
    """Harvest from Wikimedia Commons categories (~20-50 images).

    Uses the MediaWiki API to enumerate files in printed Bible categories.
    Only CC0/CC-BY/PD images are downloaded.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    if scripts == "all":
        target_scripts = list(_WIKIMEDIA_CATEGORIES.keys())
    else:
        target_scripts = [s.strip() for s in scripts.split(",")]

    total_downloaded = 0
    total_skipped = 0

    for script_code in target_scripts:
        categories = _WIKIMEDIA_CATEGORIES.get(script_code, [])
        if not categories:
            click.echo(f"\n[{script_code}] No Wikimedia categories defined, skipping.")
            continue

        click.echo(f"\n[{script_code}] Searching {len(categories)} categories...")
        script_downloaded = 0

        subdir = output_dir / "wikimedia" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        seen_titles: set[str] = set()

        for category in categories:
            params: dict[str, Any] = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmtype": "file",
                "cmlimit": 50,
                "format": "json",
            }

            while True:
                try:
                    resp = session.get(_WIKIMEDIA_API, params=params, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                except requests.RequestException as exc:
                    click.echo(f"  [ERROR] {category}: {exc}", err=True)
                    break

                members = data.get("query", {}).get("categorymembers", [])

                for member in members:
                    title = member.get("title", "")
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    if 0 < max_images <= script_downloaded:
                        break

                    # Get file info (URL + license)
                    file_params: dict[str, Any] = {
                        "action": "query",
                        "titles": title,
                        "prop": "imageinfo",
                        "iiprop": "url|extmetadata|size",
                        "iiurlwidth": 4000,
                        "format": "json",
                    }

                    try:
                        file_resp = session.get(
                            _WIKIMEDIA_API, params=file_params, timeout=30
                        )
                        file_resp.raise_for_status()
                        file_data = file_resp.json()
                    except requests.RequestException:
                        continue

                    pages = file_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        ii = page.get("imageinfo", [{}])[0]
                        url = ii.get("url", "")
                        if not url:
                            continue

                        # Check license
                        ext_meta = ii.get("extmetadata", {})
                        license_val = ext_meta.get("LicenseShortName", {}).get(
                            "value", ""
                        )
                        license_lower = license_val.lower()

                        # Only accept CC0, PD, CC-BY
                        if not any(
                            tag in license_lower
                            for tag in (
                                "cc0",
                                "public domain",
                                "pd",
                                "cc-by-4",
                                "cc-by-3",
                                "cc-by-2",
                                "cc by 4",
                                "cc by 3",
                            )
                        ):
                            total_skipped += 1
                            continue

                        # Only image files
                        if not url.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".tif", ".tiff")
                        ):
                            continue

                        safe_name = (
                            title.replace("File:", "")
                            .replace(" ", "_")
                            .replace("/", "_")
                        )
                        if len(safe_name) > 200:
                            safe_name = safe_name[:200]
                        out_path = subdir / safe_name

                        # Map license to canonical form
                        lic_str = "public_domain"
                        if "cc0" in license_lower:
                            lic_str = "CC0"
                        elif "cc-by" in license_lower or "cc by" in license_lower:
                            lic_str = "CC-BY-4.0"

                        ok = _download_image(
                            url,
                            out_path,
                            sha_set=sha_set,
                            registry_path=registry_path,
                            source_institution="wikimedia_commons",
                            catalog_number=None,
                            license_str=lic_str,
                            acquisition_method="mediawiki_api",
                            output_dir=output_dir,
                            script_iso15924=script_code,
                            dry_run=dry_run,
                            rate_limit=rate_limit,
                        )
                        if ok:
                            script_downloaded += 1
                            total_downloaded += 1

                if 0 < max_images <= script_downloaded:
                    break

                cont = data.get("continue", {})
                if "cmcontinue" not in cont:
                    break
                params["cmcontinue"] = cont["cmcontinue"]

        click.echo(f"  [{script_code}] Downloaded: {script_downloaded}")

    click.echo(
        f"\nWikimedia harvest complete: {total_downloaded} downloaded, "
        f"{total_skipped} skipped (license)."
    )


# ---------------------------------------------------------------------------
# harvest-gallica
# ---------------------------------------------------------------------------


@cli.command("harvest-gallica")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=5,
    show_default=True,
    help="Max canvases to download per manifest.",
)
@click.pass_context
def harvest_gallica(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from BnF/Gallica IIIF manifests (~10-20 images, PD pre-1850).

    Downloads high-resolution page images from Gallica IIIF endpoints.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    catalog = _load_catalog()

    # Filter catalog to Gallica items
    gallica_items = [
        (cat_num, entry)
        for cat_num, entry in catalog.items()
        if entry.get("harvest_source") == "harvest-gallica"
        and entry.get("harvest_phase") == 1
        and entry.get("iiif_manifest_url")
    ]

    if not gallica_items:
        click.echo(
            "No Gallica items in catalog (Phase 1). Add items with iiif_manifest_url."
        )
        return

    total_downloaded = 0

    for cat_num, entry in gallica_items:
        manifest_url = entry["iiif_manifest_url"]
        name = entry["edition_name"]
        script_code = entry["script_iso15924"]
        license_str = entry.get("license", "public_domain")

        subdir = output_dir / "gallica" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        click.echo(f"\n[{cat_num}] {name}")

        try:
            resp = requests.get(
                manifest_url,
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            manifest = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            continue

        canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
        if not canvases:
            canvases = manifest.get("items", [])

        click.echo(f"  Found {len(canvases)} canvases")

        page_count = 0
        for i, canvas in enumerate(canvases):
            if 0 < max_pages <= page_count:
                break

            img_url = _extract_image_url_from_canvas(canvas)
            if not img_url:
                continue

            out_path = subdir / f"gallica_{cat_num}_{i:04d}.jpg"

            ok = _download_image(
                img_url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="bnf_gallica",
                catalog_number=cat_num,
                license_str=license_str,
                acquisition_method="iiif_manifest",
                output_dir=output_dir,
                script_iso15924=script_code,
                dry_run=dry_run,
                rate_limit=1.5,
            )
            if ok:
                page_count += 1
                total_downloaded += 1

    click.echo(f"\nGallica harvest complete: {total_downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-loc (Library of Congress)
# ---------------------------------------------------------------------------


@cli.command("harvest-loc")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=10,
    show_default=True,
    help="Max pages to download per LOC item (0 = all).",
)
@click.pass_context
def harvest_loc(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from Library of Congress digital collections.

    Uses the LOC JSON API + IIIF tile server for page images.
    LOC items are public domain (no known restrictions).
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    catalog = _load_catalog()

    # Filter catalog to LOC Phase 1 items
    loc_items = [
        (cat_num, entry)
        for cat_num, entry in catalog.items()
        if entry.get("harvest_source") == "harvest-loc"
        and entry.get("harvest_phase") == 1
        and entry.get("loc_item_id")
    ]

    if not loc_items:
        click.echo("No LOC items in catalog (Phase 1).")
        return

    click.echo(f"Found {len(loc_items)} LOC items to harvest.")
    total_downloaded = 0

    for item_idx, (cat_num, entry) in enumerate(loc_items):
        if item_idx > 0:
            click.echo("  [WAIT] 15s between LOC items...")
            time.sleep(15.0)
        loc_id = entry["loc_item_id"]
        resource_id = entry.get("loc_resource_id", "")
        name = entry["edition_name"]
        script_code = entry["script_iso15924"]
        license_str = entry.get("license", "public_domain")

        subdir = output_dir / "loc" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        click.echo(f"\n[{cat_num}] {name} (LOC {loc_id}) — {script_code}")

        # Get item metadata to find resources (with retry for rate limiting)
        item_url = f"https://www.loc.gov/item/{loc_id}/?fo=json"
        item_data = _fetch_json_with_retry(item_url, initial_delay=15.0)
        if item_data is None:
            click.echo("  [SKIP] Could not fetch item metadata")
            continue

        # Find resource URL and page count
        resources = item_data.get("resources", [])
        if not resources:
            # Try alternate structure
            resources = item_data.get("item", {}).get("resources", [])

        if not resources:
            click.echo("  [SKIP] No resources found in item metadata")
            # Fallback: try direct resource ID with sequential pages
            if resource_id:
                click.echo(f"  Trying direct resource: {resource_id}")
                page_count = 0
                for page_num in range(1, max_pages + 1 if max_pages > 0 else 100):
                    # LOC IIIF tile server format
                    img_url = (
                        f"https://tile.loc.gov/image-services/iiif/"
                        f"service:{resource_id}:{page_num:04d}"
                        f"/full/pct:100/0/default.jpg"
                    )
                    out_path = subdir / f"loc_{cat_num}_{page_num:04d}.jpg"

                    ok = _download_image(
                        img_url,
                        out_path,
                        sha_set=sha_set,
                        registry_path=registry_path,
                        source_institution="library_of_congress",
                        catalog_number=cat_num,
                        license_str=license_str,
                        acquisition_method="loc_iiif_tile",
                        output_dir=output_dir,
                        script_iso15924=script_code,
                        dry_run=dry_run,
                        rate_limit=2.0,
                    )
                    if ok:
                        page_count += 1
                        total_downloaded += 1
                    elif not dry_run:
                        # Stop on first failure (end of pages)
                        break
                click.echo(f"  Downloaded {page_count} pages via direct resource")
            continue

        for resource in resources:
            res_url = resource.get("url", "")
            page_count_total = resource.get("files", 1)
            if isinstance(page_count_total, list):
                page_count_total = len(page_count_total)

            click.echo(f"  Resource: {res_url} ({page_count_total} pages)")

            if dry_run:
                click.echo(f"    [DRY RUN] Would download up to {max_pages} pages")
                continue

            # Try to get page file URLs from resource JSON
            res_json_url = f"https://www.loc.gov{res_url}?fo=json"
            time.sleep(5.0)  # Respect LOC rate limits between resources
            res_data = _fetch_json_with_retry(res_json_url, initial_delay=15.0)
            if res_data is None:
                continue

            # LOC resource JSON has a "files" key with nested arrays
            file_groups = res_data.get("files", [])
            page_count = 0
            for group in file_groups:
                if 0 < max_pages <= page_count:
                    break
                if not isinstance(group, list):
                    continue
                # Each group is a list of file format options for one page
                # Pick the largest JPEG
                best_url = ""
                best_size = 0
                for file_info in group:
                    if file_info.get("mimetype", "") == "image/jpeg":
                        size = file_info.get("size", 0)
                        if isinstance(size, str):
                            try:
                                size = int(size)
                            except ValueError:
                                size = 0
                        if size > best_size:
                            best_size = size
                            best_url = file_info.get("url", "")

                if not best_url:
                    continue

                # Ensure full URL
                if best_url.startswith("//"):
                    best_url = "https:" + best_url
                elif best_url.startswith("/"):
                    best_url = "https://www.loc.gov" + best_url

                out_path = subdir / f"loc_{cat_num}_{page_count:04d}.jpg"
                ok = _download_image(
                    best_url,
                    out_path,
                    sha_set=sha_set,
                    registry_path=registry_path,
                    source_institution="library_of_congress",
                    catalog_number=cat_num,
                    license_str=license_str,
                    acquisition_method="loc_json_api",
                    output_dir=output_dir,
                    script_iso15924=script_code,
                    dry_run=dry_run,
                    rate_limit=2.0,
                )
                if ok:
                    page_count += 1
                    total_downloaded += 1

    click.echo(f"\nLOC harvest complete: {total_downloaded} downloaded.")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@cli.command("stats")
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show registry statistics by script, institution, technology, and license."""
    registry_path: Path = ctx.obj["registry"]
    _, entries = _load_registry(registry_path)

    if not entries:
        click.echo("Registry is empty.")
        return

    click.echo(f"Total images: {len(entries)}")

    by_script: dict[str, int] = {}
    by_inst: dict[str, int] = {}
    by_license: dict[str, int] = {}
    for e in entries:
        script = e.get("script_iso15924", "unknown")
        by_script[script] = by_script.get(script, 0) + 1
        inst = e.get("source_institution", "unknown")
        by_inst[inst] = by_inst.get(inst, 0) + 1
        lic = e.get("license", "unknown")
        by_license[lic] = by_license.get(lic, 0) + 1

    click.echo("\nBy script:")
    for script, count in sorted(by_script.items(), key=lambda x: -x[1]):
        click.echo(f"  {script}: {count}")

    click.echo("\nBy institution:")
    for inst, count in sorted(by_inst.items(), key=lambda x: -x[1]):
        click.echo(f"  {inst}: {count}")

    click.echo("\nBy license:")
    for lic, count in sorted(by_license.items(), key=lambda x: -x[1]):
        click.echo(f"  {lic}: {count}")

    # Catalog coverage
    catalog = _load_catalog()
    mapped_cats = {e.get("catalog_number") for e in entries if e.get("catalog_number")}
    click.echo(
        f"\nCatalog items harvested: {len(mapped_cats)}/{len(catalog)} "
        f"({len(mapped_cats) * 100 // max(len(catalog), 1)}%)"
    )


# ---------------------------------------------------------------------------
# verify-licenses
# ---------------------------------------------------------------------------


@cli.command("verify-licenses")
@click.pass_context
def verify_licenses(ctx: click.Context) -> None:
    """Show license verification status for all institutions."""
    licenses = _load_licenses()

    verified = []
    unverified = []
    blocked = []

    for key, info in licenses.items():
        name = info.get("display_name", key)
        status = info.get("license_verified")
        if status is True:
            verified.append((name, info))
        elif status is False:
            unverified.append((name, info))
        else:
            blocked.append((name, info))

    click.echo("VERIFIED (safe to harvest):")
    for name, info in verified:
        click.echo(
            f"  {name}: {info.get('license', '?')} | Scripts: {info.get('scripts', [])}"
        )

    click.echo(f"\nNEEDS VERIFICATION ({len(unverified)} institutions):")
    for name, info in unverified:
        click.echo(f"  {name}: {info.get('license', '?')}")

    if blocked:
        click.echo(f"\nBLOCKED ({len(blocked)} institutions):")
        for name, info in blocked:
            click.echo(f"  {name}: {info.get('notes', '?')}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    cli()
