---
schema_type: common
title: "Dataset Taxonomy Coverage Matrix"
tags:
  - reference
  - taxonomy
  - coverage
status: published
owner: docs-team
purpose: Track which taxonomy elements are available for each dataset in the base data collection.
---

**Version**: 1.0
**Date**: 2025-12-17
**Status**: Initial Assessment

## Purpose

This document tracks coverage of taxonomy elements across all datasets. Use this to:

1. Identify gaps requiring annotation
2. Prioritize enrichment efforts
3. Track progress toward complete metadata coverage

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Available from source dataset |
| 🔧 | Derivable via automated pipeline |
| ❌ | Not available, requires manual annotation or LLM |
| ➖ | Not applicable to this dataset |

---

## Coverage Matrix: Source Information

| Dataset | Original Path | File Hash | Download Date | Dataset Version | Original Labels |
|---------|---------------|-----------|---------------|-----------------|-----------------|
| **diqa-5000** | ✅ | 🔧 | ✅ | ✅ | ✅ MOS scores |
| **live** | ✅ | 🔧 | ✅ | ✅ | ✅ DMOS scores |
| **csiq** | ✅ | 🔧 | ✅ | ✅ | ✅ DMOS scores |
| **smartdoc-qa** | ✅ | 🔧 | ✅ | ✅ | ✅ MOS + device |
| **dibco** | ✅ | 🔧 | ✅ | ✅ | ✅ Binary GT |
| **tobacco800** | ✅ | 🔧 | ✅ | ✅ | ❌ |
| **historical_degraded** | ✅ | 🔧 | ✅ | ✅ | ❌ |
| **rvl_cdip** | ✅ | 🔧 | ✅ | ✅ | ✅ 16 categories |
| **doclaynet** | ✅ | 🔧 | ✅ | ✅ | ✅ COCO layout |
| **nist_db2** | ✅ | 🔧 | ✅ | ✅ | ✅ Form fields |
| **nist_sd6** | ✅ | 🔧 | ✅ | ✅ | ✅ Form fields |
| **funsd** | ✅ | 🔧 | ✅ | ✅ | ✅ NER + layout |
| **funsd_plus** | ✅ | 🔧 | ✅ | ✅ | ✅ Extended NER |
| **sroie** | ✅ | 🔧 | ✅ | ✅ | ✅ Entity labels |
| **tablebank** | ✅ | 🔧 | ✅ | ✅ | ✅ Table regions |
| **pubtabnet** | ✅ | 🔧 | ✅ | ✅ | ✅ Table structure |
| **nist_sd19** | ✅ | 🔧 | ✅ | ✅ | ✅ Writer ID |
| **signatr6k** | ✅ | 🔧 | ✅ | ✅ | ✅ Writer + genuine |
| **maths_handwriting** | ✅ | 🔧 | ✅ | ✅ | ❌ |
| **im2latex** | ✅ | 🔧 | ✅ | ✅ | ✅ LaTeX source |
| **mathverse** | ✅ | 🔧 | ✅ | ✅ | ✅ Math problems |
| **multimodal_textbook** | ✅ | 🔧 | ✅ | ✅ | ✅ Page content |

---

## Coverage Matrix: File Metadata (Axis 0)

| Dataset | Format | Width | Height | Channels | File Size | DPI | Color Space |
|---------|--------|-------|--------|----------|-----------|-----|-------------|
| **diqa-5000** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **live** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **csiq** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **smartdoc-qa** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **dibco** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **tobacco800** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **historical_degraded** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **rvl_cdip** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **doclaynet** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **nist_db2** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ✅ 300 | 🔧 |
| **nist_sd6** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ✅ 300 | 🔧 |
| **funsd** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **funsd_plus** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **sroie** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **tablebank** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **pubtabnet** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **nist_sd19** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ✅ 300 | 🔧 |
| **signatr6k** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **maths_handwriting** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **im2latex** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **mathverse** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |
| **multimodal_textbook** | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 |

---

## Coverage Matrix: Domain Classification (Axis 1)

| Dataset | Level 1 | Level 2 | Level 3 | Specific Type | Confidence |
|---------|---------|---------|---------|---------------|------------|
| **diqa-5000** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **live** | ➖ | ➖ | ➖ | ➖ | ➖ |
| **csiq** | ➖ | ➖ | ➖ | ➖ | ➖ |
| **smartdoc-qa** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **dibco** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **tobacco800** | ✅ ADM | ❌ | ❌ | ❌ | 🔧 |
| **historical_degraded** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **rvl_cdip** | ✅ 16 cats | ✅ | ❌ | ❌ | ✅ |
| **doclaynet** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **nist_db2** | ✅ FIN | ✅ Forms | ✅ Checks | ✅ | 🔧 |
| **nist_sd6** | ✅ TAX | ✅ Forms | ✅ Tax Forms | ✅ | 🔧 |
| **funsd** | ✅ ADM | ❌ | ❌ | ❌ | 🔧 |
| **funsd_plus** | ✅ ADM | ❌ | ❌ | ❌ | 🔧 |
| **sroie** | ✅ FIN | ✅ Receipts | ❌ | ❌ | 🔧 |
| **tablebank** | ✅ SCI | ❌ | ❌ | ❌ | 🔧 |
| **pubtabnet** | ✅ SCI | ✅ Papers | ❌ | ❌ | 🔧 |
| **nist_sd19** | ✅ PER | ✅ Handwriting | ❌ | ❌ | 🔧 |
| **signatr6k** | ✅ PER | ✅ Signatures | ❌ | ❌ | 🔧 |
| **maths_handwriting** | ✅ EDU | ✅ Math | ❌ | ❌ | 🔧 |
| **im2latex** | ✅ SCI | ✅ Formulas | ❌ | ❌ | 🔧 |
| **mathverse** | ✅ EDU | ✅ Math | ❌ | ❌ | 🔧 |
| **multimodal_textbook** | ✅ EDU | ✅ Textbooks | ❌ | ❌ | 🔧 |

---

## Coverage Matrix: Structure (Axis 2)

| Dataset | Text Density | Layout Type | Element Types | Reading Order |
|---------|--------------|-------------|---------------|---------------|
| **diqa-5000** | ❌ | ❌ | ❌ | ❌ |
| **live** | ➖ | ➖ | ➖ | ➖ |
| **csiq** | ➖ | ➖ | ➖ | ➖ |
| **smartdoc-qa** | ❌ | ❌ | ❌ | ❌ |
| **dibco** | ❌ | ❌ | ❌ | ❌ |
| **tobacco800** | ❌ | ❌ | ❌ | ❌ |
| **historical_degraded** | ❌ | ❌ | ❌ | ❌ |
| **rvl_cdip** | ❌ | 🔧 | ❌ | ❌ |
| **doclaynet** | 🔧 | ✅ | ✅ COCO | ✅ |
| **nist_db2** | 🔧 | ✅ Form | ✅ Fields | ✅ Form |
| **nist_sd6** | 🔧 | ✅ Form | ✅ Fields | ✅ Form |
| **funsd** | 🔧 | ✅ Form | ✅ Entities | ✅ |
| **funsd_plus** | 🔧 | ✅ Form | ✅ Entities | ✅ |
| **sroie** | 🔧 | ✅ Receipt | ✅ Entities | ✅ |
| **tablebank** | 🔧 | ✅ Tabular | ✅ Tables | ➖ |
| **pubtabnet** | 🔧 | ✅ Tabular | ✅ Tables | ✅ |
| **nist_sd19** | 🔧 Sparse | ✅ 1-col | ✅ HW | ✅ Linear |
| **signatr6k** | ✅ Sparse | ➖ | ✅ Signature | ➖ |
| **maths_handwriting** | 🔧 | ❌ | ✅ Math/HW | ❌ |
| **im2latex** | 🔧 | ❌ | ✅ Formula | ➖ |
| **mathverse** | 🔧 | ❌ | ✅ Math/Fig | ❌ |
| **multimodal_textbook** | 🔧 | ❌ | ✅ Mixed | ❌ |

---

## Coverage Matrix: Production Method (Axis 3)

| Dataset | Method | Handwriting % | Era |
|---------|--------|---------------|-----|
| **diqa-5000** | ❌ | ❌ | ❌ |
| **live** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **csiq** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **smartdoc-qa** | ❌ | ❌ | ❌ |
| **dibco** | ✅ Historical | ✅ Variable | ✅ Historical |
| **tobacco800** | ✅ Mixed | 🔧 | ✅ Mid-20th |
| **historical_degraded** | ✅ Historical | ✅ Variable | ✅ Historical |
| **rvl_cdip** | ❌ | ❌ | ❌ |
| **doclaynet** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **nist_db2** | ✅ Printed | ✅ 0% | ✅ Recent |
| **nist_sd6** | ✅ Printed | ✅ 0% | ✅ Recent |
| **funsd** | ✅ Printed | 🔧 | ✅ Recent |
| **funsd_plus** | ✅ Printed | 🔧 | ✅ Recent |
| **sroie** | ✅ Thermal | ✅ 0% | ✅ Contemporary |
| **tablebank** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **pubtabnet** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **nist_sd19** | ✅ HW Print | ✅ 100% | ✅ Late 20th |
| **signatr6k** | ✅ HW Cursive | ✅ 100% | ✅ Contemporary |
| **maths_handwriting** | ✅ HW Print | ✅ 100% | ✅ Contemporary |
| **im2latex** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **mathverse** | ✅ Digital | ✅ 0% | ✅ Contemporary |
| **multimodal_textbook** | ✅ Digital | ✅ 0% | ✅ Contemporary |

---

## Coverage Matrix: Capture Method (Axis 4)

| Dataset | Method | Resolution | DPI Category | Confidence |
|---------|--------|------------|--------------|------------|
| **diqa-5000** | ❌ Mixed | 🔧 | 🔧 | ❌ |
| **live** | ✅ Camera Pro | 🔧 | 🔧 | 🔧 |
| **csiq** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **smartdoc-qa** | ✅ Smartphone | 🔧 | 🔧 | ✅ |
| **dibco** | ✅ Scanner | 🔧 | 🔧 | 🔧 |
| **tobacco800** | ✅ Scanner ADF | 🔧 | 🔧 | 🔧 |
| **historical_degraded** | ✅ Scanner | 🔧 | 🔧 | 🔧 |
| **rvl_cdip** | ✅ Scanner ADF | 🔧 | 🔧 | 🔧 |
| **doclaynet** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **nist_db2** | ✅ Scanner | ✅ | ✅ 300 | 🔧 |
| **nist_sd6** | ✅ Scanner | ✅ | ✅ 300 | 🔧 |
| **funsd** | ✅ Scanner ADF | 🔧 | 🔧 | 🔧 |
| **funsd_plus** | ✅ Scanner ADF | 🔧 | 🔧 | 🔧 |
| **sroie** | ✅ Smartphone | 🔧 | 🔧 | 🔧 |
| **tablebank** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **pubtabnet** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **nist_sd19** | ✅ Scanner | ✅ | ✅ 300 | 🔧 |
| **signatr6k** | ✅ Scanner | 🔧 | 🔧 | 🔧 |
| **maths_handwriting** | ✅ Scanner | 🔧 | 🔧 | 🔧 |
| **im2latex** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **mathverse** | ✅ Digital | 🔧 | 🔧 | 🔧 |
| **multimodal_textbook** | ✅ Digital | 🔧 | 🔧 | 🔧 |

---

## Coverage Matrix: Quality/Degradations (Axis 5)

| Dataset | Overall Score | Blur | Noise | Skew | Contrast | Compression | Physical |
|---------|---------------|------|-------|------|----------|-------------|----------|
| **diqa-5000** | ✅ MOS | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **live** | ✅ DMOS | ✅ | ✅ | ➖ | ✅ | ✅ | ➖ |
| **csiq** | ✅ DMOS | ✅ | ✅ | ➖ | ✅ | ✅ | ➖ |
| **smartdoc-qa** | ✅ MOS | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **dibco** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ✅ |
| **tobacco800** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ✅ Real |
| **historical_degraded** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ✅ Real |
| **rvl_cdip** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ❌ |
| **doclaynet** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ➖ |
| **nist_db2** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ➖ |
| **nist_sd6** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ➖ |
| **funsd** | ❌ | 🔧 | ✅ Real | 🔧 | 🔧 | 🔧 | ❌ |
| **funsd_plus** | ❌ | 🔧 | ✅ Real | 🔧 | 🔧 | 🔧 | ❌ |
| **sroie** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ✅ Thermal |
| **tablebank** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ➖ |
| **pubtabnet** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | 🔧 | ➖ |
| **nist_sd19** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ❌ |
| **signatr6k** | ❌ | 🔧 | 🔧 | ➖ | 🔧 | ➖ | ❌ |
| **maths_handwriting** | ❌ | 🔧 | 🔧 | 🔧 | 🔧 | ➖ | ❌ |
| **im2latex** | ❌ | 🔧 | 🔧 | ➖ | 🔧 | 🔧 | ➖ |
| **mathverse** | ❌ | 🔧 | 🔧 | ➖ | 🔧 | 🔧 | ➖ |
| **multimodal_textbook** | ❌ | 🔧 | 🔧 | ➖ | 🔧 | 🔧 | ➖ |

---

## Coverage Matrix: Language/Script (Axis 6)

| Dataset | Primary Lang | Script Type | Multilingual | Secondary Langs |
|---------|--------------|-------------|--------------|-----------------|
| **diqa-5000** | ❌ | ❌ | ❌ | ❌ |
| **live** | ➖ | ➖ | ➖ | ➖ |
| **csiq** | ➖ | ➖ | ➖ | ➖ |
| **smartdoc-qa** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **dibco** | ❌ | ❌ | ❌ | ❌ |
| **tobacco800** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **historical_degraded** | ❌ | ❌ | ❌ | ❌ |
| **rvl_cdip** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **doclaynet** | ✅ EN | ✅ Latin | ❌ | ❌ |
| **nist_db2** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **nist_sd6** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **funsd** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **funsd_plus** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **sroie** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **tablebank** | ✅ EN | ✅ Latin | ❌ | ❌ |
| **pubtabnet** | ✅ EN | ✅ Latin | ❌ | ❌ |
| **nist_sd19** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **signatr6k** | ➖ | ➖ | ➖ | ➖ |
| **maths_handwriting** | ✅ Math | ✅ Latin | ✅ No | ➖ |
| **im2latex** | ✅ Math | ✅ Latin | ✅ No | ➖ |
| **mathverse** | ✅ EN | ✅ Latin | ✅ No | ➖ |
| **multimodal_textbook** | ✅ EN | ✅ Latin | ❌ | ❌ |

---

## Coverage Matrix: Perceptual Scores (Axis 7)

| Dataset | Human MOS | Human DMOS | Human Normalized | LLM Score | LLM Confidence |
|---------|-----------|------------|------------------|-----------|----------------|
| **diqa-5000** | ✅ 1-5 | ➖ | 🔧 | ❌ | ❌ |
| **live** | ➖ | ✅ 0-100 | 🔧 | ❌ | ❌ |
| **csiq** | ➖ | ✅ 0-1 | 🔧 | ❌ | ❌ |
| **smartdoc-qa** | ✅ 1-5 | ➖ | 🔧 | ❌ | ❌ |
| **dibco** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **tobacco800** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **historical_degraded** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **rvl_cdip** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **doclaynet** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **nist_db2** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **nist_sd6** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **funsd** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **funsd_plus** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **sroie** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **tablebank** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **pubtabnet** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **nist_sd19** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **signatr6k** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **maths_handwriting** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **im2latex** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **mathverse** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **multimodal_textbook** | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Coverage Summary

### By Axis

| Axis | Description | ✅ Available | 🔧 Derivable | ❌ Missing |
|------|-------------|--------------|--------------|------------|
| **0** | File Metadata | 3 datasets | 22 datasets | 0 |
| **1** | Domain | 15 datasets | 7 datasets | 0 |
| **2** | Structure | 12 datasets | 10 datasets | 0 |
| **3** | Production | 18 datasets | 4 datasets | 0 |
| **4** | Capture Method | 20 datasets | 2 datasets | 0 |
| **5** | Quality | 4 datasets | 18 datasets | 0 |
| **6** | Language | 16 datasets | 0 datasets | 6 |
| **7** | Perceptual | 4 datasets | 0 datasets | 18 |

### Critical Gaps

1. **Human Perceptual Scores (Axis 7)**: Only 4 datasets have human MOS/DMOS
   - Available: diqa-5000, live, csiq, smartdoc-qa
   - **Action**: LLM scoring needed for remaining 18 datasets

2. **Domain Classification (Axis 1)**: Level 3/4 specificity missing for most
   - **Action**: Automated classifier or manual annotation

3. **Quality/Degradations (Axis 5)**: Per-degradation severity not annotated
   - **Action**: Run classical CV + ML IQA pipeline

4. **Structure (Axis 2)**: Element detection incomplete
   - **Action**: Run layout-lite detection pipeline

---

## Priority Enrichment Order

| Priority | Dataset | Reason | Est. Effort |
|----------|---------|--------|-------------|
| 1 | diqa-5000 | Human MOS ground truth - parse labels | Low |
| 2 | live | Human DMOS ground truth - parse labels | Low |
| 3 | csiq | Human DMOS ground truth - parse labels | Low |
| 4 | smartdoc-qa | Human MOS + device info | Low |
| 5 | tobacco800 | Real degradation - classical CV | Medium |
| 6 | historical_degraded | Real degradation - classical CV | Medium |
| 7 | funsd / funsd_plus | Real scan noise - use existing labels | Low |
| 8 | sroie | Mobile capture proxy - existing labels | Low |
| 9 | doclaynet | Layout labels available - parse COCO | Medium |
| 10 | All others | Run full enrichment pipeline | High |

---

## References

- [detection-taxonomy.md](detection-taxonomy.md) - Taxonomy definitions
- [document-type-taxonomy.md](document-type-taxonomy.md) - Domain hierarchy
- [metadata-versioning-schema.md](metadata-versioning-schema.md) - Schema specification
- [DATASET_CATALOG.md](../DATASET_CATALOG.md) - Dataset inventory

---

**Created**: 2025-12-17 (Phase 7 - Taxonomy Solidification)
**Status**: Initial assessment
**Next Steps**:

1. Run annotate_base_metadata.py to populate 🔧 derivable fields
2. Parse existing labels from source datasets
3. LLM scoring for Axis 7 perceptual scores
**Next Review**: After initial enrichment run
