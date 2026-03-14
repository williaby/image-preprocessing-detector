#!/usr/bin/env python3
"""DIQA-OCR Correlation Analysis.

Correlates OCR quality proxy metrics with DIQA-5000 human MOS scores
to identify which OCR output characteristics predict perceptual quality.

Data sources:
    - L2 metadata: /mnt/e/image_detection/metadata_registry/json/diqa-5000_metadata.json
    - OCR text: /mnt/e/image_detection/annotations/diqa-5000/ocr/ocr_batch_*.jsonl
    - SigLIP2: siglip2_diqa5000_outputs/*.jsonl

Output:
    - results/diqa_ocr_correlation_report.json
    - Console summary table

Usage:
    PYTHONPATH=/home/byron/dev/image_detection uv run python scripts/analyze_diqa_ocr_correlation.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy import stats

# Project imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.image_preprocessing_detector.schema_utils.ocr_quality_proxy import (  # noqa: E402
    compute_all_proxies,
)

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
L2_METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/diqa-5000_metadata.json"
)
OCR_DIR = Path("/mnt/e/image_detection/annotations/diqa-5000/ocr")
SIGLIP2_DIR = Path("siglip2_diqa5000_outputs")
OUTPUT_PATH = Path("results/diqa_ocr_correlation_report.json")

# Text-class layout labels (egret-xlarge uses lowercase with underscores)
# Matching both canonical (UPPER) and raw (lowercase) forms
TEXT_CLASSES = frozenset({
    "text", "title", "section_header", "caption", "footnote",
    "list_item", "formula", "page_header", "page_footer",
    "Text", "Title", "Section-Header", "Caption", "Footnote",
    "List-Item", "Formula", "Page-Header", "Page-Footer",
    "TEXT", "TITLE", "SECTION_HEADER", "CAPTION", "FOOTNOTE",
    "LIST_ITEM", "FORMULA", "PAGE_HEADER", "PAGE_FOOTER",
})


@dataclass
class CorrelationResult:
    """Statistical test result for one proxy-MOS pair."""

    proxy_name: str
    mos_dimension: str
    spearman_r: float
    spearman_p: float
    pearson_r: float
    pearson_p: float
    significant_after_fdr: bool = False


@dataclass
class GroupComparisonResult:
    """Kruskal-Wallis test across MOS quartiles."""

    proxy_name: str
    mos_dimension: str
    h_statistic: float
    p_value: float
    quartile_medians: list[float]


@dataclass
class EffectSizeResult:
    """Cohen's d between ori/ and res/ groups."""

    proxy_name: str
    cohens_d: float
    ori_mean: float
    res_mean: float
    ori_n: int
    res_n: int


# -----------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------


def load_l2_metadata() -> list[dict]:
    """Load L2 metadata and return per-sample records with enrichment data."""
    print(f"Loading L2 metadata from {L2_METADATA_PATH}...")
    with open(L2_METADATA_PATH) as f:
        data = json.load(f)

    samples = data["samples"]
    print(f"  Loaded {len(samples)} samples")

    records = []
    for s in samples:
        d = s["enrichments"]["versions"][-1]["data"]
        source = s["source"]
        path = source["original_path"]

        # Parse image dimensions
        res = d.get("resolution_pixels", [0, 0])
        width, height = int(res[0]), int(res[1])

        # Layout text regions
        layout_dets = d.get("layout_detections", [])
        text_regions = [
            det for det in layout_dets
            if det.get("class_name", "") in TEXT_CLASSES
            or det.get("canonical_class", "") in TEXT_CLASSES
        ]
        text_region_count = len(text_regions)

        # Compute text region area from bounding boxes (COCO xywh)
        text_area_px = 0.0
        for det in text_regions:
            bbox = det.get("bbox", [0, 0, 0, 0])
            if len(bbox) == 4:
                text_area_px += bbox[2] * bbox[3]  # width * height

        image_area = width * height
        text_area_ratio = text_area_px / image_area if image_area > 0 else 0.0

        # Extract text stats
        text_stats = d.get("text_statistics", {})

        records.append({
            "image": source["original_filename"],
            "path": path,
            "split": source.get("split", d.get("split", "")),
            "is_ori": "/ori/" in path,
            "is_res": "/res/" in path,
            "width": width,
            "height": height,
            "mos_overall": d.get("quality_overall_mos"),
            "mos_sharpness": d.get("quality_sharpness_mos"),
            "mos_color": d.get("quality_color_fidelity_mos"),
            "text_region_count": text_region_count,
            "text_area_px": text_area_px,
            "text_area_ratio": text_area_ratio,
            "char_count": text_stats.get("char_count", 0),
            "classical_iqa_blur_score": d.get("classical_iqa_blur_score"),
            "classical_iqa_noise_level": d.get("classical_iqa_noise_level"),
            "classical_iqa_contrast_score": d.get("classical_iqa_contrast_score"),
        })

    return records


def load_ocr_text() -> dict[str, str]:
    """Load OCR text from batch JSONL files, keyed by filename."""
    print(f"Loading OCR text from {OCR_DIR}...")
    ocr_map: dict[str, str] = {}

    for jsonl_file in sorted(OCR_DIR.glob("ocr_batch_*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                rec = json.loads(line)
                source = rec.get("source", "")
                # Extract filename from source path
                filename = Path(source).name
                if rec.get("success", False) and rec.get("text"):
                    ocr_map[filename] = rec["text"]

    print(f"  Loaded OCR for {len(ocr_map)} images")
    return ocr_map


def load_siglip2_predictions() -> dict[str, dict]:
    """Load SigLIP2 predictions from JSONL files, keyed by image name."""
    print(f"Loading SigLIP2 predictions from {SIGLIP2_DIR}...")
    siglip_map: dict[str, dict] = {}

    for jsonl_file in sorted(SIGLIP2_DIR.glob("siglip2_diqa5000_*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                rec = json.loads(line)
                siglip_map[rec["image"]] = rec

    print(f"  Loaded SigLIP2 for {len(siglip_map)} images")
    return siglip_map


# -----------------------------------------------------------------------
# Compute proxy metrics
# -----------------------------------------------------------------------


def compute_all_metrics(
    records: list[dict],
    ocr_map: dict[str, str],
    siglip_map: dict[str, dict],
) -> list[dict]:
    """Compute OCR proxy metrics for all records."""
    print("Computing OCR proxy metrics...")

    # First pass: compute text_yield for all to find max (for normalization)
    text_yields: list[float] = []
    for rec in records:
        text = ocr_map.get(rec["image"], "")
        if text and rec["width"] > 0 and rec["height"] > 0:
            area_mpx = (rec["width"] * rec["height"]) / 1_000_000.0
            non_ws = len(text.replace(" ", "").replace("\n", ""))
            text_yields.append(non_ws / area_mpx if area_mpx > 0 else 0.0)
    text_yield_max = max(text_yields) if text_yields else 1.0

    # Build ori text_yield map for paired analysis
    ori_yields: dict[str, float] = {}
    for rec in records:
        if rec["is_ori"]:
            text = ocr_map.get(rec["image"], "")
            area_mpx = (rec["width"] * rec["height"]) / 1_000_000.0
            if area_mpx > 0:
                non_ws = len(text.replace(" ", "").replace("\n", ""))
                # Map ori number to yield: test_ori_00001 -> 00001
                num = rec["image"].split("_")[-1].split(".")[0]
                ori_yields[num] = non_ws / area_mpx

    enriched = []
    for rec in records:
        text = ocr_map.get(rec["image"], "")

        # Find paired ori text_yield for res/ images
        ori_yield = None
        if rec["is_res"]:
            num = rec["image"].split("_")[-1].split(".")[0]
            ori_yield = ori_yields.get(num)

        # SigLIP2 IQA
        siglip = siglip_map.get(rec["image"], {})
        iqa_mu = siglip.get("iqa_overall_mu")

        metrics = compute_all_proxies(
            text=text,
            image_width=rec["width"],
            image_height=rec["height"],
            layout_text_region_count=rec["text_region_count"],
            text_region_area_px=rec["text_area_px"],
            layout_text_area_ratio=rec["text_area_ratio"],
            ori_text_yield=ori_yield,
            iqa_overall_mu=iqa_mu,
            text_yield_max=text_yield_max,
        )

        rec["metrics"] = metrics.to_dict()
        rec["ocr_text_length"] = len(text)
        enriched.append(rec)

    print(f"  Computed metrics for {len(enriched)} images")
    return enriched


# -----------------------------------------------------------------------
# Statistical analysis
# -----------------------------------------------------------------------

PROXY_NAMES = [
    "text_yield", "word_density", "ocr_completeness",
    "cjk_latin_consistency", "line_regularity", "valid_char_rate",
    "layout_text_agreement",
]
MOS_DIMS = ["mos_overall", "mos_sharpness", "mos_color"]


def run_correlations(records: list[dict]) -> list[CorrelationResult]:
    """Spearman + Pearson correlations for each proxy vs each MOS dimension."""
    # Filter to res/ images with MOS scores
    res_records = [
        r for r in records
        if r["is_res"] and r.get("mos_overall") is not None
    ]
    print(f"\nCorrelation analysis on {len(res_records)} res/ images with MOS...")

    results = []
    for proxy in PROXY_NAMES:
        for mos_dim in MOS_DIMS:
            x = np.array([r["metrics"][proxy] for r in res_records], dtype=np.float64)
            y = np.array([r[mos_dim] for r in res_records], dtype=np.float64)

            # Remove NaN pairs
            mask = ~(np.isnan(x) | np.isnan(y))
            x, y = x[mask], y[mask]

            if len(x) < 10:
                continue

            # Skip constant arrays
            if np.std(x) < 1e-10 or np.std(y) < 1e-10:
                continue

            sp_r, sp_p = stats.spearmanr(x, y)
            pe_r, pe_p = stats.pearsonr(x, y)

            if np.isnan(sp_r) or np.isnan(pe_r):
                continue

            results.append(CorrelationResult(
                proxy_name=proxy,
                mos_dimension=mos_dim.replace("mos_", ""),
                spearman_r=float(sp_r),
                spearman_p=float(sp_p),
                pearson_r=float(pe_r),
                pearson_p=float(pe_p),
            ))

    # Benjamini-Hochberg FDR correction
    p_values = [r.spearman_p for r in results]
    if p_values:
        sorted_indices = np.argsort(p_values)
        m = len(p_values)
        for rank, idx in enumerate(sorted_indices, 1):
            threshold = 0.05 * rank / m
            results[idx].significant_after_fdr = p_values[idx] <= threshold

    return results


def run_ori_res_comparison(records: list[dict]) -> list[EffectSizeResult]:
    """Cohen's d between ori/ and res/ groups for each proxy."""
    ori_records = [r for r in records if r["is_ori"]]
    res_records = [r for r in records if r["is_res"]]

    print(f"\nOri/Res comparison: {len(ori_records)} ori vs {len(res_records)} res...")

    results = []
    for proxy in PROXY_NAMES:
        ori_vals = np.array(
            [r["metrics"][proxy] for r in ori_records], dtype=np.float64
        )
        res_vals = np.array(
            [r["metrics"][proxy] for r in res_records], dtype=np.float64
        )

        ori_vals = ori_vals[~np.isnan(ori_vals)]
        res_vals = res_vals[~np.isnan(res_vals)]

        if len(ori_vals) < 5 or len(res_vals) < 5:
            continue

        # Cohen's d
        pooled_std = np.sqrt(
            (np.var(ori_vals) * (len(ori_vals) - 1)
             + np.var(res_vals) * (len(res_vals) - 1))
            / (len(ori_vals) + len(res_vals) - 2)
        )
        d = (float(np.mean(res_vals)) - float(np.mean(ori_vals))) / max(pooled_std, 1e-10)

        results.append(EffectSizeResult(
            proxy_name=proxy,
            cohens_d=float(d),
            ori_mean=float(np.mean(ori_vals)),
            res_mean=float(np.mean(res_vals)),
            ori_n=len(ori_vals),
            res_n=len(res_vals),
        ))

    return results


def run_quartile_analysis(records: list[dict]) -> list[GroupComparisonResult]:
    """Kruskal-Wallis H-test across MOS quartiles for each proxy."""
    res_records = [
        r for r in records
        if r["is_res"] and r.get("mos_overall") is not None
    ]

    results = []
    for proxy in PROXY_NAMES:
        for mos_dim in MOS_DIMS:
            mos_vals = np.array(
                [r[mos_dim] for r in res_records], dtype=np.float64
            )
            proxy_vals = np.array(
                [r["metrics"][proxy] for r in res_records], dtype=np.float64
            )

            mask = ~(np.isnan(mos_vals) | np.isnan(proxy_vals))
            mos_vals = mos_vals[mask]
            proxy_vals = proxy_vals[mask]

            if len(mos_vals) < 20:
                continue

            # Split into quartiles
            quartiles = np.percentile(mos_vals, [25, 50, 75])
            groups = []
            q_medians = []
            for i in range(4):
                if i == 0:
                    group_mask = mos_vals <= quartiles[0]
                elif i == 3:
                    group_mask = mos_vals > quartiles[2]
                else:
                    group_mask = (mos_vals > quartiles[i - 1]) & (mos_vals <= quartiles[i])

                group = proxy_vals[group_mask]
                if len(group) > 0:
                    groups.append(group)
                    q_medians.append(float(np.median(group)))

            if len(groups) < 2:
                continue

            # Skip if all groups are constant
            if all(np.std(g) < 1e-10 for g in groups):
                continue

            try:
                h_stat, p_val = stats.kruskal(*groups)
            except ValueError:
                continue

            if np.isnan(h_stat):
                continue

            results.append(GroupComparisonResult(
                proxy_name=proxy,
                mos_dimension=mos_dim.replace("mos_", ""),
                h_statistic=float(h_stat),
                p_value=float(p_val),
                quartile_medians=q_medians,
            ))

    return results


def run_siglip2_analysis(records: list[dict]) -> dict:
    """Analyze SigLIP2-OCR agreement metric if available."""
    res_with_siglip = [
        r for r in records
        if r["is_res"]
        and r.get("mos_overall") is not None
        and r["metrics"].get("siglip2_ocr_agreement") is not None
    ]

    if not res_with_siglip:
        return {"available": False, "reason": "No SigLIP2 predictions found"}

    agreement_vals = np.array(
        [r["metrics"]["siglip2_ocr_agreement"] for r in res_with_siglip],
        dtype=np.float64,
    )
    mos_vals = np.array(
        [r["mos_overall"] for r in res_with_siglip], dtype=np.float64
    )

    sp_r, sp_p = stats.spearmanr(agreement_vals, mos_vals)

    return {
        "available": True,
        "n_samples": len(res_with_siglip),
        "agreement_mean": float(np.mean(agreement_vals)),
        "agreement_std": float(np.std(agreement_vals)),
        "spearman_r_vs_mos_overall": float(sp_r),
        "spearman_p": float(sp_p),
    }


# -----------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------


def print_summary(
    correlations: list[CorrelationResult],
    effect_sizes: list[EffectSizeResult],
    quartile_results: list[GroupComparisonResult],
    siglip2_analysis: dict,
) -> None:
    """Print formatted summary table to console."""
    print("\n" + "=" * 80)
    print("DIQA-OCR CORRELATION ANALYSIS RESULTS")
    print("=" * 80)

    # Correlation table
    print("\n--- Spearman Correlations (proxy vs MOS) ---")
    print(f"{'Proxy':<25} {'MOS Dim':<12} {'r':>7} {'p':>10} {'FDR sig':>8} {'Strength':>12}")
    print("-" * 80)

    for c in sorted(correlations, key=lambda x: abs(x.spearman_r), reverse=True):
        strength = (
            "STRONG" if abs(c.spearman_r) > 0.7
            else "moderate" if abs(c.spearman_r) > 0.5
            else "weak" if abs(c.spearman_r) > 0.3
            else "negligible"
        )
        sig = "YES" if c.significant_after_fdr else "no"
        print(
            f"{c.proxy_name:<25} {c.mos_dimension:<12} "
            f"{c.spearman_r:>7.3f} {c.spearman_p:>10.2e} "
            f"{sig:>8} {strength:>12}"
        )

    # Effect sizes
    print("\n--- Ori vs Res Effect Sizes (Cohen's d) ---")
    print(f"{'Proxy':<25} {'d':>8} {'Ori Mean':>10} {'Res Mean':>10} {'Effect':>10}")
    print("-" * 65)

    for e in sorted(effect_sizes, key=lambda x: abs(x.cohens_d), reverse=True):
        effect = (
            "large" if abs(e.cohens_d) > 0.8
            else "medium" if abs(e.cohens_d) > 0.5
            else "small" if abs(e.cohens_d) > 0.2
            else "negligible"
        )
        print(
            f"{e.proxy_name:<25} {e.cohens_d:>8.3f} "
            f"{e.ori_mean:>10.4f} {e.res_mean:>10.4f} {effect:>10}"
        )

    # Quartile analysis (top results only)
    print("\n--- Kruskal-Wallis H-test (top 5 by H-statistic) ---")
    print(f"{'Proxy':<25} {'MOS Dim':<12} {'H':>10} {'p':>10} {'Q1->Q4 Medians'}")
    print("-" * 80)

    for q in sorted(quartile_results, key=lambda x: x.h_statistic, reverse=True)[:5]:
        medians_str = " -> ".join(f"{m:.4f}" for m in q.quartile_medians)
        print(
            f"{q.proxy_name:<25} {q.mos_dimension:<12} "
            f"{q.h_statistic:>10.1f} {q.p_value:>10.2e} {medians_str}"
        )

    # SigLIP2
    print("\n--- SigLIP2-OCR Agreement ---")
    if siglip2_analysis.get("available"):
        print(f"  N samples: {siglip2_analysis['n_samples']}")
        print(f"  Agreement mean: {siglip2_analysis['agreement_mean']:.4f}")
        print(f"  Spearman r vs MOS overall: {siglip2_analysis['spearman_r_vs_mos_overall']:.4f}")
        print(f"  p-value: {siglip2_analysis['spearman_p']:.2e}")
    else:
        print(f"  {siglip2_analysis.get('reason', 'N/A')}")

    # Summary
    print("\n--- Key Findings ---")
    sig_correlations = [
        c for c in correlations if c.significant_after_fdr and abs(c.spearman_r) > 0.3
    ]
    if sig_correlations:
        print("Proxies with significant |r| > 0.3 (calibration-useful):")
        for c in sig_correlations:
            print(f"  {c.proxy_name} vs {c.mos_dimension}: r={c.spearman_r:.3f}")
    else:
        print("No proxies reached |r| > 0.3 with FDR significance.")
        print("Consider: DIQA-5000's paired structure (10 enhancements per base)")
        print("causes within-group variance that attenuates correlations.")

    large_effects = [e for e in effect_sizes if abs(e.cohens_d) > 0.5]
    if large_effects:
        print("\nProxies with medium/large ori-vs-res effect:")
        for e in large_effects:
            direction = "res > ori" if e.cohens_d > 0 else "ori > res"
            print(f"  {e.proxy_name}: d={e.cohens_d:.3f} ({direction})")


def save_report(
    correlations: list[CorrelationResult],
    effect_sizes: list[EffectSizeResult],
    quartile_results: list[GroupComparisonResult],
    siglip2_analysis: dict,
    record_count: int,
    res_count: int,
) -> None:
    """Save full report to JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "metadata": {
            "dataset": "diqa-5000",
            "total_images": record_count,
            "res_images_with_mos": res_count,
            "proxy_metrics": PROXY_NAMES,
            "mos_dimensions": [d.replace("mos_", "") for d in MOS_DIMS],
        },
        "correlations": [asdict(c) for c in correlations],
        "effect_sizes": [asdict(e) for e in effect_sizes],
        "quartile_analysis": [asdict(q) for q in quartile_results],
        "siglip2_analysis": siglip2_analysis,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {OUTPUT_PATH}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------


def main() -> None:
    """Run the full DIQA-OCR correlation analysis."""
    # Load data
    records = load_l2_metadata()
    ocr_map = load_ocr_text()
    siglip_map = load_siglip2_predictions()

    # Compute metrics
    enriched = compute_all_metrics(records, ocr_map, siglip_map)

    # Run analyses
    correlations = run_correlations(enriched)
    effect_sizes = run_ori_res_comparison(enriched)
    quartile_results = run_quartile_analysis(enriched)
    siglip2_analysis = run_siglip2_analysis(enriched)

    # Count for report
    res_with_mos = sum(
        1 for r in enriched
        if r["is_res"] and r.get("mos_overall") is not None
    )

    # Output
    print_summary(correlations, effect_sizes, quartile_results, siglip2_analysis)
    save_report(
        correlations, effect_sizes, quartile_results,
        siglip2_analysis, len(enriched), res_with_mos,
    )


if __name__ == "__main__":
    main()
