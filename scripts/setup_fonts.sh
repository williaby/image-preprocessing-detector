#!/bin/bash
# Font setup script for synthetic document generation
# Installs all required fonts for 27-script coverage
#
# Usage: ./scripts/setup_fonts.sh
#
# This script:
# 1. Installs Noto font packages via apt (requires sudo)
# 2. Installs additional regional/script-specific packages
# 3. Copies bundled handwriting/mimicry fonts to user fonts
# 4. Updates font cache

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLED_FONTS="$REPO_ROOT/fonts/synthetic-gen"
USER_FONTS="$HOME/.local/share/fonts/synthetic-gen"

# Constant for separator line (avoid duplication)
SEPARATOR_LINE="=============================================="

echo "$SEPARATOR_LINE"
echo "Font Setup for Synthetic Document Generation"
echo "$SEPARATOR_LINE"
echo ""

# Check if running with sudo capability
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        echo "This script requires sudo for apt package installation."
        echo "Please run with sudo or enter password when prompted."
        echo ""
    fi
    return 0
}

# Step 1: Install Noto font packages
install_noto_fonts() {
    echo "=== Step 1: Installing Noto Font Packages ==="
    echo ""

    # Core Noto packages (provides 27-script coverage)
    NOTO_PACKAGES=(
        # Core packages
        fonts-noto
        fonts-noto-core
        fonts-noto-extra
        fonts-noto-mono
        fonts-noto-ui-core
        fonts-noto-ui-extra
        fonts-noto-unhinted
        # CJK (Chinese, Japanese, Korean)
        fonts-noto-cjk
        fonts-noto-cjk-extra
        # Color emoji (optional but useful)
        fonts-noto-color-emoji
    )

    echo "Installing packages: ${NOTO_PACKAGES[*]}"
    sudo apt-get update
    sudo apt-get install -y "${NOTO_PACKAGES[@]}"
    echo "  ✓ Noto fonts installed"
    echo ""
    return 0
}

# Step 2: Install additional regional font packages
install_regional_fonts() {
    echo "=== Step 2: Installing Regional Font Packages ==="
    echo ""

    REGIONAL_PACKAGES=(
        # Arabic
        fonts-arabeyes
        fonts-hosny-amiri
        # Bengali (Bangladesh)
        fonts-beng
        fonts-beng-extra
        # Devanagari
        fonts-lohit-deva
        # Ethiopic
        fonts-sil-abyssinica
        # Georgian
        fonts-dejavu
        # Gujarati
        fonts-lohit-gujr
        # Gurmukhi (Punjabi)
        fonts-lohit-guru
        # Kannada
        fonts-lohit-knda
        # Khmer
        fonts-khmeros
        # Malayalam
        fonts-lohit-mlym
        # Myanmar
        fonts-sil-padauk
        # Odia
        fonts-lohit-orya
        # Sinhala
        fonts-lklug-sinhala
        # Tamil
        fonts-lohit-taml
        fonts-lohit-taml-classical
        # Telugu
        fonts-lohit-telu
        # Thai
        fonts-thai-tlwg
        # Tibetan
        fonts-tibetan-machine
        # Russian/Cyrillic
        fonts-paratype
        # Liberation (Arial/Times equivalents)
        fonts-liberation
        fonts-liberation2
    )

    echo "Installing packages: ${REGIONAL_PACKAGES[*]}"
    sudo apt-get install -y "${REGIONAL_PACKAGES[@]}" 2>/dev/null || {
        echo "  Note: Some packages may not be available in your distribution"
        echo "  Continuing with available packages..."
        for pkg in "${REGIONAL_PACKAGES[@]}"; do
            sudo apt-get install -y "$pkg" 2>/dev/null || true
        done
    }
    echo "  ✓ Regional fonts installed"
    echo ""
    return 0
}

# Step 3: Copy bundled fonts (handwriting, mimicry, SIL)
copy_bundled_fonts() {
    echo "=== Step 3: Copying Bundled Fonts ==="
    echo ""

    if [[ -d "$BUNDLED_FONTS" ]]; then
        mkdir -p "$USER_FONTS"
        cp -n "$BUNDLED_FONTS"/*.ttf "$USER_FONTS/" 2>/dev/null || true
        cp -n "$BUNDLED_FONTS"/*.otf "$USER_FONTS/" 2>/dev/null || true
        BUNDLED_COUNT=$(ls -1 "$BUNDLED_FONTS"/*.ttf 2>/dev/null | wc -l)
        echo "  ✓ Copied $BUNDLED_COUNT bundled fonts to $USER_FONTS"
    else
        echo "  Warning: Bundled fonts directory not found at $BUNDLED_FONTS"
        echo "  Skipping bundled font copy"
    fi
    echo ""
    return 0
}

# Step 4: Update font cache
update_font_cache() {
    echo "=== Step 4: Updating Font Cache ==="
    echo ""

    fc-cache -fv
    echo "  ✓ Font cache updated"
    echo ""
    return 0
}

# Step 5: Verify installation
verify_installation() {
    echo "=== Step 5: Verification ==="
    echo ""

    # Check total font count
    TOTAL_FONTS=$(fc-list | wc -l)
    echo "Total fonts available: $TOTAL_FONTS"

    # Check critical scripts
    echo ""
    echo "Critical script coverage:"

    SCRIPTS=(
        "NotoSansArabic:Arab"
        "NotoSansDevanagari:Deva"
        "NotoSansBengali:Beng"
        "NotoSansCJKsc:Hans"
        "NotoSansCJKjp:Jpan"
        "NotoSansCJKkr:Kore"
        "NotoSansHebrew:Hebr"
        "NotoSansTibetan:Tibt"
        "NotoSansThai:Thai"
        "NotoSansEthiopic:Ethi"
    )

    for entry in "${SCRIPTS[@]}"; do
        FONT="${entry%%:*}"
        SCRIPT="${entry##*:}"
        if fc-list | grep -qi "$FONT"; then
            echo "  ✓ $SCRIPT ($FONT)"
        else
            echo "  ✗ $SCRIPT ($FONT) - MISSING"
        fi
    done

    # Check handwriting fonts
    echo ""
    echo "Handwriting fonts:"
    HANDWRITING=(
        "BadScript:Cyrillic"
        "Caveat:Latin"
        "Kalam:Devanagari"
        "ArefRuqaa:Arabic"
        "MaShanZheng:Chinese"
    )

    for entry in "${HANDWRITING[@]}"; do
        FONT="${entry%%:*}"
        SCRIPT="${entry##*:}"
        if fc-list | grep -qi "$FONT"; then
            echo "  ✓ $FONT ($SCRIPT)"
        else
            echo "  ✗ $FONT ($SCRIPT) - MISSING"
        fi
    done

    echo ""
    return 0
}

# Main execution
main() {
    check_sudo
    install_noto_fonts
    install_regional_fonts
    copy_bundled_fonts
    update_font_cache
    verify_installation

    echo "$SEPARATOR_LINE"
    echo "Font Setup Complete!"
    echo "$SEPARATOR_LINE"
    echo ""
    echo "Fonts installed to:"
    echo "  - System: /usr/share/fonts/"
    echo "  - User:   $USER_FONTS"
    echo ""
    echo "The FontManager will automatically discover all fonts."
    return 0
}

main "$@"
