#!/usr/bin/env python3
"""Generate visual font comparison panels for each script.

Renders sample text in every available font for a given script,
producing a grid image for human review of diversity and legibility.

Usage:
    python scripts/generate_font_comparison_panel.py --script Thai
    python scripts/generate_font_comparison_panel.py --all --output-dir reports/font_panels/
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from PIL import Image, ImageDraw, ImageFont

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from image_preprocessing_detector.synthetic.fonts import FontManager

logger = logging.getLogger(__name__)

# Sample text per script (short phrases in each script)
SAMPLE_TEXT: dict[str, str] = {
    "Latn": "The quick brown fox jumps over the lazy dog. 0123456789",
    "Arab": "بسم الله الرحمن الرحيم ٠١٢٣٤٥٦٧٨٩",
    "Deva": "नमस्ते भारत। यह एक परीक्षण है। ०१२३४५६",
    "Beng": "নমস্কার বাংলাদেশ। এটি একটি পরীক্ষা।",
    "Taml": "வணக்கம் தமிழ்நாடு। இது ஒரு சோதனை।",
    "Telu": "నమస్కారం తెలుగు। ఇది ఒక పరీక్ష।",
    "Gujr": "નમસ્તે ગુજરાત। આ એક કસોટી છે।",
    "Knda": "ನಮಸ್ಕಾರ ಕರ್ನಾಟಕ। ಇದು ಒಂದು ಪರೀಕ್ಷೆ।",
    "Mlym": "നമസ്കാരം കേരളം। ഇതൊരു പരീക്ഷണമാണ്।",
    "Orya": "ନମସ୍କାର ଓଡ଼ିଶା। ଏହା ଏକ ପରୀକ୍ଷା।",
    "Guru": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਪੰਜਾਬ। ਇਹ ਇੱਕ ਟੈਸਟ ਹੈ।",
    "Sinh": "ආයුබෝවන් ශ්‍රී ලංකාව। මෙය පරීක්ෂණයකි.",
    "Thai": "สวัสดีประเทศไทย นี่คือการทดสอบ ๐๑๒๓๔๕",
    "Khmr": "សួស្តីកម្ពុជា។ នេះជាការសាកល្បង។",
    "Mymr": "မင်္ဂလာပါ မြန်မာ။ ဤသည်မှာ စမ်းသပ်မှုဖြစ်သည်။",
    "Laoo": "ສະບາຍດີ ລາວ ນີ້ແມ່ນການທົດສອບ",
    "Tibt": "བཀྲ་ཤིས་བདེ་ལེགས། འདི་ནི་ཚོད་ལྟ་ཞིག་རེད།",
    "Hans": "你好中国。这是一个测试。零一二三四五六七八九",
    "Hant": "你好台灣。這是一個測試。零一二三四五六七八九",
    "Jpan": "こんにちは日本。これはテストです。〇一二三",
    "Hang": "안녕하세요 한국입니다. 이것은 테스트입니다.",
    "Kore": "안녕하세요 한국입니다. 이것은 테스트입니다.",
    "Cyrl": "Привет, мир! Это тестовый текст. 0123456789",
    "Grek": "Γειά σου κόσμε! Αυτό είναι ένα τεστ. 0123456789",
    "Hebr": "שלום עולם! זוהי בדיקה. ₪0123456789",
    "Ethi": "ሰላም ዓለም! ይህ ፈተና ነው።",
    "Armn": "Բարեdelays աdelays! Սա թdelays delays :",
    "Geor": "გamარჯობა მsworld! ეs ტესტია.",
    "Cher": "ᏣᎳᎩ ᎦᏬᏂᎯᏍᏗ",
    "Cans": "ᓀᐦᐃᔭᐍᐏᐣ",
}

ROW_HEIGHT = 50
LABEL_WIDTH = 200
TEXT_WIDTH = 800
FONT_SIZE = 24
PADDING = 10


def _render_panel(
    font_manager: FontManager,
    script_code: str,
    output_path: Path,
) -> int:
    """Render a comparison panel for a single script.

    Args:
        font_manager: Initialized FontManager
        script_code: ISO 15924 script code
        output_path: Path to save the PNG panel

    Returns:
        Number of fonts rendered
    """
    cache = font_manager.fonts_by_script.get(script_code)
    if not cache or not cache.fonts:
        logger.warning("No fonts found for script %s", script_code)
        return 0

    sample = SAMPLE_TEXT.get(script_code, "Sample text 0123456789")
    fonts = cache.fonts

    # Calculate image dimensions
    img_width = LABEL_WIDTH + TEXT_WIDTH + PADDING * 3
    img_height = ROW_HEIGHT * (len(fonts) + 1) + PADDING * 2  # +1 for header

    image = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(image)

    # Header
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        header_font = ImageFont.load_default()

    draw.text(
        (PADDING, PADDING),
        f"Script: {script_code} — {len(fonts)} fonts available",
        fill="black",
        font=header_font,
    )
    draw.line([(0, ROW_HEIGHT), (img_width, ROW_HEIGHT)], fill="gray", width=1)

    rendered_count = 0
    for idx, font_info in enumerate(fonts):
        y = ROW_HEIGHT * (idx + 1) + PADDING

        # Draw font name label
        label = f"{font_info.family} ({font_info.style})"
        if len(label) > 28:
            label = label[:25] + "..."
        draw.text((PADDING, y + 5), label, fill="gray", font=header_font)

        # Try to render sample text in this font
        try:
            font = ImageFont.truetype(str(font_info.path), FONT_SIZE)
            draw.text(
                (LABEL_WIDTH + PADDING * 2, y),
                sample,
                fill="black",
                font=font,
            )
            rendered_count += 1
        except OSError as e:
            draw.text(
                (LABEL_WIDTH + PADDING * 2, y + 5),
                f"[LOAD ERROR: {e}]",
                fill="red",
                font=header_font,
            )

        # Row separator
        draw.line(
            [(0, ROW_HEIGHT * (idx + 2)), (img_width, ROW_HEIGHT * (idx + 2))],
            fill="#eee",
            width=1,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path))
    return rendered_count


@click.command()
@click.option(
    "--script",
    default=None,
    help="ISO 15924 script code to generate panel for (e.g., 'Thai', 'Deva').",
)
@click.option(
    "--all",
    "all_scripts",
    is_flag=True,
    default=False,
    help="Generate panels for all 27 scripts.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("reports/font_panels"),
    show_default=True,
    help="Output directory for panel images.",
)
def main(script: str | None, all_scripts: bool, output_dir: Path) -> None:
    """Generate visual font comparison panels."""
    fm = FontManager()
    fm.scan_fonts()

    scripts_to_render: list[str]
    if all_scripts:
        scripts_to_render = sorted(fm.fonts_by_script.keys())
    elif script:
        scripts_to_render = [script]
    else:
        click.echo("Please specify --script CODE or --all", err=True)
        sys.exit(1)

    for sc in scripts_to_render:
        output_path = output_dir / f"font_panel_{sc}.png"
        count = _render_panel(fm, sc, output_path)
        click.echo(f"{sc}: {count} fonts rendered → {output_path}")


if __name__ == "__main__":
    main()
