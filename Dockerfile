# Image Preprocessing Detector API
# Multi-stage build for optimized production image

# ============================================================================
# Stage 1: Build stage with poetry
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=2.1.1
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Copy project files
COPY pyproject.toml poetry.lock* ./
COPY src/ ./src/
COPY benchmarks/ ./benchmarks/

# Configure poetry to not create virtualenv
RUN poetry config virtualenvs.create false

# Export requirements for production (base + api dependencies)
RUN poetry export -f requirements.txt --without-hashes --extras api > requirements.txt

# ============================================================================
# Stage 2: Production runtime
# ============================================================================
FROM python:3.11-slim as runtime

LABEL org.opencontainers.image.title="Image Preprocessing Detector API"
LABEL org.opencontainers.image.description="Intelligent image preprocessing detection for RAG document pipelines"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.source="https://github.com/williaby/image-preprocessing-detector"

# Create non-root user for security
RUN groupadd -r imgprep && useradd -r -g imgprep imgprep

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    # PDF processing (MuPDF dependencies)
    libmupdf-dev \
    # Health check
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/benchmarks ./benchmarks

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Create directories for temporary files and logs
RUN mkdir -p /app/tmp /app/logs && \
    chown -R imgprep:imgprep /app

# Switch to non-root user
USER imgprep

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV IMGPREP_API_TITLE="Image Preprocessing Detector API"
ENV IMGPREP_API_VERSION="0.1.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "image_preprocessing_detector.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info"]
