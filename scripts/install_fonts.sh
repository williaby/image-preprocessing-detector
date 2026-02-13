#!/bin/bash
# Font installation script for synthetic document generation
# Usage: sudo ./scripts/install_fonts.sh

set -e

echo "=============================================="
echo "Font Installation for Synthetic Doc Generator"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./scripts/install_fonts.sh)"
    exit 1
fi

echo ""
echo "=== Phase 1: Installing package fonts ==="

# Update package list
apt-get update -qq

# Liberation fonts (Arial/Times/Courier equivalents)
echo "Installing Liberation fonts..."
apt-get install -y -qq fonts-liberation fonts-liberation2

# Lohit Indic fonts
echo "Installing Lohit Indic fonts..."
apt-get install -y -qq \
    fonts-lohit-deva \
    fonts-lohit-beng \
    fonts-lohit-taml \
    fonts-lohit-telu \
    fonts-lohit-knda \
    fonts-lohit-mlym \
    fonts-lohit-gujr \
    fonts-lohit-guru \
    fonts-lohit-orya 2>/dev/null || echo "Some Lohit fonts not available"

# Google/Adobe CJK fonts
echo "Installing CJK fonts..."
apt-get install -y -qq \
    fonts-noto-cjk \
    fonts-noto-cjk-extra 2>/dev/null || echo "CJK fonts not available"

# SIL fonts
echo "Installing SIL fonts..."
apt-get install -y -qq \
    fonts-sil-charis \
    fonts-sil-gentiumplus \
    fonts-sil-andika \
    fonts-sil-doulos \
    fonts-sil-scheherazade \
    fonts-sil-padauk \
    fonts-sil-abyssinica 2>/dev/null || echo "Some SIL fonts not available"

# Thai fonts
echo "Installing Thai fonts..."
apt-get install -y -qq \
    fonts-tlwg-sarabun \
    fonts-tlwg-garuda \
    fonts-tlwg-loma \
    fonts-thai-tlwg 2>/dev/null || echo "Thai fonts not available"

# Khmer fonts
echo "Installing Khmer fonts..."
apt-get install -y -qq fonts-khmeros 2>/dev/null || echo "Khmer fonts not available"

# Arabic fonts
echo "Installing Arabic fonts..."
apt-get install -y -qq \
    fonts-hosny-amiri 2>/dev/null || echo "Arabic fonts not available"

# Additional Google fonts from packages
echo "Installing additional fonts..."
apt-get install -y -qq \
    fonts-roboto \
    fonts-open-sans \
    fonts-firacode \
    fonts-freefont-ttf 2>/dev/null || echo "Some additional fonts not available"

# Tibetan fonts
echo "Installing Tibetan fonts..."
apt-get install -y -qq fonts-tibetan-machine 2>/dev/null || echo "Tibetan fonts not available"

# Myanmar fonts
echo "Installing Myanmar fonts..."
apt-get install -y -qq fonts-sil-padauk 2>/dev/null || echo "Myanmar fonts already installed"

# Ethiopic fonts
echo "Installing Ethiopic fonts..."
apt-get install -y -qq fonts-sil-abyssinica 2>/dev/null || echo "Ethiopic fonts already installed"

echo ""
echo "=== Phase 2: Updating font cache ==="
fc-cache -fv

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Fonts installed via packages. Run './scripts/download_fonts.sh' for additional manual downloads."
