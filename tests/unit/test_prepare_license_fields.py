"""License provenance on manifests and --exclude-license-class at merge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import scripts.prepare_multitask_datasets as pmd


def _rec(path: str, dataset: str | None, **extra: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "image_path": path,
        "warping": 0.3,
        "split": "train",
        **extra,
    }
    if dataset:
        rec["source_dataset"] = dataset
    return rec


@pytest.fixture
def stubbed_gcs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub GCS so merge runs offline; returns the uploaded object names."""
    uploaded: list[str] = []
    monkeypatch.setattr(pmd, "_get_gcs_bucket", lambda _name: object())
    monkeypatch.setattr(
        pmd,
        "_upload_manifest",
        lambda _recs, _bucket, key, dry_run=False: uploaded.append(key),
    )
    return uploaded


@pytest.mark.unit
def test_task_manifest_records_carry_license_fields(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {"image_path": "doc3d/img/1/a.png", "mesh_id": "1", "warping_severity": 0.4}
        )
        + "\n"
    )
    out = tmp_path / "out"
    result = CliRunner().invoke(
        pmd.cli,
        ["warping", "--synthetic-metadata", str(tmp_path / "none.json"),
         "--l2-metadata-dir", str(tmp_path / "no_l2"), "--output-dir", str(out),
         "--extra-real-labels", str(labels)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    rec = json.loads((out / "warping_manifest.json").read_text())[0]
    # doc3d row had no license: dataset unknown to the L2 path -> must NOT default to eligible.
    assert rec["license_class"] == "unspecified"
    assert "license" in rec


@pytest.mark.unit
def test_merge_excludes_license_classes(tmp_path: Path, stubbed_gcs: list[str]) -> None:
    task_dir = tmp_path / "warping_training"
    task_dir.mkdir()
    records = [
        _rec("a.png", "sd7k"),  # MIT
        _rec("b.png", "wsrd"),  # CC-BY-NC-SA
        _rec("c.png", "anyphotodoc6300"),  # GPL
        _rec("d.png", "warpdoc"),  # unspecified
        _rec("e.png", None, provenance="synthetic_v3"),  # generated
    ]
    (task_dir / "warping_manifest.json").write_text(json.dumps(records))
    out = tmp_path / "merged"
    result = CliRunner().invoke(
        pmd.cli,
        ["merge", "--warping-dir", str(task_dir), "--output-dir", str(out),
         "--gcs-output-prefix", "gs://bucket/prefix",
         "--exclude-license-class", "non_commercial",
         "--exclude-license-class", "copyleft_gpl",
         "--exclude-license-class", "unspecified"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "Excluded 3 records" in result.output
    # dry_run False here, so local manifests are written
    kept = json.loads((out / "train_manifest.json").read_text())
    assert sorted(Path(r["image_path"]).name for r in kept) == ["a.png", "e.png"]
    assert {r["license_class"] for r in kept} == {"permissive", "generated"}


@pytest.mark.unit
def test_merge_refuses_when_everything_is_excluded(
    tmp_path: Path, stubbed_gcs: list[str]
) -> None:
    task_dir = tmp_path / "warping_training"
    task_dir.mkdir()
    (task_dir / "warping_manifest.json").write_text(json.dumps([_rec("b.png", "wsrd")]))
    result = CliRunner().invoke(
        pmd.cli,
        ["merge", "--warping-dir", str(task_dir), "--output-dir", str(tmp_path / "m"),
         "--gcs-output-prefix", "gs://bucket/prefix", "--exclude-license-class", "non_commercial"],
    )  # fmt: skip
    assert result.exit_code != 0
    assert "all records excluded" in result.output
