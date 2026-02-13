#!/usr/bin/env python3
"""
Split DATASET_CATALOG.md into individual dataset files.

This script extracts each dataset section (#### {Dataset Name}) from the
DATASET_CATALOG.md file and creates individual markdown files in
docs/datasets/source/{canonical-name}.md
"""

import re
from pathlib import Path

# Canonical name mapping from DATASET_NAMING_STANDARD.md
CANONICAL_NAMES = {
    "arabic-docs": ["arabic_docs_ocr", "arabic_docs", "arabic-ocr"],
    "bhutan-afs": ["bhutan_financial", "bhutan_financial", "bhutan-financial"],
    "cc-ocr": ["cc_ocr", "cc_ocr", "ccocr"],
    "coco-text": ["cocotext", "cocotext", "coco_text", "CocoText"],
    "cvsi": ["cvsi", "cvsi2015", "cvsi-2015"],
    "dibco": ["dibco", "dibco-train"],
    "diqa-5000": ["diqa", "diqa_5000", "diqa5000", "DIQA-5000", "DIQA"],
    "doc3d": ["doc3D-dataset", "doc-3d", "doc_3d", "Doc3D"],
    "doclaynet": ["doclaynet", "doc-laynet", "DocLayNet"],
    "docsynth": ["docsynth300k", "docsynth_300k", "docsynth-300k"],
    "dzongkha-digits": ["dzongkha_digits", "dzongkha-digits", "dzongkha_digits"],
    "financebench": ["financebench", "finance-bench", "FinanceBench"],
    "fintabnet": ["fintabnet", "fin-tab-net", "FinTabNet"],
    "funsd": ["funsd", "FUNSD"],
    "funsd-plus": ["funsd_plus", "funsdplus", "funsd+"],
    "hasy": ["hasyv2", "hasy_v2", "maths_handwriting", "HASYv2"],
    "hindi-synth": ["hindi_ocr_synthetic", "hindi_ocr", "hindi-ocr-synthetic"],
    "hiertext": ["hiertext", "hier-text", "hier_text", "HierText"],
    "iam": ["iam_handwriting", "iam_handwriting", "iam-handwriting", "IAM"],
    "im2latex": ["im2latex", "im2latex-100k", "Im2LaTeX"],
    "invoices-kg": [
        "invoices_kaggle",
        "invoices_kaggle",
        "kaggle-invoices",
        "invoices-kg",
    ],
    "jssoda": ["jssoda", "JSSODa"],
    "mathverse": ["mathverse", "math-verse", "MathVerse"],
    "mdiw13": ["mdiw13", "mdiw-13", "mdiw_13", "MDIW-13"],
    "midv500": ["midv500", "midv-500", "MIDV-500"],
    "midv500-data": ["midv500_data", "midv500_data", "midv-500-data"],
    "mle2e": ["mle2e", "ml-e2e"],
    "mlt19": ["mlt19", "mlt-19", "icdar-mlt19", "MLT19"],
    "mobile-receipts": ["mobile_receipts_voxel51", "mobile_receipts", "receipts-voxel"],
    "multilingual-scripts": ["multilingual_scripts", "multilingual_scripts"],
    "multimodal-textbook": ["multimodal_textbook", "multimodal_textbook"],
    "openlid-v2": ["openlid_v2", "openlid-v2", "openlid2", "OpenLID"],
    "muharaf": ["muharaf", "muharaf_arabic_manuscripts"],
    "nepali-handwritten": ["nepali_handwritten", "nepali_handwritten"],
    "nist-sd2": ["nist-sd2", "nist_sd2", "nist_sd_2", "nist-db2", "NIST SD-2"],
    "nist-sd6": ["nist_sd6", "nist_sd_6", "NIST SD-6"],
    "nist-sd19": ["nist_sd19", "nist_sd_19", "NIST SD-19"],
    "ocr-quality": ["ocr_quality", "ocr_quality"],
    "ohr-bench": ["ohr_bench", "ohr_bench", "ohrbench", "OHR-Bench"],
    "omnidocbench": ["omnidocbench", "omni-doc-bench", "OmniDocBench"],
    "pubtabnet": ["pubtabnet", "pub-tab-net", "PubTabNet"],
    "pucit-ohul": ["pucit-ohul", "pucit_ohul", "pucit-ohul-urdu"],
    "realdae": ["realdae", "real-dae", "RealDAE"],
    "rvl-cdip": ["rvl_cdip", "rvl_cdip", "rvlcdip", "RVL-CDIP"],
    "signatr6k": ["signatr6k", "signatr-6k", "signature-6k"],
    "siw13": ["siw13", "siw-13", "siw_13", "SIW-13"],
    "smartdoc-qa": ["smartdoc-qa", "smartdoc_qa", "SmartDoc-QA"],
    "sroie": ["sroie", "sroie-receipts", "SROIE"],
    "synth-multiscript-250k": ["synthetic_250k", "synth-multiscript", "synthetic_250k"],
    "synthetic-iqa": ["synthetic_iqa", "synthetic_iqa"],
    "tablebank": ["tablebank", "table-bank", "TableBank"],
}


def normalize_dataset_name(name: str) -> str:
    """Convert a dataset name to its canonical form."""
    # Remove markdown formatting
    name = name.strip().replace("**", "")

    # Manual mappings for specific catalog names to canonical names
    manual_mappings = {
        "Arabic Documents OCR Dataset": "arabic-docs",
        "Arabic OCR Dataset": None,  # Exclude - not in canonical 51
        "Bhutan Financial Statements": "bhutan-afs",
        "CC-OCR (CJK Mixed Benchmark)": "cc-ocr",
        "CVSI-2015 (Competition on Video Script Identification)": "cvsi",
        "dibco (Document Image Binarization Competition)": "dibco",
        "DIQA-5000": "diqa-5000",
        "Doc3D (Document 3D Shape Recovery)": "doc3d",
        "DocLayNet": "doclaynet",
        "docsynth300k": "docsynth",
        "Dzongkha Digits (Tibetan Script)": "dzongkha-digits",
        "FinanceBench": "financebench",
        "FinTabNet": "fintabnet",
        "FUNSD": "funsd",
        "FUNSD+ (Extended FUNSD)": "funsd-plus",
        "hasy (HASYv2 - Math Symbols Handwriting)": "hasy",
        "HierText": "hiertext",
        "Hindi OCR Synthetic Dataset": "hindi-synth",
        "IAM Handwriting Database": "iam",
        "im2latex-100k": "im2latex",
        "invoices_kaggle": "invoices-kg",
        "invoices-kg": "invoices-kg",
        "JSSODa (Japanese Simple Synthetic OCR Dataset)": "jssoda",
        "MathVerse": "mathverse",
        "MDIW-13 (Foundational Script Identification Dataset)": "mdiw13",
        "MIDV-500 (Cyrillic + Latin ID Documents)": "midv500",
        "MLE2E (Multi-Language End-to-End)": "mle2e",
        "mle2e (Multi-Language End-to-End)": "mle2e",
        "MLT-19 (ICDAR 2019 Multilingual Text)": "mlt19",
        "Muharaf (Arabic Historical Manuscripts)": "muharaf",
        "Multimodal Textbook": "multimodal-textbook",
        "Nepali Handwritten Dataset": "nepali-handwritten",
        "NIST Special Database 2 (SD-2)": "nist-sd2",
        "NIST Special Database 6 (SD-6)": "nist-sd6",
        "NIST Special Database 19 (SD-19)": "nist-sd19",
        "OCR-Quality": "ocr-quality",
        "OHR-Bench": "ohr-bench",
        "OmniDocBench": "omnidocbench",
        "OpenLID-v2 (Text Corpus for Synthetic Generation)": "openlid-v2",
        "PubTabNet": "pubtabnet",
        "PUCIT-OHUL": "pucit-ohul",
        "RealDAE (Real-world Document Appearance Enhancement)": "realdae",
        "receipts_hitl (Human-in-the-Loop Receipts)": "mobile-receipts",
        "RVL-CDIP": "rvl-cdip",
        "SignaTR6K (Signature Dataset)": "signatr6k",
        "SIW-13 (Script Identification in the Wild)": "siw13",
        "SmartDoc-QA": "smartdoc-qa",
        "SROIE": "sroie",
        "Synthetic Multi-Script Dataset (OpenLID-Integrated)": "synth-multiscript-250k",
        "TableBank": "tablebank",
        "TibHCR (Tibetan Handwritten Character Recognition)": "tibhcr",
        "Tobacco-800": "tobacco800",
        "WiLI-2018": "wili-2018",
        "Yarmouk OCR Dataset": "yarmouk",
    }

    # Check manual mappings first
    if name in manual_mappings:
        return manual_mappings[name]

    # Check if it's already canonical
    if name.lower() in CANONICAL_NAMES:
        return name.lower()

    # Search in aliases
    for canonical, aliases in CANONICAL_NAMES.items():
        if name in aliases or name.lower() in [a.lower() for a in aliases]:
            return canonical

    # If not found, convert to lowercase kebab-case
    return re.sub(r"[_\s\(\)]+", "-", name.lower()).strip("-")


def is_subsection_header(header_text: str) -> bool:
    """Check if a #### header is a subsection (not a dataset name)."""
    header_lower = header_text.lower()

    # Subsections that start with numbers (e.g., "1.", "2.", "3c.", "4.1", etc.)
    if re.match(r"^\d+[a-z]?\.", header_lower):
        return True

    # Informational sections (not actual datasets)
    informational_patterns = [
        r"downloaded\s+.*\s+datasets",  # "Downloaded Script Detection Datasets"
        r"additional\s+.*\s+resources",  # "Additional Script Detection Resources"
        r"nepal\s+devanagari\s+documents",  # "Nepal Devanagari Documents" (meta section)
        r"human-in-the-loop",  # "receipts_hitl (Human-in-the-Loop Receipts)" - might be a dataset, keep for now
    ]

    for pattern in informational_patterns:
        if re.search(pattern, header_lower):
            return True

    # Subsection keyword patterns (not dataset names)
    subsection_keywords = [
        # Meta sections
        r"\boverview\b",
        r"\binventory\b",
        r"\busage\b",
        r"\bstatistics\b",
        r"\bcomposition\b",
        r"\bprofile\b",
        r"\bissues\b",
        r"\blimitations\b",
        r"\breferences\b",
        r"\bnotes\b",
        r"\blocations\b",
        r"\bcoverage\b",
        r"\bvalue\b",
        r"\blayer\s+2\b",
        r"\bannotation\s+summary\b",
        r"\bdistortion\s+types\b",
        r"\bfinding\b",
        r"\bcitation\b",
        r"\bdownload\s+instructions\b",
        r"\brepresentative\s+samples\b",
        r"\bdata\s+structure\b",
        r"\bmetadata\b",
        # Specific patterns
        r"^\s*benchmark\s+(performance|purpose|results)",
        r"^\s*(document|ocr)\s+(domains|sources|types|noise)",
        r"^\s*project\s+usage",
        r"^\s*parser\s+",
        r"^\s*key\s+(research\s+)?finding",
    ]

    for pattern in subsection_keywords:
        if re.search(pattern, header_lower):
            return True

    # Check for "X & Y" patterns (e.g., "Known Issues & Limitations")
    if "&" in header_text:
        return True

    return False


def is_major_section_header(header_text: str) -> bool:
    """Check if a ### header is a major section (not a dataset)."""
    # Category section headers (e.g., "1.1 Tables", "1.2 Documents")
    if re.match(r"^\d+\.\d+\s+\w+", header_text):
        return True

    major_sections = [
        "Base Training Datasets",
        "Language & Script Detection",
        "Text Corpus Sources",
        "Benchmark-Only",
        "Cross-Validation",
        "Training Datasets",
        "IQA & Benchmark Datasets",
        "Extracted Annotations Summary",
        "Phase",
        "Legacy Model Folders",
        "Source Archives",
        "Dataset Backups",
        "Checkpoint Backups",
        "For Training",
        "For Evaluation",
        "For Development",
        "Dataset Documentation",
        "Schema & Label Mapping",
        "Schema Utilities",
        "External Standards References",
    ]

    for section in major_sections:
        if section.lower() in header_text.lower():
            return True
    return False


def extract_datasets(
    catalog_path: Path,
) -> tuple[list[tuple[str, str, int, int]], list[str]]:
    """
    Extract dataset sections from catalog.

    Returns:
        - list of (canonical_name, section_content, start_line, end_line)
        - list of skipped dataset names
    """
    with open(catalog_path, encoding="utf-8") as f:
        lines = f.readlines()

    datasets = []
    current_dataset = None
    current_lines = []
    start_line = 0
    skipped_datasets = []

    for i, line in enumerate(lines, 1):
        # Look for dataset headers (### or #### {Dataset Name})
        if line.startswith("### "):
            section_title = line[4:].strip()

            # Check if this is a major section boundary (skip it, don't reset dataset)
            if is_major_section_header(section_title):
                # Save current dataset if exists
                if current_dataset and current_lines:
                    content = "".join(current_lines)
                    datasets.append((current_dataset, content, start_line, i - 1))
                    current_dataset = None
                    current_lines = []
                # Don't start a new dataset for category headers, just skip
                continue

            # Otherwise, this is a dataset at ### level
            # Save previous dataset if exists
            if current_dataset:
                content = "".join(current_lines)
                datasets.append((current_dataset, content, start_line, i - 1))

            # Start new dataset
            canonical_name = normalize_dataset_name(section_title)
            if canonical_name is None:
                # Skip this dataset
                skipped_datasets.append(section_title)
                current_dataset = None
                current_lines = []
                continue
            current_dataset = canonical_name
            current_lines = [line]
            start_line = i

        elif line.startswith("#### "):
            dataset_name = line[5:].strip()

            # Check if this is a subsection header (not a dataset)
            if is_subsection_header(dataset_name):
                # This is a subsection within a dataset, just accumulate
                if current_dataset:
                    current_lines.append(line)
                continue

            # This is a new dataset header at #### level
            # Save previous dataset if exists
            if current_dataset:
                content = "".join(current_lines)
                datasets.append((current_dataset, content, start_line, i - 1))

            # Start new dataset
            canonical_name = normalize_dataset_name(dataset_name)
            if canonical_name is None:
                # Skip this dataset (e.g., "Arabic OCR Dataset" - not in canonical 51)
                skipped_datasets.append(dataset_name)
                current_dataset = None
                current_lines = []
                continue
            current_dataset = canonical_name
            current_lines = [line]
            start_line = i

        # Accumulate lines for current dataset
        elif current_dataset:
            current_lines.append(line)

    # Save last dataset
    if current_dataset and current_lines:
        content = "".join(current_lines)
        datasets.append((current_dataset, content, start_line, len(lines)))

    return datasets, skipped_datasets


def main():
    catalog_path = Path("/home/byron/dev/image_detection/docs/DATASET_CATALOG.md")
    output_dir = Path("/home/byron/dev/image_detection/docs/datasets/source")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract datasets
    print(f"Reading {catalog_path}...")
    datasets, skipped_datasets = extract_datasets(catalog_path)

    print(f"\nFound {len(datasets)} dataset sections:")
    print("-" * 80)

    created_files = []

    for canonical_name, content, start_line, end_line in datasets:
        output_file = output_dir / f"{canonical_name}.md"

        # Write file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        created_files.append(output_file.name)
        print(
            f"✓ {canonical_name:30s} → {output_file.name:35s} (lines {start_line:5d}-{end_line:5d}, {len(content):6d} bytes)"
        )

    print("-" * 80)
    print(f"\nCreated {len(created_files)} files in {output_dir}")

    if skipped_datasets:
        print(f"\nSkipped {len(skipped_datasets)} datasets (not in canonical list):")
        for name in sorted(set(skipped_datasets)):
            print(f"  - {name}")

    print("\nFiles created:")
    for filename in sorted(created_files):
        print(f"  - {filename}")

    # Verify count
    expected_count = len(CANONICAL_NAMES)
    actual_count = len(created_files)
    print("\nVerification:")
    print(f"  Expected datasets: {expected_count}")
    print(f"  Extracted datasets: {actual_count}")

    if actual_count < expected_count:
        print(f"\n⚠️  Warning: Missing {expected_count - actual_count} datasets")
        # Find missing datasets
        created_names = set(f.replace(".md", "") for f in created_files)
        missing = set(CANONICAL_NAMES.keys()) - created_names
        if missing:
            print(f"  Missing: {', '.join(sorted(missing))}")
    elif actual_count > expected_count:
        print(f"\n⚠️  Warning: {actual_count - expected_count} extra datasets found")
    else:
        print("  ✓ All datasets extracted successfully!")


if __name__ == "__main__":
    main()
