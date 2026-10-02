"""End-to-end test of scripts/label_doc3d_warping_severity.py on synthetic data."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from click.testing import CliRunner

from scripts.label_doc3d_warping_severity import cli, unwarp

SIZE = 128
N = 40


def _texture(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = (rng.random((SIZE, SIZE)) * 255).astype(np.uint8)
    gray = cv2.GaussianBlur(noise, (0, 0), 1.5)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _bm(amplitude: float) -> np.ndarray:
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    out_y = ys + amplitude * np.sin(xs / SIZE * np.pi * 2)
    return np.stack([xs, out_y], axis=-1)


@pytest.fixture
def dataset(tmp_path: Path) -> tuple[Path, Path]:
    bm_dir, img_dir = tmp_path / "doc3d", tmp_path / "img" / "1"
    bm_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)
    amplitudes = np.linspace(0.5, 14.0, N)
    with zipfile.ZipFile(bm_dir / "bm_1.zip", "w") as archive:
        for i, amp in enumerate(amplitudes):
            npy = tmp_path / f"s{i}.npy"
            np.save(npy, _bm(float(amp)))
            archive.write(npy, f"bm/1/s{i}.npy")
            cv2.imwrite(str(img_dir / f"s{i}.png"), _texture(i))
    return bm_dir, tmp_path / "img"


@pytest.mark.unit
def test_pipeline_end_to_end(dataset: tuple[Path, Path], tmp_path: Path) -> None:
    bm_dir, img_dir = dataset
    raw, cal, final = (
        tmp_path / "raw.jsonl",
        tmp_path / "cal.json",
        tmp_path / "sev.jsonl",
    )
    runner = CliRunner()

    result = runner.invoke(cli, ["score", "--bm-dir", str(bm_dir), "--out", str(raw)])
    assert result.exit_code == 0, result.output
    assert f"scored={N}" in result.output

    result = runner.invoke(
        cli,
        ["calibrate", "--raw", str(raw), "--bm-dir", str(bm_dir), "--image-dir", str(img_dir),
         "--out", str(cal), "--sample", str(N)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "WARNING" not in result.output

    result = runner.invoke(
        cli,
        ["apply", "--raw", str(raw), "--calibration", str(cal), "--out", str(final)],
    )
    assert result.exit_code == 0, result.output

    rows = [json.loads(line) for line in final.read_text().splitlines()]
    raws = {
        json.loads(line)["id"]: json.loads(line)["raw"]
        for line in raw.read_text().splitlines()
    }
    assert len(rows) == N
    assert all(0.0 <= r["warping_severity"] <= 1.0 for r in rows)
    ordered = sorted(rows, key=lambda r: raws[r["id"]])
    sev = [r["warping_severity"] for r in ordered]
    assert sev == sorted(sev), "calibrated severity must be monotone in raw score"
    assert sev[-1] > sev[0]


@pytest.mark.unit
def test_spot_check_fails_loudly_when_no_maps(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    result = CliRunner().invoke(
        cli,
        [
            "score",
            "--bm-dir",
            str(tmp_path / "empty"),
            "--out",
            str(tmp_path / "o.jsonl"),
            "--spot-check",
            "5",
        ],
    )
    assert result.exit_code != 0
    assert "No usable backward maps" in result.output


@pytest.mark.unit
class TestUnwarp:
    def test_identity_pixel_map_is_noop(self) -> None:
        img = _texture(1)
        out = unwarp(img, _bm(0.0))
        assert out is not None
        assert np.abs(out.astype(int) - img.astype(int)).max() <= 1

    def test_normalised_identity_map_is_noop(self) -> None:
        img = _texture(2)
        ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
        bm = np.stack([xs / (SIZE - 1) * 2 - 1, ys / (SIZE - 1) * 2 - 1], axis=-1)
        out = unwarp(img, bm)
        assert out is not None
        assert np.abs(out.astype(int) - img.astype(int)).max() <= 1

    def test_bad_shape_returns_none(self) -> None:
        assert unwarp(_texture(3), np.zeros((SIZE, SIZE, 3))) is None


@pytest.mark.unit
def test_apply_with_image_dir_emits_training_fields(
    dataset: tuple[Path, Path], tmp_path: Path
) -> None:
    bm_dir, img_dir = dataset
    raw, cal, final = (
        tmp_path / "raw.jsonl",
        tmp_path / "cal.json",
        tmp_path / "sev.jsonl",
    )
    runner = CliRunner()
    runner.invoke(cli, ["score", "--bm-dir", str(bm_dir), "--out", str(raw)])
    runner.invoke(
        cli,
        ["calibrate", "--raw", str(raw), "--bm-dir", str(bm_dir), "--image-dir", str(img_dir),
         "--out", str(cal), "--sample", str(N)],
    )  # fmt: skip
    result = runner.invoke(
        cli,
        ["apply", "--raw", str(raw), "--calibration", str(cal), "--out", str(final),
         "--image-dir", str(img_dir)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    row = json.loads(final.read_text().splitlines()[0])
    assert row["image_path"].startswith("doc3d/img/1/s")
    assert row["mesh_id"] == "1"
    assert row["license"] == "MIT"


@pytest.mark.unit
def test_apply_with_no_matching_images_fails_instead_of_reporting_success(
    dataset: tuple[Path, Path], tmp_path: Path
) -> None:
    bm_dir, _ = dataset
    raw, cal, final = (
        tmp_path / "raw.jsonl",
        tmp_path / "cal.json",
        tmp_path / "sev.jsonl",
    )
    empty_images = tmp_path / "empty_img"
    empty_images.mkdir()
    runner = CliRunner()
    runner.invoke(cli, ["score", "--bm-dir", str(bm_dir), "--out", str(raw)])
    cal.write_text(json.dumps({"xs": [0.0, 1.0], "ys": [0.0, 1.0]}))
    result = runner.invoke(
        cli,
        ["apply", "--raw", str(raw), "--calibration", str(cal), "--out", str(final),
         "--image-dir", str(empty_images)],
    )  # fmt: skip
    assert result.exit_code != 0
    assert "no rows written" in result.output


@pytest.mark.unit
def test_calibrate_with_no_usable_pairs_is_a_clean_error(
    dataset: tuple[Path, Path], tmp_path: Path
) -> None:
    bm_dir, img_dir = dataset
    raw = tmp_path / "raw.jsonl"
    runner = CliRunner()
    runner.invoke(cli, ["score", "--bm-dir", str(bm_dir), "--out", str(raw)])
    for png in img_dir.rglob("*.png"):
        png.write_bytes(b"not a png")  # every image fails to load
    result = runner.invoke(
        cli,
        ["calibrate", "--raw", str(raw), "--bm-dir", str(bm_dir), "--image-dir", str(img_dir),
         "--out", str(tmp_path / "cal.json"), "--sample", str(N)],
    )  # fmt: skip
    assert result.exit_code != 0
    assert "calibration failed" in result.output
    assert "Traceback" not in result.output
