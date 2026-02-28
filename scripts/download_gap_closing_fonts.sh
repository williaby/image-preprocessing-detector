#!/usr/bin/env bash
# Download open-source fonts to close per-script diversity gaps.
# All fonts are SIL OFL licensed from Google Fonts GitHub repo.
#
# Usage: bash scripts/download_gap_closing_fonts.sh
#
# Source: https://github.com/google/fonts (SIL OFL 1.1)

set -euo pipefail

DEST="${1:-fonts/synthetic-gen}"
GHRAW="https://raw.githubusercontent.com/google/fonts/main/ofl"

mkdir -p "$DEST"

echo "=== Downloading gap-closing fonts to $DEST ==="

# Helper: download a single .ttf from Google Fonts GitHub
dl() {
    local family_dir="$1"
    local filename="$2"
    local dest_name="${3:-$filename}"
    if [ -f "$DEST/$dest_name" ]; then
        echo "  [skip] $dest_name"
        return
    fi
    echo "  [get]  $dest_name"
    curl -sL "${GHRAW}/${family_dir}/${filename}" -o "$DEST/$dest_name" 2>/dev/null
    # Verify it's a real font (not a 404 HTML page)
    local magic
    magic=$(head -c4 "$DEST/$dest_name" 2>/dev/null | xxd -p 2>/dev/null || echo "")
    if [[ "$magic" != "00010000" && "$magic" != "4f54544f" && "$magic" != "74727565" ]]; then
        echo "    WARNING: $dest_name may not be a valid font (magic: $magic)"
        rm -f "$DEST/$dest_name"
    fi
}

echo ""
echo "--- TAMIL (Taml) ---"
dl "catamaran" "Catamaran%5Bwght%5D.ttf" "Catamaran[wght].ttf"
dl "catamaran" "Catamaran-Regular.ttf"
dl "muktamalar" "MuktaMalar-Regular.ttf"
dl "muktamalar" "MuktaMalar-Bold.ttf"
dl "hindmadurai" "HindMadurai-Regular.ttf"
dl "hindmadurai" "HindMadurai-Bold.ttf"
dl "hindmadurai" "HindMadurai-Light.ttf"
dl "arimamadurai" "ArimaMadurai-Regular.ttf"
dl "arimamadurai" "ArimaMadurai-Bold.ttf"
dl "kavivanar" "Kavivanar-Regular.ttf"

echo ""
echo "--- TELUGU (Telu) ---"
dl "ntr" "NTR-Regular.ttf"
dl "ramabhadra" "Ramabhadra-Regular.ttf"
dl "mandali" "Mandali-Regular.ttf"
dl "hindguntur" "HindGuntur-Regular.ttf"
dl "hindguntur" "HindGuntur-Bold.ttf"
dl "hindguntur" "HindGuntur-Light.ttf"

echo ""
echo "--- GUJARATI (Gujr) ---"
dl "hindvadodara" "HindVadodara-Regular.ttf"
dl "hindvadodara" "HindVadodara-Bold.ttf"
dl "hindvadodara" "HindVadodara-Light.ttf"
dl "muktavaani" "MuktaVaani-Regular.ttf"
dl "muktavaani" "MuktaVaani-Bold.ttf"
dl "rasa" "Rasa%5Bwght%5D.ttf" "Rasa[wght].ttf"
dl "rasa" "Rasa-Regular.ttf"
dl "baloobhai2" "BalooBhai2-Regular.ttf"
dl "baloobhai2" "BalooBhai2-Bold.ttf"

echo ""
echo "--- KANNADA (Knda) ---"
dl "timmana" "Timmana-Regular.ttf"
dl "balootamma2" "BalooTamma2-Regular.ttf"
dl "balootamma2" "BalooTamma2-Bold.ttf"

echo ""
echo "--- MALAYALAM (Mlym) ---"
dl "manjari" "Manjari-Regular.ttf"
dl "manjari" "Manjari-Bold.ttf"
dl "manjari" "Manjari-Thin.ttf"

echo ""
echo "--- ODIA (Orya) ---"
dl "baloobhaina2" "BalooBhaina2-Regular.ttf"
dl "baloobhaina2" "BalooBhaina2-Bold.ttf"

echo ""
echo "--- SINHALA (Sinh) ---"
dl "abhayalibre" "AbhayaLibre-Regular.ttf"
dl "abhayalibre" "AbhayaLibre-Bold.ttf"
dl "abhayalibre" "AbhayaLibre-SemiBold.ttf"
dl "yaldevi" "Yaldevi%5Bwght%5D.ttf" "Yaldevi[wght].ttf"
dl "yaldevi" "Yaldevi-Regular.ttf"

echo ""
echo "--- GURMUKHI (Guru) ---"
dl "muktamahee" "MuktaMahee-Regular.ttf"
dl "muktamahee" "MuktaMahee-Bold.ttf"
dl "muktamahee" "MuktaMahee-Light.ttf"
dl "baloopaaji2" "BalooPaaji2-Regular.ttf"
dl "baloopaaji2" "BalooPaaji2-Bold.ttf"

echo ""
echo "--- DEVANAGARI (Deva) ---"
dl "tirodevanagarihindinormal" "TiroDevanagariHindi-Regular.ttf"
dl "tirodevanagarihindinormal" "TiroDevanagariHindi-Italic.ttf"
dl "hind" "Hind-Regular.ttf"
dl "hind" "Hind-Bold.ttf"
dl "hind" "Hind-Light.ttf"
dl "mukta" "Mukta-Regular.ttf"
dl "mukta" "Mukta-Bold.ttf"
dl "mukta" "Mukta-Light.ttf"
dl "baloo2" "Baloo2-Regular.ttf"
dl "baloo2" "Baloo2-Bold.ttf"

echo ""
echo "--- THAI (Thai) ---"
dl "kanit" "Kanit-Regular.ttf"
dl "kanit" "Kanit-Bold.ttf"
dl "kanit" "Kanit-Light.ttf"
dl "kanit" "Kanit-Italic.ttf"
dl "pridi" "Pridi-Regular.ttf"
dl "pridi" "Pridi-Bold.ttf"
dl "pridi" "Pridi-Light.ttf"
dl "baijamjuree" "BaiJamjuree-Regular.ttf"
dl "baijamjuree" "BaiJamjuree-Bold.ttf"
dl "mitr" "Mitr-Regular.ttf"
dl "mitr" "Mitr-Bold.ttf"

echo ""
echo "--- KHMER (Khmr) ---"
dl "battambang" "Battambang-Regular.ttf"
dl "battambang" "Battambang-Bold.ttf"
dl "battambang" "Battambang-Light.ttf"
dl "content" "Content-Regular.ttf"
dl "content" "Content-Bold.ttf"
dl "moul" "Moul-Regular.ttf"

echo ""
echo "--- ARABIC (Arab) ---"
dl "mada" "Mada-Regular.ttf"
dl "mada" "Mada-Bold.ttf"
dl "mada" "Mada-Light.ttf"
dl "tajawal" "Tajawal-Regular.ttf"
dl "tajawal" "Tajawal-Bold.ttf"
dl "tajawal" "Tajawal-Light.ttf"
dl "elmessiri" "ElMessiri%5Bwght%5D.ttf" "ElMessiri[wght].ttf"
dl "elmessiri" "ElMessiri-Regular.ttf"

echo ""
echo "--- KOREAN (Hang) ---"
dl "nanummyeongjo" "NanumMyeongjo-Regular.ttf"
dl "nanummyeongjo" "NanumMyeongjo-Bold.ttf"
dl "nanummyeongjo" "NanumMyeongjo-ExtraBold.ttf"

echo ""
echo "--- GREEK (Grek) ---"
dl "gfsneohellenic" "GFSNeohellenic-Regular.ttf"
dl "gfsneohellenic" "GFSNeohellenic-Bold.ttf"
dl "gfsneohellenic" "GFSNeohellenic-BoldItalic.ttf"

echo ""
echo "=== Download complete ==="
TOTAL_FONTS=$(find "$DEST" -maxdepth 1 \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | wc -l)
echo "Total bundled fonts: $TOTAL_FONTS"
echo "New fonts added: $((TOTAL_FONTS - 147))"
