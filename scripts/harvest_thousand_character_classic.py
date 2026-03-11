#!/usr/bin/env python3
"""Harvest Thousand Character Classic (千字文) images from open-access sources.

Multi-source download CLI for building the thousand-character-classic dataset.
Targets Tier 1 (API/IIIF, explicit open license) and Tier 2 (open access) sources.

Expected yield: 175-290 images from 6 source institutions.

Usage:
    # Dry run — check API connectivity and expected yield
    uv run python scripts/harvest_thousand_character_classic.py harvest-wikimedia --dry-run

    # Download from all Tier 1 sources
    uv run python scripts/harvest_thousand_character_classic.py harvest-wikimedia
    uv run python scripts/harvest_thousand_character_classic.py harvest-met
    uv run python scripts/harvest_thousand_character_classic.py harvest-iiif

    # Show registry stats
    uv run python scripts/harvest_thousand_character_classic.py stats

Requires:
    requests>=2.28.0   (already in base deps)
    Pillow>=10.0.0     (already in base deps)
    imagehash>=4.3.1   (optional: ood extra)
    PyYAML>=6.0        (already in base deps)
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
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_CATALOG_PATH = _PROJECT_ROOT / "config" / "thousand_character_classic_catalog.yaml"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "thousand_character_classic_registry.jsonl"
)
_DEFAULT_OUTPUT_DIR = Path("/mnt/e/image_detection/01_base_data/calligraphy/thousand-character-classic")

# MediaWiki API
_WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
_WIKIMEDIA_CATEGORIES = [
    "Category:Thousand_characters_classical-Qianziwen",
    "Category:Thousand_Character_Classic_in_Regular_and_Cursive_Scripts_by_Zhiyong",
]
_USER_AGENT = (
    "ThousandCharClassicHarvester/1.0 "
    "(https://github.com/ByronWilliamsCPA/image_detection; dataset research)"
)

# Met Museum API
_MET_API = "https://collectionapi.metmuseum.org/public/collection/v1/objects"
_MET_OBJECT_IDS = [78125, 671036]

# NPM Taipei collection IDs (from catalog #13-25)
_NPM_DETAIL_IDS = [
    1932, 593, 13915, 1524, 17583, 17585, 17635, 19189, 2583, 2582, 2520, 779, 22100,
]

# NDL IIIF PIDs (from catalog #47-52)
_NDL_PIDS = [853547, 910125, 1181692, 853440, 781828, 853669]

# Kyoto U IIIF items (from catalog #53-55)
_KYOTO_ITEMS = ["rb00011078", "rb00009713", "rb00012112"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    hasher = hashlib.sha256()
    with filepath.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_registry(registry_path: Path) -> tuple[set[str], list[dict[str, Any]]]:
    """Load existing registry entries, returning (sha256_set, entries_list)."""
    sha_set: set[str] = set()
    entries: list[dict[str, Any]] = []
    if registry_path.exists():
        with registry_path.open("r") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                sha_set.add(entry["sha256"])
                entries.append(entry)
    return sha_set, entries


def _append_entry(entry: dict[str, Any], registry_path: Path) -> None:
    """Append a single JSONL entry to the registry."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _build_entry(
    filepath: Path,
    source_url: str,
    source_institution: str,
    catalog_number: int | None,
    license_str: str,
    acquisition_method: str,
    output_dir: Path,
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
    """Load the 74-item catalog YAML."""
    with _CATALOG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


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
    """Harvest Thousand Character Classic images from open-access sources."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = output_dir
    ctx.obj["registry"] = registry


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
    help="Maximum images to download (0 = unlimited).",
)
@click.pass_context
def harvest_wikimedia(
    ctx: click.Context, dry_run: bool, rate_limit: float, max_images: int
) -> None:
    """Harvest from Wikimedia Commons categories (~100-147 images).

    Uses the MediaWiki API to enumerate files in the Qianziwen category
    and subcategories. Downloads full-resolution originals.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "wikimedia"
    subdir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    downloaded = 0
    skipped = 0

    # Collect all file titles from categories (with subcategory recursion)
    all_files: list[dict[str, Any]] = []
    visited_categories: set[str] = set()

    def _enumerate_category(cat_title: str, depth: int = 0) -> None:
        """Recursively enumerate files and subcategories."""
        if cat_title in visited_categories or depth > 3:
            return
        visited_categories.add(cat_title)

        click.echo(f"Enumerating {cat_title} (depth={depth})...")
        cmcontinue = None

        while True:
            params: dict[str, Any] = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat_title,
                "cmlimit": 500,
                "format": "json",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            resp = session.get(_WIKIMEDIA_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for member in data.get("query", {}).get("categorymembers", []):
                ns = member.get("ns", 0)
                title = member.get("title", "")
                if ns == 6:  # File namespace
                    all_files.append(member)
                elif ns == 14:  # Category namespace
                    _enumerate_category(title, depth + 1)

            cont = data.get("continue", {})
            cmcontinue = cont.get("cmcontinue")
            if not cmcontinue:
                break

            time.sleep(0.5)

    for cat in _WIKIMEDIA_CATEGORIES:
        _enumerate_category(cat)

    click.echo(f"\nFound {len(all_files)} files across {len(visited_categories)} categories.")

    if dry_run:
        for f in all_files[:20]:
            click.echo(f"  {f.get('title', 'unknown')}")
        if len(all_files) > 20:
            click.echo(f"  ... and {len(all_files) - 20} more")
        click.echo(f"\n[DRY RUN] Would download up to {len(all_files)} files.")
        return

    # Get image info and download each file
    for file_info in all_files:
        if 0 < max_images <= downloaded:
            click.echo(f"Reached max_images={max_images}, stopping.")
            break

        title = file_info.get("title", "")

        # Get image URL via imageinfo query
        params = {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "format": "json",
        }
        try:
            resp = session.get(_WIKIMEDIA_API, params=params, timeout=30)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] imageinfo for {title}: {exc}", err=True)
            time.sleep(rate_limit)
            continue

        for page in pages.values():
            ii_list = page.get("imageinfo", [])
            if not ii_list:
                continue
            ii = ii_list[0]
            img_url = ii.get("url", "")
            mime = ii.get("mime", "")

            # Skip non-image files (PDFs, SVGs, etc.)
            if not mime.startswith("image/"):
                click.echo(f"  [SKIP] Non-image: {title} ({mime})")
                skipped += 1
                continue

            # Determine file extension
            ext = ".jpg"
            if "png" in mime:
                ext = ".png"
            elif "tiff" in mime:
                ext = ".tif"
            elif "gif" in mime:
                ext = ".gif"

            # Sanitize filename
            safe_name = (
                title.replace("File:", "")
                .replace(" ", "_")
                .replace("/", "_")[:200]
            )
            if not safe_name.lower().endswith(ext):
                safe_name += ext

            out_path = subdir / safe_name

            ok = _download_image(
                img_url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="wikimedia",
                catalog_number=None,  # Will be mapped post-hoc
                license_str="public_domain",
                acquisition_method="mediawiki_api",
                output_dir=output_dir,
                rate_limit=rate_limit,
            )
            if ok:
                downloaded += 1
            else:
                skipped += 1

    click.echo(f"\nWikimedia harvest complete: {downloaded} downloaded, {skipped} skipped.")


# ---------------------------------------------------------------------------
# harvest-met
# ---------------------------------------------------------------------------


@cli.command("harvest-met")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_met(ctx: click.Context, dry_run: bool) -> None:
    """Harvest from Metropolitan Museum Open Access API (~20 images, CC0).

    Downloads primary and additional images for Qianziwen objects.
    Object 78125 (Zhan Jingfeng) has 19 section images.
    Object 671036 (Ike no Taiga) is a single hanging scroll.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "met"
    subdir.mkdir(parents=True, exist_ok=True)

    catalog_map = {78125: 34, 671036: 35}
    downloaded = 0

    for obj_id in _MET_OBJECT_IDS:
        click.echo(f"\nFetching Met object {obj_id}...")
        try:
            resp = requests.get(
                f"{_MET_API}/{obj_id}",
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            obj = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            continue

        title = obj.get("title", f"object_{obj_id}")
        click.echo(f"  Title: {title}")

        # Collect all image URLs
        image_urls: list[str] = []
        primary = obj.get("primaryImage", "")
        if primary:
            image_urls.append(primary)
        additional = obj.get("additionalImages", [])
        image_urls.extend(additional)

        click.echo(f"  Found {len(image_urls)} images")

        if dry_run:
            for url in image_urls[:5]:
                click.echo(f"    [DRY RUN] {url}")
            if len(image_urls) > 5:
                click.echo(f"    ... and {len(image_urls) - 5} more")
            continue

        for i, url in enumerate(image_urls):
            ext = Path(url.split("?")[0]).suffix or ".jpg"
            filename = f"met_{obj_id}_{i:03d}{ext}"
            out_path = subdir / filename

            ok = _download_image(
                url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="met_museum",
                catalog_number=catalog_map.get(obj_id),
                license_str="CC0",
                acquisition_method="met_open_access_api",
                output_dir=output_dir,
                rate_limit=0.5,
            )
            if ok:
                downloaded += 1

    click.echo(f"\nMet harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-iiif
# ---------------------------------------------------------------------------


@cli.command("harvest-iiif")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--source",
    type=click.Choice(["ndl", "kyoto", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Which IIIF source to harvest.",
)
@click.option(
    "--max-pages",
    type=int,
    default=0,
    help="Max pages per volume (0 = all).",
)
@click.pass_context
def harvest_iiif(
    ctx: click.Context, dry_run: bool, source: str, max_pages: int
) -> None:
    """Harvest from IIIF sources: NDL (~30-60 images) and Kyoto U (~10-30 images).

    Parses IIIF Presentation API v2/v3 manifests to extract canvas image URLs.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    downloaded = 0

    ndl_catalog_map = {
        853547: 47, 910125: 48, 1181692: 49,
        853440: 50, 781828: 51, 853669: 52,
    }
    kyoto_catalog_map = {
        "rb00011078": 53, "rb00009713": 54, "rb00012112": 55,
    }

    def _harvest_iiif_manifest(
        manifest_url: str,
        inst_name: str,
        inst_subdir: str,
        catalog_num: int | None,
        license_str: str,
        item_id: str,
    ) -> int:
        """Parse an IIIF manifest and download all canvas images."""
        count = 0
        subdir = output_dir / inst_subdir
        subdir.mkdir(parents=True, exist_ok=True)

        click.echo(f"\nFetching IIIF manifest: {manifest_url}")
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
            return 0

        # Extract canvases (IIIF v2 or v3)
        canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
        if not canvases:
            # Try IIIF v3 format
            canvases = manifest.get("items", [])

        click.echo(f"  Found {len(canvases)} canvases")

        for i, canvas in enumerate(canvases):
            if 0 < max_pages <= i:
                break

            # Extract image URL from canvas
            img_url = _extract_image_url_from_canvas(canvas)
            if not img_url:
                click.echo(f"  [SKIP] No image URL in canvas {i}")
                continue

            if dry_run:
                click.echo(f"  [DRY RUN] Canvas {i}: {img_url[:100]}...")
                count += 1
                continue

            filename = f"{inst_subdir}_{item_id}_{i:04d}.jpg"
            out_path = subdir / filename

            # Try full resolution first; fall back to max 2048px if 403
            urls_to_try = [img_url]
            if "/full/full/" in img_url:
                urls_to_try.append(img_url.replace("/full/full/", "/full/,2048/"))

            ok = False
            for try_url in urls_to_try:
                ok = _download_image(
                    try_url,
                    out_path,
                    sha_set=sha_set,
                    registry_path=registry_path,
                    source_institution=inst_name,
                    catalog_number=catalog_num,
                    license_str=license_str,
                    acquisition_method="iiif_manifest",
                    output_dir=output_dir,
                    rate_limit=1.0,
                )
                if ok:
                    break
            if ok:
                count += 1

        return count

    # NDL
    if source in ("ndl", "all"):
        for pid in _NDL_PIDS:
            manifest_url = f"https://www.dl.ndl.go.jp/api/iiif/{pid}/manifest.json"
            n = _harvest_iiif_manifest(
                manifest_url,
                inst_name="ndl",
                inst_subdir="ndl",
                catalog_num=ndl_catalog_map.get(pid),
                license_str="public_domain",
                item_id=str(pid),
            )
            downloaded += n

    # Kyoto U
    if source in ("kyoto", "all"):
        for item_id in _KYOTO_ITEMS:
            manifest_url = (
                f"https://rmda.kulib.kyoto-u.ac.jp/iiif/{item_id}/manifest.json"
            )
            n = _harvest_iiif_manifest(
                manifest_url,
                inst_name="kyoto_u",
                inst_subdir="kyoto_u",
                catalog_num=kyoto_catalog_map.get(item_id),
                license_str="open_access",
                item_id=item_id,
            )
            downloaded += n

    click.echo(f"\nIIIF harvest complete: {downloaded} downloaded.")


def _extract_image_url_from_canvas(canvas: dict[str, Any]) -> str | None:
    """Extract the best image URL from an IIIF canvas (v2 or v3).

    Attempts full resolution first, falls back to /full/full/ IIIF Image API.
    """
    # IIIF v2: canvas.images[].resource.@id or canvas.images[].resource.service.@id
    images = canvas.get("images", [])
    for img in images:
        resource = img.get("resource", {})
        # Try direct URL first
        url = resource.get("@id", "")
        if url:
            # If URL is an IIIF Image API info.json, convert to full image
            if url.endswith("/info.json"):
                url = url.replace("/info.json", "/full/full/0/default.jpg")
            return url

        # Try service endpoint
        service = resource.get("service", {})
        if isinstance(service, list):
            service = service[0] if service else {}
        service_id = service.get("@id", "")
        if service_id:
            return f"{service_id}/full/full/0/default.jpg"

    # IIIF v3: canvas.items[].items[].body.id
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


# ---------------------------------------------------------------------------
# harvest-npm-taipei
# ---------------------------------------------------------------------------


@cli.command("harvest-npm-taipei")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_npm_taipei(ctx: click.Context, dry_run: bool) -> None:
    """Harvest from National Palace Museum Taipei (CC0/CC BY 4.0, ~13-30 images).

    NPM provides IIIF-compatible digital archive. Attempts to resolve
    collection detail pages to downloadable image URLs.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "npm_taipei"
    subdir.mkdir(parents=True, exist_ok=True)

    catalog = _load_catalog()
    downloaded = 0

    # NPM Taipei detail IDs map to catalog numbers 13-25
    npm_catalog_map = dict(zip(_NPM_DETAIL_IDS, range(13, 26)))

    for detail_id in _NPM_DETAIL_IDS:
        cat_num = npm_catalog_map.get(detail_id)
        cat_entry = catalog.get(cat_num, {})
        calligrapher = cat_entry.get("calligrapher", "unknown")

        click.echo(f"\nNPM Detail/{detail_id}: {calligrapher}")

        # Try IIIF manifest first
        manifest_url = f"https://digitalarchive.npm.gov.tw/Painting/set498/{detail_id}/manifest.json"

        if dry_run:
            click.echo(f"  [DRY RUN] Would try: {manifest_url}")
            click.echo(f"  [DRY RUN] Fallback: direct image API")
            continue

        # Attempt direct image download (NPM image API pattern)
        # NPM provides mid-res (~6MP) at CC BY 4.0
        img_url = f"https://digitalarchive.npm.gov.tw/Image/GetImage?imageId={detail_id}"
        filename = f"npm_{detail_id}_{calligrapher.replace(' ', '_')}.jpg"
        out_path = subdir / filename

        ok = _download_image(
            img_url,
            out_path,
            sha_set=sha_set,
            registry_path=registry_path,
            source_institution="npm_taipei",
            catalog_number=cat_num,
            license_str="CC0",
            acquisition_method="npm_image_api",
            output_dir=output_dir,
            rate_limit=1.5,
        )
        if ok:
            downloaded += 1

    click.echo(f"\nNPM Taipei harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-internet-archive
# ---------------------------------------------------------------------------


@cli.command("harvest-internet-archive")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_internet_archive(ctx: click.Context, dry_run: bool) -> None:
    """Harvest from Internet Archive (catalog #74, 600 PPI Kangxi edition).

    Uses the Internet Archive metadata API to find JP2/JPEG page scans.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "internet_archive"
    subdir.mkdir(parents=True, exist_ok=True)

    ia_id = "chung_27149_hotmail_24"
    metadata_url = f"https://archive.org/metadata/{ia_id}"

    click.echo(f"Fetching Internet Archive metadata: {ia_id}")
    try:
        resp = requests.get(metadata_url, timeout=30)
        resp.raise_for_status()
        metadata = resp.json()
    except requests.RequestException as exc:
        click.echo(f"  [ERROR] {exc}", err=True)
        return

    files = metadata.get("files", [])
    # Filter to image files (JP2 or JPEG page scans)
    image_files = [
        f for f in files
        if f.get("name", "").lower().endswith((".jp2", ".jpg", ".jpeg", ".png", ".tif"))
        and f.get("source", "") != "metadata"
    ]

    click.echo(f"  Found {len(image_files)} image files")

    if dry_run:
        for f in image_files[:10]:
            click.echo(f"  [DRY RUN] {f['name']} ({f.get('size', '?')} bytes)")
        if len(image_files) > 10:
            click.echo(f"  ... and {len(image_files) - 10} more")
        return

    downloaded = 0
    for f in image_files:
        fname = f["name"]
        url = f"https://archive.org/download/{ia_id}/{fname}"
        out_path = subdir / fname.replace("/", "_")

        ok = _download_image(
            url,
            out_path,
            sha_set=sha_set,
            registry_path=registry_path,
            source_institution="internet_archive",
            catalog_number=74,
            license_str="public_domain",
            acquisition_method="ia_download_api",
            output_dir=output_dir,
            rate_limit=0.5,
        )
        if ok:
            downloaded += 1

    click.echo(f"\nInternet Archive harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@cli.command("stats")
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show registry statistics."""
    registry_path: Path = ctx.obj["registry"]
    _, entries = _load_registry(registry_path)

    if not entries:
        click.echo("Registry is empty.")
        return

    click.echo(f"Total images: {len(entries)}")

    # By institution
    by_inst: dict[str, int] = {}
    by_license: dict[str, int] = {}
    for e in entries:
        inst = e.get("source_institution", "unknown")
        by_inst[inst] = by_inst.get(inst, 0) + 1
        lic = e.get("license", "unknown")
        by_license[lic] = by_license.get(lic, 0) + 1

    click.echo("\nBy institution:")
    for inst, count in sorted(by_inst.items(), key=lambda x: -x[1]):
        click.echo(f"  {inst}: {count}")

    click.echo("\nBy license:")
    for lic, count in sorted(by_license.items(), key=lambda x: -x[1]):
        click.echo(f"  {lic}: {count}")

    # Catalog coverage
    mapped = sum(1 for e in entries if e.get("catalog_number") is not None)
    click.echo(f"\nCatalog-mapped: {mapped}/{len(entries)}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
