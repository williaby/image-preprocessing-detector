# ClusterFuzzLite Dockerfile for Image Preprocessing Detector
# Python fuzzing environment with Atheris and dependencies

FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:122afa48603810a0c6b495ab2e1cfdc5a88e4378ab051d3a83f666bd69b4eb0b

# Install system dependencies for image/PDF processing
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpoppler-cpp-dev \
    lld \
    llvm \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Note: Base image (gcr.io/oss-fuzz-base/base-builder-python) provides Python 3.10.14
# This is compatible with Atheris (supports Python 3.8-3.11, not 3.12+ due to PRECALL opcode changes)
# Project pyproject.toml updated to support Python 3.10+ for fuzzing compatibility

# Copy project source
COPY . $SRC/image-preprocessing-detector
WORKDIR $SRC/image-preprocessing-detector

# Copy build script to expected location
COPY .clusterfuzzlite/build.sh /src/build.sh
RUN chmod +x /src/build.sh
