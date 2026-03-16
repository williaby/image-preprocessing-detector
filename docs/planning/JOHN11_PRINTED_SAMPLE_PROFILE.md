# John 1:1 Printed Editions — Target Sample Profile

> **Status**: Active | Dataset Design
> **Created**: 2026-03-12
> **Parallel Dataset**: `john11-manuscripts` (handwritten, 11 scripts, 210-520 images)
> **Target**: ~400-500 images across ~22 scripts, 575 years of print history

---

## 1. Purpose

Define diversity targets and quotas for the `john11-printed-editions` dataset before source
research begins. This framework ensures the collected samples span the full range of print
technologies, time periods, scripts, typography styles, and physical conditions needed for
multi-task model training.

**Training value**:

- **Handwriting negatives**: 100% printed = NONE class for `handwriting_presence` head
- **Script diversity**: 22 scripts in printed form (vs 11 handwritten)
- **Typography diversity**: Real-world complement to V4 synthetic font diversity strategy
- **IQA training**: Print-specific degradation patterns distinct from manuscript degradation
- **REL domain**: Extends Religious domain coverage alongside manuscripts

---

## 2. Diversity Dimensions

Every catalog entry is tagged on 5 orthogonal dimensions:

### 2.1 Print Technology (`print_technology`)

| Value | Period | Visual Characteristics | IQA Relevance |
|-------|--------|----------------------|---------------|
| `movable_type_letterpress` | 1450-1900 | Impression marks, ink squash, uneven inking | ink_bleed, impression_depth |
| `woodblock` | 1450-1600 | Coarse grain, uneven ink transfer | wood_grain_texture |
| `lithography` | 1800-1950 | Smooth gradients, stone texture possible | dot_pattern |
| `offset` | 1900-present | Even ink, halftone dots visible at magnification | dot_gain, registration_error |
| `digital` | 1980-present | Sharp edges, uniform ink density | minimal_degradation |
| `typewriter` | 1870-1990 | Monospaced, uneven strike pressure, ribbon wear | strike_variation |

**Target distribution**: letterpress 30%, offset 25%, digital 15%, lithography 10%, typewriter 10%, woodblock 5%, other 5%.

### 2.2 Time Period (`time_period`)

| Bin | Date Range | Characteristics |
|-----|-----------|-----------------|
| `incunabula` | 1450-1500 | Blackletter, rubrication, hand-colored initials, movable type |
| `early_modern` | 1501-1700 | Transition blackletter→roman, polyglot editions, title page evolution |
| `enlightenment` | 1701-1850 | Standardized roman type, missionary translations begin, steam press |
| `industrial` | 1851-1950 | Mass production, stereotype plates, missionary Bible explosion, CJK/Asian |
| `modern` | 1951-present | Offset/digital, diverse fonts, study Bibles, Unicode-era |

**Target distribution**: incunabula 5-10%, early_modern 15-20%, enlightenment 20-25%, industrial 30-35%, modern 15-20%.

### 2.3 Script/Language (`script_iso15924`)

#### Group A: Parallel to manuscripts (10 scripts)

| Script | ISO 15924 | ML Class | OOD? | Target | Key Printed Editions |
|--------|-----------|----------|------|--------|---------------------|
| Greek | Grek | GREK | No | 40-60 | Erasmus 1516, Stephanus 1550, Nestl-Aland |
| Latin | Latn | LATN | No | 60-80 | Gutenberg 1455, Clementine Vulgate, Douay-Rheims |
| Ethiopic | Ethi | OTHER | No | 10-20 | BFBS Amharic editions, Swedish Mission Press |
| Armenian | Armn | OTHER | Yes | 10-15 | Amsterdam 1666 (first), Zohrab 1805 |
| Syriac | Syrc | OTHER | Yes | 5-10 | Peshitta (London/Paris polyglots), Urmia editions |
| Arabic | Arab | ARAB | No | 15-25 | Van Dyck 1865, Smith-Van Dyck, Propaganda Fide |
| Cyrillic | Cyrl | CYRL | No | 15-25 | Ostrog Bible 1581, Elizabeth Bible 1751, Synodal |
| Coptic | Copt | OTHER | No | 5-10 | Wilkins 1716, Schwartze/Tattam, Horner editions |
| Gothic | Goth | OTHER | Yes | 3-5 | Uppstrom 1854 facsimile, Streitberg edition |
| Georgian | Geor | OTHER | Yes | 5-10 | Mcxeta Bible 1743, BFBS Georgian 1816 |

#### Group B: Expanded scripts (12 additional)

| Script | ISO 15924 | ML Class | OOD? | Target | Key Printed Editions |
|--------|-----------|----------|------|--------|---------------------|
| Chinese | Hani | CJK | No | 15-25 | Marshman 1822, Delegates' 1854, CUV 1919 |
| Japanese | Kana | CJK | No | 8-12 | Gutzlaff 1837, Meiji translations, Shinkaiyaku |
| Korean | Hang | HANG | No | 8-12 | Ross 1887, Korean RV 1961 |
| Devanagari | Deva | DEVA | No | 8-12 | Carey 1811, Hindi OV 1835, modern editions |
| Bengali | Beng | INDIC_OTHER | No | 5-8 | Carey Bengali NT 1801 (first), BFBS editions |
| Tamil | Taml | TAML | No | 5-8 | Fabricius 1714, Ziegenbalg/Schultze, TBS editions |
| Gurmukhi | Guru | INDIC_OTHER | No | 3-5 | Punjab Bible Society editions |
| Sinhala | Sinh | INDIC_OTHER | No | 3-5 | Ceylon editions |
| Thai | Thai | THAI | No | 5-8 | Bradley 1843 (partial), McFarland, Thai Standard |
| Myanmar | Mymr | SE_ASIAN_OTHER | No | 3-5 | Judson 1835, modern BBS editions |
| Khmer | Khmr | SE_ASIAN_OTHER | No | 3-5 | Cambodia Bible Society editions |
| Tibetan | Tibt | OTHER | No | 3-5 | Moravian Mission editions (rare) |

**Total target**: ~400-500 images across 22 scripts.

### 2.4 Typography (`typography`)

| Value | Description | Scripts Where Common |
|-------|-------------|---------------------|
| `blackletter` | Gothic textura, Schwabacher, Fraktur | Latn (pre-1800), Cyrl (pre-1700) |
| `roman_serif` | Humanist, Transitional, Didone, Slab | Latn, Grek (post-1500), all modern editions |
| `italic` | Italic or oblique as primary text style | Rare as primary; common in parallel editions |
| `sans_serif` | Grotesque, Neo-grotesque, Humanist sans | Modern editions (post-1950) |
| `monospace` | Typewriter, Courier-family | Typewriter editions only |
| `native_script` | Script-specific traditional typography | CJK, Deva, Arab, Thai, Ethi, etc. |
| `mixed` | Multiple typography styles on same page | Polyglot editions, study Bibles |

**Target distribution**: roman_serif 35%, native_script 25%, blackletter 15%, mixed 10%, sans_serif 8%, monospace 5%, italic 2%.

### 2.5 Physical Condition (`condition`)

| Value | Description | IQA Degradation Types |
|-------|-------------|----------------------|
| `pristine` | Clean digital scan, no visible degradation | none |
| `aged_yellowed` | Paper yellowing, minor age spots | yellowing, foxing |
| `foxed` | Significant foxing/age spots | foxing, staining |
| `ink_degraded` | Ink bleed, fading, bleed-through | ink_bleed, fading, bleed_through |
| `poor_scan` | Low resolution, skew, uneven lighting | binding_shadow, creasing |
| `microfilm` | Microfilm/microfiche digitization artifacts | fading, low_contrast |

**Target distribution**: pristine 20%, aged_yellowed 30%, foxed 15%, ink_degraded 15%, poor_scan 10%, microfilm 10%.

---

## 3. Coverage Matrix

Minimum required coverage (dimension pairs that MUST be represented):

| | Letterpress | Lithography | Offset | Digital | Typewriter |
|---|---|---|---|---|---|
| **Incunabula** | 3+ | - | - | - | - |
| **Early Modern** | 5+ | - | - | - | - |
| **Enlightenment** | 5+ | 2+ | - | - | - |
| **Industrial** | 3+ | 3+ | 5+ | - | 3+ |
| **Modern** | - | - | 5+ | 5+ | 2+ |

Each script with target >= 10 must appear in at least 2 time periods.
Each script with target >= 10 must appear in at least 2 condition categories.

---

## 4. Quality Gates

Before accepting an image into the dataset:

1. **Content verification**: Image contains John 1:1 text (at minimum the opening phrase)
2. **Content type**: Image shows printed/typed text (not handwritten)
3. **License**: Verified public domain, CC0, or CC-BY-4.0
4. **Resolution**: Minimum 800px on longest edge (prefer >= 1500px)
5. **Legibility**: Text must be legible (even if degraded, the print must be discernible)
6. **Uniqueness**: No SHA256 or perceptual hash duplicates within dataset or with john11-manuscripts

---

## 5. Excluded Content

- Handwritten text of any kind (those belong in john11-manuscripts)
- Pages that do not contain John 1:1 (even if from same edition)
- Modern screenshots of digital Bible text (born-digital without physical printing)
- Images with watermarks that obscure text
- Images requiring login/authentication to access (license unverifiable)

---

## 6. Relationship to V4 Font Diversity Strategy

This dataset provides **real-world printed examples** complementing the synthetic font diversity
in `V4_FONT_DIVERSITY_STRATEGY.md`:

| V4 Synthetic | john11-printed-editions |
|-------------|------------------------|
| SYSTEM tier (Noto, 40%) | Modern digital editions (sans/serif, 15%) |
| REGIONAL tier (Google Fonts, 25%) | Native script typography (CJK, Indic, 25%) |
| STYLISTIC tier (display, 15%) | Blackletter/Fraktur incunabula (15%) |
| HANDWRITING tier (brush, 15%) | N/A (handwriting covered by john11-manuscripts) |
| ADVERSARIAL tier (confusable, 5%) | Historical typography at degradation extremes |

---

## 7. Success Criteria

| Metric | Target |
|--------|--------|
| Total images | 400-500 |
| Scripts represented | >= 20 |
| Print technologies | >= 4 |
| Time periods | All 5 bins populated |
| Condition categories | All 6 bins populated |
| License compliance | 100% verified PD/CC0/CC-BY |
| Visual QA pass rate | >= 95% (contact sheet review) |
