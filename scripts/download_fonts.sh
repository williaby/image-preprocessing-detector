#!/bin/bash
# Manual font download script for synthetic document generation
# Fonts that are not available via apt packages
# Usage: ./scripts/download_fonts.sh

set -e

FONT_DIR="$HOME/.local/share/fonts/synthetic-gen"
TEMP_DIR="/tmp/font-downloads"

echo "=============================================="
echo "Font Download Script for Synthetic Doc Gen"
echo "=============================================="

mkdir -p "$FONT_DIR"
mkdir -p "$TEMP_DIR"

download_google_font() {
    local family="$1"
    local output="$2"
    echo "  Downloading $family..."
    curl -sL "https://fonts.google.com/download?family=${family// /%20}" -o "$TEMP_DIR/$output.zip" 2>/dev/null || {
        echo "  Warning: Could not download $family"
        return 1
    }
    unzip -o -q "$TEMP_DIR/$output.zip" -d "$FONT_DIR/" 2>/dev/null || true
}

echo ""
echo "=== Phase 1: Google Fonts ==="

# PT Sans/Serif (Russian standard)
download_google_font "PT Sans" "pt-sans"
download_google_font "PT Serif" "pt-serif"

# Fira Sans (Bulgarian Cyrillic with locl features)
download_google_font "Fira Sans" "fira-sans"

# Vazirmatn (Modern Persian)
download_google_font "Vazirmatn" "vazirmatn"

# Amiri (Classical Arabic) - backup if not in packages
download_google_font "Amiri" "amiri"

# Nanum Gothic (Korean)
download_google_font "Nanum Gothic" "nanum-gothic"

# Merriweather (Latin/Vietnamese variety)
download_google_font "Merriweather" "merriweather"

# Exo 2 (Bulgarian Cyrillic)
download_google_font "Exo 2" "exo2"

# Anek Gujarati
download_google_font "Anek Gujarati" "anek-gujarati"

# Rasa (Gujarati)
download_google_font "Rasa" "rasa"

# Arima Madurai (Tamil)
download_google_font "Arima" "arima"

echo ""
echo "=== Phase 2: SIL Fonts (Direct Downloads) ==="

# Awami Nastaliq (CRITICAL for Urdu)
echo "  Downloading Awami Nastaliq..."
curl -sL "https://software.sil.org/downloads/r/awami/AwamiNastaliq-3.200.zip" -o "$TEMP_DIR/awami-nastaliq.zip" 2>/dev/null || {
    echo "  Warning: Could not download Awami Nastaliq"
}
if [[ -f "$TEMP_DIR/awami-nastaliq.zip" ]]; then
    unzip -o -q "$TEMP_DIR/awami-nastaliq.zip" -d "$TEMP_DIR/awami" 2>/dev/null || true
    find "$TEMP_DIR/awami" -name "*.ttf" -exec cp {} "$FONT_DIR/" \; 2>/dev/null || true
fi

echo ""
echo "=== Phase 3: Regional Fonts ==="

# SolaimanLipi (Bangladesh Bengali - CRITICAL)
echo "  Downloading SolaimanLipi..."
curl -sL "https://raw.githubusercontent.com/nicjcb/Fonts/master/SolaimanLipi.ttf" -o "$FONT_DIR/SolaimanLipi.ttf" 2>/dev/null || {
    echo "  Warning: Could not download SolaimanLipi"
}

# Kalpurush (Bengali open-source)
echo "  Downloading Kalpurush..."
curl -sL "https://raw.githubusercontent.com/nicjcb/Fonts/master/kalpurush.ttf" -o "$FONT_DIR/Kalpurush.ttf" 2>/dev/null || {
    echo "  Warning: Could not download Kalpurush"
}

# Jomolhari (Tibetan)
echo "  Downloading Jomolhari..."
curl -sL "https://github.com/OpenPecha/tibetan-fonts/raw/main/Jomolhari/Jomolhari.ttf" -o "$FONT_DIR/Jomolhari.ttf" 2>/dev/null || {
    echo "  Warning: Could not download Jomolhari"
}

echo ""
echo "=== Phase 4: Cleanup ==="
rm -rf "$TEMP_DIR"

echo ""
echo "=== Phase 5: Updating font cache ==="
fc-cache -fv "$FONT_DIR"

echo ""
echo "=== Download Complete ==="
echo ""
echo "Fonts installed to: $FONT_DIR"
echo ""
echo "Verification:"
echo "  Total fonts in custom dir: $(find "$FONT_DIR" -name "*.ttf" -o -name "*.otf" 2>/dev/null | wc -l)"
echo ""
echo "Key fonts to verify:"
fc-list "$FONT_DIR" | head -20
