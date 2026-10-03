"""Restore lossless PNGs for datasets that were converted to JPEG (rvl-cdip, khatt).

Decision record: docs/planning/MASTER_PROJECT_PLAN.md ("Dataset format
remediation"). JPEG artifacts corrupt IQA labels, so the TIFF originals are
converted to PNG, verified, and only then may the JPEGs be retired.

Three explicit steps; nothing is deleted unless ``retire-jpeg --yes`` is given
and a fresh verification of the directories is clean. ``retire-jpeg`` never reads
paths from the report file, so a tampered report cannot delete files:

    convert      TIFF (dir or .zip) -> PNG, pixel-exact check on every file
    verify       every JPEG has a decodable PNG of identical dimensions
    retire-jpeg  re-verify, then delete the JPEGs found under --jpeg-dir

Naming: a PNG takes the TIFF's stem. If the TIFF names differ from the JPEG
names (true for the rvl-cdip subset), pass ``--mapping`` with a two-column CSV
``jpeg_stem,tiff_relative_path``; the PNG is then named after the JPEG stem.

Example:
    uv run python scripts/convert_tiff_to_png.py convert \\
        --src data/train.zip --src data/validation.zip --dest out/khatt_png
    uv run python scripts/convert_tiff_to_png.py verify \\
        --png-dir out/khatt_png --jpeg-dir 01_base_data/khatt --report out/report.json
    uv run python scripts/convert_tiff_to_png.py retire-jpeg \\
        --png-dir out/khatt_png --jpeg-dir 01_base_data/khatt   # dry run; add --yes
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import click
import numpy as np
from PIL import Image

_TIFF_SUFFIXES = {".tif", ".tiff"}
_JPEG_SUFFIXES = {".jpg", ".jpeg"}
# Modes PNG stores without changing any pixel value. Anything else (CMYK, I, F, ...)
# is rejected: converting it to RGB would silently lose data while still passing a
# round-trip check against the *converted* image.
_PNG_SAFE_MODES = {"1", "L", "LA", "P", "RGB", "RGBA", "I;16"}
DEFAULT_MAX_ENTRY_MB = 512
# Sanity check before a JPEG may be retired: a lossless PNG of the same page differs
# from its JPEG only by compression noise, which averages out at this scale.
_CONTENT_SIZE = (128, 128)
DEFAULT_MAX_CONTENT_DIFF = 4.0


def _check_size(name: str, size: int, max_bytes: int) -> None:
    if size > max_bytes:
        msg = f"{name}: {size} bytes exceeds the {max_bytes}-byte entry limit"
        raise ValueError(msg)


def _iter_zip_tiffs(
    source: Path, max_bytes: int
) -> Iterator[tuple[str, Callable[[], bytes]]]:
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            if Path(info.filename).suffix.lower() in _TIFF_SUFFIXES:
                yield info.filename, _zip_loader(archive, info, max_bytes)


def _iter_dir_tiffs(
    source: Path, max_bytes: int
) -> Iterator[tuple[str, Callable[[], bytes]]]:
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() in _TIFF_SUFFIXES:
            yield str(path.relative_to(source)), _file_loader(path, max_bytes)


def iter_tiffs(
    sources: tuple[Path, ...], max_bytes: int
) -> Iterator[tuple[str, Callable[[], bytes]]]:
    """Yield ``(relative_name, loader)`` for every TIFF in directories or zips.

    Bytes are read lazily by calling ``loader()``, which refuses entries larger
    than ``max_bytes`` *before* decompressing/reading them.
    """
    for source in sources:
        if source.is_file() and source.suffix == ".zip":
            yield from _iter_zip_tiffs(source, max_bytes)
        else:
            yield from _iter_dir_tiffs(source, max_bytes)


def _zip_loader(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo, max_bytes: int
) -> Callable[[], bytes]:
    def load() -> bytes:
        _check_size(info.filename, info.file_size, max_bytes)
        return archive.read(info)

    return load


def _file_loader(path: Path, max_bytes: int) -> Callable[[], bytes]:
    def load() -> bytes:
        _check_size(path.name, path.stat().st_size, max_bytes)
        return path.read_bytes()

    return load


def tiff_bytes_to_png(data: bytes, dest: Path) -> tuple[int, int]:
    """Write PNG for the TIFF bytes; raise if it cannot be stored losslessly.

    Raises:
        ValueError: Unsupported (non-lossless) mode, or round trip not pixel-exact.

    Returns ``(width, height)``.
    """
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        if img.mode not in _PNG_SAFE_MODES:
            msg = (
                f"mode {img.mode!r} cannot be stored in PNG without changing pixel "
                "values; convert it deliberately outside this script"
            )
            raise ValueError(msg)
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="PNG")
        expected = np.asarray(img)
        size = img.size
    with Image.open(dest) as check:
        if not np.array_equal(np.asarray(check), expected):
            dest.unlink(missing_ok=True)
            msg = f"PNG round trip not pixel-exact for {dest.name}"
            raise ValueError(msg)
    return size


def _index_by_stem(paths: Iterable[Path]) -> tuple[dict[str, Path], list[str]]:
    """Map stem -> path for stems that occur once; also list ambiguous stems."""
    grouped: dict[str, list[Path]] = {}
    for path in paths:
        grouped.setdefault(path.stem, []).append(path)
    unique = {stem: found[0] for stem, found in grouped.items() if len(found) == 1}
    return unique, sorted(stem for stem, found in grouped.items() if len(found) > 1)


def _content_distance(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute grayscale difference at a coarse common scale (0-255)."""
    ga = np.asarray(
        a.convert("L").resize(_CONTENT_SIZE, Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    gb = np.asarray(
        b.convert("L").resize(_CONTENT_SIZE, Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    return float(np.mean(np.abs(ga - gb)))


def verify_pngs(
    png_dir: Path,
    jpeg_dir: Path,
    max_content_diff: float = DEFAULT_MAX_CONTENT_DIFF,
) -> dict[str, Any]:
    """Compare the JPEG set with the PNG set; return a report dict.

    A JPEG is verified only if its stem matches exactly one PNG, both decode, the
    sizes are equal, and the pictures agree at a coarse scale (so an unrelated
    PNG that happens to share a stem and size cannot authorise deletion). Stems
    occurring more than once on either side are ``ambiguous`` and block retirement.
    """
    jpeg_root = jpeg_dir.resolve()
    jpeg_paths = [
        p
        for p in jpeg_root.rglob("*")
        if p.suffix.lower() in _JPEG_SUFFIXES
        and p.is_file()
        and not p.is_symlink()
        and p.resolve().is_relative_to(jpeg_root)  # never act outside the JPEG tree
    ]
    jpegs, dup_jpeg = _index_by_stem(jpeg_paths)
    pngs, dup_png = _index_by_stem(png_dir.rglob("*.png"))
    ambiguous = sorted(set(dup_jpeg) | set(dup_png))
    missing = sorted(set(jpegs) - set(pngs) - set(ambiguous))
    extra = sorted(set(pngs) - set(jpegs) - set(ambiguous))
    bad: list[str] = []
    verified: list[str] = []
    for stem in sorted(set(jpegs) & set(pngs)):
        problem = _compare(jpegs[stem], pngs[stem], max_content_diff)
        if problem:
            bad.append(f"{stem}: {problem}")
        else:
            verified.append(str(jpegs[stem]))
    return {
        "jpeg_count": len(jpeg_paths),
        "png_count": len(pngs) + len(dup_png),
        "missing_png": missing,
        "extra_png": extra,
        "ambiguous_stems": ambiguous,
        "bad": bad,
        "verified_jpegs": verified,
        "ok": not missing
        and not bad
        and not ambiguous
        and len(verified) == len(jpeg_paths),
    }


def _compare(jpeg: Path, png: Path, max_content_diff: float) -> str | None:
    """None if the PNG verifiably replaces the JPEG, else a short reason."""
    try:
        with Image.open(jpeg) as j, Image.open(png) as p:
            p.load()
            j.load()
            if j.size != p.size:
                return f"size {j.size} != {p.size}"
            distance = _content_distance(j, p)
    except OSError as exc:
        return str(exc)
    if distance > max_content_diff:
        return f"content mismatch (mean abs diff {distance:.1f} > {max_content_diff})"
    return None


@click.group()
def cli() -> None:
    """TIFF -> PNG lossless remediation."""


@cli.command()
@click.option(
    "--src",
    "sources",
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--dest", type=click.Path(path_type=Path), required=True)
@click.option("--mapping", type=click.Path(exists=True, path_type=Path), default=None)
@click.option(
    "--max-entry-mb",
    type=int,
    default=DEFAULT_MAX_ENTRY_MB,
    show_default=True,
    help="Refuse TIFF entries larger than this before reading them into memory.",
)
def convert(
    sources: tuple[Path, ...], dest: Path, mapping: Path | None, max_entry_mb: int
) -> None:
    """Convert TIFFs to pixel-exact PNGs (fails closed on anything lossy or ambiguous)."""
    rename: dict[str, str] = {}
    if mapping is not None:
        with mapping.open(newline="", encoding="utf-8") as fh:
            rename = {
                Path(row[1]).as_posix(): row[0]
                for row in csv.reader(fh)
                if len(row) >= 2
            }
    done = failed = 0
    planned: dict[str, str] = {}  # output stem -> source name that claimed it
    for name, load in iter_tiffs(sources, max_entry_mb * 1024 * 1024):
        key = Path(name).as_posix()
        if rename and key not in rename:
            continue
        out_stem = Path(rename[key] if rename else Path(name).stem).stem
        if not out_stem:
            failed += 1
            click.echo(f"FAILED {name}: empty output name", err=True)
            continue
        if out_stem in planned:
            failed += 1
            click.echo(
                f"FAILED {name}: output name {out_stem!r} already used by "
                f"{planned[out_stem]!r}; refusing to overwrite (use --mapping)",
                err=True,
            )
            continue
        planned[out_stem] = name
        try:
            tiff_bytes_to_png(load(), dest / f"{out_stem}.png")
            done += 1
        except (OSError, ValueError) as exc:
            failed += 1
            click.echo(f"FAILED {name}: {exc}", err=True)
    click.echo(f"converted={done} failed={failed}")
    if failed:
        raise click.ClickException(f"{failed} conversions failed")


_CONTENT_DIFF_OPTION = click.option(
    "--max-content-diff",
    type=float,
    default=DEFAULT_MAX_CONTENT_DIFF,
    show_default=True,
    help="Largest mean grayscale difference (0-255, at 128x128) between a JPEG and "
    "its PNG. A coarse same-picture sanity check, not proof of provenance.",
)


@cli.command()
@click.option("--png-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jpeg-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--report", type=click.Path(path_type=Path), required=True)
@_CONTENT_DIFF_OPTION
def verify(
    png_dir: Path, jpeg_dir: Path, report: Path, max_content_diff: float
) -> None:
    """Check every JPEG has exactly one decodable, same-size, same-looking PNG."""
    result = verify_pngs(png_dir, jpeg_dir, max_content_diff)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    click.echo(
        f"jpeg={result['jpeg_count']} png={result['png_count']} "
        f"missing={len(result['missing_png'])} bad={len(result['bad'])} "
        f"ambiguous={len(result['ambiguous_stems'])} ok={result['ok']}"
    )
    if not result["ok"]:
        raise click.ClickException("verification failed; see report")


@cli.command("retire-jpeg")
@click.option("--png-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jpeg-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--yes", is_flag=True, help="Actually delete (default is a dry run).")
@_CONTENT_DIFF_OPTION
def retire_jpeg(
    png_dir: Path, jpeg_dir: Path, yes: bool, max_content_diff: float
) -> None:
    """Re-verify, then delete the JPEGs under --jpeg-dir that have a matching PNG.

    Deletion targets are recomputed here from the directory contents (regular,
    non-symlink files inside --jpeg-dir only); no path is read from a report.
    """
    result = verify_pngs(png_dir, jpeg_dir, max_content_diff)
    if not result["ok"]:
        raise click.ClickException(
            f"verification failed (missing={len(result['missing_png'])} "
            f"bad={len(result['bad'])} ambiguous={len(result['ambiguous_stems'])}); "
            "refusing to delete anything"
        )
    paths = [Path(p) for p in result["verified_jpegs"]]
    if not yes:
        click.echo(f"dry run: would delete {len(paths)} JPEGs (re-run with --yes)")
        return
    for path in paths:
        path.unlink(missing_ok=True)
    click.echo(f"deleted {len(paths)} JPEGs")


if __name__ == "__main__":
    cli()
