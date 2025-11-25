# Test Fixtures

**Purpose**: Small, representative dataset samples for CI/CD testing without requiring full dataset downloads (88+ GB).

**Total Size Target**: < 50 MB (safe for GitHub commits)

**Last Updated**: 2025-11-24

---

## Directory Structure

```
test_fixtures/
├── doclaynet/               # 5 representative layout samples (432 KB)
├── tablebank/               # 5 table detection samples (324 KB)
├── wili_2018/               # 10 language identification samples (52 KB)
├── iqa_samples/             # 6 IQA ground truth samples + labels.json (2.3 MB) ✅ NEW
├── training_validation/     # 5 training validation samples + manifest.json (1.8 MB) ✅ NEW
├── augmentation_input/      # 3 clean baseline samples (728 KB) ✅ NEW
├── layout_samples/          # 4 layout edge case samples + manifest.json (904 KB) ✅ NEW
└── README.md                # This file
```

**Total Size**: 6.5 MB (well under 50 MB GitHub limit)

---

## Selection Criteria

Each fixture set contains **5-10 carefully selected samples** that represent:

1. **Coverage**: Different document types, layouts, quality levels
2. **Edge cases**: Skewed pages, low contrast, blurry text, complex tables
3. **File size**: Smaller files preferred to stay under 50 MB total
4. **License**: Permissively licensed samples safe for GitHub distribution

### doclaynet/

**Purpose**: Test layout detection and page-level IQA

**Selected samples** (5 PDFs):
- Simple text-heavy document
- Document with tables and figures
- Complex multi-column layout
- Skewed/rotated pages
- Low contrast or blurry scans

**Source**: Extracted from `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet/` (40.97 GB)

**License**: CDLA-Permissive-1.0 (DocLayNet dataset)

**Extraction command**:
```bash
# TODO: Run extraction script once created
poetry run python scripts/extract_test_fixtures.py --dataset doclaynet --count 5
```

### tablebank/

**Purpose**: Test table detection and structure recognition

**Selected samples** (5 images):
- Simple table (3-5 columns)
- Complex table (10+ columns, merged cells)
- Rotated table
- Low quality/blurry table
- Table with graphics/images embedded

**Source**: Extracted from `data/benchmarks/tablebank/` (46.38 GB)

**License**: Apache-2.0 (TableBank dataset)

**Extraction command**:
```bash
# TODO: Run extraction script once created
poetry run python scripts/extract_test_fixtures.py --dataset tablebank --count 5
```

### cocotext/

**Purpose**: Test text detection gate and OCR preprocessing

**Selected samples** (5 images):
- Dense text (paragraphs)
- Sparse text (signage, labels)
- Different font sizes/styles
- Handwritten text mixed with printed
- Challenging backgrounds (low contrast)

**Source**: Extracted from `data/benchmarks/cocotext/` (52 MB)

**License**: Creative Commons Attribution 4.0 (COCO dataset)

**Extraction command**:
```bash
# TODO: Run extraction script once created
poetry run python scripts/extract_test_fixtures.py --dataset cocotext --count 5
```

### wili_2018/

**Purpose**: Test language identification (multilingual OCR routing)

**Selected samples** (10 text files):
- English (EN)
- French (FR)
- German (DE)
- Spanish (ES)
- Chinese (ZH)
- Arabic (AR)
- Russian (RU)
- Japanese (JA)
- Korean (KO)
- Hindi (HI)

**Source**: Extracted from `data/benchmarks/wili_2018/` (128 MB)

**License**: Apache-2.0 (WiLI-2018 dataset)

**Extraction command**:
```bash
# TODO: Run extraction script once created
poetry run python scripts/extract_test_fixtures.py --dataset wili_2018 --count 10
```

### omnidocbench/

**Purpose**: Test comprehensive document understanding (Phase 3)

**Selected samples** (5 images):
- Financial document (tables, text, numbers)
- Scientific paper (formulas, figures, citations)
- Invoice/receipt (structured data extraction)
- Form with handwriting
- Mixed media document (images + text)

**Source**: Extracted from `data/benchmarks/omnidocbench/` (1.16 GB)

**License**: MIT (OmniDocBench dataset)

**Extraction command**:
```bash
# TODO: Run extraction script once created
poetry run python scripts/extract_test_fixtures.py --dataset omnidocbench --count 5
```

---

## Usage in Tests

### Unit Tests

Use specific fixtures for targeted testing:

```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "test_fixtures"

def test_skew_detection():
    """Test skew detection on known skewed sample."""
    skewed_pdf = FIXTURES_DIR / "doclaynet" / "skewed_sample.pdf"
    result = detect_skew(skewed_pdf)
    assert result.angle > 2.0  # Known skew angle
```

### Integration Tests

Use full fixture sets for pipeline testing:

```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "test_fixtures"

def test_full_pipeline_doclaynet_fixtures():
    """Test full pipeline on doclaynet fixtures."""
    for pdf in (FIXTURES_DIR / "doclaynet").glob("*.pdf"):
        result = process_document(pdf)
        assert result.status == "success"
        assert len(result.pages) > 0
```

### CI/CD Integration

GitHub Actions automatically uses test fixtures:

```yaml
# .github/workflows/ci.yml
- name: Run tests with fixtures
  run: |
    poetry run pytest -v -m "not requires_full_dataset"
  # Automatically uses data/test_fixtures/
```

**Test markers**:
```python
@pytest.mark.requires_full_dataset
def test_full_benchmark():
    """Skipped in CI - requires full datasets (88+ GB)."""
    pass

def test_with_fixtures():
    """Runs in CI - uses test_fixtures only."""
    pass
```

---

## Updating Fixtures

### When to Update

- **New detection capabilities**: Add edge cases for new algorithms
- **Production bugs discovered**: Add failing samples that exposed bugs
- **Phase transitions**: Add Phase 2/3 specific document types
- **Dataset updates**: Refresh fixtures when upstream datasets update

### How to Update

1. **Extract new samples**:
   ```bash
   poetry run python scripts/extract_test_fixtures.py \
     --dataset doclaynet \
     --count 5 \
     --criteria "skewed,low_contrast,complex_layout"
   ```

2. **Verify size constraint**:
   ```bash
   du -sh data/test_fixtures/
   # Should be < 50 MB
   ```

3. **Commit to GitHub**:
   ```bash
   git add data/test_fixtures/
   git commit -m "test: Update doclaynet fixtures with complex layout samples"
   git push
   ```

---

## Size Monitoring

**Last Updated**: 2025-11-13

Current size breakdown:

```bash
# Check current sizes
$ du -sh data/test_fixtures/*/

# Actual sizes:
doclaynet/      432K (5 PDFs)
tablebank/      324K (5 images)
wili_2018/      52K (10 text files)
cocotext/       4K (empty - not extracted)
omnidocbench/   4K (empty - not extracted)
TOTAL:          828K (0.8 MB - well under 50 MB target)
```

### Extracted Fixtures Inventory

**doclaynet/** (5 PDFs, 432K total):
- `simple_text_1.pdf` (18K) - Simple text-heavy document
- `tables_figures_2.pdf` (29K) - Document with tables and figures
- `multi_column_3.pdf` (50K) - Multi-column layout
- `skewed_4.pdf` (234K) - Skewed/rotated pages
- `low_contrast_5.pdf` (84K) - Low contrast scans

**tablebank/** (5 images, 324K total):
- `simple_table_1.png` (4.9K) - Simple 3-5 column table
- `complex_table_2.png` (44K) - Complex table with merged cells
- `rotated_3.jpg` (74K) - Rotated table
- `low_quality_4.jpg` (133K) - Low quality/blurry table
- `embedded_graphics_5.jpg` (51K) - Table with embedded graphics

**wili_2018/** (10 text files, 52K total):
- `eng_eng.txt` (446 bytes) - English sample
- `fra_fra.txt` (168 bytes) - French sample
- `deu_deu.txt` (496 bytes) - German sample
- `spa_spa.txt` (193 bytes) - Spanish sample
- `zho_zho.txt` (576 bytes) - Chinese sample
- `ara_ara.txt` (1.6K) - Arabic sample
- `rus_rus.txt` (729 bytes) - Russian sample
- `jpn_jpn.txt` (675 bytes) - Japanese sample
- `kor_kor.txt` (394 bytes) - Korean sample
- `hin_hin.txt` (2.1K) - Hindi sample

**cocotext/** - Not yet extracted (dataset structure requires special handling)

**omnidocbench/** - Not yet extracted (Arrow format requires special handling)

**iqa_samples/** - Planned for Phase 2 Week 3 (~2 MB total):
- `live/`: 3-5 LIVE dataset extracts with ground-truth quality scores (DMOS)
  - Reference image (clean, DMOS=0.0)
  - JPEG compression sample (DMOS~25)
  - Gaussian blur sample (DMOS~45)
  - White noise sample (DMOS~38)
  - Low contrast sample (DMOS~52)
- `synthetic/`: 2-3 generated variants for edge case testing
  - Extreme blur (edge case detection)
  - Combined defects (blur + noise)
  - Rotated/skewed document (orientation testing)
- `labels.json`: Ground-truth quality scores and defect labels

See [tmp_cleanup/.tmp-test-fixtures-iqa-requirements-20251113.md](../../tmp_cleanup/.tmp-test-fixtures-iqa-requirements-20251113.md) for detailed requirements analysis.
```

### Projected Size After Phase 2

```bash
# Projected total after IQA fixtures added (Week 3):
doclaynet/      432K (5 PDFs)
tablebank/      324K (5 images)
wili_2018/      52K (10 text files)
iqa_samples/    2.0M (8 images + labels.json)  # NEW in Week 3
  ├── live/     1.5M (5 LIVE extracts)
  └── synthetic/ 500K (3 generated variants)
TOTAL:          3.0M (well under 50 MB target)
```

---

## License Compliance

All fixtures are extracted from permissively licensed datasets:

| Dataset | License | Commercial Use | Redistribution |
|---------|---------|----------------|----------------|
| doclaynet | CDLA-Permissive-1.0 | ✅ Yes | ✅ Yes |
| tablebank | Apache-2.0 | ✅ Yes | ✅ Yes |
| cocotext | CC BY 4.0 | ✅ Yes | ✅ Yes (with attribution) |
| wili_2018 | Apache-2.0 | ✅ Yes | ✅ Yes |
| omnidocbench | MIT | ✅ Yes | ✅ Yes |
| **iqa_samples (LIVE)** | Academic/Research | ✅ Yes (with citation) | ⚠️ Research use only |

**Attribution**: See LICENSE file and dataset source links in [DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md)

**IQA Fixtures Citation** (required for LIVE dataset):
```
Sheikh, H. R., Seshadrinathan, K., Moorthy, A. K., Wang, Z., Bovik, A. C., & Cormack, L. K. (2006).
A statistical evaluation of recent full reference image quality assessment algorithms.
IEEE Transactions on Image Processing, 15(11), 3440-3451.
```

---

## Newly Added Fixtures (2025-11-24)

### iqa_samples/ ✅ NEW

**Purpose**: IQA model validation with ground truth quality labels

**Selected samples** (6 images + labels.json, 2.3 MB total):
- `reference_clean.png` (206 KB) - Pristine reference, all defects = 0.0
- `gaussian_blur_high.png` (316 KB) - High blur (1.0) + artifacts (1.0)
- `white_noise_high.png` (605 KB) - High noise (1.0) + skew (1.0)
- `contrast_low.png` (449 KB) - Low contrast/poor illumination (1.0)
- `jpeg_artifacts_high.png` (237 KB) - High JPEG compression artifacts (1.0)
- `combined_blur_noise.png` (509 KB) - Combined defects: blur, noise, skew (all 1.0)
- `labels.json` (1.3 KB) - Ground truth DMOS and defect scores

**Source**: iqa_phase2_100k training dataset (synthetic/genalog-generated)

**License**: Derived from synthetic data (permissive)

**Usage**: Validate ML IQA model predictions against known ground truth labels

### training_validation/ ✅ NEW

**Purpose**: Training pipeline validation samples

**Selected samples** (5 images + manifest.json, 1.8 MB total):
- `sample_000000.jpg` (406 KB) - Clean, high-quality baseline
- `sample_000001.jpg` (261 KB) - Clean, high-quality baseline
- `sample_000009.jpg` (318 KB) - Clean, high-quality baseline
- `sample_000002.jpg` (449 KB) - Moderate degradation (illumination=1.0)
- `sample_000003.jpg` (316 KB) - Severe degradation (blur=1.0, artifacts=1.0)
- `manifest.json` (1.8 KB) - Sample metadata and quality labels

**Source**: iqa_phase2_100k validation split

**License**: Derived from synthetic data (permissive)

**Usage**: Test training data loading and validation pipeline

### augmentation_input/ ✅ NEW

**Purpose**: Baseline samples for augmentation/degradation testing

**Selected samples** (3 images, 728 KB total):
- `clean_text_page.jpg` (406 KB) - Clean mixed layout document
- `clean_table_page.jpg` (206 KB) - Clean table document
- `clean_form_page.jpg` (112 KB) - Clean form document

**Source**: iqa_phase2_100k dataset (pristine samples)

**License**: Derived from synthetic data (permissive)

**Usage**: Test genalog augmentation pipeline with clean baseline inputs

### layout_samples/ ✅ NEW

**Purpose**: Layout-lite edge case detection testing

**Selected samples** (4 files + manifest.json, 904 KB total):
- `dense_math_page4.pdf` (220 KB) - Scientific paper with dense equations, PDEs, matrices
  - **Source**: arXiv 2409.13432 (CC-BY-4.0)
  - **License**: CC-BY-4.0 with attribution
- `watermarked_document.pdf` (51 KB) - Multi-column doc with "CONFIDENTIAL" watermark
  - **Source**: Synthetic (from doclaynet/multi_column_3.pdf)
  - **License**: Derived from CDLA-Permissive-1.0
- `colorful_background.jpg` (443 KB) - Text doc with blue-to-purple gradient background
  - **Source**: Synthetic (gradient overlay on clean_text_page.jpg)
  - **License**: Derived from synthetic data
- `handwriting_mixed.jpg` (177 KB) - Table doc with handwritten annotations
  - **Source**: Synthetic (IAM handwriting composited over clean_table_page.jpg)
  - **License**: Derived from IAM (academic use) + synthetic data
- `manifest.json` (12 KB) - Sample metadata and expected attributes

**Usage**: Test layout-lite classification for watermarks, colorful backgrounds, dense math, and handwriting detection

**Attribution Required**:
```
Dense math sample from: "Dense cell-by-cell systems of PDEs: approximation,
spectral analysis, and preconditioning" (arXiv:2409.13432) - CC-BY-4.0
```

---

## Next Steps

### Phase 1 (Completed)
- [x] Create `scripts/extract_test_fixtures.py` automated extraction script
- [x] Create `scripts/extract_wili_samples.py` for WiLI-2018 language extraction
- [x] Extract representative samples from doclaynet, tablebank, wili_2018 (< 50 MB total)
- [x] Document specific fixture filenames and characteristics
- [x] Add pytest markers for `requires_full_dataset` and `real_data`
- [x] Create `tests/conftest.py` with fixture paths and markers
- [x] Create `tests/integration/test_real_fixtures.py` with 14 real data tests

### Phase 2 Week 3 (Planned - IQA Fixtures)
- [ ] Download LIVE, CSIQ, LIVE Challenge datasets (~5 GB)
- [ ] Extract 5 LIVE samples with ground-truth DMOS scores (~1.5 MB)
- [ ] Generate 3 synthetic IQA variants (extreme blur, combined defects, orientation) (~0.5 MB)
- [ ] Create `iqa_samples/labels.json` with quality scores
- [ ] Create `scripts/extract_iqa_fixtures.py` extraction script
- [ ] Add IQA integration tests to `tests/integration/test_real_fixtures.py`
- [ ] Update total fixtures size: 828 KB → 3.0 MB (still well under 50 MB)

### Future Phases
- [ ] Extract cocotext fixtures (requires handling nested directory structure)
- [ ] Extract omnidocbench fixtures (requires Apache Arrow format handling)
- [ ] Update CI configuration to use fixtures for integration tests

---

**References**:
- [TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md) - Complete testing strategy
- [DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md) - Full dataset sources
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml) - CI/CD configuration
