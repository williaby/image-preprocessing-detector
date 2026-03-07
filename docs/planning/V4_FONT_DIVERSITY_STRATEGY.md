# v4 Font Diversity & Adversarial Strategy

> **Status**: Phase A-B Complete | v4 Generation Guidance
> **Created**: 2026-02-28
> **Updated**: 2026-02-28
> **Source Research**: `tmp_cleanup/fonts/fonts_1.md`, `fonts_2.md`, `fonts_3.md`
> **Baseline**: 255 bundled fonts (was 241; +14 adversarial) + 7,000+ system fonts; 27/27 scripts at 5+ families
> **References**: `UNIFIED_TRAINING_CORPUS.md` (§3.5, §7), `OOD_DATASET_CATALOG.md` (§1h)

---

## 1. Problem Statement

Synth-multiscript-v3 rendered every script using a single default font (the dead-code bug, now
fixed). v4 must produce images across the full font tier distribution (SYSTEM 40%, REGIONAL 25%,
STYLISTIC 15%, HANDWRITING 15%, ADVERSARIAL 5%) to train a script classifier that generalizes
beyond standard Noto typefaces. Additionally, the UNIFIED_TRAINING_CORPUS requires ≥5 font
families per script (§3.5), and OOD-Script category 1h ("Font variation") needs 75 decorative-
font images to test whether the script head overfits to specific font shapes.

---

## 2. Current Font Inventory (Post-Audit)

**255 bundled fonts** across all 27 scripts. All pass the 5-family minimum (deep cmap audit).
See `reports/font_availability_deep_audit_v4.json` for per-script family counts.

### Scripts by Diversity Level

| Level | Scripts | Families | Notes |
|-------|---------|----------|-------|
| Rich (10+) | Latn(183), Cyrl(51), Arab(24), Thai(14), Taml(12), Cans(12), Hebr(13), Deva(11), Laoo(11) | Broad tier coverage | Good adversarial candidates already bundled |
| Moderate (6-9) | Hang(6), Jpan(8), Hans(7), Hant(7), Beng(8), Gujr(9), Telu(8), Mymr(8), Geor(7), Mlym(7), Knda(6), Khmr(6), Tibt(6), Guru(6), Cher(9) | Adequate for training | Need adversarial augmentation via style sweeps |
| Minimal (5) | Orya(5), Ethi(5), Sinh(5) | At threshold | Rely on weight/width variable axis sweeps |

---

## 3. Adversarial Font Strategy for v4 Generation

### 3.1 The Five Attack Vectors (from fonts_2.md research)

The research identifies five systematic ways adversarial fonts break script classifiers.
v4 generation must exercise all five:

| # | Attack Vector | v4 Implementation | Tier |
|---|--------------|-------------------|------|
| 1 | **Cross-script design unification** | Use Baloo family (10 Indic scripts), Anek family, Tiro family, EB Garamond (Latn/Cyrl/Grek) | ADVERSARIAL |
| 2 | **Historical/archaic letterforms** | Jaini (15c Deva), Uncial Antiqua (late-antique Latn), Metal (pre-1970 Khmr) | ADVERSARIAL |
| 3 | **Calligraphic style transfer** | Brush scripts that share dynamics across traditions: Liu Jian Mao Cao (Hans), Comforter Brush (Latn→CJK), Nanum Brush Script (Hang→Hans) | ADVERSARIAL |
| 4 | **Variable font extremes** | Sweep wght/wdth axes of Noto Variable, Anek, Reem Kufi to ExtraCondensed Black or Expanded Thin | ADVERSARIAL + STYLISTIC |
| 5 | **Structural feature destruction** | Stencil (Stick No Bills/Sinh), dotted (Ge'ez Handwriting/Ethi), extreme weight (Modak/Deva) | ADVERSARIAL |

### 3.2 Fonts to Download for ADVERSARIAL Tier

The following fonts from the research are NOT yet in `fonts/synthetic-gen/` and should be
downloaded to populate ADVERSARIAL tiers. All are SIL OFL 1.1 unless noted.

**Priority 1 — High-impact adversarial fonts (download before v4 generation)**

| Font | Script | Attack Vector | Why Adversarial |
|------|--------|--------------|-----------------|
| UnifrakturMaguntia | Latn | Historical | Blackletter; 'k'≈Cyrl 'к', 'n'≈'п'; dense vertical strokes |
| Lobster | Cyrl+Latn | Cross-script unification | Connected brush; ~11 shared Latin/Cyrillic glyphs near-identical |
| Pacifico | Cyrl+Latn | Cross-script unification | Brush script; Cyrl extension designed for visual unity with Latin |
| Jaini | Deva | Structural destruction | Disconnected shirorekha — the #1 Deva classifier cue |
| Modak | Deva | Structural destruction | Adjacent chars merge into fused forms; shirorekha buried |
| Reem Kufi | Arab | Structural destruction | Geometric Kufic; no cursive flow; resembles Latin display |
| Liu Jian Mao Cao | Hans | Calligraphic transfer | Grass script (草書); strokes merge into flowing lines |
| Nanum Brush Script | Hang | Calligraphic transfer | Heavy brush Hangul; blocks resemble Chinese characters |
| Stick No Bills | Sinh | Structural destruction | Stencil cuts sever continuous curved strokes |
| Comforter Brush | Latn | Calligraphic transfer | Brush strokes mimic CJK semi-cursive |

**Priority 2 — Cross-script confusion pairs**

| Font | Script | Confuses With | Why |
|------|--------|---------------|-----|
| Cinzel Decorative | Latn | Deva (shirorekha mimic) | Top-serif flourishes create horizontal lines |
| Monsieur La Doulaise | Latn | Arab (Diwani) | Flourishes 3-5× beyond letter bodies |
| Gulzar | Arab | — | 16+ contextual variants per glyph; 1,161 glyphs |
| GFS Bodoni | Grek | Latn/Cyrl | Extreme Didone; 14/24 uppercase identical to Latin |
| EB Garamond | Grek+Latn+Cyrl | Three-way | Harmonized humanist pen logic across 3 scripts |
| Lakki Reddy | Telu | Knda | Thick brush softens Telugu→Kannada confusion |
| Charmonman | Thai | Latn cursive | Zapfino-inspired swashes blur Thai identity |
| Moul | Khmr | Mymr | Heavy rounded forms resemble Myanmar circular letters |

**Priority 3 — Variable-axis extremes (no download needed — use existing Noto Variable)**

For scripts where we have Noto Variable fonts installed, render at axis extremes:

- ExtraCondensed Black: Geor→vertical strokes (Armn/Ethi confusion)
- Expanded Thin: Cher→thin Latin uppercase confusion
- ExtraCondensed: Orya curves flatten→angular Bengali confusion

### 3.3 ADVERSARIAL Tier Recommendations per Script

Update `config.py FONT_RECOMMENDATIONS` ADVERSARIAL entries after downloading Priority 1 fonts:

```python
FONT_RECOMMENDATIONS = {
    "Latn": {
        # ... existing ...
        "ADVERSARIAL": ["UnifrakturMaguntia", "CinzelDecorative", "ComforterBrush",
                        "MonsieurLaDoulaise"],
    },
    "Arab": {
        "ADVERSARIAL": ["ReemKufi", "Gulzar"],
    },
    "Deva": {
        "ADVERSARIAL": ["Jaini", "Modak"],
    },
    "Cyrl": {
        "ADVERSARIAL": ["Lobster", "Pacifico"],  # Cross-script with Latin
    },
    "Grek": {
        "ADVERSARIAL": ["GFSBodoni", "EBGaramond"],  # Three-way confusion
    },
    "Hans": {
        "ADVERSARIAL": ["LiuJianMaoCao"],  # Grass script
    },
    "Hang": {
        "ADVERSARIAL": ["NanumBrushScript"],  # Brush → CJK confusion
    },
    "Sinh": {
        "ADVERSARIAL": ["StickNoBills"],  # Stencil destruction
    },
    "Telu": {
        "ADVERSARIAL": ["LakkiReddy"],  # Telugu→Kannada confusion
    },
    "Khmr": {
        "ADVERSARIAL": ["Moul"],  # Already bundled; Khmer→Myanmar confusion
    },
    "Thai": {
        "ADVERSARIAL": ["Charmonman"],  # Thai→Latin cursive confusion
    },
}
```

---

## 4. Impact on Unified Training Corpus

### 4.1 Script Detection Dataset (§3.5 — 108K balanced)

**Current requirement**: ≥5 font families per script (MET for all 27).

**New requirement from font research**: The corpus specification says "max class imbalance 3×"
and "weighted sampling" — but says nothing about font-style distribution within each class.
The research demonstrates that a model trained only on standard Noto will fail on:

- Handwriting variants (15% tier weight)
- Display/decorative variants (part of STYLISTIC 15%)
- Adversarial fonts designed to break classifiers (5% tier weight)

**Recommendation — v4 generation font distribution per script:**

```text
For each of the ~60K v3-sourced script detection images:
  40% SYSTEM   (Noto Sans/Serif variants — the "easy" baseline)
  25% REGIONAL (Google Fonts, SIL fonts — moderate diversity)
  15% STYLISTIC (Display, condensed, weight extremes — visual edge)
  15% HANDWRITING (Brush, pen, calligraphic — domain-specific noise)
   5% ADVERSARIAL (Cross-script confusables, structural destruction)
```

This maps directly to the tier weights in `fonts.py:get_tiered_font()`.

**Per-class training weight interaction**: Scripts with class weight >1.0 (TIBT=2.0,
SE_ASIAN_OTHER=1.8, GREK=1.5) should have proportionally MORE adversarial font coverage,
because the model needs to be robust to the hard cases for these underrepresented scripts.

### 4.2 Impact on Other Training Views (via Pool 1 sharing)

Pool 1 (v3) images serve 7-9 heads. When v4 generation uses diverse fonts:

| Head | Font Diversity Impact |
|------|---------------------|
| Script Detection | **Direct benefit** — the primary target |
| Orientation | Indirect — diverse fonts create more realistic training images for rotation classification |
| Skew | Indirect — text rendered in various fonts provides better generalization for skew estimation |
| Resolution Quality | Indirect — different fonts have different char heights at same DPI |
| IQA pseudo-labels | Indirect — font variation adds natural quality variation |
| Shadow/Warping | No impact — geometric transforms don't depend on font |
| Capture Method | Minimal — synthetic provenance overrides font effects |
| Handwriting negatives | **Benefit** — diverse printed fonts make the NONE class more representative |

### 4.3 Synth-Multiscript-v3 Rebalancing (§3.5 Script Rebalancing Protocol)

The v3 dataset has a confirmed Arab imbalance (49,169 = 3.8× target). The rebalancing protocol
caps Arab at 13K and upsamples 17 underrepresented scripts.

**Font diversity interaction with rebalancing**: When upsampling an underrepresented script
(e.g., TIBT with weight 2.0), the same image will be seen multiple times. If each appearance
uses the same font (as in v3), the model learns the font texture, not the script structure.

**Recommendation**: For v4, ensure that when upsampled images are re-presented during training,
they are rendered with DIFFERENT fonts each time. This can be implemented as:

1. Pre-render each text in 3-5 different fonts at v4 generation time
2. OR: Apply font augmentation at training time (re-render on-the-fly from stored text)

Option 1 is simpler and recommended.

---

## 5. Impact on OOD Dataset

### 5.1 OOD-Script Category 1h — Font Variation (75 images)

The OOD catalog specifies 75 images testing font variation in trained scripts. The research
provides a precise mapping of which adversarial fonts to use:

| Sub-target | Count | Fonts to Render | Script Labels |
|------------|-------|-----------------|---------------|
| Blackletter Latin | 15 | UnifrakturMaguntia | Latn |
| Brush script Latin | 10 | ComforterBrush, MonsieurLaDoulaise | Latn |
| Shirorekha-broken Deva | 10 | Jaini, Modak | Deva |
| Geometric Kufic Arabic | 10 | ReemKufi | Arab |
| Grass script Hans | 10 | LiuJianMaoCao | Hans |
| Brush Hangul | 5 | NanumBrushScript | Hang |
| Stencil Sinhala | 5 | StickNoBills | Sinh |
| Cross-script Cyrl/Latn | 10 | Lobster, Pacifico | Cyrl |

**Acquisition method**: Render via Python (Pillow + HarfBuzz shaping) at 300 DPI on standard
document templates. Label as `capture_method=born_digital`, `open_set=false`.

### 5.2 OOD-Mixed Category 9c — Cross-Script Confusion (New Sub-Source)

The research identifies 15 high-risk confusion pairs. The OOD-Mixed spec mentions
"9c-1" and "9c-3" for script-related mixed OOD. The research suggests a dedicated
**adversarial font confusion sub-source** within OOD-Mixed:

| Confusion Pair | Risk | Adversarial Font | Test Scenario |
|---------------|------|-----------------|---------------|
| Cherokee ↔ Latin | Extreme | NotoSansCherokee (Thin) | Thin weight Cherokee rendered at low res |
| Thai ↔ Lao | Extreme | NotoSansThaiLooped + NotoLoopedLao | Same text concept in both scripts, looped |
| Cyrillic ↔ Latin | Very High | Lobster, Pacifico | Connected brush with shared homoglyphs |
| Deva ↔ Gujarati | Very High | Jaini + BalooBhai2 | Broken shirorekha vs pseudo-bar |
| Telugu ↔ Kannada | High | TiroTelugu + TiroKannada | Same design DNA, different scripts |
| CJK cross-script | High | LiuJianMaoCao, NanumBrushScript | Brush calligraphy indistinguishable |

**Recommendation**: Add 50 images as OOD-Mixed sub-source 9c-4 (adversarial font confusion
pairs), 2 per confusion pair × 5 most critical pairs × 5 font/size combinations.

### 5.3 OOD-Script Category 1e — Historical Fraktur (50 images)

Already specified in the OOD catalog. The research confirms **UnifrakturMaguntia** as the
primary adversarial font for this category. Additionally:

- Fraktur 'k' ≈ Cyrillic 'к'
- Fraktur 'n' ≈ Cyrillic 'п'
- Long 's' (ſ) is unique to historical Latin

These specific confusable pairs should be documented in the OOD-Script labels as
`confusable_pairs: ["Latn-Cyrl"]` for targeted evaluation.

---

## 6. Implementation Roadmap

### Phase A: Font Downloads (1–2 hours)

Download Priority 1 adversarial fonts from Google Fonts / GitHub:

```bash
# Create download script
for font in UnifrakturMaguntia Lobster Pacifico Jaini Modak ReemKufi \
            LiuJianMaoCao StickNoBills ComforterBrush CinzelDecorative \
            MonsieurLaDoulaise GFSBodoni Charmonman LakkiReddy Gulzar; do
    # Download from google/fonts repo
    curl -sL "https://raw.githubusercontent.com/google/fonts/main/ofl/${font,,}/${font}-Regular.ttf" \
         -o "fonts/synthetic-gen/${font}-Regular.ttf"
done
```

Update MANIFEST.json, FONT_NAME_TO_SCRIPT, FONT_RECOMMENDATIONS ADVERSARIAL tiers.

### Phase B: Generator Configuration (2–3 hours)

1. Verify `get_tiered_font()` correctly samples from ADVERSARIAL tier at 5% rate
2. Add ADVERSARIAL tier entries to all script FONT_RECOMMENDATIONS
3. Add `adversarial_font_name` field to v4 sidecar metadata
4. Implement variable-axis rendering for Noto Variable (wght/wdth extremes)

### Phase C: OOD Font Variation Rendering (2–3 hours)

1. Create `scripts/render_ood_font_variation.py`
2. Render 75 images per §5.1 specification
3. Register in `metadata_registry/ood_registry.jsonl`

### Phase D: Validation (1–2 hours)

1. Generate 1,000 test images (37/script) with tiered font sampling
2. Verify each script used 3+ distinct font families
3. Verify ADVERSARIAL tier hit rate ~5%
4. Verify cross-script confusion pairs rendered correctly

---

## 7. Cross-Script Confusion Matrix — Training Implications

The research identifies 15 confusion pairs ranked by risk. For v4 training, the most
critical pairs should receive **targeted hard-negative mining** — ensuring the model sees
both sides of each confusion pair in the same training batch.

### Priority Confusion Pairs for Hard-Negative Mining

| Pair | v4 Action |
|------|-----------|
| Cherokee ↔ Latin | Dedicate 2% of LATN and CHER training images to thin-weight adversarial fonts |
| Thai ↔ Lao | Include looped variants in both scripts; ensure training batches mix both |
| Cyrillic ↔ Latin | Include brush scripts (Lobster, Pacifico) in both Cyrl and Latn adversarial tiers |
| Deva ↔ Gujarati | Include Jaini (broken bar) in Deva; BalooBhai2 (pseudo-bar) in Gujr |
| Telugu ↔ Kannada | Use same Tiro design family for both scripts to force structural discrimination |

### Impact on ML Class Structure (19 classes)

The script_cls head groups some scripts into aggregate classes:

- INDIC_OTHER: Gujr + Guru + Knda + Mlym + Orya + Sinh
- SE_ASIAN_OTHER: Mymr + Khmr + Laoo

**Within-group confusion is NOT an error** — the model only needs to classify at the
aggregate level. Cross-group confusion (e.g., DEVA ↔ INDIC_OTHER) is a true error and
should be the focus of adversarial training.

---

## 8. What NOT to Do

1. **Don't regenerate v3 from scratch** — the base images and text are fine; only the font
   sampling was broken (single font per script). v4 fixes this at generation time.

2. **Don't use GPL-only fonts in training** without font exception — Fonts like
   BPG Mrgvlovani (Georgian), Dyuthi (Malayalam), and Sofer Stam (Hebrew) are GPL v2/v3
   without clear font exceptions. Use only for OOD evaluation, not training data generation.

3. **Don't conflate "decorative" with "adversarial"** — A decorative font within a single
   script (e.g., a fancy Thai font) is STYLISTIC tier, not ADVERSARIAL. ADVERSARIAL tier is
   specifically for fonts that create cross-script confusion or destroy discriminative features.

4. **Don't assume font coverage = script coverage** — Some multi-script fonts (e.g.,
   Aboriginal Sans covers both Cans AND Cher) may produce unexpected script assignments
   if not correctly mapped in FONT_NAME_TO_SCRIPT.

5. **Don't train on reserved scripts** — Mongolian (Mong), Syriac (Syrc), Georgian (Geor)
   fonts must NEVER appear in training manifests. They are OOD-only.

---

## 9. Consensus Analysis (6-Model Review)

Six-model consensus analysis validated this strategy at **8.0/10 mean confidence**
(Gemini 3.1 Pro, DeepSeek v3.2, Grok 4.1 Fast, Minimax M2.5, Qwen 3.5 397B, Kimi K2.5).
All models confirmed: no technical blockers, font selections show high domain expertise,
phased implementation is correct.

### Key Findings and Decisions

| Topic | Consensus | Decision |
|-------|-----------|----------|
| Adversarial tier rate | Split: 5% (Gemini/Grok), 8-10% (DeepSeek/Minimax), 12-15% (Qwen/Kimi) | **Keep 5% in data generation**. Document loss re-weighting as training-time recommendation. |
| OOD set sizing | 5/6 models say 175 is insufficient; range 500-1,000 recommended | **Expanded to ~375**: 150 font variations, 100 cross-script confusion, ~25 case variation, ~50 mimicry |
| Font selections | 6/6 endorse the 14 fonts | **Proceeded as-is**. Gaps (CJK simplified/traditional, Arabic connectivity) documented as future work. |
| Missing vectors | Combination attacks (font+degradation), mixed-script documents | **Documented as future work** — out of scope for infrastructure phase. |
| Case variation | ALL CAPS removes case-based discrimination cues, increasing cross-script confusability | **ALL CAPS rendering added** to OOD pipeline for cased scripts (Latn, Cyrl, Grek). Capped at 5% of total samples. |
| Mimicry/simulation | Latin fonts styled to look like other scripts (Sefarad, Al-Andalus, ChopSuey, RussoOne) | **Wired existing MIMICRY_FONTS + get_mimicry_font()** into OOD rendering. |
| Aravrit split-design | Experimental typeface: top half = Arabic, bottom half = Hebrew | **Documented as future work** — not open-source, cannot download. |

### Training-Time Recommendations (Not Implemented Yet)

Per Qwen 3.5 397B suggestion, consider at training time:

- **Loss re-weighting**: Increase loss weight for ADVERSARIAL tier samples (2-3x)
- **Hard-negative mining**: Batch adversarial samples from confusable script pairs together
- **Curriculum learning**: Introduce adversarial fonts gradually during training schedule

---

## 10. Implementation Status

### Phase A: Font Downloads — COMPLETE

- **Script**: `scripts/download_adversarial_fonts.sh`
- **Result**: 14/14 adversarial fonts downloaded to `fonts/synthetic-gen/`
- 11 from Google Fonts GitHub, 1 from Greek Font Society (GFS Bodoni ZIP)
- 4 already bundled (Pacifico, LiuJianMaoCao, NanumBrushScript, Moul)
- MANIFEST.json updated (241 -> 255 total fonts)
- FONT_NAME_TO_SCRIPT entries added for all 14 fonts

### Phase B: Generator Configuration — COMPLETE

- ADVERSARIAL tiers populated for 11 scripts in `config.py:FONT_RECOMMENDATIONS`
- `get_tiered_font()` correctly samples from ADVERSARIAL tier at 5% rate (tested)
- `adversarial_type` metadata field added to OOD rendering pipeline
- 23 new tests added: tier population, font discovery, sampling rate, case cap, mimicry loading

### Phase C: OOD Rendering — READY (Not Yet Run)

- `build_ood_dataset.py render-font-variations` expanded: 4 -> 11 scripts
- Default `--n-images` increased from 75 to 150
- New flags: `--include-9c4` (100 cross-script confusion images), `--include-case-variation`
  (~25 ALL CAPS images, 5% cap), `--include-mimicry` (~50 simulation font images)
- Total OOD target: ~375 images (was 175)

### Phase D: Validation — PENDING

- Dry-run to be executed before actual rendering
- Integration with `metadata_registry/ood_registry.jsonl`

---

## 11. Future Work

### 11.1 Aravrit and Split-Design Fonts

**Aravrit** (Liron Lavi Turkenich): An experimental typeface where the top half of every glyph
represents Arabic while the bottom half represents Hebrew. A single bounding box contains valid
topological features for two mutually exclusive scripts.

**Status**: NOT open-source, cannot be freely downloaded.

**Future directions**:

- If licensing permits, Aravrit text would be the ultimate adversarial OOD test
- **Programmatic proxy**: Synthetically composite the top half of Arabic-rendered text with the
  bottom half of Hebrew-rendered text, creating artificial "chimera" images for OOD evaluation
- **Additional hybrid concepts**: LXGW WenKai TC (Japanese design DNA + Traditional Chinese),
  Zen Antique (different visual weights per script component), Jura (Kayah Li stroke mechanics
  applied to Latin/Cyrillic/Greek)

### 11.2 CJK Confusable Pairs

The current adversarial fonts cover broad strokes but lack specific CJK simplified/traditional
confusion pairs. Future work should add:

- Fonts that blur Simplified Chinese (Hans) vs Traditional Chinese (Hant) boundaries
- Japanese-specific Kanji variants that differ subtly from Chinese counterparts

### 11.3 Combination Attacks

Not yet implemented: applying adversarial fonts simultaneously with degradation augmentations
(blur + historical font, noise + stencil font). This creates a multiplicative effect that is
harder for classifiers to handle.

### 11.4 Variable Font Axis Sweeps

Priority 3 fonts (Noto Variable axis extremes) are deferred to v4 generation phase. Sweeping
wght/wdth axes to ExtraCondensed Black or Expanded Thin creates additional adversarial cases
without downloading new fonts.
