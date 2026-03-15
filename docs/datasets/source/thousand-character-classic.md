---
dataset_id: thousand-character-classic
version: "1.0"
license: Mixed (CC0, CC-BY-4.0, PD, KOGL)
commercial_use: true
iqa_profiles:
  - scanner
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: partial
---

### Thousand Character Classic (千字文)

> **Quick Stats**: 1,248 images | 9 institutions | Historical CJK calligraphy | 12 script styles, 3 writing traditions
>
> **License**: Mixed per-image (CC0, CC BY 4.0, Public Domain, NDL Open, KOGL) | **Commercial Use**: Mostly yes (per-image tracking)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Thousand Character Classic Calligraphy Collection |
| **Version** | 2.0 |
| **Release Date** | 2026 |
| **Maintainer** | Project A team (assembled from 20+ institutions) |
| **Paper** | N/A (assembled dataset from public collections) |
| **Repository** | N/A |
| **License** | Mixed: CC0, CC BY 4.0, Public Domain, KOGL (tracked per-image in registry) |
| **Local Storage** | `E:\image_detection\01_base_data\calligraphy\thousand-character-classic\` |
| **Documentation Status** | Complete |

**Dataset Description**: A curated collection of historical CJK calligraphy images depicting the Thousand Character Classic (千字文), a Chinese poem of exactly 1,000 unique characters used as a penmanship primer for 1,400+ years. The collection spans the Sui dynasty (6th century) to the Qing dynasty (19th century), covering 6 major Chinese script styles (kaishu, caoshu, xingshu, zhuanshu, lishu, zhangcao) across 3 CJK writing traditions (Chinese, Korean, Japanese).

**Unique value**: Ground truth text content at tier_0_exact confidence (1.0) — every image depicts a known fixed literary text, enabling text_content L2 fields without OCR.

#### 2. Source Data Inventory

> **Purpose**: Documents what the original sources provide, enabling harvest script development.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG/PNG/TIFF | Calligraphy scans and photographs from 20+ institutions |
| **Catalog** | YAML | 74-item structured catalog (`config/thousand_character_classic_catalog.yaml`) |
| **Ground Truth Text** | YAML | Complete 1,000-character text + English translation (`config/thousand_character_classic_text.yaml`) |

##### 2.2 Source Institutions

| Source | Images | License | Acquisition Method |
|--------|-------:|---------|-------------------|
| **NDL Japan** | 249 | NDL Open | IIIF Manifests |
| **LOC (World Digital Library)** | 245 | Public Domain | LOC WDL IIIF |
| **Waseda University** | 239 | Open Access | Waseda Kotenseki IIIF |
| **NPM Taipei** | 202 | CC BY 4.0 | NPM Digital Archive API |
| **Kyoto University** | 146 | Open Access | Kyoto U Rare Books IIIF |
| **Wikimedia Commons** | 140 | Public Domain / CC BY | MediaWiki API |
| **Met Museum** | 23 | CC0 | Met Open Access API |
| **National Museum of Korea** | 3 | KOGL Type 1 | NMK Open Access |
| **Smithsonian (Freer Gallery)** | 1 | Public Domain | Open Access download |
| **Internet Archive** | 0 | Public Domain | Not harvested |

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Script Style** | Catalog YAML | Image-level | Calligraphic script style (kaishu, caoshu, etc.) |
| **Calligrapher** | Catalog YAML | Image-level | Artist name, CJK name, dates |
| **Dynasty/Period** | Catalog YAML | Image-level | Historical dynasty and century |
| **Ground Truth Text** | Text YAML | Dataset-level | Complete 1,000-character Chinese text + English translation |
| **Writing Tradition** | Catalog YAML | Image-level | Chinese, Korean, or Japanese |

##### 2.4 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Expert catalog (art-historical attribution) |
| **Provenance Tier** | Tier 0 (exact — known literary text) for text_content; Tier 1 (annotation) for script style/calligrapher |
| **Text Source** | The Thousand Character Classic is a fixed text of 1,000 characters (998 unique, 2 historical duplicates) |
| **GT Label Coverage** | 100% (all images depict sections of the same known text) |

#### 3. Project Usage

##### 3a. Harvest & Enrichment Scripts

- **Harvest**: [`scripts/harvest_thousand_character_classic.py`](../../../scripts/harvest_thousand_character_classic.py) | Sub-commands: `harvest-wikimedia`, `harvest-met`, `harvest-iiif`, `harvest-npm-taipei`, `harvest-internet-archive`, `stats`
- **Enrichment**: [`scripts/enrich_thousand_character_classic.py`](../../../scripts/enrich_thousand_character_classic.py) | Sub-commands: `enrich`, `validate`, `stats`

##### 3b. Training Head Contributions

| Head ID | Head Name | Contribution | Notes |
|---------|-----------|--------------|-------|
| SIG-G2-1 | script_cls | ✅ Primary | Hant/Hani calligraphic diversity (6 styles), Kore, Jpan |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | 100% handwritten content |
| SIG-G4-2 | handwriting_legibility_cls | ✅ Primary | Script-style-to-legibility mapping (kaishu=GOOD, kuangcao=POOR) |
| SIG-G4-4 | presence_reg | ✅ Primary | DOMINANT presence (score ≥0.95) |
| SIG-G4-5 | legibility_reg | ✅ Primary | Continuous score from script style mapping |
| SIG-G5-2 | shadow_reg | ➖ Negatives | Historical scans, minimal shadow |
| SIG-G5-3 | warping_reg | ➖ Negatives | Flat museum scans |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/calligraphy/thousand-character-classic/` | ✅ Complete | 1,248 images across 9 source subfolders |
| **Registry** | `metadata_registry/thousand_character_classic_registry.jsonl` | ✅ Complete | 1,248 entries, SHA256 deduped |
| **L2 Metadata** | `metadata_registry/json/thousand-character-classic/` | ✅ Complete | 1,449 per-image L2 v2 JSON |
| **Extended Sidecar** | `metadata_registry/thousand_character_classic_extended.jsonl` | ✅ Complete | 1,449 art-historical metadata entries |
| **Catalog Config** | `config/thousand_character_classic_catalog.yaml` | ✅ Complete | 74 items |
| **Ground Truth Text** | `config/thousand_character_classic_text.yaml` | ✅ Complete | 1,000 chars + translation |
| **Quarantine** | `01_base_data/calligraphy/thousand-character-classic/_quarantined/` | ✅ Complete | 11 removed files (9 Korean web junk, 2 cross-source duplicates) |

#### 4. Dataset Statistics

##### 4.1 Dataset Coverage

| Dimension | Count | Details |
|-----------|------:|---------|
| **Total Images** | 1,248 | Across 9 source institutions (expanded from initial 391 harvest of NDL+Wikimedia+Met) |
| **Catalog Items** | 74 | Spanning 6th-19th century |
| **Calligraphers** | ~40 | Named artists + anonymous works |
| **Script Styles** | 12 | kaishu, caoshu, xingshu, zhuanshu, lishu, zhangcao, kuangcao, xingcao, xiaokai, xingkai, haeseo, choseo |
| **Dynasties** | 8+ | Sui, Tang, Song, Yuan, Ming, Qing, Joseon, Edo |
| **Writing Traditions** | 3 | Chinese, Korean, Japanese |
| **Source Institutions** | 9 | NDL, LOC WDL, Waseda, NPM Taipei, Kyoto U, Wikimedia, Met, NMK, Smithsonian |

##### 4.2 Script Style Distribution

| Script Style | CJK | Catalog Count | Legibility Mapping |
|--------------|-----|-------------:|-------------------|
| kaishu (楷書) | Regular | 15 | GOOD (0.75) |
| caoshu (草書) | Cursive | 12 | FAIR (0.45) |
| xingshu (行書) | Running | 8 | GOOD (0.65) |
| zhuanshu (篆書) | Seal | 4 | POOR (0.30) |
| lishu (隸書) | Clerical | 3 | GOOD (0.70) |
| zhangcao (章草) | Draft cursive | 2 | FAIR (0.50) |
| kuangcao (狂草) | Wild cursive | 3 | POOR (0.25) |
| mixed | Multiple | 10 | varies |
| Other (xingcao, xiaokai, etc.) | Various | 17 | varies |

#### 5. Content Composition

| Property | Value |
|----------|-------|
| **Domain** | EDU (Education) / calligraphy |
| **Content Type** | 100% handwritten |
| **Text Language** | Classical Chinese (zh), with Korean (ko) and Japanese (ja) tradition items |
| **Script Codes** | Hant (Traditional Chinese), Hani (CJK Ideographs), Kore (Korean), Jpan (Japanese) |
| **Text Direction** | Top-to-bottom (ttb), right-to-left column order |
| **Document Age** | Historical (6th-19th century) |
| **Text Content** | Fixed known text — 250 four-character lines, 1,000 total characters |

#### 6. IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Degradation Types** | Foxing, ink fading, paper aging, staining, worm damage |
| **Scan Quality** | Variable — museum flatbed (high quality) to web photographs (moderate) |
| **Resolution Range** | 600px to 60,000px+ (handscrolls) |
| **Color Mode** | RGB (color scans), some grayscale |
| **Capture Method** | Scanner flatbed (museum scans), camera (some web sources) |

#### 7. Data Format

| Property | Value |
|----------|-------|
| **Image Format** | Mixed: JPEG, PNG, TIFF |
| **Color Space** | RGB |
| **Resolution** | Variable (600px to 60,000px+ width) |
| **Annotation Format** | JSONL (registry + extended sidecar) + JSON (L2 per-image) |
| **Catalog Format** | YAML (74 items) |

#### 8. License

| Source | License | Commercial Use | Attribution |
|--------|---------|---------------|-------------|
| **Wikimedia Commons** | Public Domain / CC BY | Yes | CC BY items require attribution |
| **Met Museum** | CC0 | Yes | No attribution required |
| **NPM Taipei** | CC BY 4.0 | Yes | Attribution required |
| **Kyoto University** | Open Access | Yes | Attribution required |
| **NDL Japan** | NDL Open | Yes | Attribution to NDL |
| **LOC (World Digital Library)** | Public Domain | Yes | No attribution required |
| **Waseda University** | Open Access | Yes | Attribution required |
| **National Museum of Korea** | KOGL Type 1 | Yes | Attribution required |
| **Smithsonian (Freer Gallery)** | Public Domain | Yes | No attribution required |

**Per-image license tracking**: Each image's license is recorded in the registry JSONL (`license` field).

#### 9. Known Issues & Limitations

- **Historical bias**: All images are pre-modern (6th-19th century) — no contemporary calligraphy
- **No born-digital content**: 100% historical scans/photographs
- **Handscroll aspect ratios**: Some source images have extreme aspect ratios (e.g., 60826×2160 px handscroll panoramics)
- **Variable scan quality**: Museum high-resolution scans mixed with web-quality photographs
- **Incomplete works**: Some images depict only portions of the full 1,000-character text
- **Script style subjectivity**: Calligraphic style classification (e.g., distinguishing xingshu from xingcao) involves expert judgment
- **Korean underrepresentation**: Only 3 images from Korean sources (NMK); Korean tradition better represented via Wikimedia
- **Duplicate characters**: The canonical text contains 998 unique characters (2 historical duplicates in standard transmitted recension)
- **GIF format**: 1 Wikimedia image (`An_Authentic_Thousand_Character_Classic.gif`) uses GIF format
- **Quarantined junk**: 9 Korean NMK website scraping artifacts (logos, icons, badges at 8-208px) and 2 cross-source Met/Wikimedia duplicates moved to `_quarantined/` (2026-03-13)

#### 10. Processing Status

| Stage | Status | Notes |
|-------|--------|-------|
| **Catalog** | ✅ Complete | 74 items in `config/thousand_character_classic_catalog.yaml` |
| **Ground Truth Text** | ✅ Complete | 1,000 chars + 250-line translation in `config/thousand_character_classic_text.yaml` |
| **Harvest Script** | ✅ Complete | `scripts/harvest_thousand_character_classic.py` (6 sub-commands, min dimension filter) |
| **Enrichment Script** | ✅ Complete | `scripts/enrich_thousand_character_classic.py` (L2 + sidecar) |
| **Image Download** | ✅ Complete | 1,248 images from 9 institutions (NDL 249, LOC 245, Waseda 239, NPM 202, Kyoto 146, Wiki 140, Met 23, NMK 3, Smithsonian 1) |
| **Data Curation** | ✅ Complete | Quarantined 11 unsuitable files (9 web junk + 2 cross-source dupes); removed 356 ghost registry entries; fixed LOC path prefix; deduped 242 duplicate entries |
| **L2 Enrichment** | ✅ Complete | 1,449 records with L2 metadata |
| **Registry Sync** | ✅ Complete | 1,248/1,248 registry entries match files on disk (0 orphans) |
| **Validation** | ✅ Complete | All entries pass schema validation |

#### 11. References

##### Related Datasets

- [kuzushiji.md](kuzushiji.md) — Historical Japanese cursive handwriting (pre-modern)
- [casia-hwdb2.md](casia-hwdb2.md) — Chinese handwriting (modern simplified)
- [ndl-minhon.md](ndl-minhon.md) — Classical Japanese kuzushiji manuscripts

##### Cultural Context

The Thousand Character Classic (千字文, Qianziwen) was composed by Zhou Xingsi (周興嗣) in the Liang dynasty (6th century) as a penmanship exercise using exactly 1,000 distinct characters. It became the standard calligraphy primer across East Asia for 1,400+ years, practiced in China (千字文), Korea (천자문, Cheonjamun), Japan (千字文, Senjimon), and Uyghur traditions.
