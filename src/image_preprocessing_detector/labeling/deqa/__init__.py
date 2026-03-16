"""DeQA-Doc inference engines for document image quality assessment.

Provides subprocess-isolated inference using pre-trained DeQA-Doc models
(mPLUG-Owl2-7B) that require a separate Python environment due to
incompatible transformers version (4.36.1 vs project's >=4.40.0).

Modules:

- **subprocess_runner**: Orchestrates inference via subprocess calls
  into the DeQA-Doc venv
- **bridge_script**: Standalone script that runs inside DeQA-Doc's venv
  (no image_detection dependencies)
"""
