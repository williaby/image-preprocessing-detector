# Dataset Upload & Processing Status

Generated: 2025-01-29

## Datasets in GCS (Ready for Processing)

| Dataset | GCS Path | Est. Size | Status |
|---------|----------|-----------|--------|
| **doclaynet** | `datasets/doclaynet/` | ~41 GB | ✅ Ready |
| **pubtabnet** | `datasets/pubtabnet/` | ~5 GB | ✅ Ready |
| **tablebank** | `datasets/tablebank/` | ~15 GB | ✅ Ready |
| **fintabnet** | `datasets/fintabnet/` | ~13 GB | ✅ Ready |
| **funsd** | `datasets/funsd/` | ~100 MB | ✅ Ready |
| **nist_db2** | `datasets/nist_db2/` | ~900 MB | ✅ Ready |
| **signatr6k** | `datasets/signatr6k/` | ~2 GB | ✅ Ready |
| **ohr_bench** | `datasets/ohr_bench/` | ~1.7 GB | ✅ Ready (benchmark) |
| **omnidocbench** | `datasets/omnidocbench/` | ~1.2 GB | ✅ Ready (benchmark) |
| **cocotext** | `datasets/cocotext/` | ~50 MB | ✅ Ready |
| **wili_2018** | `datasets/wili_2018/` | text only | ⚠️ Text-only (no images) |

## Datasets Needing Upload (Tier 1 - High Priority)

| Dataset | Local Path | Est. Size | Priority |
|---------|------------|-----------|----------|
| **rvl_cdip** | `documents/rvl_cdip/` | ~37 GB | P1 - Large doc set |
| **mathverse** | `formulas/mathverse/` | ~2 GB | P1 - Formulas |
| **multimodal_textbook** | `educational/multimodal_textbook/` | ~1 GB | P1 - Educational |
| **nist_sd6** | `forms/nist_sd6/` | ~1 GB | P1 - Forms |
| **sroie** | `forms/sroie_icdar2019/` | ~400 MB | P1 - Receipts (ICDAR 2019, 973 images) |
| **funsd_plus** | `forms/funsd_plus/` | ~200 MB | P1 - Forms |
| **tobacco800** | `degraded/tobacco800/` | ~500 MB | P2 - Degraded |
| **bhutan_financial** | `documents/bhutan_financial/` | ~50 MB | P2 - Government |

## Datasets Needing Upload (Tier 2/3 - Multilingual)

| Dataset | Local Path | Est. Size | Priority |
|---------|------------|-----------|----------|
| **mlt19** | `language/mlt19/` | ~14 GB | P2 - 10 languages |
| **cc_ocr** | `language/cc_ocr_extracted/` | ~2 GB | P2 - CJK |
| **mdiw13** | `language/mdiw13/` | ~1 GB | P2 - 13 scripts |
| **arabic_docs_ocr** | `language/arabic_docs_ocr/` | ~10 GB | P3 - Arabic |
| **hindi_ocr_synthetic** | `language/hindi_ocr_synthetic/` | ~5 GB | P3 - Devanagari |
| **TibHCR** | `language/TibHCR/` | ~2 GB | P3 - Tibetan |
| **SIW-13** | `language/SIW-13/` | ~1 GB | P3 - Scene text |
| **cvsi** | `language/cvsi/` | ~1 GB | P3 - Video frames |
| **pucit_ohul** | `handwriting/Pucit/` | ~5 GB | P3 - Urdu handwriting |

## Not Suitable for Text Extraction

| Dataset | Reason |
|---------|--------|
| hasyv2 | 32x32 symbol crops |
| nist_sd19 | Character-level crops |
| im2latex | Isolated formula renders |
| dzongkha_digits | Digit-only |

## Processing Order

1. **Phase 1**: Process GCS-ready Tier 1 (doclaynet, pubtabnet, tablebank, fintabnet, funsd, nist_db2)
2. **Phase 2**: Upload & process remaining Tier 1 (rvl_cdip, mathverse, sroie, etc.)
3. **Phase 3**: Upload & process Tier 2 multilingual (mlt19, cc_ocr, mdiw13)
4. **Phase 4**: Tier 3 rare scripts (Modal processing)
