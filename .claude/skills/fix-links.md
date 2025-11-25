# Markdown Link Validation and Fixing

**Purpose**: Validate and fix broken relative links in markdown documentation.

**Usage**: `/fix-links [directory]` or `/fix-links --fix`

---

## Link Validation Checks

### 1. Relative Path Links

Check that all relative file links point to existing files:

```markdown
# Valid links
[README](../README.md)               ✅ File exists
[schema.py](src/schema.py)          ✅ File exists
[docs/](docs/)                      ✅ Directory exists

# Invalid links
[missing](../missing.md)            ❌ File not found
[broken](nonexistent/file.py)       ❌ Path doesn't exist
```

**Detection Pattern**:
```regex
\[([^\]]+)\]\(([^)#]+)(#[^\)]+)?\)
```

**Validation**:
- Extract link target (group 2)
- Skip external URLs (http://, https://, mailto:)
- Skip anchors-only links (#section)
- Resolve relative path from markdown file location
- Check if target file/directory exists

### 2. Anchor Links

Validate section anchors exist in target files:

```markdown
# Valid anchors
[See Overview](#overview)           ✅ Section exists in same file
[Setup](../README.md#installation)  ✅ Section exists in target file

# Invalid anchors
[Missing](#nonexistent-section)     ❌ Section not found
[Broken](doc.md#wrong-heading)      ❌ Heading doesn't exist
```

**Detection Pattern**:
```regex
#{1,6}\s+([^\n]+)
```

**Validation**:
- Extract all headings from target file
- Convert headings to anchor format (lowercase, replace spaces with -)
- Check if anchor exists in heading list

### 3. Absolute Paths

Warn about absolute paths that should be relative:

```markdown
# Should be relative
[File](/home/user/project/README.md)  ⚠️ Use relative path
[Docs](/absolute/path/docs/)          ⚠️ Use ./docs/ instead
```

### 4. External URLs

Optionally check external URL availability (with --check-external):

```markdown
# External URLs
[GitHub](https://github.com/williaby/image-preprocessing-detector)  ✅ Reachable
[Broken](https://example.com/404)                                   ❌ 404 Not Found
```

---

## Validation Workflow

### Step 1: Find All Markdown Files

```bash
# Recursively find .md files
find . -type f -name "*.md" | grep -v -E "(node_modules|\.venv|\.git|build|dist)"
```

**Exclude patterns**:
- `.venv/`, `node_modules/`, `.git/`
- `build/`, `dist/`, `__pycache__/`
- Hidden directories (starting with `.`)

### Step 2: Extract Links from Each File

For each markdown file:
```python
import re

link_pattern = r'\[([^\]]+)\]\(([^)#]+)(#[^\)]+)?\)'
matches = re.findall(link_pattern, markdown_content)

for link_text, link_target, anchor in matches:
    # Validate link_target and anchor
    pass
```

### Step 3: Validate Links

For each link:

1. **Skip external URLs**:
   ```python
   if link_target.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
       continue  # External link, skip or check if --check-external
   ```

2. **Skip anchor-only links**:
   ```python
   if not link_target and anchor:
       # Check anchor exists in current file
       validate_anchor(current_file, anchor)
   ```

3. **Resolve relative path**:
   ```python
   from pathlib import Path

   current_dir = Path(markdown_file).parent
   target_path = (current_dir / link_target).resolve()

   if not target_path.exists():
       report_broken_link(markdown_file, link_target)
   ```

4. **Validate anchor (if present)**:
   ```python
   if anchor:
       headings = extract_headings(target_path)
       anchor_clean = anchor.lstrip('#').lower().replace(' ', '-')
       if anchor_clean not in headings:
           report_broken_anchor(markdown_file, link_target, anchor)
   ```

### Step 4: Generate Report

Categorize issues:
- **Broken file links**: File/directory doesn't exist
- **Broken anchors**: Heading doesn't exist in target
- **Absolute paths**: Should be relative
- **External errors**: URL unreachable (optional)

---

## Output Format

```
🔗 Markdown Link Validation

📁 Scanning: docs/ (12 markdown files)

❌ Broken Links Found: 3

1. README.md:15
   Link: [Missing Doc](docs/missing.md)
   Issue: File not found
   Suggestion: Did you mean docs/overview.md?

2. docs/architecture.md:42
   Link: [Schema Details](../src/schema.py#wrongsection)
   Issue: Anchor #wrongsection not found in src/schema.py
   Available anchors:
     - #documentmetadata
     - #detectedissue
     - #pagemetadata
   Suggestion: Use #documentmetadata instead?

3. CONTRIBUTING.md:89
   Link: [Setup]($HOME/project/setup.md)
   Issue: Absolute path used
   Suggestion: Use ./setup.md (relative path)

⚠️ Warnings: 1

1. docs/api.md:23
   Link: [FastAPI Docs](https://fastapi.tiangolo.com/old-version/)
   Issue: External URL returns 404
   Note: Use --check-external to verify external links

---

📊 Summary:
- Total files scanned: 12
- Total links checked: 87
- ✅ Valid links: 84
- ❌ Broken links: 3
- ⚠️  Warnings: 1

🔧 Run with --fix to automatically fix broken links
```

---

## Auto-Fix Mode

When `--fix` flag is provided:

### Fix Strategy

1. **Broken file links**:
   ```python
   # Try to find similar files
   from difflib import get_close_matches

   all_md_files = find_all_markdown_files()
   suggestions = get_close_matches(broken_target, all_md_files, n=1, cutoff=0.6)

   if suggestions:
       # Replace link with suggested file
       new_link = calculate_relative_path(current_file, suggestions[0])
       replace_link_in_file(markdown_file, old_link, new_link)
   ```

2. **Broken anchors**:
   ```python
   # Find similar headings
   available_anchors = extract_headings(target_file)
   suggestions = get_close_matches(broken_anchor, available_anchors, n=1)

   if suggestions:
       # Replace anchor with suggested heading
       new_anchor = suggestions[0]
       replace_anchor_in_file(markdown_file, old_anchor, new_anchor)
   ```

3. **Absolute paths**:
   ```python
   # Convert to relative path
   relative_path = calculate_relative_path(current_file, absolute_target)
   replace_link_in_file(markdown_file, absolute_path, relative_path)
   ```

### Interactive Mode

Prompt user before each fix:

```
❌ Found: [Missing Doc](docs/missing.md)
💡 Suggestion: docs/overview.md (similarity: 85%)

Apply fix? (y/n/s/q)
  y - Yes, apply this fix
  n - No, skip this fix
  s - Skip all similar fixes
  q - Quit fix mode

Choice: _
```

---

## Advanced Features

### Similarity Matching

Use fuzzy matching to suggest fixes:

```python
from difflib import SequenceMatcher

def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# Example
broken_link = "docs/architcture.md"  # Typo
all_files = ["docs/architecture.md", "docs/overview.md"]

for file in all_files:
    ratio = similarity_ratio(broken_link, file)
    if ratio > 0.8:  # 80% similar
        suggest_fix(file, ratio)
```

### Anchor Generation

Generate correct anchor format from headings:

```python
def heading_to_anchor(heading: str) -> str:
    """Convert markdown heading to anchor format."""
    # Remove leading # and whitespace
    text = heading.lstrip('#').strip()

    # Lowercase
    text = text.lower()

    # Replace spaces with hyphens
    text = text.replace(' ', '-')

    # Remove special characters (keep alphanumeric and hyphens)
    text = re.sub(r'[^a-z0-9\-]', '', text)

    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text

# Example
heading = "## Project Overview & Goals"
anchor = heading_to_anchor(heading)  # "project-overview-goals"
```

### External URL Checking

When `--check-external` flag is provided:

```python
import requests

def check_external_url(url: str, timeout: int = 5) -> tuple[bool, int]:
    """Check if external URL is reachable."""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400, response.status_code
    except requests.RequestException:
        return False, 0

# Example
is_valid, status_code = check_external_url("https://github.com/williaby/repo")
if not is_valid:
    report_external_error(url, status_code)
```

---

## Configuration File

Support `.linkcheckrc.json` for custom settings:

```json
{
  "exclude_dirs": [
    ".venv",
    "node_modules",
    ".git",
    "build",
    "dist"
  ],
  "exclude_files": [
    "CHANGELOG.md",
    "tmp_cleanup/*.md"
  ],
  "check_external": false,
  "external_timeout": 5,
  "similarity_threshold": 0.8,
  "auto_fix": false,
  "ignore_patterns": [
    "https://example.com/.*",
    "mailto:.*"
  ]
}
```

---

## Success Criteria

- ✅ All markdown files scanned
- ✅ All relative file links validated
- ✅ All anchor links validated
- ✅ Absolute paths converted to relative
- ✅ No broken links remaining
- ✅ Suggestions provided for broken links
- ✅ Auto-fix applied successfully (if --fix used)

**Link Health**: 100% ✅

**Ready to commit**: All documentation links valid
