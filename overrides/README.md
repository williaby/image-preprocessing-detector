# overrides/

**Purpose**: MkDocs theme customization and template overrides for documentation site.

## What Goes Here

**✅ Belongs in overrides/**:
- Custom MkDocs HTML templates
- Theme overrides (Jinja2 templates)
- Custom CSS/JavaScript for docs site
- Documentation layout customizations

**❌ Does NOT belong here**:
- **Documentation content** → `docs/` (markdown content files)
- **MkDocs config** → `mkdocs.yml` (root-level configuration)
- **Application UI** → `src/` (production application code)

## Current Files

### main.html
**Purpose**: Custom base template for MkDocs Material theme

**Customizations**:
- Modified header/footer
- Custom navigation structure
- Additional metadata tags
- Analytics integration (if configured)

## MkDocs Integration

Configured in `mkdocs.yml`:

```yaml
theme:
  name: material
  custom_dir: overrides
  features:
    - navigation.tabs
    - navigation.sections
```

## File Structure

```
overrides/
├── main.html           # Base template override
├── partials/           # Partial template overrides (future)
│   ├── header.html
│   └── footer.html
├── assets/             # Custom CSS/JS (future)
│   ├── stylesheets/
│   │   └── extra.css
│   └── javascripts/
│       └── extra.js
└── README.md
```

## Customization Guide

### Overriding Templates

MkDocs Material uses Jinja2 templates. To customize:

1. **Identify template**: Find template in Material theme source
2. **Copy to overrides/**: Copy template to `overrides/`
3. **Modify**: Edit template with custom content
4. **Test**: Run `mkdocs serve` to preview changes

### Adding Custom CSS

```css
/* overrides/assets/stylesheets/extra.css */
:root {
  --md-primary-fg-color: #0066cc;
}

.md-header {
  background-color: var(--md-primary-fg-color);
}
```

Register in `mkdocs.yml`:
```yaml
extra_css:
  - assets/stylesheets/extra.css
```

### Adding Custom JavaScript

```javascript
// overrides/assets/javascripts/extra.js
document.addEventListener('DOMContentLoaded', function() {
  console.log('Custom docs loaded');
});
```

Register in `mkdocs.yml`:
```yaml
extra_javascript:
  - assets/javascripts/extra.js
```

## Distinction from Other Folders

### vs. docs/
- **overrides/**: HTML templates and styling for docs site
- **docs/**: Actual markdown documentation content

### vs. site/
- **overrides/**: Source templates (committed to git)
- **site/**: Built documentation site (gitignored, generated)

## Best Practices

1. **Minimal Changes**: Only override what's necessary
2. **Comments**: Document why overrides exist
3. **Version Compatibility**: Test overrides when updating MkDocs Material
4. **Backup**: Keep original templates for reference

## Building Documentation

```bash
# Serve documentation locally
poetry run mkdocs serve

# Build static site
poetry run mkdocs build

# Output in site/ folder
```

## Theme Documentation

For MkDocs Material theme customization:
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Customization Guide](https://squidfunk.github.io/mkdocs-material/customization/)
- [Template Overrides](https://squidfunk.github.io/mkdocs-material/customization/#overriding-template-blocks)
