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
from typing import Any

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

_FRONTMATTER_LICENSE = re.compile(r"^license:\s*(.+?)\s*$", re.MULTILINE)


def classify_license(raw: str | None) -> str:
    """Map a free-text license string to a license class.

    Order matters: non-commercial is checked before share-alike because
    ``CC-BY-NC-SA`` contains both.
    """
    if raw is None:
        return UNSPECIFIED
    text = raw.strip().lower()
    if not text or text in {"none", "null"}:
        return UNSPECIFIED
    if text.startswith("mixed"):
        return MIXED
    if text.startswith(("unknown", "unspecified")):
        return UNSPECIFIED
    if re.search(r"(^|[^a-z])nc([^a-z]|$)", text) or "non-commercial" in text:
        return NON_COMMERCIAL
    if "gpl" in text and "lgpl" not in text:
        return COPYLEFT_GPL
    if "research" in text or "academic" in text:
        return RESEARCH_ONLY
    if (
        re.search(r"(^|[^a-z])sa([^a-z]|$)", text)
        or "sharing" in text
        or "odbl" in text
    ):
        return SHARE_ALIKE
    if text in {"cc0", "cc0-1.0"} or "public domain" in text:
        return PUBLIC_DOMAIN
    if re.search(r"mit|apache|bsd|cc-by|cdla-permissive|ofl|isc", text):
        return PERMISSIVE
    return UNSPECIFIED


def _collapse(name: str) -> str:
    """Normalise dataset names: ``rvlcdip`` / ``rvl_cdip`` / ``rvl-cdip`` match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_dataset_licenses(source_dir: Path) -> dict[str, str]:
    """Read ``{collapsed-name: raw license}`` from dataset source docs.

    Args:
        source_dir: Directory of ``<canonical-name>.md`` files (``docs/datasets/source``).
    """
    licenses: dict[str, str] = {}
    if not source_dir.is_dir():
        return licenses
    for path in sorted(source_dir.glob("*.md")):
        head = path.read_text(encoding="utf-8")[:2000]
        match = _FRONTMATTER_LICENSE.search(head)
        licenses[_collapse(path.stem)] = match.group(1).strip("\"'") if match else ""
    return licenses


def annotate_license(
    records: Iterable[dict[str, Any]],
    licenses: Mapping[str, str],
) -> dict[str, int]:
    """Add ``license`` and ``license_class`` to records in place.

    Existing ``license`` values are kept (their class is still computed). Records
    with ``provenance == "synthetic_v3"`` are class ``generated``. Records whose
    dataset is unknown get ``unspecified`` so they cannot slip into production.

    Returns:
        Count of records per license class.
    """
    counts: dict[str, int] = {}
    for rec in records:
        if rec.get("provenance") == "synthetic_v3":
            rec.setdefault("license", "generated (synth-multiscript-v3)")
            rec["license_class"] = GENERATED
        else:
            raw = rec.get("license")
            if raw is None:
                dataset = rec.get("source_dataset") or rec.get("dataset") or ""
                raw = licenses.get(_collapse(str(dataset)))
                rec["license"] = raw if raw else "unspecified"
            rec["license_class"] = classify_license(str(rec["license"]))
        counts[rec["license_class"]] = counts.get(rec["license_class"], 0) + 1
    return counts
