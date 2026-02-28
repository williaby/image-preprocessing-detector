#!/bin/bash
# Download gap-closing fonts for remaining 6 underserved scripts
# All fonts are SIL OFL 1.1 unless noted otherwise
set -euo pipefail

FONTS_DIR="fonts/synthetic-gen"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

downloaded=0
failed=0

download_font() {
    local url="$1"
    local filename="$2"
    local script="$3"

    if [ -f "$FONTS_DIR/$filename" ]; then
        echo "  SKIP (exists): $filename"
        return
    fi

    echo "  Downloading: $filename ($script)"
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

    if [ -f "$FONTS_DIR/$target_name" ]; then
        echo "  SKIP (exists): $target_name"
        return
    fi

    echo "  Downloading ZIP for: $target_name ($script)"
    local zipfile="$TEMP_DIR/download.zip"
    if curl -sL --fail -o "$zipfile" "$url" 2>/dev/null; then
        # Extract matching file
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

download_from_github_release() {
    local repo="$1"
    local asset_pattern="$2"
    local ttf_pattern="$3"
    local target_name="$4"
    local script="$5"

    if [ -f "$FONTS_DIR/$target_name" ]; then
        echo "  SKIP (exists): $target_name"
        return
    fi

    echo "  Fetching latest release from: $repo ($script)"
    local release_url
    release_url=$(curl -sL "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null | \
        python3 -c "import sys,json; assets=json.load(sys.stdin).get('assets',[]); [print(a['browser_download_url']) for a in assets if '$asset_pattern' in a['name'].lower()]" 2>/dev/null | head -1)

    if [ -z "$release_url" ]; then
        echo "    FAIL: No matching release asset for $asset_pattern"
        ((failed++)) || true
        return
    fi

    download_from_zip "$release_url" "$ttf_pattern" "$target_name" "$script"
}

echo "=== Gap-Closing Font Downloads v2 ==="
echo "Target directory: $FONTS_DIR"
echo ""

# --- KANNADA (Knda) — need 1 more family ---
echo "--- Kannada (Knda) ---"
GF_BASE="https://raw.githubusercontent.com/google/fonts/main/ofl"
download_font "$GF_BASE/hindmysuru/HindMysuru-Regular.ttf" "HindMysuru-Regular.ttf" "Knda"
download_font "$GF_BASE/hindmysuru/HindMysuru-Bold.ttf" "HindMysuru-Bold.ttf" "Knda"
download_font "$GF_BASE/benne/Benne-Regular.ttf" "Benne-Regular.ttf" "Knda"
echo ""

# --- ODIA (Orya) — need 2 more families ---
echo "--- Odia (Orya) ---"
download_font "$GF_BASE/anekodia/AnekOdia%5Bwdth%2Cwght%5D.ttf" "AnekOdia-Variable.ttf" "Orya"
download_font "$GF_BASE/alkatra/Alkatra%5Bwght%5D.ttf" "Alkatra-Variable.ttf" "Orya"
echo ""

# --- TIBETAN (Tibt) — need 4 more families ---
echo "--- Tibetan (Tibt) ---"
download_font "$GF_BASE/uchen/Uchen-Regular.ttf" "Uchen-Regular.ttf" "Tibt"
# DDC Uchen from fontlibrary.org
download_from_zip "https://fontlibrary.org/assets/downloads/ddc-uchen/4bbdbe2c3375fe64e9796c0b5e111680/ddc-uchen.zip" ".ttf" "DDCUchen-Regular.ttf" "Tibt"
echo ""

# --- CHEROKEE (Cher) — ecosystem gap, only NotoSansCherokee is OFL ---
echo "--- Cherokee (Cher) ---"
echo "  NOTE: Only 1 OFL Cherokee font exists (NotoSansCherokee)."
echo "  No additional OFL-licensed Cherokee fonts found."
echo ""

# --- CANADIAN SYLLABICS (Cans) — need 2 more families ---
echo "--- Canadian Syllabics (Cans) ---"
# BJCree from SIL International (SIL OFL 1.1)
download_from_zip "https://software.sil.org/downloads/r/bjcree/BJCree-7.000.zip" "bjcree-regular" "BJCree-Regular.ttf" "Cans"
echo ""

# --- ETHIOPIC (Ethi) — need 2 more families ---
echo "--- Ethiopic (Ethi) ---"
# Brana from raeytype (SIL OFL 1.1)
download_from_github_release "raeytype/brana" ".zip" ".ttf" "Brana-Regular.ttf" "Ethi"
# Geez Manuscript Zemen from geezorg/emufi (SIL OFL 1.1)
download_from_github_release "geezorg/emufi" ".zip" ".ttf" "GeezManuscriptZemen-Regular.ttf" "Ethi"
echo ""

echo "=== Summary ==="
echo "Downloaded: $downloaded new fonts"
echo "Failed: $failed"
echo "Total bundled: $(find "$FONTS_DIR" -maxdepth 1 \( -name '*.ttf' -o -name '*.otf' \) 2>/dev/null | wc -l) fonts"
