#### OpenLID-v2 (Text Corpus for Synthetic Generation)

> **Quick Stats**: 116M+ text samples | 201 language varieties | 27 scripts | Multi-language corpus
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Open Language Identification Dataset v2 |
| **Short Code** | `openlid-v2` |
| **Version** | 2.0 |
| **Maintainer** | Laurie Vanhoof (KU Leuven) |
| **HuggingFace** | [laurievb/OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) |
| **License** | MIT |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Note**: This is a text-only corpus streamed from HuggingFace, not a traditional image dataset.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Text Corpus** | HuggingFace Streaming | 116M+ text samples streamed via API |
| **Cached JSON** | JSON | Optional per-script cache files (27 files) |
| **Metadata** | Inline | Language codes embedded in `language` field |

##### 2.2 Dataset Split Locations

**Split Organization Pattern**: `no_splits` (continuous streaming corpus)

> **Note**: This corpus has no train/val/test splits. Synthetic generator samples dynamically
> with reproducible seeding (5,000 samples per language, capped).

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Language Code** | String | Sample-level | ISO 639-3 + ISO 15924 format (e.g., `eng_Latn`) |
| **Text Content** | String | Sentence-level | Raw text samples for synthetic rendering |

> **Note**: No visual annotations (bounding boxes, layouts, etc.) - text corpus only.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Language-Script Pair** | `language` field | 201 unique language varieties |
| **Text Content** | `text` field | Sentence-level paragraphs |

##### 2.5 Annotation Schema Details

**HuggingFace Dataset Row**:

```json
{
  "language": "eng_Latn",
  "text": "Sample sentence in English demonstrating OpenLID-v2 format."
}
```

**Cached JSON Format** (`corpus_Latn.json`):

```json
{
  "script_code": "Latn",
  "sample_count": 5000,
  "samples": [
    {
      "text": "Sample sentence...",
      "language_code": "eng_Latn",
      "source": "openlid-v2"
    }
  ]
}
```

**Key Fields**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `language` | string | Yes | Format: `{ISO639-3}_{ISO15924}` |
| `text` | string | Yes | Sentence-level text content |

##### 2.6 Parser Potential Summary

| Data Available | Integration Extractable | Priority | Notes |
|----------------|------------------------|----------|-------|
| ✅ Language codes | `language.script_code`, `language.iso_639_1` | High | Via TextCorpusManager |
| ✅ Text content | Rendered into synthetic images | High | Feeds synthetic generator |
| ⚠️ Character count | Computed dynamically | Medium | Not in source, computed |
| ❌ Visual layout | - | N/A | Text corpus only |

**Integration Status**: ✅ Complete via `TextCorpusManager` class (not a traditional parser)

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 116,000,000+ |
| **Languages** | 201 unique language-script pairs |
| **Scripts** | 27 ISO 15924 scripts |
| **Format** | Text (sentence-level) |
| **Language Code Format** | `{ISO 639-3}_{ISO 15924}` (e.g., `eng_Latn`, `arb_Arab`) |

##### 4.1 Split Coverage

> **CRITICAL**: This text corpus has NO explicit train/val/test splits. It is a streaming dataset
> sampled dynamically by the synthetic generator.

| Split | Source Count | Sampling Strategy | Status |
|-------|--------------|-------------------|--------|
| **Streaming** | 116M+ samples | Dynamic sampling with seed | ✅ Available |
| **Per-Language Cap** | 5,000 max | Prevents Latin over-representation | ✅ Configured |
| **Reproducible** | Via seed parameter | Ensures consistent synthetic generation | ✅ Implemented |

**Split Status Legend:**

- ✅ Available - Corpus accessible via streaming API
- ℹ️ N/A - Traditional train/val/test splits not applicable to streaming corpus

> **Note**: The synthetic generator (`synth-multiscript-250k`) that consumes this corpus DOES
> have train/val/test splits. The splits are applied to the generated images, not the source text.

##### 4.3 Text Statistics

> **Source**: [Empirically Derived] from 1,000-sample profiling across 27 scripts
>
> **Availability**: ✅ Available (text corpus primary content)

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | 142 ± 98 | 5 | 5,000 | 78 / 115 / 178 |
| **Word Count** | 24 ± 17 | 1 | 850 | 13 / 20 / 31 |
| **Sentence Count** | 1.8 ± 1.2 | 1 | 10 | 1 / 2 / 2 |

**Text Source**: `dataset_provided` (raw text samples from HuggingFace)

**Density Categorization** (computed by TextCorpusManager):

| Density Level | Character Range | Sample Distribution |
|---------------|-----------------|---------------------|
| MINIMAL | 5-30 chars | 12% |
| SHORT | 30-150 chars | 52% |
| MEDIUM | 150-500 chars | 28% |
| LONG | 500-1,500 chars | 6% |
| DENSE | 1,500-5,000 chars | 2% |

> **Note**: Text statistics are computed from the raw corpus. The synthetic images generated from
> this text may have different characteristics based on rendering parameters (font size, line
> spacing, page dimensions).

##### Language-Script Coverage

| Script | Languages | Example Codes |
|--------|-----------|---------------|
| **Latin (Latn)** | 125 | eng_Latn, spa_Latn, fra_Latn, vie_Latn, tur_Latn |
| **Arabic (Arab)** | 21 | arb_Arab, arz_Arab, pes_Arab, urd_Arab |
| **Cyrillic (Cyrl)** | 12 | rus_Cyrl, ukr_Cyrl, bul_Cyrl, kaz_Cyrl |
| **Devanagari (Deva)** | 10 | hin_Deva, mar_Deva, npi_Deva, san_Deva |
| **Other** | 33 | Various (Bengali, Tamil, Japanese, etc.) |

##### Script-Confusable Pairs

Languages written in multiple scripts (valuable for robustness training):

| Language | Script 1 | Script 2 |
|----------|----------|----------|
| Kashmiri | kas_Arab | kas_Deva |
| Acehnese | ace_Arab | ace_Latn |
| Banjar | bjn_Arab | bjn_Latn |
| Central Kanuri | knc_Arab | knc_Latn |

##### 5.2 Script Taxonomy

> **Purpose**: Document the 27 ISO 15924 scripts covered by this corpus.
>
> **Applicability**: Script detection training, multilingual document generation.

| Script | ISO 15924 | Languages | Sample Density | Notes |
|--------|-----------|-----------|----------------|-------|
| Latin | Latn | 125 | High | Most represented script |
| Arabic | Arab | 21 | Medium | Right-to-left script |
| Cyrillic | Cyrl | 12 | Medium | Slavic languages |
| Devanagari | Deva | 10 | Medium | Hindi, Sanskrit, Marathi |
| Han (Simplified) | Hans | 1 | Low | Mandarin Chinese |
| Han (Traditional) | Hant | 1 | Low | Traditional Chinese |
| Japanese | Jpan | 1 | Low | Mixed script (Hiragana, Katakana, Kanji) |
| Korean | Kore | 1 | Low | Hangul |
| Bengali | Beng | 3 | Low | Indic script family |
| Tamil | Taml | 1 | Low | Dravidian script |
| Telugu | Telu | 1 | Low | Dravidian script |
| Thai | Thai | 1 | Low | Southeast Asian |
| Greek | Grek | 1 | Low | Historic European |
| Hebrew | Hebr | 1 | Low | Right-to-left |
| **Other** | 13 scripts | 20 | Very Low | Gujarati, Kannada, Malayalam, etc. |

**Script Families Present**: Latin, Arabic, Cyrillic, Indic, CJK, Dravidian, Semitic

> **Script-Confusable Pairs**: Kashmiri (Arab/Deva), Acehnese (Arab/Latn), Banjar (Arab/Latn),
> Central Kanuri (Arab/Latn) - valuable for training script detection models that must
> distinguish script from language.

##### Project Usage

- **Path**: `~/.cache/synthetic_corpus/openlid_v2/` (cached locally)
- **Phase(s)**: Phase 10B (Script Detection Training)
- **Purpose**: Text source for synthetic multi-script document generation
- **Sampling**: 5,000 samples per language (capped), weighted by language prevalence
- **Integration**: `src/image_preprocessing_detector/synthetic/corpus.py`

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Integration Class** | `TextCorpusManager` in [`corpus.py`](../../src/image_preprocessing_detector/synthetic/corpus.py) |
| **Integration Status** | ✅ Complete |
| **Parser Status** | ℹ️ Not Applicable (text corpus uses custom integration, not traditional parser) |
| **Layer 1 Fields** | N/A (text corpus does not generate Layer 1 image metadata) |
| **Layer 2 Downstream** | Feeds `synth-multiscript-250k` which receives Layer 2 enrichment |
| **Language Detection** | [`openlid_integration.py`](../../src/image_preprocessing_detector/schema_utils/openlid_integration.py) |

**Integration Methods**:

- `load_from_openlid()` - Streams from HuggingFace dataset
- `load_from_gcs()` - Downloads pre-processed corpus from GCS
- `load_from_cache()` - Loads cached JSON files
- `save_to_cache()` - Saves samples to local JSON
- `get_text_with_language()` - Retrieves text by script and density

**Language Mapping**:

- ✅ ISO 639-3 to ISO 639-1 mapping (201 languages)
- ✅ Script code extraction (27 ISO 15924 scripts)
- ✅ Script-confusable pair handling (4 languages)

> **Note**: This text corpus does NOT undergo traditional image parsing. Instead, it feeds the
> synthetic document generator which produces images that receive standard Layer 2 enrichment.

##### Key Features

- **Language Diversity**: 125 Latin-script languages alone (vs single-language approach)
- **Regional Variants**: Arabic dialects (Egyptian, Moroccan, Levantine), Chinese variants
- **Quality Filtering**: Pre-filtered by OpenLID team for language identification accuracy
- **Sentence-Level**: Appropriate text lengths for document generation

##### External References

- [OpenLID Paper](https://arxiv.org/abs/2305.13820) - Language identification methodology
- [fastText LID](https://fasttext.cc/docs/en/language-identification.html) - Related technology

#### 10. Dataset-Specific Notes

> **CRITICAL**: This is a **text-only corpus**, NOT an image dataset. It serves as the text source
> for synthetic multi-script document generation.

##### 10.1 Text Corpus Characteristics

- **No Images**: This dataset contains zero image files - text samples only
- **HuggingFace Streaming**: Accessed via `datasets` library API, not local files
- **116M+ Samples**: Largest multilingual text corpus in our inventory
- **201 Languages**: More language coverage than any other dataset (by 6x vs next largest)
- **27 Scripts**: Comprehensive script coverage for global document types

##### 10.2 Integration Pattern (Non-Standard)

Unlike image datasets, this corpus does NOT use the standard parser workflow:

**Standard Image Dataset Flow**:

```text
Images → Parser → Layer 1 Metadata → Layer 2 Enrichment
```

**OpenLID-v2 Text Corpus Flow**:

```text
HuggingFace API → TextCorpusManager → Synthetic Generator → synth-multiscript-250k Images
                                                                  ↓
                                                          Layer 2 Enrichment
```

**Key Implementation Files**:

- `src/image_preprocessing_detector/synthetic/corpus.py` - TextCorpusManager class
- `src/image_preprocessing_detector/schema_utils/openlid_integration.py` - Language mappings
- `scripts/poc_openlid_v2.py` - Integration proof of concept

##### 10.3 Caching Strategy

**Three-Tier Caching**:

1. **Local Cache** (fastest): `~/.cache/synthetic_corpus/openlid_v2/` - 27 JSON files (one per script)
2. **GCS Bucket** (fast): `gs://image_detection_b/datasets/synthetic-corpus/` - Backup cache
3. **HuggingFace API** (slow): Streaming download if no cache available

**Cache Size**: ~2.7 GB for 5,000-sample-per-language subset (135K samples total)

##### 10.4 Synthetic Generation Context

This corpus feeds the `synth-multiscript-250k` synthetic dataset (see TRAINING_DATASET_CATALOG.md):

| Synthetic Dataset Attribute | Derived from OpenLID-v2 |
|-----------------------------|------------------------|
| **Text Content** | Raw text samples |
| **Language Labels** | ISO 639-3 codes mapped to 639-1 |
| **Script Labels** | ISO 15924 codes extracted from language field |
| **Text Density** | Character count → 5-level categorization |
| **Sample Diversity** | 198 languages (subset of 201) |

**Sampling Strategy**:

- 5,000 samples per language (prevents Latin over-representation)
- Weighted by language prevalence in real documents
- Reproducible via seed parameter

##### 10.5 Known Limitations (Text Corpus Context)

- **No Visual Characteristics**: Cannot train visual IQA models directly (no images)
- **Sentence-Level Granularity**: Not suitable for document-level context modeling
- **Language Distribution Skew**: 62% Latin-script languages may bias synthetic output
- **Streaming Required**: Initial download takes 2-4 hours for full corpus
- **Script Imbalance**: Some scripts have 100+ languages (Latin), others have 1 (Tamil)

##### 10.6 Usage Best Practices

**DO**:

- ✅ Use for synthetic multi-script document generation
- ✅ Sample with capped per-language limits (5,000 recommended)
- ✅ Use local/GCS cache for faster iteration
- ✅ Apply reproducible seeding for consistent datasets

**DON'T**:

- ❌ Treat as an image dataset (no pixels to process)
- ❌ Attempt traditional parser integration (use TextCorpusManager)
- ❌ Sample unlimited Latin (will dominate synthetic dataset)
- ❌ Skip caching strategy (streaming is 10-50x slower)

##### 10.7 Documentation References

- **Source Label Review**: [openlid-v2_review.md](../datasets/reviews/openlid-v2_review.md)
- **Source Labels Spec**: [openlid-v2_source_labels.md](../datasets/source_labels/openlid-v2_source_labels.md)
- **Integration Code**: `src/image_preprocessing_detector/synthetic/corpus.py`
- **Validation Script**: `scripts/validate_openlid_mlt19.py`
- **POC Script**: `scripts/poc_openlid_v2.py`

---
