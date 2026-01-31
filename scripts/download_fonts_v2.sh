#!/bin/bash
# Enhanced font download script with reliable sources
# Usage: ./scripts/download_fonts_v2.sh

set -e

FONT_DIR="$HOME/.local/share/fonts/synthetic-gen"
mkdir -p "$FONT_DIR"

echo "=============================================="
echo "Font Download Script v2 - Reliable Sources"
echo "=============================================="

download_file() {
    local url="$1"
    local output="$2"
    echo "  Downloading: $(basename "$output")"
    if curl -sL --fail "$url" -o "$output" 2>/dev/null; then
        echo "    ✓ Success"
        return 0
    else
        echo "    ✗ Failed"
        return 1
    fi
}

echo ""
echo "=== 1. SIL International Fonts ==="

# Awami Nastaliq (CRITICAL for Urdu) - from GitHub releases
echo "Downloading Awami Nastaliq (Urdu)..."
cd /tmp
rm -rf awami-temp && mkdir awami-temp && cd awami-temp
if curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/AwamiNastaliq-Regular.ttf" -o "$FONT_DIR/AwamiNastaliq-Regular.ttf" 2>/dev/null; then
    echo "  ✓ Awami Nastaliq from nicjcb"
else
    # Try SIL direct
    curl -sL "https://software.sil.org/downloads/r/awami/AwamiNastaliq-3.200.zip" -o awami.zip 2>/dev/null && \
    unzip -q awami.zip && \
    find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
    echo "  ✓ Awami Nastaliq from SIL" || echo "  ✗ Awami Nastaliq failed"
fi

# Charis SIL (African languages)
echo "Downloading Charis SIL (African)..."
cd /tmp
rm -rf charis-temp && mkdir charis-temp && cd charis-temp
curl -sL "https://software.sil.org/downloads/r/charis/CharisSIL-6.200.zip" -o charis.zip 2>/dev/null && \
unzip -q charis.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Charis SIL" || echo "  ✗ Charis SIL failed"

# Gentium Plus (African/Linguistics)
echo "Downloading Gentium Plus (African)..."
cd /tmp
rm -rf gentium-temp && mkdir gentium-temp && cd gentium-temp
curl -sL "https://software.sil.org/downloads/r/gentium/GentiumPlus-6.200.zip" -o gentium.zip 2>/dev/null && \
unzip -q gentium.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Gentium Plus" || echo "  ✗ Gentium Plus failed"

# Padauk (Myanmar) - already in system, backup download
echo "Downloading Padauk (Myanmar)..."
cd /tmp
rm -rf padauk-temp && mkdir padauk-temp && cd padauk-temp
curl -sL "https://software.sil.org/downloads/r/padauk/Padauk-5.001.zip" -o padauk.zip 2>/dev/null && \
unzip -q padauk.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Padauk" || echo "  ✗ Padauk failed"

# Abyssinica SIL (Ethiopic)
echo "Downloading Abyssinica SIL (Ethiopic)..."
cd /tmp
rm -rf abyssinica-temp && mkdir abyssinica-temp && cd abyssinica-temp
curl -sL "https://software.sil.org/downloads/r/abyssinica/AbyssinicaSIL-2.201.zip" -o abyssinica.zip 2>/dev/null && \
unzip -q abyssinica.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Abyssinica SIL" || echo "  ✗ Abyssinica SIL failed"

# Scheherazade New (Arabic)
echo "Downloading Scheherazade New (Arabic)..."
cd /tmp
rm -rf scheherazade-temp && mkdir scheherazade-temp && cd scheherazade-temp
curl -sL "https://software.sil.org/downloads/r/scheherazade/ScheherazadeNew-4.000.zip" -o scheh.zip 2>/dev/null && \
unzip -q scheh.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Scheherazade New" || echo "  ✗ Scheherazade New failed"

# Andika (Literacy font)
echo "Downloading Andika (Literacy)..."
cd /tmp
rm -rf andika-temp && mkdir andika-temp && cd andika-temp
curl -sL "https://software.sil.org/downloads/r/andika/Andika-6.200.zip" -o andika.zip 2>/dev/null && \
unzip -q andika.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Andika" || echo "  ✗ Andika failed"

# Doulos SIL (Times-like with Unicode)
echo "Downloading Doulos SIL..."
cd /tmp
rm -rf doulos-temp && mkdir doulos-temp && cd doulos-temp
curl -sL "https://software.sil.org/downloads/r/doulos/DoulosSIL-6.200.zip" -o doulos.zip 2>/dev/null && \
unzip -q doulos.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Doulos SIL" || echo "  ✗ Doulos SIL failed"

echo ""
echo "=== 2. Google Fonts from GitHub ==="

# PT Sans/Serif (Russian)
echo "Downloading PT Sans/Serif (Russian)..."
curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/PTSans-Regular.ttf" -o "$FONT_DIR/PTSans-Regular.ttf" 2>/dev/null && echo "  ✓ PT Sans Regular" || echo "  ✗ PT Sans failed"
curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/PTSans-Bold.ttf" -o "$FONT_DIR/PTSans-Bold.ttf" 2>/dev/null && echo "  ✓ PT Sans Bold" || true
curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/PTSerif-Regular.ttf" -o "$FONT_DIR/PTSerif-Regular.ttf" 2>/dev/null && echo "  ✓ PT Serif Regular" || true

# Roboto
echo "Downloading Roboto..."
curl -sL "https://github.com/googlefonts/roboto/releases/download/v2.138/roboto-android.zip" -o /tmp/roboto.zip 2>/dev/null && \
cd /tmp && unzip -q -o roboto.zip -d roboto-temp && \
cp roboto-temp/*.ttf "$FONT_DIR/" 2>/dev/null && \
echo "  ✓ Roboto" || echo "  ✗ Roboto failed"

# Fira Sans (Bulgarian Cyrillic)
echo "Downloading Fira Sans (Bulgarian)..."
cd /tmp
rm -rf fira-temp && mkdir fira-temp && cd fira-temp
curl -sL "https://github.com/mozilla/Fira/archive/refs/tags/4.202.tar.gz" -o fira.tar.gz 2>/dev/null && \
tar -xzf fira.tar.gz && \
find . -name "*.ttf" -path "*ttf*" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Fira Sans" || echo "  ✗ Fira Sans failed"

# Open Sans
echo "Downloading Open Sans..."
curl -sL "https://github.com/googlefonts/opensans/archive/refs/heads/main.zip" -o /tmp/opensans.zip 2>/dev/null && \
cd /tmp && rm -rf opensans-temp && mkdir opensans-temp && \
unzip -q opensans.zip -d opensans-temp && \
find opensans-temp -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Open Sans" || echo "  ✗ Open Sans failed"

# Amiri (Arabic calligraphic)
echo "Downloading Amiri (Arabic)..."
cd /tmp
rm -rf amiri-temp && mkdir amiri-temp && cd amiri-temp
curl -sL "https://github.com/aliftype/amiri/releases/download/1.000/Amiri-1.000.zip" -o amiri.zip 2>/dev/null && \
unzip -q amiri.zip && \
find . -name "*.ttf" -exec cp {} "$FONT_DIR/" \; && \
echo "  ✓ Amiri" || echo "  ✗ Amiri failed"

echo ""
echo "=== 3. Regional/Specialized Fonts ==="

# Jomolhari (Tibetan) - from OpenPecha
echo "Downloading Jomolhari (Tibetan)..."
curl -sL "https://github.com/OpenPecha/tibetan-fonts/raw/main/Jomolhari/Jomolhari.ttf" -o "$FONT_DIR/Jomolhari.ttf" 2>/dev/null && \
echo "  ✓ Jomolhari" || echo "  ✗ Jomolhari failed"

# Lohit fonts from Fedora (if not in apt)
echo "Downloading Lohit Devanagari..."
curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/Lohit-Devanagari.ttf" -o "$FONT_DIR/Lohit-Devanagari.ttf" 2>/dev/null && \
echo "  ✓ Lohit Devanagari" || echo "  ✗ Lohit Devanagari failed"

# Bengali fonts - SolaimanLipi from OmicronLab
echo "Downloading SolaimanLipi (Bengali)..."
curl -sL "https://github.com/nicjcb/Fonts/raw/master/SolaimanLipi.ttf" -o "$FONT_DIR/SolaimanLipi.ttf" 2>/dev/null && \
echo "  ✓ SolaimanLipi" || echo "  ✗ SolaimanLipi failed"

# Kalpurush (Bengali)
echo "Downloading Kalpurush (Bengali)..."
curl -sL "https://github.com/nicjcb/Fonts/raw/master/kalpurush.ttf" -o "$FONT_DIR/Kalpurush.ttf" 2>/dev/null && \
echo "  ✓ Kalpurush" || echo "  ✗ Kalpurush failed"

# Nanum Gothic (Korean) from Google
echo "Downloading Nanum Gothic (Korean)..."
cd /tmp
rm -rf nanum-temp && mkdir nanum-temp && cd nanum-temp
curl -sL "https://github.com/nicjcb/Fonts/raw/master/fonts/NanumGothic.ttf" -o "$FONT_DIR/NanumGothic.ttf" 2>/dev/null && \
echo "  ✓ Nanum Gothic" || echo "  ✗ Nanum Gothic failed"

echo ""
echo "=== 4. Cleanup ==="
rm -rf /tmp/*-temp /tmp/*.zip /tmp/*.tar.gz 2>/dev/null || true

echo ""
echo "=== 5. Update font cache ==="
fc-cache -fv "$FONT_DIR"

echo ""
echo "=== Installation Summary ==="
echo ""
echo "Fonts installed to: $FONT_DIR"
FONT_COUNT=$(find "$FONT_DIR" -name "*.ttf" -o -name "*.otf" 2>/dev/null | wc -l)
echo "Total fonts downloaded: $FONT_COUNT"
echo ""
echo "Downloaded fonts:"
ls -la "$FONT_DIR"/*.ttf 2>/dev/null | awk '{print "  " $NF}' | sed 's|.*/||'
