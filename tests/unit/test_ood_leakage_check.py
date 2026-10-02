"""`_check_ood_leakage`: detects leaks, and no longer passes silently when it hashes nothing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.prepare_multitask_datasets import _check_ood_leakage


def _registry(tmp_path: Path, *hashes: str) -> Path:
    path = tmp_path / "ood.jsonl"
    path.write_text("\n".join(json.dumps({"sha256": h}) for h in hashes) + "\n")
    return path


def _image(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.unit
def test_detects_leak_via_image_root(tmp_path: Path) -> None:
    digest = _image(tmp_path / "data" / "doc3d" / "a.png", b"ood-bytes")
    registry = _registry(tmp_path, digest)
    with pytest.raises(SystemExit) as exc:
        _check_ood_leakage(
            [{"image_path": "doc3d/a.png"}], registry, image_root=tmp_path / "data"
        )
    assert exc.value.code == 2


@pytest.mark.unit
def test_clean_samples_pass_and_report_hashed_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _image(tmp_path / "data" / "x.png", b"clean")
    registry = _registry(tmp_path, "0" * 64)
    _check_ood_leakage(
        [{"image_path": "x.png"}], registry, image_root=tmp_path / "data"
    )
    out = capsys.readouterr()
    assert "1 of 1 samples hashed" in out.out
    assert "WARNING" not in out.err


@pytest.mark.unit
def test_vacuous_pass_is_now_loudly_flagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Relative paths that resolve to nothing (wrong cwd) must not look like a clean pass."""
    registry = _registry(tmp_path, "0" * 64)
    samples = [{"image_path": "doc3d/img/1/a.png"}, {"image_path": "doc3d/img/1/b.png"}]
    _check_ood_leakage(samples, registry)  # no image_root, files do not exist
    out = capsys.readouterr()
    assert "hashed 0 of 2 samples" in out.err
    assert "NOT checked" in out.err
    assert "0 of 2 samples hashed" in out.out


@pytest.mark.unit
@pytest.mark.parametrize("rel", ["../secret.bin", "..\\secret.bin"])
def test_traversal_paths_are_never_hashed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], rel: str
) -> None:
    secret = tmp_path / "secret.bin"
    digest = _image(secret, b"secret")
    registry = _registry(tmp_path, digest)  # would raise if the file were hashed
    root = tmp_path / "data"
    root.mkdir()
    _check_ood_leakage([{"image_path": rel}], registry, image_root=root)
    assert "1 rejected as unsafe" in capsys.readouterr().err
