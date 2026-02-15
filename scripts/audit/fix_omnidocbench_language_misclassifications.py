#!/usr/bin/env python3
"""Fix omnidocbench language/script misclassifications found during 100% visual review.

Visual review of all 672 LLM-pre-classified omnidocbench samples across 8 prefix
groups (jiaocai, jiaocaineedrop, yanbaor2, yanbaopptmerge, PPT, eastmoney, scihub,
book) found ~75 samples incorrectly classified as zh/cjk that should be en/latin.

Misclassification sources:
- jiaocai: 3 files with "_en_" in name that are English academic content, not Chinese
- jiaocaineedrop: 26 files (Libretexts, English textbooks, chapter files) among Chinese
- yanbaor2: 29 files (EY reports, international consulting, English PPTs) among Chinese
- yanbaopptmerge: 17 files (CS/SE textbooks, English teaching slides) among Chinese

Usage::

    python scripts/audit/fix_omnidocbench_language_misclassifications.py --dry-run
    python scripts/audit/fix_omnidocbench_language_misclassifications.py

"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/omnidocbench_metadata.json"
)

# ============================================================================
# jiaocai group: 3 files with English academic content incorrectly tagged zh/cjk
# These have "_en_" in filename but are genuinely English academic content
# (Theory of Computation exam, SQL exam, bilingual CS exam)
# ============================================================================
JIAOCAI_EN_FILES: set[str] = {
    "jiaocai_jiaocai_en_37.jpg",  # English Theory of Computation exam
    "jiaocai_jiaocai_en_91.jpg",  # English SQL database exam
    "jiaocai_jiaocai_en_310.jpg",  # Bilingual Chinese header + English CS exam
}

# ============================================================================
# jiaocaineedrop group: 26 files that are English academic content
# Libretexts (bio-*, biz-*, chem-*, eng-*, geo-*, socialsci-*, math-*)
# English textbooks (Evans_PDE, Proofs_From_The_Book, AMC8)
# Chapter files (Chap11, Chapter9, chap02/05/10/15, c04, unit2t03)
# Other (2005_QP)
# NOTE: All ~188 jiaocai_needrop_en_* files are CHINESE despite "en" in name
# NOTE: c2-ma-11-q-11-cl is CHINESE (correctly classified)
# ============================================================================
JIAOCAINEEDROP_EN_FILES: set[str] = {
    # Libretexts-style academic content (12 files)
    "jiaocaineedrop_bio-113065.pdf_213.jpg",
    "jiaocaineedrop_biz-96816.pdf_48.jpg",
    "jiaocaineedrop_chem-203343.pdf_121.jpg",
    "jiaocaineedrop_chem-323236.pdf_183.jpg",
    "jiaocaineedrop_chem-354334.pdf_20.jpg",
    "jiaocaineedrop_chem-436205.pdf_793.jpg",
    "jiaocaineedrop_chem-441760.pdf_165.jpg",
    "jiaocaineedrop_chem-97961.pdf_128.jpg",
    "jiaocaineedrop_eng-45646.pdf_30.jpg",
    "jiaocaineedrop_geo-12644.pdf_353.jpg",
    "jiaocaineedrop_math-134115.pdf_670.jpg",
    "jiaocaineedrop_socialsci-74973.pdf_31.jpg",
    # English textbook names (3 files)
    "jiaocaineedrop_AMC8_V5.pdf_64.jpg",
    "jiaocaineedrop_Evans_PDE_Solution_Chapter_6_Second-Order_Elliptic_Equations.pdf_5.jpg",
    "jiaocaineedrop_Proofs_From_The_Book(Aigner).pdf_54.jpg",
    # Chapter/unit files - English (8 files, excludes c2-ma which is Chinese)
    "jiaocaineedrop_Chap11.pdf_10.jpg",
    "jiaocaineedrop_Chapter9.pdf_46.jpg",
    "jiaocaineedrop_chap02.pdf_16.jpg",
    "jiaocaineedrop_chap05.pdf_4.jpg",  # Note: listed as chap5 in dir
    "jiaocaineedrop_chap10.pdf_8.jpg",
    "jiaocaineedrop_chap15.pdf_3.jpg",
    "jiaocaineedrop_c04_874768_mt.pdf_6.jpg",
    "jiaocaineedrop_unit2t03.pdf_63.jpg",
    # Other English content (3 files)
    "jiaocaineedrop_2005_QP.pdf_5.jpg",
    "jiaocaineedrop_eng_gls.pdf_6.jpg",
    "jiaocaineedrop_glossary.pdf_7.jpg",
}

# Alternate filename for chap5 (may appear as chap5 instead of chap05)
JIAOCAINEEDROP_EN_ALTS: dict[str, str] = {
    "jiaocaineedrop_chap5.pdf_4.jpg": "jiaocaineedrop_chap05.pdf_4.jpg",
}

# ============================================================================
# yanbaor2 group: 29 files that are English content among Chinese reports
# - 12 hash-named files (international consulting reports: Deloitte, KPMG, McKinsey, EY)
# - 12 EY (Ernst & Young) named files (all English except ey-*-zh which is Chinese)
# - 5 yanbaoPPT files with English content
# ============================================================================
YANBAOR2_EN_FILES: set[str] = {
    # Hash-named English consulting/industry reports (12 files)
    "yanbaor2_001c0e4e970dcae8f91980266459d41aa0fd9c54245320b5d41d9651c4fc575d.pdf_26.jpg",
    "yanbaor2_001c0e4e970dcae8f91980266459d41aa0fd9c54245320b5d41d9651c4fc575d.pdf_46.jpg",
    "yanbaor2_0071908e787f90267682e19ef093bb18dda6e1c1614534c445ddd62c425b3a94.pdf_36.jpg",
    "yanbaor2_0071908e787f90267682e19ef093bb18dda6e1c1614534c445ddd62c425b3a94.pdf_44.jpg",
    "yanbaor2_0a49fd5fc362650bf30a0a9391a2d2f091e751ba3d51da18e630e23856905c63.pdf_8.jpg",
    "yanbaor2_3e1be78252e2fdfe1adf12bba38ec2a7b30699e152d61269aa6e5827f5adcc35.pdf_13.jpg",
    "yanbaor2_930d8c81854d7450cd35af7b050fed88e4e461b4f0ac0dab07e3232a4e703a06.pdf_14.jpg",
    "yanbaor2_9674ff37a7d4ea8fb80538bf2d8193dd0dca8f838bdd51f4862769746e996126.pdf_26.jpg",
    "yanbaor2_a6a80b48db3438977793c75185e980ee4aff22f79083427cb03ea4134f7b241f.pdf_67.jpg",
    "yanbaor2_b997efc056ce194205f46dbd1c669eb32da025c4a3055c88d5f19ce434040b7b.pdf_46.jpg",
    "yanbaor2_d599e33e54376640020110ac1733ccdde8c6323d5d5f0c3ca8cb395dc6e46cf5.pdf_7.jpg",
    "yanbaor2_e2f6b15971d68a7f081216b0c0d8538cab413124fc8911f4db4fbb3d17f167c4.pdf_14.jpg",
    # EY (Ernst & Young) English reports (12 files)
    # NOTE: ey-report-strategy-for-a-tech-driven-gba-zh is CHINESE (correctly zh/cjk)
    "yanbaor2_ey-better-pension-outcomes-reimagined-20180926.pdf_1.jpg",
    "yanbaor2_ey-beyond-traditional-corporate-governance.pdf_1.jpg",
    "yanbaor2_ey-digital-state-tax-article.pdf_0.jpg",
    "yanbaor2_ey-drug-device-combination-products-whitepaper.pdf_6.jpg",
    "yanbaor2_ey-financial-sustainability-whitepaper.pdf_17.jpg",
    "yanbaor2_ey-global-fintech-adoption-index.pdf_30.jpg",
    "yanbaor2_ey-how-can-all-benefit-from-green-leadership-by-the-few.pdf_21.jpg",
    "yanbaor2_ey-how-covid-19-has-triggered-a-sprint-toward-smarter-health-care.pdf_5.jpg",
    "yanbaor2_ey-icl-barking-and-dagenham-case-study.pdf_10.jpg",
    "yanbaor2_ey-icl-harnessing-the-power-of-data.pdf_13.jpg",
    "yanbaor2_ey-is-your-next-step-about-changing-direction-or-directing-change.pdf_4.jpg",
    "yanbaor2_ey-political-guidelines-next-commission.pdf_14.jpg",
    # yanbaoPPT English slides (5 files)
    "yanbaor2_yanbaoPPT_1295.jpg",  # English consulting report "Section I: What do they want?"
    "yanbaor2_yanbaoPPT_1517.jpg",  # McKinsey Health Institute "Addressing employee burnout"
    "yanbaor2_yanbaoPPT_469.jpg",  # English analytics maturity report
    "yanbaor2_yanbaoPPT_5627.jpg",  # "5 trends reshaping China's consumer market" (English)
    "yanbaor2_yanbaoPPT_5946.jpg",  # English business/trading report
}

# ============================================================================
# yanbaopptmerge group: 17 files that are English content among Chinese PPTs
# - 8 hash-named files (English textbook pages: physics, math, US gov, economics)
# - 5 named files (PattPatel, SE05/14/17/20 Software Engineering)
# - 4 English teaching PPT slides
# ============================================================================
YANBAOPPTMERGE_EN_FILES: set[str] = {
    # Hash-named English textbook pages (8 files)
    "yanbaopptmerge_1c5f17c3dfa38c45b86802b9d014da18.pdf_1372.jpg",  # Physics: Wave Nature of Matter
    "yanbaopptmerge_2b8553b00244437fa3e502aa2d3d319ed74459a1e264a4fdd9ecc14ce46609d5.pdf_2.jpg",  # Education
    "yanbaopptmerge_9081a70ff98b3e7d640660a9412c447d.pdf_1287.jpg",  # CS: Symbol Table
    "yanbaopptmerge_abef2a4978ae4d13e931f0392502bd40.pdf_1130.jpg",  # Math: Exercises
    "yanbaopptmerge_abef2a4978ae4d13e931f0392502bd40.pdf_1287.jpg",  # Math: Exercises
    "yanbaopptmerge_ba38a4c7e8f15937f3ae537cf2de2cd5.pdf_104.jpg",  # US Gov: Interest Groups
    "yanbaopptmerge_d346b889f1d85c61950a71d4b0ac2752.pdf_89.jpg",  # Economics: equilibrium
    "yanbaopptmerge_d4fc7cba428625974e93183edfccea73.pdf_89.jpg",  # Statistics: std deviation
    # Named English CS/SE textbook chapters (5 files)
    "yanbaopptmerge_PattPatelCh12.pdf_27.jpg",  # Computer Architecture: Human Factors
    "yanbaopptmerge_SE05.pdf_7.jpg",  # Software Engineering Ch5: Components
    "yanbaopptmerge_SE14.pdf_1.jpg",  # Software Engineering Ch14: Interface Design
    "yanbaopptmerge_SE17.pdf_10.jpg",  # Software Engineering Ch17: Defect Amplification
    "yanbaopptmerge_SE20.pdf_2.jpg",  # Software Engineering Ch20
    # English teaching PPT slides (4 files)
    "yanbaopptmerge_m3_Unit_1_Where_did_you_go.pdf_5.jpg",  # English: Where did Amy go?
    "yanbaopptmerge_yanbaoPPT_1090.jpg",  # English: Listen and say (50 teachers)
    "yanbaopptmerge_yanbaoPPT_4565.jpg",  # English: Retell 1a dialogue
    "yanbaopptmerge_yanbaoPPT_485.jpg",  # English: Look at the giraffe
}

# Combine all English correction sets
ALL_EN_CORRECTIONS: set[str] = (
    JIAOCAI_EN_FILES
    | JIAOCAINEEDROP_EN_FILES
    | YANBAOR2_EN_FILES
    | YANBAOPPTMERGE_EN_FILES
)


def main() -> int:
    """Fix language/script misclassifications in omnidocbench metadata."""
    parser = argparse.ArgumentParser(
        description="Fix omnidocbench language misclassifications from visual review",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying metadata",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=METADATA_PATH,
        help="Path to omnidocbench metadata JSON",
    )
    args = parser.parse_args()

    if not args.metadata_path.exists():
        log.error("Metadata file not found: %s", args.metadata_path)
        return 1

    log.info("Loading metadata from %s", args.metadata_path)
    with open(args.metadata_path) as fh:
        metadata = json.load(fh)

    samples = metadata.get("samples", [])
    log.info("Total samples: %d", len(samples))
    log.info(
        "Corrections to apply: %d (jiaocai=%d, jiaocaineedrop=%d, yanbaor2=%d, yanbaopptmerge=%d)",
        len(ALL_EN_CORRECTIONS),
        len(JIAOCAI_EN_FILES),
        len(JIAOCAINEEDROP_EN_FILES),
        len(YANBAOR2_EN_FILES),
        len(YANBAOPPTMERGE_EN_FILES),
    )

    # Build alt-name lookup for files that might have variant names
    alt_lookup = dict(JIAOCAINEEDROP_EN_ALTS)

    matched: set[str] = set()
    updated = 0

    for sample in samples:
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            continue
        data = versions[-1].get("data", {})

        filename = sample.get("source", {}).get("original_filename", "")
        if not filename:
            continue

        # Check if this file needs correction
        needs_fix = False
        if filename in ALL_EN_CORRECTIONS:
            needs_fix = True
            matched.add(filename)
        elif filename in alt_lookup and alt_lookup[filename] in ALL_EN_CORRECTIONS:
            needs_fix = True
            matched.add(alt_lookup[filename])

        if not needs_fix:
            continue

        old_lang = data.get("iso639_language", "")
        old_script = data.get("script_family", "")

        if old_lang == "en" and old_script == "latin":
            log.info("Already correct: %s", filename[:80])
            matched.add(filename)
            continue

        log.info(
            "FIX: %s  %s/%s -> en/latin",
            filename[:80],
            old_lang or "empty",
            old_script or "empty",
        )

        if not args.dry_run:
            data["iso639_language"] = "en"
            data["script_family"] = "latin"
            data["language_confidence"] = 0.95
            data["language_detection_method"] = "visual_review_100pct_correction"
            updated += 1

    # Report unmatched files
    unmatched = ALL_EN_CORRECTIONS - matched
    if unmatched:
        log.warning("=== %d files NOT FOUND in metadata ===", len(unmatched))
        for fn in sorted(unmatched):
            log.warning("  NOT FOUND: %s", fn)

    log.info("=== Summary ===")
    log.info("Files matched: %d / %d", len(matched), len(ALL_EN_CORRECTIONS))
    log.info("Files not found: %d", len(unmatched))

    if args.dry_run:
        log.info("Dry run - no changes written")
    else:
        with open(args.metadata_path, "w") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Updated %d samples in %s", updated, args.metadata_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
