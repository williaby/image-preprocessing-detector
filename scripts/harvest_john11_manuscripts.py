#!/usr/bin/env python3
"""Harvest John 1:1 multi-script manuscript images from open-access sources.

Multi-source download CLI for building the john11-manuscripts dataset.
Only harvests from institutions with verified open licenses (Phase 1).

Expected yield (Phase 1 verified-only): ~80-170 images across 11 scripts.

Usage:
    # Dry run — check API connectivity and expected yield
    uv run python scripts/harvest_john11_manuscripts.py harvest-wikimedia --dry-run

    # Download from verified CC0/PD sources
    uv run python scripts/harvest_john11_manuscripts.py harvest-wikimedia
    uv run python scripts/harvest_john11_manuscripts.py harvest-met
    uv run python scripts/harvest_john11_manuscripts.py harvest-walters
    uv run python scripts/harvest_john11_manuscripts.py harvest-gallica
    uv run python scripts/harvest_john11_manuscripts.py harvest-internet-archive

    # Show registry stats
    uv run python scripts/harvest_john11_manuscripts.py stats

Requires:
    requests>=2.28.0   (already in base deps)
    Pillow>=10.0.0     (already in base deps)
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
_CATALOG_PATH = _PROJECT_ROOT / "config" / "john11_manuscript_catalog.yaml"
_LICENSE_PATH = _PROJECT_ROOT / "config" / "john11_source_licenses.yaml"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_manuscripts_registry.jsonl"
)
_DEFAULT_OUTPUT_DIR = Path(
    "/mnt/e/image_detection/01_base_data/manuscripts/john11"
)
# Local fallback when E: drive is unavailable
_LOCAL_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "john11-manuscripts"

# Minimum image dimension filter — reject images smaller than this in either
# dimension.  Website UI scraping artifacts (logos, icons, badges) are typically
# well below this threshold.  Manuscript/printed edition pages should be
# substantially larger.
MIN_IMAGE_DIMENSION = 200  # pixels

# MediaWiki API
_WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# Wikimedia categories to search for John 1:1 manuscript images, by script
_WIKIMEDIA_CATEGORIES: dict[str, list[str]] = {
    "Grek": [
        "Category:Codex_Sinaiticus",
        "Category:Codex_Vaticanus_Graecus_1209",
        "Category:Codex_Alexandrinus",
        "Category:Codex_Bezae",
        "Category:Codex_Washingtonianus",
        "Category:Greek_New_Testament_manuscripts",
        "Category:Gospel_of_John_in_manuscripts",
        "Category:Papyrus_66",
        "Category:Papyrus_75",
        "Category:Papyrus_45",
        "Category:Bodmer_Papyri",
    ],
    "Latn": [
        "Category:Book_of_Kells",
        "Category:Lindisfarne_Gospels",
        "Category:Book_of_Durrow",
        "Category:Codex_Amiatinus",
        "Category:Harley_Golden_Gospels",
        "Category:Lichfield_Gospels",
        "Category:Carolingian_manuscripts",
        "Category:Insular_manuscripts",
        "Category:Gospel_of_John",
        "Category:King_James_Version",
        "Category:Gutenberg_Bible",
        "Category:Wycliffe_Bible",
        "Category:Tyndale_Bible",
        "Category:Reina-Valera_Bible",
        "Category:Spanish_Bible_translations",
    ],
    "Ethi": [
        "Category:Ethiopian_manuscripts",
        "Category:Ethiopian_Gospel_books",
    ],
    "Armn": [
        "Category:Armenian_manuscripts",
        "Category:Armenian_Gospel_books",
        "Category:Armenian_illuminated_manuscripts",
        "Category:Matenadaran",
    ],
    "Syrc": [
        "Category:Syriac_manuscripts",
        "Category:Syriac_language",
        "Category:Peshitta",
    ],
    "Arab": [
        "Category:Arabic_manuscripts",
        "Category:Arabic_Bible_manuscripts",
        "Category:Arabic_calligraphy",
        "Category:Quran_manuscripts",
    ],
    "Cyrs": [
        "Category:Old_Church_Slavonic_manuscripts",
        "Category:Codex_Marianus",
        "Category:Codex_Zographensis",
        "Category:Ostromir_Gospels",
    ],
    "Copt": [
        "Category:Coptic_manuscripts",
        "Category:Nag_Hammadi_codices",
        "Category:Coptic_language",
        "Category:Coptic_Bibles",
    ],
    "Goth": [
        "Category:Codex_Argenteus",
    ],
    "Geor": [
        "Category:Georgian_manuscripts",
        "Category:Georgian_calligraphy",
        "Category:Ecclesiastical_texts_in_Georgian",
    ],
}

# Met Museum Open Access object IDs with Armenian Gospel content
_MET_ARMENIAN_OBJECTS = [
    449536,  # Sargis, Title Page of Gospel of John (1386), accession 57.185.3
]

# Digital Walters manuscript IDs by script (CC0, all verified open)
# Access via: https://www.thedigitalwalters.org/Data/WaltersManuscripts/W{NUM}/
# Image pattern: W{NUM}/data/W.{NUM}/sap/W{NUM}_{PAGE:06d}_sap.jpg
_WALTERS_MANUSCRIPTS: dict[str, list[dict[str, Any]]] = {
    "Armn": [
        {"w_num": 537, "name": "Armenian Gospels", "pages": range(1, 50)},
        {"w_num": 543, "name": "Armenian Gospels (Gladzor)", "pages": range(1, 50)},
        {"w_num": 540, "name": "Armenian Gospels", "pages": range(1, 30)},
        {"w_num": 538, "name": "Armenian Gospels", "pages": range(1, 30)},
    ],
    "Syrc": [
        {"w_num": 530, "name": "Syriac Gospels (Monastery)", "pages": range(1, 30)},
        {"w_num": 533, "name": "Syriac Gospels", "pages": range(1, 20)},
    ],
    "Arab": [
        {"w_num": 592, "name": "Arabic Gospel Book", "pages": range(1, 30)},
        {"w_num": 556, "name": "Arabic Gospels", "pages": range(1, 20)},
    ],
}

# BnF/Gallica IIIF manifests for specific manuscripts (ARK IDs)
_GALLICA_MANUSCRIPTS: list[dict[str, Any]] = [
    {
        "ark_id": "btv1b8470433r",
        "name": "Codex Ephraemi Rescriptus",
        "script": "Grek",
        "catalog_number": 6,
    },
    {
        "ark_id": "btv1b10507230d",
        "name": "Codex Regius (L, 019)",
        "script": "Grek",
        "catalog_number": 7,
    },
    {
        "ark_id": "btv1b6000718s",
        "name": "Godescalc Evangelistary",
        "script": "Latn",
        "catalog_number": 20,
    },
    {
        "ark_id": "btv1b52505852n",
        "name": "Echternach Gospels",
        "script": "Latn",
        "catalog_number": 21,
    },
]

_USER_AGENT = (
    "John11ManuscriptHarvester/1.0 "
    "(https://github.com/ByronWilliamsCPA/image_detection; dataset research)"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers (following TCC harvest pattern)
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
    """Load the manuscript catalog YAML."""
    with _CATALOG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _load_licenses() -> dict[str, dict[str, Any]]:
    """Load the source license verification YAML."""
    with _LICENSE_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _extract_image_url_from_canvas(canvas: dict[str, Any]) -> str | None:
    """Extract the best image URL from an IIIF canvas (v2 or v3).

    Attempts full resolution first, falls back to /full/full/ IIIF Image API.
    """
    # IIIF v2: canvas.images[].resource.@id or canvas.images[].resource.service.@id
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
    """Harvest John 1:1 multi-script manuscript images from open-access sources."""
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
    help="Maximum images to download per script (0 = unlimited).",
)
@click.option(
    "--scripts",
    type=str,
    default="all",
    show_default=True,
    help="Comma-separated ISO 15924 codes to harvest (e.g., 'Grek,Latn') or 'all'.",
)
@click.pass_context
def harvest_wikimedia(
    ctx: click.Context,
    dry_run: bool,
    rate_limit: float,
    max_images: int,
    scripts: str,
) -> None:
    """Harvest from Wikimedia Commons categories (~30-80 images across scripts).

    Uses the MediaWiki API to enumerate files in manuscript categories
    per script. Downloads full-resolution originals. Only CC0/CC-BY/PD images.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    # Determine which scripts to harvest
    if scripts == "all":
        target_scripts = list(_WIKIMEDIA_CATEGORIES.keys())
    else:
        target_scripts = [s.strip() for s in scripts.split(",")]

    total_downloaded = 0
    total_skipped = 0

    for script_code in target_scripts:
        categories = _WIKIMEDIA_CATEGORIES.get(script_code, [])
        if not categories:
            click.echo(f"\n[WARN] No Wikimedia categories for script {script_code}")
            continue

        click.echo(f"\n{'='*60}")
        click.echo(f"Script: {script_code} ({len(categories)} categories)")
        click.echo(f"{'='*60}")

        subdir = output_dir / "wikimedia" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        # Collect all file titles from categories (with subcategory recursion)
        all_files: list[dict[str, Any]] = []
        visited_categories: set[str] = set()
        seen_titles: set[str] = set()

        def _enumerate_category(cat_title: str, depth: int = 0) -> None:
            """Recursively enumerate files and subcategories."""
            if cat_title in visited_categories or depth > 2:  # noqa: B023
                return
            visited_categories.add(cat_title)  # noqa: B023

            click.echo(f"  Enumerating {cat_title} (depth={depth})...")
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

                try:
                    resp = session.get(_WIKIMEDIA_API, params=params, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                except requests.RequestException as exc:
                    click.echo(f"    [ERROR] {exc}", err=True)
                    break

                for member in data.get("query", {}).get("categorymembers", []):
                    ns = member.get("ns", 0)
                    title = member.get("title", "")
                    if ns == 6 and title not in seen_titles:  # noqa: B023
                        all_files.append(member)  # noqa: B023
                        seen_titles.add(title)  # noqa: B023
                    elif ns == 14:  # Category namespace
                        _enumerate_category(title, depth + 1)

                cont = data.get("continue", {})
                cmcontinue = cont.get("cmcontinue")
                if not cmcontinue:
                    break

                time.sleep(0.5)

        for cat in categories:
            _enumerate_category(cat)

        click.echo(
            f"  Found {len(all_files)} files across "
            f"{len(visited_categories)} categories"
        )

        if dry_run:
            for f in all_files[:10]:
                click.echo(f"    {f.get('title', 'unknown')}")
            if len(all_files) > 10:
                click.echo(f"    ... and {len(all_files) - 10} more")
            total_downloaded += len(all_files)
            continue

        downloaded = 0
        skipped = 0

        for file_info in all_files:
            if 0 < max_images <= downloaded:
                click.echo(f"  Reached max_images={max_images} for {script_code}")
                break

            title = file_info.get("title", "")

            # Get image info and license via imageinfo query
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
                click.echo(f"    [ERROR] imageinfo for {title}: {exc}", err=True)
                time.sleep(rate_limit)
                continue

            for page in pages.values():
                ii_list = page.get("imageinfo", [])
                if not ii_list:
                    continue
                ii = ii_list[0]
                img_url = ii.get("url", "")
                mime = ii.get("mime", "")

                # Skip non-image files
                if not mime.startswith("image/"):
                    skipped += 1
                    continue

                # Check license from extmetadata
                extmeta = ii.get("extmetadata", {})
                license_short = extmeta.get("LicenseShortName", {}).get("value", "")
                license_lower = license_short.lower()

                # Only accept open licenses
                accepted = False
                license_str = "unknown"
                if any(
                    term in license_lower
                    for term in ["public domain", "pd", "cc0", "cc-zero"]
                ):
                    accepted = True
                    license_str = "public_domain"
                elif "cc by-sa" in license_lower or "cc-by-sa" in license_lower:
                    accepted = True
                    license_str = "CC-BY-SA"
                elif "cc by" in license_lower or "cc-by" in license_lower:
                    # Accept CC-BY but NOT CC-BY-NC
                    if "nc" not in license_lower:
                        accepted = True
                        license_str = "CC-BY-4.0"

                if not accepted:
                    click.echo(
                        f"    [SKIP] Non-open license: {title} ({license_short})"
                    )
                    skipped += 1
                    continue

                # Determine file extension
                ext = ".jpg"
                if "png" in mime:
                    ext = ".png"
                elif "tiff" in mime:
                    ext = ".tif"

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
                    catalog_number=None,
                    license_str=license_str,
                    acquisition_method="mediawiki_api",
                    output_dir=output_dir,
                    script_iso15924=script_code,
                    rate_limit=rate_limit,
                )
                if ok:
                    downloaded += 1
                else:
                    skipped += 1

        click.echo(
            f"  {script_code} complete: {downloaded} downloaded, {skipped} skipped"
        )
        total_downloaded += downloaded
        total_skipped += skipped

    click.echo(
        f"\nWikimedia harvest complete: {total_downloaded} downloaded, "
        f"{total_skipped} skipped."
    )


# ---------------------------------------------------------------------------
# harvest-met
# ---------------------------------------------------------------------------


@cli.command("harvest-met")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.pass_context
def harvest_met(ctx: click.Context, dry_run: bool) -> None:
    """Harvest from Metropolitan Museum Open Access API (~3-5 images, CC0).

    Downloads Armenian Gospel manuscript images (accession 57.185.3).
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "met"
    subdir.mkdir(parents=True, exist_ok=True)

    met_api = "https://collectionapi.metmuseum.org/public/collection/v1/objects"
    downloaded = 0

    for obj_id in _MET_ARMENIAN_OBJECTS:
        click.echo(f"\nFetching Met object {obj_id}...")
        try:
            resp = requests.get(
                f"{met_api}/{obj_id}",
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            obj = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            continue

        if not obj.get("isPublicDomain", False):
            click.echo(f"  [SKIP] Not public domain: {obj.get('title', '')}")
            continue

        title = obj.get("title", f"object_{obj_id}")
        click.echo(f"  Title: {title}")

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
                catalog_number=40,
                license_str="CC0",
                acquisition_method="met_open_access_api",
                output_dir=output_dir,
                script_iso15924="Armn",
                rate_limit=0.5,
            )
            if ok:
                downloaded += 1

    # Also search for Ethiopian, Coptic, Arabic Gospel manuscripts
    search_terms = [
        ("Ethiopian Gospel", "Ethi"),
        ("Ethiopian manuscript", "Ethi"),
        ("Coptic Gospel", "Copt"),
        ("Coptic manuscript", "Copt"),
        ("Arabic Bible", "Arab"),
        ("Arabic Gospel", "Arab"),
        ("Greek Gospel manuscript", "Grek"),
        ("Syriac Gospel", "Syrc"),
        ("Armenian Gospel", "Armn"),
        ("Armenian manuscript", "Armn"),
        ("Georgian Gospel", "Geor"),
    ]

    for search_term, script_code in search_terms:
        click.echo(f"\nSearching Met for '{search_term}'...")
        try:
            resp = requests.get(
                f"{met_api[:-8]}/search",
                params={
                    "q": search_term,
                    "isPublicDomain": "true",
                    "hasImages": "true",
                },
                headers={"User-Agent": _USER_AGENT},
                timeout=30,
            )
            resp.raise_for_status()
            search_results = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            continue

        object_ids = search_results.get("objectIDs", []) or []
        click.echo(f"  Found {len(object_ids)} objects")

        for obj_id in object_ids[:20]:  # Limit to 20 per search term
            try:
                resp = requests.get(
                    f"{met_api}/{obj_id}",
                    headers={"User-Agent": _USER_AGENT},
                    timeout=30,
                )
                resp.raise_for_status()
                obj = resp.json()
            except requests.RequestException:
                continue

            if not obj.get("isPublicDomain", False):
                continue

            # Check if it's actually a manuscript
            medium = obj.get("medium", "").lower()
            classification = obj.get("classification", "").lower()
            if not any(
                kw in medium or kw in classification
                for kw in ["ink", "parchment", "vellum", "manuscript", "codex", "leaf"]
            ):
                continue

            primary_img = obj.get("primaryImage", "")
            if not primary_img:
                continue

            obj_title = obj.get("title", f"object_{obj_id}")

            if dry_run:
                click.echo(f"    [DRY RUN] {obj_title} ({obj_id})")
                continue

            safe_title = obj_title.replace(" ", "_").replace("/", "_")[:80]
            filename = f"met_{obj_id}_{safe_title}.jpg"
            out_path = subdir / filename

            ok = _download_image(
                primary_img,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="met_museum",
                catalog_number=None,
                license_str="CC0",
                acquisition_method="met_open_access_api",
                output_dir=output_dir,
                script_iso15924=script_code,
                rate_limit=0.5,
            )
            if ok:
                downloaded += 1

            time.sleep(0.3)

    click.echo(f"\nMet harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-walters
# ---------------------------------------------------------------------------


@cli.command("harvest-walters")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=20,
    show_default=True,
    help="Max pages per manuscript (0 = all).",
)
@click.pass_context
def harvest_walters(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from The Digital Walters file server (~30-80 images, CC0).

    Downloads Armenian, Syriac, and Arabic Gospel manuscript page images
    from thedigitalwalters.org (SAP/web resolution JPEGs, ~1800px).
    All Walters manuscript images are CC0.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "walters"
    subdir.mkdir(parents=True, exist_ok=True)

    base_url = "https://www.thedigitalwalters.org/Data/WaltersManuscripts"
    downloaded = 0
    errors = 0

    for script_code, manuscripts in _WALTERS_MANUSCRIPTS.items():
        click.echo(f"\n{'='*60}")
        click.echo(f"Script: {script_code} ({len(manuscripts)} manuscripts)")
        click.echo(f"{'='*60}")

        for ms in manuscripts:
            w_num = ms["w_num"]
            name = ms["name"]
            pages = ms["pages"]

            click.echo(f"\n  Manuscript W.{w_num}: {name}")

            page_count = 0
            for page_num in pages:
                if 0 < max_pages <= page_count:
                    break

                # Digital Walters SAP (web) URL pattern
                fname = f"W{w_num}_{page_num:06d}_sap.jpg"
                url = f"{base_url}/W{w_num}/data/W.{w_num}/sap/{fname}"

                if dry_run:
                    if page_count < 3:
                        click.echo(f"    [DRY RUN] {url}")
                    elif page_count == 3:
                        click.echo("    ... and more pages")
                    page_count += 1
                    continue

                out_path = subdir / f"W{w_num}_{page_num:06d}.jpg"

                ok = _download_image(
                    url,
                    out_path,
                    sha_set=sha_set,
                    registry_path=registry_path,
                    source_institution="walters_art_museum",
                    catalog_number=None,
                    license_str="CC0",
                    acquisition_method="digital_walters_file_server",
                    output_dir=output_dir,
                    script_iso15924=script_code,
                    rate_limit=0.5,
                )
                if ok:
                    downloaded += 1
                    page_count += 1
                else:
                    errors += 1
                    # Stop if we get consecutive 404s (wrong page range)
                    if errors > 3:
                        click.echo(f"    Stopping W.{w_num} after {errors} errors")
                        errors = 0
                        break

            click.echo(f"    Downloaded {page_count} pages from W.{w_num}")

    click.echo(f"\nWalters harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-gallica
# ---------------------------------------------------------------------------


@cli.command("harvest-gallica")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=10,
    show_default=True,
    help="Max pages per manuscript to download (0 = all).",
)
@click.pass_context
def harvest_gallica(ctx: click.Context, dry_run: bool, max_pages: int) -> None:
    """Harvest from BnF/Gallica IIIF manifests (~20-40 images, PD).

    Downloads pages from pre-1850 Public Domain Gospel manuscripts.
    Focuses on folios containing or near John 1:1.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    downloaded = 0

    for ms in _GALLICA_MANUSCRIPTS:
        ark_id = ms["ark_id"]
        name = ms["name"]
        script_code = ms["script"]
        cat_num = ms["catalog_number"]

        subdir = output_dir / "gallica" / script_code.lower()
        subdir.mkdir(parents=True, exist_ok=True)

        manifest_url = f"https://gallica.bnf.fr/iiif/ark:/12148/{ark_id}/manifest.json"
        click.echo(f"\nFetching Gallica IIIF: {name} ({ark_id})")

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

        # Extract canvases (IIIF v2 or v3)
        canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
        if not canvases:
            canvases = manifest.get("items", [])

        click.echo(f"  Found {len(canvases)} canvases")

        if dry_run:
            limit = max_pages if max_pages > 0 else len(canvases)
            click.echo(f"  [DRY RUN] Would download up to {limit} pages")
            continue

        page_count = 0
        for i, canvas in enumerate(canvases):
            if 0 < max_pages <= page_count:
                break

            img_url = _extract_image_url_from_canvas(canvas)
            if not img_url:
                continue

            safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")[:60]
            filename = f"gallica_{safe_name}_{i:04d}.jpg"
            out_path = subdir / filename

            # Try full resolution; fall back to max 2048px
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
                    source_institution="bnf_gallica",
                    catalog_number=cat_num,
                    license_str="public_domain",
                    acquisition_method="iiif_manifest",
                    output_dir=output_dir,
                    script_iso15924=script_code,
                    rate_limit=1.0,
                )
                if ok:
                    break
            if ok:
                page_count += 1
                downloaded += 1

    click.echo(f"\nGallica harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# harvest-internet-archive
# ---------------------------------------------------------------------------


@cli.command("harvest-internet-archive")
@click.option("--dry-run", is_flag=True, help="Preview without downloading.")
@click.option(
    "--max-pages",
    type=int,
    default=20,
    show_default=True,
    help="Max page scans to download per item (0 = all).",
)
@click.pass_context
def harvest_internet_archive(
    ctx: click.Context, dry_run: bool, max_pages: int
) -> None:
    """Harvest from Internet Archive (~10-20 images, PD).

    Searches for Public Domain Latin/Greek Gospel facsimiles.
    """
    output_dir: Path = ctx.obj["output_dir"]
    registry_path: Path = ctx.obj["registry"]
    sha_set, _ = _load_registry(registry_path)
    subdir = output_dir / "internet_archive"
    subdir.mkdir(parents=True, exist_ok=True)

    # Known IA items containing Gospel of John facsimiles (PD)
    ia_items = [
        {
            "ia_id": "CodexSinaiticus",
            "name": "Codex Sinaiticus facsimile",
            "script": "Grek",
        },
        {
            "ia_id": "lindisfarnegosp00brit",
            "name": "Lindisfarne Gospels facsimile",
            "script": "Latn",
        },
    ]

    downloaded = 0

    for item in ia_items:
        ia_id = item["ia_id"]
        name = item["name"]
        script_code = item["script"]

        metadata_url = f"https://archive.org/metadata/{ia_id}"
        click.echo(f"\nFetching IA metadata: {name} ({ia_id})")

        try:
            resp = requests.get(metadata_url, timeout=30)
            resp.raise_for_status()
            metadata = resp.json()
        except requests.RequestException as exc:
            click.echo(f"  [ERROR] {exc}", err=True)
            continue

        files = metadata.get("files", [])
        image_files = [
            f
            for f in files
            if f.get("name", "").lower().endswith(
                (".jp2", ".jpg", ".jpeg", ".png", ".tif")
            )
            and f.get("source", "") != "metadata"
        ]

        click.echo(f"  Found {len(image_files)} image files")

        if dry_run:
            for f in image_files[:5]:
                click.echo(f"    [DRY RUN] {f['name']} ({f.get('size', '?')} bytes)")
            continue

        page_count = 0
        for f in image_files:
            if 0 < max_pages <= page_count:
                break

            fname = f["name"]
            url = f"https://archive.org/download/{ia_id}/{fname}"
            out_path = subdir / f"{ia_id}_{fname.replace('/', '_')}"

            ok = _download_image(
                url,
                out_path,
                sha_set=sha_set,
                registry_path=registry_path,
                source_institution="internet_archive",
                catalog_number=None,
                license_str="public_domain",
                acquisition_method="ia_download_api",
                output_dir=output_dir,
                script_iso15924=script_code,
                rate_limit=0.5,
            )
            if ok:
                page_count += 1
                downloaded += 1

    click.echo(f"\nInternet Archive harvest complete: {downloaded} downloaded.")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@cli.command("stats")
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show registry statistics by script, institution, and license."""
    registry_path: Path = ctx.obj["registry"]
    _, entries = _load_registry(registry_path)

    if not entries:
        click.echo("Registry is empty.")
        return

    click.echo(f"Total images: {len(entries)}")

    # By script
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

    # Tiered requirements
    tier_reqs = {
        "Grek": 200,
        "Latn": 200,
        "Ethi": 30,
        "Armn": 30,
        "Syrc": 10,
        "Arab": 10,
        "Cyrs": 10,
        "Copt": 10,
    }

    click.echo("\nBy script (vs tiered requirements):")
    for script, count in sorted(by_script.items(), key=lambda x: -x[1]):
        req = tier_reqs.get(script, 0)
        status = ""
        if req > 0:
            status = " OK" if count >= req else f" NEED {req - count} MORE"
        click.echo(f"  {script}: {count}{status}")

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
            f"  {name}: {info.get('license', '?')} "
            f"| Scripts: {info.get('scripts', [])}"
        )

    click.echo(f"\nNEEDS VERIFICATION ({len(unverified)} institutions):")
    for name, info in unverified:
        priority = info.get("verification_priority", "?")
        click.echo(
            f"  [{priority}] {name}: {info.get('verification_method', '?')}"
        )

    click.echo(f"\nBLOCKED ({len(blocked)} institutions):")
    for name, info in blocked:
        click.echo(f"  {name}: {info.get('notes', '?')[:80]}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
