<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

# Third-Party Dataset Licenses

This document tracks licenses for all third-party datasets used in benchmarking.

## License Summary

| Dataset | License | Usage | Redistribution | Commercial Use |
|---------|---------|-------|----------------|----------------|
| DocLayNet | CDLA-Permissive-2.0 | ✓ | ✓ | ✓ |
| DocBank | CC-BY-4.0 | ✓ | ✓ | ✓ |
| TableBank | CC-BY-4.0 | ✓ | ✓ | ✓ |
| FinTabNet | CDLA-Permissive | ✓ | ✓ | ✓ |
| PubTabNet | CC-BY-4.0 | ✓ | ✓ | ✓ |
| COCO-Text | CC-BY-4.0 | ✓ | ✓ | ✓ |
| WiLI-2018 | CC-BY-SA-4.0 | ✓ | ✓ (share-alike) | ✓ |
| ICDAR MLT 2019 | RRC Terms | Eval only | ✗ | ✗ |
| OmniDocBench | CC-BY-NC-4.0 | Eval only | ✓ (non-commercial) | ✗ |

## Dataset Details

### DocLayNet

**Full Name**: DocLayNet - A Large Human-Annotated Dataset for Document-Layout Analysis

**License**: CDLA-Permissive-2.0

**Source**: <https://github.com/DS4SD/DocLayNet>

**Description**: 80,863 pages from financial reports, manuals, scientific articles. 11-class taxonomy for layout detection.

**Usage**: Full bundle use permitted. Commercial use allowed.

**Citation**:

```bibtex
@inproceedings{pfitzmann2022doclaynet,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis},
  author={Pfitzmann, Birgit and Auer, Christoph and Dolfi, Michele and Nassar, Ahmed S and Staar, Peter WJ},
  booktitle={Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining},
  pages={3743--3751},
  year={2022}
}
```

**SPDX-License-Identifier**: `CDLA-Permissive-2.0`

---

### DocBank

**Full Name**: DocBank - A Large-scale Dataset for Document Layout Analysis

**License**: CC-BY-4.0

**Source**: <https://doc-analysis.github.io/docbank-page/>

**Description**: 500K document pages with fine-grained layout annotations.

**Usage**: Full bundle use permitted. Attribution required.

**Citation**:

```bibtex
@inproceedings{li2020docbank,
  title={DocBank: A Benchmark Dataset for Document Layout Analysis},
  author={Li, Minghao and Xu, Yiheng and Cui, Lei and Huang, Shaohan and Wei, Furu and Li, Zhoujun and Zhou, Ming},
  booktitle={Proceedings of the 28th International Conference on Computational Linguistics},
  pages={949--960},
  year={2020}
}
```

**SPDX-License-Identifier**: `CC-BY-4.0`

---

### TableBank

**Full Name**: TableBank - A Benchmark Dataset for Table Detection and Recognition

**License**: CC-BY-4.0

**Source**: <https://doc-analysis.github.io/tablebank-page/>

**Description**: 417K table images from Word and LaTeX documents.

**Usage**: Evaluation use. Attribution required.

**Citation**:

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: Table Benchmark for Image-based Table Detection and Recognition},
  author={Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming and Li, Zhoujun},
  booktitle={Proceedings of the 12th Language Resources and Evaluation Conference},
  pages={1918--1925},
  year={2020}
}
```

**SPDX-License-Identifier**: `CC-BY-4.0`

---

### FinTabNet

**Full Name**: FinTabNet - Financial Table Extraction Dataset

**License**: CDLA-Permissive

**Source**: <https://developer.ibm.com/exchanges/data/all/fintabnet/>

**Description**: 113K tables from financial reports with structure annotations.

**Usage**: Full bundle use permitted. Commercial use allowed.

**Citation**:

```bibtex
@article{zheng2021global,
  title={Global table extractor (GTE): A framework for joint table identification and cell structure recognition using visual context},
  author={Zheng, Xinyi and Burdick, Doug and Popa, Lucian and Zhong, Xu and Wang, Nancy Xin Ru},
  journal={Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision},
  pages={697--706},
  year={2021}
}
```

**SPDX-License-Identifier**: `CDLA-Permissive`

---

### PubTabNet

**Full Name**: PubTabNet - Table Recognition from Scientific Publications

**License**: CC-BY-4.0

**Source**: <https://github.com/ibm-aur-nlp/PubTabNet>

**Description**: 568K table images from PubMed Central with HTML structure.

**Usage**: Evaluation use. Attribution required.

**Citation**:

```bibtex
@inproceedings{zhong2020image,
  title={Image-based table recognition: data, model, and evaluation},
  author={Zhong, Xu and ShafieiBavani, Elaheh and Jimeno Yepes, Antonio},
  booktitle={European Conference on Computer Vision},
  pages={564--580},
  year={2020},
  organization={Springer}
}
```

**SPDX-License-Identifier**: `CC-BY-4.0`

---

### COCO-Text

**Full Name**: COCO-Text - Dataset for Text Detection and Recognition

**License**: CC-BY-4.0

**Source**: <https://bgshih.github.io/cocotext/>

**Description**: 63K images with 145K text annotations. Includes printed/handwritten labels.

**Usage**: Full bundle use permitted. Attribution required.

**Citation**:

```bibtex
@inproceedings{veit2016coco,
  title={Coco-text: Dataset and benchmark for text detection and recognition in natural images},
  author={Veit, Andreas and Matera, Tomas and Neumann, Lukas and Matas, Jiri and Belongie, Serge},
  booktitle={arXiv preprint arXiv:1601.07140},
  year={2016}
}
```

**SPDX-License-Identifier**: `CC-BY-4.0`

---

### WiLI-2018

**Full Name**: WiLI-2018 - Wikipedia Language Identification Database

**License**: CC-BY-SA-4.0

**Source**: <https://dataset.cs.uni-duesseldorf.de/>

**Description**: 235K paragraphs in 235 languages for language identification.

**Usage**: Full bundle use permitted. Share-alike required for derivatives.

**Citation**:

```bibtex
@inproceedings{thoma2018wili,
  title={The WiLI benchmark dataset for written language identification},
  author={Thoma, Martin},
  booktitle={arXiv preprint arXiv:1801.07779},
  year={2018}
}
```

**SPDX-License-Identifier**: `CC-BY-SA-4.0`

---

### ICDAR MLT 2019

**Full Name**: ICDAR 2019 Robust Reading Competition on Multi-lingual Scene Text Detection and Recognition

**License**: RRC Terms (Evaluation Only)

**Source**: <https://rrc.cvc.uab.es/?ch=15>

**Description**: Multi-lingual scene text in 10 languages/scripts.

**Usage**: **Evaluation only**. No redistribution. No commercial use.

**Citation**:

```bibtex
@inproceedings{nayef2019icdar2019,
  title={ICDAR2019 robust reading challenge on multi-lingual scene text detection and recognition—RRC-MLT-2019},
  author={Nayef, Nibal and Yin, Fei and Bizid, Imen and Choi, Hyunsoo and others},
  booktitle={2019 International Conference on Document Analysis and Recognition (ICDAR)},
  pages={1582--1587},
  year={2019},
  organization={IEEE}
}
```

**SPDX-License-Identifier**: Proprietary

**⚠️ IMPORTANT**: This dataset cannot be redistributed. Use for evaluation only.

---

### OmniDocBench

**Full Name**: OmniDocBench - Unified Benchmark for Document Understanding

**License**: CC-BY-NC-4.0

**Source**: <https://opendatalab.com/OmniDocBench>

**Description**: Comprehensive benchmark covering layout, text, tables, formulas, and attributes.

**Usage**: **Evaluation only**. No commercial use. Attribution required.

**Citation**:

```bibtex
@article{li2024omnidocbench,
  title={OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations},
  author={Li, Linke and Qu, Bin and Huang, Botian and others},
  journal={arXiv preprint arXiv:2412.07626},
  year={2024}
}
```

**SPDX-License-Identifier**: `CC-BY-NC-4.0`

**⚠️ IMPORTANT**: Non-commercial use only. Cannot be used in production systems.

---

### Synthetic IQA

**Full Name**: Synthetic Image Quality Assessment Test Set (Internal)

**License**: CC0-1.0 (Public Domain)

**Source**: Generated internally

**Description**: Synthetic test images with controlled quality degradations (blur, skew, noise, contrast).

**Usage**: Unrestricted. Public domain.

**SPDX-License-Identifier**: `CC0-1.0`

---

## Compliance Guidelines

### Attribution Requirements

For datasets requiring attribution (CC-BY, CC-BY-SA, CC-BY-NC):

1. **Include dataset name and authors** in documentation
2. **Link to original source** in README and publications
3. **Include license text** in `licenses/third_party/`
4. **Cite papers** in publications using these datasets

### Redistribution Restrictions

**Cannot redistribute**:

- ICDAR MLT 2019 (RRC Terms)

**Non-commercial only**:

- OmniDocBench (CC-BY-NC-4.0)

**Share-alike required**:

- WiLI-2018 (CC-BY-SA-4.0) - Derivatives must use same license

### Commercial Use

**Allowed**:

- DocLayNet, DocBank, TableBank, FinTabNet, PubTabNet, COCO-Text, WiLI-2018

**Not allowed**:

- ICDAR MLT 2019, OmniDocBench

### Evaluation-Only Datasets

Some datasets are **evaluation-only** and should not be used for:

- Model training
- Commercial products
- Public redistribution

**Evaluation-only datasets**:

- ICDAR MLT 2019
- OmniDocBench

## Verification

To verify license compliance:

```bash
# Check SPDX headers in adapter files
grep -r "SPDX-License-Identifier" benchmarks/adapters/

# List all dataset licenses
cat benchmarks/LICENSES.md | grep "SPDX-License-Identifier"
```

## Adding New Datasets

When adding a new dataset:

1. **Research the license** - Check dataset homepage and papers
2. **Add entry to this document** with full details
3. **Add SPDX identifier** to adapter source code
4. **Store license text** in `licenses/third_party/{dataset_name}.txt`
5. **Update README.md** with usage restrictions
6. **Add citation** to papers and documentation

## License Texts

Full license texts are stored in `licenses/third_party/`:

```text
licenses/third_party/
├── CDLA-Permissive-2.0.txt
├── CC-BY-4.0.txt
├── CC-BY-SA-4.0.txt
├── CC-BY-NC-4.0.txt
└── CC0-1.0.txt
```

## References

- [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/)
- [Creative Commons Licenses](https://creativecommons.org/licenses/)
- [SPDX License List](https://spdx.org/licenses/)

---

**Last Updated**: 2025-11-12

For questions about dataset licensing, contact the project maintainer or consult the original dataset authors.
