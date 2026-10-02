"""Dataset license classification for training-manifest provenance.

The released model weights are CC-BY-SA-4.0 (decision 2026-10-01, see
``docs/planning/MASTER_PROJECT_PLAN.md``). Every manifest record therefore
carries the license of the dataset it came from, so that production runs can be
filtered by license class without rebuilding manifests.

The source of truth for a dataset's license is the ``license:`` frontmatter key
in ``docs/datasets/source/<canonical-name>.md``.

Classes (see :func:`classify_license`):

==============  ============================================================  =====================
class           examples                                                      production default
==============  ============================================================  =====================
permissive      MIT, Apache-2.0, CC-BY-4.0, CDLA-Permissive-1.0               eligible
public_domain   CC0, Public Domain                                            eligible
share_alike     CC-BY-SA-*, CDLA-Sharing, ODbL                                eligible (SA weights)
generated       our own synthetic generation (e.g. synth-multiscript-v3)      eligible
research_only   "Research Only", "Academic"                                   OPEN DECISION
mixed           per-source licenses (needs per-image review)                  OPEN DECISION
non_commercial  CC-BY-NC-*                                                    excluded
copyleft_gpl    GPL-*                                                         excluded
unspecified     Unknown / Unspecified / missing                               excluded
==============  ============================================================  =====================

``research_only`` is deliberately not auto-excluded: whether research-terms data
may be used for a public CC-BY-SA release is an open decision (see
``docs/planning/RUNSHEET_DATA_ASSEMBLY.md`` section 0).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

PERMISSIVE = "permissive"
PUBLIC_DOMAIN = "public_domain"
SHARE_ALIKE = "share_alike"
GENERATED = "generated"
RESEARCH_ONLY = "research_only"
MIXED = "mixed"
NON_COMMERCIAL = "non_commercial"
COPYLEFT_GPL = "copyleft_gpl"
UNSPECIFIED = "unspecified"

ALL_CLASSES = (
    PERMISSIVE,
    PUBLIC_DOMAIN,
    SHARE_ALIKE,
    GENERATED,
    RESEARCH_ONLY,
    MIXED,
    NON_COMMERCIAL,
    COPYLEFT_GPL,
    UNSPECIFIED,
)

#: Classes eligible for a production CC-BY-SA release without further decisions.
PRODUCTION_ELIGIBLE = frozenset({PERMISSIVE, PUBLIC_DOMAIN, SHARE_ALIKE, GENERATED})
#: Classes excluded from production training (evaluation/calibration use only).
PRODUCTION_EXCLUDED = frozenset({NON_COMMERCIAL, COPYLEFT_GPL, UNSPECIFIED})

# Approved permissive forms must match in full. A string that merely contains an
# approved name (a NoDerivatives variant, or a grant followed by a noncommercial
# rider) is not approved and falls through to unspecified, pending a decision.
_PERMISSIVE_FORMS = (
    r"mit|apache-2\.0|bsd-[23]-clause|isc|ofl-1\.1|unlicense"
    r"|cc-by-(?:2\.0|2\.5|3\.0|4\.0)|cdla-permissive-[12]\.0"
)

# Ordered: the first matching rule wins, so restrictions are tested before grants
# (CC-BY-NC-SA contains both "nc" and "sa"; CC-BY-ND is a restriction, not a grant).
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (cls, re.compile(pattern))
    for cls, pattern in (
        (MIXED, r"^mixed"),
        (UNSPECIFIED, r"^(?:unknown|unspecified|none|null)"),
        (NON_COMMERCIAL, r"(?:^|[^a-z])nc(?:[^a-z]|$)|non-?commercial"),
        (UNSPECIFIED, r"(?:^|[^a-z])nd(?:[^a-z]|$)|no-?deriv"),
        (COPYLEFT_GPL, r"(?<!l)gpl"),
        (RESEARCH_ONLY, r"research|academic"),
        (SHARE_ALIKE, r"(?:^|[^a-z])sa(?:[^a-z]|$)|sharing|odbl"),
        (GENERATED, r"^generated"),  # after restrictions: "generated, NC only" is NC
        (PUBLIC_DOMAIN, r"^(?:cc0(?:-1\.0)?|public-domain|pd)$"),
        (PERMISSIVE, rf"^(?:{_PERMISSIVE_FORMS})$"),
    )
)


def classify_license(raw: str | None) -> str:
    """Map a free-text license string to a license class (fail closed).

    Unrecognised or ambiguous strings are ``unspecified``, never permissive.
    """
    text = re.sub(r"\s+", "-", (raw or "").strip().lower())
    for cls, pattern in _RULES:
        if pattern.search(text):
            return cls
    return UNSPECIFIED


def _collapse(name: str) -> str:
    """Normalise dataset names: ``rvlcdip`` / ``rvl_cdip`` / ``rvl-cdip`` match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _front_matter_lines(text: str) -> list[str]:
    """Lines of the leading ``---`` delimited YAML block, or [] if there is none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:end]
    return []


def _front_matter_license(text: str) -> str:
    """The top-level ``license:`` value from the leading YAML front matter only.

    Parsed with ``yaml.safe_load`` so inline comments, quoting and folded scalars
    resolve as YAML defines them. Anything that is not a string value (missing
    key, null, list, malformed YAML) yields "", which classifies as unspecified.
    """
    lines = _front_matter_lines(text)
    if not lines:
        return ""
    import yaml  # data-tooling dependency (ml/colab extras); not needed at inference

    try:
        data = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError:
        return ""
    value: object = None
    if isinstance(data, dict):
        mapping = cast("dict[str, object]", data)
        value = mapping.get("license")
    return " ".join(value.split()) if isinstance(value, str) else ""


def load_dataset_licenses(source_dir: Path) -> dict[str, str]:
    """Read ``{collapsed-name: raw license}`` from dataset source docs.

    Only the YAML front matter is consulted, so a ``license:`` line in a document
    body cannot grant a license.

    Args:
        source_dir: Directory of ``<canonical-name>.md`` files (``docs/datasets/source``).
    """
    if not source_dir.is_dir():
        return {}
    return {
        _collapse(path.stem): _front_matter_license(path.read_text(encoding="utf-8"))
        for path in sorted(source_dir.glob("*.md"))
    }


def annotate_license(
    records: Iterable[dict[str, Any]],
    licenses: Mapping[str, str],
) -> dict[str, int]:
    """Add ``license`` and ``license_class`` to records in place.

    A license already on the record is kept and classified (so a restricted
    license is never relabelled ``generated`` because of synthetic provenance).
    Records with ``provenance == "synthetic_v3"`` and no license default to
    ``generated``. Records whose dataset is unknown get ``unspecified`` so they
    cannot slip into production.

    Returns:
        Count of records per license class.
    """
    counts: dict[str, int] = {}
    for rec in records:
        raw = rec.get("license")
        if raw is None:
            if rec.get("provenance") == "synthetic_v3":
                raw = "generated (synth-multiscript-v3)"
            else:
                dataset = rec.get("source_dataset") or rec.get("dataset") or ""
                raw = licenses.get(_collapse(str(dataset))) or "unspecified"
            rec["license"] = raw
        rec["license_class"] = classify_license(str(raw))
        counts[rec["license_class"]] = counts.get(rec["license_class"], 0) + 1
    return counts
