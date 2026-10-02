"""Tests for scripts/convert_tiff_to_png.py."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner, Result
from PIL import Image

from scripts.convert_tiff_to_png import cli, tiff_bytes_to_png, verify_pngs


def _picture(seed: int, size: tuple[int, int]) -> Image.Image:
    """A structured grayscale picture; different seeds look different at coarse scale."""
    width, height = size
    ys, xs = np.mgrid[0:height, 0:width]
    base = ((xs * (seed + 1) + ys * (3 - seed % 3)) % 256).astype(np.uint8)
    x0, y0 = (seed * 7) % max(width // 2, 1), (seed * 5) % max(height // 2, 1)
    base[y0 : y0 + height // 3, x0 : x0 + width // 3] = 255 - base[y0, x0]
    return Image.fromarray(base, "L")


def _make(path: Path, seed: int, size: tuple[int, int]) -> Path:
    """Write the picture to ``path`` (format from the suffix; JPEGs at high quality)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {"quality": 95} if path.suffix.lower() in {".jpg", ".jpeg"} else {}
    _picture(seed, size).save(path, **kwargs)
    return path


@pytest.fixture
def khatt_like(tmp_path: Path) -> tuple[Path, Path]:
    """A TIFF zip plus matching JPEG dir (each JPEG is the same picture as its TIFF)."""
    tiffs, jpegs = tmp_path / "tiffs", tmp_path / "jpegs"
    for seed, (stem, size) in enumerate({"a": (160, 120), "b": (180, 90)}.items()):
        _make(tiffs / f"{stem}.tif", seed, size)
        _make(jpegs / f"{stem}.jpg", seed, size)
    zip_path = tmp_path / "train.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for p in sorted(tiffs.glob("*.tif")):
            z.write(p, f"train/{p.name}")
    return zip_path, jpegs


def _run(*args: str | Path) -> Result:
    return CliRunner().invoke(cli, [str(a) for a in args])


@pytest.mark.unit
def test_roundtrip_is_pixel_exact(tmp_path: Path) -> None:
    tif = _make(tmp_path / "x.tif", 1, (32, 16))
    size = tiff_bytes_to_png(tif.read_bytes(), tmp_path / "x.png")
    assert size == (32, 16)


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["CMYK", "I", "F"])
def test_modes_png_cannot_hold_losslessly_are_rejected(
    tmp_path: Path, mode: str
) -> None:
    """Converting these to RGB would lose data yet still pass a round-trip check."""
    tif = tmp_path / "m.tif"
    Image.new(mode, (8, 8)).save(tif)
    data = tif.read_bytes()
    with pytest.raises(ValueError, match="cannot be stored in PNG"):
        tiff_bytes_to_png(data, tmp_path / "m.png")
    assert not (tmp_path / "m.png").exists()


@pytest.mark.unit
def test_convert_verify_retire_flow(
    khatt_like: tuple[Path, Path], tmp_path: Path
) -> None:
    zip_path, jpegs = khatt_like
    out, report = tmp_path / "png", tmp_path / "report.json"

    converted = _run("convert", "--src", zip_path, "--dest", out)
    assert converted.exit_code == 0, converted.output
    verified = _run("verify", "--png-dir", out, "--jpeg-dir", jpegs, "--report", report)
    assert verified.exit_code == 0, verified.output

    args = ["retire-jpeg", "--png-dir", out, "--jpeg-dir", jpegs]
    dry = _run(*args)
    assert "dry run" in dry.output
    assert len(list(jpegs.glob("*.jpg"))) == 2  # nothing deleted without --yes

    retired = _run(*args, "--yes")
    assert retired.exit_code == 0, retired.output
    assert list(jpegs.glob("*.jpg")) == []


@pytest.mark.unit
def test_oversized_zip_entry_is_refused_before_reading(tmp_path: Path) -> None:
    tif = _make(tmp_path / "big.tif", 2, (200, 200))
    zip_path = tmp_path / "z.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(tif, "big.tif")
    result = _run(
        "convert", "--src", zip_path, "--dest", tmp_path / "o", "--max-entry-mb", "0"
    )
    assert result.exit_code != 0
    assert "exceeds" in result.output
    assert not list((tmp_path / "o").glob("*.png"))


@pytest.mark.unit
def test_duplicate_output_names_are_refused_not_overwritten(tmp_path: Path) -> None:
    src = tmp_path / "t"
    _make(src / "d1" / "page.tif", 1, (40, 30))
    _make(src / "d2" / "page.tif", 2, (50, 20))  # same stem, different picture
    out = tmp_path / "out"
    result = _run("convert", "--src", src, "--dest", out)
    assert result.exit_code != 0
    assert "already used" in result.output
    assert len(list(out.glob("*.png"))) == 1  # first kept, second not overwritten


@pytest.mark.unit
def test_verify_flags_missing_and_size_mismatch(tmp_path: Path) -> None:
    jpegs, pngs = tmp_path / "j", tmp_path / "p"
    _make(jpegs / "a.jpg", 1, (160, 120))
    _make(jpegs / "b.jpg", 2, (160, 120))
    _make(pngs / "a.png", 1, (161, 120))  # wrong size; b.png missing
    report = verify_pngs(pngs, jpegs)
    assert report["ok"] is False
    assert report["missing_png"] == ["b"]
    assert len(report["bad"]) == 1


@pytest.mark.unit
def test_unrelated_png_with_same_stem_and_size_does_not_verify(tmp_path: Path) -> None:
    """Dimensions + stem alone must not authorise deleting a JPEG."""
    jpegs, pngs = tmp_path / "j", tmp_path / "p"
    _make(jpegs / "a.jpg", 1, (160, 120))
    _make(pngs / "a.png", 4, (160, 120))  # different picture, identical size
    report = verify_pngs(pngs, jpegs)
    assert report["ok"] is False
    assert "content mismatch" in report["bad"][0]
    result = _run("retire-jpeg", "--png-dir", pngs, "--jpeg-dir", jpegs, "--yes")
    assert result.exit_code != 0
    assert (jpegs / "a.jpg").exists()


@pytest.mark.unit
def test_duplicate_stems_make_matching_ambiguous_and_block_retirement(
    tmp_path: Path,
) -> None:
    jpegs, pngs = tmp_path / "j", tmp_path / "p"
    _make(jpegs / "x" / "a.jpg", 1, (160, 120))
    _make(jpegs / "y" / "a.jpg", 1, (160, 120))  # two JPEGs share a stem
    _make(pngs / "a.png", 1, (160, 120))
    report = verify_pngs(pngs, jpegs)
    assert report["ambiguous_stems"] == ["a"]
    assert report["ok"] is False
    result = _run("retire-jpeg", "--png-dir", pngs, "--jpeg-dir", jpegs, "--yes")
    assert result.exit_code != 0
    assert len(list(jpegs.rglob("*.jpg"))) == 2


@pytest.mark.unit
def test_retire_refuses_when_verification_fails(tmp_path: Path) -> None:
    jpeg = _make(tmp_path / "j" / "a.jpg", 1, (80, 60))
    (tmp_path / "p").mkdir()  # no PNGs: verification must fail
    result = _run(
        "retire-jpeg",
        "--png-dir",
        tmp_path / "p",
        "--jpeg-dir",
        tmp_path / "j",
        "--yes",
    )
    assert result.exit_code != 0
    assert jpeg.exists()


@pytest.mark.unit
def test_retire_ignores_tampered_report_and_never_deletes_outside_jpeg_dir(
    tmp_path: Path,
) -> None:
    """A report listing an outside file must have no effect: paths are not read from it."""
    victim = tmp_path / "precious.txt"
    victim.write_text("keep me")
    jpeg = _make(tmp_path / "j" / "a.jpg", 1, (160, 120))
    png_dir = tmp_path / "p"
    _make(png_dir / "a.png", 1, (160, 120))
    (tmp_path / "r.json").write_text(
        json.dumps({"ok": True, "verified_jpegs": [str(victim)]})
    )

    result = _run(
        "retire-jpeg", "--png-dir", png_dir, "--jpeg-dir", tmp_path / "j", "--yes"
    )
    assert result.exit_code == 0, result.output
    assert victim.exists()
    assert not jpeg.exists()


@pytest.mark.unit
def test_symlinked_jpeg_is_not_followed_or_deleted(tmp_path: Path) -> None:
    outside = _make(tmp_path / "outside" / "secret.jpg", 1, (160, 120))
    jdir, pdir = tmp_path / "j", tmp_path / "p"
    jdir.mkdir()
    (jdir / "link.jpg").symlink_to(outside)
    _make(pdir / "link.png", 1, (160, 120))
    report = verify_pngs(pdir, jdir)
    assert report["jpeg_count"] == 0  # symlink ignored
    result = _run("retire-jpeg", "--png-dir", pdir, "--jpeg-dir", jdir, "--yes")
    assert result.exit_code == 0
    assert outside.exists()


@pytest.mark.unit
def test_mapping_renames_output_to_jpeg_stem(tmp_path: Path) -> None:
    tiffs = tmp_path / "t"
    _make(tiffs / "imagesa" / "aa" / "hash123.tif", 1, (32, 32))
    _make(tiffs / "imagesa" / "aa" / "other.tif", 2, (32, 32))
    mapping = tmp_path / "m.csv"
    mapping.write_text("rvl_letter_0001,imagesa/aa/hash123.tif\n")
    out = tmp_path / "out"
    result = _run("convert", "--src", tiffs, "--dest", out, "--mapping", mapping)
    assert result.exit_code == 0, result.output
    assert [p.name for p in out.glob("*.png")] == ["rvl_letter_0001.png"]
