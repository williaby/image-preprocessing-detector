#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Select 36 representative images from DIQA-5000 for metadata audit.

Loads four data sources (base metadata, LLM enrichment, language enrichment,
MOS CSVs) and applies stratified sampling across split, folder (ori/res), MOS
quality tier, language, and content-flag diversity constraints.

Usage::

    python scripts/audit/select_diqa_audit_samples.py
    python scripts/audit/select_diqa_audit_samples.py --seed 42
    python scripts/audit/select_diqa_audit_samples.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASET_NAME = "diqa-5000"
TARGET_SAMPLE_COUNT = 36
DEFAULT_SEED = 2026

IMAGE_ROOT = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
METADATA_ROOT = Path("/mnt/e/image_detection/metadata_registry/json")
METADATA_JSON = METADATA_ROOT / "diqa-5000_metadata.json"
LLM_ENRICHMENT_JSON = METADATA_ROOT / "diqa-5000_llm_enrichment.json"
LANGUAGE_ENRICHMENT_JSON = METADATA_ROOT / "diqa-5000_language_enrichment.json"

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results" / "diqa-5000"

# Stratum allocation: (split, folder) -> count
# train has ~3500 res + 350 ori, test has ~1000 res + 100 ori, val has ~500 res + 50 ori
# Base allocation = 30, diversity picks = 6, total = 36
STRATUM_ALLOCATION: dict[tuple[str, str], int] = {
    ("train", "ori"): 4,
    ("train", "res"): 12,
    ("val", "ori"): 2,
    ("val", "res"): 4,
    ("test", "ori"): 2,
    ("test", "res"): 6,
}
DIVERSITY_PICKS = 6  # additional picks to meet diversity constraints

# MOS quality tiers for res/ images
MOS_LOW_UPPER = 2.5
MOS_HIGH_LOWER = 3.5

# Diversity minimums
DIVERSITY_CONSTRAINTS: dict[str, int] = {
    "chinese_language": 6,
    "english_language": 4,
    "other_script": 1,
    "has_table": 2,
    "has_formula": 2,
    "has_handwriting": 1,
    "has_figure": 1,
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MosScores:
    """Mean Opinion Scores from the DIQA ground-truth CSVs."""

    overall: float | None = None
    sharpness: float | None = None
    color_fidelity: float | None = None


@dataclass
class ImageRecord:
    """Merged record for a single image across all data sources."""

    image_id: str
    sample_uuid: str
    image_path: str
    absolute_path: str
    split: str
    folder: str  # "ori" or "res"

    # MOS (only for res/ images)
    mos: MosScores = field(default_factory=MosScores)

    # LLM enrichment (only for ori/ images, ~500 total)
    llm_domain: str | None = None
    llm_language: str | None = None
    llm_has_table: bool = False
    llm_has_formula: bool = False
    llm_has_handwriting: bool = False
    llm_has_figure: bool = False

    # OpenLID language enrichment
    openlid_language: str | None = None
    openlid_script: str | None = None
    openlid_confidence: float | None = None

    selection_reason: str = ""

    @property
    def effective_language(self) -> str | None:
        """Best-effort language from LLM or OpenLID."""
        return self.llm_language or self.openlid_language

    @property
    def is_chinese(self) -> bool:
        """True if either enrichment source reports Chinese."""
        lang = self.effective_language
        return lang in {"zh", "yue"} if lang else False

    @property
    def is_english(self) -> bool:
        """True if either enrichment source reports English."""
        return self.effective_language == "en"

    @property
    def is_other_script(self) -> bool:
        """True if script is neither Hans/Hant/Latn."""
        if self.openlid_script and self.openlid_script not in {
            "Hans",
            "Hant",
            "Latn",
        }:
            return True
        return False

    @property
    def mos_tier(self) -> str:
        """Classify MOS overall into low/mid/high/none."""
        if self.mos.overall is None:
            return "none"
        if self.mos.overall < MOS_LOW_UPPER:
            return "low"
        if self.mos.overall > MOS_HIGH_LOWER:
            return "high"
        return "mid"

    def to_output_dict(self) -> dict[str, Any]:
        """Serialize for the output JSON."""
        return {
            "image_id": self.image_id,
            "sample_uuid": self.sample_uuid,
            "image_path": self.image_path,
            "absolute_path": self.absolute_path,
            "split": self.split,
            "folder": self.folder,
            "mos_overall": self.mos.overall,
            "mos_sharpness": self.mos.sharpness,
            "mos_color_fidelity": self.mos.color_fidelity,
            "llm_domain": self.llm_domain,
            "llm_language": self.llm_language,
            "llm_has_table": self.llm_has_table,
            "llm_has_formula": self.llm_has_formula,
            "llm_has_handwriting": self.llm_has_handwriting,
            "llm_has_figure": self.llm_has_figure,
            "openlid_language": self.openlid_language,
            "openlid_script": self.openlid_script,
            "openlid_confidence": self.openlid_confidence,
            "selection_reason": self.selection_reason,
        }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _parse_split_and_folder(original_path: str) -> tuple[str, str]:
    """Extract split and folder from a path like ``train/ori/train_ori_00001.jpg``.

    Returns:
        Tuple of (split, folder) e.g. ("train", "ori").
    """
    parts = Path(original_path).parts
    if len(parts) >= 2:
        return parts[0], parts[1]
    msg = f"Cannot parse split/folder from path: {original_path}"
    raise ValueError(msg)


def load_metadata(path: Path) -> dict[str, ImageRecord]:
    """Load base metadata and build the initial record map keyed by image_id.

    The image_id is the filename stem (e.g. ``test_ori_00001``).
    """
    logger.info("Loading metadata from %s", path)
    with open(path) as fh:
        data = json.load(fh)

    records: dict[str, ImageRecord] = {}
    for sample in data["samples"]:
        original_path: str = sample["source"]["original_path"]
        filename: str = sample["source"]["original_filename"]
        image_id = filename.removesuffix(".jpg")
        split, folder = _parse_split_and_folder(original_path)

        records[image_id] = ImageRecord(
            image_id=image_id,
            sample_uuid=sample["id"],
            image_path=original_path,
            absolute_path=str(IMAGE_ROOT / original_path),
            split=split,
            folder=folder,
        )

    logger.info("Loaded %d metadata records", len(records))
    return records


def load_llm_enrichment(path: Path, records: dict[str, ImageRecord]) -> None:
    """Merge LLM enrichment data into existing records (in-place)."""
    logger.info("Loading LLM enrichment from %s", path)
    with open(path) as fh:
        data = json.load(fh)

    matched = 0
    for sample in data["samples"]:
        image_id: str = sample["image_id"]
        rec = records.get(image_id)
        if rec is None:
            continue
        rec.llm_domain = sample.get("domain_level1")
        rec.llm_language = sample.get("iso639_language")
        rec.llm_has_table = bool(sample.get("has_table", False))
        rec.llm_has_formula = bool(sample.get("has_formula", False))
        rec.llm_has_handwriting = bool(sample.get("has_handwriting", False))
        rec.llm_has_figure = bool(sample.get("has_figure", False))
        matched += 1

    logger.info("Merged LLM enrichment for %d records", matched)


def load_language_enrichment(path: Path, records: dict[str, ImageRecord]) -> None:
    """Merge OpenLID language enrichment into existing records (in-place)."""
    logger.info("Loading language enrichment from %s", path)
    with open(path) as fh:
        data = json.load(fh)

    matched = 0
    for sample in data["samples"]:
        image_id: str = sample["image_id"]
        rec = records.get(image_id)
        if rec is None:
            continue
        rec.openlid_language = sample.get("language")
        rec.openlid_script = sample.get("script")
        conf = sample.get("confidence")
        rec.openlid_confidence = float(conf) if conf is not None else None
        matched += 1

    logger.info("Merged language enrichment for %d records", matched)


def load_mos_scores(records: dict[str, ImageRecord]) -> None:
    """Load MOS scores from per-split CSVs and merge into res/ records.

    CSVs live at ``IMAGE_ROOT/{split}/{split}.csv`` with columns:
    ``res, ori, overall, sharpness, color_fidelity``.
    """
    for split in ("train", "val", "test"):
        csv_path = IMAGE_ROOT / split / f"{split}.csv"
        if not csv_path.exists():
            logger.warning("MOS CSV not found: %s", csv_path)
            continue

        logger.info("Loading MOS scores from %s", csv_path)
        with open(csv_path, newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                res_filename: str = row["res"]
                res_id = res_filename.removesuffix(".jpg")
                rec = records.get(res_id)
                if rec is None:
                    continue

                rec.mos = MosScores(
                    overall=_safe_float(row.get("overall")),
                    sharpness=_safe_float(row.get("sharpness")),
                    color_fidelity=_safe_float(row.get("color_fidelity")),
                )

                # Also propagate LLM enrichment from the ori partner
                # since LLM enrichment only exists for ori/ images.
                ori_filename: str = row["ori"]
                ori_id = ori_filename.removesuffix(".jpg")
                ori_rec = records.get(ori_id)
                if ori_rec is not None and rec.llm_domain is None:
                    rec.llm_domain = ori_rec.llm_domain
                    rec.llm_language = ori_rec.llm_language
                    rec.llm_has_table = ori_rec.llm_has_table
                    rec.llm_has_formula = ori_rec.llm_has_formula
                    rec.llm_has_handwriting = ori_rec.llm_has_handwriting
                    rec.llm_has_figure = ori_rec.llm_has_figure


def _safe_float(value: str | None) -> float | None:
    """Convert a string to float, returning None on failure."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------
@dataclass
class StratumPool:
    """Pool of candidate images for one (split, folder) stratum."""

    split: str
    folder: str
    target_count: int
    candidates: list[ImageRecord] = field(default_factory=list)
    selected: list[ImageRecord] = field(default_factory=list)


def build_strata(records: dict[str, ImageRecord]) -> list[StratumPool]:
    """Partition records into strata by (split, folder)."""
    pools: dict[tuple[str, str], StratumPool] = {}
    for key, count in STRATUM_ALLOCATION.items():
        pools[key] = StratumPool(split=key[0], folder=key[1], target_count=count)

    for rec in records.values():
        key = (rec.split, rec.folder)
        if key in pools:
            pools[key].candidates.append(rec)

    return list(pools.values())


def _select_from_res_pool(pool: StratumPool, rng: random.Random) -> list[ImageRecord]:
    """Select res/ images stratified by MOS quality tier.

    Distributes the target count roughly evenly across low/mid/high MOS
    tiers, then fills any shortfall from the largest remaining tier.
    """
    by_tier: dict[str, list[ImageRecord]] = {"low": [], "mid": [], "high": []}
    for rec in pool.candidates:
        tier = rec.mos_tier
        if tier in by_tier:
            by_tier[tier].append(rec)
        else:
            # "none" tier (missing MOS) goes to mid bucket
            by_tier["mid"].append(rec)

    target = pool.target_count
    per_tier = target // 3
    remainder = target - per_tier * 3

    selected: list[ImageRecord] = []
    tier_order = ["low", "mid", "high"]

    for idx, tier_name in enumerate(tier_order):
        tier_target = per_tier + (1 if idx < remainder else 0)
        tier_candidates = by_tier[tier_name]
        rng.shuffle(tier_candidates)
        picks = tier_candidates[:tier_target]
        for pick in picks:
            pick.selection_reason = (
                f"{pool.split}/{pool.folder} stratum, MOS tier={tier_name}"
            )
        selected.extend(picks)

    # If any tier was short, fill from other tiers
    if len(selected) < target:
        already = {r.image_id for r in selected}
        all_remaining = [r for r in pool.candidates if r.image_id not in already]
        rng.shuffle(all_remaining)
        shortfall = target - len(selected)
        extras = all_remaining[:shortfall]
        for pick in extras:
            pick.selection_reason = f"{pool.split}/{pool.folder} stratum, MOS tier=fill"
        selected.extend(extras)

    return selected


def _select_from_ori_pool(pool: StratumPool, rng: random.Random) -> list[ImageRecord]:
    """Select ori/ images with basic random sampling."""
    rng.shuffle(pool.candidates)
    picks = pool.candidates[: pool.target_count]
    for pick in picks:
        pick.selection_reason = f"{pool.split}/{pool.folder} stratum"
    return picks


def select_stratum_samples(
    strata: list[StratumPool], rng: random.Random
) -> list[ImageRecord]:
    """Run stratified selection across all (split, folder) strata.

    Returns:
        30 selected records (24 base allocation).
    """
    selected: list[ImageRecord] = []
    for pool in strata:
        if pool.folder == "res":
            picks = _select_from_res_pool(pool, rng)
        else:
            picks = _select_from_ori_pool(pool, rng)
        pool.selected = picks
        selected.extend(picks)

    return selected


# ---------------------------------------------------------------------------
# Diversity enforcement
# ---------------------------------------------------------------------------
@dataclass
class DiversityState:
    """Track how well the current selection meets diversity constraints."""

    chinese_count: int = 0
    english_count: int = 0
    other_script_count: int = 0
    table_count: int = 0
    formula_count: int = 0
    handwriting_count: int = 0
    figure_count: int = 0

    def update_from(self, records: list[ImageRecord]) -> None:
        """Recompute all counts from a list of records."""
        self.chinese_count = sum(1 for r in records if r.is_chinese)
        self.english_count = sum(1 for r in records if r.is_english)
        self.other_script_count = sum(1 for r in records if r.is_other_script)
        self.table_count = sum(1 for r in records if r.llm_has_table)
        self.formula_count = sum(1 for r in records if r.llm_has_formula)
        self.handwriting_count = sum(1 for r in records if r.llm_has_handwriting)
        self.figure_count = sum(1 for r in records if r.llm_has_figure)

    def deficits(self) -> dict[str, int]:
        """Return mapping of constraint name -> shortfall (0 if met)."""
        return {
            "chinese_language": max(
                0, DIVERSITY_CONSTRAINTS["chinese_language"] - self.chinese_count
            ),
            "english_language": max(
                0, DIVERSITY_CONSTRAINTS["english_language"] - self.english_count
            ),
            "other_script": max(
                0, DIVERSITY_CONSTRAINTS["other_script"] - self.other_script_count
            ),
            "has_table": max(0, DIVERSITY_CONSTRAINTS["has_table"] - self.table_count),
            "has_formula": max(
                0, DIVERSITY_CONSTRAINTS["has_formula"] - self.formula_count
            ),
            "has_handwriting": max(
                0, DIVERSITY_CONSTRAINTS["has_handwriting"] - self.handwriting_count
            ),
            "has_figure": max(
                0, DIVERSITY_CONSTRAINTS["has_figure"] - self.figure_count
            ),
        }

    def is_satisfied(self) -> bool:
        """True if all diversity constraints are met."""
        return all(v == 0 for v in self.deficits().values())


def _candidate_satisfies(rec: ImageRecord, constraint_name: str) -> bool:
    """Check whether a candidate helps satisfy a specific deficit."""
    match constraint_name:
        case "chinese_language":
            return rec.is_chinese
        case "english_language":
            return rec.is_english
        case "other_script":
            return rec.is_other_script
        case "has_table":
            return rec.llm_has_table
        case "has_formula":
            return rec.llm_has_formula
        case "has_handwriting":
            return rec.llm_has_handwriting
        case "has_figure":
            return rec.llm_has_figure
        case _:
            return False


def select_diversity_picks(
    current_selection: list[ImageRecord],
    all_records: dict[str, ImageRecord],
    rng: random.Random,
    budget: int,
) -> list[ImageRecord]:
    """Select additional images to satisfy diversity constraints.

    Uses a greedy approach: for each unmet constraint, find a candidate from
    the full pool that satisfies it. If budget remains after meeting all
    constraints, fill with random images for general diversity.

    Args:
        current_selection: Already-selected images.
        all_records: Full pool of all records.
        rng: Seeded random instance.
        budget: Maximum number of additional picks.

    Returns:
        List of additional diversity picks (up to *budget*).
    """
    selected_ids = {r.image_id for r in current_selection}
    diversity_picks: list[ImageRecord] = []

    state = DiversityState()
    state.update_from(current_selection)

    # Priority-ordered constraint resolution
    constraint_priority = [
        "chinese_language",
        "english_language",
        "other_script",
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_figure",
    ]

    remaining_budget = budget

    for constraint_name in constraint_priority:
        deficit = state.deficits().get(constraint_name, 0)
        if deficit <= 0 or remaining_budget <= 0:
            continue

        candidates = [
            r
            for r in all_records.values()
            if r.image_id not in selected_ids
            and _candidate_satisfies(r, constraint_name)
        ]
        rng.shuffle(candidates)

        picks_needed = min(deficit, remaining_budget)
        for candidate in candidates[:picks_needed]:
            candidate.selection_reason = f"diversity pick: {constraint_name}"
            diversity_picks.append(candidate)
            selected_ids.add(candidate.image_id)
            remaining_budget -= 1

        # Recompute state with new picks included
        state.update_from(current_selection + diversity_picks)

    # Fill remaining budget with random diversity picks
    if remaining_budget > 0:
        remaining_candidates = [
            r for r in all_records.values() if r.image_id not in selected_ids
        ]
        rng.shuffle(remaining_candidates)
        for candidate in remaining_candidates[:remaining_budget]:
            candidate.selection_reason = "diversity pick: general"
            diversity_picks.append(candidate)
            selected_ids.add(candidate.image_id)

    return diversity_picks


def _perform_constraint_swaps(
    constraint_name: str,
    deficit: int,
    selected: list[ImageRecord],
    selected_ids: set[str],
    all_records: dict[str, ImageRecord],
    state: DiversityState,
    rng: random.Random,
) -> None:
    """Swap records to satisfy a single diversity constraint."""
    swap_candidates = [
        r
        for r in all_records.values()
        if r.image_id not in selected_ids and _candidate_satisfies(r, constraint_name)
    ]
    rng.shuffle(swap_candidates)

    swaps_done = 0
    for swap_in in swap_candidates:
        if swaps_done >= deficit:
            break
        swap_out_candidates = [
            r
            for r in selected
            if r.split == swap_in.split
            and r.folder == swap_in.folder
            and not _candidate_satisfies(r, constraint_name)
            and not _is_uniquely_needed(r, selected, state)
        ]
        if not swap_out_candidates:
            continue

        swap_out = rng.choice(swap_out_candidates)
        idx = selected.index(swap_out)
        selected[idx] = swap_in
        swap_in.selection_reason = (
            f"swap for diversity: {constraint_name} (replaced {swap_out.image_id})"
        )
        selected_ids.discard(swap_out.image_id)
        selected_ids.add(swap_in.image_id)
        swaps_done += 1


def apply_swap_repairs(
    selected: list[ImageRecord],
    all_records: dict[str, ImageRecord],
    rng: random.Random,
) -> list[ImageRecord]:
    """Swap out base-stratum picks to meet diversity constraints if needed.

    Only swaps within the same stratum (split, folder) to preserve the
    stratification structure. Returns the repaired selection list.
    """
    state = DiversityState()
    state.update_from(selected)

    if state.is_satisfied():
        return selected

    logger.info("Running swap repairs to meet diversity constraints")
    selected_ids = {r.image_id for r in selected}

    constraint_priority = [
        "chinese_language",
        "english_language",
        "other_script",
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_figure",
    ]

    for constraint_name in constraint_priority:
        deficit = state.deficits().get(constraint_name, 0)
        if deficit <= 0:
            continue
        _perform_constraint_swaps(
            constraint_name,
            deficit,
            selected,
            selected_ids,
            all_records,
            state,
            rng,
        )
        state.update_from(selected)

    return selected


def _is_uniquely_needed(
    rec: ImageRecord,
    _selected: list[ImageRecord],
    state: DiversityState,
) -> bool:
    """Check if removing *rec* would create a new diversity deficit.

    Prevents swapping out a record that is the sole contributor to a
    currently-satisfied constraint.
    """
    check_attrs = [
        ("chinese_language", rec.is_chinese, state.chinese_count),
        ("english_language", rec.is_english, state.english_count),
        ("other_script", rec.is_other_script, state.other_script_count),
        ("has_table", rec.llm_has_table, state.table_count),
        ("has_formula", rec.llm_has_formula, state.formula_count),
        ("has_handwriting", rec.llm_has_handwriting, state.handwriting_count),
        ("has_figure", rec.llm_has_figure, state.figure_count),
    ]

    for constraint_name, has_attr, current_count in check_attrs:
        minimum = DIVERSITY_CONSTRAINTS[constraint_name]
        if has_attr and current_count <= minimum:
            return True

    return False


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------
def build_output(
    selected: list[ImageRecord],
    seed: int,
) -> dict[str, Any]:
    """Build the final JSON output structure."""
    state = DiversityState()
    state.update_from(selected)

    # Stratum distribution summary
    stratum_dist: dict[str, int] = {}
    for rec in selected:
        key = f"{rec.split}/{rec.folder}"
        stratum_dist[key] = stratum_dist.get(key, 0) + 1

    # MOS tier distribution for res/ images
    mos_dist: dict[str, int] = {}
    for rec in selected:
        if rec.folder == "res":
            tier = rec.mos_tier
            mos_dist[tier] = mos_dist.get(tier, 0) + 1

    return {
        "dataset": DATASET_NAME,
        "sample_count": len(selected),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "random_seed": seed,
        "selection_criteria": {
            "target_count": TARGET_SAMPLE_COUNT,
            "stratum_allocation": {
                f"{k[0]}/{k[1]}": v for k, v in STRATUM_ALLOCATION.items()
            },
            "diversity_picks": DIVERSITY_PICKS,
            "mos_tiers": {
                "low": f"overall < {MOS_LOW_UPPER}",
                "mid": f"{MOS_LOW_UPPER} <= overall <= {MOS_HIGH_LOWER}",
                "high": f"overall > {MOS_HIGH_LOWER}",
            },
            "diversity_constraints": DIVERSITY_CONSTRAINTS,
        },
        "distribution_summary": {
            "by_stratum": stratum_dist,
            "by_mos_tier": mos_dist,
            "diversity_counts": {
                "chinese_language": state.chinese_count,
                "english_language": state.english_count,
                "other_script": state.other_script_count,
                "has_table": state.table_count,
                "has_formula": state.formula_count,
                "has_handwriting": state.handwriting_count,
                "has_figure": state.figure_count,
            },
            "diversity_satisfied": state.is_satisfied(),
        },
        "samples": [rec.to_output_dict() for rec in selected],
    }


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------
def _print_stratum_table(
    base_picks: list[ImageRecord],
    div_picks: list[ImageRecord],
    total_selected: int,
) -> None:
    """Print the stratum distribution table."""
    print(f"\n{'Stratum Distribution':}")
    print(f"  {'Stratum':<20} {'Base':>6}  {'Target':>6}")
    print(f"  {'-' * 20} {'-' * 6}  {'-' * 6}")
    for (split, folder), target in STRATUM_ALLOCATION.items():
        count = sum(1 for r in base_picks if r.split == split and r.folder == folder)
        marker = " *" if count != target else ""
        print(f"  {split}/{folder:<15} {count:>6}  {target:>6}{marker}")
    print(f"  {'diversity picks':<20} {len(div_picks):>6}  {DIVERSITY_PICKS:>6}")
    print(f"  {'TOTAL':<20} {total_selected:>6}  {TARGET_SAMPLE_COUNT:>6}")


def _print_mos_table(selected: list[ImageRecord]) -> None:
    """Print MOS quality tier distribution for res/ images."""
    print(f"\n{'MOS Quality Tier Distribution (res/ only)':}")
    res_selected = [r for r in selected if r.folder == "res"]
    tier_counts: dict[str, int] = {"low": 0, "mid": 0, "high": 0}
    for rec in res_selected:
        tier = rec.mos_tier
        if tier in tier_counts:
            tier_counts[tier] += 1
    for tier_name, count in tier_counts.items():
        print(f"  {tier_name:<10} {count:>4}")
    print(f"  {'total':<10} {sum(tier_counts.values()):>4}")


def _print_diversity_table(state: DiversityState) -> bool:
    """Print diversity constraint satisfaction table. Returns True if all met."""
    print(f"\n{'Diversity Constraint Satisfaction':}")
    print(f"  {'Constraint':<22} {'Count':>6}  {'Min':>4}  {'Status'}")
    print(f"  {'-' * 22} {'-' * 6}  {'-' * 4}  {'-' * 6}")
    constraint_map = {
        "chinese_language": state.chinese_count,
        "english_language": state.english_count,
        "other_script": state.other_script_count,
        "has_table": state.table_count,
        "has_formula": state.formula_count,
        "has_handwriting": state.handwriting_count,
        "has_figure": state.figure_count,
    }
    all_met = True
    for name, count in constraint_map.items():
        minimum = DIVERSITY_CONSTRAINTS[name]
        met = count >= minimum
        if not met:
            all_met = False
        status = "OK" if met else "UNMET"
        print(f"  {name:<22} {count:>6}  {minimum:>4}  {status}")
    return all_met


def print_summary(selected: list[ImageRecord]) -> None:
    """Print a human-readable distribution table."""
    state = DiversityState()
    state.update_from(selected)

    sep = "-" * 62
    print(f"\n{'DIQA-5000 Audit Sample Selection Summary':^62}")
    print(sep)

    def is_diversity(rec: ImageRecord) -> bool:
        return rec.selection_reason.startswith("diversity")

    base_picks = [r for r in selected if not is_diversity(r)]
    div_picks = [r for r in selected if is_diversity(r)]

    _print_stratum_table(base_picks, div_picks, len(selected))
    _print_mos_table(selected)
    all_met = _print_diversity_table(state)

    print(sep)
    overall = "ALL CONSTRAINTS MET" if all_met else "SOME CONSTRAINTS UNMET"
    print(f"  Result: {overall}")
    print(sep)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_selection(seed: int, dry_run: bool = False) -> dict[str, Any]:
    """Execute the full sample selection pipeline.

    Args:
        seed: Random seed for reproducibility.
        dry_run: If True, print summary but do not write output file.

    Returns:
        The output JSON structure.
    """
    rng = random.Random(seed)

    # Step 1: Load all data sources
    records = load_metadata(METADATA_JSON)
    load_llm_enrichment(LLM_ENRICHMENT_JSON, records)
    load_language_enrichment(LANGUAGE_ENRICHMENT_JSON, records)
    load_mos_scores(records)

    logger.info(
        "Total records loaded: %d (ori=%d, res=%d)",
        len(records),
        sum(1 for r in records.values() if r.folder == "ori"),
        sum(1 for r in records.values() if r.folder == "res"),
    )

    # Step 2: Stratified sampling (30 base picks)
    strata = build_strata(records)
    base_selection = select_stratum_samples(strata, rng)
    logger.info("Base stratum selection: %d images", len(base_selection))

    # Step 3: Swap repairs within strata to improve diversity
    base_selection = apply_swap_repairs(base_selection, records, rng)

    # Step 4: Diversity picks (6 additional)
    diversity_extra = select_diversity_picks(
        base_selection, records, rng, budget=DIVERSITY_PICKS
    )
    logger.info("Diversity picks: %d images", len(diversity_extra))

    # Step 5: Combine and verify
    final_selection = base_selection + diversity_extra
    assert len(final_selection) == TARGET_SAMPLE_COUNT, (
        f"Expected {TARGET_SAMPLE_COUNT} samples, got {len(final_selection)}"
    )

    # Step 6: Print summary
    print_summary(final_selection)

    # Step 7: Build and write output
    output = build_output(final_selection, seed)

    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "sample_set.json"
        with open(output_path, "w") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False)
        logger.info("Wrote %d samples to %s", len(final_selection), output_path)
        print(f"\nOutput written to: {output_path}")
    else:
        print("\n[DRY RUN] No output file written.")

    return output


def main() -> None:
    """Entry point for CLI execution."""
    parser = argparse.ArgumentParser(
        description="Select 36 representative DIQA-5000 images for metadata audit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing output file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_selection(seed=args.seed, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
