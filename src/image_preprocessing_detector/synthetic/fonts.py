# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Font management for synthetic document generation.

This module provides font discovery, loading, and management for
rendering text in multiple scripts. It focuses on Noto fonts which
provide comprehensive Unicode coverage.

The FontManager scans common system font directories and caches
discovered fonts for efficient access during document generation.

Example:
    >>> from image_preprocessing_detector.synthetic.fonts import FontManager
    >>> manager = FontManager()
    >>> manager.scan_fonts()
    >>> font = manager.get_font("Tibt", size=24)
    >>> if font:
    ...     # Use font for rendering
    ...     pass
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import ImageFont

logger = logging.getLogger(__name__)

# Common log messages (S1192: avoid duplicate string literals)
FONT_LOAD_ERROR = "Failed to load font %s: %s"

# Common font search directories across platforms
FONT_SEARCH_PATHS: list[Path] = [
    # Project-bundled fonts (highest priority for reproducibility)
    Path(__file__).parent.parent.parent.parent / "fonts/synthetic-gen",
    # Linux (standard)
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/noto"),
    Path("/usr/share/fonts/google-noto"),
    Path("/usr/share/fonts/opentype/noto"),
    Path("/usr/share/fonts/truetype"),
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    # Linux (user)
    Path.home() / ".local/share/fonts",
    Path.home() / ".fonts",
    # macOS
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
    Path.home() / "Library/Fonts",
    # Windows
    Path("C:/Windows/Fonts"),
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
]

# Font file extensions to search (including .ttc TrueType Collections for CJK)
FONT_EXTENSIONS: set[str] = {".ttf", ".otf", ".ttc", ".TTF", ".OTF", ".TTC"}


@dataclass
class FontInfo:
    """Information about a discovered font file.

    Attributes:
        path: Full path to the font file
        family: Font family name (extracted from filename)
        style: Font style (Regular, Bold, Italic, etc.)
        script_hint: Guessed script from font name (e.g., "Tibetan" from NotoSerifTibetan)
        is_noto: True if this is a Noto font
    """

    path: Path
    family: str
    style: str
    script_hint: str | None = None
    is_noto: bool = False


@dataclass
class FontCache:
    """Cached font information for a script.

    Attributes:
        script_code: ISO 15924 script code
        fonts: List of FontInfo objects for this script
        default_font: Preferred font for this script
    """

    script_code: str
    fonts: list[FontInfo] = field(default_factory=list)
    default_font: FontInfo | None = None


# Mapping from font name patterns to ISO 15924 script codes
FONT_NAME_TO_SCRIPT: dict[str, str] = {
    # CJK
    "SC": "Hans",
    "SimplifiedChinese": "Hans",
    "TC": "Hant",
    "TraditionalChinese": "Hant",
    "JP": "Jpan",
    "Japanese": "Jpan",
    "KR": "Kore",
    "Korean": "Kore",
    # Indic
    "Devanagari": "Deva",
    "Bengali": "Beng",
    "Tamil": "Taml",
    "Telugu": "Telu",
    "Gujarati": "Gujr",
    "Kannada": "Knda",
    "Malayalam": "Mlym",
    "Oriya": "Orya",
    "Sinhala": "Sinh",
    "Gurmukhi": "Guru",
    # Southeast Asian
    "Thai": "Thai",
    "Khmer": "Khmr",
    "Myanmar": "Mymr",
    "Lao": "Laoo",
    "Tibetan": "Tibt",
    # Middle Eastern
    "Arabic": "Arab",
    "Hebrew": "Hebr",
    "NaskhArabic": "Arab",
    "NastaliqUrdu": "Arab",
    # European/Other
    "Armenian": "Armn",
    "Georgian": "Geor",
    "Ethiopic": "Ethi",
    "Greek": "Grek",
}


def _extract_script_from_font_name(name: str) -> str | None:
    """Extract script code from font filename.

    Args:
        name: Font filename (without path)

    Returns:
        ISO 15924 script code if detected, None otherwise
    """
    # Remove extension and common prefixes
    base = name.rsplit(".", 1)[0]
    base = base.replace("NotoSans", "").replace("NotoSerif", "").replace("Noto", "")
    base = base.replace("-Regular", "").replace("-Bold", "").replace("-Italic", "")

    # Check against known patterns
    for pattern, script in FONT_NAME_TO_SCRIPT.items():
        if pattern.lower() in base.lower():
            return script

    return None


def _extract_style_from_font_name(name: str) -> str:
    """Extract font style from filename.

    Args:
        name: Font filename

    Returns:
        Style string (Regular, Bold, Italic, etc.)
    """
    name_lower = name.lower()
    if "bold" in name_lower and "italic" in name_lower:
        return "BoldItalic"
    if "bold" in name_lower:
        return "Bold"
    if "italic" in name_lower:
        return "Italic"
    if "light" in name_lower:
        return "Light"
    if "medium" in name_lower:
        return "Medium"
    if "semibold" in name_lower:
        return "SemiBold"
    return "Regular"


def _extract_family_from_font_name(name: str) -> str:
    """Extract font family from filename.

    Args:
        name: Font filename

    Returns:
        Family name
    """
    base = name.rsplit(".", 1)[0]
    # Remove style suffixes
    for suffix in ["-Regular", "-Bold", "-Italic", "-Light", "-Medium", "-SemiBold"]:
        base = base.replace(suffix, "")
    return base


class FontManager:
    """Manages font discovery and loading for synthetic document generation.

    The FontManager scans system font directories to find Noto fonts
    and other fonts suitable for multi-script rendering. It maintains
    a cache of discovered fonts organized by script.

    Attributes:
        fonts_by_script: Dict mapping script codes to FontCache objects
        all_fonts: List of all discovered fonts
        search_paths: List of directories to search for fonts
    """

    def __init__(
        self,
        additional_paths: list[Path] | None = None,
        prefer_noto: bool = True,
    ) -> None:
        """Initialize the font manager.

        Args:
            additional_paths: Extra directories to search for fonts
            prefer_noto: If True, prefer Noto fonts over others
        """
        self.search_paths = list(FONT_SEARCH_PATHS)
        if additional_paths:
            self.search_paths.extend(additional_paths)

        self.prefer_noto = prefer_noto
        self.fonts_by_script: dict[str, FontCache] = {}
        self.all_fonts: list[FontInfo] = []
        self._font_objects: dict[tuple[Path, int], ImageFont.FreeTypeFont] = {}
        self._scanned = False

    def scan_fonts(self) -> int:
        """Scan system directories for fonts.

        Returns:
            Number of fonts discovered
        """
        self.all_fonts = []
        self.fonts_by_script = {}

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            self._scan_directory(search_path)

        # Organize fonts by script
        self._organize_by_script()

        self._scanned = True
        logger.info(
            "Font scan complete: %d fonts found, %d scripts supported",
            len(self.all_fonts),
            len(self.fonts_by_script),
        )

        return len(self.all_fonts)

    def _scan_directory(self, directory: Path) -> None:
        """Recursively scan a directory for font files.

        Args:
            directory: Directory to scan
        """
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    self._scan_directory(item)
                elif item.suffix in FONT_EXTENSIONS:
                    # Special handling for CJK TrueType Collections
                    if item.suffix.lower() == ".ttc" and "CJK" in item.name:
                        cjk_fonts = self._parse_cjk_collection(item)
                        self.all_fonts.extend(cjk_fonts)
                    else:
                        font_info = self._parse_font_file(item)
                        if font_info:
                            self.all_fonts.append(font_info)
        except PermissionError:
            logger.debug("Permission denied scanning: %s", directory)
        except OSError as e:
            logger.debug("Error scanning %s: %s", directory, e)

    def _parse_font_file(self, path: Path) -> FontInfo | None:
        """Parse font file metadata.

        Args:
            path: Path to font file

        Returns:
            FontInfo if valid font, None otherwise
        """
        name = path.name
        family = _extract_family_from_font_name(name)
        style = _extract_style_from_font_name(name)
        script_hint = _extract_script_from_font_name(name)
        is_noto = name.lower().startswith("noto")

        return FontInfo(
            path=path,
            family=family,
            style=style,
            script_hint=script_hint,
            is_noto=is_noto,
        )

    def _parse_cjk_collection(self, path: Path) -> list[FontInfo]:
        """Parse CJK TrueType Collection and return entries for each variant.

        CJK .ttc files contain multiple fonts for different locales (SC, TC, JP, KR).
        This creates separate FontInfo entries for each.

        Args:
            path: Path to .ttc file

        Returns:
            List of FontInfo objects for each CJK variant
        """
        name = path.name
        style = _extract_style_from_font_name(name)
        is_noto = name.lower().startswith("noto")

        # CJK locale to script mapping
        cjk_scripts = {
            "SC": "Hans",  # Simplified Chinese
            "TC": "Hant",  # Traditional Chinese
            "JP": "Jpan",  # Japanese
            "KR": "Kore",  # Korean
        }

        fonts = []
        for locale, script in cjk_scripts.items():
            fonts.append(
                FontInfo(
                    path=path,
                    family=f"NotoSansCJK{locale}"
                    if "Sans" in name
                    else f"NotoSerifCJK{locale}",
                    style=style,
                    script_hint=script,
                    is_noto=is_noto,
                )
            )
        return fonts

    def _organize_by_script(self) -> None:
        """Organize discovered fonts by script code."""
        # Group fonts by detected script
        script_fonts: dict[str, list[FontInfo]] = {}

        for font in self.all_fonts:
            if font.script_hint:
                if font.script_hint not in script_fonts:
                    script_fonts[font.script_hint] = []
                script_fonts[font.script_hint].append(font)

        # Also add Latin-compatible fonts (generic Noto Sans/Serif)
        latin_fonts = [
            f
            for f in self.all_fonts
            if f.is_noto and f.script_hint is None and "Sans" in f.family
        ]
        if latin_fonts:
            script_fonts["Latn"] = latin_fonts

        # Also support Cyrillic and Greek with Latin fonts
        for script in ["Cyrl", "Grek"]:
            if script not in script_fonts:
                script_fonts[script] = latin_fonts

        # Create FontCache objects
        for script_code, fonts in script_fonts.items():
            # Sort: prefer Noto, then Regular style
            fonts.sort(
                key=lambda f: (
                    not f.is_noto,
                    f.style != "Regular",
                    f.family,
                )
            )

            self.fonts_by_script[script_code] = FontCache(
                script_code=script_code,
                fonts=fonts,
                default_font=fonts[0] if fonts else None,
            )

    def get_font(
        self,
        script_code: str,
        size: int = 16,
        style: str = "Regular",
    ) -> ImageFont.FreeTypeFont | None:
        """Get a font for a specific script.

        Args:
            script_code: ISO 15924 script code
            size: Font size in points
            style: Preferred style (Regular, Bold, etc.)

        Returns:
            Loaded ImageFont or None if not available
        """
        if not self._scanned:
            self.scan_fonts()

        from PIL import ImageFont

        cache = self.fonts_by_script.get(script_code)
        if not cache or not cache.fonts:
            logger.warning("No fonts found for script: %s", script_code)
            return None

        # Try to find matching style
        font_info = None
        for f in cache.fonts:
            if f.style == style:
                font_info = f
                break

        # Fall back to default
        if not font_info:
            font_info = cache.default_font

        if not font_info:
            return None

        # Check cache
        cache_key = (font_info.path, size)
        if cache_key in self._font_objects:
            return self._font_objects[cache_key]

        # Load font
        try:
            font = ImageFont.truetype(str(font_info.path), size)
            self._font_objects[cache_key] = font
            return font
        except OSError as e:
            logger.error(FONT_LOAD_ERROR, font_info.path, e)
            return None

    def get_random_font(
        self,
        script_code: str,
        size: int = 16,
    ) -> ImageFont.FreeTypeFont | None:
        """Get a random font for a script (for variety in generation).

        Args:
            script_code: ISO 15924 script code
            size: Font size in points

        Returns:
            Loaded ImageFont or None if not available
        """
        if not self._scanned:
            self.scan_fonts()

        cache = self.fonts_by_script.get(script_code)
        if not cache or not cache.fonts:
            return None

        from PIL import ImageFont

        font_info = random.choice(cache.fonts)

        # Check cache
        cache_key = (font_info.path, size)
        if cache_key in self._font_objects:
            return self._font_objects[cache_key]

        try:
            font = ImageFont.truetype(str(font_info.path), size)
            self._font_objects[cache_key] = font
            return font
        except OSError as e:
            logger.error(FONT_LOAD_ERROR, font_info.path, e)
            return None

    def get_available_scripts(self) -> list[str]:
        """Get list of scripts with available fonts.

        Returns:
            List of ISO 15924 script codes
        """
        if not self._scanned:
            self.scan_fonts()
        return list(self.fonts_by_script.keys())

    def get_font_info(self, script_code: str) -> FontCache | None:
        """Get font cache info for a script.

        Args:
            script_code: ISO 15924 script code

        Returns:
            FontCache or None if not found
        """
        if not self._scanned:
            self.scan_fonts()
        return self.fonts_by_script.get(script_code)

    def has_font_for_script(self, script_code: str) -> bool:
        """Check if fonts are available for a script.

        Args:
            script_code: ISO 15924 script code

        Returns:
            True if fonts available
        """
        if not self._scanned:
            self.scan_fonts()
        cache = self.fonts_by_script.get(script_code)
        return cache is not None and len(cache.fonts) > 0

    def get_tiered_font(
        self,
        script_code: str,
        size: int = 16,
        language_code: str | None = None,
    ) -> ImageFont.FreeTypeFont | None:
        """Get a font using tiered sampling based on FONT_RECOMMENDATIONS.

        This method implements the font diversity strategy from font_research.md,
        sampling fonts from SYSTEM (50%), REGIONAL (30%), and STYLISTIC (20%) tiers.

        Special handling for Urdu/Punjabi Arabic (Nastaliq style).

        Args:
            script_code: ISO 15924 script code
            size: Font size in points
            language_code: Optional OpenLID language code (e.g., "urd_Arab")
                          Used to detect Nastaliq requirement for Urdu

        Returns:
            Loaded ImageFont or None if not available
        """
        if not self._scanned:
            self.scan_fonts()

        from PIL import ImageFont

        from image_preprocessing_detector.synthetic.config import (
            BULGARIAN_CYRILLIC_LANGUAGES,
            FONT_RECOMMENDATIONS,
            FONT_TIER_WEIGHTS,
            NASTALIQ_LANGUAGES,
        )

        # Determine effective script (handle special language variants)
        effective_script = script_code

        # Nastaliq for Urdu/Punjabi Arabic
        if language_code and language_code in NASTALIQ_LANGUAGES:
            effective_script = "Arab_Nastaliq"
        # Bulgarian Cyrillic has distinct glyph forms
        elif language_code and language_code in BULGARIAN_CYRILLIC_LANGUAGES:
            effective_script = "Cyrl_Bulgarian"

        # Get font recommendations for this script
        recommendations = FONT_RECOMMENDATIONS.get(effective_script)
        if not recommendations:
            # Fall back to standard script
            recommendations = FONT_RECOMMENDATIONS.get(script_code)
        if not recommendations:
            # Fall back to default random selection
            logger.debug(
                "No font recommendations for script %s, using default",
                script_code,
            )
            return self.get_random_font(script_code, size)

        # Select tier based on weights
        tier = self._select_tier(FONT_TIER_WEIGHTS)

        # Get font families for selected tier
        tier_families = recommendations.get(tier, [])
        if not tier_families:
            # Fall back to SYSTEM tier
            tier_families = recommendations.get("SYSTEM", [])

        # Find matching fonts from discovered fonts
        matching_fonts = self._find_fonts_by_families(script_code, tier_families)

        if not matching_fonts:
            # Fall back to any font for this script
            logger.debug(
                "No tier %s fonts found for script %s, using fallback",
                tier,
                script_code,
            )
            return self.get_random_font(script_code, size)

        # Select random font from matches
        font_info = random.choice(matching_fonts)

        # Check cache
        cache_key = (font_info.path, size)
        if cache_key in self._font_objects:
            return self._font_objects[cache_key]

        # Load font
        try:
            font = ImageFont.truetype(str(font_info.path), size)
            self._font_objects[cache_key] = font
            logger.debug(
                "Loaded tiered font: %s (tier=%s, script=%s)",
                font_info.family,
                tier,
                script_code,
            )
            return font
        except OSError as e:
            logger.error(FONT_LOAD_ERROR, font_info.path, e)
            return self.get_random_font(script_code, size)

    def _select_tier(self, tier_weights: dict[str, float]) -> str:
        """Select a tier based on probability weights.

        Args:
            tier_weights: Dict mapping tier names to probabilities

        Returns:
            Selected tier name
        """
        tiers = list(tier_weights.keys())
        weights = list(tier_weights.values())
        return random.choices(tiers, weights=weights, k=1)[0]

    def _find_fonts_by_families(
        self,
        script_code: str,
        family_patterns: list[str],
    ) -> list[FontInfo]:
        """Find fonts matching any of the given family patterns.

        Args:
            script_code: Script to search within
            family_patterns: List of family name substrings to match

        Returns:
            List of matching FontInfo objects
        """
        matching = []

        # Search in script-specific fonts
        cache = self.fonts_by_script.get(script_code)
        if cache:
            for font in cache.fonts:
                for pattern in family_patterns:
                    if pattern.lower() in font.family.lower():
                        matching.append(font)
                        break

        # Also search all fonts for multi-script fonts like Liberation
        if not matching:
            for font in self.all_fonts:
                for pattern in family_patterns:
                    if pattern.lower() in font.family.lower():
                        matching.append(font)
                        break

        return matching

    def get_font_diversity_stats(self, script_code: str) -> dict[str, int]:
        """Get statistics about font diversity for a script.

        Args:
            script_code: ISO 15924 script code

        Returns:
            Dict with counts by tier and total
        """
        if not self._scanned:
            self.scan_fonts()

        from image_preprocessing_detector.synthetic.config import FONT_RECOMMENDATIONS

        recommendations = FONT_RECOMMENDATIONS.get(script_code, {})
        stats = {
            "total": 0,
            "SYSTEM": 0,
            "REGIONAL": 0,
            "STYLISTIC": 0,
            "HANDWRITING": 0,
            "ADVERSARIAL": 0,
        }

        for tier, families in recommendations.items():
            if tier in stats:
                matches = self._find_fonts_by_families(script_code, families)
                stats[tier] = len(matches)
                stats["total"] += len(matches)

        return stats

    def get_mimicry_font(
        self,
        target_script: str,
        size: int = 16,
    ) -> tuple[ImageFont.FreeTypeFont | None, str]:
        """Get a Latin font that mimics the visual style of another script.

        These are adversarial fonts for training robustness. The font
        LOOKS like the target script but is actually Latin and should
        be labeled as Latin in training data.

        Args:
            target_script: Script being mimicked (e.g., "Arab", "Grek", "Hans")
            size: Font size in points

        Returns:
            Tuple of (loaded ImageFont, font_family_name) or (None, "")
        """
        if not self._scanned:
            self.scan_fonts()

        from PIL import ImageFont

        from image_preprocessing_detector.synthetic.config import MIMICRY_FONTS

        mimicry_families = MIMICRY_FONTS.get(target_script, [])
        if not mimicry_families:
            logger.debug("No mimicry fonts configured for script: %s", target_script)
            return None, ""

        # Find matching fonts from all fonts (mimicry fonts are Latin)
        matching_fonts = []
        for font in self.all_fonts:
            for pattern in mimicry_families:
                if pattern.lower() in font.family.lower():
                    matching_fonts.append(font)
                    break

        if not matching_fonts:
            logger.debug(
                "No mimicry fonts found for script %s (tried: %s)",
                target_script,
                mimicry_families,
            )
            return None, ""

        # Select random mimicry font
        font_info = random.choice(matching_fonts)

        # Check cache
        cache_key = (font_info.path, size)
        if cache_key in self._font_objects:
            return self._font_objects[cache_key], font_info.family

        # Load font
        try:
            loaded_font = ImageFont.truetype(str(font_info.path), size)
            self._font_objects[cache_key] = loaded_font
            logger.debug(
                "Loaded mimicry font: %s (mimics %s)",
                font_info.family,
                target_script,
            )
            return loaded_font, font_info.family
        except OSError as e:
            logger.error("Failed to load mimicry font %s: %s", font_info.path, e)
            return None, ""

    def get_handwriting_font(
        self,
        script_code: str,
        size: int = 16,
    ) -> ImageFont.FreeTypeFont | None:
        """Get a handwriting-style font for authentic noise.

        These fonts capture the topological transformations that occur
        in real handwriting (e.g., Russian cursive т→m, Arabic Ruq'ah cascade).

        Args:
            script_code: ISO 15924 script code
            size: Font size in points

        Returns:
            Loaded ImageFont or None if not available
        """
        if not self._scanned:
            self.scan_fonts()

        from PIL import ImageFont

        from image_preprocessing_detector.synthetic.config import HANDWRITING_FONTS

        handwriting_families = HANDWRITING_FONTS.get(script_code, [])
        if not handwriting_families:
            # Fall back to HANDWRITING tier from FONT_RECOMMENDATIONS
            from image_preprocessing_detector.synthetic.config import (
                FONT_RECOMMENDATIONS,
            )

            recommendations = FONT_RECOMMENDATIONS.get(script_code, {})
            handwriting_families = recommendations.get("HANDWRITING", [])

        if not handwriting_families:
            logger.debug("No handwriting fonts for script: %s", script_code)
            return self.get_random_font(script_code, size)

        # Find matching fonts
        matching_fonts = self._find_fonts_by_families(script_code, handwriting_families)

        # Also search all fonts for multi-script handwriting fonts
        if not matching_fonts:
            for font in self.all_fonts:
                for pattern in handwriting_families:
                    if pattern.lower() in font.family.lower():
                        matching_fonts.append(font)
                        break

        if not matching_fonts:
            logger.debug(
                "No handwriting fonts found for script %s, using fallback",
                script_code,
            )
            return self.get_random_font(script_code, size)

        # Select random handwriting font
        font_info = random.choice(matching_fonts)

        # Check cache
        cache_key = (font_info.path, size)
        if cache_key in self._font_objects:
            return self._font_objects[cache_key]

        # Load font
        try:
            loaded_font = ImageFont.truetype(str(font_info.path), size)
            self._font_objects[cache_key] = loaded_font
            logger.debug(
                "Loaded handwriting font: %s (script=%s)",
                font_info.family,
                script_code,
            )
            return loaded_font
        except OSError as e:
            logger.error("Failed to load handwriting font %s: %s", font_info.path, e)
            return self.get_random_font(script_code, size)


__all__ = [
    "FONT_SEARCH_PATHS",
    "FontCache",
    "FontInfo",
    "FontManager",
]
