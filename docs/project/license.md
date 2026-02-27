---
schema_type: common
title: "License Information"
description: "CC-BY-SA-4.0 License and third-party license information"
tags: [license, legal, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the project license and third-party dependency licenses for legal compliance."
---

The Image Preprocessing Detector is released under the **Creative Commons Attribution-ShareAlike 4.0 International License** (CC-BY-SA-4.0), a copyleft license that allows commercial and private use while requiring attribution and share-alike terms for derivative works.

## CC-BY-SA-4.0

**Copyright (c) 2025 Byron Williams**

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
<https://creativecommons.org/licenses/by-sa/4.0/> or see the full text in the
[LICENSE](../../LICENSE) file.

## What This Means

### You CAN

- **Use commercially**: Build products and services using this software
- **Share**: Copy and redistribute the material in any medium or format
- **Adapt**: Remix, transform, and build upon the material for any purpose

### You MUST

- **Attribution**: Give appropriate credit, provide a link to the license, and indicate if changes were made
- **ShareAlike**: If you remix, transform, or build upon the material, you must distribute your contributions under the same license (CC-BY-SA-4.0 or a [compatible license](https://creativecommons.org/compatiblelicenses))
- **No additional restrictions**: You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits

### You CANNOT

- **Hold liable**: The licensor is not liable for damages or issues
- **Use trademarks**: Patent and trademark rights are not licensed

## Why CC-BY-SA-4.0?

This license was chosen because:

1. **Dataset compatibility**: Resolves the ShareAlike gray zone for key training datasets (kuzushiji, hiertext, midv2020) that use CC-BY-SA-4.0, adding ~496K clean training images
2. **Commercial viability**: Unlike CC-BY-NC licenses, commercial use is permitted
3. **Open ecosystem**: The ShareAlike requirement ensures derivatives remain open, benefiting the research community
4. **ML model standard**: CC-BY-SA-4.0 is widely used for ML model weights and datasets

See [LICENSE_IMPACT_REPORT.md](../planning/LICENSE_IMPACT_REPORT.md) for the full dataset license compatibility analysis (Scenario 2a).

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
| **Ruff** | MIT | Code formatting and linting |
| **BasedPyright** | MIT | Type checking |
| **pre-commit** | MIT | Git hooks |
| **Bandit** | Apache-2.0 | Security scanning |

## AGPL-3.0 Dependencies

**PyMuPDF** and **Ultralytics** are licensed under AGPL-3.0, which requires:

- Source code disclosure for network use
- Derivative works must use AGPL-3.0
- Commercial use requires compliance with AGPL terms

### Compliance Strategy

**Current Approach**: Service separation

- Use PyMuPDF and Ultralytics as separate services
- Communicate via JSON API (no code linking)
- No AGPL contamination of CC-BY-SA-4.0 codebase

### AGPL Compliance Checklist

For users deploying with PyMuPDF or Ultralytics:

- [ ] Provide source code access for AGPL components
- [ ] Include AGPL license text with AGPL components
- [ ] Document modifications to AGPL libraries
- [ ] Ensure network users can access source code

## License Compatibility

### Compatible Inbound Licenses

The following dependency licenses are compatible with CC-BY-SA-4.0:

- MIT (permissive)
- Apache-2.0 (permissive)
- BSD-3-Clause, BSD-2-Clause (permissive)
- ISC (permissive)
- CC0 (public domain)
- CC-BY-4.0 (one-way compatible into CC-BY-SA-4.0)

### Incompatible Licenses

- GPL-2.0, GPL-3.0 (incompatible copyleft -- GPL and CC-BY-SA-4.0 are separate copyleft families)
- AGPL-3.0 (network copyleft -- requires service separation)

### Outbound Compatibility

CC-BY-SA-4.0 derivatives must be shared under:

- CC-BY-SA-4.0 (same license)
- A [BY-SA Compatible License](https://creativecommons.org/compatiblelicenses) (currently includes GPL-3.0 for one-way compatibility)

## Commercial Use

### Using This Software Commercially

This software is free for commercial use under CC-BY-SA-4.0:

1. **SaaS Products**: Build cloud services using this software
2. **On-Premise Installations**: Deploy in customer environments
3. **Consulting Services**: Use in client projects
4. **ML Model Deployment**: Deploy trained models commercially

**Requirements for commercial use**:

- Provide attribution (credit, license link, indication of changes)
- Share derivative works under CC-BY-SA-4.0 or compatible license
- Do not apply additional restrictions

### Sharing Modified Versions

You may:

- Sell products or services built with this software
- Charge for support, training, or custom features

You must:

- Share modifications under CC-BY-SA-4.0 or a compatible license
- Provide attribution to the original project
- Indicate what changes were made

## Attribution

When using this software, attribution is **required**:

**Markdown**:

```markdown
Built with [Image Preprocessing Detector](https://github.com/williaby/image-preprocessing-detector)
by Byron Williams, licensed under [CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/).
```

**Code Comments**:

```python
# Image quality assessment using Image Preprocessing Detector
# https://github.com/williaby/image-preprocessing-detector
# Licensed under CC-BY-SA-4.0
```

## License Audit

To check licenses of all dependencies:

```bash
# Install license checker
uv add --group dev pip-licenses

# Generate license report
uv run pip-licenses --format=markdown --with-urls > licenses.md

# Check for GPL/AGPL
uv run pip-licenses | grep -E "GPL|AGPL"
```

## Legal Disclaimer

This license information is provided for convenience and may not be legally comprehensive. For legal advice on licensing, consult a qualified attorney.

**No Warranty**: This software is provided "as is" without warranty of any kind. See the full CC-BY-SA-4.0 license text in [LICENSE](../../LICENSE) for details.

## Questions

For licensing questions:

- **General Use**: Review the CC-BY-SA-4.0 terms at <https://creativecommons.org/licenses/by-sa/4.0/>
- **Commercial Use**: Contact the maintainers
- **Contributions**: See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## See Also

- [License File](../../LICENSE) - Full CC-BY-SA-4.0 legal text
- [License Impact Report](../planning/LICENSE_IMPACT_REPORT.md) - Dataset compatibility analysis
- [Contributing Guide](../../CONTRIBUTING.md) - Contribution guidelines
- [Code of Conduct](../../CODE_OF_CONDUCT.md) - Community standards

---

**Last Updated**: 2026-02-26
**License Version**: CC-BY-SA-4.0
