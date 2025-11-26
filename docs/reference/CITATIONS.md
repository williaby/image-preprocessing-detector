---
schema_type: common
title: "Dataset Citations and Attributions"
tags:
  - reference
  - datasets
  - research
status: published
owner: docs-team
purpose: Reference documentation for dataset citations and attributions.
---

This document provides proper citations for all datasets used or referenced in the Image Preprocessing Detector project. **Researchers must cite the appropriate papers when using these datasets in publications or derivative works.**

---

## Datasets Currently In Use

### DocLayNet

**Status**: ✅ **CURRENTLY USED** for validation (See `validation/DOCLAYNET_COVERAGE.md`)

**Citation**:

```bibtex
@inproceedings{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  author={Pfitzmann, Birgit and Auer, Christoph and Dolfi, Michele and Nassar, Ahmed S and Staar, Peter W J},
  booktitle={Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining},
  pages={3743--3751},
  year={2022},
  doi={10.1145/3534678.3539043}
}
```

**License**: CDLA-Permissive-2.0 (Community Data License Agreement)

**Access**:

- GitHub: <https://github.com/DS4SD/DocLayNet>
- Hugging Face: <https://huggingface.co/datasets/ds4sd/DocLayNet>
- Paper: <https://arxiv.org/abs/2206.01062>

**Usage in Project**:

- Validation of document element detection (Stage 3B)
- Ground truth for tables, figures, formulas, and footnotes
- 80,863 manually annotated pages across 6 document categories
- See `validation/DOCLAYNET_COVERAGE.md` for detailed coverage analysis

**Required Attribution**:
> This work uses the DocLayNet dataset (Pfitzmann et al., 2022), available under the CDLA-Permissive-2.0 license.

---

## Phase 2 Datasets (Planned for IQA Training)

### Genalog

**Status**: 🔨 **INFRASTRUCTURE READY** - Integrated for synthetic data generation (See [GENALOG_INTEGRATION.md](../research/genalog-integration.md))

**Citation**:

```bibtex
@misc{genalog2021,
  author={Microsoft},
  title={Genalog: An Open Source Python Package for Document Generation and Degradation},
  year={2021},
  howpublished={\url{https://github.com/microsoft/genalog}}
}
```

**License**: MIT License

**Access**:

- GitHub: <https://github.com/microsoft/genalog>
- Documentation: <https://microsoft.github.io/genalog/>
- PyPI: `pip install genalog`

**Usage in Project**:

- Synthetic document degradation for IQA training data augmentation
- Infrastructure complete (Phase 2 Week 1)
- See `src/image_preprocessing_detector/augmentation/` and [GENALOG_INTEGRATION.md](../research/genalog-integration.md)

**Required Attribution**:
> This work uses Genalog, an open-source synthetic document generation library from Microsoft, available under the MIT License.

### SOC Dataset (Sharpness-OCR-Correlation)

**Status**: 📋 **PLANNED** for Phase 2 functional validation

**Citation**:

```bibtex
@inproceedings{chen2015dataset,
  title={A Dataset for Quality Assessment of Camera Captured Document Images},
  author={Chen, Renjie and Luo, Cheng and Yu, Shangxuan and Ma, Huijun and Xue, Hanqing and Wang, Wei},
  booktitle={International Conference on Computer Analysis of Images and Patterns},
  pages={?--?},
  year={2015},
  organization={Springer}
}
```

**Access**: <https://github.com/rjchern/DIQA_CNN>

**Usage in Project**:

- Gold standard for RAG validation (OCR accuracy ground truth)
- 175 images with Tesseract accuracy scores
- Functional validation strategy described in `image_reference_sets.md`

**Required Attribution**:
> This work uses the SOC (Sharpness-OCR-Correlation) Dataset for functional document quality validation.

### DIQA-5000 (VQualA 2025 Challenge)

**Status**: 📋 **PLANNED** for Phase 2 perceptual IQA training

**Citation**:

```bibtex
@misc{vquala2025,
  title={VQualA 2025 Challenge: Document Image Quality Assessment},
  author={VQualA Challenge Organizers},
  year={2025},
  howpublished={\url{https://codalab.lisn.upsaclay.fr/competitions/23020}}
}
```

**Access**: <https://codalab.lisn.upsaclay.fr/competitions/23020>

**Usage in Project**:

- Perceptual quality assessment training data
- 5,000 images with MOS scores (sharpness, color fidelity)

**Required Attribution**:
> This work uses the DIQA-5000 dataset from the VQualA 2025 Challenge.

---

## Phase 3 Datasets (Planned for Layout Detection)

### PubLayNet

**Status**: 📋 **REFERENCE ONLY** - Not recommended for use (low diversity)

**Citation**:

```bibtex
@inproceedings{zhong2019publaynet,
  title={PubLayNet: Largest Dataset Ever for Document Layout Analysis},
  author={Zhong, Xu and Tang, Jianbin and Yepes, Antonio Jimeno},
  booktitle={2019 International Conference on Document Analysis and Recognition (ICDAR)},
  pages={1015--1022},
  year={2019},
  organization={IEEE}
}
```

**License**: CDLA-Permissive-1.0

**Access**: <https://github.com/ibm-aur-nlp/PubLayNet>

**Note**: Project uses **DocLayNet** instead due to superior source diversity (see `image_reference_sets.md` for rationale)

### TableBank

**Status**: 📋 **REFERENCE** - Alternative specialized table dataset if needed

**Citation**:

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: A Benchmark Dataset for Table Detection and Recognition},
  author={Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming and Li, Zhoujun},
  booktitle={Proceedings of the 12th Language Resources and Evaluation Conference},
  pages={1918--1925},
  year={2020}
}
```

**Access**: <https://doc-analysis.github.io/tablebank-page/>

### Marmot

**Status**: 📋 **REFERENCE** - Mathematical formula detection

**Citation**:

```bibtex
@inproceedings{marmot2013,
  title={A Dataset for Mathematical Formula Detection},
  author={Hu, Jingzhou and Kashi, Ramanujan S and Lopresti, Daniel P and Wilfong, Gordon T},
  booktitle={International Conference on Document Analysis and Recognition},
  year={2013},
  organization={Peking University}
}
```

**Access**: <https://www.icst.pku.edu.cn/cpdp/sjzy/>

### SignaTR6K

**Status**: 📋 **REFERENCE** - Handwriting segmentation

**Citation**:

```bibtex
@inproceedings{signatr6k2023,
  title={Handwritten and Printed Text Segmentation: A Signature Case Study},
  author={Gholamian, Sina and others},
  booktitle={Proceedings of the IEEE/CVF International Conference on Computer Vision},
  pages={?--?},
  year={2023}
}
```

**Access**: <https://arxiv.org/abs/2307.07887>

---

## Base Clean Document Datasets

### RVL-CDIP

**Status**: 📋 **REFERENCE** - Base clean documents for synthetic augmentation

**Citation**:

```bibtex
@inproceedings{harley2015rvlcdip,
  title={Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval},
  author={Harley, Adam W and Ufkes, Alex and Derpanis, Konstantinos G},
  booktitle={2015 13th International Conference on Document Analysis and Recognition (ICDAR)},
  pages={991--995},
  year={2015},
  organization={IEEE}
}
```

**Access**:

- Website: <https://adamharley.com/rvl-cdip/>
- Hugging Face: <https://huggingface.co/datasets/rvl_cdip>

### DocBank

**Status**: 📋 **REFERENCE** - Born-digital base documents

**Citation**:

```bibtex
@article{li2020docbank,
  title={DocBank: A Benchmark Dataset for Document Layout Analysis},
  author={Li, Minghao and Xu, Yiheng and Cui, Lei and Huang, Shaohan and Wei, Furu and Li, Zhoujun and Zhou, Ming},
  journal={arXiv preprint arXiv:2006.01038},
  year={2020}
}
```

**Access**: <https://doc-analysis.github.io/docbank-page/>

---

## Skew Detection Datasets

### DISEC'13

**Citation**:

```bibtex
@article{disec2019,
  title={A Document Skew Detection Method Using Fast Hough Transform},
  author={Authors},
  journal={arXiv preprint arXiv:1912.02504},
  year={2019}
}
```

**Access**: <https://arxiv.org/abs/1912.02504>

### Kaggle Noisy and Rotated Scanned Documents

**Citation**:
When using this dataset, cite as:
> Kaggle dataset: "Noisy and Rotated Scanned Documents" by Sthabile

**Access**: <https://www.kaggle.com/datasets/sthabile/noisy-and-rotated-scanned-documents>

---

## Citation Guidelines

### When to Cite

1. **Required Citations** (Must include in publications):
   - Any dataset **actively used** in training, validation, or testing
   - Currently: **DocLayNet** and **Genalog**

2. **Recommended Citations** (Include for completeness):
   - Datasets referenced in methodology sections
   - Datasets used for comparison or alternative approaches

3. **Optional Citations**:
   - Datasets mentioned only for context or background

### How to Cite in Publications

**In-Text Citation Example**:
> We validate our document element detection using the DocLayNet dataset (Pfitzmann et al., 2022), which provides 80,863 manually annotated pages across diverse document categories.

**Methods Section**:
> Our IQA training data was augmented using Genalog (Microsoft, 2021), a synthetic document degradation library. We validated functional OCR performance using the SOC dataset (Chen et al., 2015), which provides ground truth Tesseract accuracy scores for 175 images with varying blur levels.

**Acknowledgments Section**:
> This work uses the DocLayNet dataset, available under the CDLA-Permissive-2.0 license, and Genalog, available under the MIT License. We thank the authors and maintainers of these datasets for making them publicly available.

### Repository README Citation

Add to your project README:

```markdown
## Datasets Used

This project uses the following datasets:

- **DocLayNet** (Pfitzmann et al., 2022) - Document layout analysis validation
- **Genalog** (Microsoft, 2021) - Synthetic document degradation

Full citations available in [CITATIONS.md](../references/CITATIONS.md).
```

### License Compliance

| Dataset | License | Commercial Use | Attribution Required | Share-Alike |
|---------|---------|----------------|---------------------|-------------|
| **DocLayNet** | CDLA-Permissive-2.0 | ✅ Yes | ✅ Yes | ❌ No |
| **Genalog** | MIT | ✅ Yes | ✅ Yes | ❌ No |
| **PubLayNet** | CDLA-Permissive-1.0 | ✅ Yes | ✅ Yes | ❌ No |
| **RVL-CDIP** | Academic Use | ⚠️ Check | ✅ Yes | ❌ No |
| **TableBank** | Attribution Required | ✅ Yes | ✅ Yes | ❌ No |

---

## Updates

**How to Update This File**:

1. When adding a new dataset to the project:

   ```bash
   # Add entry to appropriate section above
   # Include: Citation, License, Access URLs, Usage in Project
   ```

2. When a dataset moves from "Planned" to "In Use":
   - Update status from 📋 **PLANNED** to ✅ **CURRENTLY USED**
   - Add detailed usage description
   - Update project README with citation

3. Quarterly review:
   - Verify all URLs are still valid
   - Check for updated dataset versions
   - Review license compliance

---

## Contact

For questions about dataset usage or citations in this project:

- Open an issue: <https://github.com/williaby/image-preprocessing-detector/issues>
- Email: <byronawilliams@gmail.com>

---

**Last Updated**: 2025-01-15
**Document Version**: 1.0
**Maintained by**: Image Preprocessing Detector Project Team
