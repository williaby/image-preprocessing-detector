---
schema_type: common
title: "License Information"
description: "MIT License and third-party license information"
tags: [license, legal, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the project license and third-party dependency licenses for legal compliance."
---

The Image Preprocessing Detector is released under the MIT License, a permissive open-source license that allows commercial and private use with minimal restrictions.

## MIT License

**Copyright (c) 2025 Byron Williams**

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## What This Means

### You CAN

- ✅ **Use commercially**: Build products and services using this software
- ✅ **Modify**: Adapt the code for your needs
- ✅ **Distribute**: Share the software with others
- ✅ **Sublicense**: Include in proprietary software
- ✅ **Private use**: Use for internal projects without sharing changes

### You MUST

- 📋 **Include license**: Include the MIT License text in distributions
- 📋 **Include copyright**: Preserve copyright notices

### You CANNOT

- ❌ **Hold liable**: Authors are not liable for damages or issues
- ❌ **Use trademarks**: The name and logo are not licensed

## Third-Party Licenses

This project depends on several open-source libraries. Their licenses are listed below:

### Core Dependencies

| Package | License | Use Case |
|---------|---------|----------|
| **PyMuPDF** | AGPL-3.0 | PDF extraction |
| **Pillow** | HPND | Image I/O |
| **OpenCV** | Apache-2.0 | Computer vision algorithms |
| **Pydantic** | MIT | Data validation |
| **Click** | BSD-3-Clause | CLI framework |
| **structlog** | MIT / Apache-2.0 | Structured logging |
| **rich** | MIT | Console output |

### ML Dependencies (Phase 2+)

| Package | License | Use Case |
|---------|---------|----------|
| **PyTorch** | BSD-3-Clause | Deep learning framework |
| **torchvision** | BSD-3-Clause | Computer vision models |
| **Ultralytics** | AGPL-3.0 | YOLOv8 implementation |
| **Albumentations** | MIT | Data augmentation |
| **ONNX Runtime** | MIT | Production inference |

### API Dependencies (Phase 4)

| Package | License | Use Case |
|---------|---------|----------|
| **FastAPI** | MIT | REST API framework |
| **Uvicorn** | BSD-3-Clause | ASGI server |
| **Celery** | BSD-3-Clause | Async task queue |

### Development Dependencies

| Package | License | Use Case |
|---------|---------|----------|
| **pytest** | MIT | Testing framework |
| **Black** | MIT | Code formatting |
| **Ruff** | MIT | Linting |
| **MyPy** | MIT | Type checking |
| **pre-commit** | MIT | Git hooks |
| **Bandit** | Apache-2.0 | Security scanning |

## AGPL-3.0 Dependencies

**PyMuPDF** and **Ultralytics** are licensed under AGPL-3.0, which requires:

- Source code disclosure for network use
- Derivative works must use AGPL-3.0
- Commercial use requires compliance with AGPL terms

### Compliance Strategy

**Option 1: Keep MIT License (Recommended)**
- Use PyMuPDF and Ultralytics as separate services
- Communicate via JSON API (no code linking)
- No AGPL contamination of MIT codebase

**Option 2: Dual Licensing**
- Core library: MIT License
- ML components: AGPL-3.0 License
- Clearly document separation

**Option 3: Replace AGPL Dependencies**
- PyMuPDF → pdfplumber (MIT) or PyPDF2 (BSD)
- Ultralytics → Detectron2 (Apache-2.0) or MMDetection (Apache-2.0)

**Current Approach**: Option 1 (service separation)

### AGPL Compliance Checklist

For users deploying with PyMuPDF or Ultralytics:

- [ ] Provide source code access for AGPL components
- [ ] Include AGPL license text with AGPL components
- [ ] Document modifications to AGPL libraries
- [ ] Ensure network users can access source code

## License Compatibility

### Compatible Licenses

The MIT License is compatible with:
- ✅ Apache-2.0 (permissive)
- ✅ BSD-3-Clause (permissive)
- ✅ BSD-2-Clause (permissive)
- ✅ ISC (permissive)
- ✅ CC0 (public domain)

### Incompatible Licenses

The MIT License is NOT compatible with:
- ❌ GPL-2.0 (copyleft, requires GPL)
- ❌ GPL-3.0 (copyleft, requires GPL)
- ⚠️ AGPL-3.0 (network copyleft, requires service separation)

## Commercial Use

### Using This Software Commercially

This software is free for commercial use under the MIT License:

1. **SaaS Products**: Build cloud services using this software
2. **On-Premise Installations**: Deploy in customer environments
3. **Embedded Systems**: Include in hardware products
4. **Consulting Services**: Use in client projects

**Requirements**:
- Include MIT License text in distributions
- Preserve copyright notices
- No warranty or liability claims

### Selling Modified Versions

You may:
- Sell proprietary software that uses this library
- Keep your modifications closed-source
- Charge for support, training, or custom features

You must:
- Include the original MIT License text
- Preserve copyright notices

## Attribution

When using this software, we appreciate (but don't require) attribution:

**Markdown**:
```markdown
Built with [Image Preprocessing Detector](https://github.com/williaby/image-preprocessing-detector) by Byron Williams.
```

**HTML**:
```html
<p>Powered by <a href="https://github.com/williaby/image-preprocessing-detector">Image Preprocessing Detector</a></p>
```

**Code Comments**:
```python
# Image quality assessment using Image Preprocessing Detector
# https://github.com/williaby/image-preprocessing-detector
```

## License Audit

To check licenses of all dependencies:

```bash
# Install license checker
poetry add --group dev pip-licenses

# Generate license report
poetry run pip-licenses --format=markdown --with-urls > licenses.md

# Check for GPL/AGPL
poetry run pip-licenses | grep -E "GPL|AGPL"
```

## Updating Licenses

If you modify this project:

1. **Keep MIT License**: Retain original MIT License text
2. **Add Your Copyright**: Add your copyright alongside existing ones
3. **Document Changes**: Note modifications in CHANGELOG.md
4. **Update Dependencies**: Run license audit for new dependencies

## Legal Disclaimer

This license information is provided for convenience and may not be legally comprehensive. For legal advice on licensing, consult a qualified attorney.

**No Warranty**: This software is provided "as is" without warranty of any kind. See the full MIT License text above for details.

## Questions

For licensing questions:
- **General Use**: Review the MIT License text above
- **Commercial Use**: Contact the maintainers
- **Contributions**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## See Also

- [License File](../../LICENSE) - Full MIT License text
- [Contributing Guide](../../CONTRIBUTING.md) - Contribution guidelines
- [Code of Conduct](../../CODE_OF_CONDUCT.md) - Community standards
- [Third-Party Notices](../../THIRD_PARTY_NOTICES.md) - Complete dependency licenses

---

**Last Updated**: 2025-11-08
**License Version**: MIT (unchanged since project inception)
