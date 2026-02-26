#!/usr/bin/env python3
"""Generate OOD code-screenshot images (Phase 3e, Recipes 11 + 12).

Renders syntax-highlighted source code and prose+code markdown documents as
raster images, creating samples with ``code_cls=1`` that have ~0% coverage
in non-code IQA training data.

Recipe 11 (300 images): Syntax-highlighted code rendered with Pygments.
  - Sources: Python files from the project ``src/`` tree (permissive use).
  - Variations: light/dark theme, 3 font sizes (10/12/14 pt), with/without
    line numbers.

Recipe 12 (124 images): Mixed prose + code Markdown document renders.
  - Sources: Markdown files from the project ``docs/`` tree.
  - Rendered at 1080 px width with monospace code blocks distinguished by
    a shaded background.

All images registered under ``ood_code`` with ``code_confidence=1.0``.

Usage:
    # Dry run
    uv run python scripts/generate_ood_code_screenshots.py --dry-run

    # Generate all 424 images
    uv run python scripts/generate_ood_code_screenshots.py \\
        --src-dir src \\
        --docs-dir docs \\
        --output-dir /mnt/e/image_detection/ood/code
"""
from __future__ import annotations

import io
import random
import sys
import textwrap
from pathlib import Path

import click
import numpy as np

# #ASSUME: env: PIL available; pygments optional (graceful degradation)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    click.echo(f"Missing dependency: {exc}. Run: uv sync --extra dev", err=True)
    sys.exit(1)

try:
    from pygments import highlight
    from pygments.formatters import ImageFormatter
    from pygments.lexers import PythonLexer, guess_lexer_for_filename, TextLexer
    from pygments.styles import get_style_by_name

    _PYGMENTS_AVAILABLE = True
except ImportError:
    _PYGMENTS_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.ood_utils import (
    append_registry_entry,
    build_ground_truth_template,
    hamming_distance,
    load_ood_registry,
    log_dry_run_summary,
)

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(11)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_000B) & 0xFFFFFFFF

_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/code")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Image canvas dimensions
_CANVAS_WIDTH = 1080
_CODE_FONT_SIZES = [10, 12, 14]
_PROSE_FONT_SIZE = 13

# Theme options for recipe 11
_LIGHT_STYLE = "friendly"
_DARK_STYLE = "monokai"

# Background colours for fallback (no pygments) rendering
_LIGHT_BG = (252, 252, 252)
_DARK_BG = (40, 42, 54)
_LIGHT_FG = (30, 30, 30)
_DARK_FG = (248, 248, 242)
_CODE_BLOCK_BG = (235, 235, 240)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hashes_from_bytes(data: bytes) -> tuple[str, str]:
    """Compute (sha256_hex, phash_hex) directly from image bytes."""
    import hashlib

    import imagehash

    sha256 = hashlib.sha256(data).hexdigest()
    img = Image.open(io.BytesIO(data))
    ph = imagehash.phash(img)
    bits = ph.hash.flatten()
    byte_vals = [int("".join(str(int(b)) for b in bits[i : i + 8]), 2) for i in range(0, 64, 8)]
    phash_hex = bytes(byte_vals).hex()
    return sha256, phash_hex


def _find_source_files(src_dir: Path) -> list[Path]:
    """Collect Python source files from src_dir, excluding __pycache__."""
    files = [
        p for p in src_dir.rglob("*.py")
        if "__pycache__" not in p.parts and p.stat().st_size > 200
    ]
    return sorted(files)


def _find_markdown_files(docs_dir: Path) -> list[Path]:
    """Collect Markdown files from docs_dir."""
    return sorted(docs_dir.rglob("*.md"))


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a monospace font at *size* pt, falling back to default."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ]
    for path in font_candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _render_code_pygments(
    source_text: str, filename: str, font_size: int, dark_theme: bool, show_linenos: bool
) -> Image.Image | None:
    """Render code with Pygments ImageFormatter.

    Returns None if Pygments is unavailable or rendering fails.
    """
    if not _PYGMENTS_AVAILABLE:
        return None
    try:
        try:
            lexer = guess_lexer_for_filename(filename, source_text)
        except Exception:
            lexer = PythonLexer()

        style_name = _DARK_STYLE if dark_theme else _LIGHT_STYLE
        fmt = ImageFormatter(
            style=style_name,
            font_size=font_size,
            line_numbers=show_linenos,
            image_pad=10,
        )
        img_bytes = highlight(source_text, lexer, fmt)
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        return None


def _render_code_fallback(
    source_text: str, font_size: int, dark_theme: bool
) -> Image.Image:
    """Render code as plain text image when Pygments is unavailable."""
    bg = _DARK_BG if dark_theme else _LIGHT_BG
    fg = _DARK_FG if dark_theme else _LIGHT_FG

    font = _get_font(font_size)
    lines = source_text.splitlines()[:60]  # cap at 60 lines

    # Estimate dimensions
    line_height = font_size + 4
    h = max(200, line_height * len(lines) + 20)
    img = Image.new("RGB", (_CANVAS_WIDTH, h), bg)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        y = 10 + i * line_height
        draw.text((10, y), line[:120], fill=fg, font=font)

    return img


def _render_code_image(
    source_text: str,
    filename: str,
    font_size: int,
    dark_theme: bool,
    show_linenos: bool,
) -> Image.Image:
    """Render source code to PIL Image, trying Pygments then fallback."""
    # Take a manageable slice of the source
    lines = source_text.splitlines()
    start = random.randint(0, max(0, len(lines) - 40))
    snippet = "\n".join(lines[start : start + 40])

    img = _render_code_pygments(snippet, filename, font_size, dark_theme, show_linenos)
    if img is None:
        img = _render_code_fallback(snippet, font_size, dark_theme)

    # Resize to standard width, preserving aspect ratio
    if img.width != _CANVAS_WIDTH:
        scale = _CANVAS_WIDTH / img.width
        new_h = int(img.height * scale)
        img = img.resize((_CANVAS_WIDTH, new_h), Image.Resampling.LANCZOS)

    return img


def _render_markdown_image(md_text: str) -> Image.Image:
    """Render Markdown text as a prose+code image at CANVAS_WIDTH.

    Code blocks (``` fenced) get a shaded background. Regular text is
    rendered in a proportional font.  No external Markdown library needed.
    """
    font_prose = _get_font(_PROSE_FONT_SIZE)
    font_code = _get_font(_PROSE_FONT_SIZE - 2)

    bg = (255, 255, 255)
    fg_prose = (30, 30, 30)
    fg_code = (50, 50, 120)
    code_bg = _CODE_BLOCK_BG

    lines = md_text.splitlines()[:80]
    line_height = _PROSE_FONT_SIZE + 5
    h = max(400, line_height * len(lines) + 30)
    img = Image.new("RGB", (_CANVAS_WIDTH, h), bg)
    draw = ImageDraw.Draw(img)

    in_code_block = False
    y = 12
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            draw.rectangle([(0, y - 1), (_CANVAS_WIDTH, y + line_height - 1)], fill=code_bg)
            draw.text((16, y), line[:110], fill=fg_code, font=font_code)
        else:
            # Strip simple Markdown formatting for rendering
            stripped = line.lstrip("#").lstrip(">").lstrip("*").lstrip("-").strip()
            draw.text((12, y), stripped[:120], fill=fg_prose, font=font_prose)

        y += line_height
        if y > h - line_height:
            break

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--src-dir",
    type=click.Path(path_type=Path),
    default=Path("src"),
    show_default=True,
    help="Project source directory to harvest Python files from (Recipe 11).",
)
@click.option(
    "--docs-dir",
    type=click.Path(path_type=Path),
    default=Path("docs"),
    show_default=True,
    help="Project docs directory to harvest Markdown files from (Recipe 12).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=_OUTPUT_DEFAULT,
    show_default=True,
    help="Directory to write generated OOD images.",
)
@click.option(
    "--registry",
    type=click.Path(path_type=Path),
    default=_REGISTRY_DEFAULT,
    show_default=True,
    help="OOD registry JSONL file.",
)
@click.option("--n-code", default=300, show_default=True, help="Recipe 11 target (code renders).")
@click.option("--n-markdown", default=124, show_default=True, help="Recipe 12 target (markdown renders).")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    src_dir: Path,
    docs_dir: Path,
    output_dir: Path,
    registry: Path,
    n_code: int,
    n_markdown: int,
    dry_run: bool,
) -> None:
    """Generate code-screenshot OOD images (Phase 3e, Recipes 11 + 12).

    Recipe 11: Renders Python source files with Pygments syntax highlighting
    (light/dark themes, variable font sizes, optional line numbers).

    Recipe 12: Renders project Markdown files as mixed prose+code images.

    All images are registered under ood_code with code_confidence=1.0.
    """
    rng = random.Random(_OOD_RNG_SEED)

    if not _PYGMENTS_AVAILABLE:
        click.echo(
            "  [WARN] pygments not installed — Recipe 11 uses plain-text fallback renderer.\n"
            "         Install: uv add pygments"
        )

    ood_sha256s, ood_phashes = load_ood_registry(registry)
    known_phashes = list(ood_phashes)

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    n_skipped_dup = n_code_registered = n_md_registered = 0

    # ------------------------------------------------------------------
    # Recipe 11: syntax-highlighted code renders
    # ------------------------------------------------------------------
    py_files = _find_source_files(src_dir)
    if not py_files:
        click.echo(f"  [WARN] No Python files found under {src_dir}; skipping Recipe 11.")
    else:
        click.echo(f"  Recipe 11: {len(py_files)} Python source files found.")
        rng.shuffle(py_files)

        n_cands_11 = 0
        pool_11 = py_files * (n_code // max(1, len(py_files)) + 2)  # repeat if needed

        for src_path in pool_11:
            if n_code_registered >= n_code:
                break
            n_cands_11 += 1

            try:
                source_text = src_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            font_size = rng.choice(_CODE_FONT_SIZES)
            dark_theme = rng.random() < 0.4
            show_linenos = rng.random() < 0.6

            try:
                img = _render_code_image(
                    source_text, src_path.name, font_size, dark_theme, show_linenos
                )
            except Exception:
                continue

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            img_bytes = buf.getvalue()

            sha256, phash = _hashes_from_bytes(img_bytes)

            if sha256 in ood_sha256s:
                n_skipped_dup += 1
                continue
            if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
                n_skipped_dup += 1
                continue

            out_name = f"code_{n_code_registered:05d}.jpg"
            out_path = output_dir / out_name

            if not dry_run:
                out_path.write_bytes(img_bytes)

            gt = build_ground_truth_template()
            gt["code_confidence"] = 1.0
            gt["capture_method"] = "born_digital"
            gt["color_mode"] = "dark" if dark_theme else "light"

            from datetime import date

            entry = {
                "sha256": sha256,
                "phash": phash,
                "source_path": str(out_path),
                "registered_date": date.today().isoformat(),
                "ood_categories": ["ood_code"],
                "reason": (
                    f"Syntax-highlighted code render from {src_path.name}; "
                    f"theme={'dark' if dark_theme else 'light'}, "
                    f"font={font_size}pt, linenos={show_linenos}; "
                    "code_cls head stress-test"
                ),
                "acquisition_method": "synthetic_generation",
                "license": "MIT",
                "dedup_verified": True,
                "evaluation_pipeline_stage": ["siglip2"],
                "ground_truth": gt,
                "generation_metadata": {
                    "source_file": src_path.name,
                    "generator_script": "generate_ood_code_screenshots.py",
                    "recipe": "phase3e_recipe11",
                    "seed": _OOD_RNG_SEED,
                    "font_size": font_size,
                    "dark_theme": dark_theme,
                    "show_linenos": show_linenos,
                    "pygments_available": _PYGMENTS_AVAILABLE,
                },
            }

            if not dry_run:
                append_registry_entry(entry, registry)

            ood_sha256s.add(sha256)
            known_phashes.append(phash)
            n_code_registered += 1

    # ------------------------------------------------------------------
    # Recipe 12: Markdown prose+code renders
    # ------------------------------------------------------------------
    md_files = _find_markdown_files(docs_dir)
    if not md_files:
        click.echo(f"  [WARN] No Markdown files found under {docs_dir}; skipping Recipe 12.")
    else:
        click.echo(f"  Recipe 12: {len(md_files)} Markdown files found.")
        rng.shuffle(md_files)

        n_cands_12 = 0
        pool_12 = md_files * (n_markdown // max(1, len(md_files)) + 2)

        for md_path in pool_12:
            if n_md_registered >= n_markdown:
                break
            n_cands_12 += 1

            try:
                md_text = md_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # Focus on sections that contain code blocks
            if "```" not in md_text:
                continue

            # Slice to a window that includes at least one code block
            lines = md_text.splitlines()
            code_line_indices = [i for i, ln in enumerate(lines) if ln.startswith("```")]
            if not code_line_indices:
                continue
            start_line = max(0, rng.choice(code_line_indices) - 10)
            snippet_lines = lines[start_line : start_line + 80]
            snippet = "\n".join(snippet_lines)

            try:
                img = _render_markdown_image(snippet)
            except Exception:
                continue

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            img_bytes = buf.getvalue()

            sha256, phash = _hashes_from_bytes(img_bytes)

            if sha256 in ood_sha256s:
                n_skipped_dup += 1
                continue
            if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
                n_skipped_dup += 1
                continue

            out_name = f"mdcode_{n_md_registered:05d}.jpg"
            out_path = output_dir / out_name

            if not dry_run:
                out_path.write_bytes(img_bytes)

            gt = build_ground_truth_template()
            gt["code_confidence"] = 1.0
            gt["capture_method"] = "born_digital"
            gt["handwriting_presence"] = "NONE"

            from datetime import date

            entry = {
                "sha256": sha256,
                "phash": phash,
                "source_path": str(out_path),
                "registered_date": date.today().isoformat(),
                "ood_categories": ["ood_code"],
                "reason": (
                    f"Prose+code Markdown render from {md_path.name}; "
                    "mixed text/code layout challenges code_cls head"
                ),
                "acquisition_method": "synthetic_generation",
                "license": "MIT",
                "dedup_verified": True,
                "evaluation_pipeline_stage": ["siglip2"],
                "ground_truth": gt,
                "generation_metadata": {
                    "source_file": md_path.name,
                    "generator_script": "generate_ood_code_screenshots.py",
                    "recipe": "phase3e_recipe12",
                    "seed": _OOD_RNG_SEED,
                    "start_line": start_line,
                },
            }

            if not dry_run:
                append_registry_entry(entry, registry)

            ood_sha256s.add(sha256)
            known_phashes.append(phash)
            n_md_registered += 1

    total = n_code_registered + n_md_registered
    n_target = n_code + n_markdown
    log_dry_run_summary(
        sub_command="generate-ood-code-screenshots",
        candidates=0,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=total,
        dry_run=dry_run,
    )
    click.echo(
        f"  Code OOD: {n_code_registered}/{n_code} (Recipe 11) + "
        f"{n_md_registered}/{n_markdown} (Recipe 12) = {total}/{n_target}"
    )


if __name__ == "__main__":
    main()
