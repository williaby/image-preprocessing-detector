"""Quarantine unsuitable images from the john11-manuscripts dataset.

Removes junk files (web thumbnails, non-manuscript content like architecture/
ceramics/tiles/fonts/monuments, wrong biblical books, and duplicate registry
entries) from disk, registry, extended sidecar, and L2 metadata.

Usage:
    python scripts/quarantine_john11_junk.py --dry-run   # Preview changes
    python scripts/quarantine_john11_junk.py              # Execute cleanup
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DATA = Path("/home/byron/dev/image_detection/data/john11-manuscripts")
REGISTRY_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/john11_manuscripts_registry.jsonl"
)
EXTENDED_SIDECAR_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/john11_manuscripts_extended.jsonl"
)
L2_DIR = Path("/mnt/e/image_detection/metadata_registry/json/john11-manuscripts")
QUARANTINE_DIR = BASE_DATA / "_quarantined"

# ---------------------------------------------------------------------------
# Files to remove from disk + registry + L2 metadata
# ---------------------------------------------------------------------------

JUNK_FILES: list[str] = [
    # ── Small images (under 200px min dimension) ──────────────────────────
    "wikimedia/copt/Coptic_small.jpg",  # 127x60
    "wikimedia/copt/Coptictesttext.png",  # 300x111
    "wikimedia/copt/Paopi.png",  # 115x35
    "wikimedia/cyrs/Ostromirovo_pp-226.jpg",  # 198x864
    "wikimedia/goth/Detail_of_Codex_Argenteus.jpg",  # 187x115
    "wikimedia/grek/EB1911_Palaeography_-_The_Bible.jpg",  # 753x123
    "wikimedia/grek/Papyrus_75_-_Gospel_of_John_-_title.jpg",  # 155x50
    "wikimedia/latn/CarolingianMinuscule.jpg",  # 310x148
    "wikimedia/latn/KarolingischeMinuskel.jpg",  # 1281x118
    "wikimedia/latn/Tacitus-Varusschlacht.jpg",  # 500x124
    # ── Architecture (mosques, churches, madrasahs, mausoleums) ───────────
    "wikimedia/arab/Selimiye_Mosque,_Dome.jpg",
    "wikimedia/arab/Selimiye_Mosque_Mosque_0170.jpg",
    "wikimedia/arab/Ulugbek_madrasah_-_Inside_-_courtyard_9_student_cell_calligraphy_above_door.JPG",
    "wikimedia/arab/Resurrection_Lutheran_Church,_Princeton_Park,_Chicago_window.jpg",
    "wikimedia/arab/Hazrat_Imam_15.jpg",
    "wikimedia/arab/Samarcanda,_Registán_09.jpg",
    "wikimedia/arab/Samarcanda,_Registán_13.jpg",
    "wikimedia/arab/Samarkand_Shah-i_Zinda_Tuman_Aqa_complex_cropped2.jpg",
    "wikimedia/arab/Mausolée_de_Touman_Aka_(Shah-i-Zinda,_Samarcande)_(6009410911).jpg",
    "wikimedia/arab/Elément_de_décor_du_mausolée_dAlim_Nesefi_(Shah-i-Zinda,_Samarcande)_(6009389583).jpg",
    "wikimedia/arab/Bujará,_Ark_11.jpg",
    "wikimedia/arab/BüyükcamiiIMG_0485.jpg",
    "wikimedia/arab/Akseki_Han_çinileri_2.jpg",
    "wikimedia/arab/Kermán,_mezquita_(2000)_11.jpg",
    "wikimedia/arab/Kermán,_varios_(2000)_04.jpg",
    "wikimedia/arab/Slot_at_the_Zaouia_Moulay_Idriss_II_1.jpg",
    "wikimedia/arab/East_Jerusalem_Octagram_(6809612420).jpg",
    "wikimedia/arab/Octagram_(4942304224).jpg",
    "wikimedia/arab/Octagram_Double_Square_Wall_(4945016806).jpg",
    "wikimedia/arab/Octagram_in_Jerusalem_(6806683019).jpg",
    "wikimedia/copt/Coptic_and_Arabic_inscriptions_in_an_Old_Cairo_church.jpg",
    # ── Ceramics / tiles ──────────────────────────────────────────────────
    "wikimedia/arab/Azulejo_con_decoración_vidriada_(Kashan,_Irán)._Siglo_XIII_-_MARQ_01.jpg",
    "wikimedia/arab/Kashan_lustre-decorated_star_tile,_Central_Persia,_probably_14th_Century,_Christie's_sale_2835_Dec._2009.jpg",
    "wikimedia/arab/Konya_Karatay_Ceramics_Museum_Kubad_Abad_Palace_find_2405.jpg",
    "wikimedia/arab/Star_Tile_with_Griffins_and_Birds_amid_Arabesque,_late_12th_-_early_13th_century,_Saljuq-Atabeg_period,_Kashan,_Iran_-_Sackler_Museum_-_DSC02484.JPG",
    "wikimedia/arab/Star_Tile_with_Seated_Figure_Surrounded_by_Spiraling_Vine,_late_12th_-_early_13th_century,_Saljuq-Atabeg_period,_Kashan,_Iran_-_Sackler_Museum_-_DSC02485.JPG",
    "wikimedia/arab/Star-shaped_tile_with_2_birds,_under-glazed_ceramic._Part_of_4_tiles_surrounding_a_cross._Anatolian_Seljuk_period,_1st_half_of_the_13th_century_CE._From_the_excavations_at_carried_Kubadabad_Palace,_Ko.jpg",
    "wikimedia/arab/Alicatado,_Colección_Carranza_(Sevilla).jpg",
    "wikimedia/arab/Atauriques.jpg",
    "wikimedia/arab/Persian_Fritware_Seljuq_Era_13th_Century.JPG",
    "wikimedia/arab/Khalili_Collection_Islamic_Art_pot_1677.1.jpg",
    # ── Font specimens / UI screenshots ───────────────────────────────────
    "wikimedia/geor/Inkscape_Fonts_-_Segoe_UI.png",
    "wikimedia/geor/Metro_design_language.png",
    "wikimedia/geor/My_articles_segoe_ui_light.png",  # also <200px
    "wikimedia/geor/My_tools_segoe_ui_light.png",  # also <200px
    "wikimedia/arab/Nastaliq_Navees_font.png",
    "wikimedia/arab/Helvetica_arabic_mostra.png",
    # ── Monuments / stucco panels ─────────────────────────────────────────
    "wikimedia/arab/'AA_By_@ibneazhar'_Monument_F9_FatimaJinnah_Park-Islamabad-Pakistan_(22).JPG",
    "wikimedia/arab/Detail_from_monumental_stucco_panel,_Iran,_12th_cent.;Museum_of_Islamic_Art,_Doha,_Qata_(3).jpg",
    "wikimedia/arab/Monumental_stucco_panel,_Iran,_12th_cent.;Museum_of_Islamic_Art,_Doha,_Qatar.jpg",
    # ── Wrong content (non-documents) ─────────────────────────────────────
    "wikimedia/arab/Appropriation_(46235873561).jpg",
    "wikimedia/arab/Detail_of_a_Salor_Turkmen_ceremonial_camel_trapping.jpg",
    "wikimedia/arab/Djerba_Explore-The_artifact-sky_walker.jpg",
    "wikimedia/arab/SOLE_LUNA_DOC_FILM_FESTIVAL_2017.jpg",
    'wikimedia/arab/Shopping_center_"Sezam"_at_Yamalskaya_Street_(2).jpg',
    # ── Wrong biblical books (not John 1:1) ───────────────────────────────
    "wikimedia/grek/Codex_Alexandrinus_1_Tim_3,16.jpg",  # 1 Timothy, also <200px
    "wikimedia/grek/·_Codex_Sinaiticus_·_Primera_Epístola_a_Timoteo_2.12_a_4.16.png",
    # ── Hildebrandslied (Old High German epic, not biblical manuscript) ───
    "wikimedia/latn/Hildebrandslied1.jpg",
    "wikimedia/latn/Hildebrandslied2._wynn_rune.jpg",  # also <200px
    "wikimedia/latn/Hildebrandslied2.jpg",
    "wikimedia/latn/Hildebrandslied_Facsimile_1830.jpg",
]

# Duplicate registry entries: same source_path appears twice with different
# SHA256 (Met Museum re-downloads). Keep first occurrence, remove second.
DUPLICATE_REGISTRY_ENTRIES: list[str] = [
    "met/met_449536_001.JPG",
    "met/met_449536_005.jpg",
]

ALL_QUARANTINE_PATHS = set(JUNK_FILES)


def quarantine_files(dry_run: bool) -> dict[str, int]:
    """Move junk files to quarantine directory and clean registry/L2/sidecar."""
    stats = {
        "files_quarantined": 0,
        "registry_entries_removed": 0,
        "sidecar_entries_removed": 0,
        "l2_files_removed": 0,
        "duplicate_entries_removed": 0,
        "errors": 0,
    }

    # --- Step 1: Move junk files to quarantine (preserving directory structure) ---
    print("\n=== Step 1: Quarantine junk files from disk ===")
    for rel_path in JUNK_FILES:
        src = BASE_DATA / rel_path
        dst = QUARANTINE_DIR / rel_path
        if src.exists():
            if dry_run:
                print(f"  [DRY RUN] Would move: {rel_path}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  Moved: {rel_path}")
            stats["files_quarantined"] += 1
        else:
            print(f"  SKIP (not on disk): {rel_path}")

    # --- Step 2: Clean registry ---
    print("\n=== Step 2: Remove entries from registry ===")
    if not REGISTRY_PATH.exists():
        print(f"  ERROR: Registry not found at {REGISTRY_PATH}")
        stats["errors"] += 1
        return stats

    kept_lines: list[str] = []
    removed_count = 0
    removed_sample_ids: set[str] = set()

    # Track seen source_paths to detect duplicates
    seen_source_paths: set[str] = set()
    dupe_set = set(DUPLICATE_REGISTRY_ENTRIES)

    with open(REGISTRY_PATH) as f:
        for line in f:
            rec = json.loads(line)
            source_path = rec.get("source_path", "")

            # Remove junk entries
            if source_path in ALL_QUARANTINE_PATHS:
                removed_count += 1
                removed_sample_ids.add(rec.get("sample_id", ""))
                if dry_run:
                    print(f"  [DRY RUN] Would remove registry entry: {source_path}")
                else:
                    print(f"  Removed: {source_path}")
                continue

            # Remove duplicate entries (keep first, remove second)
            if source_path in dupe_set:
                if source_path in seen_source_paths:
                    stats["duplicate_entries_removed"] += 1
                    removed_sample_ids.add(rec.get("sample_id", ""))
                    if dry_run:
                        print(
                            f"  [DRY RUN] Would remove duplicate: {source_path} "
                            f"(sample_id={rec.get('sample_id', '')})"
                        )
                    else:
                        print(
                            f"  Removed duplicate: {source_path} "
                            f"(sample_id={rec.get('sample_id', '')})"
                        )
                    continue

            seen_source_paths.add(source_path)
            kept_lines.append(line)

    if not dry_run and (removed_count > 0 or stats["duplicate_entries_removed"] > 0):
        # Backup original registry (copyfile only — WSL NTFS lacks chmod/utime)
        backup = REGISTRY_PATH.with_suffix(".jsonl.bak")
        shutil.copyfile(REGISTRY_PATH, backup)
        print(f"  Backed up registry to: {backup.name}")

        with open(REGISTRY_PATH, "w") as f:
            f.writelines(kept_lines)

    stats["registry_entries_removed"] = removed_count

    # --- Step 3: Clean extended sidecar ---
    print("\n=== Step 3: Remove entries from extended sidecar ===")
    if not EXTENDED_SIDECAR_PATH.exists():
        print(f"  WARNING: Extended sidecar not found at {EXTENDED_SIDECAR_PATH}")
    else:
        sidecar_kept: list[str] = []
        sidecar_removed = 0

        with open(EXTENDED_SIDECAR_PATH) as f:
            for line in f:
                rec = json.loads(line)
                sample_id = rec.get("sample_id", "")
                if sample_id in removed_sample_ids:
                    sidecar_removed += 1
                    if dry_run:
                        print(
                            f"  [DRY RUN] Would remove sidecar entry: "
                            f"{rec.get('source_path', sample_id)}"
                        )
                    else:
                        print(
                            f"  Removed: {rec.get('source_path', sample_id)}"
                        )
                else:
                    sidecar_kept.append(line)

        if not dry_run and sidecar_removed > 0:
            backup = EXTENDED_SIDECAR_PATH.with_suffix(".jsonl.bak")
            shutil.copyfile(EXTENDED_SIDECAR_PATH, backup)
            print(f"  Backed up sidecar to: {backup.name}")

            with open(EXTENDED_SIDECAR_PATH, "w") as f:
                f.writelines(sidecar_kept)

        stats["sidecar_entries_removed"] = sidecar_removed

    # --- Step 4: Clean L2 metadata ---
    print("\n=== Step 4: Remove L2 metadata files ===")
    if not L2_DIR.exists():
        print(f"  WARNING: L2 directory not found at {L2_DIR}")
    else:
        for sample_id in removed_sample_ids:
            l2_file = L2_DIR / f"{sample_id}.json"
            if l2_file.exists():
                if dry_run:
                    print(f"  [DRY RUN] Would remove L2: {l2_file.name}")
                else:
                    l2_file.unlink()
                    print(f"  Removed L2: {l2_file.name}")
                stats["l2_files_removed"] += 1

    # --- Step 5: Write quarantine manifest ---
    print("\n=== Step 5: Write quarantine manifest ===")
    manifest = {
        "quarantine_date": datetime.now(timezone.utc).isoformat(),
        "reason": "john11-manuscripts dataset cleanup — unsuitable images",
        "dry_run": dry_run,
        "junk_files": JUNK_FILES,
        "duplicate_registry_entries": DUPLICATE_REGISTRY_ENTRIES,
        "stats": stats,
        "categories": {
            "small_images_under_200px": [
                p
                for p in JUNK_FILES
                if p
                in {
                    "wikimedia/copt/Coptic_small.jpg",
                    "wikimedia/copt/Coptictesttext.png",
                    "wikimedia/copt/Paopi.png",
                    "wikimedia/cyrs/Ostromirovo_pp-226.jpg",
                    "wikimedia/goth/Detail_of_Codex_Argenteus.jpg",
                    "wikimedia/grek/EB1911_Palaeography_-_The_Bible.jpg",
                    "wikimedia/grek/Papyrus_75_-_Gospel_of_John_-_title.jpg",
                    "wikimedia/latn/CarolingianMinuscule.jpg",
                    "wikimedia/latn/KarolingischeMinuskel.jpg",
                    "wikimedia/latn/Tacitus-Varusschlacht.jpg",
                    "wikimedia/geor/My_articles_segoe_ui_light.png",
                    "wikimedia/geor/My_tools_segoe_ui_light.png",
                    "wikimedia/grek/Codex_Alexandrinus_1_Tim_3,16.jpg",
                    "wikimedia/latn/Hildebrandslied2._wynn_rune.jpg",
                }
            ],
            "architecture": [
                p
                for p in JUNK_FILES
                if any(
                    kw in p
                    for kw in [
                        "Mosque",
                        "madrasah",
                        "Church",
                        "church",
                        "Mausolée",
                        "Registán",
                        "Zinda",
                        "Bujará",
                        "Büyükcami",
                        "Akseki",
                        "Kermán",
                        "Zaouia",
                        "Octagram",
                        "Imam",
                    ]
                )
            ],
            "ceramics_tiles": [
                p
                for p in JUNK_FILES
                if any(
                    kw in p
                    for kw in [
                        "Tile",
                        "tile",
                        "Kashan",
                        "Ceramics",
                        "Azulejo",
                        "Alicatado",
                        "Atauriques",
                        "Fritware",
                        "Khalili",
                    ]
                )
            ],
            "font_ui_screenshots": [
                p
                for p in JUNK_FILES
                if any(
                    kw in p
                    for kw in [
                        "Segoe",
                        "segoe",
                        "Inkscape",
                        "Metro_design",
                        "Nastaliq_Navees_font",
                        "Helvetica",
                    ]
                )
            ],
            "monuments_stucco": [
                p
                for p in JUNK_FILES
                if any(kw in p for kw in ["Monument", "monument", "stucco"])
            ],
            "wrong_content": [
                p
                for p in JUNK_FILES
                if any(
                    kw in p
                    for kw in [
                        "Appropriation",
                        "Salor_Turkmen",
                        "Djerba",
                        "SOLE_LUNA",
                        "Shopping_center",
                    ]
                )
            ],
            "wrong_biblical_books": [
                p
                for p in JUNK_FILES
                if any(kw in p for kw in ["1_Tim", "Timoteo"])
            ],
            "hildebrandslied": [
                p for p in JUNK_FILES if "Hildebrandslied" in p
            ],
            "met_duplicate_registry": DUPLICATE_REGISTRY_ENTRIES,
        },
    }

    manifest_path = QUARANTINE_DIR / "quarantine_manifest.json"
    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"  Written: {manifest_path}")
    else:
        print(f"  [DRY RUN] Would write manifest to: {manifest_path}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quarantine unsuitable john11-manuscripts dataset images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    args = parser.parse_args()

    print(
        f"john11-manuscripts Dataset Quarantine "
        f"{'(DRY RUN)' if args.dry_run else '(LIVE)'}"
    )
    print(f"Base data: {BASE_DATA}")
    print(f"Registry: {REGISTRY_PATH}")
    print(f"Extended sidecar: {EXTENDED_SIDECAR_PATH}")
    print(f"L2 metadata: {L2_DIR}")
    print(f"Quarantine dir: {QUARANTINE_DIR}")

    stats = quarantine_files(dry_run=args.dry_run)

    print("\n=== Summary ===")
    print(f"  Files quarantined:          {stats['files_quarantined']}")
    print(f"  Registry entries removed:   {stats['registry_entries_removed']}")
    print(f"  Sidecar entries removed:    {stats['sidecar_entries_removed']}")
    print(f"  L2 metadata removed:        {stats['l2_files_removed']}")
    print(f"  Duplicate entries removed:  {stats['duplicate_entries_removed']}")
    print(f"  Errors:                     {stats['errors']}")

    if args.dry_run:
        print(
            "\n  ** DRY RUN — no changes made. "
            "Run without --dry-run to execute. **"
        )

    sys.exit(1 if stats["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
