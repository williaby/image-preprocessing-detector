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

# Note: Base image provides Python 3.8 which is compatible with Atheris
# Atheris requires Python <= 3.11 (doesn't support PRECALL opcode in 3.12+)

# Copy project source
COPY . $SRC/image-preprocessing-detector
WORKDIR $SRC/image-preprocessing-detector

# Install Poetry
RUN pip3 install poetry

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction

# Install Atheris fuzzing engine
RUN pip3 install atheris

# Copy fuzzing harnesses
COPY fuzz/*.py $OUT/
