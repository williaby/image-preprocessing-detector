"""Update Data Locations tables in all dataset documentation files.

Reads verified E drive image counts and annotation status,
then updates/inserts Data Locations tables in docs/datasets/source/*.md.
"""

from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path("docs/datasets/source")

# Verified E drive image counts and paths (from 2026-02-06 audit)
DATASET_INFO: dict[str, dict[str, str | int | bool]] = {
    "arabic-docs": {
        "images": 10045,
        "e_path": "01_base_data/language/arabic_docs_ocr",
        "img_format": "JPG/PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "12 document categories with matching JSON annotations",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "bhutan-afs": {
        "images": 135,
        "e_path": "01_base_data/documents/bhutan_financial",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Bhutan Annual Financial Statements",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "cc-ocr": {
        "images": 6533,
        "e_path": "01_base_data/language/cc-ocr",
        "img_format": "JPG/PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Multi-scene, multi-lingual OCR benchmark",
        "gt_text": True,
        "gt_text_format": "TSV",
        "gt_text_desc": "Full OCR text in `answer` field (doc_parsing, kie TSVs)",
    },
    "coco-text": {
        "images": 123287,
        "e_path": "01_base_data/text_detection/cocotext",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "MS COCO images with text annotations",
        "gt_text": True,
        "gt_text_format": "JSON (COCO)",
        "gt_text_desc": "Word-level scene text (`anns.utf8_string` in cocotext.v2.json)",
    },
    "cvsi": {
        "images": 10715,
        "e_path": "01_base_data/language/cvsi",
        "img_format": "JPG/PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "CVSI-2015 video script identification",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "dibco": {
        "images": 212,
        "e_path": "02_benchmark_only/dibco",
        "img_format": "PNG/BMP",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Document Image Binarization Competition (benchmark only)",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "diqa-5000": {
        "images": 5500,
        "e_path": "02_benchmark_only/diqa-5000",
        "img_format": "JPG",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 5500,
        "layout_records": 5411,
        "notes": "Document Image Quality Assessment",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "doc3d": {
        "images": 102064,
        "e_path": "01_base_data/camera_captured/doc3d/data/doc3d/img",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "448x448 RGBA, 21 mesh ID subdirs (~5K each)",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "doclaynet": {
        "images": 81471,
        "e_path": "01_base_data/documents/doclaynet",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Has native DocLayNet annotations (11-class COCO format)",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "Word-level text with font metadata (`cells[].text` in per-doc JSON)",
    },
    "docsynth": {
        "images": 300000,
        "e_path": "01_base_data/layout/docsynth300k",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "DocSynth300K synthetic documents with layout annotations",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "dzongkha-digits": {
        "images": 62,
        "e_path": "01_base_data/language/multilingual_scripts/dzongkha_digits",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Dzongkha handwritten digit samples",
        "gt_text": "partial",
        "gt_text_format": "Labels",
        "gt_text_desc": "Digit class labels from directory structure",
    },
    "financebench": {
        "images": 54121,
        "e_path": "02_benchmark_only/financebench",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Financial document pages from SEC filings",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "QA text pairs from financial documents",
    },
    "fintabnet": {
        "images": 97475,
        "e_path": "01_base_data/tables/fintabnet",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Financial table images with structure annotations",
        "gt_text": True,
        "gt_text_format": "JSONL",
        "gt_text_desc": "Cell-level text in table structure annotations",
    },
    "funsd": {
        "images": 348,
        "e_path": "01_base_data/forms/funsd",
        "img_format": "PNG",
        "has_ocr": True,
        "has_layout": False,
        "ocr_records": 1324,
        "layout_records": 0,
        "notes": "199 forms (348 image files across train/test splits)",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "Entity & word-level transcriptions (`form[].text`, `form[].words[].text`)",
    },
    "funsd-plus": {
        "images": 1139,
        "e_path": "01_base_data/forms/funsd_plus",
        "img_format": "PNG/JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Extended FUNSD with additional annotations",
        "gt_text": True,
        "gt_text_format": "Arrow/Parquet",
        "gt_text_desc": "Word-level transcriptions (`words` string array in HuggingFace format)",
    },
    "hasy": {
        "images": 168233,
        "e_path": "01_base_data/handwriting/hasy",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "HASYv2 handwritten symbol recognition",
        "gt_text": "partial",
        "gt_text_format": "CSV",
        "gt_text_desc": "LaTeX symbol labels (`latex` field, e.g., `A`, `\\alpha`, `\\sum`)",
    },
    "hiertext": {
        "images": 11641,
        "e_path": "01_base_data/text_detection/hiertext",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Hierarchical text detection annotations",
        "gt_text": True,
        "gt_text_format": "JSONL",
        "gt_text_desc": "Word & line-level text (`words[].text`, `lines[].text` in gt/*.jsonl)",
    },
    "hindi-synth": {
        "images": 80009,
        "e_path": "01_base_data/language/hindi_ocr_synthetic",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Synthetic Hindi OCR line images",
        "gt_text": True,
        "gt_text_format": "CSV/TXT",
        "gt_text_desc": "Paired image-text files (Devanagari line transcriptions)",
    },
    "iam": {
        "images": 130212,
        "e_path": "01_base_data/handwriting/iam_handwriting",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "IAM Handwriting Database (words + lines + forms)",
        "gt_text": True,
        "gt_text_format": "XML + TXT",
        "gt_text_desc": "Word/line transcriptions (`xml/*.xml` word text + `ascii/lines.txt`)",
    },
    "im2latex": {
        "images": 10000,
        "e_path": "01_base_data/formulas/im2latex",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "LaTeX formula images with ground truth LaTeX",
        "gt_text": True,
        "gt_text_format": "TXT",
        "gt_text_desc": "LaTeX formula source code (`im2latex_formulas.lst`, line-indexed)",
    },
    "invoices-kg": {
        "images": 1414,
        "e_path": "01_base_data/forms/invoices_kaggle",
        "img_format": "JPG/PNG",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 1414,
        "layout_records": 1414,
        "notes": "Invoice images from Kaggle",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "Invoice fields + line items + full OCR text (`ocred_text`, `json_data`)",
    },
    "jssoda": {
        "images": 2000,
        "e_path": "01_base_data/language/multilingual_scripts/jssoda",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Japanese Street Sign OCR Dataset",
        "gt_text": "partial",
        "gt_text_format": "JSON",
        "gt_text_desc": "Japanese text annotations in sign images",
    },
    "mathverse": {
        "images": 6940,
        "e_path": "02_benchmark_only/mathverse",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Mathematical reasoning visual problems (benchmark only)",
        "gt_text": True,
        "gt_text_format": "JSON/Parquet",
        "gt_text_desc": "Math problem text and answers",
    },
    "mdiw13": {
        "images": 290213,
        "e_path": "01_base_data/language/mdiw13",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Multi-Domain Isolated Word dataset (13 scripts)",
        "gt_text": "partial",
        "gt_text_format": "Labels",
        "gt_text_desc": "Word-level script/language labels (not full text transcriptions)",
    },
    "midv500": {
        "images": 3612,
        "e_path": "01_base_data/documents/midv500",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Identity document video frames",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "ID document field values (`ground_truth/{doc_type}.json`)",
    },
    "mle2e": {
        "images": 1816,
        "e_path": "01_base_data/language/mle2e",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Multi-Language End-to-End text detection",
        "gt_text": True,
        "gt_text_format": "TXT/JSON",
        "gt_text_desc": "Word-level text in detection annotations",
    },
    "mlt19": {
        "images": 19993,
        "e_path": "01_base_data/language/mlt19",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "ICDAR 2019 Multi-Lingual Text detection",
        "gt_text": True,
        "gt_text_format": "TXT",
        "gt_text_desc": "Per-word text with language labels (`TrainGT/*.txt`)",
    },
    "multimodal-textbook": {
        "images": 1113,
        "e_path": "01_base_data/educational/multimodal_textbook",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Textbook pages with multimodal content",
        "gt_text": True,
        "gt_text_format": "Parquet/JSON",
        "gt_text_desc": "Full textbook content text",
    },
    "muharaf": {
        "images": 25711,
        "e_path": "01_base_data/handwriting/muharaf",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Arabic handwriting recognition dataset",
        "gt_text": True,
        "gt_text_format": "TXT + XML",
        "gt_text_desc": "Line-level Arabic transcriptions (24,495 `.txt` files + PAGE XML `<Unicode>`)",
    },
    "nepali-handwritten": {
        "images": 958,
        "e_path": "01_base_data/language/nepali_handwritten",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Nepali handwritten text detection",
        "gt_text": "partial",
        "gt_text_format": "Labels",
        "gt_text_desc": "Character/digit class labels",
    },
    "nist-sd19": {
        "images": 3669,
        "e_path": "01_base_data/handwriting/nist-sd19",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "NIST Special Database 19 handwriting samples",
        "gt_text": "partial",
        "gt_text_format": "Binary (.hsf)",
        "gt_text_desc": "Character-level ground truth from filename/directory structure",
    },
    "nist-sd2": {
        "images": 5590,
        "e_path": "01_base_data/forms/nist-sd2",
        "img_format": "TIF",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 5590,
        "layout_records": 5590,
        "notes": "NIST Special Database 2 structured forms",
        "gt_text": True,
        "gt_text_format": "TXT (.fmt)",
        "gt_text_desc": "Form field values (field_id value pairs in `.fmt` files)",
    },
    "nist-sd6": {
        "images": 5595,
        "e_path": "01_base_data/forms/nist_sd6",
        "img_format": "PNG",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 5595,
        "layout_records": 5593,
        "notes": "NIST Special Database 6 structured forms",
        "gt_text": True,
        "gt_text_format": "TXT (.fmt)",
        "gt_text_desc": "Form field values (field_id value pairs in `.fmt` files)",
    },
    "ocr-quality": {
        "images": 1000,
        "e_path": "01_base_data/ocr_quality",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "OCR quality assessment images",
        "gt_text": True,
        "gt_text_format": "Parquet",
        "gt_text_desc": "Full page OCR text by Qwen2.5-VL-72B (`ocr_text` field)",
    },
    "ohr-bench": {
        "images": 16091,
        "e_path": "02_benchmark_only/ohr-bench",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Online Handwriting Recognition Benchmark",
        "gt_text": True,
        "gt_text_format": "Parquet",
        "gt_text_desc": "Structured ground truth text (`gt_text` field in HuggingFace parquet)",
    },
    "omnidocbench": {
        "images": 1358,
        "e_path": "02_benchmark_only/omnidocbench",
        "img_format": "PNG/JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Multi-source document benchmark (benchmark only)",
        "gt_text": True,
        "gt_text_format": "Parquet",
        "gt_text_desc": "Multi-level ground truth text (`gt_text` field in HuggingFace parquet)",
    },
    "openlid-v2": {
        "images": 0,
        "e_path": "N/A",
        "img_format": "N/A",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Text corpus for language identification - no images",
        "text_corpus": True,
        "gt_text": True,
        "gt_text_format": "HuggingFace",
        "gt_text_desc": "Sentence-level text samples (116M+ text corpus, `text` field)",
    },
    "pucit-ohul": {
        "images": 7401,
        "e_path": "01_base_data/language/pucit-ohul",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "PUCIT Handwritten Urdu Lines dataset",
        "gt_text": True,
        "gt_text_format": "XLSX",
        "gt_text_desc": "Line-level Urdu transcriptions (`train_labels_v2.xlsx`, `test_labels_v2.xlsx`)",
    },
    "pubtabnet": {
        "images": 519030,
        "e_path": "01_base_data/tables/pubtabnet",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Table recognition with structure annotations in JSONL",
        "gt_text": True,
        "gt_text_format": "JSONL",
        "gt_text_desc": "Cell-level text as token arrays (`html.cells[].tokens`)",
    },
    "realdae": {
        "images": 1200,
        "e_path": "01_base_data/camera_captured/realdae",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Real Document Adverse Environment captures",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "rvl-cdip": {
        "images": 16000,
        "e_path": "01_base_data/documents/rvl_cdip",
        "img_format": "JPEG",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 16000,
        "layout_records": 15733,
        "notes": "Document classification (4% subset of full 400K)",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "signatr6k": {
        "images": 12514,
        "e_path": "01_base_data/handwriting/signatr6k",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Signature image dataset",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "siw13": {
        "images": 16291,
        "e_path": "01_base_data/language/siw13",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Script Identification in the Wild (13 scripts)",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "smartdoc-qa": {
        "images": 4280,
        "e_path": "02_benchmark_only/smartdoc-qa",
        "img_format": "JPG",
        "has_ocr": True,
        "has_layout": True,
        "ocr_records": 3000,
        "layout_records": 2203,
        "notes": "SmartDoc-QA document quality assessment",
        "gt_text": True,
        "gt_text_format": "JSON",
        "gt_text_desc": "QA text pairs from document images",
    },
    "sroie": {
        "images": 973,
        "e_path": "01_base_data/forms/sroie_icdar2019",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "ICDAR 2019 SROIE receipts with OCR ground truth",
        "gt_text": True,
        "gt_text_format": "JSON + TXT",
        "gt_text_desc": "Per-region transcriptions + entity labels (company, date, address, total)",
    },
    "tablebank": {
        "images": 260025,
        "e_path": "01_base_data/tables/tablebank",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Table detection with COCO-format annotations",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "tibhcr": {
        "images": 141698,
        "e_path": "01_base_data/language/huggingface_downloads/TibHCR",
        "img_format": "PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Tibetan Handwritten Character Recognition",
        "gt_text": "partial",
        "gt_text_format": "TXT (CSV)",
        "gt_text_desc": "Tibetan Unicode character labels (`label.txt`)",
    },
    "tobacco800": {
        "images": 1290,
        "e_path": "01_base_data/degraded/tobacco800",
        "img_format": "TIFF/PNG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Tobacco litigation documents (degraded)",
        "gt_text": False,
        "gt_text_format": "",
        "gt_text_desc": "",
    },
    "wili-2018": {
        "images": 0,
        "e_path": "01_base_data/language/wili_2018",
        "img_format": "N/A",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Text corpus for language identification - no images",
        "text_corpus": True,
        "gt_text": True,
        "gt_text_format": "TXT",
        "gt_text_desc": "Wikipedia paragraph text (`x_train.txt`, `x_test.txt`)",
    },
    "yarmouk": {
        "images": 15062,
        "e_path": "01_base_data/language/yarmouk",
        "img_format": "JPG",
        "has_ocr": False,
        "has_layout": False,
        "ocr_records": 0,
        "layout_records": 0,
        "notes": "Yarmouk Arabic OCR dataset",
        "gt_text": "partial",
        "gt_text_format": "TXT",
        "gt_text_desc": "OCR output text files (`OCR/` directory, 4,633 files)",
    },
}


def format_count(n: int) -> str:
    """Format number with commas."""
    return f"{n:,}"


def build_data_locations_table(name: str, info: dict) -> str:
    """Build the Data Locations markdown table for a dataset."""
    images = info["images"]
    e_path = info["e_path"]
    img_format = info["img_format"]
    is_text_corpus = info.get("text_corpus", False)
    has_ocr = info["has_ocr"]
    has_layout = info["has_layout"]
    ocr_records = info["ocr_records"]
    layout_records = info["layout_records"]
    notes = info["notes"]

    lines = []
    lines.append("")
    lines.append("##### Data Locations")
    lines.append("")
    lines.append("| Data Type | Path | Status | Notes |")
    lines.append("|-----------|------|--------|-------|")

    # Images row
    if is_text_corpus:
        lines.append(
            "| **Images** | N/A | N/A | Text corpus - no images |"
        )
    elif images == 0 and "zip" in str(notes).lower():
        lines.append(
            f"| **Images** | `{e_path}/` "
            f"| ⚠️ Archives | {notes} |"
        )
    else:
        lines.append(
            f"| **Images** | `{e_path}/` "
            f"| ✅ Available | {format_count(images)} {img_format} files |"
        )

    # Ground truth text row (native dataset annotations, not Docling OCR)
    gt_text = info.get("gt_text", False)
    gt_text_format = info.get("gt_text_format", "")
    gt_text_desc = info.get("gt_text_desc", "")

    if gt_text is True:
        lines.append(
            f"| **Text/GT** | Native annotations | ✅ Available | {gt_text_format}: {gt_text_desc} |"
        )
    elif gt_text == "partial":
        lines.append(
            f"| **Text/GT** | Native annotations | ⚠️ Partial | {gt_text_format}: {gt_text_desc} |"
        )
    else:
        lines.append(
            "| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |"
        )

    # OCR row (Docling extraction)
    if has_ocr:
        ocr_pattern = "batch_*.jsonl" if name == "funsd" else "ocr_batch_*.jsonl"
        coverage = ""
        if images > 0:
            pct = min(100, round(ocr_records / images * 100))
            coverage = f" ({pct}%)"
        lines.append(
            f"| **Text/OCR Extracted** | `annotations/{name}/ocr/{ocr_pattern}` "
            f"| ✅ Available | {format_count(ocr_records)} records{coverage}, Docling OCR |"
        )
    else:
        lines.append(
            "| **Text/OCR Extracted** | - "
            "| ❌ Not extracted | Docling OCR not yet run |"
        )

    # Layout row
    if has_layout:
        coverage = ""
        if images > 0:
            pct = min(100, round(layout_records / images * 100))
            coverage = f" ({pct}%)"
        lines.append(
            f"| **Layout Extracted** | `annotations/{name}/layout/layout_batch_*.json` "
            f"| ✅ Available | {format_count(layout_records)} records{coverage}, DocLayout-YOLO |"
        )
    else:
        lines.append(
            "| **Layout Extracted** | - "
            "| ❌ Not extracted | DocLayout-YOLO not yet run |"
        )

    lines.append("")
    return "\n".join(lines)


def find_insertion_point(content: str) -> tuple[int, int, str]:
    """Find where to insert/replace Data Locations table.

    Returns (start_idx, end_idx, method) where method is 'replace' or 'insert'.
    """
    lines = content.split("\n")

    # First, check if Data Locations table already exists
    for i, line in enumerate(lines):
        if "Data Locations" in line and line.strip().startswith("#"):
            # Found existing table header - find extent
            start = i
            # Look backwards for blank line before heading
            while start > 0 and lines[start - 1].strip() == "":
                start -= 1

            # Find end of table (next heading or section break)
            end = i + 1
            in_table = False
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped.startswith("|"):
                    in_table = True
                    end = j + 1
                elif in_table and stripped == "":
                    end = j + 1
                    break
                elif in_table and (stripped.startswith("#") or stripped.startswith("---")):
                    break
                elif not in_table and stripped == "":
                    continue
                elif not in_table and (
                    stripped.startswith("|") or stripped == ""
                ):
                    continue
                elif stripped.startswith("#") or stripped.startswith("---"):
                    break
                else:
                    end = j + 1

            return start, end, "replace"

    # Check for Quick Reference Data Locations (different format)
    for i, line in enumerate(lines):
        if line.strip() == "**Data Locations**:":
            start = i
            end = i + 1
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped.startswith("|"):
                    end = j + 1
                elif stripped == "":
                    end = j + 1
                    break
                elif stripped.startswith("#") or stripped.startswith("["):
                    break
                else:
                    end = j + 1
            return start, end, "replace"

    # No existing table - find insertion point after Project Usage section
    for i, line in enumerate(lines):
        if re.search(r"Project Usage", line) and line.strip().startswith("#"):
            # Find end of Project Usage section
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped.startswith("#") and "Data" not in stripped:
                    return j, j, "insert"
            # If Project Usage is the last section, insert at end
            return len(lines), len(lines), "insert"

    # Fallback: insert before References or at end of file
    for i, line in enumerate(lines):
        if re.search(r"References|Citation", line) and line.strip().startswith("#"):
            return i, i, "insert"

    # Last resort: insert before the last line
    return len(lines) - 1, len(lines) - 1, "insert"


def update_dataset_file(name: str, info: dict) -> tuple[bool, str]:
    """Update a single dataset file with correct Data Locations."""
    filepath = DOCS_DIR / f"{name}.md"
    if not filepath.exists():
        return False, f"File not found: {filepath}"

    content = filepath.read_text()
    table = build_data_locations_table(name, info)
    lines = content.split("\n")

    start, end, method = find_insertion_point(content)

    if method == "replace":
        new_lines = lines[:start] + table.split("\n") + lines[end:]
    else:
        new_lines = lines[:start] + table.split("\n") + lines[start:]

    new_content = "\n".join(new_lines)

    # Clean up triple+ blank lines
    while "\n\n\n\n" in new_content:
        new_content = new_content.replace("\n\n\n\n", "\n\n\n")

    filepath.write_text(new_content)
    return True, f"{method}d at line {start}"


def main() -> None:
    """Update all dataset documentation files."""
    print(f"Updating {len(DATASET_INFO)} dataset documentation files...\n")

    success = 0
    failed = 0

    for name in sorted(DATASET_INFO):
        info = DATASET_INFO[name]
        ok, msg = update_dataset_file(name, info)
        status = "OK" if ok else "FAIL"
        print(f"  {status}: {name:<25} {msg}")
        if ok:
            success += 1
        else:
            failed += 1

    print(f"\nDone: {success} updated, {failed} failed")


if __name__ == "__main__":
    main()
