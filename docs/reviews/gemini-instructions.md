# GEMINI.md

## Project Overview

This project, "Image Preprocessing Detector," is a Python-based intelligent system designed to prepare scanned documents and images for AI processing, particularly for Retrieval-Augmented Generation (RAG) applications. It automatically analyzes documents (PDFs, images) for quality issues like blurriness, skew, and noise, and identifies necessary preprocessing steps.

The system employs a multi-stage pipeline architecture. An initial "Text Detection Gate" routes documents to specialized paths: one for text-based documents that require layout analysis (detecting tables, images, handwriting) using a YOLOv8 model, and another for image-only documents that undergo Image Quality Assessment (IQA) using a hybrid of classical computer vision techniques and a lightweight CNN.

The final output is a structured JSON file containing metadata about detected issues, document elements with bounding boxes, and a history of transformations applied. This output is optimized for consumption by downstream OCR and document analysis tools.

## Building and Running

The project uses Poetry for dependency management and Nox for task automation.

### Setup

1.  **Install dependencies:**
    ```bash
    poetry install
    ```

2.  **Install development dependencies:**
    ```bash
    poetry install --with dev
    ```

3.  **Set up pre-commit hooks:**
    ```bash
    poetry run pre-commit install
    ```

### Running Tests

*   **Run all tests:**
    ```bash
    poetry run pytest -v
    ```

*   **Run tests with coverage:**
    ```bash
    poetry run pytest --cov=src/image_preprocessing_detector --cov-report=html
    ```

### Linting and Formatting

*   **Format code with Black:**
    ```bash
    poetry run black src tests
    ```

*   **Lint with Ruff:**
    ```bash
    poetry run ruff check --fix src tests
    ```

*   **Type-check with MyPy:**
    ```bash
    poetry run mypy src
    ```

### Documentation

*   **Build documentation:**
    ```bash
    nox -s docs
    ```

*   **Serve documentation locally:**
    ```bash
    nox -s serve
    ```

## Development Conventions

*   **Dependency Management:** The project uses [Poetry](https://python-poetry.org/) to manage dependencies. Dependencies are listed in `pyproject.toml`.
*   **Code Style:** Code is formatted with [Black](https://github.com/psf/black) and linted with [Ruff](https://github.com/astral-sh/ruff).
*   **Type Checking:** [MyPy](http://mypy-lang.org/) is used for static type checking.
*   **Testing:** [Pytest](https://pytest.org/) is the testing framework. Tests are located in the `tests/` directory.
*   **Automation:** [Nox](https://nox.thea.codes/) is used for automating tasks like testing, linting, and building documentation. See `noxfile.py` for available sessions.
*   **Pre-commit Hooks:** The project uses pre-commit hooks to enforce code quality standards before committing. See `.pre-commit-config.yaml` for the configured hooks.
*   **Conventional Commits:** The project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.
*   **Documentation:** Project documentation is built with [MkDocs](https://www.mkdocs.org/) and [MkDocs Material](https://squidfunk.github.io/mkdocs-material/). Source files are in the `docs/` directory.
