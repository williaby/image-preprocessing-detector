#!/usr/bin/env python3
"""Batch add front matter to markdown files that are missing it.

This script adds valid front matter to documentation files that don't have
the required schema_type field, fixing the discriminated union validation error.
"""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter

# Mapping of path keywords to tags. Each entry is (keywords, tag) where
# keywords is a tuple -- ALL keywords must be present for the tag to apply.
_PATH_TAG_RULES: list[tuple[tuple[str, ...], str]] = [
    (("architecture",), "architecture"),
    (("diagram",), "documentation"),
    (("planning",), "planning"),
    (("reference",), "reference"),
    (("benchmark",), "benchmarking"),
    (("model", "training"), "training"),
    (("dataset",), "datasets"),
    (("labeling",), "labeling"),
    (("iqa",), "iqa"),
    (("quality",), "iqa"),
    (("workflow",), "pipeline"),
    (("pseudo",), "weak_supervision"),
    (("production",), "production"),
    (("runtime",), "production"),
    (("monitoring",), "monitoring"),
    (("drift",), "monitoring"),
]


def infer_tags(path: Path, _content: str) -> list[str]:
    """Infer appropriate tags based on file path and content."""
    path_str = str(path).lower()

    tags: list[str] = []
    for keywords, tag in _PATH_TAG_RULES:
        if all(kw in path_str for kw in keywords) and tag not in tags:
            tags.append(tag)

    if not tags:
        tags.append("documentation")

    return tags[:4]


def extract_title(content: str) -> str:
    """Extract title from H1 heading."""
    h1_match = re.search(r"^#\s+(.+?)(?:\s*\{[^}]+\})?\s*$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    return "Untitled Document"


def infer_purpose(title: str, path: Path) -> str:
    """Create a purpose statement from title and path."""
    path_str = str(path)

    if "index" in path_str.lower():
        return f"Index and navigation for {title.lower().replace('index', '').strip() or 'this section'}."
    if "readme" in path_str.lower():
        return f"Overview and documentation for {title}."
    if "template" in path_str.lower():
        return f"Template for creating consistent {title.lower().replace('template', '').strip()} documents."
    if "guide" in path_str.lower():
        return f"Guidance for {title.lower().replace('guide', '').strip()}."

    return f"Documentation for {title}."


def _parse_existing_front_matter(text: str) -> tuple[dict, str]:
    """Parse existing front matter and extract content body.

    Returns:
        Tuple of (metadata_dict, content_body).
    """
    try:
        post = frontmatter.loads(text)
        meta = post.metadata if isinstance(post.metadata, dict) else {}
    except Exception:
        meta = {}
        post = frontmatter.Post(text)

    content = post.content if hasattr(post, "content") else text

    # Remove existing front matter from content if partial
    if text.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n", text, flags=re.DOTALL)
        if match:
            content = text[match.end() :]

    return meta, content


def _build_new_meta(meta: dict, content: str, path: Path) -> dict:
    """Build new front matter metadata from existing meta and content."""
    title = meta.get("title") or extract_title(content)
    purpose = meta.get("purpose") or infer_purpose(title, path)

    if purpose and not purpose.strip().endswith((".", "!", "?")):
        purpose = purpose.strip() + "."

    new_meta = {
        "schema_type": "common",
        "title": title,
        "status": meta.get("status", "draft"),
        "owner": meta.get("owner", "docs-team"),
        "purpose": purpose,
        "tags": meta.get("tags") or infer_tags(path, content),
    }

    if meta.get("description"):
        new_meta["description"] = meta["description"]

    return new_meta


def add_front_matter_to_file(path: Path, dry_run: bool = False) -> bool:
    """Add front matter to a file that's missing schema_type.

    Returns True if changes were made.
    """
    text = path.read_text(encoding="utf-8")
    meta, content = _parse_existing_front_matter(text)

    if meta.get("schema_type") in ("common", "script", "knowledge", "planning"):
        return False

    new_meta = _build_new_meta(meta, content, path)
    title = new_meta["title"]

    content_cleaned = re.sub(
        r"^\s*#\s+" + re.escape(title) + r"\s*$\n?",
        "",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    new_post = frontmatter.Post(content_cleaned.lstrip(), **new_meta)
    new_text = frontmatter.dumps(new_post)

    if dry_run:
        print(f"Would update: {path}")
        print(f"  Title: {title}")
        print(f"  Tags: {new_meta['tags']}")
        return True

    path.write_text(new_text, encoding="utf-8")
    print(f"Updated: {path}")
    return True


def _has_schema_type_error(item: dict) -> bool:
    """Check if a validation item has a schema_type-related error."""
    if item["ok"]:
        return False
    return any(
        "schema_type" in err or "Unable to extract tag using discriminator" in err
        for err in item.get("errors", [])
    )


def main() -> int:
    """Process all markdown files in docs/ that have front matter issues."""
    import json
    import subprocess

    result = subprocess.run(
        [  # noqa: S607
            "uv",
            "run",
            "python",
            "tools/validate_front_matter.py",
            "docs",
            "--emit-json",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to get validation results")
        return 1

    files_to_fix = [Path(item["file"]) for item in data if _has_schema_type_error(item)]
    print(f"Found {len(files_to_fix)} files with schema_type issues")

    fixed = sum(
        1
        for path in files_to_fix
        if path.exists() and add_front_matter_to_file(path, dry_run=False)
    )
    print(f"Fixed {fixed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
