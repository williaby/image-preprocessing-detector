## OpenLID-v2 - Source Labels

**Dataset**: openlid-v2
**Source**: [HuggingFace: laurievb/OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2)
**License**: MIT

### Label Files Structure

**Note**: This is a text-only corpus streamed from HuggingFace. Local cache structure shown below.

```
~/.cache/synthetic_corpus/openlid_v2/
├── corpus_Latn.json          # Latin script samples (125 languages)
├── corpus_Arab.json          # Arabic script samples (21 languages)
├── corpus_Cyrl.json          # Cyrillic script samples (12 languages)
├── corpus_Deva.json          # Devanagari script samples (10 languages)
├── corpus_Hans.json          # Simplified Chinese samples
├── corpus_Hant.json          # Traditional Chinese samples
├── corpus_Jpan.json          # Japanese script samples
├── corpus_Kore.json          # Korean script samples
├── corpus_Thai.json          # Thai script samples
├── corpus_Grek.json          # Greek script samples
├── corpus_Hebr.json          # Hebrew script samples
├── corpus_Beng.json          # Bengali script samples
├── corpus_Taml.json          # Tamil script samples
├── corpus_Telu.json          # Telugu script samples
├── corpus_Gujr.json          # Gujarati script samples
├── corpus_Knda.json          # Kannada script samples
├── corpus_Mlym.json          # Malayalam script samples
├── corpus_Orya.json          # Odia script samples
├── corpus_Sinh.json          # Sinhala script samples
├── corpus_Guru.json          # Gurmukhi script samples
├── corpus_Khmr.json          # Khmer script samples
├── corpus_Mymr.json          # Burmese script samples
├── corpus_Laoo.json          # Lao script samples
├── corpus_Tibt.json          # Tibetan script samples
├── corpus_Armn.json          # Armenian script samples
├── corpus_Geor.json          # Georgian script samples
└── corpus_Ethi.json          # Ethiopian script samples
```

### Label Format

**Format Type**: HuggingFace streaming dataset (text-only)

**Fields Available**:

- Language code: ✅ Yes (ISO 639-3 + ISO 15924 format: `eng_Latn`)
- Script code: ✅ Yes (embedded in language field)
- Text content: ✅ Yes (sentence-level paragraphs)
- Bounding boxes: ❌ No (text-only corpus)
- OCR text: N/A (source text, not OCR output)
- Quality scores: ❌ No (text corpus, no images)

**Example Label**:

**HuggingFace Dataset Row**:

```json
{
  "language": "eng_Latn",
  "text": "This is a sample sentence in English demonstrating the OpenLID-v2 format."
}
```

**Cached JSON Format** (`corpus_Latn.json`):

```json
{
  "script_code": "Latn",
  "sample_count": 5000,
  "samples": [
    {
      "text": "This is a sample sentence in English.",
      "language_code": "eng_Latn",
      "source": "openlid-v2"
    },
    {
      "text": "Esto es una oración de ejemplo en español.",
      "language_code": "spa_Latn",
      "source": "openlid-v2"
    }
  ]
}
```

### Language Code Format

**Format**: `{ISO 639-3}_{ISO 15924}`

**Examples**:

- `eng_Latn` - English in Latin script
- `arb_Arab` - Standard Arabic in Arabic script
- `cmn_Hans` - Mandarin Chinese in Simplified script
- `hin_Deva` - Hindi in Devanagari script
- `rus_Cyrl` - Russian in Cyrillic script
- `jpn_Jpan` - Japanese in Japanese script mix

**Total Language-Script Pairs**: 201

### Script Distribution

| Script | Languages | Percentage |
|--------|-----------|------------|
| Latin (Latn) | 125 | 62.2% |
| Arabic (Arab) | 21 | 10.4% |
| Cyrillic (Cyrl) | 12 | 6.0% |
| Devanagari (Deva) | 10 | 5.0% |
| Other (33 scripts) | 33 | 16.4% |

### Script-Confusable Language Pairs

Languages written in multiple scripts (valuable for robustness):

| Language | Script Variant 1 | Script Variant 2 |
|----------|-----------------|-----------------|
| Kashmiri | kas_Arab | kas_Deva |
| Acehnese | ace_Arab | ace_Latn |
| Banjar | bjn_Arab | bjn_Latn |
| Central Kanuri | knc_Arab | knc_Latn |

### Split Information

**No explicit train/val/test splits** - streaming corpus

- Total: 116,000,000+ samples across 201 language varieties
- Sampling: 5,000 samples per language (capped in TextCorpusManager)
- Weighted: By language prevalence
- Reproducible: Via seed parameter

**TextCorpusManager Sampling**:

- Max samples per language: 5,000 (configurable)
- Min text length: 10 characters (configurable)
- Max text length: 5,000 characters (configurable)

### Density Categorization (Computed)

**Not in source labels** - computed by `TextCorpusManager`

| Density Level | Character Range | Use Case |
|---------------|----------------|----------|
| MINIMAL | 5-30 chars | Short labels, captions |
| SHORT | 30-150 chars | Sentences, brief paragraphs |
| MEDIUM | 150-500 chars | Multi-sentence paragraphs |
| LONG | 500-1,500 chars | Full paragraphs, short articles |
| DENSE | 1,500-5,000 chars | Multi-paragraph text blocks |

### License & Usage Restrictions

- Commercial use: ✅ Yes (MIT license)
- Research only: ❌ No restrictions
- Attribution required: ✅ Yes
- Redistribution: ✅ Allowed with attribution
- Modification: ✅ Allowed

**Citation**:

```
@misc{openlid-v2,
  title={OpenLID-v2: Open Language Identification Dataset v2},
  author={Vanhoof, Laurie},
  year={2023},
  publisher={HuggingFace},
  url={https://huggingface.co/datasets/laurievb/OpenLID-v2}
}
```

### Integration with Synthetic Generation

**Usage Flow**:

1. Stream or cache text samples by script
2. Filter by text density requirements
3. Sample text with language code
4. Render text into synthetic document images
5. Apply degradations (blur, noise, skew)
6. Generate Layer 2 metadata with language/script labels

**Target Dataset**: `synth-multiscript-250k`

- 250,000 synthetic images
- 27 scripts
- 198 languages (subset of OpenLID-v2's 201)
- Balanced script distribution

### External References

- **OpenLID Paper**: [arXiv:2305.13820](https://arxiv.org/abs/2305.13820)
- **fastText LID**: [fasttext.cc/docs/en/language-identification.html](https://fasttext.cc/docs/en/language-identification.html)
- **ISO 15924 Scripts**: [unicode.org/iso15924/](https://unicode.org/iso15924/)
- **ISO 639-3 Languages**: [iso639-3.sil.org](https://iso639-3.sil.org)
