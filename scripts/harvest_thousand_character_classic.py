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
_LOCAL_DATA_DIR = Path("data/calligraphy/thousand-character-classic")
_EXTERNAL_DATA_DIR = Path(
    "/mnt/e/image_detection/01_base_data/calligraphy/thousand-character-classic"
)
# Use local storage by default; move to external drive when mounted
_DEFAULT_OUTPUT_DIR = (
    _EXTERNAL_DATA_DIR if _EXTERNAL_DATA_DIR.exists() else _LOCAL_DATA_DIR
)

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
    1932,
    593,
    13915,
    1524,
    17583,
    17585,
    17635,
    19189,
    2583,
    2582,
    2520,
    779,
    22100,
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
    """Load the catalog YAML (74+ items)."""
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

    click.echo(
        f"\nFound {len(all_files)} files across {len(visited_categories)} categories."
    )

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
                title.replace("File:", "").replace(" ", "_").replace("/", "_")[:200]
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

    click.echo(
        f"\nWikimedia harvest complete: {downloaded} downloaded, {skipped} skipped."
    )


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
        853547: 47,
        910125: 48,
        1181692: 49,
        853440: 50,
        781828: 51,
        853669: 52,
    }
    kyoto_catalog_map = {
        "rb00011078": 53,
        "rb00009713": 54,
        "rb00012112": 55,
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
            # Kyoto U uses uppercase IDs and metadata_manifest path
            upper_id = item_id.upper()
            manifest_url = (
                f"https://rmda.kulib.kyoto-u.ac.jp/iiif/"
                f"metadata_manifest/{upper_id}/manifest.json"
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

    Prefers IIIF Image API service endpoint at full resolution over
    direct image URLs which may be thumbnails.
    """
    # IIIF v2: canvas.images[].resource.@id or canvas.images[].resource.service.@id
    images = canvas.get("images", [])
    for img in images:
        resource = img.get("resource", {})

        # Prefer service endpoint (full resolution via IIIF Image API)
        service = resource.get("service", {})
        if isinstance(service, list):
            service = service[0] if service else {}
        service_id = service.get("@id", "")
        if service_id:
            return f"{service_id}/full/full/0/default.jpg"

        # Fall back to direct URL
        url = resource.get("@id", "")
        if url:
            # If URL is an IIIF Image API info.json, convert to full image
            if url.endswith("/info.json"):
                url = url.replace("/info.json", "/full/full/0/default.jpg")
            return url

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
@click.option("--max-pages", type=int, default=0, help="Max pages per item (0 = all).")
@click.pass_context
def harvest_npm_taipei(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from National Palace Museum Taipei via IIIF manifests.

    NPM provides IIIF v2 manifests at iiifod.npm.gov.tw with full-resolution
    images. Manifest URL pattern: /Integrate/GetJson?cid={detail_id}&dept=P

    Images are available at ~3000x2300 (7MP) under CC BY 4.0.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "npm_taipei"
    subdir.mkdir(parents=True, exist_ok=True)

    catalog = _load_catalog()
    downloaded = 0
    errors = 0

    # NPM Taipei detail IDs map to catalog numbers 13-25
    npm_catalog_map = dict(zip(_NPM_DETAIL_IDS, range(13, 26)))

    for detail_id in _NPM_DETAIL_IDS:
        cat_num = npm_catalog_map[detail_id]
        cat_entry = catalog.get(cat_num, {})
        calligrapher = cat_entry.get("calligrapher", "unknown")

        click.echo(f"\nNPM cid={detail_id} (catalog #{cat_num}): {calligrapher}")

        # IIIF v2 manifest from NPM digital archive
        manifest_url = (
            f"https://digitalarchive.npm.gov.tw/Integrate/GetJson"
            f"?cid={detail_id}&dept=P"
        )

        if dry_run:
            click.echo(f"  [DRY RUN] Manifest: {manifest_url}")
            # Fetch manifest to count canvases
            try:
                resp = requests.get(
                    manifest_url,
                    headers={"User-Agent": _USER_AGENT},
                    timeout=30,
                )
                resp.raise_for_status()
                manifest = resp.json()
                canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
                click.echo(f"  [DRY RUN] {len(canvases)} canvases available")
                downloaded += len(canvases)
            except requests.RequestException as exc:
                click.echo(f"  [ERROR] {exc}", err=True)
                errors += 1
            time.sleep(0.5)
            continue

        # Fetch IIIF manifest
        try:
            resp = requests.get(
                manifest_url,
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            manifest = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] Manifest fetch failed: {exc}", err=True)
            errors += 1
            continue

        canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
        click.echo(f"  Found {len(canvases)} canvases")

        for i, canvas in enumerate(canvases):
            if 0 < max_pages <= i:
                break

            img_url = _extract_image_url_from_canvas(canvas)
            if not img_url:
                click.echo(f"  [SKIP] No image URL in canvas {i}")
                continue

            safe_name = calligrapher.replace(" ", "_").replace("(", "").replace(")", "")
            filename = f"npm_{detail_id}_{safe_name}_{i:04d}.jpg"
            out_path = subdir / filename

            # Try full/full first; fall back to full/max if 403
            urls_to_try = [img_url]
            if "/full/full/" in img_url:
                urls_to_try.append(img_url.replace("/full/full/", "/full/max/"))

            ok = False
            for try_url in urls_to_try:
                ok = _download_image(
                    try_url,
                    out_path,
                    sha_set=sha_set,
                    registry_path=registry_path,
                    source_institution="npm_taipei",
                    catalog_number=cat_num,
                    license_str="CC_BY_4.0",
                    acquisition_method="npm_iiif_manifest",
                    output_dir=output_dir,
                    rate_limit=1.0,
                )
                if ok:
                    break
            if ok:
                downloaded += 1

        time.sleep(1)  # Rate limit between items

    click.echo(f"\nNPM Taipei harvest complete: {downloaded} images, {errors} errors.")


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
        f
        for f in files
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
# match-wikimedia
# ---------------------------------------------------------------------------

# Filename substring -> catalog number (or "REMOVE" for misclassified content)
_WIKIMEDIA_EXACT_MATCHES: dict[str, int | str] = {
    "ZhiYong1000charcter": 1,
    "明_王宠_千字文_局部": 3,
    "徐霖篆书千字文卷": 7,
    "Han_Ho-Cheonjamun": 64,
    "한석봉_천자문": 64,
    "An_Authentic_Thousand_Character_Classic": 79,
    "隷書千字文_(Calligraphy_by_Rosanjin)": 77,
    "王澍千字文拓本": 78,
    "Pakapoo_ticket": "REMOVE",
}

# Prefix -> catalog number
_WIKIMEDIA_PREFIX_MATCHES: list[tuple[str, int | str]] = [
    ("MET_DP", 34),
    ("MET_TR", 34),
    ("Classique_mille_carac", 75),
    ("Thiên_tự_văn", 76),
    ("Thien_tu_van", 76),
]


def _match_wikimedia_filename(filename: str) -> int | str | None:
    """Match a Wikimedia filename to a catalog number.

    Returns:
        int: catalog number if matched
        str "REMOVE": if content is misclassified
        None: if no match found
    """
    # Check exact substring matches first
    for pattern, cat_num in _WIKIMEDIA_EXACT_MATCHES.items():
        if pattern in filename:
            return cat_num

    # Check prefix matches
    for prefix, cat_num in _WIKIMEDIA_PREFIX_MATCHES:
        if filename.startswith(prefix):
            return cat_num

    return None


@cli.command("match-wikimedia")
@click.option(
    "--dry-run", is_flag=True, help="Preview matches without modifying registry."
)
@click.option(
    "--remove-misclassified",
    is_flag=True,
    help="Remove misclassified images (e.g., Pakapoo ticket) from registry and disk.",
)
@click.option(
    "--investigate-only",
    is_flag=True,
    help="Only query Wikimedia API for unmatched image metadata.",
)
@click.pass_context
def match_wikimedia(
    ctx: click.Context,
    dry_run: bool,
    remove_misclassified: bool,
    investigate_only: bool,
) -> None:
    """Match unmatched Wikimedia images to catalog entries.

    Maps 130 Wikimedia images (catalog_number=null) to catalog entries using
    filename-based matching rules. Creates new catalog entries as needed.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    _, entries = _load_registry(registry_path)

    # Find unmatched Wikimedia entries
    unmatched = [
        e
        for e in entries
        if e.get("source_institution") == "wikimedia"
        and e.get("catalog_number") is None
    ]
    click.echo(f"Found {len(unmatched)} unmatched Wikimedia images")

    if investigate_only:
        click.echo("\n--- Investigating via Wikimedia API ---")
        for e in unmatched[:5]:
            fname = e.get("source_path", "").split("/")[-1]
            click.echo(f"\n  {fname}")
            try:
                params = {
                    "action": "query",
                    "titles": f"File:{fname}",
                    "prop": "imageinfo",
                    "iiprop": "extmetadata",
                    "format": "json",
                }
                resp = requests.get(
                    _WIKIMEDIA_API,
                    params=params,
                    headers={"User-Agent": _USER_AGENT},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page in pages.values():
                    ii = page.get("imageinfo", [{}])[0]
                    ext = ii.get("extmetadata", {})
                    desc = ext.get("ImageDescription", {}).get("value", "N/A")[:200]
                    artist = ext.get("Artist", {}).get("value", "N/A")[:100]
                    click.echo(f"    Description: {desc}")
                    click.echo(f"    Artist: {artist}")
            except requests.RequestException as exc:
                click.echo(f"    [ERROR] {exc}", err=True)
            time.sleep(1)
        if len(unmatched) > 5:
            click.echo(f"\n  ... and {len(unmatched) - 5} more (showing first 5)")
        return

    # Apply matching rules
    matched_count = 0
    removed_count = 0
    still_unmatched = 0
    matched_entries: list[tuple[dict[str, Any], int]] = []
    removed_entries: list[dict[str, Any]] = []

    for e in unmatched:
        source_path = e.get("source_path", "")
        fname = source_path.split("/")[-1] if "/" in source_path else source_path

        result = _match_wikimedia_filename(fname)

        if result == "REMOVE":
            click.echo(f"  [REMOVE] {fname} (misclassified content)")
            removed_entries.append(e)
            removed_count += 1
        elif isinstance(result, int):
            click.echo(f"  [MATCH] {fname} -> catalog #{result}")
            matched_entries.append((e, result))
            matched_count += 1
        else:
            click.echo(f"  [UNMATCHED] {fname}")
            still_unmatched += 1

    click.echo(
        f"\nSummary: {matched_count} matched, {removed_count} to remove, "
        f"{still_unmatched} still unmatched"
    )

    if dry_run:
        click.echo("\n[DRY RUN] No changes made.")
        return

    # Build updated registry
    removed_ids = {e["sample_id"] for e in removed_entries}
    matched_map = {e["sample_id"]: cat_num for e, cat_num in matched_entries}

    updated_entries: list[dict[str, Any]] = []
    for e in entries:
        sid = e["sample_id"]
        if sid in removed_ids:
            if remove_misclassified:
                # Remove image file from disk
                img_path = output_dir / e.get("source_path", "")
                if img_path.exists():
                    img_path.unlink()
                    click.echo(f"  Deleted: {img_path}")
                continue  # Skip this entry
            click.echo(
                f"  [SKIP] Would remove {e.get('source_path', '')} "
                f"(use --remove-misclassified)"
            )
            updated_entries.append(e)
            continue

        if sid in matched_map:
            e["catalog_number"] = matched_map[sid]

        updated_entries.append(e)

    # Write atomically
    tmp_path = registry_path.with_suffix(".jsonl.tmp")
    with tmp_path.open("w") as fh:
        for e in updated_entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp_path.rename(registry_path)

    final_removed = len(entries) - len(updated_entries)
    click.echo(
        f"\nRegistry updated: {matched_count} catalog numbers set, "
        f"{final_removed} entries removed."
    )


# ---------------------------------------------------------------------------
# harvest-waseda
# ---------------------------------------------------------------------------

# Waseda archive paths -> catalog numbers (#38-46).
# Format: (archive_path, catalog_number).
# archive_path is the path under https://archive.wul.waseda.ac.jp/kosho/
# Most items: {collection}/{item}  -> images at {item}/{item}_p{page}.jpg
# Nested items: {collection}/{parent}/{sub_item} -> images at {sub_item}/{sub_item}_p{page}.jpg
_WASEDA_ITEMS: list[tuple[str, int]] = [
    ("chi06/chi06_00856", 38),
    ("chi06/chi06_04748", 39),
    ("bunko31/bunko31_e1746", 40),
    ("chi06/chi06_00499", 41),
    ("bunko31/bunko31_e1734", 42),
    ("to02/to02_04575/to02_04575_b0057", 43),
    ("i17/i17_02128", 44),
    ("chi06/chi06_02237", 45),
    ("ho03/ho03_01755", 46),
]


def _count_waseda_pages(item_id: str) -> int:
    """Probe Waseda archive to count available pages for an item.

    Sends HEAD requests for sequential page numbers until a 404 is returned.
    Returns the number of pages found (0 if page 1 doesn't exist).
    """
    base = f"https://archive.wul.waseda.ac.jp/kosho/{item_id}/{item_id.split('/')[-1]}"
    page = 1
    max_probe = 500  # safety limit
    while page <= max_probe:
        url = f"{base}_p{page:04d}.jpg"
        try:
            resp = requests.head(
                url,
                headers={"User-Agent": _USER_AGENT},
                timeout=15,
                allow_redirects=True,
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
        except requests.RequestException:
            break
        page += 1
        time.sleep(0.3)
    return page - 1


@cli.command("harvest-waseda")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=0,
    show_default=True,
    help="Max pages per volume (0 = all).",
)
@click.pass_context
def harvest_waseda(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from Waseda University Library (catalog #38-46, 9 items).

    Waseda serves full-size page images at direct archive URLs:
    https://archive.wul.waseda.ac.jp/kosho/{collection}/{item}/{item}_p{page}.jpg

    Pages are enumerated sequentially (p0001, p0002, ...) until a 404 is hit.
    Expected yield: ~90-270 images across kaishu, zhangcao, and mixed styles.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    downloaded = 0

    catalog = _load_catalog()

    for waseda_path, cat_num in _WASEDA_ITEMS:
        cat_entry = catalog.get(cat_num, {})
        calligrapher = cat_entry.get("calligrapher", "unknown")
        script_style = cat_entry.get("script_style", "unknown")
        item_id = waseda_path.split("/")[-1]

        click.echo(f"\nWaseda {waseda_path}: {calligrapher} ({script_style})")

        # Probe page count
        total_pages = _count_waseda_pages(waseda_path)
        click.echo(f"  Found {total_pages} pages")

        if total_pages == 0:
            click.echo("  [SKIP] No pages found at archive URL")
            continue

        limit = total_pages if max_pages == 0 else min(max_pages, total_pages)

        subdir = output_dir / "waseda"
        subdir.mkdir(parents=True, exist_ok=True)

        for page in range(1, limit + 1):
            img_url = (
                f"https://archive.wul.waseda.ac.jp/kosho/"
                f"{waseda_path}/{item_id}_p{page:04d}.jpg"
            )
            safe_id = waseda_path.replace("/", "_")
            filename = f"waseda_{safe_id}_{page:04d}.jpg"
            out_path = subdir / filename

            if dry_run:
                click.echo(f"  [DRY RUN] Would download: {img_url}")
                downloaded += 1
                continue

            ok = _download_image(
                img_url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="waseda",
                catalog_number=cat_num,
                license_str="open_access",
                acquisition_method="direct_download",
                output_dir=output_dir,
                rate_limit=1.5,
            )
            if ok:
                downloaded += 1

    click.echo(f"\nWaseda harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-met-extended
# ---------------------------------------------------------------------------


@cli.command("harvest-met-extended")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_met_extended(ctx: click.Context, dry_run: bool) -> None:
    """Harvest ALL Thousand Character Classic objects from Met Museum.

    Searches the Met API for all TCC-related objects (93 results) and downloads
    public domain images. Extends beyond the 2 hard-coded objects in harvest-met.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "met"
    subdir.mkdir(parents=True, exist_ok=True)

    # Search Met API for all TCC objects in Asian Art (department 6)
    search_url = (
        "https://collectionapi.metmuseum.org/public/collection/v1/search"
        "?q=thousand+character+classic&departmentId=6"
    )
    click.echo("Searching Met API for Thousand Character Classic objects...")

    try:
        resp = requests.get(
            search_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        search_data = resp.json()
    except requests.RequestException as exc:
        click.echo(f"[ERROR] Search failed: {exc}", err=True)
        return

    object_ids = search_data.get("objectIDs", [])
    total = search_data.get("total", 0)
    click.echo(f"Found {total} objects ({len(object_ids)} IDs)")

    # Skip already-harvested objects
    already_harvested = set(_MET_OBJECT_IDS)
    downloaded = 0
    skipped = 0
    catalog = _load_catalog()

    # Next available catalog number for new items
    max_cat = max(catalog.keys())
    next_cat = max_cat + 1

    for obj_id in object_ids:
        if obj_id in already_harvested:
            continue

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
            time.sleep(0.5)
            continue

        title = obj.get("title", f"object_{obj_id}")
        is_pd = obj.get("isPublicDomain", False)
        dynasty = obj.get("dynasty", "")
        artist = obj.get("artistDisplayName", "")
        medium_str = obj.get("medium", "")

        click.echo(f"  Title: {title}")
        click.echo(f"  Artist: {artist} | Dynasty: {dynasty} | Public Domain: {is_pd}")

        if not is_pd:
            click.echo("  [SKIP] Not public domain")
            skipped += 1
            time.sleep(0.3)
            continue

        # Collect all image URLs
        image_urls: list[str] = []
        primary = obj.get("primaryImage", "")
        if primary:
            image_urls.append(primary)
        additional = obj.get("additionalImages", [])
        image_urls.extend(additional)

        if not image_urls:
            click.echo("  [SKIP] No images available")
            skipped += 1
            time.sleep(0.3)
            continue

        click.echo(f"  Found {len(image_urls)} images")

        if dry_run:
            for url in image_urls[:3]:
                click.echo(f"    [DRY RUN] {url[:100]}")
            if len(image_urls) > 3:
                click.echo(f"    ... and {len(image_urls) - 3} more")
            downloaded += len(image_urls)
            time.sleep(0.3)
            continue

        # Use next_cat for this new object, increment for next
        cat_num = next_cat
        next_cat += 1

        for i, url in enumerate(image_urls):
            safe_title = title.replace(" ", "_").replace("/", "_")[:80]
            filename = f"met_{obj_id}_{safe_title}_{i:03d}.jpg"
            out_path = subdir / filename

            ok = _download_image(
                url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="met_museum",
                catalog_number=cat_num,
                license_str="CC0",
                acquisition_method="met_open_access_api",
                output_dir=output_dir,
                rate_limit=0.5,
            )
            if ok:
                downloaded += 1

    click.echo(
        f"\nMet extended harvest complete: {downloaded} downloaded, "
        f"{skipped} skipped (not public domain or no images)."
    )


# ---------------------------------------------------------------------------
# harvest-korean
# ---------------------------------------------------------------------------


@cli.command("harvest-korean")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_korean(ctx: click.Context, dry_run: bool) -> None:
    """Harvest from National Museum of Korea (KOGL license, 2 confirmed items).

    Downloads directly available images for Korean calligraphy items.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "korean"
    subdir.mkdir(parents=True, exist_ok=True)

    # NMK direct image paths (extracted from relic detail pages)
    _NMK_KNOWN_IMAGES: dict[int, list[str]] = {
        8003: [
            "/relic_image/PS01001001/koo005/2016/1114125941596/koo005570-00-00.jpg",
            "/relic_image/PS01001001/koo005/2016/1114125941596/koo005570-00-01.jpg",
            "/relic_image/PS01001001/koo005/2016/1114125941596/koo005570-00-02.jpg",
        ],
    }

    # National Museum of Korea items with direct image URLs
    # These are confirmed available from the collection database
    korean_items: list[dict[str, str | int | None]] = [
        {
            "relic_id": 8003,
            "catalog_number": 64,
            "name": "Han Ho Cheonjamun (haeseo)",
            "url": "https://www.museum.go.kr/site/eng/relic/search/view?relicId=8003",
            "license": "KOGL",
        },
        {
            "relic_id": 7031,
            "catalog_number": None,  # New entry — ancient seal script
            "name": "Gojeon Cheonjamun (seal script)",
            "url": "https://www.museum.go.kr/site/eng/relic/search/view?relicId=7031",
            "license": "KOGL",
        },
    ]

    downloaded = 0

    for item in korean_items:
        click.echo(f"\nKorean item: {item['name']}")
        click.echo(f"  URL: {item['url']}")

        if dry_run:
            click.echo(
                "  [DRY RUN] Would attempt to download images from collection page"
            )
            click.echo("  Note: Korean museum sites may require manual download")
            continue

        # Try known direct image paths first, fall back to page scraping
        cat_num_val = item["catalog_number"]
        license_val = str(item["license"])
        relic_id = item["relic_id"]

        known_paths = _NMK_KNOWN_IMAGES.get(int(str(relic_id)), [])
        if known_paths:
            click.echo(f"  Using {len(known_paths)} known image paths")
            found_urls = [f"https://www.museum.go.kr{p}" for p in known_paths]
        else:
            # Fall back to scraping the relic page
            page_url = str(item["url"])
            try:
                resp = requests.get(
                    page_url,
                    headers={"User-Agent": _USER_AGENT},
                    timeout=30,
                )
                resp.raise_for_status()
                html = resp.text

                import re

                img_patterns = [
                    r'(https?://[^"\']+\.(?:jpg|jpeg|png|tif))',
                    r'src="(/[^"]+\.(?:jpg|jpeg|png|tif))"',
                ]
                found_urls = []
                for pattern in img_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for m in matches:
                        if "relic" in m.lower() or "image" in m.lower():
                            if m.startswith("/"):
                                m = f"https://www.museum.go.kr{m}"
                            found_urls.append(m)
            except requests.RequestException as exc:
                click.echo(f"  [ERROR] {exc}", err=True)
                continue

        if not found_urls:
            click.echo("  [SKIP] No downloadable image URLs found")
            click.echo("  Manual download may be required")
            continue

        click.echo(f"  Found {len(found_urls)} image URLs")

        try:
            for i, img_url in enumerate(found_urls[:10]):
                filename = f"korean_{relic_id}_{i:03d}.jpg"
                out_path = subdir / filename

                ok = _download_image(
                    img_url,
                    out_path,
                    sha_set=sha_set,
                    registry_path=registry_path,
                    source_institution="national_museum_korea",
                    catalog_number=int(cat_num_val)
                    if cat_num_val is not None
                    else None,
                    license_str=license_val,
                    acquisition_method="nmk_direct_download",
                    output_dir=output_dir,
                    rate_limit=1.5,
                )
                if ok:
                    downloaded += 1

        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)

    click.echo(f"\nKorean harvest complete: {downloaded} downloaded.")
    if downloaded == 0:
        click.echo("Note: Korean museum sites often require manual download.")
        click.echo("Visit the URLs above to download images manually.")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# harvest-ndl-pdfs
# ---------------------------------------------------------------------------

# NDL PDF files on Wikimedia Commons → catalog number mapping
# Each tuple: (Wikimedia filename (without "File:" prefix), catalog_number)
_NDL_PDF_ITEMS: list[tuple[str, int]] = [
    # Yoshida Shigematsu (1890-1940) — Showa — caoshu
    ("NDL1107939 草書千字文 上.pdf", 82),
    # Yoshida Shigematsu (1890-1940) — Showa — xingshu
    ("NDL1107940 行書千字文 中.pdf", 83),
    # Tamaki Aiseki (1853-1928) — Taisho — lishu
    ("NDL853841 隷書千字文.pdf", 84),
    # Nishikawa Shundo (1847-1915) — Meiji — zhuanshu
    ("NDL853397 漢篆千字文.pdf", 85),
    # Iwatani Ichiroku (1834-1905) — Meiji — four-style
    ("NDL853545 四体千字文.pdf", 86),
    # Uehara Chinkyu — Meiji — lishu
    ("NDL853684 正隷千字文.pdf", 87),
    # Onuma Rensai (1839-1898) — Meiji — kaishu
    ("NDL853622 真書千字文.pdf", 88),
]

# Met Museum modern TCC objects (20th century)
_MET_MODERN_IDS: list[tuple[int, int]] = [
    (64060, 80),  # Preface to TCC, 20th c rubbing
    (64049, 81),  # TCC cursive script, 20th c rubbing
    (64061, 91),  # TCC seal script (zhuanshu), 20th c
]


def _get_wikimedia_file_url(filename: str) -> str | None:
    """Resolve a Wikimedia Commons filename to its direct download URL."""
    import urllib.parse

    encoded = urllib.parse.quote(f"File:{filename}")
    url = (
        f"{_WIKIMEDIA_API}?action=query&titles={encoded}"
        "&prop=imageinfo&iiprop=url&format=json"
    )
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            ii = page.get("imageinfo", [{}])
            if ii:
                return str(ii[0].get("url", ""))
    except requests.RequestException as exc:
        click.echo(f"  [ERROR] Resolving {filename}: {exc}", err=True)
    return None


def _render_pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    *,
    prefix: str,
    dpi: int = 200,
) -> list[Path]:
    """Render PDF pages to JPEG images using PyMuPDF.

    Returns list of output image paths.
    """
    import fitz  # PyMuPDF

    image_paths: list[Path] = []
    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        out_path = output_dir / f"{prefix}_p{page_num:04d}.jpg"
        # Convert to JPEG via PIL for consistent quality
        from PIL import Image

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(out_path, "JPEG", quality=90)
        image_paths.append(out_path)

    doc.close()
    return image_paths


@cli.command("harvest-ndl-pdfs")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--rate-limit",
    type=float,
    default=1.0,
    help="Seconds between downloads.",
)
@click.pass_context
def harvest_ndl_pdfs(ctx: click.Context, dry_run: bool, rate_limit: float) -> None:
    """Harvest NDL calligraphy PDFs from Wikimedia, render pages to images.

    Downloads PDF files of modern-era (Meiji/Taisho/Showa) TCC calligraphy
    from Wikimedia Commons (original NDL scans), renders each page to a JPEG,
    and registers in the dataset.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "ndl"
    subdir.mkdir(parents=True, exist_ok=True)

    import tempfile

    downloaded = 0
    errors = 0

    click.echo(f"Harvesting {len(_NDL_PDF_ITEMS)} NDL PDFs from Wikimedia Commons...")

    for filename, cat_num in _NDL_PDF_ITEMS:
        click.echo(f"\n--- {filename} (catalog #{cat_num}) ---")

        # Resolve Wikimedia file URL
        file_url = _get_wikimedia_file_url(filename)
        if not file_url:
            click.echo(f"  [ERROR] Could not resolve URL for {filename}")
            errors += 1
            continue

        click.echo(f"  URL: {file_url[:80]}...")

        if dry_run:
            click.echo(f"  [DRY RUN] Would download and render: {filename}")
            downloaded += 1
            continue

        # Download PDF to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            resp = requests.get(
                file_url,
                headers={"User-Agent": _USER_AGENT},
                timeout=300,
                stream=True,
            )
            resp.raise_for_status()

            with tmp_path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=65_536):
                    fh.write(chunk)

            click.echo(f"  Downloaded {tmp_path.stat().st_size / 1024 / 1024:.1f} MB")

            # Build prefix from filename
            safe_name = filename.replace(" ", "_").replace(".pdf", "")
            prefix = f"ndl_{safe_name}"

            # Render PDF pages to images
            image_paths = _render_pdf_to_images(
                tmp_path,
                subdir,
                prefix=prefix,
                dpi=200,
            )
            click.echo(f"  Rendered {len(image_paths)} pages")

            # Register each page image
            page_ok = 0
            for img_path in image_paths:
                sha256 = _compute_sha256(img_path)
                if sha256 in sha_set:
                    click.echo(f"  [SKIP] Duplicate: {img_path.name}")
                    img_path.unlink()
                    continue

                entry = _build_entry(
                    img_path,
                    file_url,
                    "ndl",
                    cat_num,
                    "public_domain",
                    "wikimedia_pdf_render",
                    output_dir,
                )
                _append_entry(entry, registry_path)
                sha_set.add(sha256)
                page_ok += 1

            downloaded += page_ok
            click.echo(f"  Registered {page_ok} new page images")

        except Exception as exc:
            click.echo(f"  [ERROR] {filename}: {exc}", err=True)
            errors += 1
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        time.sleep(rate_limit)

    # Also harvest Met modern objects
    click.echo(f"\n--- Met Museum modern TCC ({len(_MET_MODERN_IDS)} objects) ---")
    for obj_id, cat_num in _MET_MODERN_IDS:
        click.echo(f"\nFetching Met object {obj_id} (catalog #{cat_num})...")
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
            errors += 1
            continue

        title = obj.get("title", f"object_{obj_id}")
        image_urls: list[str] = []
        primary = obj.get("primaryImage", "")
        if primary:
            image_urls.append(primary)
        image_urls.extend(obj.get("additionalImages", []))

        if not image_urls:
            click.echo(f"  [SKIP] No images for {title}")
            continue

        for i, url in enumerate(image_urls):
            safe_title = title.replace(" ", "_").replace("/", "_")[:60]
            filename_out = f"met_{obj_id}_{safe_title}_{i:03d}.jpg"
            out_path = (output_dir / "met") / filename_out

            ok = _download_image(
                url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="met_museum",
                catalog_number=cat_num,
                license_str="CC0",
                acquisition_method="met_open_access_api",
                output_dir=output_dir,
                dry_run=dry_run,
                rate_limit=0.5,
            )
            if ok:
                downloaded += 1

    click.echo(f"\nModern TCC harvest complete: {downloaded} images, {errors} errors.")


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

    # Script style distribution (from catalog)
    catalog = _load_catalog()
    by_style: dict[str, int] = {}
    for e in entries:
        cat_num = e.get("catalog_number")
        if cat_num is not None:
            cat_entry = catalog.get(cat_num, {})
            style = cat_entry.get("script_style", "unknown")
        else:
            style = "(unmapped)"
        by_style[style] = by_style.get(style, 0) + 1

    click.echo("\nBy script style (via catalog):")
    for style, count in sorted(by_style.items(), key=lambda x: -x[1]):
        click.echo(f"  {style}: {count}")


# ---------------------------------------------------------------------------
# harvest-dunhuang — IDP (British Library) + BnF Gallica
# ---------------------------------------------------------------------------

# BnF Gallica IIIF manifests for Dunhuang TCC manuscripts
# Pelliot chinois collection — known TCC manuscript fragments
_DUNHUANG_BNF_ITEMS: list[tuple[str, str, int | None]] = [
    # (ark_id, description, catalog_number)
    # Pelliot chinois 2578 — TCC fragment, Tang dynasty student copy
    ("btv1b8302295d", "Pelliot chinois 2578 — TCC fragment", None),
    # Pelliot chinois 3561 — TCC practice copy
    ("btv1b83022954", "Pelliot chinois 3561 — TCC practice copy", None),
]

# IDP (British Library) IIIF manifests
_DUNHUANG_IDP_ITEMS: list[tuple[str, str, int | None]] = [
    # (manifest_id, description, catalog_number)
    # Or.8210/S.5765 — TCC student copy, Tang dynasty
    # IDP IIIF: https://iiif.bl.uk/manifest/ark:/81055/vdc_[id]
]


def _harvest_iiif_source(
    manifest_url: str,
    *,
    output_dir: Path,
    sha_set: set[str],
    registry_path: Path,
    source_institution: str,
    catalog_number: int | None,
    license_str: str,
    acquisition_method: str,
    item_id: str,
    dry_run: bool = False,
    max_pages: int = 0,
    rate_limit: float = 1.0,
    extra_headers: dict[str, str] | None = None,
    registry_base_dir: Path | None = None,
) -> int:
    """Parse a IIIF manifest and download all canvas images (standalone version).

    Args:
        registry_base_dir: Base directory for computing relative source_path in
            registry entries. Defaults to output_dir.parent if not provided.
    """
    count = 0
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": _USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)

    click.echo(f"\nFetching IIIF manifest: {manifest_url}")
    manifest: dict[str, Any] | None = None
    for attempt in range(4):
        try:
            resp = requests.get(
                manifest_url,
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 5.0 * (2**attempt)
                click.echo(f"  [429] Rate limited, retrying in {wait:.0f}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            manifest = resp.json()
            break
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            if attempt < 3:
                time.sleep(5.0 * (2**attempt))
                continue
            return 0
    if manifest is None:
        click.echo("  [ERROR] Exhausted retries", err=True)
        return 0

    # Extract canvases (IIIF v2 or v3)
    canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
    if not canvases:
        canvases = manifest.get("items", [])

    click.echo(f"  Found {len(canvases)} canvases")

    for i, canvas in enumerate(canvases):
        if 0 < max_pages <= i:
            break

        img_url = _extract_image_url_from_canvas(canvas)
        if not img_url:
            click.echo(f"  [SKIP] No image URL in canvas {i}")
            continue

        if dry_run:
            click.echo(f"  [DRY RUN] Canvas {i}: {img_url[:100]}...")
            count += 1
            continue

        filename = f"{source_institution}_{item_id}_{i:04d}.jpg"
        out_path = output_dir / filename

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
                source_institution=source_institution,
                catalog_number=catalog_number,
                license_str=license_str,
                acquisition_method=acquisition_method,
                output_dir=registry_base_dir or output_dir.parent,
                rate_limit=rate_limit,
            )
            if ok:
                break
        if ok:
            count += 1

    return count


@cli.command("harvest-dunhuang")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option("--max-pages", type=int, default=0, help="Max pages per item (0 = all).")
@click.option(
    "--source",
    type=click.Choice(["bnf", "idp", "all"]),
    default="all",
    help="Which Dunhuang source to harvest.",
)
@click.pass_context
def harvest_dunhuang(
    ctx: click.Context, dry_run: bool, max_pages: int, source: str
) -> None:
    """Harvest Dunhuang TCC manuscripts from BnF Gallica and IDP."""
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]

    sha_set, _ = _load_registry(registry_path)
    dunhuang_dir = output_dir / "dunhuang"

    total = 0

    if source in ("bnf", "all"):
        click.echo("\n=== BnF Gallica (Pelliot chinois collection) ===")
        for ark_id, desc, cat_num in _DUNHUANG_BNF_ITEMS:
            click.echo(f"\n--- {desc} ---")
            manifest_url = (
                f"https://gallica.bnf.fr/iiif/ark:/12148/{ark_id}/manifest.json"
            )
            total += _harvest_iiif_source(
                manifest_url,
                output_dir=dunhuang_dir / "bnf",
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="bnf_gallica",
                catalog_number=cat_num,
                license_str="public_domain",
                acquisition_method="bnf_iiif_manifest",
                item_id=ark_id,
                dry_run=dry_run,
                max_pages=max_pages,
            )

    if source in ("idp", "all"):
        click.echo("\n=== IDP (British Library) ===")
        for manifest_id, desc, cat_num in _DUNHUANG_IDP_ITEMS:
            click.echo(f"\n--- {desc} ---")
            manifest_url = f"https://iiif.bl.uk/manifest/{manifest_id}"
            total += _harvest_iiif_source(
                manifest_url,
                output_dir=dunhuang_dir / "idp",
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="idp_bl",
                catalog_number=cat_num,
                license_str="CC-BY-NC-SA-4.0",
                acquisition_method="idp_iiif_manifest",
                item_id=manifest_id,
                dry_run=dry_run,
                max_pages=max_pages,
            )

    click.echo(f"\nDunhuang harvest complete: {total} images downloaded.")


# ---------------------------------------------------------------------------
# Library of Congress items
# ---------------------------------------------------------------------------

# LOC World Digital Library items — free to use and reuse (public domain)
_LOC_WDL_ITEMS: list[tuple[str, str, str, str, int | None]] = [
    # (lccn, description, script_style, period, catalog_number)
    # Korean TCC woodblock print — 68 pages, actual TCC text
    (
        "2016500252",
        "Ch'onjamun — Korean TCC woodblock print (1896)",
        "kaishu",
        "19th",
        92,
    ),
    # Jiang tie — earliest private calligraphy anthology, Wang Xizhi works
    (
        "2021667447",
        "Jiang tie — Song calligraphy rubbings anthology",
        "mixed",
        "11th",
        93,
    ),
    # Yi que Fo kan bei — Chu Suiliang, Tang regular script, 106 pages
    (
        "2021667449",
        "Yi que Fo kan bei — Chu Suiliang kaishu (Tang, 641)",
        "kaishu",
        "7th",
        94,
    ),
    # Shen ce jun bei — Liu Gongquan, Tang regular script, 60 pages
    (
        "2021667418",
        "Shen ce jun bei — Liu Gongquan kaishu (Tang, 843)",
        "kaishu",
        "9th",
        95,
    ),
    # Zheng zuo wei tie — Yan Zhenqing, Tang running script, 11 pages
    (
        "2021666489",
        "Zheng zuo wei tie — Yan Zhenqing xingshu (Tang)",
        "xingshu",
        "8th",
        96,
    ),
    # Yi he ming — Southern Dynasties proto-standard script, 14 pages
    (
        "2021666522",
        "Yi he ming — Southern Dynasties (514 CE)",
        "kaishu",
        "6th",
        97,
    ),
]

# LOC Chinese Rare Book items — educational/research use only
_LOC_CRB_ITEMS: list[tuple[str, str, str, str, int | None]] = [
    # (lccn, description, script_style, period, catalog_number)
    (
        "2012402760",
        "Shu fa jin liang — calligraphy compilation (4 juan)",
        "mixed",
        "17th-19th",
        None,
    ),
]


@cli.command("harvest-loc")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option("--max-pages", type=int, default=0, help="Max pages per item (0 = all).")
@click.option(
    "--source",
    type=click.Choice(["wdl", "crb", "all"]),
    default="all",
    help="Which LOC collection to harvest (wdl=World Digital Library, crb=Chinese Rare Books).",
)
@click.pass_context
def harvest_loc(ctx: click.Context, dry_run: bool, max_pages: int, source: str) -> None:
    """Harvest Chinese calligraphy from Library of Congress IIIF collections."""
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]

    sha_set, _ = _load_registry(registry_path)
    loc_dir = output_dir / "loc"

    # LOC requires browser-like headers for IIIF manifest access
    loc_headers = {
        "Accept": "application/ld+json, application/json",
        "Referer": "https://www.loc.gov/",
    }

    total = 0

    # LOC rate-limits aggressively; pause between manifest fetches
    loc_rate = 3.0  # seconds between items

    if source in ("wdl", "all"):
        click.echo("\n=== LOC World Digital Library (free reuse) ===")
        for idx, (lccn, desc, _style, _period, cat_num) in enumerate(_LOC_WDL_ITEMS):
            if idx > 0:
                time.sleep(loc_rate)
            click.echo(f"\n--- {desc} ---")
            manifest_url = f"https://www.loc.gov/item/{lccn}/manifest.json"
            total += _harvest_iiif_source(
                manifest_url,
                output_dir=loc_dir / "wdl",
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="loc_wdl",
                catalog_number=cat_num,
                license_str="public_domain",
                acquisition_method="loc_iiif_manifest",
                item_id=lccn,
                dry_run=dry_run,
                max_pages=max_pages,
                rate_limit=2.0,
                extra_headers=loc_headers,
                registry_base_dir=output_dir,
            )

    if source in ("crb", "all"):
        click.echo("\n=== LOC Chinese Rare Book Collection (research use) ===")
        for idx, (lccn, desc, _style, _period, cat_num) in enumerate(_LOC_CRB_ITEMS):
            if idx > 0 or total > 0:
                time.sleep(loc_rate)
            click.echo(f"\n--- {desc} ---")
            manifest_url = f"https://www.loc.gov/item/{lccn}/manifest.json"
            total += _harvest_iiif_source(
                manifest_url,
                output_dir=loc_dir / "crb",
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="loc_crb",
                catalog_number=cat_num,
                license_str="educational_research_only",
                acquisition_method="loc_iiif_manifest",
                item_id=lccn,
                dry_run=dry_run,
                max_pages=max_pages,
                rate_limit=2.0,
                extra_headers=loc_headers,
                registry_base_dir=output_dir,
            )

    click.echo(f"\nLOC harvest complete: {total} images downloaded.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
