"""Build manuscript groups config for john11-manuscripts dataset.

Groups all 577 John 1:1 manuscript images by physical codex so that
train/val splits can be done at the manuscript level, preventing
near-duplicate leakage from the same hand/parchment/degradation.

Output: config/john11_manuscript_groups.yaml

Usage:
    uv run python scripts/build_manuscript_groups_john11.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGISTRY_PATH = Path("metadata_registry/john11_manuscripts_registry.jsonl")
OUTPUT_PATH = Path("config/john11_manuscript_groups.yaml")

# Human-readable manuscript names keyed by (institution, codex_key).
# Walters codex identifiers resolved from The Digital Walters catalogue.
WALTERS_NAMES: dict[str, tuple[str, str]] = {
    "W533": ("Walters W.533 — Syriac Gospels (Peshitta)", "Syrc"),
    "W537": ("Walters W.537 — Armenian Gospels", "Armn"),
    "W538": ("Walters W.538 — Armenian Gospels", "Armn"),
    "W540": ("Walters W.540 — Armenian Gospels", "Armn"),
    "W543": ("Walters W.543 — Armenian Gospels", "Armn"),
    "W556": ("Walters W.556 — Arabic Gospels", "Arab"),
    "W592": ("Walters W.592 — Arabic Gospels", "Arab"),
}

# Gallica ARK/catalog mapping: catalog_number → (group_key, manuscript_name, script)
GALLICA_CATALOG: dict[int, tuple[str, str, str]] = {
    6: (
        "gallica_codex_ephraemi_rescriptus",
        "Codex Ephraemi Rescriptus (BnF Grec 9)",
        "Grek",
    ),
    20: (
        "gallica_godescalc_evangelistary",
        "Godescalc Evangelistary (BnF Lat 1203)",
        "Latn",
    ),
}

# Wikimedia: known multi-image codices where the simple prefix algorithm
# would produce distinct keys for images that are in fact the same codex.
# Maps (script, canonical_group_key) → list of filename prefix patterns
# that should be merged into that group.
WIKIMEDIA_MERGE_RULES: dict[tuple[str, str], list[str]] = {
    # Book of Kells — Trinity College Dublin, MS 58
    ("latn", "wikimedia_latn_kellsfol"): [
        "kellsfol",
        "bookfol",
        "book_of_kells",
        "bookofkells",
        "kellspourpre",
        "lettrine_historiée,_livre_de_kells",
        "meister_des_book_of_kells",
        "bookkells",
    ],
    # Book of Durrow — Trinity College Dublin, MS 57
    ("latn", "wikimedia_latn_book_of_durrow"): [
        "bookdurrow",
        "book_of_durrow",
        "bookofdurow",
        "durrow",
        "ie_tcd_ms_57",
    ],
    # Codex Aureus of Canterbury — Stockholm, Kungliga biblioteket A.135
    ("latn", "wikimedia_latn_codexaureus"): [
        "codexaureus",
    ],
    # Codex Amiatinus — Florence, Biblioteca Medicea Laurenziana
    ("latn", "wikimedia_latn_codex_amiatinus"): [
        "codex_amiatinus",
        "codexamiatinus",
        "codx_amiatinus",
        "codxamiatinus",
        "amiatinus",
        "ezra_codex_amiatinus",
        "meister_des_codex_amiatus",
        "esdra_en_scriptorium",
        "1911_britannica-bible-codex_amiatinus",
    ],
    # Codex Alexandrinus — British Library, Royal MS 1 D V-VIII
    ("grek", "wikimedia_grek_codex_alexandrinus"): [
        "codexalexandrinus",
        "codex_alexandrinus",
        "codexalexandrin",
        "1911_britannica-bible-codex_alexandrinus",
        "modern_greek_alexandrinus",
        "codealexandrinusfolio",
        "colophon_alexandrinus",
        "end_of_2_peter_and_beginning_of_1_john_in_alexandrinus",
        "photographic_facsimiles_of_the_remains_of_the_epistles_of_clement_of_rome._made_from_the_unique_copy_preserved_in_the_codex_alexandrinus",
    ],
    # Codex Argenteus — Uppsala University Library
    ("goth", "wikimedia_goth_codex_argenteus"): [
        "argenteus",
        "codexargenteus",
        "codex_argenteus",
        "codex_argentus",
        "codexargentus",
        "codicis_argentei",
        "codex_argentus_at",
        "detail_of_codex_argenteus",
        "diplomatique_codex_d'argent",
        "wulfila_bibel",
        "studies_in_lowland_scots_plate",
    ],
    # Codex Marianus — OCS glagolitic gospel
    ("cyrs", "wikimedia_cyrs_codex_marianus"): [
        "codex_marianus",
        "заставка_и_инициал_в_мариинското_евангелие",
        "мариинско_евангелие",
        "факсимиле_на_страница_от_мариинското_евангелие",
    ],
    # Codex Zographensis — OCS glagolitic gospel
    ("cyrs", "wikimedia_cyrs_codex_zographensis"): [
        "zograf",
        "kodex.zograf",
        "zographensis",
        "минијатура_на_св._петар_и_павле,_зографско_евангелие",
    ],
    # Ostromir Gospels — Saint Petersburg, Russian National Library
    ("cyrs", "wikimedia_cyrs_ostromir_gospels"): [
        "ostromir",
        "ostromirovo",
        "остромирове_євангеліє",
    ],
    # Garima Gospels — Abba Garima Monastery, Ethiopia
    ("ethi", "wikimedia_ethi_garima_gospels"): [
        "garima_gospels",
        "garima-gospels",
        "illumination-from-abba-garima-gospel",
    ],
}

# Inverted lookup: (script, prefix_lower) → canonical_group_key
_MERGE_INDEX: dict[tuple[str, str], str] = {}
for (script, group_key), patterns in WIKIMEDIA_MERGE_RULES.items():
    for pat in patterns:
        _MERGE_INDEX[(script, pat.lower())] = group_key


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------


def _wikimedia_group_key(script: str, filename: str) -> str:
    """Return a stable group key for a Wikimedia image.

    Strategy:
    1. Check whether the filename prefix (lowercased) matches a known
       multi-image codex merge rule exactly or as a prefix match.
    2. Otherwise fall back to: strip extension, strip trailing digit run,
       strip trailing punctuation, produce ``wikimedia_{script}_{stem}``.
    """
    script_lower = script.lower()
    base = re.sub(r"\.[^.]+$", "", filename)
    base_lower = base.lower()

    # Exact or prefix match against merge rules
    for (ms, pat), group_key in _MERGE_INDEX.items():
        if ms == script_lower:
            if base_lower == pat or base_lower.startswith(pat):
                return group_key

    # Generic fallback: strip trailing digits and punctuation
    stem = re.sub(r"[\d]+$", "", base).rstrip("_-. ,")
    if not stem:
        stem = base
    safe = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    # If ASCII normalization produced an empty string (e.g. non-Latin filenames),
    # treat each such image as its own singleton group keyed by the full basename.
    if not safe:
        # Use the raw filename (unicode) as a unique discriminator
        safe = re.sub(r"[^a-z0-9]+", "_", base.encode("ascii", "ignore").decode().lower()).strip("_")
    if not safe:
        # Last resort: hash the filename
        import hashlib
        safe = hashlib.md5(filename.encode()).hexdigest()[:8]  # noqa: S324
    return f"wikimedia_{script_lower}_{safe}"


def _walters_group_key(codex_id: str, script: str) -> str:
    """Return group key for a Walters manuscript."""
    return f"walters_{codex_id.lower()}_{script.lower()}"


def _gallica_group_key(catalog_number: int) -> str:
    """Return group key for a Gallica manuscript."""
    info = GALLICA_CATALOG.get(catalog_number)
    if info:
        return info[0]
    return f"gallica_cat{catalog_number}"


def _met_group_key(catalog_number: int, script: str) -> str:
    """Return group key for a Met Museum manuscript."""
    return f"met_cat{catalog_number}_{script.lower()}"


# ---------------------------------------------------------------------------
# Record processing
# ---------------------------------------------------------------------------


def _parse_walters_codex(source_path: str) -> str | None:
    """Extract W### codex identifier from a Walters source_path."""
    match = re.match(r"walters/(W\d+)_", source_path)
    return match.group(1) if match else None


def build_groups(
    registry_path: Path,
) -> dict[str, dict[str, object]]:
    """Read registry and return groups dict.

    Returns:
        Mapping of group_key → {manuscript_name, script, institution,
        source_path_pattern, image_count, sample_ids}.
    """
    # group_key → list of (sample_id, source_path)
    raw: dict[str, list[tuple[str, str]]] = defaultdict(list)
    # group_key → metadata attrs
    meta: dict[str, dict[str, str]] = {}

    with registry_path.open() as fh:
        for line in fh:
            record = json.loads(line)
            sample_id: str = record["sample_id"]
            source_path: str = record["source_path"]
            institution: str = record["source_institution"]
            script: str = record.get("script_iso15924", "Zyyy")
            catalog_number = record.get("catalog_number")

            if institution == "walters_art_museum":
                codex_id = _parse_walters_codex(source_path)
                if codex_id is None:
                    codex_id = "unknown"
                group_key = _walters_group_key(codex_id, script)
                if group_key not in meta:
                    walters_info = WALTERS_NAMES.get(codex_id)
                    name = walters_info[0] if walters_info else f"Walters {codex_id}"
                    meta[group_key] = {
                        "manuscript_name": name,
                        "script": script,
                        "institution": institution,
                        "source_path_pattern": f"walters/{codex_id}_*",
                    }

            elif institution == "bnf_gallica":
                cat = int(catalog_number) if catalog_number is not None else -1
                group_key = _gallica_group_key(cat)
                if group_key not in meta:
                    gal_info = GALLICA_CATALOG.get(cat)
                    name = gal_info[1] if gal_info else f"Gallica cat {cat}"
                    path_dir = "/".join(source_path.split("/")[:2])
                    meta[group_key] = {
                        "manuscript_name": name,
                        "script": script,
                        "institution": institution,
                        "source_path_pattern": f"{path_dir}/gallica_*",
                    }

            elif institution == "met_museum":
                cat = int(catalog_number) if catalog_number is not None else -1
                group_key = _met_group_key(cat, script)
                if group_key not in meta:
                    meta[group_key] = {
                        "manuscript_name": f"Met Museum object {cat} ({script})",
                        "script": script,
                        "institution": institution,
                        "source_path_pattern": f"met/met_{cat}_*",
                    }

            else:  # wikimedia
                parts = source_path.split("/")
                filename = parts[-1]
                group_key = _wikimedia_group_key(script, filename)
                if group_key not in meta:
                    # Derive a readable name from the group key
                    readable = group_key.replace("wikimedia_", "", 1)
                    readable = re.sub(r"^[a-z]{4}_", "", readable)
                    readable = readable.replace("_", " ").title()
                    meta[group_key] = {
                        "manuscript_name": readable,
                        "script": script,
                        "institution": institution,
                        "source_path_pattern": f"wikimedia/{script.lower()}/*",
                    }

            raw[group_key].append((sample_id, source_path))

    # Assemble final groups, sorted by script then group_key
    groups: dict[str, dict[str, object]] = {}
    for group_key in sorted(raw.keys(), key=lambda k: (meta[k]["script"], k)):
        entries = raw[group_key]
        sample_ids = sorted({sid for sid, _ in entries})
        source_paths = sorted({sp for _, sp in entries})

        # Derive pattern from actual paths when possible
        path_dirs = {"/".join(sp.split("/")[:2]) for sp in source_paths}
        if len(path_dirs) == 1:
            pattern = list(path_dirs)[0] + "/*"
        else:
            pattern = meta[group_key].get("source_path_pattern", "")

        groups[group_key] = {
            "manuscript_name": meta[group_key]["manuscript_name"],
            "script": meta[group_key]["script"],
            "institution": meta[group_key]["institution"],
            "source_path_pattern": pattern,
            "image_count": len(sample_ids),
            "sample_ids": sample_ids,
        }

    return groups


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------


def _build_yaml_doc(groups: dict[str, dict[str, object]]) -> dict[str, object]:
    """Wrap groups in the top-level YAML structure."""
    total_images = sum(int(g["image_count"]) for g in groups.values())
    return {
        "metadata": {
            "created": "2026-03-12",
            "dataset": "john11-manuscripts",
            "total_images": total_images,
            "total_groups": len(groups),
            "purpose": (
                "Prevent near-duplicate leakage in train/val splits — "
                "all images in a group go to the same split"
            ),
            "split_strategy": (
                "Assign each group entirely to train or val; "
                "do not split a group across both sets"
            ),
        },
        "groups": groups,
    }


def _write_yaml(doc: dict[str, object], output_path: Path) -> None:
    """Write the YAML document with a descriptive header comment."""
    header = (
        "# Manuscript groups for john11-manuscripts dataset\n"
        "# Each group = one physical codex; all images in a group go to the same split\n"
        "# Generated by scripts/build_manuscript_groups_john11.py\n"
        "#\n"
        "# Usage: assign entire groups to train/val to prevent near-duplicate leakage.\n"
        "# Images from the same physical manuscript share hand, parchment, and degradation.\n"
        "#\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.dump(
        doc,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    output_path.write_text(header + yaml_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------


def _print_summary(groups: dict[str, dict[str, object]]) -> None:
    """Print a concise summary of groups to stdout."""
    by_script: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, grp in groups.items():
        script = str(grp["script"])
        count = int(grp["image_count"])
        by_script[script].append((key, count))

    total_images = sum(int(g["image_count"]) for g in groups.values())
    total_groups = len(groups)

    print(f"\nManuscript groups summary — {total_images} images in {total_groups} groups")
    print("=" * 70)

    for script in sorted(by_script):
        entries = sorted(by_script[script], key=lambda x: -x[1])
        script_total = sum(c for _, c in entries)
        print(f"\n  {script} ({len(entries)} groups, {script_total} images):")
        for key, count in entries:
            name = str(groups[key]["manuscript_name"])
            label = f"{name[:55]:<55}" if len(name) <= 55 else name[:52] + "..."
            print(f"    {label}  {count:3d} imgs  [{key}]")

    print("\n" + "=" * 70)
    singleton_count = sum(
        1 for g in groups.values() if int(g["image_count"]) == 1
    )
    print(f"  Singletons (1 image): {singleton_count}")
    print(f"  Multi-image groups:   {total_groups - singleton_count}")
    print(f"  Output: {OUTPUT_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Build and write the manuscript groups YAML config."""
    if not REGISTRY_PATH.exists():
        msg = f"Registry not found: {REGISTRY_PATH}"
        raise FileNotFoundError(msg)

    print(f"Reading registry: {REGISTRY_PATH}")
    groups = build_groups(REGISTRY_PATH)
    doc = _build_yaml_doc(groups)
    _write_yaml(doc, OUTPUT_PATH)
    _print_summary(groups)
    print(f"\nWrote {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
