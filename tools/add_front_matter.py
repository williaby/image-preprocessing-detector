#!/usr/bin/env python3
"""Batch add front matter to markdown files that are missing it.

This script adds valid front matter to documentation files that don't have
the required schema_type field, fixing the discriminated union validation error.
"""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter


def infer_tags(path: Path, content: str) -> list[str]:  # noqa: ARG001
    """Infer appropriate tags based on file path and content."""
    tags = []
    path_str = str(path).lower()

    # Path-based tags
    if "architecture" in path_str:
        tags.append("architecture")
    if "diagram" in path_str:
        tags.append("documentation")
    if "planning" in path_str:
        tags.append("planning")
    if "reference" in path_str:
        tags.append("reference")
    if "benchmark" in path_str:
        tags.append("benchmarking")
    if "model" in path_str and "training" in path_str:
        tags.append("training")
    if "dataset" in path_str:
        tags.append("datasets")
    if "labeling" in path_str:
        tags.append("labeling")
    if "iqa" in path_str or "quality" in path_str:
        tags.append("iqa")
    if "workflow" in path_str:
        tags.append("pipeline")
    if "pseudo" in path_str:
        tags.append("weak_supervision")
    if "production" in path_str or "runtime" in path_str:
        tags.append("production")
    if "monitoring" in path_str or "drift" in path_str:
        tags.append("monitoring")

    # Content-based fallback
    if not tags:
        tags.append("documentation")

    return tags[:4]  # Max 4 tags


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


def add_front_matter_to_file(path: Path, dry_run: bool = False) -> bool:
    """Add front matter to a file that's missing schema_type.

    Returns True if changes were made.
    """
    text = path.read_text(encoding="utf-8")

    # Check if file already has front matter
    try:
        post = frontmatter.loads(text)
        meta = post.metadata if isinstance(post.metadata, dict) else {}
    except Exception:
        meta = {}
        post = frontmatter.Post(text)

    # Check if already has valid schema_type
    if meta.get("schema_type") in ("common", "script", "knowledge", "planning"):
        return False

    # Extract existing content
    content = post.content if hasattr(post, "content") else text

    # Remove existing front matter from content if partial
    if text.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n", text, flags=re.DOTALL)
        if match:
            content = text[match.end() :]

    # Extract title and create purpose
    title = meta.get("title") or extract_title(content)
    purpose = meta.get("purpose") or infer_purpose(title, path)

    # Ensure purpose ends with punctuation
    if purpose and not purpose.strip().endswith((".", "!", "?")):
        purpose = purpose.strip() + "."

    # Build new front matter
    new_meta = {
        "schema_type": "common",
        "title": title,
        "status": meta.get("status", "draft"),
        "owner": meta.get("owner", "docs-team"),
        "purpose": purpose,
        "tags": meta.get("tags") or infer_tags(path, content),
    }

    # Preserve other existing fields that are valid
    if meta.get("description"):
        new_meta["description"] = meta["description"]

    # Remove redundant H1 from content (since title is in front matter)
    content_cleaned = re.sub(
        r"^\s*#\s+" + re.escape(title) + r"\s*$\n?",
        "",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    # Create new post
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


def main() -> int:
    """Process all markdown files in docs/ that have front matter issues."""
    import subprocess

    # Get list of files with issues
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

    import json

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to get validation results")
        return 1

    # Find files with schema_type issues
    files_to_fix = []
    for item in data:
        if not item["ok"]:
            errors = item.get("errors", [])
            for err in errors:
                if (
                    "schema_type" in err
                    or "Unable to extract tag using discriminator" in err
                ):
                    files_to_fix.append(Path(item["file"]))
                    break

    print(f"Found {len(files_to_fix)} files with schema_type issues")

    fixed = 0
    for path in files_to_fix:
        if path.exists() and add_front_matter_to_file(path, dry_run=False):
            fixed += 1

    print(f"Fixed {fixed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
