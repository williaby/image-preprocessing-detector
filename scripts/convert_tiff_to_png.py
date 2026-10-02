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
from pathlib import Path
from typing import Any

import click
import numpy as np
from PIL import Image

_TIFF_SUFFIXES = {".tif", ".tiff"}
_JPEG_SUFFIXES = {".jpg", ".jpeg"}
_PNG_SAFE_MODES = {"1", "L", "LA", "P", "RGB", "RGBA", "I;16"}


def iter_tiffs(sources: tuple[Path, ...]) -> Any:
    """Yield ``(relative_name, bytes)`` for every TIFF in directories or zips."""
    for source in sources:
        if source.is_file() and source.suffix == ".zip":
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    if Path(name).suffix.lower() in _TIFF_SUFFIXES:
                        yield name, archive.read(name)
        else:
            for path in sorted(source.rglob("*")):
                if path.suffix.lower() in _TIFF_SUFFIXES:
                    yield str(path.relative_to(source)), path.read_bytes()


def tiff_bytes_to_png(data: bytes, dest: Path) -> tuple[int, int]:
    """Write PNG for the TIFF bytes; raise if the round trip is not pixel-exact.

    Returns ``(width, height)``.
    """
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        image = img if img.mode in _PNG_SAFE_MODES else img.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, format="PNG")
        expected = np.asarray(image)
        size = image.size
    with Image.open(dest) as check:
        if not np.array_equal(np.asarray(check), expected):
            dest.unlink(missing_ok=True)
            msg = f"PNG round trip not pixel-exact for {dest.name}"
            raise ValueError(msg)
    return size


def verify_pngs(png_dir: Path, jpeg_dir: Path) -> dict[str, Any]:
    """Compare JPEG set against PNG set by stem; return a report dict."""
    jpeg_root = jpeg_dir.resolve()
    jpegs = {
        p.stem: p
        for p in jpeg_root.rglob("*")
        if p.suffix.lower() in _JPEG_SUFFIXES
        and p.is_file()
        and not p.is_symlink()
        and p.resolve().is_relative_to(jpeg_root)  # never act outside the JPEG tree
    }
    pngs = {p.stem: p for p in png_dir.rglob("*.png")}
    missing = sorted(set(jpegs) - set(pngs))
    extra = sorted(set(pngs) - set(jpegs))
    bad: list[str] = []
    verified: list[str] = []
    for stem in sorted(set(jpegs) & set(pngs)):
        try:
            with Image.open(jpegs[stem]) as j, Image.open(pngs[stem]) as p:
                p.load()
                if j.size != p.size:
                    bad.append(f"{stem}: size {j.size} != {p.size}")
                    continue
        except OSError as exc:
            bad.append(f"{stem}: {exc}")
            continue
        verified.append(str(jpegs[stem]))
    return {
        "jpeg_count": len(jpegs),
        "png_count": len(pngs),
        "missing_png": missing,
        "extra_png": extra,
        "bad": bad,
        "verified_jpegs": verified,
        "ok": not missing and not bad and len(verified) == len(jpegs),
    }


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
def convert(sources: tuple[Path, ...], dest: Path, mapping: Path | None) -> None:
    """Convert TIFFs to pixel-exact PNGs."""
    rename: dict[str, str] = {}
    if mapping is not None:
        with mapping.open(newline="", encoding="utf-8") as fh:
            rename = {
                Path(row[1]).as_posix(): row[0]
                for row in csv.reader(fh)
                if len(row) >= 2
            }
    done = failed = 0
    for name, data in iter_tiffs(sources):
        out_stem = (
            rename.get(Path(name).as_posix(), Path(name).stem)
            if rename
            else Path(name).stem
        )
        if rename and Path(name).as_posix() not in rename:
            continue
        try:
            tiff_bytes_to_png(data, dest / f"{Path(out_stem).stem}.png")
            done += 1
        except (OSError, ValueError) as exc:
            failed += 1
            click.echo(f"FAILED {name}: {exc}", err=True)
    click.echo(f"converted={done} failed={failed}")
    if failed:
        raise click.ClickException(f"{failed} conversions failed")


@cli.command()
@click.option("--png-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jpeg-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--report", type=click.Path(path_type=Path), required=True)
def verify(png_dir: Path, jpeg_dir: Path, report: Path) -> None:
    """Check every JPEG has a decodable PNG of identical size."""
    result = verify_pngs(png_dir, jpeg_dir)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    click.echo(
        f"jpeg={result['jpeg_count']} png={result['png_count']} "
        f"missing={len(result['missing_png'])} bad={len(result['bad'])} ok={result['ok']}"
    )
    if not result["ok"]:
        raise click.ClickException("verification failed; see report")


@cli.command("retire-jpeg")
@click.option("--png-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jpeg-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--yes", is_flag=True, help="Actually delete (default is a dry run).")
def retire_jpeg(png_dir: Path, jpeg_dir: Path, yes: bool) -> None:
    """Re-verify, then delete the JPEGs under --jpeg-dir that have a matching PNG.

    Deletion targets are recomputed here from the directory contents (regular,
    non-symlink files inside --jpeg-dir only); no path is read from a report.
    """
    result = verify_pngs(png_dir, jpeg_dir)
    if not result["ok"]:
        raise click.ClickException(
            f"verification failed (missing={len(result['missing_png'])} "
            f"bad={len(result['bad'])}); refusing to delete anything"
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
