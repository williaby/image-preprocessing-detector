"""`prepare_multitask_datasets.py warping --extra-real-labels` ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.prepare_multitask_datasets import cli


def _write_labels(path: Path, n_meshes: int = 20, per_mesh: int = 5) -> None:
    rows = [
        {
            "id": f"m{m}_{i}",
            "image_path": f"doc3d/img/{m}/m{m}_{i}.png",
            "mesh_id": str(m),
            "warping_severity": round((m * per_mesh + i) / (n_meshes * per_mesh), 4),
            "provenance": "real_render_doc3d",
            "license": "MIT",
        }
        for m in range(n_meshes)
        for i in range(per_mesh)
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _run(tmp_path: Path, labels: Path, *extra: str) -> list[dict[str, object]]:
    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli,
        ["warping", "--synthetic-metadata", str(tmp_path / "none.json"),
         "--l2-metadata-dir", str(tmp_path / "no_l2"), "--output-dir", str(out),
         "--extra-real-labels", str(labels), *extra],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    return json.loads((out / "warping_manifest.json").read_text())


@pytest.mark.unit
def test_extra_labels_become_warping_samples(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    _write_labels(labels)
    manifest = _run(tmp_path, labels)
    assert len(manifest) == 100
    assert all("warping" in r and 0.0 <= float(r["warping"]) <= 1.0 for r in manifest)  # type: ignore[arg-type]
    assert all(r["image_path"].startswith("doc3d/img/") for r in manifest)  # type: ignore[union-attr]


@pytest.mark.unit
def test_meshes_never_span_splits(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    _write_labels(labels, n_meshes=60)
    manifest = _run(tmp_path, labels)
    splits_by_mesh: dict[str, set[object]] = {}
    for rec in manifest:
        mesh = str(rec["image_path"]).split("/")[2]
        splits_by_mesh.setdefault(mesh, set()).add(rec["split"])
    assert all(len(s) == 1 for s in splits_by_mesh.values())
    assert (
        len({next(iter(s)) for s in splits_by_mesh.values()}) > 1
    )  # not all one split


@pytest.mark.unit
def test_max_extra_real_caps_records(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    _write_labels(labels)
    assert len(_run(tmp_path, labels, "--max-extra-real", "30")) == 30


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_path",
    [
        "/etc/passwd",
        "../../secret.png",
        "doc3d/../../x.png",
        "C:\\Windows\\x.png",
        "",
        "a\x00b.png",
    ],
)
def test_unsafe_image_paths_are_rejected(tmp_path: Path, bad_path: str) -> None:
    labels = tmp_path / "labels.jsonl"
    good = {"image_path": "doc3d/img/1/ok.png", "mesh_id": "1", "warping_severity": 0.2}
    bad = {"image_path": bad_path, "mesh_id": "2", "warping_severity": 0.9}
    labels.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n")
    manifest = _run(tmp_path, labels)
    assert [r["image_path"] for r in manifest] == ["doc3d/img/1/ok.png"]


@pytest.mark.unit
def test_cap_selection_is_independent_of_input_order(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    _write_labels(labels)
    first = {r["image_path"] for r in _run(tmp_path, labels, "--max-extra-real", "25")}
    lines = labels.read_text().splitlines()
    labels.write_text("\n".join(reversed(lines)) + "\n")
    second = {r["image_path"] for r in _run(tmp_path, labels, "--max-extra-real", "25")}
    assert first == second


@pytest.mark.unit
def test_malformed_rows_are_skipped_not_fatal(tmp_path: Path) -> None:
    good = {
        "image_path": "doc3d/img/1/ok.png",
        "mesh_id": "1",
        "warping_severity": "0.25",
    }
    lines = [
        json.dumps(good),
        json.dumps([1, 2, 3]),  # valid JSON, not an object
        json.dumps("a string"),
        "{this is not json",
        json.dumps({"image_path": "doc3d/a.png", "warping_severity": None}),
        json.dumps({"image_path": "doc3d/b.png", "warping_severity": "high"}),
        json.dumps({"image_path": "doc3d/c.png", "warping_severity": float("nan")}),
        json.dumps({"image_path": "doc3d/d.png", "warping_severity": True}),
    ]
    labels = tmp_path / "labels.jsonl"
    labels.write_text("\n".join(lines) + "\n")
    manifest = _run(tmp_path, labels)
    assert [r["image_path"] for r in manifest] == ["doc3d/img/1/ok.png"]
    assert manifest[0]["warping"] == 0.25  # numeric string coerced to float
