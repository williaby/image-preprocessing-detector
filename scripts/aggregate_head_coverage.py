#!/usr/bin/env python3
"""Aggregates Section 13 head coverage data from all 69 dataset source files."""

import re
import sys
from pathlib import Path

SOURCE_DIR = Path("/home/byron/dev/image_detection/docs/datasets/source")

DATASETS = [
    "anyphotodoc6300",
    "arabic-docs",
    "bhutan-afs",
    "casia-hwdb2",
    "casia-hwdb2-line",
    "cc-ocr",
    "cocotext",
    "cvsi",
    "dibco",
    "diqa-5000",
    "doc3d",
    "docalign12k",
    "doclaynet",
    "docreal",
    "docsynth",
    "document-haystack",
    "drccbi",
    "dzongkha-digits",
    "financebench",
    "fintabnet",
    "funsd",
    "funsd-plus",
    "hasy",
    "hiertext",
    "hindi-synth",
    "iam",
    "iiit-hw-hindi",
    "im2latex",
    "indicdlp",
    "invoices-kg",
    "jssoda",
    "khatt",
    "kuzushiji",
    "markushgrapher",
    "mathverse",
    "mdiw13",
    "mle2e",
    "midv2020",
    "midv500",
    "mlt19",
    "muharaf",
    "multimodal-textbook",
    "multilingual-scripts",
    "nepali-handwritten",
    "nist-sd19",
    "nist-sd2",
    "nist-sd6",
    "ocr-quality",
    "ohr-bench",
    "omnidocbench",
    "openlid-v2",
    "pubtabnet",
    "pucit-ohul",
    "q-doc",
    "realdae",
    "rvl-cdip",
    "sd7k",
    "signatr6k",
    "siw13",
    "smartdoc-qa",
    "sroie",
    "staindoc",
    "tablebank",
    "tibhcr",
    "tobacco800",
    "warpdoc",
    "wili-2018",
    "wsrd",
    "yarmouk",
]

HEAD_IDS = [
    "MNV4-H1",
    "MNV4-H2",
    "MNV4-H3",
    "SIG-G1-1",
    "SIG-G1-2",
    "SIG-G1-3",
    "SIG-G1-4",
    "SIG-G1-5",
    "SIG-G1-6",
    "SIG-G2-1",
    "SIG-G3-1",
    "SIG-G3-2",
    "SIG-G4-1",
    "SIG-G4-2",
    "SIG-G4-3",
    "SIG-G4-4",
    "SIG-G4-5",
    "SIG-G5-1",
    "SIG-G5-2",
    "SIG-G5-3",
    "SIG-G5-4",
    "SIG-G5-5",
]


def parse_contribution(text: str) -> str:
    if "✅" in text:
        return "✅"
    if "🟡" in text:
        return "🟡"
    if "➖" in text:
        return "➖"
    if "❌" in text:
        return "❌"
    return "❓"


def parse_section13(filepath: Path) -> tuple[dict, str]:
    content = filepath.read_text(encoding="utf-8")
    contributions = dict.fromkeys(HEAD_IDS, "❓")
    corpus_role = ""

    s13_match = re.search(r"## 13\. Training Head Coverage", content)
    if not s13_match:
        print(f"  WARNING: No Section 13 found in {filepath.name}", file=sys.stderr)
        return contributions, corpus_role

    s13_content = content[s13_match.start() :]

    # Parse table rows - each head has a row like:
    # | MNV4-H1 | orientation_cls | ✅ | ...
    for head_id in HEAD_IDS:
        # Match the head ID as first column, then capture third column (Contribution)
        pattern = (
            r"\|\s*" + re.escape(head_id) + r"\s*\|"
            r"[^|]+\|"  # head name column
            r"\s*([^\|]+?)\s*\|"  # contribution column
        )
        match = re.search(pattern, s13_content)
        if match:
            contributions[head_id] = parse_contribution(match.group(1))
        else:
            print(
                f"  WARNING: Head {head_id} not found in {filepath.name}",
                file=sys.stderr,
            )

    # Parse 13.3 corpus role
    s133_match = re.search(
        r"### 13\.3 Corpus Role & Constraints\s*\n+(.*?)(?=\n---|\n##|\Z)",
        s13_content,
        re.DOTALL,
    )
    if s133_match:
        corpus_role = s133_match.group(1).strip()

    return contributions, corpus_role


def main():
    all_data = {}

    print("Reading source files...", file=sys.stderr)
    for dataset in DATASETS:
        filepath = SOURCE_DIR / f"{dataset}.md"
        if not filepath.exists():
            print(f"  MISSING: {filepath}", file=sys.stderr)
            all_data[dataset] = (
                dict.fromkeys(HEAD_IDS, "❓"),
                f"File not found: {filepath.name}",
            )
            continue
        contribs, role = parse_section13(filepath)
        all_data[dataset] = (contribs, role)
        print(f"  OK: {dataset}", file=sys.stderr)

    # Compute coverage statistics per head
    stats = {}
    for head_id in HEAD_IDS:
        primary = [d for d in DATASETS if all_data[d][0][head_id] == "✅"]
        secondary = [d for d in DATASETS if all_data[d][0][head_id] == "🟡"]
        negatives = [d for d in DATASETS if all_data[d][0][head_id] == "➖"]
        stats[head_id] = {
            "primary": primary,
            "secondary": secondary,
            "negatives": negatives,
        }

    # Generate output
    lines = []

    # Grid A: MNV4 heads
    lines.append("### Grid A: MobileNetV4 Heads (3 heads)")
    lines.append("")
    lines.append(
        "| Dataset | MNV4-H1 orientation_cls | MNV4-H2 skew_reg | MNV4-H3 resolution_quality_reg |"
    )
    lines.append(
        "| ------- | ----------------------- | ---------------- | ------------------------------- |"
    )
    for ds in DATASETS:
        c = all_data[ds][0]
        lines.append(f"| {ds} | {c['MNV4-H1']} | {c['MNV4-H2']} | {c['MNV4-H3']} |")

    lines.append("")
    lines.append("### Grid B: SigLIP 2 Group 1 — IQA (6 heads)")
    lines.append("")
    lines.append(
        "| Dataset | G1-1 blur | G1-2 noise | G1-3 contrast | G1-4 skew_score | G1-5 compression | G1-6 overall_quality |"
    )
    lines.append(
        "| ------- | --------- | ---------- | ------------- | --------------- | ---------------- | -------------------- |"
    )
    for ds in DATASETS:
        c = all_data[ds][0]
        lines.append(
            f"| {ds} | {c['SIG-G1-1']} | {c['SIG-G1-2']} | {c['SIG-G1-3']} | {c['SIG-G1-4']} | {c['SIG-G1-5']} | {c['SIG-G1-6']} |"
        )

    lines.append("")
    lines.append("### Grid C: SigLIP 2 Group 2 — Script (1 head)")
    lines.append("")
    lines.append("| Dataset | G2-1 script_cls |")
    lines.append("| ------- | --------------- |")
    for ds in DATASETS:
        c = all_data[ds][0]
        lines.append(f"| {ds} | {c['SIG-G2-1']} |")

    lines.append("")
    lines.append("### Grid D: SigLIP 2 Groups 3–5 (12 heads)")
    lines.append("")
    lines.append(
        "| Dataset | G3-1 orient_post | G3-2 skew_post | G4-1 hw_presence | G4-2 hw_legibility | G4-3 hw_content | G4-4 presence_reg | G4-5 legibility_reg | G5-1 capture | G5-2 shadow | G5-3 warping | G5-4 code | G5-5 res_qual |"
    )
    lines.append(
        "| ------- | ---------------- | -------------- | ---------------- | ------------------ | --------------- | ----------------- | ------------------- | ------------ | ----------- | ------------ | --------- | ------------- |"
    )
    for ds in DATASETS:
        c = all_data[ds][0]
        lines.append(
            f"| {ds} | {c['SIG-G3-1']} | {c['SIG-G3-2']} | {c['SIG-G4-1']} | {c['SIG-G4-2']} | "
            f"{c['SIG-G4-3']} | {c['SIG-G4-4']} | {c['SIG-G4-5']} | {c['SIG-G5-1']} | "
            f"{c['SIG-G5-2']} | {c['SIG-G5-3']} | {c['SIG-G5-4']} | {c['SIG-G5-5']} |"
        )

    print("\n--- GRIDS ---")
    print("\n".join(lines))

    print("\n--- SECTION 3 ---")
    for ds in DATASETS:
        role = all_data[ds][1]
        print(f"\n### {ds}\n")
        print(role if role else "_No corpus role summary found._")

    print("\n--- COVERAGE STATS ---")
    head_names = {
        "MNV4-H1": "orientation_cls (MNV4)",
        "MNV4-H2": "skew_reg (MNV4)",
        "MNV4-H3": "resolution_quality_reg (MNV4)",
        "SIG-G1-1": "blur_score",
        "SIG-G1-2": "noise_score",
        "SIG-G1-3": "contrast_score",
        "SIG-G1-4": "skew_score",
        "SIG-G1-5": "compression_score",
        "SIG-G1-6": "overall_quality",
        "SIG-G2-1": "script_cls",
        "SIG-G3-1": "orientation_cls (post)",
        "SIG-G3-2": "skew_reg (post)",
        "SIG-G4-1": "handwriting_presence_cls",
        "SIG-G4-2": "handwriting_legibility_cls",
        "SIG-G4-3": "handwriting_content_type_cls",
        "SIG-G4-4": "presence_reg",
        "SIG-G4-5": "legibility_reg",
        "SIG-G5-1": "capture_method_cls",
        "SIG-G5-2": "shadow_reg",
        "SIG-G5-3": "warping_reg",
        "SIG-G5-4": "code_cls",
        "SIG-G5-5": "resolution_quality_reg (SigLIP)",
    }
    for head_id in HEAD_IDS:
        s = stats[head_id]
        print(f"\n**{head_id} — {head_names[head_id]}**")
        print(
            f"- Primary contributors ({len(s['primary'])}): {', '.join(s['primary']) or 'none'}"
        )
        print(
            f"- Secondary contributors ({len(s['secondary'])}): {', '.join(s['secondary']) or 'none'}"
        )
        print(
            f"- Negatives only ({len(s['negatives'])}): {', '.join(s['negatives']) or 'none'}"
        )


if __name__ == "__main__":
    main()
