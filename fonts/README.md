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

### Tier 2: Bundled Fonts (this directory) - 147 fonts

These supplemental fonts provide:

- **Handwriting styles** for authentic noise training
- **Mimicry fonts** (Latin fonts that look like other scripts) for adversarial training
- **Regional variants** not available in apt packages
- **SIL linguistic fonts** for academic/linguistic contexts

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
| Arabic | ArefRuqaa, Harmattan | Ruq'ah cascade style |
| Devanagari | Kalam | Breaks shirorekha |
| Bengali | Atma, Galada | Informal styles |
| CJK | MaShanZheng, LiuJianMaoCao | Brush/calligraphy |
| Korean | NanumPenScript, NanumBrushScript | Pen/brush scripts |
| Latin | DancingScript, PatrickHand, GreatVibes | Script fonts |

**Mimicry/Adversarial Fonts** (5% of training samples):

| Target Script | Fonts | Purpose |
|---------------|-------|---------|
| Arabic-like | Aladin | Latin with Arabic aesthetic |
| Greek-like | CaesarDressing | Latin with Greek aesthetic |
| Cyrillic-like | RussoOne | Latin with Constructivist style |
| CJK-like | Bungee | Latin with blocky CJK style |

**Regional/SIL Fonts**:

- AwamiNastaliq (Urdu - CRITICAL)
- Amiri (Arabic calligraphic)
- ScheherazadeNew (Arabic traditional)
- Abyssinica (Ethiopic)
- Jomolhari (Tibetan)
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

```python
from image_preprocessing_detector.synthetic.fonts import FontManager

manager = FontManager()
manager.scan_fonts()

print(f"Total fonts: {len(manager.all_fonts)}")
print(f"Scripts covered: {len(manager.fonts_by_script)}")

# Check all 27 scripts have fonts
for script in manager.fonts_by_script:
    count = len(manager.fonts_by_script[script].fonts)
    print(f"  {script}: {count} fonts")
```

Expected output: 7,000+ fonts covering all 27 scripts.

## License

- **Noto fonts**: SIL Open Font License 1.1
- **SIL fonts**: SIL Open Font License 1.1
- **Google Fonts**: SIL Open Font License 1.1
- **ParaType fonts**: ParaType Free Font License
