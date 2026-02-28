#!/bin/bash
# Download adversarial fonts for V4 Font Diversity Strategy
# These fonts are designed to confuse script identification models via:
#   - Cross-script design unification
#   - Historical/archaic letterforms
#   - Calligraphic style transfer
#   - Structural feature destruction
# All fonts are SIL OFL 1.1
set -euo pipefail

FONTS_DIR="fonts/synthetic-gen"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

downloaded=0
failed=0
skipped=0

download_font() {
    local url="$1"
    local filename="$2"
    local script="$3"
    local attack_vector="$4"

    if [ -f "$FONTS_DIR/$filename" ]; then
        echo "  SKIP (exists): $filename"
        ((skipped++)) || true
        return
    fi

    echo "  Downloading: $filename ($script — $attack_vector)"
    if curl -sL --fail -o "$FONTS_DIR/$filename" "$url" 2>/dev/null; then
        # Verify it's a font file (starts with font magic bytes, not HTML)
        local magic
        magic=$(xxd -l 4 -p "$FONTS_DIR/$filename" 2>/dev/null || echo "")
        if [[ "$magic" == "00010000" || "$magic" == "4f54544f" || "$magic" == "74727565" || "$magic" == "74746366" || "$magic" == "774f4632" || "$magic" == "774f4646" ]]; then
            echo "    OK: $filename ($(stat -c%s "$FONTS_DIR/$filename") bytes)"
            ((downloaded++)) || true
        else
            echo "    FAIL: $filename (not a valid font file, removing)"
            rm -f "$FONTS_DIR/$filename"
            ((failed++)) || true
        fi
    else
        echo "    FAIL: $filename (download failed)"
        ((failed++)) || true
    fi
}

download_from_zip() {
    local url="$1"
    local pattern="$2"
    local target_name="$3"
    local script="$4"
    local attack_vector="$5"

    if [ -f "$FONTS_DIR/$target_name" ]; then
        echo "  SKIP (exists): $target_name"
        ((skipped++)) || true
        return
    fi

    echo "  Downloading ZIP for: $target_name ($script — $attack_vector)"
    local zipfile="$TEMP_DIR/download.zip"
    if curl -sL --fail -o "$zipfile" "$url" 2>/dev/null; then
        local found_file
        found_file=$(unzip -l "$zipfile" 2>/dev/null | grep -i "$pattern" | head -1 | awk '{print $NF}')
        if [ -n "$found_file" ]; then
            unzip -o -j "$zipfile" "$found_file" -d "$TEMP_DIR" 2>/dev/null
            local basename
            basename=$(basename "$found_file")
            if [ -f "$TEMP_DIR/$basename" ]; then
                cp "$TEMP_DIR/$basename" "$FONTS_DIR/$target_name"
                echo "    OK: $target_name ($(stat -c%s "$FONTS_DIR/$target_name") bytes)"
                ((downloaded++)) || true
            else
                echo "    FAIL: Could not extract $pattern from ZIP"
                ((failed++)) || true
            fi
        else
            echo "    FAIL: Pattern '$pattern' not found in ZIP"
            ((failed++)) || true
        fi
        rm -f "$zipfile" "$TEMP_DIR"/*.ttf "$TEMP_DIR"/*.otf 2>/dev/null || true
    else
        echo "    FAIL: ZIP download failed"
        ((failed++)) || true
    fi
}

GF_BASE="https://raw.githubusercontent.com/google/fonts/main/ofl"

echo "=== Adversarial Font Downloads (V4 Font Diversity) ==="
echo "Target directory: $FONTS_DIR"
echo ""

# --- PRIORITY 1: Core adversarial fonts (11 fonts) ---

echo "--- Latin: Historical Blackletter ---"
download_font "$GF_BASE/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf" \
    "UnifrakturMaguntia-Book.ttf" "Latn" "Historical blackletter"
echo ""

echo "--- Latin+Cyrillic: Cross-script Unification ---"
download_font "$GF_BASE/lobster/Lobster-Regular.ttf" \
    "Lobster-Regular.ttf" "Cyrl+Latn" "Cross-script unification"
echo ""

echo "--- Devanagari: Structural Destruction ---"
download_font "$GF_BASE/jaini/Jaini-Regular.ttf" \
    "Jaini-Regular.ttf" "Deva" "Structural destruction"
download_font "$GF_BASE/modak/Modak-Regular.ttf" \
    "Modak-Regular.ttf" "Deva" "Structural destruction"
echo ""

echo "--- Arabic: Structural Destruction ---"
download_font "$GF_BASE/reemkufi/ReemKufi%5Bwght%5D.ttf" \
    "ReemKufi[wght].ttf" "Arab" "Structural destruction"
echo ""

echo "--- Sinhala: Structural Destruction ---"
download_font "$GF_BASE/sticknobills/StickNoBills%5Bwght%5D.ttf" \
    "StickNoBills[wght].ttf" "Sinh" "Structural destruction"
echo ""

echo "--- Latin: Calligraphic Transfer ---"
download_font "$GF_BASE/comforterbrush/ComforterBrush-Regular.ttf" \
    "ComforterBrush-Regular.ttf" "Latn" "Calligraphic transfer"
echo ""

echo "--- Latin: Cross-script Confusion ---"
download_font "$GF_BASE/cinzeldecorative/CinzelDecorative-Regular.ttf" \
    "CinzelDecorative-Regular.ttf" "Latn" "Cross-script confusion (all-caps, Deva-like shirorekha)"
download_font "$GF_BASE/monsieurladoulaise/MonsieurLaDoulaise-Regular.ttf" \
    "MonsieurLaDoulaise-Regular.ttf" "Latn" "Cross-script confusion (Arabic-like flow)"
echo ""

echo "--- Thai: Cross-script Confusion ---"
download_font "$GF_BASE/charmonman/Charmonman-Regular.ttf" \
    "Charmonman-Regular.ttf" "Thai" "Cross-script confusion"
echo ""

echo "--- Greek: Cross-script Confusion ---"
# GFS Bodoni is NOT on Google Fonts GitHub — it's from the Greek Font Society
# Download from greekfontsociety-gfs.gr and extract from ZIP
if [ -f "$FONTS_DIR/GFSBodoni-Regular.ttf" ]; then
    echo "  SKIP (exists): GFSBodoni-Regular.ttf"
    ((skipped++)) || true
else
    echo "  Downloading ZIP for: GFSBodoni-Regular.ttf (Grek — Cross-script confusion)"
    if curl -sL --fail -o "$TEMP_DIR/GFS_Bodoni.zip" "https://greekfontsociety-gfs.gr/_assets/fonts/GFS_Bodoni.zip" 2>/dev/null; then
        python3 -c "
import zipfile, shutil, sys
with zipfile.ZipFile('$TEMP_DIR/GFS_Bodoni.zip') as zf:
    for name in zf.namelist():
        if name.endswith('GFSBodoni.ttf'):
            with zf.open(name) as src, open('$FONTS_DIR/GFSBodoni-Regular.ttf', 'wb') as dst:
                shutil.copyfileobj(src, dst)
            sys.exit(0)
    sys.exit(1)
" 2>/dev/null
        if [ -f "$FONTS_DIR/GFSBodoni-Regular.ttf" ]; then
            echo "    OK: GFSBodoni-Regular.ttf ($(stat -c%s "$FONTS_DIR/GFSBodoni-Regular.ttf") bytes)"
            ((downloaded++)) || true
        else
            echo "    FAIL: GFSBodoni-Regular.ttf (extraction failed)"
            ((failed++)) || true
        fi
        rm -f "$TEMP_DIR/GFS_Bodoni.zip"
    else
        echo "    FAIL: GFSBodoni-Regular.ttf (download failed)"
        ((failed++)) || true
    fi
fi
echo ""

# --- PRIORITY 2: Additional adversarial fonts ---

echo "--- Priority 2: Additional Adversarial Fonts ---"
download_font "$GF_BASE/gulzar/Gulzar-Regular.ttf" \
    "Gulzar-Regular.ttf" "Arab" "Calligraphic transfer (Nastaliq influence)"
download_font "$GF_BASE/lakkireddy/LakkiReddy-Regular.ttf" \
    "LakkiReddy-Regular.ttf" "Telu" "Structural destruction"
download_font "$GF_BASE/ebgaramond/EBGaramond%5Bwght%5D.ttf" \
    "EBGaramond[wght].ttf" "Latn+Grek+Cyrl" "Cross-script unification (3-script harmonized design)"
echo ""

# --- Verify already-bundled adversarial fonts ---

echo "--- Verifying Already-Bundled Adversarial Fonts ---"
bundled_ok=0
bundled_missing=0
for font in "Pacifico-Regular.ttf" "LiuJianMaoCao-Regular.ttf" "NanumBrushScript-Regular.ttf" "Moul-Regular.ttf"; do
    if [ -f "$FONTS_DIR/$font" ]; then
        echo "  OK (bundled): $font"
        ((bundled_ok++)) || true
    else
        echo "  MISSING (expected bundled): $font"
        ((bundled_missing++)) || true
    fi
done
echo ""

echo "=== Summary ==="
echo "Downloaded: $downloaded new fonts"
echo "Skipped (already exist): $skipped"
echo "Failed: $failed"
echo "Bundled verified: $bundled_ok (missing: $bundled_missing)"
echo "Total in directory: $(find "$FONTS_DIR" -maxdepth 1 \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | wc -l) fonts"
