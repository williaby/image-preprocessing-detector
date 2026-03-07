# Fonts for Synthetic Document Generation

This directory contains **supplemental fonts** for the synthetic document generator. The core Unicode coverage comes from system-installed Noto fonts.

## Font Strategy (Two-Tier Approach)

### Tier 1: System Fonts (via apt packages) - 7,000+ fonts

The bulk of font coverage comes from apt packages, particularly the Noto font family which provides comprehensive Unicode coverage for all 27 scripts.

**Required packages** (~2GB download):

```bash
# Core Noto fonts (all 27 scripts)
sudo apt install fonts-noto fonts-noto-core fonts-noto-extra fonts-noto-cjk

# Regional fonts
sudo apt install fonts-paratype fonts-liberation fonts-sil-padauk fonts-sil-abyssinica
```

### Tier 2: Bundled Fonts (this directory) - 241 fonts

These supplemental fonts provide:

- **Handwriting styles** for authentic noise training
- **Mimicry fonts** (Latin fonts that look like other scripts) for adversarial training
- **Regional variants** not available in apt packages (especially Indic scripts)
- **SIL linguistic fonts** for academic/linguistic contexts
- **Google Fonts** for under-covered scripts (Tamil, Telugu, Gujarati, Kannada, etc.)

See `fonts/synthetic-gen/MANIFEST.json` for per-font license and source metadata.

## Quick Setup

```bash
# Full setup (recommended) - installs all required fonts
./scripts/setup_fonts.sh

# Or manual installation:
# 1. Install system fonts
sudo apt install fonts-noto fonts-noto-cjk fonts-paratype fonts-liberation

# 2. Copy bundled fonts to user directory
mkdir -p ~/.local/share/fonts/synthetic-gen
cp fonts/synthetic-gen/* ~/.local/share/fonts/synthetic-gen/
fc-cache -fv
```

## Font Categories

### System Fonts (from apt)

| Script Family | Packages | Coverage |
|--------------|----------|----------|
| CJK | `fonts-noto-cjk` | Hans, Hant, Jpan, Kore |
| Arabic | `fonts-noto`, `fonts-hosny-amiri` | Arab, Nastaliq |
| Indic | `fonts-noto`, `fonts-lohit-*` | Deva, Beng, Taml, etc. |
| Thai/Khmer/Lao | `fonts-noto`, `fonts-thai-tlwg` | Thai, Khmr, Laoo |
| Cyrillic/Greek | `fonts-noto`, `fonts-paratype` | Cyrl, Grek |
| Latin | `fonts-liberation`, `fonts-noto` | Latn |

### Bundled Fonts (this directory)

**Handwriting Fonts** (15% of training samples):

| Script | Fonts | Purpose |
|--------|-------|---------|
| Cyrillic | BadScript, Caveat, MarckScript | Russian cursive (т→m) |
| Arabic | ArefRuqaa, Harmattan, PlaypenSansArabic | Ruq'ah cascade style |
| Devanagari | Kalam | Breaks shirorekha |
| Bengali | Atma, Galada | Informal styles |
| Tamil | Kavivanar | Handwritten Tamil |
| CJK | MaShanZheng, LiuJianMaoCao | Brush/calligraphy |
| Korean | NanumPenScript, NanumBrushScript | Pen/brush scripts |
| Latin | DancingScript, PatrickHand, GreatVibes | Script fonts |
| Thai | Itim | Handwritten Thai style |
| Malayalam | Chilanka | SMC handwriting font |
| Myanmar | Khyay | Display/headline style |
| Lao | Phetsarath | Government calligraphic serif |

**Mimicry/Adversarial Fonts** (5% of training samples):

| Target Script | Fonts | Purpose |
|---------------|-------|---------|
| Arabic-like | Aladin | Latin with Arabic aesthetic |
| Greek-like | CaesarDressing | Latin with Greek aesthetic |
| Cyrillic-like | RussoOne | Latin with Constructivist style |
| CJK-like | Bungee | Latin with blocky CJK style |

**Regional/Google Fonts** (added for v4 diversity):

| Script | Fonts Added | Source |
|--------|-------------|--------|
| Tamil (Taml) | Catamaran, HindMadurai, MuktaMalar, ArimaMadurai, Kavivanar | Google Fonts |
| Telugu (Telu) | HindGuntur, Ramabhadra, Mandali, NTR | Google Fonts |
| Gujarati (Gujr) | HindVadodara, MuktaVaani, Rasa, BalooBhai2 | Google Fonts |
| Kannada (Knda) | Timmana, BalooTamma2, HindMysuru, Benne | Google Fonts |
| Malayalam (Mlym) | Manjari | Google Fonts |
| Odia (Orya) | BalooBhaina2, AnekOdia, Alkatra | Google Fonts |
| Sinhala (Sinh) | AbhayaLibre, Yaldevi | Google Fonts |
| Gurmukhi (Guru) | MuktaMahee, BalooPaaji2 | Google Fonts |
| Devanagari (Deva) | Hind, Mukta, Baloo2, TiroDevanagariHindi | Google Fonts |
| Thai | Kanit, Pridi, BaiJamjuree, Mitr | Google Fonts |
| Khmer (Khmr) | Battambang, Content, Moul | Google Fonts |
| Arabic (Arab) | Tajawal, Mada, ElMessiri | Google Fonts |
| Korean (Kore) | NanumMyeongjo | Google Fonts |

**SIL/Regional Fonts** (original bundled):

- AwamiNastaliq (Urdu - CRITICAL)
- Amiri, NotoKufiArabic (Arabic calligraphic)
- ScheherazadeNew (Arabic traditional)
- Abyssinica, Brana, GeezManuscriptZemen (Ethiopic)
- Jomolhari, Uchen, DDCUchen, TibetanMachineUni, MonlamUni (Tibetan)
- BJCree (Canadian Syllabics - SIL)
- AboriginalSans, AboriginalSerif (Canadian Syllabics + Cherokee)
- SolaimanLipi, Kalpurush (Bengali - Bangladesh)

## FontManager Configuration

The `FontManager` searches these paths in order:

1. **Project-bundled**: `fonts/synthetic-gen/` (this directory)
2. **System fonts**: `/usr/share/fonts/`
3. **User fonts**: `~/.local/share/fonts/`

Font tier distribution for training:

| Tier | Weight | Source |
|------|--------|--------|
| SYSTEM | 40% | System fonts (Noto) |
| REGIONAL | 25% | System + Bundled |
| STYLISTIC | 15% | System + Bundled |
| HANDWRITING | 15% | Bundled |
| ADVERSARIAL | 5% | Bundled |

## Verification

After setup, verify font coverage:

```bash
# Quick audit (filename heuristics)
python scripts/audit_font_coverage.py --fail-below --min-families 5

# Visual comparison panels
python scripts/generate_font_comparison_panel.py --all --output-dir reports/font_panels/

# Programmatic check
python -c "
from image_preprocessing_detector.synthetic.fonts import FontManager
fm = FontManager()
fm.scan_fonts()
print(f'Total fonts: {sum(len(c.fonts) for c in fm.fonts_by_script.values())}')
print(f'Scripts covered: {len(fm.fonts_by_script)}')
for script, cache in sorted(fm.fonts_by_script.items()):
    print(f'  {script}: {len(cache.fonts)} fonts')
"
```

Expected output: 7,000+ fonts covering all 27 scripts, with all 27 at 5+ font families.

### Audit Results (v4 baseline — deep cmap scan)

```bash
python scripts/audit_font_coverage.py --deep --output reports/font_availability_deep_audit_v3.json
```

**All 27/27 scripts pass the 5-family minimum.**

| Script | Families | Notable Sources |
|--------|----------|----------------|
| Latn   | 180      | Liberation, Roboto, DejaVu, SIL linguistic |
| Cyrl   | 51       | ParaType, Liberation, DejaVu |
| Arab   | 24       | Amiri, Scheherazade, Tajawal, Mada |
| Thai   | 13       | Kanit, Pridi, BaiJamjuree, NotoLooped |
| Hebr   | 13       | Noto, DanaYad, GvretLevin |
| Taml   | 12       | Catamaran, HindMadurai, Kavivanar |
| Cans   | 12       | NotoSansCanadianAboriginal, BJCree, Aboriginal |
| Laoo   | 10       | Noto, NotoLoopedLao |
| Cher   | 9        | NotoSansCherokee, AboriginalSans/Serif |
| Gujr   | 9        | HindVadodara, MuktaVaani, Rasa |
| Telu   | 8        | HindGuntur, Ramabhadra, Mandali |
| Beng   | 8        | SolaimanLipi, Kalpurush, Atma |
| Jpan   | 8        | NotoSansCJK, NotoSerifJP |
| Mymr   | 7        | Padauk |
| Hans   | 7        | NotoSansCJK, MaShanZheng |
| Hant   | 7        | NotoSansCJK |
| Geor   | 7        | NotoSans/SerifGeorgian |
| Tibt   | 6        | Uchen, DDCUchen, TibetanMachineUni, Monlam |
| Knda   | 6        | HindMysuru, Benne, BalooTamma2 |
| Mlym   | 6        | Manjari |
| Khmr   | 6        | Battambang, Content, Moul |
| Hang   | 6        | NanumGothic, NanumMyeongjo |
| Guru   | 6        | MuktaMahee, BalooPaaji2 |
| Ethi   | 5        | Abyssinica, Brana, GeezManuscriptZemen |
| Sinh   | 5        | AbhayaLibre, Yaldevi |
| Orya   | 5        | AnekOdia, Alkatra, BalooBhaina2 |
| Deva   | 11       | Lohit, Hind, Mukta, TiroDevanagari |

## License

- **Noto fonts**: SIL Open Font License 1.1
- **SIL fonts**: SIL Open Font License 1.1
- **Google Fonts**: SIL Open Font License 1.1
- **ParaType fonts**: ParaType Free Font License
- **TibetanMachineUni, Monlam**: GPL + font exception
- **Aboriginal Sans/Serif**: Free (Chris Harvey)

See `fonts/synthetic-gen/MANIFEST.json` for per-font license details.
