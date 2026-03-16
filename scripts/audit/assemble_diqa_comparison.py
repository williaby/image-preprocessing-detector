"""Assemble a per-field comparison of 5 data sources for 36 DIQA-5000 audit samples.

Sources compared:
    A  Current L2 metadata       (5,500 records from annotate_base_metadata pipeline)
    B  Egret layout results      (36 audit samples, docling-layout-egret-xlarge)
    C  Docling GPU layout        (28 batch files in COCO format, 5,499 records)
    D  LLM enrichment            (500 records, Gemini vision on ori/ images)
    E  Visual ground truth       (36 hand-inspected samples -- the reference)

Also loads:
    Language enrichment          (OpenLID detection, up to 5,499 records)
    Sample set                   (36 audit samples with selection metadata)

Outputs ``comparison_report.json`` containing per-sample field-level comparisons,
per-field agreement metrics, and overall accuracy by source.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
METADATA_DIR = Path("/mnt/e/image_detection/metadata_registry/json")
EXTRACTED_DIR = Path("/mnt/e/image_detection/metadata_registry/extracted/diqa-5000")
AUDIT_DIR = Path("/home/byron/dev/image_detection/scripts/audit/results/diqa-5000")

L2_METADATA_PATH = METADATA_DIR / "diqa-5000_metadata.json"
LLM_ENRICHMENT_PATH = METADATA_DIR / "diqa-5000_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = METADATA_DIR / "diqa-5000_language_enrichment.json"
EGRET_RESULTS_PATH = AUDIT_DIR / "egret_results.json"
VISUAL_GT_PATH = AUDIT_DIR / "visual_ground_truth.json"
SAMPLE_SET_PATH = AUDIT_DIR / "sample_set.json"
OUTPUT_PATH = AUDIT_DIR / "comparison_report.json"

# Fields to compare (order preserved for report readability)
COMPARISON_FIELDS: list[str] = [
    "capture_method",
    "domain_level1",
    "iso639_language",
    "script_family",
    "orientation_class",
    "has_table",
    "has_formula",
    "has_figure",
    "has_handwriting",
    "layout_class_count",
    "color_mode",
    "physical_degradation",
    "split",
]

# Mapping from source letter to human-readable name
SOURCE_NAMES: dict[str, str] = {
    "A": "L2 Metadata",
    "B": "Egret Layout",
    "C": "Docling GPU Layout",
    "D": "LLM Enrichment",
    "E": "Visual Ground Truth",
    "lang": "Language Enrichment",
    "sample_set": "Sample Set",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _image_id_from_filename(filename: str) -> str:
    """Derive image_id from a filename like ``test_ori_00001.jpg``."""
    return Path(filename).stem


def _safe_get(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Nested dict access that returns *default* on any missing key."""
    current: Any = record
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def _normalize_value(value: Any) -> Any:
    """Normalize a value for comparison.

    Booleans are lowercased strings; ``None`` stays ``None``; lists are sorted.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return sorted(str(v).lower() for v in value)
    if isinstance(value, (int, float)):
        return value
    return str(value).strip().lower()


def _values_match(val_a: Any, val_b: Any) -> bool:
    """Return ``True`` when two normalized values are equal."""
    norm_a = _normalize_value(val_a)
    norm_b = _normalize_value(val_b)
    if norm_a is None or norm_b is None:
        return False
    return norm_a == norm_b


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_l2_metadata() -> dict[str, dict[str, Any]]:
    """Load source A: L2 metadata keyed by image_id."""
    with L2_METADATA_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for sample in raw["samples"]:
        filename = _safe_get(sample, "source", "original_filename", default="")
        image_id = _image_id_from_filename(filename)
        if not image_id:
            continue

        # Extract the latest enrichment data
        enrichment_data: dict[str, Any] = {}
        versions = _safe_get(sample, "enrichments", "versions", default=[])
        if versions:
            enrichment_data = versions[-1].get("data", {})

        result[image_id] = {
            "raw": sample,
            "enrichment": enrichment_data,
            "split": _safe_get(sample, "source", "split"),
        }
    return result


def load_egret_results() -> dict[str, dict[str, Any]]:
    """Load source B: Egret layout results keyed by image_id."""
    with EGRET_RESULTS_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for record in raw.get("results", []):
        image_id = record.get("image_id", "")
        if image_id:
            result[image_id] = record
    return result


def load_docling_layout() -> dict[str, dict[str, Any]]:
    """Load source C: Docling GPU layout from COCO-format batch files.

    Returns a dict keyed by image_id with ``annotation_count`` and
    ``category_names`` (unique class names detected).
    """
    batch_files = sorted(EXTRACTED_DIR.glob("layout_batch_*.json"))
    if not batch_files:
        print("WARNING: No docling layout batch files found", file=sys.stderr)
        return {}

    # Build category id->name map (same across batches but re-read for safety)
    result: dict[str, dict[str, Any]] = {}

    for batch_path in batch_files:
        with batch_path.open() as fh:
            batch = json.load(fh)

        cat_map: dict[int, str] = {
            c["id"]: c["name"] for c in batch.get("categories", [])
        }

        # Map numeric image_id -> filename
        img_id_to_name: dict[int, str] = {}
        for img in batch.get("images", []):
            img_id_to_name[img["id"]] = _image_id_from_filename(img["file_name"])

        # Collect annotations per image
        per_image: dict[str, list[str]] = defaultdict(list)
        for ann in batch.get("annotations", []):
            numeric_id = ann.get("image_id")
            name = img_id_to_name.get(numeric_id, "")
            if name:
                cat_name = cat_map.get(ann.get("category_id", -1), "unknown")
                per_image[name].append(cat_name)

        for image_id, cats in per_image.items():
            if image_id not in result:
                result[image_id] = {
                    "annotation_count": len(cats),
                    "category_names": sorted(set(cats)),
                }
            else:
                # Merge if image appears in multiple batches (shouldn't happen)
                result[image_id]["annotation_count"] += len(cats)
                existing = set(result[image_id]["category_names"])
                existing.update(cats)
                result[image_id]["category_names"] = sorted(existing)

    return result


def load_llm_enrichment() -> dict[str, dict[str, Any]]:
    """Load source D: LLM enrichment keyed by image_id."""
    with LLM_ENRICHMENT_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for sample in raw.get("samples", []):
        image_id = sample.get("image_id", "")
        if image_id:
            result[image_id] = sample
    return result


def load_visual_ground_truth() -> dict[str, dict[str, Any]]:
    """Load source E: Visual ground truth keyed by image_id."""
    with VISUAL_GT_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for sample in raw.get("samples", []):
        image_id = sample.get("image_id", "")
        if image_id:
            result[image_id] = sample
    return result


def load_language_enrichment() -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) keyed by image_id."""
    with LANGUAGE_ENRICHMENT_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for sample in raw.get("samples", []):
        image_id = sample.get("image_id", "")
        if image_id:
            result[image_id] = sample
    return result


def load_sample_set() -> dict[str, dict[str, Any]]:
    """Load sample set keyed by image_id."""
    with SAMPLE_SET_PATH.open() as fh:
        raw = json.load(fh)

    result: dict[str, dict[str, Any]] = {}
    for sample in raw.get("samples", []):
        image_id = sample.get("image_id", "")
        if image_id:
            result[image_id] = sample
    return result


# ---------------------------------------------------------------------------
# Field Extraction
# ---------------------------------------------------------------------------
def _extract_split_from_image_id(image_id: str) -> str:
    """Derive split (train/test) from image_id prefix like ``train_ori_00272``."""
    parts = image_id.split("_")
    if parts and parts[0] in ("train", "test"):
        return parts[0]
    return "unknown"


def extract_field_values(
    image_id: str,
    *,
    l2: dict[str, dict[str, Any]],
    egret: dict[str, dict[str, Any]],
    docling: dict[str, dict[str, Any]],
    llm: dict[str, dict[str, Any]],
    gt: dict[str, dict[str, Any]],
    lang: dict[str, dict[str, Any]],
    sample_set: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Extract per-source values for all comparison fields for one sample.

    Returns a dict of ``{field_name: {source_label: value}}``.
    """
    a_rec = l2.get(image_id, {})
    a_enrich = a_rec.get("enrichment", {})
    b_rec = egret.get(image_id, {})
    c_rec = docling.get(image_id, {})
    d_rec = llm.get(image_id, {})
    e_rec = gt.get(image_id, {})
    lang_rec = lang.get(image_id, {})
    ss_rec = sample_set.get(image_id, {})

    fields: dict[str, dict[str, Any]] = {}

    # capture_method
    fields["capture_method"] = {
        "A": a_enrich.get("capture_method"),
        "D": d_rec.get("capture_method"),
        "E": e_rec.get("capture_method"),
    }

    # domain_level1
    fields["domain_level1"] = {
        "A": a_enrich.get("domain_level1"),
        "D": d_rec.get("domain_level1"),
        "E": e_rec.get("domain_level1"),
    }

    # iso639_language
    fields["iso639_language"] = {
        "A": a_enrich.get("iso639_language"),
        "D": ss_rec.get("llm_language"),
        "lang": lang_rec.get("language"),
        "E": e_rec.get("iso639_language"),
    }

    # script_family
    fields["script_family"] = {
        "A": a_enrich.get("script_family"),
        "E": e_rec.get("script_family"),
    }

    # orientation_class
    a_orientation = a_enrich.get("orientation_class")
    if a_orientation is None:
        # Try geometric sub-dict if present
        geometric = a_enrich.get("geometric", {})
        if isinstance(geometric, dict):
            a_orientation = geometric.get("orientation_class")
    fields["orientation_class"] = {
        "A": a_orientation,
        "E": e_rec.get("orientation_class"),
    }

    # Content flags: has_table, has_formula, has_figure, has_handwriting
    for flag in ("has_table", "has_formula", "has_figure", "has_handwriting"):
        fields[flag] = {
            "A": a_enrich.get(flag),
            "D": d_rec.get(flag),
            "E": e_rec.get(flag),
        }

    # layout_class_count: number of layout detections per source
    a_layout_count = len(a_enrich.get("layout_detections", []))
    b_layout_count = b_rec.get("detection_count", len(b_rec.get("detections", [])))
    c_layout_count = c_rec.get("annotation_count", 0) if c_rec else 0
    fields["layout_class_count"] = {
        "A": a_layout_count,
        "B": b_layout_count,
        "C": c_layout_count,
    }

    # color_mode (may only be in E)
    fields["color_mode"] = {
        "E": e_rec.get("color_mode"),
    }

    # physical_degradation (may only be in E)
    fields["physical_degradation"] = {
        "E": e_rec.get("physical_degradation"),
    }

    # split
    fields["split"] = {
        "A": a_rec.get("split"),
        "E": _extract_split_from_image_id(image_id),
    }

    return fields


# ---------------------------------------------------------------------------
# Agreement Metrics
# ---------------------------------------------------------------------------
def _compute_field_gt_stats(
    field_name: str,
    all_comparisons: list[dict[str, Any]],
    source_correct: dict[str, int],
    source_total: dict[str, int],
) -> dict[str, Any]:
    """Compute per-source accuracy vs GT for a single field."""
    field_stats: dict[str, dict[str, int]] = {}
    gt_values_present = 0

    for comp in all_comparisons:
        field_data = comp.get("fields", {}).get(field_name, {})
        sources = field_data.get("sources", {})
        gt_val = sources.get("E")

        if gt_val is None:
            continue
        gt_values_present += 1

        for src_label, src_val in sources.items():
            if src_label == "E":
                continue
            if src_label not in field_stats:
                field_stats[src_label] = {"matches": 0, "total": 0}
            field_stats[src_label]["total"] += 1
            if _values_match(src_val, gt_val):
                field_stats[src_label]["matches"] += 1
                source_correct[src_label] += 1
            source_total[src_label] += 1

    best_source = None
    best_accuracy = -1.0
    source_accuracies: dict[str, float] = {}
    for src_label, stats in field_stats.items():
        if stats["total"] > 0:
            accuracy = stats["matches"] / stats["total"]
            source_accuracies[src_label] = round(accuracy, 4)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_source = src_label

    return {
        "gt_values_present": gt_values_present,
        "source_accuracies": source_accuracies,
        "best_source": best_source,
        "best_accuracy": round(best_accuracy, 4) if best_accuracy >= 0 else None,
    }


def compute_agreement_metrics(
    all_comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute per-field and per-source agreement with ground truth (E).

    Returns a dict with ``per_field`` and ``per_source`` sections.
    """
    source_correct: dict[str, int] = defaultdict(int)
    source_total: dict[str, int] = defaultdict(int)

    per_field = {
        field_name: _compute_field_gt_stats(
            field_name, all_comparisons, source_correct, source_total
        )
        for field_name in COMPARISON_FIELDS
    }

    per_source: dict[str, dict[str, Any]] = {}
    for src_label in sorted(set(source_correct.keys()) | set(source_total.keys())):
        total = source_total[src_label]
        correct = source_correct[src_label]
        per_source[src_label] = {
            "source_name": SOURCE_NAMES.get(src_label, src_label),
            "fields_compared": total,
            "fields_matching_gt": correct,
            "overall_accuracy": round(correct / total, 4) if total > 0 else None,
        }

    return {
        "per_field": per_field,
        "per_source": per_source,
    }


# ---------------------------------------------------------------------------
# Disagreement Detail
# ---------------------------------------------------------------------------
def find_disagreements(
    all_comparisons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a list of all fields where at least one source disagrees with E."""
    disagreements: list[dict[str, Any]] = []

    for comp in all_comparisons:
        image_id = comp["image_id"]
        for field_name in COMPARISON_FIELDS:
            field_data = comp.get("fields", {}).get(field_name, {})
            sources = field_data.get("sources", {})
            gt_val = sources.get("E")

            if gt_val is None:
                continue

            for src_label, src_val in sources.items():
                if src_label == "E":
                    continue
                if src_val is None:
                    continue
                if not _values_match(src_val, gt_val):
                    disagreements.append(
                        {
                            "image_id": image_id,
                            "field": field_name,
                            "source": src_label,
                            "source_name": SOURCE_NAMES.get(src_label, src_label),
                            "source_value": src_val,
                            "gt_value": gt_val,
                        }
                    )

    return disagreements


# ---------------------------------------------------------------------------
# Derived content flag comparison for Egret (B)
# ---------------------------------------------------------------------------
def _egret_content_flags(egret_rec: dict[str, Any]) -> dict[str, bool]:
    """Derive content flags from Egret detection results."""
    derived = egret_rec.get("content_flags_derived", {})
    if derived:
        return {
            "has_table": derived.get("has_table", False),
            "has_formula": derived.get("has_formula", False),
            "has_figure": derived.get("has_figure", False),
            "has_handwriting": False,  # Egret doesn't detect handwriting
        }

    # Fallback: derive from raw detections
    detections = egret_rec.get("detections", [])
    classes_found = {d.get("class_name_canonical", "").upper() for d in detections}
    return {
        "has_table": "TABLE" in classes_found,
        "has_formula": "FORMULA" in classes_found,
        "has_figure": "PICTURE" in classes_found or "FIGURE" in classes_found,
        "has_handwriting": False,
    }


def _docling_content_flags(docling_rec: dict[str, Any]) -> dict[str, bool]:
    """Derive content flags from Docling GPU layout detection categories."""
    cats = set(docling_rec.get("category_names", []))
    return {
        "has_table": "table" in cats,
        "has_formula": "formula" in cats,
        "has_figure": "picture" in cats or "figure" in cats,
        "has_handwriting": False,  # Docling layout doesn't detect handwriting
    }


# ---------------------------------------------------------------------------
# Main Assembly
# ---------------------------------------------------------------------------
_CONTENT_FLAGS = ("has_table", "has_formula", "has_figure", "has_handwriting")


def _augment_content_flags(
    base_fields: dict[str, dict[str, Any]],
    egret_rec: dict[str, Any],
    docling_rec: dict[str, Any],
) -> None:
    """Augment base_fields content flags with derived values from Egret and Docling."""
    if egret_rec:
        b_flags = _egret_content_flags(egret_rec)
        for flag in _CONTENT_FLAGS:
            base_fields[flag]["B"] = b_flags[flag]
    if docling_rec:
        c_flags = _docling_content_flags(docling_rec)
        for flag in _CONTENT_FLAGS:
            base_fields[flag]["C"] = c_flags[flag]


def _build_diqa_sample_comparison(
    image_id: str,
    base_fields: dict[str, dict[str, Any]],
    source_lookup: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Build a per-sample comparison record for the DIQA comparison."""
    sample_comparison: dict[str, Any] = {
        "image_id": image_id,
        "sources_available": {
            name: image_id in data for name, data in source_lookup.items()
        },
        "fields": {},
    }

    for field_name in COMPARISON_FIELDS:
        sources = base_fields.get(field_name, {})
        gt_val = sources.get("E")

        matches: dict[str, bool | None] = {}
        for src_label, src_val in sources.items():
            if src_label == "E":
                continue
            if src_val is None or gt_val is None:
                matches[src_label] = None
            else:
                matches[src_label] = _values_match(src_val, gt_val)

        sample_comparison["fields"][field_name] = {
            "sources": sources,
            "matches_gt": matches,
        }

    return sample_comparison


def assemble_comparison() -> dict[str, Any]:
    """Load all sources and assemble the full comparison report."""
    print("Loading data sources...")

    l2 = load_l2_metadata()
    print(f"  A  L2 Metadata:         {len(l2):>6,} records")

    egret = load_egret_results()
    print(f"  B  Egret Layout:        {len(egret):>6,} records")

    docling = load_docling_layout()
    print(f"  C  Docling GPU Layout:  {len(docling):>6,} records")

    llm = load_llm_enrichment()
    print(f"  D  LLM Enrichment:      {len(llm):>6,} records")

    gt = load_visual_ground_truth()
    print(f"  E  Visual Ground Truth: {len(gt):>6,} records")

    lang = load_language_enrichment()
    print(f"     Language Enrichment: {len(lang):>6,} records")

    ss = load_sample_set()
    print(f"     Sample Set:          {len(ss):>6,} records")

    audit_ids = sorted(gt.keys())
    print(f"\nAudit samples: {len(audit_ids)}")

    source_lookup: dict[str, dict[str, dict[str, Any]]] = {
        "A": l2,
        "B": egret,
        "C": docling,
        "D": llm,
        "E": gt,
        "lang": lang,
    }

    all_comparisons: list[dict[str, Any]] = []
    for image_id in audit_ids:
        base_fields = extract_field_values(
            image_id,
            l2=l2,
            egret=egret,
            docling=docling,
            llm=llm,
            gt=gt,
            lang=lang,
            sample_set=ss,
        )
        _augment_content_flags(
            base_fields, egret.get(image_id, {}), docling.get(image_id, {})
        )
        all_comparisons.append(
            _build_diqa_sample_comparison(image_id, base_fields, source_lookup)
        )

    metrics = compute_agreement_metrics(all_comparisons)
    disagreements = find_disagreements(all_comparisons)

    report: dict[str, Any] = {
        "report_metadata": {
            "dataset": "diqa-5000",
            "audit_sample_count": len(audit_ids),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "sources": {
                k: {"name": v, "path": str(p)}
                for k, v, p in [
                    ("A", "L2 Metadata", L2_METADATA_PATH),
                    ("B", "Egret Layout", EGRET_RESULTS_PATH),
                    ("C", "Docling GPU Layout", EXTRACTED_DIR),
                    ("D", "LLM Enrichment", LLM_ENRICHMENT_PATH),
                    ("E", "Visual Ground Truth", VISUAL_GT_PATH),
                ]
            },
            "fields_compared": COMPARISON_FIELDS,
        },
        "samples": all_comparisons,
        "agreement_metrics": metrics,
        "disagreements": disagreements,
        "disagreement_count": len(disagreements),
    }

    return report


# ---------------------------------------------------------------------------
# Summary Printer
# ---------------------------------------------------------------------------
def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary statistics to stdout."""
    metrics = report["agreement_metrics"]
    n_samples = report["report_metadata"]["audit_sample_count"]
    n_disagree = report["disagreement_count"]

    print("\n" + "=" * 72)
    print(f"  DIQA-5000 Audit Comparison Report  ({n_samples} samples)")
    print("=" * 72)

    # Per-source overall accuracy
    print("\n--- Overall Accuracy by Source (vs Visual Ground Truth) ---")
    per_source = metrics["per_source"]
    for src_label in sorted(per_source.keys()):
        info = per_source[src_label]
        acc = info["overall_accuracy"]
        acc_str = f"{acc:.1%}" if acc is not None else "N/A"
        print(
            f"  {src_label:>10s} ({info['source_name']:>20s}):  "
            f"{info['fields_matching_gt']:>4d} / {info['fields_compared']:>4d}  "
            f"= {acc_str}"
        )

    # Per-field accuracy breakdown
    print("\n--- Per-Field Accuracy (best source highlighted) ---")
    per_field = metrics["per_field"]
    for field_name in COMPARISON_FIELDS:
        finfo = per_field.get(field_name, {})
        gt_count = finfo.get("gt_values_present", 0)
        best = finfo.get("best_source", "?")
        best_acc = finfo.get("best_accuracy")
        best_str = f"{best_acc:.1%}" if best_acc is not None else "N/A"

        accs = finfo.get("source_accuracies", {})
        parts = []
        for src_label in sorted(accs.keys()):
            a = accs[src_label]
            marker = " *" if src_label == best else ""
            parts.append(f"{src_label}={a:.1%}{marker}")
        acc_detail = ", ".join(parts) if parts else "no comparisons"

        print(
            f"  {field_name:<24s} (n={gt_count:>2d})  best={best} ({best_str})  [{acc_detail}]"
        )

    # Disagreement summary
    print(f"\n--- Disagreements with Ground Truth: {n_disagree} total ---")
    if n_disagree > 0:
        # Group by field
        by_field: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)
        for d in report["disagreements"]:
            by_field[d["field"]] += 1
            by_source[d["source"]] += 1

        print("  By field:")
        for field_name, count in sorted(by_field.items(), key=lambda x: -x[1]):
            print(f"    {field_name:<24s} {count:>3d}")

        print("  By source:")
        for src_label, count in sorted(by_source.items(), key=lambda x: -x[1]):
            name = SOURCE_NAMES.get(src_label, src_label)
            print(f"    {src_label} ({name:<20s}) {count:>3d}")

    print("\n" + "=" * 72)
    print(f"Report written to: {OUTPUT_PATH}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the comparison assembly and write results."""
    report = assemble_comparison()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as fh:
        json.dump(report, fh, indent=2, default=str)

    print_summary(report)


if __name__ == "__main__":
    main()
