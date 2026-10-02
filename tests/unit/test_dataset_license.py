"""Tests for dataset license classification and manifest annotation."""

from __future__ import annotations

from pathlib import Path

import pytest

from image_preprocessing_detector.schema_utils import dataset_license as dl

REPO_SOURCE_DIR = Path(__file__).resolve().parents[2] / "docs" / "datasets" / "source"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MIT", dl.PERMISSIVE),
        ("Apache-2.0", dl.PERMISSIVE),
        ("CC-BY-4.0", dl.PERMISSIVE),
        ("CDLA-Permissive-1.0", dl.PERMISSIVE),
        ("CC0", dl.PUBLIC_DOMAIN),
        ("CC0-1.0", dl.PUBLIC_DOMAIN),
        ("Public Domain", dl.PUBLIC_DOMAIN),
        ("CC-BY-SA-4.0", dl.SHARE_ALIKE),
        ("CC-BY-SA-2.5", dl.SHARE_ALIKE),
        ("CDLA-Sharing-1.0", dl.SHARE_ALIKE),
        ("ODbL-1.0", dl.SHARE_ALIKE),
        ("CC-BY-NC-4.0", dl.NON_COMMERCIAL),
        ("CC-BY-NC-SA-4.0", dl.NON_COMMERCIAL),  # NC wins over SA
        ("GPL-3.0", dl.COPYLEFT_GPL),
        ("Research Only", dl.RESEARCH_ONLY),
        ("Academic", dl.RESEARCH_ONLY),
        ("academic", dl.RESEARCH_ONLY),
        ("Mixed (CC0, PD, CC-BY-4.0, CC-BY-SA)", dl.MIXED),
        ("Unknown", dl.UNSPECIFIED),
        ("Unknown (verify with authors before production use)", dl.UNSPECIFIED),
        ("Unspecified", dl.UNSPECIFIED),
        ("", dl.UNSPECIFIED),
        (None, dl.UNSPECIFIED),
        ("Some Bespoke Terms", dl.UNSPECIFIED),
        # restrictions must never be approved by a permissive substring match
        ("CC-BY-ND-4.0", dl.UNSPECIFIED),
        ("CC-BY-NC-ND-4.0", dl.NON_COMMERCIAL),
        ("CC-BY-4.0; noncommercial use only", dl.NON_COMMERCIAL),
        ("CC-BY-4.0 with extra conditions", dl.UNSPECIFIED),
        ("MIT (code only)", dl.UNSPECIFIED),
        ("AGPL-3.0", dl.COPYLEFT_GPL),
        ("LGPL-3.0", dl.UNSPECIFIED),
        ("generated (synth-multiscript-v3)", dl.GENERATED),
    ],
)
def test_classify_license(raw: str | None, expected: str) -> None:
    assert dl.classify_license(raw) == expected


@pytest.mark.unit
def test_every_class_is_partitioned_by_policy() -> None:
    open_decision = {dl.RESEARCH_ONLY, dl.MIXED}
    assert (
        set(dl.ALL_CLASSES)
        == dl.PRODUCTION_ELIGIBLE | dl.PRODUCTION_EXCLUDED | open_decision
    )
    assert not dl.PRODUCTION_ELIGIBLE & dl.PRODUCTION_EXCLUDED


@pytest.mark.unit
def test_annotate_resolves_aliases_and_marks_unknown(tmp_path: Path) -> None:
    (tmp_path / "rvl-cdip.md").write_text("---\nlicense: Research Only\n---\n")
    (tmp_path / "sd7k.md").write_text("---\nlicense: MIT\n---\n")
    licenses = dl.load_dataset_licenses(tmp_path)
    records = [
        {"source_dataset": "rvlcdip"},  # alias without hyphen
        {"source_dataset": "sd7k"},
        {"source_dataset": "never-heard-of-it"},
        {"provenance": "synthetic_v3"},
        {"source_dataset": "doc3d", "license": "MIT"},  # pre-set license kept
    ]
    counts = dl.annotate_license(records, licenses)
    assert [r["license_class"] for r in records] == [
        dl.RESEARCH_ONLY,
        dl.PERMISSIVE,
        dl.UNSPECIFIED,
        dl.GENERATED,
        dl.PERMISSIVE,
    ]
    assert records[2]["license"] == "unspecified"
    assert counts[dl.PERMISSIVE] == 2


@pytest.mark.unit
def test_repo_decisions_are_reflected_in_real_source_docs() -> None:
    """Guard the 2026-10-01 decisions against the real dataset docs."""
    licenses = dl.load_dataset_licenses(REPO_SOURCE_DIR)
    if not licenses:
        pytest.skip("dataset source docs not available")
    cls = {name: dl.classify_license(licenses.get(dl._collapse(name))) for name in
           ("sd7k", "docreal", "doc3d", "doclaynet", "midv500")}  # fmt: skip
    assert all(c in dl.PRODUCTION_ELIGIBLE for c in cls.values()), cls
    excluded = {name: dl.classify_license(licenses.get(dl._collapse(name))) for name in
                ("wsrd", "anyphotodoc6300", "warpdoc", "docalign12k")}  # fmt: skip
    assert all(c in dl.PRODUCTION_EXCLUDED for c in excluded.values()), excluded


@pytest.mark.unit
def test_license_key_in_body_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "front.md").write_text("---\nlicense: MIT\n---\nbody\n")
    (tmp_path / "bodyonly.md").write_text("---\ntitle: x\n---\nlicense: MIT\n")
    (tmp_path / "nofront.md").write_text("license: MIT\nno front matter\n")
    licenses = dl.load_dataset_licenses(tmp_path)
    assert licenses["front"] == "MIT"
    assert licenses["bodyonly"] == ""
    assert licenses["nofront"] == ""
    assert dl.classify_license(licenses["bodyonly"]) == dl.UNSPECIFIED


@pytest.mark.unit
def test_synthetic_provenance_does_not_launder_a_restricted_license() -> None:
    records = [
        {"provenance": "synthetic_v3", "license": "CC-BY-NC-4.0"},
        {"provenance": "synthetic_v3"},
    ]
    dl.annotate_license(records, {})
    assert records[0]["license_class"] == dl.NON_COMMERCIAL
    assert records[1]["license_class"] == dl.GENERATED


@pytest.mark.unit
def test_front_matter_parser_edge_cases(tmp_path: Path) -> None:
    cases = {
        "quoted": ('---\nlicense: "MIT"\n---\n', "MIT"),
        "crlf": ("---\r\nlicense: Apache-2.0\r\n---\r\nbody\r\n", "Apache-2.0"),
        "indented": (
            "---\nmeta:\n  license: MIT\n---\n",
            "",
        ),  # nested key is not top-level
        "unterminated": ("---\nlicense: MIT\nno closing delimiter\n", ""),
        "colonvalue": (
            '---\nlicense: "CC-BY-4.0 (see: terms)"\n---\n',
            "CC-BY-4.0 (see: terms)",
        ),
        "empty": ("", ""),
    }
    for name, (text, expected) in cases.items():
        (tmp_path / f"{name}.md").write_text(text)
    licenses = dl.load_dataset_licenses(tmp_path)
    for name, (_, expected) in cases.items():
        assert licenses[name] == expected, name


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\nlicense: MIT  # upstream\n---\n", "MIT"),
        ('---\nlicense: "CC-BY-4.0"\n---\n', "CC-BY-4.0"),
        ("---\nlicense: >-\n  CC-BY-NC\n  4.0\n---\n", "CC-BY-NC 4.0"),
        ("---\nlicense: [MIT]\n---\n", ""),
        ("---\nlicense: : bad: [\n---\n", ""),
        ("---\ntitle: x\n---\nlicense: MIT\n", ""),
    ],
)
def test_front_matter_license_is_yaml_parsed(text: str, expected: str) -> None:
    assert dl._front_matter_license(text) == expected


@pytest.mark.unit
def test_generated_does_not_override_restrictions() -> None:
    assert dl.classify_license("generated, noncommercial use only") == "non_commercial"
    assert dl.classify_license("generated (synth-multiscript-v3)") == "generated"
