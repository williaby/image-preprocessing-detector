# Dataset Audit Report

**Datasets audited**: 50

## Executive Summary

| Dimension | Complete | Partial | Missing |
|-----------|----------|---------|---------|
| documentation | 2 | 46 | 2 |
| metadata | 27 | 5 | 18 |
| parser | 31 | 10 | 9 |
| cross_file | 45 | 5 | 0 |
| aggregation | 11 | 9 | 30 |

## Per-Dataset Status (worst first)

| Dataset | Score | Docs | Metadata | Parser | Cross-File | Aggregation |
|---------|-------|------|----------|--------|------------|-------------|
| coco-text | 18.8 | Missing | Missing | Missing | Partial | Missing |
| arabic-docs | 25.0 | Partial | Missing | Partial | Complete | Missing |
| doc3d | 25.0 | Partial | Missing | Missing | Complete | Missing |
| hiertext | 25.0 | Partial | Missing | Partial | Complete | Missing |
| hindi-synth | 25.0 | Partial | Missing | Missing | Partial | Missing |
| invoices-kg | 25.0 | Partial | Missing | Partial | Partial | Missing |
| jssoda | 25.0 | Partial | Missing | Partial | Complete | Missing |
| mathverse | 25.0 | Partial | Missing | Partial | Complete | Complete |
| openlid-v2 | 25.0 | Partial | Missing | Missing | Complete | Missing |
| yarmouk | 25.0 | Partial | Missing | Partial | Complete | Missing |
| bhutan-afs | 31.2 | Partial | Missing | Missing | Complete | Missing |
| ohr-bench | 35.4 | Missing | Partial | Complete | Complete | Partial |
| docsynth | 37.5 | Partial | Missing | Missing | Complete | Missing |
| hasy | 37.5 | Partial | Missing | Missing | Complete | Missing |
| muharaf | 37.5 | Partial | Missing | Complete | Partial | Missing |
| nist-sd2 | 37.5 | Partial | Missing | Partial | Complete | Missing |
| wili-2018 | 37.5 | Partial | Missing | Missing | Complete | Missing |
| dzongkha-digits | 43.8 | Partial | Missing | Missing | Complete | Missing |
| iam | 43.8 | Partial | Missing | Complete | Complete | Missing |
| mdiw13 | 47.9 | Partial | Partial | Complete | Complete | Complete |
| mlt19 | 50.0 | Partial | Complete | Complete | Complete | Partial |
| financebench | 51.0 | Partial | Complete | Complete | Complete | Missing |
| multimodal-textbook | 53.1 | Partial | Partial | Complete | Complete | Missing |
| siw13 | 53.1 | Partial | Complete | Complete | Complete | Missing |
| dibco | 54.1 | Partial | Partial | Complete | Partial | Partial |
| midv500 | 54.1 | Partial | Complete | Complete | Complete | Partial |
| im2latex | 55.2 | Partial | Complete | Complete | Complete | Complete |
| funsd-plus | 56.2 | Partial | Complete | Complete | Complete | Missing |
| sroie | 56.2 | Partial | Complete | Complete | Complete | Complete |
| tobacco800 | 56.2 | Partial | Complete | Complete | Complete | Partial |
| omnidocbench | 58.4 | Partial | Complete | Complete | Complete | Partial |
| smartdoc-qa | 58.4 | Partial | Complete | Partial | Complete | Partial |
| cc-ocr | 59.4 | Partial | Complete | Complete | Complete | Missing |
| pucit-ohul | 60.4 | Partial | Complete | Complete | Complete | Missing |
| tibhcr | 60.4 | Partial | Complete | Complete | Complete | Complete |
| fintabnet | 61.5 | Partial | Complete | Complete | Complete | Complete |
| signatr6k | 61.5 | Partial | Complete | Partial | Complete | Complete |
| diqa-5000 | 62.5 | Partial | Complete | Partial | Complete | Partial |
| nist-sd19 | 62.5 | Partial | Complete | Complete | Complete | Missing |
| doclaynet | 64.6 | Partial | Complete | Complete | Complete | Complete |
| cvsi | 66.7 | Partial | Complete | Complete | Complete | Missing |
| ocr-quality | 66.7 | Partial | Partial | Complete | Complete | Missing |
| rvl-cdip | 68.8 | Partial | Complete | Complete | Complete | Missing |
| mle2e | 71.8 | Partial | Complete | Complete | Complete | Missing |
| nepali-handwritten | 72.9 | Partial | Complete | Complete | Complete | Missing |
| funsd | 74.0 | Partial | Complete | Complete | Complete | Complete |
| pubtabnet | 74.0 | Partial | Complete | Complete | Complete | Complete |
| tablebank | 74.0 | Partial | Complete | Complete | Complete | Complete |
| realdae | 76.0 | Complete | Complete | Complete | Complete | Partial |
| nist-sd6 | 78.1 | Complete | Complete | Complete | Complete | Missing |

## Action Items

### P0: No Layer 2 metadata

- coco-text: No Layer 2 metadata in parquet
- arabic-docs: No Layer 2 metadata in parquet
- doc3d: No Layer 2 metadata in parquet
- hiertext: No Layer 2 metadata in parquet
- hindi-synth: No Layer 2 metadata in parquet
- invoices-kg: No Layer 2 metadata in parquet
- jssoda: No Layer 2 metadata in parquet
- mathverse: No Layer 2 metadata in parquet
- openlid-v2: No Layer 2 metadata in parquet
- yarmouk: No Layer 2 metadata in parquet
- bhutan-afs: No Layer 2 metadata in parquet
- docsynth: No Layer 2 metadata in parquet
- hasy: No Layer 2 metadata in parquet
- muharaf: No Layer 2 metadata in parquet
- nist-sd2: No Layer 2 metadata in parquet
- wili-2018: No Layer 2 metadata in parquet
- dzongkha-digits: No Layer 2 metadata in parquet
- iam: No Layer 2 metadata in parquet

### P2: Documentation compliance gaps

- coco-text: Missing sections: 3_project_usage, 5_content, 6_iqa_profile, 7_known_issues, 9_references
- arabic-docs: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- doc3d: Missing sections: 5_content, 6_iqa_profile, 7_known_issues, 9_references
- hiertext: Missing sections: 5_content, 6_iqa_profile, 7_known_issues, 9_references
- hindi-synth: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- invoices-kg: Missing sections: 5_content, 6_iqa_profile, 7_known_issues, 9_references
- jssoda: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- mathverse: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- openlid-v2: Missing sections: 5_content, 6_iqa_profile, 7_known_issues, 9_references
- yarmouk: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- bhutan-afs: Missing sections: 2_source_data, 7_known_issues, 9_references
- ohr-bench: Missing sections: 3_project_usage, 4_statistics, 5_content, 6_iqa_profile, 7_known_issues, 9_references
- mdiw13: Missing sections: 3_project_usage, 5_content, 6_iqa_profile, 7_known_issues
- mlt19: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- financebench: Missing sections: 4_statistics, 5_content, 7_known_issues, 9_references
- multimodal-textbook: Missing sections: 2_source_data, 7_known_issues, 9_references
- siw13: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- dibco: Missing sections: 5_content, 7_known_issues, 9_references
- midv500: Missing sections: 2_source_data, 5_content, 7_known_issues, 9_references
- im2latex: Missing sections: 4_statistics, 5_content, 7_known_issues, 9_references
- funsd-plus: Missing sections: 4_statistics, 7_known_issues, 9_references
- sroie: Missing sections: 2_source_data, 5_content, 9_references
- tobacco800: Missing sections: 5_content, 7_known_issues, 9_references
- omnidocbench: Missing sections: 5_content, 7_known_issues, 9_references
- smartdoc-qa: Missing sections: 5_content, 7_known_issues, 9_references
- cc-ocr: Missing sections: 2_source_data, 7_known_issues, 9_references
- pucit-ohul: Missing sections: 5_content, 6_iqa_profile, 7_known_issues, 9_references
- tibhcr: Missing sections: 5_content, 7_known_issues, 9_references
- fintabnet: Missing sections: 2_source_data, 7_known_issues, 9_references
- signatr6k: Missing sections: 2_source_data, 7_known_issues, 9_references
- nist-sd19: Missing sections: 2_source_data, 7_known_issues, 9_references
- doclaynet: Missing sections: 2_source_data, 5_content, 7_known_issues

### P3: Aggregation / optional sections

- coco-text: 8 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- coco-text: No aggregation stats file
- arabic-docs: No aggregation stats file
- doc3d: 0 NEEDS_PROFILING, 5 NEEDS_VERIFICATION
- doc3d: No aggregation stats file
- hiertext: No aggregation stats file
- hindi-synth: No aggregation stats file
- invoices-kg: No aggregation stats file
- jssoda: No aggregation stats file
- openlid-v2: No aggregation stats file
- yarmouk: No aggregation stats file
- bhutan-afs: No aggregation stats file
- docsynth: 2 NEEDS_PROFILING, 4 NEEDS_VERIFICATION
- docsynth: No aggregation stats file
- hasy: 1 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- hasy: No aggregation stats file
- muharaf: 4 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- muharaf: No aggregation stats file
- nist-sd2: No aggregation stats file
- wili-2018: No aggregation stats file
- dzongkha-digits: No aggregation stats file
- iam: 0 NEEDS_PROFILING, 1 NEEDS_VERIFICATION
- iam: No aggregation stats file
- mdiw13: 7 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- financebench: No aggregation stats file
- multimodal-textbook: No aggregation stats file
- siw13: No aggregation stats file
- funsd-plus: No aggregation stats file
- sroie: 0 NEEDS_PROFILING, 3 NEEDS_VERIFICATION
- cc-ocr: No aggregation stats file
- pucit-ohul: 3 NEEDS_PROFILING, 2 NEEDS_VERIFICATION
- pucit-ohul: No aggregation stats file
- diqa-5000: 8 NEEDS_PROFILING, 11 NEEDS_VERIFICATION
- nist-sd19: No aggregation stats file
- cvsi: 11 NEEDS_PROFILING, 4 NEEDS_VERIFICATION
- cvsi: No aggregation stats file
- ocr-quality: 4 NEEDS_PROFILING, 5 NEEDS_VERIFICATION
- ocr-quality: No aggregation stats file
- rvl-cdip: 4 NEEDS_PROFILING, 1 NEEDS_VERIFICATION
- rvl-cdip: No aggregation stats file
- mle2e: 8 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- mle2e: No aggregation stats file
- nepali-handwritten: No aggregation stats file
- tablebank: 1 NEEDS_PROFILING, 0 NEEDS_VERIFICATION
- nist-sd6: No aggregation stats file
