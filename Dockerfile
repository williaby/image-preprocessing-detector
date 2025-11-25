# Multi-stage Dockerfile for Image Preprocessing Detector
# Optimized for production with security best practices and minimal image size
#
# Build: docker build -t image-preprocessing-detector .
# Run:   docker run -v $(pwd)/data:/app/data image-preprocessing-detector process input.pdf

# =============================================================================
# Stage 1: Builder - Install dependencies
# =============================================================================
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    # PDF processing
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to a virtual environment (without dev dependencies)
# This creates .venv/ which we'll copy to the final stage
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim

# Metadata labels (OCI standard)
LABEL org.opencontainers.image.title="Image Preprocessing Detector"
LABEL org.opencontainers.image.description="Intelligent image preprocessing detection system for RAG applications"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.authors="Byron Williams <byronawilliams@gmail.com>"
LABEL org.opencontainers.image.url="https://github.com/williaby/image-preprocessing-detector"
LABEL org.opencontainers.image.source="https://github.com/williaby/image-preprocessing-detector"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    # OpenCV runtime dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    # PDF processing
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories
RUN mkdir -p /app/data/input /app/data/output && chown -R appuser:appuser /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src

# Switch to non-root user
USER appuser

# Default command - run CLI help
CMD ["imgprep", "--help"]

# =============================================================================
# Usage Examples
# =============================================================================
# Process a PDF:
#   docker run -v $(pwd)/input:/app/data/input -v $(pwd)/output:/app/data/output \
#     image-preprocessing-detector process /app/data/input/document.pdf \
#     --output /app/data/output/result.json
#
# Interactive shell:
#   docker run -it --entrypoint /bin/bash image-preprocessing-detector
#
# =============================================================================
# Build with ML dependencies (larger image)
# =============================================================================
# For ML inference, build with ml extra:
#   docker build --build-arg INSTALL_ML=true -t image-preprocessing-detector:ml .
#
# ARG INSTALL_ML=false
# RUN if [ "$INSTALL_ML" = "true" ]; then uv sync --frozen --extra ml; fi

# =============================================================================
# Multi-architecture support
# =============================================================================
# Build for multiple platforms:
#   docker buildx build --platform linux/amd64,linux/arm64 -t image-preprocessing-detector:latest .
