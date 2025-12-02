# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for tools/validate_front_matter.py - Markdown front matter validation.

These tests verify the front matter validator correctly:
- Parses YAML front matter from Markdown files
- Validates against Pydantic schemas
- Enforces tag and owner allow-lists
- Auto-fixes common issues (tags, punctuation)
- Detects redundant H1 headings
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add tools directory to path for import
TOOLS_DIR = Path(__file__).parent.parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

# These tests require the frontmatter and ruamel.yaml packages
frontmatter = pytest.importorskip("frontmatter")
ruamel_yaml = pytest.importorskip("ruamel.yaml")

from validate_front_matter import (
    autofix_front_matter,
    load_allowlists,
    parse_front_matter,
    validate_file,
)


class TestLoadAllowlists:
    """Tests for the load_allowlists function."""

    @pytest.fixture
    def valid_allowlist_dir(self, tmp_path: Path) -> Path:
        """Create a valid _data directory with allow-lists."""
        data_dir = tmp_path / "_data"
        data_dir.mkdir()

        # Create tags allow-list
        tags_content = """
allowed:
  - documentation
  - api
  - security
  - testing
"""
        (data_dir / "tags.yml").write_text(tags_content)

        # Create owners allow-list
        owners_content = """
owners:
  byron:
    name: Byron Williams
    email: byron@example.com
  alice:
    name: Alice Smith
    email: alice@example.com
"""
        (data_dir / "owners.yml").write_text(owners_content)

        return tmp_path

    def test_load_valid_allowlists(self, valid_allowlist_dir: Path) -> None:
        """Test loading valid allow-lists."""
        allowed_tags, allowed_owners = load_allowlists(valid_allowlist_dir)

        assert "documentation" in allowed_tags
        assert "api" in allowed_tags
        assert "byron" in allowed_owners
        assert "alice" in allowed_owners

    def test_missing_tags_file_raises(self, tmp_path: Path) -> None:
        """Test that missing tags file raises FileNotFoundError."""
        data_dir = tmp_path / "_data"
        data_dir.mkdir()
        (data_dir / "owners.yml").write_text("owners: {}")

        with pytest.raises(FileNotFoundError, match="tags"):
            load_allowlists(tmp_path)

    def test_missing_owners_file_raises(self, tmp_path: Path) -> None:
        """Test that missing owners file raises FileNotFoundError."""
        data_dir = tmp_path / "_data"
        data_dir.mkdir()
        (data_dir / "tags.yml").write_text("allowed: []")

        with pytest.raises(FileNotFoundError, match="owners"):
            load_allowlists(tmp_path)


class TestParseFrontMatter:
    """Tests for the parse_front_matter function."""

    def test_parse_valid_front_matter(self, tmp_path: Path) -> None:
        """Test parsing valid YAML front matter."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test Document
tags:
  - documentation
  - api
---

# Content

Some content here.
""")

        meta, content = parse_front_matter(md_file)

        assert meta is not None
        assert meta["title"] == "Test Document"
        assert "documentation" in meta["tags"]
        assert "Content" in content

    def test_parse_missing_front_matter(self, tmp_path: Path) -> None:
        """Test parsing file without front matter."""
        md_file = tmp_path / "no_fm.md"
        md_file.write_text("""# Just a document

No front matter here.
""")

        meta, content = parse_front_matter(md_file)

        # Should return empty dict or None depending on implementation
        assert meta is not None  # frontmatter library returns empty dict

    def test_parse_invalid_yaml(self, tmp_path: Path) -> None:
        """Test parsing file with invalid YAML."""
        md_file = tmp_path / "invalid.md"
        md_file.write_text("""---
title: [invalid yaml
---

Content.
""")

        meta, content = parse_front_matter(md_file)

        # Should return None for invalid YAML
        assert meta is None or meta == {}


class TestAutofixFrontMatter:
    """Tests for the autofix_front_matter function."""

    def test_fix_tag_hyphens_to_underscores(self, tmp_path: Path) -> None:
        """Test converting hyphenated tags to snake_case."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test
tags:
  - api-design
  - security-testing
---

Content.
""")

        changed = autofix_front_matter(md_file)

        assert changed is True

        # Read updated content
        updated = md_file.read_text()
        assert "api_design" in updated
        assert "security_testing" in updated
        assert "api-design" not in updated

    def test_fix_tag_uppercase_to_lowercase(self, tmp_path: Path) -> None:
        """Test converting uppercase tags to lowercase."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test
tags:
  - API
  - Documentation
---

Content.
""")

        changed = autofix_front_matter(md_file)

        assert changed is True

        updated = md_file.read_text()
        assert "api" in updated
        assert "documentation" in updated

    def test_fix_purpose_punctuation(self, tmp_path: Path) -> None:
        """Test adding terminal punctuation to purpose field."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test
purpose: This is the purpose without punctuation
---

Content.
""")

        changed = autofix_front_matter(md_file)

        assert changed is True

        updated = md_file.read_text()
        assert "punctuation." in updated

    def test_no_changes_needed(self, tmp_path: Path) -> None:
        """Test no changes when front matter is already valid."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test
tags:
  - valid_tag
purpose: Already has punctuation.
---

Content.
""")

        changed = autofix_front_matter(md_file)

        assert changed is False

    def test_no_front_matter_returns_false(self, tmp_path: Path) -> None:
        """Test returns False when no front matter exists."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""# No front matter

Just content.
""")

        changed = autofix_front_matter(md_file)

        assert changed is False


class TestValidateFile:
    """Tests for the validate_file function."""

    @pytest.fixture
    def allowlists(self) -> tuple[set[str], set[str]]:
        """Provide sample allow-lists."""
        allowed_tags = {"documentation", "api", "security", "testing"}
        allowed_owners = {"byron", "alice"}
        return allowed_tags, allowed_owners

    def test_valid_file(self, tmp_path: Path, allowlists: tuple[set, set]) -> None:
        """Test validation of valid file."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "valid.md"
        md_file.write_text("""---
title: Valid Document
type: general
purpose: This is a valid document.
owner: byron
tags:
  - documentation
  - api
---

Content without redundant H1.
""")

        # Mock the FM_ADAPTER validation to avoid importing the full contract
        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners)

        assert result["ok"] is True
        assert len(result["errors"]) == 0

    def test_unknown_tag_error(
        self, tmp_path: Path, allowlists: tuple[set, set]
    ) -> None:
        """Test validation fails for unknown tag."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "invalid_tag.md"
        md_file.write_text("""---
title: Document
type: general
tags:
  - unknown_tag
---

Content.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners)

        assert result["ok"] is False
        assert any("unknown tag" in err.lower() for err in result["errors"])

    def test_unknown_owner_error(
        self, tmp_path: Path, allowlists: tuple[set, set]
    ) -> None:
        """Test validation fails for unknown owner."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "invalid_owner.md"
        md_file.write_text("""---
title: Document
type: general
owner: unknown_person
---

Content.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners)

        assert result["ok"] is False
        assert any("unknown owner" in err.lower() for err in result["errors"])

    def test_redundant_h1_warning(
        self, tmp_path: Path, allowlists: tuple[set, set]
    ) -> None:
        """Test detection of redundant H1 heading."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "with_h1.md"
        md_file.write_text("""---
title: Document Title
type: general
---

# Document Title

This H1 is redundant because title is in front matter.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners)

        assert result["ok"] is False
        assert any("redundant h1" in err.lower() for err in result["errors"])

    def test_h1_in_code_block_ignored(
        self, tmp_path: Path, allowlists: tuple[set, set]
    ) -> None:
        """Test that H1 in code blocks is not flagged."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "code_h1.md"
        md_file.write_text("""---
title: Document
type: general
---

Some content.

```markdown
# This H1 is in a code block and should be ignored
```

More content.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners)

        # Should not flag the H1 in the code block
        h1_errors = [err for err in result["errors"] if "redundant h1" in err.lower()]
        assert len(h1_errors) == 0

    def test_autofix_flag(self, tmp_path: Path, allowlists: tuple[set, set]) -> None:
        """Test that autofix flag triggers fixes."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "needs_fix.md"
        md_file.write_text("""---
title: Document
type: general
tags:
  - API-Design
---

Content.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, allowed_tags, allowed_owners, autofix=True)

        assert result["fixed"] is True

        # Verify the file was modified
        updated = md_file.read_text()
        assert "api_design" in updated

    def test_missing_front_matter(
        self, tmp_path: Path, allowlists: tuple[set, set]
    ) -> None:
        """Test validation fails for missing front matter."""
        allowed_tags, allowed_owners = allowlists

        md_file = tmp_path / "no_fm.md"
        md_file.write_text("""# Just a heading

No front matter at all.
""")

        result = validate_file(md_file, allowed_tags, allowed_owners)

        # Validation should fail for missing front matter
        # The file will have an empty metadata dict, which will fail Pydantic validation
        # or the H1 will be flagged as redundant
        assert result["ok"] is False
        assert len(result["errors"]) > 0


class TestResultStructure:
    """Tests for validation result structure."""

    def test_result_has_required_fields(self, tmp_path: Path) -> None:
        """Test that validation result has all required fields."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""---
title: Test
type: general
---

Content.
""")

        with patch("validate_front_matter.FM_ADAPTER") as mock_adapter:
            mock_adapter.validate_python = MagicMock()

            result = validate_file(md_file, set(), set())

        assert "file" in result
        assert "ok" in result
        assert "errors" in result
        assert "fixed" in result

        assert isinstance(result["file"], str)
        assert isinstance(result["ok"], bool)
        assert isinstance(result["errors"], list)
        assert isinstance(result["fixed"], bool)
