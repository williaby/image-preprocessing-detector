## WiLI-2018 - Source Labels

**Dataset**: wili_2018
**Source**: [Zenodo](https://zenodo.org/records/841984) | [HuggingFace](https://huggingface.co/datasets/MartinThoma/wili_2018)
**License**: Apache-2.0

### Label Files Structure

**Note**: This dataset is text-only and NOT integrated into the pipeline. Structure shown for reference.

```
wili_2018/
├── x_train.txt              # Training text paragraphs (one per line)
├── y_train.txt              # Training language labels (one per line)
├── x_test.txt               # Test text paragraphs (one per line)
└── y_test.txt               # Test language labels (one per line)
```

### Label Format

**Format Type**: Plain text files (tab-separated or newline-separated)

**Fields Available**:

- Language code: ✅ Yes (ISO 639-3, 3-letter codes)
- Script code: ❌ No (NOT provided in source)
- Text content: ✅ Yes (Wikipedia paragraphs)
- Bounding boxes: ❌ No (text-only corpus)
- OCR text: N/A (source text, not OCR output)
- Quality scores: ❌ No (no images to assess)
- Document images: ❌ No (text-only corpus)

**Example Labels**:

**x_train.txt** (text paragraphs):

```
The quick brown fox jumps over the lazy dog. This is an English Wikipedia paragraph.
El rápido zorro marrón salta sobre el perro perezoso. Este es un párrafo en español.
Быстрая коричневая лиса прыгает через ленивую собаку. Это абзац на русском языке.
```

**y_train.txt** (language labels):

```
eng
spa
rus
```

**Paired Format**:

- Line N in `x_train.txt` corresponds to line N in `y_train.txt`
- No script information included
- Perfectly balanced: 1,000 samples per language

### Language Code Format

**Format**: ISO 639-3 (3-letter codes)

**Examples**:

- `eng` - English
- `spa` - Spanish
- `rus` - Russian
- `hin` - Hindi
- `ara` - Arabic (no script variant specified)
- `zho` - Chinese (no script variant specified)

**Total Languages**: 235

**Critical Limitation**: No script codes

- Cannot distinguish `cmn_Hans` vs `cmn_Hant` (Simplified vs Traditional Chinese)
- Cannot distinguish `arb_Arab` variants (Egyptian Arabic vs Standard Arabic)
- Requires manual script inference from text content

### Language Distribution

| Category | Languages | Notes |
|----------|-----------|-------|
| High-resource | ~50 | English, Spanish, French, etc. |
| Medium-resource | ~100 | Regional languages with Wikipedia presence |
| Low-resource | ~85 | Endangered and minority languages |

**Perfectly Balanced**: 1,000 paragraphs per language (235,000 total)

### Split Information

**Train/Test Split**:

- Train: ~188,000 paragraphs (80%)
- Test: ~47,000 paragraphs (20%)
- Split provided in separate files

**No validation split** - only train and test

**Sampling Strategy**:

- Random sampling from Wikipedia paragraphs
- Length-normalized (similar paragraph lengths)
- Quality-filtered (no stubs or very short articles)

### Comparison to OpenLID-v2

| Feature | WiLI-2018 | OpenLID-v2 |
|---------|-----------|------------|
| Languages | 235 | 201 |
| Script Codes | ❌ No | ✅ Yes (ISO 15924) |
| Samples | 235K (1K each) | 116M+ (variable) |
| Balance | ✅ Perfect | ⚠️ Needs capping |
| Text Length | Paragraphs | Sentences |
| Integration | ❌ Blocked | ✅ Complete |

**Why Not Used**:

1. ❌ No script codes (inferior to OpenLID-v2)
2. ❌ OpenLID-v2 provides superior integration
3. ❌ No immediate use case for Prepare-Doc

### License & Usage Restrictions

- Commercial use: ✅ Yes (Apache-2.0)
- Research only: ❌ No restrictions
- Attribution required: ✅ Yes
- Redistribution: ✅ Allowed with attribution
- Modification: ✅ Allowed

**Citation**:

```bibtex
@article{thoma2018wili,
  title={The WiLI benchmark dataset for written language identification},
  author={Thoma, Martin},
  journal={arXiv preprint arXiv:1801.07779},
  year={2018}
}
```

### Why This Dataset is Blocked

**From DATASET_PROCESSING_STATUS.md**:
> **Status**: ❌ Text-only
> **Issue**: No visual component (text corpus only)
> **Resolution**: **Cannot use for image training**. Useful for language ID if needed, but not applicable to visual IQA/layout tasks.

**Fundamental Incompatibilities**:

1. ❌ No images - cannot assess visual quality
2. ❌ No script codes - cannot map to visual scripts
3. ❌ No layout - cannot train layout detection
4. ❌ Superseded by OpenLID-v2 - better coverage with script codes

**Prepare-Doc Requirements**:

- Image preprocessing and quality assessment
- Visual layout detection
- Script identification from rendered text
- Document structure analysis

**WiLI-2018 Provides**:

- Text-only paragraphs
- Language labels (no scripts)
- No visual features

**Conclusion**: Incompatible with image-based pipeline

### Potential Future Uses (Not Planned)

**Scenarios Where This Could Be Useful**:

1. **Language ID model training** - Text-based classifier
2. **Script inference validation** - Test language → script mapping
3. **Benchmark comparison** - Compare against OpenLID-v2
4. **Low-resource language coverage** - 235 languages vs OpenLID's 201

**Current Decision**: ❌ Do not integrate

- OpenLID-v2 fully satisfies text corpus needs
- Script codes essential for synthetic generation
- No capacity to process 235 languages without scripts

### External References

- **Paper**: [The WiLI benchmark dataset (arXiv:1801.07779)](https://arxiv.org/abs/1801.07779)
- **Zenodo Archive**: [zenodo.org/records/841984](https://zenodo.org/records/841984)
- **HuggingFace**: [MartinThoma/wili_2018](https://huggingface.co/datasets/MartinThoma/wili_2018)
- **Alternative**: OpenLID-v2 (integrated and preferred)
