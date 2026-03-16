---
dataset_id: john11-manuscripts-expansion
version: "1.0"
license: Mixed (CC0, PD, CC-BY-4.0, CC-BY-SA)
commercial_use: true
iqa_profiles:
  - handwriting
  - scanner
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: inferred
---

### John 1:1 Dataset Expansion Investigation

> **Status**: Research Complete | Updated 2026-03-13
> **Purpose**: Evaluate HMML, Vatican, Library of Congress, and alternative sources for dataset expansion
> **Context**: Consensus review (Item 6) identified statistical thinness in Syriac (11) and Georgian (15) OOD scripts; LOC investigation revealed massive public domain Gospel manuscript collections

#### 1. Investigation Summary

| Institution | Scripts | Gospel MSS | Verdict | Reason |
|-------------|---------|-----------|---------|--------|
| **LOC — St. Catherine's Sinai** | Grek, Arab, Syrc, Geor, Cyrs | **152** | **PROCEED** | Public Domain, IIIF, no restrictions |
| **LOC — Jerusalem Patriarchates** | Grek, Armn, Arab, Geor, Cyrs | **85** | **PROCEED** | Public Domain, IIIF, no restrictions |
| HMML / vHMML | Syrc, Geor, Armn, Ethi | N/A | BLOCKED | CC-BY-NC 4.0; partner images prohibit redistribution |
| Vatican (DigiVatLib) | Syrc, Geor | N/A | BLOCKED | Personal/scholarly use only |
| syri.ac aggregator | Syrc | N/A | PARTIAL | Per-institution licenses vary |
| Bodleian Library | Geor, Syrc | N/A | INVESTIGATE | Per-item IIIF license |

#### 2. Library of Congress — St. Catherine's Monastery, Mt. Sinai (PROCEED)

**Collection**: 1,691 digitized manuscripts from the oldest continuously operating library in the world (est. 6th c. AD). Microfilmed in 1949 by Kenneth W. Clark for LOC; now fully digitized with IIIF access.

**License**: **Public Domain** — "This Collection is in the public domain"
**Credit**: "Library of Congress Collection of Manuscripts in St. Catherine's Monastery, Mt. Sinai"
**Access**: IIIF endpoints, no registration, full-resolution images (2000-4000px)
**Format**: Digitized microfilm (B&W); variable quality

##### 2.1 Gospel Manuscripts by Script (154 total "gospel" results)

| Script | ISO 15924 | Four Gospels | Lectionaries | Other Gospel | Total |
|--------|-----------|-------------|-------------|--------------|-------|
| Greek | Grek | 63 | ~5 | ~3 (commentaries) | **~68** |
| Arabic | Arab | 19 | ~20 | ~5 (commentaries) | **~44** |
| Syriac | Syrc | 9 | ~15 | ~3 (partial gospels) | **~27** |
| Georgian | Geor | 5 | 3 | 2 (partial, homilies) | **~10** |
| Old Church Slavonic | Cyrs | 2 | 0 | 1 (commentary) | **~3** |

##### 2.2 Key Syriac Manuscripts (highest expansion priority)

| MS ID | Title | Date | Pages | Notes |
|-------|-------|------|-------|-------|
| Syriac MS 30 | Lives of Holy Women Palimpsest: Four Gospels | **3rd c.** | ~186 | Palimpsest — oldest Syriac Gospel |
| Syriac MS 2 | Four Gospels | 5th c. | 186 | Early Peshitta |
| Syriac MS 11 | Four Gospels | 8th c. | 130 | |
| Syriac MS 135 | Four Gospels | 11th c. | 181 | |
| Syriac MS 145 | Four Gospels | 1188 | 243 | |
| Syriac MS 74 | Four Gospels | 12th c. | 179 | |
| Syriac MS 205 | Four Gospels | 13th c. | 330 | |
| Syriac MS 231 | Four Gospels | 12th c. | 345 | |
| Syriac MS 272 | Four Gospels | 1296 | 202 | |
| Syriac MS 159 | Gospels (Matthew, John) | 1260 | — | Contains John directly |
| Syriac MS 259 | Gospels (Luke and John) | 12th c. | — | Contains John directly |
| + 16 Lectionaries | Gospel readings | 6th-13th c. | — | May include John 1:1 pericope |

**Yield estimate**: 9 Four Gospels + 2 partial (containing John) = **11 definite** John 1:1 images; lectionaries may add 5-10 more. Current dataset has 11 Syriac → potential **22-32 Syriac total**.

##### 2.3 Key Georgian Manuscripts

| MS ID | Title | Date | Pages |
|-------|-------|------|-------|
| Georgian MS 15 | Four Gospels | 978 | 301 |
| Georgian MS 16 | Four Gospels | 9th c. | 338 |
| Georgian MS 19 | Four Gospels | 1074 | 296 |
| Georgian MS 30 | Four Gospels | 9th c. | 166 |
| Georgian MS 81 | Four Gospels | 12th c. | 277 |
| Georgian MS 38 | Gospels (Luke and John) | 979 | — |
| + 3 Lectionaries | Gospel readings | 9th-12th c. | — |

**Yield estimate**: 5 Four Gospels + 1 partial = **6 definite** John 1:1 images. Current dataset has 15 Georgian → potential **21-24 Georgian total**.

##### 2.4 Old Church Slavonic Manuscripts

| MS ID | Title | Date | Pages |
|-------|-------|------|-------|
| Slavonic MS 1 | Four Gospels [Chetveroevangelie] | Unknown | — |
| Slavonic MS 3 | Four Gospels [Chetveroevangelie] | Unknown | — |

**Yield estimate**: 2 definite John 1:1 images. Current dataset has 25 Cyrs.

#### 3. Library of Congress — Jerusalem Patriarchates (PROCEED)

**Collection**: 998 manuscripts from Greek Patriarchate + 32 from Armenian Patriarchate. Microfilmed by LOC; digitized. Covers 11 languages.

**License**: **Public Domain**
**Credit**: "Library of Congress Collection of Manuscripts in the Greek/Armenian Patriarchate of Jerusalem"
**Access**: Same IIIF infrastructure as St. Catherine's collection

##### 3.1 Gospel Manuscripts by Script (85 total gospel results)

| Script | ISO 15924 | Four Gospels | Other Gospel | Total |
|--------|-----------|-------------|--------------|-------|
| Greek | Grek | ~40 | ~3 | **~43** |
| **Armenian** | **Armn** | **21** | 0 | **21** |
| Arabic | Arab | 8 | 1 | **9** |
| Georgian | Geor | 7 | 0 | **7** |
| Old Church Slavonic | Cyrs | 5 | 0 | **5** |

##### 3.2 Key Armenian Manuscripts (new script source!)

| MS ID | Title | Date | Pages (ft of film) |
|-------|-------|------|-----|
| Armenian 1924 | Four Gospels | 1064 | 47 ft |
| Armenian 2555 | Four Gospels | 11th c. | 41 ft |
| Armenian 2556 | "King Gagek" Gospels | 11th c. | 80 ft |
| Armenian 2562 | Four Gospels | ca. 11th c. | 38 ft |
| Armenian 251 | Four Gospels | 1260 | 43 ft |
| Armenian 1941 | Four Gospels | 1264 | 46 ft |
| Armenian 1956 | Four Gospels | 1265 | 41 ft |
| Armenian 2563 | "Queen Keran" Gospels | 1272 | 86 ft |
| Armenian 1796 | Four Gospels | 1287 | 37 ft |
| Armenian 1949 | Four Gospels | 1312 | 40 ft |
| Armenian 1950 | Four Gospels | 1316 | 51 ft |
| Armenian 2360 | Four Gospels | 1331 | 37 ft |
| Armenian 2649 | "The Miracle Gospels" | 1332 | 43 ft |
| Armenian 1973 | Four Gospels | 1346 | 25 ft |
| Armenian 2650 | Four Gospels | 1424 | 31 ft |
| Armenian 1944 | Four Gospels | 1589 | 46 ft |
| Armenian 1938 | Four Gospels | 1611 | 41 ft |
| Armenian 2625 | Four Gospels | 1612 | 23 ft |
| Armenian 2660 | Four Gospels | 1262 | 42 ft |
| Armenian 2568 | "Prince Vassak" Gospels | 13th c. | 55 ft |
| Armenian 1935 | Four Gospels | 1746 | 24 ft |

**Yield estimate**: **21 definite** John 1:1 images. Current dataset has 80 Armenian (Walters, Met, Wikimedia) → potential **101 Armenian total**. These include famous illuminated manuscripts ("King Gagek", "Queen Keran", "Miracle Gospels").

##### 3.3 Key Georgian Manuscripts (Jerusalem)

| MS ID | Title | Date | Pages (ft) |
|-------|-------|------|-----|
| Georgian 49 | Four Gospels | 11th c. | 44 ft |
| Georgian 93 | Four Gospels | 13th-15th c. | 29 ft |
| Georgian 102 | Four Gospels | 12th-14th c. | 36 ft |
| Georgian 103 | Four Gospels | 12th-14th c. | 27 ft |
| Georgian 122 | Four Gospels | 13th-14th c. | 32 ft |
| Georgian 153 | Four Gospels | 12th c. | 17 ft |
| Georgian 160 | Four Gospels | 17th-18th c. | 45 ft |

**Yield estimate**: **7 definite** John 1:1 images. Combined with Sinai collection (6), total LOC Georgian = **13 new images**. Current dataset 15 → potential **28 Georgian total**.

##### 3.4 Slavonic Manuscripts (Jerusalem)

| MS ID | Title | Date |
|-------|-------|------|
| Slavonic Abraam 1 | Four Gospels | 1665 |
| Slavonic Abraam 2 | Four Gospels | 16th c. |
| Slavonic Abraam 3 | Four Gospels | 13th c. |
| Slavonic Abraam 4 | Four Gospels | 15th c. |
| Slavonic 2 | Four Gospels | 1532 |

**Yield estimate**: **5 definite** John 1:1 images. Current dataset has 25 Cyrs → potential **32 Cyrs total**.

#### 4. Combined LOC Expansion Potential

| Script | Current | LOC Sinai | LOC Jerusalem | New Total | Change |
|--------|--------:|----------:|--------------:|----------:|--------|
| **Syriac** (OOD) | 11 | **11-21** | 0 | **22-32** | +100-190% |
| **Georgian** (OOD) | 15 | **6** | **7** | **28** | +87% |
| **Armenian** (OOD) | 80 | 0 | **21** | **101** | +26% |
| Greek | 68 | ~68 | ~43 | **179** | +163% |
| Arabic | 112 | ~44 | ~9 | **165** | +47% |
| Old Ch. Slavonic | 25 | ~2 | ~5 | **32** | +28% |
| **TOTAL** | **514** | **~131** | **~85** | **~730** | +42% |

**Note**: Base dataset was curated from 577 to 514 images (61 junk files quarantined). Each LOC "Gospel manuscript" yields exactly 1 John 1:1 page image (the folio where John's Gospel begins). Lectionaries may or may not include the John 1:1 pericope — requires manual inspection. Estimates above count Four Gospels as definite and lectionaries as possible.

#### 5. HMML / vHMML (BLOCKED)

**Collection scale**: ~75,000 Eastern Christian manuscripts (digital + microfilm), including 14,000+ Syriac manuscripts digitized since 2003.

**Terms of Use** (vhmml.org/terms):

- HMML-owned images: **CC-BY-NC 4.0** (non-commercial only)
- Partner library images: "you agree not to copy or redistribute images from HMML's partner libraries without prior authorization"
- ML training: Not explicitly addressed; CC-BY-NC prohibits commercial applications

**Recommendation**: BLOCKED. Contact <hmml@hmml.org> only if a non-commercial research track is established.

#### 6. Vatican Library / DigiVatLib (BLOCKED)

**Collection scale**: 80,000 codices being digitized; 30,467+ manuscripts digitized. IIIF-based access.

**Relevant collections**:

- Vat.sir (Vaticani Siriaci): 663 signatures (substantial Syriac)
- Borg.sir (Borgiani Siriaci): 178 items (45 digitized)
- Vat.iber (Vaticani Iberici): **3 signatures only** (negligible Georgian)

**Terms**: Free for personal/scholarly use only. Publication requires permission via <rights@vatlib.it>. ML training not addressed.

**Recommendation**: BLOCKED. Terms prohibit dataset assembly.

#### 7. Other Sources

##### 7a. syri.ac Aggregator (PARTIAL)

- 3,700+ digitized Syriac manuscripts from multiple institutions
- Per-institution licenses vary; use as discovery tool to find open-licensed items

##### 7b. Bodleian Library — Georgian Wardrop Collection (INVESTIGATE)

- Per-item IIIF license; check [digital.bodleian.ox.ac.uk/collections/georgian/](https://digital.bodleian.ox.ac.uk/collections/georgian/)

##### 7c. Manchester Digital Collections — Syriac (INVESTIGATE)

- Syriac manuscripts including Peshitta texts; per-item licensing

#### 8. Harvest Strategy

**Phase 1 (Immediate — LOC Collections)**:

1. Build LOC harvest script (IIIF-based, similar to Gallica harvester)
2. For each Four Gospels MS: identify John 1:1 folio (typically ~75% through manuscript)
3. Download single folio per manuscript at full resolution
4. Register in john11 registry with `source_institution: "loc_sinai"` or `"loc_jerusalem"`

**Phase 2 (Medium-term — Lectionary Inspection)**:

1. Download table-of-contents / first pages of Gospel Lectionaries
2. Identify which include John 1:1 pericope (Christmas/Easter reading in many traditions)
3. Harvest confirmed John 1:1 pages

**Technical considerations**:

- LOC IIIF endpoint: `tile.loc.gov/image-services/iiif/service:amed:amedmonastery:{id}`
- Full resolution available at `pct:100` (2000-4000px typical)
- Microfilm digitization = B&W, may have lower quality scores than existing dataset
- B&W microfilm images introduce a new capture_method not well-represented in current dataset

**Harvest pipeline status** (as of 2026-03-13):

- `scripts/harvest_john11_loc.py` — LOC IIIF harvest script implemented with dimension filtering (`MIN_IMAGE_DIMENSION = 200px`) and PIL image validation (corrupt/truncated image rejection)
- `config/john11_loc_manuscript_catalog.json` — 376 entries catalogued (326 definite John 1:1, 36 possible, 8 unknown, 6 unlikely); covers both Sinai (213) and Jerusalem (163) collections. This significantly exceeds the initial estimates of ~216 candidates in Section 10
- `config/john11_loc_folio_estimates.json` — Only 2/326 folio estimates completed; 0 images harvested. Folio identification is the current bottleneck
- LOC output directory exists but contains 0 images — pipeline is early stage

#### 9. Impact on Dataset Composition

**Before LOC expansion** (current):

- 514 images, 10 scripts, 4 institutions (post-curation; 61 junk files quarantined from original 577)
- OOD scripts: Armn(80), Geor(15), Goth(25), Syrc(11) = 131 OOD (25.5%)

**After LOC expansion** (projected):

- ~730 images, 10 scripts, 6 institutions (+LOC Sinai, LOC Jerusalem)
- OOD scripts: Armn(101), Geor(28), Goth(25), Syrc(22-32) = 176-186 OOD (24-25%)
- New date range: 3rd-18th century (vs current 4th-19th century)
- New capture method: B&W microfilm digitization (~37% of expanded dataset)
- Syriac achieves statistical adequacy for per-script OOD evaluation (n>=20)
- Georgian approaches adequacy (n=28 with bootstrap CI)

**New known limitations**:

- B&W microfilm images lack color information — quality assessment methodology may need adaptation
- LOC images from 1949 microfilm expedition — compression artifacts from double digitization (film→scan)
- John 1:1 folio identification requires manual or VLM-assisted page finding per manuscript

#### 10. Recommendations

1. **PROCEED immediately** with LOC harvest — both collections are public domain with no barriers
2. **Prioritize Syriac and Georgian** Four Gospels (definite John 1:1 content)
3. **Armenian LOC harvest** strengthens an already-adequate OOD script and adds prestigious illuminated MSS
4. **Greek and Arabic LOC harvest** provides volume but is lower priority (already well-represented)
5. **B&W microfilm** images should be flagged with `capture_method: "microfilm_scan"` and annotated for quality impact
6. **LOC becomes the largest single source** with 326 definite John 1:1 candidates catalogued (up from initial estimate of ~216); actual catalog at `config/john11_loc_manuscript_catalog.json` has 376 total entries across both collections
7. **HMML and Vatican** remain blocked — revisit only if formal research agreements become feasible
