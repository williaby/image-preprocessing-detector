# ClusterFuzzLite Dockerfile for Image Preprocessing Detector
# Python fuzzing environment with Atheris and dependencies

FROM gcr.io/oss-fuzz-base/base-builder-python

# Install system dependencies for image/PDF processing
RUN apt-get update && apt-get install -y \
    clang \
    llvm \
    lld \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Note: Base image (gcr.io/oss-fuzz-base/base-builder-python) provides Python 3.11.13
# This is compatible with Atheris (supports Python 3.8-3.11, not 3.12+ due to PRECALL opcode changes)
# Project pyproject.toml updated to support Python 3.11+ for fuzzing compatibility

# Copy project source
COPY . $SRC/image-preprocessing-detector
WORKDIR $SRC/image-preprocessing-detector

# Copy build script to expected location
COPY .clusterfuzzlite/build.sh /src/build.sh
RUN chmod +x /src/build.sh
