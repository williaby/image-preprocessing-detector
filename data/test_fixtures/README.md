# Test Fixtures

**Purpose**: Small, representative dataset samples for CI/CD testing without requiring full dataset downloads (88+ GB).

**Total Size Target**: < 50 MB (safe for GitHub commits)

**Last Updated**: 2025-11-13

---

## Directory Structure

```
test_fixtures/
├── doclaynet/          # 5-10 representative layout samples
├── tablebank/          # 5-10 table detection samples
├── cocotext/           # 5-10 text detection samples
├── wili_2018/          # 10 language identification samples
├── omnidocbench/       # 5-10 multi-task benchmark samples
└── README.md           # This file
```

**Note**: `synthetic_iqa` fixtures not needed (auto-generated during benchmark runs)

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

**Attribution**: See LICENSE file and dataset source links in [DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md)

---

## Next Steps

- [x] Create `scripts/extract_test_fixtures.py` automated extraction script
- [x] Create `scripts/extract_wili_samples.py` for WiLI-2018 language extraction
- [x] Extract representative samples from doclaynet, tablebank, wili_2018 (< 50 MB total)
- [x] Document specific fixture filenames and characteristics
- [x] Add pytest markers for `requires_full_dataset` and `real_data`
- [x] Create `tests/conftest.py` with fixture paths and markers
- [x] Create `tests/integration/test_real_fixtures.py` with 14 real data tests
- [ ] Extract cocotext fixtures (requires handling nested directory structure)
- [ ] Extract omnidocbench fixtures (requires Apache Arrow format handling)
- [ ] Update CI configuration to use fixtures for integration tests

---

**References**:
- [TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md) - Complete testing strategy
- [DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md) - Full dataset sources
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml) - CI/CD configuration
