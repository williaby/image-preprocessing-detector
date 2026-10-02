"""Tests for scripts/convert_tiff_to_png.py."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner
from PIL import Image

from scripts.convert_tiff_to_png import cli, tiff_bytes_to_png, verify_pngs


def _make(tmp: Path, name: str, size: tuple[int, int], mode: str = "L") -> Path:
    rng = np.random.default_rng(abs(hash(name)) % 1000)
    arr = (rng.random((size[1], size[0])) * 255).astype(np.uint8)
    img = Image.fromarray(arr, "L").convert(mode)
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


@pytest.fixture
def khatt_like(tmp_path: Path) -> tuple[Path, Path]:
    """A TIFF zip plus matching JPEG dir."""
    tiffs, jpegs = tmp_path / "tiffs", tmp_path / "jpegs"
    for stem, size in {"a": (40, 30), "b": (50, 20)}.items():
        _make(tiffs, f"{stem}.tif", size)
        _make(jpegs, f"{stem}.jpg", size)
    zip_path = tmp_path / "train.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for p in sorted(tiffs.glob("*.tif")):
            z.write(p, f"train/{p.name}")
    return zip_path, jpegs


@pytest.mark.unit
def test_roundtrip_is_pixel_exact_and_rejects_nothing_for_gray(tmp_path: Path) -> None:
    tif = _make(tmp_path, "x.tif", (32, 16))
    assert tiff_bytes_to_png(tif.read_bytes(), tmp_path / "x.png") == (32, 16)


@pytest.mark.unit
def test_cmyk_converted_to_rgb(tmp_path: Path) -> None:
    img = Image.new("CMYK", (8, 8), (10, 20, 30, 40))
    tif = tmp_path / "c.tif"
    img.save(tif)
    tiff_bytes_to_png(tif.read_bytes(), tmp_path / "c.png")
    assert Image.open(tmp_path / "c.png").mode == "RGB"


@pytest.mark.unit
def test_convert_verify_retire_flow(
    khatt_like: tuple[Path, Path], tmp_path: Path
) -> None:
    zip_path, jpegs = khatt_like
    out, report = tmp_path / "png", tmp_path / "report.json"
    runner = CliRunner()

    assert (
        runner.invoke(
            cli, ["convert", "--src", str(zip_path), "--dest", str(out)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            cli,
            [
                "verify",
                "--png-dir",
                str(out),
                "--jpeg-dir",
                str(jpegs),
                "--report",
                str(report),
            ],
        ).exit_code
        == 0
    )

    args = ["retire-jpeg", "--png-dir", str(out), "--jpeg-dir", str(jpegs)]
    dry = runner.invoke(cli, args)
    assert "dry run" in dry.output
    assert len(list(jpegs.glob("*.jpg"))) == 2  # nothing deleted without --yes

    assert runner.invoke(cli, [*args, "--yes"]).exit_code == 0
    assert list(jpegs.glob("*.jpg")) == []


@pytest.mark.unit
def test_verify_flags_missing_and_size_mismatch(tmp_path: Path) -> None:
    jpegs, pngs = tmp_path / "j", tmp_path / "p"
    _make(jpegs, "a.jpg", (40, 30))
    _make(jpegs, "b.jpg", (40, 30))
    _make(pngs, "a.png", (41, 30))  # wrong size; b.png missing
    report = verify_pngs(pngs, jpegs)
    assert report["ok"] is False
    assert report["missing_png"] == ["b"]
    assert len(report["bad"]) == 1


@pytest.mark.unit
def test_retire_refuses_when_verification_fails(tmp_path: Path) -> None:
    jpeg = _make(tmp_path / "j", "a.jpg", (8, 8))
    (tmp_path / "p").mkdir()  # no PNGs: verification must fail
    result = CliRunner().invoke(
        cli,
        [
            "retire-jpeg",
            "--png-dir",
            str(tmp_path / "p"),
            "--jpeg-dir",
            str(tmp_path / "j"),
            "--yes",
        ],
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
    jpeg = _make(tmp_path / "j", "a.jpg", (8, 8))
    png_dir = tmp_path / "p"
    _make(png_dir, "a.png", (8, 8))
    (tmp_path / "r.json").write_text(
        json.dumps({"ok": True, "verified_jpegs": [str(victim)]})
    )

    result = CliRunner().invoke(
        cli,
        [
            "retire-jpeg",
            "--png-dir",
            str(png_dir),
            "--jpeg-dir",
            str(tmp_path / "j"),
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output
    assert victim.exists()
    assert not jpeg.exists()


@pytest.mark.unit
def test_symlinked_jpeg_is_not_followed_or_deleted(tmp_path: Path) -> None:
    outside = _make(tmp_path / "outside", "secret.jpg", (8, 8))
    jdir, pdir = tmp_path / "j", tmp_path / "p"
    jdir.mkdir()
    (jdir / "link.jpg").symlink_to(outside)
    _make(pdir, "link.png", (8, 8))
    assert verify_pngs(pdir, jdir)["jpeg_count"] == 0  # symlink ignored
    result = CliRunner().invoke(
        cli, ["retire-jpeg", "--png-dir", str(pdir), "--jpeg-dir", str(jdir), "--yes"]
    )
    assert result.exit_code == 0
    assert outside.exists()


@pytest.mark.unit
def test_mapping_renames_output_to_jpeg_stem(tmp_path: Path) -> None:
    tiffs = tmp_path / "t"
    _make(tiffs, "imagesa/aa/hash123.tif", (16, 16))
    _make(tiffs, "imagesa/aa/other.tif", (16, 16))
    mapping = tmp_path / "m.csv"
    mapping.write_text("rvl_letter_0001,imagesa/aa/hash123.tif\n")
    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli,
        ["convert", "--src", str(tiffs), "--dest", str(out), "--mapping", str(mapping)],
    )
    assert result.exit_code == 0, result.output
    assert [p.name for p in out.glob("*.png")] == ["rvl_letter_0001.png"]
